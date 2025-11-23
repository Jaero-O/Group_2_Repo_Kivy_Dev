"""Date Range Picker Widget - Custom date range selection dialog."""
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.properties import ObjectProperty
from datetime import datetime, timedelta


class DateRangePicker(Popup):
    """Custom date range picker with preset options and manual selection.
    
    Provides quick preset options (Today, Last 7 Days, etc.) and custom
    date range selection using month/day/year spinners.
    """
    
    callback = ObjectProperty(None)
    
    def __init__(self, callback=None, **kwargs):
        super().__init__(**kwargs)
        self.callback = callback
        self.title = "Select Date Range"
        self.size_hint = (0.9, 0.7)
        self.auto_dismiss = False
        self.title_color = (3/255, 30/255, 0/255, 1)  # Dark green
        self.title_font = 'Roboto'
        self.separator_color = (220/255, 220/255, 220/255, 1)
        
        # Date range state
        self.start_date = None
        self.end_date = None
        
        self._build_ui()
    
    def _build_ui(self):
        """Build the dialog UI with presets and custom selectors."""
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Set background color
        from kivy.graphics import Color, Rectangle
        with layout.canvas.before:
            Color(248/255, 248/255, 248/255, 1)
            layout.bg_rect = Rectangle(pos=layout.pos, size=layout.size)
        layout.bind(pos=lambda _, v: setattr(layout.bg_rect, 'pos', v),
                   size=lambda _, v: setattr(layout.bg_rect, 'size', v))
        
        # Preset options section
        presets = BoxLayout(orientation='vertical', size_hint_y=0.5, spacing=5)
        presets.add_widget(Label(
            text='Quick Filters:',
            size_hint_y=0.15,
            font_size='16sp',
            bold=True,
            color=(3/255, 30/255, 0/255, 1)
        ))
        
        preset_options = [
            'Today',
            'Last 7 Days',
            'Last 30 Days',
            'Last 90 Days',
            'All Time'
        ]
        
        for preset in preset_options:
            btn = Button(
                text=preset,
                size_hint_y=0.17,
                background_normal='',
                background_color=(1, 1, 1, 1),
                color=(3/255, 30/255, 0/255, 1),
                font_size=16,
                bold=True
            )
            btn.bind(on_release=lambda b, p=preset: self._apply_preset(p))
            presets.add_widget(btn)
        
        layout.add_widget(presets)
        
        # Custom range selection section
        custom = BoxLayout(orientation='vertical', size_hint_y=0.35, spacing=5)
        custom.add_widget(Label(
            text='Custom Range:',
            size_hint_y=0.2,
            font_size='16sp',
            bold=True,
            color=(3/255, 30/255, 0/255, 1)
        ))
        
        # Start date selectors
        start_box = BoxLayout(size_hint_y=0.4, spacing=5)
        start_box.add_widget(Label(text='From:', size_hint_x=0.2, color=(3/255, 30/255, 0/255, 1)))
        
        current_year = datetime.now().year
        self.start_month = Spinner(
            text='Month',
            values=[datetime(2000, i, 1).strftime('%b') for i in range(1, 13)],
            size_hint_x=0.27
        )
        self.start_day = Spinner(
            text='Day',
            values=[str(i) for i in range(1, 32)],
            size_hint_x=0.27
        )
        self.start_year = Spinner(
            text='Year',
            values=[str(y) for y in range(2020, current_year + 1)],
            size_hint_x=0.26
        )
        
        start_box.add_widget(self.start_month)
        start_box.add_widget(self.start_day)
        start_box.add_widget(self.start_year)
        custom.add_widget(start_box)
        
        # End date selectors
        end_box = BoxLayout(size_hint_y=0.4, spacing=5)
        end_box.add_widget(Label(text='To:', size_hint_x=0.2, color=(3/255, 30/255, 0/255, 1)))
        
        self.end_month = Spinner(
            text='Month',
            values=[datetime(2000, i, 1).strftime('%b') for i in range(1, 13)],
            size_hint_x=0.27
        )
        self.end_day = Spinner(
            text='Day',
            values=[str(i) for i in range(1, 32)],
            size_hint_x=0.27
        )
        self.end_year = Spinner(
            text='Year',
            values=[str(y) for y in range(2020, current_year + 1)],
            size_hint_x=0.26
        )
        
        end_box.add_widget(self.end_month)
        end_box.add_widget(self.end_day)
        end_box.add_widget(self.end_year)
        custom.add_widget(end_box)
        
        layout.add_widget(custom)
        
        # Action buttons
        buttons = BoxLayout(size_hint_y=0.15, spacing=10)
        buttons.add_widget(Button(
            text='Cancel',
            on_release=self.dismiss,
            background_normal='',
            background_color=(241/255, 241/255, 241/255, 1),
            color=(3/255, 30/255, 0/255, 1),
            bold=True,
            font_size=14
        ))
        buttons.add_widget(Button(
            text='Apply Custom',
            on_release=self._apply_custom,
            background_normal='',
            background_color=(6/255, 87/255, 6/255, 1),
            color=(1, 1, 1, 1),
            bold=True,
            font_size=14
        ))
        layout.add_widget(buttons)
        
        self.content = layout
    
    def _apply_preset(self, preset):
        """Apply preset date range."""
        today = datetime.now()
        
        if preset == 'Today':
            self.start_date = today.replace(hour=0, minute=0, second=0, microsecond=0)
            self.end_date = today
        elif preset == 'Last 7 Days':
            self.start_date = today - timedelta(days=7)
            self.end_date = today
        elif preset == 'Last 30 Days':
            self.start_date = today - timedelta(days=30)
            self.end_date = today
        elif preset == 'Last 90 Days':
            self.start_date = today - timedelta(days=90)
            self.end_date = today
        else:  # All Time
            self.start_date = None
            self.end_date = None
        
        if self.callback:
            self.callback(self.start_date, self.end_date)
        self.dismiss()
    
    def _apply_custom(self, instance):
        """Apply custom date range from spinners."""
        # Validate all fields are selected
        if (self.start_month.text == 'Month' or self.start_day.text == 'Day' or 
            self.start_year.text == 'Year' or self.end_month.text == 'Month' or 
            self.end_day.text == 'Day' or self.end_year.text == 'Year'):
            # Show error or just return
            return
        
        try:
            # Convert month name to number
            month_map = {datetime(2000, i, 1).strftime('%b'): i for i in range(1, 13)}
            start_month_num = month_map[self.start_month.text]
            end_month_num = month_map[self.end_month.text]
            
            self.start_date = datetime(
                int(self.start_year.text),
                start_month_num,
                int(self.start_day.text),
                0, 0, 0
            )
            self.end_date = datetime(
                int(self.end_year.text),
                end_month_num,
                int(self.end_day.text),
                23, 59, 59
            )
            
            if self.callback:
                self.callback(self.start_date, self.end_date)
            self.dismiss()
        except (ValueError, KeyError):
            # Invalid date selected
            pass
