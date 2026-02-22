"""Custom Filter Modal - Custom date range selection modal matching AddTreeModal design."""
from kivy.uix.modalview import ModalView
from kivy.uix.dropdown import DropDown
from kivy.uix.button import Button
from kivy.properties import ObjectProperty, StringProperty, BooleanProperty
from kivy.graphics import Color, RoundedRectangle
from kivy.lang import Builder
from kivy.clock import Clock
from datetime import datetime, timedelta
import os

# Load KV file
kv_path = os.path.join(os.path.dirname(__file__), 'CustomFilterModal.kv')
Builder.load_file(kv_path)


class StyledDropDown(DropDown):
    """Custom DropDown with rounded corners. Touch-safe for touchscreen LCD."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bg_rect = None
        self.max_height = 220
        self.dismiss_on_select = True
        self.auto_dismiss = False

    def open(self, widget):
        super().open(widget)
        if self.container and not self.bg_rect:
            with self.container.canvas.before:
                Color(248/255, 248/255, 248/255, 1)
                self.bg_rect = RoundedRectangle(
                    pos=self.container.pos,
                    size=self.container.size,
                    radius=[10, 10, 10, 10]
                )
            self.container.bind(pos=self._update_bg, size=self._update_bg)

    def _update_bg(self, instance, value):
        if self.bg_rect:
            self.bg_rect.pos = instance.pos
            self.bg_rect.size = instance.size


class CustomFilterModal(ModalView):
    """Custom date range picker with preset options and manual selection."""

    callback = ObjectProperty(None)

    selected_quick_filter = StringProperty("Select a preset")
    quick_filter_active = BooleanProperty(False)

    start_month_text = StringProperty("Month")
    start_day_text = StringProperty("Day")
    start_year_text = StringProperty("Year")
    start_month_active = BooleanProperty(False)
    start_day_active = BooleanProperty(False)
    start_year_active = BooleanProperty(False)

    end_month_text = StringProperty("Month")
    end_day_text = StringProperty("Day")
    end_year_text = StringProperty("Year")
    end_month_active = BooleanProperty(False)
    end_day_active = BooleanProperty(False)
    end_year_active = BooleanProperty(False)

    start_date = None
    end_date = None

    # Track which dropdown is open for border highlight
    quick_filter_open = BooleanProperty(False)
    start_month_open = BooleanProperty(False)
    start_day_open  = BooleanProperty(False)
    start_year_open = BooleanProperty(False)
    end_month_open  = BooleanProperty(False)
    end_day_open    = BooleanProperty(False)
    end_year_open   = BooleanProperty(False)

    def __init__(self, callback=None, **kwargs):
        super().__init__(**kwargs)
        self.callback = callback

    # ------------------------------------------------------------------ #
    #  Quick Filter
    # ------------------------------------------------------------------ #
    def show_quick_filter_dropdown(self):
        from kivy.factory import Factory
        self.quick_filter_open = True

        dropdown = StyledDropDown(auto_width=False, width=336)

        presets = ['Today', 'Last 7 Days', 'Last 30 Days', 'Last 90 Days', 'All Time']
        for preset in presets:
            btn = Factory.FilterOption(text=preset)
            btn.bind(on_press=lambda b, p=preset: self._select_quick_filter(p, dropdown))
            dropdown.add_widget(btn)

        dropdown.bind(on_dismiss=lambda *_: setattr(self, 'quick_filter_open', False))
        dropdown.open(self.ids.quick_filter_btn)

    def _select_quick_filter(self, preset, dropdown):
        self.selected_quick_filter = preset
        self.quick_filter_active = True
        Clock.schedule_once(lambda dt: dropdown.dismiss(), 0.15)

    # ------------------------------------------------------------------ #
    #  Month / Day / Year dropdowns
    # ------------------------------------------------------------------ #
    def show_month_dropdown(self, date_type):
        from kivy.factory import Factory
        open_attr = f'{date_type}_month_open'
        setattr(self, open_attr, True)

        dropdown = StyledDropDown(auto_width=False, width=90)
        months = [datetime(2000, i, 1).strftime('%b') for i in range(1, 13)]

        for month in months:
            btn = Factory.FilterOption(text=month)
            btn.bind(on_press=lambda b, m=month: self._select_month(date_type, m, dropdown))
            dropdown.add_widget(btn)

        dropdown.bind(on_dismiss=lambda *_: setattr(self, open_attr, False))
        btn_id = f'{date_type}_month_btn'
        dropdown.open(self.ids[btn_id])

    def _select_month(self, date_type, month, dropdown):
        if date_type == 'start':
            self.start_month_text = month
            self.start_month_active = True
        else:
            self.end_month_text = month
            self.end_month_active = True
        Clock.schedule_once(lambda dt: dropdown.dismiss(), 0.15)

    def show_day_dropdown(self, date_type):
        from kivy.factory import Factory
        open_attr = f'{date_type}_day_open'
        setattr(self, open_attr, True)

        dropdown = StyledDropDown(auto_width=False, width=90)
        days = [str(i) for i in range(1, 32)]

        for day in days:
            btn = Factory.FilterOption(text=day)
            btn.bind(on_press=lambda b, d=day: self._select_day(date_type, d, dropdown))
            dropdown.add_widget(btn)

        dropdown.bind(on_dismiss=lambda *_: setattr(self, open_attr, False))
        btn_id = f'{date_type}_day_btn'
        dropdown.open(self.ids[btn_id])

    def _select_day(self, date_type, day, dropdown):
        if date_type == 'start':
            self.start_day_text = day
            self.start_day_active = True
        else:
            self.end_day_text = day
            self.end_day_active = True
        Clock.schedule_once(lambda dt: dropdown.dismiss(), 0.15)

    def show_year_dropdown(self, date_type):
        from kivy.factory import Factory
        open_attr = f'{date_type}_year_open'
        setattr(self, open_attr, True)

        dropdown = StyledDropDown(auto_width=False, width=95)
        current_year = datetime.now().year
        years = [str(y) for y in range(2020, current_year + 1)]

        for year in years:
            btn = Factory.FilterOption(text=year)
            btn.bind(on_press=lambda b, y=year: self._select_year(date_type, y, dropdown))
            dropdown.add_widget(btn)

        dropdown.bind(on_dismiss=lambda *_: setattr(self, open_attr, False))
        btn_id = f'{date_type}_year_btn'
        dropdown.open(self.ids[btn_id])

    def _select_year(self, date_type, year, dropdown):
        if date_type == 'start':
            self.start_year_text = year
            self.start_year_active = True
        else:
            self.end_year_text = year
            self.end_year_active = True
        Clock.schedule_once(lambda dt: dropdown.dismiss(), 0.15)

    # ------------------------------------------------------------------ #
    #  Apply / Cancel
    # ------------------------------------------------------------------ #
    def _apply_custom(self, instance):
        if self.quick_filter_active and self.selected_quick_filter != "Select a preset":
            self._apply_quick_filter()
            return

        if (self.start_month_text == 'Month' or self.start_day_text == 'Day' or
                self.start_year_text == 'Year' or self.end_month_text == 'Month' or
                self.end_day_text == 'Day' or self.end_year_text == 'Year'):
            return

        try:
            month_map = {datetime(2000, i, 1).strftime('%b'): i for i in range(1, 13)}
            self.start_date = datetime(
                int(self.start_year_text), month_map[self.start_month_text],
                int(self.start_day_text), 0, 0, 0
            )
            self.end_date = datetime(
                int(self.end_year_text), month_map[self.end_month_text],
                int(self.end_day_text), 23, 59, 59
            )
            if self.callback:
                self.callback(self.start_date, self.end_date)
            self.dismiss()
        except (ValueError, KeyError):
            pass

    def _apply_quick_filter(self):
        today = datetime.now()
        if self.selected_quick_filter == 'Today':
            start = today.replace(hour=0, minute=0, second=0, microsecond=0)
            end = today
        elif self.selected_quick_filter == 'Last 7 Days':
            start = today - timedelta(days=7); end = today
        elif self.selected_quick_filter == 'Last 30 Days':
            start = today - timedelta(days=30); end = today
        elif self.selected_quick_filter == 'Last 90 Days':
            start = today - timedelta(days=90); end = today
        else:
            start = None; end = None

        if self.callback:
            self.callback(start, end)
        self.dismiss()