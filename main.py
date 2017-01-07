import kivy
kivy.require('1.9.1') # replace with your current kivy version !

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.tabbedpanel import TabbedPanel
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.clock import Clock
from kivy.properties import StringProperty, NumericProperty, ObjectProperty
from kivy.uix.camera import Camera
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.uix.popup import Popup
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.config import Config

Window.size = (800,480)
Config.set('graphics', 'maxfps', '100')

import diIndicator, doToggle
import serial
import os
BASE = "/sys/class/backlight/rpi_backlight/"

debug_mode = 0

class ScreenManagement(ScreenManager):
    passcode = '1234'
    passcode_try = ''
    logged_in = 1
    ignition_input = NumericProperty(0)
    reverse_input = NumericProperty(0)
    passcode_ref = ObjectProperty(None)

    def __init__(self,**kwargs):
        super (ScreenManagement,self).__init__(**kwargs)
        self.transition = NoTransition()

    def on_ignition_input(self, instance, state):
        if state == 1:
            #self.current = 'passcode_screen'
            self.current = 'main_screen'
            state_str = '0'
        else:
            Clock.schedule_once(self.delayed_screen_off, 5)
            state_str = '1'
        #_power = open(os.path.join(BASE, "bl_power"), "w")
        #_power.write(state_str)
        #_power.close()

    def delayed_screen_off(self, dt):
        self.current = 'off_screen'
        self.logged_in = 0

    def on_reverse_input(self, instance, state):
        if state == 1:
            self.current = "camera_screen"
        else:
            if self.ignition_input == 1:
                if self.logged_in == 1:
                    self.current = "main_screen"
                else:
                    self.current = "passcode_screen"
            else:
                self.current = 'off_screen'

    def try_passcode(self, number):
        self.passcode_try = self.passcode_try + number
        if len(self.passcode_try) == len(self.passcode):
            if self.passcode_try == self.passcode:
                self.current = 'main_screen'
                self.logged_in = 1
            else:
                self.current_screen.ids.fail_popup.open()
            self.passcode_try = ''

class MainScreen(Screen):
    pass

class PasscodeScreen(Screen):
    pass

class CameraScreen(Screen):
    reverse_input = NumericProperty(0)

    def __init__(self,**kwargs):
        super (CameraScreen,self).__init__(**kwargs)
        self.cam = Camera(resolution=(800, 480))
        self.add_widget(self.cam)

    def on_reverse_input(self, instance, state):
        if state == 1:
            self.cam.play = True
        else:
            self.cam.play = False

class MainApp(App):

    def build(self):
        self.arduino = Arduino()
        return ScreenManagement()

    def brightness(self, value):
        if value > 0 and value < 256:
            #_brightness = open(os.path.join(BASE, "brightness"), "w")
            #_brightness.write(str(value))
            #_brightness.close()
            return
        raise TypeError("Brightness should be between 0 and 255")

    def exit_app(self):
        self.stop()

class Arduino(Widget):
    digital_inputs = NumericProperty(0)
    reverse_input = NumericProperty(0)
    ignition_input = NumericProperty(0)

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
                    self.reverse_input = self.digital_inputs & 1
                    self.ignition_input = (self.digital_inputs & 1000000) >> 6
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
