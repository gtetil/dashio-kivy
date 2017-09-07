import kivy
kivy.require('1.9.1') # replace with your current kivy version !

from kivy.config import Config
Config.set('kivy', 'keyboard_mode', 'systemanddock')
Config.set('graphics', 'maxfps', '100')
Config.set('postproc', 'double_tap_distance', '100')

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.tabbedpanel import TabbedPanel
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.slider import Slider
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.switch import Switch
from kivy.clock import Clock
from kivy.properties import StringProperty, NumericProperty, ObjectProperty, BooleanProperty, ListProperty
from kivy.uix.camera import Camera
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.uix.popup import Popup
from kivy.core.window import Window
from kivy.animation import Animation
from navigationdrawer import NavigationDrawer
from kivy.uix.settings import SettingsWithSidebar, SettingString, SettingNumeric, SettingSpacer, Settings
from kivy.metrics import dp
from kivy.uix.scatterlayout import ScatterLayout
from kivy.uix.scatter import Scatter
from kivy.graphics.transformation import Matrix
from kivy.graphics import Color, Rectangle
from kivy.factory import Factory
from kivy_cv import KivyCamera
import app_settings
import cv2

import json
from functools import partial

Window.size = (800,480)

import psutil
import serial
import os
import time
import re
import platform
from operator import xor
BASE = "/sys/class/backlight/rpi_backlight/"

operating_sys = platform.system()

try:
    import RPi.GPIO as GPIO
except:
    pass

current_milli_time = lambda: int(round(time.time() * 1000))
initial_time = current_milli_time()

class SlideLayout(NavigationDrawer):
    pass

class SlideMenu(BoxLayout):
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
        self.start_inactivity_clock()

    def on_touch_down(self, touch):
        self.start_inactivity_clock()
        return super(ScreenManagement, self).on_touch_down(touch)

    def start_inactivity_clock(self):
        self.app_ref.variables.set_by_alias('SYS_INACTIVE', '0')
        try:
            self.screen_inactive_event.cancel()
        except:
            pass
        self.screen_inactive_event = Clock.schedule_once(self.sys_inactive, int(self.app_ref.variables.get('SYS_INACTIVE_TIME')))

    def sys_inactive(self, dt):
        self.app_ref.variables.set_by_alias('SYS_INACTIVE', '1')

    def on_ignition_input(self, instance, state):
        if state == 1:
            if self.reverse_input == 0:
                self.current = 'main_screen'
            else:
                self.current = 'camera_screen'
            self.backlight_on(True)
            try:
                self.screen_off_event.cancel()
                self.shutdown_event.cancel()
            except:
                print('event probably was not created yet')
        else:
            self.screen_off_event = Clock.schedule_once(self.delayed_screen_off, int(self.app_ref.variables.get('SYS_SCREEN_OFF_DELAY')))
            self.shutdown_event = Clock.schedule_once(self.delayed_shutdown, float(self.app_ref.variables.get('SYS_SHUTDOWN_DELAY'))*60)

    def delayed_screen_off(self, dt):
        self.current = 'off_screen'
        self.backlight_on(False)

    def delayed_shutdown(self, dt):
        self.app_ref.variables.set_by_alias('SYS_SHUTDOWN', '1')

    def backlight_on(self, state):
        if state:
            state_str = '0'
        else:
            state_str = '1'
        try:
            _power = open(os.path.join(BASE, "bl_power"), "w")
            _power.write(state_str)
            _power.close()
        except Exception as e:
            print('Tried to toggle RPi backlight:')
            print(e)

    def on_reverse_input(self, instance, state):
        print('rev state, ' + str(state))
        if state == 1:
            self.current = "camera_screen"
        else:
            if self.ignition_input == 1:
                self.current = "main_screen"
            else:
                self.current = 'off_screen'

    def try_passcode(self, number):
        self.passcode_try = self.passcode_try + number
        if len(self.passcode_try) == len(self.passcode):
            if self.passcode_try == self.passcode:
                self.current = 'main_screen'
                self.app_ref.variables.set_by_alias('SYS_LOGGED_IN', '1')
            else:
                self.current_screen.ids.fail_popup.open()
            self.passcode_try = ''

class MainScreen(Screen):
    pass

class FloatInput(TextInput):
    pat = re.compile('[^0-9]')
    def insert_text(self, substring, from_undo=False):
        pat = self.pat
        if '.' in self.text:
            s = re.sub(pat, '', substring)
        else:
            s = '.'.join([re.sub(pat, '', s) for s in substring.split('.', 1)])
        return super(FloatInput, self).insert_text(s, from_undo=from_undo)

class DynamicLayout(Widget):
    app_ref = ObjectProperty(None)
    modify_mode = BooleanProperty(False)
    layout_file = 'dynamic_layout.json'
    dyn_widget_dict = {}
    scatter_dict = {}

    def build_layout(self):
        with open(self.layout_file, 'r') as file:
            self.dyn_layout_json = json.load(file)
        for id in self.dyn_layout_json:
            self.create_dyn_widget(id)
            self.update_widget(id)

    def reconcile_layout(self):
        for id, dyn_widget in self.dyn_widget_dict.items():
            self.update_widget(id)
            self.edit_widget_json(id)
        self.save_layout()

    def create_dyn_widget(self, id):
        widget = self.dyn_layout_json[id]['widget']
        if widget in ['Toggle Button', 'Indicator']:
            dyn_widget = DynToggleButton(text='',
                                         id=str(id),
                                         button_on_text=self.dyn_layout_json[id]['on_text'],
                                         button_off_text=self.dyn_layout_json[id]['off_text'],
                                         var_tag=self.dyn_layout_json[id]['var_tag'],
                                         var_alias=self.dyn_layout_json[id]['var_alias'],
                                         widget=widget,
                                         invert=self.dyn_layout_json[id]['invert'])
        elif widget == 'Button':
            dyn_widget = DynButton(text='',
                                   id=str(id),
                                   button_on_text=self.dyn_layout_json[id]['on_text'],
                                   button_off_text=self.dyn_layout_json[id]['off_text'],
                                   var_tag=self.dyn_layout_json[id]['var_tag'],
                                   var_alias=self.dyn_layout_json[id]['var_alias'],
                                   widget=widget,
                                   invert=self.dyn_layout_json[id]['invert'])
        else:
            dyn_widget = DynLabel(text='',
                                   id=str(id),
                                   button_on_text=self.dyn_layout_json[id]['on_text'],
                                   button_off_text=self.dyn_layout_json[id]['off_text'],
                                   var_tag=self.dyn_layout_json[id]['var_tag'],
                                   var_alias=self.dyn_layout_json[id]['var_alias'],
                                   widget=widget,
                                   invert=self.dyn_layout_json[id]['invert'])
        scatter_layout = MyScatterLayout(id=str(id) + '_scatter',
                                         do_rotation=False,
                                         size=(self.dyn_layout_json[id]['size'][0], self.dyn_layout_json[id]['size'][1]),
                                         size_hint=(None, None),
                                         pos=self.dyn_layout_json[id]['pos'])
        scatter_layout.add_widget(dyn_widget)
        self.app_ref.main_screen_ref.ids.main_layout.add_widget(scatter_layout)
        self.dyn_widget_dict[id] = dyn_widget
        self.scatter_dict[id] = scatter_layout

    def update_widget(self, id):
        dyn_widget_ref = self.dyn_widget_dict[id]
        try:
            alias = self.app_ref.variables.alias_by_tag_dict[dyn_widget_ref.var_tag]
            tag = self.app_ref.variables.tag_by_alias_dict[alias]
        except:
            pass
        if dyn_widget_ref.var_alias in self.app_ref.variables.var_aliases:
            dyn_widget_ref.var_tag = tag  # get tag just in case the alias moved to another variable
        else:
            if tag != dyn_widget_ref.var_tag:
                dyn_widget_ref.var_alias = dyn_widget_ref.var_tag  # the tag has changed, and the alias doesn't exist anymore, so default back to tag
            else:
                dyn_widget_ref.var_alias = dyn_widget_ref.app_ref.variables.alias_by_tag_dict[dyn_widget_ref.var_tag]  # tag is the same, so update with new alias
        if dyn_widget_ref.widget != 'Label':
            if dyn_widget_ref.state == 'normal':
                if dyn_widget_ref.button_off_text == '':
                    dyn_widget_ref.text = dyn_widget_ref.var_alias
                else:
                    dyn_widget_ref.text = dyn_widget_ref.button_off_text
            if dyn_widget_ref.state == 'down':
                if dyn_widget_ref.button_on_text == '':
                    dyn_widget_ref.text = dyn_widget_ref.var_alias
                else:
                    dyn_widget_ref.text = dyn_widget_ref.button_on_text
        else:
            dyn_widget_ref.text = dyn_widget_ref.button_on_text

    def add_widget_json(self):
        id_list = []
        new_json = {}
        for id, dyn_widget in self.dyn_widget_dict.items():
            id_list.append(int(id))
        new_id = str(max(id_list) + 1)  #make new id one greater than largest id
        #create default widget parameters
        new_json['on_text'] = ''
        new_json['off_text'] = ''
        new_json['var_tag'] = ''
        new_json['var_alias'] = ''
        new_json['widget'] = 'Toggle Button'
        new_json['invert'] = False
        new_json['size'] = (170, 160)
        new_json['pos'] = (320, 160)
        self.dyn_layout_json.update({new_id: new_json})
        self.create_dyn_widget(new_id)
        self.update_widget(new_id)
        self.save_layout()
        self.end_modify()
        self.modify_screen()
        self.app_ref.main_screen_ref.item_edit_popup.edit_popup(self.dyn_widget_dict[new_id])

    def edit_widget_json(self, id):
        dyn_widget_ref = self.dyn_widget_dict[id]
        scatter_ref = self.scatter_dict[id]
        self.dyn_layout_json[id]['on_text'] = dyn_widget_ref.button_on_text
        self.dyn_layout_json[id]['off_text'] = dyn_widget_ref.button_off_text
        self.dyn_layout_json[id]['var_tag'] = dyn_widget_ref.var_tag
        self.dyn_layout_json[id]['var_alias'] = dyn_widget_ref.var_alias
        self.dyn_layout_json[id]['widget'] = dyn_widget_ref.widget
        self.dyn_layout_json[id]['invert'] = dyn_widget_ref.invert
        self.dyn_layout_json[id]['size'] = scatter_ref.size
        self.dyn_layout_json[id]['pos'] = scatter_ref.pos

    def exchange_widget(self, id):
        self.remove_dyn_widget(id)
        self.create_dyn_widget(id)
        self.update_widget(id)
        self.edit_widget_json(id)
        self.end_modify()
        self.modify_screen()

    def delete_widget(self, id):
        self.remove_dyn_widget(id)
        del self.dyn_layout_json[id]
        del self.dyn_widget_dict[id]
        self.save_layout()

    def remove_dyn_widget(self, id):
        dyn_widget_ref = self.dyn_widget_dict[id]
        scatter_ref = self.scatter_dict[id]
        scatter_ref.remove_widget(dyn_widget_ref)
        self.app_ref.main_screen_ref.ids.main_layout.remove_widget(scatter_ref)

    def save_layout(self):
        with open(self.layout_file, 'w') as file:
            json.dump(self.dyn_layout_json, file, sort_keys=True, indent=4)

    def modify_screen(self):
        self.modify_mode = True
        for id, dyn_widget in self.dyn_widget_dict.items():
            if dyn_widget.widget == 'Label':
                dyn_widget.dyn_label_background()
            else:
                dyn_widget.background_color = 1, 1, 1, .3
                dyn_widget.background_normal = 'button_pressed.png'
                dyn_widget.background_down = 'button_pressed.png'
                self.animate(dyn_widget)

    def end_modify(self):
        self.modify_mode = False
        for id, dyn_widget in self.dyn_widget_dict.items():
            Animation.cancel_all(dyn_widget)
            if dyn_widget.widget == 'Label':
                dyn_widget.dyn_label_background()
            else:
                dyn_widget.color = 1, 1, 1, 1
                dyn_widget.background_color = 1, 1, 1, 1
                dyn_widget.background_normal = 'button.png'
                dyn_widget.background_down = 'button_pressed.png'
        self.save_layout() #save for size and position changes
        self.app_ref.variables.refresh_data = True

    def animate(self, widget):
        anim = Animation(background_color=[1, 1, 1, 0.3],  duration=1, t='linear') + Animation(
            background_color=[1, 1, 1, .5], duration=1, t='linear')
        anim.repeat = True
        anim.start(widget)

class ScreenItemEditPopup(Popup):
    app_ref = ObjectProperty(None)
    button_on_text = ObjectProperty(None)
    button_off_text = ObjectProperty(None)
    invert_check = ObjectProperty(None)
    variable_spinner = ObjectProperty(None)
    widget_spinner = ObjectProperty(None)
    item = ObjectProperty(None)
    dynamic_layout = ObjectProperty(None)
    modify_mode = BooleanProperty(False)

    def edit_popup(self, item):
        if self.modify_mode:
            self.item = item
            self.button_on_text.text = self.item.button_on_text
            self.button_off_text.text = self.item.button_off_text
            self.invert_check.active = self.item.invert
            self.variable_spinner.text = self.item.var_alias
            self.widget_spinner.text = self.item.widget
            self.open()

    def save_item(self):
        self.item.button_on_text = self.button_on_text.text
        self.item.button_off_text = self.button_off_text.text
        self.item.invert = self.invert_check.active
        self.item.var_alias = self.variable_spinner.text
        self.item.var_tag = self.app_ref.variables.tag_by_alias_dict[self.item.var_alias]  #save tag of associated alias, in case alias is changed/deleted
        if self.item.widget != self.widget_spinner.text:
            exchange = True
        else:
            exchange = False
        self.item.widget = self.widget_spinner.text
        self.dynamic_layout.update_widget(self.item.id)
        self.dynamic_layout.edit_widget_json(self.item.id)
        if exchange:  #a new type of widget has been selected, so exchange it
            self.dynamic_layout.exchange_widget(self.item.id)
        self.dynamic_layout.save_layout()
        self.dismiss()

    def delete_item(self):
        self.dynamic_layout.delete_widget(self.item.id)
        self.dismiss()

class DynItem(Widget):
    invert = BooleanProperty(True)
    var_alias = StringProperty("")
    var_tag = StringProperty("")
    widget = StringProperty("")
    button_on_text = StringProperty("")
    button_off_text = StringProperty("")
    ignition_input = NumericProperty(0)
    digital_inputs = NumericProperty(0)
    app_ref = ObjectProperty(None)
    data_change = BooleanProperty(False)

    def on_data_change(self, instance, data):
        value = self.app_ref.variables.get(self.var_alias)
        if value == '1':
            bool_state = True
        else:
            bool_state = False
        bool_state = xor(bool_state, self.invert)
        if bool_state:
            self.state = 'down'
            if self.button_on_text != '':
                self.text = self.button_on_text
            else:
                self.text = self.var_alias
        else:
            self.state = 'normal'
            if self.button_off_text != '':
                self.text = self.button_off_text
            else:
                self.text = self.var_alias

    def on_ignition_input(self, instance, state):
        if state == 0:
            self.state = 'normal'
            if self.button_off_text != '':
                self.text = self.button_off_text
            else:
                self.text = self.var_alias
            self.output_cmd()

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if self.app_ref.slide_layout.state != 'open':
                if not self.app_ref.dynamic_layout.modify_mode and self.widget != 'Label':
                    if self.widget != 'Indicator':
                        if self.var_alias != 'SYS_LOGGED_IN': #don't allow SYS_LOGGED_IN to be changed by a button
                            self._do_press()
                            self.output_cmd()
                        else:
                            self.app_ref.screen_man.current = "passcode_screen"  #open passcode screen with SYS_LOGGED_IN
                        return xor(True, self.invert)
                    else:
                        return xor(True, self.invert)
                else:
                    if touch.is_double_tap:
                        self.app_ref.main_screen_ref.item_edit_popup.edit_popup(self)
                        return False
            return False
        return super(DynItem, self).on_touch_down(touch)

    def on_touch_up(self, touch):
        if self.collide_point(*touch.pos):
            if self.app_ref.slide_layout.state != 'open':
                if not self.app_ref.dynamic_layout.modify_mode and self.widget == 'Button':
                    self._do_release()
                    self.output_cmd()
                    return True
                else:
                    if touch.is_double_tap:
                        self.app_ref.main_screen_ref.item_edit_popup.edit_popup(self)
                        return False
            return False
        return super(DynItem, self).on_touch_down(touch)

    def output_cmd(self):
        if not self.app_ref.dynamic_layout.modify_mode and self.app_ref.variables.DI_IGNITION:
            if self.state == 'normal':
                bool_state = True
            else:
                bool_state = False
            #bool_state = xor(bool_state, self.invert)
            if bool_state:
                state = '0'
            else:
                state = '1'
            self.app_ref.variables.set_by_alias(self.var_alias, state)
            self.app_ref.variables.refresh_data = True

class DynToggleButton(DynItem, ToggleButton):
    pass

class DynButton(DynItem, Button):
    pass

class DynLabel(DynItem, Label):
    def __init__(self,**kwargs):
        super (DynLabel,self).__init__(**kwargs)
        self.dyn_label_background()

    def on_data_change(self, instance, data):
        value = self.app_ref.variables.get(self.var_alias)
        self.text = self.button_on_text
        self.text = self.text.replace('%d', value)

    def on_size(self, *args):
        self.dyn_label_background()

    def dyn_label_background(self):
        self.canvas.before.clear()
        with self.canvas.before:
            if self.app_ref.dynamic_layout.modify_mode:
                Color(.298, .298, .047, .3)
            else:
                Color(0, 0, 0, 0)
            Rectangle(pos=self.pos, size=self.size)

class PasscodeScreen(Screen):
    pass

class CameraScreen(Screen):
    camera_toggle = StringProperty('0')

    def __init__(self,**kwargs):
        super (CameraScreen,self).__init__(**kwargs)
        self.capture = cv2.VideoCapture(0)
        self.my_camera = KivyCamera(capture=self.capture, fps=30)
        self.add_widget(self.my_camera)

    def on_camera_toggle(self, *args):
        if self.camera_toggle == '1':
            self.my_camera.run_camera()
        else:
            self.my_camera.pause_camera()

class MainApp(App):
    main_screen_ref = ObjectProperty(None)
    scripts = []

    def build(self):
        self.settings_cls = SettingsWithSidebar
        self.use_kivy_settings = False

        self.dynamic_layout = DynamicLayout()
        self.variables = Variables()
        self.screen_man = ScreenManagement()
        self.slide_layout = SlideLayout()
        self.slide_menu = SlideMenu()
        self.slide_layout.add_widget(self.slide_menu)
        self.slide_layout.add_widget(self.screen_man)
        self.dynamic_layout.build_layout()
        self.get_aliases()
        self.get_scripts()
        self.get_saved_vars()
        self.screen_man.current = 'main_screen' #fixes issue where screen is blank when adruino can't initially connect
        return self.slide_layout

    def build_config(self, config):
        config.setdefaults('Settings', {
            'SYS_SCREEN_BRIGHTNESS': 255,
            'SYS_SCREEN_OFF_DELAY': 1,
            'SYS_SHUTDOWN_DELAY': 60,
            'SYS_INACTIVE_TIME': 5})
        '''for key in app_settings.auto_var_tags:
            config.setdefaults('AutoVars', {key: ''})
        for key in app_settings.arduino_input_tags:
            config.setdefaults('InputAliases', {key: key})
        for key in app_settings.arduino_output_tags:
            config.setdefaults('OutputAliases', {key: key})'''

    def build_settings(self, settings):
        settings.register_type('alias', SettingAlias)
        settings.register_type('mynumeric', MySettingNumeric)
        settings.register_type('script', SettingScript)
        settings.register_type('action', SettingAction)
        settings.add_json_panel('Settings', self.config, data=app_settings.settings_json)
        settings.add_json_panel('Aliases', self.config, data=app_settings.aliases_json)
        settings.add_json_panel('Scripts', self.config, data=app_settings.scripts_json)
        settings.add_json_panel('Developer', self.config, data=app_settings.developer_json)

    def on_config_change(self, config, section, key, value):
        self.get_aliases()
        self.get_saved_vars()
        self.variables.save_variables()
        self.get_scripts()
        self.screen_man.start_inactivity_clock() #restart clock in case value has changed

    def get_scripts(self):
        self.scripts = []
        for (key, value) in self.config.items('Scripts'):
            script = value.replace("[tab]", '\t')
            script = script.replace('get([', 'self.get(("')
            script = script.replace('event([', 'self.get_event(("')
            script = script.replace(']', '")')
            script = script.replace('set([', 'self.set_by_alias(("')
            self.scripts.append(script)
            print script

    def get_saved_vars(self):
        for (key, value) in self.config.items('Settings'):
            self.variables.set_by_alias(key.upper(), value)

    #get aliases from config file, right them to variables.json, update lists, then rebuild dynamic layout in case there were any alias changes that would effect a screen item
    def get_aliases(self):
        self.config_aliases = [''] #start with one item, for the first blank variable
        for (key, value) in self.config.items('InputAliases'):
            self.config_aliases.append(value)
        for (key, value) in self.config.items('OutputAliases'):
            self.config_aliases.append(value)
        for (key, value) in self.config.items('UserVarAliases'):
            self.config_aliases.append(value)
        for (key, value) in self.config.items('TimerAliases'):
            self.config_aliases.append(value)
        for i in range(len(self.config_aliases)):
            self.variables.variables_json[i]['alias'] = self.config_aliases[i]
        self.variables.set_var_lists()
        self.variables.save_variables()

    def close_settings(self, settings=None):
        self.get_aliases()
        self.dynamic_layout.reconcile_layout()
        super(MainApp, self).close_settings(settings)

    def exit_app(self):
        self.stop()

class Variables(Widget):
    app_ref = ObjectProperty(None)
    data_change = BooleanProperty(False)
    refresh_data = BooleanProperty(False)
    display_var_tags = ListProperty()
    variables_file = 'variables.json'
    DI_IGNITION = StringProperty('0')
    SYS_REVERSE_CAM_ON = StringProperty('0')

    def __init__(self, **kwargs):
        super(Variables, self).__init__(**kwargs)
        self.open_variables()
        self.set_var_lists()
        self.variable_data = ['0'] * len(self.var_aliases)
        self.old_variable_data = ['0'] * len(self.var_aliases)
        self.var_events = [False] * len(self.var_aliases)
        self.arduino_data_len = 7 + 1
        self.arduino_data = ['0'] * self.arduino_data_len
        self.set_saved_vars()
        self.toggle_update_clock(True)
        self.set_by_alias('SYS_INIT', '1')
        self.arduino_read_dt = 0.05
        self.arduino_read_clock(self.arduino_read_dt)
        Clock.schedule_interval(self.read_system, 1)

    def set_var_lists(self):
        self.var_aliases = []
        self.var_save = []
        self.var_save_values = []
        self.var_display = []
        self.display_var_tags = [] #this is a kivy property
        self.var_ids_dict = {}
        self.var_aliases_dict = {}
        self.var_tag_dict = {}
        self.tag_by_alias_dict = {}
        self.alias_by_tag_dict = {}
        self.save_by_alias_dict = {}
        for i in range(len(self.variables_json)):
            #create variable lists
            hidden = self.variables_json[i]['hidden']
            save = self.variables_json[i]['save']
            value = self.variables_json[i]['value']
            if self.variables_json[i]['type'] == "SYS":  #if system variable, then use tag for alias
                alias = self.variables_json[i]['tag']
            else:
                alias = self.variables_json[i]['alias']
            self.var_aliases.append(alias)
            if not hidden: self.var_display.append(alias)
            if save:
                self.var_save.append(alias)
                self.var_save_values.append(value)

            # create variable dictionaries to easily find data indexes, or to reconcile variable_json
            self.var_ids_dict[self.variables_json[i]['id']] = self.variables_json[i]['data_index']  # dictionary to find data_index by id
            self.var_aliases_dict[alias] = self.variables_json[i]['data_index']  # dictionary to find data_index by alias
            self.var_tag_dict[self.variables_json[i]['tag']] = self.variables_json[i]['data_index']  # dictionary to find data_index by tag
            self.tag_by_alias_dict[self.variables_json[i]['alias']] = self.variables_json[i]['tag']  # dictionary to find tag by alias
            self.alias_by_tag_dict[self.variables_json[i]['tag']] = self.variables_json[i]['alias']  # dictionary to find alias by tag
            self.save_by_alias_dict[self.variables_json[i]['alias']] = self.variables_json[i]['save']  # dictionary to find save by alias
        self.display_var_tags = self.var_display  #this is to defer kivy property updates until the end, otherwise it slows down program for every append

    def open_variables(self):
        with open(self.variables_file, 'r') as file:
            self.variables_json = json.load(file)

    def set_saved_vars(self):
        # set variables that were saved
        for i in range(len(self.var_save)):
            self.set_by_alias(self.var_save[i], self.var_save_values[i])

    def save_variables(self):
        for alias in self.var_save:
            data_index = self.var_aliases_dict[alias]
            self.variables_json[data_index]['value'] = self.variable_data[data_index]
        with open(self.variables_file, 'w') as file:
            json.dump(self.variables_json, file, sort_keys=True, indent=4)

    def read_arduino(self, dt):
        try:
            serial_data = self.ser.readline().rstrip().split(',')
            if len(serial_data) == self.arduino_data_len:
                self.arduino_data = serial_data
        except Exception as e:
            print('read_arduino error:')
            print(e)
            self.connect_arduino()

    def connect_arduino(self):
        try:
            self.ser.close()
        except:
            pass
        try:
            if operating_sys == 'Linux':
                self.ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=0)
            else:
                self.ser = serial.Serial('COM5', 115200, timeout=0)
            self.arduino_read_clock(self.arduino_read_dt)
        except Exception as e:
            print('connect_arduino error:')
            print(e)
            self.arduino_read_clock(1) #try to reconnect only every second to reduce cpu usage

    def arduino_read_clock(self, dt):
        try:
            self.arduino_clk.cancel()
        except:
            pass
        self.arduino_clk = Clock.schedule_interval(self.read_arduino, dt)

    def read_system(self, dt):
        self.set_by_alias('SYS_TIME', str((current_milli_time() - initial_time) / 1000))
        self.set_by_alias('SYS_CPU_USAGE', str(psutil.cpu_percent()))
        self.set_by_alias('SYS_CPU_TEMP', os.popen('vcgencmd measure_temp').readline().replace("temp=", "").replace("'C\n", ""))

    def update_data(self, dt):
        for i in range(0, 7):
            self.variable_data[i+1] = self.arduino_data[i]
        if (self.variable_data != self.old_variable_data) or self.refresh_data:
            self.data_change = True
            print('variable data')
            print(self.variable_data)
            self.refresh_data = False
        else:
            self.data_change = False

        for i in range(len(self.variable_data)):
            if self.variable_data[i] != self.old_variable_data[i]:
                self.var_events[i] = True
            else:
                self.var_events[i] = False

        self.old_variable_data = list(self.variable_data)  # 'list()' must be used, otherwise it only copies a reference to the original list

        #variable driven events
        self.SYS_REVERSE_CAM_ON = self.variable_data[22]

        self.DI_IGNITION = self.variable_data[7]  #need to update last due to screen initialization issue

        self.exec_scripts()

        if self.get('SYS_INIT') == '1':  #turn SYS_INIT right back off, so it should only have been on for for loop cycle
            print 'init off'
            self.set_by_alias('SYS_INIT', '0')

    def exec_scripts(self):
        if self.data_change:
            for script in self.app_ref.scripts:
                if script != '':
                    try:
                        exec(script)
                    except Exception as e:
                        print('script error:')
                        print(e)

    def toggle_update_clock(self, state):
        if state:
            self.read_clock = Clock.schedule_interval(self.update_data, 0)
        else:
            try:
                self.read_clock.cancel()
            except:
                pass

    def get(self, alias):
        if alias != '':
            try:
                data_index = self.var_aliases_dict[alias]
                return self.variable_data[data_index]
            except Exception as e:
                print('variables.get error:')
                print(e)
                return ''
        return ''

    def get_event(self, alias):
        if alias != '':
            try:
                data_index = self.var_aliases_dict[alias]
                return self.var_events[data_index]
            except:
                print('variables.get_event: tag not found')
                return ''
        return ''

    def write_arduino(self, command):
        self.ser.write(command)

    def set_by_alias(self, alias, value):
        data_index = self.var_aliases_dict[alias]
        self.set(data_index, value)
        if self.save_by_alias_dict[alias]: #if variable's 'save' parameter is set to true, then save it
            self.save_variables()
            print('saved vars')

    def set(self, index, value):
        try:
            self.variable_data[index] = value
            channel_type = self.variables_json[index]['type']
            tag = self.variables_json[index]['tag']
            if channel_type == 'DO':
                self.write_arduino('digital_output/' + str(tag) + '/' + str(value) + '/')
            if channel_type == 'SYS':
                self.sys_cmd(tag, value)
        except Exception as e:
            print('variables.set error:')
            print(e)

    #SYSTEM COMMANDS#

    def sys_cmd(self, tag, value):
        if tag == 'SYS_DIM_BACKLIGHT':
            if value == '1':
                self.backlight_brightness(int(self.get('SYS_SCREEN_BRIGHTNESS'))) #need to use "get" to get around initialization issue
            else:
                self.backlight_brightness(255)
        if tag == 'SYS_SCREEN_BRIGHTNESS':
            if self.get('SYS_DIM_BACKLIGHT') == "1":
                self.backlight_brightness(int(value))
        if tag == 'SYS_ENG_KILL_POPUP':
            if value == '1':
                self.app_ref.main_screen_ref.engine_kill_popup.open()
                self.set_by_alias(tag, '0')
        if tag == 'SYS_CLOSE_APP':
            if value == '1':
                self.set_by_alias(tag, '0')
                exit()
        if tag == 'SYS_REBOOT':
            if value == '1':
                os.system("reboot")
                self.set_by_alias(tag, '0')
        if tag == 'SYS_SHUTDOWN':
            if value == '1':
                os.system("poweroff")
                self.set_by_alias(tag, '0')

    def backlight_brightness(self, value):
        print('brightness cmd')
        print(value)
        try:
            if int(value) > 0 and int(value) < 256:
                print('brightness written')
                _brightness = open(os.path.join(BASE, "brightness"), "w")
                _brightness.write(str(value))
                _brightness.close()
                return
        except Exception as e:
            print('Tried changing RPi backlight brightness:')
            print(e)


###SETTINGS STUFF###

class SettingAlias(SettingString):
    def _create_popup(self, instance):
        # create popup layout
        content = BoxLayout(orientation='vertical', spacing='5dp')
        popup_width = min(0.95 * Window.width, dp(500))
        self.popup = popup = Popup(
            title=self.title, content=content, size_hint=(None, None),
            size=(popup_width, '250dp'), pos_hint={'middle': 1, 'top': 1})
        # create the textinput used for numeric input
        self.textinput = textinput = TextInput(
            text=self.value, font_size='24sp', multiline=False,
            size_hint_y=None, height='42sp')
        textinput.bind(on_text_validate=self._validate)
        self.textinput = textinput

        # construct the content, widget are used as a spacer
        content.add_widget(Widget())
        content.add_widget(textinput)
        content.add_widget(Widget())
        content.add_widget(SettingSpacer())

        # 2 buttons are created for accept or cancel the current value
        btnlayout = BoxLayout(size_hint_y=None, height='50dp', spacing='5dp')
        btn = Button(text='Ok')
        btn.bind(on_release=self._validate)
        btnlayout.add_widget(btn)
        btn = Button(text='Cancel')
        btn.bind(on_release=self._dismiss)
        btnlayout.add_widget(btn)
        content.add_widget(btnlayout)

        # all done, open the popup !
        popup.open()

    def _validate(self, instance):
        self._dismiss()
        value = self.textinput.text.strip()
        # if text input (alias) is left blank, use tag
        if value == '':
            self.value = self.title
        else:
            self.value = value

class SettingScript(SettingString):
    app_ref = ObjectProperty(None)

    def _create_popup(self, instance):
        # create popup layout
        content = BoxLayout(orientation='vertical', spacing='5dp')
        popup_width = min(0.95 * Window.width, dp(500))
        self.popup = popup = Popup(
            title=self.title, content=content, size_hint=(None, None),
            size=(popup_width, '275dp'), pos_hint={'middle': 1, 'top': 1})
        # create the textinput used for numeric input
        self.textinput = textinput = TextInput(
            text=self.value.replace("[tab]", '\t'), font_size='18sp', multiline=True,
            size_hint_y=None, height='110sp')
        textinput.bind(on_text_validate=self._validate)
        self.textinput = textinput
        self.spinner = Spinner(id='script_var_spinner',
                    size_hint=(.75, 1),
                    option_cls=Factory.get("SpinnerLabel"),
                    font_size='13sp',
                    text='DI_0',
                    values=self.app_ref.variables.display_var_tags,
                    size_hint_y=None, height='30sp',
                    size_hint_x=0.5)
        self.insert_button = Button(text='Insert', size_hint_x=0.5)
        self.insert_button.bind(on_release=self.insert_var)
        self.box_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height='35dp', spacing='5dp')
        self.box_layout.add_widget(self.spinner)
        self.box_layout.add_widget(self.insert_button)

        # construct the content, widget are used as a spacer
        content.add_widget(self.box_layout)
        content.add_widget(textinput)
        #content.add_widget(SettingSpacer())

        # 2 buttons are created for accept or cancel the current value
        btnlayout = BoxLayout(size_hint_y=None, height='50dp', spacing='5dp')
        btn = Button(text='Ok')
        btn.bind(on_release=self._validate)
        btnlayout.add_widget(btn)
        btn = Button(text='Cancel')
        btn.bind(on_release=self._dismiss)
        btnlayout.add_widget(btn)
        content.add_widget(btnlayout)

        # all done, open the popup !
        popup.open()

    def insert_var(self, instance):
        alias = '[' + self.spinner.text + ']'
        self.textinput.insert_text(alias)
        self.textinput.focus = True

    def _validate(self, instance):
        self._dismiss()
        value = self.textinput.text.strip()
        self.value = value
        self.value = self.value.replace('\t', "[tab]")

class MySettingNumeric(SettingNumeric):
    def _create_popup(self, instance):
        # create popup layout
        content = BoxLayout(orientation='vertical', spacing='5dp')
        popup_width = min(0.95 * Window.width, dp(500))
        self.popup = popup = Popup(
            title=self.title, content=content, size_hint=(None, None),
            size=(popup_width, '250dp'), pos_hint={'middle': 1, 'top': 1})
        # create the textinput used for numeric input
        self.textinput = textinput = TextInput(
            text=self.value, font_size='24sp', multiline=False,
            size_hint_y=None, height='42sp')
        textinput.bind(on_text_validate=self._validate)
        self.textinput = textinput

        # construct the content, widget are used as a spacer
        content.add_widget(Widget())
        content.add_widget(textinput)
        content.add_widget(Widget())
        content.add_widget(SettingSpacer())

        # 2 buttons are created for accept or cancel the current value
        btnlayout = BoxLayout(size_hint_y=None, height='50dp', spacing='5dp')
        btn = Button(text='Ok')
        btn.bind(on_release=self._validate)
        btnlayout.add_widget(btn)
        btn = Button(text='Cancel')
        btn.bind(on_release=self._dismiss)
        btnlayout.add_widget(btn)
        content.add_widget(btnlayout)

        # all done, open the popup !
        popup.open()

class SettingAction(SettingString):
    app_ref = ObjectProperty(None)

    def _create_popup(self, instance):
        # create popup layout
        content = BoxLayout(orientation='vertical', spacing='5dp')
        popup_width = min(0.95 * Window.width, dp(500))
        self.popup = popup = Popup(
            title=self.title, content=content, size_hint=(None, None),
            size=(popup_width, '250dp'), pos_hint={'middle': 1, 'top': 1})
        # create the textinput used for numeric input
        self.label = label = Label(
            text='Are you sure you want to ' + self.title + '?')

        # construct the content, widget are used as a spacer
        content.add_widget(Widget())
        content.add_widget(label)
        content.add_widget(Widget())
        content.add_widget(SettingSpacer())

        # 2 buttons are created for accept or cancel the current value
        btnlayout = BoxLayout(size_hint_y=None, height='50dp', spacing='5dp')
        btn = Button(text='Yes')
        btn.bind(on_release=self._validate)
        btnlayout.add_widget(btn)
        btn = Button(text='No')
        btn.bind(on_release=self._dismiss)
        btnlayout.add_widget(btn)
        content.add_widget(btnlayout)

        # all done, open the popup !
        popup.open()

    def _validate(self, instance):
        self.app_ref.variables.set_by_alias(self.key, '1')
        self._dismiss()


###SCATTER LAYOUT FOR DYN WIDGETS###

class MyScatterLayout(ScatterLayout):
    app_ref = ObjectProperty(None)
    move_lock = False
    scale_lock_left = False
    scale_lock_right = False
    scale_lock_top = False
    scale_lock_bottom = False

    def on_touch_up(self, touch):
        self.move_lock = False
        self.scale_lock_left = False
        self.scale_lock_right = False
        self.scale_lock_top = False
        self.scale_lock_bottom = False
        if touch.grab_current is self:
            touch.ungrab(self)
            x = self.pos[0] / 10
            x = round(x, 0)
            x = x * 10
            y = self.pos[1] / 10
            y = round(y, 0)
            y = y * 10
            self.pos = x, y
            self.app_ref.dynamic_layout.edit_widget_json(self.id.split('_')[0])  # update widget size/pos in json
        return super(MyScatterLayout, self).on_touch_up(touch)

    def transform_with_touch(self, touch):
        if self.app_ref.dynamic_layout.modify_mode:
            changed = False
            x = self.bbox[0][0]
            y = self.bbox[0][1]
            width = self.bbox[1][0]
            height = self.bbox[1][1]
            mid_x = x + width / 2
            mid_y = y + height / 2
            inner_width = width * 0.5
            inner_height = height * 0.5
            left = mid_x - (inner_width / 2)
            right = mid_x + (inner_width / 2)
            top = mid_y + (inner_height / 2)
            bottom = mid_y - (inner_height / 2)

                # just do a simple one finger drag
            if len(self._touches) == self.translation_touches:
                # _last_touch_pos has last pos in correct parent space,
                # just like incoming touch
                dx = (touch.x - self._last_touch_pos[touch][0]) \
                     * self.do_translation_x
                dy = (touch.y - self._last_touch_pos[touch][1]) \
                     * self.do_translation_y
                dx = dx / self.translation_touches
                dy = dy / self.translation_touches
                if (touch.x > left and touch.x < right and touch.y < top and touch.y > bottom or self.move_lock)\
                        and not self.scale_lock_left and not self.scale_lock_right and not self.scale_lock_top and not self.scale_lock_bottom:
                    self.move_lock = True
                    self.apply_transform(Matrix().translate(dx, dy, 0))
                    changed = True

            change_x = touch.x - self.prev_x
            change_y = touch.y - self.prev_y
            anchor_sign = 1
            sign = 1
            if abs(change_x) >= 9 and not self.move_lock and not self.scale_lock_top and not self.scale_lock_bottom:
                if change_x < 0:
                    sign = -1
                if (touch.x < left or self.scale_lock_left) and not self.scale_lock_right:
                    self.scale_lock_left = True
                    self.pos = (self.pos[0] + (sign * 10), self.pos[1])
                    anchor_sign = -1
                elif (touch.x > right or self.scale_lock_right) and not self.scale_lock_left:
                    self.scale_lock_right = True
                self.size[0] = self.size[0] + (sign * anchor_sign * 10)
                self.prev_x = touch.x
                changed = True
            if abs(change_y) >= 9 and not self.move_lock and not self.scale_lock_left and not self.scale_lock_right:
                if change_y < 0:
                    sign = -1
                if (touch.y > top or self.scale_lock_top) and not self.scale_lock_bottom:
                    self.scale_lock_top = True
                elif (touch.y < bottom or self.scale_lock_bottom) and not self.scale_lock_top:
                    self.scale_lock_bottom = True
                    self.pos = (self.pos[0], self.pos[1] + (sign * 10))
                    anchor_sign = -1
                self.size[1] = self.size[1] + (sign * anchor_sign * 10)
                self.prev_y = touch.y
                changed = True
            return changed

    def on_touch_down(self, touch):
        x, y = touch.x, touch.y
        self.prev_x = touch.x
        self.prev_y = touch.y
        # if the touch isnt on the widget we do nothing
        if not self.do_collide_after_children:
            if not self.collide_point(x, y):
                return False

        # let the child widgets handle the event if they want
        touch.push()
        touch.apply_transform_2d(self.to_local)
        if super(Scatter, self).on_touch_down(touch):
            # ensure children don't have to do it themselves
            if 'multitouch_sim' in touch.profile:
                touch.multitouch_sim = True
            touch.pop()
            self._bring_to_front(touch)
            return True
        touch.pop()

        # if our child didn't do anything, and if we don't have any active
        # interaction control, then don't accept the touch.
        if not self.do_translation_x and \
                not self.do_translation_y and \
                not self.do_rotation and \
                not self.do_scale:
            return False

        if self.do_collide_after_children:
            if not self.collide_point(x, y):
                return False

        if 'multitouch_sim' in touch.profile:
            touch.multitouch_sim = True
        # grab the touch so we get all it later move events for sure
        self._bring_to_front(touch)
        touch.grab(self)
        self._touches.append(touch)
        self._last_touch_pos[touch] = touch.pos

        return True

if __name__ == '__main__':

    #turn on status output for shutdown circuit
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(17, GPIO.OUT)
        GPIO.output(17, 1)
    except Exception as e:
        print('GPIO error:')
        print(e)

    MainApp().run()

    print('closed')
