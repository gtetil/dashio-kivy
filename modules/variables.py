import json
import os
import platform
import time

import psutil
from kivy.clock import Clock
from kivy.properties import StringProperty, ObjectProperty, BooleanProperty, ListProperty
from kivy.uix.widget import Widget

import settings.app_settings as app_settings
from engines.can_com import CANcom
from modules.event_log import EventLog
from modules.flame_alarm import FlameAlarm

operating_sys = platform.system()
BASE = "/sys/class/backlight/rpi_backlight/"

try:
    import RPi.GPIO as GPIO
except:
    pass

class Variables(Widget):
    app_ref = ObjectProperty(None)
    data_change = BooleanProperty(False)
    refresh_data = BooleanProperty(False)
    display_var_tags = ListProperty()
    variables_file = 'settings/variables.json'
    DI_IGNITION = StringProperty('0')
    SYS_REVERSE_CAM_ON = StringProperty('0')
    SYS_DEBUG_MODE = BooleanProperty(False)

    def __init__(self, **kwargs):
        super(Variables, self).__init__(**kwargs)
        self.open_variables()
        self.set_var_lists()
        self.variable_data = ['0'] * len(self.var_aliases)
        self.old_variable_data = ['0'] * len(self.var_aliases)
        self.var_events = [False] * len(self.var_aliases)
        self.can_data = 0
        self.set_saved_vars()
        self.toggle_update_clock(True)
        self.set_by_alias('SYS_INIT', '1')
        Clock.schedule_interval(self.read_system, 1)
        self.can_com = CANcom()
        Clock.schedule_interval(self.read_can, 0.05)
        self.flame_alarms = [FlameAlarm() for i in range(app_settings.flame_detect_len)]
        self.alarm_states = [False] * app_settings.flame_detect_len
        self.alarm_counters = [0] * app_settings.flame_detect_len
        self.flame_state_ctrs = [0] * app_settings.flame_detect_len
        self.flame_log_header = [('Row ' + str(i + 1)) for i in range(0, app_settings.flame_detect_len)]
        self.flame_alarm_log = EventLog(directory=os.path.join(app_settings.flame_log_dir, 'alarm_counters'), header=self.flame_log_header)
        self.flame_state_log = EventLog(directory=os.path.join(app_settings.flame_log_dir, 'state_change_counters'), header=self.flame_log_header)
        Clock.schedule_interval(self.log_files, 1)
        self.shutdown_pin = 17
        self.ignition_pin = 27
        self.last_shutdown_state = 0
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.shutdown_pin, GPIO.OUT) # status output for shutdown circuit
            GPIO.setup(self.ignition_pin, GPIO.IN)  # setup input for ignition status
        except Exception as e:
            print('GPIO error:')
            print(e)

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

    def read_can(self, dt):
        try:
            self.can_data = self.can_com.can_read_data
        except Exception as e:
            #print('CAN read error:')
            #print(e)
            pass

    def read_system(self, dt):
        #self.set_by_alias('SYS_TIME_SEC', str((current_milli_time() - initial_time) / 1000))
        self.set_by_alias('SYS_CPU_USAGE', str(psutil.cpu_percent()))
        self.set_by_alias('SYS_CPU_TEMP', os.popen('vcgencmd measure_temp').readline().replace("temp=", "").replace("'C\n", ""))
        self.set_by_alias('SYS_TIME', str(time.time()))

        # heartbeat signal to rpi power supply
        if not self.SYS_DEBUG_MODE:
            self.set_gpio_output(self.shutdown_pin, self.last_shutdown_state)
            self.last_shutdown_state = not self.last_shutdown_state

    def log_files(self, dt):
        self.flame_alarm_log.write(self.alarm_counters)
        self.flame_state_log.write(self.flame_state_ctrs)

    def update_data(self, dt):
        if self.get('SYS_DIO_MODULE') == '1':
            for i in range(0, app_settings.dio_mod_input_len):
                di_state = (self.can_data & 2**i) >> i
                self.variable_data[i + app_settings.dio_mod_di_data_start] = str(di_state)  # update variable data array with di states
        if self.get('SYS_FLAME_DETECT') == '1':
            for i in range(0, app_settings.flame_detect_len):
                if self.SYS_DEBUG_MODE:
                    flame_state = self.get("ROW " + str(i + 1))  # this is used for debug, when CAN isn't available
                else:
                    flame_state = (self.can_data & 2**i) >> i
                self.variable_data[i+app_settings.flame_detect_data_start] = str(flame_state) # update variable data array with flame states
                self.alarm_states[i] = self.flame_alarms[i].update(bool(int(flame_state))) # get array of all flame alarm states
                self.alarm_counters[i] = self.flame_alarms[i].alarm_counter
                self.flame_state_ctrs[i] = self.flame_alarms[i].state_change_ctr
        if any(self.alarm_states) and not self.app_ref.screen_man.alarm_state:
            self.app_ref.screen_man.alarm_animation(True)  # show alarm animation
        if (self.variable_data != self.old_variable_data) or self.refresh_data:
            self.data_change = True
            #print('variable data')
            #print(self.variable_data)
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
        #self.SYS_REVERSE_CAM_ON = self.variable_data[30]  # NOT NEEDED ANYMORE?

        #old way of reading ignition status from DIO module
        #self.DI_IGNITION = self.variable_data[7]  #need to update last due to screen initialization issue

        if not self.SYS_DEBUG_MODE:
            try:
                ignition_state = GPIO.input(self.ignition_pin)
                if not ignition_state:
                    self.DI_IGNITION = '1'
                else:
                    self.DI_IGNITION = '0'
            except Exception as e:
                print('gpio error:')
                print(e)

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
                self.can_com.can_write(index - app_settings.dio_mod_do_data_start, int(value))
            if channel_type == 'SYS':
                self.sys_cmd(tag, value)
        except Exception as e:
            print('variables.set error:')
            print(e)

    def set_gpio_output(self, pin, state):
        try:
            GPIO.output(pin, state)
        except Exception as e:
            print(e)


    # SYSTEM COMMANDS#

    def sys_cmd(self, tag, value):
        if tag == 'SYS_DIM_BACKLIGHT':
            if value == '1':
                self.backlight_brightness(
                    int(self.get('SYS_SCREEN_BRIGHTNESS')))  # need to use "get" to get around initialization issue
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
                self.app_ref.exit_app()
        if tag == 'SYS_REBOOT':
            if value == '1':
                GPIO.cleanup()
                os.system("reboot")
                self.set_by_alias(tag, '0')
        if tag == 'SYS_SHUTDOWN':
            if value == '1':
                try:
                    GPIO.cleanup()
                except Exception as e:
                    print e
                os.system("poweroff")
                self.set_by_alias(tag, '0')
        if tag == 'SYS_REVERSE_CAM_ON':
            if value == '1':
                self.SYS_REVERSE_CAM_ON = '1'
            else:
                self.SYS_REVERSE_CAM_ON = '0'
        if tag == 'SYS_DEBUG_MODE':
            if value == '1':
                self.app_ref.screen_man.admin_login(False)
                self.SYS_DEBUG_MODE = True
            else:
                self.SYS_DEBUG_MODE = False

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