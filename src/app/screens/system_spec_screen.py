from kivy.uix.screenmanager import Screen
from kivy.lang import Builder
import os

class SystemSpecScreen(Screen):
    description_text = (
        "The system is designed to identify anthracnose disease in mango leaves using an "
        "image-based detection approach. It utilizes a Raspberry Pi 4 Model B as the main "
        "processing unit, paired with a high-resolution camera module that captures detailed "
        "images of mango leaves placed on the scanner platform. The captured images are analyzed "
        "to detect symptoms of anthracnose infection with accuracy and consistency.\n\n"
        "The scanning module is equipped with a controlled lighting environment to ensure image "
        "clarity and uniformity during the scanning process. The Raspberry Pi handles image "
        "acquisition and processing, while the results of each scan are transmitted to a connected "
        "mobile application that acts as the main user interface for interaction and data viewing.\n\n"
        "The mobile application allows users to initiate scans, view diagnostic results, and manage "
        "stored images and records. All data is stored locally on the device, ensuring privacy and "
        "offline functionality without the need for an internet connection.\n\n"
        "All scanned images and corresponding disease detection results are organized and stored within "
        "the system’s database. This data serves as both a record of past analyses and a source of information "
        "for building a larger dataset, which can be used to improve detection algorithms and enhance accuracy "
        "over time.\n\n"
        "Overall, the system integrates compact hardware, efficient processing, and user-friendly software "
        "to provide a reliable and portable solution for mango leaf disease detection and agricultural "
        "research applications."
    )
