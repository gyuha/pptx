from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TypedDict


class DocumentRegistryEntry(TypedDict):
    doc_id: str
    input_file: str
    relative_path: str
    input_name: str
    input_type: str
    input_size_bytes: int
    sha256: str


class DocumentRegistryPayload(TypedDict):
    schema: str
    batch_id: str
    input_dir: str
    document_count: int
    documents: list[DocumentRegistryEntry]


def sha256_file(input_path: Path) -> str:
    digest = hashlib.sha256()
    with input_path.open("rb") as file_handle:
        while True:
            chunk = file_handle.read(8192)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def deterministic_doc_id(*, input_dir: Path, input_path: Path, sha256_hex: str) -> str:
    relative_path = input_path.relative_to(input_dir).as_posix()
    digest = hashlib.sha256(
        f"{relative_path}::{sha256_hex}".encode("utf-8")
    ).hexdigest()
    return digest[:16]


def build_document_registry(
    *, input_dir: Path, batch_id: str, input_files: list[Path]
) -> DocumentRegistryPayload:
    documents: list[DocumentRegistryEntry] = []
    sorted_files = sorted(
        input_files,
        key=lambda input_path: input_path.relative_to(input_dir).as_posix(),
    )
    for input_path in sorted_files:
        relative_path = input_path.relative_to(input_dir).as_posix()
        sha256_hex = sha256_file(input_path)
        documents.append(
            {
                "doc_id": deterministic_doc_id(
                    input_dir=input_dir,
                    input_path=input_path,
                    sha256_hex=sha256_hex,
                ),
                "input_file": str(input_path),
                "relative_path": relative_path,
                "input_name": input_path.name,
                "input_type": input_path.suffix.lower().lstrip("."),
                "input_size_bytes": input_path.stat().st_size,
                "sha256": sha256_hex,
            }
        )

    return {
        "schema": "pipeline.document_registry.v1",
        "batch_id": batch_id,
        "input_dir": str(input_dir),
        "document_count": len(documents),
        "documents": documents,
    }
