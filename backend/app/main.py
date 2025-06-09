import os
import shutil
import tempfile
import io
import json
from datetime import datetime
from typing import List, Optional

import fitz                    # PyMuPDF
import pytesseract
from PIL import Image
from fastapi import FastAPI, File, UploadFile, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware

# chunking helpers
from app.core.chunking import chunk_pdf_text_pages, chunk_ocr_lines

# persistence & indexing
from app.services.vector_store import add_chunks_to_vector_store, query_top_k
from app.services.llm import llama3_answer



from app.services.vector_store import add_chunks_to_vector_store, query_top_k, delete_doc_chunks




app = FastAPI(title="Document Research & Theme Identifier")

# CORS (enable your React frontend to call us)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev only—lock this down in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------------
# File‐based persistence: data/index.json + per‐doc files
# -------------------------------------------------------------------
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
INDEX_PATH = os.path.join(DATA_DIR, "index.json")

def load_index():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(INDEX_PATH):
        idx = {"next_id": 1, "documents": []}
        with open(INDEX_PATH, "w", encoding="utf-8") as f:
            json.dump(idx, f, indent=2)
        return idx
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_index(index_data):
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index_data, f, indent=2)

def persist_document(filename: str, extraction_method: str, extracted_text):
    """
    1) Assigns new DOC### ID
    2) Updates data/index.json
    3) Writes data/DOC###.json with metadata + content
    """
    idx = load_index()
    nid = idx["next_id"]
    doc_id = f"DOC{nid:03d}"

    record = {
        "doc_id": doc_id,
        "filename": filename,
        "extraction_method": extraction_method,
        "upload_time": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    }
    idx["documents"].append(record)
    idx["next_id"] = nid + 1
    save_index(idx)

    doc_data = {
        **record,
        "content": extracted_text
    }
    out_path = os.path.join(DATA_DIR, f"{doc_id}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(doc_data, f, ensure_ascii=False, indent=2)

    return doc_id

# -------------------------------------------------------------------
# Text extraction routines
# -------------------------------------------------------------------
def extract_text_from_pdf(pdf_path: str) -> List[str]:
    texts = []
    doc = fitz.open(pdf_path)
    for i in range(doc.page_count):
        texts.append(doc.load_page(i).get_text("text"))
    doc.close()
    return texts

def ocr_scanned_pdf_tesseract(pdf_path: str) -> List[List[str]]:
    pages = []
    doc = fitz.open(pdf_path)
    for i in range(doc.page_count):
        page = doc.load_page(i)
        mat = fitz.Matrix(2.5, 2.5)  # ~180 DPI
        pix = page.get_pixmap(matrix=mat)
        png = pix.pil_tobytes(format="PNG")
        img = Image.open(io.BytesIO(png)).convert("L")
        def stretch(p): return 0 if p<100 else (255 if p>200 else int((p-100)*255/100))
        bw = img.point(stretch, "L")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp_name = tmp.name
            bw.save(tmp_name, format="PNG")
        text = pytesseract.image_to_string(tmp_name, lang="eng")
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        pages.append(lines)
        os.remove(tmp_name)
    doc.close()
    return pages

def ocr_image_tesseract(image_path: str) -> List[str]:
    img = Image.open(image_path).convert("L")
    def stretch(p): return 0 if p<100 else (255 if p>200 else int((p-100)*255/100))
    bw = img.point(stretch, "L")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        tmp_name = tmp.name
        bw.save(tmp_name, format="PNG")
    text = pytesseract.image_to_string(tmp_name, lang="eng")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    os.remove(tmp_name)
    return lines

# -------------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------------
@app.get("/health")
async def health_check():
    return {"status": "OK", "message": "Service is up and running."}

@app.post("/upload/")
async def upload_document(file: UploadFile = File(...)):
    """
    1) Save file
    2) Extract text via embedded‐PDF or OCR
    3) Persist JSON → get doc_id
    4) Chunk + index chunks
    5) Return metadata + extracted lines/pages
    """
    tmp_dir = "temp_uploads"
    os.makedirs(tmp_dir, exist_ok=True)
    fp = os.path.join(tmp_dir, file.filename)
    with open(fp, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext in ("jpg","jpeg","png","bmp","tiff"):
        lines = ocr_image_tesseract(fp)
        os.remove(fp)

        doc_id = persist_document(file.filename, "image-ocr", lines)
        chunks = chunk_ocr_lines([lines], max_lines_per_chunk=20)
        print(f"[DEBUG] image-ocr: {file.filename} → {len(chunks)} chunks")
        add_chunks_to_vector_store(doc_id, chunks)

        return {
            "doc_id": doc_id,
            "filename": file.filename,
            "extraction_method": "image-ocr",
            "extracted_text": lines
        }

    elif ext == "pdf":
        pages = extract_text_from_pdf(fp)
        if any(p.strip() for p in pages):
            os.remove(fp)

            doc_id = persist_document(file.filename, "pdf-text", pages)
            chunks = chunk_pdf_text_pages(pages)
            print(f"[DEBUG] pdf-text: {file.filename} → {len(chunks)} chunks")
            add_chunks_to_vector_store(doc_id, chunks)

            return {
                "doc_id": doc_id,
                "filename": file.filename,
                "extraction_method": "pdf-text",
                "extracted_text": pages
            }
        else:
            pages_ocr = ocr_scanned_pdf_tesseract(fp)
            os.remove(fp)

            doc_id = persist_document(file.filename, "pdf-ocr", pages_ocr)
            chunks = chunk_ocr_lines(pages_ocr, max_lines_per_chunk=20)
            print(f"[DEBUG] pdf-ocr: {file.filename} → {len(chunks)} chunks")
            add_chunks_to_vector_store(doc_id, chunks)

            return {
                "doc_id": doc_id,
                "filename": file.filename,
                "extraction_method": "pdf-ocr",
                "extracted_text": pages_ocr
            }

    else:
        os.remove(fp)
        raise HTTPException(400, "Unsupported file type. Upload a PDF or image.")

@app.get("/documents/")
async def list_documents():
    return load_index()["documents"]

@app.get("/documents/{doc_id}")
async def get_document(doc_id: str):
    p = os.path.join(DATA_DIR, f"{doc_id}.json")
    if not os.path.exists(p):
        raise HTTPException(404, f"{doc_id} not found.")
    return json.load(open(p, "r", encoding="utf-8"))

@app.post("/answer/")
async def answer_query(
    query: str = Body(..., embed=True),
    doc_ids: Optional[List[str]] = Body(None, embed=True),
    top_k: int = Body(5, embed=True)
):
    chunks = query_top_k(query, top_k=top_k, doc_ids=doc_ids or [])
    if not chunks:
        return {"answer": "No relevant information found in the selected documents."}
    ans = llama3_answer(query, chunks)
    return {"answer": ans, "chunks_used": chunks}

