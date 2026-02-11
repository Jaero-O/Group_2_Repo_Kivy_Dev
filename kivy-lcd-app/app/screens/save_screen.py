from kivy.uix.screenmanager import Screen
from kivy.properties import ObjectProperty, StringProperty, NumericProperty
from kivy.app import App
from kivy.animation import Animation
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.behaviors import ButtonBehavior
from kivy.clock import Clock


class TreeItem(ButtonBehavior, BoxLayout):
    pass


class ModalButton(ButtonBehavior, BoxLayout):
    pass


class SaveScreen(Screen):
    selected_tree = ObjectProperty(None, rebind=True, allownone=True)
    prediction_label = StringProperty("")
    prediction_confidence = NumericProperty(0.0)
    severity_percentage = NumericProperty(0.0)
    severity_level = StringProperty("")
    image_path = StringProperty("")
    trees_cache = []  # Class-level cache
    cache_timestamp = 0  # When cache was last updated

    def on_pre_enter(self, *args):
        self._load_scan_info()
        self.build_tree_list()

    def _load_scan_info(self):
        app = App.get_running_app()
        data = getattr(app, "scan_result", {}) or {}
        self.prediction_label = data.get("label", "")
        self.prediction_confidence = data.get("confidence", 0.0)
        self.severity_percentage = data.get("severity_percentage", 0.0)
        self.severity_level = data.get("severity_level", "")
        self.image_path = data.get("image_path", "")

    def build_tree_list(self):
        """Build tree list using cache with async refresh."""
        import time
        from threading import Thread
        from kivy.clock import Clock
        
        tree_list = self.ids.tree_list
        tree_list.clear_widgets()
        
        # Use cache if fresh (< 60 seconds old)
        cache_age = time.time() - SaveScreen.cache_timestamp
        if SaveScreen.trees_cache and cache_age < 60:
            # Use cached data
            self.trees = SaveScreen.trees_cache
            self.filtered_trees = self.trees.copy()
            self.selected_tree = None
            for t in self.trees:
                self.add_tree_item(t['name'], t['id'])
            return
        
        # Load asynchronously
        def load_in_background():
            from app.core.db import list_trees
            trees = list_trees()
            # Update cache
            SaveScreen.trees_cache = trees
            SaveScreen.cache_timestamp = time.time()
            # Schedule UI update on main thread
            Clock.schedule_once(lambda dt: self._populate_tree_list(trees), 0)
        
        # Start background load
        thread = Thread(target=load_in_background, daemon=True)
        thread.start()
    
    def _populate_tree_list(self, trees):
        """Populate tree list on main thread."""
        tree_list = self.ids.tree_list
        tree_list.clear_widgets()
        self.trees = trees
        self.filtered_trees = self.trees.copy()
        self.selected_tree = None
        for t in self.trees:
            self.add_tree_item(t['name'], t['id'])
    
    @classmethod
    def invalidate_cache(cls):
        """Invalidate tree list cache (call after adding new tree)."""
        cls.trees_cache = []
        cls.cache_timestamp = 0

    def add_tree_item(self, name, tree_id=None):
        # Create a container with padding for the border
        container = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=42,  # Increased from 38 to accommodate top/bottom padding
            padding=[3, 2, 3, 2]  # Add padding on all sides for border visibility
        )
        
        box = TreeItem(
            orientation='horizontal',
            size_hint_y=None,
            height=38,
            padding=[10, 0, 10, 0],
            on_release=lambda *_: self.select_tree(box, name, tree_id)
        )

        # Background and border setup
        with box.canvas.before:
            box.bg_color = Color(255 / 255, 255 / 255, 255 / 255, 1)
            box.bg_rect = RoundedRectangle(radius=[10], pos=box.pos, size=box.size)
            box.border_color = Color(0, 0, 0, 0.08)
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
        box.tree_name = name
        box.tree_id = tree_id
        
        # Add box to container, then container to tree_list
        container.add_widget(box)
        self.ids.tree_list.add_widget(container)

        # Fade-in animation
        container.opacity = 0
        Animation(opacity=1, duration=0.3).start(container)

    def select_tree(self, box, name, tree_id):
        # Reset colors of all items (accounting for container wrapper)
        for container in self.ids.tree_list.children:
            if hasattr(container, 'children') and len(container.children) > 0:
                child = container.children[0]
                if hasattr(child, "border_color"):
                    child.border_color.rgba = (0, 0, 0, 0.08)
                    child.border_line.width = 1

        # Highlight selected with green border
        box.border_color.rgba = (0 / 255, 152 / 255, 0 / 255, 1)
        box.border_line.width = 2
        self.selected_tree = name
        self.selected_tree_id = tree_id

    def on_add_tree(self):
        """Show dialog to add new tree with extended fields."""
        from app.dialogs.tree_dialog import TreeDialog
        
        def on_tree_added(tree_id, name, location, variety):
            '''Callback when tree is successfully added.'''
            tree_obj = {"id": tree_id, "name": name}
            self.trees.insert(0, tree_obj)
            self.filtered_trees.insert(0, tree_obj)
            self.add_tree_item(name, tree_id)
            self.show_modal(f"'{name}' added successfully!", show_buttons=False)
        
        dialog = TreeDialog(callback=on_tree_added)
        dialog.open()

    def on_search_text(self, text):
        tree_list = self.ids.tree_list
        tree_list.clear_widgets()
        search_text = text.lower().strip()
        if search_text:
            self.filtered_trees = [t for t in self.trees if search_text in t['name'].lower()]
        else:
            self.filtered_trees = self.trees.copy()
        self.selected_tree = None
        self.selected_tree_id = None
        for t in self.filtered_trees:
            self.add_tree_item(t['name'], t['id'])
        Clock.schedule_once(lambda dt: setattr(self.ids.scroll_view, 'scroll_y', 1), 0.1)

    def on_save_button(self):
        if not self.selected_tree:
            self.show_modal("Please select a tree first", show_buttons=False)
            return
        # Persist record now (deferred until user confirmation)
        self._persist_scan()
        msg_parts = [f"Leaf saved to '{self.selected_tree}'"]
        if self.prediction_label:
            msg_parts.append(f"Disease: {self.prediction_label} ({self.prediction_confidence:.2f})")
        if self.severity_level:
            msg_parts.append(f"Severity: {self.severity_level} {self.severity_percentage:.1f}%")
        message = "\n".join(msg_parts)
        self.show_modal(message, show_buttons=True)

    def _persist_scan(self):
        from app.core.db import insert_scan_record, get_or_create_disease, get_or_create_severity
        from app.core.image_thumb import generate_thumbnail
        from kivy.app import App
        
        if not getattr(self, 'selected_tree_id', None):
            return
        
        disease_id = get_or_create_disease(self.prediction_label) if self.prediction_label else None
        severity_id = get_or_create_severity(self.severity_level) if self.severity_level else None
        thumb_path = generate_thumbnail(self.image_path)
        
        # Get confidence score and leaf area from app state (set by ML predictor)
        app = App.get_running_app()
        scan_result = getattr(app, 'scan_result', {}) or {}
        confidence_score = scan_result.get('confidence', None)
        total_leaf_area = scan_result.get('total_leaf_area', None)
        lesion_area = scan_result.get('lesion_area', None)
        
        # Insert and get the scan_id
        scan_id = insert_scan_record(
            self.selected_tree_id, disease_id, severity_id, 
            self.severity_percentage, self.image_path, thumb_path, None,
            confidence_score=confidence_score,
            total_leaf_area=total_leaf_area,
            lesion_area=lesion_area
        )
        
        # Store scan_id in app state for ResultScreen
        app.current_scan_id = scan_id

    def show_modal(self, message, show_buttons=True):
        # Create overlay background
        from kivy.uix.floatlayout import FloatLayout
        
        overlay = FloatLayout(
            size_hint=(1, 1),
            opacity=0
        )
        
        with overlay.canvas.before:
            Color(0, 0, 0, 0.5)
            overlay.bg_rect = RoundedRectangle(pos=overlay.pos, size=overlay.size)
        
        overlay.bind(
            pos=lambda _, v: setattr(overlay.bg_rect, 'pos', v),
            size=lambda _, v: setattr(overlay.bg_rect, 'size', v)
        )
        
        # Create modal with dynamic height
        modal_height = 170 if show_buttons else 120
        
        modal = BoxLayout(
            orientation='vertical',
            size_hint=(None, None),
            size=(300, modal_height),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            padding=[18, 18, 18, 18],
            spacing=12
        )

        with modal.canvas.before:
            # Shadow and background
            Color(0, 0, 0, 0.25)
            modal.shadow_rect = RoundedRectangle(
                radius=[16], 
                pos=(modal.x + 2, modal.y - 4), 
                size=modal.size
            )
            Color(1, 1, 1, 1)
            modal.bg_rect = RoundedRectangle(radius=[16], pos=modal.pos, size=modal.size)

        modal.bind(
            pos=lambda _, v: (
                setattr(modal.bg_rect, 'pos', v),
                setattr(modal.shadow_rect, 'pos', (v[0] + 2, v[1] - 4))
            ),
            size=lambda _, v: (
                setattr(modal.bg_rect, 'size', v),
                setattr(modal.shadow_rect, 'size', v)
            )
        )

        if show_buttons:
            # Title label for success modal
            title_label = Label(
                text="Leaf Saved!",
                color=(3 / 255, 33 / 255, 0 / 255, 1),
                font_size=20,
                bold=True,
                size_hint_y=None,
                height=26,
                halign="center",
                valign="middle"
            )
            title_label.bind(size=lambda l, _: setattr(l, 'text_size', l.size))
            modal.add_widget(title_label)
        
        # Add spacer for non-button modals to center the message
        if not show_buttons:
            modal.add_widget(BoxLayout(size_hint_y=0.3))
        
        # Message label
        message_label = Label(
            text=message,
            color=(49 / 255, 49 / 255, 49 / 255, 1),
            font_size=15,
            bold=True,
            size_hint_y=None,
            height=40,
            halign="center",
            valign="middle"
        )
        message_label.bind(size=lambda l, _: setattr(l, 'text_size', l.size))
        modal.add_widget(message_label)
        
        # Add bottom spacer for non-button modals
        if not show_buttons:
            modal.add_widget(BoxLayout(size_hint_y=0.3))
        
        if show_buttons:
            # Buttons container
            buttons_box = BoxLayout(
                orientation='horizontal',
                size_hint_y=None,
                height=34,
                spacing=8
            )
            
            # Scan Again Button
            scan_again_btn = ModalButton()
            scan_again_btn.size_hint_x = 0.5
            scan_again_btn.bind(on_release=lambda *args: self.close_modal_and_navigate(overlay, 'scan'))
            
            with scan_again_btn.canvas.before:
                Color(241 / 255, 241 / 255, 241 / 255, 1)
                scan_again_btn.bg_rect = RoundedRectangle(
                    radius=[7], 
                    pos=scan_again_btn.pos, 
                    size=scan_again_btn.size
                )
            
            scan_again_btn.bind(
                pos=lambda _, v: setattr(scan_again_btn.bg_rect, 'pos', v),
                size=lambda _, v: setattr(scan_again_btn.bg_rect, 'size', v)
            )
            
            scan_label = Label(
                text="Scan Again",
                color=(0 / 255, 152 / 255, 0 / 255, 1),
                font_size=14,
                bold=True,
                halign="center",
                valign="middle"
            )
            scan_label.bind(size=lambda l, _: setattr(l, 'text_size', (l.width, None)))
            scan_again_btn.add_widget(scan_label)
            
            # Home Button
            home_btn = ModalButton()
            home_btn.size_hint_x = 0.5
            home_btn.bind(on_release=lambda *args: self.close_modal_and_navigate(overlay, 'home'))
            
            with home_btn.canvas.before:
                Color(0 / 255, 152 / 255, 0 / 255, 1)
                home_btn.bg_rect = RoundedRectangle(
                    radius=[7], 
                    pos=home_btn.pos, 
                    size=home_btn.size
                )
            
            home_btn.bind(
                pos=lambda _, v: setattr(home_btn.bg_rect, 'pos', v),
                size=lambda _, v: setattr(home_btn.bg_rect, 'size', v)
            )
            
            home_label = Label(
                text="Home",
                color=(1, 1, 1, 1),
                font_size=14,
                bold=True,
                halign="center",
                valign="middle"
            )
            home_label.bind(size=lambda l, _: setattr(l, 'text_size', (l.width, None)))
            home_btn.add_widget(home_label)
            
            # Add buttons to container
            buttons_box.add_widget(scan_again_btn)
            buttons_box.add_widget(home_btn)
            modal.add_widget(buttons_box)
        
        overlay.add_widget(modal)
        self.add_widget(overlay)

        # Fade in animation
        anim = Animation(opacity=1, duration=0.25)
        anim.start(overlay)
        
        # Auto-close for non-button modals
        if not show_buttons:
            Clock.schedule_once(lambda dt: self.close_modal(overlay), 2.0)
    
    def close_modal(self, overlay):
        # Close modal without navigation
        anim = Animation(opacity=0, duration=0.2)
        anim.bind(on_complete=lambda *_: self.remove_widget(overlay))
        anim.start(overlay)
    
    def close_modal_and_navigate(self, overlay, screen_name):
        # Close modal and navigate to specified screen
        anim = Animation(opacity=0, duration=0.2)
        anim.bind(on_complete=lambda *_: (
            self.remove_widget(overlay),
            setattr(self.manager, 'current', screen_name)
        ))
        anim.start(overlay)