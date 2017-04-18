import kivy
kivy.require('1.9.1') # replace with your current kivy version !

from kivy.config import Config
Config.set('kivy', 'keyboard_mode', 'systemanddock')
Config.set('graphics', 'maxfps', '100')

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.tabbedpanel import TabbedPanel
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.slider import Slider
from kivy.uix.textinput import TextInput
from kivy.uix.switch import Switch
from kivy.clock import Clock
from kivy.properties import StringProperty, NumericProperty, ObjectProperty, BooleanProperty
from kivy.uix.camera import Camera
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.uix.popup import Popup
from kivy.core.window import Window
from kivy.animation import Animation

import json
from functools import partial

Window.size = (800,480)

import serial
import os
import time
BASE = "/sys/class/backlight/rpi_backlight/"

debug_mode = False
pc_mode = True

current_milli_time = lambda: int(round(time.time() * 1000))

class ScreenManagement(ScreenManager):
    passcode = '1234'
    passcode_try = ''
    logged_in = 0
    main_screen = ObjectProperty(None)
    ignition_input = NumericProperty(0)
    reverse_input = NumericProperty(0)
    app_ref = ObjectProperty(None)
    settings_file = 'settings.json'

    def __init__(self,**kwargs):
        super (ScreenManagement,self).__init__(**kwargs)
        self.transition = NoTransition()
        self.main_screen.dynamic_layout.build_layout()

    def on_ignition_input(self, instance, state):
        if state == 1:
            if self.reverse_input == 0:
                if self.app_ref.variables.SYS_PASSWORD_DISABLE == '1':
                    self.current = 'main_screen'
                else:
                    self.current = 'passcode_screen'
            else:
                self.current = 'camera_screen'
            self.backlight_on(True)
            try:
                self.event.cancel()
            except:
                print('event probably was not created yet')
        else:
            self.event = Clock.schedule_once(self.delayed_screen_off, int(self.app_ref.variables.SYS_SCREEN_OFF_DELAY))
            self.event = Clock.schedule_once(self.delayed_shutdown, int(self.app_ref.variables.SYS_SHUTDOWN_DELAY))

    def delayed_screen_off(self, dt):
        self.current = 'off_screen'
        self.logged_in = 0
        self.backlight_on(False)

    def delayed_shutdown(self, dt):
        os.system("poweroff")

    def backlight_on(self, state):
        if not pc_mode:
            if state:
                state_str = '0'
            else:
                state_str = '1'
            _power = open(os.path.join(BASE, "bl_power"), "w")
            _power.write(state_str)
            _power.close()

    def on_reverse_input(self, instance, state):
        if state == 1:
            self.current = "camera_screen"
        else:
            if self.ignition_input == 1:
                if self.logged_in == 1 or self.app_ref.variables.SYS_PASSWORD_DISABLE == '1':
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
    app_ref = ObjectProperty(None)
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
            config['toggle'] = indicator.toggle
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
            toggle = data['indicator_' + str(i)]['toggle']
            channel = data['indicator_' + str(i)]['channel']
            enable = data['indicator_' + str(i)]['enable']
            if toggle:
                button = DynToggleButton(text=label, id='indicator_' + str(i))
            else:
                button = DynButton(text=label, id='indicator_' + str(i))
            button.bind(on_press=partial(self.item_edit_popup.edit_popup, 'button_' + str(i), indicator=False))
            button.set_properties(self, channel, enable)
            self.indicator_layout.add_widget(button)

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
            self.channel_spinner.text = self.item.channel
            self.toggle_layout.disabled = indicator
            self.open()

    def save_item(self):
        self.item.text = self.label_input.text
        self.item.toggle = self.toggle_check.active
        self.item.enable = self.enable_check.active
        self.item.channel = self.channel_spinner.text
        self.dynamic_layout.save_layout()
        self.dynamic_layout.build_layout()
        self.dismiss()

class DynItem(Widget):
    dynamic_layout = ObjectProperty(None)
    toggle = BooleanProperty(True)
    enable = BooleanProperty(True)
    channel = StringProperty("")
    ignition_input = NumericProperty(0)
    digital_inputs = NumericProperty(0)
    app_ref = ObjectProperty(None)
    data_change = BooleanProperty(False)

    def on_data_change(self, instance, value):
        state = self.app_ref.variables.get(self.channel)
        if state == '1':
            self.state = 'down'
        else:
            self.state = 'normal'

    def set_properties(self, ref, channel, enable):
        self.dynamic_layout = ref
        self.channel = str(channel)
        self.enable = enable
        ChangeItemBackground(self)

    def on_ignition_input(self, instance, state):
        if state == 0:
            self.state = 'normal'
            self.output_cmd()

    def on_press(self):
        self.output_cmd()

    def on_release(self):
        if not self.toggle:
            self.output_cmd()

    def output_cmd(self):
        if not self.dynamic_layout.modify_mode and self.enable and self.app_ref.variables.DI_IGNITION:
            if self.state == 'normal':
                state = '0'
            else:
                state = '1'
            self.app_ref.variables.set(self.channel, state)
        else:
            self.state = 'normal'

class DynToggleButton(DynItem, ToggleButton):
    pass

class DynButton(DynItem, Button):
    toggle = BooleanProperty(False)

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
    pass

class MainApp(App):

    def build(self):
        self.variables = Variables()
        self.screen_man = ScreenManagement()
        return self.screen_man

    def exit_app(self):
        self.stop()

class Variables(Widget):
    app_ref = ObjectProperty(None)
    data_change = BooleanProperty(False)
    variables_file = 'variables.json'
    arduino_input_tags = ['DI_0', 'DI_1', 'DI_2', 'DI_3', 'DI_4', 'DI_5', 'DI_IGNITION']
    arduino_output_tags = ['DO_0', 'DO_1', 'DO_2', 'DO_3', 'DO_4', 'DO_5']
    sys_save_var_tags = ['SYS_PASSWORD_DISABLE', 'SYS_SCREEN_BRIGHTNESS', 'SYS_DIM_BACKLIGHT', 'SYS_SCREEN_OFF_DELAY', 'SYS_SHUTDOWN_DELAY']
    sys_var_tags = ['SYS_REVERSE_CAM_ON']
    var_tags = arduino_input_tags + arduino_output_tags + sys_save_var_tags + sys_var_tags
    DI_0 = StringProperty('0')
    DI_1 = StringProperty('0')
    DI_2 = StringProperty('0')
    DI_3 = StringProperty('0')
    DI_4 = StringProperty('0')
    DI_5 = StringProperty('0')
    DI_IGNITION = StringProperty('0')
    DO_0 = StringProperty('0')
    DO_1 = StringProperty('0')
    DO_2 = StringProperty('0')
    DO_3 = StringProperty('0')
    DO_4 = StringProperty('0')
    DO_5 = StringProperty('0')
    SYS_DIM_BACKLIGHT = StringProperty('0')
    SYS_PASSWORD_DISABLE = StringProperty('0')
    SYS_SCREEN_BRIGHTNESS = StringProperty('0')
    SYS_SCREEN_OFF_DELAY = StringProperty('0')
    SYS_SHUTDOWN_DELAY = StringProperty('0')
    SYS_REVERSE_CAM_ON = StringProperty('0')

    def __init__(self, **kwargs):
        super(Variables, self).__init__(**kwargs)
        self.variable_data = ['0'] * len(self.var_tags)
        self.old_variable_data = ['0'] * len(self.var_tags)
        self.open_variables()
        self.toggle_ser_read(True)

    def open_variables(self):
        with open(self.variables_file, 'r') as file:
            self.sys_data_json = json.load(file)
        for tag in self.sys_save_var_tags:
            value = self.sys_data_json[tag]
            self.set(tag, value)

    def save_variables(self):
        for tag in self.sys_save_var_tags:
            self.sys_data_json[tag] = self.get(tag)
        with open(self.variables_file, 'w') as file:
            json.dump(self.sys_data_json, file, sort_keys=True, indent=4)

    def update_data(self, dt):
        if not debug_mode:
            #try:
            self.arduino_data = ser.readline().rstrip().split(',')
            for i in range(7):
                self.variable_data[i] = self.arduino_data[i]
            if self.variable_data == self.old_variable_data:
                self.data_change = False
            else:
                self.data_change = True
                print('variable data')
                print(self.variable_data)
                if self.variable_data[13:18] <> self.old_variable_data[13:18]:
                    self.save_variables()
                    print('saved vars')
            self.old_variable_data = list(self.variable_data)  # 'list()' must be used, otherwise it only copies a reference to the original list
            '''except:
                print('Serial Read Failure')
                exit()'''
        else:
            pass
        self.DI_0 = self.variable_data[0]
        self.DI_1 = self.variable_data[1]
        self.DI_2 = self.variable_data[2]
        self.DI_3 = self.variable_data[3]
        self.DI_4 = self.variable_data[4]
        self.DI_5 = self.variable_data[5]

        self.DO_0 = self.variable_data[7]
        self.DO_1 = self.variable_data[8]
        self.DO_2 = self.variable_data[9]
        self.DO_3 = self.variable_data[10]
        self.DO_4 = self.variable_data[11]
        self.DO_5 = self.variable_data[12]
        self.SYS_PASSWORD_DISABLE = self.variable_data[13]
        self.SYS_SCREEN_BRIGHTNESS = self.variable_data[14]
        self.SYS_DIM_BACKLIGHT = self.variable_data[15]
        self.SYS_SCREEN_OFF_DELAY = self.variable_data[16]
        self.SYS_SHUTDOWN_DELAY = self.variable_data[17]
        self.SYS_REVERSE_CAM_ON = self.variable_data[18]

        self.DI_IGNITION = '1'  # self.variable_data[6]  #need to update last due to screen initialization issue

    def toggle_ser_read(self, state):
        if state:
            self.read_clock = Clock.schedule_interval(self.update_data, 0)
        else:
            try:
                self.read_clock.cancel()
            except:
                pass

    def get(self, tag):
        index = self.var_tags.index(tag)
        return self.variable_data[index]

    def write_arduino(self, command):
        ser.write(command)
        time.sleep(.1)

    def set(self, tag, value):
        index = self.var_tags.index(tag)
        self.variable_data[index] = value
        channel_type = self.var_tags[index].split('_')[0]
        if channel_type == 'DO':
            self.write_arduino('digital_output/' + tag + '/' + value + '/')
        if channel_type == 'SYS':
            if tag == 'SYS_DIM_BACKLIGHT':
                self.sys_cmd(tag, int(value))

    #SYSTEM COMMANDS#

    def sys_cmd(self, command, value):
        if command == 'SYS_DIM_BACKLIGHT':
            if value == 1:
                self.backlight_brightness(int(self.get('SYS_SCREEN_BRIGHTNESS'))) #need to use "get" to get around initialization issue
            else:
                self.backlight_brightness(255)
        if command == 'SYS_SCREEN_BRIGHTNESS':
            if self.SYS_DIM_BACKLIGHT == "1":
                self.backlight_brightness(value)

    def backlight_brightness(self, value):
        print('brightness cmd')
        print(value)
        if not pc_mode:
            if value > 0 and value < 256:
                _brightness = open(os.path.join(BASE, "brightness"), "w")
                _brightness.write(str(value))
                _brightness.close()
                return
            raise TypeError("Brightness should be between 0 and 255")

if __name__ == '__main__':

    if not debug_mode:
        try:
            if not pc_mode:
                ser = serial.Serial('/dev/ttyUSB0', 115200)
            else:
                ser = serial.Serial('COM6', 115200)
        except:
            print "Failed to connect"
            exit()

    MainApp().run()

    ser.close()
    print('closed')
