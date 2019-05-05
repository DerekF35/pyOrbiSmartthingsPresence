import yaml
import re
import requests

def setOnline( deviceName ):
	hostPingRequest( deviceName , 'online')

def setOffline( deviceName ):
	hostPingRequest( deviceName , 'offline')

def hostPingRequest( deviceName , state ):
	ide=config['smartthings_ide']
	app_id=config['host_pinger_app_id']
	access_token=config['host_pinger_access_token']
	myUrl = f"{ide}/api/smartapps/installations/{app_id}/statechanged/{state}?access_token={access_token}&ipadd={deviceName}"
	print(myUrl)
	r = requests.get(myUrl)


CONFIG_FILE='config.yml'
CACHE_FILE='cache.yml'

config = yaml.load(open(CONFIG_FILE))

try:
	prevState = yaml.load(open(CACHE_FILE))
except FileNotFoundError:
    prevState = { 'found': [] , 'not_found': [] }

from pynetgear import Netgear

netgear = Netgear( password=config['orbi_password'], ssl=False )

currentDevices = netgear.get_attached_devices()

devicesFound = []
devicesNotFound = []

for device in config['rules']:

	print(device)
	print(config['rules'][device])

	myFound = False

	for i in currentDevices:
		if re.match( config['rules'][device]['pattern'] , getattr( i , config['rules'][device]['field'] ) ):
			print(i)
			myFound = True

	if myFound:
		print("{0}: Device was found.  Adding to devicesFound".format( device ) )
		devicesFound.append(device)
	else:
		print("{0}: Device was NOT found.  Adding to devicesNotFound".format( device ) )
		devicesNotFound.append(device)

print('FOUND DEVICES')
print('=============')
print(devicesFound)

print()

print('NOT FOUND DEVICES')
print('=================')
print(devicesNotFound)



for device in devicesFound:
	if device in prevState['found']:
		print('Device found in found cache.  Skipping action.')
	else:
		print('Device not found in found cache. Taking action.')
		setOnline(device)

for device in devicesNotFound:
	if device in prevState['not_found']:
		print('Device found in not_found cache.  Skipping action.')
	else:
		print('Device not found in not_found cache. Taking action.')
		setOffline(device)

with open(CACHE_FILE, 'w') as outfile:
	myCache = { 'found': devicesFound, 'not_found': devicesNotFound }
	yaml.dump( myCache, outfile, default_flow_style=False)
