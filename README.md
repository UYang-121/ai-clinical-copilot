# AI Clinical Copilot

AI Clinical Copilot is a full-stack clinical document assistant built with FastAPI, React, PostgreSQL, Docker, and retrieval-augmented generation patterns. The app supports medical record upload, lightweight entity extraction, semantic retrieval, and source-grounded question answering.

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

## Resume Alignment

This project demonstrates:

- AI-powered clinical document ingestion and metadata extraction
- RAG-style chunking, embeddings, retrieval, and grounded generation
- FastAPI service design for ingestion, retrieval, and Q&A
- Dockerized local deployment with reproducible setup instructions
