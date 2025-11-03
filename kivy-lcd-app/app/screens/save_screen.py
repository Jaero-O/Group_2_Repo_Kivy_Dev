from kivy.uix.screenmanager import Screen
from kivy.properties import ObjectProperty
from kivy.animation import Animation
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.behaviors import ButtonBehavior


class TreeItem(ButtonBehavior, BoxLayout):
    pass

class SaveScreen(Screen):
    selected_tree = ObjectProperty(None, rebind=True)

    def on_pre_enter(self, *args):
        self.build_tree_list()

    def build_tree_list(self):
        tree_list = self.ids.tree_list
        tree_list.clear_widgets()
        self.trees = ["Kenny Tree", "Jae Tree", "Lei Tree", "Emilay Tree"]
        for name in self.trees:
            self.add_tree_item(name)

    def add_tree_item(self, name):
        box = TreeItem(
            orientation='horizontal',
            size_hint_y=None,
            height=38,
            padding=[10, 0, 10, 0],
            on_release=lambda *_: self.select_tree(box, name)
        )

        # === Background and border setup ===
        with box.canvas.before:
            box.bg_color = Color(232 / 255, 255 / 255, 208 / 255, 1)
            box.bg_rect = RoundedRectangle(radius=[10], pos=box.pos, size=box.size)
            Color(0, 0, 0, 0.08)
            box.border_line = Line(
                rounded_rectangle=(box.x, box.y, box.width, box.height, 10),
                width=1
            )

        box.bind(
            pos=lambda _, v: (
                setattr(box.bg_rect, 'pos', v),
                setattr(box.border_line, 'rounded_rectangle', (v[0], v[1], box.width, box.height, 10))
            ),
            size=lambda _, v: (
                setattr(box.bg_rect, 'size', v),
                setattr(box.border_line, 'rounded_rectangle', (box.x, box.y, v[0], v[1], 10))
            )
        )

        label = Label(
            text=name,
            color=(56 / 255, 73 / 255, 38 / 255, 1),
            font_size=14,
            bold=True,
            halign='left',
            valign='middle',
        )
        label.bind(size=lambda l, _: setattr(l, 'text_size', (l.width, None)))
        box.add_widget(label)
        self.ids.tree_list.add_widget(box)

        # === Fade-in animation ===
        box.opacity = 0
        Animation(opacity=1, duration=0.3).start(box)

    def select_tree(self, box, name):
        # Reset colors of all items
        for child in self.ids.tree_list.children:
            if hasattr(child, "bg_color"):
                child.bg_color.rgba = (232 / 255, 255 / 255, 208 / 255, 1)

        # Highlight selected
        box.bg_color.rgba = (183 / 255, 255 / 255, 138 / 255, 1)
        self.selected_tree = name

    def on_add_tree(self):
        new_name = self.ids.add_input.text.strip()
        if new_name:
            self.add_tree_item(new_name)
            self.ids.add_input.text = ''

    def on_save_button(self):
        if not self.selected_tree:
            self.show_popup("Please select a tree first")
            return

        message = f"Successfully saved in '{self.selected_tree}' !"
        self.show_popup(message)

    def show_popup(self, message):
        popup = BoxLayout(
            size_hint=(None, None),
            size=(300, 43),
            pos_hint={"center_x": 0.5, "top": 0.87},
            opacity=0
        )

        with popup.canvas.before:
            Color(1, 1, 1, 1)
            popup.bg_rect = RoundedRectangle(radius=[10], pos=popup.pos, size=popup.size)
            Color(0, 0, 0, 0.15)
            popup.border_line = Line(
                rounded_rectangle=(popup.x, popup.y, popup.width, popup.height, 10),
                width=1
            )

        popup.bind(
            pos=lambda _, v: (
                setattr(popup.bg_rect, 'pos', v),
                setattr(popup.border_line, 'rounded_rectangle',
                        (v[0], v[1], popup.width, popup.height, 10))
            ),
            size=lambda _, v: (
                setattr(popup.bg_rect, 'size', v),
                setattr(popup.border_line, 'rounded_rectangle',
                        (popup.x, popup.y, v[0], v[1], 10))
            )
        )

        popup_label = Label(
            text=message,
            color=(49 / 255, 49 / 255, 49 / 255, 1),
            font_size=14,
            halign="center",
            valign="middle",
            bold=True
        )
        popup_label.bind(size=lambda l, _: setattr(l, 'text_size', (l.width, None)))
        popup.add_widget(popup_label)
        self.add_widget(popup)

        # === Popup animation ===
        anim = Animation(opacity=1, duration=0.3)
        anim += Animation(opacity=1, duration=1.5)
        anim += Animation(opacity=0, duration=0.4)
        anim.bind(on_complete=lambda *_: self.remove_widget(popup))
        anim.start(popup)