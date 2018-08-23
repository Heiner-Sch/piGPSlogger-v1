#!/usr/bin/python3

import subprocess
import shutil
import time
import RPi.GPIO as GPIO


# Function: error LED on/off
def error_LED(switch_state):
    if str(switch_state) == 'on':
        print('Error-LED on...\n')
        GPIO.output(12, GPIO.HIGH)
    elif str(switch_state) == 'off':
        print('GPXlogger-LED off\n')
        GPIO.output(12, GPIO.LOW)
    else:
        print('wrong function call!')


# Function: gpxlogger LED on/off
def gpxlogger_LED(switch_state):
    if str(switch_state) == 'on':
        print('GPXlogger-LED on\n')
        GPIO.output(7, GPIO.HIGH)
    elif str(switch_state) == 'off':
        print('GPXlogger-LED off\n')
        GPIO.output(7, GPIO.LOW)
    else:
        print('wrong function call!')


# Function: python script LED on/off
def python_LED(switch_state):
    if str(switch_state) == 'on':
        print('python-LED on\n')
        GPIO.output(16, GPIO.HIGH)
    elif str(switch_state) == 'off':
        print('python-LED off\n')
        GPIO.output(16, GPIO.LOW)
    else:
        print('wrong function call!')


# Function to shutdown
def raspi_shutdown():
    print('function raspi_shutdown')
    python_LED('off')
    error_LED('off')
    gpxlogger_LED('off')
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
            gpxlogger_LED('on')
            time.sleep(.5)

    else:                        # gpxlogger switch off
        if debounce_sw_falling(GPIOport) and GPIO.input(GPIOport) == 0:
            print ("gpxlogger stop ...")
            killall_gpxlogger()
            gpxlogger_LED('off')
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
GPIO.setup(24, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # switch to control gpxlogger
GPIO.setup(25, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # button to shutdown raspi

GPIO.setup(12, GPIO.OUT) # Error LED
GPIO.setup(16, GPIO.OUT) # py-script LED
GPIO.setup(7, GPIO.OUT) # gpxlogger LED

GPIO.output(12, GPIO.LOW) # Error LED off
GPIO.output(16, GPIO.LOW) # py-script LED off
GPIO.output(7, GPIO.LOW) # gpxlogger LED off
print('GPIO setup done.\n')

# Make sure gpxlogger is not running
print('make sure gpxlogger is not running...')
if gpxlogger_running():
    print('killall gpxlogger')
    gpxlogger_LED('on')
    killall_gpxlogger()
    time.sleep(1)
    if not gpxlogger_running():
        print('gpxlogger stopped!\n')
        gpxlogger_LED('off')
    else:
        print('gpxlogger running with unknown reason ...\n')
        error_LED('on')
        gpxlogger_LED('on')


# Check sw_logger is off
if GPIO.input(24):
    print('gpxlogger switch on, switch it off and start again ...\n')
    error_LED('on')


# End init

print("PythonScript started ... \n")
# pythonScript-LED on
python_LED('on')



while 1:
    # this event controls the gpxlogger
    GPIO.add_event_detect(24, GPIO.BOTH, callback=ctrl_gpxlogger, bouncetime=100)

    print("Press shutdown button 5 seconds for shutdown, 2 seconds to stop program ...")
    print('or start gpxlogger ... \n')
    GPIO.wait_for_edge(25, GPIO.RISING, bouncetime=500) # button to shutdown

    if ctrl_shutdown_button(25):
        GPIO.cleanup()
        break

    GPIO.remove_event_detect(24)

