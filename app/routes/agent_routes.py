from typing import Any, Dict, Optional

import re
import requests
from flask import Blueprint, jsonify, request

from app.config import DEFAULT_PROVIDER, MODEL_PROVIDERS
from app.services.cover_service import _create_cover_image_task, _query_cover_image_task
from app.services.export_service import _export_markdown
from app.services.llm_service import _call_provider_json, _has_qiniu_text_credential
from app.services.prompt_service import (
    _cover_packaging_prompt,
    _command_prompt,
    _global_router_prompt,
    _story_engine_prompt,
    _title_packaging_prompt,
    _story_review_prompt,
    _story_rewrite_prompt,
    _storyboard_prompt,
    _workshop_prompt,
)
from app.services.story_template_service import _get_story_template, _list_story_templates
from app.utils.helpers import _estimate_duration, _calculate_cost
from app.utils.normalizers import (
    _normalize_story_engine_result,
    _normalize_story_review_result,
    _normalize_story_rewrite_result,
    _normalize_title_packaging_result,
    _normalize_workshop_result,
    _normalize_storyboard_result,
    _normalize_command_result,
    _normalize_cover_packaging_result,
    _normalize_global_router_result,
)

agent_bp = Blueprint("agent", __name__)

_ADD_CHARACTER_PATTERNS = [
    r"(?:加|添加|新增|补充)(?:一个|一位|个)?(?:人物|角色)",
    r"(?:人物|角色)(?:叫|名叫|名字是)",
]


def _extract_character_name(command_text: str) -> str:
    text = str(command_text or "").strip()
    if not text:
        return ""

    match = re.search(r"(?:叫|名叫|名字是)\s*([^\s，。,.！？!?；;]{1,20})", text)
    if not match:
        return ""
    return str(match.group(1)).strip()


def _is_add_character_command(command_text: str) -> bool:
    text = str(command_text or "")
    if not text:
        return False
    return any(re.search(pattern, text) for pattern in _ADD_CHARACTER_PATTERNS)


def _apply_command_fallback(payload: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(result, dict):
        return result

    updated_state = result.get("updated_state", {})
    if isinstance(updated_state, dict) and updated_state:
        return result

    command_text = str(payload.get("command", "")).strip()
    if not _is_add_character_command(command_text):
        return result

    name = _extract_character_name(command_text)
    if not name:
        return result

    project_state = payload.get("project_state", {}) if isinstance(payload, dict) else {}
    workshop = project_state.get("workshop", {}) if isinstance(project_state, dict) else {}
    characters = workshop.get("characters", []) if isinstance(workshop, dict) else []
    existing = [item for item in characters if isinstance(item, dict)]

    if any(str(item.get("name", "")).strip() == name for item in existing):
        return {
            **result,
            "command_understanding": f"命令识别为新增人物，但角色“{name}”已存在。",
            "updated_state": {},
            "consistency_report": ["未重复添加角色，保持当前状态不变。"],
            "suggestions": ["可继续补充该角色的标签、动机和人物弧光。"],
        }

    fallback_character = {
        "name": name,
        "tags": ["待完善"],
        "motivation": "",
        "arc": "",
    }

    return {
        **result,
        "command_understanding": f"已按命令新增人物：{name}",
        "updated_state": {
            "workshop": {
                "characters": [*existing, fallback_character],
            }
        },
        "consistency_report": ["采用后端规则兜底，仅增量更新 workshop.characters。"],
        "suggestions": ["建议补充该角色的标签、动机和人物弧光。"],
    }


def _extract_duration_seconds(text: str) -> Optional[int]:
    source = str(text or "")
    if not source:
        return None

    for pattern in [r"(\d{1,2})\s*(?:秒|s|sec|second)", r"(?:时长|长度)\s*(\d{1,2})"]:
        match = re.search(pattern, source, flags=re.IGNORECASE)
        if match:
            value = int(match.group(1))
            return max(1, min(60, value))
    return None


def _extract_video_prompt(text: str) -> str:
    source = str(text or "").strip()
    if not source:
        return ""

    patterns = [
        r"(?:提示词|prompt)\s*(?:是|为|:|：)\s*([^\n\r]+)$",
        r"(?:视频|片子|任务)\s*(?:内容|主题)?\s*(?:是|为|:|：)\s*([^\n\r]+)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, source, flags=re.IGNORECASE)
        if match:
            return str(match.group(1)).strip(" ，。,.!?！？")
    return ""


def _extract_project_name(text: str) -> str:
    source = str(text or "").strip()
    if not source:
        return ""

    patterns = [
        r"(?:切换(?:到)?(?:项目)?|进入(?:项目)?|打开(?:项目)?)\s*[:：]?\s*([^\s，。,.!?！？]{1,40})$",
        r"(?:项目)\s*[:：]?\s*([^\s，。,.!?！？]{1,40})$",
    ]
    for pattern in patterns:
        match = re.search(pattern, source, flags=re.IGNORECASE)
        if match:
            return str(match.group(1)).strip()
    return ""


def _infer_router_fallback(utterance: str) -> Optional[Dict[str, Any]]:
    text = str(utterance or "").strip()
    if not text:
        return None

    lowered = text.lower()
    duration = _extract_duration_seconds(text)
    video_prompt = _extract_video_prompt(text)
    project_name = _extract_project_name(text)

    if re.search(r"(导出|导成|导为|export)", text, flags=re.IGNORECASE):
        if "pdf" in lowered:
            return {"module": "export", "action": "export_pdf", "risk_level": "low"}
        if re.search(r"(docx|word)", lowered, flags=re.IGNORECASE):
            return {"module": "export", "action": "export_docx", "risk_level": "low"}
        if re.search(r"(markdown|md)", lowered, flags=re.IGNORECASE):
            return {"module": "export", "action": "export_markdown", "risk_level": "low"}

    if re.search(r"(切换|进入|打开)", text, flags=re.IGNORECASE) and re.search(r"(项目|project)", text, flags=re.IGNORECASE):
        return {
            "module": "project",
            "action": "switch_project",
            "risk_level": "medium",
            "project_name": project_name,
        }

    if re.search(r"(生成|创建|新建)", text, flags=re.IGNORECASE) and re.search(r"(视频|video|任务)", text, flags=re.IGNORECASE):
        return {
            "module": "video",
            "action": "create_task",
            "risk_level": "low",
            "duration": duration,
            "prompt": video_prompt,
        }

    if re.search(r"(查询|查看)", text, flags=re.IGNORECASE) and re.search(r"(视频|任务|状态)", text, flags=re.IGNORECASE):
        return {"module": "video", "action": "query_task", "risk_level": "low"}

    if re.search(r"(新增|添加|修改|改成|改为|调整|删除|角色|人物|场景|剧情|台词)", text, flags=re.IGNORECASE):
        return {
            "module": "creative",
            "action": "edit_story",
            "risk_level": "low",
            "command_text": text,
        }

    return None


def _apply_global_router_fallback(payload: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(result, dict):
        return result

    utterance = str(payload.get("utterance", "") if isinstance(payload, dict) else "").strip()
    if not utterance:
        return result

    intent = result.get("intent", {})
    intent = intent if isinstance(intent, dict) else {}
    params = result.get("params", {})
    params = params if isinstance(params, dict) else {}
    safety = result.get("safety", {})
    safety = safety if isinstance(safety, dict) else {}

    module = str(intent.get("module", "")).strip().lower()
    action = str(intent.get("action", "")).strip().lower()
    confidence_raw = intent.get("confidence", 0.0)
    try:
        confidence = float(confidence_raw)
    except (TypeError, ValueError):
        confidence = 0.0

    inferred = _infer_router_fallback(utterance)
    if not inferred:
        return result

    should_override = module == "unknown" or action == "unknown" or confidence < 0.35
    should_enrich = (module, action) in {("video", "create_task"), ("project", "switch_project"), ("creative", "edit_story")}
    if not should_override and not should_enrich:
        return result

    merged_intent = dict(intent)
    merged_params = dict(params)
    merged_safety = dict(safety)

    if should_override:
        merged_intent["module"] = inferred.get("module", module or "unknown")
        merged_intent["action"] = inferred.get("action", action or "unknown")
        merged_intent["risk_level"] = inferred.get("risk_level", merged_intent.get("risk_level", "medium"))
        merged_intent["confidence"] = max(confidence, 0.78)
        reason = str(merged_intent.get("reason", "")).strip()
        merged_intent["reason"] = (reason + "；" if reason else "") + "触发规则兜底"

    if inferred.get("command_text") and not str(merged_params.get("command_text", "")).strip():
        merged_params["command_text"] = inferred["command_text"]
    if inferred.get("prompt") and not str(merged_params.get("prompt", "")).strip():
        merged_params["prompt"] = inferred["prompt"]
    duration = inferred.get("duration")
    if isinstance(duration, int):
        raw_duration = merged_params.get("duration")
        raw_duration_int: Optional[int] = None
        if isinstance(raw_duration, (int, float)):
            raw_duration_int = int(raw_duration)
        elif isinstance(raw_duration, str) and raw_duration.isdigit():
            raw_duration_int = int(raw_duration)
        if raw_duration_int in (None, 0) or (raw_duration_int in (1, 10) and duration != raw_duration_int):
            merged_params["duration"] = duration
    if inferred.get("project_name") and not str(merged_params.get("project_name", "")).strip():
        merged_params["project_name"] = inferred["project_name"]

    if merged_intent.get("action") == "switch_project":
        merged_safety["needs_confirmation"] = True
        if not str(merged_safety.get("confirm_message", "")).strip():
            merged_safety["confirm_message"] = "确认切换项目吗？"

    return {
        **result,
        "intent": merged_intent,
        "params": merged_params,
        "safety": merged_safety,
    }


@agent_bp.get("/api/story-templates")
def get_story_templates():
    return jsonify({"ok": True, "templates": _list_story_templates()})


@agent_bp.get("/api/providers")
def get_providers():
    providers_list = []
    for key, config in MODEL_PROVIDERS.items():
        if config.get("requires_qiniu_credential"):
            has_credential = _has_qiniu_text_credential()
        else:
            has_credential = bool(config.get("api_key"))

        providers_list.append(
            {
                "id": key,
                "name": config["name"],
                "model": config["model"],
                "has_api_key": has_credential,
                "is_default": key == DEFAULT_PROVIDER,
            }
        )
    return jsonify({"ok": True, "providers": providers_list})


@agent_bp.post("/api/agent/compare")
def compare_providers():
    req_json = request.get_json(silent=True) or {}
    stage = req_json.get("stage")
    payload = req_json.get("payload", {})
    providers = req_json.get("providers", [])

    if not providers:
        return jsonify({"error": "No providers specified for comparison."}), 400

    results: Dict[str, Any] = {}
    errors: Dict[str, str] = {}

    for provider in providers:
        try:
            if stage == "story_engine":
                result = _call_provider_json(
                    provider,
                    "你是专业短剧编剧策划，擅长结构化输出高抓力短剧故事卡。",
                    _story_engine_prompt(payload),
                )
                result = _normalize_story_engine_result(result, _get_story_template(payload.get("template_id", "")))
            else:
                continue

            results[provider] = result
        except Exception as e:  # noqa: BLE001
            errors[provider] = str(e)

    return jsonify(
        {
            "ok": True,
            "stage": stage,
            "results": results,
            "errors": errors,
        }
    )


@agent_bp.post("/api/agent/run")
def run_agent_stage():
    req_json = request.get_json(silent=True) or {}
    stage = req_json.get("stage")
    payload = req_json.get("payload", {})
    provider = req_json.get("provider", DEFAULT_PROVIDER)

    if stage not in {
        "story_engine",
        "story_review",
        "story_rewrite",
        "title_packaging",
        "cover_packaging",
        "cover_image_generate",
        "cover_image_query",
        "workshop",
        "storyboard",
        "command",
        "global_router",
        "export",
    }:
        return jsonify({"error": "Unsupported stage."}), 400

    try:
        if stage == "story_engine":
            response = _call_provider_json(
                provider,
                "你是专业短剧编剧策划，擅长结构化输出高抓力短剧故事卡。",
                _story_engine_prompt(payload),
            )
            result = response["result"]
            result = _normalize_story_engine_result(result, _get_story_template(payload.get("template_id", "")))
        elif stage == "story_review":
            response = _call_provider_json(
                provider,
                "你是专业短剧审稿评分器，擅长发现爆点不足、冲突不足和执行风险，并输出结构化评分。",
                _story_review_prompt(payload),
            )
            result = response["result"]
            result = _normalize_story_review_result(result)
        elif stage == "story_rewrite":
            response = _call_provider_json(
                provider,
                "你是专业短剧改稿器，擅长基于评分结果输出多个可直接替换的强化版本。",
                _story_rewrite_prompt(payload),
            )
            result = response["result"]
            result = _normalize_story_rewrite_result(result)
        elif stage == "title_packaging":
            response = _call_provider_json(
                provider,
                "你是短剧标题包装顾问，擅长输出吸睛标题、标题评分和平台话题标签。",
                _title_packaging_prompt(payload),
            )
            result = response["result"]
            result = _normalize_title_packaging_result(result)
        elif stage == "cover_packaging":
            response = _call_provider_json(
                provider,
                "你是短剧封面包装顾问，擅长输出封面标题、卖点文案、视觉方向和文生图提示词。",
                _cover_packaging_prompt(payload),
            )
            result = response["result"]
            result = _normalize_cover_packaging_result(result)
        elif stage == "cover_image_generate":
            result = _create_cover_image_task(payload)
            response = result.get("meta", {"actual_cost": 0.0, "retry_count": 0})
        elif stage == "cover_image_query":
            result = _query_cover_image_task(str(payload.get("task_id", "") if isinstance(payload, dict) else ""))
            response = {"actual_cost": 0.0, "retry_count": 0}
        elif stage == "workshop":
            response = _call_provider_json(
                provider,
                "你是专业短剧编剧，擅长角色与情节构建，并做一致性检查。",
                _workshop_prompt(payload),
            )
            result = response["result"]
            result = _normalize_workshop_result(result)
        elif stage == "storyboard":
            response = _call_provider_json(
                provider,
                "你是分镜导演，擅长把剧情拆成可拍摄镜头。",
                _storyboard_prompt(payload),
            )
            result = response["result"]
            result = _normalize_storyboard_result(result)
        elif stage == "command":
            response = _call_provider_json(
                provider,
                "你是编剧助手，负责执行自然语言编辑命令并保持一致性。",
                _command_prompt(payload),
            )
            result = response["result"]
            result = _normalize_command_result(result)
            result = _apply_command_fallback(payload, result)
        elif stage == "global_router":
            response = _call_provider_json(
                provider,
                "You are a global intent router for a short-video creation assistant. Return strict JSON only.",
                _global_router_prompt(payload),
            )
            result = response["result"]
            result = _normalize_global_router_result(result)
            result = _apply_global_router_fallback(payload, result)
        else:
            result = _export_markdown(payload)
            response = {"actual_cost": 0.0, "retry_count": 0}  # export不调用模型

        # 新增：计算meta
        estimated_duration = response.get("estimated_duration", _estimate_duration(stage))
        provider_config = MODEL_PROVIDERS.get(provider, {})
        model_name = provider_config.get("model", "default")
        estimated_cost = response.get("estimated_cost", _calculate_cost(model_name))
        actual_cost = response.get("actual_cost", 0.0)
        retry_count = response.get("retry_count", 0)
        primary_model = response.get("primary_model", model_name)
        final_model = response.get("final_model", model_name)
        fallback_triggered = response.get("fallback_triggered", False)
        fallback_reason = response.get("fallback_reason", "")
        fallback_from = response.get("fallback_from", "")
        fallback_to = response.get("fallback_to", "")
        estimated_tokens = int(response.get("estimated_tokens", 0) or 0)
        cost_type = response.get("cost_type", "text" if estimated_tokens else "")
        prompt_tokens = int(response.get("prompt_tokens", 0) or 0)
        completion_tokens = int(response.get("completion_tokens", 0) or 0)
        cache_hit_tokens = int(response.get("cache_hit_tokens", 0) or 0)
        cache_miss_tokens = int(response.get("cache_miss_tokens", 0) or 0)
        cost_per_token = float(response.get("cost_per_token", 0.0) or 0.0)
        cost_per_1k_tokens = float(response.get("cost_per_1k_tokens", cost_per_token * 1000) or 0.0)
        input_cost = float(response.get("input_cost", 0.0) or 0.0)
        output_cost = float(response.get("output_cost", 0.0) or 0.0)
        input_price_per_1m_tokens = float(response.get("input_price_per_1m_tokens", 0.0) or 0.0)
        input_cache_hit_price_per_1m_tokens = float(response.get("input_cache_hit_price_per_1m_tokens", 0.0) or 0.0)
        output_price_per_1m_tokens = float(response.get("output_price_per_1m_tokens", 0.0) or 0.0)

        meta = {
            "stage": stage,
            "cost_type": cost_type,
            "estimated_duration": estimated_duration,
            "estimated_cost": estimated_cost,
            "actual_cost": actual_cost,
            "retry_count": retry_count,
            "primary_model": primary_model,
            "final_model": final_model,
            "fallback_triggered": fallback_triggered,
            "fallback_reason": fallback_reason,
            "fallback_from": fallback_from,
            "fallback_to": fallback_to,
            "estimated_tokens": estimated_tokens,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cache_hit_tokens": cache_hit_tokens,
            "cache_miss_tokens": cache_miss_tokens,
            "cost_per_token": cost_per_token,
            "cost_per_1k_tokens": cost_per_1k_tokens,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "input_price_per_1m_tokens": input_price_per_1m_tokens,
            "input_cache_hit_price_per_1m_tokens": input_cache_hit_price_per_1m_tokens,
            "output_price_per_1m_tokens": output_price_per_1m_tokens,
            "image_count": int(response.get("image_count", 0) or 0),
            "image_size": response.get("image_size", ""),
            "image_price_per_task": float(response.get("image_price_per_task", 0.0) or 0.0),
            "video_duration": int(response.get("video_duration", 0) or 0),
            "video_size": response.get("video_size", ""),
            "video_price_per_second": float(response.get("video_price_per_second", 0.0) or 0.0),
            "video_with_reference": bool(response.get("video_with_reference", False)),
        }

        return jsonify({"ok": True, "stage": stage, "provider": provider, "result": result, "meta": meta})
    except requests.Timeout as e:
        return jsonify({"ok": False, "error": "Model API request timed out", "detail": str(e)}), 504
    except requests.HTTPError as e:
        detail: Optional[str] = None
        if e.response is not None:
            detail = e.response.text
        return jsonify({"ok": False, "error": "Model API request failed", "detail": detail}), 502
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 500
