import fitz
import tempfile
import os
from PIL import Image
import io
import pytesseract

# If Tesseract isn't on your PATH, specify the full executable path:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def ocr_scanned_pdf_tesseract(pdf_path):
    extracted_pages = []
    doc = fitz.open(pdf_path)
    for page_index in range(doc.page_count):
        page = doc.load_page(page_index)

        zoom = 2.5
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.pil_tobytes(format="PNG")

        pil_img = Image.open(io.BytesIO(img_data))
        gray = pil_img.convert("L")

        # Optionally apply contrast‐stretch as before
        def contrast_stretch(pixel):
            if pixel < 100:
                return 0
            elif pixel > 200:
                return 255
            else:
                return int((pixel - 100) * 255 / 100)

        bw = gray.point(contrast_stretch, "L")

        # Save to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp_name = tmp.name
            bw.save(tmp_name, format="PNG")

        # Run Tesseract on that file
        text = pytesseract.image_to_string(tmp_name, lang="eng")
        lines = [l.strip() for l in text.splitlines() if l.strip() != ""]
        extracted_pages.append(lines)

        os.remove(tmp_name)

    doc.close()
    return extracted_pages

if __name__ == "__main__":
    scanned_pdf = "../docs/sample_scanned_pdf.pdf"
    print(f"Opening scanned PDF (Tesseract) at path: {scanned_pdf}")

    pages_text = ocr_scanned_pdf_tesseract(scanned_pdf)
    print(f"Total pages processed (via Tesseract OCR): {len(pages_text)}")
    for idx, lines in enumerate(pages_text):
        print(f"\n--- Page {idx+1} OCR Lines (first 5) ---")
        if not lines:
            print("  (No text detected on this page.)")
        else:
            for line in lines[:5]:
                print(f"  {line}")
