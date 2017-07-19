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
from kivy.properties import StringProperty, NumericProperty, ObjectProperty, BooleanProperty, ListProperty
from kivy.uix.camera import Camera
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.uix.popup import Popup
from kivy.core.window import Window
from kivy.animation import Animation
from navigationdrawer import NavigationDrawer
from kivy.uix.settings import SettingsWithSidebar, SettingString, SettingNumeric, SettingSpacer
from kivy.metrics import dp
from kivy.uix.scatterlayout import ScatterLayout
from kivy.uix.scatter import Scatter
from kivy.graphics.transformation import Matrix
import app_settings

import json
from functools import partial
import autoVar

Window.size = (800,480)

import serial
import os
import time
import re
from operator import xor
BASE = "/sys/class/backlight/rpi_backlight/"

debug_mode = True
pc_mode = True
win_mode = False
#!!!CHECK CAMERA RESOLUTION BEFORE UPLOADING TO PI!!!!

try:
    import RPi.GPIO as GPIO
except:
    pass

current_milli_time = lambda: int(round(time.time() * 1000))

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
            self.screen_off_event = Clock.schedule_once(self.delayed_screen_off, int(self.app_ref.variables.SYS_SCREEN_OFF_DELAY))
            self.shutdown_event = Clock.schedule_once(self.delayed_shutdown, float(self.app_ref.variables.SYS_SHUTDOWN_DELAY)*60)

    def delayed_screen_off(self, dt):
        self.current = 'off_screen'
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

#class SettingsScreen(Screen):
    #pass

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

    def main_screen_ref(self, main_screen):
        self.main_layout = main_screen.ids.main_layout
        self.item_edit_popup = main_screen.ids.item_edit_popup

    def save_layout(self):
        json_data = []
        for scatter_layout in self.main_layout.children:
            dyn_widget = scatter_layout.children[0].children[0]
            data = {}
            data['id'] = dyn_widget.id
            data['label'] = dyn_widget.label
            data['toggle'] = dyn_widget.toggle
            data['var_tag'] = dyn_widget.var_tag
            data['var_alias'] = dyn_widget.var_alias
            data['enable'] = dyn_widget.enable
            data['invert'] = dyn_widget.invert
            data['pos'] = scatter_layout.pos
            data['size'] = scatter_layout.size
            json_data.append(data)
        with open(self.layout_file, 'w') as file:
            json.dump(json_data, file, sort_keys=True, indent=4)

    def build_layout(self):
        self.main_layout.clear_widgets()
        with open(self.layout_file, 'r') as file:
            self.dyn_layout_json = json.load(file)
        for i in range(len(self.dyn_layout_json)):
            id = self.dyn_layout_json[i]['id']
            size = self.dyn_layout_json[i]['size']
            pos = self.dyn_layout_json[i]['pos']
            label = self.dyn_layout_json[i]['label']
            toggle = self.dyn_layout_json[i]['toggle']
            self.var_tag = self.dyn_layout_json[i]['var_tag']
            self.var_alias = self.dyn_layout_json[i]['var_alias']
            enable = self.dyn_layout_json[i]['enable']
            invert = self.dyn_layout_json[i]['invert']

            try:
                alias = self.app_ref.variables.alias_by_tag_dict[self.var_tag]
                tag = self.app_ref.variables.tag_by_alias_dict[alias]
            except:
                pass
            if self.var_alias in self.app_ref.variables.var_aliases:
                self.var_tag = tag  # get tag just in case the alias moved to another variable
            else:
                if tag != self.var_tag:
                    self.var_alias = self.var_tag  #the tag has changed, and the alias doesn't exist anymore, so default back to tag
                else:
                    self.var_alias = self.app_ref.variables.alias_by_tag_dict[self.var_tag]  #tag is the same, so update with new alias

            if label == '':
                item_label = self.var_alias
            else:
                item_label = label
            if toggle:
                dyn_widget = DynToggleButton(text=item_label, id=str(id))
            else:
                dyn_widget = DynButton(text=item_label, id=str(id))
            scatter_layout = MyScatterLayout(id=str(id) + '_scatter', do_rotation=False, size=(size[0], size[1]), size_hint=(None, None), pos=pos)
            dyn_widget.set_properties(self, self.var_alias, self.var_tag, enable, self.item_edit_popup, invert, label)
            scatter_layout.add_widget(dyn_widget)
            self.main_layout.add_widget(scatter_layout)
        self.app_ref.variables.refresh_data = True
        if self.modify_mode:
            self.modify_screen()

    def modify_screen(self):
        self.modify_mode = True
        for scatter_layout in self.main_layout.children:
            self.animate(scatter_layout.children[0].children[0])

    def end_modify(self):
        self.modify_mode = False
        for scatter_layout in self.main_layout.children:
            dyn_widget = scatter_layout.children[0].children[0]
            Animation.cancel_all(dyn_widget)
            dyn_widget.background_color = 1, 1, 1, 1
        self.save_layout() #save for size and position changes

    def animate(self, widget):
        anim = Animation(background_color=[1, 1, 0, 0.75], duration=1, t='linear') + Animation(
            background_color=[1, 1, 1, 1], duration=1, t='linear')
        anim.repeat = True
        anim.start(widget)

class ScreenItemEditPopup(Popup):
    app_ref = ObjectProperty(None)
    label_input = ObjectProperty(None)
    toggle_check = ObjectProperty(None)
    enable_check = ObjectProperty(None)
    invert_check = ObjectProperty(None)
    variable_spinner = ObjectProperty(None)
    toggle_layout = ObjectProperty(None)
    item = ObjectProperty(None)
    dynamic_layout = ObjectProperty(None)
    modify_mode = BooleanProperty(False)

    def edit_popup(self, instance, item, dyn_widget):
        if self.modify_mode:
            self.item = item
            self.label_input.text = self.item.label
            self.toggle_check.active = self.item.toggle
            self.enable_check.active = self.item.enable
            self.invert_check.active = self.item.invert
            self.variable_spinner.text = self.item.var_alias
            self.toggle_layout.disabled = dyn_widget
            self.open()

    def save_item(self):
        self.item.label = self.label_input.text
        self.item.toggle = self.toggle_check.active
        self.item.enable = self.enable_check.active
        self.item.invert = self.invert_check.active
        self.item.var_alias = self.variable_spinner.text
        self.item.var_tag = self.app_ref.variables.tag_by_alias_dict[self.item.var_alias]  #save tag of associated alias, in case alias is changed/deleted
        self.dynamic_layout.save_layout()
        self.dynamic_layout.build_layout()
        self.dismiss()

class DynItem(Widget):
    dynamic_layout = ObjectProperty(None)
    toggle = BooleanProperty(True)
    enable = BooleanProperty(True)
    invert = BooleanProperty(True)
    var_alias = StringProperty("")
    var_tag = StringProperty("")
    label = StringProperty("")
    ignition_input = NumericProperty(0)
    digital_inputs = NumericProperty(0)
    app_ref = ObjectProperty(None)
    data_change = BooleanProperty(False)

    def on_data_change(self, instance, value):
        state = self.app_ref.variables.get(self.var_alias)
        if state == '1':
            bool_state = True
        else:
            bool_state = False
        bool_state = xor(bool_state, self.invert)
        if bool_state:
            self.state = 'down'
        else:
            self.state = 'normal'

    def set_properties(self, ref, var_alias, var_tag, enable, item_edit_popup, invert, label):
        self.dynamic_layout = ref
        self.var_alias = str(var_alias)
        self.var_tag = str(var_tag)
        self.label = str(label)
        self.enable = enable
        self.invert = invert
        self.item_edit_popup = item_edit_popup
        ChangeItemBackground(self)

    def on_ignition_input(self, instance, state):
        if state == 0:
            self.state = 'normal'
            self.output_cmd()

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if self.app_ref.slide_layout.state != 'open':
                if not self.dynamic_layout.modify_mode:
                    if self.enable:
                        if self.var_alias != 'SYS_LOGGED_IN': #don't allow SYS_LOGGED_IN to be change by a button
                            self._do_press()
                            self.output_cmd()
                        return xor(True, self.invert)
                    else:
                        return xor(False, self.invert)
                else:
                    if touch.is_double_tap:
                        self.item_edit_popup.edit_popup(self.item_edit_popup, self, False)
                        return False
            return False
        return super(DynItem, self).on_touch_down(touch)

    def on_touch_up(self, touch):
        if self.collide_point(*touch.pos):
            if self.app_ref.slide_layout.state != 'open':
                if not self.dynamic_layout.modify_mode and not self.toggle:
                    if self.enable:
                        if self.var_alias != 'SYS_LOGGED_IN':  # don't allow SYS_LOGGED_IN to be change by a button
                            self._do_release()
                            self.output_cmd()
                        return True
                    else:
                        return False
                else:
                    if touch.is_double_tap:
                        self.item_edit_popup.edit_popup(self.item_edit_popup, self, False)
                        return False
            return False
        return super(DynItem, self).on_touch_down(touch)

    def output_cmd(self):
        if not self.dynamic_layout.modify_mode and self.enable and self.app_ref.variables.DI_IGNITION:
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
        self.settings_cls = SettingsWithSidebar
        self.use_kivy_settings = False

        self.dynamic_layout = DynamicLayout()
        self.variables = Variables()
        self.screen_man = ScreenManagement()
        self.slide_layout = SlideLayout()
        self.slide_menu = SlideMenu()
        self.slide_layout.add_widget(self.slide_menu)
        self.slide_layout.add_widget(self.screen_man)
        self.get_aliases()
        return self.slide_layout

    def build_config(self, config):
        config.setdefaults('Settings', {
            'SYS_SCREEN_BRIGHTNESS': 255,
            'SYS_SCREEN_OFF_DELAY': 1,
            'SYS_SHUTDOWN_DELAY': 60})
        '''for key in app_settings.auto_var_tags:
            config.setdefaults('AutoVars', {key: ''})
        for key in app_settings.arduino_input_tags:
            config.setdefaults('InputAliases', {key: key})
        for key in app_settings.arduino_output_tags:
            config.setdefaults('OutputAliases', {key: key})'''

    def build_settings(self, settings):
        settings.register_type('alias', SettingAlias)
        settings.register_type('mynumeric', MySettingNumeric)
        settings.register_type('calc', SettingCalc)
        settings.add_json_panel('Settings', self.config, data=app_settings.settings_json)
        settings.add_json_panel('Aliases', self.config, data=app_settings.aliases_json)
        settings.add_json_panel('CalcVars', self.config, data=app_settings.calcvars_json)

    def on_config_change(self, config, section, key, value):
        self.get_saved_vars()
        self.variables.save_variables()

    def get_saved_vars(self):
        for (key, value) in self.config.items('Settings'):
            self.variables.set(self.variables.var_aliases_dict[key.upper()], value)

    #get aliases from config file, right them to variables.json, update lists, then rebuild dynamic layout in case there were any alias changes that would effect a screen item
    def get_aliases(self):
        self.config_aliases = [''] #start with one item, for the first blank variable
        for (key, value) in self.config.items('InputAliases'):
            self.config_aliases.append(value)
        for (key, value) in self.config.items('OutputAliases'):
            self.config_aliases.append(value)
        for i in range(len(self.config_aliases)):
            self.variables.variables_json[i]['alias'] = self.config_aliases[i]
        self.variables.set_var_lists()
        self.variables.save_variables()
        self.dynamic_layout.build_layout()
        self.dynamic_layout.save_layout()

    def close_settings(self, settings=None):
        print('settings closed')
        self.get_aliases()
        super(MainApp, self).close_settings(settings)

    def exit_app(self):
        self.stop()

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

class SettingCalc(SettingAlias):
    pass

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

class Variables(Widget):
    app_ref = ObjectProperty(None)
    data_change = BooleanProperty(False)
    refresh_data = BooleanProperty(False)
    display_var_tags = ListProperty()
    variables_file = 'variables.json'
    prev_autovar_state_1 = '0'
    prev_autovar_state_2 = '0'
    prev_autovar_state_3 = '0'
    prev_autovar_state_4 = '0'
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
    SYS_LOGGED_IN = StringProperty('0')
    SYS_PASSCODE_PROMPT = StringProperty('0')
    SYS_REVERSE_CAM_ON = StringProperty('0')
    SYS_DIM_BACKLIGHT = StringProperty('0')
    SYS_SCREEN_BRIGHTNESS = StringProperty('0')
    SYS_SCREEN_OFF_DELAY = StringProperty('0')
    SYS_SHUTDOWN_DELAY = StringProperty('0')
    AUTOVAR_OPERATOR_1 = StringProperty('')
    AUTOVAR_OPERATOR_2_1 = StringProperty('')
    AUTOVAR_GET_VAR_1 = StringProperty('')
    AUTOVAR_GET_VAR_2_1 = StringProperty('')
    AUTOVAR_SET_VAR_1 = StringProperty('')
    AUTOVAR_OPERATOR_2 = StringProperty('')
    AUTOVAR_OPERATOR_2_2 = StringProperty('')
    AUTOVAR_GET_VAR_2 = StringProperty('')
    AUTOVAR_GET_VAR_2_2 = StringProperty('')
    AUTOVAR_SET_VAR_2 = StringProperty('')
    AUTOVAR_OPERATOR_3 = StringProperty('')
    AUTOVAR_OPERATOR_2_3 = StringProperty('')
    AUTOVAR_GET_VAR_3 = StringProperty('')
    AUTOVAR_GET_VAR_2_3 = StringProperty('')
    AUTOVAR_SET_VAR_3 = StringProperty('')
    AUTOVAR_OPERATOR_4 = StringProperty('')
    AUTOVAR_OPERATOR_2_4 = StringProperty('')
    AUTOVAR_GET_VAR_4 = StringProperty('')
    AUTOVAR_GET_VAR_2_4 = StringProperty('')
    AUTOVAR_SET_VAR_4 = StringProperty('')

    def __init__(self, **kwargs):
        super(Variables, self).__init__(**kwargs)
        self.open_variables()
        self.set_var_lists()
        self.variable_data = ['0'] * len(self.var_aliases)
        self.old_variable_data = ['0'] * len(self.var_aliases)
        self.arduino_data_len = 7 + 1
        self.arduino_data = ['0'] * self.arduino_data_len
        self.set_saved_vars()
        self.toggle_update_clock(True)
        Clock.schedule_interval(self.read_arduino, 0.05)

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
        if not debug_mode:
            try:
                #time = current_milli_time()
                serial_data = ser.readline().rstrip().split(',')
                if len(serial_data) == self.arduino_data_len:
                    self.arduino_data = serial_data
                #print(current_milli_time() - time)
            except:
                print('Serial Read Failure, or possibly some other failure')
                exit()
        else:
            pass

    def update_data(self, dt):
        for i in range(0, 7):
            self.variable_data[i+1] = self.arduino_data[i]
        if (self.variable_data != self.old_variable_data) or self.refresh_data:
            self.data_change = True
            print('variable data')
            print(self.variable_data)
            if self.variable_data[14:41] <> self.old_variable_data[14:41]:
                self.save_variables()
                print('saved vars')
            self.refresh_data = False
        else:
            self.data_change = False
        self.old_variable_data = list(self.variable_data)  # 'list()' must be used, otherwise it only copies a reference to the original list

        #skip index zero for blank selection
        self.DI_0 = self.variable_data[1]
        self.DI_1 = self.variable_data[2]
        self.DI_2 = self.variable_data[3]
        self.DI_3 = self.variable_data[4]
        self.DI_4 = self.variable_data[5]
        self.DI_5 = self.variable_data[6]

        self.DO_0 = self.variable_data[8]
        self.DO_1 = self.variable_data[9]
        self.DO_2 = self.variable_data[10]
        self.DO_3 = self.variable_data[11]
        self.DO_4 = self.variable_data[12]
        self.DO_5 = self.variable_data[13]
        self.SYS_LOGGED_IN = self.variable_data[14]
        self.SYS_PASSCODE_PROMPT = self.variable_data[15]
        self.SYS_REVERSE_CAM_ON = self.variable_data[16]
        self.SYS_SCREEN_BRIGHTNESS = self.variable_data[17]
        self.SYS_DIM_BACKLIGHT = self.variable_data[18]
        self.SYS_SCREEN_OFF_DELAY = self.variable_data[19]
        self.SYS_SHUTDOWN_DELAY = self.variable_data[20]
        '''self.AUTOVAR_OPERATOR_1 = self.variable_data[21]
        self.AUTOVAR_OPERATOR_2_1 = self.variable_data[22]
        self.AUTOVAR_GET_VAR_1 = self.variable_data[23]
        self.AUTOVAR_GET_VAR_2_1 = self.variable_data[24]
        self.AUTOVAR_SET_VAR_1 = self.variable_data[25]
        self.AUTOVAR_OPERATOR_2 = self.variable_data[26]
        self.AUTOVAR_OPERATOR_2_2 = self.variable_data[27]
        self.AUTOVAR_GET_VAR_2 = self.variable_data[28]
        self.AUTOVAR_GET_VAR_2_2 = self.variable_data[29]
        self.AUTOVAR_SET_VAR_2 = self.variable_data[30]
        self.AUTOVAR_OPERATOR_3 = self.variable_data[31]
        self.AUTOVAR_OPERATOR_2_3 = self.variable_data[32]
        self.AUTOVAR_GET_VAR_3 = self.variable_data[33]
        self.AUTOVAR_GET_VAR_2_3 = self.variable_data[34]
        self.AUTOVAR_SET_VAR_3 = self.variable_data[35]
        self.AUTOVAR_OPERATOR_4 = self.variable_data[36]
        self.AUTOVAR_OPERATOR_2_4 = self.variable_data[37]
        self.AUTOVAR_GET_VAR_4 = self.variable_data[38]
        self.AUTOVAR_GET_VAR_2_4 = self.variable_data[39]
        self.AUTOVAR_SET_VAR_4 = self.variable_data[40]'''

        if not debug_mode:
            self.DI_IGNITION = self.variable_data[7]  #need to update last due to screen initialization issue
        else:
            self.DI_IGNITION = '1'

        self.scan_auto_vars()

    def eval_auto_var(self, op, op2, get, get2, set, prev_state):
        if op != '':
            if (op == 'if' and self.get(get) == '1') or (op == 'if not' and self.get(get) == '0'):
                if op2 == '' or op2 == 'or' or op2 == 'or not':
                    state = '1'
                elif (op2 == 'and' and self.get(get2) == '1') or (op2 == 'and not' and self.get(get2) == '0'):
                    state = '1'
                else:
                    state = '0'
            else:
                if op2 == '':
                    state = '0'
                elif (op2 == 'or' and self.get(get2) == '1') or (op2 == 'or not' and self.get(get2) == '0'):
                    state = '1'
                else:
                    state = '0'
            if prev_state != state:
                self.set_by_alias(set, state)
            return state
    
    def scan_auto_vars(self):
        if self.data_change:
            self.prev_autovar_state_1 = self.eval_auto_var(self.AUTOVAR_OPERATOR_1, self.AUTOVAR_OPERATOR_2_1, self.AUTOVAR_GET_VAR_1, self.AUTOVAR_GET_VAR_2_1, self.AUTOVAR_SET_VAR_1, self.prev_autovar_state_1)
            self.prev_autovar_state_2 = self.eval_auto_var(self.AUTOVAR_OPERATOR_2, self.AUTOVAR_OPERATOR_2_2, self.AUTOVAR_GET_VAR_2, self.AUTOVAR_GET_VAR_2_2, self.AUTOVAR_SET_VAR_2, self.prev_autovar_state_2)
            self.prev_autovar_state_3 = self.eval_auto_var(self.AUTOVAR_OPERATOR_3, self.AUTOVAR_OPERATOR_2_3, self.AUTOVAR_GET_VAR_3, self.AUTOVAR_GET_VAR_2_3, self.AUTOVAR_SET_VAR_3, self.prev_autovar_state_3)
            self.prev_autovar_state_4 = self.eval_auto_var(self.AUTOVAR_OPERATOR_4, self.AUTOVAR_OPERATOR_2_4, self.AUTOVAR_GET_VAR_4, self.AUTOVAR_GET_VAR_2_4, self.AUTOVAR_SET_VAR_4, self.prev_autovar_state_4)

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
            #try:
            data_index = self.var_aliases_dict[alias]
            return self.variable_data[data_index]
            #except:
                #print('variables.get: tag not found')
                #return ''
        return ''

    def write_arduino(self, command):
        ser.write(command)
        #time.sleep(.1)

    def set_by_alias(self, alias, value):
        data_index = self.var_aliases_dict[alias]
        self.set(data_index, value)

    '''def set_by_tag(self, tag, value):
        data_index = self.var_tag_dict[tag]
        self.set(data_index, value)'''

    def set(self, index, value):
        try:
            self.variable_data[index] = value
            channel_type = self.variables_json[index]['type']
            tag = self.variables_json[index]['tag']
            if channel_type == 'DO':
                if not debug_mode:
                    self.write_arduino('digital_output/' + tag + '/' + value + '/')
            if channel_type == 'SYS':
                #if tag == 'SYS_DIM_BACKLIGHT':
                self.sys_cmd(tag, int(value))
        except:
            print('variable.set: tag not found')

    #SYSTEM COMMANDS#

    def sys_cmd(self, tag, value):
        if tag == 'SYS_DIM_BACKLIGHT':
            if value == 1:
                self.backlight_brightness(int(self.get('SYS_SCREEN_BRIGHTNESS'))) #need to use "get" to get around initialization issue
            else:
                self.backlight_brightness(255)
        if tag == 'SYS_SCREEN_BRIGHTNESS':
            if self.SYS_DIM_BACKLIGHT == "1":
                self.backlight_brightness(value)
        if tag == 'SYS_PASSCODE_PROMPT':
            if value == 1:
                self.app_ref.screen_man.current = "passcode_screen"
                self.set_by_alias(tag, '0')

    def backlight_brightness(self, value):
        print('brightness cmd')
        print(value)
        if not pc_mode:
            if int(value) > 0 and int(value) < 256:
                print('brightness written')
                _brightness = open(os.path.join(BASE, "brightness"), "w")
                _brightness.write(str(value))
                _brightness.close()
                return
            #raise TypeError("Brightness should be between 0 and 255")

class MyScatterLayout(ScatterLayout):
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
        return super(MyScatterLayout, self).on_touch_up(touch)

    def transform_with_touch(self, touch):
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
            if (touch.x > left and touch.x < right and touch.y < top and touch.y > bottom or self.move_lock) and not self.scale_lock_left and not self.scale_lock_right and not self.scale_lock_top and not self.scale_lock_bottom:
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

    if not debug_mode:
        try:
            if not win_mode:
                ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=0)
            else:
                ser = serial.Serial('COM6', 115200, timeout=0)
        except:
            print "Failed to connect"
            exit()

        #turn on status output for shutdown circuit
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(17, GPIO.OUT)
        GPIO.output(17, 1)

    MainApp().run()

    ser.close()
    print('closed')
