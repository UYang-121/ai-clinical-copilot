from __future__ import annotations

import hashlib
import math
import os
import re
from pathlib import Path

import httpx
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Document, DocumentChunk


def ensure_upload_dir() -> Path:
    upload_path = Path(settings.upload_dir)
    upload_path.mkdir(parents=True, exist_ok=True)
    return upload_path


def extract_text(file_path: Path, content_type: str) -> str:
    if content_type == "application/pdf" or file_path.suffix.lower() == ".pdf":
        reader = PdfReader(str(file_path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return file_path.read_text(encoding="utf-8", errors="ignore")


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    clean_text = re.sub(r"\s+", " ", text).strip()
    if not clean_text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(clean_text):
        end = min(start + size, len(clean_text))
        chunks.append(clean_text[start:end].strip())
        if end == len(clean_text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def _hash_embedding(text: str, dimensions: int = 128) -> list[float]:
    vector = [0.0] * dimensions
    for token in re.findall(r"[a-zA-Z0-9]+", text.lower()):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        for i in range(0, dimensions, 4):
            bucket = int.from_bytes(digest[(i // 4) % len(digest):(i // 4) % len(digest) + 2], "big") % dimensions
            sign = 1.0 if digest[(i // 4) % len(digest)] % 2 == 0 else -1.0
            vector[bucket] += sign
    magnitude = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [round(v / magnitude, 6) for v in vector]


async def embed_text(text: str) -> list[float]:
    if settings.embedding_provider == "openai" and settings.openai_api_key:
        headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
        payload = {"input": text, "model": settings.embedding_model}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{settings.openai_base_url}/embeddings",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()["data"][0]["embedding"]
    return _hash_embedding(text)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))


def _pick_first(patterns: list[str], text: str) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def extract_entities(text: str) -> dict:
    medications = sorted(set(re.findall(r"(metformin|lisinopril|atorvastatin|albuterol|insulin)", text, flags=re.I)))
    conditions = sorted(set(re.findall(r"(diabetes|hypertension|asthma|hyperlipidemia|anemia)", text, flags=re.I)))
    allergies = sorted(set(re.findall(r"allerg(?:y|ies)\s*:\s*([^.\\n]+)", text, flags=re.I)))
    labs = sorted(set(re.findall(r"(A1C\s*[0-9.]+|BP\s*[0-9/]+|LDL\s*[0-9.]+)", text, flags=re.I)))
    follow_up = sorted(set(re.findall(r"follow[- ]up[^.\\n]*", text, flags=re.I)))
    return {
        "conditions": conditions,
        "medications": medications,
        "allergies": allergies,
        "labs": labs,
        "follow_up": follow_up,
    }


def summarize_text(text: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(sentences[:3])[:500]


def infer_metadata(text: str) -> dict:
    patient_name = _pick_first(
        [r"patient(?: name)?\s*:\s*([A-Z][A-Za-z ,.'-]+)", r"name\s*:\s*([A-Z][A-Za-z ,.'-]+)"],
        text,
    )
    visit_date = _pick_first([r"(?:visit date|date)\s*:\s*([0-9/\-]{8,10})"], text)
    document_type = _pick_first(
        [r"document type\s*:\s*([A-Za-z ]+)", r"(discharge summary|progress note|consult note|lab report)"],
        text,
    )
    return {
        "patient_name": patient_name,
        "visit_date": visit_date,
        "document_type": document_type.title() if document_type else "Clinical Note",
    }


def build_grounded_answer(question: str, matches: list[DocumentChunk]) -> str:
    if not matches:
        return "I could not find grounded evidence in the uploaded records for that question."
    evidence_lines = []
    for chunk in matches[:3]:
        snippet = chunk.content[:220].strip()
        evidence_lines.append(f"- {chunk.document.filename}: {snippet}")
    return (
        f"Question: {question}\n"
        "Grounded answer based on retrieved clinical context:\n"
        + "\n".join(evidence_lines)
        + "\nSynthesis: The retrieved notes indicate the answer should be limited to the cited excerpts above."
    )


async def maybe_generate_llm_answer(question: str, matches: list[DocumentChunk]) -> str:
    if settings.llm_provider == "openai" and settings.openai_api_key:
        context = "\n\n".join(
            f"Source {idx + 1} ({chunk.document.filename}): {chunk.content}" for idx, chunk in enumerate(matches[:5])
        )
        headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
        payload = {
            "model": settings.llm_model,
            "messages": [
                {
                    "role": "system",
                    "content": "You answer only with grounded medical record evidence and mention uncertainty when evidence is missing.",
                },
                {
                    "role": "user",
                    "content": f"Question: {question}\n\nContext:\n{context}",
                },
            ],
        }
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                f"{settings.openai_base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
    return build_grounded_answer(question, matches)


async def ingest_document(
    db: Session,
    filename: str,
    content_type: str,
    raw_bytes: bytes,
) -> Document:
    upload_dir = ensure_upload_dir()
    safe_name = f"{hashlib.md5(raw_bytes).hexdigest()}-{os.path.basename(filename)}"
    file_path = upload_dir / safe_name
    file_path.write_bytes(raw_bytes)

    text = extract_text(file_path, content_type)
    metadata = infer_metadata(text)
    entities = extract_entities(text)
    summary = summarize_text(text)

    document = Document(
        filename=filename,
        content_type=content_type or "text/plain",
        patient_name=metadata["patient_name"],
        document_type=metadata["document_type"],
        visit_date=metadata["visit_date"],
        summary=summary,
        extracted_entities=entities,
        source_path=str(file_path),
    )
    db.add(document)
    db.flush()

    for index, chunk in enumerate(chunk_text(text, settings.chunk_size, settings.chunk_overlap)):
        embedding = await embed_text(chunk)
        db.add(
            DocumentChunk(
                document_id=document.id,
                chunk_index=index,
                content=chunk,
                embedding=embedding,
                token_estimate=max(1, len(chunk.split())),
                relevance_hint=summary[:120] if summary else None,
            )
        )

    db.commit()
    db.refresh(document)
    return document


async def retrieve_chunks(db: Session, query: str, top_k: int) -> list[tuple[DocumentChunk, float]]:
    query_embedding = await embed_text(query)
    chunks = db.scalars(select(DocumentChunk).order_by(DocumentChunk.id)).all()
    scored = [(chunk, cosine_similarity(query_embedding, chunk.embedding)) for chunk in chunks]
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:top_k]

