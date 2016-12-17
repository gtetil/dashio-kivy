from kivy.uix.togglebutton import ToggleButton
from kivy.properties import NumericProperty, StringProperty, ObjectProperty

from kivy.factory import Factory
from kivy.lang import Builder

Builder.load_string("""
<DOToggle>:
    font_size: '20sp'
    size_hint: None, None
    size: 153.33, 153.33
    on_press: app.arduino.set('digital/' + str(self.index) + '/', self.state)

""")

class DOToggle(ToggleButton):
    index = NumericProperty(0)

Factory.register('KivyB', module='DOToggle')