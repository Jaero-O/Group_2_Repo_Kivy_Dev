"""Add Tree Modal - Add new tree with extended fields."""
from kivy.uix.modalview import ModalView
from kivy.properties import ObjectProperty, StringProperty
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.lang import Builder
from app.core.db import insert_tree, get_all_tree_names
import os

# Load the KV file
kv_path = os.path.join(os.path.dirname(__file__), 'AddTreeModal.kv')
Builder.load_file(kv_path)


class AddTreeModal(ModalView):
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
        self._error_hide_event = None
    
    def show_error(self, message):
        """Show error message with auto-hide after 3 seconds."""
        # Cancel any existing hide event
        if self._error_hide_event:
            self._error_hide_event.cancel()
        
        # Set error message and show it
        self.ids.error_label.text = message
        Animation(opacity=1, duration=0.3).start(self.ids.error_label)
        
        # Schedule auto-hide after 3 seconds
        self._error_hide_event = Clock.schedule_once(self.hide_error, 3.0)
    
    def hide_error(self, *args):
        """Hide error message with fade animation."""
        Animation(opacity=0, duration=0.3).start(self.ids.error_label)
        self._error_hide_event = None
    
    def validate_name(self, name: str) -> tuple:
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
    
    def add_tree(self):
        """Validate inputs and add tree to database."""
        name = self.ids.name_input.text.strip()
        location = self.ids.location_input.text.strip() or None
        variety = self.ids.variety_input.text.strip() or None
        
        # Validate name
        is_valid, error = self.validate_name(name)
        if not is_valid:
            self.show_error(error)
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
                self.show_error("Failed to add tree to database")
        except Exception as e:
            self.show_error(f"Error: {str(e)}")
    
    def cancel(self):
        """Close dialog without saving."""
        self.dismiss()