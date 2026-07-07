import { useEffect, useState } from 'react';

const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

async function parseJson(response) {
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

function Section({ title, children }) {
  return (
    <section className="panel">
      <div className="section-header">
        <h2>{title}</h2>
      </div>
      {children}
    </section>
  );
}

export default function App() {
  const [documents, setDocuments] = useState([]);
  const [query, setQuery] = useState('diabetes medication follow-up');
  const [question, setQuestion] = useState('What follow-up plan is documented?');
  const [retrievalResults, setRetrievalResults] = useState([]);
  const [answer, setAnswer] = useState(null);
  const [status, setStatus] = useState('Ready');

  async function loadDocuments() {
    const data = await parseJson(await fetch(`${apiBase}/documents`));
    setDocuments(data);
  }

  useEffect(() => {
    loadDocuments().catch((error) => setStatus(error.message));
  }, []);

  async function handleUpload(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    setStatus(`Uploading ${file.name}...`);
    await parseJson(
      await fetch(`${apiBase}/documents/upload`, {
        method: 'POST',
        body: formData,
      }),
    );
    await loadDocuments();
    setStatus(`Indexed ${file.name}`);
  }

  async function handleRetrieve() {
    setStatus('Running retrieval...');
    const data = await parseJson(
      await fetch(`${apiBase}/retrieve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, top_k: 5 }),
      }),
    );
    setRetrievalResults(data);
    setStatus(`Retrieved ${data.length} chunks`);
  }

  async function handleAsk() {
    setStatus('Generating grounded answer...');
    const data = await parseJson(
      await fetch(`${apiBase}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, top_k: 5 }),
      }),
    );
    setAnswer(data);
    setStatus('Answer ready');
  }

  return (
    <main className="app-shell">
      <header className="hero">
        <p className="eyebrow">Clinical Note Search</p>
        <h1>Clinical Intelligence Copilot</h1>
        <p className="lede">
          Upload notes, extract a few structured fields, search semantically, and ask grounded
          questions against the indexed records.
        </p>
        <div className="status-pill">{status}</div>
      </header>

      <div className="grid">
        <Section title="Ingestion">
          <label className="upload-box">
            <span>Upload PDF or text notes</span>
            <input type="file" accept=".pdf,.txt,.md" onChange={handleUpload} />
          </label>
          <div className="document-list">
            {documents.map((doc) => (
              <article className="document-card" key={doc.id}>
                <div className="document-meta">
                  <strong>{doc.filename}</strong>
                  <span>{doc.document_type || 'Clinical Note'}</span>
                  <span>{doc.patient_name || 'Unknown patient'}</span>
                </div>
                <p>{doc.summary || 'No summary available.'}</p>
              </article>
            ))}
            {documents.length === 0 && <p className="empty">No records indexed yet.</p>}
          </div>
        </Section>

        <Section title="Retrieval">
          <textarea value={query} onChange={(event) => setQuery(event.target.value)} rows={4} />
          <button onClick={handleRetrieve}>Retrieve Evidence</button>
          <div className="result-list">
            {retrievalResults.map((result) => (
              <article className="result-card" key={result.chunk_id}>
                <div className="result-header">
                  <strong>{result.filename}</strong>
                  <span>{result.score}</span>
                </div>
                <p>{result.snippet}</p>
              </article>
            ))}
          </div>
        </Section>

        <Section title="Grounded Q&A">
          <textarea value={question} onChange={(event) => setQuestion(event.target.value)} rows={4} />
          <button onClick={handleAsk}>Generate Answer</button>
          {answer && (
            <div className="answer-card">
              <pre>{answer.answer}</pre>
              <div className="citation-list">
                {answer.citations.map((citation) => (
                  <article className="result-card" key={citation.chunk_id}>
                    <div className="result-header">
                      <strong>{citation.filename}</strong>
                      <span>{citation.score}</span>
                    </div>
                    <p>{citation.snippet}</p>
                  </article>
                ))}
              </div>
            </div>
          )}
        </Section>
      </div>
    </main>
  );
}
