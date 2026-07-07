from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.database import Base, engine, get_db
from app.models import Document, DocumentChunk
from app.schemas import AskRequest, AskResponse, AnswerCitation, DocumentResponse, RetrievalMatch, RetrievalRequest
from app.services import ingest_document, maybe_generate_llm_answer, retrieve_chunks


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def healthcheck() -> dict:
    return {"status": "ok"}


@app.get("/documents", response_model=list[DocumentResponse])
def list_documents(db: Session = Depends(get_db)) -> list[Document]:
    return db.scalars(select(Document).order_by(Document.created_at.desc())).all()


@app.post("/documents/upload", response_model=DocumentResponse)
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)) -> Document:
    contents = await file.read()
    return await ingest_document(db, file.filename, file.content_type or "text/plain", contents)


@app.post("/retrieve", response_model=list[RetrievalMatch])
async def retrieve(request: RetrievalRequest, db: Session = Depends(get_db)) -> list[RetrievalMatch]:
    matches = await retrieve_chunks(db, request.query, request.top_k)
    return [
        RetrievalMatch(
            document_id=chunk.document_id,
            chunk_id=chunk.id,
            filename=chunk.document.filename,
            score=round(score, 4),
            snippet=chunk.content[:240],
            relevance_hint=chunk.relevance_hint,
        )
        for chunk, score in matches
    ]


@app.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest, db: Session = Depends(get_db)) -> AskResponse:
    matches = await retrieve_chunks(db, request.question, request.top_k)
    hydrated_chunks = db.scalars(
        select(DocumentChunk)
        .where(DocumentChunk.id.in_([chunk.id for chunk, _ in matches]))
        .options(selectinload(DocumentChunk.document))
    ).all()
    chunk_lookup = {chunk.id: chunk for chunk in hydrated_chunks}
    ordered_chunks = [chunk_lookup[chunk.id] for chunk, _ in matches if chunk.id in chunk_lookup]
    answer = await maybe_generate_llm_answer(request.question, ordered_chunks)
    citations = [
        AnswerCitation(
            document_id=chunk.document_id,
            chunk_id=chunk.id,
            filename=chunk.document.filename,
            snippet=chunk.content[:220],
            score=round(score, 4),
        )
        for chunk, score in matches
    ]
    return AskResponse(answer=answer, citations=citations)

