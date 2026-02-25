from __future__ import annotations

# pyright: reportAttributeAccessIssue=false, reportMissingImports=false, reportMissingTypeStubs=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownVariableType=false

from pathlib import Path
from typing import Literal, TypedDict

import fitz
import pdfplumber

EXTRACT_SCHEMA_VERSION = "extract.v1"


class ConfidenceMeta(TypedDict):
    engine: str
    signals: list[str]


class ExtractBlock(TypedDict):
    block_id: str
    kind: Literal["text", "table"]
    text: str
    bbox: list[float]
    confidence: float
    confidence_meta: ConfidenceMeta


class ExtractPageSize(TypedDict):
    width: float
    height: float


class ExtractPage(TypedDict):
    page_number: int
    size: ExtractPageSize
    blocks: list[ExtractBlock]


class ExtractInputMeta(TypedDict):
    file: str
    page_count: int


class ExtractRunMeta(TypedDict):
    primary_engine: str
    fallback_engine: str
    fallback_used: bool
    confidence_policy: str


class ExtractPayload(TypedDict):
    schema_version: str
    input: ExtractInputMeta
    status: Literal["ok", "unsupported"]
    reason_code: str | None
    reason: str | None
    metadata: ExtractRunMeta
    pages: list[ExtractPage]


def _normalize_text(value: str) -> str:
    return " ".join(value.split()).strip()


def _bbox(x0: float, y0: float, x1: float, y1: float) -> list[float]:
    return [
        round(float(x0), 2),
        round(float(y0), 2),
        round(float(x1), 2),
        round(float(y1), 2),
    ]


def _fitz_blocks(page: fitz.Page, page_number: int) -> list[ExtractBlock]:
    blocks: list[ExtractBlock] = []
    raw_blocks = page.get_text("blocks", sort=True)
    for index, block in enumerate(raw_blocks, start=1):
        x0, y0, x1, y1, text, *_ = block
        normalized = _normalize_text(str(text))
        if not normalized:
            continue
        words = max(1, len(normalized.split()))
        confidence = min(0.99, 0.86 + (min(words, 25) * 0.003))
        blocks.append(
            {
                "block_id": f"p{page_number:03d}-b{index:04d}",
                "kind": "text",
                "text": normalized,
                "bbox": _bbox(x0, y0, x1, y1),
                "confidence": round(confidence, 3),
                "confidence_meta": {
                    "engine": "pymupdf",
                    "signals": ["text_block"],
                },
            }
        )
    return blocks


def _pdfplumber_blocks(
    plumber_page: pdfplumber.page.Page, page_number: int
) -> list[ExtractBlock]:
    blocks: list[ExtractBlock] = []
    words = plumber_page.extract_words(use_text_flow=True, keep_blank_chars=False)
    for index, word in enumerate(words, start=1):
        text = _normalize_text(str(word.get("text", "")))
        if not text:
            continue
        blocks.append(
            {
                "block_id": f"p{page_number:03d}-fb{index:04d}",
                "kind": "text",
                "text": text,
                "bbox": _bbox(
                    float(word.get("x0", 0.0)),
                    float(word.get("top", 0.0)),
                    float(word.get("x1", 0.0)),
                    float(word.get("bottom", 0.0)),
                ),
                "confidence": 0.67,
                "confidence_meta": {
                    "engine": "pdfplumber",
                    "signals": ["word_level_fallback"],
                },
            }
        )

    tables = plumber_page.find_tables()
    for table_index, table in enumerate(tables, start=1):
        rows = table.extract() or []
        row_text = []
        for row in rows:
            cells = ["" if cell is None else _normalize_text(str(cell)) for cell in row]
            row_text.append("\t".join(cells).strip())
        table_text = "\n".join(segment for segment in row_text if segment)
        if not table_text:
            continue
        blocks.append(
            {
                "block_id": f"p{page_number:03d}-ft{table_index:04d}",
                "kind": "table",
                "text": table_text,
                "bbox": _bbox(
                    table.bbox[0], table.bbox[1], table.bbox[2], table.bbox[3]
                ),
                "confidence": 0.61,
                "confidence_meta": {
                    "engine": "pdfplumber",
                    "signals": ["table_detection_fallback"],
                },
            }
        )

    return blocks


def extract_pdf(input_path: Path) -> ExtractPayload:
    path = Path(input_path)
    doc = fitz.open(path)
    try:
        if doc.needs_pass:
            return {
                "schema_version": EXTRACT_SCHEMA_VERSION,
                "input": {"file": str(path), "page_count": 0},
                "status": "unsupported",
                "reason_code": "encrypted_pdf",
                "reason": "Password-protected PDFs are unsupported in this stage.",
                "metadata": {
                    "primary_engine": "pymupdf",
                    "fallback_engine": "pdfplumber",
                    "fallback_used": False,
                    "confidence_policy": "heuristic-v1",
                },
                "pages": [],
            }

        pages: list[ExtractPage] = []
        fallback_candidates: list[int] = []
        has_images = False
        fallback_used = False

        for page_index, page in enumerate(doc, start=1):
            page_blocks = _fitz_blocks(page, page_index)
            if not page_blocks:
                fallback_candidates.append(page_index)
            if page.get_images(full=True):
                has_images = True
            pages.append(
                {
                    "page_number": page_index,
                    "size": {
                        "width": round(float(page.rect.width), 2),
                        "height": round(float(page.rect.height), 2),
                    },
                    "blocks": page_blocks,
                }
            )

        if fallback_candidates:
            with pdfplumber.open(path) as plumber_doc:
                for page_number in fallback_candidates:
                    plumber_page = plumber_doc.pages[page_number - 1]
                    fallback_blocks = _pdfplumber_blocks(plumber_page, page_number)
                    if fallback_blocks:
                        pages[page_number - 1]["blocks"] = fallback_blocks
                        fallback_used = True

        block_count = sum(len(page["blocks"]) for page in pages)
        status = "ok"
        reason_code: str | None = None
        reason: str | None = None
        if block_count == 0:
            status = "unsupported"
            if has_images:
                reason_code = "scanned_or_image_only"
                reason = "No extractable text found; document appears scanned or image-only. OCR is disabled."
            else:
                reason_code = "no_extractable_text"
                reason = "No extractable text found in document."

        return {
            "schema_version": EXTRACT_SCHEMA_VERSION,
            "input": {
                "file": str(path),
                "page_count": len(pages),
            },
            "status": status,
            "reason_code": reason_code,
            "reason": reason,
            "metadata": {
                "primary_engine": "pymupdf",
                "fallback_engine": "pdfplumber",
                "fallback_used": fallback_used,
                "confidence_policy": "heuristic-v1",
            },
            "pages": pages,
        }
    finally:
        doc.close()
