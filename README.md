# Clinical Intelligence Copilot

Small full-stack project for working with uploaded clinical notes. The app ingests text or PDF records, extracts a few useful fields, chunks content for retrieval, and returns grounded answers over the uploaded material.

The project started as a lightweight local prototype, so a few parts are intentionally simple:

- extraction is mostly regex/rule based
- local development defaults to SQLite
- embeddings can fall back to a deterministic local implementation
- answer generation can run without a paid model API

## Stack

- Backend: FastAPI, SQLAlchemy, PostgreSQL, OpenAI-compatible API integration
- Frontend: React + Vite
- Retrieval: document chunking, deterministic hash embeddings by default, optional OpenAI embeddings
- Containerization: Docker + Docker Compose

## Features

- Upload PDF, TXT, or Markdown clinical notes
- Extract patient-facing metadata and simple clinical entities
- Chunk documents and generate embeddings for semantic retrieval
- Retrieve top matching evidence snippets for user queries
- Produce source-grounded answers with citations
- Run locally with mock LLM mode or with an OpenAI-compatible API key

## Notes On The Current Implementation

- `POST /documents/upload` stores the raw file on disk and indexes chunks into the database.
- `POST /retrieve` does an in-process similarity ranking over stored chunk vectors.
- `POST /ask` reuses retrieval results and either calls an OpenAI-compatible chat endpoint or falls back to a local grounded summary.
- Right now the vector search is simple and lives in the app layer. If this grew, pgvector or a dedicated vector store would be the next obvious cleanup.

## Local Development

### Backend

```bash
cd /Users/youyangh/ai-clinical-copilot/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd /Users/youyangh/ai-clinical-copilot/frontend
npm install
npm run dev
```

The frontend expects the API at `http://localhost:8000`.

## Docker

```bash
cd /Users/youyangh/ai-clinical-copilot
docker compose up --build
```

Frontend: `http://localhost:5173`

Backend docs: `http://localhost:8000/docs`

## Optional LLM API Setup

Create `.env` in the repository root:

```bash
OPENAI_API_KEY=your_key_here
LLM_PROVIDER=openai
EMBEDDING_PROVIDER=openai
OPENAI_BASE_URL=https://api.openai.com/v1
```

If no API key is supplied, the app still works using a deterministic local embedding fallback and a grounded mock answer synthesizer.

## Demo Flow

1. Start the stack.
2. Upload [`sample_data/sample_clinical_note.txt`](/Users/youyangh/ai-clinical-copilot/sample_data/sample_clinical_note.txt).
3. Run retrieval with a query like `diabetes medication`.
4. Ask `What follow-up plan is documented?`

## Notes

- Default local development uses SQLite for convenience.
- Docker Compose uses PostgreSQL to match the production-style architecture described in the project summary.
- The embedding and answer-generation layers support OpenAI-compatible APIs, but the application remains fully demoable without paid API access.
- There are still obvious places to harden things: better PDF parsing, more robust extraction, and a real vector index once the dataset size grows.
