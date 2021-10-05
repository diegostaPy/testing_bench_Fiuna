#!/usr/bin/python
# -*- coding: utf-8 -*-
"""PiPyADC: Example file for class ADS1256 in module pipyadc:
"""
import sys
import numpy as np
import datetime as dt
from pipyadc.ADS1256_definitions import *
from pipyadc import ADS1256
# In this example, we pretend myconfig_2 was a different configuration file
# named "myconfig_2.py" for a second ADS1256 chip connected to the SPI bus.
import pipyadc.ADS1256_default_config as myconfig_2
from smbus2 import SMBus
I2C_ADDRESS=0x01
READ_TEMPERATURE_CMD=0xB2
READ_HUMIDITY_CMD=0xB3
def readData():
    bus = SMBus(1)
    read = bus.read_byte_data(I2C_ADDRESS,READ_TEMPERATURE_CMD)
    temp=read<<8
    read = bus.read_byte_data(I2C_ADDRESS,READ_TEMPERATURE_CMD)
    temp=temp+read
    read = bus.read_byte_data(I2C_ADDRESS,READ_HUMIDITY_CMD)
    hum=read<<8
    read = bus.read_byte_data(I2C_ADDRESS,READ_HUMIDITY_CMD)
    hum=hum+read
    return temp/100, hum/100    
#import configv2 as myconfig_22
### START EXAMPLE ###
################################################################################
###  STEP 0: CONFIGURE CHANNELS AND USE DEFAULT OPTIONS FROM CONFIG FILE: ###
#
# For channel code values (bitmask) definitions, see ADS1256_definitions.py.
# The values representing the negative and positive input pins connected to
# the ADS1256 hardware multiplexer must be bitwise OR-ed to form eight-bit
# values, which will later be sent to the ADS1256 MUX register. The register
# can be explicitly read and set via ADS1256.mux property, but here we define
# a list of differential channels to be input to the ADS1256.read_sequence()
# method which reads all of them one after another.
#
# ==> Each channel in this context represents a differential pair of physical
# input pins of the ADS1256 input multiplexer.
#
# ==> For single-ended measurements, simply select AINCOM as the negative input.
#
# AINCOM does not have to be connected to AGND (0V), but it is if the jumper
# on the Waveshare board is set.
#
# Input pin for the potentiometer on the Waveshare Precision ADC board:
fio2= POS_AIN0|NEG_AINCOM
# Light dependant resistor of the same board:
pressure= POS_AIN1|NEG_AINCOM

flow= POS_AIN2|NEG_AINCOM
# Specify here an arbitrary length list (tuple) of arbitrary input channel pair
# eight-bit code values to scan sequentially from index 0 to last.
# Eight channels fit on the screen nicely for this example..
CH_SEQUENCE = (fio2,pressure,flow)
################################################################################

##########################  CALIBRATION  CONSTANTS  ############################
# This shows how to use individual channel calibration values.
#
# The ADS1256 has internal gain and offset calibration registers, but these are
# applied to all channels without making any difference.
# I we want to use individual calibration values, e.g. to compensate external
# circuitry parasitics, we can do this very easily in software.
# The following values are only for demonstration and have no meaning.
CH_OFFSET = np.array((0,   0, 0), dtype=np.int64)
GAIN_CAL  = np.array((1.0, 1.0,1.0), dtype=np.float64)
################################################################################

# Using the Numpy library, digital signal processing is easy as (Raspberry) Pi..
# However, this constant only specifies the length of a moving average.
FILTER_SIZE = 1
################################################################################


def do_measurement():
    ### STEP 1: Initialise ADC objects for two chips connected to the SPI bus.
    # In this example, we pretend myconfig_2 was a different configuration file
    # named "myconfig_2.py" for a second ADS1256 chip connected to the SPI bus.
    # This file must be imported, see top of the this file.
    # Omitting the first chip here, as this is only an example.

    #ads1 = ADS1256(myconfig_1)
    # (Note1: See ADS1256_default_config.py, see ADS1256 datasheet)
    # (Note2: Input buffer on means limited voltage range 0V...3V for 5V supply)
    ads2 = ADS1256(myconfig_2)
    
    # Just as an example: Change the default sample rate of the ADS1256:
    # This shows how to acces ADS1256 registers via instance property
    ads2.drate = DRATE_1000  

    ### STEP 2: Gain and offset self-calibration:
    ads2.cal_self()

    ### Get ADC chip ID and check if chip is connected correctly.
    chip_ID = ads2.chip_ID
    print("\nADC No. 2 reported a numeric ID value of: {}.".format(chip_ID))
    # When the value is not correct, user code should exit here.
    if chip_ID != 3:
        print("\nRead incorrect chip ID for ADS1256. Is the hardware connected?")
    # Passing that step because this is an example:
    #    sys.exit(1)

    # Channel gain must be multiplied by LSB weight in volts per digit to
    # display each channels input voltage. The result is a np.array again here:
    CH_GAIN = ads2.v_per_digit * GAIN_CAL

    # Numpy 2D array as buffer for raw input samples. Each row is one complete
    # sequence of samples for eight input channel pin pairs. Each column stores
    # the number of FILTER_SIZE samples for each channel.
    temp, hum=readData()
   
    
    header =[]            
    header.extend(["Timestamp","pressure","flow","fi02"])   # Define a CSV header 
    filename = sys.argv[1]
    with open(filename,"w") as file:
       file.write("#"+str(temp)+",°C, "+str(hum)+",%hum\n")                             # With the opened file...
       file.write(",".join(str(value) for value in header)+ "\n")   # Write each value from the header 
    k=0
    with open(filename,"a") as file:           # Open the file into Append mode (enter data without erase previous data)

        while True:
            read=ads2.read_sequence(CH_SEQUENCE)*  CH_GAIN
            _pressure = 105.0/4.0*(read[1]-0.5) - 5.0
            _flow =(-1)*(read[2]-2.5)*125.0
            _fio2 =(39)*(read[0]-3.0) + 100.0
            file.write(str(dt.datetime.now().timestamp()) + "," + str(_pressure) + "," + str(_flow) + ", " + str(_fio2) +"\n")
            k=k+1

### END EXAMPLE ###



# Start data acquisition
try:
    print("\033[2J\033[H") # Clear screen
    print(__doc__)
    print("\nPress CTRL-C to exit.")
    do_measurement()

except (KeyboardInterrupt):
    print("\n"*8 + "User exit.\n")
 
