from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.core.window import Window
from kivy.utils import platform

# ========== SCREEN SETTINGS ==========
WIDTH, HEIGHT = 360, 640

# Detect platform
IS_PI = False
try:
    with open("/proc/cpuinfo") as f:
        IS_PI = "Raspberry Pi" in f.read()
except Exception:
    IS_PI = False

# ---------- Apply Screen Settings ----------
if IS_PI:
    # On Raspberry Pi → fullscreen, no borders
    Window.fullscreen = True
    print("Running on Raspberry Pi → fullscreen mode enabled.")
else:
    # On desktop → fixed portrait and centered
    Window.size = (WIDTH, HEIGHT)
    Window.fullscreen = False
    try:
        import tkinter as tk
        root = tk.Tk()
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        root.destroy()

        x = int((screen_width - WIDTH) / 2)
        y = int((screen_height - HEIGHT) / 2)
        Window.left = x
        Window.top = y
        print(f"Centered window at {x}, {y} on desktop.")
    except Exception as e:
        print("Centering skipped:", e)

# -------- Screen Definitions --------
class HomeScreen(Screen): pass
class ScanScreen(Screen): pass
class ScanResultScreen(Screen): pass
class SaveLeafScreen(Screen): pass
class AddTreeScreen(Screen): pass
class ClassificationScreen(Screen): pass
class SaveConfirmationScreen(Screen): pass
class ViewRecordsScreen(Screen): pass
class ImagesPerTreeScreen(Screen): pass
class LeafDataScreen(Screen): pass
class ShareScreen(Screen): pass
class HelpScreen(Screen): pass
class DiseaseInfoScreen(Screen): pass
class SystemSpecScreen(Screen): pass
class GuidelinesScreen(Screen): pass
class AboutScreen(Screen): pass


# -------- Screen Manager --------
class MangoScannerApp(App):
    def build(self):
        # Explicitly load KV layout
        Builder.load_file("gui.kv")

        sm = ScreenManager(transition=FadeTransition(duration=0.1))

        sm.add_widget(HomeScreen(name='home'))
        sm.add_widget(ScanScreen(name='scan'))
        sm.add_widget(ScanResultScreen(name='scan_result'))
        sm.add_widget(SaveLeafScreen(name='save_leaf'))
        sm.add_widget(AddTreeScreen(name='add_tree'))
        sm.add_widget(ClassificationScreen(name='classification'))
        sm.add_widget(SaveConfirmationScreen(name='save_confirmation'))
        sm.add_widget(ViewRecordsScreen(name='view_records'))
        sm.add_widget(ImagesPerTreeScreen(name='images_per_tree'))
        sm.add_widget(LeafDataScreen(name='leaf_data'))
        sm.add_widget(ShareScreen(name='share'))
        sm.add_widget(HelpScreen(name='help'))
        sm.add_widget(DiseaseInfoScreen(name='disease_info'))
        sm.add_widget(SystemSpecScreen(name='system_spec'))
        sm.add_widget(GuidelinesScreen(name='guidelines'))
        sm.add_widget(AboutScreen(name='about'))

        return sm


if __name__ == '__main__':
    MangoScannerApp().run()
