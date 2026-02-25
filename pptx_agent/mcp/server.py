from __future__ import annotations

# pyright: reportAttributeAccessIssue=false, reportMissingImports=false, reportMissingTypeStubs=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUntypedBaseClass=false, reportUnusedCallResult=false

import json
import sys
import hashlib
from pathlib import Path
from typing import ClassVar, Literal, TypedDict, cast

from pydantic import BaseModel, ConfigDict, ValidationError

from ..contracts import SlideSpec
from ..contracts.batch_manifest import BatchManifest
from .. import cli as cli_module
from ..extract import extract_document
from ..hooks import read_qa_summary_file
from ..normalize import normalize_extract_payload
from ..plan import plan_normalized_payload
from ..render import render_slidespec_to_pptx

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "pptx-agent-mcp"
SERVER_VERSION = "0.1.0"
WORKSPACE_ROOT = Path(__file__).resolve().parents[2]


class JsonRpcRequest(BaseModel):
    jsonrpc: str
    id: int | str | None = None
    method: str
    params: dict[str, object] = {}


class JsonRpcErrorObject(TypedDict):
    code: int
    message: str
    data: object | None


class JsonRpcResponse(TypedDict):
    jsonrpc: str
    id: int | str | None
    result: dict[str, object] | None
    error: JsonRpcErrorObject | None


class ExtractArgs(BaseModel):
    input_pdf: str


class NormalizeArgs(BaseModel):
    extract_payload: dict[str, object]


class PlanArgs(BaseModel):
    normalized_payload: dict[str, object]


class RenderArgs(BaseModel):
    slidespec: dict[str, object]
    output_pptx: str


class QaReadArgs(BaseModel):
    qa_summary_path: str


class RunFolderArgs(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    input_dir: str
    output_dir: str
    artifacts_root: str = "artifacts/batches"
    model_profile: Literal["local", "cloud"] = "local"
    continue_on_error: bool = True


class AnalysisSummaryArgs(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    batch_manifest_path: str


class ReviseArgs(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    run_dir: str
    feedback_path: str


class ExtractResult(BaseModel):
    schema_version: str
    status: str
    reason_code: str | None
    reason: str | None
    page_count: int
    block_count: int
    payload: dict[str, object]


class NormalizeResult(BaseModel):
    schema_version: str
    status: str
    deck_id: str
    page_count: int
    element_count: int
    has_unsupported: bool
    payload: dict[str, object]


class PlanResult(BaseModel):
    schema_version: str
    deck_id: str
    slide_count: int
    element_count: int
    payload: dict[str, object]


class RenderResult(BaseModel):
    output_pptx: str
    qa_report: dict[str, object]


class QaReadResult(BaseModel):
    qa_summary: dict[str, object]


def _resolve_workspace_path(raw_path: str, *, must_exist: bool) -> Path:
    path = Path(raw_path)
    candidate = (
        path.resolve() if path.is_absolute() else (WORKSPACE_ROOT / path).resolve()
    )

    if not candidate.is_relative_to(WORKSPACE_ROOT):
        raise PermissionError("Path is outside workspace root.")

    if must_exist and not candidate.exists():
        raise FileNotFoundError(str(candidate))

    return candidate


def _workspace_relative(path: Path) -> str:
    return path.resolve().relative_to(WORKSPACE_ROOT).as_posix()


def _to_workspace_relative_path(path_value: str | None) -> str | None:
    if path_value is None:
        return None
    return _workspace_relative(Path(path_value))


def _sorted_input_files(input_dir: Path) -> list[Path]:
    files = [path for path in input_dir.rglob("*") if path.is_file()]
    return sorted(files, key=lambda path: path.relative_to(input_dir).as_posix())


def _deterministic_batch_id(
    *, input_dir: Path, output_dir: Path, artifacts_root: Path, input_files: list[Path]
) -> str:
    rel_paths = [path.relative_to(input_dir).as_posix() for path in input_files]
    joined = "|".join(rel_paths)
    raw = f"{input_dir.resolve()}::{output_dir.resolve()}::{artifacts_root.resolve()}::{joined}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _run_cli_handler(command_args: list[str]) -> int:
    parser = cli_module.build_parser()
    namespace = parser.parse_args(command_args)
    handler = cast(object, getattr(namespace, "handler", None))
    if handler is None or not callable(handler):
        raise RuntimeError("CLI command did not resolve to a handler.")
    result = handler(namespace)
    if not isinstance(result, int):
        raise RuntimeError("CLI handler returned non-integer exit code.")
    return int(result)


def _tool_specs() -> list[dict[str, object]]:
    return [
        {
            "name": "extract",
            "description": "Extract structured text/table blocks from a supported document (.pdf, .docx).",
            "inputSchema": ExtractArgs.model_json_schema(),
        },
        {
            "name": "normalize",
            "description": "Normalize extract.v1 payload into normalize.v1 payload.",
            "inputSchema": NormalizeArgs.model_json_schema(),
        },
        {
            "name": "plan",
            "description": "Plan normalized payload into SlideSpec v1.",
            "inputSchema": PlanArgs.model_json_schema(),
        },
        {
            "name": "render",
            "description": "Render SlideSpec v1 into deterministic PPTX + QA report.",
            "inputSchema": RenderArgs.model_json_schema(),
        },
        {
            "name": "qa-summary-read",
            "description": "Read and validate render hook QA summary JSON.",
            "inputSchema": QaReadArgs.model_json_schema(),
        },
        {
            "name": "run-folder",
            "description": "Run deterministic folder orchestration with approved runtime options.",
            "inputSchema": RunFolderArgs.model_json_schema(),
        },
        {
            "name": "analysis-summary",
            "description": "Read and summarize a batch manifest into deterministic analysis metrics.",
            "inputSchema": AnalysisSummaryArgs.model_json_schema(),
        },
        {
            "name": "revise",
            "description": "Trigger deterministic feedback-driven revision for one run directory.",
            "inputSchema": ReviseArgs.model_json_schema(),
        },
    ]


def _tool_result_payload(name: str, payload: dict[str, object]) -> dict[str, object]:
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(payload, sort_keys=True),
            }
        ],
        "isError": False,
        "structuredContent": {
            "tool": name,
            "ok": True,
            "result": payload,
        },
    }


def _handle_extract(arguments: dict[str, object]) -> dict[str, object]:
    parsed = ExtractArgs.model_validate(arguments)
    payload = cast(
        dict[str, object], cast(object, extract_document(Path(parsed.input_pdf)))
    )
    pages = cast(list[dict[str, object]], payload.get("pages", []))
    block_count = sum(len(cast(list[object], page.get("blocks", []))) for page in pages)
    result = ExtractResult(
        schema_version=str(payload.get("schema_version", "")),
        status=str(payload.get("status", "")),
        reason_code=cast(str | None, payload.get("reason_code")),
        reason=cast(str | None, payload.get("reason")),
        page_count=len(pages),
        block_count=block_count,
        payload=payload,
    )
    return result.model_dump(mode="json")


def _handle_normalize(arguments: dict[str, object]) -> dict[str, object]:
    parsed = NormalizeArgs.model_validate(arguments)
    normalized = normalize_extract_payload(parsed.extract_payload)
    element_count = sum(len(page.elements) for page in normalized.pages)
    result = NormalizeResult(
        schema_version=normalized.schema_version,
        status=normalized.status,
        deck_id=normalized.deck_id,
        page_count=len(normalized.pages),
        element_count=element_count,
        has_unsupported=normalized.unsupported_report.has_unsupported,
        payload=cast(dict[str, object], normalized.model_dump(mode="json")),
    )
    return result.model_dump(mode="json")


def _handle_plan(arguments: dict[str, object]) -> dict[str, object]:
    parsed = PlanArgs.model_validate(arguments)
    slidespec = plan_normalized_payload(parsed.normalized_payload)
    element_count = sum(len(slide.elements) for slide in slidespec.slides)
    result = PlanResult(
        schema_version=slidespec.schema_version,
        deck_id=slidespec.deck_id,
        slide_count=len(slidespec.slides),
        element_count=element_count,
        payload=cast(dict[str, object], slidespec.model_dump(mode="json")),
    )
    return result.model_dump(mode="json")


def _handle_render(arguments: dict[str, object]) -> dict[str, object]:
    parsed = RenderArgs.model_validate(arguments)
    slidespec = SlideSpec.model_validate(parsed.slidespec)
    output_path = Path(parsed.output_pptx)
    qa_report = cast(
        dict[str, object],
        cast(
            object,
            render_slidespec_to_pptx(slidespec=slidespec, output_path=output_path),
        ),
    )
    result = RenderResult(output_pptx=str(output_path), qa_report=qa_report)
    return result.model_dump(mode="json")


def _handle_qa_summary_read(arguments: dict[str, object]) -> dict[str, object]:
    parsed = QaReadArgs.model_validate(arguments)
    qa_summary = cast(
        dict[str, object],
        cast(object, read_qa_summary_file(Path(parsed.qa_summary_path))),
    )
    result = QaReadResult(qa_summary=qa_summary)
    return result.model_dump(mode="json")


def _handle_run_folder(arguments: dict[str, object]) -> dict[str, object]:
    parsed = RunFolderArgs.model_validate(arguments)
    input_dir = _resolve_workspace_path(parsed.input_dir, must_exist=True)
    output_dir = _resolve_workspace_path(parsed.output_dir, must_exist=False)
    artifacts_root = _resolve_workspace_path(parsed.artifacts_root, must_exist=False)

    input_files = _sorted_input_files(input_dir)
    batch_id: str | None = None
    batch_manifest_path: Path | None = None

    if input_files:
        batch_id = _deterministic_batch_id(
            input_dir=input_dir,
            output_dir=output_dir,
            artifacts_root=artifacts_root,
            input_files=input_files,
        )
        batch_manifest_path = artifacts_root / batch_id / "batch_manifest.json"

    exit_code = _run_cli_handler(
        [
            "run-folder",
            "--in-dir",
            str(input_dir),
            "--out-dir",
            str(output_dir),
            "--artifacts-root",
            str(artifacts_root),
            "--model-profile",
            parsed.model_profile,
            "--continue-on-error",
            "true" if parsed.continue_on_error else "false",
        ]
    )

    counts: dict[str, int] | None = None
    status = "failed"
    if batch_manifest_path is not None and batch_manifest_path.exists():
        manifest_payload = cast(
            dict[str, object],
            json.loads(batch_manifest_path.read_text(encoding="utf-8")),
        )
        manifest = BatchManifest.model_validate(manifest_payload)
        status = manifest.status
        counts = {
            "total": manifest.counts.total,
            "passed": manifest.counts.passed,
            "failed": manifest.counts.failed,
            "unsupported": manifest.counts.unsupported,
        }

    return {
        "schema": "mcp.run_folder.result.v1",
        "exit_code": exit_code,
        "batch_id": batch_id,
        "batch_manifest_path": (
            _workspace_relative(batch_manifest_path)
            if batch_manifest_path is not None and batch_manifest_path.exists()
            else None
        ),
        "status": status,
        "counts": counts,
    }


def _handle_analysis_summary(arguments: dict[str, object]) -> dict[str, object]:
    parsed = AnalysisSummaryArgs.model_validate(arguments)
    batch_manifest_path = _resolve_workspace_path(
        parsed.batch_manifest_path, must_exist=True
    )
    manifest_payload = cast(
        dict[str, object],
        json.loads(batch_manifest_path.read_text(encoding="utf-8")),
    )
    manifest = BatchManifest.model_validate(manifest_payload)

    documents = sorted(
        [
            {
                "doc_id": doc.doc_id,
                "status": doc.status,
                "failure_reason": doc.failure_reason,
                "run_dir": _to_workspace_relative_path(doc.run_dir),
                "output_pptx": _to_workspace_relative_path(doc.output_pptx),
            }
            for doc in manifest.documents
        ],
        key=lambda item: str(item["doc_id"]),
    )

    return {
        "schema": "mcp.analysis_summary.v1",
        "batch_id": manifest.batch_id,
        "status": manifest.status,
        "runtime": {
            "model_profile": manifest.runtime.model_profile,
            "language": manifest.runtime.language,
            "image_model": manifest.runtime.image_model,
            "text_model": manifest.runtime.text_model,
        },
        "counts": {
            "total": manifest.counts.total,
            "passed": manifest.counts.passed,
            "failed": manifest.counts.failed,
            "unsupported": manifest.counts.unsupported,
        },
        "documents": cast(list[dict[str, object]], documents),
    }


def _handle_revise(arguments: dict[str, object]) -> dict[str, object]:
    parsed = ReviseArgs.model_validate(arguments)
    run_dir = _resolve_workspace_path(parsed.run_dir, must_exist=True)
    feedback_path = _resolve_workspace_path(parsed.feedback_path, must_exist=True)

    exit_code = _run_cli_handler(
        [
            "revise",
            "--run-dir",
            str(run_dir),
            "--feedback",
            str(feedback_path),
        ]
    )

    run_manifest_path = run_dir / "run_manifest.json"
    manifest_payload: dict[str, object] | None = None
    if run_manifest_path.exists():
        manifest_payload = cast(
            dict[str, object],
            json.loads(run_manifest_path.read_text(encoding="utf-8")),
        )

    return {
        "schema": "mcp.revise.result.v1",
        "exit_code": exit_code,
        "run_manifest_path": (
            _workspace_relative(run_manifest_path)
            if run_manifest_path.exists()
            else None
        ),
        "status": (
            str(manifest_payload.get("status", "unknown"))
            if manifest_payload is not None
            else ("pass" if exit_code == 0 else "failed")
        ),
        "run_id": (
            cast(str | None, manifest_payload.get("run_id"))
            if manifest_payload is not None
            else None
        ),
        "parent_run_id": (
            cast(str | None, manifest_payload.get("parent_run_id"))
            if manifest_payload is not None
            else None
        ),
        "targeted_slide_ids": (
            cast(list[str], manifest_payload.get("targeted_slide_ids", []))
            if manifest_payload is not None
            else []
        ),
    }


TOOL_HANDLERS = {
    "extract": _handle_extract,
    "normalize": _handle_normalize,
    "plan": _handle_plan,
    "render": _handle_render,
    "qa-summary-read": _handle_qa_summary_read,
    "run-folder": _handle_run_folder,
    "analysis-summary": _handle_analysis_summary,
    "revise": _handle_revise,
}


def _make_result_response(
    request_id: int | str | None, result: dict[str, object]
) -> JsonRpcResponse:
    return {"jsonrpc": "2.0", "id": request_id, "result": result, "error": None}


def _make_error_response(
    request_id: int | str | None,
    *,
    code: int,
    message: str,
    data: object | None = None,
) -> JsonRpcResponse:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": None,
        "error": {"code": code, "message": message, "data": data},
    }


def _handle_call(request: JsonRpcRequest) -> JsonRpcResponse | None:
    method = request.method
    params = request.params

    if method == "notifications/initialized":
        return None

    if method == "initialize":
        result = cast(
            dict[str, object],
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        )
        return _make_result_response(request.id, result)

    if method == "tools/list":
        return _make_result_response(request.id, {"tools": _tool_specs()})

    if method == "tools/call":
        tool_name = cast(str | None, params.get("name"))
        if tool_name not in TOOL_HANDLERS:
            return _make_error_response(
                request.id,
                code=-32601,
                message="Operation is not approved on this MCP surface.",
                data={"allowed_tools": sorted(TOOL_HANDLERS.keys())},
            )

        arguments = cast(dict[str, object], params.get("arguments", {}))
        try:
            payload = TOOL_HANDLERS[tool_name](arguments)
        except ValidationError as exc:
            return _make_error_response(
                request.id,
                code=-32602,
                message="Invalid params for tool call.",
                data={"tool": tool_name, "errors": exc.errors()},
            )
        except FileNotFoundError as exc:
            return _make_error_response(
                request.id,
                code=-32002,
                message="Required file not found.",
                data={"tool": tool_name, "path": str(exc)},
            )
        except PermissionError as exc:
            return _make_error_response(
                request.id,
                code=-32601,
                message="Operation is blocked by MCP path policy.",
                data={"tool": tool_name, "detail": str(exc)},
            )
        except Exception as exc:
            return _make_error_response(
                request.id,
                code=-32000,
                message="Tool execution failed.",
                data={
                    "tool": tool_name,
                    "error_type": exc.__class__.__name__,
                    "detail": str(exc),
                },
            )

        return _make_result_response(
            request.id, _tool_result_payload(tool_name, payload)
        )

    return _make_error_response(
        request.id, code=-32601, message=f"Method not found: {method}"
    )


def run_stdio_server() -> int:
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue

        request_id: int | str | None = None
        try:
            parsed_line = cast(object, json.loads(line))
            request = JsonRpcRequest.model_validate(parsed_line)
            request_id = request.id
        except ValidationError as exc:
            response = _make_error_response(
                request_id,
                code=-32600,
                message="Invalid JSON-RPC request.",
                data=exc.errors(),
            )
            _ = sys.stdout.write(json.dumps(response, sort_keys=True) + "\n")
            _ = sys.stdout.flush()
            continue
        except json.JSONDecodeError as exc:
            response = _make_error_response(
                request_id,
                code=-32700,
                message="Parse error.",
                data={"line": exc.lineno, "column": exc.colno, "detail": exc.msg},
            )
            _ = sys.stdout.write(json.dumps(response, sort_keys=True) + "\n")
            _ = sys.stdout.flush()
            continue

        response = _handle_call(request)
        if response is None:
            continue

        _ = sys.stdout.write(json.dumps(response, sort_keys=True) + "\n")
        _ = sys.stdout.flush()

    return 0


def main() -> int:
    return run_stdio_server()


if __name__ == "__main__":
    raise SystemExit(main())
