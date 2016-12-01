import kivy
kivy.require('1.0.6') # replace with your current kivy version !

from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.popup import Popup
from kivy.uix.image import Image
from kivy.uix.slider import Slider
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.uix.accordion import Accordion, AccordionItem
from kivy.config import Config
from kivy.uix.camera import Camera
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.core.window import Window

Window.size = (800, 480)

import serial
#ser = serial.Serial('/dev/serial/by-path/platform-3f980000.usb-usb-0:1.5:1.0-port0', 115200)
ser = serial.Serial('/dev/ttyUSB0', 115200)
import subprocess

import os
BASE = "/sys/class/backlight/rpi_backlight/"

global digitalInputInd
digitalInputInd = [Button()]*7
global digitalOutputBtn
digitalOutputBtn = [Button()]*6
prev_bkp_state = 0
prev_backlight_state = 0
password = '1234'
password_try = ''
logged_in = 0

cam = Camera(resolution=(800, 480))

# Define some helper functions:

# This callback will be bound to the LED toggle and Beep button:
def press_callback(obj):
    if obj.state == "down":
        print ("button on")
        ser.write(obj.id + '1/')
    else:
        print ("button off")
        ser.write(obj.id + '0/')

def login_callback(obj):
    global password
    global password_try
    global logged_in
    password_try = password_try + obj.text
    if len(password_try) == 4:
        if password_try == password:
            sm.current = 'main_screen'
            logged_in = 1
        else:
            login_fail_popup.open()
        password_try = ''

#close app when exit button is pushed
def exit_callback(obj):
    App.get_running_app().stop()

# This is called when the slider is updated:
def update_speed(obj, value):
    global speed
    print("Updating speed to:" + str(obj.value))
    speed = obj.value
    brightness(int(obj.value))

def brightness(value):
    if value > 0 and value < 256:
        _brightness = open(os.path.join(BASE,"brightness"), "w")
        _brightness.write(str(value))
        _brightness.close()
        return
    raise TypeError("Brightness should be between 0 and 255")

# Modify the Button Class to update according to GPIO input:
def update_digital_inputs(dt):
    serial_data = ser.readline().rstrip()
    digitalInputs = 0
    try:
        digitalInputs = int(serial_data)
    except ValueError:
        print('value error')
    for i in range(0,7):
        mask = 1 << i
        state = digitalInputs & mask
        state = state >> i
        if state == 1:
            digitalInputInd[i].state = 'down'
        else:
            digitalInputInd[i].state = 'normal'
        if i == 0:
            bkp_camera(state)
        if i == 6:
            backlight(state)
    
def bkp_camera(state):
    global prev_bkp_state
    global logged_in
    if prev_bkp_state == 0 and state == 1:
        cam.play = True
        sm.current = 'camera_screen'
    if prev_bkp_state == 1 and state == 0:
        cam.play = False
        if logged_in == 1:
            sm.current = 'main_screen'
        else:
            sm.current = 'login_screen'
    prev_bkp_state = state

def backlight(state):
    global prev_backlight_state
    global logged_in
    if (prev_backlight_state == 0 and state == 1) or (prev_backlight_state == 1 and state == 0):
        if state == 1:
            state_str = '0'
        else:
            state_str = '1'
            sm.current = 'login_screen'
            logged_in = 0
        _power = open(os.path.join(BASE,"bl_power"), "w")
        _power.write(state_str)
        _power.close()
    prev_backlight_state = state

class MainScreen(Screen):

    def __init__(self,**kwargs):
        super (MainScreen,self).__init__(**kwargs)
        
        # Set up the layout:	
        main_layout = BoxLayout(orientation='horizontal')
        di_layout = BoxLayout(orientation='vertical', spacing=5, padding=5, size_hint_x=None, width=200)
        do_layout = GridLayout(cols=3, rows=3, spacing=5, padding=5, size_hint_x=None, width=475)
        settings_layout = RelativeLayout(size_hint_x=None, width=125)

        main_layout.add_widget(di_layout)
        main_layout.add_widget(do_layout)
        main_layout.add_widget(settings_layout)

        # Make the background gray:
        with main_layout.canvas.before:
            Color(.2,.2,.2,1)
            #self.rect = Rectangle(size=(800,480), pos=main_layout.pos)

        # Instantiate the first UI object (the GPIO input indicator):
        for i in range(0,6):
            digitalInputInd[i] = Button(text="Input_" + str(i))

        # Schedule the update of the state of the GPIO input button:
        event = Clock.schedule_interval(update_digital_inputs, 0.01)

        # Create the rest of the UI objects (and bind them to callbacks, if necessary):
        for i in range(0,6):
            digitalOutputBtn[i] = ToggleButton(text="Output_" + str(i), id="digital/" + str(i) + "/", size=(153.33, 153.33), size_hint=(None, None))
            digitalOutputBtn[i].bind(on_press=press_callback)
        speedSlider = Slider(orientation='vertical', min=20, max=200, value=200, pos=(0, 90), size_hint_y=None, height=300)
        speedSlider.bind(on_touch_down=update_speed, on_touch_move=update_speed)
        exitBtn = Button(text="X", size=(20, 20), size_hint=(None, None), pos=(105, 0))
        exitBtn.bind(on_press=exit_callback)

        # Add the UI elements to the layout:
        for i in range(0,6):
            di_layout.add_widget(digitalInputInd[i])
        for i in range(0,6):
            do_layout.add_widget(digitalOutputBtn[i])
        settings_layout.add_widget(speedSlider)
        settings_layout.add_widget(exitBtn)

        self.add_widget(main_layout)  

class LoginScreen(Screen):
    def __init__(self,**kwargs):
        super (LoginScreen,self).__init__(**kwargs)

        loginBtn = [Button()]*10
        
        login_layout = GridLayout(cols=3, rows=4, spacing=5, padding=5, size_hint_x=None, width=400, pos=(200, 0))

        for i in range(0,10):
            loginBtn[i] = Button(text=str(i))
            loginBtn[i].bind(on_press=login_callback)

        for i in range(1,10):
            login_layout.add_widget(loginBtn[i])
        login_layout.add_widget(loginBtn[0])    

        self.add_widget(login_layout)

class CameraScreen(Screen):
    def __init__(self,**kwargs):
        super (CameraScreen,self).__init__(**kwargs)
        camera_layout = FloatLayout(orientation='horizontal')
        camera_layout.add_widget(cam)
        self.add_widget(camera_layout)

sm = ScreenManager(transition=NoTransition())
login_screen = LoginScreen(name='login_screen')
main_screen = MainScreen(name='main_screen')
camera_screen = CameraScreen(name='camera_screen')
sm.add_widget(login_screen)
sm.add_widget(main_screen)
sm.add_widget(camera_screen)

login_fail_content = RelativeLayout()
login_fail_button = Button(text='Try Again', size_hint=(None, None), size=(120, 120), pos=(28,8))
login_fail_content.add_widget(login_fail_button)
login_fail_popup = Popup(title='Invalid Passcode', content=login_fail_content, size_hint=(None, None), size=(200, 200))
login_fail_button.bind(on_press=login_fail_popup.dismiss)

class MyApp(App):

    def build(self):
        return sm

if __name__ == '__main__':
	MyApp().run()
