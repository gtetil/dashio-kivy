# coding:utf-8
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.clock import Clock
import os
import time

import settings.app_settings as app_settings

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
    def __init__(self, dio_module, flame_detect, stack_temp, syrup_temp, **kwargs):
        super(CANcom, self).__init__(**kwargs)
        self.can_read_data = 0
        self.can_write_data = 0
        self.can_event = Clock.schedule_interval(self.can_read, 0.01)
        self.msg0 = self.msg1 = self.msg2 = 0
        self.write_can_data = False
        self.dio_module = dio_module
        self.flame_detect = flame_detect
        self.stack_temp = stack_temp
        self.stack_temp_can_read_data = [0] * app_settings.stack_read_data_len
        self.syrup_temp = syrup_temp
        self.syrup_temp_can_read_data = [0] * app_settings.syrup_read_data_len

    def can_read(self, dt):
        try:
            message = bufferedReader.get_message(timeout=0.005)
            if message:
                if self.dio_module or self.flame_detect:
                    # get CAN message from module at address 0
                    if message.arbitration_id == 0x000:
                        self.msg0 = message.data[0]
                        self.write_can_data = True
                    # get CAN message from module at address 1
                    if message.arbitration_id == 0x001:
                        self.msg1 = message.data[0] << 8
                        self.write_can_data = True
                    # get CAN message from module at address 2
                    if message.arbitration_id == 0x002:
                        self.msg2 = message.data[0] << 16
                        self.write_can_data = True

                    # write the CAN data that was just read to the can_read_data variable
                    # this is NOT writing CAN data to the bus...that's in another function
                    if self.write_can_data:
                        self.can_read_data = self.msg0 + self.msg1 + self.msg2
                        self.write_can_data = False

                if self.stack_temp:
                    if message.arbitration_id == 0x010:
                        self.stack_temp_can_read_data[0] = message.data[0] + (message.data[1] << 8)  # 0-1:  Current Temp (0-8192)
                        self.stack_temp_can_read_data[1] = message.data[2] + (message.data[3] << 8)  # 2-3:  Temp Setpoint (0-8192)

                if self.syrup_temp:
                    if message.arbitration_id == 0x011:
                        self.syrup_temp_can_read_data[0] = message.data[0] + (message.data[1] << 8)  # 0-1:  Current Temp (0-8192)
                        self.syrup_temp_can_read_data[1] = message.data[2] + (message.data[3] << 8)  # 2-3:  Temp Setpoint (0-8192)
                        self.syrup_temp_can_read_data[2] = message.data[4]  # 4:  Auto Mode State (0-1)
                        self.syrup_temp_can_read_data[3] = message.data[5]  # 5:  Close Valve State (0-1)
                        self.syrup_temp_can_read_data[4] = message.data[6]  # 6:  Open Valve State (0-1)

        except Exception as e:
            pass

    def can_write(self, index, value, channel_type):
        if self.dio_module or self.flame_detect:
            self.can_write_data = self.set_bit(self.can_write_data, index, value)
            self.msg = can.Message(arbitration_id=0x000+0x010, extended_id=False, data=[0, 0, 0, 0, 0, 0, 0, self.can_write_data])

        if self.stack_temp:
            if channel_type == 'STACK_TEMP_WRITE':
                can_data = [0]*3
                can_data[0] = value & 0xff  # 0-1:  Temp Setpoint (0-8192)
                can_data[1] = value >> 8
                can_data[2] = 1  # 2:  Output Enable (0-1)
                self.msg = can.Message(arbitration_id=0x000, extended_id=False, data=can_data)

        if self.syrup_temp:
            if channel_type == 'SYRUP_TEMP_WRITE':
                # set data requested to be written
                self.syrup_temp_can_read_data[index] = value

                # build message with current data, and requested data to be written
                can_data = [0]*5
                can_data[0] = self.syrup_temp_can_read_data[0] & 0xff  # 0-1:  Temp Setpoint (0-8192)
                can_data[1] = self.syrup_temp_can_read_data[0] >> 8
                can_data[2] = self.syrup_temp_can_read_data[2]  # 2:  Auto Mode (0-1)
                can_data[3] = self.syrup_temp_can_read_data[3]  # 3:  Close Valve (0-1, 2 = timed)
                can_data[4] = self.syrup_temp_can_read_data[4]  # 4:  Open Valve (0-1, 2 = timed)

                self.msg = can.Message(arbitration_id=0x000, extended_id=False, data=can_data)

        bus.send(self.msg)

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