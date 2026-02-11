# process_leaf_sub.py
import sys
import json
from PIL import Image, ImageOps
import cv2
import numpy as np
from rembg.bg import remove
from rembg.session_factory import new_session

# Load U2NET session once
U2NET_SESSION = new_session(model_name="u2net")

def process_leaf(input_path, output_path):
    try:
        img_pil = Image.open(input_path)
        img_no_bg = remove(img_pil, session=U2NET_SESSION)
        img_no_bg = img_no_bg.convert("RGBA")
        
        background = Image.new("RGB", img_no_bg.size, (255, 255, 255))
        background.paste(img_no_bg, mask=img_no_bg.split()[3])
        
        img_cv = cv2.cvtColor(np.array(background), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        _, leaf_mask = cv2.threshold(gray, 250, 255, cv2.THRESH_BINARY_INV)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        leaf_mask = cv2.morphologyEx(leaf_mask, cv2.MORPH_CLOSE, kernel)
        leaf_mask = cv2.morphologyEx(leaf_mask, cv2.MORPH_OPEN, kernel)
        
        contours, _ = cv2.findContours(leaf_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            raise ValueError("No leaf detected")
        
        leaf_contour = max(contours, key=cv2.contourArea)
        x, y, w_crop, h_crop = cv2.boundingRect(leaf_contour)
        cropped_leaf = img_cv[y:y+h_crop, x:x+w_crop]
        cv2.imwrite(output_path, cropped_leaf)
        
        print(json.dumps({"status": "success", "output_path": output_path}))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(json.dumps({"status": "error", "message": "Usage: process_leaf_sub.py input_path output_path"}))
    else:
        process_leaf(sys.argv[1], sys.argv[2])
