const STORAGE_KEY = 'ai_short_drama_state_v1';
const PROVIDER_KEY = 'ai_short_drama_provider_v1';
const CURRENT_PROJECT_KEY = 'ai_short_drama_current_project_id_v1';
const AUTO_SAVE_DELAY_MS = 3000;

const EMPTY_STATE = {
  story_card: null,
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
  };

  if (
    normalized.logline ||
    normalized.theme ||
    normalized.tone ||
    normalized.structure_template ||
    normalized.core_conflict ||
    normalized.anchor_points.length ||
    normalized.hook ||
    normalized.ending_type
  ) {
    return normalized;
  }
  return null;
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
let saveDebounceTimer = null;
let stateDirty = false;
let projectSaveInFlight = false;
let projectDrawerOpen = false;

let relationshipNetwork = null;
let timelineSortable = null;
let selectedRelationIndex = null;
let draftRelationNodes = [];
let visualUndoStack = [];
let videoPollTimer = null;
let providersList = [];
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

function normalizeState(input) {
  const parsed = (input && typeof input === 'object') ? input : {};
  return {
    story_card: normalizeStoryCard(parsed.story_card),
    workshop: normalizeWorkshopData(parsed.workshop),
    storyboard: normalizeStoryboardData(parsed.storyboard),
    video_lab: normalizeVideoState(parsed.video_lab),
  };
}

function applyState(newState) {
  const normalized = normalizeState(newState);
  state.story_card = normalized.story_card;
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

function clearOutputsByPage() {
  const ids = [
    'story-output',
    'workshop-output',
    'storyboard-output',
    'command-output',
    'export-output',
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
    card.addEventListener('click', async () => {
      const targetId = card.getAttribute('data-project-id');
      if (!targetId || String(targetId) === String(currentProjectId)) {
        return;
      }
      await switchProject(targetId);
    });
  });
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

  if (currentProjectMeta?.last_provider) {
    currentProvider = currentProjectMeta.last_provider;
    saveProvider(currentProvider);
  }

  clearOutputsByPage();
  restoreOutputsOnPageLoad();
  refreshVisualEditors();
  renderProjectMeta();
  await loadProjects();
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
    renderVideoResult(video.video_url);
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
  const resp = await fetch('/api/agent/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ stage, payload, provider: provider || currentProvider }),
  });
  return resp.json();
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

  return lines.join('\\n').trim();
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

  return lines.join('\\n').trim();
}

function bindWorkshopActions() {
  const btnStory = bind('btn-story');
  if (btnStory) {
    btnStory.addEventListener('click', async () => {
      updateOutput('story-output', '生成中...');
      const payload = {
        idea: bind('idea')?.value.trim() || '',
        theme: bind('theme')?.value.trim() || '',
        tone: bind('tone')?.value.trim() || '',
        structure: bind('structure')?.value.trim() || '',
      };

      const data = await runStage('story_engine', payload);
      if (!data.ok) {
        updateOutput('story-output', `错误: ${data.error}\n${data.detail || ''}`);
        return;
      }

      state.story_card = normalizeStoryCard(data.result.story_card);
      saveState();

      updateOutput('story-output', formatStoryResult(data.result));
    });
  }

  const btnStoryCompare = bind('btn-story-compare');
  if (btnStoryCompare) {
    btnStoryCompare.addEventListener('click', async () => {
      const payload = {
        idea: bind('idea')?.value.trim() || '',
        theme: bind('theme')?.value.trim() || '',
        tone: bind('tone')?.value.trim() || '',
        structure: bind('structure')?.value.trim() || '',
      };

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
        const formattedResult = formatStoryResult(result);
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
      refreshVisualEditors();
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
    });
  }

  const btnCommand = bind('btn-command');
  if (btnCommand) {
    btnCommand.addEventListener('click', async () => {
      updateOutput('command-output', '执行中...');
      const payload = {
        command: bind('command')?.value.trim() || '',
        project_state: {
          story_card: state.story_card,
          workshop: state.workshop,
          storyboard: state.storyboard,
        },
      };

      const data = await runStage('command', payload);
      if (!data.ok) {
        updateOutput('command-output', `错误: ${data.error}\n${data.detail || ''}`);
        return;
      }

      if (data.result.updated_state) {
        state.story_card = normalizeStoryCard(data.result.updated_state.story_card) || state.story_card;
        state.workshop = normalizeWorkshopData(data.result.updated_state.workshop) || state.workshop;
        state.storyboard = normalizeStoryboardData(data.result.updated_state.storyboard) || state.storyboard;
        saveState();
        refreshVisualEditors();
      }

      let cmdText = `【理解命令】\n${data.result.command_understanding || '-'}\n\n`;
      cmdText += `【一致性检查】\n`;
      if (data.result.consistency_report && data.result.consistency_report.length) {
        data.result.consistency_report.forEach(r => cmdText += `- ${r}\n`);
      } else {
        cmdText += '-\n';
      }
      cmdText += `\n【下一步建议】\n`;
      if (data.result.suggestions && data.result.suggestions.length) {
        data.result.suggestions.forEach(s => cmdText += `- ${s}\n`);
      } else {
        cmdText += '-\n';
      }
      updateOutput('command-output', cmdText.trim());
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

function buildExportPayload() {
  return {
    project: currentProjectMeta ? { ...currentProjectMeta } : null,
    current_provider: currentProvider,
    exported_at: new Date().toISOString(),
    story_card: normalizeStoryCard(state.story_card),
    workshop: normalizeWorkshopData(state.workshop),
    storyboard: normalizeStoryboardData(state.storyboard),
    video_lab: normalizeVideoState(getVideoState()),
  };
}


function restoreOutputsOnPageLoad() {
  if (bind('story-output') && state.story_card) {
    updateOutput('story-output', formatStoryResult({ story_card: state.story_card }));
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

  const video = getVideoState();
  if (bind('video-script-output') && video.script) {
    updateOutput('video-script-output', video.script);
  }
  if (bind('video-prompt') && video.prompt) {
    bind('video-prompt').value = video.prompt;
  }
  if (bind('video-task-output') && video.task_id) {
    updateOutput('video-task-output', `最近任务: ${video.task_id}\n状态: ${video.task_status || 'UNKNOWN'}`);
  }
  if (bind('video-auto-poll')) {
    bind('video-auto-poll').checked = Boolean(video.auto_poll);
  }
  if (video.video_url) {
    renderVideoResult(video.video_url);
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

  let html = '<h3>?????????</h3>';
  html += '<p class="hint">????????????????????????</p>';
  html += '<ul class="segment-list">';
  segments.forEach((seg) => {
    const shortPrompt = String(seg.prompt || '').slice(0, 60);
    html += `
      <li style="margin-bottom:8px;">
        <div><strong>? ${seg.index} ?</strong> | ?? ${seg.duration} ? | Task ID: ${seg.task_id || '-'} | ??: ${seg.task_status || 'PENDING'}</div>
        <div style="font-size:12px; color:var(--muted);">???: ${shortPrompt}${seg.prompt && seg.prompt.length > 60 ? '...' : ''}</div>
        ${seg.task_id ? `<button data-task-id="${seg.task_id}" data-index="${seg.index}" class="btn-seg-play">????????</button>` : ''}
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

      updateOutput('video-task-output', `????? ${idx} ??? ${taskId} ...`);

      try {
        const data = await fetchJson(`/api/video/task/${taskId}`, { method: 'GET' });
        if (!data.ok) {
          updateOutput('video-task-output', `??: ${data.error}
${data.detail || ''}`);
          return;
        }

        const output = data.result?.output || data.result || {};
        const status = output.task_status || output.status || 'UNKNOWN';
        const url = output.video_url || output.url || output?.result?.video?.url || '';

        updateOutput('video-task-output', `? ${idx} ??? ${taskId}
??: ${status}`);

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
          renderVideoResult(url);
        }
      } catch (err) {
        updateOutput('video-task-output', `??: ${err.message}`);
      }
    });
  });
}

async function fetchJson(url, options) {
  const resp = await fetch(url, options);
  const data = await resp.json();
  return data;
}

function extractPromptFromScript(scriptText) {
  const marker = '???????';
  const idx = scriptText.indexOf(marker);
  if (idx < 0) {
    return scriptText.slice(0, 600);
  }
  return scriptText.slice(idx).replace(/^.*?[:?]/, '').trim();
}

function bindExportActions() {
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

      const payload = {
        prompt: bind('video-prompt')?.value.trim() || '',
        model: bind('video-model')?.value.trim() || 'viduq3-turbo',
        size: bind('video-size')?.value.trim() || '1280*720',
        duration: Number(bind('video-duration-task')?.value || 10),
        prompt_extend: true,
        image_url: bind('video-image-url')?.value.trim() || '',
        start_image_url: bind('video-start-image-url')?.value.trim() || '',
        end_image_url: bind('video-end-image-url')?.value.trim() || '',
      };

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
      const video = resetVideoRunState({ preservePrompt: true, preserveScript: true, preserveSegments: false });
      video.prompt = payload.prompt;
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
        total_duration: totalDuration,
        segment_duration: segmentDuration,
        prompt_extend: true,
        provider: currentProvider,
      };

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
        const video = resetVideoRunState({ preservePrompt: true, preserveScript: true, preserveSegments: false });
        video.prompt = normalizedVideo.prompt;
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

async function initApp() {
  bindProjectDrawerActions();
  bindWorkshopActions();
  bindVisualActions();
  bindExportActions();
  bindVideoActions();

  await initProjectContext();
  restoreOutputsOnPageLoad();
  refreshVisualEditors();
  loadProviders();
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
