from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator

DECK_OUTLINE_SCHEMA_VERSION_V1 = "deck_outline.v1"
REQUIRED_SECTION_NAMES = [
    "Problem",
    "Scope",
    "Approach",
    "Delivery Plan",
    "Timeline",
    "Pricing Assumptions",
    "Risks",
    "Differentiators",
    "Next Steps",
]
NUMERIC_FACT_PATTERN = re.compile(r"\d+(?:[.,]\d+)?(?:%|주|개월|년|일|원|억|만|명|건)?")


class OutlineVisualSpec(BaseModel):
    kind: Literal["none", "image", "table"] = "none"
    image_prompt: str | None = None
    image_model: str | None = None
    image_seed: int | None = None

    @model_validator(mode="after")
    def _validate_image_requirements(self) -> "OutlineVisualSpec":
        if self.kind != "image":
            return self
        if self.image_prompt is None or not self.image_prompt.strip():
            raise ValueError("image_prompt is required when kind='image'")
        if self.image_model is None or not self.image_model.strip():
            raise ValueError("image_model is required when kind='image'")
        return self


class OutlineSlide(BaseModel):
    slide_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    objective: str = Field(..., min_length=1)
    evidence_ids: list[str] = Field(..., min_length=1)
    body_bullets: list[str] = Field(default_factory=list)
    visual: OutlineVisualSpec = Field(default_factory=lambda: OutlineVisualSpec())

    @field_validator("title", "objective")
    @classmethod
    def _validate_non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be blank")
        return value

    @field_validator("evidence_ids", "body_bullets")
    @classmethod
    def _validate_string_list(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("list values must not be blank")
        return value


class OutlineSection(BaseModel):
    section_id: str = Field(..., min_length=1)
    section_name: str = Field(..., min_length=1)
    intent: str = Field(..., min_length=1)
    summary: str = Field(..., min_length=1)
    slides: list[OutlineSlide] = Field(..., min_length=1)

    @field_validator("section_name", "intent", "summary")
    @classmethod
    def _validate_non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be blank")
        return value

    @model_validator(mode="after")
    def _validate_uncited_numeric_summary(self) -> "OutlineSection":
        if NUMERIC_FACT_PATTERN.search(self.summary):
            raise ValueError(
                "summary must not include numeric facts; move numeric claims to slide-level evidence-backed fields"
            )
        return self


class OutlineMetadata(BaseModel):
    model_profile: Literal["local", "cloud"] = "local"
    language: str = Field("ko-KR", min_length=1)
    image_generation_required: bool = True


class DeckOutline(BaseModel):
    schema_version: Literal["deck_outline.v1"]
    deck_id: str = Field(..., min_length=1)
    source_document_id: str = Field(..., min_length=1)
    language: str = Field("ko-KR", min_length=1)
    target_slide_count: int = Field(..., ge=8, le=18)
    sections: list[OutlineSection] = Field(..., min_length=1)
    metadata: OutlineMetadata = Field(
        default_factory=lambda: OutlineMetadata(language="ko-KR")
    )

    @field_validator("language")
    @classmethod
    def _validate_language(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("language must not be blank")
        return value

    @field_validator("sections")
    @classmethod
    def _validate_sections(
        cls, value: list[OutlineSection], info: ValidationInfo
    ) -> list[OutlineSection]:
        observed = {section.section_name for section in value}
        missing = [name for name in REQUIRED_SECTION_NAMES if name not in observed]
        if missing:
            missing_display = ", ".join(missing)
            raise ValueError(f"sections missing required names: {missing_display}")

        section_names = [section.section_name for section in value]
        if len(set(section_names)) != len(section_names):
            raise ValueError("section_name values must be unique")

        slide_total = sum(len(section.slides) for section in value)
        target_slide_count = info.data.get("target_slide_count")
        if isinstance(target_slide_count, int) and slide_total != target_slide_count:
            raise ValueError(
                "target_slide_count must match the total number of section slides"
            )
        return value


__all__ = [
    "DECK_OUTLINE_SCHEMA_VERSION_V1",
    "DeckOutline",
    "REQUIRED_SECTION_NAMES",
]
