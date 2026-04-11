from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _default_project_state() -> Dict[str, Any]:
    def _empty_review_lab(stage: str) -> Dict[str, Any]:
        return {
            "latest_review": {
                "summary": "",
                "overall_score": 0,
                "dimensions": [],
                "top_issues": [],
                "priority_actions": [],
                "low_score_dimensions": [],
            },
            "rewrite_candidates": [],
            "last_review_stage": stage,
            "last_review_time": "",
        }

    return {
        "story_inputs": {
            "idea": "",
            "theme": "",
            "tone": "",
            "structure": "",
            "template_id": "",
        },
        "story_card": None,
        "review_labs": {
            "story_engine": _empty_review_lab("story_engine"),
            "workshop": _empty_review_lab("workshop"),
            "storyboard": _empty_review_lab("storyboard"),
        },
        "review_panel_state": {
            "story_engine": False,
            "workshop": False,
            "storyboard": False,
        },
        "cover_lab": {
            "current_title": "",
            "style_preference": "",
            "focus_point": "",
            "summary": "",
            "main_title": "",
            "subtitle": "",
            "hook_lines": [],
            "visual_direction": "",
            "layout_direction": "",
            "color_palette": "",
            "image_prompt": "",
            "generated_image_url": "",
            "image_model": "",
            "image_size": "",
            "image_task_id": "",
            "image_task_status": "",
            "image_status_message": "",
            "updated_at": "",
        },
        "title_lab": {
            "current_title": "",
            "summary": "",
            "evaluated_title": None,
            "recommended_title_id": "",
            "recommended_reason": "",
            "title_suggestions": [],
            "topic_tags": [],
            "updated_at": "",
        },
        "workshop": None,
        "storyboard": None,
        "video_lab": {
            "script": "",
            "prompt": "",
            "image_url": "",
            "start_image_url": "",
            "end_image_url": "",
            "task_id": "",
            "task_status": "",
            "video_url": "",
            "auto_poll": True,
            "last_check_time": "",
            "long_segments": [],
            "total_duration": 0,
            "filename_prefix": "",
            "long_chain_by_last_frame": False,
            "long_model": "",
            "long_size": "",
            "long_prompt_extend": True,
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
