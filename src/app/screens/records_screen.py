from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.properties import ObjectProperty, BooleanProperty, StringProperty
from kivy.animation import Animation
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image
from kivy.uix.behaviors import ButtonBehavior
from kivy.clock import Clock
from kivy.lang import Builder


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


from app.theme import apply_background, COLORS, FONTS

class RecordsScreen(Screen):
    selected_tree = ObjectProperty(None, rebind=True)
    active_card = ObjectProperty(None, allownone=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize internal lists to make methods safe when called
        # outside of full KV-driven app lifecycle (unit tests).
        self.trees = []
        self.filtered_trees = []

    def on_pre_enter(self, *args):
        # Schedule fetch of trees (mirrors prior behavior and allows tests
        # to call _fetch_trees directly).
        Clock.schedule_once(self._fetch_trees, 0)
        # Apply themed background
        apply_background(self, 'bg_primary')
        try:
            if 'records_heading' in self.ids:
                self.ids.records_heading.color = COLORS['text_primary']
                self.ids.records_heading.font_size = FONTS['heading_size']
            if 'records_subheading' in self.ids:
                self.ids.records_subheading.color = COLORS['text_secondary']
                self.ids.records_subheading.font_size = FONTS['body_size']
        except Exception:
            pass

    def build_tree_list(self):
        tree_list = self.ids.tree_list
        tree_list.clear_widgets()
        # Populate the list from the database. Use the existing
        # _fetch_trees method which calls the DB manager and will
        # invoke `populate_trees_list` with results.
        # Hide action buttons initially (if present)
        try:
            self.ids.action_buttons.opacity = 0
            self.ids.action_buttons.disabled = True
        except Exception:
            pass

        # Trigger a DB-backed refresh if the running App provides a DB manager.
        # Otherwise, ensure the UI shows an empty state instead of any
        # previously hardcoded placeholders.
        try:
            app = App.get_running_app()
        except Exception:
            app = None

        if app and hasattr(app, 'db_manager') and app.db_manager is not None:
            self._fetch_trees(0)
        else:
            # No DB available in this context (unit tests or isolated usage).
            # Clear widgets and show empty label so the screen isn't static.
            try:
                self.ids.tree_list.clear_widgets()
                from kivy.uix.label import Label
                lbl = Label(text="No records found.")
                self.ids.tree_list.add_widget(lbl)
            except Exception:
                # If ids aren't available, just update the internal lists.
                self.trees = []
                self.filtered_trees = []

    def add_tree_item(self, name):
        # Name may be a dict from DB or a plain string
        tree_name = name['name'] if isinstance(name, dict) else name
        # Create card
        box = RecordTreeItem(tree_name=tree_name)
        
        # Set up initial canvas with border
        # Graphics operations can fail in headless/unit-test environments.
        try:
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
        except Exception:
            # If drawing primitives are unavailable, continue without them.
            pass
        
        box.bind(
            pos=lambda w, v: self.update_card_graphics(w),
            size=lambda w, v: self.update_card_graphics(w)
        )
        
        # Main content container
        content_box = BoxLayout(orientation='horizontal', spacing=10)
        
        # Tree name label
        display_name = tree_name
        label = Label(
            text=display_name,
            color=(56/255, 73/255, 38/255, 1),
            font_size=18,
            bold=True,
            halign='left',
            valign='middle',
        )
        label.bind(size=lambda l, _: setattr(l, 'text_size', (l.width, None)))
        content_box.add_widget(label)
        box.label = label

        # View Records Button
        view_button = Button(
            text="View Records",
            color=(0/255, 152/255, 0/255, 1),
            font_size=14,
            italic=True,
            halign='right',
            valign='middle',
            size_hint=(None, 1),
            width=100,
            background_normal='',
            background_color=(0, 0, 0, 0),
            bold=False
        )
        # If the original `name` arg was a DB dict (contains 'id'), pass it
        # to `view_tree_scans` so the ImageSelection screen can fetch records
        # by tree id. If `name` is just a string (no id), fall back to
        # navigate_to_image_selection which preserves existing behavior.
        if isinstance(name, dict) and 'id' in name:
            view_button.bind(on_release=lambda btn, t=name: self.view_tree_scans(t))
        else:
            view_button.bind(on_release=lambda btn: self.navigate_to_image_selection(box))
        content_box.add_widget(view_button)
        
        box.add_widget(content_box)

        # Click detection for card selection (not navigation)
        box.bind(on_release=self.on_card_click)
        box.is_selected = False
        
        self.ids.tree_list.add_widget(box)

        # Fade-in
        box.opacity = 0
        Animation(opacity=1, duration=0.3, t='out_quad').start(box)

    # --- Methods required by unit tests ---
    def _fetch_trees(self, dt):
        app = App.get_running_app()
        app.db_manager.get_all_trees_async(on_success_callback=self.populate_trees_list)

    def populate_trees_list(self, trees):
        # Expecting a list of dicts: [{'id':..,'name':..}, ...]
        # UI updates must run on the main Kivy thread. This method can be
        # invoked from background threads (Database callbacks), so schedule
        # the actual widget work on the main loop.
        self.trees = trees

        def _ui_update(dt):
            try:
                self.ids.tree_list.clear_widgets()
            except Exception:
                # If ids or tree_list aren't available in this context,
                # skip UI work.
                return

            if not trees:
                from kivy.uix.label import Label
                lbl = Label(text="No records found.")
                self.ids.tree_list.add_widget(lbl)
                return

            for t in trees:
                self.add_tree_item(t)

        # If we're on the main thread, run UI updates synchronously so tests
        # that call the DB in synchronous mode see immediate results. If
        # we're on a background thread (normal app runtime), schedule the
        # update on the main Kivy loop to avoid graphics-thread errors.
        import threading
        if threading.current_thread().name == 'MainThread':
            _ui_update(0)
        else:
            try:
                Clock.schedule_once(_ui_update, 0)
            except Exception:
                # As a last resort, call synchronously
                _ui_update(0)

    def filter_and_populate(self, all_trees, search_text):
        # Accept list of dicts and filter by their 'name' field.
        filtered = [t for t in all_trees if search_text in (t['name'].lower() if isinstance(t, dict) else str(t).lower())]
        self.populate_trees_list(filtered)

    def view_tree_scans(self, tree):
        app = App.get_running_app()
        app.selected_tree_id = tree['id']
        self.manager.current = 'image_selection'

    def on_add_tree(self):
        # Read from input and create via DB manager
        app = App.get_running_app()
        name = self.ids.add_input.text.strip()
        if not name:
            return

        def _on_added(result):
            # after adding, refresh list
            self._fetch_trees(0)

        app.db_manager.add_tree_async(name, on_success_callback=_on_added)

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
        if 'action_buttons' not in self.ids:
            return
        try:
            self.ids.action_buttons.disabled = False
            Animation(opacity=1, duration=0.2, t='out_quad').start(self.ids.action_buttons)
        except Exception:
            pass

    def hide_action_buttons(self):
        """Animate hiding action buttons"""
        if 'action_buttons' not in self.ids:
            return
        try:
            Animation(opacity=0, duration=0.2, t='out_quad').start(self.ids.action_buttons)
            Clock.schedule_once(lambda dt: setattr(self.ids.action_buttons, 'disabled', True), 0.2)
        except Exception:
            pass

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
        """Enable editing mode for tree name"""
        if card.is_editing:
            return
        
        card.is_editing = True
        original_name = card.tree_name
        
        # Remove label temporarily
        content_box = card.children[0]
        label = content_box.children[1]  # The tree name label
        content_box.remove_widget(label)
        
        # Create edit input
        edit_input = TextInput(
            text=card.tree_name,
            multiline=False,
            font_size=18,
            bold=True,
            foreground_color=(56/255, 73/255, 38/255, 1),
            background_color=(0, 0, 0, 0),
            cursor_color=(56/255, 73/255, 38/255, 1),
            padding=[0, 12, 0, 0]
        )
        
        def save_edit(instance):
            new_name = edit_input.text.strip()
            if new_name and new_name != original_name:
                if new_name in self.trees and new_name != original_name:
                    self.show_notification(f"'{new_name}' already exists!")
                    cancel_edit()
                    return
                
                # Update tree name
                index = self.trees.index(original_name)
                self.trees[index] = new_name
                card.tree_name = new_name
                card.label.text = new_name
                
                content_box.remove_widget(edit_input)
                content_box.add_widget(card.label, index=1)
                card.is_editing = False
                
                self.show_notification(f"Renamed to '{new_name}'")
            else:
                cancel_edit()
        
        def cancel_edit(*args):
            content_box.remove_widget(edit_input)
            content_box.add_widget(card.label, index=1)
            card.is_editing = False
        
        edit_input.bind(on_text_validate=save_edit)
        content_box.add_widget(edit_input, index=1)
        edit_input.focus = True

    def confirm_delete(self, card):
        """Show confirmation dialog before deleting"""
        from kivy.factory import Factory
        
        modal = Factory.ConfirmDeleteModal()
        modal.ids.title_label.text = f"Delete '{card.tree_name}'?"
        modal.opacity = 0
        
        def close_modal(*args):
            anim = Animation(opacity=0, duration=0.2)
            anim.bind(on_complete=lambda *_: self.remove_widget(modal))
            anim.start(modal)
        
        def delete_tree(*args):
            self.trees.remove(card.tree_name)
            if card.tree_name in self.filtered_trees:
                self.filtered_trees.remove(card.tree_name)
            
            fade_out = Animation(opacity=0, duration=0.2)
            fade_out.bind(on_complete=lambda *_: self.ids.tree_list.remove_widget(card))
            fade_out.start(card)
            
            close_modal()
            self.hide_action_buttons()
            self.active_card = None
            self.show_notification(f"'{card.tree_name}' deleted")
        
        modal.ids.cancel_btn.bind(on_release=close_modal)
        modal.ids.delete_btn.bind(on_release=delete_tree)
        
        self.add_widget(modal)
        Animation(opacity=1, duration=0.2).start(modal)

    def navigate_to_image_selection(self, card):
        """Navigate to image selection screen"""
        self.selected_tree = card.tree_name
        self.manager.current = 'image_selection'

    # NOTE: on_add_tree uses the DB-backed implementation defined earlier

    def on_search_text(self, text):
        """Filter tree list based on search text"""
        tree_list = self.ids.tree_list
        tree_list.clear_widgets()
        
        search_text = text.lower().strip()
        
        if search_text:
            self.filtered_trees = [t for t in self.trees if search_text in (t['name'].lower() if isinstance(t, dict) else str(t).lower())]
        else:
            self.filtered_trees = self.trees.copy()
        
        # Hide action buttons when searching
        self.hide_action_buttons()
        self.active_card = None
        
        for name in self.filtered_trees:
            self.add_tree_item(name)
        
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