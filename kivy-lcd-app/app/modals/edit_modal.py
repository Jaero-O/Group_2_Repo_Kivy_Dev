"""Edit Modal - Dialog for editing tree names."""
from kivy.uix.modalview import ModalView
from kivy.properties import ObjectProperty, StringProperty
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.lang import Builder
import os

# Load the KV file
kv_path = os.path.join(os.path.dirname(__file__), 'EditModal.kv')
Builder.load_file(kv_path)


class EditModal(ModalView):
    """Modal for editing tree names.
    
    Allows user to edit a tree's name with validation and database update.
    """
    
    callback = ObjectProperty(None)
    tree_name = StringProperty("")
    tree_id = ObjectProperty(None)
    original_name = StringProperty("")
    
    def __init__(self, tree_name, tree_id, callback=None, **kwargs):
        super().__init__(**kwargs)
        self.tree_name = tree_name
        self.original_name = tree_name
        self.tree_id = tree_id
        self.callback = callback
        self._error_hide_event = None
        
        # Set focus to input after modal opens
        Clock.schedule_once(self._set_focus, 0.1)
    
    def _set_focus(self, dt):
        """Set focus to the name input field."""
        if 'name_input' in self.ids:
            self.ids.name_input.focus = True
            # Select all text
            self.ids.name_input.select_all()
    
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
        from app.core.db import get_all_tree_names
        
        # Check if empty
        if not name or not name.strip():
            return False, "Tree name is required"
        
        # Check if unchanged
        if name.strip() == self.original_name:
            return False, "Name unchanged"
        
        # Check length
        if len(name.strip()) < 2:
            return False, "Tree name must be at least 2 characters"
        
        # Check uniqueness
        existing_names = get_all_tree_names()
        if name.strip() in existing_names:
            return False, f"Tree '{name.strip()}' already exists"
        
        return True, ""
    
    def save_changes(self):
        """Validate and save the edited tree name."""
        from app.core.db import update_tree_name
        
        new_name = self.ids.name_input.text.strip()
        
        # Validate name
        is_valid, error = self.validate_name(new_name)
        if not is_valid:
            self.show_error(error)
            return
        
        # Update in database
        try:
            success = update_tree_name(self.tree_id, new_name)
            
            if success:
                # Call callback with success and new name
                if self.callback:
                    self.callback(True, new_name, self.original_name)
                self.dismiss()
            else:
                self.show_error("Failed to update tree name")
        except Exception as e:
            self.show_error(f"Error: {str(e)}")
    
    def cancel(self):
        """Close modal without saving."""
        if self.callback:
            self.callback(False, self.original_name, self.original_name)
        self.dismiss()