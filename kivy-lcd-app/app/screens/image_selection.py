from kivy.uix.screenmanager import Screen
from kivy.uix.image import Image
from kivy.properties import NumericProperty, StringProperty, ListProperty, BooleanProperty, DictProperty, ObjectProperty
from kivy.animation import Animation
from kivy.app import App
from kivy.uix.dropdown import DropDown
from kivy.uix.button import Button
from kivy.uix.label import Label
import os
from datetime import datetime, timedelta


class RecycleViewImage(Image):
    """Clickable image inside the gallery."""
    scan_data = DictProperty({})  # Use DictProperty instead of class variable

    def on_touch_down(self, touch):
        """Handle image tap and navigate to the Result screen."""
        if self.collide_point(*touch.pos):
            app = App.get_running_app()
            app.last_screen = 'image_select'
            
            # Populate app.scan_result with the scan data
            # Note: confidence is not stored in DB, using 0.0 as placeholder
            app.scan_result = {
                "label": self.scan_data.get("disease_name") or "",
                "confidence": 0.0,  # Not stored in database
                "severity_percentage": self.scan_data.get("severity_percentage") or 0.0,
                "image_path": self.scan_data.get("image_path") or "",
                "severity_level": self.scan_data.get("severity_name") or "Unknown",
                "scan_timestamp": self.scan_data.get("scan_timestamp") or "N/A",
            }
            
            app.root.current = 'result'
            return True
        return super().on_touch_down(touch)


class ImageSelection(Screen):
    """Main screen for selecting and filtering images with enhanced disease, date, and sort filters."""

    highlight_x = NumericProperty(104.5 * 3 + 6)  # Starting position for highlight under 'All Photos'
    active_filter = StringProperty("All Photos")
    displayed_images = ListProperty([])  # list of image paths
    scans_cache = []  # full scan dicts from DB query
    page_size = 50  # Number of images to load per page (reduced for faster loads with filters)
    current_offset = 0
    has_more = BooleanProperty(True)
    
    # Enhanced filter properties
    selected_disease = StringProperty("All Diseases")
    selected_date_range = StringProperty("All Time")
    sort_order = StringProperty("newest")  # newest, oldest, severity
    date_range_start = ObjectProperty(None, allownone=True)
    date_range_end = ObjectProperty(None, allownone=True)
    is_loading = BooleanProperty(False)
    tree_id = ObjectProperty(None, allownone=True)
    tree_name = StringProperty("")

    def on_pre_enter(self, *args):
        # Get tree context from app
        app = App.get_running_app()
        self.tree_id = getattr(app, 'selected_tree_id', None)
        self.tree_name = getattr(app, 'current_tree_name', '')
        
        # DEBUG: Print tree context
        print(f"[ImageSelection] on_pre_enter - tree_id={self.tree_id} (type={type(self.tree_id)}), tree_name='{self.tree_name}'")
        
        # Reset pagination and all filters
        self.current_offset = 0
        self.has_more = True
        self.selected_disease = "All Diseases"
        self.selected_date_range = "All Time"
        self.sort_order = "newest"
        self.date_range_start = None
        self.date_range_end = None
        self.update_images("All Photos", reset=True)

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
        self.current_offset = 0
        self.has_more = True
        
        # Clear custom date range when using preset time filters
        self.date_range_start = None
        self.date_range_end = None
        self.selected_date_range = "All Time"  # Reset to default
        
        self.update_images(filter_name, reset=True)

    def update_images(self, filter_name=None, reset=False):
        """Query DB for scans with enhanced filtering (disease, date, sort) and update gallery asynchronously.
        
        Args:
            filter_name: Time filter name (for backward compatibility)
            reset: If True, clear existing images and start from beginning
        """
        from threading import Thread
        from kivy.clock import Clock
        
        if self.is_loading:
            return
        
        if reset:
            self.current_offset = 0
        
        self.is_loading = True
        
        def load_in_background():
            from app.core.db import get_scans_filtered
            
            # Calculate date range from time filter or custom range
            start_date = None
            end_date = None
            
            if self.date_range_start and self.date_range_end:
                # Use custom date range
                start_date = self.date_range_start.strftime("%Y-%m-%d")
                end_date = self.date_range_end.strftime("%Y-%m-%d")
            elif filter_name and filter_name != "All Photos":
                # Calculate from preset filter
                today = datetime.now()
                if filter_name == "Days":
                    start_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
                elif filter_name == "Months":
                    start_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
                elif filter_name == "Years":
                    start_date = (today - timedelta(days=365)).strftime("%Y-%m-%d")
                end_date = today.strftime("%Y-%m-%d")
            
            # Apply disease filter
            disease_filter = None if self.selected_disease == "All Diseases" else self.selected_disease
            
            # Determine SQL sort order
            if self.sort_order == "newest":
                order_by = "scan_timestamp"
                order_dir = "DESC"
            elif self.sort_order == "oldest":
                order_by = "scan_timestamp"
                order_dir = "ASC"
            else:  # severity
                order_by = "severity_percentage"
                order_dir = "DESC"
            
            # Fetch paginated results with enhanced filtering
            scans = get_scans_filtered(
                tree_id=self.tree_id,
                disease_name=disease_filter,
                start_date=start_date,
                end_date=end_date,
                limit=self.page_size,
                offset=self.current_offset,
                order_by=order_by,
                order_dir=order_dir
            )
            
            # DEBUG: Print query results
            print(f"[ImageSelection] Query returned {len(scans)} scans for tree_id={self.tree_id}")
            if scans:
                print(f"  First scan: id={scans[0].get('id')}, tree_name={scans[0].get('tree_name')}, image_path={scans[0].get('image_path')}")
                print(f"  Thumbnail: {scans[0].get('thumbnail_path')}")
            
            # Process images in background (file I/O)
            images = []
            placeholder = "app/assets/placeholder_gallery.png"
            for s in scans:
                thumb = s.get('thumbnail_path') or ''
                img_path = s.get('image_path') or ''
                # Prefer thumbnail to reduce memory usage; fall back to original image then placeholder
                chosen = None
                if thumb and os.path.exists(thumb):
                    chosen = thumb
                elif img_path and os.path.exists(img_path):
                    chosen = img_path
                else:
                    chosen = placeholder
                images.append(chosen)
            
            # DEBUG: Print after processing all images
            print(f"[ImageSelection] Processed {len(images)} image paths")
            if images:
                print(f"  First image path: {images[0]}")
                print(f"  Path exists: {os.path.exists(images[0]) if images[0] != placeholder else 'N/A (placeholder)'}")
            
            # Schedule UI update on main thread
            Clock.schedule_once(lambda dt: self._on_images_loaded(scans, images, reset), 0)
        
        # Start background thread
        thread = Thread(target=load_in_background, daemon=True)
        thread.start()
    
    def _on_images_loaded(self, scans, images, reset):
        """Handle loaded images on main thread."""
        print(f"[ImageSelection] _on_images_loaded - scans={len(scans)}, images={len(images)}, reset={reset}")
        
        # Check if there are more records
        self.has_more = len(scans) >= self.page_size
        
        # Update cache and offset
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
        
        # Clear loading state
        self.is_loading = False

    def refresh_gallery(self):
        """Rebuild the gallery grid with fade-in animations."""
        print(f"[ImageSelection] refresh_gallery - displayed_images count={len(self.displayed_images)}")
        
        grid = self.ids.image_grid
        grid.clear_widgets()
        # empty_label text already bound; ensure size updates
        self.ids.empty_label.opacity = 1 if len(self.displayed_images) == 0 else 0

        for i, src in enumerate(self.displayed_images):
            img = RecycleViewImage(
                source=src,
                size_hint=(None, None),
                size=(156, 133),
                opacity=0
            )
            # Attach scan data to image widget
            if i < len(self.scans_cache):
                img.scan_data = self.scans_cache[i]
            
            grid.add_widget(img)
            anim = Animation(opacity=1, duration=0.3, t='out_quad')
            anim.start(img)
    
    def append_gallery_images(self, new_images):
        """Append new images to existing gallery without clearing."""
        grid = self.ids.image_grid
        # Calculate offset for scan data indexing
        start_index = len(self.displayed_images) - len(new_images)
        
        for i, src in enumerate(new_images):
            img = RecycleViewImage(
                source=src,
                size_hint=(None, None),
                size=(156, 133),
                opacity=0
            )
            # Attach scan data to image widget
            scan_index = start_index + i
            if scan_index < len(self.scans_cache):
                img.scan_data = self.scans_cache[scan_index]
            
            grid.add_widget(img)
            anim = Animation(opacity=1, duration=0.3, t='out_quad')
            anim.start(img)
    
    def load_more(self):
        """Load next page of images."""
        if self.has_more:
            self.update_images(self.active_filter, reset=False)
    
    def on_scroll(self, scroll_y):
        """Auto-load more when scrolling near bottom."""
        if scroll_y < 0.1 and self.has_more:  # Near bottom (scroll_y is 0 at bottom, 1 at top)
            self.load_more()
    
    def show_disease_dropdown(self):
        """Show dropdown with disease filter options."""
        from app.core.db import list_diseases
        
        dropdown = DropDown()
        
        # Add "All Diseases" option
        btn = Button(
            text="All Diseases",
            size_hint_y=None,
            height=44,
            color=(3/255, 30/255, 0/255, 1),
            font_size=16,
            bold=True,
            background_normal='',
            background_color=(248/255, 248/255, 248/255, 1) if self.selected_disease == "All Diseases" else (1, 1, 1, 1)
        )
        btn.bind(on_release=lambda b: self._select_disease("All Diseases", dropdown))
        dropdown.add_widget(btn)
        
        # Add diseases from database
        diseases = list_diseases()
        for disease in diseases:
            disease_name = disease['name']
            btn = Button(
                text=disease_name,
                size_hint_y=None,
                height=44,
                color=(3/255, 30/255, 0/255, 1),
                font_size=16,
                bold=True,
                background_normal='',
                background_color=(248/255, 248/255, 248/255, 1) if self.selected_disease == disease_name else (1, 1, 1, 1)
            )
            btn.bind(on_release=lambda b, d=disease_name: self._select_disease(d, dropdown))
            dropdown.add_widget(btn)
        
        # Open dropdown
        dropdown.open(self.ids.disease_btn)
    
    def _select_disease(self, disease_name, dropdown):
        """Handle disease selection."""
        self.selected_disease = disease_name
        self.ids.disease_btn.text = f"Disease: {disease_name}"
        dropdown.dismiss()
        self.current_offset = 0
        self.has_more = True
        self.update_images(reset=True)
    
    def show_date_dropdown(self):
        """Show dropdown with date range preset options."""
        dropdown = DropDown()
        
        presets = [
            ("All Time", "All Time"),
            ("Last 7 Days", "Last 7 Days"),
            ("Last 30 Days", "Last 30 Days"),
            ("Last 90 Days", "Last 90 Days"),
            ("Last Year", "Last Year")
        ]
        
        for display_text, value in presets:
            btn = Button(
                text=display_text,
                size_hint_y=None,
                height=44,
                color=(3/255, 30/255, 0/255, 1),
                font_size=16,
                bold=True,
                background_normal='',
                background_color=(248/255, 248/255, 248/255, 1) if self.selected_date_range == value else (1, 1, 1, 1)
            )
            btn.bind(on_release=lambda b, v=value: self._select_date_preset(v, dropdown))
            dropdown.add_widget(btn)
        
        dropdown.open(self.ids.date_btn)
    
    def _select_date_preset(self, preset, dropdown):
        """Handle date preset selection."""
        self.selected_date_range = preset
        self.ids.date_btn.text = f"Date: {preset}"
        dropdown.dismiss()
        
        # Calculate date range from preset
        today = datetime.now()
        if preset == "Last 7 Days":
            self.date_range_start = today - timedelta(days=7)
            self.date_range_end = today
        elif preset == "Last 30 Days":
            self.date_range_start = today - timedelta(days=30)
            self.date_range_end = today
        elif preset == "Last 90 Days":
            self.date_range_start = today - timedelta(days=90)
            self.date_range_end = today
        elif preset == "Last Year":
            self.date_range_start = today - timedelta(days=365)
            self.date_range_end = today
        else:  # All Time
            self.date_range_start = None
            self.date_range_end = None
        
        self.current_offset = 0
        self.has_more = True
        self.update_images(reset=True)
    
    def show_sort_dropdown(self):
        """Show dropdown with sort options."""
        dropdown = DropDown()
        
        sort_options = [
            ("Newest First", "newest"),
            ("Oldest First", "oldest"),
            ("Highest Severity", "severity")
        ]
        
        for display_text, value in sort_options:
            btn = Button(
                text=display_text,
                size_hint_y=None,
                height=44,
                color=(3/255, 30/255, 0/255, 1),
                font_size=16,
                bold=True,
                background_normal='',
                background_color=(248/255, 248/255, 248/255, 1) if self.sort_order == value else (1, 1, 1, 1)
            )
            btn.bind(on_release=lambda b, v=value, t=display_text: self._select_sort(v, t, dropdown))
            dropdown.add_widget(btn)
        
        dropdown.open(self.ids.sort_btn)
    
    def _select_sort(self, sort_value, display_text, dropdown):
        """Handle sort selection."""
        self.sort_order = sort_value
        self.ids.sort_btn.text = f"Sort: {display_text}"
        dropdown.dismiss()
        self.current_offset = 0
        self.has_more = True
        self.update_images(reset=True)
    
    def open_custom_date_picker(self):
        """Open custom date range picker dialog."""
        from app.widgets.date_range_picker import DateRangePicker
        
        def on_date_selected(start_date, end_date):
            if start_date and end_date:
                self.date_range_start = start_date
                self.date_range_end = end_date
                self.selected_date_range = f"{start_date.strftime('%m/%d/%y')} - {end_date.strftime('%m/%d/%y')}"
                self.ids.date_btn.text = f"Date: {self.selected_date_range}"
            else:
                # All Time selected
                self.date_range_start = None
                self.date_range_end = None
                self.selected_date_range = "All Time"
                self.ids.date_btn.text = "Date: All Time"
            
            self.current_offset = 0
            self.has_more = True
            self.update_images(reset=True)
        
        picker = DateRangePicker(callback=on_date_selected)
        picker.open()

