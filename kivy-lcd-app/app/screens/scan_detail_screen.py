"""Scan Detail Screen - Display full details of a single scan record."""
from kivy.uix.screenmanager import Screen
from kivy.uix.modalview import ModalView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.floatlayout import FloatLayout
from kivy.app import App
from kivy.properties import StringProperty, NumericProperty, BooleanProperty
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle, Line
import os


class ConfirmDeleteModal(ModalView):
    detail_text = StringProperty("")
    on_confirm_callback = None

    def cancel(self):
        self.dismiss()

    def confirm(self):
        self.dismiss()
        if self.on_confirm_callback:
            self.on_confirm_callback()


class ScanDetailScreen(Screen):
    """Display detailed information about a single scan record."""

    scan_id = NumericProperty(0)
    image_path = StringProperty("")
    disease_name = StringProperty("Unknown")
    confidence_score = NumericProperty(0.0)
    severity_percentage = NumericProperty(0.0)
    severity_name = StringProperty("Unknown")
    tree_name = StringProperty("Unknown")
    scan_timestamp = StringProperty("N/A")
    formatted_timestamp = StringProperty("N/A")

    total_leaf_area = NumericProperty(0.0)
    lesion_area = NumericProperty(0.0)
    lesion_coverage = NumericProperty(0.0)

    # Classification tag (Healthy / Early / Advance)
    confidence_badge_text = StringProperty("")

    delete_enabled = BooleanProperty(True)

    def on_pre_enter(self, *args):
        self._load_scan_details()

    def _load_scan_details(self):
        from app.core.db import get_scan_detail

        app = App.get_running_app()
        scan_id = getattr(app, 'current_scan_id', 0)

        if not scan_id:
            self.disease_name = "Error: No scan selected"
            return

        self.scan_id = scan_id
        scan_data = get_scan_detail(scan_id)

        if not scan_data:
            self.disease_name = "Error: Scan not found"
            return

        self.image_path = scan_data.get("image_path", "")
        self.disease_name = scan_data.get("disease_name", "Unknown")
        self.confidence_score = scan_data.get("confidence_score", 0.0)
        self.severity_percentage = scan_data.get("severity_percentage", 0.0)
        self.severity_name = scan_data.get("severity_name", "Unknown")
        self.tree_name = scan_data.get("tree_name", "Unknown")
        self.scan_timestamp = scan_data.get("scan_timestamp", "N/A")

        self._format_timestamp()
        self._update_classification_tag(self.confidence_score)
        self._calculate_leaf_metrics()

    def _format_timestamp(self):
        try:
            from datetime import datetime
            dt = datetime.strptime(self.scan_timestamp, "%Y-%m-%d %H:%M:%S")
            self.formatted_timestamp = dt.strftime("%B %d, %Y %I:%M %p")
        except Exception:
            self.formatted_timestamp = self.scan_timestamp

    def _calculate_leaf_metrics(self):
        standard_leaf_area = 100000.0
        self.total_leaf_area = standard_leaf_area
        self.lesion_coverage = self.severity_percentage
        self.lesion_area = (self.severity_percentage / 100.0) * standard_leaf_area

    def _update_classification_tag(self, confidence):
        """
        Sets classification tag text. Colors handled in KV.
          < 0.60  → Advance  (red bg)
          0.60–0.85 → Early  (yellow bg)
          ≥ 0.85  → Healthy  (green bg)
        """
        if confidence < 0.60:
            self.confidence_badge_text = "Advance"
        elif confidence < 0.85:
            self.confidence_badge_text = "Early"
        else:
            self.confidence_badge_text = "Healthy"

    def confirm_delete(self):
        """Show styled delete confirmation modal."""
        modal = ConfirmDeleteModal()
        modal.detail_text = (
            f"Disease: {self.disease_name}\n"
            "This action cannot be undone."
        )
        modal.on_confirm_callback = self.delete_scan
        modal.open()

    def delete_scan(self):
        from app.core.db import delete_scan_record

        if not self.scan_id:
            self.show_notification("No scan ID to delete.", icon_type='fail')
            return

        try:
            success = delete_scan_record(self.scan_id)
            if success:
                self.go_back()
            else:
                self.show_notification("Failed to delete scan.", icon_type='fail')
        except Exception as e:
            self.show_notification(f"Delete error: {str(e)}", icon_type='fail')

    def export_data(self):
        from app.core.db import export_scan_to_json

        if not self.scan_id:
            self.show_notification("No scan to export.", icon_type='fail')
            return

        try:
            output_path = export_scan_to_json(self.scan_id)
            if output_path:
                self.show_notification(
                    f"Exported: {os.path.basename(output_path)}",
                    icon_type='success'
                )
            else:
                self.show_notification("Export failed.", icon_type='fail')
        except Exception as e:
            self.show_notification(f"Export error: {str(e)}", icon_type='fail')

    def show_notification(self, message, icon_type=None):
        """Show animated notification popup with optional icon.
        Matches the same style as RecordsScreen.show_notification.

        Args:
            message: The notification text
            icon_type: 'success' for checkmark, 'fail' for warning, None for no icon
        """
        # Measure label first to size container dynamically
        popup_label = Label(
            text=message,
            color=(49/255, 49/255, 49/255, 1),
            font_size=14,
            halign="left",
            valign="middle",
            bold=True,
            pos_hint={"center_y": 0.52}
        )
        popup_label.texture_update()
        popup_label.size = popup_label.texture_size

        # Calculate content width: icon (if any) + spacing + label
        icon_width = 24 + 8 if icon_type else 0
        content_width = icon_width + popup_label.width

        # Equal horizontal padding on both sides
        h_padding = 20
        popup_width = content_width + h_padding * 2
        popup_height = 45

        popup = FloatLayout(
            size_hint=(None, None),
            size=(popup_width, popup_height),
            pos_hint={"center_x": 0.5, "top": 0.88},
            opacity=0
        )

        with popup.canvas.before:
            Color(1, 1, 1, 1)
            popup.bg_rect = RoundedRectangle(radius=[10], pos=popup.pos, size=popup.size)
            Color(0, 0, 0, 0.15)
            popup.border_line = Line(
                rounded_rectangle=(popup.x, popup.y, popup.width, popup.height, 10),
                width=1
            )

        popup.bind(
            pos=lambda _, v: (
                setattr(popup.bg_rect, 'pos', v),
                setattr(popup.border_line, 'rounded_rectangle',
                        (v[0], v[1], popup.width, popup.height, 10))
            ),
            size=lambda _, v: (
                setattr(popup.bg_rect, 'size', v),
                setattr(popup.border_line, 'rounded_rectangle',
                        (popup.x, popup.y, v[0], v[1], 10))
            )
        )

        content = BoxLayout(
            orientation='horizontal',
            size_hint=(None, None),
            size=(content_width, 24),
            spacing=8,
            pos_hint={"center_x": 0.5, "center_y": 0.5}
        )

        if icon_type == 'success':
            icon = Image(
                source='app/assets/success.png',
                size_hint=(None, None),
                size=(24, 24),
                allow_stretch=True,
                keep_ratio=True,
                mipmap=True
            )
            content.add_widget(icon)
        elif icon_type == 'fail':
            icon = Image(
                source='app/assets/fail.png',
                size_hint=(None, None),
                size=(24, 24),
                allow_stretch=True,
                keep_ratio=True,
                mipmap=True
            )
            content.add_widget(icon)

        content.add_widget(popup_label)
        popup.add_widget(content)
        self.add_widget(popup)

        anim = Animation(opacity=1, duration=0.3)
        anim += Animation(opacity=1, duration=1.5)
        anim += Animation(opacity=0, duration=0.4)
        anim.bind(on_complete=lambda *_: self.remove_widget(popup))
        anim.start(popup)

    def go_back(self):
        """Navigate back to Result screen (where More Info was clicked)."""
        app = App.get_running_app()
        last = getattr(app, 'last_screen', 'result')
        if last == 'result':
            self.manager.current = 'result'
        elif last == 'scan_list':
            self.manager.current = 'scan_list'
        else:
            self.manager.current = 'records'
