#!/usr/bin/env python

import os
import paho.mqtt.client as mqtt
from mistupisci import *
import time
import sys

SEND_ROOM_TEMPERATURE_INTERVAL_MS = 60000;

try:
    MQTT_HOST = os.environ['MQTT_HOST']
except KeyError:
    print("ERROR: missing MQTT_HOST environment variable")
    sys.exit(1)

try:
    MQTT_PORT = os.environ['MQTT_PORT']
except KeyError:
    print("ERROR: missing MQTT_PORT environment variable")
    sys.exit(1)

try:
    AC_SETTINGS_TOPIC = os.environ['AC_SETTINGS_TOPIC']
except KeyError:
    print("ERROR: missing AC_SETTINGS_TOPIC environment variable")
    sys.exit(1)

try: 
    AC_STATUS_TOPIC = os.environ['AC_STATUS_TOPIC']
except KeyError:
    print("ERROR: missing AC_STATUS_TOPIC environment variable")
    sys.exit(1)

def on_connect(client, userdata, flags, rc):
    print('Connected successfully!')
    client.subscribe(AC_SETTINGS_TOPIC)
    client.subscribe(AC_STATUS_TOPIC)

def on_message(client, userdata, msg):
    if msg.topic == AC_SETTINGS_TOPIC:
        settings = json.loads(msg.payload)
        acSettings = AcSettings(
            settings["power"], 
            settings["mode"],
            int(settings["temperature"]),
            settings["fan"],
            settings["vane"],
        )
        logger.info(settings["power"])
        ac.setAcSettings(acSettings)
        
if __name__ == '__main__':
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    print('Trying to connect...')
    client.connect(MQTT_HOST, int(MQTT_PORT), 60)
    
    ac = AirConditioner()
    ac.connect()
    ac.autoUpdate = True
    
    lastTemperatureSent = millis()

    while(True):
        try:
            ac.sync()
            # client.publish("morsellif/air_conditioner/settings", ac.actualSettings.toJSON())

            if millis() > (lastTemperatureSent + SEND_ROOM_TEMPERATURE_INTERVAL_MS):
                client.publish(AC_STATUS_TOPIC, ac.actualStatus.toJSON())
                lastTemperatureSent = millis()
            client.loop_start()

        except KeyboardInterrupt:
            break
