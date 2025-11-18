from kivy.uix.screenmanager import Screen
from kivy.properties import ObjectProperty
from kivy.animation import Animation
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.behaviors import ButtonBehavior
from kivy.clock import Clock, mainthread
from kivy.lang import Builder

from app.app.core import db_manager
from kivy.app import App

class RecordTreeItem(ButtonBehavior, BoxLayout):
    """Single record card"""
    record_data = ObjectProperty(None)

class RecordsScreen(Screen):
    def on_pre_enter(self, *args):
        db_manager.get_all_trees_async(on_success_callback=self.populate_trees_list)

    @mainthread
    def populate_trees_list(self, trees):
        """Callback function to populate the list with trees from the DB."""
        tree_list = self.ids.tree_list
        tree_list.clear_widgets()

        if not trees:
            no_records_label = Label(text="No records found.", color=(0.5, 0.5, 0.5, 1), font_size='18sp')
            tree_list.add_widget(no_records_label)
            return

        for tree in trees:
            self.add_tree_item(tree)

    def add_tree_item(self, tree_data):
        display_name = tree_data['name']
        box = RecordTreeItem(record_data=tree_data, on_release=lambda x: self.view_tree_scans(x.record_data))

        from kivy.graphics import Color, RoundedRectangle, Line
        with box.canvas.before:
            box.bg_color = Color(255/255, 255/255, 255/255, 1)
            box.bg_rect = RoundedRectangle(
                pos=box.pos,
                size=box.size,
                radius=[11]
            )
            box.border_color = Color(0, 0, 0, 0.1)
            box.border = Line(
                rounded_rectangle=(box.x, box.y, box.width, box.height, 11),
                width=1
            )
        
        box.bind(
            pos=lambda w, v: self.update_card_graphics(w),
            size=lambda w, v: self.update_card_graphics(w)
        )
        
        content_box = BoxLayout(orientation='horizontal', spacing=10, padding=[10, 0, 10, 0])

        label = Label(
            text=display_name,
            color=(49/255, 49/255, 49/255, 1),
            font_size=18,
            bold=True,
            halign='left',
            valign='middle',
        )
        label.bind(size=lambda l, s: setattr(l, 'text_size', (l.width, None)))
        
        content_box.add_widget(label)
        box.add_widget(content_box)
        
        self.ids.tree_list.add_widget(box)

        box.opacity = 0
        Animation(opacity=1, duration=0.3, t='out_quad').start(box)

    def update_card_graphics(self, card):
        """Update card graphics when position or size changes"""
        if hasattr(card, 'bg_rect'):
            card.bg_rect.pos = card.pos
            card.bg_rect.size = card.size
            card.border.rounded_rectangle = (card.x, card.y, card.width, card.height, 11)

    def view_tree_scans(self, tree_data):
        """
        Sets the selected tree and navigates to the image selection screen
        to show its associated scans.
        """
        app = App.get_running_app()
        app.selected_tree_id = tree_data.get('id')
        self.manager.current = 'image_selection'

    def on_search_text(self, text):
        """Filter tree list based on search text"""
        tree_list = self.ids.tree_list
        tree_list.clear_widgets()
        
        search_text = text.lower().strip()
        db_manager.get_all_trees_async(on_success_callback=lambda trees: self.filter_and_populate(trees, search_text))
        Clock.schedule_once(lambda dt: setattr(self.ids.scroll_view, 'scroll_y', 1), 0.1)

    @mainthread
    def filter_and_populate(self, trees, search_text):
        """Helper to filter trees by name before populating."""
        if search_text:
            filtered_trees = [tree for tree in trees if search_text in tree['name'].lower()]
        else:
            filtered_trees = trees
        self.populate_trees_list(filtered_trees)