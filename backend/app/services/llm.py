import os
from groq import Groq

API_KEY = os.getenv(
    "GROQ_API_KEY",
    "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"
)
client = Groq(api_key=API_KEY)

def llama3_answer(
    query: str,
    chunks: list[dict],
    max_tokens: int = 1024
) -> str:
    context = ""
    for chunk in chunks:
        md = chunk["metadata"]
        cite = f"[{md['doc_id']}, page {md['page_number']}, chunk {md['chunk_id']}]"
        context += f"{cite}: {chunk['text']}\n"

    prompt = f"""You are a highly intelligent research assistant.

Your goal is to help the user understand the themes and ideas across multiple documents.

Follow these steps strictly:
1. Read the context chunks below.
2. Identify and group **distinct themes** based on the information.
3. For each theme, write:
   - A clear heading for the theme.
   - A brief explanation.
   - Supporting quotes or insights with citations like [DOC007, page 8, chunk 13].

Context:
{context}

User Question:
{query}

Answer Format:
Theme 1 – [Short Title]
Explanation...
Supporting details... [citation]

Theme 2 – [Short Title]
...

Answer: 
"""

    resp = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.2,
        top_p=1,
        stream=False
    )
    return resp.choices[0].message.content.strip()
