# backend/ocr_demo.py

import easyocr
from PIL import Image
import numpy as np

def ocr_image(image_path):
    """
    Runs OCR on the provided image file and returns a list of recognized text lines.
    """
    # Initialize the EasyOCR Reader (English only). If you have a GPU, set gpu=True.
    reader = easyocr.Reader(['en'], gpu=False)

    # reader.readtext(image_path, detail=0) returns a list of recognized text strings.
    result = reader.readtext(image_path, detail=0)

    return result

if __name__ == "__main__":
    # Adjusted to point to the .jpg file under `docs/`
    sample_image = "../docs/sample_scanned_page.jpg"

    # Run OCR on that image:
    lines = ocr_image(sample_image)

    print(f"\nOCR Output for '{sample_image}':")
    if not lines:
        print("  (No text detected. Check that the image exists and contains legible text.)\n")
    else:
        for idx, line in enumerate(lines):
            print(f"  {idx+1}: {line}")
