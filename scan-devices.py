import json
import logging
import re
import requests
import yaml

from pynetgear_enhanced import NetgearEnhanced

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

logging.basicConfig(format='[%(levelname)s][%(asctime)s] %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.INFO)

CONFIG_FILE='config.yml'
CACHE_FILE='cache.yml'

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

config = yaml.load(open(CONFIG_FILE), Loader=yaml.FullLoader)

try:
	prevState = yaml.load(open(CACHE_FILE), Loader=yaml.FullLoader)
except FileNotFoundError:
    prevState = { 'found': [] , 'not_found': [] }

netgear = NetgearEnhanced( password=config['orbi_password'] )

currentDevices = netgear.get_attached_devices()

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
	myCache = { 'found': devicesFound, 'not_found': devicesNotFound }
	yaml.dump( myCache, outfile, default_flow_style=False)
