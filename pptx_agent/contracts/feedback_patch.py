from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

FEEDBACK_PATCH_SCHEMA_VERSION_V1 = "feedback_patch.v1"


class SlidePatch(BaseModel):
    slide_id: str = Field(..., min_length=1)
    operation: Literal[
        "replace_title",
        "replace_body",
        "append_body_bullet",
        "set_layout_hint",
        "replace_image_prompt",
    ]
    path: str = Field(..., min_length=1)
    value: object
    rationale: str = Field(..., min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)

    @field_validator("path", "rationale")
    @classmethod
    def _validate_non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be blank")
        return value

    @field_validator("evidence_ids")
    @classmethod
    def _validate_evidence_ids(cls, value: list[str]) -> list[str]:
        if any(not evidence_id.strip() for evidence_id in value):
            raise ValueError("evidence_ids must not contain blank values")
        return value


class FeedbackPatch(BaseModel):
    schema_version: Literal["feedback_patch.v1"]
    run_id: str = Field(..., min_length=1)
    doc_id: str = Field(..., min_length=1)
    language_override: str | None = None
    summary: str = Field(..., min_length=1)
    patches: list[SlidePatch] = Field(..., min_length=1)

    @field_validator("summary")
    @classmethod
    def _validate_summary(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("summary must not be blank")
        return value

    @field_validator("language_override")
    @classmethod
    def _validate_language_override(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("language_override must not be blank")
        return value


__all__ = ["FEEDBACK_PATCH_SCHEMA_VERSION_V1", "FeedbackPatch"]
