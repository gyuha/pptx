import argparse
import hashlib
import json
import os
import re
import shutil
from pathlib import Path
from typing import Callable, TypedDict, cast

# pyright: reportMissingImports=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnusedCallResult=false

from .contracts import (
    BATCH_MANIFEST_SCHEMA_VERSION_V1,
    DECK_OUTLINE_SCHEMA_VERSION_V1,
    SCHEMA_VERSION_V1,
    BatchManifest,
    DeckOutline,
    FeedbackPatch,
    validate_slidespec_file,
)
from .extract import extract_document
from .hooks import (
    HookPolicyError,
    compute_run_id,
    post_render_qa_gate,
    pre_render_contract_gate,
    read_qa_summary_file,
    write_on_error_report,
)
from .normalize import normalize_extract_payload_json
from .plan import (
    build_deck_outline_payload_json,
    build_evidence_graph_payload_json,
    outline_to_slidespec_payload,
    plan_normalized_payload_json,
)
from .registry import build_document_registry
from .render import (
    ImageGenerationFailedError,
    UnsupportedLayoutHintError,
    render_slidespec_to_pptx,
)


class QAGateReport(TypedDict):
    schema: str
    run_id: str
    slidespec_path: str
    qa_report_path: str | None
    hook_summary_path: str | None
    checks: dict[str, bool]
    metrics: dict[str, float | int]
    failures: list[str]
    status: str


def _write_json_file(output_path: Path, payload: object) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _ = output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _deterministic_run_id(input_path: Path) -> str:
    digest = hashlib.sha256(str(input_path.resolve()).encode("utf-8")).hexdigest()
    return digest[:16]


def _unlink_if_exists(path: Path) -> None:
    if path.exists():
        path.unlink()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _cleanup_temp_paths(*, files: list[Path], dirs: list[Path]) -> None:
    for file_path in files:
        _unlink_if_exists(file_path)
    for dir_path in dirs:
        if dir_path.exists() and dir_path.is_dir():
            shutil.rmtree(dir_path)


def _parse_feedback_patch(feedback_path: Path) -> FeedbackPatch:
    return FeedbackPatch.model_validate_json(feedback_path.read_text(encoding="utf-8"))


def _required_non_blank_string(*, value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"unknown_target: {field_name} requires non-blank string value"
        )
    return value


_PATCH_ELEMENT_INDEX_PATTERN = re.compile(r"elements\[(\d+)\]")


def _resolve_target_element(
    *,
    slide_id: str,
    elements: list[dict[str, object]],
    kind: str,
    patch_path: str,
) -> dict[str, object]:
    element_index_match = _PATCH_ELEMENT_INDEX_PATTERN.search(patch_path)

    if element_index_match is not None:
        index = int(element_index_match.group(1))
        if index < 0 or index >= len(elements):
            raise ValueError(
                "unknown_target: "
                + f"path='{patch_path}' index={index} out of range for slide_id='{slide_id}'"
            )
        element = elements[index]
        if cast(str, element.get("kind", "")) != kind:
            raise ValueError(
                "unknown_target: "
                + f"path='{patch_path}' points to kind='{element.get('kind')}', expected kind='{kind}'"
            )
        return element

    for element in elements:
        if cast(str, element.get("kind", "")) == kind:
            return element

    raise ValueError(
        "unknown_target: " + f"slide_id='{slide_id}' has no element kind='{kind}'"
    )


def _apply_feedback_patch_to_slidespec(
    *, slidespec_path: Path, feedback_patch: FeedbackPatch
) -> tuple[dict[str, object], list[str]]:
    slidespec = validate_slidespec_file(slidespec_path)
    mutable_payload = cast(dict[str, object], slidespec.model_dump(mode="json"))
    slides = cast(list[dict[str, object]], mutable_payload["slides"])
    slide_index_by_id = {
        cast(str, slide["slide_id"]): index for index, slide in enumerate(slides)
    }

    targeted_slide_ids: set[str] = set()
    for patch in feedback_patch.patches:
        slide_index = slide_index_by_id.get(patch.slide_id)
        if slide_index is None:
            raise ValueError(f"unknown_target: slide_id='{patch.slide_id}' not found")

        targeted_slide_ids.add(patch.slide_id)
        target_slide = slides[slide_index]
        operation = patch.operation

        if operation == "replace_title":
            if "title" not in patch.path:
                raise ValueError(
                    "unknown_target: "
                    + f"path='{patch.path}' invalid for operation='replace_title'"
                )
            target_slide["title"] = _required_non_blank_string(
                value=patch.value,
                field_name="replace_title",
            )
            continue

        if operation == "set_layout_hint":
            if patch.value is None:
                target_slide["layout_hint"] = None
            else:
                target_slide["layout_hint"] = _required_non_blank_string(
                    value=patch.value,
                    field_name="set_layout_hint",
                )
            continue

        target_slide_elements = cast(list[dict[str, object]], target_slide["elements"])

        if operation == "replace_body":
            target_element = _resolve_target_element(
                slide_id=patch.slide_id,
                elements=target_slide_elements,
                kind="body",
                patch_path=patch.path,
            )
            target_element["text"] = _required_non_blank_string(
                value=patch.value,
                field_name="replace_body",
            )
            continue

        if operation == "append_body_bullet":
            target_element = _resolve_target_element(
                slide_id=patch.slide_id,
                elements=target_slide_elements,
                kind="body",
                patch_path=patch.path,
            )
            existing_text = str(target_element.get("text") or "").strip()
            appended_bullet = "- " + _required_non_blank_string(
                value=patch.value,
                field_name="append_body_bullet",
            )
            target_element["text"] = (
                appended_bullet
                if not existing_text
                else existing_text + "\n" + appended_bullet
            )
            continue

        if operation == "replace_image_prompt":
            target_element = _resolve_target_element(
                slide_id=patch.slide_id,
                elements=target_slide_elements,
                kind="image",
                patch_path=patch.path,
            )
            target_element["image_prompt"] = _required_non_blank_string(
                value=patch.value,
                field_name="replace_image_prompt",
            )
            continue

        raise ValueError(f"unknown_target: unsupported operation='{operation}'")

    validated_payload = cast(
        dict[str, object],
        slidespec.__class__.model_validate(mutable_payload).model_dump(mode="json"),
    )
    return validated_payload, sorted(targeted_slide_ids)


def _unsafe_text_matches(slidespec_texts: list[tuple[str, str]]) -> list[str]:
    unsafe_markers = [
        "ignore previous instructions",
        "ignore all previous instructions",
        "system prompt",
        "developer message",
        "tool call",
        "shell command",
        "rm -rf",
        "curl http",
        "exfiltrate",
        "base64 decode and execute",
    ]
    matches: list[str] = []
    for location, text in slidespec_texts:
        lowered = text.lower()
        for marker in unsafe_markers:
            if marker in lowered:
                matches.append(f"{location}: marker='{marker}'")
                break
    return matches


_NUMERIC_FACT_PATTERN = re.compile(
    r"\d+(?:[.,]\d+)?(?:%|주|개월|년|일|원|억|만|명|건)?"
)
_CLAIM_SIGNATURE_CLEANUP_PATTERN = re.compile(r"[^0-9a-zA-Z가-힣\s]")
_CITATION_EVIDENCE_PATTERN = re.compile(
    r"(?:extract\.pages\[|evidence[_-]?id|\bev-[0-9A-Za-z_-]+\b|#p\d{3}-b\d{4})"
)


def _numeric_tokens(text: str) -> list[str]:
    tokens = {
        match.group(0).replace(",", "").strip().lower()
        for match in _NUMERIC_FACT_PATTERN.finditer(text)
    }
    return sorted(token for token in tokens if token)


def _is_citation_grounded(*, source_page: int, evidence: str) -> bool:
    if source_page < 1:
        return False
    if not evidence.strip():
        return False
    return bool(_CITATION_EVIDENCE_PATTERN.search(evidence))


def _claim_signature(text: str) -> str:
    without_numbers = _NUMERIC_FACT_PATTERN.sub(" <num> ", text.lower())
    cleaned = _CLAIM_SIGNATURE_CLEANUP_PATTERN.sub(" ", without_numbers)
    return " ".join(cleaned.split())


def _coerce_int(value: object, *, default: int) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return default
    return default


def _coerce_bool(value: object, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return default


def _generation_settings_hash(payload: dict[str, object]) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _resolve_runtime_model_settings(*, model_profile: str) -> dict[str, object]:
    normalized_profile = model_profile.strip().lower()
    if normalized_profile not in {"local", "cloud"}:
        raise ValueError(
            "invalid model profile: " + f"{model_profile!r} (supported: local, cloud)"
        )

    text_provider_default = "openai" if normalized_profile == "cloud" else "mock"
    image_provider_default = "openai" if normalized_profile == "cloud" else "mock"
    text_model_default = (
        "gpt-4.1-mini" if normalized_profile == "cloud" else "text-model-v1"
    )
    image_model_default = (
        "gpt-image-1" if normalized_profile == "cloud" else "image-model-v1"
    )

    text_provider = (
        os.getenv("PPTX_AGENT_TEXT_API_PROVIDER", text_provider_default).strip().lower()
    )
    if not text_provider:
        text_provider = text_provider_default

    image_provider = (
        os.getenv("PPTX_AGENT_IMAGE_API_PROVIDER", image_provider_default)
        .strip()
        .lower()
    )
    if not image_provider:
        image_provider = image_provider_default

    text_model = os.getenv("PPTX_AGENT_TEXT_MODEL", text_model_default).strip()
    if not text_model:
        text_model = text_model_default

    image_model = os.getenv("PPTX_AGENT_IMAGE_MODEL", image_model_default).strip()
    if not image_model:
        image_model = image_model_default

    if normalized_profile == "cloud":
        missing_or_invalid: list[str] = []
        if text_provider != "openai":
            missing_or_invalid.append(
                "PPTX_AGENT_TEXT_API_PROVIDER must be 'openai' for model-profile=cloud"
            )
        if image_provider != "openai":
            missing_or_invalid.append(
                "PPTX_AGENT_IMAGE_API_PROVIDER must be 'openai' for model-profile=cloud"
            )
        if not os.getenv("OPENAI_API_KEY", "").strip():
            missing_or_invalid.append(
                "OPENAI_API_KEY is required for model-profile=cloud"
            )

        if missing_or_invalid:
            raise ValueError(
                "cloud profile credential/config check failed: "
                + "; ".join(missing_or_invalid)
            )

    settings_payload: dict[str, object] = {
        "model_profile": normalized_profile,
        "language": "ko-KR",
        "text_provider": text_provider,
        "text_model": text_model,
        "image_provider": image_provider,
        "image_model": image_model,
    }
    settings_payload["generation_settings_hash"] = _generation_settings_hash(
        settings_payload
    )
    return settings_payload


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


def _read_manifest_failure_reason(run_manifest_path: Path) -> str | None:
    if not run_manifest_path.exists():
        return None
    payload = cast(
        dict[str, object],
        json.loads(run_manifest_path.read_text(encoding="utf-8")),
    )
    status = str(payload.get("status", "unknown"))
    reason_code = payload.get("reason_code")
    reason = payload.get("reason")
    if reason_code is not None:
        return f"{status}:{reason_code}"
    if reason is not None:
        return f"{status}:{reason}"
    failures = payload.get("failures")
    if isinstance(failures, list) and failures:
        first_failure = failures[0]
        if isinstance(first_failure, str):
            return f"{status}:{first_failure}"
    return status


def _default_image_generation_payload(
    *, image_provider: str | None = None, image_model: str | None = None
) -> dict[str, object]:
    return {
        "requested": 0,
        "succeeded": 0,
        "failed": 0,
        "image_provider": image_provider,
        "image_model": image_model,
    }


def _read_run_manifest_image_metadata(
    run_manifest_path: Path,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    if not run_manifest_path.exists():
        return _default_image_generation_payload(), []
    payload = cast(
        dict[str, object],
        json.loads(run_manifest_path.read_text(encoding="utf-8")),
    )
    image_generation_payload = payload.get("image_generation")
    image_generation: dict[str, object]
    if isinstance(image_generation_payload, dict):
        image_generation = {
            "requested": _coerce_int(
                image_generation_payload.get("requested"), default=0
            ),
            "succeeded": _coerce_int(
                image_generation_payload.get("succeeded"), default=0
            ),
            "failed": _coerce_int(image_generation_payload.get("failed"), default=0),
            "image_provider": (
                str(image_generation_payload.get("image_provider")).strip().lower()
                if isinstance(image_generation_payload.get("image_provider"), str)
                and str(image_generation_payload.get("image_provider")).strip()
                else None
            ),
            "image_model": (
                str(image_generation_payload.get("image_model")).strip()
                if isinstance(image_generation_payload.get("image_model"), str)
                and str(image_generation_payload.get("image_model")).strip()
                else None
            ),
        }
    else:
        image_generation = _default_image_generation_payload()

    traces_raw = payload.get("image_traces")
    image_traces: list[dict[str, object]] = []
    if isinstance(traces_raw, list):
        for trace in traces_raw:
            if isinstance(trace, dict):
                image_traces.append(trace)
    return image_generation, image_traces


def _rewrite_image_trace_paths(
    *,
    image_traces: list[dict[str, object]],
    old_images_dir: Path,
    new_images_dir: Path,
) -> list[dict[str, object]]:
    old_rel = old_images_dir.as_posix()
    new_rel = new_images_dir.as_posix()
    old_abs = str(old_images_dir.resolve())
    new_abs = str(new_images_dir.resolve())
    normalized_traces: list[dict[str, object]] = []

    for trace in image_traces:
        normalized_trace = dict(trace)
        image_path = normalized_trace.get("image_path")
        if isinstance(image_path, str):
            if image_path.startswith(old_rel):
                normalized_trace["image_path"] = new_rel + image_path[len(old_rel) :]
            elif image_path.startswith(old_abs):
                normalized_trace["image_path"] = new_abs + image_path[len(old_abs) :]
        normalized_traces.append(normalized_trace)

    return normalized_traces


def _build_run_manifest_paths(
    *,
    extract_path: Path,
    normalized_path: Path,
    deck_outline_path: Path,
    slidespec_path: Path,
    output_path: Path,
    qa_report_path: Path,
    hook_summary_path: Path,
    preflight_gate_path: Path,
    postrender_gate_path: Path,
    run_dir: Path,
    hook_error_path: Path | None = None,
) -> dict[str, str]:
    paths: dict[str, str] = {
        "extract": str(extract_path),
        "normalized": str(normalized_path),
        "deck_outline": str(deck_outline_path),
        "slidespec": str(slidespec_path),
        "output_pptx": str(output_path),
        "qa_report": str(qa_report_path),
        "hook_summary": str(hook_summary_path),
        "qa_preflight": str(preflight_gate_path),
        "qa_postrender": str(postrender_gate_path),
        "run_dir": str(run_dir),
    }
    if hook_error_path is not None:
        paths["hook_error"] = str(hook_error_path)
    return paths


def _write_failed_run_manifest(
    *,
    manifest_path: Path,
    run_id: str,
    status: str,
    reason_code: str,
    reason: str,
    paths: dict[str, str],
    failures: list[str] | None = None,
    image_generation: dict[str, object] | None = None,
    image_traces: list[dict[str, object]] | None = None,
    runtime: dict[str, object] | None = None,
) -> None:
    payload: dict[str, object] = {
        "schema": "pipeline.run.manifest.v1",
        "run_id": run_id,
        "status": status,
        "reason_code": reason_code,
        "reason": reason,
        "paths": paths,
        "image_generation": (
            image_generation
            if image_generation is not None
            else _default_image_generation_payload()
        ),
        "image_traces": image_traces if image_traces is not None else [],
    }
    if runtime is not None:
        payload["runtime"] = runtime
    if failures:
        payload["failures"] = failures
    _write_json_file(manifest_path, payload)


def _build_qa_gate_report(
    *,
    run_id: str,
    slidespec_path: Path,
    qa_report_path: Path | None,
    hook_summary_path: Path | None,
) -> tuple[QAGateReport, int]:
    slidespec = validate_slidespec_file(slidespec_path)
    all_elements = [element for slide in slidespec.slides for element in slide.elements]

    provenance_covered = 0
    for element in all_elements:
        if (
            element.source_page >= 1
            and bool(element.evidence.strip())
            and 0.0 <= element.confidence <= 1.0
        ):
            provenance_covered += 1

    provenance_total = len(all_elements)
    provenance_ratio = (
        round(float(provenance_covered) / float(provenance_total), 4)
        if provenance_total > 0
        else 1.0
    )

    text_samples = [
        (f"slides[{index}].title", slide.title)
        for index, slide in enumerate(slidespec.slides)
    ]
    citation_total_claim_elements = 0
    citation_covered_claim_elements = 0
    missing_citation_failures: list[str] = []
    uncited_numeric_fact_failures: list[str] = []
    contradiction_candidates: dict[str, dict[str, list[str]]] = {}
    for slide_index, slide in enumerate(slidespec.slides):
        for element_index, element in enumerate(slide.elements):
            if element.text:
                claim_location = f"slides[{slide_index}].elements[{element_index}].text"
                text_samples.append(
                    (
                        claim_location,
                        element.text,
                    )
                )
                if element.kind in {"title", "body", "table"}:
                    citation_total_claim_elements += 1
                    grounded = _is_citation_grounded(
                        source_page=element.source_page,
                        evidence=element.evidence,
                    )
                    if grounded:
                        citation_covered_claim_elements += 1
                    else:
                        missing_citation_failures.append(
                            "missing_citation: "
                            + f"{claim_location} evidence='{element.evidence}'"
                        )

                    numeric_tokens = _numeric_tokens(element.text)
                    if numeric_tokens:
                        if not grounded:
                            uncited_numeric_fact_failures.append(
                                "uncited_numeric_fact: "
                                + f"{claim_location} tokens={numeric_tokens}"
                            )

                        signature = _claim_signature(element.text)
                        if signature:
                            token_key = "|".join(numeric_tokens)
                            signature_map = contradiction_candidates.setdefault(
                                signature,
                                {},
                            )
                            signature_map.setdefault(token_key, []).append(
                                claim_location
                            )
            text_samples.append(
                (
                    f"slides[{slide_index}].elements[{element_index}].evidence",
                    element.evidence,
                )
            )

    contradiction_failures: list[str] = []
    for signature in sorted(contradiction_candidates.keys()):
        signature_map = contradiction_candidates[signature]
        if len(signature_map) <= 1:
            continue
        token_sets = sorted(signature_map.keys())
        locations = sorted(
            location for bucket in signature_map.values() for location in bucket
        )
        contradiction_failures.append(
            "contradiction_detected: "
            + f"signature='{signature}' token_sets={token_sets} locations={locations}"
        )

    unsafe_matches = _unsafe_text_matches(text_samples)
    citation_ratio = (
        round(
            float(citation_covered_claim_elements)
            / float(citation_total_claim_elements),
            4,
        )
        if citation_total_claim_elements > 0
        else 1.0
    )

    checks: dict[str, bool] = {
        "slidespec_valid": True,
        "provenance_coverage_complete": provenance_covered == provenance_total,
        "citation_coverage_complete": (
            citation_covered_claim_elements == citation_total_claim_elements
        ),
        "uncited_numeric_fact_absent": len(uncited_numeric_fact_failures) == 0,
        "contradiction_absent": len(contradiction_failures) == 0,
        "unsafe_text_absent": len(unsafe_matches) == 0,
    }

    critical_overflow_count = 0
    slide_count_matches = True
    if qa_report_path is not None:
        qa_payload = cast(
            dict[str, object],
            json.loads(qa_report_path.read_text(encoding="utf-8")),
        )
        critical_overflow_count = _coerce_int(
            qa_payload.get("critical_overflow_count", -1),
            default=-1,
        )
        slide_count_matches = bool(
            _coerce_int(qa_payload.get("slide_count_expected", -1), default=-1)
            == _coerce_int(qa_payload.get("slide_count_rendered", -2), default=-2)
        )
        checks["critical_overflow_zero"] = critical_overflow_count == 0
        checks["rendered_slide_count_matches"] = slide_count_matches

    if hook_summary_path is not None:
        hook_summary = read_qa_summary_file(hook_summary_path)
        checks["hook_summary_pass"] = hook_summary["status"] == "pass"

    failures = [name for name, passed in checks.items() if not passed]
    failures.extend(missing_citation_failures)
    failures.extend(uncited_numeric_fact_failures)
    failures.extend(contradiction_failures)
    failures.extend(unsafe_matches)

    report: QAGateReport = {
        "schema": "pipeline.qa.gate.v1",
        "run_id": run_id,
        "slidespec_path": str(slidespec_path),
        "qa_report_path": str(qa_report_path) if qa_report_path is not None else None,
        "hook_summary_path": (
            str(hook_summary_path) if hook_summary_path is not None else None
        ),
        "checks": checks,
        "metrics": {
            "critical_overflow_count": critical_overflow_count,
            "provenance_total_elements": provenance_total,
            "provenance_covered_elements": provenance_covered,
            "provenance_coverage_ratio": provenance_ratio,
            "citation_total_claim_elements": citation_total_claim_elements,
            "citation_covered_claim_elements": citation_covered_claim_elements,
            "citation_coverage_ratio": citation_ratio,
            "missing_citation_count": len(missing_citation_failures),
            "uncited_numeric_fact_count": len(uncited_numeric_fact_failures),
            "contradiction_count": len(contradiction_failures),
            "unsafe_text_match_count": len(unsafe_matches),
            "rendered_slide_count_match": 1 if slide_count_matches else 0,
        },
        "failures": failures,
        "status": "pass" if not failures else "fail",
    }

    return report, 0 if not failures else 1


def _cmd_validate_ir(args: argparse.Namespace) -> int:
    input_path = Path(cast(str, getattr(args, "input_path")))
    try:
        _ = validate_slidespec_file(input_path)
    except FileNotFoundError:
        print(f"Validation failed: file not found: {input_path}")
        return 1
    except Exception as exc:
        if exc.__class__.__name__ != "ValidationError":
            raise
        errors = getattr(exc, "errors", None)
        if not callable(errors):
            raise
        validation_errors = errors()
        if not isinstance(validation_errors, list):
            raise
        print(f"Validation failed for {input_path}:")
        for err in validation_errors:
            location = ".".join(str(part) for part in err["loc"])
            print(f"- {location}: {err['msg']}")
        return 1

    print(f"SlideSpec v1 valid: {input_path} (schema_version={SCHEMA_VERSION_V1})")
    return 0


def _cmd_validate_outline(args: argparse.Namespace) -> int:
    input_path = Path(cast(str, getattr(args, "input_path")))
    try:
        payload = input_path.read_text(encoding="utf-8")
        _ = DeckOutline.model_validate_json(payload)
    except FileNotFoundError:
        print(f"Validation failed: file not found: {input_path}")
        return 1
    except Exception as exc:
        if exc.__class__.__name__ != "ValidationError":
            raise
        errors = getattr(exc, "errors", None)
        if not callable(errors):
            raise
        validation_errors = errors()
        if not isinstance(validation_errors, list):
            raise
        print(f"Validation failed for {input_path}:")
        for err in validation_errors:
            location = ".".join(str(part) for part in err["loc"])
            print(f"- {location}: {err['msg']}")
        return 1

    print(
        "DeckOutline v1 valid: "
        + f"{input_path} (schema_version={DECK_OUTLINE_SCHEMA_VERSION_V1})"
    )
    return 0


def _cmd_extract(args: argparse.Namespace) -> int:
    input_path = Path(cast(str, getattr(args, "input_path")))
    output_path = Path(cast(str, getattr(args, "output_path")))

    if not input_path.exists():
        print(f"Extraction failed: file not found: {input_path}")
        return 1

    payload = extract_document(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _ = output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    status = str(payload.get("status", "unknown"))
    if status == "ok":
        pages = payload.get("pages", [])
        block_count = sum(len(page.get("blocks", [])) for page in pages)
        print(
            f"Extraction complete: {input_path} -> {output_path} ({len(pages)} pages, {block_count} blocks)"
        )
        return 0

    reason_code = payload.get("reason_code", "unknown")
    reason = payload.get("reason", "unsupported")
    print(f"Extraction unsupported: {input_path} ({reason_code}) - {reason}")
    return 2


def _cmd_normalize(args: argparse.Namespace) -> int:
    input_path = Path(cast(str, getattr(args, "input_path")))
    output_path = Path(cast(str, getattr(args, "output_path")))

    if not input_path.exists():
        print(f"Normalization failed: file not found: {input_path}")
        return 1

    payload_json = input_path.read_text(encoding="utf-8")

    try:
        normalized = normalize_extract_payload_json(payload_json)
    except Exception as exc:
        if exc.__class__.__name__ != "ValidationError":
            raise
        errors = getattr(exc, "errors", None)
        if not callable(errors):
            raise
        validation_errors = errors()
        if not isinstance(validation_errors, list):
            raise
        print(f"Normalization failed for {input_path}:")
        for err in validation_errors:
            location = ".".join(str(part) for part in err["loc"])
            print(f"- {location}: {err['msg']}")
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    _ = output_path.write_text(
        normalized.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )

    total_elements = sum(len(page.elements) for page in normalized.pages)
    summary = (
        f"Normalization complete: {input_path} -> {output_path} "
        f"({len(normalized.pages)} pages, {total_elements} elements, "
        f"unsupported={normalized.unsupported_report.has_unsupported})"
    )
    print(summary)
    return 0 if normalized.status == "ok" else 2


def _cmd_plan(args: argparse.Namespace) -> int:
    input_path = Path(cast(str, getattr(args, "input_path")))
    output_path = Path(cast(str, getattr(args, "output_path")))

    if not input_path.exists():
        print(f"Planning failed: file not found: {input_path}")
        return 1

    payload_json = input_path.read_text(encoding="utf-8")

    try:
        slidespec = plan_normalized_payload_json(payload_json)
    except ValueError as exc:
        print(f"Planning failed for {input_path}:")
        print(f"- {exc}")
        return 1
    except Exception as exc:
        if exc.__class__.__name__ != "ValidationError":
            raise
        errors = getattr(exc, "errors", None)
        if not callable(errors):
            raise
        validation_errors = errors()
        if not isinstance(validation_errors, list):
            raise
        print(f"Planning failed for {input_path}:")
        for err in validation_errors:
            location = ".".join(str(part) for part in err["loc"])
            print(f"- {location}: {err['msg']}")
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    _ = output_path.write_text(
        slidespec.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )

    total_elements = sum(len(slide.elements) for slide in slidespec.slides)
    summary = (
        f"Planning complete: {input_path} -> {output_path} "
        + f"({len(slidespec.slides)} slides, {total_elements} elements, "
        + f"schema={SCHEMA_VERSION_V1})"
    )
    print(summary)
    return 0


def _cmd_outline(args: argparse.Namespace) -> int:
    input_path = Path(cast(str, getattr(args, "input_path")))
    output_path = Path(cast(str, getattr(args, "output_path")))

    if not input_path.exists():
        print(f"Outline planning failed: file not found: {input_path}")
        return 1

    payload_json = input_path.read_text(encoding="utf-8")

    try:
        outline = build_deck_outline_payload_json(payload_json)
    except ValueError as exc:
        print(f"Outline planning failed for {input_path}:")
        print(f"- {exc}")
        return 1
    except Exception as exc:
        if exc.__class__.__name__ != "ValidationError":
            raise
        errors = getattr(exc, "errors", None)
        if not callable(errors):
            raise
        validation_errors = errors()
        if not isinstance(validation_errors, list):
            raise
        print(f"Outline planning failed for {input_path}:")
        for err in validation_errors:
            location = ".".join(str(part) for part in err["loc"])
            print(f"- {location}: {err['msg']}")
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    _ = output_path.write_text(
        outline.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )

    summary = (
        f"Outline planning complete: {input_path} -> {output_path} "
        + f"({len(outline.sections)} sections, {outline.target_slide_count} slides, "
        + f"schema={outline.schema_version})"
    )
    print(summary)
    return 0


def _cmd_outline_to_slidespec(args: argparse.Namespace) -> int:
    outline_path = Path(cast(str, getattr(args, "outline_path")))
    normalized_path = Path(cast(str, getattr(args, "normalized_path")))
    output_path = Path(cast(str, getattr(args, "output_path")))

    if not outline_path.exists():
        print(f"Outline conversion failed: file not found: {outline_path}")
        return 1
    if not normalized_path.exists():
        print(f"Outline conversion failed: file not found: {normalized_path}")
        return 1

    outline_payload_json = outline_path.read_text(encoding="utf-8")
    normalized_payload_json = normalized_path.read_text(encoding="utf-8")

    try:
        outline_payload = cast(dict[str, object], json.loads(outline_payload_json))
        normalized_payload = cast(
            dict[str, object],
            json.loads(normalized_payload_json),
        )
        slidespec = outline_to_slidespec_payload(
            outline_payload=outline_payload,
            normalized_payload=normalized_payload,
        )
    except ValueError as exc:
        print(f"Outline conversion failed for {outline_path}:")
        print(f"- {exc}")
        return 1
    except Exception as exc:
        if exc.__class__.__name__ != "ValidationError":
            raise
        errors = getattr(exc, "errors", None)
        if not callable(errors):
            raise
        validation_errors = errors()
        if not isinstance(validation_errors, list):
            raise
        print(f"Outline conversion failed for {outline_path}:")
        for err in validation_errors:
            location = ".".join(str(part) for part in err["loc"])
            print(f"- {location}: {err['msg']}")
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    _ = output_path.write_text(
        slidespec.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )

    total_elements = sum(len(slide.elements) for slide in slidespec.slides)
    print(
        f"Outline conversion complete: {outline_path} -> {output_path} "
        + f"({len(slidespec.slides)} slides, {total_elements} elements, "
        + f"schema={SCHEMA_VERSION_V1})"
    )
    return 0


def _cmd_evidence_graph(args: argparse.Namespace) -> int:
    input_path = Path(cast(str, getattr(args, "input_path")))
    output_path = Path(cast(str, getattr(args, "output_path")))

    if not input_path.exists():
        print(f"Evidence graph build failed: file not found: {input_path}")
        return 1

    payload_json = input_path.read_text(encoding="utf-8")

    try:
        evidence_graph = build_evidence_graph_payload_json(payload_json)
    except ValueError as exc:
        print(f"Evidence graph build failed for {input_path}:")
        print(f"- {exc}")
        return 1
    except Exception as exc:
        if exc.__class__.__name__ != "ValidationError":
            raise
        errors = getattr(exc, "errors", None)
        if not callable(errors):
            raise
        validation_errors = errors()
        if not isinstance(validation_errors, list):
            raise
        print(f"Evidence graph build failed for {input_path}:")
        for err in validation_errors:
            location = ".".join(str(part) for part in err["loc"])
            print(f"- {location}: {err['msg']}")
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    _ = output_path.write_text(
        evidence_graph.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )

    summary = (
        f"Evidence graph build complete: {input_path} -> {output_path} "
        + f"({len(evidence_graph.evidence_nodes)} evidence nodes, "
        + f"{len(evidence_graph.claims)} claims, {len(evidence_graph.links)} links, "
        + f"schema={evidence_graph.schema_version})"
    )
    print(summary)
    return 0


def _cmd_render(args: argparse.Namespace) -> int:
    input_path = Path(cast(str, getattr(args, "input_path")))
    output_path = Path(cast(str, getattr(args, "output_path")))
    run_id = compute_run_id(input_path, output_path)

    if not input_path.exists():
        print(f"Render failed: file not found: {input_path}")
        return 1

    try:
        slidespec = pre_render_contract_gate(input_path)
        qa_report = render_slidespec_to_pptx(slidespec, output_path)
        qa_path = output_path.with_suffix(output_path.suffix + ".qa.json")
        qa_path.parent.mkdir(parents=True, exist_ok=True)
        _ = qa_path.write_text(
            json.dumps(qa_report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        _ = post_render_qa_gate(
            run_id=run_id,
            input_path=input_path,
            output_path=output_path,
            qa_report_path=qa_path,
            qa_report=qa_report,
        )
    except UnsupportedLayoutHintError as exc:
        error_path = write_on_error_report(
            run_id=run_id,
            input_path=input_path,
            output_path=output_path,
            phase="render",
            reason="unsupported_layout",
            error=exc,
            details=[str(exc)],
        )
        print(f"Render failed: {exc}")
        print(f"Render hook error report written: {error_path}")
        return 2
    except ImageGenerationFailedError as exc:
        error_path = write_on_error_report(
            run_id=run_id,
            input_path=input_path,
            output_path=output_path,
            phase="render",
            reason="image_generation_failed",
            error=exc,
            details=[str(exc)],
        )
        print(f"Render failed: {exc}")
        print(f"Render hook error report written: {error_path}")
        return 1
    except HookPolicyError as exc:
        error_path = write_on_error_report(
            run_id=run_id,
            input_path=input_path,
            output_path=output_path,
            phase=exc.phase,
            reason=exc.reason,
            error=exc,
            details=exc.details,
        )
        print(f"Render failed: hook policy violation [{exc.phase}] {exc.reason}")
        for detail in exc.details:
            print(f"- {detail}")
        print(f"Render hook error report written: {error_path}")
        return 1
    except Exception as exc:
        error_path = write_on_error_report(
            run_id=run_id,
            input_path=input_path,
            output_path=output_path,
            phase="render",
            reason="unexpected_exception",
            error=exc,
            details=[str(exc)],
        )
        print(f"Render failed: unexpected exception: {exc}")
        print(f"Render hook error report written: {error_path}")
        return 1

    print(json.dumps(qa_report, sort_keys=True))
    print(f"Render QA report written: {qa_path}")
    return 0


def _cmd_qa(args: argparse.Namespace) -> int:
    slidespec_path = Path(cast(str, getattr(args, "slidespec_path")))
    qa_report_raw = cast(str | None, getattr(args, "qa_report_path", None))
    hook_summary_raw = cast(str | None, getattr(args, "hook_summary_path", None))
    output_path = Path(cast(str, getattr(args, "output_path")))
    run_id = cast(str | None, getattr(args, "run_id", None))

    qa_report_path = Path(qa_report_raw) if qa_report_raw else None
    hook_summary_path = Path(hook_summary_raw) if hook_summary_raw else None

    if not slidespec_path.exists():
        print(f"QA gate failed: slidespec file not found: {slidespec_path}")
        return 1
    if qa_report_path is not None and not qa_report_path.exists():
        print(f"QA gate failed: qa report file not found: {qa_report_path}")
        return 1
    if hook_summary_path is not None and not hook_summary_path.exists():
        print(f"QA gate failed: hook summary file not found: {hook_summary_path}")
        return 1

    effective_run_id = run_id if run_id else _deterministic_run_id(slidespec_path)

    try:
        report, exit_code = _build_qa_gate_report(
            run_id=effective_run_id,
            slidespec_path=slidespec_path,
            qa_report_path=qa_report_path,
            hook_summary_path=hook_summary_path,
        )
    except Exception as exc:
        print(f"QA gate failed: {exc}")
        return 1

    _write_json_file(output_path, report)
    print(json.dumps(report, sort_keys=True))
    print(f"QA gate report written: {output_path}")
    return exit_code


def _cmd_run_local(args: argparse.Namespace) -> int:
    input_path = Path(cast(str, getattr(args, "input_path")))
    artifacts_root = Path(cast(str, getattr(args, "artifacts_root")))
    explicit_run_id = cast(str | None, getattr(args, "run_id", None))
    model_profile = cast(str, getattr(args, "model_profile", "local"))
    run_id = explicit_run_id if explicit_run_id else _deterministic_run_id(input_path)
    run_dir = artifacts_root / run_id

    if not input_path.exists():
        print(f"Run failed: input file not found: {input_path}")
        return 1

    extract_path = run_dir / "extract.json"
    normalized_path = run_dir / "normalized.json"
    deck_outline_path = run_dir / "deck_outline.json"
    slidespec_path = run_dir / "slidespec.json"
    output_path = run_dir / "output.pptx"
    qa_report_path = run_dir / "output.pptx.qa.json"
    hook_summary_path = run_dir / "output.pptx.hooks.qa.json"
    hook_error_path = run_dir / "output.pptx.hooks.error.json"
    image_assets_dir = output_path.with_suffix(output_path.suffix + ".images")
    preflight_gate_path = run_dir / "qa.preflight.json"
    postrender_gate_path = run_dir / "qa.postrender.json"
    manifest_path = run_dir / "run_manifest.json"

    try:
        runtime_settings = _resolve_runtime_model_settings(model_profile=model_profile)
    except ValueError as exc:
        _write_failed_run_manifest(
            manifest_path=manifest_path,
            run_id=run_id,
            status="failed_profile",
            reason_code="missing_credentials",
            reason=str(exc),
            paths={
                "run_dir": str(run_dir),
            },
            image_generation=_default_image_generation_payload(),
            runtime={
                "model_profile": model_profile.strip().lower(),
                "language": "ko-KR",
            },
        )
        print(f"Run failed: {exc}")
        print(f"Run manifest written: {manifest_path}")
        return 1

    image_generation_payload: dict[str, object] = _default_image_generation_payload(
        image_provider=cast(str | None, runtime_settings.get("image_provider")),
        image_model=cast(str | None, runtime_settings.get("image_model")),
    )

    run_dir.mkdir(parents=True, exist_ok=True)
    for stale_path in [
        output_path,
        qa_report_path,
        hook_summary_path,
        hook_error_path,
        preflight_gate_path,
        postrender_gate_path,
        manifest_path,
        deck_outline_path,
    ]:
        _unlink_if_exists(stale_path)
    if image_assets_dir.exists() and image_assets_dir.is_dir():
        shutil.rmtree(image_assets_dir)

    extract_payload = extract_document(input_path)
    _write_json_file(extract_path, extract_payload)
    if str(extract_payload.get("status", "unknown")) != "ok":
        _write_json_file(
            manifest_path,
            {
                "schema": "pipeline.run.manifest.v1",
                "run_id": run_id,
                "status": "unsupported",
                "paths": {
                    "extract": str(extract_path),
                    "run_dir": str(run_dir),
                },
                "reason_code": extract_payload.get("reason_code"),
                "reason": extract_payload.get("reason"),
                "runtime": runtime_settings,
                "image_generation": image_generation_payload,
                "image_traces": [],
            },
        )
        print(
            "Run unsupported: "
            + f"{input_path} ({extract_payload.get('reason_code', 'unknown')})"
        )
        print(f"Run manifest written: {manifest_path}")
        return 2

    normalized = normalize_extract_payload_json(
        json.dumps(extract_payload, sort_keys=True)
    )
    _ = normalized_path.write_text(
        normalized.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )

    deck_outline = build_deck_outline_payload_json(normalized.model_dump_json())
    _ = deck_outline_path.write_text(
        deck_outline.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    slidespec = outline_to_slidespec_payload(
        outline_payload=deck_outline.model_dump(mode="json"),
        normalized_payload=normalized.model_dump(mode="json"),
    )
    _ = slidespec_path.write_text(
        slidespec.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    _ = validate_slidespec_file(slidespec_path)

    preflight_report, preflight_exit = _build_qa_gate_report(
        run_id=run_id,
        slidespec_path=slidespec_path,
        qa_report_path=None,
        hook_summary_path=None,
    )
    _write_json_file(preflight_gate_path, preflight_report)
    if preflight_exit != 0:
        _write_failed_run_manifest(
            manifest_path=manifest_path,
            run_id=run_id,
            status="failed_preflight",
            reason_code="preflight_qa_failed",
            reason="preflight qa gate failed",
            paths={
                "extract": str(extract_path),
                "normalized": str(normalized_path),
                "deck_outline": str(deck_outline_path),
                "slidespec": str(slidespec_path),
                "qa_preflight": str(preflight_gate_path),
                "run_dir": str(run_dir),
            },
            failures=preflight_report["failures"],
            image_generation=image_generation_payload,
            runtime=runtime_settings,
        )
        print("Run blocked by preflight QA gate.")
        print(f"Run manifest written: {manifest_path}")
        return 1

    render_run_id = compute_run_id(slidespec_path, output_path)
    post_render_hook_error: HookPolicyError | None = None
    post_render_error_path: Path | None = None
    image_traces_payload: list[dict[str, object]] = []
    run_manifest_paths = _build_run_manifest_paths(
        extract_path=extract_path,
        normalized_path=normalized_path,
        deck_outline_path=deck_outline_path,
        slidespec_path=slidespec_path,
        output_path=output_path,
        qa_report_path=qa_report_path,
        hook_summary_path=hook_summary_path,
        preflight_gate_path=preflight_gate_path,
        postrender_gate_path=postrender_gate_path,
        run_dir=run_dir,
    )
    try:
        validated_slidespec = pre_render_contract_gate(slidespec_path)
        qa_report = render_slidespec_to_pptx(validated_slidespec, output_path)
        _write_json_file(qa_report_path, qa_report)
        image_generation_raw = qa_report["image_generation"]
        image_generation_payload = cast(
            dict[str, object],
            {
                "requested": _coerce_int(
                    image_generation_raw.get("requested"), default=0
                ),
                "succeeded": _coerce_int(
                    image_generation_raw.get("succeeded"), default=0
                ),
                "failed": _coerce_int(image_generation_raw.get("failed"), default=0),
                "image_provider": runtime_settings["image_provider"],
                "image_model": (
                    str(image_generation_raw.get("image_model")).strip()
                    if isinstance(image_generation_raw.get("image_model"), str)
                    and str(image_generation_raw.get("image_model")).strip()
                    else None
                ),
            },
        )
        traces_raw = qa_report["image_traces"]
        image_traces_payload = cast(
            list[dict[str, object]],
            [trace for trace in traces_raw],
        )
        try:
            _ = post_render_qa_gate(
                run_id=render_run_id,
                input_path=slidespec_path,
                output_path=output_path,
                qa_report_path=qa_report_path,
                qa_report=qa_report,
            )
        except HookPolicyError as exc:
            if exc.phase == "post_render" and exc.reason == "qa_gate_failed":
                post_render_hook_error = exc
                post_render_error_path = write_on_error_report(
                    run_id=render_run_id,
                    input_path=slidespec_path,
                    output_path=output_path,
                    phase=exc.phase,
                    reason=exc.reason,
                    error=exc,
                    details=exc.details,
                )
            else:
                raise
    except UnsupportedLayoutHintError as exc:
        error_path = write_on_error_report(
            run_id=render_run_id,
            input_path=slidespec_path,
            output_path=output_path,
            phase="render",
            reason="unsupported_layout",
            error=exc,
            details=[str(exc)],
        )
        _write_failed_run_manifest(
            manifest_path=manifest_path,
            run_id=run_id,
            status="failed_render",
            reason_code="unsupported_layout",
            reason=str(exc),
            paths={**run_manifest_paths, "hook_error": str(error_path)},
            image_generation=image_generation_payload,
            image_traces=image_traces_payload,
            runtime=runtime_settings,
        )
        print(f"Run failed: {exc}")
        print(f"Run hook error report written: {error_path}")
        print(f"Run manifest written: {manifest_path}")
        return 2
    except ImageGenerationFailedError as exc:
        error_path = write_on_error_report(
            run_id=render_run_id,
            input_path=slidespec_path,
            output_path=output_path,
            phase="render",
            reason="image_generation_failed",
            error=exc,
            details=[str(exc)],
        )
        _write_failed_run_manifest(
            manifest_path=manifest_path,
            run_id=run_id,
            status="failed_render",
            reason_code="image_generation_failed",
            reason=str(exc),
            paths={**run_manifest_paths, "hook_error": str(error_path)},
            image_generation=image_generation_payload,
            image_traces=image_traces_payload,
            runtime=runtime_settings,
        )
        print(f"Run failed: {exc}")
        print(f"Run hook error report written: {error_path}")
        print(f"Run manifest written: {manifest_path}")
        return 1
    except HookPolicyError as exc:
        error_path = write_on_error_report(
            run_id=render_run_id,
            input_path=slidespec_path,
            output_path=output_path,
            phase=exc.phase,
            reason=exc.reason,
            error=exc,
            details=exc.details,
        )
        _write_failed_run_manifest(
            manifest_path=manifest_path,
            run_id=run_id,
            status="failed_render",
            reason_code=exc.reason,
            reason=f"hook policy violation [{exc.phase}] {exc.reason}",
            paths={**run_manifest_paths, "hook_error": str(error_path)},
            failures=exc.details,
            image_generation=image_generation_payload,
            image_traces=image_traces_payload,
            runtime=runtime_settings,
        )
        print(f"Run failed: hook policy violation [{exc.phase}] {exc.reason}")
        for detail in exc.details:
            print(f"- {detail}")
        print(f"Run hook error report written: {error_path}")
        print(f"Run manifest written: {manifest_path}")
        return 1
    except Exception as exc:
        error_path = write_on_error_report(
            run_id=render_run_id,
            input_path=slidespec_path,
            output_path=output_path,
            phase="render",
            reason="unexpected_exception",
            error=exc,
            details=[str(exc)],
        )
        _write_failed_run_manifest(
            manifest_path=manifest_path,
            run_id=run_id,
            status="failed_render",
            reason_code="unexpected_exception",
            reason=str(exc),
            paths={**run_manifest_paths, "hook_error": str(error_path)},
            image_generation=image_generation_payload,
            image_traces=image_traces_payload,
            runtime=runtime_settings,
        )
        print(f"Run failed: unexpected exception: {exc}")
        print(f"Run hook error report written: {error_path}")
        print(f"Run manifest written: {manifest_path}")
        return 1

    postrender_report, postrender_exit = _build_qa_gate_report(
        run_id=run_id,
        slidespec_path=slidespec_path,
        qa_report_path=qa_report_path,
        hook_summary_path=hook_summary_path,
    )
    _write_json_file(postrender_gate_path, postrender_report)

    manifest_payload: dict[str, object] = {
        "schema": "pipeline.run.manifest.v1",
        "run_id": run_id,
        "status": "pass" if postrender_exit == 0 else "failed_postrender",
        "paths": {
            "extract": str(extract_path),
            "normalized": str(normalized_path),
            "deck_outline": str(deck_outline_path),
            "slidespec": str(slidespec_path),
            "output_pptx": str(output_path),
            "qa_report": str(qa_report_path),
            "hook_summary": str(hook_summary_path),
            "qa_preflight": str(preflight_gate_path),
            "qa_postrender": str(postrender_gate_path),
            "run_dir": str(run_dir),
        },
        "render_run_id": render_run_id,
        "runtime": runtime_settings,
        "image_generation": image_generation_payload,
        "image_traces": image_traces_payload,
    }
    if post_render_error_path is not None:
        cast(dict[str, str], manifest_payload["paths"])["hook_error"] = str(
            post_render_error_path
        )
    if postrender_exit != 0:
        manifest_payload["reason_code"] = "postrender_qa_failed"
        manifest_payload["reason"] = "postrender qa gate failed"
        manifest_payload["failures"] = postrender_report["failures"]
    _write_json_file(manifest_path, manifest_payload)

    print(
        "Run complete: "
        + f"{input_path} -> {output_path} (run_id={run_id}, artifacts={run_dir})"
    )
    if post_render_hook_error is not None:
        print(
            "Run failed: hook policy violation "
            + f"[{post_render_hook_error.phase}] {post_render_hook_error.reason}"
        )
        for detail in post_render_hook_error.details:
            print(f"- {detail}")
        if post_render_error_path is not None:
            print(f"Run hook error report written: {post_render_error_path}")
    print(f"Run manifest written: {manifest_path}")
    return postrender_exit


def _cmd_run_folder(args: argparse.Namespace) -> int:
    input_dir = Path(cast(str, getattr(args, "input_dir")))
    output_dir = Path(cast(str, getattr(args, "output_dir")))
    artifacts_root = Path(cast(str, getattr(args, "artifacts_root")))
    model_profile = cast(str, getattr(args, "model_profile", "local"))
    continue_on_error = _coerce_bool(
        getattr(args, "continue_on_error", True),
        default=True,
    )

    if not input_dir.exists() or not input_dir.is_dir():
        print(f"Run failed: input directory not found: {input_dir}")
        return 1

    input_files = _sorted_input_files(input_dir)
    if not input_files:
        print(f"Run failed: no input files found in {input_dir}")
        return 1

    try:
        runtime_settings = _resolve_runtime_model_settings(model_profile=model_profile)
    except ValueError as exc:
        print(f"Run failed: {exc}")
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts_root.mkdir(parents=True, exist_ok=True)

    batch_id = _deterministic_batch_id(
        input_dir=input_dir,
        output_dir=output_dir,
        artifacts_root=artifacts_root,
        input_files=input_files,
    )
    batch_dir = artifacts_root / batch_id
    docs_root = batch_dir / "docs"
    document_registry_path = batch_dir / "document_registry.json"
    batch_manifest_path = batch_dir / "batch_manifest.json"
    docs_root.mkdir(parents=True, exist_ok=True)

    document_registry = build_document_registry(
        input_dir=input_dir,
        batch_id=batch_id,
        input_files=input_files,
    )
    _write_json_file(document_registry_path, document_registry)

    document_manifests: list[dict[str, object]] = []
    passed = 0
    failed = 0
    unsupported = 0

    for registry_entry in document_registry["documents"]:
        input_path = Path(registry_entry["input_file"])
        sha256_hex = registry_entry["sha256"]
        doc_id = registry_entry["doc_id"]
        run_dir = docs_root / doc_id
        output_pptx = output_dir / f"{doc_id}.pptx"
        _unlink_if_exists(output_pptx)

        doc_status = "fail"
        failure_reason: str | None = None
        image_generation_payload: dict[str, object] = (
            _default_image_generation_payload()
        )
        image_traces_payload: list[dict[str, object]] = []
        run_local_args = argparse.Namespace(
            input_path=str(input_path),
            artifacts_root=str(docs_root),
            run_id=doc_id,
            model_profile=model_profile,
        )
        try:
            exit_code = _cmd_run_local(run_local_args)
        except Exception as exc:
            exit_code = 1
            failure_reason = f"unexpected_exception:{exc.__class__.__name__}"
        run_output = run_dir / "output.pptx"
        run_manifest_path = run_dir / "run_manifest.json"
        (
            image_generation_payload,
            image_traces_payload,
        ) = _read_run_manifest_image_metadata(run_manifest_path)

        if exit_code == 0 and run_output.exists():
            _ = shutil.copy2(run_output, output_pptx)
            doc_status = "pass"
            passed += 1
        elif exit_code == 2:
            doc_status = "unsupported"
            failure_reason = _read_manifest_failure_reason(run_manifest_path)
            unsupported += 1
        else:
            doc_status = "fail"
            failure_reason = _read_manifest_failure_reason(run_manifest_path)
            failed += 1

        if doc_status != "pass" and failure_reason is None:
            failure_reason = "run_failed"

        document_manifests.append(
            {
                "doc_id": doc_id,
                "input_file": str(input_path),
                "sha256": sha256_hex,
                "status": doc_status,
                "run_dir": str(run_dir),
                "output_pptx": str(output_pptx) if doc_status == "pass" else None,
                "run_manifest_path": (
                    str(run_dir / "run_manifest.json")
                    if (run_dir / "run_manifest.json").exists()
                    else None
                ),
                "qa_preflight_path": (
                    str(run_dir / "qa.preflight.json")
                    if (run_dir / "qa.preflight.json").exists()
                    else None
                ),
                "qa_postrender_path": (
                    str(run_dir / "qa.postrender.json")
                    if (run_dir / "qa.postrender.json").exists()
                    else None
                ),
                "failure_reason": failure_reason,
                "image_generation": image_generation_payload,
                "image_traces": image_traces_payload,
            }
        )

        if doc_status != "pass" and not continue_on_error:
            break

    total = len(document_manifests)
    if passed == total:
        batch_status = "pass"
    elif passed == 0:
        batch_status = "fail"
    else:
        batch_status = "partial_fail"

    manifest_payload = {
        "schema_version": BATCH_MANIFEST_SCHEMA_VERSION_V1,
        "batch_id": batch_id,
        "status": batch_status,
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "artifacts_root": str(artifacts_root),
        "runtime": {
            "model_profile": runtime_settings["model_profile"],
            "text_provider": runtime_settings["text_provider"],
            "text_model": runtime_settings["text_model"],
            "image_provider": runtime_settings["image_provider"],
            "image_model": runtime_settings["image_model"],
            "language": runtime_settings["language"],
            "generation_settings_hash": runtime_settings["generation_settings_hash"],
        },
        "counts": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "unsupported": unsupported,
        },
        "documents": document_manifests,
    }
    validated_manifest = BatchManifest.model_validate(manifest_payload)
    _write_json_file(batch_manifest_path, validated_manifest.model_dump(mode="json"))

    print(
        "Batch run complete: "
        + f"input_dir={input_dir} output_dir={output_dir} batch_id={batch_id}"
    )
    print(f"Document registry written: {document_registry_path}")
    print(f"Batch manifest written: {batch_manifest_path}")

    return 0 if failed == 0 and unsupported == 0 else 1


def _cmd_revise(args: argparse.Namespace) -> int:
    run_dir = Path(cast(str, getattr(args, "run_dir")))
    feedback_path = Path(cast(str, getattr(args, "feedback_path")))

    if not run_dir.exists() or not run_dir.is_dir():
        print(f"Revise failed: run directory not found: {run_dir}")
        return 1
    if not feedback_path.exists():
        print(f"Revise failed: feedback file not found: {feedback_path}")
        return 1

    slidespec_path = run_dir / "slidespec.json"
    output_path = run_dir / "output.pptx"
    qa_report_path = run_dir / "output.pptx.qa.json"
    hook_summary_path = run_dir / "output.pptx.hooks.qa.json"
    hook_error_path = run_dir / "output.pptx.hooks.error.json"
    preflight_gate_path = run_dir / "qa.preflight.json"
    postrender_gate_path = run_dir / "qa.postrender.json"
    manifest_path = run_dir / "run_manifest.json"

    if not slidespec_path.exists():
        print(f"Revise failed: slidespec file not found: {slidespec_path}")
        return 1

    try:
        feedback_patch = _parse_feedback_patch(feedback_path)
    except FileNotFoundError:
        print(f"Revise failed: feedback file not found: {feedback_path}")
        return 1
    except Exception as exc:
        if exc.__class__.__name__ != "ValidationError":
            raise
        errors = getattr(exc, "errors", None)
        if not callable(errors):
            raise
        validation_errors = errors()
        if not isinstance(validation_errors, list):
            raise
        print(f"Revise failed for {feedback_path}:")
        for err in validation_errors:
            location = ".".join(str(part) for part in err["loc"])
            print(f"- {location}: {err['msg']}")
        return 1

    parent_run_id = run_dir.name
    if manifest_path.exists():
        manifest_payload = cast(
            dict[str, object],
            json.loads(manifest_path.read_text(encoding="utf-8")),
        )
        manifest_run_id = manifest_payload.get("run_id")
        if isinstance(manifest_run_id, str) and manifest_run_id.strip():
            parent_run_id = manifest_run_id

    feedback_sha256 = _sha256_file(feedback_path)
    revised_run_id = hashlib.sha256(
        f"{parent_run_id}:{feedback_sha256}".encode("utf-8")
    ).hexdigest()[:16]

    try:
        revised_slidespec_payload, targeted_slide_ids = (
            _apply_feedback_patch_to_slidespec(
                slidespec_path=slidespec_path,
                feedback_patch=feedback_patch,
            )
        )
    except ValueError as exc:
        print(f"Revise failed: {exc}")
        return 1

    if not targeted_slide_ids:
        print("Revise failed: unknown_target: no targeted slide ids found")
        return 1

    temp_slidespec_path = run_dir / "slidespec.revise.tmp.json"
    temp_output_path = run_dir / "output.revise.tmp.pptx"
    temp_qa_report_path = run_dir / "output.revise.tmp.pptx.qa.json"
    temp_hook_summary_path = run_dir / "output.revise.tmp.pptx.hooks.qa.json"
    temp_hook_error_path = run_dir / "output.revise.tmp.pptx.hooks.error.json"
    temp_preflight_gate_path = run_dir / "qa.revise.preflight.tmp.json"
    temp_postrender_gate_path = run_dir / "qa.revise.postrender.tmp.json"
    temp_output_images_dir = temp_output_path.with_suffix(
        temp_output_path.suffix + ".images"
    )

    _cleanup_temp_paths(
        files=[
            temp_slidespec_path,
            temp_output_path,
            temp_qa_report_path,
            temp_hook_summary_path,
            temp_hook_error_path,
            temp_preflight_gate_path,
            temp_postrender_gate_path,
        ],
        dirs=[temp_output_images_dir],
    )

    _write_json_file(temp_slidespec_path, revised_slidespec_payload)
    _ = validate_slidespec_file(temp_slidespec_path)

    preflight_report, preflight_exit = _build_qa_gate_report(
        run_id=revised_run_id,
        slidespec_path=temp_slidespec_path,
        qa_report_path=None,
        hook_summary_path=None,
    )
    _write_json_file(temp_preflight_gate_path, preflight_report)
    if preflight_exit != 0:
        print("Revise blocked by preflight QA gate.")
        for failure in preflight_report["failures"]:
            print(f"- {failure}")
        _cleanup_temp_paths(
            files=[
                temp_slidespec_path,
                temp_output_path,
                temp_qa_report_path,
                temp_hook_summary_path,
                temp_hook_error_path,
                temp_preflight_gate_path,
                temp_postrender_gate_path,
            ],
            dirs=[temp_output_images_dir],
        )
        return 1

    post_render_hook_error: HookPolicyError | None = None
    image_generation_payload: dict[str, object] = _default_image_generation_payload()
    image_traces_payload: list[dict[str, object]] = []

    try:
        validated_slidespec = pre_render_contract_gate(temp_slidespec_path)
        qa_report = render_slidespec_to_pptx(validated_slidespec, temp_output_path)
        _write_json_file(temp_qa_report_path, qa_report)
        image_generation_raw = qa_report["image_generation"]
        image_generation_payload = cast(
            dict[str, object],
            {
                "requested": _coerce_int(
                    image_generation_raw.get("requested"), default=0
                ),
                "succeeded": _coerce_int(
                    image_generation_raw.get("succeeded"), default=0
                ),
                "failed": _coerce_int(image_generation_raw.get("failed"), default=0),
                "image_model": (
                    str(image_generation_raw.get("image_model")).strip()
                    if isinstance(image_generation_raw.get("image_model"), str)
                    and str(image_generation_raw.get("image_model")).strip()
                    else None
                ),
            },
        )
        image_traces_payload = cast(
            list[dict[str, object]], [trace for trace in qa_report["image_traces"]]
        )
        try:
            _ = post_render_qa_gate(
                run_id=compute_run_id(temp_slidespec_path, temp_output_path),
                input_path=temp_slidespec_path,
                output_path=temp_output_path,
                qa_report_path=temp_qa_report_path,
                qa_report=qa_report,
            )
        except HookPolicyError as exc:
            if exc.phase == "post_render" and exc.reason == "qa_gate_failed":
                post_render_hook_error = exc
                _ = write_on_error_report(
                    run_id=compute_run_id(temp_slidespec_path, temp_output_path),
                    input_path=temp_slidespec_path,
                    output_path=temp_output_path,
                    phase=exc.phase,
                    reason=exc.reason,
                    error=exc,
                    details=exc.details,
                )
            else:
                raise
    except UnsupportedLayoutHintError as exc:
        print(f"Revise failed: {exc}")
        _cleanup_temp_paths(
            files=[
                temp_slidespec_path,
                temp_output_path,
                temp_qa_report_path,
                temp_hook_summary_path,
                temp_hook_error_path,
                temp_preflight_gate_path,
                temp_postrender_gate_path,
            ],
            dirs=[temp_output_images_dir],
        )
        return 2
    except ImageGenerationFailedError as exc:
        print(f"Revise failed: {exc}")
        _cleanup_temp_paths(
            files=[
                temp_slidespec_path,
                temp_output_path,
                temp_qa_report_path,
                temp_hook_summary_path,
                temp_hook_error_path,
                temp_preflight_gate_path,
                temp_postrender_gate_path,
            ],
            dirs=[temp_output_images_dir],
        )
        return 1
    except HookPolicyError as exc:
        print(f"Revise failed: hook policy violation [{exc.phase}] {exc.reason}")
        for detail in exc.details:
            print(f"- {detail}")
        _cleanup_temp_paths(
            files=[
                temp_slidespec_path,
                temp_output_path,
                temp_qa_report_path,
                temp_hook_summary_path,
                temp_hook_error_path,
                temp_preflight_gate_path,
                temp_postrender_gate_path,
            ],
            dirs=[temp_output_images_dir],
        )
        return 1

    postrender_report, postrender_exit = _build_qa_gate_report(
        run_id=revised_run_id,
        slidespec_path=temp_slidespec_path,
        qa_report_path=temp_qa_report_path,
        hook_summary_path=temp_hook_summary_path,
    )
    _write_json_file(temp_postrender_gate_path, postrender_report)
    if postrender_exit != 0 or post_render_hook_error is not None:
        print("Revise failed: postrender QA gate failed")
        for failure in postrender_report["failures"]:
            print(f"- {failure}")
        _cleanup_temp_paths(
            files=[
                temp_slidespec_path,
                temp_output_path,
                temp_qa_report_path,
                temp_hook_summary_path,
                temp_hook_error_path,
                temp_preflight_gate_path,
                temp_postrender_gate_path,
            ],
            dirs=[temp_output_images_dir],
        )
        return 1

    canonical_output_images_dir = output_path.with_suffix(
        output_path.suffix + ".images"
    )
    _unlink_if_exists(hook_error_path)
    _ = temp_slidespec_path.replace(slidespec_path)
    _ = temp_output_path.replace(output_path)
    _ = temp_qa_report_path.replace(qa_report_path)
    _ = temp_hook_summary_path.replace(hook_summary_path)
    _ = temp_preflight_gate_path.replace(preflight_gate_path)
    _ = temp_postrender_gate_path.replace(postrender_gate_path)
    if canonical_output_images_dir.exists() and canonical_output_images_dir.is_dir():
        shutil.rmtree(canonical_output_images_dir)
    if temp_output_images_dir.exists() and temp_output_images_dir.is_dir():
        _ = temp_output_images_dir.replace(canonical_output_images_dir)
    image_traces_payload = _rewrite_image_trace_paths(
        image_traces=image_traces_payload,
        old_images_dir=temp_output_images_dir,
        new_images_dir=canonical_output_images_dir,
    )

    manifest_payload: dict[str, object] = {
        "schema": "pipeline.run.manifest.v1",
        "run_id": revised_run_id,
        "status": "pass",
        "parent_run_id": parent_run_id,
        "feedback_reference": {
            "path": str(feedback_path.resolve()),
            "sha256": feedback_sha256,
            "run_id": feedback_patch.run_id,
            "doc_id": feedback_patch.doc_id,
            "summary": feedback_patch.summary,
        },
        "targeted_slide_ids": targeted_slide_ids,
        "paths": {
            "slidespec": str(slidespec_path),
            "output_pptx": str(output_path),
            "qa_report": str(qa_report_path),
            "hook_summary": str(hook_summary_path),
            "qa_preflight": str(preflight_gate_path),
            "qa_postrender": str(postrender_gate_path),
            "run_dir": str(run_dir),
        },
        "render_run_id": compute_run_id(slidespec_path, output_path),
        "image_generation": image_generation_payload,
        "image_traces": image_traces_payload,
    }
    _write_json_file(manifest_path, manifest_payload)

    print(
        "Revise complete: "
        + f"run_dir={run_dir} targeted_slide_ids={targeted_slide_ids} run_id={revised_run_id}"
    )
    print(f"Run manifest written: {manifest_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pptx-agent")
    _ = parser.add_argument(
        "--version",
        action="version",
        version="pptx-agent 0.1.0",
    )
    subparsers = parser.add_subparsers(dest="command")

    validate_ir = subparsers.add_parser(
        "validate-ir",
        help="Validate SlideSpec v1 JSON IR",
    )
    _ = validate_ir.add_argument(
        "--in",
        dest="input_path",
        required=True,
        help="Path to SlideSpec JSON file",
    )
    validate_ir.set_defaults(handler=_cmd_validate_ir)

    validate_outline = subparsers.add_parser(
        "validate-outline",
        help="Validate DeckOutline v1 JSON",
    )
    _ = validate_outline.add_argument(
        "--in",
        dest="input_path",
        required=True,
        help="Path to DeckOutline JSON file",
    )
    validate_outline.set_defaults(handler=_cmd_validate_outline)

    extract = subparsers.add_parser(
        "extract",
        help="Extract page/block text payload from supported documents",
    )
    _ = extract.add_argument(
        "--in",
        dest="input_path",
        required=True,
        help="Path to input document (.pdf or .docx)",
    )
    _ = extract.add_argument(
        "--out",
        dest="output_path",
        required=True,
        help="Path to output extraction JSON",
    )
    extract.set_defaults(handler=_cmd_extract)

    normalize = subparsers.add_parser(
        "normalize",
        help="Normalize extract.v1 payload into SlideSpec-ready structure",
    )
    _ = normalize.add_argument(
        "--in",
        dest="input_path",
        required=True,
        help="Path to extraction JSON",
    )
    _ = normalize.add_argument(
        "--out",
        dest="output_path",
        required=True,
        help="Path to output normalized JSON",
    )
    normalize.set_defaults(handler=_cmd_normalize)

    plan = subparsers.add_parser(
        "plan",
        help="Transform normalized payload into SlideSpec v1 planning output",
    )
    _ = plan.add_argument(
        "--in",
        dest="input_path",
        required=True,
        help="Path to normalized JSON",
    )
    _ = plan.add_argument(
        "--out",
        dest="output_path",
        required=True,
        help="Path to output SlideSpec JSON",
    )
    plan.set_defaults(handler=_cmd_plan)

    outline = subparsers.add_parser(
        "outline",
        help="Transform normalized payload into DeckOutline v1 planning output",
    )
    _ = outline.add_argument(
        "--in",
        dest="input_path",
        required=True,
        help="Path to normalized JSON",
    )
    _ = outline.add_argument(
        "--out",
        dest="output_path",
        required=True,
        help="Path to output DeckOutline JSON",
    )
    outline.set_defaults(handler=_cmd_outline)

    outline_to_slidespec = subparsers.add_parser(
        "outline-to-slidespec",
        help="Convert DeckOutline v1 + normalize.v1 payload into SlideSpec v1",
    )
    _ = outline_to_slidespec.add_argument(
        "--outline",
        dest="outline_path",
        required=True,
        help="Path to DeckOutline JSON",
    )
    _ = outline_to_slidespec.add_argument(
        "--normalized",
        dest="normalized_path",
        required=True,
        help="Path to normalized JSON",
    )
    _ = outline_to_slidespec.add_argument(
        "--out",
        dest="output_path",
        required=True,
        help="Path to output SlideSpec JSON",
    )
    outline_to_slidespec.set_defaults(handler=_cmd_outline_to_slidespec)

    evidence_graph = subparsers.add_parser(
        "evidence-graph",
        help="Build evidence_graph.v1 from normalize.v1 payload",
    )
    _ = evidence_graph.add_argument(
        "--in",
        dest="input_path",
        required=True,
        help="Path to normalized JSON",
    )
    _ = evidence_graph.add_argument(
        "--out",
        dest="output_path",
        required=True,
        help="Path to output evidence_graph JSON",
    )
    evidence_graph.set_defaults(handler=_cmd_evidence_graph)

    render = subparsers.add_parser(
        "render",
        help="Render SlideSpec v1 JSON into deterministic PPTX output",
    )
    _ = render.add_argument(
        "--in",
        dest="input_path",
        required=True,
        help="Path to SlideSpec JSON",
    )
    _ = render.add_argument(
        "--out",
        dest="output_path",
        required=True,
        help="Path to output PPTX file",
    )
    render.set_defaults(handler=_cmd_render)

    qa = subparsers.add_parser(
        "qa",
        help="Run QA/provenance/injection gate checks with machine-readable output",
    )
    _ = qa.add_argument(
        "--slidespec",
        dest="slidespec_path",
        required=True,
        help="Path to SlideSpec JSON file",
    )
    _ = qa.add_argument(
        "--qa-report",
        dest="qa_report_path",
        required=False,
        help="Path to render QA JSON report",
    )
    _ = qa.add_argument(
        "--hook-summary",
        dest="hook_summary_path",
        required=False,
        help="Path to render hook QA summary JSON",
    )
    _ = qa.add_argument(
        "--out",
        dest="output_path",
        required=True,
        help="Path to QA gate output JSON",
    )
    _ = qa.add_argument(
        "--run-id",
        dest="run_id",
        required=False,
        help="Optional run ID for deterministic reporting",
    )
    qa.set_defaults(handler=_cmd_qa)

    run_local = subparsers.add_parser(
        "run-local",
        help="Canonical end-to-end local pipeline run with run_id-scoped artifacts",
    )
    _ = run_local.add_argument(
        "--in",
        dest="input_path",
        required=True,
        help="Path to input document (.pdf or .docx)",
    )
    _ = run_local.add_argument(
        "--artifacts-root",
        dest="artifacts_root",
        required=False,
        default="artifacts",
        help="Root directory for run artifacts (default: artifacts)",
    )
    _ = run_local.add_argument(
        "--run-id",
        dest="run_id",
        required=False,
        help="Optional run ID override for artifacts/<run_id>/...",
    )
    _ = run_local.add_argument(
        "--model-profile",
        dest="model_profile",
        required=False,
        choices=["local", "cloud"],
        default="local",
        help="Runtime model profile for manifest/runtime checks (default: local)",
    )
    run_local.set_defaults(handler=_cmd_run_local)

    run_folder = subparsers.add_parser(
        "run-folder",
        help="Batch folder orchestrator producing one PPTX per supported input file",
    )
    _ = run_folder.add_argument(
        "--in-dir",
        dest="input_dir",
        required=True,
        help="Path to input folder containing documents",
    )
    _ = run_folder.add_argument(
        "--out-dir",
        dest="output_dir",
        required=True,
        help="Path to output folder for generated PPTX files",
    )
    _ = run_folder.add_argument(
        "--artifacts-root",
        dest="artifacts_root",
        required=False,
        default="artifacts/batches",
        help="Root directory for batch artifacts (default: artifacts/batches)",
    )
    _ = run_folder.add_argument(
        "--model-profile",
        dest="model_profile",
        required=False,
        choices=["local", "cloud"],
        default="local",
        help="Runtime model profile recorded in batch manifest (default: local)",
    )
    _ = run_folder.add_argument(
        "--continue-on-error",
        dest="continue_on_error",
        required=False,
        choices=["true", "false"],
        default="true",
        help="Continue processing when a document fails (default: true)",
    )
    run_folder.set_defaults(handler=_cmd_run_folder)

    revise = subparsers.add_parser(
        "revise",
        help="Apply feedback_patch.v1 to an existing run directory and rerun gated render",
    )
    _ = revise.add_argument(
        "--run-dir",
        dest="run_dir",
        required=True,
        help="Path to existing per-document run directory",
    )
    _ = revise.add_argument(
        "--feedback",
        dest="feedback_path",
        required=True,
        help="Path to feedback_patch.v1 JSON",
    )
    revise.set_defaults(handler=_cmd_revise)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    handler = cast(
        Callable[[argparse.Namespace], int] | None, getattr(args, "handler", None)
    )
    if handler is None:
        return 0
    return int(handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
