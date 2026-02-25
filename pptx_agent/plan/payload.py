from __future__ import annotations

# pyright: reportAttributeAccessIssue=false, reportMissingImports=false, reportMissingTypeStubs=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownVariableType=false

import hashlib
import json
import re
from typing import Literal

from ..contracts import (
    DECK_OUTLINE_SCHEMA_VERSION_V1,
    EVIDENCE_GRAPH_SCHEMA_VERSION_V1,
    SCHEMA_VERSION_V1,
    DeckOutline,
    EvidenceGraph,
    OutlineSection,
    OutlineSlide,
    OutlineVisualSpec,
    REQUIRED_SECTION_NAMES,
    Slide,
    SlideElement,
    SlideSpec,
)
from ..normalize.payload import NormalizedElement, NormalizedPayload

LOW_CONFIDENCE_THRESHOLD = 0.75
LOW_CONFIDENCE_PREFIX = "[LOW_CONFIDENCE]"
NUMERIC_FACT_PATTERN = re.compile(r"\d+(?:[.,]\d+)?(?:%|주|개월|년|일|원|억|만|명|건)?")

SECTION_INTENTS: dict[str, str] = {
    "Problem": "고객 과제와 사업 필요성을 명확히 정의합니다.",
    "Scope": "수행 범위와 제외 범위를 구조적으로 정리합니다.",
    "Approach": "실행 가능한 방법론과 추진 전략을 제안합니다.",
    "Delivery Plan": "단계별 산출물과 납품 체계를 제시합니다.",
    "Timeline": "마일스톤 중심 일정 계획을 제시합니다.",
    "Pricing Assumptions": "가격 산정의 전제와 가정을 명시합니다.",
    "Risks": "핵심 리스크와 대응 방향을 투명하게 제시합니다.",
    "Differentiators": "경쟁 대비 차별화 포인트를 강조합니다.",
    "Next Steps": "의사결정 이후 후속 실행 단계를 안내합니다.",
}

SECTION_SUMMARIES: dict[str, str] = {
    "Problem": "요구사항 근거를 기반으로 문제 정의를 정렬합니다.",
    "Scope": "필수 요구를 중심으로 수행 범위를 분명히 설정합니다.",
    "Approach": "검증 가능한 실행 접근을 단계적으로 제안합니다.",
    "Delivery Plan": "산출물 책임과 검수 흐름을 계획합니다.",
    "Timeline": "주요 마일스톤 중심 일정을 계획합니다.",
    "Pricing Assumptions": "가격 가정과 비용 추정의 기준을 문서화합니다.",
    "Risks": "예상 리스크와 완화 전략을 선제적으로 준비합니다.",
    "Differentiators": "제안 경쟁력을 구성하는 핵심 요소를 명시합니다.",
    "Next Steps": "제안 승인 이후 실행 착수 절차를 정리합니다.",
}

SECTION_TAG_PRIORITIES: dict[str, tuple[str, ...]] = {
    "Problem": ("mandatory_requirement", "compliance", "security"),
    "Scope": ("mandatory_requirement", "deliverable", "service_level"),
    "Approach": ("deliverable", "security", "compliance"),
    "Delivery Plan": ("deliverable", "service_level", "mandatory_requirement"),
    "Timeline": ("timeline", "mandatory_requirement"),
    "Pricing Assumptions": ("budget", "mandatory_requirement"),
    "Risks": ("security", "compliance", "timeline"),
    "Differentiators": ("deliverable", "service_level", "advisory_requirement"),
    "Next Steps": ("timeline", "deliverable", "advisory_requirement"),
}


def _stable_hash(payload: object) -> str:
    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _evidence_id_for_element(element: NormalizedElement) -> str:
    digest = _stable_hash(
        {
            "element_id": element.element_id,
            "source_document_id": element.source_document_id,
            "source_page": element.source_page,
            "source_block_id": element.source_block_id,
            "source_bbox": element.source_bbox,
            "text": element.text,
            "evidence": element.evidence,
        }
    )
    return f"ev_{digest[:16]}"


def _flatten_elements(normalized: NormalizedPayload) -> list[NormalizedElement]:
    flattened: list[NormalizedElement] = []
    for page in sorted(normalized.pages, key=lambda candidate: candidate.page_number):
        sorted_page_elements = sorted(
            page.elements, key=lambda candidate: candidate.element_id
        )
        flattened.extend(sorted_page_elements)
    return flattened


def _evidence_node_payloads(normalized: NormalizedPayload) -> list[dict[str, object]]:
    node_payloads: list[dict[str, object]] = []
    for element in _flatten_elements(normalized):
        node_payloads.append(
            {
                "evidence_id": _evidence_id_for_element(element),
                "text": element.text,
                "requirement_tags": sorted(set(element.requirement_tags)),
                "provenance": {
                    "source_document_id": element.source_document_id,
                    "source_page": element.source_page,
                    "source_block_id": element.source_block_id,
                    "source_span": {
                        "source_bbox": element.source_bbox,
                        "char_start": 0,
                        "char_end": len(element.text),
                    },
                    "evidence": element.evidence,
                    "confidence": element.confidence,
                },
            }
        )
    return node_payloads


def _extract_claim_reference_map(
    normalized: NormalizedPayload,
) -> list[dict[str, object]] | None:
    claim_reference_map = normalized.metadata.get("claim_reference_map")
    if claim_reference_map is None:
        return None
    if not isinstance(claim_reference_map, list):
        raise ValueError(
            "Unsupported planning input: metadata.claim_reference_map must be a list."
        )
    extracted: list[dict[str, object]] = []
    for index, claim_reference in enumerate(claim_reference_map):
        if not isinstance(claim_reference, dict):
            raise ValueError(
                "Unsupported planning input: "
                + f"metadata.claim_reference_map[{index}] must be an object."
            )
        extracted.append(claim_reference)
    return extracted


def _validate_claim_reference_map(
    *, claim_reference_map: list[dict[str, object]] | None, known_evidence_ids: set[str]
) -> None:
    if claim_reference_map is None:
        return

    for index, claim_reference in enumerate(claim_reference_map):
        claim_id_raw = claim_reference.get("claim_id")
        claim_id = claim_id_raw.strip() if isinstance(claim_id_raw, str) else ""
        if not claim_id:
            raise ValueError(
                "Unsupported planning input: "
                + f"metadata.claim_reference_map[{index}].claim_id must be a non-empty string."
            )

        evidence_ids_raw = claim_reference.get("evidence_ids")
        if not isinstance(evidence_ids_raw, list) or not evidence_ids_raw:
            raise ValueError(
                "Unsupported planning input: "
                + "metadata.claim_reference_map"
                + f"[{index}].evidence_ids must contain at least one evidence ID."
            )

        normalized_evidence_ids: list[str] = []
        for evidence_index, evidence_id_raw in enumerate(evidence_ids_raw):
            if not isinstance(evidence_id_raw, str) or not evidence_id_raw.strip():
                raise ValueError(
                    "Unsupported planning input: "
                    + "metadata.claim_reference_map"
                    + f"[{index}].evidence_ids[{evidence_index}] must be a non-empty string."
                )
            normalized_evidence_ids.append(evidence_id_raw.strip())

        orphan_evidence_ids = sorted(
            evidence_id
            for evidence_id in set(normalized_evidence_ids)
            if evidence_id not in known_evidence_ids
        )
        if orphan_evidence_ids:
            joined = ", ".join(orphan_evidence_ids)
            raise ValueError(
                "Unsupported planning input: orphan evidence reference for "
                + f"claim '{claim_id}': {joined}."
            )


def _numeric_tokens(text: str) -> set[str]:
    return set(NUMERIC_FACT_PATTERN.findall(text))


def _evidence_nodes_by_id(
    normalized: NormalizedPayload,
) -> dict[str, NormalizedElement]:
    return {
        _evidence_id_for_element(element): element
        for element in _flatten_elements(normalized)
    }


def _select_section_evidence(
    *,
    section_name: str,
    evidence_by_id: dict[str, NormalizedElement],
    fallback_order: list[str],
    cursor: int,
) -> tuple[str, int]:
    priorities = SECTION_TAG_PRIORITIES.get(section_name, ())
    ranked_ids: list[str] = []
    seen: set[str] = set()
    for tag in priorities:
        matching = sorted(
            evidence_id
            for evidence_id, element in evidence_by_id.items()
            if tag in element.requirement_tags
        )
        for evidence_id in matching:
            if evidence_id in seen:
                continue
            ranked_ids.append(evidence_id)
            seen.add(evidence_id)

    if not ranked_ids:
        ranked_ids = fallback_order
    if not ranked_ids:
        raise ValueError(
            "Unsupported planning input: normalized payload contains no evidence-bearing elements."
        )

    selected_id = ranked_ids[cursor % len(ranked_ids)]
    return selected_id, cursor + 1


def _outline_claims_with_paths(
    outline: DeckOutline,
) -> list[tuple[str, str, tuple[str, ...]]]:
    claims: list[tuple[str, str, tuple[str, ...]]] = []
    for section in outline.sections:
        claims.append(
            (
                f"section[{section.section_name}].summary",
                section.summary,
                tuple(),
            )
        )
        for slide in section.slides:
            claims.append(
                (
                    f"slide[{slide.slide_id}].title",
                    slide.title,
                    tuple(slide.evidence_ids),
                )
            )
            claims.append(
                (
                    f"slide[{slide.slide_id}].objective",
                    slide.objective,
                    tuple(slide.evidence_ids),
                )
            )
            for bullet_index, bullet in enumerate(slide.body_bullets):
                claims.append(
                    (
                        f"slide[{slide.slide_id}].body_bullets[{bullet_index}]",
                        bullet,
                        tuple(slide.evidence_ids),
                    )
                )
    return claims


def _validate_outline_numeric_citations(
    *, outline: DeckOutline, evidence_by_id: dict[str, NormalizedElement]
) -> None:
    evidence_numeric_tokens: dict[str, set[str]] = {
        evidence_id: _numeric_tokens(element.text)
        for evidence_id, element in evidence_by_id.items()
    }

    for claim_path, claim_text, claim_evidence_ids in _outline_claims_with_paths(
        outline
    ):
        claim_tokens = _numeric_tokens(claim_text)
        if not claim_tokens:
            continue

        if not claim_evidence_ids:
            raise ValueError(
                "Unsupported planning input: uncited numeric fact in outline claim "
                + f"'{claim_path}': {sorted(claim_tokens)}."
            )

        unknown_evidence_ids = sorted(
            evidence_id
            for evidence_id in set(claim_evidence_ids)
            if evidence_id not in evidence_numeric_tokens
        )
        if unknown_evidence_ids:
            raise ValueError(
                "Unsupported planning input: outline claim references unknown evidence IDs "
                + f"for '{claim_path}': {', '.join(unknown_evidence_ids)}."
            )

        unresolved_tokens = sorted(
            token
            for token in claim_tokens
            if not any(
                token in evidence_numeric_tokens[evidence_id]
                for evidence_id in claim_evidence_ids
            )
        )
        if unresolved_tokens:
            raise ValueError(
                "Unsupported planning input: uncited numeric fact(s) "
                + f"{unresolved_tokens} in outline claim '{claim_path}'."
            )


def _outline_slide(
    *,
    slide_id: str,
    title: str,
    objective: str,
    evidence_id: str,
    body_bullets: list[str],
    visual_kind: Literal["none", "image", "table"] = "none",
) -> OutlineSlide:
    if visual_kind == "image":
        visual = OutlineVisualSpec(
            kind="image",
            image_prompt="기업 제안서용 추진 전략 인포그래픽",
            image_model="image-model-v1",
            image_seed=None,
        )
    else:
        visual = OutlineVisualSpec(kind=visual_kind)
    return OutlineSlide(
        slide_id=slide_id,
        title=title,
        objective=objective,
        evidence_ids=[evidence_id],
        body_bullets=body_bullets,
        visual=visual,
    )


def _to_ko_claim(prefix: str, source_text: str) -> str:
    normalized_text = " ".join(source_text.split())
    clipped = normalized_text[:140]
    return f"{prefix}: {clipped}" if clipped else prefix


def build_deck_outline_model(normalized: NormalizedPayload) -> DeckOutline:
    if normalized.status != "ok":
        raise ValueError(
            "Unsupported planning input: normalized.status must be 'ok' "
            + f"(got '{normalized.status}')."
        )

    evidence_by_id = _evidence_nodes_by_id(normalized)
    fallback_order = sorted(evidence_by_id.keys())
    if not fallback_order:
        raise ValueError(
            "Unsupported planning input: normalized payload contains no evidence-bearing elements."
        )

    sections: list[OutlineSection] = []
    cursor = 0
    slide_seq = 1
    for section_index, section_name in enumerate(REQUIRED_SECTION_NAMES, start=1):
        evidence_id, cursor = _select_section_evidence(
            section_name=section_name,
            evidence_by_id=evidence_by_id,
            fallback_order=fallback_order,
            cursor=cursor,
        )
        evidence_element = evidence_by_id[evidence_id]
        base_title = f"{section_name}"
        base_objective = _to_ko_claim(
            prefix="핵심 근거를 바탕으로 실행 포인트를 정리합니다",
            source_text=evidence_element.text,
        )
        base_bullet = _to_ko_claim(
            prefix="근거 요약",
            source_text=evidence_element.text,
        )

        visual_kind: Literal["none", "image", "table"] = "none"
        if section_name == "Approach":
            visual_kind = "image"
        elif section_name in {"Delivery Plan", "Timeline"}:
            visual_kind = "table"

        slides = [
            _outline_slide(
                slide_id=f"slide_{slide_seq:03d}",
                title=base_title,
                objective=base_objective,
                evidence_id=evidence_id,
                body_bullets=[base_bullet],
                visual_kind=visual_kind,
            )
        ]
        slide_seq += 1

        if section_name == "Approach":
            secondary_id, cursor = _select_section_evidence(
                section_name=section_name,
                evidence_by_id=evidence_by_id,
                fallback_order=fallback_order,
                cursor=cursor,
            )
            secondary_element = evidence_by_id[secondary_id]
            slides.append(
                _outline_slide(
                    slide_id=f"slide_{slide_seq:03d}",
                    title="Approach - 실행 단계",
                    objective=_to_ko_claim(
                        prefix="추진 단계별 실행 근거를 제시합니다",
                        source_text=secondary_element.text,
                    ),
                    evidence_id=secondary_id,
                    body_bullets=[
                        _to_ko_claim(
                            prefix="단계 근거",
                            source_text=secondary_element.text,
                        )
                    ],
                    visual_kind="image",
                )
            )
            slide_seq += 1

        sections.append(
            OutlineSection(
                section_id=f"section_{section_index:02d}",
                section_name=section_name,
                intent=SECTION_INTENTS[section_name],
                summary=SECTION_SUMMARIES[section_name],
                slides=slides,
            )
        )

    target_slide_count = sum(len(section.slides) for section in sections)
    outline = DeckOutline.model_validate(
        {
            "schema_version": DECK_OUTLINE_SCHEMA_VERSION_V1,
            "deck_id": normalized.deck_id,
            "source_document_id": normalized.source_document_id,
            "language": "ko-KR",
            "target_slide_count": target_slide_count,
            "sections": [section.model_dump(mode="json") for section in sections],
            "metadata": {
                "model_profile": "local",
                "language": "ko-KR",
                "image_generation_required": True,
            },
        }
    )
    _validate_outline_numeric_citations(outline=outline, evidence_by_id=evidence_by_id)
    return outline


def build_deck_outline_payload(payload: dict[str, object]) -> DeckOutline:
    normalized = NormalizedPayload.model_validate(payload)
    return build_deck_outline_model(normalized)


def build_deck_outline_payload_json(payload_json: str) -> DeckOutline:
    normalized = NormalizedPayload.model_validate_json(payload_json)
    return build_deck_outline_model(normalized)


def outline_to_slidespec_model(
    *, outline: DeckOutline, normalized: NormalizedPayload
) -> SlideSpec:
    evidence_by_id = _evidence_nodes_by_id(normalized)
    _validate_outline_numeric_citations(outline=outline, evidence_by_id=evidence_by_id)

    slides: list[Slide] = []
    for section in outline.sections:
        for outline_slide in section.slides:
            primary_evidence_id = outline_slide.evidence_ids[0]
            primary_element = evidence_by_id.get(primary_evidence_id)
            if primary_element is None:
                raise ValueError(
                    "Unsupported planning input: outline references unknown evidence_id "
                    + f"'{primary_evidence_id}' in slide '{outline_slide.slide_id}'."
                )

            elements: list[SlideElement] = [
                SlideElement(
                    kind="title",
                    text=outline_slide.title,
                    source_page=primary_element.source_page,
                    evidence=primary_element.evidence,
                    confidence=primary_element.confidence,
                ),
                SlideElement(
                    kind="body",
                    text=outline_slide.objective,
                    source_page=primary_element.source_page,
                    evidence=primary_element.evidence,
                    confidence=primary_element.confidence,
                ),
            ]

            for bullet_index, bullet in enumerate(outline_slide.body_bullets):
                evidence_id = outline_slide.evidence_ids[
                    bullet_index % len(outline_slide.evidence_ids)
                ]
                bullet_element = evidence_by_id.get(evidence_id)
                if bullet_element is None:
                    raise ValueError(
                        "Unsupported planning input: outline references unknown evidence_id "
                        + f"'{evidence_id}' in slide '{outline_slide.slide_id}'."
                    )
                elements.append(
                    SlideElement(
                        kind="body",
                        text=bullet,
                        source_page=bullet_element.source_page,
                        evidence=bullet_element.evidence,
                        confidence=bullet_element.confidence,
                    )
                )

            layout_hint: str | None = None
            if outline_slide.visual.kind == "table":
                layout_hint = "title_table_focus"
                elements.append(
                    SlideElement(
                        kind="table",
                        text="근거 표",
                        source_page=primary_element.source_page,
                        evidence=primary_element.evidence,
                        confidence=primary_element.confidence,
                    )
                )
            elif outline_slide.visual.kind == "image":
                layout_hint = "title_body_flow"
                image_text = (
                    outline_slide.visual.image_prompt
                    if outline_slide.visual.image_prompt is not None
                    else "시각화 이미지"
                )
                elements.append(
                    SlideElement(
                        kind="image",
                        text=image_text,
                        image_prompt=outline_slide.visual.image_prompt,
                        image_model=outline_slide.visual.image_model,
                        image_seed=outline_slide.visual.image_seed,
                        source_page=primary_element.source_page,
                        evidence=primary_element.evidence,
                        confidence=primary_element.confidence,
                    )
                )

            slides.append(
                Slide(
                    slide_id=outline_slide.slide_id,
                    title=outline_slide.title,
                    layout_hint=layout_hint,
                    elements=elements,
                )
            )

    if not slides:
        raise ValueError("Unsupported planning input: deck outline contains no slides.")

    return SlideSpec(
        schema_version=SCHEMA_VERSION_V1,
        deck_id=outline.deck_id,
        slides=slides,
    )


def outline_to_slidespec_payload(
    *, outline_payload: dict[str, object], normalized_payload: dict[str, object]
) -> SlideSpec:
    outline = DeckOutline.model_validate(outline_payload)
    normalized = NormalizedPayload.model_validate(normalized_payload)
    return outline_to_slidespec_model(outline=outline, normalized=normalized)


def build_evidence_graph_model(normalized: NormalizedPayload) -> EvidenceGraph:
    if normalized.status != "ok":
        raise ValueError(
            "Unsupported evidence graph input: normalized.status must be 'ok' "
            + f"(got '{normalized.status}')."
        )

    evidence_nodes = _evidence_node_payloads(normalized)
    if not evidence_nodes:
        raise ValueError(
            "Unsupported evidence graph input: normalized payload contains no evidence-bearing elements."
        )

    known_evidence_ids = {
        str(node_payload["evidence_id"])
        for node_payload in evidence_nodes
        if isinstance(node_payload.get("evidence_id"), str)
    }
    claim_reference_map = _extract_claim_reference_map(normalized)
    _validate_claim_reference_map(
        claim_reference_map=claim_reference_map,
        known_evidence_ids=known_evidence_ids,
    )

    claims: list[dict[str, str]] = []
    links: list[dict[str, str]] = []
    if claim_reference_map:
        for claim_reference in claim_reference_map:
            claim_id = str(claim_reference["claim_id"]).strip()
            claim_text_raw = claim_reference.get("text")
            claim_text = (
                claim_text_raw.strip() if isinstance(claim_text_raw, str) else claim_id
            )
            claims.append({"claim_id": claim_id, "text": claim_text})

            rationale_raw = claim_reference.get("rationale")
            rationale = (
                rationale_raw.strip()
                if isinstance(rationale_raw, str) and rationale_raw.strip()
                else "claim_reference_map"
            )
            evidence_ids = claim_reference["evidence_ids"]
            if isinstance(evidence_ids, list):
                for evidence_id_raw in evidence_ids:
                    evidence_id = str(evidence_id_raw).strip()
                    links.append(
                        {
                            "claim_id": claim_id,
                            "evidence_id": evidence_id,
                            "rationale": rationale,
                        }
                    )

    return EvidenceGraph.model_validate(
        {
            "schema_version": EVIDENCE_GRAPH_SCHEMA_VERSION_V1,
            "deck_id": normalized.deck_id,
            "language": "ko-KR",
            "evidence_nodes": evidence_nodes,
            "claims": sorted(claims, key=lambda claim: claim["claim_id"]),
            "links": sorted(
                links,
                key=lambda link: (
                    link["claim_id"],
                    link["evidence_id"],
                    link["rationale"],
                ),
            ),
        }
    )


def build_evidence_graph_payload(payload: dict[str, object]) -> EvidenceGraph:
    normalized = NormalizedPayload.model_validate(payload)
    return build_evidence_graph_model(normalized)


def build_evidence_graph_payload_json(payload_json: str) -> EvidenceGraph:
    normalized = NormalizedPayload.model_validate_json(payload_json)
    return build_evidence_graph_model(normalized)


def plan_normalized_payload(payload: dict[str, object]) -> SlideSpec:
    normalized = NormalizedPayload.model_validate(payload)
    return plan_normalized_model(normalized)


def plan_normalized_payload_json(payload_json: str) -> SlideSpec:
    normalized = NormalizedPayload.model_validate_json(payload_json)
    return plan_normalized_model(normalized)


def plan_normalized_model(normalized: NormalizedPayload) -> SlideSpec:
    known_evidence_ids = {
        str(node_payload["evidence_id"])
        for node_payload in _evidence_node_payloads(normalized)
    }
    claim_reference_map = _extract_claim_reference_map(normalized)
    _validate_claim_reference_map(
        claim_reference_map=claim_reference_map,
        known_evidence_ids=known_evidence_ids,
    )
    outline = build_deck_outline_model(normalized)
    return outline_to_slidespec_model(outline=outline, normalized=normalized)


__all__ = [
    "build_deck_outline_model",
    "build_deck_outline_payload",
    "build_deck_outline_payload_json",
    "build_evidence_graph_model",
    "build_evidence_graph_payload",
    "build_evidence_graph_payload_json",
    "LOW_CONFIDENCE_PREFIX",
    "LOW_CONFIDENCE_THRESHOLD",
    "outline_to_slidespec_model",
    "outline_to_slidespec_payload",
    "plan_normalized_model",
    "plan_normalized_payload",
    "plan_normalized_payload_json",
]
