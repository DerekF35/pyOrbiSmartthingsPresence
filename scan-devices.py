#!/usr/bin/env python

import json
import logging
import re
import requests
import time
import yaml
import copy
import sqlite3

from pynetgear_enhanced import NetgearEnhanced

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# TODO: input the logging level
logging.basicConfig(format='[%(levelname)s][%(asctime)s] %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.INFO)

CONFIG_FILE='config.yml'
CACHE_FILE='cache.yml'
DATA_LOCATION='device_history/'
DEVICE_FILE='device_history/devices.json'
# TODO: Make this an input
SLACK_NOTIFY=True
TIMESTAMP_FORMAT="YYYY-MM-DD HH:MM"

def setOnline( deviceName ):
	hostPingRequest( deviceName , 'online')

def setOffline( deviceName ):
	hostPingRequest( deviceName , 'offline')

def hostPingRequest( deviceName , state ):
	ide=config['smartthings_ide']
	app_id=config['host_pinger_app_id']
	access_token=config['host_pinger_access_token']
	myUrl = f"{ide}/api/smartapps/installations/{app_id}/statechanged/{state}?access_token={access_token}&ipadd={deviceName}"
	r = requests.get(myUrl)

def postSlack( channel , text ):
	myUrl = config["slack_webhook_url"]
	myData = {
		"text": text
	}
	response = requests.post(
	    myUrl, data=json.dumps(myData),
	    headers={'Content-Type': 'application/json'}
	)
	if response.status_code != 200:
	    raise ValueError(
	        'Request to slack returned an error %s, the response is:\n%s'
	        % (response.status_code, response.text)
	    )

config = yaml.load(open(CONFIG_FILE), Loader=yaml.FullLoader)

conn = sqlite3.connect(DATA_LOCATION + config['database'])
conn.row_factory = lambda c, r: dict([(col[0], r[idx]) for idx, col in enumerate(c.description)])
c = conn.cursor()


c.execute("CREATE TABLE IF NOT EXISTS devices ( mac TEXT PRIMARY KEY , data BLOB, first_seen TEXT  , last_seen TEXT ); ")
c.execute("CREATE TABLE IF NOT EXISTS device_history ( mac TEXT , timestamp TEXT , data BLOB ); ")
c.execute("CREATE TABLE IF NOT EXISTS cache ( device TEXT PRIMARY KEY, found INTEGER  ); ")
conn.commit()

netgear = NetgearEnhanced( url=config['orbi_host'] , password=config['orbi_password'], force_login_v2=True )

currentDevices = netgear.get_attached_devices_2()

for device in currentDevices:
	logging.debug("Device: " + json.dumps(device) )

nowSeconds = time.strftime('%Y%m%d_%H%M%S')

for device in config['rules']:

	logging.info("Checking device: " + device)
	logging.debug( "Rules: " + json.dumps(config['rules'][device]) )

	myFound = False

	for i in currentDevices:
		if re.match( config['rules'][device]['pattern'] , getattr( i , config['rules'][device]['field'] ) ):
			myFound = True

	logging.debug("Device %s current status is found = %s.", device , myFound )

	cacheFound = None

	c.execute('SELECT found FROM cache WHERE device = ?' , (device,) )
	r = c.fetchone()
	if r is not None:
		if r['found'] == 1 :
			cacheFound = True
		else:
			cacheFound = False

	logging.debug("Device %s cache status is found = %s.", device , cacheFound )

	if cacheFound is not None and cacheFound == myFound:
		logging.info(f'{device} found matches cache.  Skipping action.')
	else:
		logging.info(f'{device} found mismatch with cache.  Taking action.')
		if myFound:
			logging.info(f'{device} setting online.')
			setOnline(device)
		else:
			logging.info(f'{device} setting offline.')
			setOffline(device)

		c.execute("INSERT OR REPLACE INTO cache ( device , found ) VALUES ( ? , ? )" , ( device, myFound ,) )
		conn.commit()

for i in currentDevices:
	logging.debug("Device: " + json.dumps(i))
	myMac = i.mac
	myName = i.name
	myType = i.type
	myModel = i.device_model
	myDeviceType = i.device_type
	mySSID = i.ssid

	myDevicesAttrbs = {
		'name': myName,
		'type': myType,
		'model': myModel,
		'device_type': myDeviceType,
		'ssid': mySSID,
	}

	myNewDevice = False
	myLastKnown = c.execute("SELECT data FROM devices WHERE mac = ?", (myMac,) ).fetchone()

	if myLastKnown is None:
		myLastKnown = {}
		myNewDevice = True
	else:
		myLastKnown = json.loads(myLastKnown['data'])

	logging.debug("Last Known Device: " + json.dumps(myLastKnown))

	for i in ['name','type','device_type','model','ssid']:
		try:
			myLastKnown[i] = myDevicesAttrbs[i]
		except KeyError:
			pass

	if myNewDevice:
		c.execute( "INSERT INTO devices (mac , data , first_seen , last_seen) VALUES ( ? , ? , datetime('now', 'localtime') , datetime('now', 'localtime') )",(myMac,json.dumps(myDevicesAttrbs),) )
		c.execute( "INSERT INTO device_history (mac , timestamp , data) VALUES ( ? , datetime('now', 'localtime') , ? )",(myMac,json.dumps(myDevicesAttrbs),) )
		conn.commit()
		if SLACK_NOTIFY:
			postSlack( config["slack_channel"] , f"NEW DEVICE CONNECTED: `{myMac}`\n```\nName: {myName}\nConnection: {myType}```")
	else:
		c.execute( "UPDATE devices SET last_seen = datetime('now', 'localtime') WHERE mac = ?",(myMac,) )
		conn.commit()

		updateMade = False

		for x in ['name','model']:
			if myLastKnown[x] != myDevicesAttrbs[x]:
				updateMade = True

		if updateMade:
			logging.info("Device update found for " + myMac)

			c.execute( "UPDATE devices SET data = ? WHERE mac = ?",(json.dumps(myDevicesAttrbs),myMac,) )
			c.execute( "INSERT INTO device_history (mac , timestamp , data) VALUES ( ? , datetime('now', 'localtime')  ? )",(myMac,json.dumps(myDevicesAttrbs),) )

			if SLACK_NOTIFY:
				postSlack( config["slack_channel"] , f"DEVICE UPDATED: `{myMac}`\n```\nName: {myName}\nDevice Type: {myDeviceType}\nConnection: {myType}\nModel: {myModel}\nSSID: {mySSID}```")

conn.close()
