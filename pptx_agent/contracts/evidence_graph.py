from __future__ import annotations

# pyright: reportAny=false, reportUnknownVariableType=false

from typing import Literal

from pydantic import BaseModel, Field, ValidationInfo, field_validator

EVIDENCE_GRAPH_SCHEMA_VERSION_V1 = "evidence_graph.v1"


class EvidenceProvenance(BaseModel):
    source_document_id: str = Field(..., min_length=1)
    source_page: int = Field(..., ge=1)
    source_block_id: str = Field(..., min_length=1)
    source_span: "EvidenceSourceSpan"
    evidence: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)

    @field_validator("evidence")
    @classmethod
    def _validate_evidence(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("evidence must not be blank")
        return value


class EvidenceSourceSpan(BaseModel):
    source_bbox: list[float] = Field(..., min_length=4, max_length=4)
    char_start: int = Field(..., ge=0)
    char_end: int = Field(..., ge=0)

    @field_validator("char_end")
    @classmethod
    def _validate_char_end(cls, value: int, info: ValidationInfo) -> int:
        char_start = info.data.get("char_start")
        if isinstance(char_start, int) and value < char_start:
            raise ValueError("char_end must be greater than or equal to char_start")
        return value


class EvidenceNode(BaseModel):
    evidence_id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    requirement_tags: list[str] = Field(default_factory=list)
    provenance: EvidenceProvenance

    @field_validator("text")
    @classmethod
    def _validate_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be blank")
        return value


class ClaimNode(BaseModel):
    claim_id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)

    @field_validator("text")
    @classmethod
    def _validate_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be blank")
        return value


class ClaimEvidenceLink(BaseModel):
    claim_id: str = Field(..., min_length=1)
    evidence_id: str = Field(..., min_length=1)
    rationale: str = Field(..., min_length=1)

    @field_validator("rationale")
    @classmethod
    def _validate_rationale(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("rationale must not be blank")
        return value


class EvidenceGraph(BaseModel):
    schema_version: Literal["evidence_graph.v1"]
    deck_id: str = Field(..., min_length=1)
    language: str = Field("ko-KR", min_length=1)
    evidence_nodes: list[EvidenceNode] = Field(..., min_length=1)
    claims: list[ClaimNode] = Field(default_factory=list)
    links: list[ClaimEvidenceLink] = Field(default_factory=list)

    @field_validator("language")
    @classmethod
    def _validate_language(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("language must not be blank")
        return value

    @field_validator("links")
    @classmethod
    def _validate_link_integrity(
        cls, value: list[ClaimEvidenceLink], info: ValidationInfo
    ) -> list[ClaimEvidenceLink]:
        claim_ids: set[str] = set()
        claims_obj: object = info.data.get("claims", [])
        if isinstance(claims_obj, list):
            for claim_obj in claims_obj:
                if isinstance(claim_obj, ClaimNode):
                    claim_ids.add(claim_obj.claim_id)

        evidence_ids: set[str] = set()
        evidence_nodes_obj: object = info.data.get("evidence_nodes", [])
        if isinstance(evidence_nodes_obj, list):
            for evidence_node_obj in evidence_nodes_obj:
                if isinstance(evidence_node_obj, EvidenceNode):
                    evidence_ids.add(evidence_node_obj.evidence_id)

        for link in value:
            if link.claim_id not in claim_ids:
                raise ValueError(f"links include unknown claim_id '{link.claim_id}'")
            if link.evidence_id not in evidence_ids:
                raise ValueError(
                    f"links include unknown evidence_id '{link.evidence_id}'"
                )
        return value


__all__ = ["EVIDENCE_GRAPH_SCHEMA_VERSION_V1", "EvidenceGraph"]
