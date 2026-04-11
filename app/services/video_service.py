import base64
import hashlib
import hmac
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote
from uuid import uuid4

import requests

from app.config import (
    QINIU_AK,
    QINIU_SK,
    QINIU_TEXT_API_KEY,
    QINIU_VIDEO_API_KEY,
    QINIU_LLM_BASE_URL,
    QINIU_WEB_SEARCH_PATH,
    QINIU_VIDEO_MODEL,
    QINIU_VIDEO_BASE_URL,
    QINIU_VIDEO_CREATE_PATH,
    QINIU_VIDEO_TASK_PATH_TEMPLATE,
    QINIU_VIDU_Q3_TEXT_TO_VIDEO_PATH,
    QINIU_VIDU_Q3_IMAGE_TO_VIDEO_PATH,
    QINIU_VIDU_Q3_START_END_TO_VIDEO_PATH,
    QINIU_ENABLE_ASYNC_HEADER,
    QINIU_KODO_BUCKET,
    QINIU_KODO_PUBLIC_DOMAIN,
    QINIU_KODO_UPLOAD_HOST,
    _get_video_price_per_second,
)
from app.services.llm_service import (
    _resolve_url,
    _build_url_candidates,
    _is_not_found_or_method_not_allowed,
    _build_qiniu_aksk_headers,
    _build_qiniu_headers,
    _call_provider_text,
    _request_no_proxy,
)


def _has_qiniu_video_credential() -> bool:
    return bool(QINIU_VIDEO_API_KEY or QINIU_TEXT_API_KEY or (QINIU_AK and QINIU_SK))


def _urlsafe_b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8")


def _normalize_public_domain(domain: str) -> str:
    text = str(domain or "").strip()
    if not text:
        return ""
    if text.startswith("http://") or text.startswith("https://"):
        return text.rstrip("/")
    return f"https://{text.rstrip('/')}"


def _build_qiniu_upload_token(bucket: str, key: str, expires_in_sec: int = 3600) -> str:
    if not QINIU_AK or not QINIU_SK:
        raise RuntimeError("QINIU_AK/QINIU_SK is required for qiniu object upload")

    policy = {
        "scope": f"{bucket}:{key}",
        "deadline": int(time.time()) + max(60, int(expires_in_sec or 3600)),
    }
    encoded_policy = _urlsafe_b64(json.dumps(policy, separators=(",", ":")).encode("utf-8"))
    sign = hmac.new(QINIU_SK.encode("utf-8"), encoded_policy.encode("utf-8"), hashlib.sha1).digest()
    encoded_sign = _urlsafe_b64(sign)
    return f"{QINIU_AK}:{encoded_sign}:{encoded_policy}"


def _upload_image_to_qiniu_kodo(local_file_path: str, object_key: str) -> str:
    bucket = str(QINIU_KODO_BUCKET or "").strip()
    public_domain = _normalize_public_domain(QINIU_KODO_PUBLIC_DOMAIN)
    upload_host = str(QINIU_KODO_UPLOAD_HOST or "https://up.qiniup.com").strip()

    if not bucket or not public_domain:
        raise RuntimeError("QINIU_KODO_BUCKET 或 QINIU_KODO_PUBLIC_DOMAIN 未配置")

    path = Path(local_file_path)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"image file not found: {local_file_path}")

    token = _build_qiniu_upload_token(bucket=bucket, key=object_key)

    def _upload_once(host: str) -> requests.Response:
        with path.open("rb") as fp:
            files = {"file": (path.name, fp, "application/octet-stream")}
            data = {"token": token, "key": object_key}
            return _request_no_proxy("POST", host, data=data, files=files, timeout=60, verify=False)

    response = _upload_once(upload_host)
    if response.status_code < 200 or response.status_code >= 300:
        detail_text = ""
        try:
            detail_json = response.json()
            detail_text = json.dumps(detail_json, ensure_ascii=False)
        except Exception:  # noqa: BLE001
            detail_text = (response.text or "").strip()

        # Example: "incorrect region, please use up-z2.qiniup.com, bucket is: xxx"
        hint_match = re.search(r"please use\s+([\w.-]+qiniup\.com)", detail_text, re.IGNORECASE)
        if hint_match:
            hinted_host = f"https://{hint_match.group(1).strip()}"
            if hinted_host.rstrip("/") != upload_host.rstrip("/"):
                retry_resp = _upload_once(hinted_host)
                if 200 <= retry_resp.status_code < 300:
                    return f"{public_domain}/{quote(object_key)}"
                try:
                    retry_detail = retry_resp.json()
                    detail_text = (
                        f"{detail_text}; retry({hinted_host}) failed: "
                        f"{json.dumps(retry_detail, ensure_ascii=False)}"
                    )
                except Exception:  # noqa: BLE001
                    detail_text = f"{detail_text}; retry({hinted_host}) failed: {(retry_resp.text or '').strip()}"

        detail_text = detail_text or f"HTTP {response.status_code}"
        raise RuntimeError(f"Qiniu Kodo upload failed: {detail_text}")

    return f"{public_domain}/{quote(object_key)}"


def _extract_last_frame_to_qiniu(video_url: str) -> str:
    url = str(video_url or "").strip()
    if not url:
        raise ValueError("video_url is required")

    temp_dir = Path(__file__).resolve().parents[2] / "static" / "uploads" / "video_refs"
    temp_dir.mkdir(parents=True, exist_ok=True)

    ts = int(time.time())
    suffix = Path(url.split("?")[0]).suffix.lower() or ".mp4"
    local_video = temp_dir / f"tmp_video_{ts}_{uuid4().hex[:8]}{suffix}"
    local_frame = temp_dir / f"tmp_frame_{ts}_{uuid4().hex[:8]}.jpg"

    try:
        resp = _request_no_proxy("GET", url, stream=True, timeout=120, verify=False)
        resp.raise_for_status()
        with local_video.open("wb") as fp:
            for chunk in resp.iter_content(chunk_size=1024 * 256):
                if chunk:
                    fp.write(chunk)

        from moviepy.editor import VideoFileClip
        import imageio.v2 as imageio

        with VideoFileClip(str(local_video)) as clip:
            duration = float(clip.duration or 0.0)
            frame_time = max(0.0, duration - 0.08) if duration > 0 else 0.0
            frame = clip.get_frame(frame_time)
            imageio.imwrite(str(local_frame), frame, quality=92)

        object_key = f"video_refs/last_frame_{ts}_{uuid4().hex[:8]}.jpg"
        return _upload_image_to_qiniu_kodo(str(local_frame), object_key)
    finally:
        try:
            if local_video.exists():
                local_video.unlink()
        except Exception:  # noqa: BLE001
            pass
        try:
            if local_frame.exists():
                local_frame.unlink()
        except Exception:  # noqa: BLE001
            pass


def _looks_like_vidu_queue_path(path_text: str) -> bool:
    return "queue/fal-ai/vidu" in str(path_text or "").lower()


def _pick_vidu_create_path(payload: Dict[str, Any], model: str, configured_path: str) -> str:
    mode = str(payload.get("video_mode", "")).strip().lower()
    if mode in {"text", "text-to-video", "t2v"}:
        return QINIU_VIDU_Q3_TEXT_TO_VIDEO_PATH
    if mode in {"image", "image-to-video", "i2v"}:
        return QINIU_VIDU_Q3_IMAGE_TO_VIDEO_PATH
    if mode in {"start_end", "start-end", "start-end-to-video", "s2v"}:
        return QINIU_VIDU_Q3_START_END_TO_VIDEO_PATH

    model_text = str(model or "").lower()
    if "viduq3" not in model_text:
        return configured_path

    start_image_url = str(payload.get("start_image_url", "")).strip()
    end_image_url = str(payload.get("end_image_url", "")).strip()
    image_url = str(payload.get("image_url", "")).strip()

    if start_image_url and end_image_url:
        return QINIU_VIDU_Q3_START_END_TO_VIDEO_PATH
    if image_url:
        return QINIU_VIDU_Q3_IMAGE_TO_VIDEO_PATH
    return QINIU_VIDU_Q3_TEXT_TO_VIDEO_PATH


def _size_to_vidu_resolution(size: str) -> str:
    text = str(size or "").strip().lower().replace("x", "*")
    mapping = {
        "1920*1080": "1080p",
        "1280*720": "720p",
        "960*540": "540p",
    }
    return mapping.get(text, "720p")


def _build_video_cost_meta(model: str, size: str, duration: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    with_reference = bool(
        str(payload.get("image_url", "")).strip()
        or str(payload.get("start_image_url", "")).strip()
        or str(payload.get("end_image_url", "")).strip()
    )
    unit_price = _get_video_price_per_second(model, size, with_reference=with_reference)
    normalized_duration = max(0, int(duration or 0))
    return {
        "stage": "video_generate",
        "cost_type": "video",
        "primary_model": str(model or "").strip(),
        "final_model": str(model or "").strip(),
        "estimated_duration": normalized_duration,
        "estimated_cost": unit_price * normalized_duration,
        "actual_cost": unit_price * normalized_duration,
        "video_duration": normalized_duration,
        "video_size": str(size or "").strip(),
        "video_price_per_second": unit_price,
        "video_with_reference": with_reference,
        "retry_count": 0,
        "fallback_triggered": False,
        "fallback_reason": "",
    }


def _map_task_status(raw_status: str) -> str:
    status = str(raw_status or "").upper()
    if status in {"SUCCEEDED", "FAILED", "CANCELED", "IN_PROGRESS", "IN_QUEUE", "PENDING"}:
        return status
    if status in {"COMPLETED", "DONE", "SUCCESS"}:
        return "SUCCEEDED"
    if status in {"QUEUED"}:
        return "IN_QUEUE"
    if status in {"RUNNING", "PROCESSING"}:
        return "IN_PROGRESS"
    if status in {"CANCELLED"}:
        return "CANCELED"
    return status or "UNKNOWN"


def _normalize_create_video_response(data: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return {"output": {"task_id": "", "task_status": "UNKNOWN"}, "raw": data}

    if isinstance(data.get("output"), dict):
        return data

    request_id = str(data.get("request_id", "")).strip()
    status = _map_task_status(str(data.get("status", "")).strip())
    if request_id:
        return {
            "output": {
                "task_id": request_id,
                "task_status": status or "IN_QUEUE",
                "status_url": data.get("status_url", ""),
                "response_url": data.get("response_url", ""),
                "cancel_url": data.get("cancel_url", ""),
            },
            "raw": data,
        }

    return {"output": {"task_id": "", "task_status": status or "UNKNOWN"}, "raw": data}


def _normalize_query_video_response(data: Dict[str, Any], task_id: str) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return {
            "output": {
                "task_id": task_id,
                "task_status": "UNKNOWN",
                "video_url": "",
            },
            "raw": data,
        }

    if isinstance(data.get("output"), dict):
        output = dict(data.get("output", {}))
        output["task_id"] = output.get("task_id") or task_id
        output["task_status"] = _map_task_status(str(output.get("task_status", "")))
        return {**data, "output": output}

    status = _map_task_status(str(data.get("status", "")).strip())
    result = data.get("result") if isinstance(data.get("result"), dict) else {}
    video = result.get("video") if isinstance(result.get("video"), dict) else {}
    video_url = str(video.get("url", "") or "").strip()
    request_id = str(data.get("request_id", "") or task_id)

    return {
        "output": {
            "task_id": request_id,
            "task_status": status or "UNKNOWN",
            "video_url": video_url,
            "url": video_url,
            "status_url": data.get("status_url", ""),
            "response_url": data.get("response_url", ""),
            "cancel_url": data.get("cancel_url", ""),
        },
        "raw": data,
    }


def _create_video_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not _has_qiniu_video_credential():
        raise RuntimeError("QINIU_VIDEO_API_KEY or QINIU_AK/QINIU_SK is missing in .env")

    prompt = str(payload.get("prompt", "")).strip()
    if not prompt:
        raise ValueError("Video prompt is required.")

    model = payload.get("model", QINIU_VIDEO_MODEL)
    size = payload.get("size", "1280*720")
    duration = int(payload.get("duration", 10))
    prompt_extend = bool(payload.get("prompt_extend", True))

    create_path = _pick_vidu_create_path(payload, str(model), QINIU_VIDEO_CREATE_PATH)
    is_vidu_queue = _looks_like_vidu_queue_path(create_path)

    headers = _build_qiniu_headers("video", include_content_type=True)
    if QINIU_ENABLE_ASYNC_HEADER:
        headers["X-DashScope-Async"] = "enable"

    if is_vidu_queue:
        body: Dict[str, Any] = {
            "prompt": prompt,
            "duration": duration,
            "resolution": str(payload.get("resolution", "")).strip() or _size_to_vidu_resolution(str(size)),
            "movement_amplitude": str(payload.get("movement_amplitude", "auto")).strip() or "auto",
            "seed": int(payload.get("seed", 0) or 0),
            "is_rec": bool(payload.get("is_rec", False)),
            "audio": bool(payload.get("audio", False)),
        }

        if str(payload.get("voice_id", "")).strip():
            body["voice_id"] = str(payload.get("voice_id", "")).strip()

        if "start-end-to-video" in str(create_path):
            start_image_url = str(payload.get("start_image_url", "")).strip()
            end_image_url = str(payload.get("end_image_url", "")).strip()
            if not start_image_url or not end_image_url:
                raise ValueError("start_image_url and end_image_url are required for start-end-to-video endpoint.")
            body["start_image_url"] = start_image_url
            body["end_image_url"] = end_image_url
        elif "text-to-video" in str(create_path):
            body["style"] = str(payload.get("style", "general")).strip() or "general"
            body["aspect_ratio"] = str(payload.get("aspect_ratio", "16:9")).strip() or "16:9"
            body["bgm"] = bool(payload.get("bgm", False))
        else:
            image_url = str(payload.get("image_url", "")).strip()
            if not image_url:
                raise ValueError("image_url is required for image-to-video endpoint.")
            body["image_url"] = image_url
    else:
        body = {
            "model": model,
            "input": {"prompt": prompt},
            "parameters": {
                "size": size,
                "duration": duration,
                "duration_seconds": duration,
                "durationSeconds": duration,
                "prompt_extend": prompt_extend,
                "watermark": False,
            },
        }

    last_error: Optional[requests.HTTPError] = None
    url_candidates = _build_url_candidates(QINIU_VIDEO_BASE_URL, create_path)

    for idx, url in enumerate(url_candidates):
        try:
            response = _request_no_proxy("POST", url, headers=headers, json=body, timeout=60, verify=False)
            response.raise_for_status()
            normalized = _normalize_create_video_response(response.json())
            return {
                **normalized,
                "meta": _build_video_cost_meta(str(model), str(size), duration, payload),
            }
        except requests.HTTPError as err:
            last_error = err
            can_retry = idx < len(url_candidates) - 1 and _is_not_found_or_method_not_allowed(err)
            if can_retry:
                continue
            raise

    if last_error:
        raise last_error
    raise RuntimeError("Video task creation failed")


def _query_video_task(task_id: str) -> Dict[str, Any]:
    if not _has_qiniu_video_credential():
        raise RuntimeError("QINIU_VIDEO_API_KEY or QINIU_AK/QINIU_SK is missing in .env")

    task_path = QINIU_VIDEO_TASK_PATH_TEMPLATE.format(task_id=task_id)
    headers = _build_qiniu_headers("video", include_content_type=False)

    last_error: Optional[requests.HTTPError] = None
    url_candidates = _build_url_candidates(QINIU_VIDEO_BASE_URL, task_path)

    for idx, url in enumerate(url_candidates):
        try:
            response = _request_no_proxy("GET", url, headers=headers, timeout=60, verify=False)
            response.raise_for_status()
            return _normalize_query_video_response(response.json(), task_id)
        except requests.HTTPError as err:
            last_error = err
            can_retry = idx < len(url_candidates) - 1 and _is_not_found_or_method_not_allowed(err)
            if can_retry:
                continue
            raise

    if last_error:
        raise last_error
    raise RuntimeError("Video task query failed")


def _qiniu_web_search(query: str, max_results: int = 10, search_type: str = "web") -> Dict[str, Any]:
    if not QINIU_TEXT_API_KEY and not (QINIU_AK and QINIU_SK):
        raise RuntimeError("QINIU_TEXT_API_KEY (or OPENAI_API_KEY) is missing in .env")

    payload = {
        "query": query,
        "max_results": int(max_results),
        "search_type": search_type,
    }
    url = _resolve_url(QINIU_LLM_BASE_URL, QINIU_WEB_SEARCH_PATH)
    headers = _build_qiniu_headers("text", include_content_type=True)
    response = _request_no_proxy("POST", url, headers=headers, json=payload, timeout=60, verify=False)
    response.raise_for_status()
    return response.json()


def _extend_video_prompts(
    total_duration: int,
    segment_duration: int,
    base_prompt: str,
    provider: str,
) -> List[Dict[str, Any]]:
    if total_duration <= 0:
        raise ValueError("total_duration must be positive")

    segment_duration = max(1, min(segment_duration, 10))
    segments: List[Dict[str, Any]] = []

    remaining = total_duration
    index = 1
    history: List[Dict[str, Any]] = []

    while remaining > 0:
        current_duration = min(segment_duration, remaining)

        if index == 1:
            segment_prompt = (
                f"【长视频第1段（0-{current_duration}秒）】在整体设定基础上，"
                f"生成这一段的详细画面描述，用于文生视频提示词。整体提示如下：\n{base_prompt}"
            )
        else:
            system_prompt = (
                "你是视频提示词续写助手。现在有一个长视频被拆成多段，每段约10秒。"
                "你需要根据前面已经生成的各段提示词，总结已经发生的剧情，并继续写出下一段的提示词，"
                "保证人物、场景、风格和镜头运动尽量连贯。输出一段可直接用于文生视频的中文提示词，不要解释。"
            )

            user_prompt = (
                "整体设定（用户原始提示）如下：\n"
                f"{base_prompt}\n\n"
                "前面已经规划好的各段提示词与时长：\n"
                f"{__import__('json').dumps(history, ensure_ascii=False, indent=2)}\n\n"
                f"现在请继续编写第{index}段（预计时长 {current_duration} 秒）的提示词，只输出这一段的提示词。"
            )

            segment_prompt = _call_provider_text(provider, system_prompt, user_prompt)

        segment = {
            "index": index,
            "duration": current_duration,
            "prompt": segment_prompt.strip(),
        }
        segments.append(segment)
        history.append(segment)

        remaining -= current_duration
        index += 1

    return segments
