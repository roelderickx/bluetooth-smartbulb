import sys, logging, getch
from bulb import BluetoothBulb

if len(sys.argv) < 2:
    print('Usage: %s [MAC-address]' % sys.argv[0])
    quit()

logging.basicConfig(level=getattr(logging, 'INFO', None))

b = BluetoothBulb(sys.argv[1], 'test')
try:
    b.connect()
    
    print('Usage:')
    print('p    Toggle power')
    print('w,c  Toggle white or color mode')
    print('-,+  Decrement or increment brightness')
    print('[,]  Decrement or increment hue by 5 degrees')
    print('0-9  Set color temperature from 1500K to 6600K')
    print('q    Quit')
    
    is_running = True
    while is_running:
        c = getch.getch()
        if c == 'p':
            b.set_power(not b.is_powered_on())
        elif c == 'w':
            b.set_color_mode(False)
        elif c == 'c':
            b.set_color_mode(True)
        elif c == '-':
            new_brightness = max(1, b.get_brightness() - 1)
            b.set_brightness(new_brightness)
        elif c == '+':
            new_brightness = min(16, b.get_brightness() + 1)
            b.set_brightness(new_brightness)
        elif c == '[':
            (hue, sat, val) = b.get_color_hsv()
            new_hue = hue - 5
            if new_hue < 0:
                new_hue += 360
            b.set_color_hsv(new_hue, b.get_brightness())
        elif c == ']':
            (hue, sat, val) = b.get_color_hsv()
            new_hue = hue + 5
            if new_hue >= 360:
                new_hue -= 360
            b.set_color_hsv(new_hue, b.get_brightness())
        elif c == '0':
            b.set_white_temperature(1500, b.get_brightness())
        elif c == '1':
            b.set_white_temperature(2067, b.get_brightness())
        elif c == '2':
            b.set_white_temperature(2633, b.get_brightness())
        elif c == '3':
            b.set_white_temperature(3200, b.get_brightness())
        elif c == '4':
            b.set_white_temperature(3767, b.get_brightness())
        elif c == '5':
            b.set_white_temperature(4333, b.get_brightness())
        elif c == '6':
            b.set_white_temperature(4900, b.get_brightness())
        elif c == '7':
            b.set_white_temperature(5467, b.get_brightness())
        elif c == '8':
            b.set_white_temperature(6033, b.get_brightness())
        elif c == '9':
            b.set_white_temperature(6600, b.get_brightness())
        elif c == 'q':
            is_running = False
finally:
    b.disconnect()

