import kivy
kivy.require('1.9.1') # replace with your current kivy version !

from kivy.config import Config
Config.set('kivy', 'keyboard_mode', 'systemanddock')
Config.set('graphics', 'maxfps', '10')

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.tabbedpanel import TabbedPanel
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.clock import Clock
from kivy.properties import StringProperty, NumericProperty, ObjectProperty, BooleanProperty
from kivy.uix.camera import Camera
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.uix.popup import Popup
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.animation import Animation

import json
from functools import partial

Window.size = (800,480)
Config.set('graphics', 'maxfps', '100')

import diIndicator, doToggle
import serial
import os
BASE = "/sys/class/backlight/rpi_backlight/"

debug_mode = 1

class ScreenManagement(ScreenManager):
    passcode = '7'
    passcode_try = ''
    logged_in = 0
    main_screen = ObjectProperty(None)
    ignition_input = NumericProperty(0)
    reverse_input = NumericProperty(0)
    settings_file = 'settings.json'

    def __init__(self,**kwargs):
        super (ScreenManagement,self).__init__(**kwargs)
        self.transition = NoTransition()
        self.main_screen.dynamic_layout.build_layout()

        with open(self.settings_file, 'r') as file:
            data = json.load(file)
            self.main_screen.screen_brightness_slider.value = data['settings']['screen_brightness']
            self.main_screen.screen_off_delay_input.text = str(data['settings']['screen_off_delay'])
            self.main_screen.password_disable_switch.active = data['settings']['password_disable']

    def save_settings(self):
        data = {}
        config = {}
        config['screen_brightness'] = int(self.main_screen.screen_brightness_slider.value)
        config['screen_off_delay'] = int(self.main_screen.screen_off_delay_input.text)
        config['password_disable'] = self.main_screen.password_disable_switch.active
        data['settings'] = config
        with open(self.settings_file, 'w') as file:
            json.dump(data, file, sort_keys=True, indent=4)

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

class DynamicLayout(Widget):
    indicator_layout = ObjectProperty(None)
    button_layout = ObjectProperty(None)
    indicator_edit_popup = ObjectProperty(None)
    button_edit_popup = ObjectProperty(None)
    modify_mode = BooleanProperty(False)
    layout_file = 'dynamic_layout.json'

    def save_layout(self):
        data = {}
        for indicator in self.indicator_layout.children:
            config = {}
            config['label'] = indicator.text
            config['channel'] = indicator.channel
            config['enable'] = indicator.enable
            data[indicator.id] = config
        for button in self.button_layout.children:
            config = {}
            config['label'] = button.text
            config['toggle'] = button.toggle
            config['channel'] = button.channel
            config['enable'] = button.enable
            data[button.id] = config
        with open(self.layout_file, 'w') as file:
            json.dump(data, file, sort_keys=True, indent=4)

    def build_layout(self):
        self.indicator_layout.clear_widgets()
        self.button_layout.clear_widgets()
        with open(self.layout_file, 'r') as file:
            data = json.load(file)
        for i in range(6):
            label = data['indicator_'+str(i)]['label']
            channel = data['indicator_' + str(i)]['channel']
            enable = data['indicator_' + str(i)]['enable']
            indicator_button = IndicatorButton(text=label, id='indicator_' + str(i))
            indicator_button.bind(on_press=partial(self.item_edit_popup.edit_popup, 'indicator_' + str(i), indicator=True))
            indicator_button.set_properties('null', channel, enable)
            self.indicator_layout.add_widget(indicator_button)

            label = data['button_' + str(i)]['label']
            toggle = data['button_' + str(i)]['toggle']
            enable = data['button_' + str(i)]['enable']
            channel = data['button_' + str(i)]['channel']
            if toggle:
                button = DynToggleButton(text=label, id='button_' + str(i))
            else:
                button = DynButton(text=label, id='button_' + str(i))
            button.bind(on_press=partial(self.item_edit_popup.edit_popup, 'button_' + str(i), indicator=False))
            button.set_properties(self, channel, enable)
            self.button_layout.add_widget(button)
        if self.modify_mode:
            self.modify_screen()

    def modify_screen(self):
        self.modify_mode = True
        for indicator in self.indicator_layout.children:
            self.animate(indicator)
        for button in self.button_layout.children:
            self.animate(button)
            button.output_cmd()

    def end_modify(self):
        self.modify_mode = False
        for indicator in self.indicator_layout.children:
            Animation.cancel_all(indicator)
            indicator.background_color = 1, 1, 1, 1
        for button in self.button_layout.children:
            Animation.cancel_all(button)
            button.background_color = 1, 1, 1, 1

    def animate(self, widget):
        anim = Animation(background_color=[1, 1, 0, 0.75], duration=0.5, t='linear') + Animation(
            background_color=[1, 1, 1, 1], duration=0.5, t='linear')
        anim.repeat = True
        anim.start(widget)

class ScreenItemEditPopup(Popup):
    label_input = ObjectProperty(None)
    toggle_check = ObjectProperty(None)
    enable_check = ObjectProperty(None)
    channel_spinner = ObjectProperty(None)
    toggle_layout = ObjectProperty(None)
    item = ObjectProperty(None)
    dynamic_layout = ObjectProperty(None)
    modify_mode = BooleanProperty(False)

    def edit_popup(self, instance, item, indicator):
        if self.modify_mode:
            self.item = item
            self.label_input.text = self.item.text
            self.toggle_check.active = self.item.toggle
            self.enable_check.active = self.item.enable
            self.channel_spinner.text = str(self.item.channel)
            self.toggle_layout.disabled = indicator
            self.open()

    def save_item(self):
        self.item.text = self.label_input.text
        self.item.toggle = self.toggle_check.active
        self.item.enable = self.enable_check.active
        self.item.channel = int(self.channel_spinner.text)
        self.dynamic_layout.save_layout()
        self.dynamic_layout.build_layout()
        self.dismiss()

class DynToggleButton(ToggleButton):
    dynamic_layout = ObjectProperty(None)
    toggle = BooleanProperty(True)
    enable = BooleanProperty(True)
    channel = NumericProperty(0)
    ignition_input = NumericProperty(0)
    app_ref = ObjectProperty(True)

    def set_properties(self, ref, channel, enable):
        self.dynamic_layout = ref
        self.channel = channel
        self.enable = enable
        ChangeItemBackground(self)

    def on_ignition_input(self, instance, state):
        if state == 0:
            self.state = 'normal'
            self.output_cmd()

    def on_press(self):
        self.output_cmd()

    def output_cmd(self):
        if self.dynamic_layout.modify_mode or not self.enable or not self.app_ref.arduino.ignition_input:
            self.state = 'normal'
        self.app_ref.arduino.set('digital/' + str(self.channel) + '/', self.state)

class DynButton(Button):
    dynamic_layout = ObjectProperty(None)
    toggle = BooleanProperty(False)
    enable = BooleanProperty(True)
    channel = NumericProperty(0)
    ignition_input = NumericProperty(0)
    app_ref = ObjectProperty(True)

    def set_properties(self, ref, channel, enable):
        self.dynamic_layout = ref
        self.channel = channel
        self.enable = enable
        ChangeItemBackground(self)

    def on_ignition_input(self, instance, state):
        if state == 0:
            self.state = 'normal'
            self.output_cmd()

    def on_press(self):
        self.output_cmd()

    def on_release(self):
        self.output_cmd()

    def output_cmd(self):
        if self.dynamic_layout.modify_mode or not self.enable or not self.app_ref.arduino.ignition_input:
            self.state = 'normal'
        self.app_ref.arduino.set('digital/' + str(self.channel) + '/', self.state)

class IndicatorButton(Button):
    channel = NumericProperty(0)
    toggle = BooleanProperty(False)
    enable = BooleanProperty(True)
    digital_inputs = NumericProperty(0)

    def set_properties(self, ref, channel, enable):
        self.channel = channel
        self.enable = enable
        ChangeItemBackground(self)

    def on_digital_inputs(self, instance, di_byte):
        if self.enable:
            mask = 1 << self.channel
            state = di_byte & mask
            state = state >> self.channel
            if state == 1:
                self.state = 'down'
            else:
                self.state = 'normal'

    def on_press(self):
        self.state = 'normal'

def ChangeItemBackground(item):
    if item.enable:
        item.background_normal = 'atlas://data/images/defaulttheme/button'
        item.color = 1, 1, 1, 1
    else:
        item.background_normal = 'atlas://data/images/defaulttheme/button_disabled'
        item.color = 0, 0, 0, 0

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
        try:
            #serial_data = ser.readline().rstrip()
            serial_data = '255'
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

    def set(self, command, state):
        if state == "down":
            int_state = '1/'
        else:
            int_state = '0/'
        #ser.write(command + int_state)

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
