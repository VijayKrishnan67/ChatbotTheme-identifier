// frontend/src/App.js
import React, { useEffect, useState } from 'react';

function App() {
  const [docs, setDocs] = useState([]);
  const [selected, setSelected] = useState({});
  const [file, setFile] = useState(null);
  const [query, setQuery] = useState('');
  const [answer, setAnswer] = useState(null);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [loadingAnswer, setLoadingAnswer] = useState(false);

  const API = 'http://127.0.0.1:8000';

  useEffect(() => {
    fetchDocs();
  }, []);

  const fetchDocs = async () => {
    setLoadingDocs(true);
    try {
      const res = await fetch(`${API}/documents/`);
      const data = await res.json();
      setDocs(data);
    } catch (err) {
      console.error('Error fetching documents:', err);
    }
    setLoadingDocs(false);
  };

  const onFileChange = (e) => setFile(e.target.files[0]);

  const uploadDoc = async () => {
    if (!file) {
      alert('Please choose a file first.');
      return;
    }

    const form = new FormData();
    form.append('file', file);

    try {
      await fetch(`${API}/upload/`, {
        method: 'POST',
        body: form,
      });
      setFile(null);
      document.getElementById('file-input').value = '';
      fetchDocs();
    } catch (err) {
      console.error('Upload error:', err);
      alert('Upload failed, see console.');
    }
  };

  const toggleDoc = (docId) =>
    setSelected((prev) => ({ ...prev, [docId]: !prev[docId] }));

  const askQuestion = async () => {
    if (!query.trim()) return;
    setLoadingAnswer(true);
    setAnswer(null);

    const chosenIds = Object.keys(selected).filter((id) => selected[id]);
    const body = {
      query,
      doc_ids: chosenIds.length ? chosenIds : undefined,
      top_k: 5,
    };

    try {
      const res = await fetch(`${API}/answer/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      setAnswer(data);
    } catch (err) {
      console.error('Error getting answer:', err);
      alert('Failed to get answer, see console.');
    }
    setLoadingAnswer(false);
  };

  return (
    <div style={{ padding: 20, fontFamily: 'sans-serif' }}>
      <h1>Document Research &amp; Theme Identifier Chatbot</h1>

      {/* 1. Upload */}
      <section>
        <h2>1. Upload Document</h2>
        <input id="file-input" type="file" onChange={onFileChange} style={{ marginRight: 8 }} />
        <button onClick={uploadDoc}>Upload</button>
      </section>

      {/* 2. Uploaded Docs */}
      <section style={{ marginTop: 30 }}>
        <h2>2. Uploaded Documents</h2>
        {loadingDocs ? (
          <p>Loading documents…</p>
        ) : (
          <table border="1" cellPadding="8" style={{ borderCollapse: 'collapse', width: '100%' }}>
            <thead>
              <tr>
                <th>Select</th>
                <th>Doc ID</th>
                <th>Filename</th>
                <th>Type</th>
                <th>Uploaded</th>
              </tr>
            </thead>
            <tbody>
              {docs.map((doc) => (
                <tr key={doc.doc_id}>
                  <td>
                    <input
                      type="checkbox"
                      checked={!!selected[doc.doc_id]}
                      onChange={() => toggleDoc(doc.doc_id)}
                    />
                  </td>
                  <td>{doc.doc_id}</td>
                  <td>{doc.filename}</td>
                  <td>{doc.extraction_method}</td>
                  <td>{doc.upload_time?.replace('T', ' ').replace('Z', '')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* 3. Ask Question */}
      <section style={{ marginTop: 30 }}>
        <h2>3. Ask a Research Question</h2>
        <input
          type="text"
          style={{ width: '60%', marginRight: 8 }}
          placeholder="e.g. What penalties are imposed for non-compliance?"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button onClick={askQuestion} disabled={loadingAnswer}>
          {loadingAnswer ? 'Asking…' : 'Ask'}
        </button>
      </section>

      {/* 4. Answer */}
      {answer && (
        <section style={{ marginTop: 30 }}>
          <h2>Answer</h2>
          <div
            style={{
              background: '#f5f5f5',
              padding: 16,
              borderRadius: 4,
              whiteSpace: 'pre-wrap',
            }}
          >
            {answer.answer}
          </div>

          {answer.chunks_used && answer.chunks_used.length > 0 && (
            <>
              <h3 style={{ marginTop: 20 }}>Citations (Top Chunks Used):</h3>
              <ul>
                {answer.chunks_used.map((chunk, i) => {
                  const md = chunk.metadata;
                  const cite = `[${md.doc_id}, page ${md.page_number}, chunk ${md.chunk_id}]`;
                  return (
                    <li key={i} style={{ marginBottom: 10 }}>
                      <strong>{cite}:</strong>{' '}
                      <em>{chunk.text.length > 300 ? chunk.text.slice(0, 300) + '…' : chunk.text}</em>
                    </li>
                  );
                })}
              </ul>
            </>
          )}
        </section>
      )}
    </div>
  );
}

export default App;