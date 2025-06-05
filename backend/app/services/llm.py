import os
from groq import Groq

# For production, load API key from env. For now, you can hardcode if needed
client = Groq(api_key=os.environ.get("GROQ_API_KEY", "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"))

def llama3_answer(query: str, chunks: list[dict], max_tokens: int = 512) -> str:
    context = ""
    for chunk in chunks:
        md = chunk["metadata"]
        cite = f"[{md['doc_id']}, page {md['page_number']}, chunk {md['chunk_id']}]"
        context += f"{cite}: {chunk['text']}\n"
    prompt = f"""You are a helpful assistant. Use ONLY the provided context to answer.
If possible, cite sources in square brackets.

Context:
{context}

User question: {query}

Answer with detailed info and include clear citations like [DOC001, page 1, chunk 2].
"""
    response = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.2,
        top_p=1,
        stream=False,
        stop=None
    )
    return response.choices[0].message.content.strip()
