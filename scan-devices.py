#!/usr/bin/env python

import json
import logging
import re
import requests
import time
import yaml
import pprint
import copy

from pynetgear_enhanced import NetgearEnhanced

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

logging.basicConfig(format='[%(levelname)s][%(asctime)s] %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.INFO)
pp = pprint.PrettyPrinter(indent=4)

CONFIG_FILE='config.yml'
CACHE_FILE='cache.yml'
DEVICE_FILE='device_history/devices.json'

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

try:
	prevState = yaml.load(open(CACHE_FILE), Loader=yaml.FullLoader)
except FileNotFoundError:
	prevState = { 'found': [] , 'not_found': [] }

netgear = NetgearEnhanced( password=config['orbi_password'] )

currentDevices = netgear.get_attached_devices_2()

for device in currentDevices:
	logging.debug("Device: " + json.dumps(device) )

nowSeconds = time.strftime('%Y%m%d_%H%M%S')

devicesFound = []
devicesNotFound = []

for device in config['rules']:

	logging.info("Checking device: " + device)
	logging.debug( "Rules: " + json.dumps(config['rules'][device]) )

	myFound = False

	for i in currentDevices:
		if re.match( config['rules'][device]['pattern'] , getattr( i , config['rules'][device]['field'] ) ):
			myFound = True

	if myFound:
		logging.debug("Device %s was found.  Adding to devicesFound", device )
		devicesFound.append(device)
	else:
		logging.debug("Device %s was NOT found.  Adding to devicesNotFound", device )
		devicesNotFound.append(device)

logging.info('FOUND DEVICES: ' + json.dumps(devicesFound))
logging.info('NOT FOUND DEVICES: ' + json.dumps(devicesNotFound))

for device in devicesFound:
	if device in prevState['found']:
		logging.info(f'{device} found in found cache.  Skipping action.')
	else:
		logging.info(f'{device} not found in found cache. Taking action.')
		setOnline(device)

for device in devicesNotFound:
	if device in prevState['not_found']:
		logging.info(f'{device} found in not_found cache.  Skipping action.')
	else:
		logging.info(f'{device} not found in not_found cache. Taking action.')
		setOffline(device)

with open(CACHE_FILE, 'w') as outfile:
	myCache = {
		'found': devicesFound,
		'not_found': devicesNotFound
	}
	yaml.dump( myCache, outfile, default_flow_style=False)

try:
	with open(DEVICE_FILE, "r") as read_file:
		devices = json.load(read_file)
except FileNotFoundError:
	devices = {}

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

	myLastKnown = {}

	for i in ['name','type','device_type','model','ssid']:
		try:
			myLastKnown[i] = devices[myMac][i]
		except KeyError:
			pass

	if myMac in devices:
		devices[myMac]['last_seen'] = nowSeconds

		if myLastKnown != myDevicesAttrbs:
			logging.info("Device update found for " + myMac)

			devices[myMac].update(myDevicesAttrbs)

			# migrate old data
			try:
				devices[myMac]['attrb_history'] = devices[myMac].pop('attrbs')
			except KeyError:
				pass

			devices[myMac]['attrb_history'][nowSeconds] = copy.deepcopy(myDevicesAttrbs)

			postSlack( config["slack_channel"] , f"DEVICE UPDATED: `{myMac}`\n```\nName: {myName}\nDevice Type: {myDeviceType}\nConnection: {myType}\nModel: {myModel}\nSSID: {mySSID}```")
	else:
		myDevice = copy.deepcopy(myDevicesAttrbs)

		myDevice['first_seen'] = nowSeconds
		myDevice['last_seen'] = nowSeconds
		myDevice['attrb_history'] = {}
		myDevice['attrb_history'][nowSeconds] = copy.deepcopy(myDevicesAttrbs)

		logging.debug(myDevice)
		devices[myMac] = myDevice
		postSlack( config["slack_channel"] , f"NEW DEVICE CONNECTED: `{myMac}`\n```\nName: {myName}\nConnection: {myType}```")


with open(DEVICE_FILE, 'w') as outfile:
	pp.pprint(devices)
	json.dump( devices, outfile , sort_keys=True, indent=4)
