import os
import chromadb
from app.core.embedding import embed_text

# Persistent ChromaDB directory
VECTOR_DB_DIR = os.path.join(os.path.dirname(__file__), "..", "chroma_db")
client = chromadb.PersistentClient(path=VECTOR_DB_DIR)

def get_vector_collection():
    return client.get_or_create_collection(
        name="doc_chunks",
        metadata={"hnsw:space": "cosine"}
    )

def add_chunks_to_vector_store(doc_id: str, chunks: list[dict]):
    collection = get_vector_collection()
    ids, metadatas, docs, embs = [], [], [], []
    for c in chunks:
        uid = f"{doc_id}__p{c['page_number']}__c{c['chunk_id']}"
        ids.append(uid)
        metadatas.append({
            "doc_id": doc_id,
            "page_number": c["page_number"],
            "chunk_id": c["chunk_id"]
        })
        docs.append(c["text"])
        embs.append(embed_text(c["text"]))
    collection.add(ids=ids, metadatas=metadatas, documents=docs, embeddings=embs)

def query_top_k(question: str, top_k: int = 5, doc_ids: list[str] = None) -> list[dict]:
    collection = get_vector_collection()
    q_emb = embed_text(question)
    kwargs = {"query_embeddings": [q_emb], "n_results": top_k}
    if doc_ids:
        kwargs["where"] = {"doc_id": {"$in": doc_ids}}
    res = collection.query(**kwargs)
    out = []
    for i in range(len(res["ids"][0])):
        out.append({
            "id": res["ids"][0][i],
            "metadata": res["metadatas"][0][i],
            "text": res["documents"][0][i],
            "distance": res["distances"][0][i]
        })
    return out

def delete_doc_chunks(doc_id: str):
    if not os.path.exists(VECTOR_DB_DIR):
        return
    collection = get_vector_collection()
    all_ids = collection.get()["ids"]
    ids_to_delete = [id for id in all_ids if id.startswith(f"{doc_id}__")]
    if ids_to_delete:
        collection.delete(ids=ids_to_delete)
