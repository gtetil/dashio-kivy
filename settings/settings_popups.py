from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.properties import StringProperty, NumericProperty, ObjectProperty, BooleanProperty, ListProperty
from kivy.uix.popup import Popup
from kivy.core.window import Window
from kivy.uix.settings import SettingsWithSidebar, SettingString, SettingNumeric, SettingSpacer, SettingPath
from kivy.metrics import dp
from kivy.factory import Factory
from kivy.uix.filechooser import FileChooserListView
from kivy.utils import get_color_from_hex, get_hex_from_color
from modules.color_picker import MyColorPicker
from modules.data_viewer import DataViewer
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.clock import Clock
from . import app_settings
import os
import csv
import socket

class SettingColorPicker(SettingString):
    app_ref = ObjectProperty(None)

    def _create_popup(self, instance):
        # create popup layout
        content = BoxLayout(orientation='vertical', spacing=5)
        self.color_popup = popup = Popup(
            title=self.title, content=content, size_hint=(None,None), size=(400,480), pos_hint={'middle': 1, 'center': 1})
        # create the textinput used for numeric input.
        self.color_picker = MyColorPicker(current_color=self.value,
                                          prev_sel_color = self.app_ref.variables.get('SYS_COLOR_HISTORY'))

        # construct the content, widget are used as a spacer
        content.add_widget(self.color_picker)

        # 2 buttons are created for accept or cancel the current value
        btnlayout = BoxLayout(size_hint_y=None, height='50dp')
        btn = Button(text='Ok')
        btn.bind(on_release=self._warning_popup)
        btnlayout.add_widget(btn)
        btn = Button(text='Cancel')
        btn.bind(on_release=popup.dismiss)
        btnlayout.add_widget(btn)
        content.add_widget(btnlayout)

        # all done, open the popup !
        popup.open()

    def _warning_popup(self, instance):
        if self.key != 'SYS_SCREEN_BACKGROUND_COLOR':
            # create popup layout
            content = BoxLayout(orientation='vertical')
            popup_width = min(0.95 * Window.width, dp(500))
            self.warning_popup = popup = Popup(
                title=self.title, content=content, size_hint=(None, None),
            size=(popup_width, '250dp'), pos_hint={'middle': 1, 'center': 1})
            # create the textinput used for numeric input
            self.label = Label(text='This action will affect ALL widgets.  Is that ok?')

            # construct the content, widget are used as a spacer
            content.add_widget(Widget())
            content.add_widget(self.label)
            content.add_widget(Widget())
            content.add_widget(SettingSpacer())

            # 2 buttons are created for accept or cancel the current value
            btnlayout = BoxLayout(size_hint_y=None, height='50dp', spacing='5dp')
            btn = Button(text='Yes')
            btn.bind(on_release=self._validate)
            btnlayout.add_widget(btn)
            btn = Button(text='Cancel')
            btn.bind(on_release=self._dismiss_warning)
            btnlayout.add_widget(btn)
            content.add_widget(btnlayout)

            # all done, open the popup !
            popup.open()
        else:
            self._validate(instance)

    def _dismiss_warning(self, instance):
        try:
            self.warning_popup.dismiss()
        except:
            pass
        self.color_popup.dismiss()

    def _validate(self, instance):
        self._dismiss_warning(instance)
        self.value = self.color_picker.current_color
        self.app_ref.variables.set_by_alias('SYS_COLOR_HISTORY', self.value, defer_save=True)
        self.app_ref.dynamic_layout.global_modify(self.key)


class SettingAlias(SettingString):
    def _create_popup(self, instance):
        # create popup layout
        content = BoxLayout(orientation='vertical', spacing='5dp')
        popup_width = min(0.95 * Window.width, dp(500))
        self.popup = popup = Popup(
            title=self.title, content=content, size_hint=(None, None),
            size=(popup_width, '250dp'), pos_hint={'middle': 1, 'top': 1})
        # create the textinput used for numeric input
        self.textinput = textinput = TextInput(
            text=self.value, font_size='24sp', multiline=False,
            size_hint_y=None, height='42sp')
        textinput.bind(on_text_validate=self._validate)
        self.textinput = textinput

        # construct the content, widget are used as a spacer
        content.add_widget(Widget())
        content.add_widget(textinput)
        content.add_widget(Widget())
        content.add_widget(SettingSpacer())

        # 2 buttons are created for accept or cancel the current value
        btnlayout = BoxLayout(size_hint_y=None, height='50dp', spacing='5dp')
        btn = Button(text='Ok')
        btn.bind(on_release=self._validate)
        btnlayout.add_widget(btn)
        btn = Button(text='Cancel')
        btn.bind(on_release=self._dismiss)
        btnlayout.add_widget(btn)
        content.add_widget(btnlayout)

        # all done, open the popup !
        popup.open()

    def _validate(self, instance):
        self._dismiss()
        value = self.textinput.text.strip()
        # if text input (alias) is left blank, use tag
        if value == '':
            self.value = self.title
        else:
            self.value = value

class SettingScript(SettingString):
    app_ref = ObjectProperty(None)

    def _create_popup(self, instance):
        # create popup layout
        content = BoxLayout(orientation='vertical', spacing='5dp')
        popup_width = min(0.95 * Window.width, dp(500))
        self.popup = popup = Popup(
            title=self.title, content=content, size_hint=(None, None),
            size=(popup_width, '275dp'), pos_hint={'middle': 1, 'top': 1})
        # create the textinput used for numeric input
        self.textinput = textinput = TextInput(
            text=self.value.replace("[tab]", '\t'), font_size='18sp', multiline=True,
            size_hint_y=None, height='110sp')
        textinput.bind(on_text_validate=self._validate)
        self.textinput = textinput
        self.spinner = Spinner(id='script_var_spinner',
                    size_hint=(.75, 1),
                    option_cls=Factory.get("SpinnerLabel"),
                    font_size='13sp',
                    text='DI_0',
                    values=self.app_ref.variables.display_var_tags,
                    size_hint_y=None, height='30sp',
                    size_hint_x=0.5)
        self.insert_button = Button(text='Insert', size_hint_x=0.5)
        self.insert_button.bind(on_release=self.insert_var)
        self.box_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height='35dp', spacing='5dp')
        self.box_layout.add_widget(self.spinner)
        self.box_layout.add_widget(self.insert_button)

        # construct the content, widget are used as a spacer
        content.add_widget(self.box_layout)
        content.add_widget(textinput)
        #content.add_widget(SettingSpacer())

        # 2 buttons are created for accept or cancel the current value
        btnlayout = BoxLayout(size_hint_y=None, height='50dp', spacing='5dp')
        btn = Button(text='Ok')
        btn.bind(on_release=self._validate)
        btnlayout.add_widget(btn)
        btn = Button(text='Cancel')
        btn.bind(on_release=self._dismiss)
        btnlayout.add_widget(btn)
        content.add_widget(btnlayout)

        # all done, open the popup !
        popup.open()

    def insert_var(self, instance):
        alias = '[' + self.spinner.text + ']'
        self.textinput.insert_text(alias)
        self.textinput.focus = True

    def _validate(self, instance):
        self._dismiss()
        value = self.textinput.text.strip()
        self.value = value
        self.value = self.value.replace('\t', "[tab]")

class MySettingPath(SettingPath):
    app_ref = ObjectProperty(None)

    def _create_popup(self, instance):
        # create popup layout
        content = BoxLayout(orientation='vertical', spacing=5)
        popup_width = min(0.95 * Window.width, dp(500))
        self.popup = popup = Popup(
            title=self.title, content=content, size_hint=(None, 0.9),
            width=popup_width)

        # create the filechooser
        initial_path = self.value or os.getcwd()
        self.textinput = textinput = FileChooserListView(
            path=app_settings.layout_dir, size_hint=(1, 1),
            dirselect=self.dirselect, show_hidden=self.show_hidden, filters=['*.json'])
        textinput.bind(on_path=self._validate)

        # construct the content
        content.add_widget(textinput)
        content.add_widget(SettingSpacer())

        # 2 buttons are created for accept or cancel the current value
        btnlayout = BoxLayout(size_hint_y=None, height='50dp', spacing='5dp')
        btn = Button(text='Ok')
        btn.bind(on_release=self._validate)
        btnlayout.add_widget(btn)
        btn = Button(text='Cancel')
        btn.bind(on_release=self._dismiss)
        btnlayout.add_widget(btn)
        content.add_widget(btnlayout)

        # all done, open the popup !
        popup.open()

    def _validate(self, instance):
        self._dismiss()
        value = self.textinput.selection

        if not value:
            return

        self.value = os.path.realpath(value[0])
        self.value = os.path.split(self.value)[1]

        self.app_ref.variables.set_by_alias(self.key, self.value)

class MySettingNumeric(SettingNumeric):
    app_ref = ObjectProperty(None)

    def _create_popup(self, instance):
        # create popup layout
        content = BoxLayout(orientation='vertical', spacing='5dp')
        popup_width = min(0.95 * Window.width, dp(500))
        self.popup = popup = Popup(
            title=self.title, content=content, size_hint=(None, None),
            size=(popup_width, '250dp'), pos_hint={'middle': 1, 'top': 1})
        # create the textinput used for numeric input
        self.textinput = textinput = TextInput(
            text=self.value, font_size='24sp', multiline=False,
            size_hint_y=None, height='42sp')
        textinput.bind(on_text_validate=self._validate)
        self.textinput = textinput

        # construct the content, widget are used as a spacer
        content.add_widget(Widget())
        content.add_widget(textinput)
        content.add_widget(Widget())
        content.add_widget(SettingSpacer())

        # 2 buttons are created for accept or cancel the current value
        btnlayout = BoxLayout(size_hint_y=None, height='50dp', spacing='5dp')
        btn = Button(text='Ok')
        btn.bind(on_release=self._validate)
        btnlayout.add_widget(btn)
        btn = Button(text='Cancel')
        btn.bind(on_release=self._dismiss)
        btnlayout.add_widget(btn)
        content.add_widget(btnlayout)

        # all done, open the popup !
        popup.open()

class SettingAction(SettingString):
    app_ref = ObjectProperty(None)

    def _create_popup(self, instance):
        # create popup layout
        content = BoxLayout(orientation='vertical', spacing='5dp')
        popup_width = min(0.95 * Window.width, dp(500))
        self.popup = popup = Popup(
            title=self.title, content=content, size_hint=(None, None),
            size=(popup_width, '250dp'), pos_hint={'middle': 1, 'top': 1})
        # create the textinput used for numeric input
        self.label = label = Label(
            text='Are you sure you want to ' + self.title + '?')

        # construct the content, widget are used as a spacer
        content.add_widget(Widget())
        content.add_widget(label)
        content.add_widget(Widget())
        content.add_widget(SettingSpacer())

        # 2 buttons are created for accept or cancel the current value
        btnlayout = BoxLayout(size_hint_y=None, height='50dp', spacing='5dp')
        btn = Button(text='Yes')
        btn.bind(on_release=self._validate)
        btnlayout.add_widget(btn)
        btn = Button(text='No')
        btn.bind(on_release=self._dismiss)
        btnlayout.add_widget(btn)
        content.add_widget(btnlayout)

        # all done, open the popup !
        popup.open()

    def _validate(self, instance):
        self.app_ref.variables.set_by_alias(self.key, '1')
        self._dismiss()

class SettingCSVReader(SettingPath):
    app_ref = ObjectProperty(None)
    data_viewer = DataViewer()

    def _create_popup(self, instance):
        # create popup layout
        content = BoxLayout(orientation='vertical', spacing=5)
        popup_width = min(0.95 * Window.width, dp(500))
        self.popup = popup = Popup(
            title=self.title, content=content, size_hint=(None, 0.9),
            width=popup_width)

        # create the filechooser
        initial_path = os.path.join(os.getcwd(), app_settings.flame_log_dir)
        self.textinput = textinput = FileChooserListView(
            path=initial_path, size_hint=(1, 1),
            dirselect=False, show_hidden=self.show_hidden, filters=['*.csv'])
        #textinput.bind(on_path=self._print_csv_data)

        # construct the content
        content.add_widget(textinput)
        content.add_widget(SettingSpacer())

        # 2 buttons are created for accept or cancel the current value
        btnlayout = BoxLayout(size_hint_y=None, height='50dp', spacing='5dp')
        btn = Button(text='Open')
        btn.bind(on_release=self._csv_data_popup)
        btnlayout.add_widget(btn)
        btn = Button(text='Close')
        btn.bind(on_release=self._dismiss)
        btnlayout.add_widget(btn)
        content.add_widget(btnlayout)

        # all done, open the popup !
        popup.open()

    def _csv_data_popup(self, instance):
        value = self.textinput.selection[0]

        if not value:
            return

        # read csv file
        with open(value, 'r') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            items = [row for row in reader]
            self.data_viewer.clear()
            for i, item in reversed(list(enumerate(items[0]))):
                self.data_viewer.insert(item + ':   ' + items[1][i])

        # create popup layout
        self.csv_content = BoxLayout(orientation='vertical', spacing=5)
        popup_width = min(0.95 * Window.width, dp(500))
        self.csv_popup = Popup(
            title=value, content=self.csv_content, size_hint=(None, 0.9),
            width=popup_width)

        # construct the self.csv_content
        self.csv_content.add_widget(SettingSpacer())
        self.csv_content.add_widget(self.data_viewer)
        self.csv_content.add_widget(SettingSpacer())

        # 2 buttons are created for accept or cancel the current value
        btnlayout = BoxLayout(size_hint_y=None, height='50dp', spacing='5dp')
        btn = Button(text='Close')
        btn.bind(on_release=self._csv_dismiss)
        btnlayout.add_widget(btn)
        self.csv_content.add_widget(btnlayout)

        # all done, open the popup !
        self.csv_popup.open()

    def _csv_dismiss(self, instance):
        self.csv_popup.dismiss()
        self.csv_content.remove_widget(self.data_viewer)

class SettingViewer(SettingString):
    app_ref = ObjectProperty(None)
    data_viewer = DataViewer()

    def __init__(self, **kwargs):
        super(SettingViewer, self).__init__(**kwargs)
        self.get_data(0)  #this solves an initial refresh issue

    def get_data(self, dt):
        self.data_viewer.clear()
        for i, item in reversed(list(enumerate(self.app_ref.variables.var_aliases))):
            self.data_viewer.insert(item + ':   ' + self.app_ref.variables.variable_data[i])
        self.data_viewer.remove()  #the first element in variables is a placeholder, so remove

    def _create_popup(self, instance):
        self.data_clock = Clock.schedule_interval(self.get_data, 1)
        # create popup layout
        self.content = BoxLayout(orientation='vertical', spacing='5dp')
        popup_width = min(0.95 * Window.width, dp(500))
        self.popup = popup = Popup(
            title=self.title, content=self.content, size_hint=(None, None),
            size=(popup_width, '480dp'), pos_hint={'middle': 1, 'top': 1})

        # construct the content, widget are used as a spacer
        self.content.add_widget(SettingSpacer())
        self.content.add_widget(self.data_viewer)
        self.content.add_widget(SettingSpacer())

        # 2 buttons are created for accept or cancel the current value
        btnlayout = BoxLayout(size_hint_y=None, height='50dp', spacing='5dp')
        btn = Button(text='Close')
        btn.bind(on_release=self._dismiss)
        btnlayout.add_widget(btn)
        self.content.add_widget(btnlayout)

        # all done, open the popup !
        popup.open()

    def _dismiss(self, *largs):
        if self.textinput:
            self.textinput.focus = False
        if self.popup:
            self.popup.dismiss()
        self.popup = None
        self.data_clock.cancel()
        self.content.remove_widget(self.data_viewer)

class SettingIPAddress(SettingString):
    app_ref = ObjectProperty(None)

    def _create_popup(self, instance):
        # create popup layout
        content = BoxLayout(orientation='vertical', spacing='5dp')
        popup_width = min(0.95 * Window.width, dp(500))
        self.popup = popup = Popup(
            title=self.title, content=content, size_hint=(None, None),
            size=(popup_width, '250dp'), pos_hint={'middle': 1, 'top': 1})
        # create the textinput used for numeric input
        #f = os.popen('ifconfig eth0 | grep "inet\ addr" | cut -d: -f2 | cut -d" " -f1')
        #ip_address = f.read()
        #ip_address = '10.30.189.255'
        ip_address = get_ip_address()
        self.label = label = Label(
            text='IP Address:  ' + ip_address)

        '''f = os.popen('ifconfig wlan0 | grep "inet\ addr" | cut -d: -f2 | cut -d" " -f1')
        ip_address = f.read()
        #ip_address = '10.30.189.255'
        self.label2 = label2 = Label(
            text='WLAN:  ' + ip_address)'''

        # construct the content, widget are used as a spacer
        content.add_widget(Widget())
        content.add_widget(label)
        #content.add_widget(label2)
        content.add_widget(Widget())
        content.add_widget(SettingSpacer())

        # 2 buttons are created for accept or cancel the current value
        btnlayout = BoxLayout(size_hint_y=None, height='50dp', spacing='5dp')
        btn = Button(text='Close')
        btn.bind(on_release=self._dismiss)
        btnlayout.add_widget(btn)
        content.add_widget(btnlayout)

        # all done, open the popup !
        popup.open()

def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]
