from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ExtractedEntities(BaseModel):
    conditions: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    labs: list[str] = Field(default_factory=list)
    follow_up: list[str] = Field(default_factory=list)


class DocumentResponse(BaseModel):
    id: int
    filename: str
    content_type: str
    patient_name: str | None
    document_type: str | None
    visit_date: str | None
    summary: str | None
    extracted_entities: dict
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RetrievalRequest(BaseModel):
    query: str
    top_k: int = 5


class RetrievalMatch(BaseModel):
    document_id: int
    chunk_id: int
    filename: str
    score: float
    snippet: str
    relevance_hint: str | None


class AskRequest(BaseModel):
    question: str
    top_k: int = 5


class AnswerCitation(BaseModel):
    document_id: int
    chunk_id: int
    filename: str
    snippet: str
    score: float


class AskResponse(BaseModel):
    answer: str
    citations: list[AnswerCitation]
