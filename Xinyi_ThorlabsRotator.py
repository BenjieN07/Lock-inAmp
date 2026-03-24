#
"""
Created on Feb 22 2019

By Xinyi Xu

"""

import os
import time
import ctypes
from ctypes import *



class MotorizedStage(object):
    def __init__(self):
        # Load dll lib, 64-bit python 3.6.8 with 64-bit Kinesis
        os.chdir(r"C:\Program Files (x86)\Thorlabs\Kinesis")
        self.lib = ctypes.CDLL("Thorlabs.MotionControl.IntegratedStepperMotors.dll")
        # set up serial number variable
        self.serialNumber = c_char_p(b"55243224")  # S/N number on the mount
        self.deviceUnit = c_int()
        self.ins_pos = float()  # Variable to chase the current pos
        self.moveTimeout = 60.0
        self.moved = True  # Global flag to identify whether stage is moved
        self.homed = False  # Global flag to identify whether stage is homed
        # Device state data
        self.messageType = c_ushort()
        self.messageID = c_ushort()
        self.messageData = c_ulong()


    # connect the devices + homing
    def initialize(self):
        # Build device list
        self.lib.TLI_BuildDeviceList()

        # constants for the K10CR1
        stepsPerRev = 200
        gearBoxRatio = 120
        pitch = 360.0

        # set up device
        self.lib.ISC_Open(self.serialNumber)
        self.lib.ISC_StartPolling(self.serialNumber, c_int(200))

        #time.sleep(3)

        self.lib.ISC_EnableChannel(self.serialNumber)
        self.lib.ISC_ClearMessageQueue(self.serialNumber)

        # home device
        #print('Homing Device')
        #homeStartTime = time.time()
        #self.lib.ISC_Home(self.serialNumber)  # Set the device to a known state and determine the home position (0 deg)

        #while (self.homed == False):
        #    self.lib.ISC_GetNextMessage(self.serialNumber, byref(self.messageType), byref(self.messageID), byref(self.messageData))
        #    if ((self.messageID.value == 0 and self.messageType.value == 2) or (
        #            time.time() - homeStartTime) > self.moveTimeout): self.homed = True
        #self.ins_pos = 0.0                                #Chasing the current pos
        #self.lib.ISC_ClearMessageQueue(self.serialNumber)

        # Set up to convert physical units to units on the device
        self.lib.ISC_SetMotorParamsExt(self.serialNumber, c_double(stepsPerRev), c_double(gearBoxRatio), c_double(pitch))
        self.lib.ISC_LoadSettings(self.serialNumber)



    # homing the devices
    def homing(self):
        # home device
        print('Homing Device')
        homeStartTime = time.time()
        self.lib.ISC_Home(self.serialNumber)  # Set the device to a known state and determine the home position (0 deg)

        self.homed = False
        while (self.homed == False):
            self.lib.ISC_GetNextMessage(self.serialNumber, byref(self.messageType), byref(self.messageID), byref(self.messageData))
            if ((self.messageID.value == 0 and self.messageType.value == 2) or (
                    time.time() - homeStartTime) > self.moveTimeout): self.homed = True
        print('Homed')
        self.lib.ISC_ClearMessageQueue(self.serialNumber)
        self.ins_pos = 0.0
        #print(self.ins_pos)


    #go to a specific position
    def go_to_pos(self, target_deg):

        time0 = time.time()

        realUnit = c_double(target_deg)
        self.lib.ISC_GetDeviceUnitFromRealValue(self.serialNumber, realUnit, byref(self.deviceUnit), 0)
        print(self.deviceUnit)

        # send move command
        print('Moving Device to Position: %.2f'%target_deg)
        moveStartTime = time.time()
        self.lib.ISC_GetPosition(self.serialNumber)
        self.lib.ISC_MoveToPosition(self.serialNumber, self.deviceUnit)
        # lib.ISC_MoveJog(serialNumber, c_short(1))

        # Self check: whether the moving command is finished
        self.moved = False

        while (self.moved == False):
            self.lib.ISC_GetNextMessage(self.serialNumber, byref(self.messageType), byref(self.messageID), byref(self.messageData))
            if ((self.messageID.value == 1 and self.messageType.value == 2) or (
                    time.time() - moveStartTime) > self.moveTimeout): self.moved = True

        self.ins_pos = self.lib.ISC_GetPosition(self.serialNumber) / 136533  # there are 136533 pos in 1 deg; return the current pos in unit of deg
        #print(self.ins_pos)

        time_elapse = time.time() - time0
        print ('Collection Moving Time: %d s'%time_elapse)


    def move_clockwise(self, step):
        realUnit = c_double(self.ins_pos+step)
        self.lib.ISC_GetDeviceUnitFromRealValue(self.serialNumber, realUnit, byref(self.deviceUnit), 0)

        # send move command
        print('Clockwise Moving Device')
        moveStartTime = time.time()
        self.lib.ISC_MoveToPosition(self.serialNumber, self.deviceUnit)
        # lib.ISC_MoveJog(serialNumber, c_short(1))

        # Self check: whether the moving command is finished
        self.moved = False

        while (self.moved == False):
            self.lib.ISC_GetNextMessage(self.serialNumber, byref(self.messageType), byref(self.messageID), byref(self.messageData))

            if ((self.messageID.value == 1 and self.messageType.value == 2) or (
                    time.time() - moveStartTime) > self.moveTimeout): self.moved = True

        self.ins_pos = self.lib.ISC_GetPosition(self.serialNumber) / 136533  # there are 136533 pos in 1 deg; return the current pos in unit of deg

        #print(self.ins_pos)

    def move_counterclockwise(self, step):
        realUnit = c_double(self.ins_pos - step)
        self.lib.ISC_GetDeviceUnitFromRealValue(self.serialNumber, realUnit, byref(self.deviceUnit), 0)

        # send move command
        print('Counterclockwise Moving Device')
        moveStartTime = time.time()
        self.lib.ISC_MoveToPosition(self.serialNumber, self.deviceUnit)
        # lib.ISC_MoveJog(serialNumber, c_short(1))

        # Self check: whether the moving command is finished
        self.moved = False

        while (self.moved == False):
            self.lib.ISC_GetNextMessage(self.serialNumber, byref(self.messageType), byref(self.messageID), byref(self.messageData))

            if ((self.messageID.value == 1 and self.messageType.value == 2) or (
                    time.time() - moveStartTime) > self.moveTimeout): self.moved = True

        self.ins_pos = self.lib.ISC_GetPosition(self.serialNumber) / 136533  # there are 136533 pos in 1 deg; return the current pos in unit of deg

        #print(self.ins_pos)



    # disconnect_exit
    def close(self):
        # clean up and exit
        self.lib.ISC_ClearMessageQueue(self.serialNumber)
        # print lib.ISC_GetPosition()

        self.lib.ISC_DisableChannel(self.serialNumber)
        self.lib.ISC_StopPolling(self.serialNumber)

        self.lib.ISC_Close(self.serialNumber)


    def current_pos(self):
        return self.ins_pos



    def StopImmediate(self):
        self.lib.ISC_StopImmediate(self.serialNumber)





# #test code
h = MotorizedStage()
h.initialize()
print('Succesfullyh initialized')
h.go_to_pos(90)
# time.sleep(0.5)
# h.homing()
# print ('Succesfully Homed')
# time.sleep(0.5)
# h.go_to_pos(370)
# time.sleep(0.5)
# h.homing()
# time.sleep(0.5)
# h.move_clockwise(25)
# time.sleep(0.5)
# h.move_counterclockwise(15)
# time.sleep(0.5)
# h.close()
# print ('Succesfullyh Closed')
