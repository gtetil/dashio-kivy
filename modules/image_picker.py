
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image

import glob

Builder.load_string('''
    
<ImagePicker>:
    padding: 5
    spacing: 5
    cols: 3
    
<MyImage>:
    allow_stretch: True
    keep_ratio: False

''')

class MyImage(Image):
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            print self.source

class ImagePicker(GridLayout):

    def __init__(self, **kwargs):
        super(ImagePicker, self).__init__(**kwargs)
        images = glob.glob('C:\pics\*.png')
        for img in images:
            thumb = MyImage(source=img)
            self.add_widget(thumb)

class IconPickerApp(App):
    def build(self):
        image_picker = ImagePicker()
        return image_picker

if __name__ == '__main__':
    IconPickerApp().run()
