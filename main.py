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
BASE = "/sys/class/backlight/rpi_backlight/"

debug_mode = True
pc_mode = True

class Variable(Widget):
    var_tag = StringProperty('')
    var_description = StringProperty('')
    var_id = NumericProperty(0)
    var_data_type = StringProperty('')
    var_variable_type = StringProperty('')
    var_writeable = BooleanProperty(False)
    var_value = StringProperty('')
    app_ref = ObjectProperty(None)

    def on_var_tag(self, instance, value):
        self.get_from_json()

    def on_var_value(self, instance, value):
        if self.var_data_type == 'integer':
            self.value = int(value)
        if self.var_data_type == 'string':
            self.text = value
        if self.var_data_type == 'boolean':
            if value == 'True':
                self.active = True
            else:
                self.active = False
        self.set_to_json()
        self.app_ref.save_sys_data()

    def on_value(self, instance, value):
        self.var_value = str(int(value))

    def on_text(self, instance, value):
        self.var_value = value

    def on_active(self, instance, value):
        self.var_value = str(value)

    def get_from_json(self):
        try:
            self.var_tag = self.app_ref.sys_data_json[self.var_tag]['tag']
            self.var_description = self.app_ref.sys_data_json[self.var_tag]['description']
            self.var_id = self.app_ref.sys_data_json[self.var_tag]['id']
            self.var_data_type = self.app_ref.sys_data_json[self.var_tag]['data_type']
            self.var_variable_type = self.app_ref.sys_data_json[self.var_tag]['variable_type']
            self.var_writeable = self.app_ref.sys_data_json[self.var_tag]['writeable']
            self.var_value = self.app_ref.sys_data_json[self.var_tag]['var_value']
        except:
            pass

    def set_to_json(self):
        variable = {}
        variable['tag'] = str(self.var_tag)
        variable['description'] = str(self.var_description)
        variable['id'] = self.var_id
        variable['data_type'] = str(self.var_data_type)
        variable['variable_type'] = str(self.var_variable_type)
        variable['writeable'] = self.var_writeable
        variable['var_value'] = str(self.var_value)
        self.app_ref.sys_data_json[str(self.var_tag)] = variable

class VarSlider(Variable, Slider):
    pass

class VarTextInput(Variable, TextInput):
    pass

class VarSwitch(Variable, Switch):
    pass

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
        self.brightness()

    def brightness(self):
        value = int(self.main_screen.screen_brightness_slider.value)
        self.app_ref.system.backlight_brightness(value)

    def on_ignition_input(self, instance, state):
        if state == 1:
            if self.reverse_input == 0:
                if self.main_screen.password_disable_switch.active:
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
            self.event = Clock.schedule_once(self.delayed_screen_off, int(self.main_screen.screen_off_delay_input.text))
            self.event = Clock.schedule_once(self.delayed_shutdown, int(self.main_screen.shutdown_delay_input.text))

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
                if self.logged_in == 1 or self.main_screen.password_disable_switch.active:
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
    channel_type = StringProperty("")
    ignition_input = NumericProperty(0)
    digital_inputs = NumericProperty(0)
    app_ref = ObjectProperty(True)

    def set_properties(self, ref, channel, enable):
        self.dynamic_layout = ref
        self.channel = channel
        self.channel_type = self.channel.split('_')[0]
        self.variable = self.channel.split('_')[1]
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
        if not self.dynamic_layout.modify_mode and self.enable and self.app_ref.arduino.ignition_input:
            if self.channel_type == 'DO':
                self.app_ref.arduino.set('digital/' + self.variable + '/', self.state)
            if self.channel_type == 'SYS':
                if self.state == 'normal':
                    dim_state = 0
                else:
                    dim_state = 1
                self.app_ref.system.sys_cmd('DIM_BACKLIGHT', dim_state)
        else:
            self.state = 'normal'

class DynToggleButton(DynItem, ToggleButton):
    pass

class DynButton(DynItem, Button):
    toggle = BooleanProperty(False)

class IndicatorButton(DynItem, Button):
    toggle = BooleanProperty(False)

    def on_digital_inputs(self, instance, di_byte):
        if self.enable:
            if self.channel_type == 'DI':
                mask = 1 << int(self.variable)
                state = di_byte & mask
                state = state >> int(self.variable)
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
    pass

class MainApp(App):
    variables_file = 'variables.json'

    def build(self):
        self.open_sys_data()
        self.arduino = Arduino()
        self.system = System()
        self.screen_man = ScreenManagement()
        return self.screen_man

    def open_sys_data(self):
        with open(self.variables_file, 'r') as file:
            self.sys_data_json = json.load(file)

    def save_sys_data(self):
        with open(self.variables_file, 'w') as file:
            json.dump(self.sys_data_json, file, sort_keys=True, indent=4)

    def exit_app(self):
        self.stop()

class System(Widget):
    backlight_dim_value = NumericProperty(0)
    app_ref = ObjectProperty(None)
    main_screen = ObjectProperty(None)

    def sys_cmd(self, command, value):
        print(command + ", " + str(value))
        if command == 'DIM_BACKLIGHT':
            if value == 1:
                self.backlight_brightness(self.app_ref.screen_man.main_screen.screen_brightness_slider.value)
            else:
                self.backlight_brightness(255)


    def backlight_brightness(self, value):
        print(value)
        if not pc_mode:
            if value > 0 and value < 256:
                _brightness = open(os.path.join(BASE, "brightness"), "w")
                _brightness.write(str(value))
                _brightness.close()
                return
            raise TypeError("Brightness should be between 0 and 255")

class Arduino(Widget):
    digital_inputs = NumericProperty(0)
    reverse_input = NumericProperty(0)
    ignition_input = NumericProperty(0)

    def __init__(self, **kwargs):
        super(Arduino, self).__init__(**kwargs)
        self.toggle_ser_read(True)
        self.di_0 = Variable(var_tag = 'DI_0')
        #self.add_widget(self.di_0)

    def update_data(self, dt):
        if not debug_mode:
            try:
                serial_data = ser.readline().rstrip()
                try:
                    self.digital_inputs = int(serial_data)
                except ValueError:
                    print('value error')
            except:
                print('Serial Read Failure')
                exit()
        else:
            self.digital_inputs = 112
        self.reverse_input = self.digital_inputs & 1
        self.ignition_input = (self.digital_inputs & 1000000) >> 6

    def toggle_ser_read(self, state):
        if state:
            self.read_clock = Clock.schedule_interval(self.update_data, 0)
        else:
            try:
                self.read_clock.cancel()
            except:
                pass

    def set(self, command, state):
        if state == "down":
            int_state = '1/'
        else:
            int_state = '0/'
        if not debug_mode:
            ser.write(command + int_state)

if __name__ == '__main__':

    if not debug_mode:
        try:
            ser = serial.Serial('/dev/ttyUSB0', 115200)
        except:
            print "Failed to connect"
            exit()

    MainApp().run()

    ser.close()
    print('closed')
