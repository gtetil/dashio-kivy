from kivy.uix.togglebutton import ToggleButton
from kivy.properties import NumericProperty, StringProperty, ObjectProperty

from kivy.factory import Factory
from kivy.lang import Builder

Builder.load_string("""
<DIIndicator>:
    font_size: '20sp'
    digital_inputs: app.arduino.digital_inputs

""")

class DIIndicator(ToggleButton):
    index = NumericProperty(0)
    digital_inputs = NumericProperty(0)
    state = StringProperty('normal')

    def on_digital_inputs(self, instance, di_byte):
        mask = 1 << self.index
        state = di_byte & mask
        state = state >> self.index
        if state == 1:
            self.state = 'down'
        else:
            self.state = 'normal'

Factory.register('KivyB', module='DIIndicator')