import kivy
kivy.require('1.9.1') # replace with your current kivy version !

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.tabbedpanel import TabbedPanel
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.clock import Clock
from kivy.properties import StringProperty, NumericProperty
from kivy.uix.camera import Camera
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition

from kivy.core.window import Window

Window.size = (800,480)

import diIndicator, doToggle
import serial
import os
BASE = "/sys/class/backlight/rpi_backlight/"

debug_mode = 0
cam = Camera(resolution=(800, 480))

class MainScreen(Screen):
    pass

class MainApp(App):
    passcode = '1234'
    passcode_try = ''
    logged_in = NumericProperty(0)

    def build(self):
        self.arduino = Arduino()
        return MainScreen()

    def try_passcode(self, number):
        self.passcode_try = self.passcode_try + number
        if len(self.passcode_try) == len(self.passcode):
            if self.passcode_try == self.passcode:
                self.logged_in = 1
                self.root.add_widget(self.root.ids.logout_button)
            else:
                self.root.ids.main_tabbed_panel.switch_to(self.root.ids.main)
            self.passcode_try = ''
            self.root.ids.passcode_popup.dismiss()

    def brightness(self, value):
        if value > 0 and value < 256:
            _brightness = open(os.path.join(BASE, "brightness"), "w")
            _brightness.write(str(value))
            _brightness.close()
            return
        raise TypeError("Brightness should be between 0 and 255")

    def exit_app(self):
        self.stop()

class Arduino(Widget):
    digital_inputs = NumericProperty(0)

    def __init__(self, **kwargs):
        super(Arduino, self).__init__(**kwargs)
        Clock.schedule_interval(self.update_data, 0)

    def update_data(self, dt):
        if debug_mode == 0:
            try:
                serial_data = ser.readline().rstrip()
                self.digital_inputs = 0
                try:
                    self.digital_inputs = int(serial_data)
                except ValueError:
                    print('value error')
            except:
                print('Serial Read Failure')
                exit()
        else:
            self.digital_inputs = 5

    def set(self, command, state):
        if state == "down":
            int_state = '1/'
        else:
            int_state = '0/'
        ser.write(command + int_state)

if __name__ == '__main__':

    if debug_mode == 0:
        try:
            ser = serial.Serial('/dev/ttyUSB0', 115200)
        except:
            print "Failed to connect"
            exit()

    MainApp().run()

    ser.close()
    print('closed')
