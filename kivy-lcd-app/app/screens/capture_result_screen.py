from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.boxlayout import BoxLayout
from kivy.animation import Animation
from kivy.graphics import Color, RoundedRectangle, Line


class CaptureResultScreen(Screen):
    """Screen that handles capture results and navigates to the result screen."""

    def open_result(self):
        """Switch to the 'result' screen and store the last active screen."""
        app = App.get_running_app()
        app.last_screen = 'capture_result'
        self.manager.current = 'result'

    def open_save_modal(self):
        """Open the SaveModal as a floating modal over this screen."""
        from app.modals.save_modal import SaveModal
        modal = SaveModal()
        modal.open()

    def show_notification(self, message, icon_type=None):
        """Show animated notification popup — called after SaveModal dismisses."""
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

        icon_width = 24 + 8 if icon_type else 0
        content_width = icon_width + popup_label.width
        h_padding = 20
        popup_width = content_width + h_padding * 2
        popup_height = 45

        popup = FloatLayout(
            size_hint=(None, None),
            size=(popup_width, popup_height),
            pos_hint={"center_x": 0.5, "top": 0.95},
            opacity=0
        )

        from kivy.graphics import Color, RoundedRectangle, Line
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
                source='app/assets/export_success.png',
                size_hint=(None, None),
                size=(24, 24),
                allow_stretch=True,
                keep_ratio=True,
                mipmap=True
            )
            content.add_widget(icon)
        elif icon_type == 'fail':
            icon = Image(
                source='app/assets/export_fail.png',
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