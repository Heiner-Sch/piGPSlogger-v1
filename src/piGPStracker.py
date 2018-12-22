#!/usr/bin/python3

import subprocess
import shutil
import time
import gpsd
import RPi.GPIO as GPIO
import threading

# Function: LED on/off
def LED_on_off(LED, switch_state):
    if switch_state == 1:
        print('LED ',LED,' on')
        GPIO.output(LED, GPIO.HIGH)
    elif switch_state == 0:
        print('LED ',LED,' off')
        GPIO.output(LED, GPIO.LOW)
    else:
        print('wrong fuction call!!!')


def LED_blink(LED):
    t = threading.currentThread()
    while True:
        while getattr(t, "do_run", True):
            GPIO.output(LED, GPIO.HIGH)
            time.sleep(.5)
            GPIO.output(LED, GPIO.LOW)
            time.sleep(1)
        # Stopping if do_run is False
        GPIO.output(LED, GPIO.LOW)


# Funktion to check GPS link
def check_GPSfix():
    packet = gpsd.get_current()
    if packet.mode > 1:
        return True
    return False
    

# Function to shutdown
def raspi_shutdown():
    print('function raspi_shutdown')
    LED_on_off(pyscriptLED,0)
    LED_on_off(errorLED,0)
    LED_on_off(gpxloggerLED,0)
    print('sudo shutdown -h now ...\n')
    GPIO.cleanup()
    time.sleep(.5)
    subprocess.run(['sudo', 'shutdown', '-h', 'now'])


# Function: gpxlogger_running
def gpxlogger_running():
    self = 0
    self = subprocess.run(['pgrep', 'gpxlogger'], stdout=subprocess.PIPE)
    if self.returncode == 0:
        output = True
    else:
        output = False
    return output


# Function killall_gpxlogger
def killall_gpxlogger():
    print('function killall_gpxlogger')
    subprocess.run(['killall', 'gpxlogger'])
    time.sleep(1)


# Function debounce switch falling
def debounce_sw_falling(GPIOport):
    sw_off = 0
    i = 0
    while i < 20:
        sw_off += int(GPIO.input(GPIOport))
        i += 1
        time.sleep(.03)
    if sw_off <= 4 and GPIO.input(GPIOport) == 0:
        output = True
    else:
        output = False
    return output


# Function debounce switch raising
def debounce_sw_raising(GPIOport):
    sw_on = 0
    i = 0
    while i < 20:
        sw_on += int(GPIO.input(GPIOport))
        i += 1
        time.sleep(.03)
    if sw_on > 7 and GPIO.input(GPIOport) == 1:
        output = True
    else:
        output = False
    return output


# Function to control gpxlogger
def ctrl_gpxlogger(GPIOport):
    if GPIO.input(GPIOport):     # gpxlogger switch on
        if debounce_sw_raising(GPIOport) and GPIO.input(GPIOport) == 1  and not gpxlogger_running():
            print ("-> gpxlogger start ...")
            subprocess.run(['gpxlogger', '-d', '-f', 'Track-current.gpx'])
            LED_on_off(gpxloggerLED,1)
            time.sleep(.5)

    else:                        # gpxlogger switch off
        if debounce_sw_falling(GPIOport) and GPIO.input(GPIOport) == 0:
            print ("gpxlogger stop ...")
            killall_gpxlogger()
            LED_on_off(gpxloggerLED,0)
            shutil.copy2('Track-current.gpx', 'Track-'+time.strftime("%Y-%m-%d_%H%M%S")+'.gpx')
            time.sleep(1)


# Function to control the shutdown button
def ctrl_shutdown_button(GPIOport):
    print("Function to control shutdown botton")
    output = False
    time.sleep(.5)
    if GPIO.input(GPIOport) and not gpxlogger_running():
        print('Die Schleife startet...')
        i = 1
        while GPIO.input(GPIOport):
            if i >= 14:
                print('Zeit zum shutdown')
                raspi_shutdown()
                break
            elif i >= 5:
                print('Zeit reicht zum ProgrammStop')
                output = True
            i += 1
            print('i=', i)
            time.sleep(.5)
        if not output:
            print('press min. 2 seconds to stop or 5 seconds for shutdown!')
        elif output:
            print ('i= ', i, ' - Program stop')
    elif GPIO.input(GPIOport) and gpxlogger_running():
        print('stop gpxlogger first!')
        output = False
    return output


# Init Raspi

print('GPIO init start')
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(24, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # switch to control gpxlogger
GPIO.setup(25, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # button to shutdown raspi

GPIO.setup(12, GPIO.OUT) # Error LED
errorLED = 12
GPIO.setup(16, GPIO.OUT) # py-script LED
pyscriptLED = 16
GPIO.setup(7, GPIO.OUT) # gpxlogger LED
gpxloggerLED = 7

GPIO.output(12, GPIO.LOW) # Error LED off
GPIO.output(16, GPIO.LOW) # py-script LED off
GPIO.output(7, GPIO.LOW) # gpxlogger LED off
print('GPIO setup done.\n')

# Connect to the local gpsd
gpsd.connect()

# check GPS status
#
# wait until GPS fix is done:
print('wait for GPS fix ...')
t = threading.Thread(target=LED_blink, args=(errorLED,))
if check_GPSfix() == False:
    t.start()
while check_GPSfix() == False:
    time.sleep(2)
print('GPS fix!')
t.do_run = False

# Make sure gpxlogger is not running
print('make sure gpxlogger is not running...')
if gpxlogger_running():
    print('killall gpxlogger')
    LED_on_off(gpxloggerLED,1)
    killall_gpxlogger()
    time.sleep(1)
    if not gpxlogger_running():
        print('gpxlogger stopped!\n')
        LED_on_off(gpxloggerLED,0)
    else:
        print('gpxlogger running with unknown reason ...\n')
        LED_on_off(errorLED,1)
        LED_on_off(gpxloggerLED,1)


# Check sw_logger is off
if GPIO.input(24):
    print('gpxlogger switch on, switch it off and start again ...\n')
    LED_on_off(errorLED,1)


# End init

print("PythonScript started ... \n")
# pythonScript-LED on
LED_on_off(pyscriptLED,1)


GPIO.add_event_detect(24, GPIO.BOTH, bouncetime=100)
GPIO.add_event_detect(25, GPIO.RISING, bouncetime=500)

print("Press shutdown button 5 seconds for shutdown, 2 seconds to stop program ...")
print('or start gpxlogger ... \n')

while 1:
    try:
        # this event controls the gpxlogger
        if GPIO.event_detected(24):
            ctrl_gpxlogger(24)

        if GPIO.event_detected(25): # button to shutdown
            if ctrl_shutdown_button(25):
                GPIO.remove_event_detect(24)
                GPIO.remove_event_detect(25)
                GPIO.cleanup()
                break

        if check_GPSfix() == False:
            # ErrorLED blink
            t.do_run = True
        else:
            # ErrorLED dark
            t.do_run = False

    except KeyboardInterrupt:
        print("--KeyboardInterupt--")
        GPIO.cleanup()
        break

