from __future__ import annotations

# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false

from pathlib import Path
from zipfile import BadZipFile, ZipFile

from .pdf import (
    EXTRACT_SCHEMA_VERSION,
    ExtractBlock,
    ExtractInputMeta,
    ExtractPage,
    ExtractPageSize,
    ExtractPayload,
    ExtractRunMeta,
)

_DOCX_PAGE_SIZE: ExtractPageSize = {"width": 595.0, "height": 842.0}


def _normalize_text(value: str) -> str:
    return " ".join(value.split()).strip()


def _unsupported_payload(path: Path, reason_code: str, reason: str) -> ExtractPayload:
    input_meta: ExtractInputMeta = {"file": str(path), "page_count": 0}
    metadata: ExtractRunMeta = {
        "primary_engine": "docx-xml",
        "fallback_engine": "none",
        "fallback_used": False,
        "confidence_policy": "heuristic-v1",
    }
    return {
        "schema_version": EXTRACT_SCHEMA_VERSION,
        "input": input_meta,
        "status": "unsupported",
        "reason_code": reason_code,
        "reason": reason,
        "metadata": metadata,
        "pages": [],
    }


def _extract_blocks(document_xml: str) -> list[ExtractBlock]:
    import xml.etree.ElementTree as ET

    word_namespace = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    namespace = {"w": word_namespace}
    root = ET.fromstring(document_xml)
    body = root.find("w:body", namespace)
    if body is None:
        return []

    blocks: list[ExtractBlock] = []
    block_index = 0

    paragraph_tag = f"{{{word_namespace}}}p"
    table_tag = f"{{{word_namespace}}}tbl"
    for child in list(body):
        if child.tag == paragraph_tag:
            text_nodes = child.findall(".//w:t", namespace)
            text = _normalize_text("".join(node.text or "" for node in text_nodes))
            if not text:
                continue
            block_index += 1
            blocks.append(
                {
                    "block_id": f"p001-b{block_index:04d}",
                    "kind": "text",
                    "text": text,
                    "bbox": [0.0, 0.0, 0.0, 0.0],
                    "confidence": 0.9,
                    "confidence_meta": {
                        "engine": "docx-xml",
                        "signals": ["paragraph"],
                    },
                }
            )
            continue

        if child.tag != table_tag:
            continue

        row_segments: list[str] = []
        for row in child.findall(".//w:tr", namespace):
            cells: list[str] = []
            for cell in row.findall(".//w:tc", namespace):
                text_nodes = cell.findall(".//w:t", namespace)
                cell_text = _normalize_text(
                    "".join(node.text or "" for node in text_nodes)
                )
                cells.append(cell_text)
            row_segments.append("\t".join(cells).strip())
        table_text = "\n".join(segment for segment in row_segments if segment)
        if not table_text:
            continue
        block_index += 1
        blocks.append(
            {
                "block_id": f"p001-t{block_index:04d}",
                "kind": "table",
                "text": table_text,
                "bbox": [0.0, 0.0, 0.0, 0.0],
                "confidence": 0.82,
                "confidence_meta": {
                    "engine": "docx-xml",
                    "signals": ["table"],
                },
            }
        )

    return blocks


def extract_docx(input_path: Path) -> ExtractPayload:
    path = Path(input_path)
    try:
        with ZipFile(path) as docx_zip:
            try:
                document_xml = docx_zip.read("word/document.xml").decode("utf-8")
            except KeyError:
                return _unsupported_payload(
                    path,
                    "missing_docx_document_xml",
                    "DOCX package missing word/document.xml.",
                )
    except BadZipFile:
        return _unsupported_payload(
            path,
            "invalid_docx_package",
            "DOCX package is invalid or corrupted.",
        )

    try:
        blocks = _extract_blocks(document_xml)
    except Exception:
        return _unsupported_payload(
            path,
            "invalid_docx_xml",
            "DOCX word/document.xml is malformed.",
        )

    status = "ok"
    reason_code: str | None = None
    reason: str | None = None
    pages: list[ExtractPage] = []
    if not blocks:
        status = "unsupported"
        reason_code = "no_extractable_text"
        reason = "No extractable text found in document."
    else:
        pages.append(
            {
                "page_number": 1,
                "size": _DOCX_PAGE_SIZE,
                "blocks": blocks,
            }
        )

    input_meta: ExtractInputMeta = {"file": str(path), "page_count": len(pages)}
    metadata: ExtractRunMeta = {
        "primary_engine": "docx-xml",
        "fallback_engine": "none",
        "fallback_used": False,
        "confidence_policy": "heuristic-v1",
    }
    return {
        "schema_version": EXTRACT_SCHEMA_VERSION,
        "input": input_meta,
        "status": status,
        "reason_code": reason_code,
        "reason": reason,
        "metadata": metadata,
        "pages": pages,
    }
