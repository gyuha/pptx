from importlib import import_module
from pathlib import Path
from typing import Callable, cast

from .pdf import EXTRACT_SCHEMA_VERSION, ExtractPayload, extract_pdf


def extract_docx(input_path: Path) -> ExtractPayload:
    module = import_module("pptx_agent.extract.docx_extract")
    extractor = cast(Callable[[Path], ExtractPayload], getattr(module, "extract_docx"))
    return extractor(input_path)


def extract_document(input_path: Path) -> ExtractPayload:
    suffix = input_path.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf(input_path)
    if suffix == ".docx":
        return extract_docx(input_path)
    return {
        "schema_version": EXTRACT_SCHEMA_VERSION,
        "input": {"file": str(input_path), "page_count": 0},
        "status": "unsupported",
        "reason_code": "unsupported_file_type",
        "reason": f"Unsupported file type: {suffix or '<none>'}.",
        "metadata": {
            "primary_engine": "dispatcher",
            "fallback_engine": "none",
            "fallback_used": False,
            "confidence_policy": "heuristic-v1",
        },
        "pages": [],
    }


__all__ = [
    "EXTRACT_SCHEMA_VERSION",
    "extract_pdf",
    "extract_docx",
    "extract_document",
]
