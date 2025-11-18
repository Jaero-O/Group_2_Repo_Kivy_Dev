import unittest
import os
import sys
from unittest.mock import MagicMock, patch

# Add project and src directories to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from src.app.screens.image_selection_screen import ImageSelectionScreen

class TestImageSelectionScreen(unittest.TestCase):

    def setUp(self):
        """Set up a clean ImageSelectionScreen instance before each test."""
        self.patcher_app = patch('src.app.screens.image_selection_screen.App')
        mock_App = self.patcher_app.start()
        self.addCleanup(self.patcher_app.stop)

        self.mock_app = MagicMock()
        self.mock_app.db_manager = MagicMock()
        mock_App.get_running_app.return_value = self.mock_app

        self.screen = ImageSelectionScreen(name='image_selection')
        self.screen.manager = MagicMock()
        # Mock the RecycleView and its data property
        self.mock_rv = MagicMock()
        self.screen.ids = {
            'image_rv': self.mock_rv
        }

    def test_on_enter_fetches_records_for_selected_tree(self):
        """Test that on_enter calls the DB to get records for the selected tree."""
        self.mock_app.selected_tree_id = 5

        self.screen.on_enter()

        self.mock_app.db_manager.get_records_for_tree_async.assert_called_once_with(
            5,
            on_success_callback=self.screen.populate_image_grid,
            on_error_callback=unittest.mock.ANY
        )

    def test_on_enter_no_tree_id_navigates_back(self):
        """Test that the screen navigates back if no tree ID is set."""
        self.mock_app.selected_tree_id = None

        self.screen.on_enter()

        # Verify no DB call was made
        self.mock_app.db_manager.get_records_for_tree_async.assert_not_called()
        # Verify it navigated back to the records screen
        self.assertEqual(self.screen.manager.current, 'records')

    def test_populate_image_grid_sets_data(self):
        """Test that the RecycleView data is populated correctly."""
        mock_records = [
            {'id': 1, 'image_path': '/path/1.jpg'},
            {'id': 2, 'image_path': '/path/2.jpg'}
        ]
        # The callback receives a tuple: (records, tree_name)
        records_data = (mock_records, "My Test Tree")

        self.screen.populate_image_grid(records_data)

        # Assert that the screen's title was updated
        self.assertEqual(self.screen.tree_name, "My Test Tree")
        # Assert that the RecycleView's data property was set
        self.assertEqual(len(self.screen.ids.image_rv.data), 2)
        # Check the structure of the first item
        first_item = self.screen.ids.image_rv.data[0]
        self.assertEqual(first_item['source'], '/path/1.jpg')
        self.assertEqual(first_item['record_data'], mock_records[0])

    def test_view_record_details_navigates_to_result(self):
        """Test that clicking an image navigates to the ResultScreen with the correct ID."""
        record_to_view = {'id': 101, 'image_path': '/path/101.jpg'}

        self.screen.view_record_details(record_to_view)

        # Assert that the app's analysis_result was set with the record_id
        self.assertEqual(self.mock_app.analysis_result, {'record_id': 101})
        # Assert that the screen manager was told to navigate to the result screen
        self.assertEqual(self.screen.manager.current, 'result')

if __name__ == '__main__':
    unittest.main()