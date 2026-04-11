from typing import Any, Dict, Optional

from app.utils.helpers import (
    _as_text,
    _default_project_state,
    _derive_storyboard_prompt,
    _first_present,
    _safe_int,
    _string_list,
)


def _normalize_story_inputs(story_inputs: Any) -> Dict[str, Any]:
    base = _default_project_state()["story_inputs"]
    if not isinstance(story_inputs, dict):
        return base
    return {
        "idea": _as_text(story_inputs.get("idea")),
        "theme": _as_text(story_inputs.get("theme")),
        "tone": _as_text(story_inputs.get("tone")),
        "structure": _as_text(story_inputs.get("structure")),
        "template_id": _as_text(story_inputs.get("template_id")),
    }


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
        "viral_template_id": _as_text(story_card.get("viral_template_id")),
        "viral_template_name": _as_text(story_card.get("viral_template_name")),
        "opening_hook_strategy": _as_text(story_card.get("opening_hook_strategy")),
        "conflict_escalation_strategy": _as_text(story_card.get("conflict_escalation_strategy")),
        "cliffhanger_strategy": _as_text(story_card.get("cliffhanger_strategy")),
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
            normalized["viral_template_id"],
            normalized["viral_template_name"],
            normalized["opening_hook_strategy"],
            normalized["conflict_escalation_strategy"],
            normalized["cliffhanger_strategy"],
        ]
    ):
        return normalized
    return None


def _normalize_story_engine_result(result: Any, template: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not isinstance(result, dict):
        return {"story_card": None, "next_questions": []}
    story_card = _normalize_story_card(result.get("story_card") if "story_card" in result else result)
    if story_card and template:
        if not story_card.get("viral_template_id"):
            story_card["viral_template_id"] = _as_text(template.get("id"))
        if not story_card.get("viral_template_name"):
            story_card["viral_template_name"] = _as_text(template.get("name"))
        if not story_card.get("opening_hook_strategy"):
            story_card["opening_hook_strategy"] = _as_text(template.get("opening_hook_formula"))
        if not story_card.get("conflict_escalation_strategy"):
            story_card["conflict_escalation_strategy"] = " -> ".join(_string_list(template.get("conflict_escalation")))
        if not story_card.get("cliffhanger_strategy"):
            story_card["cliffhanger_strategy"] = _as_text(template.get("cliffhanger_strategy"))
    return {
        "story_card": story_card,
        "next_questions": _string_list(result.get("next_questions")),
    }


def _normalize_title_score(item: Any, index: int) -> Optional[Dict[str, Any]]:
    if not isinstance(item, dict):
        return None
    normalized = {
        "id": _as_text(item.get("id")) or f"title_score_{index}",
        "name": _as_text(item.get("name")) or f"维度{index}",
        "score": min(_safe_int(item.get("score"), 0, minimum=0), 100),
        "reason": _as_text(item.get("reason")),
    }
    if any([normalized["name"], normalized["reason"], normalized["score"]]):
        return normalized
    return None


def _normalize_title_suggestion(item: Any, index: int) -> Optional[Dict[str, Any]]:
    if not isinstance(item, dict):
        return None
    scores = [
        entry
        for entry in (
            _normalize_title_score(score, idx + 1) for idx, score in enumerate(item.get("scores", []))
        )
        if entry
    ]
    normalized = {
        "id": _as_text(item.get("id")) or f"title_{index}",
        "title": _as_text(item.get("title")),
        "style": _as_text(item.get("style")),
        "hook_point": _as_text(item.get("hook_point")),
        "overall_score": min(_safe_int(item.get("overall_score"), 0, minimum=0), 100),
        "verdict": _as_text(item.get("verdict")),
        "reason": _as_text(item.get("reason")),
        "scores": scores,
    }
    if normalized["title"]:
        return normalized
    return None


def _normalize_title_packaging_result(result: Any) -> Dict[str, Any]:
    base = _default_project_state()["title_lab"]
    if not isinstance(result, dict):
        return base

    evaluated_title = _normalize_title_suggestion(result.get("evaluated_title"), 0)
    title_suggestions = [
        item
        for item in (
            _normalize_title_suggestion(candidate, idx + 1)
            for idx, candidate in enumerate(result.get("title_suggestions", []))
        )
        if item
    ]

    recommended_title_id = _as_text(result.get("recommended_title_id"))
    if recommended_title_id and not any(item["id"] == recommended_title_id for item in title_suggestions):
        recommended_title_id = title_suggestions[0]["id"] if title_suggestions else ""

    return {
        "current_title": _as_text(result.get("current_title")),
        "summary": _as_text(result.get("summary")),
        "evaluated_title": evaluated_title,
        "recommended_title_id": recommended_title_id or (title_suggestions[0]["id"] if title_suggestions else ""),
        "recommended_reason": _as_text(result.get("recommended_reason")),
        "title_suggestions": title_suggestions,
        "topic_tags": _string_list(result.get("topic_tags")),
        "updated_at": _as_text(result.get("updated_at")),
    }


def _normalize_cover_packaging_result(result: Any) -> Dict[str, Any]:
    base = _default_project_state()["cover_lab"]
    if not isinstance(result, dict):
        return base
    return {
        "current_title": _as_text(result.get("current_title")),
        "style_preference": _as_text(result.get("style_preference")),
        "focus_point": _as_text(result.get("focus_point")),
        "summary": _as_text(result.get("summary")),
        "main_title": _as_text(result.get("main_title")),
        "subtitle": _as_text(result.get("subtitle")),
        "hook_lines": _string_list(result.get("hook_lines")),
        "visual_direction": _as_text(result.get("visual_direction")),
        "layout_direction": _as_text(result.get("layout_direction")),
        "color_palette": _as_text(result.get("color_palette")),
        "image_prompt": _as_text(result.get("image_prompt")),
        "generated_image_url": _as_text(result.get("generated_image_url")),
        "image_model": _as_text(result.get("image_model")),
        "image_size": _as_text(result.get("image_size")),
        "image_task_id": _as_text(result.get("image_task_id")),
        "image_task_status": _as_text(result.get("image_task_status")),
        "image_status_message": _as_text(result.get("image_status_message")),
        "updated_at": _as_text(result.get("updated_at")),
    }


def _normalize_review_dimension(dimension: Any, index: int) -> Optional[Dict[str, Any]]:
    if not isinstance(dimension, dict):
        return None
    normalized = {
        "id": _as_text(dimension.get("id")) or f"dimension_{index}",
        "name": _as_text(dimension.get("name")) or f"维度{index}",
        "score": _safe_int(dimension.get("score"), 0, minimum=0),
        "reason": _as_text(dimension.get("reason")),
        "suggestion": _as_text(dimension.get("suggestion")),
    }
    normalized["score"] = min(normalized["score"], 100)
    if any([normalized["name"], normalized["reason"], normalized["suggestion"], normalized["score"]]):
        return normalized
    return None


def _normalize_story_review_result(result: Any) -> Dict[str, Any]:
    base = _default_project_state()["review_labs"]["story_engine"]["latest_review"]
    if not isinstance(result, dict):
        return base

    dimensions = [
        item
        for item in (
            _normalize_review_dimension(dimension, idx + 1)
            for idx, dimension in enumerate(result.get("dimensions", []))
        )
        if item
    ]
    low_score_dimensions = [
        item
        for item in _string_list(result.get("low_score_dimensions"))
        if any(d["id"] == item for d in dimensions)
    ]
    if not low_score_dimensions:
        low_score_dimensions = [d["id"] for d in dimensions if int(d.get("score", 0)) < 75]

    return {
        "summary": _as_text(result.get("summary")),
        "overall_score": min(_safe_int(result.get("overall_score"), 0, minimum=0), 100),
        "dimensions": dimensions,
        "top_issues": _string_list(result.get("top_issues")),
        "priority_actions": _string_list(result.get("priority_actions")),
        "low_score_dimensions": low_score_dimensions,
    }


def _normalize_rewrite_target(target: Any) -> str:
    value = _as_text(target)
    return value if value in {"story_card", "workshop", "storyboard"} else "story_card"


def _normalize_rewrite_candidate(candidate: Any, index: int, target: str) -> Optional[Dict[str, Any]]:
    if not isinstance(candidate, dict):
        return None

    normalized_target = _normalize_rewrite_target(candidate.get("target") or target)
    normalized = {
        "id": _as_text(candidate.get("id")) or f"rewrite_{index}",
        "title": _as_text(candidate.get("title")) or f"改写版本 {index}",
        "strategy": _as_text(candidate.get("strategy")),
        "focus_dimensions": _string_list(candidate.get("focus_dimensions")),
        "target": normalized_target,
        "story_card": None,
        "workshop": None,
        "storyboard": None,
    }

    if normalized_target == "story_card":
        normalized["story_card"] = _normalize_story_card(candidate.get("story_card"))
        return normalized if normalized["story_card"] is not None else None
    if normalized_target == "workshop":
        normalized["workshop"] = _normalize_workshop_result(candidate.get("workshop"))
        return normalized if normalized["workshop"] is not None else None

    normalized["storyboard"] = _normalize_storyboard_result(candidate.get("storyboard"))
    return normalized if normalized["storyboard"] is not None else None


def _normalize_story_rewrite_result(result: Any) -> Dict[str, Any]:
    if not isinstance(result, dict):
        return {"target": "story_card", "candidates": []}
    target = _normalize_rewrite_target(result.get("target"))
    candidates = [
        item
        for item in (
            _normalize_rewrite_candidate(candidate, idx + 1, target)
            for idx, candidate in enumerate(result.get("candidates", []))
        )
        if item
    ]
    return {
        "target": target,
        "candidates": candidates,
    }


def _normalize_single_review_lab_state(review_lab: Any, stage: str = "") -> Dict[str, Any]:
    base = _default_project_state()["review_labs"]["story_engine"]
    if not isinstance(review_lab, dict):
        return base
    latest_review = _normalize_story_review_result(review_lab.get("latest_review"))
    rewrite_data = _normalize_story_rewrite_result({"candidates": review_lab.get("rewrite_candidates", [])})
    return {
        "latest_review": latest_review,
        "rewrite_candidates": rewrite_data.get("candidates", []),
        "last_review_stage": _as_text(review_lab.get("last_review_stage")) or stage,
        "last_review_time": _as_text(review_lab.get("last_review_time")),
    }


def _normalize_review_labs_state(review_labs: Any, legacy_review_lab: Any = None) -> Dict[str, Any]:
    result = {
        "story_engine": _normalize_single_review_lab_state(None, "story_engine"),
        "workshop": _normalize_single_review_lab_state(None, "workshop"),
        "storyboard": _normalize_single_review_lab_state(None, "storyboard"),
    }

    if isinstance(review_labs, dict):
        for stage in ("story_engine", "workshop", "storyboard"):
            result[stage] = _normalize_single_review_lab_state(review_labs.get(stage), stage)

    if isinstance(legacy_review_lab, dict):
        legacy_stage = _as_text(legacy_review_lab.get("last_review_stage"))
        target_stage = legacy_stage if legacy_stage in result else "story_engine"
        result[target_stage] = _normalize_single_review_lab_state(legacy_review_lab, target_stage)

    return result


def _normalize_review_panel_state(panel_state: Any) -> Dict[str, bool]:
    base = _default_project_state()["review_panel_state"]
    if not isinstance(panel_state, dict):
        return base
    return {
        "story_engine": bool(panel_state.get("story_engine", base["story_engine"])),
        "workshop": bool(panel_state.get("workshop", base["workshop"])),
        "storyboard": bool(panel_state.get("storyboard", base["storyboard"])),
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
        "image_url": _as_text(video_lab.get("image_url")),
        "start_image_url": _as_text(video_lab.get("start_image_url")),
        "end_image_url": _as_text(video_lab.get("end_image_url")),
        "task_id": _as_text(video_lab.get("task_id")),
        "task_status": _as_text(video_lab.get("task_status")),
        "video_url": _as_text(_first_present(video_lab, "video_url", "url")),
        "auto_poll": bool(video_lab.get("auto_poll", True)),
        "last_check_time": _as_text(video_lab.get("last_check_time")),
        "long_segments": segments,
        "total_duration": _safe_int(video_lab.get("total_duration"), 0, minimum=0),
        "filename_prefix": _as_text(video_lab.get("filename_prefix")),
        "long_chain_by_last_frame": bool(video_lab.get("long_chain_by_last_frame", False)),
        "long_model": _as_text(video_lab.get("long_model")),
        "long_size": _as_text(video_lab.get("long_size")),
        "long_prompt_extend": bool(video_lab.get("long_prompt_extend", True)),
    }


def _normalize_project_state(state: Any) -> Dict[str, Any]:
    return {
        "story_inputs": _normalize_story_inputs(state.get("story_inputs") if isinstance(state, dict) else None),
        "story_card": _normalize_story_card(state.get("story_card")) if isinstance(state, dict) else None,
        "review_labs": _normalize_review_labs_state(
            state.get("review_labs") if isinstance(state, dict) else None,
            state.get("review_lab") if isinstance(state, dict) else None,
        ),
        "review_panel_state": _normalize_review_panel_state(
            state.get("review_panel_state") if isinstance(state, dict) else None
        ),
        "cover_lab": _normalize_cover_packaging_result(state.get("cover_lab") if isinstance(state, dict) else None),
        "title_lab": _normalize_title_packaging_result(state.get("title_lab") if isinstance(state, dict) else None),
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


def _normalize_global_router_result(result: Any) -> Dict[str, Any]:
    base = {
        "intent": {
            "module": "unknown",
            "action": "unknown",
            "confidence": 0.0,
            "risk_level": "medium",
            "reason": "",
        },
        "params": {
            "command_text": "",
            "prompt": "",
            "duration": 10,
            "model": "viduq3-turbo",
            "size": "1280*720",
            "task_id": "",
            "project_name": "",
            "project_id": "",
            "snapshot_name": "",
            "snapshot_description": "",
        },
        "clarify_questions": [],
        "safety": {
            "needs_confirmation": False,
            "confirm_message": "",
        },
    }
    if not isinstance(result, dict):
        return base

    intent_raw = result.get("intent", {})
    intent_raw = intent_raw if isinstance(intent_raw, dict) else {}
    module = _as_text(intent_raw.get("module"))
    action = _as_text(intent_raw.get("action"))
    confidence = float(max(0.0, min(1.0, _safe_int(intent_raw.get("confidence"), 0) / 100.0)))
    if isinstance(intent_raw.get("confidence"), (int, float)):
        confidence = float(max(0.0, min(1.0, float(intent_raw.get("confidence")))))
    risk_level = _as_text(intent_raw.get("risk_level")).lower()

    valid_modules = {"creative", "video", "project", "export", "unknown"}
    valid_actions = {
        "edit_story",
        "create_task",
        "query_task",
        "create_project",
        "switch_project",
        "create_snapshot",
        "export_markdown",
        "export_docx",
        "export_pdf",
        "unknown",
    }
    valid_risk = {"low", "medium", "high"}

    normalized_intent = {
        "module": module if module in valid_modules else "unknown",
        "action": action if action in valid_actions else "unknown",
        "confidence": confidence,
        "risk_level": risk_level if risk_level in valid_risk else "medium",
        "reason": _as_text(intent_raw.get("reason")),
    }

    params_raw = result.get("params", {})
    params_raw = params_raw if isinstance(params_raw, dict) else {}
    normalized_params = {
        "command_text": _as_text(params_raw.get("command_text")),
        "prompt": _as_text(params_raw.get("prompt")),
        "duration": min(60, max(1, _safe_int(params_raw.get("duration"), 10, minimum=1))),
        "model": _as_text(params_raw.get("model")) or "viduq3-turbo",
        "size": _as_text(params_raw.get("size")) or "1280*720",
        "task_id": _as_text(params_raw.get("task_id")),
        "project_name": _as_text(params_raw.get("project_name")),
        "project_id": _as_text(params_raw.get("project_id")),
        "snapshot_name": _as_text(params_raw.get("snapshot_name")),
        "snapshot_description": _as_text(params_raw.get("snapshot_description")),
    }

    safety_raw = result.get("safety", {})
    safety_raw = safety_raw if isinstance(safety_raw, dict) else {}
    normalized_safety = {
        "needs_confirmation": bool(safety_raw.get("needs_confirmation")),
        "confirm_message": _as_text(safety_raw.get("confirm_message")),
    }

    return {
        "intent": normalized_intent,
        "params": normalized_params,
        "clarify_questions": _string_list(result.get("clarify_questions")),
        "safety": normalized_safety,
    }
