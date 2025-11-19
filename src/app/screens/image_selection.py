from kivy.uix.screenmanager import Screen
from kivy.uix.image import Image
from kivy.properties import NumericProperty, StringProperty, ListProperty
from kivy.animation import Animation
from kivy.app import App


class RecycleViewImage(Image):
    """Clickable image inside the gallery."""

    def on_touch_down(self, touch):
        """Handle image tap and navigate to the Result screen."""
        if self.collide_point(*touch.pos):
            app = App.get_running_app()
            app.last_screen = 'image_selection'
            app.root.current = 'result'
            return True
        return super().on_touch_down(touch)


class ImageSelection(Screen):
    """Main screen for selecting and filtering images."""

    highlight_x = NumericProperty(104.5 * 3 + 6)  # Starting position for highlight under 'All Photos'
    active_filter = StringProperty("All Photos")
    displayed_images = ListProperty([])

    def on_kv_post(self, base_widget):
        """Initialize the screen once KV layout is loaded."""
        # Only attempt to update images if the KV ids have been populated.
        try:
            # Do not populate placeholders here. Only populate when a tree
            # is selected (ImageSelectionScreen.on_enter will call populate).
            pass
        except Exception:
            # In unit tests the `ids` dict may behave differently; skip update.
            pass

    def move_highlight(self, filter_name):
        """Move the highlight bar and refresh displayed images."""
        filter_positions = {
            "Years": 0,
            "Months": 1,
            "Days": 2,
            "All Photos": 3,
        }

        index = filter_positions.get(filter_name, 3)
        new_x = 104.5 * index + 6

        # Animate highlight bar movement
        Animation.cancel_all(self, 'highlight_x')
        anim = Animation(highlight_x=new_x, duration=0.25, t='out_quad')
        anim.start(self)

        # Update the active filter and displayed images
        self.active_filter = filter_name
        self.update_images(filter_name)

    def update_images(self, filter_name):
        """Update the grid. If a tree is selected, load its records from DB.
        Otherwise, do not show placeholders — image selection should only
        display already-scanned images tied to a tree."""
        app = None
        try:
            app = App.get_running_app()
        except Exception:
            app = None

        # If a tree is selected, request its records from DB and populate
        # the gallery from the returned record file paths.
        if app and getattr(app, 'selected_tree_id', None):
            def _on_records(records):
                # records expected as list of dicts with 'image_path' keys
                imgs = []
                for r in records:
                    if isinstance(r, dict) and r.get('image_path'):
                        imgs.append(r['image_path'])
                # If no images found, fallback to a small placeholder grid
                if not imgs:
                    imgs = ["app/assets/placeholder_gallery.png"]
                self.displayed_images = imgs
                self.refresh_gallery()

            try:
                app.db_manager.get_records_for_tree_async(app.selected_tree_id, on_success_callback=_on_records)
                return
            except Exception:
                # If DB call fails, fall through to placeholder fallback
                pass

        # If no tree is selected, keep the grid empty — this ensures the
        # screen only shows already-scanned images for a specific tree.
        self.displayed_images = []
        try:
            # If a RecycleView exists, clear its data
            rv = self.ids.get('image_rv')
            if rv is not None:
                rv.data = []
                try:
                    rv.refresh_from_data()
                except Exception:
                    pass
        except Exception:
            pass

    def refresh_gallery(self):
        """Rebuild the gallery grid with fade-in animations."""
        # Guard access to `image_grid` because unit tests may not load KV rules.
        try:
            grid = self.ids.image_grid
        except Exception:
            return

        try:
            grid.clear_widgets()
        except Exception:
            # If clearing widgets isn't available in the test harness, skip.
            return

        for i, src in enumerate(self.displayed_images):
            img = RecycleViewImage(
                source=src,
                size_hint=(None, None),
                size=(156, 133),
                opacity=0
            )
            grid.add_widget(img)

            # Fade in each image with a small delay for a smooth effect
            delay = i * 0.04
            anim = Animation(opacity=1, duration=0.3, t='out_quad')
            anim.start(img)
