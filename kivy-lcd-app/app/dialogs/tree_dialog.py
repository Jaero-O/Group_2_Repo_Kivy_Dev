"""Tree Input Dialog - Add new tree with extended fields."""
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.properties import ObjectProperty, StringProperty
from app.core.db import insert_tree, get_all_tree_names


class TreeDialog(Popup):
    """Dialog for adding a new tree with extended fields.
    
    Fields:
    - Name (required, unique)
    - Location (optional)
    - Variety (optional)
    """
    
    callback = ObjectProperty(None)
    error_message = StringProperty("")
    
    def __init__(self, callback=None, **kwargs):
        super().__init__(**kwargs)
        self.callback = callback
        self.title = "Add New Tree"
        self.size_hint = (0.85, 0.6)
        self.auto_dismiss = False
        
        # Build UI
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Error label
        self.error_label = Label(
            text="",
            color=(1, 0.3, 0.3, 1),
            size_hint_y=0.1,
            font_size='14sp'
        )
        content.add_widget(self.error_label)
        
        # Name field (required)
        name_box = BoxLayout(orientation='horizontal', size_hint_y=0.2, spacing=10)
        name_box.add_widget(Label(text='Name*:', size_hint_x=0.3, halign='right'))
        self.name_input = TextInput(
            hint_text='Enter tree name (required)',
            multiline=False,
            size_hint_x=0.7
        )
        name_box.add_widget(self.name_input)
        content.add_widget(name_box)
        
        # Location field (optional)
        location_box = BoxLayout(orientation='horizontal', size_hint_y=0.2, spacing=10)
        location_box.add_widget(Label(text='Location:', size_hint_x=0.3, halign='right'))
        self.location_input = TextInput(
            hint_text='e.g., North Field, Row 3',
            multiline=False,
            size_hint_x=0.7
        )
        location_box.add_widget(self.location_input)
        content.add_widget(location_box)
        
        # Variety field (optional)
        variety_box = BoxLayout(orientation='horizontal', size_hint_y=0.2, spacing=10)
        variety_box.add_widget(Label(text='Variety:', size_hint_x=0.3, halign='right'))
        self.variety_input = TextInput(
            hint_text='e.g., Carabao, Kent, Alphonso',
            multiline=False,
            size_hint_x=0.7
        )
        variety_box.add_widget(self.variety_input)
        content.add_widget(variety_box)
        
        # Info label
        info_label = Label(
            text='* Required field\nName must be unique',
            color=(0.7, 0.7, 0.7, 1),
            size_hint_y=0.15,
            font_size='12sp',
            halign='center'
        )
        content.add_widget(info_label)
        
        # Buttons
        button_box = BoxLayout(size_hint_y=0.15, spacing=10)
        
        cancel_btn = Button(
            text='Cancel',
            on_press=self.cancel
        )
        button_box.add_widget(cancel_btn)
        
        add_btn = Button(
            text='Add Tree',
            background_color=(0.2, 0.7, 0.3, 1.0),
            on_press=self.add_tree
        )
        button_box.add_widget(add_btn)
        
        content.add_widget(button_box)
        
        self.content = content
    
    def validate_name(self, name: str) -> tuple[bool, str]:
        """Validate tree name.
        
        Returns:
            (is_valid, error_message)
        """
        # Check if empty
        if not name or not name.strip():
            return False, "Tree name is required"
        
        # Check length
        if len(name.strip()) < 2:
            return False, "Tree name must be at least 2 characters"
        
        # Check uniqueness
        existing_names = get_all_tree_names()
        if name.strip() in existing_names:
            return False, f"Tree '{name.strip()}' already exists"
        
        return True, ""
    
    def add_tree(self, instance):
        """Validate inputs and add tree to database."""
        name = self.name_input.text.strip()
        location = self.location_input.text.strip() or None
        variety = self.variety_input.text.strip() or None
        
        # Validate name
        is_valid, error = self.validate_name(name)
        if not is_valid:
            self.error_label.text = error
            return
        
        # Insert into database
        try:
            tree_id = insert_tree(name, location, variety)
            
            if tree_id:
                # Success - call callback and close
                if self.callback:
                    self.callback(tree_id, name, location, variety)
                self.dismiss()
            else:
                self.error_label.text = "Failed to add tree to database"
        except Exception as e:
            self.error_label.text = f"Error: {str(e)}"
    
    def cancel(self, instance):
        """Close dialog without saving."""
        self.dismiss()
