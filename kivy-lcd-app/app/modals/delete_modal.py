"""Delete Modal - Confirmation dialog for deleting trees."""
from kivy.uix.modalview import ModalView
from kivy.properties import ObjectProperty, StringProperty
from kivy.animation import Animation
from kivy.lang import Builder
import os

# Load the KV file
kv_path = os.path.join(os.path.dirname(__file__), 'DeleteModal.kv')
Builder.load_file(kv_path)


class DeleteModal(ModalView):
    """Modal for confirming tree deletion.
    
    Shows a confirmation dialog before deleting a tree from the database.
    """
    
    callback = ObjectProperty(None)
    tree_name = StringProperty("")
    tree_id = ObjectProperty(None)
    
    def __init__(self, tree_name, tree_id, callback=None, **kwargs):
        super().__init__(**kwargs)
        self.tree_name = tree_name
        self.tree_id = tree_id
        self.callback = callback
    
    def confirm_delete(self):
        """Execute deletion and call callback."""
        from app.core.db import delete_tree
        
        success = delete_tree(self.tree_id)
        
        if self.callback:
            self.callback(success, self.tree_name)
        
        self.dismiss()
    
    def cancel(self):
        """Close modal without deleting."""
        self.dismiss()