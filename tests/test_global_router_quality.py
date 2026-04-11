from typing import Any, Dict

from main import create_app


def _post_global_router(client: Any, utterance: str, fake_result: Dict[str, Any]) -> Dict[str, Any]:
    import app.routes.agent_routes as agent_routes

    def _fake_call_provider_json(provider: str, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        return {"result": fake_result, "actual_cost": 0.0, "retry_count": 0}

    agent_routes._call_provider_json = _fake_call_provider_json  # type: ignore[attr-defined]

    response = client.post(
        "/api/agent/run",
        json={
            "stage": "global_router",
            "payload": {
                "utterance": utterance,
                "project_state": {},
                "context": {},
            },
        },
    )
    data = response.get_json() or {}
    return data.get("result", {})


def test_global_router_fallback_for_core_cases() -> None:
    app = create_app()
    client = app.test_client()

    unknown = {
        "intent": {"module": "unknown", "action": "unknown", "confidence": 0.0, "risk_level": "medium", "reason": ""},
        "params": {},
        "clarify_questions": [],
        "safety": {"needs_confirmation": False, "confirm_message": ""},
    }

    cases = [
        ("把第三个场景改成夜间下雨", ("creative", "edit_story")),
        ("新增角色王婶", ("creative", "edit_story")),
        ("生成一个10秒视频任务，提示词是雨夜走廊追逐", ("video", "create_task")),
        ("切换到项目 夜雨版本", ("project", "switch_project")),
        ("导出 PDF 给我", ("export", "export_pdf")),
    ]

    for utterance, expected in cases:
        result = _post_global_router(client, utterance, unknown)
        intent = result.get("intent", {})
        got = (intent.get("module"), intent.get("action"))
        assert got == expected
        assert float(intent.get("confidence", 0.0)) >= 0.78


def test_global_router_enriches_video_params() -> None:
    app = create_app()
    client = app.test_client()

    low_confidence_video = {
        "intent": {"module": "video", "action": "create_task", "confidence": 0.2, "risk_level": "low", "reason": ""},
        "params": {"prompt": "", "duration": 0},
        "clarify_questions": [],
        "safety": {"needs_confirmation": False, "confirm_message": ""},
    }

    result = _post_global_router(client, "生成一个15秒视频任务，提示词是雨夜走廊追逐", low_confidence_video)
    intent = result.get("intent", {})
    params = result.get("params", {})

    assert (intent.get("module"), intent.get("action")) == ("video", "create_task")
    assert int(params.get("duration", 0)) == 15
    assert params.get("prompt") == "雨夜走廊追逐"


def test_global_router_switch_project_requires_confirmation() -> None:
    app = create_app()
    client = app.test_client()

    unknown = {
        "intent": {"module": "unknown", "action": "unknown", "confidence": 0.0, "risk_level": "medium", "reason": ""},
        "params": {},
        "clarify_questions": [],
        "safety": {"needs_confirmation": False, "confirm_message": ""},
    }

    result = _post_global_router(client, "切换到项目 夜雨版本", unknown)
    params = result.get("params", {})
    safety = result.get("safety", {})

    assert params.get("project_name") == "夜雨版本"
    assert safety.get("needs_confirmation") is True
    assert str(safety.get("confirm_message", "")).strip()
