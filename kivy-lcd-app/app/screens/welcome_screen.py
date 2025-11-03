from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.animation import Animation


class WelcomeScreen(Screen):
    def on_enter(self):
        Clock.schedule_once(self.start_fade_animation, 0.2)

    def start_fade_animation(self, dt):
        label = self.ids.get('tap_label')
        if label:
            anim = (Animation(opacity=0, duration=1.2) +
                    Animation(opacity=1, duration=1.2))
            anim.repeat = True
            anim.start(label)

    def on_touch_down(self, touch):
        self.manager.current = 'home'
        return True
