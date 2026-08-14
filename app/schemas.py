from typing import Literal
from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


class Source(BaseModel):
    kind: Literal["superhero_api", "dataset"]
    # superhero fields
    name: str | None = None
    url: str | None = None
    # dataset fields
    doc_id: str | None = None
    chunk_id: int | None = None
    title: str | None = None


class AskResponse(BaseModel):
    answer: str
    route: Literal["superhero", "dataset", "both", "none"]
    sources: list[Source]
