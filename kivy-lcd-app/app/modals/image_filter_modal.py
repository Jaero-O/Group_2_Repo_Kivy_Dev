"""Image Filter Modal - Modal dialogs for Disease, Date, and Sort filters."""
import os
from kivy.uix.modalview import ModalView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.factory import Factory
from kivy.lang import Builder
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy.properties import ObjectProperty, NumericProperty
from datetime import datetime, timedelta

# Load KV rules — must be before any Factory usage
_kv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ImageFilterModal.kv")
Builder.load_file(_kv_path)


# ---------------------------------------------------------------------------
# KV-backed widget classes — hl_alpha is a real Kivy property so canvas reacts
# ---------------------------------------------------------------------------

class FilterOptionBtn(Button):
    hl_alpha = NumericProperty(0)  # 0 = no highlight, 1 = selected highlight


class FilterCancelBtn(Button):
    pass


# ---------------------------------------------------------------------------
# Internal layout helpers
# ---------------------------------------------------------------------------

def _draw_card(widget):
    with widget.canvas.before:
        Color(0, 0, 0, 0.25)
        widget._shadow = RoundedRectangle(
            radius=[16], pos=(widget.x + 2, widget.y - 4), size=widget.size
        )
        Color(1, 1, 1, 1)
        widget._bg = RoundedRectangle(radius=[16], pos=widget.pos, size=widget.size)

    def _update(*_):
        widget._shadow.pos = (widget.x + 2, widget.y - 4)
        widget._shadow.size = widget.size
        widget._bg.pos = widget.pos
        widget._bg.size = widget.size

    widget.bind(pos=_update, size=_update)


def _draw_overlay(widget):
    with widget.canvas.before:
        Color(0, 0, 0, 0.5)
        widget._overlay = Rectangle(pos=widget.pos, size=widget.size)
    widget.bind(
        pos=lambda w, _: setattr(w._overlay, 'pos', w.pos),
        size=lambda w, _: setattr(w._overlay, 'size', w.size),
    )


def _make_divider():
    w = Widget(size_hint_y=None, height=1)
    with w.canvas:
        Color(220/255, 220/255, 220/255, 1)
        rect = Rectangle(pos=w.pos, size=w.size)
    w.bind(pos=lambda wi, _: setattr(rect, 'pos', wi.pos),
           size=lambda wi, _: setattr(rect, 'size', wi.size))
    return w


def _make_option_button(text, is_selected, on_release_cb):
    btn = FilterOptionBtn(text=text)
    btn.hl_alpha = 1 if is_selected else 0   # Kivy property — KV canvas reacts immediately
    btn.bind(on_release=lambda b: on_release_cb(text))
    return btn


def _make_cancel_button(on_press_cb):
    btn = FilterCancelBtn(text="Cancel")
    btn.bind(on_press=lambda _: on_press_cb())
    return btn


# ---------------------------------------------------------------------------
# Base modal
# ---------------------------------------------------------------------------

class _BaseFilterModal(ModalView):

    def __init__(self, title, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (480, 800)
        self.auto_dismiss = False
        self.background = ""
        self.background_color = (0, 0, 0, 0)
        self.overlay_color = (0, 0, 0, 0)

        from kivy.uix.floatlayout import FloatLayout
        fl = FloatLayout()
        _draw_overlay(fl)

        card = BoxLayout(
            orientation='vertical',
            size_hint=(None, None),
            width=300,
            padding=[18, 18, 18, 18],
            spacing=12,
        )
        card.bind(minimum_height=card.setter('height'))
        _draw_card(card)

        title_lbl = Label(
            text=title,
            color=(3/255, 33/255, 0/255, 1),
            font_size=20,
            bold=True,
            size_hint_y=None,
            height=26,
            halign="center",
            valign="middle",
        )
        title_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
        card.add_widget(title_lbl)
        card.add_widget(_make_divider())

        self._options_box = BoxLayout(
            orientation='vertical',
            size_hint=(None, None),
            width=264,
            spacing=2,
        )
        self._options_box.bind(minimum_height=self._options_box.setter('height'))

        self._scroll = ScrollView(
            size_hint=(1, None),
            do_scroll_x=False,
            bar_width=3,
        )
        self._scroll.add_widget(self._options_box)
        card.add_widget(self._scroll)
        card.add_widget(_make_cancel_button(self.dismiss))

        card.pos_hint = {"center_x": 0.5, "center_y": 0.5}
        fl.add_widget(card)
        self.add_widget(fl)

    def _populate(self, options, selected, on_select_cb):
        self._options_box.clear_widgets()
        for opt in options:
            self._options_box.add_widget(
                _make_option_button(opt, opt == selected, on_select_cb)
            )
        self._scroll.height = min(len(options) * 44, 352)


# ---------------------------------------------------------------------------
# Concrete modals
# ---------------------------------------------------------------------------

class DiseaseFilterModal(_BaseFilterModal):
    callback = ObjectProperty(None, allownone=True)

    def __init__(self, current_selection="All Diseases", callback=None, **kwargs):
        super().__init__(title="Filter by Disease", **kwargs)
        self._selected = current_selection
        self.callback = callback

    def on_open(self):
        from app.core.db import list_diseases
        options = ["All Diseases"] + [d['name'] for d in list_diseases()]
        self._populate(options, self._selected, self._on_select)

    def _on_select(self, value):
        if self.callback:
            self.callback(value)
        self.dismiss()


class DateFilterModal(_BaseFilterModal):
    callback = ObjectProperty(None, allownone=True)

    PRESETS = ["All Time", "Last 7 Days", "Last 30 Days", "Last 90 Days", "Last Year"]
    RANGES = {"Last 7 Days": 7, "Last 30 Days": 30, "Last 90 Days": 90, "Last Year": 365}

    def __init__(self, current_selection="All Time", callback=None, **kwargs):
        super().__init__(title="Filter by Date", **kwargs)
        self._selected = current_selection
        self.callback = callback

    def on_open(self):
        self._populate(self.PRESETS, self._selected, self._on_select)

    def _on_select(self, value):
        if self.callback:
            today = datetime.now()
            start = today - timedelta(days=self.RANGES[value]) if value in self.RANGES else None
            end = today if value in self.RANGES else None
            self.callback(value, start, end)
        self.dismiss()


class SortFilterModal(_BaseFilterModal):
    callback = ObjectProperty(None, allownone=True)

    SORT_OPTIONS = [
        ("Newest First", "newest"),
        ("Oldest First", "oldest"),
        ("Highest Severity", "severity"),
    ]

    def __init__(self, current_selection="newest", callback=None, **kwargs):
        super().__init__(title="Sort By", **kwargs)
        self._selected = current_selection
        self.callback = callback

    def on_open(self):
        display_map = {v: d for d, v in self.SORT_OPTIONS}
        selected_display = display_map.get(self._selected, "Newest First")
        options = [d for d, v in self.SORT_OPTIONS]
        self._populate(options, selected_display, self._on_select)

    def _on_select(self, display_text):
        sort_map = {d: v for d, v in self.SORT_OPTIONS}
        sort_key = sort_map.get(display_text, "newest")
        if self.callback:
            self.callback(sort_key, display_text)
        self.dismiss()