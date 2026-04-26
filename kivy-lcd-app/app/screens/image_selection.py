"""Image Selection Screen - Filter buttons open modals instead of dropdowns."""
from kivy.uix.screenmanager import Screen
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.properties import (
    NumericProperty, StringProperty, ListProperty,
    BooleanProperty, DictProperty, ObjectProperty
)
from kivy.animation import Animation
from kivy.app import App
import os
from kivy.clock import Clock


class FilterButton(Button):
    """Custom button for filters — styled via KV."""
    pass


class RecycleViewImage(Image):
    """Clickable image inside the gallery."""
    scan_data = DictProperty({})

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            app = App.get_running_app()
            app.last_screen = 'image_select'
            scan_id = self.scan_data.get("id")
            if scan_id:
                app.current_scan_id = scan_id
            else:
                app.current_scan_id = None
                app.scan_result = {
                    "label": self.scan_data.get("disease_name") or "",
                    "confidence": 0.0,
                    "severity_percentage": self.scan_data.get("severity_percentage") or 0.0,
                    "image_path": self.scan_data.get("image_path") or "",
                    "severity_level": self.scan_data.get("severity_name") or "Unknown",
                    "scan_timestamp": self.scan_data.get("scan_timestamp") or "N/A",
                }
            app.root.current = 'result'
            return True
        return super().on_touch_down(touch)


class ImageSelection(Screen):
    displayed_images = ListProperty([])
    scans_cache = []
    page_size = 50
    current_offset = 0
    has_more = BooleanProperty(True)

    selected_disease = StringProperty("All Diseases")
    selected_date_range = StringProperty("All Time")
    sort_order = StringProperty("newest")
    date_range_start = ObjectProperty(None, allownone=True)
    date_range_end = ObjectProperty(None, allownone=True)
    is_loading = BooleanProperty(False)
    tree_id = ObjectProperty(None, allownone=True)
    tree_name = StringProperty("")

    def on_pre_enter(self, *args):
        app = App.get_running_app()
        self.tree_id = getattr(app, 'selected_tree_id', None)
        self.tree_name = getattr(app, 'current_tree_name', '')
        self.current_offset = 0
        self.has_more = True
        self.selected_disease = "All Diseases"
        self.selected_date_range = "All Time"
        self.sort_order = "newest"
        self._sync_button_labels()
        self.update_images(reset=True)

    # ------------------------------------------------------------------ #
    #  Button label sync helper
    # ------------------------------------------------------------------ #
    def _sync_button_labels(self):
        self.ids.disease_btn.text = "Disease"
        self.ids.date_btn.text = "Date"
        self.ids.sort_btn.text = "Sort"

    # ------------------------------------------------------------------ #
    #  Modal openers
    # ------------------------------------------------------------------ #
    def show_disease_modal(self):
        from app.modals.image_filter_modal import DiseaseFilterModal
        modal = DiseaseFilterModal(
            current_selection=self.selected_disease,
            callback=self._on_disease_selected
        )
        modal.open()

    def _on_disease_selected(self, disease_name):
        self.selected_disease = disease_name
        if disease_name == "All Diseases":
            self.ids.disease_btn.text = "Disease"
        else:
            self.ids.disease_btn.text = (
                disease_name[:8] + ".." if len(disease_name) > 8 else disease_name
            )
        self.update_images(reset=True)

    def show_date_modal(self):
        from app.modals.image_filter_modal import DateFilterModal
        modal = DateFilterModal(
            current_selection=self.selected_date_range,
            callback=self._on_date_selected
        )
        modal.open()

    def _on_date_selected(self, preset, start, end):
        self.selected_date_range = preset
        self.date_range_start = start
        self.date_range_end = end
        self.ids.date_btn.text = "Date" if preset == "All Time" else preset[:8] + ".."
        self.update_images(reset=True)

    def show_sort_modal(self):
        from app.modals.image_filter_modal import SortFilterModal
        modal = SortFilterModal(
            current_selection=self.sort_order,
            callback=self._on_sort_selected
        )
        modal.open()

    def _on_sort_selected(self, sort_key, display_text):
        self.sort_order = sort_key
        self.ids.sort_btn.text = "Sort" if sort_key == "newest" else display_text[:8] + ".."
        self.update_images(reset=True)

    # ------------------------------------------------------------------ #
    #  Custom date picker (calendar icon button)
    # ------------------------------------------------------------------ #
    def open_custom_date_picker(self):
        from app.modals.custom_filter_modal import CustomFilterModal

        def on_date_selected(start_date, end_date):
            if start_date and end_date:
                self.date_range_start = start_date
                self.date_range_end = end_date
                self.selected_date_range = (
                    f"{start_date.strftime('%m/%d/%y')} - {end_date.strftime('%m/%d/%y')}"
                )
                self.ids.date_btn.text = self.selected_date_range[:8] + ".."
            else:
                self.date_range_start = None
                self.date_range_end = None
                self.selected_date_range = "All Time"
                self.ids.date_btn.text = "Date"
            self.update_images(reset=True)

        CustomFilterModal(callback=on_date_selected).open()

    # ------------------------------------------------------------------ #
    #  Data loading
    # ------------------------------------------------------------------ #
    def update_images(self, reset=False):
        from threading import Thread
        if self.is_loading:
            return
        if reset:
            self.current_offset = 0
        self.is_loading = True

        def load_in_background():
            from app.core.db import get_scans_filtered
            start_date = (
                self.date_range_start.strftime("%Y-%m-%d")
                if self.date_range_start else None
            )
            end_date = (
                self.date_range_end.strftime("%Y-%m-%d")
                if self.date_range_end else None
            )
            disease_filter = (
                None if self.selected_disease == "All Diseases"
                else self.selected_disease
            )

            order_by = (
                "scan_timestamp" if self.sort_order in ["newest", "oldest"]
                else "severity_percentage"
            )
            order_dir = "DESC" if self.sort_order in ["newest", "severity"] else "ASC"

            scans = get_scans_filtered(
                tree_id=self.tree_id,
                unassigned=(self.tree_name == "Unassigned Scans"),
                disease_name=disease_filter,
                start_date=start_date,
                end_date=end_date,
                limit=self.page_size,
                offset=self.current_offset,
                order_by=order_by,
                order_dir=order_dir,
            )

            images = []
            placeholder = "app/assets/placeholder_gallery.png"
            for s in scans:
                thumb = s.get('thumbnail_path')
                img_path = s.get('image_path')
                chosen = (
                    thumb if thumb and os.path.exists(thumb)
                    else (img_path if img_path and os.path.exists(img_path) else placeholder)
                )
                images.append(chosen)

            Clock.schedule_once(
                lambda dt: self._on_images_loaded(scans, images, reset), 0
            )

        Thread(target=load_in_background, daemon=True).start()

    def _on_images_loaded(self, scans, images, reset):
        self.has_more = len(scans) >= self.page_size
        if reset:
            self.scans_cache = scans
            self.displayed_images = images
            self.current_offset = len(scans)
            self.refresh_gallery()
        else:
            self.scans_cache.extend(scans)
            self.displayed_images.extend(images)
            self.current_offset += len(scans)
            self.append_gallery_images(images)
        self.is_loading = False

    # ------------------------------------------------------------------ #
    #  Gallery rendering
    # ------------------------------------------------------------------ #
    def refresh_gallery(self):
        grid = self.ids.image_grid
        grid.clear_widgets()
        for i, src in enumerate(self.displayed_images):
            img = RecycleViewImage(
                source=src, size_hint=(None, None), size=(156, 133), opacity=0
            )
            if i < len(self.scans_cache):
                img.scan_data = self.scans_cache[i]
            grid.add_widget(img)
            Animation(opacity=1, duration=0.3).start(img)

    def append_gallery_images(self, new_images):
        grid = self.ids.image_grid
        start_index = len(self.displayed_images) - len(new_images)
        for i, src in enumerate(new_images):
            img = RecycleViewImage(
                source=src, size_hint=(None, None), size=(156, 133), opacity=0
            )
            if (start_index + i) < len(self.scans_cache):
                img.scan_data = self.scans_cache[start_index + i]
            grid.add_widget(img)
            Animation(opacity=1, duration=0.3).start(img)

    def load_more(self):
        if self.has_more:
            self.update_images(reset=False)

    def on_scroll(self, scroll_y):
        if scroll_y < 0.1 and self.has_more:
            self.load_more()
