# coding:utf-8
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.clock import Clock
import os
import Queue
import time
from threading import Thread
from threading import Event


try:
    import can
    os.system("sudo /sbin/ip link set can0 up type can bitrate 500000")
    #filters = [{"can_id": 0x123, "can_mask": 0x7FF}]
    bus = can.interface.Bus(channel='can0', bustype='socketcan')
    bufferedReader = can.BufferedReader()
    notifier = can.Notifier(bus, [bufferedReader])
except Exception as e:
    print('CAN setup error:')
    print(e)

class CANcom(Widget):
    def __init__(self, **kwargs):
        super(CANcom, self).__init__(**kwargs)
        self.can_read_data = 0
        self.can_write_data = 0
        self.can_event = Clock.schedule_interval(self.can_read, 0.05)

    def can_read(self, dt):
        msg0 = msg1 = msg2 = 0
        write_can_data = False
        try:
            message = bufferedReader.get_message(timeout=0.01)
            if message:
                # get CAN message from module at address 0
                if message.arbitration_id == 0x000:
                    msg0 = message.data[0]
                    write_can_data = True
                # get CAN message from module at address 1
                if message.arbitration_id == 0x001:
                    msg1 = message.data[0] << 8
                    write_can_data = True
                # get CAN message from module at address 2
                if message.arbitration_id == 0x002:
                    msg2 = message.data[0] << 16
                    write_can_data = True

                if write_can_data:
                    self.can_read_data = msg0 + msg1 + msg2
        except Exception as e:
            pass

    def can_write(self, index, value):
        self.can_write_data = self.set_bit(self.can_write_data, index, value)
        msg = can.Message(arbitration_id=0x000, data=[0, 0, 0, 0, 0, 0, 0, self.can_write_data])
        bus.send(msg)

    def set_bit(self, v, index, x):
        """Set the index:th bit of v to 1 if x is truthy, else to 0, and return the new value."""
        mask = 1 << index  # Compute mask, an integer with just bit 'index' set.
        v &= ~mask  # Clear the bit indicated by the mask (if x is False)
        if x:
            v |= mask  # If x was True, set the bit indicated by the mask.
        return v  # Return the result, we're done.

class CanApp(App):
    def build(self):
        self.my_can = CANcom()
        self.can_get_data = Clock.schedule_interval(self.update, 1)
        return self.my_can

    def update(self, dt):
        try:
            print self.my_can.can_read_data
            self.my_can.can_write(0, 1)
            self.my_can.can_write(1, 1)
        except Exception as e:
            print('response queue error:')
            print(e)
            time.sleep(0.01)

    def on_stop(self):
        pass


if __name__ == '__main__':
    CanApp().run()