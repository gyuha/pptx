from __future__ import annotations

# pyright: reportAttributeAccessIssue=false, reportMissingTypeStubs=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUntypedBaseClass=false

import hashlib
import json
from collections import Counter
from typing import Literal, cast

from pydantic import BaseModel, Field

NORMALIZE_SCHEMA_VERSION = "normalize.v1"
SUPPORTED_BLOCK_KINDS = {"text", "table"}


class ExtractConfidenceMeta(BaseModel):
    engine: str = Field(..., min_length=1)
    signals: list[str] = Field(default_factory=list)


class ExtractBlock(BaseModel):
    block_id: str = Field(..., min_length=1)
    kind: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    bbox: list[float] = Field(..., min_length=4, max_length=4)
    confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_meta: ExtractConfidenceMeta


class ExtractPageSize(BaseModel):
    width: float = Field(..., gt=0)
    height: float = Field(..., gt=0)


class ExtractPage(BaseModel):
    page_number: int = Field(..., ge=1)
    size: ExtractPageSize
    blocks: list[ExtractBlock] = Field(default_factory=list)


class ExtractInputMeta(BaseModel):
    file: str = Field(..., min_length=1)
    page_count: int = Field(..., ge=0)
    source_document_id: str | None = Field(default=None, min_length=1)


class ExtractRunMeta(BaseModel):
    primary_engine: str = Field(..., min_length=1)
    fallback_engine: str = Field(..., min_length=1)
    fallback_used: bool
    confidence_policy: str = Field(..., min_length=1)


class ExtractPayload(BaseModel):
    schema_version: Literal["extract.v1"]
    input: ExtractInputMeta
    status: Literal["ok", "unsupported"]
    reason_code: str | None = None
    reason: str | None = None
    metadata: ExtractRunMeta
    pages: list[ExtractPage] = Field(default_factory=list)


class UnsupportedItem(BaseModel):
    scope: Literal["document", "page", "block"]
    source_page: int | None = None
    source_block_id: str | None = None
    class_name: str = Field(..., min_length=1)
    reason_code: str = Field(..., min_length=1)
    details: dict[str, object] = Field(default_factory=dict)


class UnsupportedReport(BaseModel):
    has_unsupported: bool
    counts_by_reason: dict[str, int]
    items: list[UnsupportedItem]


class NormalizedElement(BaseModel):
    element_id: str = Field(..., min_length=1)
    kind: Literal["text", "table"]
    text: str = Field(..., min_length=1)
    source_document_id: str = Field(..., min_length=1)
    source_page: int = Field(..., ge=1)
    source_block_id: str = Field(..., min_length=1)
    source_bbox: list[float] = Field(..., min_length=4, max_length=4)
    evidence: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_meta: ExtractConfidenceMeta
    requirement_tags: list[str] = Field(default_factory=list)


class NormalizedPage(BaseModel):
    page_number: int = Field(..., ge=1)
    elements: list[NormalizedElement] = Field(default_factory=list)


class NormalizedPayload(BaseModel):
    schema_version: Literal["normalize.v1"]
    source_schema_version: Literal["extract.v1"]
    deck_id: str = Field(..., min_length=1)
    source_document_id: str = Field(..., min_length=1)
    input: ExtractInputMeta
    status: Literal["ok", "unsupported"]
    metadata: dict[str, object] = Field(default_factory=dict)
    pages: list[NormalizedPage] = Field(default_factory=list)
    unsupported_report: UnsupportedReport
    provenance_coverage: float = Field(..., ge=0.0, le=1.0)


def _stable_hash(payload: object) -> str:
    serialized = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _deck_id(extract_payload: ExtractPayload) -> str:
    digest = _stable_hash(
        {
            "file": extract_payload.input.file,
            "page_count": extract_payload.input.page_count,
            "schema_version": extract_payload.schema_version,
        }
    )
    return f"deck_{digest[:12]}"


def _source_document_id(extract_payload: ExtractPayload) -> str:
    if extract_payload.input.source_document_id:
        return extract_payload.input.source_document_id
    digest = _stable_hash(
        {
            "source_file": extract_payload.input.file,
            "page_count": extract_payload.input.page_count,
            "schema_version": extract_payload.schema_version,
        }
    )
    return f"doc_{digest[:16]}"


def _element_id(
    *,
    source_file: str,
    page_number: int,
    block_id: str,
    kind: str,
    text: str,
    bbox: list[float],
) -> str:
    digest = _stable_hash(
        {
            "source_file": source_file,
            "page_number": page_number,
            "block_id": block_id,
            "kind": kind,
            "text": text,
            "bbox": bbox,
        }
    )
    return f"el_{digest[:16]}"


REQUIREMENT_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("mandatory_requirement", ("shall", "must", "required", "requirement")),
    ("compliance", ("compliance", "policy", "regulation", "iso", "soc 2")),
    ("security", ("security", "encrypt", "access control", "vulnerability")),
    ("timeline", ("timeline", "milestone", "deadline", "due date", "schedule")),
    ("budget", ("budget", "cost", "price", "pricing", "financial")),
    ("deliverable", ("deliverable", "deliverables", "output", "artifact")),
    ("service_level", ("sla", "uptime", "availability", "latency", "response time")),
)


def _classify_requirement_tags(*, kind: str, text: str) -> list[str]:
    normalized = text.lower()
    tags: list[str] = []
    if kind == "table":
        tags.append("tabular_data")
    for tag, keywords in REQUIREMENT_RULES:
        if any(keyword in normalized for keyword in keywords):
            tags.append(tag)
    if any(token in normalized for token in ("should", "recommended", "prefer")):
        tags.append("advisory_requirement")
    seen: set[str] = set()
    deduped: list[str] = []
    for tag in tags:
        if tag in seen:
            continue
        seen.add(tag)
        deduped.append(tag)
    return deduped


def _normalize_extract_model(extract_payload: ExtractPayload) -> NormalizedPayload:

    unsupported_items: list[UnsupportedItem] = []
    normalized_pages: list[NormalizedPage] = []
    source_document_id = _source_document_id(extract_payload)

    if extract_payload.input.page_count != len(extract_payload.pages):
        unsupported_items.append(
            UnsupportedItem(
                scope="document",
                class_name="extract_page_count_mismatch",
                reason_code="page_count_mismatch",
                details={
                    "input_page_count": extract_payload.input.page_count,
                    "actual_pages": len(extract_payload.pages),
                },
            )
        )

    if extract_payload.status == "unsupported":
        unsupported_items.append(
            UnsupportedItem(
                scope="document",
                class_name="unsupported_document",
                reason_code=extract_payload.reason_code or "unsupported_input",
                details={"reason": extract_payload.reason or "unsupported"},
            )
        )

    for page in extract_payload.pages:
        elements: list[NormalizedElement] = []
        for index, block in enumerate(page.blocks):
            if block.kind not in SUPPORTED_BLOCK_KINDS:
                unsupported_items.append(
                    UnsupportedItem(
                        scope="block",
                        source_page=page.page_number,
                        source_block_id=block.block_id,
                        class_name=f"extract_block_kind:{block.kind}",
                        reason_code="unsupported_block_kind",
                        details={
                            "supported_kinds": sorted(SUPPORTED_BLOCK_KINDS),
                            "block_index": index,
                        },
                    )
                )
                continue

            evidence = (
                f"extract.pages[{page.page_number - 1}].blocks[{index}]"
                f"#{block.block_id}"
            )
            element_id = _element_id(
                source_file=extract_payload.input.file,
                page_number=page.page_number,
                block_id=block.block_id,
                kind=block.kind,
                text=block.text,
                bbox=block.bbox,
            )
            elements.append(
                NormalizedElement(
                    element_id=element_id,
                    kind=cast(Literal["text", "table"], block.kind),
                    text=block.text,
                    source_document_id=source_document_id,
                    source_page=page.page_number,
                    source_block_id=block.block_id,
                    source_bbox=block.bbox,
                    evidence=evidence,
                    confidence=block.confidence,
                    confidence_meta=block.confidence_meta,
                    requirement_tags=_classify_requirement_tags(
                        kind=block.kind,
                        text=block.text,
                    ),
                )
            )

        normalized_pages.append(
            NormalizedPage(page_number=page.page_number, elements=elements)
        )

    total_elements = sum(len(page.elements) for page in normalized_pages)
    elements_with_provenance = sum(
        1
        for page in normalized_pages
        for element in page.elements
        if element.source_page >= 1
        and bool(element.evidence.strip())
        and 0.0 <= element.confidence <= 1.0
    )
    provenance_coverage = (
        1.0
        if total_elements == 0
        else round(elements_with_provenance / total_elements, 6)
    )

    reason_counts = Counter(item.reason_code for item in unsupported_items)
    unsupported_report = UnsupportedReport(
        has_unsupported=bool(unsupported_items),
        counts_by_reason=dict(sorted(reason_counts.items())),
        items=unsupported_items,
    )

    normalized_status: Literal["ok", "unsupported"] = (
        "unsupported" if extract_payload.status == "unsupported" else "ok"
    )

    return NormalizedPayload(
        schema_version=NORMALIZE_SCHEMA_VERSION,
        source_schema_version=extract_payload.schema_version,
        deck_id=_deck_id(extract_payload),
        source_document_id=source_document_id,
        input=extract_payload.input,
        status=normalized_status,
        metadata={
            "extract_status": extract_payload.status,
            "extract_reason_code": extract_payload.reason_code,
            "extract_reason": extract_payload.reason,
            "engines": {
                "primary": extract_payload.metadata.primary_engine,
                "fallback": extract_payload.metadata.fallback_engine,
                "fallback_used": extract_payload.metadata.fallback_used,
            },
            "confidence_policy": extract_payload.metadata.confidence_policy,
        },
        pages=normalized_pages,
        unsupported_report=unsupported_report,
        provenance_coverage=provenance_coverage,
    )


def normalize_extract_payload(payload: dict[str, object]) -> NormalizedPayload:
    return _normalize_extract_model(ExtractPayload.model_validate(payload))


def normalize_extract_payload_json(payload_json: str) -> NormalizedPayload:
    return _normalize_extract_model(ExtractPayload.model_validate_json(payload_json))


__all__ = [
    "NORMALIZE_SCHEMA_VERSION",
    "NormalizedPayload",
    "normalize_extract_payload",
    "normalize_extract_payload_json",
]
