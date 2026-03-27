from typing import Any, Dict, List, Optional

import requests
from flask import Blueprint, jsonify, request

from app.config import DEFAULT_PROVIDER, QINIU_VIDEO_MODEL
from app.services.llm_service import _call_provider_text
from app.services.prompt_service import _video_script_prompt
from app.services.video_service import (
    _create_video_task,
    _extend_video_prompts,
    _qiniu_web_search,
    _query_video_task,
)

video_bp = Blueprint("video", __name__)


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
        for seg in segments_plan:
            task_payload = {
                "prompt": seg["prompt"],
                "model": video_model,
                "size": size,
                "duration": int(seg["duration"]),
                "prompt_extend": prompt_extend,
            }
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
                    "segments": segments_result,
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