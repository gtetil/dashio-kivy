from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.scatterlayout import ScatterLayout
from kivy.uix.scatter import Scatter
from kivy.graphics.transformation import Matrix
from kivy.properties import StringProperty, NumericProperty, ObjectProperty, BooleanProperty
from kivy.uix.popup import Popup
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.utils import get_color_from_hex, get_hex_from_color

import settings.app_settings as app_settings

import json

Window.size = (800,480)

import os
from datetime import datetime
import re
from operator import xor

class DynamicLayout(Widget):
    app_ref = ObjectProperty(None)
    modify_mode = BooleanProperty(False)
    layout_file = ''
    dyn_widget_dict = {}
    scatter_dict = {}
    tag = ''

    def build_layout(self):
        self.layout_file = os.path.join(app_settings.layout_dir, self.app_ref.variables.get('SYS_LAYOUT_FILE'))
        with open(self.layout_file, 'r') as file:
            self.dyn_layout_json = json.load(file)
        for id in self.dyn_layout_json:
            self.create_dyn_widget(id)
            self.update_widget(id)

    def reconcile_layout(self):
        for id, dyn_widget in self.dyn_widget_dict.items():
            self.update_widget(id)
            self.edit_widget_json(id)
        self.save_layout()

    def create_dyn_widget(self, id):
        widget = self.dyn_layout_json[id]['widget']
        if widget in ['Toggle Button', 'Indicator']:
            dyn_widget = DynToggleButton(text='',
                                         id=str(id),
                                         button_on_text=self.dyn_layout_json[id]['on_text'],
                                         button_off_text=self.dyn_layout_json[id]['off_text'],
                                         var_tag=self.dyn_layout_json[id]['var_tag'],
                                         var_alias=self.dyn_layout_json[id]['var_alias'],
                                         widget=widget,
                                         invert=self.dyn_layout_json[id]['invert'],
                                         color_on=self.dyn_layout_json[id]['color_on'],
                                         color_off=self.dyn_layout_json[id]['color_off'])
        elif widget == 'Button':
            dyn_widget = DynButton(text='',
                                   id=str(id),
                                   button_on_text=self.dyn_layout_json[id]['on_text'],
                                   button_off_text=self.dyn_layout_json[id]['off_text'],
                                   var_tag=self.dyn_layout_json[id]['var_tag'],
                                   var_alias=self.dyn_layout_json[id]['var_alias'],
                                   widget=widget,
                                   invert=self.dyn_layout_json[id]['invert'],
                                   color_on=self.dyn_layout_json[id]['color_on'],
                                   color_off=self.dyn_layout_json[id]['color_off'])
        else:
            dyn_widget = DynLabel(text='',
                                   id=str(id),
                                   button_on_text=self.dyn_layout_json[id]['on_text'],
                                   button_off_text=self.dyn_layout_json[id]['off_text'],
                                   var_tag=self.dyn_layout_json[id]['var_tag'],
                                   var_alias=self.dyn_layout_json[id]['var_alias'],
                                   widget=widget,
                                   invert=self.dyn_layout_json[id]['invert'],
                                   color_on=self.dyn_layout_json[id]['color_on'],
                                   color_off=self.dyn_layout_json[id]['color_off'])
        scatter_layout = MyScatterLayout(id=str(id) + '_scatter',
                                         do_rotation=False,
                                         size=(self.dyn_layout_json[id]['size'][0], self.dyn_layout_json[id]['size'][1]),
                                         size_hint=(None, None),
                                         pos=self.dyn_layout_json[id]['pos'])
        scatter_layout.add_widget(dyn_widget)
        self.app_ref.main_screen_ref.ids.main_layout.add_widget(scatter_layout)
        self.dyn_widget_dict[id] = dyn_widget
        self.scatter_dict[id] = scatter_layout

    def update_widget(self, id):
        dyn_widget_ref = self.dyn_widget_dict[id]
        try:
            alias = self.app_ref.variables.alias_by_tag_dict[dyn_widget_ref.var_tag]
            self.tag = self.app_ref.variables.tag_by_alias_dict[alias]
        except:
            pass
        if dyn_widget_ref.var_alias in self.app_ref.variables.var_aliases:
            dyn_widget_ref.var_tag = self.tag  # get tag just in case the alias moved to another variable
        else:
            if self.tag != dyn_widget_ref.var_tag:
                dyn_widget_ref.var_alias = dyn_widget_ref.var_tag  # the tag has changed, and the alias doesn't exist anymore, so default back to tag
            else:
                dyn_widget_ref.var_alias = dyn_widget_ref.app_ref.variables.alias_by_tag_dict[dyn_widget_ref.var_tag]  # tag is the same, so update with new alias
        if dyn_widget_ref.widget != 'Label':
            if dyn_widget_ref.state == 'normal':
                if dyn_widget_ref.button_off_text == '':
                    dyn_widget_ref.text = dyn_widget_ref.var_alias
                else:
                    dyn_widget_ref.text = dyn_widget_ref.button_off_text
            if dyn_widget_ref.state == 'down':
                if dyn_widget_ref.button_on_text == '':
                    dyn_widget_ref.text = dyn_widget_ref.var_alias
                else:
                    dyn_widget_ref.text = dyn_widget_ref.button_on_text
        else:
            dyn_widget_ref.text = dyn_widget_ref.button_on_text

    def add_widget_json(self):
        id_list = []
        new_json = {}
        for id, dyn_widget in self.dyn_widget_dict.items():
            id_list.append(int(id))
        new_id = str(max(id_list) + 1)  #make new id one greater than largest id
        #create default widget parameters
        new_json['on_text'] = ''
        new_json['off_text'] = ''
        new_json['var_tag'] = ''
        new_json['var_alias'] = ''
        new_json['widget'] = 'Toggle Button'
        new_json['invert'] = False
        new_json['size'] = (170, 160)
        new_json['pos'] = (320, 160)
        new_json['color_on'] = '#8fff7fff'  # green
        new_json['color_off'] = '#ffffffff' # white
        self.dyn_layout_json.update({new_id: new_json})
        self.create_dyn_widget(new_id)
        self.update_widget(new_id)
        self.save_layout()
        self.end_modify()
        self.modify_screen()
        self.app_ref.main_screen_ref.item_edit_popup.edit_popup(self.dyn_widget_dict[new_id])

    def edit_widget_json(self, id):
        dyn_widget_ref = self.dyn_widget_dict[id]
        scatter_ref = self.scatter_dict[id]
        self.dyn_layout_json[id]['on_text'] = dyn_widget_ref.button_on_text
        self.dyn_layout_json[id]['off_text'] = dyn_widget_ref.button_off_text
        self.dyn_layout_json[id]['var_tag'] = dyn_widget_ref.var_tag
        self.dyn_layout_json[id]['var_alias'] = dyn_widget_ref.var_alias
        self.dyn_layout_json[id]['widget'] = dyn_widget_ref.widget
        self.dyn_layout_json[id]['invert'] = dyn_widget_ref.invert
        self.dyn_layout_json[id]['color_on'] = dyn_widget_ref.color_on
        self.dyn_layout_json[id]['color_off'] = dyn_widget_ref.color_off
        self.dyn_layout_json[id]['size'] = scatter_ref.size
        self.dyn_layout_json[id]['pos'] = scatter_ref.pos

    def exchange_widget(self, id):
        self.remove_dyn_widget(id)
        self.create_dyn_widget(id)
        self.update_widget(id)
        self.edit_widget_json(id)
        self.end_modify()
        self.modify_screen()

    def delete_widget(self, id):
        self.remove_dyn_widget(id)
        del self.dyn_layout_json[id]
        del self.dyn_widget_dict[id]
        self.save_layout()

    def remove_dyn_widget(self, id):
        dyn_widget_ref = self.dyn_widget_dict[id]
        scatter_ref = self.scatter_dict[id]
        scatter_ref.remove_widget(dyn_widget_ref)
        self.app_ref.main_screen_ref.ids.main_layout.remove_widget(scatter_ref)

    def save_layout(self):
        with open(self.layout_file, 'w') as file:
            json.dump(self.dyn_layout_json, file, sort_keys=True, indent=4)

    def modify_screen(self):
        self.modify_mode = True
        self.app_ref.main_screen_ref.screen_edit_label(True)
        #self.app_ref.main_screen_ref.ids.screen_edit_label.text = 'Screen Edit Mode'
        for id, dyn_widget in self.dyn_widget_dict.items():
            if dyn_widget.widget == 'Label':
                dyn_widget.dyn_label_background()

    def end_modify(self):
        self.modify_mode = False
        self.app_ref.main_screen_ref.screen_edit_label(False)
        #self.app_ref.main_screen_ref.ids.screen_edit_label.text = ''
        for id, dyn_widget in self.dyn_widget_dict.items():
            if dyn_widget.widget == 'Label':
                dyn_widget.dyn_label_background()
        self.save_layout() #save for size and position changes
        self.app_ref.variables.refresh_data = True

class ScreenItemEditPopup(Popup):
    app_ref = ObjectProperty(None)
    button_on_text = ObjectProperty(None)
    button_off_text = ObjectProperty(None)
    invert_check = ObjectProperty(None)
    variable_spinner = ObjectProperty(None)
    widget_spinner = ObjectProperty(None)
    item = ObjectProperty(None)
    dynamic_layout = ObjectProperty(None)
    modify_mode = BooleanProperty(False)

    def edit_popup(self, item):
        if self.modify_mode:
            self.item = item
            self.button_on_text.text = self.item.button_on_text
            self.button_off_text.text = self.item.button_off_text
            self.invert_check.active = self.item.invert
            self.color_on_button.background_color = get_color_from_hex(self.item.color_on)
            self.color_off_button.background_color = get_color_from_hex(self.item.color_off)
            self.variable_spinner.text = self.item.var_alias
            self.widget_spinner.text = self.item.widget
            self.open()

    def save_item(self):
        self.item.button_on_text = self.button_on_text.text
        self.item.button_off_text = self.button_off_text.text
        self.item.invert = self.invert_check.active
        self.item.color_on = get_hex_from_color(self.color_on_button.background_color)
        self.item.color_off = get_hex_from_color(self.color_off_button.background_color)
        self.item.var_alias = self.variable_spinner.text
        self.item.var_tag = self.app_ref.variables.tag_by_alias_dict[self.item.var_alias]  #save tag of associated alias, in case alias is changed/deleted
        if self.item.widget != self.widget_spinner.text:
            exchange = True
        else:
            exchange = False
        self.item.widget = self.widget_spinner.text
        self.dynamic_layout.update_widget(self.item.id)
        self.dynamic_layout.edit_widget_json(self.item.id)
        if exchange:  #a new type of widget has been selected, so exchange it
            self.dynamic_layout.exchange_widget(self.item.id)
        self.dynamic_layout.save_layout()
        self.dismiss()

    def delete_item(self):
        self.dynamic_layout.delete_widget(self.item.id)
        self.dismiss()

class DynItem(Widget):
    invert = BooleanProperty(True)
    var_alias = StringProperty("")
    var_tag = StringProperty("")
    widget = StringProperty("")
    button_on_text = StringProperty("")
    button_off_text = StringProperty("")
    color_on = StringProperty("")
    color_off = StringProperty("")
    canvas_color = StringProperty("")
    ignition_input = NumericProperty(0)
    digital_inputs = NumericProperty(0)
    app_ref = ObjectProperty(None)
    data_change = BooleanProperty(False)

    def on_data_change(self, instance, data):
        value = self.app_ref.variables.get(self.var_alias)
        if value == '1':
            bool_state = True
        else:
            bool_state = False
        bool_state = xor(bool_state, self.invert)
        if bool_state:
            self.state = 'down'
            self.canvas_color = self.color_on
            if self.button_on_text != '':
                self.text = self.button_on_text
            else:
                self.text = self.var_alias
        else:
            self.state = 'normal'
            self.canvas_color = self.color_off
            if self.button_off_text != '':
                self.text = self.button_off_text
            else:
                self.text = self.var_alias

    def on_ignition_input(self, instance, state):
        if state == 0:
            self.state = 'normal'
            self.canvas_color = self.color_off
            if self.button_off_text != '':
                self.text = self.button_off_text
            else:
                self.text = self.var_alias
            self.output_cmd()

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if self.app_ref.slide_layout.state != 'open':
                if not self.app_ref.dynamic_layout.modify_mode and self.widget != 'Label':
                    if self.widget != 'Indicator':
                        if self.var_alias != 'SYS_LOGGED_IN': #don't allow SYS_LOGGED_IN to be changed by a button
                            self._do_press()
                            self.output_cmd()
                        else:
                            self.app_ref.screen_man.passcode_type = 'passcode'
                            self.app_ref.screen_man.current = "passcode_screen"  #open passcode screen with SYS_LOGGED_IN
                        return xor(True, self.invert)
                    else:
                        return xor(True, self.invert)
                else:
                    if touch.is_double_tap:
                        self.app_ref.main_screen_ref.item_edit_popup.edit_popup(self)
                        return False
            return False
        return super(DynItem, self).on_touch_down(touch)

    def on_touch_up(self, touch):
        if self.collide_point(*touch.pos):
            if self.app_ref.slide_layout.state != 'open':
                if not self.app_ref.dynamic_layout.modify_mode and self.widget == 'Button':
                    self._do_release()
                    self.output_cmd()
                    return True
                else:
                    if touch.is_double_tap:
                        self.app_ref.main_screen_ref.item_edit_popup.edit_popup(self)
                        return False
            return False
        return super(DynItem, self).on_touch_down(touch)

    def output_cmd(self):
        if not self.app_ref.dynamic_layout.modify_mode and self.app_ref.variables.DI_IGNITION:
            if self.state == 'normal':
                bool_state = True
            else:
                bool_state = False
            #bool_state = xor(bool_state, self.invert)
            if bool_state:
                state = '0'
            else:
                state = '1'
            self.app_ref.variables.set_by_alias(self.var_alias, state)
            self.app_ref.variables.refresh_data = True

class DynToggleButton(DynItem, ToggleButton):
    canvas_color = StringProperty("")

class DynButton(DynItem, Button):
    pass

class DynLabel(DynItem, Label):
    def __init__(self,**kwargs):
        super (DynLabel,self).__init__(**kwargs)
        self.dyn_label_background()

    def on_data_change(self, instance, data):
        value = self.app_ref.variables.get(self.var_alias)
        self.text = self.button_on_text
        if self.text == '%d':
            self.text = self.text.replace('%d', value)
        else:
            if self.var_alias == 'SYS_TIME':
                self.text = datetime.fromtimestamp(float(value)).strftime(self.text)

    def on_size(self, *args):
        self.dyn_label_background()

    def dyn_label_background(self):
        self.canvas.before.clear()
        with self.canvas.before:
            if self.app_ref.dynamic_layout.modify_mode:
                Color(.298, .298, .047, .3)
            else:
                Color(0, 0, 0, 0)
            Rectangle(pos=self.pos, size=self.size)

class ColorSelector(Popup):
    app_ref = ObjectProperty(None)
    widget_color = StringProperty('')
    pop_up_ref = ObjectProperty(None)
    on_select = False

    def color_open(self, pop_up_ref, on_select):
        self.pop_up_ref = pop_up_ref
        self.on_select = on_select
        if on_select:
            self.widget_color = get_hex_from_color(pop_up_ref.color_on_button.background_color)
        else:
            self.widget_color = get_hex_from_color(pop_up_ref.color_off_button.background_color)
        self.open()

    def color_save(self):
        if self.on_select:
            self.pop_up_ref.color_on_button.background_color = get_color_from_hex(self.widget_color)
        else:
            self.pop_up_ref.color_off_button.background_color = get_color_from_hex(self.widget_color)
        self.dismiss()

    def color_close(self):
        self.dismiss()

class FloatInput(TextInput):
    pat = re.compile('[^0-9]')
    def insert_text(self, substring, from_undo=False):
        pat = self.pat
        if '.' in self.text:
            s = re.sub(pat, '', substring)
        else:
            s = '.'.join([re.sub(pat, '', s) for s in substring.split('.', 1)])
        return super(FloatInput, self).insert_text(s, from_undo=from_undo)

class MyScatterLayout(ScatterLayout):
    app_ref = ObjectProperty(None)
    move_lock = False
    scale_lock_left = False
    scale_lock_right = False
    scale_lock_top = False
    scale_lock_bottom = False

    def on_touch_up(self, touch):
        self.move_lock = False
        self.scale_lock_left = False
        self.scale_lock_right = False
        self.scale_lock_top = False
        self.scale_lock_bottom = False
        if touch.grab_current is self:
            touch.ungrab(self)
            x = self.pos[0] / 10
            x = round(x, 0)
            x = x * 10
            y = self.pos[1] / 10
            y = round(y, 0)
            y = y * 10
            self.pos = x, y
            self.app_ref.dynamic_layout.edit_widget_json(self.id.split('_')[0])  # update widget size/pos in json
        return super(MyScatterLayout, self).on_touch_up(touch)

    def transform_with_touch(self, touch):
        if self.app_ref.dynamic_layout.modify_mode:
            changed = False
            x = self.bbox[0][0]
            y = self.bbox[0][1]
            width = self.bbox[1][0]
            height = self.bbox[1][1]
            mid_x = x + width / 2
            mid_y = y + height / 2
            inner_width = width * 0.5
            inner_height = height * 0.5
            left = mid_x - (inner_width / 2)
            right = mid_x + (inner_width / 2)
            top = mid_y + (inner_height / 2)
            bottom = mid_y - (inner_height / 2)

                # just do a simple one finger drag
            if len(self._touches) == self.translation_touches:
                # _last_touch_pos has last pos in correct parent space,
                # just like incoming touch
                dx = (touch.x - self._last_touch_pos[touch][0]) \
                     * self.do_translation_x
                dy = (touch.y - self._last_touch_pos[touch][1]) \
                     * self.do_translation_y
                dx = dx / self.translation_touches
                dy = dy / self.translation_touches
                if (touch.x > left and touch.x < right and touch.y < top and touch.y > bottom or self.move_lock)\
                        and not self.scale_lock_left and not self.scale_lock_right and not self.scale_lock_top and not self.scale_lock_bottom:
                    self.move_lock = True
                    self.apply_transform(Matrix().translate(dx, dy, 0))
                    changed = True

            change_x = touch.x - self.prev_x
            change_y = touch.y - self.prev_y
            anchor_sign = 1
            sign = 1
            if abs(change_x) >= 9 and not self.move_lock and not self.scale_lock_top and not self.scale_lock_bottom:
                if change_x < 0:
                    sign = -1
                if (touch.x < left or self.scale_lock_left) and not self.scale_lock_right:
                    self.scale_lock_left = True
                    self.pos = (self.pos[0] + (sign * 10), self.pos[1])
                    anchor_sign = -1
                elif (touch.x > right or self.scale_lock_right) and not self.scale_lock_left:
                    self.scale_lock_right = True
                self.size[0] = self.size[0] + (sign * anchor_sign * 10)
                self.prev_x = touch.x
                changed = True
            if abs(change_y) >= 9 and not self.move_lock and not self.scale_lock_left and not self.scale_lock_right:
                if change_y < 0:
                    sign = -1
                if (touch.y > top or self.scale_lock_top) and not self.scale_lock_bottom:
                    self.scale_lock_top = True
                elif (touch.y < bottom or self.scale_lock_bottom) and not self.scale_lock_top:
                    self.scale_lock_bottom = True
                    self.pos = (self.pos[0], self.pos[1] + (sign * 10))
                    anchor_sign = -1
                self.size[1] = self.size[1] + (sign * anchor_sign * 10)
                self.prev_y = touch.y
                changed = True
            return changed

    def on_touch_down(self, touch):
        x, y = touch.x, touch.y
        self.prev_x = touch.x
        self.prev_y = touch.y
        # if the touch isnt on the widget we do nothing
        if not self.do_collide_after_children:
            if not self.collide_point(x, y):
                return False

        # let the child widgets handle the event if they want
        touch.push()
        touch.apply_transform_2d(self.to_local)
        if super(Scatter, self).on_touch_down(touch):
            # ensure children don't have to do it themselves
            if 'multitouch_sim' in touch.profile:
                touch.multitouch_sim = True
            touch.pop()
            self._bring_to_front(touch)
            return True
        touch.pop()

        # if our child didn't do anything, and if we don't have any active
        # interaction control, then don't accept the touch.
        if not self.do_translation_x and \
                not self.do_translation_y and \
                not self.do_rotation and \
                not self.do_scale:
            return False

        if self.do_collide_after_children:
            if not self.collide_point(x, y):
                return False

        if 'multitouch_sim' in touch.profile:
            touch.multitouch_sim = True
        # grab the touch so we get all it later move events for sure
        self._bring_to_front(touch)
        touch.grab(self)
        self._touches.append(touch)
        self._last_touch_pos[touch] = touch.pos

        return True