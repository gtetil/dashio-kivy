import kivy
kivy.require('1.9.1') # replace with your current kivy version !

from kivy.config import Config
Config.set('kivy', 'keyboard_mode', 'systemanddock')
Config.set('graphics', 'maxfps', '100')
Config.set('postproc', 'double_tap_distance', '100')

from kivy.app import App
from kivy.properties import ObjectProperty
from kivy.core.window import Window
from kivy.uix.settings import SettingsWithSidebar
from modules.variables import Variables
from settings.settings_popups import SettingColorPicker, SettingAlias, SettingScript, MySettingPath, MySettingNumeric, SettingAction, SettingCSVReader
from modules.dynamic_layout import DynamicLayout
from modules.screens import ScreenManagement, SlideLayout, SlideMenu
import settings.app_settings as app_settings
import json
import time

Window.size = (800,480)

try:
    import RPi.GPIO as GPIO
except:
    pass

current_milli_time = lambda: int(round(time.time() * 1000))
initial_time = current_milli_time()

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
            'SYS_INACTIVE_TIME': 5,
            'SYS_SCREEN_BACKGROUND_COLOR': '#ffffffff',
            'SYS_WIDGET_BACKGROUND_OFF_COLOR': '#ffffffff',
            'SYS_WIDGET_BACKGROUND_ON_COLOR': '#8fff7fff',
            'SYS_WIDGET_TEXT_OFF_COLOR': '#00000000',
            'SYS_WIDGET_TEXT_ON_COLOR': '#00000000',})
        '''for key in app_settings.auto_var_tags:
            config.setdefaults('AutoVars', {key: ''})
        for key in app_settings.arduino_input_tags:
            config.setdefaults('InputAliases', {key: key})
        for key in app_settings.arduino_output_tags:
            config.setdefaults('OutputAliases', {key: key})'''

    def build_settings(self, settings):
        settings.register_type('alias', SettingAlias)
        settings.register_type('mynumeric', MySettingNumeric)
        settings.register_type('mypath', MySettingPath)
        settings.register_type('script', SettingScript)
        settings.register_type('action', SettingAction)
        settings.register_type('color_picker', SettingColorPicker)
        settings.register_type('csv_reader', SettingCSVReader)
        settings.add_json_panel('Settings', self.config, data=app_settings.settings_json)
        aliases = []
        if self.variables.get('SYS_DIO_MODULE') == '1':
            aliases = json.loads(app_settings.dio_aliases_json)
        if self.variables.get('SYS_FLAME_DETECT') == '1':
            aliases = aliases + json.loads(app_settings.row_aliases_json)
        aliases = aliases + json.loads(app_settings.aliases_json)
        aliases = json.dumps(aliases)
        settings.add_json_panel('Aliases', self.config, data=aliases)
        settings.add_json_panel('Scripts', self.config, data=app_settings.scripts_json)
        settings.add_json_panel('Developer', self.config, data=app_settings.developer_json)

    def on_config_change(self, config, section, key, value):
        if key == 'SYS_DIO_MODULE':
            self.hide_variables(value, app_settings.dio_mod_di_data_start, app_settings.dio_mod_len)
        if key == 'SYS_FLAME_DETECT':
            self.hide_variables(value, app_settings.flame_detect_data_start, app_settings.flame_detect_len)
        #if key == "SYS_LAYOUT_FILE":
            #self.dynamic_layout.build_layout()
        self.get_aliases()
        self.get_saved_vars()
        self.variables.save_variables()
        self.get_scripts()
        self.screen_man.start_inactivity_clock() #restart clock in case value has changed

    def hide_variables(self, state, start, len):
        if state == '1':
            hidden = False
        else:
            hidden = True
        for i in range(len):
            self.variables.variables_json[start + i]['hidden'] = hidden

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
        for (key, value) in self.config.items('Accessory'):
            self.variables.set_by_alias(key.upper(), value)

    #get aliases from config file, right them to variables.json, update lists, then rebuild dynamic layout in case there were any alias changes that would effect a screen item
    def get_aliases(self):
        self.config_aliases = [''] #start with one item, for the first blank variable
        for (key, value) in self.config.items('InputAliases'):
            self.config_aliases.append(value)
        for (key, value) in self.config.items('OutputAliases'):
            self.config_aliases.append(value)
        for (key, value) in self.config.items('RowAliases'):
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
        try:
            GPIO.cleanup()
        except Exception as e:
            print e
        exit()


if __name__ == '__main__':

    MainApp().run()

    print('closed')
