from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict
import base64
import time

from app.config import (
    QINIU_IMAGE_BASE_URL,
    QINIU_IMAGE_GENERATE_PATH,
    QINIU_IMAGE_MODEL,
    QINIU_IMAGE_RESPONSE_FORMAT,
    QINIU_IMAGE_SIZE,
    QINIU_IMAGE_TASK_PATH_TEMPLATE,
    QINIU_KODO_BUCKET,
    QINIU_KODO_PUBLIC_DOMAIN,
    _get_image_price_per_task,
)
from app.services.llm_service import _build_qiniu_headers, _request_no_proxy, _resolve_url
from app.services.video_service import _upload_image_to_qiniu_kodo


def _cover_object_key() -> str:
    return f"generated-covers/cover-{int(time.time() * 1000)}.png"


def _persist_base64_image(b64_text: str) -> str:
    raw = base64.b64decode(str(b64_text or "").strip())
    if not raw:
        raise RuntimeError("image generation returned empty base64 payload")

    if QINIU_KODO_BUCKET and QINIU_KODO_PUBLIC_DOMAIN:
        with NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(raw)
            temp_path = tmp.name
        try:
            return _upload_image_to_qiniu_kodo(temp_path, _cover_object_key())
        finally:
            path = Path(temp_path)
            if path.exists():
                path.unlink(missing_ok=True)

    data_url = f"data:image/png;base64,{str(b64_text or '').strip()}"
    if len(data_url) > 180000:
        raise RuntimeError("generated image is too large to store locally; please configure QINIU_KODO_BUCKET and QINIU_KODO_PUBLIC_DOMAIN")
    return data_url


def _extract_generated_image_url(data: Dict[str, Any]) -> str:
    items = data.get("data")
    if not isinstance(items, list) or not items:
        raise RuntimeError("image generation returned no data")

    first = items[0] if isinstance(items[0], dict) else {}
    image_url = str(first.get("url", "") or "").strip()
    if image_url:
        return image_url

    b64_text = str(first.get("b64_json", "") or "").strip()
    if b64_text:
        return _persist_base64_image(b64_text)

    raise RuntimeError("image generation returned neither url nor b64_json")


def _normalize_image_task_status(raw_status: Any) -> str:
    status = str(raw_status or "").strip().lower()
    if status in {"submitted", "processing", "succeed", "failed"}:
        return status
    return status or "unknown"


def _build_cover_image_cost_meta(size: str) -> Dict[str, Any]:
    price = _get_image_price_per_task(QINIU_IMAGE_MODEL)
    return {
        "stage": "cover_image_generate",
        "cost_type": "image",
        "primary_model": QINIU_IMAGE_MODEL,
        "final_model": QINIU_IMAGE_MODEL,
        "estimated_duration": 0,
        "estimated_cost": price,
        "actual_cost": price,
        "image_count": 1,
        "image_size": str(size or "").strip(),
        "image_price_per_task": price,
        "retry_count": 0,
        "fallback_triggered": False,
        "fallback_reason": "",
    }


def _create_cover_image_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    prompt = str(payload.get("image_prompt", "") or "").strip()
    if not prompt:
        raise ValueError("image_prompt is required")
    if not QINIU_IMAGE_MODEL:
        raise RuntimeError("QINIU_IMAGE_MODEL is missing in .env")

    url = _resolve_url(QINIU_IMAGE_BASE_URL, QINIU_IMAGE_GENERATE_PATH)
    headers = _build_qiniu_headers("text", include_content_type=True)
    body = {
        "model": QINIU_IMAGE_MODEL,
        "prompt": prompt,
        "size": str(payload.get("size", "") or QINIU_IMAGE_SIZE).strip() or QINIU_IMAGE_SIZE,
        "n": 1,
        "response_format": str(payload.get("response_format", "") or QINIU_IMAGE_RESPONSE_FORMAT).strip() or QINIU_IMAGE_RESPONSE_FORMAT,
    }

    response = _request_no_proxy("POST", url, headers=headers, json=body, timeout=120, verify=False)
    response.raise_for_status()
    result = response.json()
    if isinstance(result.get("data"), list) and result.get("data"):
        return {
            "task_id": "",
            "task_status": "succeed",
            "image_url": _extract_generated_image_url(result),
            "model": QINIU_IMAGE_MODEL,
            "size": body["size"],
            "prompt": prompt,
            "meta": _build_cover_image_cost_meta(str(body["size"])),
            "raw": result,
        }

    task_id = str(result.get("task_id", "") or "").strip()
    if not task_id:
        raise RuntimeError("image generation returned neither task_id nor data")

    return {
        "task_id": task_id,
        "task_status": _normalize_image_task_status(result.get("status") or result.get("task_status") or "submitted"),
        "model": QINIU_IMAGE_MODEL,
        "size": body["size"],
        "prompt": prompt,
        "meta": _build_cover_image_cost_meta(str(body["size"])),
        "raw": result,
    }


def _query_cover_image_task(task_id: str) -> Dict[str, Any]:
    current_task_id = str(task_id or "").strip()
    if not current_task_id:
        raise ValueError("task_id is required")

    url = _resolve_url(QINIU_IMAGE_BASE_URL, QINIU_IMAGE_TASK_PATH_TEMPLATE.format(task_id=current_task_id))
    headers = _build_qiniu_headers("text", include_content_type=False)
    response = _request_no_proxy("GET", url, headers=headers, timeout=120, verify=False)
    response.raise_for_status()
    result = response.json()
    status = _normalize_image_task_status(result.get("status") or result.get("task_status"))

    normalized: Dict[str, Any] = {
        "task_id": str(result.get("task_id", "") or current_task_id).strip(),
        "task_status": status,
        "status_message": str(result.get("status_message") or result.get("message") or "").strip(),
        "model": str(result.get("model", "") or QINIU_IMAGE_MODEL).strip(),
        "raw": result,
    }

    if status == "succeed":
        normalized["image_url"] = _extract_generated_image_url(result)
    else:
        normalized["image_url"] = ""

    return normalized
