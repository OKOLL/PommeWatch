from pyb import ADC, Pin
from time import time, sleep
import machine
import ssd1306

################################################################
# variables 
################################################################

HEART = [
[ 0, 0, 0, 0, 0, 0, 0, 0, 0],
[ 0, 1, 1, 0, 0, 0, 1, 1, 0],
[ 1, 1, 1, 1, 0, 1, 1, 1, 1],
[ 1, 1, 1, 1, 1, 1, 1, 1, 1],
[ 1, 1, 1, 1, 1, 1, 1, 1, 1],
[ 0, 1, 1, 1, 1, 1, 1, 1, 0],
[ 0, 0, 1, 1, 1, 1, 1, 0, 0],
[ 0, 0, 0, 1, 1, 1, 0, 0, 0],
[ 0, 0, 0, 0, 1, 0, 0, 0, 0],
]

MAX_HISTORY = 128
TOTAL_BEATS = 30

bpm = 0
last_y = 0
history = []
beats = []
options = ["chronometer","heart rate"]
selected_option = -1

################################################################
# code "init"
################################################################

# RTC
# annee mois jour jour_de_la_semaine heure minute seconde subseconde(compteur interne)
rtc = machine.RTC()
rtc.datetime((2022, 3, 14, 2, 14, 0, 0, 0))

# Power Display
machine.Pin('C13', machine.Pin.OUT).low()
machine.Pin('A8', machine.Pin.OUT).high()

# I2C --> send info to screen
i2c = machine.SoftI2C(scl=Pin('A15'), sda=Pin('C10'))

# Display
oled = ssd1306.SSD1306_I2C(128, 64, i2c)
oled.fill(0)

# Power Sensor
machine.Pin('A0', machine.Pin.OUT).low()
machine.Pin('C3', machine.Pin.OUT).high()

# ADC --> read sensor
Pin(Pin.cpu.C2, mode=Pin.IN)
adc = ADC('C2')

# Buttons
sw1 = Pin('SW1', Pin.IN)
sw1.init(Pin.IN, Pin.PULL_UP)

sw2 = Pin('SW2', Pin.IN)
sw2.init(Pin.IN, Pin.PULL_UP)

sw3 = Pin('SW3', Pin.IN)
sw3.init(Pin.IN, Pin.PULL_UP)

################################################################
# code "bpm"
################################################################

# display heart 
def display_heart():
    for y, row in enumerate(HEART):
        for x, value in enumerate(row):
            oled.pixel(x, y + 10, value)
    oled.show()

# display heartbeat
def display(time_display, bpm, value, min_value, max_value):
    global last_y

    oled.scroll(-1,0) # Scroll left 1 pixel    

    if max_value - min_value > 0:
        # Draw beat line
        y = 64 - int(21 * (value - min_value) / (max_value - min_value))
        oled.line(125, last_y, 126, y, 1)
        last_y = y

    # Clear top text area
    oled.fill_rect(0,0,128,20,0)

    oled.text(time_display, 0, 0)
    oled.text(str(int(bpm)) + " bpm", 12, 12)
    display_heart()
    
    oled.show()

def compute_bpm(beats, previous):
    if beats:
        beat_time = beats[-1] - beats[0]
        if beat_time:
            return (len(beats) / (beat_time)) * 60
    return previous

def menu_bpm():
    global history
    global beats
    global bpm

    # get date
    date = rtc.datetime()
    time_display = '{0:02d}'.format(date[4])+':'+'{0:02d}'.format(date[5])+':'+'{0:02d}'.format(date[6])

    # get sensor data
    value = adc.read()
    history.append(value)

    # Get the tail, up to MAX_HISTORY length
    history = history[-MAX_HISTORY:]
    min_value, max_value = min(history), max(history)

    # a value is considered a bit if it is bigger than 3/4 of the values
    tmp = sorted(history)
    index = (3 * len(history)) // 4
    threshold_beat = history[index]

    # a beat must be counted once, hence the verification 
    if value > threshold_beat and history[-1] > history[-2]:
        beats.append(time())
        # Truncate beats queue to max
        beats = beats[-TOTAL_BEATS:]
        bpm = compute_bpm(beats, bpm)

    display(time_display, bpm, value, min_value, max_value)

################################################################
# code "chronometer"
################################################################

def menu_chronometer():
    global selected_option

    is_running = False
    last_time = 0
    elapsed_time = 0
    timer = True

    while timer:
        oled.fill(0) 
        oled.text("Chronometer", 0, 0)

        if is_running:
            now = time()
            elapsed_time += now - last_time
            last_time = now

        hours = elapsed_time // 3600
        minutes = (elapsed_time % 3600) // 60
        seconds = elapsed_time % 60
        time_str = "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)

        oled.text(time_str, 0, 15)
        oled.show()

        if sw2.value() == 0:
            if is_running:
                # Pause chronometer
                is_running = False
            else:
                # Start chronometer
                last_time = time()
                is_running = True
            sleep(0.2)

        # Reset chronometer
        elif sw1.value() == 0:
            elapsed_time = 0
            is_running = False
            sleep(0.2)

        elif sw3.value() == 0:
            timer = False
            sleep(0.2)
            
    selected_option = -1


################################################################
# code "home"
################################################################

def menu_home():
    global selected_option
    global options

    selected_option = 0
    wait_for_validation = True
    while wait_for_validation:
        oled.fill(0)  # Clear the screen
        oled.text("Menu:", 0, 0)

        for i, option in enumerate(options):
            if i == selected_option:
                oled.text("> " + option, 0, 16 + i * 10)
            else:
                oled.text(option, 0, 16 + i * 10)
        oled.show()

        if sw1.value() == 0:
            selected_option = (selected_option - 1) % len(options)
            sleep(0.2)
        elif sw3.value() == 0:
            selected_option = (selected_option + 1) % len(options)
            sleep(0.2)
        elif sw2.value() == 0:
            oled.fill(0)  
            sleep(0.2)
            wait_for_validation = False

################################################################
# code "main"
################################################################

while(1):
    if sw3.value() == 0 or selected_option == -1:
        sleep(0.2)
        menu_home()
    elif selected_option == 0:
        menu_chronometer()
    elif selected_option == 1:
        menu_bpm()
