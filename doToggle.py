from kivy.uix.togglebutton import ToggleButton
from kivy.properties import NumericProperty, StringProperty, ObjectProperty

from kivy.factory import Factory
from kivy.lang import Builder

Builder.load_string("""
<DOToggle>:
    font_size: '20sp'
    #size_hint: None, None
    #size: 153.33, 153.33
    ignition_input: app.arduino.ignition_input
    on_press: app.arduino.set('digital/' + str(self.index) + '/', self.state)

""")

class DOToggle(ToggleButton):
    index = NumericProperty(0)
    ignition_input = NumericProperty(0)

    def on_ignition_input(self, instance, state):
        if state == 0:
            self.state = 'normal'

Factory.register('KivyB', module='DOToggle')