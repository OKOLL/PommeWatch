from pyb import ADC, Pin
from time import time
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

################################################################
# code "runtime"
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


################################################################
# code "main"
################################################################

while(1):
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
        print('beat  ' + str(value))
        beats.append(time())
        # Truncate beats queue to max
        beats = beats[-TOTAL_BEATS:]
        bpm = compute_bpm(beats, bpm)

    display(time_display, bpm, value, min_value, max_value)
