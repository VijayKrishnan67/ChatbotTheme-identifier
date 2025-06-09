# backend/app/core/chunking.py

import re
from typing import List, Dict

def is_valid_chunk(text: str) -> bool:
    text = text.strip()
    if len(text) < 50:
        return False
    if len(set(text)) < 10:
        return False
    alpha_ratio = sum(c.isalpha() for c in text) / max(len(text), 1)
    if alpha_ratio < 0.3:
        return False
    return True

def chunk_pdf_text_pages(
    pages: List[str],
    max_para_chars: int = 1000,
    max_lines_per_chunk: int = 20
) -> List[Dict]:
    """
    Splits embedded PDF pages into smaller chunks:
      - First by paragraphs (double-newline).
      - If a paragraph exceeds max_para_chars, split it into
        sub-chunks of at most max_lines_per_chunk lines each.

    Returns List of {"page_number", "chunk_id", "text"}.
    """
    chunks = []
    chunk_counter = 0

    for page_idx, page_text in enumerate(pages, start=1):
        # 1) Split into paragraphs
        paras = [p.strip() for p in page_text.split("\n\n") if p.strip()]

        # Fallback: split by sentences if no paragraphs found
        if not paras:
            paras = [s.strip() + "." for s in re.split(r'\.\s+', page_text) if s.strip()]

        for para in paras:
            if len(para) <= max_para_chars:
                if is_valid_chunk(para):
                    chunk_counter += 1
                    chunks.append({
                        "page_number": page_idx,
                        "chunk_id": chunk_counter,
                        "text": para
                    })
            else:
                lines = para.splitlines()
                for i in range(0, len(lines), max_lines_per_chunk):
                    sub = "\n".join(lines[i : i + max_lines_per_chunk])
                    if is_valid_chunk(sub):
                        chunk_counter += 1
                        chunks.append({
                            "page_number": page_idx,
                            "chunk_id": chunk_counter,
                            "text": sub
                        })

    return chunks

def chunk_ocr_lines(
    pages: List[List[str]],
    max_lines_per_chunk: int = 20
) -> List[Dict]:
    """
    Splits OCR’d pages (lists of lines) into chunks of at most max_lines_per_chunk lines,
    concatenating each group into one text string.
    """
    chunks = []
    chunk_counter = 0

    for page_num, lines in enumerate(pages, start=1):
        for i in range(0, len(lines), max_lines_per_chunk):
            group = lines[i : i + max_lines_per_chunk]
            text = " ".join(group)
            if is_valid_chunk(text):
                chunk_counter += 1
                chunks.append({
                    "page_number": page_num,
                    "chunk_id": chunk_counter,
                    "text": text
                })

    return chunks
