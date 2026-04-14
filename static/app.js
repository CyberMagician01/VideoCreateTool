const STORAGE_KEY = 'ai_short_drama_state_v1';
const PROVIDER_KEY = 'ai_short_drama_provider_v1';
const CURRENT_PROJECT_KEY = 'ai_short_drama_current_project_id_v1';
const FLOATING_WIDGET_POSITIONS_KEY = 'ai_short_drama_floating_widget_positions_v1';
const AUTO_SAVE_DELAY_MS = 3000;

const EMPTY_STATE = {
  story_inputs: {
    idea: '',
    theme: '',
    tone: '',
    structure: '',
    template_id: '',
  },
  story_card: null,
  review_lab: {
    latest_review: {
      summary: '',
      overall_score: 0,
      dimensions: [],
      top_issues: [],
      priority_actions: [],
      low_score_dimensions: [],
    },
    rewrite_candidates: [],
    last_review_stage: '',
    last_review_time: '',
  },
  title_lab: {
    current_title: '',
    summary: '',
    evaluated_title: null,
    recommended_title_id: '',
    recommended_reason: '',
    title_suggestions: [],
    topic_tags: [],
    updated_at: '',
  },
  cover_lab: {
    current_title: '',
    style_preference: '',
    focus_point: '',
    summary: '',
    main_title: '',
    subtitle: '',
    hook_lines: [],
    visual_direction: '',
    layout_direction: '',
    color_palette: '',
    image_prompt: '',
    generated_image_url: '',
    image_model: '',
    image_size: '',
    image_task_id: '',
    image_task_status: '',
    image_status_message: '',
    updated_at: '',
  },
  task_meta: null,
  task_meta_expanded: false,
  cost_records: [],
  cost_panel_expanded: false,
  billing_wallet: {
    enabled: false,
    balance: 0,
  },
  workshop: null,
  storyboard: null,
  video_lab: null,
};

function bind(id) {
  return document.getElementById(id);
}

function loadProvider() {
  try {
    return localStorage.getItem(PROVIDER_KEY) || 'qiniu';
  } catch (err) {
    return 'qiniu';
  }
}

function saveProvider(provider) {
  localStorage.setItem(PROVIDER_KEY, provider);
}

function loadCurrentProjectId() {
  try {
    return localStorage.getItem(CURRENT_PROJECT_KEY) || '';
  } catch (err) {
    return '';
  }
}

function saveCurrentProjectId(projectId) {
  localStorage.setItem(CURRENT_PROJECT_KEY, String(projectId || ''));
}

function loadFloatingWidgetPositions() {
  try {
    return JSON.parse(localStorage.getItem(FLOATING_WIDGET_POSITIONS_KEY) || '{}');
  } catch (err) {
    return {};
  }
}

function saveFloatingWidgetPosition(name, position) {
  const positions = loadFloatingWidgetPositions();
  positions[name] = position;
  localStorage.setItem(FLOATING_WIDGET_POSITIONS_KEY, JSON.stringify(positions));
}

function toText(value) {
  if (value === null || value === undefined) {
    return '';
  }
  return String(value).trim();
}

function normalizeStringList(value) {
  if (Array.isArray(value)) {
    return value
      .map((item) => toText(item))
      .filter(Boolean);
  }
  const text = toText(value);
  return text ? [text] : [];
}

function toInt(value, fallback = 0, minimum = null) {
  const parsed = Number.parseInt(value, 10);
  let result = Number.isFinite(parsed) ? parsed : fallback;
  if (minimum !== null) {
    result = Math.max(minimum, result);
  }
  return result;
}

function resolveVideoMode(imageUrl, startImageUrl, endImageUrl) {
  if (startImageUrl && endImageUrl) {
    return 'start_end';
  }
  if (imageUrl) {
    return 'image';
  }
  return 'text';
}

function normalizeProjectSearchKey(value) {
  const text = toText(value);
  if (!text) {
    return '';
  }
  return text
    .normalize('NFKC')
    .toLowerCase()
    .replace(/[?？]/g, '')
    .replace(/\s+/g, '')
    .replace(/[^0-9a-z\u4e00-\u9fa5]/g, '');
}

function extractDigitKey(value) {
  const text = toText(value);
  if (!text) {
    return '';
  }
  const chunks = text.match(/\d+/g);
  return chunks ? chunks.join('') : '';
}

function findProjectByNameLoose(projects, targetName) {
  const items = Array.isArray(projects) ? projects : [];
  const rawTarget = toText(targetName);
  if (!rawTarget) {
    return null;
  }

  const exact = items.find((item) => toText(item?.name) === rawTarget);
  if (exact) {
    return exact;
  }

  const includes = items.find((item) => toText(item?.name).includes(rawTarget));
  if (includes) {
    return includes;
  }

  const targetKey = normalizeProjectSearchKey(rawTarget);
  if (targetKey) {
    const byKey = items.find((item) => {
      const nameKey = normalizeProjectSearchKey(item?.name);
      return Boolean(nameKey) && (nameKey === targetKey || nameKey.includes(targetKey) || targetKey.includes(nameKey));
    });
    if (byKey) {
      return byKey;
    }
  }

  const targetDigits = extractDigitKey(rawTarget);
  if (targetDigits) {
    const digitCandidates = items.filter((item) => extractDigitKey(item?.name) === targetDigits);
    if (digitCandidates.length === 1) {
      return digitCandidates[0];
    }
  }

  return null;
}

function normalizeStoryCard(storyCard) {
  if (!storyCard || typeof storyCard !== 'object') {
    return null;
  }

  const normalized = {
    logline: toText(storyCard.logline),
    theme: toText(storyCard.theme),
    tone: toText(storyCard.tone),
    structure_template: toText(storyCard.structure_template),
    core_conflict: toText(storyCard.core_conflict),
    anchor_points: normalizeStringList(storyCard.anchor_points),
    hook: toText(storyCard.hook),
    ending_type: toText(storyCard.ending_type),
    viral_template_id: toText(storyCard.viral_template_id),
    viral_template_name: toText(storyCard.viral_template_name),
    opening_hook_strategy: toText(storyCard.opening_hook_strategy),
    conflict_escalation_strategy: toText(storyCard.conflict_escalation_strategy),
    cliffhanger_strategy: toText(storyCard.cliffhanger_strategy),
  };

  if (
    normalized.logline ||
    normalized.theme ||
    normalized.tone ||
    normalized.structure_template ||
    normalized.core_conflict ||
    normalized.anchor_points.length ||
    normalized.hook ||
    normalized.ending_type ||
    normalized.viral_template_id ||
    normalized.viral_template_name ||
    normalized.opening_hook_strategy ||
    normalized.conflict_escalation_strategy ||
    normalized.cliffhanger_strategy
  ) {
    return normalized;
  }
  return null;
}

function normalizeStoryInputs(storyInputs) {
  const parsed = (storyInputs && typeof storyInputs === 'object') ? storyInputs : {};
  return {
    idea: toText(parsed.idea),
    theme: toText(parsed.theme),
    tone: toText(parsed.tone),
    structure: toText(parsed.structure),
    template_id: toText(parsed.template_id),
  };
}

function normalizeTitleScore(item, index) {
  if (!item || typeof item !== 'object') {
    return null;
  }
  return {
    id: toText(item.id) || `title_score_${index + 1}`,
    name: toText(item.name) || `维度${index + 1}`,
    score: Math.max(0, Math.min(100, toInt(item.score, 0, 0))),
    reason: toText(item.reason),
  };
}

function normalizeTitleSuggestion(item, index) {
  if (!item || typeof item !== 'object') {
    return null;
  }
  const scores = Array.isArray(item.scores)
    ? item.scores.map((entry, idx) => normalizeTitleScore(entry, idx)).filter(Boolean)
    : [];
  const normalized = {
    id: toText(item.id) || `title_${index + 1}`,
    title: toText(item.title),
    style: toText(item.style),
    hook_point: toText(item.hook_point),
    overall_score: Math.max(0, Math.min(100, toInt(item.overall_score, 0, 0))),
    verdict: toText(item.verdict),
    reason: toText(item.reason),
    scores,
  };
  return normalized.title ? normalized : null;
}

function normalizeTitleLab(titleLab) {
  const base = EMPTY_STATE.title_lab;
  const parsed = (titleLab && typeof titleLab === 'object') ? titleLab : {};
  const evaluatedTitle = normalizeTitleSuggestion(parsed.evaluated_title, 0);
  const titleSuggestions = Array.isArray(parsed.title_suggestions)
    ? parsed.title_suggestions.map((item, index) => normalizeTitleSuggestion(item, index)).filter(Boolean)
    : [];
  let recommendedTitleId = toText(parsed.recommended_title_id);
  if (recommendedTitleId && !titleSuggestions.some((item) => item.id === recommendedTitleId)) {
    recommendedTitleId = '';
  }
  if (!recommendedTitleId && titleSuggestions.length) {
    recommendedTitleId = titleSuggestions[0].id;
  }
  return {
    current_title: toText(parsed.current_title) || base.current_title,
    summary: toText(parsed.summary) || base.summary,
    evaluated_title: evaluatedTitle,
    recommended_title_id: recommendedTitleId,
    recommended_reason: toText(parsed.recommended_reason) || base.recommended_reason,
    title_suggestions: titleSuggestions,
    topic_tags: normalizeStringList(parsed.topic_tags),
    updated_at: toText(parsed.updated_at) || base.updated_at,
  };
}

function normalizeCoverLab(coverLab) {
  const base = EMPTY_STATE.cover_lab;
  const parsed = (coverLab && typeof coverLab === 'object') ? coverLab : {};
  return {
    current_title: toText(parsed.current_title) || base.current_title,
    style_preference: toText(parsed.style_preference) || base.style_preference,
    focus_point: toText(parsed.focus_point) || base.focus_point,
    summary: toText(parsed.summary) || base.summary,
    main_title: toText(parsed.main_title) || base.main_title,
    subtitle: toText(parsed.subtitle) || base.subtitle,
    hook_lines: normalizeStringList(parsed.hook_lines),
    visual_direction: toText(parsed.visual_direction) || base.visual_direction,
    layout_direction: toText(parsed.layout_direction) || base.layout_direction,
    color_palette: toText(parsed.color_palette) || base.color_palette,
    image_prompt: toText(parsed.image_prompt) || base.image_prompt,
    generated_image_url: toText(parsed.generated_image_url) || base.generated_image_url,
    image_model: toText(parsed.image_model) || base.image_model,
    image_size: toText(parsed.image_size) || base.image_size,
    image_task_id: toText(parsed.image_task_id) || base.image_task_id,
    image_task_status: toText(parsed.image_task_status) || base.image_task_status,
    image_status_message: toText(parsed.image_status_message) || base.image_status_message,
    updated_at: toText(parsed.updated_at) || base.updated_at,
  };
}

function normalizeTaskMeta(meta) {
  if (!meta || typeof meta !== 'object') {
    return null;
  }
  const tokens = toInt(meta.estimated_tokens, 0, 0);
  const rawCostPerToken = Number(meta.cost_per_token || 0);
  const hasCostPer1k = meta.cost_per_1k_tokens !== undefined && meta.cost_per_1k_tokens !== null;
  const costPer1kTokens = Number(hasCostPer1k ? meta.cost_per_1k_tokens : (rawCostPerToken >= 0.0001 ? rawCostPerToken : rawCostPerToken * 1000));
  const legacyUnitBug = !hasCostPer1k && rawCostPerToken >= 0.0001 && tokens > 0;
  const promptTokens = toInt(meta.prompt_tokens, 0, 0);
  const completionTokens = toInt(meta.completion_tokens, 0, 0);
  const cacheHitTokens = toInt(meta.cache_hit_tokens, 0, 0);
  const cacheMissTokens = toInt(meta.cache_miss_tokens, 0, 0);
  return {
    stage: toText(meta.stage),
    cost_type: toText(meta.cost_type),
    estimated_duration: meta.estimated_duration,
    estimated_cost: legacyUnitBug ? costPer1kTokens : meta.estimated_cost,
    actual_cost: legacyUnitBug ? (costPer1kTokens * tokens / 1000) : meta.actual_cost,
    retry_count: toInt(meta.retry_count, 0, 0),
    primary_model: toText(meta.primary_model),
    final_model: toText(meta.final_model),
    fallback_triggered: Boolean(meta.fallback_triggered),
    fallback_reason: toText(meta.fallback_reason),
    fallback_from: toText(meta.fallback_from),
    fallback_to: toText(meta.fallback_to),
    estimated_tokens: tokens,
    prompt_tokens: promptTokens,
    completion_tokens: completionTokens,
    cache_hit_tokens: cacheHitTokens,
    cache_miss_tokens: cacheMissTokens,
    cost_per_token: costPer1kTokens / 1000,
    cost_per_1k_tokens: costPer1kTokens,
    input_cost: Number(meta.input_cost || 0),
    output_cost: Number(meta.output_cost || 0),
    input_price_per_1m_tokens: Number(meta.input_price_per_1m_tokens || 0),
    input_cache_hit_price_per_1m_tokens: Number(meta.input_cache_hit_price_per_1m_tokens || 0),
    output_price_per_1m_tokens: Number(meta.output_price_per_1m_tokens || 0),
    video_duration: toInt(meta.video_duration, 0, 0),
    video_size: toText(meta.video_size),
    video_price_per_second: Number(meta.video_price_per_second || 0),
    video_with_reference: Boolean(meta.video_with_reference),
    image_count: toInt(meta.image_count, 0, 0),
    image_size: toText(meta.image_size),
    image_price_per_task: Number(meta.image_price_per_task || 0),
  };
}

function normalizeCostRecord(item, index = 0) {
  if (!item || typeof item !== 'object') {
    return null;
  }
  const tokens = toInt(item.estimated_tokens, 0, 0);
  const rawCostPerToken = Number(item.cost_per_token || 0);
  const hasCostPer1k = item.cost_per_1k_tokens !== undefined && item.cost_per_1k_tokens !== null;
  const costPer1kTokens = Number(hasCostPer1k ? item.cost_per_1k_tokens : (rawCostPerToken >= 0.0001 ? rawCostPerToken : rawCostPerToken * 1000));
  const legacyUnitBug = !hasCostPer1k && rawCostPerToken >= 0.0001 && tokens > 0;
  const promptTokens = toInt(item.prompt_tokens, 0, 0);
  const completionTokens = toInt(item.completion_tokens, 0, 0);
  const cacheHitTokens = toInt(item.cache_hit_tokens, 0, 0);
  const cacheMissTokens = toInt(item.cache_miss_tokens, 0, 0);
  return {
    id: toText(item.id) || `cost_${index + 1}`,
    time: toText(item.time),
    stage: toText(item.stage),
    cost_type: toText(item.cost_type),
    primary_model: toText(item.primary_model),
    final_model: toText(item.final_model),
    estimated_cost: legacyUnitBug ? costPer1kTokens : Number(item.estimated_cost || 0),
    actual_cost: legacyUnitBug ? (costPer1kTokens * tokens / 1000) : Number(item.actual_cost || 0),
    estimated_duration: item.estimated_duration,
    estimated_tokens: tokens,
    prompt_tokens: promptTokens,
    completion_tokens: completionTokens,
    cache_hit_tokens: cacheHitTokens,
    cache_miss_tokens: cacheMissTokens,
    cost_per_token: costPer1kTokens / 1000,
    cost_per_1k_tokens: costPer1kTokens,
    input_cost: Number(item.input_cost || 0),
    output_cost: Number(item.output_cost || 0),
    input_price_per_1m_tokens: Number(item.input_price_per_1m_tokens || 0),
    input_cache_hit_price_per_1m_tokens: Number(item.input_cache_hit_price_per_1m_tokens || 0),
    output_price_per_1m_tokens: Number(item.output_price_per_1m_tokens || 0),
    video_duration: toInt(item.video_duration, 0, 0),
    video_size: toText(item.video_size),
    video_price_per_second: Number(item.video_price_per_second || 0),
    video_with_reference: Boolean(item.video_with_reference),
    image_count: toInt(item.image_count, 0, 0),
    image_size: toText(item.image_size),
    image_price_per_task: Number(item.image_price_per_task || 0),
    retry_count: toInt(item.retry_count, 0, 0),
    fallback_triggered: Boolean(item.fallback_triggered),
    fallback_reason: toText(item.fallback_reason),
  };
}

function normalizeCostRecords(records) {
  if (!Array.isArray(records)) {
    return [];
  }
  return records
    .slice(-80)
    .map((item, index) => normalizeCostRecord(item, index))
    .filter(Boolean);
}

function normalizeBillingWallet(wallet) {
  const parsed = (wallet && typeof wallet === 'object') ? wallet : {};
  return {
    enabled: Boolean(parsed.enabled),
    balance: Math.max(0, Number(parsed.balance || 0)),
  };
}

function normalizeReviewLab(reviewLab) {
  const base = EMPTY_STATE.review_lab;
  const parsed = (reviewLab && typeof reviewLab === 'object') ? reviewLab : {};
  const latest = (parsed.latest_review && typeof parsed.latest_review === 'object') ? parsed.latest_review : {};
  const dimensions = Array.isArray(latest.dimensions)
    ? latest.dimensions
      .map((item, index) => {
        if (!item || typeof item !== 'object') {
          return null;
        }
        return {
          id: toText(item.id) || `dimension_${index + 1}`,
          name: toText(item.name) || `维度${index + 1}`,
          score: Math.max(0, Math.min(100, toInt(item.score, 0, 0))),
          reason: toText(item.reason),
          suggestion: toText(item.suggestion),
        };
      })
      .filter(Boolean)
    : [];

  const rewriteCandidates = Array.isArray(parsed.rewrite_candidates)
    ? parsed.rewrite_candidates
      .map((item, index) => {
        if (!item || typeof item !== 'object') {
          return null;
        }
        const target = ['story_card', 'workshop', 'storyboard'].includes(toText(item.target))
          ? toText(item.target)
          : 'story_card';
        const storyCard = normalizeStoryCard(item.story_card);
        const workshop = normalizeWorkshopData(item.workshop);
        const storyboard = normalizeStoryboardData(item.storyboard);
        const hasPayload =
          (target === 'story_card' && storyCard) ||
          (target === 'workshop' && workshop) ||
          (target === 'storyboard' && storyboard);
        if (!hasPayload) {
          return null;
        }
        return {
          id: toText(item.id) || `rewrite_${index + 1}`,
          title: toText(item.title) || `改写版本 ${index + 1}`,
          strategy: toText(item.strategy),
          focus_dimensions: normalizeStringList(item.focus_dimensions),
          target,
          story_card: storyCard,
          workshop,
          storyboard,
        };
      })
      .filter(Boolean)
    : [];

  return {
    latest_review: {
      summary: toText(latest.summary),
      overall_score: Math.max(0, Math.min(100, toInt(latest.overall_score, 0, 0))),
      dimensions,
      top_issues: normalizeStringList(latest.top_issues),
      priority_actions: normalizeStringList(latest.priority_actions),
      low_score_dimensions: normalizeStringList(latest.low_score_dimensions),
    },
    rewrite_candidates: rewriteCandidates,
    last_review_stage: toText(parsed.last_review_stage) || base.last_review_stage,
    last_review_time: toText(parsed.last_review_time) || base.last_review_time,
  };
}

function normalizeWorkshopData(workshop) {
  if (!workshop || typeof workshop !== 'object') {
    return null;
  }

  const characters = Array.isArray(workshop.characters)
    ? workshop.characters
      .map((character) => {
        if (!character || typeof character !== 'object') {
          return null;
        }
        const normalized = {
          name: toText(character.name || character.character_name),
          tags: normalizeStringList(character.tags || character.labels),
          motivation: toText(character.motivation || character.goal),
          arc: toText(character.arc || character.character_arc),
        };
        return normalized.name ? normalized : null;
      })
      .filter(Boolean)
    : [];

  const relationships = Array.isArray(workshop.relationships)
    ? workshop.relationships
      .map((relationship) => {
        if (!relationship || typeof relationship !== 'object') {
          return null;
        }
        const normalized = {
          from: toText(relationship.from || relationship.source || relationship.from_character),
          to: toText(relationship.to || relationship.target || relationship.to_character),
          type: toText(relationship.type || relationship.relationship || relationship.relation),
          tension: toText(relationship.tension || relationship.conflict),
        };
        return normalized.from && normalized.to ? normalized : null;
      })
      .filter(Boolean)
    : [];

  const plotNodes = Array.isArray(workshop.plot_nodes)
    ? workshop.plot_nodes
      .map((node, index) => {
        if (!node || typeof node !== 'object') {
          return null;
        }
        const normalized = {
          id: toText(node.id || node.node_id) || `N${index + 1}`,
          template_stage: toText(node.template_stage || node.phase || node.stage),
          summary: toText(node.summary || node.plot || node.content || node.scene_summary),
          location: toText(node.location || node.scene_location),
          action_draft: toText(node.action_draft || node.action || node.action_description),
          dialogue_draft: normalizeStringList(node.dialogue_draft || node.dialogue || node.dialogues),
          emotion_shift: toText(node.emotion_shift || node.emotional_shift || node.emotion),
          consistency_check: toText(node.consistency_check || node.logic_check || node.consistency),
        };
        return (
          normalized.template_stage ||
          normalized.summary ||
          normalized.location ||
          normalized.action_draft ||
          normalized.dialogue_draft.length ||
          normalized.emotion_shift ||
          normalized.consistency_check
        )
          ? normalized
          : null;
      })
      .filter(Boolean)
    : [];

  const availableIds = new Set(plotNodes.map((node) => node.id));
  let timelineView = normalizeStringList(workshop.timeline_view).filter((id) => availableIds.has(id));
  if (!timelineView.length) {
    timelineView = plotNodes.map((node) => node.id);
  }

  const cardWallGroups = Array.isArray(workshop.card_wall_groups)
    ? workshop.card_wall_groups
      .map((group) => {
        if (!group || typeof group !== 'object') {
          return null;
        }
        const normalized = {
          group: toText(group.group || group.name || group.title),
          node_ids: normalizeStringList(group.node_ids || group.ids).filter((id) => availableIds.has(id)),
        };
        return normalized.group || normalized.node_ids.length ? normalized : null;
      })
      .filter(Boolean)
    : [];

  if (characters.length || relationships.length || plotNodes.length || cardWallGroups.length) {
    return {
      characters,
      relationships,
      plot_nodes: plotNodes,
      timeline_view: timelineView,
      card_wall_groups: cardWallGroups,
    };
  }
  return null;
}

function deriveStoryboardPrompt(shot) {
  return [
    toText(shot.shot_type),
    toText(shot.camera_movement),
    toText(shot.visual_description),
    toText(shot.dialogue_or_sfx),
  ]
    .filter(Boolean)
    .join(' | ');
}

function normalizeStoryboardData(storyboard) {
  if (!storyboard || typeof storyboard !== 'object') {
    return null;
  }

  const storyboards = Array.isArray(storyboard.storyboards)
    ? storyboard.storyboards
      .map((shot, index) => {
        if (!shot || typeof shot !== 'object') {
          return null;
        }
        const normalized = {
          shot_id: toText(shot.shot_id || shot.id) || `S${index + 1}`,
          related_node_id: toText(shot.related_node_id || shot.node_id || shot.plot_node_id),
          shot_type: toText(shot.shot_type || shot.camera_size),
          camera_movement: toText(shot.camera_movement || shot.movement || shot.camera_motion),
          visual_description: toText(
            shot.visual_description || shot.visual || shot.image_description || shot.description,
          ),
          dialogue_or_sfx: toText(shot.dialogue_or_sfx || shot.dialogue || shot.sound_design || shot.audio),
          duration_sec: toInt(shot.duration_sec || shot.duration || shot.estimated_duration, 4, 1),
          shooting_note: toText(shot.shooting_note || shot.note || shot.production_note),
          prompt_draft: toText(shot.prompt_draft || shot.video_prompt || shot.prompt || shot.visual_prompt),
        };
        if (!normalized.prompt_draft) {
          normalized.prompt_draft = deriveStoryboardPrompt(normalized);
        }
        return (
          normalized.related_node_id ||
          normalized.shot_type ||
          normalized.camera_movement ||
          normalized.visual_description ||
          normalized.dialogue_or_sfx ||
          normalized.prompt_draft
        )
          ? normalized
          : null;
      })
      .filter(Boolean)
    : [];

  const estimatedTotalDuration = toInt(
    storyboard.estimated_total_duration_sec,
    storyboards.reduce((sum, shot) => sum + (shot.duration_sec || 0), 0),
    0,
  );

  const exportReadyChecklist = normalizeStringList(storyboard.export_ready_checklist);

  if (storyboards.length || exportReadyChecklist.length || estimatedTotalDuration) {
    return {
      storyboards,
      estimated_total_duration_sec: estimatedTotalDuration,
      export_ready_checklist: exportReadyChecklist,
    };
  }
  return null;
}

function normalizeVideoState(videoLab) {
  const base = {
    script: '',
    prompt: '',
    image_url: '',
    start_image_url: '',
    end_image_url: '',
    audio_url: '',
    audio_mix_url: '',
    audio_mix_source_url: '',
    task_id: '',
    task_status: '',
    video_url: '',
    auto_poll: true,
    last_check_time: '',
    long_segments: [],
    total_duration: 0,
    filename_prefix: '',
  };

  if (!videoLab || typeof videoLab !== 'object') {
    return base;
  }

  const longSegments = Array.isArray(videoLab.long_segments)
    ? videoLab.long_segments
      .map((segment, index) => {
        if (!segment || typeof segment !== 'object') {
          return null;
        }
        return {
          index: toInt(segment.index, index + 1, 1),
          duration: toInt(segment.duration, 0, 0),
          prompt: toText(segment.prompt),
          task_id: toText(segment.task_id),
          task_status: toText(segment.task_status),
          video_url: toText(segment.video_url || segment.url),
        };
      })
      .filter(Boolean)
    : [];

  return {
    script: toText(videoLab.script),
    prompt: toText(videoLab.prompt),
    image_url: toText(videoLab.image_url),
    start_image_url: toText(videoLab.start_image_url),
    end_image_url: toText(videoLab.end_image_url),
    audio_url: toText(videoLab.audio_url),
    audio_mix_url: toText(videoLab.audio_mix_url),
    audio_mix_source_url: toText(videoLab.audio_mix_source_url),
    task_id: toText(videoLab.task_id),
    task_status: toText(videoLab.task_status),
    video_url: toText(videoLab.video_url || videoLab.url),
    auto_poll: videoLab.auto_poll !== false,
    last_check_time: toText(videoLab.last_check_time),
    long_segments: longSegments,
    total_duration: toInt(videoLab.total_duration, 0, 0),
    filename_prefix: toText(videoLab.filename_prefix),
  };
}

const state = { ...EMPTY_STATE };
let currentProvider = loadProvider();
let currentProjectId = loadCurrentProjectId();
let currentProjectMeta = null;
let projectsCache = [];
let snapshotCache = [];
let saveDebounceTimer = null;
let stateDirty = false;
let projectSaveInFlight = false;
let projectDrawerOpen = false;
let pendingBillingRechargeAmount = 0;

let relationshipNetwork = null;
let timelineSortable = null;
let selectedRelationIndex = null;
let draftRelationNodes = [];
let visualUndoStack = [];
let videoPollTimer = null;
let providersList = [];
let storyTemplates = [];
const VIDEO_POLL_INTERVAL_MS = 15000;

function setAutoSaveStatus(text) {
  const target = bind('project-save-status');
  if (target) {
    target.textContent = text;
  }
}

function formatTimeHHmmss(dateObj = new Date()) {
  const h = String(dateObj.getHours()).padStart(2, '0');
  const m = String(dateObj.getMinutes()).padStart(2, '0');
  const s = String(dateObj.getSeconds()).padStart(2, '0');
  return `${h}:${m}:${s}`;
}

function getSelectedStoryTemplate() {
  const templateId = bind('story-template-select')?.value || state.story_inputs?.template_id || '';
  return storyTemplates.find((item) => item.id === templateId) || null;
}

function renderStoryTemplateSummary() {
  const summary = bind('story-template-summary');
  if (!summary) {
    return;
  }
  const template = getSelectedStoryTemplate();
  if (!template) {
    summary.textContent = '不使用模板时，会按你的创意自由生成。';
    return;
  }
  summary.textContent = [
    `模板：${template.name} / ${template.category}`,
    `钩子：${template.opening_hook_formula || '-'}`,
    `升级：${(template.conflict_escalation || []).join(' -> ') || '-'}`,
    `悬念：${template.cliffhanger_strategy || '-'}`,
  ].join('\n');
}

function syncStoryInputsToForm() {
  const storyInputs = normalizeStoryInputs(state.story_inputs);
  const idea = bind('idea');
  const theme = bind('theme');
  const tone = bind('tone');
  const structure = bind('structure');
  const templateSelect = bind('story-template-select');

  if (idea) {
    idea.value = storyInputs.idea || '';
  }
  if (theme) {
    theme.value = storyInputs.theme || '';
  }
  if (tone) {
    tone.value = storyInputs.tone || '';
  }
  if (structure) {
    structure.value = storyInputs.structure || '';
  }
  if (templateSelect) {
    templateSelect.value = storyInputs.template_id || '';
  }
  renderStoryTemplateSummary();
}

function saveStoryInputsFromForm() {
  state.story_inputs = normalizeStoryInputs({
    idea: bind('idea')?.value,
    theme: bind('theme')?.value,
    tone: bind('tone')?.value,
    structure: bind('structure')?.value,
    template_id: bind('story-template-select')?.value,
  });
  saveState();
}

function normalizeState(input) {
  const parsed = (input && typeof input === 'object') ? input : {};
  return {
    story_inputs: normalizeStoryInputs(parsed.story_inputs),
    story_card: normalizeStoryCard(parsed.story_card),
    review_lab: normalizeReviewLab(parsed.review_lab),
    title_lab: normalizeTitleLab(parsed.title_lab),
    cover_lab: normalizeCoverLab(parsed.cover_lab),
    task_meta: normalizeTaskMeta(parsed.task_meta),
    task_meta_expanded: Boolean(parsed.task_meta_expanded),
    cost_records: normalizeCostRecords(parsed.cost_records),
    cost_panel_expanded: Boolean(parsed.cost_panel_expanded),
    billing_wallet: normalizeBillingWallet(parsed.billing_wallet),
    workshop: normalizeWorkshopData(parsed.workshop),
    storyboard: normalizeStoryboardData(parsed.storyboard),
    video_lab: normalizeVideoState(parsed.video_lab),
  };
}

function applyState(newState) {
  const normalized = normalizeState(newState);
  state.story_inputs = normalized.story_inputs;
  state.story_card = normalized.story_card;
  state.review_lab = normalized.review_lab;
  state.title_lab = normalized.title_lab;
  state.cover_lab = normalized.cover_lab;
  state.task_meta = normalized.task_meta;
  state.task_meta_expanded = normalized.task_meta_expanded;
  state.cost_records = normalized.cost_records;
  state.cost_panel_expanded = normalized.cost_panel_expanded;
  state.billing_wallet = normalized.billing_wallet;
  state.workshop = normalized.workshop;
  state.storyboard = normalized.storyboard;
  state.video_lab = normalized.video_lab;
}

function markStateDirty() {
  stateDirty = true;
  scheduleAutoSave();
}

async function saveProjectStateNow() {
  if (!currentProjectId || !stateDirty || projectSaveInFlight) {
    return;
  }
  projectSaveInFlight = true;
  try {
    const data = await fetchJson(`/api/projects/${currentProjectId}/state`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        state,
        last_provider: currentProvider,
        cover_image: currentProjectMeta?.cover_image || '',
      }),
    });
    if (!data.ok) {
      throw new Error(data.error || 'auto save failed');
    }
    stateDirty = false;
    setAutoSaveStatus(`自动保存成功（${formatTimeHHmmss()}）`);
  } catch (err) {
    console.error('auto save failed', err);
  } finally {
    projectSaveInFlight = false;
  }
}

function scheduleAutoSave() {
  if (!currentProjectId) {
    return;
  }
  if (saveDebounceTimer) {
    clearTimeout(saveDebounceTimer);
  }
  saveDebounceTimer = setTimeout(() => {
    saveProjectStateNow().catch((err) => {
      console.error('saveProjectStateNow failed', err);
    });
  }, AUTO_SAVE_DELAY_MS);
}

function saveState() {
  markStateDirty();
}

function clampFloatingWidget(root, left, top) {
  const rect = root.getBoundingClientRect();
  const padding = 12;
  return {
    left: Math.min(Math.max(padding, left), Math.max(padding, window.innerWidth - rect.width - padding)),
    top: Math.min(Math.max(padding, top), Math.max(padding, window.innerHeight - rect.height - padding)),
  };
}

function applyFloatingWidgetPosition(root, position) {
  if (!root || !position) {
    return;
  }
  const next = clampFloatingWidget(root, Number(position.left || 0), Number(position.top || 0));
  root.style.left = `${next.left}px`;
  root.style.top = `${next.top}px`;
  root.style.right = 'auto';
  root.style.bottom = 'auto';
}

function makeFloatingWidgetDraggable(root, handle, storageName) {
  if (!root || !handle) {
    return;
  }
  const savedPosition = loadFloatingWidgetPositions()[storageName];
  applyFloatingWidgetPosition(root, savedPosition);

  let dragging = false;
  let moved = false;
  let suppressClick = false;
  let startX = 0;
  let startY = 0;
  let startLeft = 0;
  let startTop = 0;

  handle.addEventListener('pointerdown', (event) => {
    if (event.button !== 0) {
      return;
    }
    const rect = root.getBoundingClientRect();
    dragging = true;
    moved = false;
    startX = event.clientX;
    startY = event.clientY;
    startLeft = rect.left;
    startTop = rect.top;
    root.classList.add('is-dragging');
    handle.setPointerCapture(event.pointerId);
  });

  handle.addEventListener('pointermove', (event) => {
    if (!dragging) {
      return;
    }
    const deltaX = event.clientX - startX;
    const deltaY = event.clientY - startY;
    if (Math.abs(deltaX) + Math.abs(deltaY) > 4) {
      moved = true;
    }
    if (!moved) {
      return;
    }
    const next = clampFloatingWidget(root, startLeft + deltaX, startTop + deltaY);
    root.style.left = `${next.left}px`;
    root.style.top = `${next.top}px`;
    root.style.right = 'auto';
    root.style.bottom = 'auto';
  });

  handle.addEventListener('pointerup', (event) => {
    if (!dragging) {
      return;
    }
    dragging = false;
    root.classList.remove('is-dragging');
    if (handle.hasPointerCapture(event.pointerId)) {
      handle.releasePointerCapture(event.pointerId);
    }
    if (moved) {
      const rect = root.getBoundingClientRect();
      const next = clampFloatingWidget(root, rect.left, rect.top);
      saveFloatingWidgetPosition(storageName, next);
      suppressClick = true;
      setTimeout(() => {
        suppressClick = false;
      }, 0);
    }
  });

  handle.addEventListener('pointercancel', () => {
    dragging = false;
    root.classList.remove('is-dragging');
  });

  handle.addEventListener('click', (event) => {
    if (!suppressClick) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
  }, true);

  window.addEventListener('resize', () => {
    const rect = root.getBoundingClientRect();
    const next = clampFloatingWidget(root, rect.left, rect.top);
    applyFloatingWidgetPosition(root, next);
    saveFloatingWidgetPosition(storageName, next);
  });
}

function clearOutputsByPage() {
  const ids = [
    'story-output',
    'workshop-output',
    'storyboard-output',
    'command-output',
    'export-output',
    'title-pack-output',
    'video-script-output',
    'video-task-output',
    'video-long-output',
  ];
  ids.forEach((id) => updateOutput(id, ''));

  const wrap = bind('video-result-wrap');
  const player = bind('video-result-player');
  const text = bind('video-result-link');
  if (wrap) wrap.style.display = 'none';
  if (player) player.src = '';
  if (text) text.textContent = '';
}

function pretty(obj) {
  return JSON.stringify(obj, null, 2);
}

function updateOutput(id, text) {
  const target = bind(id);
  if (target) {
    target.textContent = text;
  }
}

function refreshCoreDraftOutputs() {
  if (bind('story-output') && state.story_card) {
    updateOutput('story-output', formatStoryResultV2({ story_card: state.story_card }));
  }
  if (bind('workshop-output') && state.workshop) {
    updateOutput('workshop-output', formatWorkshopResult(state.workshop));
  }
  if (bind('storyboard-output') && state.storyboard) {
    updateOutput('storyboard-output', formatStoryboardResult(state.storyboard));
  }
}

function mergeStoryCardPatch(currentStoryCard, incomingStoryCardRaw) {
  if (!incomingStoryCardRaw || typeof incomingStoryCardRaw !== 'object') {
    return currentStoryCard || null;
  }
  const merged = {
    ...(currentStoryCard || {}),
    ...incomingStoryCardRaw,
  };
  return normalizeStoryCard(merged) || currentStoryCard || null;
}

function mergeWorkshopPatch(currentWorkshop, incomingWorkshopRaw) {
  const incomingWorkshop = normalizeWorkshopData(incomingWorkshopRaw);
  if (!incomingWorkshop) {
    return currentWorkshop || null;
  }
  if (!currentWorkshop) {
    return incomingWorkshop;
  }

  const merged = {
    characters: [],
    relationships: [],
    plot_nodes: [],
    timeline_view: [],
    card_wall_groups: [],
  };

  const characterMap = new Map();
  (currentWorkshop.characters || []).forEach((item) => {
    if (item?.name) {
      characterMap.set(item.name, item);
    }
  });
  (incomingWorkshop.characters || []).forEach((item) => {
    if (!item?.name) return;
    const prev = characterMap.get(item.name) || {};
    characterMap.set(item.name, {
      ...prev,
      ...item,
      tags: (item.tags && item.tags.length) ? item.tags : (prev.tags || []),
    });
  });
  merged.characters = Array.from(characterMap.values());

  const relationMap = new Map();
  const relationKey = (item) => `${item?.from || ''}->${item?.to || ''}`;
  (currentWorkshop.relationships || []).forEach((item) => {
    const key = relationKey(item);
    if (item?.from && item?.to) {
      relationMap.set(key, item);
    }
  });
  (incomingWorkshop.relationships || []).forEach((item) => {
    const key = relationKey(item);
    if (item?.from && item?.to) {
      const prev = relationMap.get(key) || {};
      relationMap.set(key, { ...prev, ...item });
    }
  });
  merged.relationships = Array.from(relationMap.values());

  const nodeMap = new Map();
  (currentWorkshop.plot_nodes || []).forEach((item) => {
    if (item?.id) {
      nodeMap.set(item.id, item);
    }
  });
  (incomingWorkshop.plot_nodes || []).forEach((item) => {
    if (!item?.id) return;
    const prev = nodeMap.get(item.id) || {};
    nodeMap.set(item.id, {
      ...prev,
      ...item,
      dialogue_draft: (item.dialogue_draft && item.dialogue_draft.length)
        ? item.dialogue_draft
        : (prev.dialogue_draft || []),
    });
  });
  merged.plot_nodes = Array.from(nodeMap.values());

  merged.timeline_view = (incomingWorkshop.timeline_view && incomingWorkshop.timeline_view.length)
    ? incomingWorkshop.timeline_view
    : (currentWorkshop.timeline_view || []);
  if (!merged.timeline_view.length && merged.plot_nodes.length) {
    merged.timeline_view = merged.plot_nodes.map((item) => item.id).filter(Boolean);
  }

  const groupMap = new Map();
  (currentWorkshop.card_wall_groups || []).forEach((item) => {
    if (item?.group) {
      groupMap.set(item.group, item);
    }
  });
  (incomingWorkshop.card_wall_groups || []).forEach((item) => {
    if (!item?.group) return;
    const prev = groupMap.get(item.group) || { group: item.group, node_ids: [] };
    groupMap.set(item.group, {
      group: item.group,
      node_ids: Array.from(new Set([...(prev.node_ids || []), ...(item.node_ids || [])])),
    });
  });
  merged.card_wall_groups = Array.from(groupMap.values());

  return normalizeWorkshopData(merged) || currentWorkshop || null;
}

function mergeStoryboardPatch(currentStoryboard, incomingStoryboardRaw) {
  const incomingStoryboard = normalizeStoryboardData(incomingStoryboardRaw);
  if (!incomingStoryboard) {
    return currentStoryboard || null;
  }
  if (!currentStoryboard) {
    return incomingStoryboard;
  }

  const shotMap = new Map();
  (currentStoryboard.storyboards || []).forEach((item) => {
    if (item?.shot_id) {
      shotMap.set(item.shot_id, item);
    }
  });
  (incomingStoryboard.storyboards || []).forEach((item) => {
    if (!item?.shot_id) return;
    const prev = shotMap.get(item.shot_id) || {};
    shotMap.set(item.shot_id, {
      ...prev,
      ...item,
    });
  });

  const merged = {
    storyboards: Array.from(shotMap.values()),
    estimated_total_duration_sec: incomingStoryboard.estimated_total_duration_sec
      || currentStoryboard.estimated_total_duration_sec
      || 0,
    export_ready_checklist: (incomingStoryboard.export_ready_checklist && incomingStoryboard.export_ready_checklist.length)
      ? incomingStoryboard.export_ready_checklist
      : (currentStoryboard.export_ready_checklist || []),
  };
  return normalizeStoryboardData(merged) || currentStoryboard || null;
}

function formatCommandResult(result) {
  let cmdText = `【理解命令】\n${result?.command_understanding || '-'}\n\n`;
  cmdText += '【一致性检查】\n';
  if (result?.consistency_report?.length) {
    result.consistency_report.forEach((item) => {
      cmdText += `- ${item}\n`;
    });
  } else {
    cmdText += '-\n';
  }

  cmdText += '\n【下一步建议】\n';
  if (result?.suggestions?.length) {
    result.suggestions.forEach((item) => {
      cmdText += `- ${item}\n`;
    });
  } else {
    cmdText += '-\n';
  }
  return cmdText.trim();
}

async function applyCommandStatePatch(result) {
  const updatedState = (result && typeof result === 'object' && result.updated_state && typeof result.updated_state === 'object')
    ? result.updated_state
    : {};
  let hasStateChanged = false;

  if (Object.prototype.hasOwnProperty.call(updatedState, 'story_card')) {
    const nextStoryCard = mergeStoryCardPatch(state.story_card, updatedState.story_card);
    if (JSON.stringify(nextStoryCard) !== JSON.stringify(state.story_card)) {
      state.story_card = nextStoryCard;
      hasStateChanged = true;
    }
  }

  if (Object.prototype.hasOwnProperty.call(updatedState, 'workshop')) {
    const nextWorkshop = mergeWorkshopPatch(state.workshop, updatedState.workshop);
    if (JSON.stringify(nextWorkshop) !== JSON.stringify(state.workshop)) {
      state.workshop = nextWorkshop;
      hasStateChanged = true;
    }
  }

  if (Object.prototype.hasOwnProperty.call(updatedState, 'storyboard')) {
    const nextStoryboard = mergeStoryboardPatch(state.storyboard, updatedState.storyboard);
    if (JSON.stringify(nextStoryboard) !== JSON.stringify(state.storyboard)) {
      state.storyboard = nextStoryboard;
      hasStateChanged = true;
    }
  }

  if (!hasStateChanged) {
    return false;
  }

  setAutoSaveStatus('命令已应用，正在保存...');
  saveState();
  refreshCoreDraftOutputs();
  refreshVisualEditors();
  await saveProjectStateNow();

  if (bind('review-panel')) {
    renderReviewLab('正在根据最新修改重新评分...');
    const nextStage = inferReviewStage();
    await runStoryReviewFlow(nextStage, { withRewrite: stageSupportsRewrite(nextStage) });
  }

  return true;
}

async function executeGlobalCommand(commandText, options = {}) {
  const opts = {
    outputId: 'command-output',
    source: 'text',
    setStatus: null,
    ...options,
  };
  const text = toText(commandText);

  if (!text) {
    if (opts.outputId) {
      updateOutput(opts.outputId, '请先输入命令。');
    }
    if (typeof opts.setStatus === 'function') {
      opts.setStatus('请先输入命令。', true);
    }
    return { ok: false, text: '', error: 'empty_command' };
  }

  if (opts.outputId) {
    updateOutput(opts.outputId, opts.source === 'voice' ? '正在识别并执行语音命令...' : '执行中...');
  }
  if (typeof opts.setStatus === 'function') {
    opts.setStatus('正在执行命令...');
  }

  try {
    const payload = {
      command: text,
      project_state: {
        story_card: state.story_card,
        workshop: state.workshop,
        storyboard: state.storyboard,
      },
    };

    const data = await runStage('command', payload);
    if (!data.ok) {
      const errorText = `错误: ${data.error}\n${data.detail || ''}`.trim();
      if (opts.outputId) {
        updateOutput(opts.outputId, errorText);
      }
      if (typeof opts.setStatus === 'function') {
        opts.setStatus(`执行失败：${data.error || 'unknown'}`, true);
      }
      return { ok: false, text: errorText, error: data.error || 'command_failed' };
    }

    await applyCommandStatePatch(data.result);
    const formatted = formatCommandResult(data.result);
    if (opts.outputId) {
      updateOutput(opts.outputId, formatted);
    }
    if (typeof opts.setStatus === 'function') {
      opts.setStatus('命令执行成功。');
    }
    return { ok: true, text: formatted, result: data.result };
  } catch (err) {
    const errorText = `错误: ${err.message || err}`;
    if (opts.outputId) {
      updateOutput(opts.outputId, errorText);
    }
    if (typeof opts.setStatus === 'function') {
      opts.setStatus(`执行失败：${err.message || err}`, true);
    }
    return { ok: false, text: errorText, error: err.message || String(err) };
  }
}

async function routeGlobalIntent(utterance) {
  const payload = {
    utterance: toText(utterance),
    project_state: {
      story_card: state.story_card,
      workshop: state.workshop,
      storyboard: state.storyboard,
    },
    context: {
      current_project_id: currentProjectId || '',
      current_project_name: currentProjectMeta?.name || '',
      page_path: window.location.pathname,
      available_projects: (projectsCache || []).map((item) => ({ id: String(item.id || ''), name: item.name || '' })),
      video_task_id: state.video_lab?.task_id || '',
    },
  };
  const data = await runStage('global_router', payload);
  return data;
}

async function executeRoutedAction(routeResult, rawCommand, options = {}) {
  const opts = {
    source: 'text',
    setStatus: null,
    ...options,
  };
  const intent = routeResult?.intent || {};
  const params = routeResult?.params || {};
  const moduleName = toText(intent.module);
  const action = toText(intent.action);

  if (moduleName === 'creative' && action === 'edit_story') {
    const commandText = toText(params.command_text) || toText(rawCommand);
    return executeGlobalCommand(commandText, { outputId: null, source: opts.source, setStatus: opts.setStatus });
  }

  if (moduleName === 'video' && action === 'query_task') {
    const taskId = toText(params.task_id) || toText(state.video_lab?.task_id);
    if (!taskId) {
      return { ok: false, text: '未提供 task_id，请补充“查询哪个任务”。', error: 'missing_task_id' };
    }
    const data = await fetchJson(`/api/video/task/${taskId}`, { method: 'GET' });
    if (!data.ok) {
      return { ok: false, text: `查询失败: ${data.error || 'unknown'}`, error: data.error || 'query_failed' };
    }
    const output = data.result?.output || data.result || {};
    const video = getVideoState();
    video.task_id = taskId;
    video.task_status = output.task_status || output.status || video.task_status || '';
    video.video_url = output.video_url || output.url || output?.result?.video?.url || video.video_url || '';
    video.last_check_time = new Date().toLocaleString();
    saveState();
    if (video.video_url) {
      const renderUrl = await ensureVideoBgmMixed(video.video_url, { silent: true });
      renderVideoResult(renderUrl);
    }
    const text = `视频任务状态: ${video.task_status || 'UNKNOWN'}\nTask ID: ${taskId}${video.video_url ? `\nURL: ${video.video_url}` : ''}`;
    return { ok: true, text };
  }

  if (moduleName === 'video' && action === 'create_task') {
    const prompt = toText(params.prompt) || toText(state.video_lab?.prompt) || toText(bind('video-prompt')?.value);
    if (!prompt) {
      return { ok: false, text: '请先提供视频提示词。', error: 'missing_prompt' };
    }
    const payload = {
      prompt,
      model: toText(params.model) || 'viduq3-turbo',
      size: toText(params.size) || '1280*720',
      duration: toInt(params.duration, 10, 1),
      prompt_extend: true,
      image_url: toText(state.video_lab?.image_url),
      start_image_url: toText(state.video_lab?.start_image_url),
      end_image_url: toText(state.video_lab?.end_image_url),
      video_mode: resolveVideoMode(
        toText(state.video_lab?.image_url),
        toText(state.video_lab?.start_image_url),
        toText(state.video_lab?.end_image_url),
      ),
    };
    const data = await fetchJson('/api/video/create-task', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ payload }),
    });
    if (!data.ok) {
      return { ok: false, text: `创建失败: ${data.error || 'unknown'}`, error: data.error || 'create_video_failed' };
    }
    const output = data.result?.output || data.result || {};
    const video = getVideoState();
    video.prompt = payload.prompt;
    video.task_id = output.task_id || output.request_id || '';
    video.task_status = output.task_status || output.status || 'PENDING';
    saveState();
    return { ok: true, text: `已创建视频任务\nTask ID: ${video.task_id}\n状态: ${video.task_status}` };
  }

  if (moduleName === 'project' && action === 'create_project') {
    const projectName = toText(params.project_name) || `语音项目 ${formatTimeHHmmss()}`;
    const data = await fetchJson('/api/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: projectName,
        creator: '语音助手',
        description: '',
        state: EMPTY_STATE,
        last_provider: currentProvider,
      }),
    });
    if (!data.ok) {
      return { ok: false, text: `创建项目失败: ${data.error || 'unknown'}`, error: data.error || 'create_project_failed' };
    }
    await loadProjects();
    if (data.project?.id) {
      await switchProject(String(data.project.id));
    }
    return { ok: true, text: `已创建并切换到项目：${projectName}` };
  }

  if (moduleName === 'project' && action === 'switch_project') {
    const targetId = toText(params.project_id);
    const targetName = toText(params.project_name);
    let selected = null;
    if (targetId) {
      selected = (projectsCache || []).find((item) => String(item.id) === targetId);
    }
    if (!selected && targetName) {
      selected = findProjectByNameLoose(projectsCache || [], targetName);
    }
    if (!selected) {
      return { ok: false, text: '未找到目标项目，请补充项目名。', error: 'project_not_found' };
    }
    await switchProject(String(selected.id));
    return { ok: true, text: `已切换到项目：${selected.name || selected.id}` };
  }

  if (moduleName === 'project' && action === 'create_snapshot') {
    if (!currentProjectId) {
      return { ok: false, text: '当前没有可用项目。', error: 'missing_project' };
    }
    const data = await fetchJson(`/api/projects/${currentProjectId}/snapshots`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: toText(params.snapshot_name) || `语音快照 ${new Date().toLocaleString()}`,
        description: toText(params.snapshot_description),
      }),
    });
    if (!data.ok) {
      return { ok: false, text: `保存快照失败: ${data.error || 'unknown'}`, error: data.error || 'snapshot_failed' };
    }
    snapshotCache = data.snapshots || snapshotCache;
    renderSnapshotList();
    return { ok: true, text: `快照已保存：${data.snapshot?.name || '未命名快照'}` };
  }

  if (moduleName === 'export' && action === 'export_markdown') {
    const data = await runStage('export', buildExportPayload());
    if (!data.ok) {
      return { ok: false, text: `导出失败: ${data.error || 'unknown'}`, error: data.error || 'export_failed' };
    }
    const markdownText = toText(data.result?.markdown || data.result || '');
    return { ok: true, text: markdownText || '导出完成。' };
  }

  if (moduleName === 'export' && action === 'export_docx') {
    await downloadFile('/api/export/docx', 'ai_short_drama_export.docx', buildExportPayload());
    return { ok: true, text: '已开始下载 DOCX。' };
  }

  if (moduleName === 'export' && action === 'export_pdf') {
    await downloadFile('/api/export/pdf', 'ai_short_drama_export.pdf', buildExportPayload());
    return { ok: true, text: '已开始下载 PDF。' };
  }

  return {
    ok: false,
    text: '暂时无法执行该命令，请换个说法或补充细节。',
    error: 'unsupported_intent',
  };
}

function getIntentActionLabel(intent) {
  const moduleName = toText(intent?.module);
  const action = toText(intent?.action);
  const key = `${moduleName}/${action}`;
  const labels = {
    'creative/edit_story': '编辑创作内容',
    'video/create_task': '创建视频任务',
    'video/query_task': '查询视频任务',
    'project/create_project': '新建项目',
    'project/switch_project': '切换项目',
    'project/create_snapshot': '创建项目快照',
    'export/export_markdown': '导出 Markdown',
    'export/export_docx': '导出 DOCX',
    'export/export_pdf': '导出 PDF',
  };
  return labels[key] || '执行动作';
}

function shouldForceConfirmation(routeResult) {
  const moduleName = toText(routeResult?.intent?.module);
  const action = toText(routeResult?.intent?.action);
  const risk = toText(routeResult?.intent?.risk_level).toLowerCase();
  if (risk === 'high') return true;
  if (moduleName === 'project' && action === 'switch_project') return true;
  if (moduleName === 'export' && ['export_docx', 'export_pdf'].includes(action)) return true;
  return false;
}

function buildConfirmationMessage(routeResult) {
  const safety = routeResult?.safety || {};
  const custom = toText(safety.confirm_message);
  if (custom) return custom;

  const moduleName = toText(routeResult?.intent?.module);
  const action = toText(routeResult?.intent?.action);
  const params = routeResult?.params || {};
  const label = getIntentActionLabel(routeResult?.intent);

  if (moduleName === 'project' && action === 'switch_project') {
    const target = toText(params.project_name) || toText(params.project_id) || '目标项目';
    return `将切换到项目「${target}」，是否继续？`;
  }
  if (moduleName === 'export' && action === 'export_docx') {
    return '将触发 DOCX 导出并下载文件，是否继续？';
  }
  if (moduleName === 'export' && action === 'export_pdf') {
    return '将触发 PDF 导出并下载文件，是否继续？';
  }
  return `将执行「${label}」，是否继续？`;
}

function buildClarifyQuestions(routeResult, rawCommand) {
  const routeQuestions = Array.isArray(routeResult?.clarify_questions) ? routeResult.clarify_questions : [];
  const questions = [...routeQuestions];
  const moduleName = toText(routeResult?.intent?.module);
  const action = toText(routeResult?.intent?.action);
  const params = routeResult?.params || {};
  const raw = toText(rawCommand);

  if (moduleName === 'creative' && action === 'edit_story') {
    if (!toText(params.command_text) && !raw) {
      questions.push('你想改的是哪一段剧情或角色？');
    }
  }
  if (moduleName === 'video' && action === 'create_task') {
    if (!toText(params.prompt) && !toText(state.video_lab?.prompt)) {
      questions.push('请补充视频提示词（想拍什么画面）。');
    }
  }
  if (moduleName === 'video' && action === 'query_task') {
    if (!toText(params.task_id) && !toText(state.video_lab?.task_id)) {
      questions.push('请告诉我要查询的 Task ID。');
    }
  }
  if (moduleName === 'project' && action === 'switch_project') {
    if (!toText(params.project_id) && !toText(params.project_name)) {
      questions.push('请告诉我要切换到的项目名。');
    }
  }
  return Array.from(new Set(questions.filter(Boolean)));
}

async function executeGlobalAssistantCommand(commandText, options = {}) {
  const opts = {
    source: 'text',
    outputId: null,
    setStatus: null,
    ...options,
  };
  const text = toText(commandText);
  if (!text) {
    const msg = '请先输入命令。';
    if (typeof opts.setStatus === 'function') {
      opts.setStatus(msg, true);
    }
    if (opts.outputId) {
      updateOutput(opts.outputId, msg);
    }
    return { ok: false, text: msg, error: 'empty_command' };
  }

  if (typeof opts.setStatus === 'function') {
    opts.setStatus('正在理解你的意图...');
  }
  const routed = await routeGlobalIntent(text);
  if (!routed?.ok) {
    const msg = `路由失败: ${routed?.error || 'unknown'}`;
    if (typeof opts.setStatus === 'function') {
      opts.setStatus(msg, true);
    }
    return { ok: false, text: msg, error: 'router_failed' };
  }

  const routeResult = routed.result || {};
  const confidence = Number(routeResult?.intent?.confidence || 0);
  const moduleName = toText(routeResult?.intent?.module);
  const action = toText(routeResult?.intent?.action);
  const clarifyQuestions = buildClarifyQuestions(routeResult, text);
  const needsConfirmation = Boolean(routeResult?.safety?.needs_confirmation) || shouldForceConfirmation(routeResult);
  const confirmMessage = buildConfirmationMessage(routeResult);

  if (moduleName === 'unknown' || action === 'unknown' || confidence < 0.55) {
    const msg = clarifyQuestions.length
      ? `我还不能准确执行这条命令，请你补充：\n- ${clarifyQuestions.join('\n- ')}`
      : '我还不能准确执行这条命令，请换个更具体的说法。';
    if (typeof opts.setStatus === 'function') {
      opts.setStatus('意图不够明确，请补充。', true);
    }
    return { ok: false, text: msg, error: 'low_confidence' };
  }

  if (needsConfirmation) {
    const confirmed = window.confirm(confirmMessage);
    if (!confirmed) {
      return { ok: false, text: '已取消本次操作。', error: 'cancelled' };
    }
  }

  if (typeof opts.setStatus === 'function') {
    const label = getIntentActionLabel(routeResult?.intent);
    opts.setStatus(`已识别为：${label}，正在执行...`);
  }
  const executed = await executeRoutedAction(routeResult, text, { source: opts.source, setStatus: opts.setStatus });
  if (opts.outputId) {
    updateOutput(opts.outputId, executed.text || '');
  }
  return executed;
}

function hasDataForExport() {
  return Boolean(state.story_card || state.workshop || state.storyboard);
}

function renderProjectMeta() {
  const panel = bind('project-current-meta');
  if (!panel) {
    return;
  }
  if (!currentProjectMeta) {
    panel.innerHTML = '<p class="hint">当前项目信息将在这里显示。</p>';
    return;
  }
  panel.innerHTML = `
    <div><strong>${currentProjectMeta.name || '未命名项目'}</strong></div>
    <div>创建人：${currentProjectMeta.creator || '-'}</div>
    <div>描述：${currentProjectMeta.description || '-'}</div>
    <div>创建时间：${currentProjectMeta.created_at || '-'}</div>
  `;
}

function getCoverHtml(project) {
  if (project.cover_image) {
    return `<img class="project-cover" src="${project.cover_image}" alt="cover" />`;
  }
  return '<div class="project-cover placeholder">空白封面</div>';
}

function renderProjectList() {
  const list = bind('project-list');
  if (!list) {
    return;
  }
  if (!projectsCache.length) {
    list.innerHTML = '<p class="hint">暂无项目</p>';
    return;
  }
  list.innerHTML = projectsCache
    .map((p) => `
      <div class="project-card ${String(p.id) === String(currentProjectId) ? 'active' : ''}" data-project-id="${p.id}">
        <button class="project-card-edit-btn" title="编辑项目" data-project-id="${p.id}">✎</button>
        ${getCoverHtml(p)}
        <div>
          <div class="project-card-title">${p.name || '未命名项目'}</div>
          <div class="project-card-meta">创建人：${p.creator || '-'}</div>
          <div class="project-card-meta">${p.updated_at || ''}</div>
        </div>
      </div>
    `)
    .join('');

  const cards = list.querySelectorAll('.project-card');
  cards.forEach((card) => {
    card.addEventListener('click', async (e) => {
      if (e.target.classList.contains('project-card-edit-btn')) {
        e.stopPropagation();
        return;
      }
      const targetId = card.getAttribute('data-project-id');
      if (!targetId || String(targetId) === String(currentProjectId)) {
        return;
      }
      await switchProject(targetId);
    });
  });

  const editBtns = list.querySelectorAll('.project-card-edit-btn');
  editBtns.forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const projectId = btn.getAttribute('data-project-id');
      const project = projectsCache.find(p => String(p.id) === String(projectId));
      if (project) {
        openEditProjectModal(project);
      }
    });
  });
}

function setSnapshotStatus(text = '') {
  const target = bind('project-snapshot-status');
  if (target) {
    target.textContent = text;
  }
}

function formatDateTimeText(value) {
  const text = toText(value);
  if (!text) {
    return '-';
  }
  const date = new Date(text);
  if (Number.isNaN(date.getTime())) {
    return text;
  }
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function renderSnapshotList() {
  const list = bind('project-snapshot-list');
  if (!list) {
    return;
  }

  if (!snapshotCache.length) {
    list.innerHTML = '<p class="hint">暂无快照</p>';
    return;
  }

  list.innerHTML = snapshotCache
    .map((snapshot) => `
      <article class="snapshot-card">
        <h5>${snapshot.name || '未命名快照'}</h5>
        <div class="snapshot-meta">创建时间：${formatDateTimeText(snapshot.created_at)}</div>
        <div class="snapshot-meta">来源更新时间：${formatDateTimeText(snapshot.source_updated_at)}</div>
        <div class="snapshot-meta">${snapshot.description || '无描述'}</div>
        <div class="snapshot-actions">
          <button class="secondary" data-action="restore" data-snapshot-id="${snapshot.id}">回滚到此快照</button>
        </div>
      </article>
    `)
    .join('');

  list.querySelectorAll('[data-action="restore"]').forEach((button) => {
    button.addEventListener('click', async () => {
      const snapshotId = button.getAttribute('data-snapshot-id');
      if (!snapshotId) {
        return;
      }
      try {
        await restoreSnapshot(snapshotId);
      } catch (err) {
        console.error(err);
        setSnapshotStatus(`回滚失败: ${err.message}`);
      }
    });
  });
}

async function loadProjectSnapshots(projectId = currentProjectId) {
  const list = bind('project-snapshot-list');
  if (!list) {
    return [];
  }
  if (!projectId) {
    snapshotCache = [];
    renderSnapshotList();
    return snapshotCache;
  }

  const data = await fetchJson(`/api/projects/${projectId}/snapshots`, { method: 'GET' });
  if (!data.ok) {
    throw new Error(data.error || '加载项目快照失败');
  }

  snapshotCache = data.snapshots || [];
  renderSnapshotList();
  return snapshotCache;
}

async function duplicateCurrentProject() {
  if (!currentProjectId) {
    return;
  }

  await saveProjectStateNow();
  const currentName = currentProjectMeta?.name || '未命名项目';
  const name = window.prompt('请输入副本名称：', `${currentName} - 副本`);
  if (name === null) {
    return;
  }

  const data = await fetchJson(`/api/projects/${currentProjectId}/duplicate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: name.trim() }),
  });
  if (!data.ok) {
    throw new Error(data.error || '复制项目失败');
  }

  await loadProjects();
  if (data.project?.id) {
    await switchProject(String(data.project.id), { skipSaveCurrent: true });
  }
  setSnapshotStatus('项目副本已创建');
}

async function createSnapshotFromDialog() {
  if (!currentProjectId) {
    return;
  }

  await saveProjectStateNow();
  const defaultName = `手动快照 ${new Date().toLocaleString('zh-CN', { hour12: false }).replace(/[/:]/g, '-')}`;
  const name = window.prompt('请输入快照名称：', defaultName);
  if (name === null) {
    return;
  }
  const description = window.prompt('请输入快照说明（可选）：', '') || '';

  const data = await fetchJson(`/api/projects/${currentProjectId}/snapshots`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: name.trim(),
      description: description.trim(),
      state,
    }),
  });
  if (!data.ok) {
    throw new Error(data.error || '保存快照失败');
  }

  snapshotCache = data.snapshots || [];
  renderSnapshotList();
  setSnapshotStatus('快照已保存');
}

async function restoreSnapshot(snapshotId) {
  if (!currentProjectId || !snapshotId) {
    return;
  }

  await saveProjectStateNow();
  const ok = window.confirm('回滚会覆盖当前项目状态，但系统会自动保存一份保护快照。确定继续吗？');
  if (!ok) {
    return;
  }

  const data = await fetchJson(`/api/projects/${currentProjectId}/snapshots/${snapshotId}/restore`, {
    method: 'POST',
  });
  if (!data.ok) {
    throw new Error(data.error || '回滚快照失败');
  }

  snapshotCache = data.snapshots || [];
  renderSnapshotList();
  await switchProject(String(currentProjectId), { skipSaveCurrent: true });
  setSnapshotStatus(`已回滚到快照：${data.snapshot?.name || snapshotId}`);
}

async function loadProjects() {
  const data = await fetchJson('/api/projects', { method: 'GET' });
  if (!data.ok) {
    throw new Error(data.error || '加载项目失败');
  }
  projectsCache = data.projects || [];
  renderProjectList();
  return projectsCache;
}

function updateDrawerOpen(open) {
  projectDrawerOpen = Boolean(open);
  const drawer = bind('project-drawer');
  if (!drawer) {
    return;
  }
  drawer.classList.toggle('open', projectDrawerOpen);
  drawer.setAttribute('aria-hidden', projectDrawerOpen ? 'false' : 'true');
}

function openEditProjectModal(project) {
  const modal = bind('edit-project-modal');
  if (!modal) {
    return;
  }
  bind('edit-project-name').value = project.name || '';
  bind('edit-project-creator').value = project.creator || '';
  bind('edit-project-description').value = project.description || '';
  modal.dataset.projectId = String(project.id);
  modal.classList.add('show');
}

function closeEditProjectModal() {
  const modal = bind('edit-project-modal');
  if (modal) {
    modal.classList.remove('show');
  }
}

async function handleEditProjectSave() {
  const modal = bind('edit-project-modal');
  const projectId = modal.dataset.projectId;
  if (!projectId) {
    return;
  }

  const name = (bind('edit-project-name')?.value || '').trim();
  const creator = (bind('edit-project-creator')?.value || '').trim();
  const description = (bind('edit-project-description')?.value || '').trim();

  if (!name) {
    alert('项目名称不能为空');
    return;
  }

  try {
    const data = await fetchJson(`/api/projects/${projectId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name,
        creator,
        description,
      }),
    });

    if (!data.ok) {
      alert(`保存失败: ${data.error}`);
      return;
    }

    closeEditProjectModal();
    await loadProjects();
    if (String(projectId) === String(currentProjectId)) {
      currentProjectMeta = data.project || currentProjectMeta;
      renderProjectMeta();
    }
    setSnapshotStatus('项目信息已更新');
  } catch (err) {
    console.error('编辑项目失败', err);
    alert(`编辑失败: ${err.message}`);
  }
}

function bindEditProjectActions() {
  const modal = bind('edit-project-modal');
  const btnCancel = bind('btn-edit-cancel');
  const btnSave = bind('btn-edit-save');

  if (!modal || !btnCancel || !btnSave) {
    return;
  }

  btnCancel.addEventListener('click', () => {
    closeEditProjectModal();
  });

  btnSave.addEventListener('click', async () => {
    await handleEditProjectSave();
  });

  const form = bind('edit-project-form');
  if (form) {
    form.addEventListener('keypress', (e) => {
      if (e.key === 'Enter' && e.ctrlKey) {
        handleEditProjectSave();
      }
    });
  }

  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      closeEditProjectModal();
    }
  });
}

function initProjectDrawerDrag() {
  const btn = bind('btn-project-drawer');
  if (!btn) {
    return;
  }

  let isDragging = false;
  let offsetX = 0;
  let offsetY = 0;

  btn.addEventListener('mousedown', (e) => {
    isDragging = true;
    const rect = btn.getBoundingClientRect();
    offsetX = e.clientX - rect.left;
    offsetY = e.clientY - rect.top;
    btn.style.transition = 'none';
  });

  document.addEventListener('mousemove', (e) => {
    if (!isDragging) {
      return;
    }
    const newLeft = e.clientX - offsetX;
    const newTop = e.clientY - offsetY;
    btn.style.left = Math.max(0, Math.min(newLeft, window.innerWidth - 60)) + 'px';
    btn.style.top = Math.max(0, Math.min(newTop, window.innerHeight - 60)) + 'px';
  });

  document.addEventListener('mouseup', () => {
    if (isDragging) {
      isDragging = false;
      btn.style.transition = 'box-shadow 0.2s ease, transform 0.2s ease';
    }
  });
}

async function ensureProjectExistsAndLoad() {
  let projects = await loadProjects();
  if (!projects.length) {
    const created = await fetchJson('/api/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: '未命名项目',
        creator: '',
        description: '',
      }),
    });
    if (!created.ok) {
      throw new Error(created.error || '创建默认项目失败');
    }
    projects = await loadProjects();
  }

  const legacy = localStorage.getItem(STORAGE_KEY);
  if (legacy && projects.length === 1 && projects[0].name === '未命名项目') {
    try {
      const legacyState = JSON.parse(legacy);
      const migrated = await fetchJson('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: '迁移项目',
          creator: '本地迁移',
          description: '从旧 localStorage 自动迁移',
          state: legacyState,
          last_provider: currentProvider,
        }),
      });
      if (migrated.ok && migrated.project?.id) {
        currentProjectId = String(migrated.project.id);
        saveCurrentProjectId(currentProjectId);
      }
      localStorage.removeItem(STORAGE_KEY);
      projects = await loadProjects();
    } catch (err) {
      console.error('legacy migration failed', err);
    }
  }

  if (!currentProjectId || !projects.some((p) => String(p.id) === String(currentProjectId))) {
    currentProjectId = String(projects[0].id);
    saveCurrentProjectId(currentProjectId);
  }

  await switchProject(currentProjectId, { skipSaveCurrent: true });
}

async function switchProject(projectId, opts = {}) {
  const options = { skipSaveCurrent: false, ...opts };
  if (!options.skipSaveCurrent) {
    await saveProjectStateNow();
  }

  const data = await fetchJson(`/api/projects/${projectId}`, { method: 'GET' });
  if (!data.ok) {
    throw new Error(data.error || '加载项目失败');
  }

  currentProjectId = String(projectId);
  saveCurrentProjectId(currentProjectId);
  currentProjectMeta = data.project || null;
  applyState(data.state || EMPTY_STATE);
  syncStoryInputsToForm();

  if (currentProjectMeta?.last_provider) {
    currentProvider = currentProjectMeta.last_provider;
    saveProvider(currentProvider);
  }

  clearOutputsByPage();
  restoreOutputsOnPageLoad();
  refreshVisualEditors();
  renderReviewLab();
  renderProjectMeta();
  await loadProjects();
  try {
    await loadProjectSnapshots(currentProjectId);
    setSnapshotStatus('');
  } catch (err) {
    console.error('loadProjectSnapshots failed', err);
    setSnapshotStatus(`快照加载失败: ${err.message}`);
  }
}

async function createProjectFromDialog() {
  const name = window.prompt('请输入项目名称：', '新项目');
  if (!name || !name.trim()) {
    return;
  }
  const creator = window.prompt('请输入创建人：', '') || '';
  const description = window.prompt('请输入项目描述：', '') || '';

  const data = await fetchJson('/api/projects', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: name.trim(),
      creator: creator.trim(),
      description: description.trim(),
      state: EMPTY_STATE,
      last_provider: currentProvider,
    }),
  });
  if (!data.ok) {
    throw new Error(data.error || '新建项目失败');
  }
  await loadProjects();
  if (data.project?.id) {
    await switchProject(String(data.project.id));
  }
}

async function deleteCurrentProject() {
  if (!currentProjectId) {
    return;
  }
  const ok = window.confirm('确认删除当前项目？此操作不可撤销。');
  if (!ok) {
    return;
  }

  const data = await fetchJson(`/api/projects/${currentProjectId}`, { method: 'DELETE' });
  if (!data.ok) {
    throw new Error(data.error || '删除项目失败');
  }

  projectsCache = data.projects || [];
  renderProjectList();

  const fallback = data.fallback_project;
  if (fallback?.id) {
    await switchProject(String(fallback.id), { skipSaveCurrent: true });
  }
}

function bindProjectDrawerActions() {
  const btnToggle = bind('btn-project-drawer');
  const btnClose = bind('btn-project-drawer-close');
  const btnNew = bind('btn-new-project');
  const btnDelete = bind('btn-delete-project');
  const btnDuplicate = bind('btn-duplicate-project');
  const btnSaveSnapshot = bind('btn-save-snapshot');
  const btnRefreshSnapshots = bind('btn-refresh-snapshots');

  if (btnToggle) {
    btnToggle.addEventListener('click', () => {
      updateDrawerOpen(!projectDrawerOpen);
    });
  }
  if (btnClose) {
    btnClose.addEventListener('click', () => {
      updateDrawerOpen(false);
    });
  }
  if (btnNew) {
    btnNew.addEventListener('click', async () => {
      try {
        await createProjectFromDialog();
      } catch (err) {
        console.error(err);
        alert(`新建项目失败: ${err.message}`);
      }
    });
  }
  if (btnDelete) {
    btnDelete.addEventListener('click', async () => {
      try {
        await deleteCurrentProject();
      } catch (err) {
        console.error(err);
        alert(`删除项目失败: ${err.message}`);
      }
    });
  }
  if (btnDuplicate) {
    btnDuplicate.addEventListener('click', async () => {
      try {
        await duplicateCurrentProject();
      } catch (err) {
        console.error(err);
        setSnapshotStatus(`复制项目失败: ${err.message}`);
      }
    });
  }
  if (btnSaveSnapshot) {
    btnSaveSnapshot.addEventListener('click', async () => {
      try {
        await createSnapshotFromDialog();
      } catch (err) {
        console.error(err);
        setSnapshotStatus(`保存快照失败: ${err.message}`);
      }
    });
  }
  if (btnRefreshSnapshots) {
    btnRefreshSnapshots.addEventListener('click', async () => {
      try {
        await loadProjectSnapshots();
        setSnapshotStatus('快照列表已刷新');
      } catch (err) {
        console.error(err);
        setSnapshotStatus(`刷新快照失败: ${err.message}`);
      }
    });
  }

  const drawer = bind('project-drawer');
  if (drawer && btnToggle) {
    document.addEventListener('click', (e) => {
      if (!projectDrawerOpen) {
        return;
      }
      const isClickInsideDrawer = drawer.contains(e.target);
      const isClickOnToggleBtn = btnToggle.contains(e.target);
      if (!isClickInsideDrawer && !isClickOnToggleBtn) {
        updateDrawerOpen(false);
      }
    });
  }
}

async function loadStoryTemplates() {
  const select = bind('story-template-select');
  const summary = bind('story-template-summary');
  if (!select) {
    return;
  }

  try {
    const data = await fetchJson('/api/story-templates', { method: 'GET' });
    if (!data.ok) {
      throw new Error(data.error || 'load templates failed');
    }

    storyTemplates = Array.isArray(data.templates) ? data.templates : [];
    select.innerHTML = [
      '<option value="">不使用模板（自由发挥）</option>',
      ...storyTemplates.map((item) => `<option value="${item.id}">${item.name} / ${item.category}</option>`),
    ].join('');
    syncStoryInputsToForm();
  } catch (err) {
    console.error('Failed to load story templates:', err);
    storyTemplates = [];
    if (summary) {
      summary.textContent = `模板加载失败：${err.message}`;
    }
  }
}

async function loadProviders() {
  try {
    const data = await fetchJson('/api/providers', { method: 'GET' });
    if (data.ok) {
      providersList = data.providers;
      renderProviderSelector();
    }
  } catch (err) {
    console.error('Failed to load providers:', err);
  }
}

function renderProviderSelector() {
  const selector = bind('provider-selector');
  if (!selector) {
    return;
  }

  if (!providersList.length) {
    selector.innerHTML = '';
    return;
  }

  if (!providersList.some((p) => p.id === currentProvider && p.has_api_key)) {
    const firstAvailable = providersList.find((p) => p.has_api_key) || providersList[0];
    currentProvider = firstAvailable.id;
    saveProvider(currentProvider);
  }

  selector.innerHTML = providersList.map(p => `
    <option value="${p.id}" ${p.id === currentProvider ? 'selected' : ''} ${!p.has_api_key ? 'disabled' : ''}>
      ${p.name} ${!p.has_api_key ? '(未配置API Key)' : ''} ${p.is_default ? '(默认)' : ''}
    </option>
  `).join('');

  selector.addEventListener('change', (e) => {
    const newProvider = e.target.value;
    const provider = providersList.find(p => p.id === newProvider);
    if (provider && provider.has_api_key) {
      currentProvider = newProvider;
      saveProvider(currentProvider);
      if (currentProjectMeta) {
        currentProjectMeta.last_provider = currentProvider;
      }
      if (currentProjectId) {
        fetchJson(`/api/projects/${currentProjectId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ last_provider: currentProvider }),
        }).catch((err) => {
          console.error('update last_provider failed', err);
        });
      }
      updateProviderDisplay();
    } else if (provider && !provider.has_api_key) {
      alert(`请先在 .env 文件中配置 ${provider.name} 的凭证（如 AK/SK）`);
      selector.value = currentProvider;
    }
  });

  updateProviderDisplay();
}

function updateProviderDisplay() {
  const display = bind('provider-display');
  if (display) {
    const provider = providersList.find(p => p.id === currentProvider);
    if (provider) {
      display.textContent = `当前模型: ${provider.name} (${provider.model})`;
    }
  }
}

function getVideoState() {
  state.video_lab = normalizeVideoState(state.video_lab);
  return state.video_lab;
}

function stopVideoPolling(notify = true) {
  if (videoPollTimer) {
    clearInterval(videoPollTimer);
    videoPollTimer = null;
    if (notify) {
      const video = getVideoState();
      const text = `Task ID: ${video.task_id || '-'}\n状态: ${video.task_status || 'UNKNOWN'}\n自动轮询已停止。`;
      updateOutput('video-task-output', text);
    }
  }
}

async function ensureVideoBgmMixed(videoUrl, { silent = false } = {}) {
  const video = getVideoState();
  const sourceVideoUrl = String(videoUrl || '').trim();
  const audioUrl = String(video.audio_url || bind('video-audio-url')?.value?.trim() || '').trim();

  if (!sourceVideoUrl || !audioUrl) {
    return sourceVideoUrl;
  }
  if (video.audio_mix_url && video.audio_mix_source_url === sourceVideoUrl) {
    return video.audio_mix_url;
  }

  if (!silent) {
    updateOutput('video-task-output', `视频已生成，正在混入上传的 BGM...`);
  }

  const data = await fetchJson('/api/video/mix-bgm', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      payload: {
        video_url: sourceVideoUrl,
        audio_url: audioUrl,
        volume: 0.35,
      },
    }),
  });

  if (!data.ok) {
    const message = `BGM 混入失败：${data.error || 'unknown'}${data.detail ? `\n${data.detail}` : ''}`;
    if (!silent) {
      updateOutput('video-task-output', message);
    }
    console.warn(message);
    return sourceVideoUrl;
  }

  const mixedUrl = String(data.result?.video_url || '').trim();
  if (!mixedUrl) {
    return sourceVideoUrl;
  }

  video.audio_mix_url = mixedUrl;
  video.audio_mix_source_url = sourceVideoUrl;
  saveState();
  return mixedUrl;
}

async function queryVideoTaskOnce({ silent = false } = {}) {
  const video = getVideoState();
  if (!video.task_id) {
    if (!silent) {
      updateOutput('video-task-output', '请先创建视频任务。');
    }
    return;
  }

  if (!silent) {
    updateOutput('video-task-output', `正在查询任务 ${video.task_id} ...`);
  }

  const data = await fetchJson(`/api/video/task/${video.task_id}`, { method: 'GET' });
  if (!data.ok) {
    updateOutput('video-task-output', `错误: ${data.error}\n${data.detail || ''}`);
    stopVideoPolling(false);
    return;
  }

  const output = data.result?.output || data.result || {};
  video.task_status = output.task_status || output.status || 'UNKNOWN';
  video.video_url = output.video_url || output.url || output?.result?.video?.url || '';
  video.last_check_time = new Date().toLocaleString();
  saveState();

  let text = `Task ID: ${video.task_id}\n状态: ${video.task_status}`;
  text += `\n最近查询: ${video.last_check_time}`;

  if (video.video_url) {
    text += '\n视频URL已生成。';
    const renderUrl = await ensureVideoBgmMixed(video.video_url, { silent });
    if (renderUrl !== video.video_url) {
      text += '\n已混入上传的 BGM。';
    } else if (video.audio_url && !video.audio_mix_url) {
      text += '\nBGM 暂未混入成功，先展示原视频。';
    }
    renderVideoResult(renderUrl);
  }

  if (video.task_status === 'SUCCEEDED' || video.task_status === 'FAILED' || video.task_status === 'CANCELED') {
    stopVideoPolling(false);
    text += '\n任务已结束，自动轮询已停止。';
  } else if (videoPollTimer) {
    text += '\n自动轮询中（15秒/次）。';
  }

  updateOutput('video-task-output', text);
}

function startVideoPolling() {
  const video = getVideoState();
  if (!video.task_id) {
    return;
  }

  stopVideoPolling(false);
  videoPollTimer = setInterval(() => {
    queryVideoTaskOnce({ silent: true }).catch((err) => {
      updateOutput('video-task-output', `错误: ${err.message}`);
      stopVideoPolling(false);
    });
  }, VIDEO_POLL_INTERVAL_MS);
}

async function runStage(stage, payload, provider = null) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 90000);
  try {
    const resp = await fetch('/api/agent/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ stage, payload, provider: provider || currentProvider }),
      signal: controller.signal,
    });

    const raw = await resp.text();
    let data = null;
    try {
      data = raw ? JSON.parse(raw) : {};
    } catch (err) {
      throw new Error(`接口返回非 JSON（HTTP ${resp.status}）`);
    }

    if (!resp.ok) {
      return {
        ok: false,
        error: data?.error || `请求失败（HTTP ${resp.status}）`,
        detail: data?.detail || '',
      };
    }
    recordCostMeta(data?.meta);
    return data;
  } catch (err) {
    if (err?.name === 'AbortError') {
      return { ok: false, error: '请求超时（90秒），请稍后重试', detail: '' };
    }
    return { ok: false, error: err?.message || String(err), detail: '' };
  } finally {
    clearTimeout(timeoutId);
  }
}

async function downloadFile(url, filename, payload) {
  const resp = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ payload }),
  });

  if (!resp.ok) {
    let errMsg = '导出失败';
    try {
      const errJson = await resp.json();
      errMsg = errJson.error || errMsg;
    } catch (e) {
      // Ignore parse error and keep generic message.
    }
    throw new Error(errMsg);
  }

  const blob = await resp.blob();
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = objectUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(objectUrl);
}

function setRelationStatus(text) {
  const tip = bind('rel-status');
  if (tip) {
    tip.textContent = text;
  }
}

function setRelationSelection(from, to, type = '', tension = '') {
  const fromInput = bind('rel-from-display');
  const toInput = bind('rel-to-display');
  const typeInput = bind('rel-type');
  const tensionInput = bind('rel-tension');
  if (!fromInput || !toInput || !typeInput || !tensionInput) {
    return;
  }

  fromInput.value = from || '';
  toInput.value = to || '';
  typeInput.value = type || '';
  tensionInput.value = tension || '';
}

function renderRelationshipGraph() {
  const container = bind('relationship-graph');
  if (!container) {
    return;
  }

  if (typeof vis === 'undefined') {
    container.innerHTML = '<div class="hint" style="padding:12px;">未加载图谱依赖，请刷新页面。</div>';
    return;
  }

  const characters = state.workshop?.characters || [];
  const relationships = state.workshop?.relationships || [];

  if (!characters.length) {
    container.innerHTML = '<div class="hint" style="padding:12px;">请先在创作工坊生成角色与情节。</div>';
    relationshipNetwork = null;
    selectedRelationIndex = null;
    draftRelationNodes = [];
    setRelationSelection('', '', '', '');
    setRelationStatus('请先生成角色数据。');
    return;
  }

  const nodes = characters.map((c, idx) => ({
    id: c.name || `角色${idx + 1}`,
    label: c.name || `角色${idx + 1}`,
    title: (c.tags || []).join(' / ') || '无标签',
    shape: 'dot',
    size: 20,
  }));

  const edges = relationships
    .map((r, idx) => ({ rel: r, idx }))
    .filter((item) => item.rel.from && item.rel.to)
    .map((item) => ({
      id: `rel-${item.idx}`,
      from: item.rel.from,
      to: item.rel.to,
      label: item.rel.type || '关系',
      title: item.rel.tension || '',
      arrows: 'to',
      smooth: true,
      width: selectedRelationIndex === item.idx ? 3 : 1,
      color: selectedRelationIndex === item.idx ? '#b84f10' : '#8f735e',
    }));

  const data = {
    nodes: new vis.DataSet(nodes),
    edges: new vis.DataSet(edges),
  };

  const options = {
    autoResize: true,
    interaction: { hover: true },
    nodes: {
      color: {
        background: '#eec9a9',
        border: '#b86a36',
        highlight: { background: '#ffd7b8', border: '#a94f14' },
      },
      font: { color: '#2b2119', size: 13 },
    },
    edges: {
      color: '#8f735e',
      font: { align: 'top', color: '#3b2f27', size: 12 },
    },
    physics: {
      solver: 'forceAtlas2Based',
      stabilization: { iterations: 80 },
    },
  };

  if (!relationshipNetwork) {
    relationshipNetwork = new vis.Network(container, data, options);
    relationshipNetwork.on('click', (params) => {
      if (!state.workshop) {
        return;
      }

      if (params.nodes.length > 0) {
        const nodeName = String(params.nodes[0]);
        selectedRelationIndex = null;

        if (draftRelationNodes.length === 0 || draftRelationNodes.length === 2) {
          draftRelationNodes = [nodeName];
        } else {
          // If we already have 1 selected node, append the new one as the second (if it's different)
          if (draftRelationNodes[0] !== nodeName) {
            draftRelationNodes.push(nodeName);
          }
        }

        if (draftRelationNodes.length === 1) {
          setRelationSelection(draftRelationNodes[0], '', '', '');
          setRelationStatus(`已选择起点：${draftRelationNodes[0]}。请再选终点。`);
        } else {
          setRelationSelection(draftRelationNodes[0], draftRelationNodes[1], '关系', '');
          setRelationStatus(`已选择关系端点：${draftRelationNodes[0]} -> ${draftRelationNodes[1]}`);
        }
        return;
      }

      if (params.edges.length > 0) {
        const edgeId = String(params.edges[0]);
        const idx = Number(edgeId.replace('rel-', ''));
        const rel = state.workshop.relationships?.[idx];
        if (Number.isInteger(idx) && rel) {
          selectedRelationIndex = idx;
          draftRelationNodes = [];
          setRelationSelection(rel.from, rel.to, rel.type || '', rel.tension || '');
          setRelationStatus(`已选中关系：${rel.from} -> ${rel.to}`);
          renderRelationshipGraph();
        }
        return;
      }

      selectedRelationIndex = null;
      draftRelationNodes = [];
      setRelationStatus('点击连线编辑；或依次点击两个角色节点创建关系。');
    });
  } else {
    relationshipNetwork.setData(data);
  }
}

function getOrderedPlotNodes() {
  const plotNodes = state.workshop?.plot_nodes || [];
  const idMap = new Map(plotNodes.map((node) => [node.id, node]));
  const view = state.workshop?.timeline_view || [];

  const ordered = [];
  view.forEach((id) => {
    if (idMap.has(id)) {
      ordered.push(idMap.get(id));
      idMap.delete(id);
    }
  });
  idMap.forEach((node) => ordered.push(node));
  return ordered;
}

function pushVisualUndo() {
  if (state && state.workshop) {
    visualUndoStack.push(JSON.parse(JSON.stringify(state.workshop)));
    if (visualUndoStack.length > 20) {
      visualUndoStack.shift();
    }
  }
}

function syncTimelineToState() {
  if (!state.workshop) {
    return;
  }

  pushVisualUndo();

  const list = bind('timeline-list');
  if (!list) {
    return;
  }

  const ids = Array.from(list.querySelectorAll('.timeline-card')).map((li) => li.dataset.nodeId);
  state.workshop.timeline_view = ids;

  const current = new Map((state.workshop.plot_nodes || []).map((node) => [node.id, node]));
  state.workshop.plot_nodes = ids.map((id) => current.get(id)).filter(Boolean);
  saveState();
}

function renderTimeline() {
  const list = bind('timeline-list');
  if (!list) {
    return;
  }

  const ordered = getOrderedPlotNodes();
  if (!ordered.length) {
    list.innerHTML = '<li class="hint">请先在创作工坊生成情节节点。</li>';
    return;
  }

  list.innerHTML = ordered
    .map(
      (node, idx) => `
      <li class="timeline-card" data-node-id="${node.id || `N${idx + 1}`}">
        <div class="meta">${idx + 1}. ${node.id || ''}</div>
        <div class="title">${node.template_stage || '剧情节点'}</div>
        <div class="summary">${node.summary || ''}</div>
      </li>
    `,
    )
    .join('');

  if (!timelineSortable && typeof Sortable !== 'undefined') {
    timelineSortable = new Sortable(list, {
      animation: 180,
      ghostClass: 'timeline-dragging',
      onEnd: () => {
        syncTimelineToState();
      },
    });
  }
}

function refreshVisualEditors() {
  renderRelationshipGraph();
  renderTimeline();
}

function formatStoryResult(result) {
  const sc = result.story_card || result || {};
  const nextQs = result.next_questions || [];

  let text = `【一句话故事】\n${sc.logline || '-'}\n\n`;
  text += `【核心冲突】\n${sc.core_conflict || '-'}\n\n`;
  text += `【前三秒钩子】\n${sc.hook || '-'}\n\n`;
  text += `【属性】\n主题：${sc.theme || '-'}\n基调：${sc.tone || '-'}\n结构：${sc.structure_template || '-'}\n结局：${sc.ending_type || '-'}\n\n`;

  text += `【结构锚点】\n`;
  text += `銆愮垎娆炬ā鏉裤€慭n${sc.viral_template_name || '未使用'}\n\n`;
  text += `銆愬紑鍦洪挬瀛愮瓥鐣ャ€慭n${sc.opening_hook_strategy || '-'}\n\n`;
  text += `銆愬啿绐佸崌绾ц妭濂忋€慭n${sc.conflict_escalation_strategy || '-'}\n\n`;
  text += `銆愮粨灏剧暀鎮康銆慭n${sc.cliffhanger_strategy || '-'}\n\n`;
  if (sc.anchor_points && sc.anchor_points.length) {
    sc.anchor_points.forEach((pt, i) => {
      text += `${i + 1}. ${pt}\n`;
    });
  } else {
    text += '-\n';
  }

  text += `\n【建议追问】\n`;
  if (nextQs.length) {
    nextQs.forEach((q) => {
      text += `- ${q}\n`;
    });
  } else {
    text += '-\n';
  }
  return text;
}

function formatStoryResultV2(result) {
  const sc = result.story_card || result || {};
  const nextQs = result.next_questions || [];

  let text = `【一句话故事】\n${sc.logline || '-'}\n\n`;
  text += `【核心冲突】\n${sc.core_conflict || '-'}\n\n`;
  text += `【前三秒钩子】\n${sc.hook || '-'}\n\n`;
  text += `【爆款模板】\n${sc.viral_template_name || '未使用'}\n\n`;
  text += `【开场钩子策略】\n${sc.opening_hook_strategy || '-'}\n\n`;
  text += `【冲突升级节奏】\n${sc.conflict_escalation_strategy || '-'}\n\n`;
  text += `【结尾留悬念】\n${sc.cliffhanger_strategy || '-'}\n\n`;
  text += `【属性】\n主题：${sc.theme || '-'}\n基调：${sc.tone || '-'}\n结构：${sc.structure_template || '-'}\n结局：${sc.ending_type || '-'}\n\n`;
  text += `【结构锚点】\n`;

  if (sc.anchor_points && sc.anchor_points.length) {
    sc.anchor_points.forEach((pt, i) => {
      text += `${i + 1}. ${pt}\n`;
    });
  } else {
    text += '-\n';
  }

  text += `\n【建议追问】\n`;
  if (nextQs.length) {
    nextQs.forEach((q) => {
      text += `- ${q}\n`;
    });
  } else {
    text += '-\n';
  }

  return text;
}

function buildReviewProjectState() {
  return {
    story_inputs: state.story_inputs,
    story_card: state.story_card,
    workshop: state.workshop,
    storyboard: state.storyboard,
  };
}

function inferReviewStage() {
  if (state.storyboard) {
    return 'storyboard';
  }
  if (state.workshop) {
    return 'workshop';
  }
  if (state.story_card) {
    return 'story_engine';
  }
  return '';
}

function stageSupportsRewrite(stage) {
  return ['story_engine', 'workshop', 'storyboard'].includes(stage);
}

function reviewCandidatePreview(item) {
  if (item.target === 'workshop') {
    return formatWorkshopResult(item.workshop);
  }
  if (item.target === 'storyboard') {
    return formatStoryboardResult(item.storyboard);
  }
  return formatStoryResultV2({ story_card: item.story_card });
}

function reviewTargetLabel(target) {
  if (target === 'workshop') {
    return '剧本工坊';
  }
  if (target === 'storyboard') {
    return '分镜工厂';
  }
  return '故事引擎';
}

async function runStoryReviewFlow(currentStage, { withRewrite = false } = {}) {
  const stage = currentStage || inferReviewStage();
  if (!stage || !state.story_card) {
    state.review_lab = normalizeReviewLab(null);
    renderReviewLab();
    return;
  }

  const reviewData = await runStage('story_review', {
    current_stage: stage,
    project_state: buildReviewProjectState(),
  });

  if (!reviewData.ok) {
    state.review_lab.latest_review = normalizeReviewLab(null).latest_review;
    state.review_lab.rewrite_candidates = [];
    state.review_lab.last_review_stage = stage;
    state.review_lab.last_review_time = new Date().toISOString();
    renderReviewLab(`评分失败：${reviewData.error}`);
    return;
  }

  state.review_lab.latest_review = normalizeReviewLab({ latest_review: reviewData.result }).latest_review;
  state.review_lab.last_review_stage = stage;
  state.review_lab.last_review_time = new Date().toISOString();

  if (withRewrite && state.review_lab.latest_review.low_score_dimensions.length) {
    const rewriteData = await runStage('story_rewrite', {
      current_stage: stage,
      project_state: buildReviewProjectState(),
      review_result: state.review_lab.latest_review,
    });
    if (rewriteData.ok) {
      state.review_lab.rewrite_candidates = normalizeReviewLab({
        rewrite_candidates: rewriteData.result.candidates,
      }).rewrite_candidates;
    } else {
      state.review_lab.rewrite_candidates = [];
    }
  } else {
    state.review_lab.rewrite_candidates = [];
  }

  saveState();
  renderReviewLab();
}

async function applyReviewCandidate(candidateId) {
  const candidates = state.review_lab?.rewrite_candidates || [];
  const selected = candidates.find((item) => String(item.id) === String(candidateId));
  if (!selected) {
    return;
  }

  let rerunStage = 'story_engine';
  if (selected.target === 'workshop' && selected.workshop) {
    state.workshop = normalizeWorkshopData(selected.workshop);
    state.storyboard = null;
    rerunStage = 'workshop';
  } else if (selected.target === 'storyboard' && selected.storyboard) {
    state.storyboard = normalizeStoryboardData(selected.storyboard);
    rerunStage = 'storyboard';
  } else if (selected.story_card) {
    state.story_card = normalizeStoryCard(selected.story_card);
    state.workshop = null;
    state.storyboard = null;
    rerunStage = 'story_engine';
  } else {
    return;
  }

  state.review_lab.rewrite_candidates = [];
  saveState();

  updateOutput('story-output', formatStoryResultV2({ story_card: state.story_card }));
  updateOutput('workshop-output', state.workshop ? formatWorkshopResult(state.workshop) : '');
  updateOutput('storyboard-output', state.storyboard ? formatStoryboardResult(state.storyboard) : '');
  refreshVisualEditors();
  renderReviewLab('已应用改写版本，正在重新评分...');
  await runStoryReviewFlow(rerunStage, { withRewrite: true });
}

function renderReviewLab(statusText = '') {
  const panel = bind('review-panel');
  if (!panel) {
    return;
  }

  const reviewLab = normalizeReviewLab(state.review_lab);
  const review = reviewLab.latest_review;
  const candidates = reviewLab.rewrite_candidates || [];
  const hasContent =
    review.summary ||
    review.dimensions.length ||
    review.top_issues.length ||
    review.priority_actions.length ||
    candidates.length ||
    statusText;

  if (!hasContent) {
    panel.style.display = 'none';
    panel.innerHTML = '';
    return;
  }

  const dimsHtml = review.dimensions.length
    ? review.dimensions
      .map(
        (item) => `
            <div class="panel soft" style="padding:10px;">
              <div style="display:flex; justify-content:space-between; gap:12px;">
                <strong>${item.name}</strong>
                <span>${item.score}</span>
              </div>
              <div class="hint" style="margin-top:6px;">问题：${item.reason || '-'}</div>
              <div class="hint" style="margin-top:4px;">建议：${item.suggestion || '-'}</div>
            </div>
          `,
      )
      .join('')
    : '<p class="hint">暂无评分结果</p>';

  const issuesHtml = review.top_issues.length
    ? review.top_issues.map((item) => `<li>${item}</li>`).join('')
    : '<li>-</li>';

  const actionsHtml = review.priority_actions.length
    ? review.priority_actions.map((item) => `<li>${item}</li>`).join('')
    : '<li>-</li>';

  const candidateHtml = candidates.length
    ? candidates
      .map(
        (item) => `
            <article class="panel" style="padding:12px; margin-top:10px;">
              <h4 style="margin-bottom:6px;">${item.title}</h4>
              <div class="hint">应用范围：${reviewTargetLabel(item.target)}</div>
              <div class="hint">策略：${item.strategy || '-'}</div>
              <div class="hint" style="margin-top:4px;">聚焦维度：${(item.focus_dimensions || []).join('、') || '-'}</div>
              <pre class="output" style="margin-top:10px; max-height:220px;">${reviewCandidatePreview(item)}</pre>
              <button class="secondary" data-review-candidate-id="${item.id}">使用这个版本</button>
            </article>
          `,
      )
      .join('')
    : '<p class="hint">当前没有自动改稿候选版本。</p>';

  panel.style.display = 'block';
  panel.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap;">
      <h3 style="margin:0;">剧本评分器</h3>
      <button id="btn-review-rerun" class="secondary">重新评分</button>
    </div>
    ${statusText ? `<p class="hint" style="margin-top:8px;">${statusText}</p>` : ''}
    <div style="margin-top:10px;"><strong>总分：</strong>${review.overall_score || 0}</div>
    <div class="hint" style="margin-top:6px;">${review.summary || '暂无整体评语'}</div>
    <div class="grid two" style="margin-top:12px;">${dimsHtml}</div>
    <div class="grid two" style="margin-top:12px;">
      <div>
        <h4 style="margin-bottom:6px;">主要问题</h4>
        <ul>${issuesHtml}</ul>
      </div>
      <div>
        <h4 style="margin-bottom:6px;">优先修改动作</h4>
        <ul>${actionsHtml}</ul>
      </div>
    </div>
    <div style="margin-top:12px;" class="hint">最近评分阶段：${reviewLab.last_review_stage || '-'} | 时间：${reviewLab.last_review_time || '-'}</div>
    <div style="margin-top:12px;">
      <h4 style="margin-bottom:6px;">自动改稿候选</h4>
      ${candidateHtml}
    </div>
  `;

  const rerunBtn = bind('btn-review-rerun');
  if (rerunBtn) {
    rerunBtn.addEventListener('click', () => {
      renderReviewLab('正在重新评分...');
      runStoryReviewFlow(reviewLab.last_review_stage || inferReviewStage(), {
        withRewrite: stageSupportsRewrite(reviewLab.last_review_stage || inferReviewStage()),
      }).catch((err) => {
        renderReviewLab(`重新评分失败：${err.message}`);
      });
    });
  }

  panel.querySelectorAll('[data-review-candidate-id]').forEach((button) => {
    button.addEventListener('click', () => {
      const candidateId = button.getAttribute('data-review-candidate-id');
      if (!candidateId) {
        return;
      }
      applyReviewCandidate(candidateId).catch((err) => {
        renderReviewLab(`应用改写失败：${err.message}`);
      });
    });
  });
}

function formatWorkshopResult(ws) {
  const workshop = normalizeWorkshopData(ws);
  if (!workshop) return '-';

  const lines = ['\u3010\u89d2\u8272\u8bbe\u5b9a\u3011'];
  if (workshop.characters.length) {
    workshop.characters.forEach((character) => {
      lines.push(`- ${character.name} (${(character.tags || []).join(', ')})`);
      lines.push(`  \u52a8\u673a: ${character.motivation || '-'}`);
      lines.push(`  \u5f27\u5149: ${character.arc || '-'}`);
    });
  } else {
    lines.push('-');
  }

  lines.push('');
  lines.push('\u3010\u89d2\u8272\u5173\u7cfb\u3011');
  if (workshop.relationships.length) {
    workshop.relationships.forEach((relationship) => {
      lines.push(`- ${relationship.from} -> ${relationship.to}: ${relationship.type || '-'} (${relationship.tension || ''})`);
    });
  } else {
    lines.push('-');
  }

  lines.push('');
  lines.push('\u3010\u5267\u60c5\u8282\u70b9\u3011');
  if (workshop.plot_nodes.length) {
    workshop.plot_nodes.forEach((node) => {
      const dialogueText = Array.isArray(node.dialogue_draft) ? node.dialogue_draft.join(' / ') : '-';
      lines.push(`[${node.id || '-'}] ${node.template_stage || '-'}`);
      lines.push(`  \u6458\u8981: ${node.summary || '-'}`);
      lines.push(`  \u5730\u70b9: ${node.location || '-'}`);
      lines.push(`  \u52a8\u4f5c: ${node.action_draft || '-'}`);
      lines.push(`  \u5bf9\u767d: ${dialogueText || '-'}`);
      lines.push(`  \u60c5\u611f: ${node.emotion_shift || '-'}`);
      lines.push(`  \u4e00\u81f4\u6027: ${node.consistency_check || '-'}`);
      lines.push('');
    });
  } else {
    lines.push('-');
  }

  return lines.join('\n').replace(/\\r\\n/g, '\n').replace(/\\n/g, '\n').replace(/\\t/g, '\t').trim();
}

function formatStoryboardResult(sb) {
  const storyboard = normalizeStoryboardData(sb);
  if (!storyboard) return '-';

  const lines = ['\u3010\u5206\u955c\u5217\u8868\u3011'];
  if (storyboard.storyboards.length) {
    storyboard.storyboards.forEach((shot) => {
      lines.push(`[${shot.shot_id || '-'}] (\u5173\u8054: ${shot.related_node_id || '-'}) | ${shot.shot_type || '-'} | ${shot.camera_movement || '-'} | ${shot.duration_sec || 0}\u79d2`);
      lines.push(`  \u753b\u9762: ${shot.visual_description || '-'}`);
      lines.push(`  \u58f0\u97f3: ${shot.dialogue_or_sfx || '-'}`);
      lines.push(`  \u63d0\u793a\u8bcd: ${shot.prompt_draft || '-'}`);
      lines.push('');
    });
  } else {
    lines.push('-');
  }

  if (storyboard.estimated_total_duration_sec) {
    lines.push(`\u9884\u4f30\u603b\u65f6\u957f: ${storyboard.estimated_total_duration_sec} \u79d2`);
  }

  return lines.join('\n').replace(/\\r\\n/g, '\n').replace(/\\n/g, '\n').replace(/\\t/g, '\t').trim();
}

function bindWorkshopActions() {
  ['idea', 'theme', 'tone', 'structure', 'story-template-select'].forEach((id) => {
    const element = bind(id);
    if (!element) {
      return;
    }
    element.addEventListener('input', saveStoryInputsFromForm);
    element.addEventListener('change', () => {
      saveStoryInputsFromForm();
      if (id === 'story-template-select') {
        renderStoryTemplateSummary();
      }
    });
  });

  const btnStory = bind('btn-story');
  if (btnStory) {
    btnStory.addEventListener('click', async () => {
      updateOutput('story-output', '生成中...');
      state.story_inputs = normalizeStoryInputs({
        idea: bind('idea')?.value,
        theme: bind('theme')?.value,
        tone: bind('tone')?.value,
        structure: bind('structure')?.value,
        template_id: bind('story-template-select')?.value,
      });
      saveState();
      const payload = { ...state.story_inputs };

      const data = await runStage('story_engine', payload);
      if (!data.ok) {
        updateOutput('story-output', `错误: ${data.error}\n${data.detail || ''}`);
        return;
      }

      state.story_card = normalizeStoryCard(data.result.story_card);
      saveState();

      updateOutput('story-output', formatStoryResultV2(data.result));
      renderTaskMeta(data.meta);
      renderReviewLab('正在评分并生成改稿建议...');
      await runStoryReviewFlow('story_engine', { withRewrite: true });
    });
  }

  const btnStoryCompare = bind('btn-story-compare');
  if (btnStoryCompare) {
    btnStoryCompare.addEventListener('click', async () => {
      state.story_inputs = normalizeStoryInputs({
        idea: bind('idea')?.value,
        theme: bind('theme')?.value,
        tone: bind('tone')?.value,
        structure: bind('structure')?.value,
        template_id: bind('story-template-select')?.value,
      });
      saveState();
      const payload = { ...state.story_inputs };

      const availableProviders = providersList.filter(p => p.has_api_key);
      if (availableProviders.length < 2) {
        alert('至少需要配置两个模型的 API Key 才能进行对比');
        return;
      }

      const comparePanel = bind('compare-panel');
      const compareResults = bind('compare-results');
      comparePanel.style.display = 'block';
      compareResults.innerHTML = '<p class="hint">正在对比各模型生成结果...</p>';

      const data = await fetchJson('/api/agent/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          stage: 'story_engine',
          payload: payload,
          providers: availableProviders.map(p => p.id)
        }),
      });

      if (!data.ok) {
        compareResults.innerHTML = `<p class="hint" style="color:red;">错误: ${data.error}</p>`;
        return;
      }

      let html = '';
      for (const [providerId, result] of Object.entries(data.results)) {
        const provider = providersList.find(p => p.id === providerId);
        const providerName = provider ? provider.name : providerId;
        const formattedResult = formatStoryResultV2(result);
        html += `
          <div class="panel soft">
            <h3>${providerName}</h3>
            <pre style="max-height:300px; overflow:auto; font-size:12px;">${formattedResult}</pre>
          </div>
        `;
      }

      if (Object.keys(data.errors).length > 0) {
        html += '<div class="panel" style="background:#fff3cd;"><h3>错误</h3><ul>';
        for (const [providerId, error] of Object.entries(data.errors)) {
          const provider = providersList.find(p => p.id === providerId);
          const providerName = provider ? provider.name : providerId;
          html += `<li><strong>${providerName}:</strong> ${error}</li>`;
        }
        html += '</ul></div>';
      }

      compareResults.innerHTML = html;
    });
  }

  const btnWorkshop = bind('btn-workshop');
  if (btnWorkshop) {
    btnWorkshop.addEventListener('click', async () => {
      updateOutput('workshop-output', '生成中...');
      const payload = {
        story_card: state.story_card,
        role_requirements: bind('role-req')?.value.trim() || '',
        plot_requirements: bind('plot-req')?.value.trim() || '',
      };

      const data = await runStage('workshop', payload);
      if (!data.ok) {
        updateOutput('workshop-output', `错误: ${data.error}\n${data.detail || ''}`);
        return;
      }

      state.workshop = normalizeWorkshopData(data.result);
      saveState();

      updateOutput('workshop-output', formatWorkshopResult(state.workshop));
      renderTaskMeta(data.meta);
      refreshVisualEditors();
      renderReviewLab('正在根据最新剧本结构评分...');
      await runStoryReviewFlow('workshop', { withRewrite: true });
    });
  }

  const btnStoryboard = bind('btn-storyboard');
  if (btnStoryboard) {
    btnStoryboard.addEventListener('click', async () => {
      updateOutput('storyboard-output', '生成中...');
      const payload = {
        workshop: state.workshop,
        visual_style: bind('visual-style')?.value.trim() || '',
      };

      const data = await runStage('storyboard', payload);
      if (!data.ok) {
        updateOutput('storyboard-output', `错误: ${data.error}\n${data.detail || ''}`);
        return;
      }

      state.storyboard = normalizeStoryboardData(data.result);
      saveState();

      updateOutput('storyboard-output', formatStoryboardResult(state.storyboard));
      renderTaskMeta(data.meta);
      renderReviewLab('正在根据最新分镜评分...');
      await runStoryReviewFlow('storyboard', { withRewrite: true });
    });
  }

  const btnCommand = bind('btn-command');
  if (btnCommand) {
    btnCommand.addEventListener('click', async () => {
      await executeGlobalCommand(bind('command')?.value.trim() || '', { outputId: 'command-output', source: 'text' });
    });
  }
}

function initGlobalCommandWidget() {
  if (!document?.body || bind('global-command-widget')) {
    return;
  }

  const root = document.createElement('div');
  root.id = 'global-command-widget';
  root.className = 'global-command-widget collapsed';
  root.innerHTML = `
    <button type="button" id="global-command-fab" class="global-command-fab" aria-label="语音命令入口">语音</button>
    <section id="global-command-panel" class="global-command-panel" aria-hidden="true">
      <header class="global-command-header">
        <strong>全局语音命令</strong>
        <button type="button" id="global-command-close" class="global-command-close" aria-label="收起">收起</button>
      </header>
      <input id="global-command-input" class="global-command-input" placeholder="例如：将第三个场景改为夜间下雨" />
      <div class="global-command-actions">
        <button type="button" id="global-command-run">执行</button>
        <button type="button" id="global-command-voice" class="secondary">语音输入</button>
      </div>
      <div id="global-command-status" class="global-command-status">点击“语音输入”后开始说话</div>
      <pre id="global-command-output" class="global-command-output"></pre>
    </section>
  `;
  document.body.appendChild(root);

  const fab = bind('global-command-fab');
  const panel = bind('global-command-panel');
  const closeBtn = bind('global-command-close');
  const runBtn = bind('global-command-run');
  const voiceBtn = bind('global-command-voice');
  const input = bind('global-command-input');
  const status = bind('global-command-status');
  const output = bind('global-command-output');

  const setOpen = (open) => {
    root.classList.toggle('collapsed', !open);
    root.classList.toggle('expanded', open);
    if (panel) {
      panel.setAttribute('aria-hidden', open ? 'false' : 'true');
    }
  };

  const setStatus = (text, isError = false) => {
    if (!status) return;
    status.textContent = text;
    status.classList.toggle('error', Boolean(isError));
  };

  const runCommandFromWidget = async (source = 'text') => {
    const commandText = toText(input?.value);
    const result = await executeGlobalAssistantCommand(commandText, {
      outputId: null,
      source,
      setStatus,
    });
    if (output) {
      output.textContent = result.text || '';
    }
  };

  if (fab) {
    fab.addEventListener('click', () => {
      setOpen(true);
      input?.focus();
    });
    makeFloatingWidgetDraggable(root, fab, 'global_command_widget');
  }
  if (closeBtn) {
    closeBtn.addEventListener('click', () => setOpen(false));
  }
  if (runBtn) {
    runBtn.addEventListener('click', async () => {
      await runCommandFromWidget('text');
    });
  }
  if (input) {
    input.addEventListener('keydown', async (event) => {
      if (event.key === 'Enter') {
        event.preventDefault();
        await runCommandFromWidget('text');
      }
    });
  }

  const SpeechRecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognitionCtor) {
    if (voiceBtn) {
      voiceBtn.disabled = true;
    }
    setStatus('当前浏览器不支持语音识别，请使用 Chrome/Edge。', true);
    return;
  }

  const recognition = new SpeechRecognitionCtor();
  recognition.lang = 'zh-CN';
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;
  let listening = false;

  recognition.onstart = () => {
    listening = true;
    if (voiceBtn) {
      voiceBtn.textContent = '停止语音';
    }
    setStatus('正在听，请说出修改指令...');
  };

  recognition.onresult = async (event) => {
    const transcript = toText(event?.results?.[0]?.[0]?.transcript);
    if (!transcript) {
      setStatus('没有识别到有效内容，请再试一次。', true);
      return;
    }
    if (input) {
      input.value = transcript;
    }
    setStatus(`已识别：${transcript}`);
    await runCommandFromWidget('voice');
  };

  recognition.onerror = (event) => {
    const code = event?.error || 'unknown';
    if (code === 'no-speech') {
      setStatus('没有检测到语音，请再试一次。', true);
    } else if (code === 'not-allowed') {
      setStatus('麦克风权限被拒绝，请允许后重试。', true);
    } else {
      setStatus(`语音识别失败：${code}`, true);
    }
  };

  recognition.onend = () => {
    listening = false;
    if (voiceBtn) {
      voiceBtn.textContent = '语音输入';
    }
  };

  if (voiceBtn) {
    voiceBtn.addEventListener('click', () => {
      try {
        if (listening) {
          recognition.stop();
          return;
        }
        recognition.start();
      } catch (err) {
        setStatus(`无法启动语音识别：${err.message || err}`, true);
      }
    });
  }
}

function bindVisualActions() {
  const btnVisualUndo = bind('btn-visual-undo');
  if (btnVisualUndo) {
    btnVisualUndo.addEventListener('click', () => {
      if (visualUndoStack.length > 0) {
        state.workshop = visualUndoStack.pop();
        saveState();
        refreshVisualEditors();
        setRelationStatus('已撤销上一步操作。');
      } else {
        setRelationStatus('没有可撤销的操作。');
      }
    });
  }

  const btnCharAdd = bind('btn-char-add');
  if (btnCharAdd) {
    btnCharAdd.addEventListener('click', () => {
      if (!state.workshop) {
        state.workshop = {
          characters: [],
          relationships: [],
          plot_nodes: [],
          timeline_view: [],
          card_wall_groups: [],
        };
      }
      const charName = bind('new-char-name')?.value.trim();
      if (!charName) {
        setRelationStatus('请输入角色名称。');
        return;
      }

      pushVisualUndo();
      state.workshop.characters = state.workshop.characters || [];
      if (!state.workshop.characters.find(c => c.name === charName)) {
        state.workshop.characters.push({
          name: charName,
          tags: ["未定义标签"],
          motivation: "",
          arc: ""
        });
        setRelationStatus(`已新增独立角色：${charName}`);
        bind('new-char-name').value = '';
        saveState();
        refreshVisualEditors();
      } else {
        setRelationStatus('该角色已存在。');
      }
    });
  }

  const btnRelSave = bind('btn-rel-save');
  if (btnRelSave) {
    btnRelSave.addEventListener('click', () => {
      if (!state.workshop) {
        setRelationStatus('请先在创作工坊生成角色与情节（或先添加角色）。');
        return;
      }

      const from = bind('rel-from-display')?.value.trim() || '';
      const to = bind('rel-to-display')?.value.trim() || '';
      const type = bind('rel-type')?.value.trim() || '关系';
      const tension = bind('rel-tension')?.value.trim() || '';

      if (!from || !to) {
        setRelationStatus('请先在关系图上选择关系。');
        return;
      }

      pushVisualUndo();
      state.workshop.relationships = state.workshop.relationships || [];
      const idx =
        selectedRelationIndex !== null
          ? selectedRelationIndex
          : state.workshop.relationships.findIndex((r) => r.from === from && r.to === to);

      const rel = { from, to, type, tension };
      if (idx >= 0) {
        state.workshop.relationships[idx] = rel;
        setRelationStatus(`已更新关系：${from} -> ${to}`);
      } else {
        state.workshop.relationships.push(rel);
        selectedRelationIndex = state.workshop.relationships.length - 1;
        setRelationStatus(`已新增关系：${from} -> ${to}`);
      }

      draftRelationNodes = [];
      saveState();
      refreshVisualEditors();
    });
  }

  const btnRelRemove = bind('btn-rel-remove');
  if (btnRelRemove) {
    btnRelRemove.addEventListener('click', () => {
      if (!state.workshop?.relationships) {
        return;
      }

      const from = bind('rel-from-display')?.value.trim() || '';
      const to = bind('rel-to-display')?.value.trim() || '';

      pushVisualUndo();

      if (selectedRelationIndex !== null && state.workshop.relationships[selectedRelationIndex]) {
        const rel = state.workshop.relationships[selectedRelationIndex];
        state.workshop.relationships.splice(selectedRelationIndex, 1);
        setRelationStatus(`已删除关系：${rel.from} -> ${rel.to}`);
      } else {
        state.workshop.relationships = state.workshop.relationships.filter((r) => !(r.from === from && r.to === to));
        setRelationStatus(`已删除关系：${from} -> ${to}`);
      }

      selectedRelationIndex = null;
      draftRelationNodes = [];
      setRelationSelection('', '', '', '');
      saveState();
      refreshVisualEditors();
    });
  }
}

function clearRenderedVideoResult() {
  const wrap = bind('video-result-wrap');
  const player = bind('video-result-player');
  const text = bind('video-result-link');
  if (wrap) wrap.style.display = 'none';
  if (player) player.src = '';
  if (text) text.textContent = '';
}

function resetVideoRunState({
  preservePrompt = true,
  preserveScript = true,
  preserveSegments = false,
} = {}) {
  const video = getVideoState();
  stopVideoPolling(false);
  video.task_id = '';
  video.task_status = '';
  video.video_url = '';
  video.audio_mix_url = '';
  video.audio_mix_source_url = '';
  video.last_check_time = '';
  if (!preservePrompt) {
    video.prompt = '';
  }
  if (!preserveScript) {
    video.script = '';
  }
  if (!preserveSegments) {
    video.long_segments = [];
    video.total_duration = 0;
    video.filename_prefix = '';
  }
  clearRenderedVideoResult();
  return video;
}

function buildVideoPromptsFromStoryboard(storyboard) {
  const normalizedStoryboard = normalizeStoryboardData(storyboard);
  if (!normalizedStoryboard || !normalizedStoryboard.storyboards.length) {
    return '';
  }

  return normalizedStoryboard.storyboards
    .map((shot, index) => {
      const promptDraft = shot.prompt_draft || deriveStoryboardPrompt(shot);
      return `镜头 ${index + 1} (${shot.shot_type || '中景'}): ${shot.visual_description || ''}。提示词: ${promptDraft}`;
    })
    .join('\n\n');
}

function formatTitlePackagingResult(titleLab) {
  const data = normalizeTitleLab(titleLab);
  const lines = [];
  lines.push('【标题包装总览】');
  lines.push(data.summary || '-');
  lines.push('');
  lines.push(`【当前标题】${data.current_title || '-'}`);
  lines.push(`【推荐标题ID】${data.recommended_title_id || '-'}`);
  lines.push(`【推荐理由】${data.recommended_reason || '-'}`);
  lines.push('');

  if (data.evaluated_title) {
    lines.push('【当前标题评估】');
    lines.push(`${data.evaluated_title.title || '-'} | 总分 ${data.evaluated_title.overall_score || 0} | ${data.evaluated_title.verdict || '-'}`);
    lines.push(`风格: ${data.evaluated_title.style || '-'}`);
    lines.push(`抓人点: ${data.evaluated_title.hook_point || '-'}`);
    lines.push(`说明: ${data.evaluated_title.reason || '-'}`);
    (data.evaluated_title.scores || []).forEach((score) => {
      lines.push(`- ${score.name}: ${score.score}分 | ${score.reason || '-'}`);
    });
    lines.push('');
  }

  lines.push('【标题建议】');
  if (data.title_suggestions.length) {
    data.title_suggestions.forEach((item, index) => {
      lines.push(`${index + 1}. [${item.id}] ${item.title}`);
      lines.push(`   总分: ${item.overall_score || 0} | 结论: ${item.verdict || '-'}`);
      lines.push(`   风格: ${item.style || '-'} | 抓人点: ${item.hook_point || '-'}`);
      lines.push(`   理由: ${item.reason || '-'}`);
      (item.scores || []).forEach((score) => {
        lines.push(`   - ${score.name}: ${score.score}分 | ${score.reason || '-'}`);
      });
    });
  } else {
    lines.push('-');
  }

  lines.push('');
  lines.push('【话题标签建议】');
  if (data.topic_tags.length) {
    data.topic_tags.forEach((item) => lines.push(item));
  } else {
    lines.push('-');
  }

  return lines.join('\n');
}

function formatCoverPackagingResult(coverLab) {
  const data = normalizeCoverLab(coverLab);
  const lines = [];
  lines.push('【封面策划总览】');
  lines.push(data.summary || '-');
  lines.push('');
  lines.push(`【当前标题】${data.current_title || '-'}`);
  lines.push(`【风格偏好】${data.style_preference || '-'}`);
  lines.push(`【主打点】${data.focus_point || '-'}`);
  lines.push(`【封面主标题】${data.main_title || '-'}`);
  lines.push(`【封面副标题】${data.subtitle || '-'}`);
  lines.push('');
  lines.push('【封面短句】');
  if (data.hook_lines.length) {
    data.hook_lines.forEach((item, index) => lines.push(`${index + 1}. ${item}`));
  } else {
    lines.push('-');
  }
  lines.push('');
  lines.push(`【视觉方向】${data.visual_direction || '-'}`);
  lines.push(`【排版建议】${data.layout_direction || '-'}`);
  lines.push(`【色彩建议】${data.color_palette || '-'}`);
  lines.push('');
  lines.push('【文生图提示词】');
  lines.push(data.image_prompt || '-');
  if (data.image_task_id || data.image_task_status || data.image_status_message) {
    lines.push('');
    lines.push(`任务状态：${data.image_task_status || '-'}`);
    lines.push(`任务ID：${data.image_task_id || '-'}`);
    lines.push(`状态说明：${data.image_status_message || '-'}`);
  }
  if (data.generated_image_url) {
    lines.push('');
    lines.push(`【图片模型】${data.image_model || '-'}`);
    lines.push(`【图片尺寸】${data.image_size || '-'}`);
    lines.push(`【已生成封面】${data.generated_image_url}`);
  }
  return lines.join('\n');
}

function wait(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function setCoverImageRunStatus(text, mode = 'idle') {
  const target = bind('cover-image-run-status');
  if (!target) return;
  target.textContent = text || '未开始生成封面';
  target.classList.toggle('cover-image-status-running', mode === 'running');
  target.classList.toggle('cover-image-status-error', mode === 'error');
}

function setCoverImageButtonBusy(isBusy, text = '生成中...') {
  const button = bind('btn-cover-image');
  if (!button) return;
  if (!button.dataset.idleText) {
    button.dataset.idleText = button.textContent || '一键生成封面';
  }
  button.disabled = Boolean(isBusy);
  button.classList.toggle('is-loading', Boolean(isBusy));
  button.textContent = isBusy ? text : button.dataset.idleText;
}

function openCoverImageModal(url, statusText = '') {
  const modal = bind('cover-image-modal');
  const image = bind('cover-image-modal-preview');
  const status = bind('cover-image-modal-status');
  if (!modal || !image) return;
  if (!url) {
    setCoverImageRunStatus('还没有可预览的封面', 'error');
    return;
  }
  image.src = url;
  if (status) {
    status.textContent = statusText || state.cover_lab?.image_status_message || '封面已生成';
  }
  modal.classList.add('show');
  modal.setAttribute('aria-hidden', 'false');
}

function closeCoverImageModal() {
  const modal = bind('cover-image-modal');
  if (!modal) return;
  modal.classList.remove('show');
  modal.setAttribute('aria-hidden', 'true');
}

function renderCoverImagePreview(url) {
  const wrap = bind('cover-image-preview-wrap');
  const image = bind('cover-image-preview');
  const previewButton = bind('btn-cover-image-preview');
  if (!wrap || !image) return;
  if (!url) {
    wrap.style.display = 'none';
    image.removeAttribute('src');
    if (previewButton) previewButton.style.display = 'none';
    return;
  }
  wrap.style.display = 'block';
  image.src = url;
  if (previewButton) previewButton.style.display = 'inline-flex';
}

async function syncCoverImageToProject(imageUrl) {
  if (!imageUrl || !currentProjectId) return;
  currentProjectMeta = currentProjectMeta || {};
  currentProjectMeta.cover_image = imageUrl;
  await fetchJson(`/api/projects/${currentProjectId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      cover_image: imageUrl,
      last_provider: currentProvider,
    }),
  });
  await loadProjects();
  renderProjectMeta();
}

async function pollCoverImageTask(taskId) {
  for (let attempt = 1; attempt <= 24; attempt += 1) {
    if (attempt > 1) await wait(5000);
    setCoverImageRunStatus(`正在查询生成结果（第 ${attempt} 次）...`, 'running');
    const data = await runStage('cover_image_query', { task_id: taskId });
    if (!data.ok) return data;

    const result = data.result || {};
    state.cover_lab = normalizeCoverLab({
      ...state.cover_lab,
      image_task_id: toText(result.task_id) || taskId,
      image_task_status: toText(result.task_status),
      image_status_message: toText(result.status_message),
      image_model: toText(result.model) || state.cover_lab?.image_model || '',
      image_size: toText(result.size) || state.cover_lab?.image_size || '',
      generated_image_url: toText(result.image_url) || state.cover_lab?.generated_image_url || '',
      updated_at: new Date().toISOString(),
    });
    saveState();
    updateOutput('cover-pack-output', formatCoverPackagingResult(state.cover_lab));

    if (state.cover_lab.generated_image_url) {
      return { ok: true, result };
    }
    if (state.cover_lab.image_task_status === 'failed') {
      return { ok: false, error: state.cover_lab.image_status_message || '封面生成失败', detail: '' };
    }
  }
  return { ok: false, error: '封面生成超时，请稍后再试', detail: '' };
}

function openContentPlayer(targetId, title) {
  const modal = bind('content-player-modal');
  const text = bind('content-player-text');
  const heading = bind('content-player-title');
  const status = bind('content-player-status');
  const source = bind(targetId);
  if (!modal || !text || !source) return;

  const content = source.textContent || source.value || '';
  text.textContent = content || '暂无可预览内容，请先生成对应内容。';
  if (heading) heading.textContent = title || '内容预览播放';
  if (status) status.textContent = content ? '已载入内容' : '暂无内容';
  modal.classList.add('show');
  modal.setAttribute('aria-hidden', 'false');
}

function closeContentPlayer() {
  const modal = bind('content-player-modal');
  if (!modal) return;
  modal.classList.remove('show');
  modal.setAttribute('aria-hidden', 'true');
}

function buildExportPayload() {
  return {
    project: currentProjectMeta ? { ...currentProjectMeta } : null,
    current_provider: currentProvider,
    exported_at: new Date().toISOString(),
    story_card: normalizeStoryCard(state.story_card),
    cover_lab: normalizeCoverLab({
      ...state.cover_lab,
      current_title: bind('current-title-input')?.value || state.cover_lab?.current_title || '',
      style_preference: bind('cover-style-input')?.value || state.cover_lab?.style_preference || '',
      focus_point: bind('cover-focus-input')?.value || state.cover_lab?.focus_point || '',
    }),
    title_lab: normalizeTitleLab({
      ...state.title_lab,
      current_title: bind('current-title-input')?.value || state.title_lab?.current_title || '',
    }),
    workshop: normalizeWorkshopData(state.workshop),
    storyboard: normalizeStoryboardData(state.storyboard),
    video_lab: normalizeVideoState(getVideoState()),
  };
}


function restoreOutputsOnPageLoad() {
  if (bind('story-output') && state.story_card) {
    updateOutput('story-output', formatStoryResultV2({ story_card: state.story_card }));
  }
  if (bind('workshop-output') && state.workshop) {
    updateOutput('workshop-output', formatWorkshopResult(state.workshop));
  }
  if (bind('storyboard-output') && state.storyboard) {
    updateOutput('storyboard-output', formatStoryboardResult(state.storyboard));
  }
  if (bind('export-output') && hasDataForExport()) {
    updateOutput('export-output', '已检测到可导出的本地数据。');
  }
  if (bind('current-title-input')) {
    bind('current-title-input').value = state.title_lab?.current_title || '';
  }
  if (bind('cover-style-input')) {
    bind('cover-style-input').value = state.cover_lab?.style_preference || '';
  }
  if (bind('cover-focus-input')) {
    bind('cover-focus-input').value = state.cover_lab?.focus_point || '';
  }
  if (bind('title-pack-output') && state.title_lab && state.title_lab.title_suggestions?.length) {
    updateOutput('title-pack-output', formatTitlePackagingResult(state.title_lab));
  } else if (bind('title-pack-output')) {
    updateOutput('title-pack-output', '');
  }
  if (bind('cover-pack-output') && state.cover_lab && (state.cover_lab.summary || state.cover_lab.image_prompt || state.cover_lab.generated_image_url)) {
    updateOutput('cover-pack-output', formatCoverPackagingResult(state.cover_lab));
  } else if (bind('cover-pack-output')) {
    updateOutput('cover-pack-output', '');
  }
  renderCoverImagePreview(state.cover_lab?.generated_image_url || currentProjectMeta?.cover_image || '');
  if (bind('cover-image-run-status')) {
    if (state.cover_lab?.generated_image_url || currentProjectMeta?.cover_image) {
      setCoverImageRunStatus('封面已生成，可点击查看封面');
    } else if (state.cover_lab?.image_task_id) {
      setCoverImageRunStatus(`最近任务状态：${state.cover_lab.image_task_status || '未知'}`);
    } else {
      setCoverImageRunStatus('未开始生成封面');
    }
  }
  if (state.task_meta) {
    renderTaskMeta(state.task_meta, { persist: false });
  }
  renderCostWidget();

  const video = getVideoState();
  if (bind('video-script-output') && video.script) {
    updateOutput('video-script-output', video.script);
  }
  if (bind('video-prompt') && video.prompt) {
    bind('video-prompt').value = video.prompt;
  }
  if (bind('video-image-url')) {
    bind('video-image-url').value = video.image_url || '';
  }
  if (bind('video-start-image-url')) {
    bind('video-start-image-url').value = video.start_image_url || '';
  }
  if (bind('video-end-image-url')) {
    bind('video-end-image-url').value = video.end_image_url || '';
  }
  if (bind('video-audio-url')) {
    bind('video-audio-url').value = video.audio_url || '';
  }
  if (bind('video-image-preview-wrap') && bind('video-image-preview')) {
    if (video.image_url) {
      bind('video-image-preview-wrap').style.display = 'block';
      bind('video-image-preview').src = video.image_url;
    } else {
      bind('video-image-preview-wrap').style.display = 'none';
      bind('video-image-preview').removeAttribute('src');
    }
  }
  if (bind('video-audio-preview-wrap') && bind('video-audio-preview')) {
    if (video.audio_url) {
      bind('video-audio-preview-wrap').style.display = 'block';
      bind('video-audio-preview').src = video.audio_url;
    } else {
      bind('video-audio-preview-wrap').style.display = 'none';
      bind('video-audio-preview').removeAttribute('src');
    }
  }
  if (bind('video-image-upload-status')) {
    bind('video-image-upload-status').textContent = video.image_url
      ? '已加载参考图，将按图生视频模式提交。'
      : '上传后将自动用于图生视频';
  }
  if (bind('video-audio-upload-status')) {
    bind('video-audio-upload-status').textContent = video.audio_url
      ? '已加载 BGM，视频生成完成后会自动混入。'
      : '上传后会在视频生成完成后自动混入';
  }
  if (bind('video-task-output') && video.task_id) {
    updateOutput('video-task-output', `最近任务: ${video.task_id}\n状态: ${video.task_status || 'UNKNOWN'}`);
  }
  if (bind('video-auto-poll')) {
    bind('video-auto-poll').checked = Boolean(video.auto_poll);
  }
  if (video.video_url) {
    renderVideoResult(video.audio_mix_url || video.video_url);
  }

  if (bind('video-long-output') && video.long_segments && video.long_segments.length) {
    updateOutput('video-long-output', '已检测到长视频拆段任务，可在下方列表中逐段查询和播放。');
  }

  if (
    bind('video-auto-poll') &&
    video.task_id &&
    video.auto_poll &&
    !['SUCCEEDED', 'FAILED', 'CANCELED'].includes(video.task_status || '')
  ) {
    startVideoPolling();
  }

  renderLongSegmentsList();
}

function renderVideoResult(url) {
  const wrap = bind('video-result-wrap');
  const player = bind('video-result-player');
  const text = bind('video-result-link');
  if (!wrap || !player || !text) {
    return;
  }
  wrap.style.display = 'block';
  player.src = url;
  text.textContent = `视频链接(24小时内有效): ${url}`;
  captureProjectCoverFromVideo(url).catch((err) => {
    console.error('capture cover failed', err);
  });
}

async function captureProjectCoverFromVideo(url) {
  if (!url || !currentProjectId) {
    return;
  }

  const video = document.createElement('video');
  video.crossOrigin = 'anonymous';
  video.muted = true;
  video.preload = 'auto';
  video.src = url;

  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('cover capture timeout')), 12000);
    video.addEventListener('loadeddata', () => {
      clearTimeout(timer);
      resolve();
    }, { once: true });
    video.addEventListener('error', () => {
      clearTimeout(timer);
      reject(new Error('video load failed'));
    }, { once: true });
  });

  const canvas = document.createElement('canvas');
  canvas.width = Math.max(1, video.videoWidth || 320);
  canvas.height = Math.max(1, video.videoHeight || 180);
  const ctx = canvas.getContext('2d');
  if (!ctx) {
    return;
  }
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  const cover = canvas.toDataURL('image/jpeg', 0.82);

  currentProjectMeta = currentProjectMeta || {};
  currentProjectMeta.cover_image = cover;

  await fetchJson(`/api/projects/${currentProjectId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      cover_image: cover,
      last_provider: currentProvider,
    }),
  });

  await loadProjects();
  renderProjectMeta();
}

function renderLongSegmentsList() {
  const video = getVideoState();
  const box = bind('video-long-segments');
  if (!box) {
    return;
  }

  const segments = video.long_segments || [];
  if (!segments.length) {
    box.style.display = 'none';
    box.innerHTML = '';
    return;
  }

  box.style.display = 'block';

  let html = '<h3>长视频分段任务</h3>';
  html += '<p class="hint">可以逐段查询任务状态，若已生成视频会自动支持预览。</p>';
  html += '<ul class="segment-list">';
  segments.forEach((seg) => {
    const shortPrompt = String(seg.prompt || '').slice(0, 60);
    html += `
      <li style="margin-bottom:8px;">
        <div><strong>第 ${seg.index} 段</strong> | 时长 ${seg.duration} 秒 | Task ID: ${seg.task_id || '-'} | 状态: ${seg.task_status || 'PENDING'}</div>
        <div style="font-size:12px; color:var(--muted);">提示词: ${shortPrompt}${seg.prompt && seg.prompt.length > 60 ? '...' : ''}</div>
        ${seg.task_id ? `<button data-task-id="${seg.task_id}" data-index="${seg.index}" class="btn-seg-play">查询并播放</button>` : ''}
      </li>`;
  });
  html += '</ul>';

  box.innerHTML = html;

  const buttons = box.querySelectorAll('.btn-seg-play');
  buttons.forEach((btn) => {
    btn.addEventListener('click', async (e) => {
      const taskId = e.currentTarget.getAttribute('data-task-id');
      const idx = e.currentTarget.getAttribute('data-index');
      if (!taskId) {
        return;
      }

      updateOutput('video-task-output', `正在查询第 ${idx} 段任务 ${taskId} ...`);

      try {
        const data = await fetchJson(`/api/video/task/${taskId}`, { method: 'GET' });
        if (!data.ok) {
          updateOutput('video-task-output', `错误: ${data.error}
${data.detail || ''}`);
          return;
        }

        const output = data.result?.output || data.result || {};
        const status = output.task_status || output.status || 'UNKNOWN';
        const url = output.video_url || output.url || output?.result?.video?.url || '';

        updateOutput('video-task-output', `第 ${idx} 段任务 ${taskId}
状态: ${status}`);

        const currentVideo = getVideoState();
        let changed = false;
        const segment = currentVideo.long_segments.find((item) => String(item.task_id) === String(taskId));
        if (segment && segment.task_status !== status) {
          segment.task_status = status;
          if (url) {
            segment.video_url = url;
          }
          changed = true;
        }
        if (url && currentVideo.video_url !== url) {
          currentVideo.video_url = url;
          changed = true;
        }
        if (changed) {
          saveState();
          renderLongSegmentsList();
        }

        if (url) {
          const renderUrl = await ensureVideoBgmMixed(url, { silent: false });
          renderVideoResult(renderUrl);
        }
      } catch (err) {
        updateOutput('video-task-output', `错误: ${err.message}`);
      }
    });
  });
}

async function fetchJson(url, options) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 90000);
  try {
    const resp = await fetch(url, { ...(options || {}), signal: controller.signal });
    const raw = await resp.text();
    if (!raw) {
      return {};
    }
    try {
      return JSON.parse(raw);
    } catch (err) {
      throw new Error(`接口返回非 JSON（HTTP ${resp.status}）`);
    }
  } catch (err) {
    if (err?.name === 'AbortError') {
      throw new Error('请求超时（90秒），请稍后重试');
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }
}

function extractPromptFromScript(scriptText) {
  const markers = ['视频提示词', '视频生成提示词', '文生视频提示词'];
  const idx = markers
    .map((m) => scriptText.indexOf(m))
    .filter((n) => n >= 0)
    .sort((a, b) => a - b)[0] ?? -1;
  if (idx < 0) {
    return scriptText.slice(0, 600);
  }
  return scriptText.slice(idx).replace(/^.*?[:?]/, '').trim();
}

function bindExportActions() {
  const currentTitleInput = bind('current-title-input');
  if (currentTitleInput) {
    currentTitleInput.addEventListener('input', () => {
      state.title_lab = normalizeTitleLab({
        ...state.title_lab,
        current_title: currentTitleInput.value,
      });
      state.cover_lab = normalizeCoverLab({
        ...state.cover_lab,
        current_title: currentTitleInput.value,
      });
      saveState();
    });
  }

  const coverStyleInput = bind('cover-style-input');
  if (coverStyleInput) {
    coverStyleInput.addEventListener('input', () => {
      state.cover_lab = normalizeCoverLab({
        ...state.cover_lab,
        style_preference: coverStyleInput.value,
      });
      saveState();
    });
  }

  const coverFocusInput = bind('cover-focus-input');
  if (coverFocusInput) {
    coverFocusInput.addEventListener('input', () => {
      state.cover_lab = normalizeCoverLab({
        ...state.cover_lab,
        focus_point: coverFocusInput.value,
      });
      saveState();
    });
  }

  const coverPreviewButton = bind('btn-cover-image-preview');
  if (coverPreviewButton) {
    coverPreviewButton.addEventListener('click', () => {
      const imageUrl = state.cover_lab?.generated_image_url || currentProjectMeta?.cover_image || '';
      openCoverImageModal(imageUrl, state.cover_lab?.image_status_message || '封面已生成');
    });
  }

  const coverModalCloseButton = bind('btn-cover-image-modal-close');
  if (coverModalCloseButton) {
    coverModalCloseButton.addEventListener('click', closeCoverImageModal);
  }

  const coverModal = bind('cover-image-modal');
  if (coverModal) {
    coverModal.addEventListener('click', (event) => {
      if (event.target === coverModal) {
        closeCoverImageModal();
      }
    });
  }

  const btnTitlePack = bind('btn-title-packaging');
  if (btnTitlePack) {
    btnTitlePack.addEventListener('click', async () => {
      if (!hasDataForExport()) {
        updateOutput('title-pack-output', '暂无可分析内容，请先生成故事、剧本或分镜。');
        return;
      }

      updateOutput('title-pack-output', '正在生成标题建议与话题标签...');
      const payload = {
        project: currentProjectMeta ? { ...currentProjectMeta } : null,
        current_title: bind('current-title-input')?.value?.trim() || '',
        story_card: normalizeStoryCard(state.story_card),
        workshop: normalizeWorkshopData(state.workshop),
        storyboard: normalizeStoryboardData(state.storyboard),
      };
      const data = await runStage('title_packaging', payload);
      if (!data.ok) {
        updateOutput('title-pack-output', `错误: ${data.error}\n${data.detail || ''}`);
        return;
      }

      state.title_lab = normalizeTitleLab({
        ...data.result,
        current_title: bind('current-title-input')?.value?.trim() || data.result.current_title || '',
        updated_at: new Date().toISOString(),
      });
      saveState();
      updateOutput('title-pack-output', formatTitlePackagingResult(state.title_lab));
    });
  }

  const btnCoverPack = bind('btn-cover-packaging');
  if (btnCoverPack) {
    btnCoverPack.addEventListener('click', async () => {
      if (!hasDataForExport()) {
        updateOutput('cover-pack-output', '暂无可分析内容，请先生成故事、剧本或分镜。');
        return;
      }

      updateOutput('cover-pack-output', '正在生成短剧封面策划...');
      setCoverImageRunStatus('正在生成封面策划...', 'running');
      const recommendedTitle =
        (state.title_lab?.title_suggestions || []).find((item) => item.id === state.title_lab?.recommended_title_id)?.title
        || '';
      const payload = {
        project: currentProjectMeta ? { ...currentProjectMeta } : null,
        current_title: bind('current-title-input')?.value?.trim() || recommendedTitle || state.cover_lab?.current_title || '',
        style_preference: bind('cover-style-input')?.value?.trim() || '',
        focus_point: bind('cover-focus-input')?.value?.trim() || '',
        story_card: normalizeStoryCard(state.story_card),
        workshop: normalizeWorkshopData(state.workshop),
        storyboard: normalizeStoryboardData(state.storyboard),
      };
      const data = await runStage('cover_packaging', payload);
      if (!data.ok) {
        updateOutput('cover-pack-output', `错误: ${data.error}\n${data.detail || ''}`);
        setCoverImageRunStatus(`封面策划失败：${data.error}`, 'error');
        return;
      }

      state.cover_lab = normalizeCoverLab({
        ...data.result,
        current_title: payload.current_title,
        style_preference: payload.style_preference,
        focus_point: payload.focus_point,
        generated_image_url: state.cover_lab?.generated_image_url || '',
        image_model: state.cover_lab?.image_model || '',
        image_size: state.cover_lab?.image_size || '',
        image_task_id: state.cover_lab?.image_task_id || '',
        image_task_status: state.cover_lab?.image_task_status || '',
        image_status_message: state.cover_lab?.image_status_message || '',
        updated_at: new Date().toISOString(),
      });
      saveState();
      updateOutput('cover-pack-output', formatCoverPackagingResult(state.cover_lab));
      setCoverImageRunStatus('封面策划已生成，可以继续一键生成封面');
      renderCoverImagePreview(state.cover_lab.generated_image_url || currentProjectMeta?.cover_image || '');
    });
  }

  const btnCoverImage = bind('btn-cover-image');
  if (btnCoverImage) {
    btnCoverImage.addEventListener('click', async () => {
      if (!hasDataForExport()) {
        updateOutput('cover-pack-output', '暂无可分析内容，请先生成故事、剧本或分镜。');
        return;
      }

      setCoverImageButtonBusy(true, '生成中...');
      setCoverImageRunStatus('正在准备封面生成任务...', 'running');
      try {
        let coverLab = normalizeCoverLab(state.cover_lab);
        if (!coverLab.image_prompt) {
          setCoverImageRunStatus('正在先生成封面策划...', 'running');
          updateOutput('cover-pack-output', '正在先生成封面策划...');
          const recommendedTitle =
            (state.title_lab?.title_suggestions || []).find((item) => item.id === state.title_lab?.recommended_title_id)?.title
            || '';
          const packagingPayload = {
            project: currentProjectMeta ? { ...currentProjectMeta } : null,
            current_title: bind('current-title-input')?.value?.trim() || recommendedTitle || state.cover_lab?.current_title || '',
            style_preference: bind('cover-style-input')?.value?.trim() || '',
            focus_point: bind('cover-focus-input')?.value?.trim() || '',
            story_card: normalizeStoryCard(state.story_card),
            workshop: normalizeWorkshopData(state.workshop),
            storyboard: normalizeStoryboardData(state.storyboard),
          };
          const packagingData = await runStage('cover_packaging', packagingPayload);
          if (!packagingData.ok) {
            updateOutput('cover-pack-output', `错误: ${packagingData.error}\n${packagingData.detail || ''}`);
            setCoverImageRunStatus(`封面策划失败：${packagingData.error}`, 'error');
            return;
          }
          state.cover_lab = normalizeCoverLab({
            ...packagingData.result,
            current_title: packagingPayload.current_title,
            style_preference: packagingPayload.style_preference,
            focus_point: packagingPayload.focus_point,
            generated_image_url: state.cover_lab?.generated_image_url || '',
            image_model: state.cover_lab?.image_model || '',
            image_size: state.cover_lab?.image_size || '',
            updated_at: new Date().toISOString(),
          });
          saveState();
          coverLab = normalizeCoverLab(state.cover_lab);
          updateOutput('cover-pack-output', formatCoverPackagingResult(coverLab));
        }

        updateOutput('cover-pack-output', `${formatCoverPackagingResult(coverLab)}\n\n正在提交封面生成任务...`);
        setCoverImageRunStatus('正在提交封面生成任务...', 'running');
        const imageData = await runStage('cover_image_generate', { image_prompt: coverLab.image_prompt });
        if (!imageData.ok) {
          updateOutput('cover-pack-output', `错误: ${imageData.error}\n${imageData.detail || ''}`);
          setCoverImageRunStatus(`生成失败：${imageData.error}`, 'error');
          return;
        }

        let imageUrl = toText(imageData.result?.image_url);
        const imageTaskId = toText(imageData.result?.task_id);
        if (imageTaskId) {
          state.cover_lab = normalizeCoverLab({
            ...state.cover_lab,
            image_model: toText(imageData.result?.model) || state.cover_lab?.image_model || '',
            image_size: toText(imageData.result?.size) || state.cover_lab?.image_size || '',
            image_task_id: imageTaskId,
            image_task_status: toText(imageData.result?.task_status) || (imageUrl ? 'succeed' : 'submitted'),
            image_status_message: '',
            updated_at: new Date().toISOString(),
          });
          saveState();
          setCoverImageRunStatus(`任务已创建：${imageTaskId}，正在生成...`, 'running');
        }
        if (!imageUrl && imageTaskId) {
          updateOutput('cover-pack-output', `${formatCoverPackagingResult(state.cover_lab)}\n\n正在等待封面生成完成...`);
          const pollData = await pollCoverImageTask(imageTaskId);
          if (!pollData.ok) {
            updateOutput('cover-pack-output', `错误: ${pollData.error}\n${pollData.detail || ''}`);
            setCoverImageRunStatus(`生成失败：${pollData.error}`, 'error');
            return;
          }
          imageUrl = toText(pollData.result?.image_url) || state.cover_lab.generated_image_url;
        }
        if (!imageUrl) {
          updateOutput('cover-pack-output', '错误: 图片任务已完成，但没有返回可用图片地址');
          setCoverImageRunStatus('生成失败：没有返回可用图片地址', 'error');
          return;
        }

        state.cover_lab = normalizeCoverLab({
          ...state.cover_lab,
          generated_image_url: imageUrl,
          image_model: toText(imageData.result?.model) || state.cover_lab?.image_model || '',
          image_size: toText(imageData.result?.size) || state.cover_lab?.image_size || '',
          image_task_status: 'succeed',
          image_status_message: '封面已生成并同步到当前项目',
          updated_at: new Date().toISOString(),
        });
        saveState();
        await syncCoverImageToProject(imageUrl);
        updateOutput('cover-pack-output', formatCoverPackagingResult(state.cover_lab));
        renderCoverImagePreview(imageUrl);
        openCoverImageModal(imageUrl, '封面生成成功，已同步到当前项目');
        setCoverImageRunStatus('封面生成成功，已同步到当前项目');
      } catch (err) {
        updateOutput('cover-pack-output', `错误: ${err.message}`);
        setCoverImageRunStatus(`生成失败：${err.message}`, 'error');
      } finally {
        setCoverImageButtonBusy(false);
      }
    });
  }

  const btnExport = bind('btn-export');
  if (btnExport) {
    btnExport.addEventListener('click', async () => {
      if (!hasDataForExport()) {
        updateOutput('export-output', '暂无可导出数据，请先去创作工坊生成内容。');
        return;
      }

      updateOutput('export-output', '导出中...');
      const payload = buildExportPayload();
      const data = await runStage('export', payload);
      if (!data.ok) {
        updateOutput('export-output', `错误: ${data.error}\n${data.detail || ''}`);
        return;
      }

      updateOutput('export-output', data.result.markdown);
    });
  }

  const btnDocx = bind('btn-export-docx');
  if (btnDocx) {
    btnDocx.addEventListener('click', async () => {
      if (!hasDataForExport()) {
        updateOutput('export-output', '暂无可导出数据，请先去创作工坊生成内容。');
        return;
      }

      updateOutput('export-output', '正在生成 Word 文件...');
      try {
        await downloadFile('/api/export/docx', 'ai_short_drama_export.docx', buildExportPayload());
        updateOutput('export-output', 'Word 导出成功，已开始下载。');
      } catch (err) {
        updateOutput('export-output', `错误: ${err.message}`);
      }
    });
  }

  const btnPdf = bind('btn-export-pdf');
  if (btnPdf) {
    btnPdf.addEventListener('click', async () => {
      if (!hasDataForExport()) {
        updateOutput('export-output', '暂无可导出数据，请先去创作工坊生成内容。');
        return;
      }

      updateOutput('export-output', '正在生成 PDF 文件...');
      try {
        await downloadFile('/api/export/pdf', 'ai_short_drama_export.pdf', buildExportPayload());
        updateOutput('export-output', 'PDF 导出成功，已开始下载。');
      } catch (err) {
        updateOutput('export-output', `错误: ${err.message}`);
      }
    });
  }
}

function bindVideoActions() {
  let imageUploadInFlight = false;
  let audioUploadInFlight = false;

  function setVideoImagePreview(url) {
    const previewWrap = bind('video-image-preview-wrap');
    const preview = bind('video-image-preview');
    if (!previewWrap || !preview) {
      return;
    }

    const imageUrl = String(url || '').trim();
    if (!imageUrl) {
      previewWrap.style.display = 'none';
      preview.removeAttribute('src');
      return;
    }

    previewWrap.style.display = 'block';
    preview.src = imageUrl;
  }

  function setVideoImageProgress(percent) {
    const progressWrap = bind('video-image-progress-wrap');
    const progress = bind('video-image-progress');
    const progressText = bind('video-image-progress-text');
    if (!progressWrap || !progress || !progressText) {
      return;
    }

    const value = Math.max(0, Math.min(100, Number(percent || 0)));
    progressWrap.style.display = 'flex';
    progress.value = value;
    progressText.textContent = `${Math.round(value)}%`;
  }

  function hideVideoImageProgress() {
    const progressWrap = bind('video-image-progress-wrap');
    const progress = bind('video-image-progress');
    const progressText = bind('video-image-progress-text');
    if (!progressWrap || !progress || !progressText) {
      return;
    }
    progressWrap.style.display = 'none';
    progress.value = 0;
    progressText.textContent = '0%';
  }

  function setVideoImageUploadStatus(text, isError = false) {
    const status = bind('video-image-upload-status');
    if (!status) {
      return;
    }
    status.textContent = text;
    status.style.color = isError ? '#a3322e' : 'var(--muted)';
  }

  function setVideoAudioPreview(url) {
    const previewWrap = bind('video-audio-preview-wrap');
    const preview = bind('video-audio-preview');
    if (!previewWrap || !preview) {
      return;
    }

    const audioUrl = String(url || '').trim();
    if (!audioUrl) {
      previewWrap.style.display = 'none';
      preview.removeAttribute('src');
      return;
    }

    previewWrap.style.display = 'block';
    preview.src = audioUrl;
  }

  function setVideoAudioProgress(percent) {
    const progressWrap = bind('video-audio-progress-wrap');
    const progress = bind('video-audio-progress');
    const progressText = bind('video-audio-progress-text');
    if (!progressWrap || !progress || !progressText) {
      return;
    }

    const value = Math.max(0, Math.min(100, Number(percent || 0)));
    progressWrap.style.display = 'flex';
    progress.value = value;
    progressText.textContent = `${Math.round(value)}%`;
  }

  function hideVideoAudioProgress() {
    const progressWrap = bind('video-audio-progress-wrap');
    const progress = bind('video-audio-progress');
    const progressText = bind('video-audio-progress-text');
    if (!progressWrap || !progress || !progressText) {
      return;
    }
    progressWrap.style.display = 'none';
    progress.value = 0;
    progressText.textContent = '0%';
  }

  function setVideoAudioUploadStatus(text, isError = false) {
    const status = bind('video-audio-upload-status');
    if (!status) {
      return;
    }
    status.textContent = text;
    status.style.color = isError ? '#a3322e' : 'var(--muted)';
  }

  function syncVideoImageInputsToState() {
    const video = getVideoState();
    video.image_url = bind('video-image-url')?.value.trim() || '';
    video.start_image_url = bind('video-start-image-url')?.value.trim() || '';
    video.end_image_url = bind('video-end-image-url')?.value.trim() || '';
    saveState();
  }

  function syncVideoAudioInputToState() {
    const video = getVideoState();
    video.audio_url = bind('video-audio-url')?.value.trim() || '';
    video.audio_mix_url = '';
    video.audio_mix_source_url = '';
    saveState();
  }

  function detectVideoMode(imageUrl, startImageUrl, endImageUrl) {
    if (startImageUrl && endImageUrl) {
      return 'start_end';
    }
    if (imageUrl) {
      return 'image';
    }
    return 'text';
  }

  function isPrivateIpv4(hostname) {
    if (!/^\d+\.\d+\.\d+\.\d+$/.test(hostname || '')) {
      return false;
    }
    const parts = hostname.split('.').map((n) => Number(n));
    if (parts.length !== 4 || parts.some((n) => !Number.isFinite(n) || n < 0 || n > 255)) {
      return false;
    }
    if (parts[0] === 10) return true;
    if (parts[0] === 127) return true;
    if (parts[0] === 192 && parts[1] === 168) return true;
    if (parts[0] === 172 && parts[1] >= 16 && parts[1] <= 31) return true;
    if (parts[0] === 169 && parts[1] === 254) return true;
    return false;
  }

  function isUnsafeImageUrl(urlText) {
    const text = String(urlText || '').trim();
    if (!text) {
      return false;
    }
    try {
      const u = new URL(text, window.location.origin);
      const protocol = String(u.protocol || '').toLowerCase();
      const hostname = String(u.hostname || '').toLowerCase();

      if (protocol !== 'http:' && protocol !== 'https:') {
        return true;
      }
      if (!hostname) {
        return true;
      }
      if (hostname === 'localhost' || hostname === '::1' || hostname === '[::1]') {
        return true;
      }
      if (isPrivateIpv4(hostname)) {
        return true;
      }
      return false;
    } catch (err) {
      return true;
    }
  }

  function validateImageUrlsForTask(imageUrl, startImageUrl, endImageUrl) {
    const items = [
      { label: '图生首帧URL', value: imageUrl },
      { label: '首尾帧-首帧URL', value: startImageUrl },
      { label: '首尾帧-尾帧URL', value: endImageUrl },
    ];

    const invalid = items.filter((item) => item.value && isUnsafeImageUrl(item.value));
    if (!invalid.length) {
      return { ok: true, message: '' };
    }

    const invalidLabels = invalid.map((item) => item.label).join('、');
    return {
      ok: false,
      message:
        `${invalidLabels} 不是公网可访问地址，模型服务无法读取。\n` +
        '请改用公网可访问的 http/https 图片链接（不要用 localhost、127.0.0.1、192.168.x.x 等内网地址）。',
    };
  }

  async function uploadVideoImage(file) {
    if (imageUploadInFlight) {
      return;
    }
    if (!file) {
      return;
    }
    if (!String(file.type || '').startsWith('image/')) {
      setVideoImageUploadStatus('仅支持图片文件（jpg/png/webp/bmp）。', true);
      return;
    }
    if (Number(file.size || 0) > 15 * 1024 * 1024) {
      setVideoImageUploadStatus('图片过大，请上传 15MB 以内文件。', true);
      return;
    }

    setVideoImageUploadStatus('正在上传图片...');
    setVideoImageProgress(0);
    imageUploadInFlight = true;

    const formData = new FormData();
    formData.append('image', file);

    try {
      const data = await new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/video/upload-image', true);
        xhr.timeout = 90000;

        xhr.upload.onprogress = (event) => {
          if (!event.lengthComputable) {
            return;
          }
          const percent = (event.loaded / event.total) * 100;
          setVideoImageProgress(percent);
        };

        xhr.onload = () => {
          let parsed = {};
          try {
            parsed = xhr.responseText ? JSON.parse(xhr.responseText) : {};
          } catch (err) {
            reject(new Error(`上传返回异常（HTTP ${xhr.status}）`));
            return;
          }
          if (xhr.status < 200 || xhr.status >= 300 || !parsed.ok) {
            const backendMsg = [parsed.error, parsed.detail].filter(Boolean).join(' ');
            reject(new Error(backendMsg || `上传失败（HTTP ${xhr.status}）`));
            return;
          }
          resolve(parsed);
        };

        xhr.onerror = () => reject(new Error('网络异常，上传失败。'));
        xhr.ontimeout = () => reject(new Error('上传超时，请稍后重试。'));
        xhr.onabort = () => reject(new Error('上传已取消。'));

        xhr.send(formData);
      });

      setVideoImageProgress(100);

      const imageUrl = String(data.image_url || '').trim();
      if (!imageUrl) {
        throw new Error('上传成功但未返回可用图片地址。');
      }

      if (bind('video-image-url')) {
        bind('video-image-url').value = imageUrl;
      }
      setVideoImagePreview(imageUrl);
      syncVideoImageInputsToState();
      setVideoImageUploadStatus('参考图上传成功，已自动用于图生视频。');
    } catch (err) {
      setVideoImageUploadStatus(`上传失败: ${err.message}`, true);
    } finally {
      imageUploadInFlight = false;
      setTimeout(() => {
        hideVideoImageProgress();
      }, 500);
    }
  }

  async function uploadVideoAudio(file) {
    if (audioUploadInFlight) {
      return;
    }
    if (!file) {
      return;
    }
    const fileType = String(file.type || '').toLowerCase();
    const audioExtOk = /\.(mp3|wav|m4a|aac|ogg|flac)$/i.test(String(file.name || ''));
    if (fileType && !fileType.startsWith('audio/') && !audioExtOk) {
      setVideoAudioUploadStatus('仅支持音频文件（mp3/wav/m4a/aac/ogg/flac）。', true);
      return;
    }
    if (!fileType && !audioExtOk) {
      setVideoAudioUploadStatus('仅支持音频文件（mp3/wav/m4a/aac/ogg/flac）。', true);
      return;
    }
    if (Number(file.size || 0) > 50 * 1024 * 1024) {
      setVideoAudioUploadStatus('音频过大，请上传 50MB 以内文件。', true);
      return;
    }

    setVideoAudioUploadStatus('正在上传音频...');
    setVideoAudioProgress(0);
    audioUploadInFlight = true;

    const formData = new FormData();
    formData.append('audio', file);

    try {
      const data = await new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/video/upload-audio', true);
        xhr.timeout = 120000;

        xhr.upload.onprogress = (event) => {
          if (!event.lengthComputable) {
            return;
          }
          setVideoAudioProgress((event.loaded / event.total) * 100);
        };

        xhr.onload = () => {
          let parsed = {};
          try {
            parsed = xhr.responseText ? JSON.parse(xhr.responseText) : {};
          } catch (err) {
            reject(new Error(`上传返回异常（HTTP ${xhr.status}）`));
            return;
          }
          if (xhr.status < 200 || xhr.status >= 300 || !parsed.ok) {
            const backendMsg = [parsed.error, parsed.detail].filter(Boolean).join(' ');
            reject(new Error(backendMsg || `上传失败（HTTP ${xhr.status}）`));
            return;
          }
          resolve(parsed);
        };

        xhr.onerror = () => reject(new Error('网络异常，上传失败。'));
        xhr.ontimeout = () => reject(new Error('上传超时，请稍后重试。'));
        xhr.onabort = () => reject(new Error('上传已取消。'));

        xhr.send(formData);
      });

      setVideoAudioProgress(100);

      const audioUrl = String(data.audio_url || '').trim();
      if (!audioUrl) {
        throw new Error('上传成功但未返回可用音频地址。');
      }

      if (bind('video-audio-url')) {
        bind('video-audio-url').value = audioUrl;
      }
      setVideoAudioPreview(audioUrl);
      syncVideoAudioInputToState();
      setVideoAudioUploadStatus(data.warning || 'BGM 上传成功，视频生成完成后会自动混入。');
    } catch (err) {
      setVideoAudioUploadStatus(`上传失败: ${err.message}`, true);
    } finally {
      audioUploadInFlight = false;
      setTimeout(() => {
        hideVideoAudioProgress();
      }, 500);
    }
  }

  const imageDropzone = bind('video-image-dropzone');
  const imageFileInput = bind('video-image-file');
  if (imageDropzone && imageFileInput) {
    imageDropzone.addEventListener('click', () => {
      imageFileInput.click();
    });

    imageDropzone.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        imageFileInput.click();
      }
    });

    imageDropzone.addEventListener('dragover', (event) => {
      event.preventDefault();
      imageDropzone.classList.add('is-dragover');
    });

    imageDropzone.addEventListener('dragleave', () => {
      imageDropzone.classList.remove('is-dragover');
    });

    imageDropzone.addEventListener('drop', async (event) => {
      event.preventDefault();
      imageDropzone.classList.remove('is-dragover');
      const file = event.dataTransfer?.files?.[0];
      await uploadVideoImage(file);
    });

    imageFileInput.addEventListener('change', async () => {
      const file = imageFileInput.files?.[0];
      await uploadVideoImage(file);
      imageFileInput.value = '';
    });
  }

  const audioDropzone = bind('video-audio-dropzone');
  const audioFileInput = bind('video-audio-file');
  if (audioDropzone && audioFileInput) {
    audioDropzone.addEventListener('click', () => {
      audioFileInput.click();
    });

    audioDropzone.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        audioFileInput.click();
      }
    });

    audioDropzone.addEventListener('dragover', (event) => {
      event.preventDefault();
      audioDropzone.classList.add('is-dragover');
    });

    audioDropzone.addEventListener('dragleave', () => {
      audioDropzone.classList.remove('is-dragover');
    });

    audioDropzone.addEventListener('drop', async (event) => {
      event.preventDefault();
      audioDropzone.classList.remove('is-dragover');
      const file = event.dataTransfer?.files?.[0];
      await uploadVideoAudio(file);
    });

    audioFileInput.addEventListener('change', async () => {
      const file = audioFileInput.files?.[0];
      await uploadVideoAudio(file);
      audioFileInput.value = '';
    });
  }

  const imageUrlInput = bind('video-image-url');
  if (imageUrlInput) {
    imageUrlInput.addEventListener('change', () => {
      const imageUrl = imageUrlInput.value.trim();
      setVideoImagePreview(imageUrl);
      syncVideoImageInputsToState();
      setVideoImageUploadStatus(
        imageUrl ? '已设置首帧参考图，将按图生视频模式提交。' : '上传后将自动用于图生视频',
        false,
      );
    });
  }

  const clearImageButton = bind('btn-video-image-clear');
  if (clearImageButton) {
    clearImageButton.addEventListener('click', () => {
      if (bind('video-image-url')) {
        bind('video-image-url').value = '';
      }
      if (bind('video-image-file')) {
        bind('video-image-file').value = '';
      }
      setVideoImagePreview('');
      syncVideoImageInputsToState();
      hideVideoImageProgress();
      setVideoImageUploadStatus('已删除参考图，当前将按文生视频模式提交。');
    });
  }

  const audioUrlInput = bind('video-audio-url');
  if (audioUrlInput) {
    audioUrlInput.addEventListener('change', () => {
      const audioUrl = audioUrlInput.value.trim();
      setVideoAudioPreview(audioUrl);
      syncVideoAudioInputToState();
      setVideoAudioUploadStatus(
        audioUrl ? '已设置 BGM，视频生成完成后会自动混入。' : '上传后会在视频生成完成后自动混入',
        false,
      );
    });
  }

  const clearAudioButton = bind('btn-video-audio-clear');
  if (clearAudioButton) {
    clearAudioButton.addEventListener('click', () => {
      if (bind('video-audio-url')) {
        bind('video-audio-url').value = '';
      }
      if (bind('video-audio-file')) {
        bind('video-audio-file').value = '';
      }
      setVideoAudioPreview('');
      syncVideoAudioInputToState();
      hideVideoAudioProgress();
      setVideoAudioUploadStatus('已删除 BGM，当前只返回模型生成的视频。');
    });
  }

  const startImageUrlInput = bind('video-start-image-url');
  if (startImageUrlInput) {
    startImageUrlInput.addEventListener('change', syncVideoImageInputsToState);
  }

  const endImageUrlInput = bind('video-end-image-url');
  if (endImageUrlInput) {
    endImageUrlInput.addEventListener('change', syncVideoImageInputsToState);
  }

  const videoPromptInput = bind('video-prompt');
  if (videoPromptInput) {
    videoPromptInput.addEventListener('change', () => {
      const nextPrompt = videoPromptInput.value;
      const video = getVideoState();
      if (video.prompt === nextPrompt) {
        return;
      }
      resetVideoRunState({ preservePrompt: false, preserveScript: true, preserveSegments: false });
      video.prompt = nextPrompt;
      saveState();
    });
  }

  const btnImportLabInfo = bind('btn-import-lab-info');
  if (btnImportLabInfo) {
    btnImportLabInfo.addEventListener('click', () => {
      if (!state.story_card && !state.workshop) {
        alert('请先在创作工坊生成故事和角色节点！');
        return;
      }

      if (state.story_card) {
        if (bind('video-idea')) bind('video-idea').value = state.story_card.logline || state.story_card.core_conflict || '';
        if (bind('video-genre')) bind('video-genre').value = state.story_card.theme || '';
      }
      if (state.workshop?.characters?.length) {
        const roles = state.workshop.characters.map((character) => character.name).join('、');
        if (bind('video-roles')) bind('video-roles').value = roles;
      }

      resetVideoRunState({ preservePrompt: false, preserveScript: false, preserveSegments: false });
      if (bind('video-prompt')) bind('video-prompt').value = '';
      if (bind('video-script-output')) updateOutput('video-script-output', '');
      if (bind('video-task-output')) updateOutput('video-task-output', '');
      if (bind('video-long-output')) updateOutput('video-long-output', '');
      saveState();

      alert('已导入核心设定、题材和人物，可以继续生成短剧脚本。');
    });
  }

  const btnImportLabStoryboard = bind('btn-import-lab-storyboard');
  if (btnImportLabStoryboard) {
    btnImportLabStoryboard.addEventListener('click', () => {
      const finalPrompts = buildVideoPromptsFromStoryboard(state.storyboard);
      if (!finalPrompts) {
        alert('请先在创作工坊生成并保存分镜！');
        return;
      }

      const video = resetVideoRunState({ preservePrompt: false, preserveScript: true, preserveSegments: false });
      video.prompt = finalPrompts;
      if (bind('video-prompt')) {
        bind('video-prompt').value = finalPrompts;
      }
      if (bind('video-task-output')) updateOutput('video-task-output', '');
      if (bind('video-long-output')) updateOutput('video-long-output', '');
      saveState();

      alert('已将分镜导入为视频提示词，现在可以创建视频任务了。');
    });
  }

  const btnScript = bind('btn-video-script');
  if (btnScript) {
    btnScript.addEventListener('click', async () => {
      updateOutput('video-script-output', '正在生成短剧脚本...');

      const payload = {
        idea: bind('video-idea')?.value.trim() || '',
        genre: bind('video-genre')?.value.trim() || '',
        roles: bind('video-roles')?.value.trim() || '',
        style: bind('video-style')?.value.trim() || '',
        duration_sec: Number(bind('video-duration')?.value || 10),
      };

      const data = await fetchJson('/api/video/script', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ payload, provider: currentProvider }),
      });

      if (!data.ok) {
        updateOutput('video-script-output', `错误: ${data.error}\n${data.detail || ''}`);
        return;
      }

      const video = resetVideoRunState({ preservePrompt: false, preserveScript: false, preserveSegments: false });
      video.script = data.script;
      video.prompt = extractPromptFromScript(data.script);
      saveState();

      updateOutput('video-script-output', data.script);
      if (bind('video-prompt')) {
        bind('video-prompt').value = video.prompt;
      }
      if (bind('video-task-output')) updateOutput('video-task-output', '');
      if (bind('video-long-output')) updateOutput('video-long-output', '');
    });
  }

  const btnCreate = bind('btn-video-create');
  if (btnCreate) {
    btnCreate.addEventListener('click', async () => {
      updateOutput('video-task-output', '正在创建视频任务...');

      const imageUrl = bind('video-image-url')?.value.trim() || '';
      const startImageUrl = bind('video-start-image-url')?.value.trim() || '';
      const endImageUrl = bind('video-end-image-url')?.value.trim() || '';
      const audioUrl = bind('video-audio-url')?.value.trim() || '';

      const payload = {
        prompt: bind('video-prompt')?.value.trim() || '',
        model: bind('video-model')?.value.trim() || 'viduq3-turbo',
        size: bind('video-size')?.value.trim() || '1280*720',
        duration: Number(bind('video-duration-task')?.value || 10),
        prompt_extend: true,
        image_url: imageUrl,
        start_image_url: startImageUrl,
        end_image_url: endImageUrl,
        video_mode: detectVideoMode(imageUrl, startImageUrl, endImageUrl),
      };

      const imageValidation = validateImageUrlsForTask(payload.image_url, payload.start_image_url, payload.end_image_url);
      if (!imageValidation.ok) {
        updateOutput('video-task-output', `错误: ${imageValidation.message}`);
        return;
      }

      const data = await fetchJson('/api/video/create-task', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ payload }),
      });

      if (!data.ok) {
        updateOutput('video-task-output', `错误: ${data.error}\n${data.detail || ''}`);
        return;
      }

      const output = data.result?.output || data.result || {};
      recordCostMeta(data.result?.meta);
      const video = resetVideoRunState({ preservePrompt: true, preserveScript: true, preserveSegments: false });
      video.prompt = payload.prompt;
      video.image_url = payload.image_url;
      video.start_image_url = payload.start_image_url;
      video.end_image_url = payload.end_image_url;
      video.audio_url = audioUrl;
      video.audio_mix_url = '';
      video.audio_mix_source_url = '';
      video.task_id = output.task_id || output.request_id || '';
      video.task_status = output.task_status || output.status || 'PENDING';
      video.auto_poll = Boolean(bind('video-auto-poll')?.checked);
      saveState();

      if (bind('video-long-output')) updateOutput('video-long-output', '');
      updateOutput('video-task-output', `任务已创建\nTask ID: ${video.task_id}\n状态: ${video.task_status}`);

      if (video.auto_poll && video.task_id) {
        startVideoPolling();
        queryVideoTaskOnce({ silent: true }).catch((err) => {
          updateOutput('video-task-output', `错误: ${err.message}`);
          stopVideoPolling(false);
        });
      }
    });
  }

  const btnCreateLong = bind('btn-video-create-long');
  if (btnCreateLong) {
    btnCreateLong.addEventListener('click', async () => {
      const basePrompt = bind('video-prompt')?.value.trim() || '';
      const model = bind('video-model')?.value.trim() || 'viduq3-turbo';
      const size = bind('video-size')?.value.trim() || '1280*720';
      const totalDuration = Number(bind('video-total-duration')?.value || 0);
      const segmentDuration = Number(bind('video-duration-task')?.value || 10);

      if (!basePrompt) {
        updateOutput('video-long-output', '请先填写视频提示词。');
        return;
      }
      if (!totalDuration || totalDuration <= 0) {
        updateOutput('video-long-output', '请填写大于 0 的总时长（秒）。');
        return;
      }
      if (totalDuration <= 10) {
        updateOutput('video-long-output', '总时长不大于 10 秒时，请直接使用“创建视频任务”按钮。');
        return;
      }

      updateOutput('video-long-output', '正在创建长视频拆段任务...');

      const payload = {
        prompt: basePrompt,
        model,
        size,
        image_url: bind('video-image-url')?.value.trim() || '',
        start_image_url: bind('video-start-image-url')?.value.trim() || '',
        end_image_url: bind('video-end-image-url')?.value.trim() || '',
        audio_url: bind('video-audio-url')?.value.trim() || '',
        total_duration: totalDuration,
        segment_duration: segmentDuration,
        prompt_extend: true,
        provider: currentProvider,
      };
      payload.video_mode = detectVideoMode(payload.image_url, payload.start_image_url, payload.end_image_url);

      const imageValidation = validateImageUrlsForTask(payload.image_url, payload.start_image_url, payload.end_image_url);
      if (!imageValidation.ok) {
        updateOutput('video-long-output', `错误: ${imageValidation.message}`);
        return;
      }

      try {
        const data = await fetchJson('/api/video/create-long-task', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ payload }),
        });

        if (!data.ok) {
          updateOutput('video-long-output', `错误: ${data.error}\n${data.detail || ''}`);
          return;
        }

        const normalizedVideo = normalizeVideoState({
          prompt: basePrompt,
          long_segments: data.result?.segments || [],
          total_duration: data.result?.total_duration || totalDuration,
          filename_prefix: bind('video-filename-prefix')?.value.trim() || '',
        });
        recordCostMeta(data.result?.meta);
        const video = resetVideoRunState({ preservePrompt: true, preserveScript: true, preserveSegments: false });
        video.prompt = normalizedVideo.prompt;
        video.image_url = payload.image_url;
        video.start_image_url = payload.start_image_url;
        video.end_image_url = payload.end_image_url;
        video.audio_url = payload.audio_url;
        video.audio_mix_url = '';
        video.audio_mix_source_url = '';
        video.long_segments = normalizedVideo.long_segments;
        video.total_duration = normalizedVideo.total_duration;
        video.filename_prefix = normalizedVideo.filename_prefix;
        saveState();

        if (bind('video-task-output')) updateOutput('video-task-output', '');

        let text = `长视频拆段任务已创建。\n总时长: ${video.total_duration} 秒`;
        if (video.long_segments.length) {
          text += `\n共拆分为 ${video.long_segments.length} 段：`;
          video.long_segments.forEach((segment) => {
            text += `\n- 第${segment.index}段: 时长 ${segment.duration} 秒, Task ID: ${segment.task_id || '-'}\n  提示词: ${String(segment.prompt || '').slice(0, 120)}...`;
          });
          text += '\n\n可以使用下方“查询任务状态”按 Task ID 查询单段状态，或在控制台查看任务详情。';
        }

        updateOutput('video-long-output', text);
        renderLongSegmentsList();
      } catch (err) {
        updateOutput('video-long-output', `错误: ${err.message}`);
      }
    });
  }

  const btnRefresh = bind('btn-video-refresh');
  if (btnRefresh) {
    btnRefresh.addEventListener('click', async () => {
      await queryVideoTaskOnce();
    });
  }

  const autoPollCheck = bind('video-auto-poll');
  if (autoPollCheck) {
    autoPollCheck.addEventListener('change', () => {
      const video = getVideoState();
      video.auto_poll = autoPollCheck.checked;
      saveState();
      if (!video.auto_poll) {
        stopVideoPolling(false);
      } else if (video.task_id && !['SUCCEEDED', 'FAILED', 'CANCELED'].includes(video.task_status || '')) {
        startVideoPolling();
      }
    });
  }

  const btnStopPoll = bind('btn-video-stop-poll');
  if (btnStopPoll) {
    btnStopPoll.addEventListener('click', () => {
      stopVideoPolling(true);
    });
  }
}

async function initProjectContext() {
  try {
    await ensureProjectExistsAndLoad();
  } catch (err) {
    console.error('init project context failed', err);
  }
}

function renderTaskMetaLegacy(meta) {
  const panel = bind('task-meta-panel');
  const content = bind('task-meta-content');
  if (!panel || !content || !meta) {
    return;
  }

  const formatCost = (cost) => {
    if (typeof cost === 'number') {
      return `¥${cost.toFixed(4)}`;
    }
    return cost || '-';
  };

  const formatDuration = (duration) => {
    if (typeof duration === 'number') {
      return `${duration.toFixed(1)}秒`;
    }
    return duration || '-';
  };

  const items = [
    { label: '预估成本', value: formatCost(meta.estimated_cost) },
    { label: '实际成本', value: formatCost(meta.actual_cost) },
    { label: '重试次数', value: meta.retry_count || 0 },
    { label: '主模型', value: meta.primary_model || '-' },
    { label: '最终模型', value: meta.final_model || '-' },
    { label: '是否降级', value: meta.fallback_triggered ? '是' : '否' },
    { label: '预估时长', value: formatDuration(meta.estimated_duration) },
  ];

  content.innerHTML = items
    .map((item) => `<div class="meta-item"><span class="meta-label">${item.label}:</span> <span class="meta-value">${item.value}</span></div>`)
    .join('');
  panel.style.display = 'block';
}

function setTaskMetaExpanded(expanded, { persist = true } = {}) {
  state.task_meta_expanded = Boolean(expanded);
  const content = bind('task-meta-content');
  const button = bind('btn-task-meta-toggle');
  if (content) {
    content.style.display = state.task_meta_expanded ? 'grid' : 'none';
  }
  if (button) {
    button.textContent = state.task_meta_expanded ? '收起' : '成本预估';
  }
  if (persist) {
    saveState();
  }
}

function renderTaskMeta(meta, opts = {}) {
  const panel = bind('task-meta-panel');
  const content = bind('task-meta-content');
  if (!panel || !content || !meta) {
    return;
  }
  const normalizedMeta = normalizeTaskMeta(meta);
  if (!normalizedMeta) {
    return;
  }
  if (opts.persist !== false) {
    state.task_meta = normalizedMeta;
  }

  const formatCost = (cost) => (typeof cost === 'number' ? `¥${cost.toFixed(4)}` : (cost || '-'));
  const formatDuration = (duration) => (typeof duration === 'number' ? `${duration.toFixed(1)} 秒` : (duration || '-'));
  const items = [
    { label: '预估成本', value: formatCost(normalizedMeta.estimated_cost) },
    { label: '实际成本', value: formatCost(normalizedMeta.actual_cost) },
    { label: '重试次数', value: normalizedMeta.retry_count || 0 },
    { label: '主模型', value: normalizedMeta.primary_model || '-' },
    { label: '最终模型', value: normalizedMeta.final_model || '-' },
    { label: '是否降级', value: normalizedMeta.fallback_triggered ? '是' : '否' },
    { label: '预估时长', value: formatDuration(normalizedMeta.estimated_duration) },
  ];

  content.innerHTML = items
    .map((item) => `<div class="meta-item"><span class="meta-label">${item.label}:</span> <span class="meta-value">${item.value}</span></div>`)
    .join('');
  panel.style.display = 'block';
  setTaskMetaExpanded(state.task_meta_expanded, { persist: false });
  if (opts.persist !== false) {
    saveState();
  }
}

function bindTaskMetaActions() {
  const button = bind('btn-task-meta-toggle');
  if (!button) {
    return;
  }
  button.addEventListener('click', () => {
    setTaskMetaExpanded(!state.task_meta_expanded);
  });
}

function costStageLabel(stage) {
  const labels = {
    story_engine: '故事引擎',
    story_review: '评分',
    story_rewrite: '改稿',
    title_packaging: '标题包装',
    cover_packaging: '封面策划',
    cover_image_generate: '封面生图',
    video_generate: '视频生成',
    workshop: '剧本工坊',
    storyboard: '分镜工厂',
    command: '智能命令',
    global_router: '全局路由',
  };
  return labels[stage] || stage || '-';
}

function formatMoney(value) {
  const num = Number(value || 0);
  return `¥${num.toFixed(4)}`;
}

function formatUnitCost(value) {
  const num = Number(value || 0);
  if (!num) {
    return '-';
  }
  return `¥${num.toFixed(6)}`;
}

function formatMillionTokenPrice(value) {
  const num = Number(value || 0);
  if (!num) {
    return '-';
  }
  return `¥${num.toFixed(2)}/百万Tokens`;
}

function formatVideoCostLines(record) {
  if (record.cost_type !== 'video') {
    return '';
  }
  return `
          <div>视频规格：${record.video_size || '-'} / ${record.video_with_reference ? '有参考图' : '无参考图'}</div>
          <div>视频时长：${record.video_duration || record.estimated_duration || '-'} 秒</div>
          <div>视频单价：${record.video_price_per_second ? `¥${record.video_price_per_second.toFixed(4)}/秒` : '-'}</div>
  `;
}

function formatImageCostLines(record) {
  if (record.cost_type !== 'image') {
    return '';
  }
  return `
          <div>图片规格：${record.image_size || '-'}</div>
          <div>图片数量：${record.image_count || '-'}</div>
          <div>图片单价：${record.image_price_per_task ? `¥${record.image_price_per_task.toFixed(4)}/张` : '-'}</div>
  `;
}

function formatTokenCostLines(record) {
  if (record.cost_type && record.cost_type !== 'text') {
    return '';
  }
  return `
          <div>Tokens：${record.estimated_tokens || '-'}（输入 ${record.prompt_tokens || '-'} / 输出 ${record.completion_tokens || '-'}）</div>
          ${record.cache_hit_tokens ? `<div>缓存：命中 ${record.cache_hit_tokens} / 未命中 ${record.cache_miss_tokens || '-'}</div>` : ''}
          <div>输入价：${formatMillionTokenPrice(record.input_price_per_1m_tokens)} | 输出价：${formatMillionTokenPrice(record.output_price_per_1m_tokens)}</div>
          ${record.cache_hit_tokens ? `<div>缓存命中输入价：${formatMillionTokenPrice(record.input_cache_hit_price_per_1m_tokens)}</div>` : ''}
          <div>综合单价：${record.cost_per_1k_tokens ? `${formatUnitCost(record.cost_per_1k_tokens)}/千Tokens` : '-'}</div>
  `;
}

function shouldRecordCostMeta(meta) {
  if (!meta || typeof meta !== 'object') {
    return false;
  }
  return [
    'story_engine',
    'story_review',
    'story_rewrite',
    'title_packaging',
    'cover_packaging',
    'cover_image_generate',
    'video_generate',
    'workshop',
    'storyboard',
    'command',
    'global_router',
  ].includes(toText(meta.stage));
}

function costRecordAmount(record) {
  return Number(record.actual_cost || record.estimated_cost || 0);
}

function getCostTotal() {
  return normalizeCostRecords(state.cost_records).reduce((sum, record) => sum + costRecordAmount(record), 0);
}

function recordCostMeta(meta) {
  if (!shouldRecordCostMeta(meta)) {
    return;
  }
  const normalizedMeta = normalizeTaskMeta(meta);
  if (!normalizedMeta) {
    return;
  }

  const record = normalizeCostRecord({
    ...normalizedMeta,
    id: `cost_${Date.now()}_${Math.random().toString(16).slice(2)}`,
    time: new Date().toLocaleString(),
  });
  if (!record) {
    return;
  }

  state.cost_records = normalizeCostRecords([...(state.cost_records || []), record]);
  saveState();
  renderCostWidget();
}

function clearCostRecords() {
  const records = normalizeCostRecords(state.cost_records);
  if (!records.length) {
    return;
  }
  const confirmed = window.confirm('确定清空当前项目的成本记录吗？');
  if (!confirmed) {
    return;
  }
  state.cost_records = [];
  saveState();
  renderCostWidget();
  renderBillingPage();
}

function setCostPanelExpanded(expanded, { persist = true } = {}) {
  state.cost_panel_expanded = Boolean(expanded);
  const panel = bind('cost-widget-detail');
  const toggle = bind('cost-widget-toggle');
  if (panel) {
    panel.style.display = state.cost_panel_expanded ? 'block' : 'none';
  }
  if (toggle) {
    toggle.setAttribute('aria-expanded', String(state.cost_panel_expanded));
  }
  if (persist) {
    saveState();
  }
}

function getBillingSummary() {
  const records = normalizeCostRecords(state.cost_records);
  const summary = {
    total: 0,
    text: 0,
    image: 0,
    video: 0,
    count: records.length,
    last_used: records.length ? records[0].time || '' : '',
  };
  records.forEach((record) => {
    const amount = costRecordAmount(record);
    summary.total += amount;
    if (record.cost_type === 'image') {
      summary.image += amount;
    } else if (record.cost_type === 'video') {
      summary.video += amount;
    } else {
      summary.text += amount;
    }
  });
  return summary;
}

function getBillingStageSummary() {
  const stageMap = new Map();
  normalizeCostRecords(state.cost_records).forEach((record) => {
    const stage = costStageLabel(record.stage);
    const amount = costRecordAmount(record);
    stageMap.set(stage, (stageMap.get(stage) || 0) + amount);
  });
  return [...stageMap.entries()]
    .map(([label, amount]) => ({ label, amount }))
    .filter((item) => item.amount > 0)
    .sort((a, b) => b.amount - a.amount);
}

function renderBillingCharts(summary) {
  const pieRoot = bind('billing-pie-chart');
  const barRoot = bind('billing-bar-chart');
  if (!pieRoot || !barRoot) {
    return;
  }

  if (!summary.total) {
    pieRoot.innerHTML = '<p class="hint">暂无成本数据。</p>';
    barRoot.innerHTML = '<p class="hint">暂无阶段成本数据。</p>';
    return;
  }

  const typeItems = [
    { label: '文本模型', amount: summary.text, color: '#4f9d69' },
    { label: '图像模型', amount: summary.image, color: '#d58b35' },
    { label: '视频模型', amount: summary.video, color: '#5778c8' },
  ];
  let cursor = 0;
  const gradientStops = typeItems.map((item) => {
    const start = cursor;
    const end = cursor + (item.amount / summary.total) * 360;
    cursor = end;
    return `${item.color} ${start.toFixed(2)}deg ${end.toFixed(2)}deg`;
  });

  pieRoot.innerHTML = `
    <div class="billing-pie-wrap">
      <div class="billing-pie" style="--billing-pie-gradient: conic-gradient(${gradientStops.join(', ')});">
        <strong>${formatMoney(summary.total)}</strong>
        <span>总成本</span>
      </div>
      <div class="billing-legend">
        ${typeItems.map((item) => `
          <div class="billing-legend-item">
            <span class="billing-legend-dot" style="background:${item.color};"></span>
            <strong>${item.label}</strong>
            <span>${formatMoney(item.amount)}</span>
          </div>
        `).join('')}
      </div>
    </div>
  `;

  const stageItems = getBillingStageSummary().slice(0, 8);
  const maxAmount = stageItems[0]?.amount || 1;
  barRoot.innerHTML = stageItems.length
    ? stageItems.map((item) => {
      const width = Math.max(4, (item.amount / maxAmount) * 100);
      return `
        <div class="billing-bar-row">
          <div class="billing-bar-meta">
            <strong>${item.label}</strong>
            <span>${formatMoney(item.amount)}</span>
          </div>
          <div class="billing-bar-track">
            <span style="width:${width.toFixed(2)}%;"></span>
          </div>
        </div>
      `;
    }).join('')
    : '<p class="hint">暂无阶段成本数据。</p>';
}

function renderBillingWallet() {
  const wallet = normalizeBillingWallet(state.billing_wallet);
  state.billing_wallet = wallet;

  const balanceRoot = bind('billing-wallet-balance');
  const statusRoot = bind('billing-interface-status');
  if (balanceRoot) {
    balanceRoot.textContent = `¥${wallet.balance.toFixed(2)}`;
  }
  if (statusRoot) {
    statusRoot.textContent = wallet.enabled
      ? '当前接口状态：测试付费接口已开通'
      : '当前接口状态：付费接口未开通';
  }
}

function addBillingBalance(amount) {
  const value = Number(amount || 0);
  if (!Number.isFinite(value) || value <= 0) {
    window.alert('请输入大于 0 的充值金额。');
    return;
  }
  const wallet = normalizeBillingWallet(state.billing_wallet);
  state.billing_wallet = {
    enabled: true,
    balance: wallet.balance + value,
  };
  saveState();
  renderBillingWallet();
}

function openBillingPaymentModal(amount) {
  const value = Number(amount || 0);
  if (!Number.isFinite(value) || value <= 0) {
    window.alert('请输入大于 0 的充值金额。');
    return;
  }
  pendingBillingRechargeAmount = value;
  const modal = bind('billing-payment-modal');
  const amountText = bind('billing-payment-amount');
  if (amountText) {
    amountText.textContent = `充值金额：¥${value.toFixed(2)}`;
  }
  if (modal) {
    modal.style.display = 'flex';
    modal.setAttribute('aria-hidden', 'false');
  }
}

function closeBillingPaymentModal() {
  const modal = bind('billing-payment-modal');
  if (modal) {
    modal.style.display = 'none';
    modal.setAttribute('aria-hidden', 'true');
  }
}

function completeBillingPayment() {
  const amount = pendingBillingRechargeAmount;
  pendingBillingRechargeAmount = 0;
  closeBillingPaymentModal();
  addBillingBalance(amount);
}

function renderBillingPage() {
  const summaryRoot = bind('billing-summary');
  const recordsRoot = bind('billing-records');
  const clearButton = bind('btn-billing-clear');
  if (!summaryRoot || !recordsRoot) {
    return;
  }

  const summary = getBillingSummary();
  if (clearButton) {
    clearButton.disabled = !summary.count;
  }
  summaryRoot.innerHTML = `
    <div class="billing-card-row">
      <div><strong>累计成本</strong><div>${formatMoney(summary.total)}</div></div>
      <div><strong>文本模型</strong><div>${formatMoney(summary.text)}</div></div>
      <div><strong>图像模型</strong><div>${formatMoney(summary.image)}</div></div>
      <div><strong>视频模型</strong><div>${formatMoney(summary.video)}</div></div>
      <div><strong>记录条数</strong><div>${summary.count}</div></div>
    </div>
  `;

  recordsRoot.innerHTML = summary.count
    ? normalizeCostRecords(state.cost_records)
      .slice()
      .reverse()
      .map((record) => `
          <article class="cost-record">
            <div class="cost-record-head">
              <strong>${costStageLabel(record.stage)}</strong>
              <span>${formatMoney(costRecordAmount(record))}</span>
            </div>
            <div>类型：${record.cost_type || 'text'}</div>
            <div>模型：${record.final_model || record.primary_model || '-'}</div>
            <div>实际：${formatMoney(record.actual_cost)} / 预估：${formatMoney(record.estimated_cost)}</div>
            <div class="hint">时间：${record.time || '-'}</div>
          </article>
        `)
      .join('')
    : '<p class="hint">当前没有成本记录，先在其他页面生成内容即可。</p>';

  renderBillingWallet();
  renderBillingCharts(summary);
}

function bindBillingActions() {
  bind('btn-billing-clear')?.addEventListener('click', clearCostRecords);
  bind('btn-billing-recharge')?.addEventListener('click', () => {
    openBillingPaymentModal(bind('billing-recharge-amount')?.value);
  });
  bind('btn-billing-test-add')?.addEventListener('click', () => {
    addBillingBalance(10);
  });
  bind('btn-billing-payment-close')?.addEventListener('click', closeBillingPaymentModal);
  bind('btn-billing-payment-done')?.addEventListener('click', completeBillingPayment);
  bind('billing-payment-modal')?.addEventListener('click', (event) => {
    if (event.target === event.currentTarget) {
      closeBillingPaymentModal();
    }
  });
  bind('btn-billing-enable')?.addEventListener('click', () => {
    const wallet = normalizeBillingWallet(state.billing_wallet);
    state.billing_wallet = {
      ...wallet,
      enabled: true,
    };
    saveState();
    renderBillingWallet();
    window.alert('测试付费接口已开通，当前仍为本地演示余额。');
  });
}

function renderCostWidget() {
  const total = bind('cost-widget-total');
  const list = bind('cost-widget-list');
  const clearButton = bind('btn-cost-clear');
  if (!total || !list) {
    return;
  }

  const records = normalizeCostRecords(state.cost_records);
  state.cost_records = records;
  total.textContent = formatMoney(getCostTotal());
  if (clearButton) {
    clearButton.disabled = !records.length;
  }

  if (!records.length) {
    list.innerHTML = '<p class="hint">暂无成本记录，生成内容后会自动记录。</p>';
  } else {
    list.innerHTML = records
      .slice()
      .reverse()
      .map((record) => `
        <article class="cost-record">
          <div class="cost-record-head">
            <strong>${costStageLabel(record.stage)}</strong>
            <span>${formatMoney(costRecordAmount(record))}</span>
          </div>
          <div>模型：${record.final_model || record.primary_model || '-'}</div>
          ${formatTokenCostLines(record)}
          ${formatVideoCostLines(record)}
          ${formatImageCostLines(record)}
          <div>预估耗时：${record.estimated_duration ? `${record.estimated_duration} 秒` : '-'}</div>
          ${record.cost_type === 'video' || record.cost_type === 'image' ? '' : `<div>输入成本：${formatMoney(record.input_cost)} | 输出成本：${formatMoney(record.output_cost)}</div>`}
          <div>预估：${formatMoney(record.estimated_cost)} | 实际：${formatMoney(record.actual_cost)}</div>
          <div>重试：${record.retry_count || 0} | 降级：${record.fallback_triggered ? '是' : '否'}</div>
          ${record.fallback_reason ? `<div>原因：${record.fallback_reason}</div>` : ''}
          <div class="hint">${record.time || '-'}</div>
        </article>
      `)
      .join('');
  }
  setCostPanelExpanded(state.cost_panel_expanded, { persist: false });
}

function initCostWidget() {
  if (bind('cost-widget') || !document.body) {
    renderCostWidget();
    return;
  }

  const root = document.createElement('aside');
  root.id = 'cost-widget';
  root.className = 'cost-widget';
  root.innerHTML = `
    <button id="cost-widget-toggle" class="cost-widget-toggle" type="button" aria-expanded="false">
      <span>当前成本</span>
      <strong id="cost-widget-total">¥0.0000</strong>
    </button>
    <div id="cost-widget-detail" class="cost-widget-detail" style="display:none;">
      <div class="cost-widget-detail-head">
        <strong>成本明细</strong>
        <div class="cost-widget-actions">
          <span class="hint">按最近使用倒序</span>
          <button id="btn-billing-center" class="secondary cost-widget-clear" type="button">查看账单中心</button>
          <button id="btn-cost-clear" class="secondary cost-widget-clear" type="button">清零</button>
        </div>
      </div>
      <div id="cost-widget-list" class="cost-widget-list"></div>
    </div>
  `;
  document.body.appendChild(root);

  bind('cost-widget-toggle')?.addEventListener('click', () => {
    setCostPanelExpanded(!state.cost_panel_expanded);
  });
  bind('btn-billing-center')?.addEventListener('click', () => {
    window.location.href = '/billing';
  });
  bind('btn-cost-clear')?.addEventListener('click', clearCostRecords);
  makeFloatingWidgetDraggable(root, bind('cost-widget-toggle'), 'cost_widget');
  renderCostWidget();
}

function bindContentPlayerActions() {
  document.querySelectorAll('[data-open-content-player]').forEach((button) => {
    button.addEventListener('click', () => {
      openContentPlayer(button.getAttribute('data-open-content-player'), button.getAttribute('data-player-title'));
    });
  });

  const closeButton = bind('btn-content-player-close');
  if (closeButton) {
    closeButton.addEventListener('click', closeContentPlayer);
  }

  const modal = bind('content-player-modal');
  if (modal) {
    modal.addEventListener('click', (event) => {
      if (event.target === modal) {
        closeContentPlayer();
      }
    });
  }
}

function removeLegacyGlobalCommandPanel() {
  const input = bind('command');
  if (!input) {
    return;
  }
  const section = input.closest('section.panel');
  if (section) {
    section.remove();
  }
}

async function initApp() {
  removeLegacyGlobalCommandPanel();
  bindProjectDrawerActions();
  initProjectDrawerDrag();
  bindEditProjectActions();
  bindTaskMetaActions();
  bindContentPlayerActions();
  initCostWidget();
  bindBillingActions();
  bindWorkshopActions();
  bindVisualActions();
  bindExportActions();
  bindVideoActions();
  initGlobalCommandWidget();

  await initProjectContext();
  await loadStoryTemplates();
  restoreOutputsOnPageLoad();
  refreshVisualEditors();
  loadProviders();
  renderBillingPage();
}

window.addEventListener('beforeunload', () => {
  if (!currentProjectId || !stateDirty) {
    return;
  }

  const body = JSON.stringify({
    state,
    last_provider: currentProvider,
    cover_image: currentProjectMeta?.cover_image || '',
  });

  try {
    navigator.sendBeacon(`/api/projects/${currentProjectId}/state`, new Blob([body], { type: 'application/json' }));
  } catch (err) {
    console.error('sendBeacon save failed', err);
  }
});

initApp();
