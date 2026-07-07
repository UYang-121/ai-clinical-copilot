# Clinical Intelligence Copilot

Clinical Intelligence Copilot is a portfolio-ready healthcare AI application built with FastAPI, React, PostgreSQL, Docker, and retrieval-augmented generation patterns. It simulates a clinical documentation copilot workflow: ingesting medical records, extracting structured information, retrieving relevant evidence, and generating source-grounded answers for downstream review.

This repository is intentionally shaped to support resume discussion around:

- AI-powered clinical document ingestion and metadata extraction
- RAG pipeline design with chunking, embeddings, retrieval, and grounded generation
- FastAPI service architecture for asynchronous ingestion and query workflows
- Dockerized local deployment with reproducible developer setup

## Stack

- Backend: FastAPI, SQLAlchemy, PostgreSQL, OpenAI-compatible API integration
- Frontend: React + Vite
- Retrieval: document chunking, deterministic hash embeddings by default, optional OpenAI embeddings
- Containerization: Docker + Docker Compose

## Architecture

1. Upload clinical notes through the React UI or FastAPI endpoint.
2. Persist document metadata in PostgreSQL and store raw uploads on disk.
3. Extract lightweight patient metadata and clinical entities with rule-based parsing.
4. Chunk note text, generate embeddings, and save chunk vectors for retrieval.
5. Rank relevant chunks against a user query and return evidence snippets.
6. Generate a grounded answer using either a local mock synthesizer or an OpenAI-compatible LLM API.

## Features

- Upload PDF, TXT, or Markdown clinical notes
- Extract patient-facing metadata and simple clinical entities
- Chunk documents and generate embeddings for semantic retrieval
- Retrieve top matching evidence snippets for user queries
- Produce source-grounded answers with citations
- Run locally with mock LLM mode or with an OpenAI-compatible API key

## API Surface

- `POST /documents/upload`: ingest a clinical record
- `GET /documents`: list indexed records and extracted metadata
- `POST /retrieve`: return top-k semantic matches for a query
- `POST /ask`: return a grounded answer with citations
- `GET /health`: service health check

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

## Suggested Demo Narrative

Use this framing when talking through the project:

1. A clinician or operations user uploads a progress note or discharge summary.
2. The backend extracts metadata, chunks the note, and indexes vectorized text for search.
3. A user asks for targeted information such as medications, follow-up plans, or abnormal labs.
4. The application retrieves the most relevant evidence and returns a source-grounded answer rather than an ungrounded generation.

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
