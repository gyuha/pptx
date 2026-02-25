from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import TypedDict, cast

# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownParameterType=false

from ..contracts import SlideSpec, validate_slidespec_file

HOOK_QA_SCHEMA = "render.hooks.qa.v1"
HOOK_ERROR_SCHEMA = "render.hooks.error.v1"


class HookPolicyError(RuntimeError):
    phase: str
    reason: str
    details: list[str]

    def __init__(
        self, phase: str, reason: str, details: list[str] | None = None
    ) -> None:
        super().__init__(f"{phase}:{reason}")
        self.phase = phase
        self.reason = reason
        self.details = details or []


class HookQASummary(TypedDict):
    run_id: str
    schema: str
    input_slidespec: str
    output_pptx: str
    qa_report: str
    status: str
    checks: dict[str, bool]
    failures: list[str]


class HookErrorReport(TypedDict):
    run_id: str
    schema: str
    input_slidespec: str
    output_pptx: str
    phase: str
    reason: str
    error_type: str
    message: str
    details: list[str]


def _format_validation_errors(exc: Exception) -> list[str]:
    errors = getattr(exc, "errors", None)
    if not callable(errors):
        return [str(exc)]
    validation_errors = errors()
    if not isinstance(validation_errors, list):
        return [str(exc)]
    details: list[str] = []
    for err in cast(list[dict[str, object]], validation_errors):
        location_parts = cast(list[object], err["loc"])
        location = ".".join(str(part) for part in location_parts)
        details.append(f"{location}: {err['msg']}")
    return details


def compute_run_id(input_path: Path, output_path: Path) -> str:
    raw = f"{input_path.resolve()}::{output_path.resolve()}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return digest[:16]


def pre_render_contract_gate(input_path: Path) -> SlideSpec:
    try:
        return validate_slidespec_file(input_path)
    except Exception as exc:
        if exc.__class__.__name__ == "ValidationError":
            details = _format_validation_errors(exc)
            raise HookPolicyError(
                phase="pre_render",
                reason="slidespec_validation_failed",
                details=details,
            ) from exc
        raise


def post_render_qa_gate(
    *,
    run_id: str,
    input_path: Path,
    output_path: Path,
    qa_report_path: Path,
    qa_report: Mapping[str, object],
) -> HookQASummary:
    slide_count_expected = cast(int, qa_report["slide_count_expected"])
    slide_count_rendered = cast(int, qa_report["slide_count_rendered"])
    critical_overflow_count = cast(int, qa_report["critical_overflow_count"])

    checks = {
        "slide_count_matches": slide_count_expected == slide_count_rendered,
        "critical_overflow_zero": critical_overflow_count == 0,
    }
    failures = [check_name for check_name, passed in checks.items() if not passed]

    summary: HookQASummary = {
        "run_id": run_id,
        "schema": HOOK_QA_SCHEMA,
        "input_slidespec": str(input_path),
        "output_pptx": str(output_path),
        "qa_report": str(qa_report_path),
        "status": "pass" if not failures else "fail",
        "checks": checks,
        "failures": failures,
    }

    summary_path = output_path.with_suffix(output_path.suffix + ".hooks.qa.json")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    _ = summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if failures:
        raise HookPolicyError(
            phase="post_render",
            reason="qa_gate_failed",
            details=failures,
        )

    return summary


def write_on_error_report(
    *,
    run_id: str,
    input_path: Path,
    output_path: Path,
    phase: str,
    reason: str,
    error: Exception,
    details: list[str] | None = None,
) -> Path:
    report: HookErrorReport = {
        "run_id": run_id,
        "schema": HOOK_ERROR_SCHEMA,
        "input_slidespec": str(input_path),
        "output_pptx": str(output_path),
        "phase": phase,
        "reason": reason,
        "error_type": error.__class__.__name__,
        "message": str(error),
        "details": details or [],
    }

    report_path = output_path.with_suffix(output_path.suffix + ".hooks.error.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    _ = report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report_path


def read_qa_summary_file(summary_path: Path) -> HookQASummary:
    payload = cast(object, json.loads(summary_path.read_text(encoding="utf-8")))
    if not isinstance(payload, dict):
        raise ValueError("qa summary must be an object")

    required_string_fields = [
        "run_id",
        "schema",
        "input_slidespec",
        "output_pptx",
        "qa_report",
        "status",
    ]
    for field in required_string_fields:
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"qa summary field '{field}' must be a non-empty string")

    checks_value = payload.get("checks")
    if not isinstance(checks_value, dict):
        raise ValueError("qa summary field 'checks' must be an object")
    for key, value in checks_value.items():
        if not isinstance(key, str) or not isinstance(value, bool):
            raise ValueError(
                "qa summary field 'checks' must map string keys to bool values"
            )

    failures_value = payload.get("failures")
    if not isinstance(failures_value, list) or not all(
        isinstance(item, str) for item in failures_value
    ):
        raise ValueError("qa summary field 'failures' must be a list of strings")

    return cast(HookQASummary, cast(object, payload))
