from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

BATCH_MANIFEST_SCHEMA_VERSION_V1 = "batch_manifest.v1"


class ImageGenerationStats(BaseModel):
    requested: int = Field(0, ge=0)
    succeeded: int = Field(0, ge=0)
    failed: int = Field(0, ge=0)
    image_provider: str | None = None
    image_model: str | None = None

    @field_validator("image_provider", "image_model")
    @classmethod
    def _validate_image_metadata(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("image metadata values must not be blank")
        return value


class ImageTrace(BaseModel):
    slide_id: str = Field(..., min_length=1)
    element_index: int = Field(..., ge=0)
    image_prompt: str = Field(..., min_length=1)
    image_model: str = Field(..., min_length=1)
    image_seed: int | None = None
    image_path: str = Field(..., min_length=1)

    @field_validator("image_prompt", "image_model", "image_path")
    @classmethod
    def _validate_non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("image trace fields must not be blank")
        return value


class BatchDocumentManifest(BaseModel):
    doc_id: str = Field(..., min_length=1)
    input_file: str = Field(..., min_length=1)
    sha256: str = Field(..., pattern=r"^[a-f0-9]{64}$")
    status: Literal["pass", "fail", "unsupported"]
    run_dir: str = Field(..., min_length=1)
    output_pptx: str | None = None
    run_manifest_path: str | None = None
    qa_preflight_path: str | None = None
    qa_postrender_path: str | None = None
    failure_reason: str | None = None
    image_generation: ImageGenerationStats = Field(
        default_factory=lambda: ImageGenerationStats(
            requested=0,
            succeeded=0,
            failed=0,
        )
    )
    image_traces: list[ImageTrace] = Field(default_factory=list)

    @field_validator(
        "output_pptx",
        "run_manifest_path",
        "qa_preflight_path",
        "qa_postrender_path",
        "failure_reason",
    )
    @classmethod
    def _validate_optional_non_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("optional string values must not be blank")
        return value


class BatchRuntimeSettings(BaseModel):
    model_profile: Literal["local", "cloud"] = "local"
    text_provider: str | None = None
    text_model: str | None = None
    image_provider: str | None = None
    image_model: str | None = None
    language: str = Field("ko-KR", min_length=1)
    generation_settings_hash: str | None = None

    @field_validator(
        "text_provider",
        "text_model",
        "image_provider",
        "image_model",
        "generation_settings_hash",
    )
    @classmethod
    def _validate_optional_model_settings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("runtime model settings must not be blank")
        return value


class BatchCounts(BaseModel):
    total: int = Field(..., ge=0)
    passed: int = Field(..., ge=0)
    failed: int = Field(..., ge=0)
    unsupported: int = Field(..., ge=0)


class BatchManifest(BaseModel):
    schema_version: Literal["batch_manifest.v1"]
    batch_id: str = Field(..., min_length=1)
    status: Literal["pass", "partial_fail", "fail"]
    input_dir: str = Field(..., min_length=1)
    output_dir: str = Field(..., min_length=1)
    artifacts_root: str = Field(..., min_length=1)
    runtime: BatchRuntimeSettings = Field(
        default_factory=lambda: BatchRuntimeSettings(language="ko-KR")
    )
    counts: BatchCounts
    documents: list[BatchDocumentManifest] = Field(..., min_length=1)


__all__ = ["BATCH_MANIFEST_SCHEMA_VERSION_V1", "BatchManifest"]
