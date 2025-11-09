from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.animation import Animation


class WelcomeScreen(Screen):
    """Displays a blinking label and navigates to the home screen when tapped."""

    def on_enter(self):
        # Start the blinking label animation after a short delay
        Clock.schedule_once(self.start_fade_animation, 0.2)

    def start_fade_animation(self, dt):
        # Create a continuous fade-in/out effect for the 'tap_label'
        label = self.ids.get('tap_label')
        if label:
            anim = (Animation(opacity=0, duration=1.2) +
                    Animation(opacity=1, duration=1.2))
            anim.repeat = True
            anim.start(label)

    def on_touch_down(self, touch):
        # Switch to the home screen on tap
        self.manager.current = 'home'
        return True
