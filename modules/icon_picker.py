from random import sample
from string import ascii_lowercase

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from settings.icon_definitions import md_icons
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.label import Label
from kivy.properties import BooleanProperty
from kivy.uix.recyclegridlayout import RecycleGridLayout
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior

Builder.load_string('''
#:import md_icons settings.icon_definitions.md_icons

<SelectableIcon>:
    orientation: 'vertical'
    padding: 5
    canvas.before:
        Color:
            rgba: (0.1, 0.1, 0.1, 1) if self.selected else (0.21, 0.21, 0.21, 1)
        Rectangle:
            size: self.size
            pos: self.pos
    value: 'alarm'
    Label:
        size_hint: 1, .8
        text: u"{}".format(md_icons[root.value])
        text_size: self.size
        font_size: self.size[1] / 2
        halign: 'center'
        valign: 'middle'
        font_name: 'pics/materialdesignicons-webfont.ttf'
    Label:
        text: root.value
        size_hint: 1, .2
        text_size: self.size
        font_size: self.size[1] / 2
        halign: 'center'
        valign: 'top'

<IconPicker>:
    canvas:
        Color:
            rgba: 0.3, 0.3, 0.3, 1
        Rectangle:
            size: self.size
            pos: self.pos
    rv: rv
    orientation: 'vertical'

    RecycleView:
        id: rv
        scroll_type: ['bars', 'content']
        scroll_wheel_distance: dp(114)
        bar_width: dp(10)
        viewclass: 'SelectableIcon'
        
        SelectableRecycleGridLayout:
            keyboard_mode: 'managed'
            default_size: None, dp(120)
            default_size_hint: 1, None
            size_hint_y: None
            height: self.minimum_height
            orientation: 'vertical'
            cols: 8
            spacing: dp(2)
''')

class SelectableRecycleGridLayout(FocusBehavior, LayoutSelectionBehavior,
                                RecycleGridLayout):
    ''' Adds selection and focus behaviour to the view. '''

class SelectableIcon(RecycleDataViewBehavior, BoxLayout):
    ''' Add selection support to the Label '''
    index = None
    selected = BooleanProperty(False)

    def on_touch_down(self, touch):
        if super(SelectableIcon, self).on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos):
            self.selected = True
            print self.value
            return self.parent.select_with_touch(self.index, touch)

class IconPicker(BoxLayout):

    def insert(self, value):
        self.rv.data.insert(0, {'value': value or 'default value'})

class IconPickerApp(App):
    def build(self):
        test = IconPicker()
        for key in reversed(sorted(md_icons)):
            test.insert(key)
        return test

if __name__ == '__main__':
    IconPickerApp().run()
