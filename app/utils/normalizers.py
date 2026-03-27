from typing import Any, Dict, Optional

from app.utils.helpers import (
    _as_text,
    _default_project_state,
    _derive_storyboard_prompt,
    _first_present,
    _safe_int,
    _string_list,
)


def _normalize_story_card(story_card: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(story_card, dict):
        return None

    normalized = {
        "logline": _as_text(story_card.get("logline")),
        "theme": _as_text(story_card.get("theme")),
        "tone": _as_text(story_card.get("tone")),
        "structure_template": _as_text(story_card.get("structure_template")),
        "core_conflict": _as_text(story_card.get("core_conflict")),
        "anchor_points": _string_list(story_card.get("anchor_points")),
        "hook": _as_text(story_card.get("hook")),
        "ending_type": _as_text(story_card.get("ending_type")),
    }
    if any(
        [
            normalized["logline"],
            normalized["theme"],
            normalized["tone"],
            normalized["structure_template"],
            normalized["core_conflict"],
            normalized["anchor_points"],
            normalized["hook"],
            normalized["ending_type"],
        ]
    ):
        return normalized
    return None


def _normalize_story_engine_result(result: Any) -> Dict[str, Any]:
    if not isinstance(result, dict):
        return {"story_card": None, "next_questions": []}
    return {
        "story_card": _normalize_story_card(result.get("story_card") if "story_card" in result else result),
        "next_questions": _string_list(result.get("next_questions")),
    }


def _normalize_character(character: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(character, dict):
        return None
    normalized = {
        "name": _as_text(_first_present(character, "name", "character_name")),
        "tags": _string_list(_first_present(character, "tags", "labels")),
        "motivation": _as_text(_first_present(character, "motivation", "goal")),
        "arc": _as_text(_first_present(character, "arc", "character_arc")),
    }
    if normalized["name"]:
        return normalized
    return None


def _normalize_relationship(relationship: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(relationship, dict):
        return None
    normalized = {
        "from": _as_text(_first_present(relationship, "from", "source", "from_character")),
        "to": _as_text(_first_present(relationship, "to", "target", "to_character")),
        "type": _as_text(_first_present(relationship, "type", "relationship", "relation")),
        "tension": _as_text(_first_present(relationship, "tension", "conflict")),
    }
    if normalized["from"] and normalized["to"]:
        return normalized
    return None


def _normalize_plot_node(node: Any, index: int) -> Optional[Dict[str, Any]]:
    if not isinstance(node, dict):
        return None
    normalized = {
        "id": _as_text(_first_present(node, "id", "node_id")) or f"N{index}",
        "template_stage": _as_text(_first_present(node, "template_stage", "phase", "stage")),
        "summary": _as_text(_first_present(node, "summary", "plot", "content", "scene_summary")),
        "location": _as_text(_first_present(node, "location", "scene_location")),
        "action_draft": _as_text(_first_present(node, "action_draft", "action", "action_description")),
        "dialogue_draft": _string_list(_first_present(node, "dialogue_draft", "dialogue", "dialogues")),
        "emotion_shift": _as_text(_first_present(node, "emotion_shift", "emotional_shift", "emotion")),
        "consistency_check": _as_text(_first_present(node, "consistency_check", "logic_check", "consistency")),
    }
    if any(
        [
            normalized["template_stage"],
            normalized["summary"],
            normalized["location"],
            normalized["action_draft"],
            normalized["dialogue_draft"],
            normalized["emotion_shift"],
            normalized["consistency_check"],
        ]
    ):
        return normalized
    return None


def _normalize_card_wall_group(group: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(group, dict):
        return None
    normalized = {
        "group": _as_text(_first_present(group, "group", "name", "title")),
        "node_ids": _string_list(_first_present(group, "node_ids", "ids")),
    }
    if normalized["group"] or normalized["node_ids"]:
        return normalized
    return None


def _normalize_workshop_result(workshop: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(workshop, dict):
        return None

    characters = [item for item in (_normalize_character(c) for c in workshop.get("characters", [])) if item]
    relationships = [
        item for item in (_normalize_relationship(r) for r in workshop.get("relationships", [])) if item
    ]
    plot_nodes = [
        item for item in (_normalize_plot_node(node, idx + 1) for idx, node in enumerate(workshop.get("plot_nodes", [])))
        if item
    ]
    available_node_ids = {node["id"] for node in plot_nodes}
    timeline_view = [
        node_id for node_id in _string_list(workshop.get("timeline_view")) if node_id in available_node_ids
    ]
    if not timeline_view:
        timeline_view = [node["id"] for node in plot_nodes]
    card_wall_groups = [
        item for item in (_normalize_card_wall_group(group) for group in workshop.get("card_wall_groups", [])) if item
    ]

    if any([characters, relationships, plot_nodes, timeline_view, card_wall_groups]):
        return {
            "characters": characters,
            "relationships": relationships,
            "plot_nodes": plot_nodes,
            "timeline_view": timeline_view,
            "card_wall_groups": card_wall_groups,
        }
    return None


def _normalize_storyboard_shot(shot: Any, index: int) -> Optional[Dict[str, Any]]:
    if not isinstance(shot, dict):
        return None
    normalized = {
        "shot_id": _as_text(_first_present(shot, "shot_id", "id")) or f"S{index}",
        "related_node_id": _as_text(_first_present(shot, "related_node_id", "node_id", "plot_node_id")),
        "shot_type": _as_text(_first_present(shot, "shot_type", "camera_size")),
        "camera_movement": _as_text(_first_present(shot, "camera_movement", "movement", "camera_motion")),
        "visual_description": _as_text(
            _first_present(shot, "visual_description", "visual", "image_description", "description")
        ),
        "dialogue_or_sfx": _as_text(_first_present(shot, "dialogue_or_sfx", "dialogue", "sound_design", "audio")),
        "duration_sec": _safe_int(_first_present(shot, "duration_sec", "duration", "estimated_duration"), 4, minimum=1),
        "shooting_note": _as_text(_first_present(shot, "shooting_note", "note", "production_note")),
        "prompt_draft": _as_text(_first_present(shot, "prompt_draft", "video_prompt", "prompt", "visual_prompt")),
    }
    if not normalized["prompt_draft"]:
        normalized["prompt_draft"] = _derive_storyboard_prompt(normalized)
    if any(
        [
            normalized["related_node_id"],
            normalized["shot_type"],
            normalized["camera_movement"],
            normalized["visual_description"],
            normalized["dialogue_or_sfx"],
            normalized["prompt_draft"],
        ]
    ):
        return normalized
    return None


def _normalize_storyboard_result(storyboard: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(storyboard, dict):
        return None

    storyboards = [
        item
        for item in (
            _normalize_storyboard_shot(shot, idx + 1)
            for idx, shot in enumerate(storyboard.get("storyboards", []))
        )
        if item
    ]
    estimated_total_duration_sec = _safe_int(
        storyboard.get("estimated_total_duration_sec"),
        sum(item["duration_sec"] for item in storyboards),
        minimum=0,
    )
    export_ready_checklist = _string_list(storyboard.get("export_ready_checklist"))

    if storyboards or export_ready_checklist or estimated_total_duration_sec:
        return {
            "storyboards": storyboards,
            "estimated_total_duration_sec": estimated_total_duration_sec,
            "export_ready_checklist": export_ready_checklist,
        }
    return None


def _normalize_video_segment(segment: Any, index: int) -> Optional[Dict[str, Any]]:
    if not isinstance(segment, dict):
        return None
    normalized = {
        "index": _safe_int(segment.get("index"), index, minimum=1),
        "duration": _safe_int(segment.get("duration"), 0, minimum=0),
        "prompt": _as_text(segment.get("prompt")),
        "task_id": _as_text(segment.get("task_id")),
        "task_status": _as_text(segment.get("task_status")),
        "video_url": _as_text(_first_present(segment, "video_url", "url")),
    }
    if any(normalized.values()):
        return normalized
    return None


def _normalize_video_lab_state(video_lab: Any) -> Dict[str, Any]:
    base = _default_project_state()["video_lab"]
    if not isinstance(video_lab, dict):
        return base

    segments = [
        item
        for item in (
            _normalize_video_segment(segment, idx + 1)
            for idx, segment in enumerate(video_lab.get("long_segments", []))
        )
        if item
    ]
    return {
        "script": _as_text(video_lab.get("script")),
        "prompt": _as_text(video_lab.get("prompt")),
        "task_id": _as_text(video_lab.get("task_id")),
        "task_status": _as_text(video_lab.get("task_status")),
        "video_url": _as_text(_first_present(video_lab, "video_url", "url")),
        "auto_poll": bool(video_lab.get("auto_poll", True)),
        "last_check_time": _as_text(video_lab.get("last_check_time")),
        "long_segments": segments,
        "total_duration": _safe_int(video_lab.get("total_duration"), 0, minimum=0),
        "filename_prefix": _as_text(video_lab.get("filename_prefix")),
    }


def _normalize_project_state(state: Any) -> Dict[str, Any]:
    return {
        "story_card": _normalize_story_card(state.get("story_card")) if isinstance(state, dict) else None,
        "workshop": _normalize_workshop_result(state.get("workshop")) if isinstance(state, dict) else None,
        "storyboard": _normalize_storyboard_result(state.get("storyboard")) if isinstance(state, dict) else None,
        "video_lab": _normalize_video_lab_state(state.get("video_lab") if isinstance(state, dict) else None),
    }


def _normalize_command_result(result: Any) -> Dict[str, Any]:
    if not isinstance(result, dict):
        return {
            "command_understanding": "",
            "updated_state": {},
            "consistency_report": [],
            "suggestions": [],
        }

    updated_state = result.get("updated_state", {})
    normalized_updated_state: Dict[str, Any] = {}
    if isinstance(updated_state, dict):
        story_card = _normalize_story_card(updated_state.get("story_card"))
        workshop = _normalize_workshop_result(updated_state.get("workshop"))
        storyboard = _normalize_storyboard_result(updated_state.get("storyboard"))
        if story_card is not None:
            normalized_updated_state["story_card"] = story_card
        if workshop is not None:
            normalized_updated_state["workshop"] = workshop
        if storyboard is not None:
            normalized_updated_state["storyboard"] = storyboard

    return {
        "command_understanding": _as_text(result.get("command_understanding")),
        "updated_state": normalized_updated_state,
        "consistency_report": _string_list(result.get("consistency_report")),
        "suggestions": _string_list(result.get("suggestions")),
    }