import os
import chromadb
from ..core.embedding import embed_text

CHROMA_DIR = os.path.join(os.path.dirname(__file__), "..", "chroma_db")
client = chromadb.PersistentClient(path=CHROMA_DIR)
collection = client.get_or_create_collection(
    name="doc_chunks",
    metadata={"hnsw:space": "cosine"}
)

def add_chunks_to_vector_store(doc_id: str, chunks: list[dict]):
    ids, metadatas, documents, embeddings = [], [], [], []
    for chunk in chunks:
        unique_id = f"{doc_id}__p{chunk['page_number']}__c{chunk['chunk_id']}"
        ids.append(unique_id)
        metadatas.append({
            "doc_id": doc_id,
            "page_number": chunk["page_number"],
            "chunk_id": chunk["chunk_id"]
        })
        documents.append(chunk["text"])
        embeddings.append(embed_text(chunk["text"]))
    collection.add(ids=ids, metadatas=metadatas, documents=documents, embeddings=embeddings)

def query_top_k(question: str, top_k: int = 5, doc_ids: list[str] = None) -> list[dict]:
    q_embedding = embed_text(question)
    where = None
    if doc_ids:
        where = {"doc_id": {"$in": doc_ids}}
    results = collection.query(
        query_embeddings=[q_embedding],
        n_results=top_k,
        where=where
    )
    retrieved = []
    for idx in range(len(results["ids"][0])):
        retrieved.append({
            "id": results["ids"][0][idx],
            "metadata": results["metadatas"][0][idx],
            "text": results["documents"][0][idx],
            "distance": results["distances"][0][idx]
        })
    return retrieved
