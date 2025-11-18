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

from src.app.screens.save_screen import SaveScreen

class TestSaveScreen(unittest.TestCase):

    def setUp(self):
        """Set up a clean SaveScreen instance before each test."""
        # Patch the App class where it's used in the save_screen module
        self.patcher_app = patch('src.app.screens.save_screen.App')
        mock_App = self.patcher_app.start()
        self.addCleanup(self.patcher_app.stop)

        # Mock the running app instance and its properties
        self.mock_app = MagicMock()
        # The app now holds the db_manager, so we mock it here.
        self.mock_app.db_manager = MagicMock()
        self.mock_app.analysis_result = {
            'image_path': '/path/to/test.jpg',
            'disease_name': 'Anthracnose',
            'severity_name': 'Early Stage',
            'severity_percentage': 15.5
        }
        mock_App.get_running_app.return_value = self.mock_app

        # Instantiate the screen to be tested
        self.screen = SaveScreen(name='save')
        
        # Mock the screen's manager and UI elements from the .kv file
        self.screen.manager = MagicMock()
        self.screen.ids = {
            'tree_list': MagicMock(),
            'add_input': MagicMock(text=''),
            'scroll_view': MagicMock()
        }
        # The clear_widgets method is important for list updates
        self.screen.ids['tree_list'].clear_widgets = MagicMock()

    def test_on_pre_enter_fetches_trees(self):
        """Test that on_pre_enter calls the database to get all trees."""
        # The on_pre_enter event in the KV file calls build_tree_list
        self.screen.build_tree_list()
        self.mock_app.db_manager.get_all_trees_async.assert_called_once_with(self.screen.on_trees_loaded)

    def test_on_trees_loaded_populates_list(self):
        """Test that the tree list is populated when trees are loaded from the DB."""
        with patch.object(self.screen, 'add_tree_item', new_callable=MagicMock) as mock_add_item:
            mock_trees = [{'id': 1, 'name': 'Tree One'}, {'id': 2, 'name': 'Tree Two'}]
    
            # Call the callback method directly
            self.screen.on_trees_loaded(mock_trees)
    
            # Assert that the internal list is populated
            self.assertEqual(self.screen.trees, mock_trees)
            # Assert that add_tree_item was called for each tree
            self.assertEqual(mock_add_item.call_count, 2)
            mock_add_item.assert_any_call(mock_trees[0])
            mock_add_item.assert_any_call(mock_trees[1])

    def test_select_tree_updates_state(self):
        """Test that selecting a tree updates the screen's state and UI."""
        # Use a patch context to ensure mocks are isolated to this test
        with patch('kivy.uix.boxlayout.BoxLayout', new_callable=MagicMock) as MockBox:
            # Mock a widget passed to the select_tree method
            mock_box = MockBox()
            # Mock the nested properties that will be accessed *inside* the patch context
            mock_box.border_color = MagicMock()
            mock_box.border_line.width = 1
            # Add the mock widget to the tree_list to simulate the UI
            self.screen.ids.tree_list.children = [MagicMock(children=[mock_box])]
    
            tree_to_select = {'id': 1, 'name': 'Selected Tree'}
            self.screen.select_tree(mock_box, tree_to_select)
 
            # Assert that the screen's selected_tree property is updated
            self.assertEqual(self.screen.selected_tree, tree_to_select)
            # Assert that the visual state of the widget was changed
            self.assertEqual(mock_box.border_line.width, 2)

    def test_add_tree_success(self):
        """Test adding a new, unique tree."""
        self.screen.on_trees_loaded([]) # Initialize the trees list
        self.screen.trees = [] # Start with an empty list of trees
        self.screen.ids.add_input.text = 'New Tree'
        self.screen.show_modal = MagicMock() # Mock the modal popup

        self.screen.on_add_tree()

        self.mock_app.db_manager.add_tree_async.assert_called_once_with('New Tree', self.screen.on_tree_added)

    def test_add_tree_duplicate_fails(self):
        """Test that adding a duplicate tree name is prevented."""
        self.screen.on_trees_loaded([{'id': 1, 'name': 'Existing Tree'}]) # Initialize the trees list
        self.screen.trees = [{'id': 1, 'name': 'Existing Tree'}]
        self.screen.ids.add_input.text = 'Existing Tree'
        self.screen.show_modal = MagicMock()

        self.screen.on_add_tree()

        # The database should NOT be called if a duplicate is found
        self.mock_app.db_manager.add_tree_async.assert_not_called()
        # A modal should be shown to the user
        self.screen.show_modal.assert_called_with("'Existing Tree' already exists!", show_buttons=False)

    def test_on_save_button_no_tree_selected(self):
        """Test that save is blocked if no tree is selected."""
        self.screen.selected_tree = None
        self.screen.show_modal = MagicMock()

        self.screen.on_save_button()

        # The database save method should not be called
        self.mock_app.db_manager.save_record_async.assert_not_called()
        # A modal should be shown to the user
        self.screen.show_modal.assert_called_with("Please select a tree first", show_buttons=False)

    def test_on_save_button_success(self):
        """Test the full save process on success."""
        # --- Setup ---
        self.screen.selected_tree = {'id': 1, 'name': 'My Tree'}
        self.screen.show_modal = MagicMock()
        
        # Mock the return value for the lookup IDs
        self.mock_app.db_manager.get_lookup_ids.return_value = (1, 2) # (disease_id, severity_id)

        # --- Action ---
        self.screen.on_save_button()

        # --- Assertions ---
        # 1. Verify that get_lookup_ids was called with the correct names
        self.mock_app.db_manager.get_lookup_ids.assert_called_once_with(
            disease_name='Anthracnose',
            severity_name='Early Stage'
        )

        # 2. Verify that save_record_async was called with all the correct data
        self.mock_app.db_manager.save_record_async.assert_called_once_with(
            tree_id=1,
            disease_id=1,
            severity_level_id=2,
            severity_percentage=15.5,
            image_path='/path/to/test.jpg',
            on_success_callback=self.screen.on_save_success,
            on_error_callback=self.screen.on_save_error
        )

if __name__ == '__main__':
    unittest.main()