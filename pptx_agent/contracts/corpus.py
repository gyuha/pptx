from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, ValidationInfo, field_validator

CORPUS_SCHEMA_VERSION_V1 = "corpus.v1"


class CorpusSourceSpan(BaseModel):
    page_number: int = Field(..., ge=1)
    block_id: str = Field(..., min_length=1)
    char_start: int = Field(..., ge=0)
    char_end: int = Field(..., ge=0)

    @field_validator("char_end")
    @classmethod
    def _validate_char_end(cls, value: int, info: ValidationInfo) -> int:
        char_start = info.data.get("char_start")
        if isinstance(char_start, int) and value < char_start:
            raise ValueError("char_end must be greater than or equal to char_start")
        return value


class CorpusChunk(BaseModel):
    chunk_id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    source_document_id: str = Field(..., min_length=1)
    source_path: str = Field(..., min_length=1)
    source_span: CorpusSourceSpan
    requirement_tags: list[str] = Field(default_factory=list)

    @field_validator("text")
    @classmethod
    def _validate_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be blank")
        return value

    @field_validator("requirement_tags")
    @classmethod
    def _validate_requirement_tags(cls, value: list[str]) -> list[str]:
        if any(not tag.strip() for tag in value):
            raise ValueError("requirement_tags must not contain blank values")
        return value


class CorpusDocument(BaseModel):
    doc_id: str = Field(..., min_length=1)
    input_path: str = Field(..., min_length=1)
    sha256: str = Field(..., pattern=r"^[a-f0-9]{64}$")
    language: str = Field(..., min_length=1)
    page_count: int = Field(..., ge=1)
    chunks: list[CorpusChunk] = Field(default_factory=list)

    @field_validator("language")
    @classmethod
    def _validate_language(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("language must not be blank")
        return value


class CorpusMetadata(BaseModel):
    model_profile: Literal["local", "cloud"] = "local"
    default_output_language: str = Field("ko-KR", min_length=1)
    image_generation_mode: Literal["llm", "disabled"] = "llm"


class Corpus(BaseModel):
    schema_version: Literal["corpus.v1"]
    batch_id: str = Field(..., min_length=1)
    language: str = Field("ko-KR", min_length=1)
    documents: list[CorpusDocument] = Field(..., min_length=1)
    metadata: CorpusMetadata = Field(
        default_factory=lambda: CorpusMetadata(default_output_language="ko-KR")
    )

    @field_validator("language")
    @classmethod
    def _validate_language(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("language must not be blank")
        return value


__all__ = ["CORPUS_SCHEMA_VERSION_V1", "Corpus"]
