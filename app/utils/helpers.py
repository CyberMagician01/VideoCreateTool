from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


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


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _string_list(value: Any) -> List[str]:
    if isinstance(value, list):
        result: List[str] = []
        for item in value:
            text = _as_text(item)
            if text:
                result.append(text)
        return result
    text = _as_text(value)
    return [text] if text else []


def _safe_int(value: Any, default: int = 0, *, minimum: Optional[int] = None) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    if minimum is not None:
        parsed = max(minimum, parsed)
    return parsed


def _first_present(data: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data:
            value = data.get(key)
            if value not in (None, "", [], {}):
                return value
    return None


def _derive_storyboard_prompt(shot: Dict[str, Any]) -> str:
    parts = [
        _as_text(shot.get("shot_type")),
        _as_text(shot.get("camera_movement")),
        _as_text(shot.get("visual_description")),
        _as_text(shot.get("dialogue_or_sfx")),
    ]
    return " | ".join(part for part in parts if part)