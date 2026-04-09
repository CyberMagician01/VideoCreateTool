from typing import Any, Dict, Optional

import requests
from flask import Blueprint, jsonify, request

from app.config import DEFAULT_PROVIDER, MODEL_PROVIDERS
from app.services.export_service import _export_markdown
from app.services.llm_service import _call_provider_json, _has_qiniu_text_credential
from app.services.prompt_service import (
    _command_prompt,
    _story_engine_prompt,
    _storyboard_prompt,
    _workshop_prompt,
)
from app.utils.normalizers import (
    _normalize_command_result,
    _normalize_story_engine_result,
    _normalize_storyboard_result,
    _normalize_workshop_result,
)

agent_bp = Blueprint("agent", __name__)


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

            if stage == "story_engine":
                result = _normalize_story_engine_result(result)
            elif stage == "workshop":
                result = _normalize_workshop_result(result)
            elif stage == "storyboard":
                result = _normalize_storyboard_result(result)

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

        if stage == "story_engine":
            result = _normalize_story_engine_result(result)
        elif stage == "workshop":
            result = _normalize_workshop_result(result)
        elif stage == "storyboard":
            result = _normalize_storyboard_result(result)
        elif stage == "command":
            result = _normalize_command_result(result)

        return jsonify({"ok": True, "stage": stage, "provider": provider, "result": result})
    except requests.HTTPError as e:
        detail: Optional[str] = None
        if e.response is not None:
            detail = e.response.text
        return jsonify({"ok": False, "error": "Model API request failed", "detail": detail}), 502
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 500
    