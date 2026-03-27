from typing import Any, Dict
import json

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
You are the workshop layer of a short-drama writing assistant.
Return strict JSON only. No markdown, no explanation.
Write all content values in Chinese.

Story card:
{json.dumps(story_card, ensure_ascii=False, indent=2)}

Role requirements:
{role_requirements}

Plot requirements:
{plot_requirements}

Required JSON schema:
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
    {{
      "from": "角色A",
      "to": "角色B",
      "type": "关系类型",
      "tension": "冲突点"
    }}
  ],
  "plot_nodes": [
    {{
      "id": "N1",
      "template_stage": "激励事件/第一次转折/高潮等",
      "summary": "这一节点发生了什么",
      "location": "地点",
      "action_draft": "动作与场面调度",
      "dialogue_draft": ["角色: 台词"],
      "emotion_shift": "这一节点前后情绪变化",
      "consistency_check": "潜在逻辑问题，没有则写无"
    }}
  ],
  "timeline_view": ["N1", "N2"],
  "card_wall_groups": [
    {{
      "group": "铺垫/冲突/反转/收束",
      "node_ids": ["N1", "N2"]
    }}
  ]
}}
""".strip()


def _storyboard_prompt(payload: Dict[str, Any]) -> str:
    workshop = payload.get("workshop", {})
    style = payload.get("visual_style", "")

    return f"""
You are the storyboard layer of a short-drama writing assistant.
Return strict JSON only. No markdown, no explanation.
Write all content values in Chinese.

Workshop result:
{json.dumps(workshop, ensure_ascii=False, indent=2)}

Visual style requirement:
{style}

Required JSON schema:
{{
  "storyboards": [
    {{
      "shot_id": "S1",
      "related_node_id": "N1",
      "shot_type": "特写/中景/全景",
      "camera_movement": "固定/推/拉/摇/移/跟拍",
      "visual_description": "画面内容",
      "dialogue_or_sfx": "对白或音效",
      "duration_sec": 4,
      "shooting_note": "拍摄备注",
      "prompt_draft": "可直接用于视频生成的提示词"
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
