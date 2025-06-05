# backend/app/main.py

import os
import shutil
import tempfile
import fitz  # PyMuPDF
import pytesseract
from fastapi import FastAPI, File, UploadFile, HTTPException, Body
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import io
import json
from datetime import datetime
from typing import List, Optional

# ==== FIXED: Use ABSOLUTE imports for package ====
from app.services.vector_store import query_top_k
from app.services.llm import llama3_answer

app = FastAPI(title="Document Research & Theme Identifier")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev only. Restrict in prod!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------------
# PERSISTENCE HELPERS
# -------------------------------------------------------------------

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
INDEX_PATH = os.path.join(DATA_DIR, "index.json")

def load_index():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(INDEX_PATH):
        index = {"next_id": 1, "documents": []}
        with open(INDEX_PATH, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2)
        return index
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_index(index_data):
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index_data, f, indent=2)

def persist_document(filename: str, extraction_method: str, extracted_text):
    index_data = load_index()
    next_id = index_data["next_id"]
    doc_id = f"DOC{next_id:03d}"  # e.g. "DOC001"
    upload_record = {
        "doc_id": doc_id,
        "filename": filename,
        "extraction_method": extraction_method,
        "upload_time": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    }
    index_data["documents"].append(upload_record)
    index_data["next_id"] = next_id + 1
    save_index(index_data)
    doc_data = {
        "doc_id": doc_id,
        "filename": filename,
        "extraction_method": extraction_method,
        "upload_time": upload_record["upload_time"],
        "content": extracted_text
    }
    doc_path = os.path.join(DATA_DIR, f"{doc_id}.json")
    with open(doc_path, "w", encoding="utf-8") as f:
        json.dump(doc_data, f, ensure_ascii=False, indent=2)
    return doc_id

# -------------------------------------------------------------------
# END OF PERSISTENCE HELPERS
# -------------------------------------------------------------------

def extract_text_from_pdf(pdf_path: str):
    texts = []
    doc = fitz.open(pdf_path)
    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        texts.append(page.get_text("text"))
    doc.close()
    return texts

def ocr_scanned_pdf_tesseract(pdf_path: str):
    extracted_pages = []
    doc = fitz.open(pdf_path)
    for page_index in range(doc.page_count):
        page = doc.load_page(page_index)
        zoom = 2.5
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.pil_tobytes(format="PNG")
        pil_img = Image.open(io.BytesIO(img_data)).convert("L")
        def contrast_stretch(pixel):
            if pixel < 100:
                return 0
            elif pixel > 200:
                return 255
            else:
                return int((pixel - 100) * 255 / 100)
        bw = pil_img.point(contrast_stretch, "L")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp_name = tmp.name
            bw.save(tmp_name, format="PNG")
        text = pytesseract.image_to_string(tmp_name, lang="eng")
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        extracted_pages.append(lines)
        os.remove(tmp_name)
    doc.close()
    return extracted_pages

def ocr_image_tesseract(image_path: str):
    pil_img = Image.open(image_path).convert("L")
    def contrast_stretch(pixel):
        if pixel < 100:
            return 0
        elif pixel > 200:
            return 255
        else:
            return int((pixel - 100) * 255 / 100)
    bw = pil_img.point(contrast_stretch, "L")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        tmp_name = tmp.name
        bw.save(tmp_name, format="PNG")
    text = pytesseract.image_to_string(tmp_name, lang="eng")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    os.remove(tmp_name)
    return lines

@app.get("/health")
async def health_check():
    return {"status": "OK", "message": "Service is up and running."}

@app.post("/upload/")
async def upload_document(file: UploadFile = File(...)):
    upload_dir = "temp_uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    suffix = file.filename.rsplit(".", 1)[-1].lower()
    if suffix in ("jpg", "jpeg", "png", "bmp", "tiff"):
        lines = ocr_image_tesseract(file_path)
        os.remove(file_path)
        doc_id = persist_document(file.filename, "image-ocr", lines)
        return {
            "doc_id": doc_id,
            "filename": file.filename,
            "extraction_method": "image-ocr",
            "extracted_text": lines,
        }
    elif suffix == "pdf":
        pages = extract_text_from_pdf(file_path)
        if any(txt.strip() for txt in pages):
            os.remove(file_path)
            doc_id = persist_document(file.filename, "pdf-text", pages)
            return {
                "doc_id": doc_id,
                "filename": file.filename,
                "extraction_method": "pdf-text",
                "extracted_text": pages,
            }
        else:
            pages_ocr = ocr_scanned_pdf_tesseract(file_path)
            os.remove(file_path)
            doc_id = persist_document(file.filename, "pdf-ocr", pages_ocr)
            return {
                "doc_id": doc_id,
                "filename": file.filename,
                "extraction_method": "pdf-ocr",
                "extracted_text": pages_ocr,
            }
    else:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail="Unsupported file type. Upload a PDF or image.")

@app.get("/documents/")
async def list_documents():
    index_data = load_index()
    return index_data["documents"]

@app.get("/documents/{doc_id}")
async def get_document(doc_id: str):
    doc_path = os.path.join(DATA_DIR, f"{doc_id}.json")
    if not os.path.exists(doc_path):
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found.")
    with open(doc_path, "r", encoding="utf-8") as f:
        return json.load(f)

@app.post("/answer/")
async def answer_query(
    query: str = Body(..., embed=True),
    doc_ids: Optional[List[str]] = Body(None, embed=True),
    top_k: int = Body(5, embed=True)
):
    results = query_top_k(query, top_k=top_k, doc_ids=doc_ids)
    if not results:
        return {"answer": "No relevant information found in the selected documents."}
    answer = llama3_answer(query, results)
    return {
        "answer": answer,
        "chunks_used": results
    }
