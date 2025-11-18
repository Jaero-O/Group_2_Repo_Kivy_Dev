from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.core.window import Window
from kivy.utils import platform
from kivy.properties import StringProperty

import tensorflow as tf
import numpy as np
import cv2

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

# -------- Model Prediction Class --------
class ModelPredict:
    def __init__(self, model_path, labels):
        self.interpreter = tf.lite.Interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        self.labels = labels

    def predict(self, image_path):
        img = cv2.imread(image_path)
        img = cv2.resize(img, (224, 224))
        img = np.expand_dims(img, axis=0)
        img = img.astype(np.float32)

        self.interpreter.set_tensor(self.input_details[0]['index'], img)
        self.interpreter.invoke()
        output_data = self.interpreter.get_tensor(self.output_details[0]['index'])
        
        prediction = self.labels[np.argmax(output_data)]
        severity = np.max(output_data) * 100
        
        return prediction, severity

# -------- Screen Definitions --------
class HomeScreen(Screen): pass
class ScanScreen(Screen): pass
class ScanResultScreen(Screen): pass
class SaveLeafScreen(Screen): pass
class AddTreeScreen(Screen): pass
class ClassificationScreen(Screen):
    disease_text = StringProperty("")
    severity_text = StringProperty("")
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
        # Model setup
        model_path = "c:/Users/kenne/Group_2_Repo/Plant_Disease_Prediction/tflite/mango_mobilenetv2.tflite"
        labels = ['Anthracnose', 'Bacterial Canker', 'Cutting Weevil', 'Die Back', 'Gall Midge', 'Healthy', 'Powdery Mildew', 'Sooty Mould']
        self.model_predict = ModelPredict(model_path, labels)

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

    def predict_disease(self):
        # Hardcoded image path for now
        image_path = "c:/Users/kenne/Group_2_Repo/leaf-detection/scripts/20211231_123305 (Custom).jpg"
        prediction, severity = self.model_predict.predict(image_path)
        
        classification_screen = self.root.get_screen('classification')
        classification_screen.disease_text = f"Disease: {prediction}"
        classification_screen.severity_text = f"Severity: {severity:.2f}%"
        
        self.root.current = 'classification'


if __name__ == '__main__':
    MangoScannerApp().run()
