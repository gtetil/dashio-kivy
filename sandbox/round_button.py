# -*- coding: utf-8 -*-
from kivy.app import App
from kivy.lang import Builder
from kivymd.theming import ThemeManager
from kivy.properties import StringProperty

main_widget_kv = '''
#:import MDThemePicker kivymd.theme_picker.MDThemePicker
#:import get_color_from_hex kivy.utils.get_color_from_hex

        
BoxLayout:
    orientation: 'vertical'
    
    MDFloatingActionButton:
        id:                    float_act_btn
        icon:                'plus-circle'
        opposite_colors:    True
        elevation_normal:    8
        pos_hint:            {'center_x': 0.5, 'center_y': 0.1}
        md_bg_color: get_color_from_hex(colors['Green']['600'])
        background_palette: 'Green'
        background_hue: '600'
        
    MDFloatingActionButton:
        id:                    float_act_btn
        icon:                'pencil'
        opposite_colors:    True
        elevation_normal:    8
        pos_hint:            {'center_x': 0.5, 'center_y': 0.1}
        md_bg_color: get_color_from_hex(colors['Red']['500'])
        background_palette: 'Red'
        background_hue: '500'
        
    MDRaisedButton:
        text: "MDRaisedButton"
        elevation_normal: 2
        opposite_colors: True
        pos_hint: {'center_x': 0.5, 'center_y': 0.4}
        size: 100,100
        md_bg_color: get_color_from_hex(colors['Grey']['500'])
        background_palette: 'Grey'
        background_hue: '500'
        

'''




class KitchenSink(App):
    theme_cls = ThemeManager()

    def build(self):
        main_widget = Builder.load_string(main_widget_kv)
        return main_widget

if __name__ == '__main__':
    KitchenSink().run()
