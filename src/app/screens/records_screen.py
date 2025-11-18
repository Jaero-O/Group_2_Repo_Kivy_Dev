from kivy.uix.screenmanager import Screen
from kivy.animation import Animation
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.behaviors import ButtonBehavior
from kivy.clock import Clock, mainthread
from kivy.lang import Builder
from kivy.factory import Factory
from kivy.properties import ObjectProperty, StringProperty
import os # Import the os module to handle file paths


class RecordTreeItem(ButtonBehavior, BoxLayout):
    """Single record card"""
    record_data = ObjectProperty(None)
    display_name = StringProperty('') # Add property for the name

# --- SOLUTION: Register the custom widget class with Kivy's Factory ---
# This makes the class known to the .kv parser before the file is loaded.
Factory.register('RecordTreeItem', cls=RecordTreeItem)
class RecordsScreen(Screen):
    """
    A screen that displays a list of trees from the database, allows adding new ones,
    and searching through the list.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.trees = [] # Ensure the 'trees' attribute always exists.

    def on_enter(self, *args):
        """
        Called when the screen is entered. We schedule the database fetch for the next
        frame to ensure all widgets and their IDs are available.
        """
        # Using Clock.schedule_once guarantees that the ids dictionary is populated.
        Clock.schedule_once(self._fetch_trees)

    def populate_trees_list(self, trees):
        """Callback function to populate the list with trees from the DB."""
        print(f"[DEBUG] populate_trees_list received {len(trees)} trees: {trees}")
        tree_list = self.ids.tree_list
        tree_list.clear_widgets()
        self.trees = trees

        if not trees:
            no_records_label = Label(text="No records found.", color=(0.5, 0.5, 0.5, 1), font_size='18sp')
            tree_list.add_widget(no_records_label)
            return

        for tree in trees:
            self.add_tree_item(tree)

    def _fetch_trees(self, dt):
        """Initiates the asynchronous database call."""
        from kivy.app import App
        from app.core.utils import call_when_db_ready

        def _call():
            App.get_running_app().db_manager.get_all_trees_async(on_success_callback=self.populate_trees_list)

        call_when_db_ready(_call)

    def add_tree_item(self, tree_data):
        print(f"[DEBUG] add_tree_item called for: {tree_data.get('name')}")
        # Instantiate the RecordTreeItem, passing data to it.
        # The .kv file will use these properties to build the UI.
        item = RecordTreeItem(
            record_data=tree_data,
            display_name=tree_data['name'],
            on_release=lambda x: self.view_tree_scans(x.record_data)
        )
        self.ids.tree_list.add_widget(item)
        Animation(opacity=1, duration=0.3, t='out_quad').start(item)

    def view_tree_scans(self, tree_data):
        """
        Sets the selected tree and navigates to the image selection screen
        to show its associated scans.
        """
        from kivy.app import App
        app = App.get_running_app()
        app.selected_tree_id = tree_data.get('id')
        self.manager.current = 'image_selection'

    def on_search_text(self, text):
        """
        Filter the displayed tree list based on search text.
        This now filters the existing in-memory list `self.trees` instead of
        re-querying the database on every key press, which is much more efficient.
        """
        search_text = text.lower().strip()
        from kivy.app import App
        # Filter the list that's already in memory
        self.filter_and_populate(self.trees, search_text)
        Clock.schedule_once(lambda dt: setattr(self.ids.scroll_view, 'scroll_y', 1), 0.1)

    def filter_and_populate(self, trees, search_text):
        """Helper to filter trees by name before populating."""
        if search_text:
            filtered_trees = [tree for tree in trees if search_text in tree['name'].lower()]
        else:
            filtered_trees = trees
        self.populate_trees_list(filtered_trees)

    def on_add_tree(self):
        """Handles the 'on_text_validate' event from the add_input TextInput."""
        new_name = self.ids.add_input.text.strip()
        if new_name:
            # Check for duplicates
            if any(tree['name'].lower() == new_name.lower() for tree in self.trees):
                print(f"Tree '{new_name}' already exists.")
                # Optionally, show a message to the user here
                return
            from kivy.app import App
            from app.core.utils import call_when_db_ready

            def _call_add():
                App.get_running_app().db_manager.add_tree_async(new_name, self.on_tree_added)

            call_when_db_ready(_call_add)

    def on_tree_added(self, new_tree):
        """Callback function for when a new tree is successfully added to the DB."""
        print(f"[DEBUG] on_tree_added received: {new_tree}")
        if new_tree:
            # If the list was previously empty, it contains the "No records found" label.
            # We must clear it before adding the first real item.
            if not self.trees:
                self.ids.tree_list.clear_widgets()

            self.trees.append(new_tree)
            self.add_tree_item(new_tree)
            self.ids.add_input.text = ''
            # Scroll to the bottom to show the new item
            Clock.schedule_once(lambda dt: setattr(self.ids.scroll_view, 'scroll_y', 0), 0.2)