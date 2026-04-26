from kivy.uix.screenmanager import Screen
from kivy.properties import ObjectProperty, BooleanProperty, StringProperty, NumericProperty
from kivy.animation import Animation
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.behaviors import ButtonBehavior
from kivy.clock import Clock
from kivy.app import App

# Import the separate modals
from app.modals.delete_modal import DeleteModal
from app.modals.edit_modal import EditModal


class RecordTreeItem(ButtonBehavior, BoxLayout):
    """Single record card"""
    is_editing = BooleanProperty(False)
    tree_name = StringProperty("")
    is_selected = BooleanProperty(False)


class RecordsScreen(Screen):
    selected_tree = ObjectProperty(None, rebind=True)
    active_card = ObjectProperty(None, allownone=True)
    total_scan_count = NumericProperty(0)
    is_loading = BooleanProperty(False)
    show_empty = BooleanProperty(False)
    empty_message = StringProperty("No records yet.\nTap 'Add Tree' to get started.")

    def on_pre_enter(self, *args):
        self.build_tree_list()

    def build_tree_list(self):
        """Load tree list asynchronously to avoid blocking UI thread."""
        from threading import Thread
        from kivy.clock import Clock
        
        self.is_loading = True
        tree_list = self.ids.tree_list
        tree_list.clear_widgets()
        
        def load_data_background():
            from app.core.db import list_trees, get_all_tree_scan_counts, count_unassigned_scans
            db_trees = list_trees()
            scan_counts = get_all_tree_scan_counts()
            unassigned_count = count_unassigned_scans()
            Clock.schedule_once(lambda dt: self._populate_tree_list(db_trees, scan_counts, unassigned_count), 0)
        
        thread = Thread(target=load_data_background, daemon=True)
        thread.start()
    
    def _populate_tree_list(self, db_trees, scan_counts, unassigned_count):
        self.trees = [
            {"id": t["id"], "name": t["name"], "count": scan_counts.get(t["id"], 0)}
            for t in db_trees
        ]
        
        if unassigned_count > 0:
            self.trees.insert(0, {
                "id": None,
                "name": "📋 Unassigned Scans",
                "count": unassigned_count,
                "is_unassigned": True
            })
        
        self.filtered_trees = self.trees.copy()
        self.total_scan_count = sum(t["count"] for t in self.trees)
        self.ids.action_buttons.opacity = 0
        self.ids.action_buttons.disabled = True

        if not self.trees:
            self.show_empty = True
            self.empty_message = "No records yet.\nTap 'Add Tree' to get started."
        else:
            self.show_empty = False

        for t in self.trees:
            self.add_tree_item(t)
        
        self.is_loading = False

    def add_tree_item(self, tree_obj):
        name = tree_obj["name"]
        scan_count = tree_obj.get("count", 0)
        tree_id = tree_obj.get("id")
        box = RecordTreeItem(tree_name=name)
        box.tree_id = tree_id
        
        from kivy.graphics import Color, RoundedRectangle, Line
        with box.canvas.before:
            box.bg_color = Color(255/255, 255/255, 255/255, 1)
            box.bg_rect = RoundedRectangle(pos=box.pos, size=box.size, radius=[11])
            box.border_color = Color(0, 0, 0, 0.1)
            box.border = Line(
                rounded_rectangle=(box.x, box.y, box.width, box.height, 11),
                width=1
            )
        
        box.bind(
            pos=lambda w, v: self.update_card_graphics(w),
            size=lambda w, v: self.update_card_graphics(w)
        )
        
        content_box = BoxLayout(orientation='horizontal', spacing=10)
        
        name_label = Label(
            text=name,
            color=(56/255, 73/255, 38/255, 1),
            font_size=18,
            bold=True,
            halign='left',
            valign='middle',
        )
        name_label.bind(size=lambda l, _: setattr(l, 'text_size', (l.width, None)))
        box.label = name_label
        content_box.add_widget(name_label)

        view_button = Button(
            text=f"View ({scan_count})",
            color=(0/255, 152/255, 0/255, 1),
            font_size=14,
            italic=True,
            halign='right',
            valign='middle',
            size_hint=(None, 1),
            width=110,
            background_normal='',
            background_color=(0, 0, 0, 0),
            bold=False
        )
        view_button.bind(on_press=lambda btn: self.navigate_to_image_selection(box))
        content_box.add_widget(view_button)
        box.view_button = view_button
        
        box.add_widget(content_box)
        box.bind(on_press=self.on_card_click)
        box.is_selected = False
        
        self.ids.tree_list.add_widget(box)
        box.opacity = 0
        Animation(opacity=1, duration=0.3, t='out_quad').start(box)

    def on_card_click(self, card):
        if self.active_card and self.active_card != card:
            self.deselect_card(self.active_card)
        
        if self.active_card == card:
            self.deselect_card(card)
            self.hide_action_buttons()
            self.active_card = None
        else:
            self.select_card(card)
            self.active_card = card

    def select_card(self, card):
        card.is_selected = True
        card.border_color.rgba = (0/255, 152/255, 0/255, 1)
        card.border.width = 2
        self.show_action_buttons()

    def deselect_card(self, card):
        card.is_selected = False
        card.border_color.rgba = (0, 0, 0, 0.1)
        card.border.width = 1

    def update_card_graphics(self, card):
        if hasattr(card, 'bg_rect'):
            card.bg_rect.pos = card.pos
            card.bg_rect.size = card.size
            card.border.rounded_rectangle = (card.x, card.y, card.width, card.height, 11)

    def show_action_buttons(self):
        self.ids.action_buttons.disabled = False
        Animation(opacity=1, duration=0.2, t='out_quad').start(self.ids.action_buttons)

    def hide_action_buttons(self):
        Animation(opacity=0, duration=0.2, t='out_quad').start(self.ids.action_buttons)
        Clock.schedule_once(lambda dt: setattr(self.ids.action_buttons, 'disabled', True), 0.2)

    def on_edit_button(self):
        if not self.active_card:
            return
        self.edit_tree(self.active_card)

    def on_delete_button(self):
        if not self.active_card:
            return
        self.confirm_delete(self.active_card)

    def edit_tree(self, card):
        if card.is_editing:
            return
        
        if not hasattr(card, 'tree_id') or card.tree_id is None:
            self.show_notification("Cannot edit this entry", icon_type='fail')
            return
        
        def on_edit_complete(success, new_name, original_name):
            if success:
                card.tree_name = new_name
                card.label.text = new_name
                for t in self.trees:
                    if t.get("id") == card.tree_id:
                        t["name"] = new_name
                        break
                for t in self.filtered_trees:
                    if t.get("id") == card.tree_id:
                        t["name"] = new_name
                        break
                self.show_notification(f"Renamed to '{new_name}'", icon_type='success')
        
        modal = EditModal(tree_name=card.tree_name, tree_id=card.tree_id, callback=on_edit_complete)
        modal.open()

    def confirm_delete(self, card):
        if not hasattr(card, 'tree_id') or card.tree_id is None:
            self.show_notification("Cannot delete this entry", icon_type='fail')
            return
        
        def on_delete_complete(success, tree_name):
            if success:
                fade_out = Animation(opacity=0, duration=0.2)
                fade_out.bind(on_complete=lambda *_: self.ids.tree_list.remove_widget(card))
                fade_out.start(card)
                self.trees = [t for t in self.trees if t["id"] != card.tree_id]
                self.filtered_trees = [t for t in self.filtered_trees if t["id"] != card.tree_id]
                self.total_scan_count = sum(t["count"] for t in self.trees)
                self.hide_action_buttons()
                self.active_card = None
                self.show_notification(f"'{tree_name}' deleted", icon_type='success')
            else:
                self.show_notification("Failed to delete tree", icon_type='fail')
        
        modal = DeleteModal(tree_name=card.tree_name, tree_id=card.tree_id, callback=on_delete_complete)
        modal.open()

    def navigate_to_image_selection(self, card):
        self.selected_tree = card.tree_name
        app = App.get_running_app()
        app.current_tree_name = card.tree_name
        app.selected_tree_id = getattr(card, 'tree_id', None)
        app.last_screen = 'records'
        self.manager.current = 'image_select'

    def on_add_tree(self):
        self.show_add_tree_modal()

    def on_search_text(self, text):
        tree_list = self.ids.tree_list
        tree_list.clear_widgets()
        search_text = (text or '').lower().strip()
        if search_text:
            self.filtered_trees = [t for t in self.trees if search_text in t['name'].lower()]
        else:
            self.filtered_trees = self.trees.copy()
        self.hide_action_buttons()
        self.active_card = None
        if not self.filtered_trees:
            self.show_empty = True
            search_text = (text or '').lower().strip()
            self.empty_message = (
                f"No trees match '{text}'." if search_text
                else "No records yet.\nTap 'Add Tree' to get started."
            )
        else:
            self.show_empty = False
        for t in self.filtered_trees:
            self.add_tree_item(t)
        Clock.schedule_once(lambda dt: setattr(self.ids.scroll_view, 'scroll_y', 1), 0.1)

    def show_notification(self, message, icon_type=None):
        """Show animated notification popup with optional icon.

        Args:
            message: The notification text
            icon_type: 'success' for checkmark, 'fail' for warning, None for no icon
        """
        from kivy.graphics import Color, RoundedRectangle, Line
        from kivy.uix.image import Image
        from kivy.uix.floatlayout import FloatLayout

        # Measure label first to size container dynamically
        popup_label = Label(
            text=message,
            color=(49/255, 49/255, 49/255, 1),
            font_size=14,
            halign="left",
            valign="middle",
            bold=True,
            pos_hint={"center_y": 0.52}
        )
        popup_label.texture_update()
        popup_label.size = popup_label.texture_size

        # Calculate content width: icon (if any) + spacing + label
        icon_width = 24 + 8 if icon_type else 0
        content_width = icon_width + popup_label.width

        # Equal horizontal padding on both sides
        h_padding = 20
        popup_width = content_width + h_padding * 2
        popup_height = 45

        # Main container — dynamically sized
        popup = FloatLayout(
            size_hint=(None, None),
            size=(popup_width, popup_height),
            pos_hint={"center_x": 0.5, "top": 0.88},
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

        # Inner content container — exact content size, centered in popup
        content = BoxLayout(
            orientation='horizontal',
            size_hint=(None, None),
            size=(content_width, 24),
            spacing=8,
            pos_hint={"center_x": 0.5, "center_y": 0.5}
        )

        if icon_type == 'success':
            icon = Image(
                source='app/assets/success.png',
                size_hint=(None, None),
                size=(24, 24),
                allow_stretch=True,
                keep_ratio=True,
                mipmap=True
            )
            content.add_widget(icon)
        elif icon_type == 'fail':
            icon = Image(
                source='app/assets/fail.png',
                size_hint=(None, None),
                size=(24, 24),
                allow_stretch=True,
                keep_ratio=True,
                mipmap=True
            )
            content.add_widget(icon)

        content.add_widget(popup_label)
        popup.add_widget(content)
        self.add_widget(popup)

        anim = Animation(opacity=1, duration=0.3)
        anim += Animation(opacity=1, duration=1.5)
        anim += Animation(opacity=0, duration=0.4)
        anim.bind(on_complete=lambda *_: self.remove_widget(popup))
        anim.start(popup)

    def export_all_scans(self):
        '''Export all scans to CSV file.'''
        from app.core.db import export_scans_to_csv
        import os
        
        try:
            file_path = export_scans_to_csv()
            if file_path and os.path.exists(file_path):
                file_name = os.path.basename(file_path)
                self.show_notification(f'Exported to {file_name}', icon_type='success')
            else:
                self.show_notification('Export failed - No scans found', icon_type='fail')
        except Exception as e:
            print(f'Export error: {e}')
            self.show_notification(f'Export failed: {str(e)}', icon_type='fail')
    
    def show_add_tree_modal(self):
        '''Show dialog to add new tree with extended fields.'''
        from app.modals.add_tree_modal import AddTreeModal
        
        def on_tree_added(tree_id, name, location, variety):
            self.show_notification(f'Tree "{name}" added successfully', icon_type='success')
            self.build_tree_list()
        
        dialog = AddTreeModal(callback=on_tree_added)
        dialog.open()
