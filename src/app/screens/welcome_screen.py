from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.lang import Builder
import logging, os
class WelcomeScreen(Screen):
    """Displays a blinking label and navigates to the home screen when tapped."""

    def on_enter(self):
        # Start the blinking label animation after a short delay
        Clock.schedule_once(self.start_fade_animation, 0.2)

    def start_fade_animation(self, dt):
        # Create a continuous fade-in/out effect for the 'tap_label'
        label = self.ids.get('tap_label')
        if label:
            logging.info("WelcomeScreen: 'tap_label' found, starting animation.")
            anim = (Animation(opacity=0, duration=1.2) +
                    Animation(opacity=1, duration=1.2))
            anim.repeat = True
            anim.start(label)
        else:
            logging.error("WelcomeScreen: Could not find widget with id 'tap_label'. KV file might be missing or incorrect.")

    def on_touch_down(self, touch):
        # Switch to the home screen on tap
        self.manager.current = 'home'
        return True
