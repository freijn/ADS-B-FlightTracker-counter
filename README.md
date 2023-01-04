# ADS-B-FlightTracker-counter
ADS-B  flight tracker counter for Home Assistant or Domoticz  Python

If you do have your own ADS-B receiver with a dongle and Raspberry Pi than this is your next step 
if you also run HomeAssistant or Domoticz.

The FlightRadar24 or FlightAware packages use dump1090 to decode the ADS-B traffic.

This Python script runs in the background and examines the dump1090 file every x seconds.
If an airplane flies into the defined circle ( 10 Km by default )  around your place it reports the airplane.
This is then sent to eighter sent via MQTT to Home Assistant of via HTTP json to Domoticz.
All free configurable in the first part of the file.


As both processes read the file, sometimes the python does crash. Have not yet been able to catch this error. 
For this I have a job running every 1 min to check and restart if required.


- create file /home/pi/flycheck.sh  with the content :
```
#! /bin/bash

case "$(pidof python home/pi/fly.py | wc -w)" in

0)  python /home/pi/fly.py &
    ;;
1)  # all ok
    ;;
*)  kill $(pidof python /home/pi/fly.py | awk '{print $1}')
    ;;
esac
```

- add this line into the crontab   ( edit via crontab -e)
```
*/1 * * * * /home/pi/flycheck.sh >> /home/pi/my.log 2>&1
```

