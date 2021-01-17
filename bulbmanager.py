import bluetooth, threading, logging
from bulb import BluetoothBulb

class BluetoothBulbManager:
    def __init__(self):
        self.__devices = { }
        self.__discover_running = False
    
    
    def __del__(self):
        if self.__discover_running:
            self.stop()
    
    
    def start(self, discover_callback):
        logging.debug('Starting discoverer')
        if not self.__discover_running:
            self.__discover_callback = discover_callback
            self.__discover_thread = threading.Thread(target=self.__discover_devices, args=())
            self.__discover_thread.start()
    
    
    def stop(self):
        logging.debug('Stopping discoverer')
        if self.__discover_thread and self.__discover_running:
            self.__discover_running = False
            self.__discover_thread.join()
            
        for addr, bulb in self.__devices.items():
            bulb.disconnect()
            self.__discover_callback(False, bulb)

        self.__devices.clear()
    
    
    def __discover_devices(self):
        self.__discover_running = True
        index = 0
        while self.__discover_running:
            index = (index + 1) % 4
            try:
                devices = bluetooth.discover_devices(duration=(1, 2, 4, 8)[index], lookup_names=True)

                for addr, name in devices:
                    if addr not in self.__devices and addr[0:4] in ('C9:7', 'C9:8', 'C9:A'):
                        bulb = BluetoothBulb(addr, name)
                        bulb.connect()
                        self.__discover_callback(True, bulb)
                        self.__devices[addr] = bulb

                to_delete = list()
                for addr, bulb in self.__devices.items():
                    if (addr, bulb.get_name()) not in devices and not bulb.is_connected():
                        to_delete.append(addr)
                        bulb.disconnect()
                        self.__discover_callback(False, bulb)
                for addr in to_delete:
                    del self.__devices[addr]
            except:
                logging.debug('Discoverer stopped unexpectedly')
                self.__discover_running = False
                raise
            # wait 1 minute before attempting new discover
            #time.sleep(60)

        logging.debug('Discoverer stopped')
    
    
    def get_bluetooth_bulb(self, addr):
        return self.__devices[addr]


