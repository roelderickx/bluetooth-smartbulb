import bluetooth, math, time, threading, logging

class BluetoothBulb:
    def __init__(self, mac_address, name):
        self.__mac_address = mac_address
        self.__name = name
        self.__sock = None
        self.__socket_lock = threading.Lock()
        self.__heartbeat_running = False
        self.__heartbeat_thread = None
        self.__is_power = None
        self.__is_color = None
        self.__current_brightness = None
        self.__current_color = None
    
    
    def is_connected(self):
        return (self.__sock is not None)


    def get_name(self):
        return self.__name


    def get_mac_address(self):
        return self.__mac_address
    
    
    def is_powered_on(self):
        return self.__is_power
    
    
    def is_color_mode(self):
        return self.__is_color
    
    
    # returns current lamp brightness. range is [1, 16]
    def get_brightness(self):
        return self.__current_brightness


    # returns tuple (r, g, b) with current lamp color
    def get_color_rgb(self):
        return self.__current_color


    # see https://en.wikipedia.org/wiki/HSL_and_HSV
    def __rgb_to_hsv(self, r, g, b):
        (r_, g_, b_) = (r/255, g/255, b/255)
        c_max = max(r_, g_, b_)
        c_min = min(r_, g_, b_)
        delta_c = c_max - c_min
        
        hue = 0
        if delta_c != 0 and c_max == r_:
            hue = 60 * (((g_-b_)/delta_c) % 6)
        elif delta_c != 0 and c_max == g_:
            hue = 60 * (((b_-r_)/delta_c) + 2)
        elif delta_c != 0 and c_max == b_:
            hue = 60 * (((r_-g_)/delta_c) + 4)
        
        sat = 0
        if c_max != 0:
            sat = delta_c / c_max
        
        val = c_max
        
        return (hue, sat, val)


    # returns tuple (hue, sat, val) with current lamp color
    def get_color_hsv(self):
        (r, g, b) = self.get_color_rgb()
        return self.__rgb_to_hsv(r, g, b)
    
    
    # calculates __current_brightness from (r, g, b) color
    # and sets __current_color to (r, g, b) at maximum intensity
    def __set_normalized_color_brightness(self, r, g, b):
        brightness = max(r, g, b, 1)
        if brightness == 255:
            self.__current_brightness = 16
            self.__current_color = (r, g, b)
        else:
            self.__current_brightness = math.ceil(brightness / 16)
            self.__current_color = \
                (math.ceil(round(r * 255 / brightness, 0)), \
                 math.ceil(round(g * 255 / brightness, 0)), \
                 math.ceil(round(b * 255 / brightness, 0)))
    

    def __send_hex_string(self, bulb_function, data):
        with self.__socket_lock:
            try:
                logging.debug('Sending function %02x - data %s' % (bulb_function, data))
                hex_string = '01fe000051%02x' % bulb_function # 01fe0000 + 51 (write) + function code
                length = int(len(data) / 2) + 7
                hex_string = '%s%02x%s' % (hex_string, length, data)
                self.__sock.send(bluetooth.binascii.unhexlify(hex_string))
                
                logging.debug('Receiving answer')
                header = self.__sock.recv(6) # 01fe0000 + 41 (read) + function code
                logging.debug('  header = %s' % bluetooth.binascii.hexlify(header))
                length = self.__sock.recv(1) # length
                logging.debug('  length = %d' % length[0])
                data = self.__sock.recv(length[0] - 7) # data
                logging.debug('  data = %s' % bluetooth.binascii.hexlify(data))
            except:
                self.__sock.close()
                self.__sock = None

        return data


    # Connects to the bulb at the given MAC address. Note that the bluetooth controller should be
    # powered on and no other device should have a connection to the bulb.
    def connect(self):
        # search for SPP service
        service_matches = bluetooth.find_service(uuid='00001101-0000-1000-8000-00805F9B34FB', \
                                                 address=self.__mac_address)

        if len(service_matches) > 0:
            #if len(service_matches) > 1:
            #    logging.warning("More than 1 service found, continuing with the first service.")

            first_match = service_matches[0]
            name = first_match['name']
            host = first_match['host']
            port = first_match['port']

            # Create the client socket
            logging.info('Connecting to \'%s\' on %s port %s' % (name, host, port))
            try:
                self.__sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
                self.__sock.connect((host, port))
                
                self.__setup_connection()
            except:
                logging.error('Connection to %s failed' % self.__mac_address)
                self.__sock = None
        else:
            logging.error('Couldn\'t find the SPP service.')


    # Disconnects from the bulb.
    def disconnect(self):
        if self.__sock:
            logging.info('Disconnecting')
            self.__stop_heartbeat_thread()
            self.__sock.close()
            self.__sock = None
            self.__is_power = None
            self.__is_color = None
            self.__current_brightness = None
            self.__current_color = None


    def __check_connection(func):
        def wrapper(self, *args, **kargs):
            if not self.__sock:
                raise Exception('Need to connect first!')
            return func(self, *args, **kargs)

        return wrapper


    @__check_connection
    def __setup_connection(self):
        logging.debug('Setup connection')
        # ASCII 01234567
        self.__sock.send(bluetooth.binascii.unhexlify('3031323334353637'))
        self.__start_heartbeat_thread()
        # read current color
        self.__read_current_status()
        # we don't know the pwer state, turn it on to be sure
        self.set_power(True)
    
    
    # bulb function 0x00, TODO information is returned but its meaning is unclear
    @__check_connection
    def read_information_0x00(self):
        return self.__send_hex_string(0x00, '000000008000000080')


    # bulb function 0x02, heartbeat TODO information is returned but its meaning is unclear
    # The official app sends this about once a second, but it turns out to be not strictly necessary
    #@__check_connection
    def __heartbeat(self):
        self.__heartbeat_running = True
        while self.__heartbeat_running:
            logging.debug('Heartbeat')
            self.__send_hex_string(0x02, '000000008000000080')
            time.sleep(1)
        logging.debug('Heartbeat stopped')
    
    
    def __start_heartbeat_thread(self):
        logging.debug('Starting heartbeat')
        if not self.__heartbeat_running:
            self.__heartbeat_thread = threading.Thread(target=self.__heartbeat, args=())
            self.__heartbeat_thread.start()
    
    
    def __stop_heartbeat_thread(self):
        logging.debug('Stopping heartbeat')
        if self.__heartbeat_thread and self.__heartbeat_running:
            self.__heartbeat_running = False
            self.__heartbeat_thread.join()
    
    
    # bulb function 0x80, read bulb identification
    # At least the name of the device is returned and probably a version number as well, but the
    # meaning of the other information is unclear
    @__check_connection
    def read_identification(self):
        logging.debug('Read lamp information')
        return self.__send_hex_string(0x80, '000000000000000000')


    # bulb function 0x81, subfunction 0x00: read power and color status
    @__check_connection
    def __read_current_status(self):
        data = self.__send_hex_string(0x81, '0000000000000000000d07010300000e')
        logging.debug('Read color mode status: %s' % bluetooth.binascii.hexlify(data))
        if data[14] == 0x01:
            self.__is_color = False
            self.__current_brightness = data[15] # range 0-16
            self.__current_color = (0xff, 0xff, 0xff)
        elif data[14] == 0x02:
            data = self.__send_hex_string(0x81, '0000000000000000000d07020300000e')
            logging.debug('Read color status: %s' % bluetooth.binascii.hexlify(data))
            self.__is_color = True
            self.__set_normalized_color_brightness(data[16], data[17], data[18])
        
        logging.info('Mode is %s' % ('color' if self.__is_color else 'yellow/white'))
        logging.info('Brightness is %d' % self.__current_brightness)
        logging.info('Color is %02x%02x%02x' % self.__current_color)
    
    
    # bulb function 0x81, subfunction 0x01: write power and color status
    @__check_connection
    def set_power(self, is_power):
        logging.debug('Set power %s' % ('on' if is_power else 'off'))
        if self.__is_power is None or self.__is_power != is_power:
            self.__send_hex_string(0x81, '0000000000000000000d07%s0301%s0e' % \
                                   ('02' if self.__is_color else '01', \
                                    '01' if is_power else '02'))
            self.__is_power = is_power
    
    
    # bulb function 0x81, subfunction 0x01: write power and color status
    @__check_connection
    def set_color_mode(self, is_color):
        logging.debug('Switch to %s' % ('color mode' if is_color else 'white/yellow mode'))
        if self.__is_color is None or self.__is_color != is_color:
            self.__send_hex_string(0x81, '0000000000000000000d07%s0301%s0e' % \
                                   ('02' if is_color else '01', \
                                    '01' if self.__is_power else '02'))
            self.__is_color = is_color


    # bulb function 0x81, subfunction 0x02: set brightness
    @__check_connection
    def set_brightness(self, brightness):
        logging.debug('Set brightness to %s' % brightness)
        if not self.__is_color:
            self.__send_hex_string(0x81, '0000000000000000000d07010302%02x0e' % brightness)
            self.__current_brightness = brightness
        else:
            (r, g, b) = self.__current_color
            r_ = int(round(r * brightness / 16, 0))
            g_ = int(round(g * brightness / 16, 0))
            b_ = int(round(b * brightness / 16, 0))
            self.set_color_rgb(r_, g_, b_)
    
    
    # bulb function 0x81, subfunction 0x03: set color
    @__check_connection
    def set_color_rgb(self, r, g, b):
        logging.debug('Set color to %02x%02x%02x' % (r, g, b))
        
        self.__send_hex_string(0x81, '0000000000000000000d0a020303%02x%02x%02x000e' % (r, g, b))
        
        self.__is_color = True
        self.__set_normalized_color_brightness(r, g, b)


    # see https://en.wikipedia.org/wiki/HSL_and_HSV
    def __hsv_to_rgb(self, hue, sat, val):
        c = val * sat
        x = c * (1 - abs(((hue/60.0) % 2) - 1))
        m = val - c
        
        (r_, g_, b_) = (0, 0, 0)
        if 0 <= hue < 60:
            (r_, g_, b_) = (c, x, 0)
        elif 60 <= hue < 120:
            (r_, g_, b_) = (x, c, 0)
        elif 120 <= hue < 180:
            (r_, g_, b_) = (0, c, x)
        elif 180 <= hue < 240:
            (r_, g_, b_) = (0, x, c)
        elif 240 <= hue < 300:
            (r_, g_, b_) = (x, 0, c)
        elif 300 <= hue < 360:
            (r_, g_, b_) = (c, 0, x)
        
        (r, g, b) = \
            (int(round((r_+m)*255, 0)), \
             int(round((g_+m)*255, 0)), \
             int(round((b_+m)*255, 0)))
        
        return (r, g, b)
        
    
    # 0 <= hue < 360, sat = 100, 1 <= brightness <= 16
    @__check_connection
    def set_color_hsv(self, hue, brightness):
        sat = 1.0 # saturation values below 0.7 are pointless, will always result in white
        val = brightness/16
        (r, g, b) = self.__hsv_to_rgb(hue, 1.0, val)
        self.set_color_rgb(r, g, b)


    # see https://tannerhelland.com/2012/09/18/convert-temperature-rgb-algorithm-code.html
    # teperature range is [1000, 40000], but the intersting red to white range is [1500, 6600]
    def __temp_to_rgb(self, temperature, brightness):
        t = min(40000, max(1000, temperature)) / 100 # constrain to [1000, 40000] and divide by 100
        # red
        r = 255
        if t > 66:
            r = t - 60
            r = 329.698727446 * pow(r, -0.1332047592)
            r = min(255, max(0, r)) # constrain to [0, 255]
        # green
        g = 255
        if t <= 66:
            g = t
            g = 99.4708025861 * math.log(g) - 161.1195681661
            g = min(255, max(0, g)) # constrain to [0, 255]
        else:
            g = t - 60
            g = 288.1221695283 * pow(g, -0.0755148492)
            g = min(255, max(0, g)) # constrain to [0, 255]
        # blue
        b = 255
        if t < 66:
            b = t - 10
            b = 138.5177312231 * math.log(b) - 305.0447927307
            b = min(255, max(0, b)) # constrain to [0, 255]
        
        (r_, g_, b_) = \
            (int(round(r * brightness / 16, 0)),
             int(round(g * brightness / 16, 0)),
             int(round(b * brightness / 16, 0)))
        
        return (r_, g_, b_)
    
    
    # 1000 <= temp_kelvin <= 40000, 1 <= brightness <= 16
    @__check_connection
    def set_white_temperature(self, temp_kelvin, brightness):
        (r, g, b) = self.__temp_to_rgb(temp_kelvin, brightness)
        self.set_color_rgb(r, g, b)
    

    # TODO investigate modes 1, 2 and 3
    # 0 -> off
    # 1 -> existing color ?? rhythm
    # 2 -> existing color ?? rhythm
    # 3 -> existing color ?? rhythm
    # 4 -> rainbow
    # 5 -> pulse
    # 6 -> candle
    # bulb function 0x81, subfunction 0x04: set party mode
    @__check_connection
    def set_party_mode(self, mode):
        logging.debug('Set party mode %s' % mode)
        self.__send_hex_string(0x81, '0000000000000000000d07020304%02x0e' % mode)
        self.__is_color = True

