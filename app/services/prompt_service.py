import json
from typing import Any, Dict

from app.services.story_template_service import _get_story_template


def _video_script_prompt(payload: Dict[str, Any]) -> str:
    return f"""
你是短剧编导，请直接输出一段可拍可生成视频的短剧脚本。

输入信息：
- 题材：{payload.get('genre', '')}
- 核心设定：{payload.get('idea', '')}
- 人物：{payload.get('roles', '')}
- 风格：{payload.get('style', '')}
- 时长：{payload.get('duration_sec', 10)} 秒

输出要求：
1. 先给出“标题”。
2. 再给“短剧脚本（分镜级）”，包含 4-6 个镜头，每个镜头写画面、动作、台词或音效。
3. 最后给“视频生成提示词（中文）”，用于文生视频，保证画面连贯。
4. 全文使用中文，简洁且有戏剧冲突。
""".strip()


def _story_engine_prompt(payload: Dict[str, Any]) -> str:
    selected_template = _get_story_template(payload.get("template_id", ""))
    effective_structure = payload.get("structure", "") or (
        selected_template.get("recommended_structure", "") if selected_template else ""
    )

    if selected_template:
        template_block = (
            f"- 模板名称: {selected_template['name']}\n"
            f"- 模板类型: {selected_template['category']}\n"
            f"- 模板摘要: {selected_template['summary']}\n"
            f"- 开场钩子句式: {selected_template['opening_hook_formula']}\n"
            f"- 冲突升级节奏: {' -> '.join(selected_template['conflict_escalation'])}\n"
            f"- 结尾留悬念策略: {selected_template['cliffhanger_strategy']}\n"
            f"- 推荐基调: {selected_template['recommended_tone']}\n"
            f"- 推荐结构: {selected_template['recommended_structure']}"
        )
    else:
        template_block = "未选择爆款模板，请根据用户输入自由生成。"

    return f"""
你是短剧创作智能体的第一层：故事引擎。
请基于用户输入，输出严格 JSON，不要附加解释文字。

用户输入：
- 创意: {payload.get('idea', '')}
- 主题偏好: {payload.get('theme', '')}
- 情绪基调: {payload.get('tone', '')}
- 结构模板偏好: {effective_structure}

爆款感模板约束：
{template_block}

生成要求：
1. 如果用户选择了爆款模板，必须明确体现模板的前 3 秒钩子、冲突升级节奏和结尾留悬念策略。
2. hook 必须适合短视频开场，要有立刻抓人的感觉。
3. anchor_points 必须能看出节奏推进，不能只是空泛概括。
4. 所有字段一律用中文。

JSON schema:
{{
  "story_card": {{
    "logline": "一句话故事梗概",
    "theme": "核心主题",
    "tone": "情绪基调",
    "structure_template": "所用结构模板",
    "core_conflict": "核心冲突",
    "anchor_points": ["开场钩子", "转折锚点", "高潮锚点", "结局锚点"],
    "hook": "前三秒抓人钩子",
    "ending_type": "开放式/反转式/治愈式等",
    "viral_template_id": "{selected_template['id'] if selected_template else ''}",
    "viral_template_name": "{selected_template['name'] if selected_template else ''}",
    "opening_hook_strategy": "本次故事采用的开场钩子策略",
    "conflict_escalation_strategy": "本次故事采用的冲突升级节奏",
    "cliffhanger_strategy": "本次故事采用的结尾留悬念策略"
  }},
  "next_questions": ["建议用户补充的问题", "建议用户补充的问题"]
}}
""".strip()


def _story_review_prompt(payload: Dict[str, Any]) -> str:
    project_state = payload.get("project_state", {}) if isinstance(payload, dict) else {}
    current_stage = payload.get("current_stage", "")
    return f"""
你是短剧创作流程中的审稿评分器。
请基于当前项目状态，从创作和执行两个角度给出严格 JSON 评分结果。
不要输出 markdown，不要输出额外解释。

当前阶段：{current_stage}
当前项目状态：
{json.dumps(project_state, ensure_ascii=False, indent=2)}

评分要求：
1. 必须评估以下五个维度：
   - hook_strength：钩子强度
   - conflict_density：冲突密度
   - motivation_clarity：角色动机清晰度
   - dialogue_naturality：台词口语化
   - shot_feasibility：镜头可执行性
2. 分数范围 0-100。
3. 如果某些材料尚未生成，例如还没有对白或分镜，也要保守评分并说明原因。
4. low_score_dimensions 只保留分数低于 75 的维度 id。
5. priority_actions 要给出最优先的 2-3 个修改动作。

JSON schema:
{{
  "summary": "整体评语",
  "overall_score": 78,
  "dimensions": [
    {{
      "id": "hook_strength",
      "name": "钩子强度",
      "score": 82,
      "reason": "为什么给这个分",
      "suggestion": "如何改进"
    }},
    {{
      "id": "conflict_density",
      "name": "冲突密度",
      "score": 70,
      "reason": "为什么给这个分",
      "suggestion": "如何改进"
    }},
    {{
      "id": "motivation_clarity",
      "name": "角色动机清晰度",
      "score": 76,
      "reason": "为什么给这个分",
      "suggestion": "如何改进"
    }},
    {{
      "id": "dialogue_naturality",
      "name": "台词口语化",
      "score": 68,
      "reason": "为什么给这个分",
      "suggestion": "如何改进"
    }},
    {{
      "id": "shot_feasibility",
      "name": "镜头可执行性",
      "score": 74,
      "reason": "为什么给这个分",
      "suggestion": "如何改进"
    }}
  ],
  "top_issues": ["最明显的问题", "第二个明显问题"],
  "priority_actions": ["优先修改动作1", "优先修改动作2"],
  "low_score_dimensions": ["conflict_density", "dialogue_naturality"]
}}
""".strip()


def _rewrite_target_config(current_stage: str) -> Dict[str, str]:
    if current_stage == "storyboard":
        return {
            "target": "storyboard",
            "target_label": "分镜结果",
            "rewrite_rule": "只改写 storyboard，不要生成 story_card 或 workshop。",
            "direction_rule": "每个候选版本都要保留当前剧情节点顺序，但强化镜头可执行性、画面表达和对白自然度。",
            "schema": """
{
  "target": "storyboard",
  "candidates": [
    {
      "id": "rewrite_1",
      "title": "强化执行版",
      "strategy": "减少复杂调度，让镜头更容易拍摄，同时保留关键冲突画面",
      "focus_dimensions": ["shot_feasibility", "dialogue_naturality"],
      "storyboard": {
        "storyboards": [
          {
            "shot_id": "S1",
            "related_node_id": "N1",
            "shot_type": "特写/中景/全景",
            "camera_movement": "固定/推/拉/摇/移/跟拍",
            "visual_description": "画面内容",
            "dialogue_or_sfx": "对白或音效",
            "duration_sec": 4,
            "shooting_note": "拍摄备注",
            "prompt_draft": "可直接用于视频生成的提示词"
          }
        ],
        "estimated_total_duration_sec": 60,
        "export_ready_checklist": ["服化道", "场景", "收音", "灯光"]
      }
    }
  ]
}
""".strip(),
        }

    if current_stage == "workshop":
        return {
            "target": "workshop",
            "target_label": "剧本工坊结果",
            "rewrite_rule": "只改写 workshop，不要生成 story_card 或 storyboard。",
            "direction_rule": "每个候选版本都要保留原始故事方向，但强化角色动机、剧情冲突密度和对白草稿的口语化。",
            "schema": """
{
  "target": "workshop",
  "candidates": [
    {
      "id": "rewrite_1",
      "title": "冲突加压版",
      "strategy": "在不改变故事走向的前提下，补强角色动机与节点冲突",
      "focus_dimensions": ["conflict_density", "motivation_clarity", "dialogue_naturality"],
      "workshop": {
        "characters": [
          {
            "name": "角色名",
            "tags": ["职业", "性格", "目标", "缺陷"],
            "motivation": "核心动机",
            "arc": "角色弧光"
          }
        ],
        "relationships": [
          {
            "from": "角色A",
            "to": "角色B",
            "type": "关系类型",
            "tension": "冲突点"
          }
        ],
        "plot_nodes": [
          {
            "id": "N1",
            "template_stage": "激励事件/第一次转折/高潮等",
            "summary": "这一节点发生了什么",
            "location": "地点",
            "action_draft": "动作与场面调度",
            "dialogue_draft": ["角色: 台词"],
            "emotion_shift": "这一节点前后情绪变化",
            "consistency_check": "潜在逻辑问题，没有则写无"
          }
        ],
        "timeline_view": ["N1", "N2"],
        "card_wall_groups": [
          {
            "group": "铺垫/冲突/反转/收束",
            "node_ids": ["N1", "N2"]
          }
        ]
      }
    }
  ]
}
""".strip(),
        }

    return {
        "target": "story_card",
        "target_label": "故事卡",
        "rewrite_rule": "只改写 story_card，不要生成 workshop 或 storyboard。",
        "direction_rule": "每个候选版本都要保留原始创意方向，但可以强化钩子、冲突和节奏。",
        "schema": """
{
  "target": "story_card",
  "candidates": [
    {
      "id": "rewrite_1",
      "title": "强化钩子版",
      "strategy": "通过更极端的开场信息差强化前三秒抓力",
      "focus_dimensions": ["hook_strength", "conflict_density"],
      "story_card": {
        "logline": "一句话故事梗概",
        "theme": "核心主题",
        "tone": "情绪基调",
        "structure_template": "所用结构模板",
        "core_conflict": "核心冲突",
        "anchor_points": ["开场钩子", "转折锚点", "高潮锚点", "结局锚点"],
        "hook": "前三秒抓人钩子",
        "ending_type": "开放式/反转式/治愈式等",
        "viral_template_id": "",
        "viral_template_name": "",
        "opening_hook_strategy": "本次故事采用的开场钩子策略",
        "conflict_escalation_strategy": "本次故事采用的冲突升级节奏",
        "cliffhanger_strategy": "本次故事采用的结尾留悬念策略"
      }
    }
  ]
}
""".strip(),
    }


def _story_rewrite_prompt(payload: Dict[str, Any]) -> str:
    project_state = payload.get("project_state", {}) if isinstance(payload, dict) else {}
    review_result = payload.get("review_result", {}) if isinstance(payload, dict) else {}
    current_stage = payload.get("current_stage", "") if isinstance(payload, dict) else ""
    config = _rewrite_target_config(current_stage)
    return f"""
你是短剧创作流程中的自动改稿器。
请针对低分项，输出 2-3 个{config["target_label"]}改写版本，要求可直接替换当前内容。
不要输出 markdown，不要输出额外解释。

当前阶段：{current_stage}
当前项目状态：
{json.dumps(project_state, ensure_ascii=False, indent=2)}

当前评分结果：
{json.dumps(review_result, ensure_ascii=False, indent=2)}

改写要求：
1. 改写目标是提升低分项，尤其是 low_score_dimensions 中提到的维度。
2. {config["rewrite_rule"]}
3. {config["direction_rule"]}
4. 必须输出 2-3 个候选版本。

JSON schema:
{config["schema"]}
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


def _title_packaging_prompt(payload: Dict[str, Any]) -> str:
    project = payload.get("project", {}) if isinstance(payload, dict) else {}
    story_card = payload.get("story_card", {}) if isinstance(payload, dict) else {}
    workshop = payload.get("workshop", {}) if isinstance(payload, dict) else {}
    storyboard = payload.get("storyboard", {}) if isinstance(payload, dict) else {}
    current_title = payload.get("current_title", "") if isinstance(payload, dict) else ""

    project_text = json.dumps(project, ensure_ascii=False)
    story_card_text = json.dumps(story_card, ensure_ascii=False)
    workshop_text = json.dumps(workshop, ensure_ascii=False)
    storyboard_text = json.dumps(storyboard, ensure_ascii=False)

    return f"""
你是短剧发行包装顾问，熟悉近一年主流短剧标题风格。
请基于下面的剧本内容，输出一组适合短剧平台传播的标题建议、标题评分和话题标签。
要求严格输出 JSON，不要输出 markdown，不要附加解释。

包装原则：
1. 标题要贴合现在常见短剧风格：强情绪、强关系、强身份差、强冲突、强悬念。
2. 标题要像短剧标题，而不是传统长剧或网文章节名。
3. 可以参考甜宠、打脸、逆袭、豪门、误会、复仇、悬疑、身份反转等常见表达，但不要直接抄现成作品名。
4. 尽量短、狠、抓人，优先让人一眼看到人物关系和爽点。
5. 话题标签要适合短视频/短剧平台分发。

当前项目：
{project_text}

当前标题（可为空）：
{current_title}

故事卡：
{story_card_text}

剧本工坊：
{workshop_text}

分镜工厂：
{storyboard_text}

评分维度说明：
- eye_catch：抓眼度
- conflict：冲突感
- info_density：信息密度
- genre_fit：短剧风格贴合度
- spreadability：传播话题性

JSON schema:
{{
  "current_title": "{current_title}",
  "summary": "整体标题包装判断",
  "evaluated_title": {{
    "id": "current_title",
    "title": "当前标题",
    "style": "当前标题所属风格，没有则概括",
    "hook_point": "当前标题抓人的核心点",
    "overall_score": 78,
    "verdict": "足够吸睛/可用但偏弱/不够抓人",
    "reason": "对当前标题的整体判断",
    "scores": [
      {{"id": "eye_catch", "name": "抓眼度", "score": 82, "reason": "评分原因"}},
      {{"id": "conflict", "name": "冲突感", "score": 75, "reason": "评分原因"}},
      {{"id": "info_density", "name": "信息密度", "score": 70, "reason": "评分原因"}},
      {{"id": "genre_fit", "name": "短剧风格贴合度", "score": 84, "reason": "评分原因"}},
      {{"id": "spreadability", "name": "传播话题性", "score": 79, "reason": "评分原因"}}
    ]
  }},
  "recommended_title_id": "title_2",
  "recommended_reason": "为什么这一条最适合当前短剧发行",
  "title_suggestions": [
    {{
      "id": "title_1",
      "title": "建议标题",
      "style": "甜宠/打脸/悬疑/身份反转等",
      "hook_point": "这一条标题的抓人点",
      "overall_score": 90,
      "verdict": "强推荐/可用/偏弱",
      "reason": "为什么能打",
      "scores": [
        {{"id": "eye_catch", "name": "抓眼度", "score": 90, "reason": "评分原因"}},
        {{"id": "conflict", "name": "冲突感", "score": 88, "reason": "评分原因"}},
        {{"id": "info_density", "name": "信息密度", "score": 84, "reason": "评分原因"}},
        {{"id": "genre_fit", "name": "短剧风格贴合度", "score": 92, "reason": "评分原因"}},
        {{"id": "spreadability", "name": "传播话题性", "score": 89, "reason": "评分原因"}}
      ]
    }}
  ],
  "topic_tags": ["#豪门反转", "#身份打脸", "#前任追妻", "#短剧推荐"]
}}

额外要求：
1. title_suggestions 输出 4-6 条。
2. 如果当前标题为空，evaluated_title 也要输出，但 title 和 verdict 要明确说明“暂无当前标题，仅基于剧本判断建议方向”。
3. topic_tags 输出 4-6 个，统一带 #。
""".strip()


def _cover_packaging_prompt(payload: Dict[str, Any]) -> str:
    project = payload.get("project", {}) if isinstance(payload, dict) else {}
    story_card = payload.get("story_card", {}) if isinstance(payload, dict) else {}
    workshop = payload.get("workshop", {}) if isinstance(payload, dict) else {}
    storyboard = payload.get("storyboard", {}) if isinstance(payload, dict) else {}
    current_title = payload.get("current_title", "") if isinstance(payload, dict) else ""
    style_preference = payload.get("style_preference", "") if isinstance(payload, dict) else ""
    focus_point = payload.get("focus_point", "") if isinstance(payload, dict) else ""

    return f"""
你是短剧封面包装顾问，擅长把短剧卖点转成封面文案与视觉方向。
请基于下面内容，输出一个可直接用于做封面的策划方案。
要求严格输出 JSON，不要输出 markdown，不要附加解释。

封面目标：
1. 一眼看懂人物关系、冲突或爽点。
2. 文案适合短剧封面，不要写成长文标题党段落。
3. 视觉方向要能直接交给设计师或文生图工具。
4. 优先突出最能吸引点击的一个核心卖点。

当前项目：
{json.dumps(project, ensure_ascii=False)}

当前标题：
{current_title}

封面风格偏好：
{style_preference}

封面主打点：
{focus_point}

故事卡：
{json.dumps(story_card, ensure_ascii=False)}

剧本工坊：
{json.dumps(workshop, ensure_ascii=False)}

分镜工厂：
{json.dumps(storyboard, ensure_ascii=False)}

JSON schema:
{{
  "current_title": "{current_title}",
  "style_preference": "{style_preference}",
  "focus_point": "{focus_point}",
  "summary": "一句话总结这张封面应该怎么打",
  "main_title": "封面主标题",
  "subtitle": "封面副标题或补充文案",
  "hook_lines": ["封面短句1", "封面短句2", "封面短句3"],
  "visual_direction": "主视觉方向，包含人物状态、关系张力、场景气质",
  "layout_direction": "排版建议，说明标题、人物、冲突信息怎么放",
  "color_palette": "建议色调，例如冷黑红、豪门金黑、清冷蓝灰",
  "image_prompt": "可直接用于文生图的中文封面提示词"
}}

额外要求：
1. hook_lines 输出 2-4 条，短、狠、能上封面。
2. main_title 和 subtitle 都要适合封面排版，不要太长。
3. image_prompt 必须包含人物关系、情绪、构图、光线、风格关键词。
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
    "story_card": {{}},
    "workshop": {{}},
    "storyboard": {{}}
  }},
  "consistency_report": ["一致性检查结果"],
  "suggestions": ["下一步建议"]
}}
""".strip()
