import React, { useState } from "react";
import axios from "axios";

const BACKEND_URL = "http://localhost:8000"; // Change if running elsewhere

function App() {
  // State
  const [file, setFile] = useState(null);
  const [docs, setDocs] = useState([]);
  const [query, setQuery] = useState("");
  const [selectedDocs, setSelectedDocs] = useState([]);
  const [answer, setAnswer] = useState("");
  const [chunks, setChunks] = useState([]);
  const [loading, setLoading] = useState(false);

  // Upload
  const handleUpload = async () => {
    if (!file) return alert("Select a file first!");
    const formData = new FormData();
    formData.append("file", file);
    setLoading(true);
    try {
      await axios.post(`${BACKEND_URL}/upload/`, formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      alert("Uploaded!");
      fetchDocs();
    } catch (err) {
      alert("Upload failed!");
    }
    setLoading(false);
  };

  // Fetch docs
  const fetchDocs = async () => {
    const res = await axios.get(`${BACKEND_URL}/documents/`);
    setDocs(res.data);
  };

  // Handle question
  const handleAsk = async () => {
    if (!query) return alert("Enter a question!");
    setLoading(true);
    setAnswer("");
    setChunks([]);
    try {
      const body = {
        query,
        doc_ids: selectedDocs.length ? selectedDocs : null,
        top_k: 5
      };
      const res = await axios.post(`${BACKEND_URL}/answer/`, body);
      setAnswer(res.data.answer);
      setChunks(res.data.chunks_used || []);
    } catch (err) {
      setAnswer("Something went wrong.");
    }
    setLoading(false);
  };

  // On mount, fetch documents
  React.useEffect(() => {
    fetchDocs();
    // eslint-disable-next-line
  }, []);

  // Handle doc selection
  const toggleDoc = (doc_id) => {
    setSelectedDocs((sel) =>
      sel.includes(doc_id) ? sel.filter((d) => d !== doc_id) : [...sel, doc_id]
    );
  };

  return (
    <div style={{ maxWidth: 900, margin: "2rem auto", padding: 20 }}>
      <h2>Document Research & Theme Identifier Chatbot</h2>

      {/* Upload */}
      <section style={{ marginBottom: 30 }}>
        <h4>1. Upload Document</h4>
        <input type="file" onChange={e => setFile(e.target.files[0])} />
        <button onClick={handleUpload} disabled={loading}>Upload</button>
      </section>

      {/* Docs */}
      <section style={{ marginBottom: 30 }}>
        <h4>2. Uploaded Documents</h4>
        <table border={1} cellPadding={5} cellSpacing={0} width="100%">
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
            {docs.map(doc => (
              <tr key={doc.doc_id}>
                <td>
                  <input
                    type="checkbox"
                    checked={selectedDocs.includes(doc.doc_id)}
                    onChange={() => toggleDoc(doc.doc_id)}
                  />
                </td>
                <td>{doc.doc_id}</td>
                <td>{doc.filename}</td>
                <td>{doc.extraction_method}</td>
                <td>{doc.upload_time.replace("T", " ").replace("Z", "")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* Ask */}
      <section>
        <h4>3. Ask a Research Question</h4>
        <input
          style={{ width: "80%", fontSize: "1rem", padding: 8 }}
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="e.g. What penalties are imposed for non-compliance?"
        />
        <button onClick={handleAsk} disabled={loading}>Ask</button>
      </section>

      {/* Output */}
      {loading && <p>Loading...</p>}
      {answer && (
        <section style={{ marginTop: 30 }}>
          <h4>Answer</h4>
          <div style={{ background: "#eee", padding: 15, borderRadius: 6 }}>
            {answer}
          </div>
          {chunks.length > 0 && (
            <>
              <h5 style={{ marginTop: 20 }}>Citations (Top Chunks Used):</h5>
              <ul>
                {chunks.map((ch, i) => (
                  <li key={i}>
                    <strong>[{ch.metadata.doc_id}, page {ch.metadata.page_number}, chunk {ch.metadata.chunk_id}]</strong>:<br />
                    <span style={{ color: "#555" }}>{ch.text}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>
      )}
    </div>
  );
}

export default App;
