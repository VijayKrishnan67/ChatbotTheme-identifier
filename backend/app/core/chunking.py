# backend/app/core/chunking.py

import re
from typing import List, Dict

def chunk_pdf_text_pages(
    pages: List[str],
    max_para_chars: int = 1000
) -> List[Dict]:
    """
    Splits embedded PDF pages into smaller chunks (paragraphs).
    
    Args:
        pages (List[str]): List of page strings.
        max_para_chars (int): Max characters per chunk (adjustable later).

    Returns:
        List[Dict]: Each chunk has page number, chunk_id, and text.
    """
    chunks = []
    chunk_counter = 0

    for page_idx, page_text in enumerate(pages, start=1):
        # Attempt splitting into paragraphs by double newlines.
        paras = [p.strip() for p in page_text.split("\n\n") if p.strip()]

        # If no paragraphs detected, split by sentence.
        if not paras:
            paras = []
            for sent in re.split(r'\.\s+', page_text):
                s = sent.strip()
                if s:
                    paras.append(s + ".")

        for para in paras:
            # Handle very long paragraphs (optional for now).
            chunk_counter += 1
            chunks.append({
                "page_number": page_idx,
                "chunk_id": chunk_counter,
                "text": para
            })

    return chunks


def chunk_ocr_lines(
    pages_of_lines: List[List[str]],
    max_lines_per_chunk: int = 10
) -> List[Dict]:
    """
    Chunks OCR-extracted text (from scanned PDF or images).

    Args:
        pages_of_lines (List[List[str]]): List of pages with OCR lines.
        max_lines_per_chunk (int): Number of OCR lines per chunk.

    Returns:
        List[Dict]: Chunks with page number, chunk_id, and combined text.
    """
    chunks = []
    chunk_counter = 0

    for page_idx, lines in enumerate(pages_of_lines, start=1):
        for i in range(0, len(lines), max_lines_per_chunk):
            block = lines[i:i+max_lines_per_chunk]
            combined = " ".join(block).strip()
            if combined:
                chunk_counter += 1
                chunks.append({
                    "page_number": page_idx,
                    "chunk_id": chunk_counter,
                    "text": combined
                })

    return chunks
