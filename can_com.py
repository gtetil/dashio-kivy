# coding:utf-8
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.clock import Clock
import os
import Queue
import time
from threading import Thread

try:
    import can
    os.system("sudo /sbin/ip link set can0 up type can bitrate 500000")
    bus = can.interface.Bus(channel='can0', bustype='socketcan')
except Exception as e:
    print('CAN setup error:')
    print(e)

class CANcom(Widget):
    def __init__(self, **kwargs):
        super(CANcom, self).__init__(**kwargs)
        self.q = Queue.Queue()
        self.rx = Thread(target=self.can_read)
        self.rx.daemon = True
        self.rx.start()

    def can_read(self):
        msg0 = msg1 = msg2 = 0
        data_to_queue = False
        while True:
            try:
                message = bus.recv(timeout=0.5)

                # get CAN message from module at address 0
                if message.arbitration_id == 0x000:
                    msg0 = message.data[0]
                    data_to_queue = True
                # get CAN message from module at address 1
                if message.arbitration_id == 0x001:
                    msg1 = message.data[0] << 8
                    data_to_queue = True
                # get CAN message from module at address 2
                if message.arbitration_id == 0x002:
                    msg2 = message.data[0] << 16
                    data_to_queue = True

                if data_to_queue:
                    msg = msg0 + msg1 + msg2
                    self.q.put(msg)  # Put data into queue
                    data_to_queue = False
                time.sleep(0.01)
            except Exception as e:
                #print('CAN Rx error:')
                #print(e)
                self.q.put(0)  # Debug Data
                time.sleep(0.1)

    def flush_queue(self):
        with self.q.mutex:
            self.q.queue.clear()

class CanApp(App):
    def build(self):
        self.my_can = CANcom()
        self.can_event = Clock.schedule_interval(self.update, 0.01)
        return self.my_can

    def update(self, dt):
        try:
            response = self.my_can.q.get()
            print response
        except Exception as e:
            print('response queue error:')
            print(e)
            time.sleep(0.01)

    def on_stop(self):
        pass


if __name__ == '__main__':
    CanApp().run()