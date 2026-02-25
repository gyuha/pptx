from __future__ import annotations

# pyright: reportAttributeAccessIssue=false, reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUntypedBaseClass=false, reportUntypedFunctionDecorator=false

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

SCHEMA_VERSION_V1 = "slidespec.v1"


class ProvenanceMixin(BaseModel):
    source_page: int = Field(..., ge=1)
    evidence: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)

    @field_validator("evidence")
    @classmethod
    def _validate_evidence(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("evidence must not be blank")
        return value


class SlideElement(ProvenanceMixin):
    kind: Literal["title", "body", "image", "table"]
    text: str | None = None
    image_prompt: str | None = None
    image_model: str | None = None
    image_seed: int | None = None

    @field_validator("image_prompt", "image_model")
    @classmethod
    def _validate_optional_non_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("optional image fields must not be blank")
        return value


class Slide(BaseModel):
    slide_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    layout_hint: str | None = None
    elements: list[SlideElement] = Field(default_factory=list)

    @field_validator("layout_hint")
    @classmethod
    def _validate_layout_hint(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("layout_hint must not be blank")
        return value


class SlideSpec(BaseModel):
    schema_version: Literal["slidespec.v1"]
    deck_id: str = Field(..., min_length=1)
    slides: list[Slide] = Field(..., min_length=1)


def validate_slidespec_file(input_path: Path) -> SlideSpec:
    payload = input_path.read_text(encoding="utf-8")
    return SlideSpec.model_validate_json(payload)


__all__ = [
    "SCHEMA_VERSION_V1",
    "Slide",
    "SlideElement",
    "SlideSpec",
    "validate_slidespec_file",
]
