# backend/pdf_text_demo.py

import fitz  # PyMuPDF

def extract_text_from_pdf(pdf_path):
    """
    Extracts plain text from each page of the PDF at 'pdf_path'.
    Returns a list where each element is the full text of that page.
    """
    texts = []
    doc = fitz.open(pdf_path)
    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        texts.append(page.get_text("text"))
    doc.close()
    return texts

if __name__ == "__main__":
    # Hard-coded sample PDF path
    sample_pdf = "../docs/sample_text_based.pdf"

    # DEBUG: Print that we’re about to open the PDF file
    print(f"Opening PDF at path: {sample_pdf}")

    # Call the function to extract text
    pages = extract_text_from_pdf(sample_pdf)
    
    # DEBUG: Print how many pages we got back
    print(f"Extracted {len(pages)} pages.")

    for i, txt in enumerate(pages[:2]):
        print(f"\n--- Page {i+1} (first 200 chars) ---")
        print(txt[:200] + "...\n")
