"""Save Modal - opened as a ModalView from CaptureResultScreen."""
import os
from kivy.uix.modalview import ModalView
from kivy.properties import (
    ObjectProperty, StringProperty, NumericProperty, BooleanProperty
)
from kivy.app import App
from kivy.animation import Animation
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.behaviors import ButtonBehavior
from kivy.clock import Clock
from kivy.lang import Builder

# Load KV rules — must be before any Factory usage
_kv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "SaveModal.kv")
Builder.load_file(_kv_path)

class TreeItem(ButtonBehavior, BoxLayout):
    pass


class SaveModal(ModalView):
    selected_tree = ObjectProperty(None, rebind=True, allownone=True)
    prediction_label = StringProperty("")
    prediction_confidence = NumericProperty(0.0)
    severity_percentage = NumericProperty(0.0)
    severity_level = StringProperty("")
    image_path = StringProperty("")

    show_empty = BooleanProperty(True)
    empty_message = StringProperty("No trees yet.\nTap '+ Tree' to get started.")

    trees_cache = []
    cache_timestamp = 0

    def on_open(self):
        self._action_taken = False  # Reset guard each time modal opens
        self._load_scan_info()
        Clock.schedule_once(lambda dt: self.build_tree_list(), 0)

    def _load_scan_info(self):
        app = App.get_running_app()
        data = getattr(app, "scan_result", {}) or {}
        self.prediction_label = data.get("label", "")
        self.prediction_confidence = data.get("confidence", 0.0)
        self.severity_percentage = data.get("severity_percentage", 0.0)
        self.severity_level = data.get("severity_level", "")
        self.image_path = data.get("image_path", "")

    def build_tree_list(self):
        import time
        from threading import Thread

        if 'tree_list' not in self.ids:
            Clock.schedule_once(lambda dt: self.build_tree_list(), 0.1)
            return

        self.ids.tree_list.clear_widgets()
        self.show_empty = True
        self.empty_message = "Loading trees..."

        cache_age = time.time() - SaveModal.cache_timestamp
        if SaveModal.trees_cache and cache_age < 60:
            self._populate_tree_list(SaveModal.trees_cache)
            return

        def load_in_background():
            from app.core.db import list_trees
            trees = list_trees()
            SaveModal.trees_cache = trees
            SaveModal.cache_timestamp = time.time()
            Clock.schedule_once(lambda dt: self._populate_tree_list(trees), 0)

        Thread(target=load_in_background, daemon=True).start()

    def _populate_tree_list(self, trees):
        self.ids.tree_list.clear_widgets()
        self.trees = trees
        self.filtered_trees = trees.copy()
        self.selected_tree = None

        if not trees:
            self.show_empty = True
            self.empty_message = "No trees yet.\nTap '+ Tree' to get started."
            return

        self.show_empty = False
        for t in trees:
            self.add_tree_item(t['name'], t['id'])

    @classmethod
    def invalidate_cache(cls):
        cls.trees_cache = []
        cls.cache_timestamp = 0

    def add_tree_item(self, name, tree_id=None):
        container = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=42,
            padding=[3, 2, 3, 2]
        )

        box = TreeItem(
            orientation='horizontal',
            size_hint_y=None,
            height=38,
            padding=[10, 0, 10, 0],
            on_release=lambda *_: self.select_tree(box, name, tree_id)
        )

        with box.canvas.before:
            box.bg_color = Color(1, 1, 1, 1)
            box.bg_rect = RoundedRectangle(radius=[10], pos=box.pos, size=box.size)
            box.border_color = Color(0, 0, 0, 0.08)
            box.border_line = Line(
                rounded_rectangle=(box.x, box.y, box.width, box.height, 10),
                width=1
            )

        box.bind(
            pos=lambda _, v: (
                setattr(box.bg_rect, 'pos', v),
                setattr(box.border_line, 'rounded_rectangle',
                        (v[0], v[1], box.width, box.height, 10))
            ),
            size=lambda _, v: (
                setattr(box.bg_rect, 'size', v),
                setattr(box.border_line, 'rounded_rectangle',
                        (box.x, box.y, v[0], v[1], 10))
            )
        )

        lbl = Label(
            text=name,
            color=(56/255, 73/255, 38/255, 1),
            font_size=14,
            bold=True,
            halign='left',
            valign='middle',
        )
        lbl.bind(size=lambda l, _: setattr(l, 'text_size', (l.width, None)))
        box.add_widget(lbl)
        box.tree_name = name
        box.tree_id = tree_id

        container.add_widget(box)
        self.ids.tree_list.add_widget(container)

        container.opacity = 0
        Animation(opacity=1, duration=0.3).start(container)

    def select_tree(self, box, name, tree_id):
        for container in self.ids.tree_list.children:
            if container.children:
                child = container.children[0]
                if hasattr(child, "border_color"):
                    child.border_color.rgba = (0, 0, 0, 0.08)
                    child.border_line.width = 1

        box.border_color.rgba = (0/255, 152/255, 0/255, 1)
        box.border_line.width = 2
        self.selected_tree = name
        self.selected_tree_id = tree_id

    def on_add_tree(self):
        # Guard against double-tap on resistive touchscreen
        if getattr(self, '_adding_tree', False):
            return
        self._adding_tree = True
        Clock.schedule_once(lambda dt: setattr(self, '_adding_tree', False), 1.0)
        from app.modals.add_tree_modal import AddTreeModal

        def on_tree_added(tree_id, name, location, variety):
            tree_obj = {"id": tree_id, "name": name}
            self.trees.insert(0, tree_obj)
            self.filtered_trees.insert(0, tree_obj)
            self.show_empty = False
            self.add_tree_item(name, tree_id)

        dialog = AddTreeModal(callback=on_tree_added)
        dialog.open()

    def on_search_text(self, text):
        self.ids.tree_list.clear_widgets()
        search_text = text.lower().strip()

        if search_text:
            self.filtered_trees = [
                t for t in self.trees if search_text in t['name'].lower()
            ]
        else:
            self.filtered_trees = self.trees.copy()

        self.selected_tree = None
        self.selected_tree_id = None

        if not self.filtered_trees:
            self.show_empty = True
            self.empty_message = (
                f"No trees match '{text}'." if search_text
                else "No trees yet.\nTap '+ Tree' to get started."
            )
        else:
            self.show_empty = False
            for t in self.filtered_trees:
                self.add_tree_item(t['name'], t['id'])

        Clock.schedule_once(
            lambda dt: setattr(self.ids.scroll_view, 'scroll_y', 1), 0.1
        )

    def on_save_button(self):
        # Guard against double-tap on resistive touchscreen
        if getattr(self, '_action_taken', False):
            return

        if not self.selected_tree:
            self._show_error("Please select a tree first.")
            return

        self._action_taken = True
        tree_name = self.selected_tree
        self._persist_scan()

        # Dismiss SaveModal then show SaveSuccessModal
        self.dismiss()
        Clock.schedule_once(lambda dt: self._open_success(tree_name), 0.15)

    def _open_success(self, tree_name):
        from app.modals.save_success_modal import SaveSuccessModal
        modal = SaveSuccessModal(tree_name=tree_name)
        modal.open()

    def _show_error(self, message):
        """Show red error label above divider, same pattern as AddTreeModal."""
        if '_error_hide_event' in dir(self) and self._error_hide_event:
            self._error_hide_event.cancel()

        label = self.ids.error_label
        label.text = message
        Animation.cancel_all(label)
        Animation(opacity=1, duration=0.3).start(label)

        self._error_hide_event = Clock.schedule_once(
            lambda dt: Animation(opacity=0, duration=0.3).start(label), 3.0
        )

    def _persist_scan(self):
        from app.core.db import insert_scan_record, get_or_create_disease, get_or_create_severity
        from app.core.image_thumb import generate_thumbnail

        if not getattr(self, 'selected_tree_id', None):
            return

        disease_id = get_or_create_disease(self.prediction_label) if self.prediction_label else None
        severity_id = get_or_create_severity(self.severity_level) if self.severity_level else None
        thumb_path = generate_thumbnail(self.image_path)

        app = App.get_running_app()
        scan_result = getattr(app, 'scan_result', {}) or {}

        scan_id = insert_scan_record(
            self.selected_tree_id, disease_id, severity_id,
            self.severity_percentage, self.image_path, thumb_path, None,
            confidence_score=scan_result.get('confidence'),
            total_leaf_area=scan_result.get('total_leaf_area'),
            lesion_area=scan_result.get('lesion_area')
        )
        app.current_scan_id = scan_id
