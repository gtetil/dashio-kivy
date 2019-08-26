import os

import cv2
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.properties import StringProperty, NumericProperty, ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from engines.kivy_cv import KivyCamera
from libs.datetimepicker import DatetimePicker
from libs.navigationdrawer import NavigationDrawer

BASE = "/sys/class/backlight/rpi_backlight/"

class ScreenManagement(ScreenManager):
    passcode = ''
    passcode_try = ''
    passcode_type = StringProperty('')
    main_screen = ObjectProperty(None)
    ignition_input = NumericProperty(0)
    reverse_input = NumericProperty(0)
    app_ref = ObjectProperty(None)
    screen_background_color = StringProperty('')
    settings_file = 'settings.json'

    def __init__(self,**kwargs):
        super (ScreenManagement,self).__init__(**kwargs)
        self.transition = NoTransition()
        self.start_inactivity_clock()
        self.alarm_state = False
        self.background_color()

    def on_touch_down(self, touch):
        self.start_inactivity_clock()
        self.alarm_animation(False)  # stop alarm animation if it was running
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
        print(('rev state, ' + str(state)))
        if state == 1:
            self.current = "camera_screen"
        else:
            if self.ignition_input == 1:
                self.current = "main_screen"
            else:
                self.current = 'off_screen'

    def try_passcode(self, number):
        if self.passcode_type == 'passcode':
            self.passcode = self.app_ref.variables.get('SYS_PASSCODE')
        if self.passcode_type == 'admin':
            self.passcode = self.app_ref.variables.get('SYS_ADMIN_CODE')
        self.passcode_try = self.passcode_try + number
        if len(self.passcode_try) == len(self.passcode):
            if self.passcode_try == self.passcode:
                self.current = 'main_screen'
                if self.passcode_type == 'passcode':
                    self.app_ref.variables.set_by_alias('SYS_LOGGED_IN', '1')
                if self.passcode_type == 'admin':
                    self.admin_login(True)
            else:
                self.current_screen.ids.fail_popup.open()
                if self.passcode_type == 'passcode':
                    self.app_ref.variables.set_by_alias('SYS_LOGGED_IN', '0')
                if self.passcode_type == 'admin':
                    self.admin_login(False)
            self.passcode_try = ''

    def admin_login(self, login, toggle=True):
        if login:
            login_str = '1'
            disabled = False
            button_text = 'ADMIN LOGOUT'
            self.app_ref.slide_layout.toggle_state()
        else:
            login_str = '0'
            disabled = True
            button_text = 'ADMIN LOGIN'
            self.back_to_main(toggle)
        self.app_ref.variables.set_by_alias('SYS_ADMIN_LOGIN', login_str)
        self.app_ref.slide_menu.ids.admin_login.text = button_text
        self.app_ref.slide_menu.ids.modify_screen.disabled = disabled
        self.app_ref.slide_menu.ids.settings.disabled = disabled
        self.app_ref.slide_menu.ids.add_widget.disabled = disabled

    def admin_toggle(self):
        self.app_ref.slide_layout.toggle_state()
        if self.app_ref.variables.get('SYS_ADMIN_LOGIN') == '1':
            self.admin_login(False)
        else:
            self.passcode_type = 'admin'
            self.current = "passcode_screen"

    def back_to_main(self, toggle):
        self.current = 'main_screen'
        if toggle:
            self.app_ref.slide_layout.toggle_state()
        if self.app_ref.dynamic_layout.modify_mode:
            self.app_ref.dynamic_layout.end_modify()
            self.app_ref.variables.toggle_update_clock(True)

    def alarm_animation(self, state):
        anim = Animation(opacity=0, duration=.5) + Animation(
            opacity=1, duration=.5)
        if state:
            anim.repeat = True
            anim.start(self.main_screen.ids.alarm_indicator)
        else:
            anim.cancel_all(self.main_screen.ids.alarm_indicator)
            self.main_screen.ids.alarm_indicator.opacity = 0
        self.alarm_state = state

    def background_color(self):
        self.screen_background_color = self.app_ref.variables.get('SYS_SCREEN_BACKGROUND_COLOR')

class MainScreen(Screen):
    app_ref = ObjectProperty(None)

    def __init__(self,**kwargs):
        super (MainScreen,self).__init__(**kwargs)
        self.label = ScreenEditLabel()

    def screen_edit_label(self, state):
        if state:
            self.add_widget(self.label)
        else:
            self.remove_widget(self.label)

class PasscodeScreen(Screen):
    app_ref = ObjectProperty(None)

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

class SlideLayout(NavigationDrawer):
    pass

class SlideMenu(BoxLayout):
    pass

class ScreenEditLabel(Button):
    pass

class DateTimePicker(DatetimePicker):
    pass