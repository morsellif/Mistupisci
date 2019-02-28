import time
start = time.time()
import sys
import serial
import logging
import json
import os

try:
    SERIAL_PORT = os.environ['SERIAL_PORT']
except KeyError:
    print("ERROR: missing SERIAL_PORT environment variable")
    sys.exit(1)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG) 

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)

def millis():
    return int(round((time.time()-start)*1000))

def valueToKey(dictionary, value):
    for key, val in dictionary.iteritems():
        if(value == val):
            return key

class AcTimers(object):
    def __init__(self, mode=None, onMinutesSet=None, onMinutesRemaining=None, offMinutesSet=None, offMinutesRemaining=None):
        self.mode = mode
        self.onMinutesSet = onMinutesSet
        self.onMinutesRemaining = onMinutesRemaining
        self.offMinutesSet = offMinutesSet
        self.offMinutesRemaining = offMinutesRemaining

class AcStatus(object):
    def __init__(self, roomTemperature=None, operating=None):
        self.roomTemperature = roomTemperature
        self.operating = operating
    def toJSON(self):
        return json.dumps(self.__dict__)

class AcSettings(object):
    def __init__(self, power=None, mode=None, temperature=None, fan=None, vane=None, wideVane=None, iSee = None):
        self.power = power
        self.mode = mode
        self.temperature = temperature
        self.fan = fan
        self.vane = vane
        self.wideVane = wideVane
        self.iSee = iSee 
    def __eq__(self, other):
        return (
            self.power == other.power and
            self.mode == other.mode and
            self.temperature == other.temperature and
            self.fan == other.fan and
            self.vane == other.vane and
            self.wideVane == other.wideVane and
            self.iSee == other.iSee
        )

    def __ne__(self, other):
        return (
            self.power != other.power or
            self.mode != other.mode or
            self.temperature != other.temperature or
            self.fan != other.fan or
            self.vane != other.vane or
            self.wideVane != other.wideVane or
            self.iSee != other.iSee
        )


    def log(self):
        logger.debug("POWER: %s, MODE: %s, TEMPERATURE: %s, FAN: %s, VANE: %s" % (self.power, self.mode, str(self.temperature), self.fan, self.vane))
    
    def toJSON(self):
        return json.dumps(self.__dict__)
       
class AirConditioner(object):
    def __init__(self, port = SERIAL_PORT):
        logger.debug('Creating AirConditioning istance...')

        self.port = port

        self.PACKET_LENGTH                          = 22
        self.PACKET_SENT_INTERVAL_MS                = 1000
        self.PACKET_INFO_INTERVAL_MS                = 2000
        self.PACKET_TYPE_DEFAULT                    = 99

        
        self.CONNECT_LENGTH                         = 8
        self.CONNECT                                = [0xfc, 0x5a, 0x01, 0x30, 0x02, 0xca, 0x01, 0xa8]

        self.HEADER_LENGTH                          = 8
        self.HEADER                                 = [0xfc, 0x41, 0x01, 0x30, 0x10, 0x01, 0x00, 0x00]

        self.INFO_HEADER_LENGTH                     = 5
        self.INFO_HEADER                            = [0xfc, 0x42, 0x01, 0x30, 0x10]

        self.INFO_MODE_LENGTH                       = 6
        self.INFO_MODE                              = [
                                                        0x02, # settings packet
                                                        0x03, # room temperature
                                                        0x04, # ?
                                                        0x05, # timers
                                                        0x06, # status
                                                        0x09 # standby mode
                                                        ]

        self.REQUEST_PACKET_SETTINGS                = 0
        self.REQUEST_PACKET_ROOM_TEMPERATURE        = 1
        self.REQUEST_PACKET_TIMERS                  = 2
        self.REQUEST_PACKET_STATUS                  = 3
        self.REQUEST_PACKET_STANDBY                 = 4

        self.RECEIVED_PACKET_FAIL                   = 0
        self.RECEIVED_PACKET_CONNECT_SUCCESS        = 1
        self.RECEIVED_PACKET_SETTINGS               = 2
        self.RECEIVED_PACKET_ROOM_TEMPERATURE       = 3
        self.RECEIVED_PACKET_UPDATE_SUCCESS         = 4
        self.RECEIVED_PACKET_STATUS                 = 5
        self.RECEIVED_PACKET_TIMER                  = 6

        self.CONTROL_PACKET_1                       = [0x01, 0x02, 0x04, 0x08, 0x10]
        """self.CONTROL_PACKET_2 = [0x01]"""

        self.POWER = {
            "off": 0x00,
            "on": 0x01
        }

        self.MODE = {
            "heat": 0x01, 
            "dry": 0x02,
            "cool": 0x03, 
            "fan": 0x07, 
            "auto": 0x08
        }

        self.TEMPERATURE = {
            31: 0x00,
            30: 0x01, 
            29: 0x02,
            28: 0x03, 
            27: 0x04, 
            26: 0x05, 
            25: 0x06, 
            24: 0x07, 
            23: 0x08, 
            22: 0x09, 
            21: 0x0a, 
            20: 0x0b,
            19: 0x0c,
            18: 0x0d,
            17: 0x0e,
            16: 0x0f
        }

        self.FAN = {
            "fan-auto": 0x00, 
            "fan-quiet": 0x01, 
            "fan-1": 0x02, 
            "fan-2": 0x03, 
            "fan-3": 0x05,
            "fan-4": 0x06
        }

        self.VANE = {
            "vane-auto": 0x00, 
            "vane-1": 0x01, 
            "vane-2": 0x02, 
            "vane-3": 0x03, 
            "vane-4": 0x04, 
            "vane-5": 0x05, 
            "vane-swing": 0x07
        }

        #self.WIDE_VANE = {
        #    "<<": 0x01, 
        #    "<": 0x02, 
        #    "|": 0x03, 
        #    ">": 0x04, 
        #    ">>": 0x05, 
        #    "<>": 0x08, 
        #    "SWING": 0x0c
        #}

        self.ROOM_TEMPERATURE = { 
            10: 0x00,
            11: 0x01, 
            12: 0x02, 
            13: 0x03, 
            14: 0x04, 
            15: 0x05, 
            16: 0x06, 
            17: 0x07, 
            18: 0x08, 
            19: 0x09, 
            20: 0x0a, 
            21: 0x0b, 
            22: 0x0c, 
            23: 0x0d, 
            24: 0x0e, 
            25: 0x0f, 
            26: 0x10, 
            27: 0x11, 
            28: 0x12, 
            29: 0x13, 
            30: 0x14, 
            31: 0x15, 
            32: 0x16, 
            33: 0x17, 
            34: 0x18, 
            35: 0x19, 
            36: 0x1a, 
            37: 0x1b, 
            38: 0x1c, 
            39: 0x1d, 
            40: 0x1e, 
            41: 0x1f
        }

        self.actualSettings = AcSettings()
        self.requestedSettings = AcSettings()
        self.actualStatus = AcStatus(0, False) 

        self.ser = None
        self.lastSent = 0 
        self.lastReceived = millis() - (self.PACKET_SENT_INTERVAL_MS * 10)
        
        self.infoMode = 0
        self.temperatureMode = False
        self.firstRun = True 
        self.autoUpdate = False
        self.externalUpdate = False
        self.connected = False

    def connect(self):
        logger.debug('Connecting to the air conditioner...')

        if self.port:
            self.connected = False 
            self.ser = serial.Serial(
                self.port, 
                baudrate=2400, 
                parity=serial.PARITY_EVEN, 
                timeout=2)

            time.sleep(2)

            logger.debug('Sending connection packet: %s' % self.CONNECT)
            self.ser.write(bytearray(self.CONNECT))
            
            packetType = self.readPacket()
            return packetType == self.RECEIVED_PACKET_CONNECT_SUCCESS

    def setAcSettings(self, settings):
        self.requestedSettings.power = settings.power
        self.requestedSettings.mode = settings.mode
        self.requestedSettings.temperature = settings.temperature
        self.requestedSettings.fan = settings.fan
        self.requestedSettings.vane = settings.vane
        self.requestedSettings.wideVane = settings.wideVane

    def update(self):
        while(not self.canSend(False)):
            time.sleep(0.01)

        logger.debug('Updating settings...')
        packet = [None]*self.PACKET_LENGTH
        self.createPacket(packet, self.requestedSettings)
        
        logger.debug('Sending new settings to the air conditioner: %s' % packet)
        self.writePacket(packet)
        
        packetType = self.readPacket()
        
        logger.debug("PACKET TYPE UPDATE: %s" % packetType)

        if(packetType == self.RECEIVED_PACKET_UPDATE_SUCCESS):
            self.lastSent = 0
            self.sync(self.REQUEST_PACKET_SETTINGS)
            return True
        else:
            return False

    def sync(self, packetType = None):
        if packetType == None:
            packetType = self.PACKET_TYPE_DEFAULT

        if (not(self.connected) or (millis() - self.lastReceived > (self.PACKET_SENT_INTERVAL_MS * 10))):
            self.connect()
        elif (self.autoUpdate and (not self.firstRun) and self.requestedSettings != self.actualSettings and packetType == self.PACKET_TYPE_DEFAULT):
            self.update()
        elif (self.canSend(True)):
            logger.debug("Syncing SETTINGS from the air conditioner")

            packet = [None] * self.PACKET_LENGTH
            self.createInfoPacket(packet, packetType)
            logger.debug("Sending INFO PACKET to the air conditioner: %s" % packet)
            self.writePacket(packet)

        self.readPacket()

    def canSend(self, isInfo):
        if isInfo == True:
            logger.debug(millis()-self.PACKET_INFO_INTERVAL_MS)
            logger.debug(self.lastSent)
            return (millis() - self.PACKET_INFO_INTERVAL_MS) > self.lastSent
        else:
            return (millis() - self.PACKET_SENT_INTERVAL_MS) > self.lastSent

    def checkSum(self, bytesToChecksum, length):
        sum = 0
        for i in range(0, length):
            sum += bytesToChecksum[i]

        return (0xfc - sum) & 0xff

    def createPacket(self, packet, settings):
        for i in range(0, 22):
            packet[i] = 0x00

        for i in range(0, self.HEADER_LENGTH):
           packet[i] = self.HEADER[i]
        
        if(settings.power != self.actualSettings.power):
            packet[8] = self.POWER[settings.power]
            packet[6] += self.CONTROL_PACKET_1[0]

        if(settings.mode != self.actualSettings.mode):
            packet[9] = self.MODE[settings.mode]
            packet[6] += self.CONTROL_PACKET_1[1]

        if (not self.temperatureMode) and settings.temperature != self.actualSettings.temperature:
            packet[10] = self.TEMPERATURE[settings.temperature]
            packet[6] += self.CONTROL_PACKET_1[2]

        else:
            if self.temperatureMode and settings.temperature != self.actualSettings.temperature:
                temperature = (settings.temperature * 2) + 128
                packet[19] = int(temperature)
                packet[6] += self.CONTROL_PACKET_1[2]

        if(settings.fan != self.actualSettings.fan):
            packet[11] = self.FAN[settings.fan]
            packet[6] += self.CONTROL_PACKET_1[3]

        if(settings.vane != self.actualSettings.vane):
            packet[12] = self.VANE[settings.vane]
            packet[6] += self.CONTROL_PACKET_1[4]

        
        #if(settings.wideVane != self.actualSettings.wideVane):
        #    packet[18]=self.WIDE_VANE[settings.wideVane]
        #    packet[6] += self.CONTROL_PACKET_2[0]
        
        checksum_tmp = self.checkSum(packet, 21)
        packet[21]=checksum_tmp

    def createInfoPacket(self, packet, packetType):
        for i in range(0, 22):
            packet[i] = 0x00

        for i in range(0, self.INFO_HEADER_LENGTH):
            packet[i] = self.INFO_HEADER[i]

        if(packetType!=self.PACKET_TYPE_DEFAULT):
            packet[5] = self.INFO_MODE[packetType]
        else:
            packet[5] = self.INFO_MODE[self.infoMode]

            if self.infoMode == (self.INFO_MODE_LENGTH-2):
                self.infoMode = 0
            else:
                self.infoMode += 1

        for i in range(0, 15):
            packet[i+6] = 0x00

        checksum_tmp = self.checkSum(packet, 21)
        packet[21] = checksum_tmp
        logger.debug("INFO PACKET: %s" % packet)

    def writePacket(self, packet):
        self.ser.write(bytearray(packet))
        time.sleep(1)

        self.lastSent = millis()

    def readPacket(self):
        incomingPacket = None
        dataSum = 0
        
        response = self.ser.read(22)
        #controllare se il contenuto valido

        for b in response:
            value = ord(b)
            if value == self.HEADER[0]:
                incomingPacket = []
            incomingPacket.append(value)

        if incomingPacket == None:
            return self.RECEIVED_PACKET_FAIL
        
        logger.debug("Reading packet from air conditioner: %s" % incomingPacket)

        if (incomingPacket[0] == self.HEADER[0] and 
            incomingPacket[2] == self.HEADER[2] and 
            incomingPacket[3] == self.HEADER[3]):
            dataLength = incomingPacket[4]

            # data from 5 to 20
            # 21 checksum

            for i in range(0, self.INFO_HEADER_LENGTH + dataLength):
                dataSum += incomingPacket[i]

            checksum = (0xfc - dataSum) & 0xff

            if incomingPacket[self.INFO_HEADER_LENGTH + dataLength] == checksum:
                logger.debug("The received packet is valid.")
                self.lastReceived = millis()
                if incomingPacket[1] == 0x62:
                    if incomingPacket[5] == 0x02:
                        logger.debug("The type of the received packet is: SETTINGS")
                        receivedSettings = AcSettings()
                        receivedSettings.power = valueToKey(self.POWER, incomingPacket[8])

                        if incomingPacket[9] > 0x08:
                            receivedSettings.iSee = True
                        else: 
                            receivedSettings.iSee = False

                        if receivedSettings.iSee:
                            receivedSettings.mode = valueToKey(self.MODE, incomingPacket[9] - 0x08)
                        else:
                            receivedSettings.mode = valueToKey(self.MODE, incomingPacket[9])

                        if incomingPacket[16] != 0x00:
                            temperature = incomingPacket[16]
                            temperature -= 128
                            receivedSettings.temperature = float(temperature/2)
                            self.temperatureMode = True
                        else:
                            receivedSettings.temperature = valueToKey(self.TEMPERATURE, incomingPacket[10])

                        receivedSettings.fan = valueToKey(self.FAN, incomingPacket[11])
                        receivedSettings.vane = valueToKey(self.VANE, incomingPacket[12])

                        logger.debug("received settings: ")
                        receivedSettings.log()
                        
                        logger.debug("actual settings: ")
                        self.actualSettings.log()

                        logger.debug("requested settings: ")
                        self.requestedSettings.log()

                        if(receivedSettings != self.actualSettings):
                            logger.debug("receivedSettings != actualSettings")
                            self.actualSettings = receivedSettings
                        
                       
                        logger.debug("received settings: ")
                        receivedSettings.log()

                        logger.debug("actual settings: ")
                        self.actualSettings.log()

                        logger.debug("requested settings: ")
                        self.requestedSettings.log()

                        if self.firstRun or (self.autoUpdate and self.externalUpdate):
                            logger.debug("firstRun")
                            self.requestedSettings = self.actualSettings
                            self.firstRun = False

                        return self.RECEIVED_PACKET_SETTINGS

                    if incomingPacket[5] == 0x03:
                        logger.debug("The type of the received packet is: ROOM TEMPERATURE")
                        receivedStatus = AcStatus()

                        receivedRoomTemperature = None
                        if incomingPacket[11] != 0x00:
                            temperature = incomingPacket[11]
                            temperature -= 128
                            receivedStatus.roomTemperature = float(temperature/2)
                        else:
                            receivedStatus.roomTemperature = valueToKey(self.ROOM_TEMPERATURE, incomingPacket[8])

                        if(self.actualStatus.roomTemperature != receivedStatus.roomTemperature):
                            self.actualStatus.roomTemperature = receivedStatus.roomTemperature

                        return self.RECEIVED_PACKET_ROOM_TEMPERATURE

                    if incomingPacket[5] == 0x04: #unknown
                        return
                    if incomingPacket[5] == 0x05: #timer packet
                        return 
                    if incomingPacket[5] == 0x06: #status
                        logger.debug("The type of the received packet is: STATUS")
                        receivedStatus = AcStatus()
                        receivedStatus.operating =bool(incomingPacket[9])

                        if (self.actualStatus.operating != receivedStatus.operating):
                            self.actualStatus.operating = receivedStatus.operating
                        return self.RECEIVED_PACKET_STATUS

                    if incomingPacket[5] == 0x09: #standby (not working)
                        return

                if incomingPacket[1] == 0x61:
                    return self.RECEIVED_PACKET_UPDATE_SUCCESS
                elif incomingPacket[1] == 0x7a:
                    self.connected = True
                    return self.RECEIVED_PACKET_CONNECT_SUCCESS

        return self.RECEIVED_PACKET_FAIL

    def setRemoteTemperature(self, temeprature):
        packet = [None] * self.PACKET_LENGTH

        for i in range(0, self.PACKET_LENGTH):
            packet[i] = 0x00

        for i in range(0, self.HEADER_LENGTH):
            packet[i] = self.HEADER[i]

        packet[5] = 0x07
        if temperature > 0:
            packet[6] = 0x01
            temperature = temperature * 2
            temperature = round(temperature)
            temperature = temperature / 2
            temperature_to_send = (temperature * 2) + 128
            packet[8] = int(temperature_to_send)
        else:
            packet[6] = 0x00
            packet[8] = 0x80

        checksum_tmp = self.checkSum(packet, 21)
        packet[21] = checksum_tmp
        self.writePacket(packet)

if __name__ == '__main__':
    ac = AirConditioner(port='/dev/ttyAMA0')
    ac.connect()

    print('First settings...')
    acSettings = AcSettings(
        sys.argv[1],#POWER 
        sys.argv[2],#MODE
        int(sys.argv[3]),#TEMPERATURE
        sys.argv[4],#FAN
        sys.argv[5],#VANE
    )

    ac.setAcSettings(acSettings)
    success = ac.update()
    if success:
        logger.debug("Successfully updated SETTINGS from the air conditioner")
    else:
        logger.debug("NOT successfully updated SETTINGS from the air conditioner")

    while(True):
        ac.sync()
        print(ac.actualStatus.toJSON())
        time.sleep(8)
