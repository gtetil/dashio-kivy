from kivy.uix.togglebutton import ToggleButton
from kivy.properties import NumericProperty, StringProperty, ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.factory import Factory
from kivy.lang import Builder

Builder.load_string("""
<AutoVar>:
    orientation: 'horizontal'
    size_hint_y: 0.1
    spacing: 5

    Spinner:
        size_hint: .13, 1
        text: root.operator
        option_cls: Factory.get("SpinnerLabel")
        font_size: '13sp'
        values: ['', 'if', 'if not']
        on_text: app.variables.set(root.operator_text, self.text)

    Spinner:
        size_hint: .38, 1
        text: root.get_var
        option_cls: Factory.get("SpinnerLabel")
        font_size: '13sp'
        values: app.variables.display_var_tags
        on_text: app.variables.set(root.get_var_text, self.text)

    Label:
        text: 'then,'
        size_hint: .1, 1

    Spinner:
        size_hint: .38, 1
        text: root.set_var
        option_cls: Factory.get("SpinnerLabel")
        font_size: '13sp'
        values: app.variables.display_var_tags
        on_text: app.variables.set(root.set_var_text, self.text)

""")

class AutoVar(BoxLayout):
    operator = StringProperty('')
    operator_text = StringProperty('')
    get_var = StringProperty('')
    get_var_text = StringProperty('')
    set_var = StringProperty('')
    set_var_text = StringProperty('')

Factory.register('KivyB', module='AutoVar')