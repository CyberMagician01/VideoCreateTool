from typing import Any, Dict, List, Optional


_STORY_HIT_TEMPLATES: List[Dict[str, Any]] = [
    {
        "id": "reverse-slap",
        "name": "反转打脸",
        "category": "强反转",
        "summary": "先让主角被轻视或误判，再用身份、能力或证据完成反杀。",
        "opening_hook_formula": "所有人都觉得主角输定了，但一个隐藏信息马上改写局势。",
        "conflict_escalation": [
            "开场3秒先抛出羞辱或公开否定",
            "中段持续加码压力，让主角看起来没有翻盘空间",
            "转折点揭露关键身份、证据或筹码，立刻反转关系强弱",
        ],
        "cliffhanger_strategy": "打脸完成后再抛出更大对手或更深内幕，让观众想继续追。",
        "recommended_tone": "爽感强、节奏快、情绪上扬",
        "recommended_structure": "压制 -> 加码 -> 反杀 -> 留更大局",
    },
    {
        "id": "suspense-chase",
        "name": "悬疑追问",
        "category": "悬疑",
        "summary": "用异常事件开场，让观众先产生疑问，再逐步揭开真相的一角。",
        "opening_hook_formula": "主角刚出现就遇到不合常理的异常，观众立刻想知道为什么。",
        "conflict_escalation": [
            "开场先给异常现象，不解释原因",
            "中段每推进一步就出现新的矛盾证据",
            "转折点给出半真相，解一个谜同时再埋一个更大的谜",
        ],
        "cliffhanger_strategy": "结尾揭示关键线索不完整，让观众只看见真相的一半。",
        "recommended_tone": "冷感、压迫、持续吊胃口",
        "recommended_structure": "异常 -> 追查 -> 伪答案 -> 真谜团",
    },
    {
        "id": "sweet-misunderstanding",
        "name": "甜宠误会",
        "category": "情感",
        "summary": "角色之间明明有感情，但因为误会和嘴硬不断错位拉扯。",
        "opening_hook_formula": "两人一见面就针锋相对，但细节暴露出彼此在意。",
        "conflict_escalation": [
            "开场先制造嘴硬和误会碰撞",
            "中段通过第三人、误听或错位行动扩大误会",
            "转折点用一个高糖动作或真心话撕开情绪裂口",
        ],
        "cliffhanger_strategy": "关系刚有回暖就插入新误会或新竞争者。",
        "recommended_tone": "轻甜、拉扯、带一点喜感",
        "recommended_structure": "互怼 -> 误会升级 -> 情绪松动 -> 再拉扯",
    },
    {
        "id": "revenge-comeback",
        "name": "复仇翻盘",
        "category": "逆袭",
        "summary": "主角带着旧伤和目的回到局中，逐步布局并完成第一轮翻盘。",
        "opening_hook_formula": "主角带着明确仇恨目标回归，第一句话就点名要讨回旧账。",
        "conflict_escalation": [
            "开场先交代主角为何回来以及要对谁动手",
            "中段安排敌方继续压制，凸显旧仇未消",
            "转折点用埋伏好的证据、资源或同盟完成第一次翻盘",
        ],
        "cliffhanger_strategy": "复仇刚起势，就揭示真正幕后人还没出场。",
        "recommended_tone": "冷狠、克制、越看越爽",
        "recommended_structure": "归来 -> 试探 -> 布局 -> 首轮翻盘",
    },
    {
        "id": "identity-gap",
        "name": "身份反差",
        "category": "反差",
        "summary": "角色表面身份普通，但真实身份极具冲击力，形成强烈反差。",
        "opening_hook_formula": "观众先看到角色的普通一面，立刻被另一个极端身份打破认知。",
        "conflict_escalation": [
            "开场先立住低预期或普通身份",
            "中段让他人基于错误认知持续误判主角",
            "转折点曝光真实身份，直接重置人物关系",
        ],
        "cliffhanger_strategy": "身份曝光后，马上引出这个身份背后的代价或禁忌。",
        "recommended_tone": "反差强、节奏利落、带惊喜",
        "recommended_structure": "伪装 -> 误判 -> 曝光 -> 新危机",
    },
    {
        "id": "workplace-rise",
        "name": "职场逆袭",
        "category": "现实爽感",
        "summary": "从职场压制开局，通过能力、洞察或关键资源实现反击。",
        "opening_hook_formula": "主角在会议、竞标或汇报现场被公开质疑，局面非常难堪。",
        "conflict_escalation": [
            "开场用公开场合的否定制造压迫感",
            "中段让上级、同事或对手继续围堵",
            "转折点用专业实力或隐藏方案直接扭转评价",
        ],
        "cliffhanger_strategy": "翻盘后抛出更大的职场博弈或高层关注。",
        "recommended_tone": "写实、利落、持续抬升",
        "recommended_structure": "压制 -> 围堵 -> 亮底牌 -> 更大博弈",
    },
    {
        "id": "family-conflict",
        "name": "家庭冲突",
        "category": "情绪冲突",
        "summary": "通过家庭关系中的偏爱、误解或旧伤，迅速制造共情和争议。",
        "opening_hook_formula": "家人之间一句偏心或误解的话，立刻点燃积压已久的情绪。",
        "conflict_escalation": [
            "开场先给一句最扎心的话",
            "中段翻出旧账、偏爱或牺牲，让冲突持续走高",
            "转折点让一个隐瞒已久的真相被迫揭开",
        ],
        "cliffhanger_strategy": "真相揭开后，不是和解，而是关系走向更难处理的局面。",
        "recommended_tone": "高共情、高争议、情绪冲击强",
        "recommended_structure": "扎心开场 -> 旧账翻涌 -> 真相揭开 -> 关系悬置",
    },
    {
        "id": "campus-crush",
        "name": "校园暗恋反转",
        "category": "青春",
        "summary": "用青春期的误会、暗恋和身份落差制造轻快又上头的追更感。",
        "opening_hook_formula": "主角以为自己暗恋无望，却在一个意外瞬间发现对方也在注意自己。",
        "conflict_escalation": [
            "开场先给暗恋的心酸或尴尬",
            "中段用同学起哄、误传或竞争者制造错位",
            "转折点让对方做出一个超出预期的暧昧动作",
        ],
        "cliffhanger_strategy": "刚确认一点心意，就被新的误会打断。",
        "recommended_tone": "轻快、暧昧、节奏明亮",
        "recommended_structure": "暗恋暴露 -> 错位拉扯 -> 暧昧升温 -> 再起误会",
    },
    {
        "id": "marriage-shura",
        "name": "婚恋修罗场",
        "category": "情感冲突",
        "summary": "围绕婚恋选择、旧爱回归或公开关系制造多方拉扯。",
        "opening_hook_formula": "主角刚想稳定关系，旧人或隐情就在最不合时宜的时候出现。",
        "conflict_escalation": [
            "开场先让现有关系出现裂纹",
            "中段让旧爱、家人或利益因素一起施压",
            "转折点用公开选择或关键表态引爆场面",
        ],
        "cliffhanger_strategy": "表态之后留一个更难回答的问题给下一集。",
        "recommended_tone": "浓烈、抓马、情绪密度高",
        "recommended_structure": "旧情入场 -> 多方施压 -> 公开表态 -> 更难选择",
    },
    {
        "id": "rich-family-secret",
        "name": "豪门秘密",
        "category": "强戏剧",
        "summary": "用秘密血缘、遗嘱、联姻或身份隐瞒制造持续的追更动力。",
        "opening_hook_formula": "一个看似体面的豪门场合，突然出现不该出现的人或信息。",
        "conflict_escalation": [
            "开场先用失控的豪门场面抓眼球",
            "中段把利益、身份和旧秘密交叉推进",
            "转折点抛出能改变继承或关系格局的信息",
        ],
        "cliffhanger_strategy": "大秘密刚露头，就说明还有人提前知道真相。",
        "recommended_tone": "华丽、压迫、戏剧张力强",
        "recommended_structure": "失控开场 -> 利益纠缠 -> 秘密浮出 -> 黑手未明",
    },
    {
        "id": "time-loop",
        "name": "时间循环",
        "category": "设定向",
        "summary": "主角陷入重复时间，用一次次失败推动认知升级和关键反转。",
        "opening_hook_formula": "主角刚经历重大变故，下一秒却发现时间回到了起点。",
        "conflict_escalation": [
            "开场先让观众明确循环已经开始",
            "中段通过多次尝试展示规则和失败代价",
            "转折点让主角发现循环背后的关键变量",
        ],
        "cliffhanger_strategy": "主角刚找到破局方向，就发现自己可能只是更大循环的一层。",
        "recommended_tone": "高概念、紧张、带智性快感",
        "recommended_structure": "循环出现 -> 多次试错 -> 发现规则 -> 更大谜题",
    },
    {
        "id": "healing-redemption",
        "name": "救赎治愈反差",
        "category": "治愈",
        "summary": "让带伤的人在冲突关系中慢慢靠近，用高反差情绪抓住观众。",
        "opening_hook_formula": "一个看起来最冷的人，做出了一件极温柔的小事。",
        "conflict_escalation": [
            "开场先立住人物外冷内热的反差",
            "中段让双方因为旧伤互相试探又互相刺痛",
            "转折点用一次主动保护或坦白完成情绪突破",
        ],
        "cliffhanger_strategy": "刚建立信任，就让旧伤来源重新出现。",
        "recommended_tone": "克制、温柔、后劲强",
        "recommended_structure": "反差钩子 -> 情绪试探 -> 真心流露 -> 旧伤回返",
    },
]


def _template_to_public(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": item["id"],
        "name": item["name"],
        "category": item["category"],
        "summary": item["summary"],
        "opening_hook_formula": item["opening_hook_formula"],
        "conflict_escalation": list(item["conflict_escalation"]),
        "cliffhanger_strategy": item["cliffhanger_strategy"],
        "recommended_tone": item["recommended_tone"],
        "recommended_structure": item["recommended_structure"],
    }


def _list_story_templates() -> List[Dict[str, Any]]:
    return [_template_to_public(item) for item in _STORY_HIT_TEMPLATES]


def _get_story_template(template_id: str) -> Optional[Dict[str, Any]]:
    target = str(template_id or "").strip()
    if not target:
        return None
    for item in _STORY_HIT_TEMPLATES:
        if item["id"] == target:
            return _template_to_public(item)
    return None
