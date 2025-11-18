from kivy.uix.screenmanager import Screen
from kivy.lang import Builder
import os

class PrecautionScreen(Screen):
    description_text = (
        "Before using the system, ensure that all hardware components are properly connected and powered. "
        "The Raspberry Pi 4 Model B should be securely attached to the camera module, and the scanning area "
        "must be free from dust, moisture, and direct sunlight to maintain optimal image quality during leaf "
        "scanning operations.\n\n"
        "When placing a mango leaf on the scanner platform, make sure the surface of the leaf is clean, flat, "
        "and free from external debris such as dirt or water droplets. Wrinkled or folded leaves may cause "
        "inaccurate readings, while wet or glossy surfaces can produce glare that interferes with the image "
        "analysis process.\n\n"
        "Avoid moving the scanner or camera module during operation. Any vibration or movement while scanning "
        "may result in blurred images, affecting the precision of anthracnose detection. It is also recommended "
        "to use a stable power source and ensure that the device is not exposed to sudden interruptions or overheating.\n\n"
        "Regular maintenance is essential to ensure long-term accuracy and performance. Clean the camera lens and "
        "scanning surface periodically using a soft, dry cloth. Do not use strong cleaning agents or liquids that "
        "may damage the hardware components or affect the system’s sensitivity.\n\n"
        "Always handle the equipment with care and follow operational instructions as provided. Proper usage and "
        "maintenance not only enhance detection reliability but also extend the system’s lifespan, ensuring "
        "consistent and safe operation for both research and field applications."
    )
