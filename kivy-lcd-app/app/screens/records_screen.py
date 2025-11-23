from kivy.uix.screenmanager import Screen
from kivy.properties import ObjectProperty, BooleanProperty, StringProperty, NumericProperty
from kivy.animation import Animation
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image
from kivy.uix.behaviors import ButtonBehavior
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.app import App  # Added import for App used in navigation


# Load confirmation modal template
Builder.load_string("""
<ConfirmDeleteModal@BoxLayout>:
    orientation: 'vertical'
    size_hint: None, None
    size: 320, 150
    pos_hint: {"center_x": 0.5, "center_y": 0.5}
    padding: [20, 20, 20, 15]
    spacing: 15
    
    canvas.before:
        Color:
            rgba: 1, 1, 1, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [15]
        Color:
            rgba: 0, 0, 0, 0.2
        Line:
            rounded_rectangle: (self.x, self.y, self.width, self.height, 15)
            width: 1.5
    
    Label:
        id: title_label
        color: 49/255, 49/255, 49/255, 1
        font_size: 18
        bold: True
        size_hint_y: 0.4
    
    Label:
        text: "This action cannot be undone."
        color: 99/255, 99/255, 99/255, 1
        font_size: 14
        size_hint_y: 0.3
    
    BoxLayout:
        size_hint_y: 0.3
        spacing: 10
        
        Button:
            id: cancel_btn
            text: "Cancel"
            font_size: 15
            bold: True
            color: 49/255, 49/255, 49/255, 1
            background_normal: ''
            background_color: 0, 0, 0, 0
            
            canvas.before:
                Color:
                    rgba: 220/255, 220/255, 220/255, 1
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [8]
        
        Button:
            id: delete_btn
            text: "Delete"
            font_size: 15
            bold: True
            color: 1, 1, 1, 1
            background_normal: ''
            background_color: 0, 0, 0, 0
            
            canvas.before:
                Color:
                    rgba: 220/255, 53/255, 69/255, 1
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [8]
""")


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

    def on_pre_enter(self, *args):
        self.build_tree_list()

    def build_tree_list(self):
        """Load tree list asynchronously to avoid blocking UI thread."""
        from threading import Thread
        from kivy.clock import Clock
        
        # Show loading state
        self.is_loading = True
        tree_list = self.ids.tree_list
        tree_list.clear_widgets()
        
        def load_data_background():
            """Execute database queries in background thread."""
            from app.core.db import list_trees, get_all_tree_scan_counts, count_unassigned_scans
            
            # Fetch all data in background
            db_trees = list_trees()
            scan_counts = get_all_tree_scan_counts()
            unassigned_count = count_unassigned_scans()
            
            # Schedule UI update on main thread
            Clock.schedule_once(lambda dt: self._populate_tree_list(db_trees, scan_counts, unassigned_count), 0)
        
        # Start background thread
        thread = Thread(target=load_data_background, daemon=True)
        thread.start()
    
    def _populate_tree_list(self, db_trees, scan_counts, unassigned_count):
        """Populate UI with loaded data (called on main thread)."""
        # Augment with scan counts
        self.trees = [
            {"id": t["id"], "name": t["name"], "count": scan_counts.get(t["id"], 0) }
            for t in db_trees
        ]
        
        # Add "Unassigned Scans" category if there are any
        if unassigned_count > 0:
            self.trees.insert(0, {
                "id": None,
                "name": "📋 Unassigned Scans",
                "count": unassigned_count,
                "is_unassigned": True
            })
        
        self.filtered_trees = self.trees.copy()
        self.total_scan_count = sum(t["count"] for t in self.trees)

        # Hide action buttons initially
        self.ids.action_buttons.opacity = 0
        self.ids.action_buttons.disabled = True

        # Populate UI
        for t in self.trees:
            self.add_tree_item(t)
        
        # Hide loading state
        self.is_loading = False

    def add_tree_item(self, tree_obj):
        name = tree_obj["name"]
        scan_count = tree_obj.get("count", 0)
        tree_id = tree_obj.get("id")
        # Create card
        box = RecordTreeItem(tree_name=name)
        box.tree_id = tree_id
        
        # Set up initial canvas with border
        from kivy.graphics import Color, RoundedRectangle, Line
        with box.canvas.before:
            box.bg_color = Color(255/255, 255/255, 255/255, 1)
            box.bg_rect = RoundedRectangle(
                pos=box.pos,
                size=box.size,
                radius=[11]
            )
            box.border_color = Color(0, 0, 0, 0.1)
            box.border = Line(
                rounded_rectangle=(box.x, box.y, box.width, box.height, 11),
                width=1
            )
        
        box.bind(
            pos=lambda w, v: self.update_card_graphics(w),
            size=lambda w, v: self.update_card_graphics(w)
        )
        
        # Main content container
        content_box = BoxLayout(orientation='horizontal', spacing=10)
        
        # Left name / right count stacked vertically
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

        # View button shows count
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
        view_button.bind(on_release=lambda btn: self.navigate_to_image_selection(box))
        content_box.add_widget(view_button)
        box.view_button = view_button
        
        box.add_widget(content_box)

        # Click detection for card selection (not navigation)
        box.bind(on_release=self.on_card_click)
        box.is_selected = False
        
        self.ids.tree_list.add_widget(box)

        # Fade-in
        box.opacity = 0
        Animation(opacity=1, duration=0.3, t='out_quad').start(box)

    def on_card_click(self, card):
        """Handle card selection"""
        # Deselect previous card
        if self.active_card and self.active_card != card:
            self.deselect_card(self.active_card)
        
        # Toggle selection of current card
        if self.active_card == card:
            self.deselect_card(card)
            self.hide_action_buttons()
            self.active_card = None
        else:
            self.select_card(card)
            self.active_card = card

    def select_card(self, card):
        """Highlight card with green border"""
        card.is_selected = True
        
        # Change border to green with thicker width
        card.border_color.rgba = (0/255, 152/255, 0/255, 1)
        card.border.width = 2
        
        # Show action buttons
        self.show_action_buttons()

    def deselect_card(self, card):
        """Remove highlight from card"""
        card.is_selected = False
        
        # Reset border to default gray with normal width
        card.border_color.rgba = (0, 0, 0, 0.1)
        card.border.width = 1

    def update_card_graphics(self, card):
        """Update card graphics when position or size changes"""
        if hasattr(card, 'bg_rect'):
            card.bg_rect.pos = card.pos
            card.bg_rect.size = card.size
            card.border.rounded_rectangle = (card.x, card.y, card.width, card.height, 11)

    def show_action_buttons(self):
        """Animate showing action buttons"""
        self.ids.action_buttons.disabled = False
        Animation(opacity=1, duration=0.2, t='out_quad').start(self.ids.action_buttons)

    def hide_action_buttons(self):
        """Animate hiding action buttons"""
        Animation(opacity=0, duration=0.2, t='out_quad').start(self.ids.action_buttons)
        Clock.schedule_once(lambda dt: setattr(self.ids.action_buttons, 'disabled', True), 0.2)

    def on_edit_button(self):
        """Handle edit button click"""
        if not self.active_card:
            return
        
        self.edit_tree(self.active_card)

    def on_delete_button(self):
        """Handle delete button click"""
        if not self.active_card:
            return
        
        self.confirm_delete(self.active_card)

    def edit_tree(self, card):
        """Enable editing mode for tree name (DB-backed)."""
        if card.is_editing:
            return
        from app.core.db import update_tree_name, get_tree_by_name
        card.is_editing = True
        original_name = card.tree_name
        content_box = card.children[0]
        label = card.label
        content_box.remove_widget(label)
        edit_input = TextInput(
            text=original_name,
            multiline=False,
            font_size=18,
            bold=True,
            foreground_color=(56/255, 73/255, 38/255, 1),
            background_color=(0, 0, 0, 0),
            cursor_color=(56/255, 73/255, 38/255, 1),
            padding=[0, 12, 0, 0]
        )

        def cancel_edit(*_):
            content_box.remove_widget(edit_input)
            content_box.add_widget(label)
            card.is_editing = False

        def save_edit(_):
            new_name = edit_input.text.strip()
            if not new_name or new_name == original_name:
                cancel_edit()
                return
            if get_tree_by_name(new_name):
                self.show_notification(f"'{new_name}' already exists!")
                cancel_edit()
                return
            if update_tree_name(card.tree_id, new_name):
                card.tree_name = new_name
                label.text = new_name
                self.show_notification(f"Renamed to '{new_name}'")
                self.total_scan_count = sum(t["count"] for t in self.trees)
            cancel_edit()

        edit_input.bind(on_text_validate=save_edit)
        content_box.add_widget(edit_input)
        edit_input.focus = True

    def confirm_delete(self, card):
        """Show confirmation dialog before deleting (DB-backed)."""
        from kivy.factory import Factory
        from app.core.db import delete_tree
        
        modal = Factory.ConfirmDeleteModal()
        modal.ids.title_label.text = f"Delete '{card.tree_name}'?"
        modal.opacity = 0
        
        def close_modal(*args):
            anim = Animation(opacity=0, duration=0.2)
            anim.bind(on_complete=lambda *_: self.remove_widget(modal))
            anim.start(modal)
        
        def do_delete(*_):
            if delete_tree(card.tree_id):
                fade_out = Animation(opacity=0, duration=0.2)
                fade_out.bind(on_complete=lambda *_: self.ids.tree_list.remove_widget(card))
                fade_out.start(card)
                self.show_notification(f"'{card.tree_name}' deleted")
                self.trees = [t for t in self.trees if t["id"] != card.tree_id]
                self.filtered_trees = [t for t in self.filtered_trees if t["id"] != card.tree_id]
                self.total_scan_count = sum(t["count"] for t in self.trees)
            close_modal()
            self.hide_action_buttons()
            self.active_card = None

        modal.ids.cancel_btn.bind(on_release=close_modal)
        modal.ids.delete_btn.bind(on_release=do_delete)
        
        self.add_widget(modal)
        Animation(opacity=1, duration=0.2).start(modal)

    def navigate_to_image_selection(self, card):
        """Navigate to enhanced ImageSelection screen filtered by selected tree."""
        self.selected_tree = card.tree_name
        app = App.get_running_app()
        # Set the current tree context for ImageSelection
        app.current_tree_name = card.tree_name
        app.selected_tree_id = getattr(card, 'tree_id', None)
        app.last_screen = 'records'
        # Navigate to the enhanced image selection screen (filtered by tree)
        self.manager.current = 'image_select'

    def on_add_tree(self):
        """Show dialog to add new tree with extended fields."""
        self.show_tree_dialog()

    def on_search_text(self, text):
        """Filter tree list based on search text (DB-backed list already loaded)."""
        tree_list = self.ids.tree_list
        tree_list.clear_widgets()
        search_text = (text or '').lower().strip()
        if search_text:
            self.filtered_trees = [t for t in self.trees if search_text in t['name'].lower()]
        else:
            self.filtered_trees = self.trees.copy()
        self.hide_action_buttons()
        self.active_card = None
        for t in self.filtered_trees:
            self.add_tree_item(t)
        Clock.schedule_once(lambda dt: setattr(self.ids.scroll_view, 'scroll_y', 1), 0.1)

    def show_notification(self, message):
        """Show animated notification popup"""
        from kivy.graphics import Color, RoundedRectangle, Line
        
        popup = BoxLayout(
            size_hint=(None, None),
            size=(320, 45),
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

        popup_label = Label(
            text=message,
            color=(49/255, 49/255, 49/255, 1),
            font_size=14,
            halign="center",
            valign="middle",
            bold=True
        )
        popup_label.bind(size=lambda l, _: setattr(l, 'text_size', (l.width, None)))
        popup.add_widget(popup_label)
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
            # Export all scans (no tree filter)
            file_path = export_scans_to_csv()
            
            if file_path and os.path.exists(file_path):
                # Show success notification with file path
                file_name = os.path.basename(file_path)
                self.show_notification(f'✓ Exported to {file_name}')
            else:
                self.show_notification('⚠ Export failed - No scans found')
        
        except Exception as e:
            print(f'Export error: {e}')
            self.show_notification(f'⚠ Export failed: {str(e)}')
    
    def show_tree_dialog(self):
        '''Show dialog to add new tree with extended fields.'''
        from app.dialogs.tree_dialog import TreeDialog
        
        def on_tree_added(tree_id, name, location, variety):
            '''Callback when tree is successfully added.'''
            self.show_notification(f'✓ Tree "{name}" added successfully')
            # Refresh tree list to show new tree
            self.build_tree_list()
        
        dialog = TreeDialog(callback=on_tree_added)
        dialog.open()
