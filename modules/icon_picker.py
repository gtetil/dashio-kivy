from random import sample
from string import ascii_lowercase

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from settings.icon_definitions import md_icons
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.label import Label
from kivy.properties import BooleanProperty, ObjectProperty, StringProperty
from kivy.uix.recyclegridlayout import RecycleGridLayout
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.uix.recycleview.layout import RecycleLayoutManagerBehavior
from kivy.uix.recycleview import RecycleView

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
        text: u"{}".format(md_icons[root.value]) if not '' else ''
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
    padding: 5
    spacing: 5
    orientation: 'vertical'
    rv: rv
    rv_layout: rv_layout
    icon: 'no-selection'
    
    RecycleView:
        id: rv
        rv_layout: rv_layout
        scroll_type: ['bars', 'content']
        scroll_wheel_distance: dp(114)
        bar_width: dp(10)
        viewclass: 'SelectableIcon'
        
        SelectableRecycleGridLayout:
            id: rv_layout
            keyboard_mode: 'managed'
            default_size: None, dp(120)
            default_size_hint: 1, None
            size_hint_y: None
            height: self.minimum_height
            orientation: 'vertical'
            cols: 8
            spacing: dp(2)
            key_selection: 'selectable'
''')

class SelectableRecycleGridLayout(FocusBehavior, LayoutSelectionBehavior,
                                RecycleGridLayout):
    ''' Adds selection and focus behaviour to the view. '''

class SelectableIcon(RecycleDataViewBehavior, BoxLayout):
    ''' Add selection support to the Label '''
    index = None
    selected = BooleanProperty(False)
    selectable = BooleanProperty(True)

    def refresh_view_attrs(self, rv, index, data):
        ''' Catch and handle the view changes '''
        self.index = index
        return super(SelectableIcon, self).refresh_view_attrs(
            rv, index, data)

    def on_touch_down(self, touch):
        ''' Add selection on touch down '''
        if super(SelectableIcon, self).on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos) and self.selectable:
            return self.parent.select_with_touch(self.index, touch)

    def apply_selection(self, rv, index, is_selected):
        ''' Respond to the selection of items in the view. '''
        self.selected = is_selected
        if is_selected:
            rv.parent.icon = rv.data[index]['value']

class IconPicker(BoxLayout):
    icon = StringProperty('')
    sorted_icons = []
    current_index = None

    def __init__(self,**kwargs):
        super(IconPicker, self).__init__(**kwargs)

    def populate_list(self):
        self.sorted_icons = sorted(md_icons)
        reversed_icons = self.sorted_icons[::-1]
        for key in reversed_icons:
            self.insert(key)

    def select_icon(self, icon):
        self.current_index = self.sorted_icons.index(icon)
        self.rv_layout.select_node(self.current_index)
        self.rv.scroll_y = 1.005 - (self.current_index / float(len(self.sorted_icons)))  # not subracting from '1' in order to align better

    def insert(self, value):
        self.rv.data.insert(0, {'value': value or 'default value', 'selectable': True})

class IconPickerApp(App):
    def build(self):
        icon_picker = IconPicker()
        icon_picker.select_icon('beats')
        return icon_picker

if __name__ == '__main__':
    IconPickerApp().run()
