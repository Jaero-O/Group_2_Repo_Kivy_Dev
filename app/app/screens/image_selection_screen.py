from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.behaviors import ButtonBehavior
from kivy.properties import StringProperty, ObjectProperty, ListProperty
from kivy.uix.image import AsyncImage
from kivy.clock import Clock

# Import the global database manager
from app.app.core import db_manager

class RecycleViewImage(ButtonBehavior, AsyncImage): # This is the viewclass for the RecycleView
    """
    An image that acts like a button, used in the image grid.
    It holds the record data associated with the image.
    The 'record_data' property is automatically populated by the RecycleView
    from the 'data' list.
    """
    record_data = ObjectProperty(None)

class ImageSelectionScreen(Screen):
    """
    Displays a grid of scanned images for a specific tree.
    """
    tree_name = StringProperty("Scans")

    def on_enter(self, *args):
        """
        Called when the screen is entered. Fetches and displays scans
        for the selected tree.
        """
        app = App.get_running_app()
        tree_id = getattr(app, 'selected_tree_id', None)

        if tree_id is None:
            print("Error: No tree_id found. Returning to records screen.")
            self.manager.current = 'records'
            return

        # Fetch scans for the given tree_id
        db_manager.get_records_for_tree_async(
            tree_id,
            on_success_callback=self.populate_image_grid,
            on_error_callback=lambda msg: print(f"Error fetching scans: {msg}")
        )

    def populate_image_grid(self, records_data):
        """
        Populates the RecycleView with data from the fetched records.
        `records_data` is a list of dictionaries, where the first element
        is the list of records and the second is the tree name.
        """
        records, tree_name = records_data
        self.tree_name = tree_name if tree_name else "Scans"
        
        rv = self.ids.image_rv

        # The data for the RecycleView is a list of dictionaries.
        # Each dictionary's keys will be mapped to the properties of the viewclass (RecycleViewImage).
        # We also add an on_release event to each item.
        rv.data = [
            {'record_data': record, 'source': record['image_path'], 'on_release': lambda r=record: self.view_record_details(r)}
            for record in records
        ]
        rv.refresh_from_data()

    def view_record_details(self, record_data):
        """
        Navigates to the ResultScreen to show details for the selected scan.
        """
        app = App.get_running_app()
        record_id = record_data.get('id')

        if record_id is None:
            print("Error: Clicked record is missing an 'id'. Cannot view details.")
            return

        # Pass only the record_id. The ResultScreen will fetch the details.
        app.analysis_result = {'record_id': record_id}
        self.manager.current = 'result'