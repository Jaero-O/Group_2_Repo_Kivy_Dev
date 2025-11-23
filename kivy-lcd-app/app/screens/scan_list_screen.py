"""Scan List Screen - Display scans for a selected tree."""
from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.properties import StringProperty, NumericProperty, ListProperty, BooleanProperty, ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import AsyncImage
from kivy.uix.dropdown import DropDown


class ScanCard(BoxLayout):
    """Card widget displaying scan summary."""
    scan_id = NumericProperty(0)
    disease_name = StringProperty("Unknown")
    confidence_score = NumericProperty(0.0)
    severity_percentage = NumericProperty(0.0)
    severity_name = StringProperty("")
    formatted_timestamp = StringProperty("")
    thumbnail_path = StringProperty("")
    
    def __init__(self, scan_data, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = '80dp'
        self.padding = '5dp'
        self.spacing = '10dp'
        
        # Store scan data
        self.scan_id = scan_data['id']
        self.disease_name = scan_data.get('disease_name', 'Unknown')
        self.severity_percentage = scan_data.get('severity_percentage', 0.0)
        self.severity_name = scan_data.get('severity_name', '')
        self.thumbnail_path = scan_data.get('thumbnail_path', '') or scan_data.get('image_path', '')
        
        # Format timestamp
        timestamp = scan_data.get('scan_timestamp', '')
        try:
            from datetime import datetime
            dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            self.formatted_timestamp = dt.strftime("%b %d, %Y")
        except:
            self.formatted_timestamp = timestamp
        
        # Calculate confidence (placeholder)
        self.confidence_score = 85.0
        
        # Build card UI
        self._build_ui()
    
    def _build_ui(self):
        """Build the card UI components."""
        from kivy.graphics import Color, RoundedRectangle
        
        # Background
        with self.canvas.before:
            Color(0.2, 0.2, 0.25, 1.0)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[10])
        
        self.bind(pos=self._update_rect, size=self._update_rect)
        
        # Thumbnail
        thumbnail = AsyncImage(
            source=self.thumbnail_path,
            allow_stretch=True,
            keep_ratio=True,
            size_hint_x=0.2
        )
        self.add_widget(thumbnail)
        
        # Info section
        info_layout = BoxLayout(orientation='vertical', size_hint_x=0.65, padding='5dp')
        
        # Disease name
        disease_label = Label(
            text=self.disease_name,
            bold=True,
            halign='left',
            valign='top',
            text_size=(None, None),
            size_hint_y=0.4
        )
        disease_label.bind(size=disease_label.setter('text_size'))
        info_layout.add_widget(disease_label)
        
        # Severity and confidence
        metrics_layout = BoxLayout(orientation='horizontal', size_hint_y=0.3)
        metrics_layout.add_widget(Label(
            text=f'Severity: {self.severity_percentage:.1f}%',
            halign='left',
            size_hint_x=0.5,
            color=self._get_severity_color()
        ))
        metrics_layout.add_widget(Label(
            text=f'Conf: {self.confidence_score:.0f}%',
            halign='left',
            size_hint_x=0.5
        ))
        info_layout.add_widget(metrics_layout)
        
        # Timestamp
        time_label = Label(
            text=self.formatted_timestamp,
            halign='left',
            size_hint_y=0.3,
            color=(0.7, 0.7, 0.7, 1.0)
        )
        info_layout.add_widget(time_label)
        
        self.add_widget(info_layout)
        
        # View button
        view_btn = Button(
            text='View',
            size_hint_x=0.15,
            background_color=(0.3, 0.5, 0.7, 1.0)
        )
        view_btn.bind(on_press=self.on_view_clicked)
        self.add_widget(view_btn)
    
    def _update_rect(self, *args):
        """Update background rectangle when size/position changes."""
        self.rect.pos = self.pos
        self.rect.size = self.size
    
    def _get_severity_color(self):
        """Get color based on severity level."""
        if self.severity_percentage >= 30:
            return (0.8, 0.2, 0.2, 1.0)  # Red - Advanced
        elif self.severity_percentage >= 10:
            return (1.0, 0.75, 0.0, 1.0)  # Yellow - Early
        else:
            return (0.2, 0.7, 0.3, 1.0)  # Green - Healthy
    
    def on_view_clicked(self, instance):
        """Handle view button click."""
        app = App.get_running_app()
        app.current_scan_id = self.scan_id
        app.last_screen = 'scan_list'
        app.root.current = 'scan_detail'


class ScanListScreen(Screen):
    """Display list of scans for a selected tree."""
    
    tree_id = NumericProperty(0)
    tree_name = StringProperty("Unknown Tree")
    scan_count = NumericProperty(0)
    scans = ListProperty([])
    
    # Filter properties
    selected_disease = StringProperty("All Diseases")
    selected_date_range = StringProperty("All Time")
    sort_order = StringProperty("newest")  # newest, oldest, severity
    
    # Custom date range
    date_range_start = None
    date_range_end = None
    
    # Pagination
    current_offset = NumericProperty(0)
    page_size = NumericProperty(50)
    has_more = BooleanProperty(True)
    is_loading = BooleanProperty(False)
    
    def on_pre_enter(self, *args):
        """Load scans when screen is entered."""
        # Reset filters and pagination
        self.selected_disease = "All Diseases"
        self.selected_date_range = "All Time"
        self.sort_order = "newest"
        self.date_range_start = None
        self.date_range_end = None
        self.current_offset = 0
        self.has_more = True
        self.scans = []  # Clear existing scans
        self._load_tree_scans(reset=True)
    
    def _load_tree_scans(self, reset=False):
        """Load scans for the selected tree with optional filters and pagination.
        
        Args:
            reset: If True, clear existing scans and start from offset 0
        """
        from app.core.db import get_scans_filtered, get_tree_by_name
        from threading import Thread
        from kivy.clock import Clock
        
        if self.is_loading:
            return  # Prevent duplicate loads
        
        # Get tree info from app state
        app = App.get_running_app()
        tree_name = getattr(app, 'current_tree_name', '')
        
        if not tree_name:
            self.tree_name = "No tree selected"
            self.scans = []
            return
        
        # Get tree ID
        tree_data = get_tree_by_name(tree_name)
        if not tree_data:
            self.tree_name = "Tree not found"
            self.scans = []
            return
        
        self.tree_id = tree_data['id']
        self.tree_name = tree_name
        
        if reset:
            self.current_offset = 0
            self.scans = []
        
        self.is_loading = True
        
        def load_in_background():
            """Execute database query in background thread."""
            # Apply filters
            disease_filter = None if self.selected_disease == "All Diseases" else self.selected_disease
            
            # Use custom date range if set, otherwise use preset
            start_date = None
            end_date = None
            
            if self.date_range_start and self.date_range_end:
                start_date = self.date_range_start.strftime("%Y-%m-%d")
                end_date = self.date_range_end.strftime("%Y-%m-%d")
            elif self.selected_date_range != "All Time":
                # Calculate date range from preset
                from datetime import datetime, timedelta
                today = datetime.now()
                
                if self.selected_date_range == "Last 7 Days":
                    start_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
                elif self.selected_date_range == "Last 30 Days":
                    start_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
                elif self.selected_date_range == "Last 90 Days":
                    start_date = (today - timedelta(days=90)).strftime("%Y-%m-%d")
                elif self.selected_date_range == "Last Year":
                    start_date = (today - timedelta(days=365)).strftime("%Y-%m-%d")
                
                end_date = today.strftime("%Y-%m-%d")
            
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
            
            # Load scans with filters, pagination, and SQL sorting
            scan_list = get_scans_filtered(
                tree_id=self.tree_id,
                disease_name=disease_filter,
                start_date=start_date,
                end_date=end_date,
                limit=self.page_size,
                offset=self.current_offset,
                order_by=order_by,
                order_dir=order_dir
            )
            
            # Schedule UI update on main thread
            Clock.schedule_once(lambda dt: self._on_scans_loaded(scan_list, reset), 0)
        
        # Start background thread
        thread = Thread(target=load_in_background, daemon=True)
        thread.start()
    
    def _on_scans_loaded(self, scan_list, reset):
        """Handle loaded scans on main thread."""
        if reset:
            self.scans = scan_list
        else:
            self.scans.extend(scan_list)
        
        self.scan_count = len(self.scans)
        self.has_more = len(scan_list) >= self.page_size
        self.is_loading = False
        
        # Populate the scan cards in the UI
        self._populate_scan_cards()
    
    def load_more_scans(self):
        """Load next page of scans."""
        if not self.has_more or self.is_loading:
            return
        
        self.current_offset += self.page_size
        self._load_tree_scans(reset=False)
    
    def _populate_scan_cards(self):
        """Populate the scrollable list with scan cards."""
        # Find the scans_container in the KV file
        scans_container = self.ids.get('scans_container')
        
        if not scans_container:
            return
        
        # Clear existing cards
        scans_container.clear_widgets()
        
        # Add scan cards
        if not self.scans:
            # Show empty state
            empty_label = Label(
                text="No scans found for this tree.\nCreate a new scan to get started!",
                halign='center',
                valign='middle'
            )
            scans_container.add_widget(empty_label)
        else:
            for scan_data in self.scans:
                card = ScanCard(scan_data)
                scans_container.add_widget(card)
    
    def go_back(self):
        """Navigate back to records screen."""
        self.manager.current = 'records'
    
    def start_new_scan(self):
        """Navigate to scan screen to create new scan for this tree."""
        app = App.get_running_app()
        # Set context so SaveScreen knows which tree to use
        app.preselected_tree_name = self.tree_name
        self.manager.current = 'scan'
    
    def show_disease_filter(self):
        """Show dropdown for disease filter."""
        from app.core.db import list_diseases
        
        dropdown = DropDown()
        
        # Add "All Diseases" option
        btn_all = Button(
            text='All Diseases',
            size_hint_y=None,
            height='40dp',
            background_color=(0.2, 0.2, 0.25, 1.0) if self.selected_disease == "All Diseases" else (0.15, 0.15, 0.18, 1.0)
        )
        btn_all.bind(on_release=lambda btn: self.on_disease_selected(dropdown, "All Diseases"))
        dropdown.add_widget(btn_all)
        
        # Add disease options
        diseases = list_diseases()
        for disease in diseases:
            disease_name = disease['name']
            btn = Button(
                text=disease_name,
                size_hint_y=None,
                height='40dp',
                background_color=(0.2, 0.2, 0.25, 1.0) if self.selected_disease == disease_name else (0.15, 0.15, 0.18, 1.0)
            )
            btn.bind(on_release=lambda btn, dn=disease_name: self.on_disease_selected(dropdown, dn))
            dropdown.add_widget(btn)
        
        # Open dropdown
        if 'disease_filter_btn' in self.ids:
            dropdown.open(self.ids.disease_filter_btn)
    
    def show_date_filter(self):
        """Show dropdown for date range filter."""
        dropdown = DropDown()
        
        date_ranges = ["All Time", "Last 7 Days", "Last 30 Days", "Last 90 Days", "Last Year"]
        
        for date_range in date_ranges:
            btn = Button(
                text=date_range,
                size_hint_y=None,
                height='40dp',
                background_color=(0.2, 0.2, 0.25, 1.0) if self.selected_date_range == date_range else (0.15, 0.15, 0.18, 1.0)
            )
            btn.bind(on_release=lambda btn, dr=date_range: self.on_date_selected(dropdown, dr))
            dropdown.add_widget(btn)
        
        # Open dropdown
        if 'date_filter_btn' in self.ids:
            dropdown.open(self.ids.date_filter_btn)
    
    def on_disease_selected(self, dropdown, disease):
        """Handle disease filter selection."""
        self.selected_disease = disease
        dropdown.dismiss()
        self._load_tree_scans(reset=True)
    
    def on_date_selected(self, dropdown, date_range):
        """Handle date range filter selection."""
        self.selected_date_range = date_range
        # Clear custom date range when using presets
        self.date_range_start = None
        self.date_range_end = None
        dropdown.dismiss()
        self._load_tree_scans(reset=True)
    
    def toggle_sort_order(self):
        """Cycle through sort orders: newest → oldest → severity → newest."""
        if self.sort_order == "newest":
            self.sort_order = "oldest"
        elif self.sort_order == "oldest":
            self.sort_order = "severity"
        else:
            self.sort_order = "newest"
        
        # Update button text if it exists
        if 'sort_button' in self.ids:
            sort_labels = {
                "newest": "Sort: Newest",
                "oldest": "Sort: Oldest",
                "severity": "Sort: Severity"
            }
            self.ids.sort_button.text = sort_labels.get(self.sort_order, "Sort")
        
        self._load_tree_scans(reset=True)
    
    def show_custom_date_picker(self):
        """Show custom date range picker dialog."""
        from app.widgets.date_range_picker import DateRangePicker
        
        def on_date_range_selected(start_date, end_date):
            """Callback when custom date range is selected."""
            self.date_range_start = start_date
            self.date_range_end = end_date
            
            # Update display
            if start_date and end_date:
                self.selected_date_range = f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d')}"
            else:
                self.selected_date_range = "All Time"
            
            self._load_tree_scans(reset=True)
        
        picker = DateRangePicker(callback=on_date_range_selected)
        picker.open()
