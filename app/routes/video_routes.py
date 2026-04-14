from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import requests
from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from app.config import BASE_DIR, DEFAULT_PROVIDER, QINIU_VIDEO_MODEL
from app.services.llm_service import _call_provider_text
from app.services.prompt_service import _video_script_prompt
from app.services.video_service import (
    _build_video_cost_meta,
    _create_video_task,
    _extract_last_frame_to_qiniu,
    _extend_video_prompts,
    _mix_video_with_bgm,
    _upload_image_to_qiniu_kodo,
    _qiniu_web_search,
    _query_video_task,
)

video_bp = Blueprint("video", __name__)

_UPLOAD_MAX_BYTES = 15 * 1024 * 1024
_AUDIO_UPLOAD_MAX_BYTES = 50 * 1024 * 1024
_ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
_ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}
_MIME_TO_EXTENSION = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
}
_AUDIO_MIME_TO_EXTENSION = {
    "audio/mpeg": ".mp3",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mp4": ".m4a",
    "audio/aac": ".aac",
    "audio/ogg": ".ogg",
    "audio/flac": ".flac",
}


@video_bp.post("/api/video/upload-image")
def upload_video_image():
    if request.content_length and request.content_length > _UPLOAD_MAX_BYTES:
        return jsonify({"ok": False, "error": "图片过大，请上传 15MB 以内图片。"}), 413

    file = request.files.get("image")
    if file is None or not str(file.filename or "").strip():
        return jsonify({"ok": False, "error": "请先选择图片文件。"}), 400

    filename = secure_filename(file.filename)
    suffix = Path(filename).suffix.lower()
    mime_type = str(file.mimetype or "").strip().lower()

    if not suffix:
        suffix = _MIME_TO_EXTENSION.get(mime_type, "")
    if suffix not in _ALLOWED_IMAGE_EXTENSIONS:
        return jsonify({"ok": False, "error": "仅支持 jpg/jpeg/png/webp/bmp 图片。"}), 400
    if mime_type and not mime_type.startswith("image/"):
        return jsonify({"ok": False, "error": "上传文件不是图片类型。"}), 400

    upload_dir = BASE_DIR / "static" / "uploads" / "video_refs"
    upload_dir.mkdir(parents=True, exist_ok=True)

    new_name = f"{datetime.now():%Y%m%d_%H%M%S}_{uuid4().hex[:10]}{suffix}"
    save_path = upload_dir / new_name
    file.save(save_path)

    relative_url = f"/static/uploads/video_refs/{new_name}"
    local_image_url = f"{request.url_root.rstrip('/')}{relative_url}"

    object_key = f"video_refs/{new_name}"
    try:
        public_image_url = _upload_image_to_qiniu_kodo(str(save_path), object_key)
        return jsonify(
            {
                "ok": True,
                "image_url": public_image_url,
                "relative_url": relative_url,
                "filename": new_name,
                "storage": "qiniu_kodo",
            }
        )
    except Exception as upload_err:  # noqa: BLE001
        # Keep local copy for debugging, but do not return local URL for remote model consumption.
        return (
            jsonify(
                {
                    "ok": False,
                    "error": (
                        "图片已接收，但未能上传到公网对象存储。"
                        "请配置 QINIU_KODO_BUCKET / QINIU_KODO_PUBLIC_DOMAIN 后重试。"
                    ),
                    "detail": str(upload_err),
                    "local_image_url": local_image_url,
                    "filename": new_name,
                }
            ),
            500,
        )


@video_bp.post("/api/video/upload-audio")
def upload_video_audio():
    if request.content_length and request.content_length > _AUDIO_UPLOAD_MAX_BYTES:
        return jsonify({"ok": False, "error": "音频过大，请上传 50MB 以内音频。"}), 413

    file = request.files.get("audio")
    if file is None or not str(file.filename or "").strip():
        return jsonify({"ok": False, "error": "请先选择音频文件。"}), 400

    filename = secure_filename(file.filename)
    suffix = Path(filename).suffix.lower()
    mime_type = str(file.mimetype or "").strip().lower()

    if not suffix:
        suffix = _AUDIO_MIME_TO_EXTENSION.get(mime_type, "")
    if suffix not in _ALLOWED_AUDIO_EXTENSIONS:
        return jsonify({"ok": False, "error": "仅支持 mp3/wav/m4a/aac/ogg/flac 音频。"}), 400
    if mime_type and not (mime_type.startswith("audio/") or mime_type == "application/octet-stream"):
        return jsonify({"ok": False, "error": "上传文件不是音频类型。"}), 400

    upload_dir = BASE_DIR / "static" / "uploads" / "video_audio"
    upload_dir.mkdir(parents=True, exist_ok=True)

    new_name = f"{datetime.now():%Y%m%d_%H%M%S}_{uuid4().hex[:10]}{suffix}"
    save_path = upload_dir / new_name
    file.save(save_path)

    relative_url = f"/static/uploads/video_audio/{new_name}"
    local_audio_url = f"{request.url_root.rstrip('/')}{relative_url}"
    object_key = f"video_audio/{new_name}"

    try:
        public_audio_url = _upload_image_to_qiniu_kodo(str(save_path), object_key)
        return jsonify(
            {
                "ok": True,
                "audio_url": public_audio_url,
                "relative_url": relative_url,
                "filename": new_name,
                "storage": "qiniu_kodo",
            }
        )
    except Exception as upload_err:  # noqa: BLE001
        return jsonify(
            {
                "ok": True,
                "audio_url": local_audio_url,
                "relative_url": relative_url,
                "filename": new_name,
                "storage": "local",
                "warning": "音频已保存到本地，但未能上传到公网对象存储。",
                "detail": str(upload_err),
            }
        )


@video_bp.post("/api/video/mix-bgm")
def mix_video_bgm():
    req_json = request.get_json(silent=True) or {}
    payload = req_json.get("payload", req_json)
    video_url = str(payload.get("video_url", "")).strip()
    audio_url = str(payload.get("audio_url", "")).strip()
    if video_url.startswith("/"):
        video_url = f"{request.url_root.rstrip('/')}{video_url}"
    if audio_url.startswith("/"):
        audio_url = f"{request.url_root.rstrip('/')}{audio_url}"
    try:
        volume = float(payload.get("volume", 0.35))
    except (TypeError, ValueError):
        volume = 0.35

    try:
        result = _mix_video_with_bgm(video_url, audio_url, volume=volume)
        return jsonify({"ok": True, "result": result})
    except requests.HTTPError as e:
        detail: Optional[str] = None
        if e.response is not None:
            detail = e.response.text
        return jsonify({"ok": False, "error": "BGM mix failed", "detail": detail}), 502
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 500


@video_bp.post("/api/video/script")
def generate_video_script():
    req_json = request.get_json(silent=True) or {}
    payload = req_json.get("payload", req_json)
    provider = req_json.get("provider", DEFAULT_PROVIDER)

    try:
        script = _call_provider_text(
            provider,
            "你是电影短剧导演和提示词工程师，擅长输出可直接用于视频生成的文本。",
            _video_script_prompt(payload),
        )
        return jsonify({"ok": True, "script": script, "provider": provider})
    except requests.HTTPError as e:
        detail: Optional[str] = None
        if e.response is not None:
            detail = e.response.text
        return jsonify({"ok": False, "error": "Video script generation failed", "detail": detail}), 502
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 500


@video_bp.post("/api/video/create-task")
def create_video_task():
    req_json = request.get_json(silent=True) or {}
    payload = req_json.get("payload", req_json)
    try:
        result = _create_video_task(payload)
        return jsonify({"ok": True, "result": result})
    except requests.HTTPError as e:
        detail: Optional[str] = None
        if e.response is not None:
            detail = e.response.text
        return jsonify({"ok": False, "error": "Video task creation failed", "detail": detail}), 502
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 500


@video_bp.post("/api/video/create-long-task")
def create_long_video_task():
    req_json = request.get_json(silent=True) or {}
    payload = req_json.get("payload", req_json)

    prompt = str(payload.get("prompt", "")).strip()
    if not prompt:
        return jsonify({"ok": False, "error": "Video prompt is required."}), 400

    try:
        total_duration = int(payload.get("total_duration", 0))
    except (TypeError, ValueError):
        total_duration = 0

    if total_duration <= 0:
        return jsonify({"ok": False, "error": "total_duration must be a positive integer."}), 400

    try:
        segment_duration = int(payload.get("segment_duration", 10))
    except (TypeError, ValueError):
        segment_duration = 10

    segment_duration = max(1, min(segment_duration, 10))
    provider = payload.get("provider") or DEFAULT_PROVIDER
    image_url = str(payload.get("image_url", "")).strip()
    start_image_url = str(payload.get("start_image_url", "")).strip()
    end_image_url = str(payload.get("end_image_url", "")).strip()
    video_mode = str(payload.get("video_mode", "")).strip()
    chain_by_last_frame = bool(payload.get("chain_by_last_frame", True))

    try:
        segments_plan = _extend_video_prompts(
            total_duration=total_duration,
            segment_duration=segment_duration,
            base_prompt=prompt,
            provider=provider,
        )

        video_model = payload.get("model", QINIU_VIDEO_MODEL)
        size = payload.get("size", "1280*720")
        prompt_extend = bool(payload.get("prompt_extend", True))

        segments_result: List[Dict[str, Any]] = []

        if chain_by_last_frame and segments_plan:
            first_seg = segments_plan[0]
            first_payload = {
                "prompt": first_seg["prompt"],
                "model": video_model,
                "size": size,
                "duration": int(first_seg["duration"]),
                "prompt_extend": prompt_extend,
            }
            if video_mode:
                first_payload["video_mode"] = video_mode
            if image_url:
                first_payload["image_url"] = image_url
            if start_image_url:
                first_payload["start_image_url"] = start_image_url
            if end_image_url:
                first_payload["end_image_url"] = end_image_url

            first_raw = _create_video_task(first_payload)
            first_output = first_raw.get("output", {}) if isinstance(first_raw, dict) else {}
            segments_result.append(
                {
                    "index": first_seg["index"],
                    "duration": first_seg["duration"],
                    "prompt": first_seg["prompt"],
                    "task_id": first_output.get("task_id", ""),
                    "task_status": first_output.get("task_status", "PENDING"),
                }
            )

            for seg in segments_plan[1:]:
                segments_result.append(
                    {
                        "index": seg["index"],
                        "duration": seg["duration"],
                        "prompt": seg["prompt"],
                        "task_id": "",
                        "task_status": "WAITING_PREVIOUS_SEGMENT",
                    }
                )
        else:
            for seg in segments_plan:
                task_payload = {
                    "prompt": seg["prompt"],
                    "model": video_model,
                    "size": size,
                    "duration": int(seg["duration"]),
                    "prompt_extend": prompt_extend,
                }
                if video_mode:
                    task_payload["video_mode"] = video_mode
                if image_url:
                    task_payload["image_url"] = image_url
                if start_image_url:
                    task_payload["start_image_url"] = start_image_url
                if end_image_url:
                    task_payload["end_image_url"] = end_image_url

                task_raw = _create_video_task(task_payload)
                output = task_raw.get("output", {}) if isinstance(task_raw, dict) else {}
                segments_result.append(
                    {
                        "index": seg["index"],
                        "duration": seg["duration"],
                        "prompt": seg["prompt"],
                        "task_id": output.get("task_id", ""),
                        "task_status": output.get("task_status", "PENDING"),
                    }
                )

        return jsonify(
            {
                "ok": True,
                "result": {
                    "total_duration": total_duration,
                    "segment_duration": segment_duration,
                    "provider": provider,
                    "chain_by_last_frame": chain_by_last_frame,
                    "model": video_model,
                    "size": size,
                    "prompt_extend": prompt_extend,
                    "segments": segments_result,
                    "meta": _build_video_cost_meta(str(video_model), str(size), int(total_duration), payload),
                },
            }
        )
    except requests.HTTPError as e:
        detail: Optional[str] = None
        if e.response is not None:
            detail = e.response.text
        return jsonify({"ok": False, "error": "Long video task creation failed", "detail": detail}), 502
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 500


@video_bp.post("/api/video/create-next-segment-from-video")
def create_next_segment_from_video():
    req_json = request.get_json(silent=True) or {}
    payload = req_json.get("payload", req_json)

    prev_video_url = str(payload.get("prev_video_url", "")).strip()
    prompt = str(payload.get("prompt", "")).strip()
    if not prev_video_url:
        return jsonify({"ok": False, "error": "prev_video_url is required."}), 400
    if not prompt:
        return jsonify({"ok": False, "error": "prompt is required."}), 400

    try:
        duration = int(payload.get("duration", 10))
    except (TypeError, ValueError):
        duration = 10

    task_payload = {
        "prompt": prompt,
        "model": payload.get("model", QINIU_VIDEO_MODEL),
        "size": payload.get("size", "1280*720"),
        "duration": max(1, min(duration, 16)),
        "prompt_extend": bool(payload.get("prompt_extend", True)),
        "video_mode": "image",
    }

    try:
        frame_url = _extract_last_frame_to_qiniu(prev_video_url)
        task_payload["image_url"] = frame_url
        result = _create_video_task(task_payload)
        return jsonify({"ok": True, "result": result, "frame_image_url": frame_url})
    except requests.HTTPError as e:
        detail: Optional[str] = None
        if e.response is not None:
            detail = e.response.text
        return jsonify({"ok": False, "error": "Next segment task creation failed", "detail": detail}), 502
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 500


@video_bp.get("/api/video/task/<task_id>")
def get_video_task(task_id: str):
    try:
        result = _query_video_task(task_id)
        return jsonify({"ok": True, "result": result})
    except requests.HTTPError as e:
        detail: Optional[str] = None
        if e.response is not None:
            detail = e.response.text
        return jsonify({"ok": False, "error": "Video task query failed", "detail": detail}), 502
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 500


@video_bp.post("/api/search/web")
def web_search_api():
    req_json = request.get_json(silent=True) or {}
    query = str(req_json.get("query", "")).strip()
    if not query:
        return jsonify({"ok": False, "error": "query is required"}), 400

    max_results = int(req_json.get("max_results", 10))
    search_type = str(req_json.get("search_type", "web")).strip() or "web"

    try:
        result = _qiniu_web_search(query=query, max_results=max_results, search_type=search_type)
        return jsonify({"ok": True, "result": result})
    except requests.HTTPError as e:
        detail: Optional[str] = None
        if e.response is not None:
            detail = e.response.text
        return jsonify({"ok": False, "error": "Qiniu web search failed", "detail": detail}), 502
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 500
