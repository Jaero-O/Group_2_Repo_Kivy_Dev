import unittest
import os
import sys
from unittest.mock import MagicMock, patch, ANY

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Add the 'src' directory to the path, mimicking main.py's behavior
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from src.app.screens.records_screen import RecordsScreen
from src.app.core.database import DatabaseManager
from kivy.clock import Clock

class TestRecordsScreen(unittest.TestCase):

    def setUp(self):
        """Set up a clean RecordsScreen instance before each test."""
        self.patcher_app = patch('src.app.screens.records_screen.App')
        mock_App = self.patcher_app.start()
        self.addCleanup(self.patcher_app.stop)

        # Mock the running app instance
        self.mock_app = MagicMock()
        # The app now holds the db_manager, so we mock it here.
        self.mock_app.db_manager = MagicMock()
        mock_App.get_running_app.return_value = self.mock_app

        # Instantiate the screen to be tested
        self.screen = RecordsScreen(name='records')
        
        # Mock the screen's manager and UI elements from the .kv file
        self.screen.manager = MagicMock()
        self.screen.ids = {
            'tree_list': MagicMock(),
            'add_input': MagicMock(text=''),
            'scroll_view': MagicMock()
        }
        self.screen.ids['tree_list'].clear_widgets = MagicMock()

    def test_on_pre_enter_fetches_all_trees(self):
        """Test that on_pre_enter calls the database to get all trees."""
        # on_enter schedules _fetch_trees, so we call it directly to test the logic
        self.screen._fetch_trees(0)
        self.mock_app.db_manager.get_all_trees_async.assert_called_once_with(
            on_success_callback=self.screen.populate_trees_list)

    def test_populate_trees_list_with_data(self):
        """Test that the UI is populated with tree items."""
        with patch.object(self.screen, 'add_tree_item', new_callable=MagicMock) as mock_add_item:
            mock_trees = [{'id': 1, 'name': 'Tree One'}, {'id': 2, 'name': 'Tree Two'}]
    
            self.screen.populate_trees_list(mock_trees)
    
            self.assertEqual(self.screen.trees, mock_trees)
            self.assertEqual(mock_add_item.call_count, 2)
            mock_add_item.assert_any_call(mock_trees[0])
            mock_add_item.assert_any_call(mock_trees[1])

    def test_populate_trees_list_empty(self):
        """Test that a label is shown when no trees are found."""
        self.screen.populate_trees_list([])
        # Verify that a "No records" label was added to the list widget
        self.screen.ids.tree_list.add_widget.assert_called_once()
        # Check that the widget added is a Label with the correct text
        added_widget = self.screen.ids.tree_list.add_widget.call_args[0][0]
        self.assertEqual(added_widget.__class__.__name__, 'Label')
        self.assertEqual(added_widget.text, "No records found.")

    def test_on_search_text_filters_list(self):
        """Test the primary filtering logic."""
        search_text = "two"
        all_trees = [
            {'id': 1, 'name': 'Tree One'},
            {'id': 2, 'name': 'Tree Two'},
            {'id': 3, 'name': 'Another Tree'}
        ]
        # Mock the populate_trees_list method to check what it's called with
        self.screen.populate_trees_list = MagicMock()

        # --- Action ---
        # This call will trigger the async DB fetch, whose callback we will test directly
        self.screen.on_search_text(search_text)

        # Now, directly call the callback that would be executed by the DB manager
        self.screen.filter_and_populate(all_trees, search_text)

        # --- Assertions ---
        # Verify that populate_trees_list was called with only the filtered results
        expected_filtered_trees = [{'id': 2, 'name': 'Tree Two'}]
        self.screen.populate_trees_list.assert_called_once_with(expected_filtered_trees)
    
    def test_integration_fetch_and_display_trees(self):
        """
        Integration test to verify that real data from the DB is fetched and populates the UI.
        """
        try:
            db_manager = DatabaseManager(db_path=':memory:', synchronous=True)
            db_manager.initialize_database()
            db_manager.add_tree_sync("Garden Tree")
            db_manager.add_tree_sync("Orchard Tree")
            
            # Mock the app instance to return our real DB manager
            mock_app_instance = MagicMock()
            mock_app_instance.db_manager = db_manager

            # Patch the RecordTreeItem class to monitor its creation
            with patch('src.app.screens.records_screen.RecordTreeItem', new_callable=MagicMock) as mock_RecordTreeItem, \
                 patch('src.app.screens.records_screen.App.get_running_app', return_value=mock_app_instance):
                
                screen = RecordsScreen(name='records')
                screen.manager = MagicMock()
                screen.ids = {
                    'tree_list': MagicMock(),
                    'add_input': MagicMock(text=''),
                    'scroll_view': MagicMock()
                }
                screen.ids['tree_list'].clear_widgets = MagicMock()
                # IMPORTANT: Use a real list to track added widgets, not a mock.
                added_widgets = []
                screen.ids['tree_list'].add_widget.side_effect = added_widgets.append

                # Action: Directly call the method that fetches data.
                # In sync mode, this will immediately call populate_trees_list.
                screen._fetch_trees(0)

                # Assertions
                self.assertEqual(len(screen.trees), 2, "Screen's internal list should contain 2 trees.")
                self.assertEqual(screen.trees[0]['name'], 'Garden Tree')
                self.assertEqual(screen.trees[1]['name'], 'Orchard Tree')

                # Verify that the UI widget was created for each tree
                self.assertEqual(mock_RecordTreeItem.call_count, 2, "RecordTreeItem should be instantiated twice.")
                self.assertEqual(len(added_widgets), 2, "Two widgets should be added to the UI list.")
        except Exception as e:
            self.fail(f"Integration test failed with exception: {e}")

    def test_integration_add_tree_and_update_ui(self):
        """
        Integration test to verify that adding a tree via the UI correctly
        updates the database and the screen's display.
        """
        try:
            db_manager = DatabaseManager(db_path=':memory:', synchronous=True)
            db_manager.initialize_database()
            
            mock_app_instance = MagicMock()
            mock_app_instance.db_manager = db_manager

            with patch('src.app.screens.records_screen.RecordTreeItem', new_callable=MagicMock) as mock_RecordTreeItem, \
                 patch('src.app.screens.records_screen.App.get_running_app', return_value=mock_app_instance):
                screen = RecordsScreen(name='records')
                screen.manager = MagicMock()
                screen.ids = {
                    'tree_list': MagicMock(),
                    'add_input': MagicMock(text=''),
                    'scroll_view': MagicMock()
                }
                # Make clear_widgets actually clear our tracking list
                screen.ids['tree_list'].clear_widgets = MagicMock(side_effect=lambda: added_widgets.clear())

                added_widgets = []
                screen.ids['tree_list'].add_widget.side_effect = added_widgets.append

                # 1. Load initial (empty) state by calling the fetch method directly
                screen._fetch_trees(0)
                self.assertEqual(len(screen.trees), 0, "Initially, the tree list should be empty.")
                self.assertEqual(len(added_widgets), 1, "A 'No records' label should be present initially.")
                # The widget is a real Label, not a mock. Let's check its class name.
                self.assertEqual(added_widgets[0].__class__.__name__, 'Label')

                # 2. Action: Simulate user typing and adding a new tree
                screen.ids.add_input.text = "New Garden Tree"
                screen.on_add_tree()

                # 3. Assertions (after the async add completes)
                self.assertEqual(len(screen.trees), 1, "Screen's internal list should be updated with the new tree.")
                self.assertEqual(screen.trees[0]['name'], "New Garden Tree", "The new tree's name is incorrect.")
                # The list is cleared, then the new item is added.
                self.assertEqual(mock_RecordTreeItem.call_count, 1, "A new RecordTreeItem should have been created.")
                # The list had 1 item ("No records"), was cleared, then 1 new item was added.
                self.assertEqual(len(added_widgets), 1, "Widget list should be cleared and contain only the new item.")
        except Exception as e:
            self.fail(f"Integration test failed with exception: {e}")

    def test_view_tree_scans_navigates_correctly(self):
        """Test that selecting a tree navigates to the image selection screen."""
        tree_to_view = {'id': 5, 'name': 'Test Tree'}
        self.screen.view_tree_scans(tree_to_view)

        # Assert that the app's selected_tree_id property was set
        self.assertEqual(self.mock_app.selected_tree_id, 5)
        # Assert that the screen manager was told to navigate
        self.assertEqual(self.screen.manager.current, 'image_selection')

if __name__ == '__main__':
    unittest.main()