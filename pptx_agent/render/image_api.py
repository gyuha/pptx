from __future__ import annotations

import base64
import json
import os
from http.client import HTTPResponse
from typing import cast
from urllib import error, request

# pyright: reportMissingImports=false, reportUnknownMemberType=false, reportUnknownVariableType=false

MOCK_IMAGE_MODEL = "image-model-v1"
_ONE_PIXEL_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
    "/w8AAgMBAQEAAP///wAAAABJRU5ErkJggg=="
)


class ImageGenerationFailedError(RuntimeError):
    pass


def _resolve_provider() -> str:
    provider = os.getenv("PPTX_AGENT_IMAGE_API_PROVIDER", "mock").strip().lower()
    if provider not in {"mock", "openai"}:
        raise ImageGenerationFailedError(
            "unsupported image API provider: " + provider + " (supported: mock, openai)"
        )
    return provider


def resolve_default_image_model() -> str:
    value = os.getenv("PPTX_AGENT_IMAGE_MODEL", MOCK_IMAGE_MODEL).strip()
    if not value:
        raise ImageGenerationFailedError("image model must not be blank")
    return value


def generate_image_bytes(*, prompt: str, model: str, seed: int | None) -> bytes:
    provider = _resolve_provider()
    if provider == "mock":
        return base64.b64decode(_ONE_PIXEL_PNG_BASE64)

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ImageGenerationFailedError(
            "OPENAI_API_KEY is required when PPTX_AGENT_IMAGE_API_PROVIDER=openai"
        )
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com").rstrip("/")
    timeout_seconds_raw = os.getenv("PPTX_AGENT_IMAGE_API_TIMEOUT_SECONDS", "30")
    try:
        timeout_seconds = max(1.0, float(timeout_seconds_raw))
    except ValueError as exc:
        raise ImageGenerationFailedError(
            "PPTX_AGENT_IMAGE_API_TIMEOUT_SECONDS must be numeric"
        ) from exc

    payload: dict[str, object] = {
        "model": model,
        "prompt": prompt,
        "size": "1024x1024",
        "response_format": "b64_json",
    }
    if seed is not None:
        payload["seed"] = seed

    endpoint = f"{base_url}/v1/images/generations"
    body = json.dumps(payload, sort_keys=True).encode("utf-8")
    req = request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        response_ctx = cast(HTTPResponse, request.urlopen(req, timeout=timeout_seconds))
        with response_ctx as response:
            response_body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ImageGenerationFailedError(
            f"image API request failed: status={exc.code} body={detail[:200]}"
        ) from exc
    except error.URLError as exc:
        raise ImageGenerationFailedError(
            f"image API request failed: {exc.reason}"
        ) from exc

    try:
        payload_obj = cast(object, json.loads(response_body))
    except json.JSONDecodeError as exc:
        raise ImageGenerationFailedError(
            "image API returned non-JSON response"
        ) from exc
    if not isinstance(payload_obj, dict):
        raise ImageGenerationFailedError("image API response must be an object")
    data = payload_obj.get("data")
    if not isinstance(data, list) or not data:
        raise ImageGenerationFailedError("image API response missing data array")
    first = data[0]
    if not isinstance(first, dict):
        raise ImageGenerationFailedError("image API response data[0] must be an object")
    b64_json = first.get("b64_json")
    if not isinstance(b64_json, str) or not b64_json.strip():
        raise ImageGenerationFailedError("image API response missing b64_json payload")
    try:
        return base64.b64decode(b64_json)
    except Exception as exc:
        raise ImageGenerationFailedError(
            "image API returned invalid base64 image payload"
        ) from exc


__all__ = [
    "ImageGenerationFailedError",
    "MOCK_IMAGE_MODEL",
    "generate_image_bytes",
    "resolve_default_image_model",
]
