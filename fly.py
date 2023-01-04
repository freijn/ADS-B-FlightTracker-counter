#####################################################
#Frank Reijn's airplane to Domoticz/Home Assistant Pyhton script.
# Version 3.2
# This script is loading the flights json file and print all the objects with the key "flight"
# Additional of  the following libraries in python are required : math,time,requests
# The install command is depending on the OS. Please use google for HowTo.
# Many thanks to Ilaria for helping out here.
# By removing some libraries speed has increased a lot compaired with the older script.
# 202204029 Added MQTT messages
# 20221020 optimize MQTTmsg and Domoticz OnOff  
#####################################################

import math
import time
import requests
import time
from requests.auth import HTTPBasicAuth
from time import gmtime, strftime
import paho.mqtt.client as mqtt  

#####################################################################
# Variables to adjust to the local environment                
#####################################################################
debug =0 			 #debug on = 1
domoticzon=0 		 #0=domoticz off  1=domoticz on
domoip = "192.168.1.155" #Domoticz ip address
domoport = "8080"    #Domoticz Port
lonhome = 4.8909126  #Home position longitude Dam
lathome = 52.373095  #Home Position latiude Dam
distfm = 10   		 #max dist radius in km's 
altfm = 37000  		 #max altitude in meters
refreshtimer=900    #refresh in seconds, to avoid red sensors in quiet times.
LoopTime = 4		 #Script looptime in sec
#The idx numbers of the sensors made in Domoticz
Textidx = "128"      #the text sensor idx  "current airplane flying" , set to "" if not used
Airplaneidx = "87"   #the airplane counter sensor , set to "" if not used
LifeLineridx = "98"  #the Lifeliner Heli counter sensor , set to "" if not used
Policeidx = "99"     #the Police Heli counter sensor , set to "" if not used

mqtton =1  			 # 0=mqtt off   1 =mqtt on 
mqttBroker ="192.168.1.175" #MQTT Broker ip address
mqttuser ="mqttuser"
mqttpassword ="mypassword"
topicFlightName ="AeroPlane/Name" #MQTT topic name
topicFlightCounter="flightcounter" #MQTT topic name
topicLifelinerCounter="AeroPlane/LifeLiner" #MQTT topic LifeLiner
topicPolicelinerCounter="AeroPlane/Police" #MQTT topic Police

########################################################################

#Var init, do not change
pfli = 0
plon = 0
plat = 0
pdist = 0
palt = 0
tick1=0 			 #keep alive timer
Aircraftname = ""

#Define logging paramters
import logging
logger = logging.getLogger('fly')
hdlr = logging.FileHandler('/var/tmp/fly.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr) 
logger.setLevel(logging.WARNING)

#call url and write message
def domo(urlmessage):
	if domoticzon:
		r=requests.get(urlmessage)

#distance calculator
def distance(lat1, lng1, lat2, lng2):
    #return distance as meter if you want km distance, remove "* 1000"
    radius = 6371 * 1000 
    dLat = (lat2-lat1) * math.pi / 180
    dLng = (lng2-lng1) * math.pi / 180
    lat1 = lat1 * math.pi / 180
    lat2 = lat2 * math.pi / 180
    val = math.sin(dLat/2) * math.sin(dLat/2) + math.sin(dLng/2) * math.sin(dLng/2) * math.cos(lat1) * math.cos(lat2)    
    ang = 2 * math.atan2(math.sqrt(val), math.sqrt(1-val))
    return radius * ang

#find element key from the just read line	
def elementline(line,key):
	fin=fink=lonf=''
	fin = (line.find("\""+key,0,len(line))) #find "
	if fin != -1:
		fink = (line.find(",",fin+1,len(line))) #find ,
		lonf = line[ fin + len(key)+3 : fink]  # grab final string
		lonf = lonf.replace('"', '') #remove "
		lonf = lonf.replace(' ', '') #remove space
	else :
		lonf = -1
	return lonf
		
	
#############################################
#Start main routine, this is the loop       #
#############################################

def main():
	global pdist
	global plon
	global plat
	global palt
	global pfli
	global tick1
	global tick2
	global rline
	global Aircraftname
	global filepath
	
	
	if mqtton:
		client.connect(mqttBroker) 

	if (time.time() - tick1) > refreshtimer:
		if debug:
			print (">>>Refresh URL called<<<")
			
		# call counter with dummy zero for keep alive ( Sensor red avoidance )
		if Airplaneidx !="":
			domo('http://'+domoip+':'+domoport+'/json.htm?type=command&param=udevice&idx='+Airplaneidx+'&svalue=0')
		if LifeLineridx !="":
			domo('http://'+domoip+':'+domoport+'/json.htm?type=command&param=udevice&idx='+LifeLineridx+'&svalue=0')
		if Policeidx !="":
			domo('http://'+domoip+':'+domoport+'/json.htm?type=command&param=udevice&idx='+Policeidx+'&svalue=0')
		tick1 = time.time()
	
	filepath = '/run/dump1090-fa/aircraft.json' #path to the aircraft file
	with open(filepath) as fp:
		pdist=100
		rline =1
		while rline:
			rline = fp.readline()
			#find long
			rlon= elementline(rline,"lon")
			#find Lat
			rlat = elementline(rline,"lat")
			#find altitude
			ralt= elementline(rline,"alt_baro")
			#print ("Ralt=",ralt)
			if rlat != -1:
				ralt = str(int( int(ralt) / 3.281 )) #convert Feet to meters
			#find flight
			rfli= elementline(rline,"flight")
			if rlon != -1 and rlat != -1: 
				dist= round((distance(lonhome,lathome,float(rlon),float(rlat))/1000))			
			if rfli != -1 and ralt != -1 and rlat != -1 and rlon != -1 :
				dist = int(dist)
				ralt = int(ralt)
				if dist < distfm :
					if dist < pdist and ralt <altfm :
						pfli = rfli
						plon = float(rlon)
						plat = float(rlat)
						palt = int(ralt)
						pdist = dist+1
	fp.close()
	
	if pdist > distfm :
		pfli = 0
		plon = 0
		plat = 0
		palt = 0
		pdist = 100
		strtoprint= 'http://'+domoip+':'+domoport+'/json.htm?type=command&param=udevice&idx='+Textidx+'&nvalue=0&svalue=No Airplane in < 10 Km'		
		if (time.time() - tick2) > refreshtimer:
			domo(strtoprint)
			tick2=time.time()
		if Aircraftname != "None":	
			Aircraftname = "None"
			domo(strtoprint)
			if mqtton:
				client.publish(topicFlightName, 'No Aircraft nearby found')
		if debug:
			#print("\033c", end="")
			print ( ">No aircraft loop<",strftime("%H:%M:%S", time.localtime()))
			print ( "ReFresh time count >",int(time.time() - tick1))
	else:
		if debug:
			#print("\033c", end="")
			print ("Nearby airplane now : ",strftime("%H:%M:%S", gmtime()))
			print ( "Flight = ",pfli)
			print ( "Lon = ",str(plon))
			print ( "Lat = ",str(plat))
			print ( "Alt = ",str(palt))
			print ( "Dist = ",str(pdist))
		strtoprint= 'http://'+domoip+':'+domoport+'/json.htm?type=command&param=udevice&idx='+Textidx+'&nvalue=0&svalue='+'AirplaneName='+pfli+'  Distance='+str(pdist) + '  Alt=' + str(palt)
		if mqtton:
			client.publish(topicFlightName, 'Name=' + pfli + '  Dist=' + str(pdist) + '  Alt=' + str(palt))
		if Textidx !="":
			domo(strtoprint)

		if Aircraftname != pfli:
			if debug:
				print ("New Aircraft found!")
			#increase aircraft counter +1
			if Airplaneidx !="":
				domo('http://'+domoip+':'+domoport+'/json.htm?type=command&param=udevice&idx='+Airplaneidx+'&svalue=1')
				client.publish(topicFlightCounter, '1')
			if "LIFELN" in pfli :
				#add to lifeliner counter
				client.publish(topicLifelinerCounter, '1')
				if LifeLineridx != "":
					domo('http://'+domoip+':'+domoport+'/json.htm?type=command&param=udevice&idx='+LifeLineridx+'&svalue=1')
			if "ZXP" in pfli :
				#add to Policeliner counter
				client.publish(topicPolicelinerCounter, '1')
				if Policeidx != "":
					domo('http://'+domoip+':'+domoport+'/json.htm?type=command&param=udevice&idx='+Policeidx+'&svalue=1')
			Aircraftname = pfli
	
		
	time.sleep(LoopTime)	

	
if __name__ == '__main__':
	logger.error('FlyMonitor script started :-)')
	#get start time in ticks
	tick1=time.time()
	tick2=time.time()
	if mqtton:
		client = mqtt.Client("FlightBox")
		client.username_pw_set(mqttuser, mqttpassword)
		client.connect(mqttBroker) 
	while (1):
		main()
	
