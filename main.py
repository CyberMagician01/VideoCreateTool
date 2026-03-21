import json
from io import BytesIO
import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import warnings

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_file
from docx import Document
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas


warnings.filterwarnings("ignore", message="Unverified HTTPS request")
load_dotenv()


QINIU_AK = os.getenv("QINIU_AK", os.getenv("AK", "")).strip()
QINIU_SK = os.getenv("QINIU_SK", os.getenv("SK", "")).strip()
QINIU_TEXT_API_KEY = os.getenv(
    "QINIU_TEXT_API_KEY",
    os.getenv("text_api_key", os.getenv("OPENAI_API_KEY", "")),
).strip()
QINIU_VIDEO_API_KEY = os.getenv("QINIU_VIDEO_API_KEY", os.getenv("video_api_key", "")).strip()
QINIU_LLM_MODEL = os.getenv("QINIU_LLM_MODEL", os.getenv("QWEN_MODEL", "qwen-plus"))
QINIU_LLM_BASE_URL = os.getenv(
    "QINIU_LLM_BASE_URL",
    os.getenv("QWEN_BASE_URL", os.getenv("OPENAI_BASE_URL", "")),
).strip()
QINIU_VIDEO_MODEL = os.getenv("QINIU_VIDEO_MODEL", os.getenv("WAN_MODEL", "wan2.6-t2v"))
QINIU_VIDEO_BASE_URL = os.getenv("QINIU_VIDEO_BASE_URL", os.getenv("WAN_BASE_URL", "")).strip()
QINIU_VIDEO_CREATE_PATH = os.getenv(
    "QINIU_VIDEO_CREATE_PATH", "/services/aigc/video-generation/video-synthesis"
).strip()
QINIU_VIDEO_TASK_PATH_TEMPLATE = os.getenv("QINIU_VIDEO_TASK_PATH_TEMPLATE", "/tasks/{task_id}").strip()
QINIU_VIDU_Q3_TEXT_TO_VIDEO_PATH = os.getenv(
    "QINIU_VIDU_Q3_TEXT_TO_VIDEO_PATH", "/queue/fal-ai/vidu/q3/text-to-video/turbo"
).strip()
QINIU_VIDU_Q3_IMAGE_TO_VIDEO_PATH = os.getenv(
    "QINIU_VIDU_Q3_IMAGE_TO_VIDEO_PATH", "/queue/fal-ai/vidu/q3/image-to-video/turbo"
).strip()
QINIU_VIDU_Q3_START_END_TO_VIDEO_PATH = os.getenv(
    "QINIU_VIDU_Q3_START_END_TO_VIDEO_PATH", "/queue/fal-ai/vidu/q3/start-end-to-video/turbo"
).strip()
QINIU_WEB_SEARCH_PATH = os.getenv("QINIU_WEB_SEARCH_PATH", "/search/web").strip()
QINIU_LLM_FALLBACK_MODELS = [
    item.strip()
    for item in os.getenv("QINIU_LLM_FALLBACK_MODELS", "").split(",")
    if item.strip()
]
QINIU_ENABLE_ASYNC_HEADER = os.getenv("QINIU_ENABLE_ASYNC_HEADER", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

DEFAULT_PROVIDER = os.getenv("DEFAULT_PROVIDER", "qiniu")


MODEL_PROVIDERS = {
    "qiniu": {
        "name": "七牛云大模型网关",
        "model": QINIU_LLM_MODEL,
        "base_url": QINIU_LLM_BASE_URL,
        "type": "qiniu_openai_compatible",
        "requires_qiniu_credential": True,
    }
}


app = Flask(__name__, template_folder="templates", static_folder="static")


DATA_DIR = Path(__file__).resolve().parent / "data"
DB_PATH = DATA_DIR / "projects.db"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _default_project_state() -> Dict[str, Any]:
    return {
        "story_card": None,
        "workshop": None,
        "storyboard": None,
        "video_lab": {
            "script": "",
            "prompt": "",
            "task_id": "",
            "task_status": "",
            "video_url": "",
            "auto_poll": True,
            "last_check_time": "",
            "long_segments": [],
            "total_duration": 0,
            "filename_prefix": "",
        },
    }


def _get_db_conn() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_projects_db() -> None:
    with _get_db_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                creator TEXT DEFAULT '',
                description TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                cover_image TEXT DEFAULT '',
                last_provider TEXT DEFAULT '',
                deleted INTEGER DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS project_states (
                project_id INTEGER PRIMARY KEY,
                state_json TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            )
            """
        )
        conn.commit()


def _row_to_project_meta(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "creator": row["creator"] or "",
        "description": row["description"] or "",
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "cover_image": row["cover_image"] or "",
        "last_provider": row["last_provider"] or "",
    }


def _create_project(
    conn: sqlite3.Connection,
    *,
    name: str,
    creator: str = "",
    description: str = "",
    state: Optional[Dict[str, Any]] = None,
    cover_image: str = "",
    last_provider: str = "",
) -> Dict[str, Any]:
    now = _utc_now_iso()
    state_payload = state if isinstance(state, dict) else _default_project_state()
    cur = conn.execute(
        """
        INSERT INTO projects(name, creator, description, created_at, updated_at, cover_image, last_provider, deleted)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        """,
        (name.strip(), creator.strip(), description.strip(), now, now, cover_image, last_provider),
    )
    project_id = cur.lastrowid
    conn.execute(
        """
        INSERT INTO project_states(project_id, state_json, updated_at)
        VALUES (?, ?, ?)
        """,
        (project_id, json.dumps(state_payload, ensure_ascii=False), now),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    return _row_to_project_meta(row)


def _list_projects(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT * FROM projects
        WHERE deleted = 0
        ORDER BY datetime(updated_at) DESC, id DESC
        """
    ).fetchall()
    return [_row_to_project_meta(r) for r in rows]


def _ensure_default_project(conn: sqlite3.Connection) -> Dict[str, Any]:
    projects = _list_projects(conn)
    if projects:
        return projects[0]
    return _create_project(conn, name="未命名项目")


def _get_project_with_state(conn: sqlite3.Connection, project_id: int) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        "SELECT * FROM projects WHERE id = ? AND deleted = 0",
        (project_id,),
    ).fetchone()
    if not row:
        return None

    state_row = conn.execute(
        "SELECT state_json FROM project_states WHERE project_id = ?",
        (project_id,),
    ).fetchone()

    state_obj: Dict[str, Any] = _default_project_state()
    if state_row and state_row["state_json"]:
        try:
            parsed = json.loads(state_row["state_json"])
            if isinstance(parsed, dict):
                state_obj = parsed
        except json.JSONDecodeError:
            state_obj = _default_project_state()

    return {
        "project": _row_to_project_meta(row),
        "state": state_obj,
    }


_init_projects_db()


@dataclass
class AgentRequest:
    stage: str
    payload: Dict[str, Any]
    provider: str = DEFAULT_PROVIDER


def _extract_json(text: str) -> Dict[str, Any]:
    """Extract the first JSON object from model output and parse it safely."""
    text = text.strip()

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("Model did not return JSON.")

    return json.loads(match.group(0))


def _resolve_url(base_url: str, path_or_url: str) -> str:
    text = str(path_or_url or "").strip()
    if text.startswith("http://") or text.startswith("https://"):
        return text

    base = str(base_url or "").strip().rstrip("/")
    if not base:
        raise RuntimeError("QINIU base url is missing in .env")

    if not text:
        return base

    if not text.startswith("/"):
        text = f"/{text}"
    return f"{base}{text}"


def _build_url_candidates(base_url: str, path_or_url: str) -> List[str]:
    """Build URL candidates for gateways that differ on /v1 vs /api/v1 prefix."""
    primary = _resolve_url(base_url, path_or_url)
    candidates = [primary]

    base = str(base_url or "").strip().rstrip("/")
    path = str(path_or_url or "").strip()

    if path and not path.startswith("/"):
        path = f"/{path}"

    if base.endswith("/api/v1"):
        alt_base = base[: -len("/api/v1")] + "/v1"
        candidates.append(f"{alt_base}{path}")
    elif base.endswith("/v1"):
        alt_base = base[: -len("/v1")] + "/api/v1"
        candidates.append(f"{alt_base}{path}")

    deduped: List[str] = []
    for url in candidates:
        if url not in deduped:
            deduped.append(url)
    return deduped


def _is_not_found_or_method_not_allowed(err: requests.HTTPError) -> bool:
    response = err.response
    if response is None:
        return False

    if response.status_code in {404, 405}:
        return True

    detail = response.text.lower()
    return ("not found" in detail) or ("method not allowed" in detail)


def _build_qiniu_aksk_headers(*, include_content_type: bool = True) -> Dict[str, str]:
    if not QINIU_AK or not QINIU_SK:
        raise RuntimeError("QINIU_AK or QINIU_SK is missing in .env")

    headers = {
        "X-Qiniu-AK": QINIU_AK,
        "X-Qiniu-SK": QINIU_SK,
        # 部分七牛网关使用自定义授权头，这里统一附加，具体格式可按网关文档调整。
        "Authorization": f"QiniuAKSK {QINIU_AK}:{QINIU_SK}",
    }
    if include_content_type:
        headers["Content-Type"] = "application/json"
    return headers


def _has_qiniu_text_credential() -> bool:
    return bool(QINIU_TEXT_API_KEY or (QINIU_AK and QINIU_SK))


def _has_qiniu_video_credential() -> bool:
    return bool(QINIU_VIDEO_API_KEY or QINIU_TEXT_API_KEY or (QINIU_AK and QINIU_SK))


def _build_qiniu_headers(scope: str, *, include_content_type: bool = True) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    if include_content_type:
        headers["Content-Type"] = "application/json"

    # 优先走 sk-... API Key，和你当前网关报错信息保持一致。
    if scope == "text" and QINIU_TEXT_API_KEY:
        headers["Authorization"] = f"Bearer {QINIU_TEXT_API_KEY}"
        return headers
    if scope == "video" and QINIU_VIDEO_API_KEY:
        headers["Authorization"] = f"Bearer {QINIU_VIDEO_API_KEY}"
        return headers
    if scope == "video" and QINIU_TEXT_API_KEY:
        headers["Authorization"] = f"Bearer {QINIU_TEXT_API_KEY}"
        return headers

    return {**headers, **_build_qiniu_aksk_headers(include_content_type=False)}


def _get_model_candidates(primary_model: str) -> List[str]:
    candidates: List[str] = []
    if primary_model:
        candidates.append(primary_model)
    for item in QINIU_LLM_FALLBACK_MODELS:
        if item not in candidates:
            candidates.append(item)
    return candidates


def _call_provider_json(provider: str, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    provider_config = MODEL_PROVIDERS.get(provider)
    if not provider_config:
        raise ValueError(f"Unknown provider: {provider}")

    if provider_config.get("requires_qiniu_credential") and (not _has_qiniu_text_credential()):
        raise RuntimeError("QINIU_TEXT_API_KEY or QINIU_AK/QINIU_SK is missing in .env")
    
    return _call_openai_compatible_json(provider_config, system_prompt, user_prompt)


def _call_provider_text(provider: str, system_prompt: str, user_prompt: str) -> str:
    provider_config = MODEL_PROVIDERS.get(provider)
    if not provider_config:
        raise ValueError(f"Unknown provider: {provider}")

    if provider_config.get("requires_qiniu_credential") and (not _has_qiniu_text_credential()):
        raise RuntimeError("QINIU_TEXT_API_KEY or QINIU_AK/QINIU_SK is missing in .env")
    
    return _call_openai_compatible_text(provider_config, system_prompt, user_prompt)


def _call_openai_compatible_json(provider_config: Dict[str, Any], system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    url = _resolve_url(provider_config.get("base_url", ""), "/chat/completions")
    headers: Dict[str, str] = {"Content-Type": "application/json"}
    if provider_config.get("type") == "qiniu_openai_compatible":
        headers.update(_build_qiniu_headers("text", include_content_type=False))
    else:
        api_key = str(provider_config.get("api_key", "")).strip()
        if not api_key:
            raise RuntimeError(f"{provider_config.get('name', 'Provider')} API key is missing in .env")
        headers["Authorization"] = f"Bearer {api_key}"
    model_candidates = _get_model_candidates(str(provider_config.get("model", "")).strip())
    if not model_candidates:
        raise RuntimeError("No model configured for qiniu provider")

    last_error: Optional[Exception] = None
    for model_name in model_candidates:
        body = {
            "model": model_name,
            "temperature": 0.7,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        try:
            response = requests.post(url, headers=headers, json=body, timeout=60, verify=False)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return _extract_json(content)
        except requests.HTTPError as e:
            last_error = e
            detail = (e.response.text if e.response is not None else "").lower()
            # 七牛网关常见报错：模型无可用通道，则自动尝试下一个候选模型。
            if "no available channels for model" in detail:
                continue
            raise

    if last_error:
        raise last_error
    raise RuntimeError("Model request failed")


def _call_openai_compatible_text(provider_config: Dict[str, Any], system_prompt: str, user_prompt: str) -> str:
    url = _resolve_url(provider_config.get("base_url", ""), "/chat/completions")
    headers: Dict[str, str] = {"Content-Type": "application/json"}
    if provider_config.get("type") == "qiniu_openai_compatible":
        headers.update(_build_qiniu_headers("text", include_content_type=False))
    else:
        api_key = str(provider_config.get("api_key", "")).strip()
        if not api_key:
            raise RuntimeError(f"{provider_config.get('name', 'Provider')} API key is missing in .env")
        headers["Authorization"] = f"Bearer {api_key}"
    model_candidates = _get_model_candidates(str(provider_config.get("model", "")).strip())
    if not model_candidates:
        raise RuntimeError("No model configured for qiniu provider")

    last_error: Optional[Exception] = None
    for model_name in model_candidates:
        body = {
            "model": model_name,
            "temperature": 0.8,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        try:
            response = requests.post(url, headers=headers, json=body, timeout=60, verify=False)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except requests.HTTPError as e:
            last_error = e
            detail = (e.response.text if e.response is not None else "").lower()
            if "no available channels for model" in detail:
                continue
            raise

    if last_error:
        raise last_error
    raise RuntimeError("Model request failed")


def _call_qwen_json(system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    return _call_provider_json(DEFAULT_PROVIDER, system_prompt, user_prompt)


def _call_qwen_text(system_prompt: str, user_prompt: str) -> str:
    return _call_provider_text(DEFAULT_PROVIDER, system_prompt, user_prompt)


def _video_script_prompt(payload: Dict[str, Any]) -> str:
    return f"""
你是短剧编导，请直接输出一段可拍可生视频的短剧脚本。

输入信息：
- 题材：{payload.get('genre', '')}
- 核心设定：{payload.get('idea', '')}
- 人物：{payload.get('roles', '')}
- 风格：{payload.get('style', '')}
- 时长：{payload.get('duration_sec', 10)} 秒

输出要求：
1) 先给出“标题”。
2) 再给“短剧脚本（分镜级）”，包含 4-6 个镜头，每个镜头写画面、动作、台词/音效。
3) 最后给“视频生成提示词（中文）”，用于文生视频，保证画面连贯。
4) 全文中文，简洁有戏剧冲突。
""".strip()


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
        output = data.get("output", {})
        output = dict(output)
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
            response = requests.post(url, headers=headers, json=body, timeout=60, verify=False)
            response.raise_for_status()
            return _normalize_create_video_response(response.json())
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
            response = requests.get(url, headers=headers, timeout=60, verify=False)
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
    if not _has_qiniu_text_credential():
        raise RuntimeError("QINIU_TEXT_API_KEY (or OPENAI_API_KEY) is missing in .env")

    payload = {
        "query": query,
        "max_results": int(max_results),
        "search_type": search_type,
    }
    url = _resolve_url(QINIU_LLM_BASE_URL, QINIU_WEB_SEARCH_PATH)
    headers = _build_qiniu_headers("text", include_content_type=True)
    response = requests.post(url, headers=headers, json=payload, timeout=60, verify=False)
    response.raise_for_status()
    return response.json()


def _extend_video_prompts(
    total_duration: int,
    segment_duration: int,
    base_prompt: str,
    provider: str,
) -> List[Dict[str, Any]]:
    """Split long video into segments and let LLM draft each segment prompt.

    This works purely在文本层面：模型根据整体提示和前面各段的提示词，续写后续段落的描述，
    以便逐段调用万相文生视频接口。这里不会真正解析视频画面。
    """

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
                "你是视频提示词续写助手。现在有一个长视频被拆成多段，每段约10秒。"\
                "你需要根据前面已经生成的各段提示词，总结已经发生的剧情，并继续写出下一段的提示词，"\
                "保证人物、场景、风格和镜头运动尽量连贯。输出一段可直接用于文生视频的中文提示词，不要解释。"
            )

            user_prompt = (
                "整体设定（用户原始提示）如下：\n"\
                f"{base_prompt}\n\n"\
                "前面已经规划好的各段提示词与时长：\n"\
                f"{json.dumps(history, ensure_ascii=False, indent=2)}\n\n"\
                f"现在请继续编写第{index}段（预计时长 {current_duration} 秒）的提示词，只输出这一段的提示词。"
            )

            segment_prompt = _call_provider_text(provider, system_prompt, user_prompt)

        segment = {
            "index": index,
            "duration": current_duration,
            "prompt": segment_prompt.strip(),
        }
        segments.append(segment)
        history.append({
            "index": index,
            "duration": current_duration,
            "prompt": segment_prompt.strip(),
        })

        remaining -= current_duration
        index += 1

    return segments


def _story_engine_prompt(payload: Dict[str, Any]) -> str:
    return f"""
你是短剧创作智能体的第一层：故事引擎。
请基于用户输入，输出严格 JSON（不要解释文字）。

用户输入：
- 创意: {payload.get('idea', '')}
- 主题偏好: {payload.get('theme', '')}
- 情绪基调: {payload.get('tone', '')}
- 结构模板偏好: {payload.get('structure', '')}

JSON schema:
{{
  "story_card": {{
    "logline": "一句话故事梗概",
    "theme": "核心主题",
    "tone": "情绪基调",
    "structure_template": "所用结构模板",
    "core_conflict": "核心冲突",
    "anchor_points": ["开端锚点", "转折锚点", "高潮锚点", "结局锚点"],
    "hook": "前三秒抓人钩子",
    "ending_type": "开放式/反转式/治愈式等"
  }},
  "next_questions": ["建议用户补充的问题1", "建议用户补充的问题2"]
}}
""".strip()


def _workshop_prompt(payload: Dict[str, Any]) -> str:
    story_card = payload.get("story_card", {})
    role_requirements = payload.get("role_requirements", "")
    plot_requirements = payload.get("plot_requirements", "")

    return f"""
你是短剧创作智能体的第二层：剧本工坊。
请基于故事卡生成角色、情节节点、对白草稿，输出严格 JSON。

故事卡：
{json.dumps(story_card, ensure_ascii=False, indent=2)}

用户角色要求：{role_requirements}
用户情节要求：{plot_requirements}

JSON schema:
{{
  "characters": [
    {{
      "name": "角色名",
      "tags": ["职业", "性格", "目标", "缺陷"],
      "motivation": "核心动机",
      "arc": "角色弧光"
    }}
  ],
  "relationships": [
    {{"from": "A", "to": "B", "type": "关系类型", "tension": "冲突点"}}
  ],
  "plot_nodes": [
    {{
      "id": "N1",
      "template_stage": "激励事件/第一次转折/高潮等",
      "summary": "节点剧情",
      "consistency_check": "若存在潜在矛盾则提示，否则写无",
      "dialogue_draft": ["角色: 台词"],
      "action_draft": "动作与场面调度"
    }}
  ],
  "timeline_view": ["按时间顺序的节点ID"],
  "card_wall_groups": [
    {{"group": "铺垫/冲突/反转", "node_ids": ["N1", "N2"]}}
  ]
}}
""".strip()


def _storyboard_prompt(payload: Dict[str, Any]) -> str:
    workshop = payload.get("workshop", {})
    style = payload.get("visual_style", "")

    return f"""
你是短剧创作智能体的第三层：分镜工厂。
请将剧本节点转换为分镜卡，输出严格 JSON。

剧本工坊结果：
{json.dumps(workshop, ensure_ascii=False, indent=2)}

视觉风格要求：{style}

JSON schema:
{{
  "storyboards": [
    {{
      "shot_id": "S1",
      "related_node_id": "N1",
      "shot_type": "特写/中景/全景",
      "camera_movement": "固定/推/拉/摇/跟拍",
      "visual_description": "画面内容",
      "dialogue_or_sfx": "对白或音效",
      "duration_sec": 4,
      "shooting_note": "拍摄备注"
    }}
  ],
  "estimated_total_duration_sec": 60,
  "export_ready_checklist": ["服化道", "场景", "收音", "灯光"]
}}
""".strip()


def _command_prompt(payload: Dict[str, Any]) -> str:
    command = payload.get("command", "")
    project_state = payload.get("project_state", {})

    return f"""
你是短剧创作助手的全局指令执行器。
请读取当前状态并执行用户自然语言命令，输出严格 JSON。

用户命令：{command}
当前项目状态：
{json.dumps(project_state, ensure_ascii=False, indent=2)}

JSON schema:
{{
  "command_understanding": "你对命令的理解",
  "updated_state": {{
    "story_card": {{}} ,
    "workshop": {{}} ,
    "storyboard": {{}}
  }},
  "consistency_report": ["一致性检查结果"],
  "suggestions": ["下一步建议"]
}}
""".strip()


def _export_markdown(payload: Dict[str, Any]) -> Dict[str, Any]:
    story_card = payload.get("story_card", {})
    workshop = payload.get("workshop", {})
    storyboard = payload.get("storyboard", {})

    lines: List[str] = []
    lines.append("# AI短剧项目导出")
    lines.append("")
    lines.append("## 1. 故事卡")
    lines.append(f"- Logline: {story_card.get('logline', '')}")
    lines.append(f"- 主题: {story_card.get('theme', '')}")
    lines.append(f"- 基调: {story_card.get('tone', '')}")
    lines.append(f"- 结构模板: {story_card.get('structure_template', '')}")
    lines.append(f"- 核心冲突: {story_card.get('core_conflict', '')}")
    lines.append("")

    lines.append("## 2. 角色设定")
    for c in workshop.get("characters", []):
        tags = ", ".join(c.get("tags", []))
        lines.append(f"- {c.get('name', '未命名角色')} | 标签: {tags} | 动机: {c.get('motivation', '')}")
    lines.append("")

    lines.append("## 3. 情节脉络")
    for n in workshop.get("plot_nodes", []):
        lines.append(
            f"- {n.get('id', '')} [{n.get('template_stage', '')}] {n.get('summary', '')}"
        )
    lines.append("")

    lines.append("## 4. 分镜表")
    lines.append("| 镜头ID | 对应节点 | 景别 | 运镜 | 画面 | 对白/音效 | 时长(秒) |")
    lines.append("|---|---|---|---|---|---|---|")
    for s in storyboard.get("storyboards", []):
        lines.append(
            "| {shot_id} | {node} | {shot_type} | {move} | {visual} | {sound} | {duration} |".format(
                shot_id=s.get("shot_id", ""),
                node=s.get("related_node_id", ""),
                shot_type=s.get("shot_type", ""),
                move=s.get("camera_movement", ""),
                visual=str(s.get("visual_description", "")).replace("|", "\\|"),
                sound=str(s.get("dialogue_or_sfx", "")).replace("|", "\\|"),
                duration=s.get("duration_sec", ""),
            )
        )

    return {"markdown": "\n".join(lines)}


def _build_docx(payload: Dict[str, Any]) -> BytesIO:
    story_card = payload.get("story_card", {})
    workshop = payload.get("workshop", {})
    storyboard = payload.get("storyboard", {})

    doc = Document()
    doc.add_heading("AI短剧项目导出", level=1)

    doc.add_heading("1. 故事卡", level=2)
    doc.add_paragraph(f"Logline: {story_card.get('logline', '')}")
    doc.add_paragraph(f"主题: {story_card.get('theme', '')}")
    doc.add_paragraph(f"基调: {story_card.get('tone', '')}")
    doc.add_paragraph(f"结构模板: {story_card.get('structure_template', '')}")
    doc.add_paragraph(f"核心冲突: {story_card.get('core_conflict', '')}")

    doc.add_heading("2. 角色设定", level=2)
    for c in workshop.get("characters", []):
        tags = ", ".join(c.get("tags", []))
        doc.add_paragraph(
            f"{c.get('name', '未命名角色')} | 标签: {tags} | 动机: {c.get('motivation', '')}",
            style="List Bullet",
        )

    doc.add_heading("3. 情节脉络", level=2)
    for n in workshop.get("plot_nodes", []):
        doc.add_paragraph(
            f"{n.get('id', '')} [{n.get('template_stage', '')}] {n.get('summary', '')}",
            style="List Bullet",
        )

    doc.add_heading("4. 分镜表", level=2)
    table = doc.add_table(rows=1, cols=7)
    headers = ["镜头ID", "对应节点", "景别", "运镜", "画面", "对白/音效", "时长(秒)"]
    header_cells = table.rows[0].cells
    for i, text in enumerate(headers):
        header_cells[i].text = text

    for s in storyboard.get("storyboards", []):
        row = table.add_row().cells
        row[0].text = str(s.get("shot_id", ""))
        row[1].text = str(s.get("related_node_id", ""))
        row[2].text = str(s.get("shot_type", ""))
        row[3].text = str(s.get("camera_movement", ""))
        row[4].text = str(s.get("visual_description", ""))
        row[5].text = str(s.get("dialogue_or_sfx", ""))
        row[6].text = str(s.get("duration_sec", ""))

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


def _register_pdf_font() -> str:
    """Use built-in CJK font to avoid local font file dependency."""
    try:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        return "STSong-Light"
    except Exception:
        return "Helvetica"


def _draw_wrapped(
    c: canvas.Canvas, text: str, font_name: str, font_size: int, x: float, y: float, width: float
) -> float:
    lines = simpleSplit(str(text), font_name, font_size, width)
    for line in lines:
        c.drawString(x, y, line)
        y -= font_size + 4
    return y


def _build_pdf(payload: Dict[str, Any]) -> BytesIO:
    story_card = payload.get("story_card", {})
    workshop = payload.get("workshop", {})
    storyboard = payload.get("storyboard", {})

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    font_name = _register_pdf_font()

    def ensure_space(y_pos: float, need: float = 28.0) -> float:
        if y_pos < need:
            c.showPage()
            c.setFont(font_name, 11)
            return height - 50
        return y_pos

    y = height - 50
    c.setFont(font_name, 16)
    c.drawString(40, y, "AI短剧项目导出")
    y -= 34

    c.setFont(font_name, 13)
    c.drawString(40, y, "1. 故事卡")
    y -= 22
    c.setFont(font_name, 11)
    for line in [
        f"Logline: {story_card.get('logline', '')}",
        f"主题: {story_card.get('theme', '')}",
        f"基调: {story_card.get('tone', '')}",
        f"结构模板: {story_card.get('structure_template', '')}",
        f"核心冲突: {story_card.get('core_conflict', '')}",
    ]:
        y = ensure_space(y)
        y = _draw_wrapped(c, line, font_name, 11, 50, y, width - 90)

    y -= 8
    y = ensure_space(y)
    c.setFont(font_name, 13)
    c.drawString(40, y, "2. 角色设定")
    y -= 22
    c.setFont(font_name, 11)
    for ch in workshop.get("characters", []):
        y = ensure_space(y)
        text = (
            f"- {ch.get('name', '未命名角色')} | 标签: {', '.join(ch.get('tags', []))} | "
            f"动机: {ch.get('motivation', '')}"
        )
        y = _draw_wrapped(c, text, font_name, 11, 50, y, width - 90)

    y -= 8
    y = ensure_space(y)
    c.setFont(font_name, 13)
    c.drawString(40, y, "3. 情节脉络")
    y -= 22
    c.setFont(font_name, 11)
    for n in workshop.get("plot_nodes", []):
        y = ensure_space(y)
        text = f"- {n.get('id', '')} [{n.get('template_stage', '')}] {n.get('summary', '')}"
        y = _draw_wrapped(c, text, font_name, 11, 50, y, width - 90)

    y -= 8
    y = ensure_space(y)
    c.setFont(font_name, 13)
    c.drawString(40, y, "4. 分镜表")
    y -= 22
    c.setFont(font_name, 11)
    for s in storyboard.get("storyboards", []):
        y = ensure_space(y, 60)
        c.drawString(50, y, f"{s.get('shot_id', '')} | 节点: {s.get('related_node_id', '')}")
        y -= 16
        y = _draw_wrapped(
            c,
            f"景别: {s.get('shot_type', '')}  运镜: {s.get('camera_movement', '')}",
            font_name,
            11,
            60,
            y,
            width - 110,
        )
        y = _draw_wrapped(
            c,
            f"画面: {s.get('visual_description', '')}",
            font_name,
            11,
            60,
            y,
            width - 110,
        )
        y = _draw_wrapped(
            c,
            f"对白/音效: {s.get('dialogue_or_sfx', '')}  时长: {s.get('duration_sec', '')}秒",
            font_name,
            11,
            60,
            y,
            width - 110,
        )
        y -= 8

    c.save()
    buffer.seek(0)
    return buffer


@app.get("/")
def index() -> str:
    return render_template("index.html")


@app.get("/studio")
def studio() -> str:
    return render_template("studio.html")


@app.get("/visual")
def visual() -> str:
    return render_template("visual.html")


@app.get("/export-center")
def export_center() -> str:
    return render_template("export_center.html")


@app.get("/video-lab")
def video_lab() -> str:
    return render_template("video_lab.html")


@app.get("/api/providers")
def get_providers():
    providers_list = []
    for key, config in MODEL_PROVIDERS.items():
        if config.get("requires_qiniu_credential"):
            has_credential = _has_qiniu_text_credential()
        else:
            has_credential = bool(config.get("api_key"))

        providers_list.append({
            "id": key,
            "name": config["name"],
            "model": config["model"],
            "has_api_key": has_credential,
            "is_default": key == DEFAULT_PROVIDER
        })
    return jsonify({"ok": True, "providers": providers_list})


@app.get("/api/projects")
def get_projects():
    try:
        with _get_db_conn() as conn:
            projects = _list_projects(conn)
            return jsonify({"ok": True, "projects": projects})
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 500


@app.post("/api/projects")
def create_project_api():
    req_json = request.get_json(silent=True) or {}
    name = str(req_json.get("name", "")).strip()
    creator = str(req_json.get("creator", "")).strip()
    description = str(req_json.get("description", "")).strip()
    state = req_json.get("state")

    if not name:
        return jsonify({"ok": False, "error": "Project name is required."}), 400

    try:
        with _get_db_conn() as conn:
            project = _create_project(
                conn,
                name=name,
                creator=creator,
                description=description,
                state=state if isinstance(state, dict) else None,
                cover_image=str(req_json.get("cover_image", ""))[:200000],
                last_provider=str(req_json.get("last_provider", ""))[:64],
            )
            return jsonify({"ok": True, "project": project})
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 500


@app.get("/api/projects/<int:project_id>")
def get_project(project_id: int):
    try:
        with _get_db_conn() as conn:
            data = _get_project_with_state(conn, project_id)
            if not data:
                return jsonify({"ok": False, "error": "Project not found."}), 404
            return jsonify({"ok": True, **data})
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 500


@app.put("/api/projects/<int:project_id>")
def update_project(project_id: int):
    req_json = request.get_json(silent=True) or {}
    allowed_fields = {"name", "creator", "description", "cover_image", "last_provider"}
    try:
        with _get_db_conn() as conn:
            existing = conn.execute(
                "SELECT id FROM projects WHERE id = ? AND deleted = 0",
                (project_id,),
            ).fetchone()
            if not existing:
                return jsonify({"ok": False, "error": "Project not found."}), 404

            updates: List[str] = []
            params: List[Any] = []
            for field in allowed_fields:
                if field in req_json:
                    updates.append(f"{field} = ?")
                    if field in {"cover_image", "description"}:
                        params.append(str(req_json.get(field, ""))[:200000])
                    elif field == "last_provider":
                        params.append(str(req_json.get(field, ""))[:64])
                    else:
                        params.append(str(req_json.get(field, ""))[:255])

            now = _utc_now_iso()
            updates.append("updated_at = ?")
            params.append(now)
            params.append(project_id)
            conn.execute(
                f"UPDATE projects SET {', '.join(updates)} WHERE id = ?",
                tuple(params),
            )

            if "state" in req_json:
                state_obj = req_json.get("state")
                if not isinstance(state_obj, dict):
                    return jsonify({"ok": False, "error": "state must be an object."}), 400
                conn.execute(
                    """
                    INSERT INTO project_states(project_id, state_json, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(project_id) DO UPDATE SET
                        state_json = excluded.state_json,
                        updated_at = excluded.updated_at
                    """,
                    (project_id, json.dumps(state_obj, ensure_ascii=False), now),
                )

            conn.commit()
            data = _get_project_with_state(conn, project_id)
            return jsonify({"ok": True, **(data or {})})
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 500


@app.delete("/api/projects/<int:project_id>")
def delete_project(project_id: int):
    try:
        with _get_db_conn() as conn:
            existing = conn.execute(
                "SELECT id FROM projects WHERE id = ? AND deleted = 0",
                (project_id,),
            ).fetchone()
            if not existing:
                return jsonify({"ok": False, "error": "Project not found."}), 404

            now = _utc_now_iso()
            conn.execute(
                "UPDATE projects SET deleted = 1, updated_at = ? WHERE id = ?",
                (now, project_id),
            )
            conn.commit()

            fallback = _ensure_default_project(conn)
            projects = _list_projects(conn)
            return jsonify({
                "ok": True,
                "deleted_project_id": project_id,
                "fallback_project": fallback,
                "projects": projects,
            })
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 500


@app.get("/api/projects/<int:project_id>/state")
def get_project_state(project_id: int):
    try:
        with _get_db_conn() as conn:
            data = _get_project_with_state(conn, project_id)
            if not data:
                return jsonify({"ok": False, "error": "Project not found."}), 404
            return jsonify({"ok": True, "project_id": project_id, "state": data["state"]})
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 500


@app.put("/api/projects/<int:project_id>/state")
@app.post("/api/projects/<int:project_id>/state")
def put_project_state(project_id: int):
    req_json = request.get_json(silent=True) or {}
    state = req_json.get("state")
    if not isinstance(state, dict):
        return jsonify({"ok": False, "error": "state must be an object."}), 400

    try:
        with _get_db_conn() as conn:
            existing = conn.execute(
                "SELECT id FROM projects WHERE id = ? AND deleted = 0",
                (project_id,),
            ).fetchone()
            if not existing:
                return jsonify({"ok": False, "error": "Project not found."}), 404

            now = _utc_now_iso()
            conn.execute(
                """
                INSERT INTO project_states(project_id, state_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(project_id) DO UPDATE SET
                    state_json = excluded.state_json,
                    updated_at = excluded.updated_at
                """,
                (project_id, json.dumps(state, ensure_ascii=False), now),
            )
            conn.execute(
                "UPDATE projects SET updated_at = ? WHERE id = ?",
                (now, project_id),
            )
            if "cover_image" in req_json:
                conn.execute(
                    "UPDATE projects SET cover_image = ? WHERE id = ?",
                    (str(req_json.get("cover_image", ""))[:200000], project_id),
                )
            if "last_provider" in req_json:
                conn.execute(
                    "UPDATE projects SET last_provider = ? WHERE id = ?",
                    (str(req_json.get("last_provider", ""))[:64], project_id),
                )
            conn.commit()
            return jsonify({"ok": True, "project_id": project_id, "updated_at": now})
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 500


@app.post("/api/agent/compare")
def compare_providers():
    req_json = request.get_json(silent=True) or {}
    stage = req_json.get("stage")
    payload = req_json.get("payload", {})
    providers = req_json.get("providers", [])

    if not providers:
        return jsonify({"error": "No providers specified for comparison."}), 400

    results = {}
    errors = {}

    for provider in providers:
        try:
            if stage == "story_engine":
                result = _call_provider_json(
                    provider,
                    "你是专业短剧编剧策划，擅长结构化输出。",
                    _story_engine_prompt(payload),
                )
            elif stage == "workshop":
                result = _call_provider_json(
                    provider,
                    "你是专业短剧编剧，擅长角色与情节构建，并做一致性检查。",
                    _workshop_prompt(payload),
                )
            elif stage == "storyboard":
                result = _call_provider_json(
                    provider,
                    "你是分镜导演，擅长把剧情拆成可拍摄镜头。",
                    _storyboard_prompt(payload),
                )
            else:
                continue

            results[provider] = result
        except Exception as e:
            errors[provider] = str(e)

    return jsonify({
        "ok": True,
        "stage": stage,
        "results": results,
        "errors": errors
    })


@app.post("/api/agent/run")
def run_agent_stage():
    req_json = request.get_json(silent=True) or {}
    stage = req_json.get("stage")
    payload = req_json.get("payload", {})
    provider = req_json.get("provider", DEFAULT_PROVIDER)

    if stage not in {"story_engine", "workshop", "storyboard", "command", "export"}:
        return jsonify({"error": "Unsupported stage."}), 400

    try:
        if stage == "story_engine":
            result = _call_provider_json(
                provider,
                "你是专业短剧编剧策划，擅长结构化输出。",
                _story_engine_prompt(payload),
            )
        elif stage == "workshop":
            result = _call_provider_json(
                provider,
                "你是专业短剧编剧，擅长角色与情节构建，并做一致性检查。",
                _workshop_prompt(payload),
            )
        elif stage == "storyboard":
            result = _call_provider_json(
                provider,
                "你是分镜导演，擅长把剧情拆成可拍摄镜头。",
                _storyboard_prompt(payload),
            )
        elif stage == "command":
            result = _call_provider_json(
                provider,
                "你是编剧助手，负责执行自然语言编辑命令并保持一致性。",
                _command_prompt(payload),
            )
        else:
            result = _export_markdown(payload)

        return jsonify({"ok": True, "stage": stage, "provider": provider, "result": result})
    except requests.HTTPError as e:
        detail: Optional[str] = None
        if e.response is not None:
            detail = e.response.text
        return jsonify({"ok": False, "error": "Model API request failed", "detail": detail}), 502
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 500


@app.post("/api/export/docx")
def export_docx():
    req_json = request.get_json(silent=True) or {}
    payload = req_json.get("payload", req_json)
    try:
        file_obj = _build_docx(payload)
        return send_file(
            file_obj,
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            as_attachment=True,
            download_name="ai_short_drama_export.docx",
        )
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 500


@app.post("/api/export/pdf")
def export_pdf():
    req_json = request.get_json(silent=True) or {}
    payload = req_json.get("payload", req_json)
    try:
        file_obj = _build_pdf(payload)
        return send_file(
            file_obj,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="ai_short_drama_export.pdf",
        )
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 500


@app.post("/api/video/script")
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
        return jsonify({"ok": False, "error": "Model API request failed", "detail": detail}), 502
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 500


@app.post("/api/video/create-task")
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


@app.post("/api/video/create-long-task")
def create_long_video_task():
    """Create multiple short video tasks to approximate a long video.

    前端传入：
    - prompt: 整体视频提示词
    - model / size: 万相模型与分辨率
    - total_duration: 期望总时长（秒，可大于10）
    - segment_duration: 单段目标时长（可选，默认10，最大不会超过10）
    - provider: 用于续写提示词的对话模型提供商（可选，默认 DEFAULT_PROVIDER）
    """
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
        # 1) 先由对话模型规划每一段的文本提示词
        segments_plan = _extend_video_prompts(
            total_duration=total_duration,
            segment_duration=segment_duration,
            base_prompt=prompt,
            provider=provider,
        )

        # 2) 针对每一段调用万相创建视频任务
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
        return (
            jsonify({"ok": False, "error": "Long video task creation failed", "detail": detail}),
            502,
        )
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 500


@app.get("/api/video/task/<task_id>")
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


@app.post("/api/search/web")
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
