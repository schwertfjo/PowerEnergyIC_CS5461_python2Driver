#!/usr/bin/env python
# -*- coding: utf-8 -*-

import RPi.GPIO as GPIO
import spidev
import time

class cs5461:

    # define command bytes
    sync0 = 254
    sync1 = 255
    reset = 128
    compu = 232

    # default settings
    default_mode = 2
    default_speed = 100000
    default_inverted = True # due to optocouplers

    def __init__(self, mode = default_mode, speed = default_speed, inverted = default_inverted):
        self.spi = spidev.SpiDev()
        self.spi_mode = mode
        self.spi_speed = speed
        self.inverted = inverted
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(25, GPIO.OUT)
        self.Init()

    def rw(self, bytes):
        send_bytes = []
        ret = -1
        if type(bytes) is int:
            send_bytes = [bytes] + [self.sync0] * 3
        elif type(bytes) is list:
            send_bytes = bytes + [self.sync0] * (4 - len(bytes))
        self.spi.open(0,0)
        self.spi.mode = self.spi_mode
        self.spi.max_speed_hz = self.spi_speed
        if self.inverted:
            r = self.spi.xfer2( map(lambda x: x ^ 0xFF, send_bytes) )
            ret = map(lambda x: x ^ 0xFF, r)
        else:
            ret = self.spi.xfer2( send_bytes )
        self.spi.close()
        return ret

    def close(self):
        self.spi.close()

    def Reset(self):
        self.rw(self.reset)

    def Sync(self):
    	self.rw([self.sync1]*3 + [self.sync0])

    def Init(self):
        # chip reset cycle via gpio25
        GPIO.output(25, True)
        time.sleep(1)
        GPIO.output(25, False)
        time.sleep(1)
        self.Sync()
        self.Reset()
        self.Sync()
        wrReg00 = 0x40 # Config
        wrReg01 = 0x42 # Current Offset
        wrReg02 = 0x44 # Current Gain
        wrReg03 = 0x46 # Voltage Offset
        wrReg04 = 0x48 # Voltage Gain
        wrReg13 = 0x5A # Timebase Calibration
        wrReg14 = 0x5C # Power Offset Calibration
        wrReg16 = 0x60 # Current Channel AC Offset
        wrReg17 = 0x62 # Voltage Channel AC Offset
        # good working calibration data for energenie power meter lan (determined by trial)
        self.rw([wrReg00, 0b1, 0b0, 0b1])
        self.rw([wrReg01, 0xFF, 0xB5, 0x62])
        self.rw([wrReg02, 0x54, 0xFE, 0xFF])
        self.rw([wrReg03, 0x15, 0x8C, 0x71])
        self.rw([wrReg04, 0x3D, 0xE0, 0xEF])
        self.rw([wrReg13, 0x83, 0x12, 0x6E])
        self.rw([wrReg14, 0xFF, 0xCF, 0xC3])
        self.rw([wrReg16, 0x00, 0x01, 0x4A])
        self.rw([wrReg17, 0x00, 0x44, 0xCA])
        # Perform continuous computation cycles
    	self.rw(self.compu)
    	time.sleep(2) # wait until values becomes good

    def readregister(self, register):
        if register > 31 or register < 0: #just check range
    	    return -1
        self.Sync()
    	received = self.rw(register << 1)
    	return received[1]*256*256 + received[2]*256 + received[3]

    def getregister(self, register):
        Expotential=    [  0, -23, -22, -23, -22, -0, -5, -23, -23, -23, # 0:9 decimal point position
                        -23, -24, -24, -23, -23, 0, -24, -24, -5, -16,   # 10:19
                        0, 0, -22, -23, 0, 0, 0, 0, 0, 0, 0, 0 ]	 # 20:31
        Binary =        [0, 15, 26, 28]				         # binary registers
        twosComplement =[1, 7, 8, 9, 10, 14, 19, 23]		         # two's complement registers

        if register > 31 or register < 0: # just check range
    	    return -1
        value = self.readregister(register)
        if register in Binary:
            return  bin(value)
        elif register in twosComplement:
            if value > 2**23:
                value = ((value ^ 0xFFFFFF) + 1) * -1 # convert to host two's complement system
        return value * 2**Expotential[register]

def main():
    Ugain = 400
    Igain = 10
    Egain = 4000
    device  = cs5461()
#    for i in range(32):
#	print i, device.getregister(i)
    while True:
        Irms = device.getregister(11)
        Urms = device.getregister(12)
        Erms = device.getregister(10)
        I = round(Irms*Igain, 3)
        U = round(Urms*Ugain, 1)
        E = round(Erms*Egain, 1)
        print( "voltage = %.1fV   current = %.3fA   power = %.1fW" % (U, I, E) )
        time.sleep(1)

if __name__ == '__main__':
    main()
