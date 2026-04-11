from typing import Any, Dict, Optional

import requests
from flask import Blueprint, jsonify, request

from app.config import DEFAULT_PROVIDER, MODEL_PROVIDERS
from app.services.cover_service import _create_cover_image_task, _query_cover_image_task
from app.services.export_service import _export_markdown
from app.services.llm_service import _call_provider_json, _has_qiniu_text_credential
from app.services.prompt_service import (
    _cover_packaging_prompt,
    _command_prompt,
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
)

agent_bp = Blueprint("agent", __name__)


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
            response = {"actual_cost": 0.0, "retry_count": 0}
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
        else:
            result = _export_markdown(payload)
            response = {"actual_cost": 0.0, "retry_count": 0}  # export不调用模型

        # 新增：计算meta
        estimated_duration = _estimate_duration(stage)
        provider_config = MODEL_PROVIDERS.get(provider, {})
        model_name = provider_config.get("model", "default")
        estimated_cost = _calculate_cost(model_name)
        actual_cost = response.get("actual_cost", 0.0)
        retry_count = response.get("retry_count", 0)
        primary_model = response.get("primary_model", model_name)
        final_model = response.get("final_model", model_name)
        fallback_triggered = response.get("fallback_triggered", False)
        fallback_reason = response.get("fallback_reason", "")
        fallback_from = response.get("fallback_from", "")
        fallback_to = response.get("fallback_to", "")

        meta = {
            "stage": stage,
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
