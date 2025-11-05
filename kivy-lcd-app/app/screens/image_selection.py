from kivy.uix.screenmanager import Screen
from kivy.uix.image import Image
from kivy.properties import NumericProperty, StringProperty, ListProperty
from kivy.animation import Animation
from kivy.app import App


class RecycleViewImage(Image):
    """Clickable image inside the gallery."""
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            app = App.get_running_app()
            app.last_screen = 'image_select'  # ✅ Remember we came from image selection
            app.root.current = 'result'       # Navigate to the Result screen
            return True
        return super().on_touch_down(touch)


class ImageSelection(Screen):
    """Main image selection and filtering screen."""

    highlight_x = NumericProperty(104.5 * 3 + 6)  # Start highlight on 'All Photos'
    active_filter = StringProperty("All Photos")
    displayed_images = ListProperty([])

    def on_kv_post(self, base_widget):
        """Once KV is loaded, initialize with 'All Photos'."""
        self.update_images("All Photos")

    def move_highlight(self, filter_name):
        """Moves gray highlight and triggers image update."""
        filter_positions = {
            "Years": 0,
            "Months": 1,
            "Days": 2,
            "All Photos": 3,
        }

        index = filter_positions.get(filter_name, 3)
        new_x = 104.5 * index + 6

        # Animate gray highlight movement
        Animation.cancel_all(self, 'highlight_x')
        anim = Animation(highlight_x=new_x, duration=0.25, t='out_quad')
        anim.start(self)

        # Update the active filter and displayed images
        self.active_filter = filter_name
        self.update_images(filter_name)

    def update_images(self, filter_name):
        """Dynamically change image count based on selected filter."""
        if filter_name == "Years":
            count = 6
        elif filter_name == "Months":
            count = 4
        elif filter_name == "Days":
            count = 8
        else:  # All Photos
            count = 21

        placeholder = "app/assets/placeholder_gallery.png"
        self.displayed_images = [placeholder for _ in range(count)]

        # Refresh grid
        self.refresh_gallery()

    def refresh_gallery(self):
        """Rebuild image grid with fade-in animation."""
        grid = self.ids.image_grid
        grid.clear_widgets()

        for i, src in enumerate(self.displayed_images):
            img = RecycleViewImage(
                source=src,
                size_hint=(None, None),
                size=(156, 133),
                opacity=0
            )
            grid.add_widget(img)

            # Fade-in animation
            delay = i * 0.04
            anim = Animation(opacity=1, duration=0.3, t='out_quad')
            anim.start(img)
