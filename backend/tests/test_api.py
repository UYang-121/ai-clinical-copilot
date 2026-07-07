from pathlib import Path

from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Document, DocumentChunk


client = TestClient(app)
sample_file = Path(__file__).resolve().parents[2] / "sample_data" / "sample_clinical_note.txt"


def reset_db() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        session.query(DocumentChunk).delete()
        session.query(Document).delete()
        session.commit()


def test_healthcheck() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ingestion_retrieval_and_qa_flow() -> None:
    reset_db()

    with sample_file.open("rb") as handle:
        upload_response = client.post(
            "/documents/upload",
            files={"file": ("sample_clinical_note.txt", handle, "text/plain")},
        )

    assert upload_response.status_code == 200
    payload = upload_response.json()
    assert payload["patient_name"] == "Maria Thompson"
    assert "metformin" in [item.lower() for item in payload["extracted_entities"]["medications"]]

    retrieval_response = client.post("/retrieve", json={"query": "diabetes medication", "top_k": 3})
    assert retrieval_response.status_code == 200
    retrieval_payload = retrieval_response.json()
    assert len(retrieval_payload) >= 1
    assert retrieval_payload[0]["filename"] == "sample_clinical_note.txt"

    ask_response = client.post("/ask", json={"question": "What follow-up plan is documented?", "top_k": 3})
    assert ask_response.status_code == 200
    answer_payload = ask_response.json()
    assert "follow-up" in answer_payload["answer"].lower()
    assert len(answer_payload["citations"]) >= 1


def test_empty_retrieval_before_uploads() -> None:
    reset_db()
    response = client.post("/retrieve", json={"query": "anything", "top_k": 3})
    assert response.status_code == 200
    assert response.json() == []


def test_unknown_question_returns_grounded_fallback() -> None:
    reset_db()
    with sample_file.open("rb") as handle:
        client.post(
            "/documents/upload",
            files={"file": ("sample_clinical_note.txt", handle, "text/plain")},
        )

    response = client.post("/ask", json={"question": "Does the chart mention a surgery?", "top_k": 3})
    assert response.status_code == 200
    payload = response.json()
    assert "answer" in payload
    assert len(payload["citations"]) >= 1
