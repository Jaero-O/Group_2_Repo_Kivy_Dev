from kivy.uix.screenmanager import Screen
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


class RecordsScreen(Screen):
    selected_tree = ObjectProperty(None, rebind=True)
    active_card = ObjectProperty(None, allownone=True)

    def on_pre_enter(self, *args):
        self.build_tree_list()

    def build_tree_list(self):
        tree_list = self.ids.tree_list
        tree_list.clear_widgets()
        self.trees = ["Kenny Tree", "Jae Tree", "Lei Tree", "Kenny Tree", "Jae Tree", "Lei Tree"]
        self.filtered_trees = self.trees.copy()
        
        # Hide action buttons initially
        self.ids.action_buttons.opacity = 0
        self.ids.action_buttons.disabled = True
        
        for name in self.trees:
            self.add_tree_item(name)

    def add_tree_item(self, name):
        # Create card
        box = RecordTreeItem(tree_name=name)
        
        # Main content container
        content_box = BoxLayout(orientation='horizontal', spacing=10)
        
        # Tree name label
        label = Label(
            text=name,
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
            color=(56/255, 73/255, 38/255, 0.7),
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
        """Highlight card and show action buttons"""
        card.is_selected = True
        
        # Change card background to match SaveScreen highlight color
        with card.canvas.before:
            from kivy.graphics import Color, RoundedRectangle, Line
            card.canvas.before.clear()
            Color(255/255, 255/255, 255/255, 1)  # Same as SaveScreen
            card.bg_rect = RoundedRectangle(
                pos=card.pos,
                size=card.size,
                radius=[11]
            )
            Color(0, 0, 0, 0.15)
            card.border = Line(
                rounded_rectangle=(card.x, card.y, card.width, card.height, 11),
                width=1.5
            )
        
        card.bind(
            pos=lambda w, v: self.update_card_graphics(w),
            size=lambda w, v: self.update_card_graphics(w)
        )
        
        # Show action buttons
        self.show_action_buttons()

    def deselect_card(self, card):
        """Remove highlight from card"""
        card.is_selected = False
        
        # Reset card background to original color
        with card.canvas.before:
            from kivy.graphics import Color, RoundedRectangle, Line
            card.canvas.before.clear()
            Color(255/255, 255/255, 255/255, 1)
            card.bg_rect = RoundedRectangle(
                pos=card.pos,
                size=card.size,
                radius=[11]
            )
            Color(0, 0, 0, 0.1)
            card.border = Line(
                rounded_rectangle=(card.x, card.y, card.width, card.height, 11),
                width=1
            )

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
        self.manager.current = 'image_select'

    def on_add_tree(self):
        """Add new tree entry"""
        new_name = self.ids.add_input.text.strip()
        if new_name:
            if new_name in self.trees:
                self.show_notification(f"'{new_name}' already exists!")
                return
            
            self.trees.append(new_name)
            self.filtered_trees.append(new_name)
            self.add_tree_item(new_name)
            self.ids.add_input.text = ''
            self.show_notification(f"'{new_name}' added successfully!")

    def on_search_text(self, text):
        """Filter tree list based on search text"""
        tree_list = self.ids.tree_list
        tree_list.clear_widgets()
        
        search_text = text.lower().strip()
        
        if search_text:
            self.filtered_trees = [t for t in self.trees if search_text in t.lower()]
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