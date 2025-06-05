# backend/app/core/embedding.py

from sentence_transformers import SentenceTransformer

# Load a lightweight, efficient embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

def embed_text(text: str) -> list[float]:
    """
    Given a string, return its embedding vector (locally computed).
    """
    vector = model.encode(text)
    return vector.tolist()
