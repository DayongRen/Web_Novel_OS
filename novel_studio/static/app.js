/* ── Novel Studio Frontend ── */
const API = '';  // 同域，无需前缀

// ── 状态 ──────────────────────────────────────────────────────────────────────
const state = {
  currentPage: 'home',
  currentSession: null,
  currentProject: null,
  currentOptions: [],
  selectedOption: null,
  currentChapter: null,
  pendingTaskId: null,
  taskPollTimer: null,
};

// ── 路由 ──────────────────────────────────────────────────────────────────────
function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  const page = document.getElementById(`page-${name}`);
  if (page) page.classList.add('active');
  const btn = document.querySelector(`.nav-btn[data-page="${name}"]`);
  if (btn) btn.classList.add('active');
  state.currentPage = name;
  if (name === 'home') loadRecentProjects();
  if (name === 'projects') loadProjectsPage();
  if (name === 'sessions') loadSessionsPage();
  if (name === 'health') loadHealthPage();
  if (name === 'write') loadWritePage();
}

// ── API 助手 ──────────────────────────────────────────────────────────────────
async function api(method, path, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const r = await fetch(API + path, opts);
  if (!r.ok) {
    const txt = await r.text();
    throw new Error(`${r.status}: ${txt}`);
  }
  return r.json();
}
const get = path => api('GET', path);
const post = (path, body) => api('POST', path, body);

function setStatus(msg, color = 'green') {
  document.getElementById('status-text').textContent = msg;
  const dot = document.getElementById('status-dot');
  dot.className = `dot ${color}`;
}

function toast(msg, type = 'success') {
  const c = document.getElementById('toast-container');
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

// ── 首页 ──────────────────────────────────────────────────────────────────────
async function loadRecentProjects() {
  try {
    const { projects } = await get('/api/projects');
    const container = document.getElementById('recent-list');
    if (!projects.length) {
      container.innerHTML = '<p style="color:var(--text3);font-size:13px">还没有项目，点击上方卡片新建</p>';
      return;
    }
    container.innerHTML = projects.slice(0, 6).map(p => {
      const pct = Math.min(100, Math.round((p.current_words || 0) / (p.target_words || 1) * 100));
      return `
      <div class="project-item" onclick="openProject('${p.project_id}')">
        <div class="project-item-name">${p.name}</div>
        <div class="project-item-meta">${p.genre} · ${(p.current_words||0).toLocaleString()}字 · ${p.current_chapters||0}章</div>
        <div class="project-item-progress"><div class="project-item-bar" style="width:${pct}%"></div></div>
      </div>`;
    }).join('');
  } catch(e) { console.error(e); }
}

// ── 任务卡点击 ────────────────────────────────────────────────────────────────
document.querySelectorAll('.task-card').forEach(card => {
  card.addEventListener('click', () => handleTaskAction(card.dataset.action));
});

function handleTaskAction(action) {
  if (action === 'new-project') openNewProjectModal();
  else if (action === 'continue-project') showPage('projects');
  else if (action === 'gen-options') openNewProjectModal('options');
  else if (action === 'write-chapters') showPage('write');
  else if (action === 'check-health') showPage('health');
  else if (action === 'rewrite-chapter') showPage('write');
}

// ── 新建项目模态框 ─────────────────────────────────────────────────────────────
async function openNewProjectModal(afterCreate) {
  await loadGenreOptions();
  document.getElementById('modal-new-project').style.display = 'flex';
  document.getElementById('confirm-new-project').dataset.afterCreate = afterCreate || 'dialogue';
}

async function loadGenreOptions() {
  try {
    const { genres } = await get('/api/genres');
    const sel = document.getElementById('np-genre');
    sel.innerHTML = genres.map(g =>
      `<option value="${g.id}">${g.display_name} (${g.target_gender}/${g.typical_length})</option>`
    ).join('');
  } catch(e) {}
}

document.getElementById('close-new-project').addEventListener('click', closeNewProjectModal);
document.getElementById('cancel-new-project').addEventListener('click', closeNewProjectModal);
function closeNewProjectModal() {
  document.getElementById('modal-new-project').style.display = 'none';
}

document.getElementById('confirm-new-project').addEventListener('click', async () => {
  const name = document.getElementById('np-name').value.trim();
  const idea = document.getElementById('np-idea').value.trim();
  const genre = document.getElementById('np-genre').value;
  const words = parseInt(document.getElementById('np-words').value);
  const chapters = parseInt(document.getElementById('np-chapters').value);
  const platform = document.getElementById('np-platform').value;
  const afterCreate = document.getElementById('confirm-new-project').dataset.afterCreate || 'dialogue';

  if (!name || !idea) { toast('请填写项目名称和想法', 'warn'); return; }
  setStatus('创建项目…', 'yellow');
  try {
    const project = await post('/api/projects/create', { name, idea, genre, target_words: words, target_chapters: chapters, platform });
    state.currentProject = project;
    closeNewProjectModal();
    toast(`项目「${name}」已创建`);
    setStatus('就绪', 'green');

    const session = await post('/api/sessions/create', {
      project_id: project.project_id,
      initial_idea: idea,
      task_type: afterCreate === 'options' ? 'options' : 'full_flow',
    });
    state.currentSession = session;

    if (afterCreate === 'options') {
      await startGenerateOptions(session.session_id);
    } else {
      await startDialogue(session.session_id);
    }
  } catch(e) {
    toast('创建失败: ' + e.message, 'error');
    setStatus('就绪', 'green');
  }
});

// ── 对话式引导 ─────────────────────────────────────────────────────────────────
async function startDialogue(sessionId) {
  showPage('dialogue');
  document.getElementById('dialogue-title').textContent = '创意引导';
  document.getElementById('chat-window').innerHTML = '';
  document.getElementById('option-cards').innerHTML = '';
  document.getElementById('chat-input-area').style.display = 'none';
  document.getElementById('generate-cta').style.display = 'none';

  setStatus('引导中…', 'yellow');
  try {
    const turn = await post(`/api/sessions/${sessionId}/dialogue/start`);
    renderSystemTurn(turn, sessionId);
    setStatus('就绪', 'green');
  } catch(e) {
    toast('引导失败: ' + e.message, 'error');
    setStatus('就绪', 'green');
  }
}

function renderSystemTurn(turn, sessionId) {
  const win = document.getElementById('chat-window');

  const badge = document.getElementById('phase-badge');
  const phaseLabels = {
    story_focus: '故事重心', protagonist: '主角设定', antagonist: '反派/阻力',
    opening_style: '开局风格', pacing_preference: '节奏偏好', world_depth: '世界观深度',
    ready: '就绪'
  };
  badge.textContent = phaseLabels[turn.phase] || turn.phase;

  const msgEl = document.createElement('div');
  msgEl.className = 'chat-msg system';
  msgEl.innerHTML = `
    <div class="msg-context">${turn.context || ''}</div>
    <div class="msg-bubble">
      <div class="msg-question">${turn.question}</div>
    </div>`;
  win.appendChild(msgEl);
  win.scrollTop = win.scrollHeight;

  updateCollectedDisplay(turn.collected_so_far || {});

  if (turn.phase === 'ready') {
    document.getElementById('chat-input-area').style.display = 'none';
    document.getElementById('generate-cta').style.display = 'block';
    return;
  }

  const optCards = document.getElementById('option-cards');
  optCards.innerHTML = (turn.options || []).map(opt => `
    <div class="option-card" data-id="${opt.id}" onclick="selectOption(this, '${opt.id}')">
      <div class="option-card-id">${opt.id}</div>
      <div class="option-card-label">${opt.label}</div>
      <div class="option-card-desc">${opt.description || ''}</div>
      ${opt.pros ? `<div class="option-card-pros">✓ ${opt.pros}</div>` : ''}
      ${opt.cons ? `<div class="option-card-cons">△ ${opt.cons}</div>` : ''}
    </div>`).join('');

  document.getElementById('chat-input-area').style.display = 'block';
  document.getElementById('generate-cta').style.display = 'none';

  document.getElementById('btn-send').onclick = () => submitDialogueResponse(sessionId, turn);
  document.getElementById('custom-input').onkeydown = e => {
    if (e.key === 'Enter') submitDialogueResponse(sessionId, turn);
  };
}

function selectOption(el, id) {
  document.querySelectorAll('.option-card').forEach(c => c.classList.remove('selected'));
  el.classList.add('selected');
}

async function submitDialogueResponse(sessionId, lastTurn) {
  const selected = document.querySelector('.option-card.selected');
  const customText = document.getElementById('custom-input').value.trim();
  if (!selected && !customText) { toast('请选择一个选项或输入想法', 'warn'); return; }

  const choiceId = selected ? selected.dataset.id : null;
  const userLabel = selected
    ? `${choiceId}: ${selected.querySelector('.option-card-label').textContent}`
    : customText;

  const win = document.getElementById('chat-window');
  const userMsg = document.createElement('div');
  userMsg.className = 'chat-msg user';
  userMsg.innerHTML = `<div class="msg-bubble">${userLabel}</div>`;
  win.appendChild(userMsg);
  win.scrollTop = win.scrollHeight;

  document.getElementById('chat-input-area').style.display = 'none';
  document.getElementById('custom-input').value = '';

  setStatus('思考下一个问题…', 'yellow');
  try {
    const next = await post(`/api/sessions/${sessionId}/dialogue/respond`, {
      choice_id: choiceId, custom_text: customText || null,
    });
    renderSystemTurn(next, sessionId);
    setStatus('就绪', 'green');
  } catch(e) {
    toast('出错: ' + e.message, 'error');
    setStatus('就绪', 'green');
    document.getElementById('chat-input-area').style.display = 'block';
  }
}

function updateCollectedDisplay(collected) {
  const container = document.getElementById('collected-display');
  const phaseLabels = {
    story_focus: '故事重心', protagonist: '主角', antagonist: '反派/阻力',
    opening_style: '开局风格', pacing_preference: '节奏', world_depth: '世界观'
  };
  container.innerHTML = Object.entries(collected).map(([phase, val]) => {
    const label = phaseLabels[phase] || phase;
    const display = typeof val === 'object' ? (val.label || JSON.stringify(val)) : String(val);
    return `<div class="collected-item">
      <div class="collected-phase">${label}</div>
      <div class="collected-value">${display}</div>
    </div>`;
  }).join('') || '<p style="color:var(--text3);font-size:12px">引导完成后将在此显示</p>';
}

// 返回按钮
document.getElementById('back-from-dialogue').addEventListener('click', () => showPage('home'));

// 就绪时的生成按钮
document.getElementById('btn-gen-bible').addEventListener('click', async () => {
  if (!state.currentSession) return;
  setStatus('生成故事圣经…', 'yellow');
  showPage('sessions');
  const { task_id } = await post(`/api/sessions/${state.currentSession.session_id}/generate`, {
    task: 'bible', params: {}
  });
  toast('故事圣经生成中，请稍候');
  pollTask(task_id, 'bible 生成完成！');
});

document.getElementById('btn-gen-options').addEventListener('click', async () => {
  if (!state.currentSession) return;
  await startGenerateOptions(state.currentSession.session_id);
});

// ── 方案候选 ──────────────────────────────────────────────────────────────────
async function startGenerateOptions(sessionId) {
  showPage('options');
  document.getElementById('options-loading').style.display = 'block';
  document.getElementById('options-grid').style.display = 'none';
  document.getElementById('options-actions').style.display = 'none';

  setStatus('生成候选方案…', 'yellow');
  try {
    const { task_id } = await post(`/api/sessions/${sessionId}/generate`, {
      task: 'options', params: { task: '故事框架', n: 3 }
    });
    pollTask(task_id, '候选方案已生成', async () => {
      await loadOptionsFromSession(sessionId);
    });
  } catch(e) {
    toast('生成失败: ' + e.message, 'error');
    setStatus('就绪', 'green');
  }
}

async function loadOptionsFromSession(sessionId) {
  try {
    const { content } = await get(`/api/sessions/${sessionId}/file?path=generated/concept_options_raw.json`);
    const options = JSON.parse(content);
    renderOptions(options, sessionId);
  } catch(e) {
    try {
      const { content } = await get(`/api/sessions/${sessionId}/file?path=generated/concept_options.md`);
      renderOptionsFallback(content, sessionId);
    } catch(e2) {
      toast('读取方案失败', 'error');
    }
  }
  document.getElementById('options-loading').style.display = 'none';
  document.getElementById('options-grid').style.display = 'grid';
  document.getElementById('options-actions').style.display = 'flex';
  setStatus('就绪', 'green');
}

function renderOptions(options, sessionId) {
  state.currentOptions = options;
  const grid = document.getElementById('options-grid');
  grid.innerHTML = options.map((opt, i) => `
    <div class="option-block" data-idx="${i}" onclick="selectOptionBlock(this, ${i})">
      <div class="option-block-id">${opt.option_id || '方案' + (i+1)}</div>
      <div class="option-block-title">${opt.title || ''}</div>
      <div class="option-block-summary">${opt.summary || ''}</div>
      <ul class="option-block-features">${(opt.key_features||[]).map(f => `<li>${f}</li>`).join('')}</ul>
      <div class="pros-cons">
        ${opt.pros ? `<div class="pros">✓ ${opt.pros}</div>` : ''}
        ${opt.cons ? `<div class="cons">△ ${opt.cons}</div>` : ''}
      </div>
      <div class="option-block-content">${opt.content || ''}</div>
    </div>`).join('');
}

function renderOptionsFallback(md, sessionId) {
  const grid = document.getElementById('options-grid');
  grid.innerHTML = `<div style="grid-column:1/-1;white-space:pre-wrap;font-size:13px;color:var(--text2)">${md}</div>`;
}

function selectOptionBlock(el, idx) {
  document.querySelectorAll('.option-block').forEach(b => b.classList.remove('selected'));
  el.classList.add('selected');
  state.selectedOption = idx;
}

document.getElementById('back-from-options').addEventListener('click', () => showPage('home'));
document.getElementById('btn-regen-options').addEventListener('click', async () => {
  if (state.currentSession) await startGenerateOptions(state.currentSession.session_id);
});

document.getElementById('btn-accept-option').addEventListener('click', async () => {
  if (state.selectedOption === null) { toast('请先选择一个方案', 'warn'); return; }
  const opt = state.currentOptions[state.selectedOption];
  if (!opt) return;
  const sessionId = state.currentSession?.session_id;
  if (!sessionId) return;
  const content = opt.content || JSON.stringify(opt, null, 2);
  const filename = `concept_options.md`;
  toast(`方案「${opt.title}」已选中，开始生成故事圣经`);
  showPage('sessions');
  const { task_id } = await post(`/api/sessions/${sessionId}/generate`, { task: 'bible', params: {} });
  pollTask(task_id, '故事圣经生成完成！');
});

document.getElementById('btn-merge-options').addEventListener('click', () => {
  document.getElementById('merge-panel').style.display = 'block';
});

document.getElementById('btn-submit-merge').addEventListener('click', async () => {
  const text = document.getElementById('merge-input').value.trim();
  if (!text || !state.currentSession) return;
  const session = await post(`/api/sessions/create`, {
    project_id: state.currentSession.project_id,
    initial_idea: `融合指令: ${text}\n\n原始想法: ${state.currentSession.initial_idea}`,
    task_type: 'full_flow',
  });
  state.currentSession = session;
  document.getElementById('merge-panel').style.display = 'none';
  await startGenerateOptions(session.session_id);
});

// ── 项目列表页 ────────────────────────────────────────────────────────────────
async function loadProjectsPage() {
  const { projects } = await get('/api/projects');
  const grid = document.getElementById('projects-grid');
  if (!projects.length) {
    grid.innerHTML = '<p style="color:var(--text3);padding:40px">还没有项目</p>';
    return;
  }
  grid.innerHTML = projects.map(p => {
    const pct = Math.min(100, Math.round((p.current_words||0) / (p.target_words||1) * 100));
    return `
    <div class="project-card" onclick="openProject('${p.project_id}')">
      <div class="project-card-name">${p.name}</div>
      <div class="project-card-genre">${p.genre}</div>
      <div class="project-card-stats">
        <div class="stat-item"><span class="stat-value">${(p.current_words||0).toLocaleString()}</span><span>已写字数</span></div>
        <div class="stat-item"><span class="stat-value">${p.current_chapters||0}</span><span>章节</span></div>
        <div class="stat-item"><span class="stat-value">${pct}%</span><span>完成度</span></div>
      </div>
      <div class="progress-bar"><div class="progress-bar-fill" style="width:${pct}%"></div></div>
      <div class="project-card-date">创建于 ${(p.created_at||'').slice(0,10)}</div>
    </div>`;
  }).join('');
}

document.getElementById('btn-new-project-2').addEventListener('click', () => openNewProjectModal());

function openProject(projectId) {
  state.currentProject = { project_id: projectId };
  showPage('write');
}

// ── 写作页 ────────────────────────────────────────────────────────────────────
async function loadWritePage() {
  const { projects } = await get('/api/projects');
  const selects = ['project-select'];
  selects.forEach(selId => {
    const sel = document.getElementById(selId);
    if (!sel) return;
    sel.innerHTML = projects.map(p => `<option value="${p.project_id}">${p.name}</option>`).join('');
    if (state.currentProject) sel.value = state.currentProject.project_id;
    sel.onchange = () => { state.currentProject = { project_id: sel.value }; loadChapterList(); };
  });
  if (projects.length) loadChapterList();
}

async function loadChapterList() {
  if (!state.currentProject) return;
  const { files } = await get(`/api/projects/${state.currentProject.project_id}/files`);
  const chapters = files.filter(f => f.type === 'chapter' && f.path.includes('ch'));
  const list = document.getElementById('chapter-list');
  if (!chapters.length) {
    list.innerHTML = '<div style="padding:20px;color:var(--text3);font-size:12px">尚无章节，点击"写下一章"开始</div>';
    return;
  }
  list.innerHTML = chapters.map(f => {
    const m = f.path.match(/ch(\d+)/);
    const num = m ? parseInt(m[1]) : 0;
    return `<div class="chapter-item" onclick="loadChapter('${f.path}', ${num})">
      <div class="chapter-item-num">第 ${num} 章</div>
      <div class="chapter-item-title">${f.path.split('/').pop().replace('.md','')}</div>
    </div>`;
  }).join('');
}

async function loadChapter(path, num) {
  if (!state.currentProject) return;
  document.querySelectorAll('.chapter-item').forEach(i => i.classList.remove('active'));
  event.currentTarget.classList.add('active');
  state.currentChapter = num;
  document.getElementById('current-chapter-label').textContent = `第 ${num} 章`;

  try {
    const { content } = await get(`/api/projects/${state.currentProject.project_id}/file?path=${encodeURIComponent(path)}`);
    document.getElementById('content-viewer').textContent = content;
    await loadChapterCard(num);
  } catch(e) {
    toast('读取章节失败', 'error');
  }
}

async function loadChapterCard(num) {
  if (!state.currentProject) return;
  try {
    const { content } = await get(`/api/projects/${state.currentProject.project_id}/file?path=outlines/chapter_cards.yaml`);
    const cards = parseChapterCards(content, num);
    renderChapterCard(cards);
  } catch(e) {
    document.getElementById('chapter-card-panel').innerHTML = '<div class="card-empty"><p>章节卡片未找到</p><p class="hint">运行 outline 阶段后可生成</p></div>';
  }
}

function parseChapterCards(yamlText, targetNum) {
  const pattern = new RegExp(`- chapter: ${targetNum}[\\s\\S]*?(?=- chapter:|$)`, 'm');
  const m = yamlText.match(pattern);
  if (!m) return null;
  return m[0];
}

function renderChapterCard(rawText) {
  const panel = document.getElementById('chapter-card-panel');
  if (!rawText) {
    panel.innerHTML = '<div class="card-empty"><p>未找到本章卡片</p></div>';
    return;
  }
  panel.innerHTML = `
    <h4 style="font-size:12px;color:var(--text2);margin-bottom:10px;text-transform:uppercase;letter-spacing:.5px">章节卡片</h4>
    <pre style="white-space:pre-wrap;font-size:11px;color:var(--text2);font-family:monospace">${rawText}</pre>`;
}

// 写章节按钮
document.getElementById('btn-write-next').addEventListener('click', async () => {
  if (!state.currentProject) { toast('请先选择项目', 'warn'); return; }
  const session = await post('/api/sessions/create', {
    project_id: state.currentProject.project_id,
    initial_idea: '继续写下一章',
    task_type: 'chapter',
  });
  state.currentSession = session;
  const nextCh = (state.currentChapter || 0) + 1;
  setStatus(`生成第${nextCh}章…`, 'yellow');
  const { task_id } = await post(`/api/sessions/${session.session_id}/generate`, {
    task: 'chapter', params: { chapter: nextCh }
  });
  pollTask(task_id, `第${nextCh}章已生成`, () => loadChapterList());
});

document.getElementById('btn-write-batch').addEventListener('click', async () => {
  if (!state.currentProject) { toast('请先选择项目', 'warn'); return; }
  const session = await post('/api/sessions/create', {
    project_id: state.currentProject.project_id,
    initial_idea: '批量写5章',
    task_type: 'batch',
  });
  state.currentSession = session;
  const start = (state.currentChapter || 0) + 1;
  setStatus(`批量生成第${start}-${start+4}章…`, 'yellow');
  const { task_id } = await post(`/api/sessions/${session.session_id}/generate`, {
    task: 'batch', params: { start, batch: 5 }
  });
  pollTask(task_id, '批量章节已生成', () => loadChapterList());
});

['rewrite-full', 'rewrite-ending', 'strengthen-payoff', 'lighten'].forEach(action => {
  document.getElementById(`btn-${action}`).addEventListener('click', () => rewriteChapter(action));
});

async function rewriteChapter(action) {
  if (!state.currentProject || !state.currentChapter) { toast('请先选择章节', 'warn'); return; }
  const instructions = {
    'rewrite-full': '重写整章，保持情节主干不变，优化节奏和文风',
    'rewrite-ending': '只重写章节末尾300字，加强钩子力度',
    'strengthen-payoff': '加强本章的爽点和情绪宣泄，让高潮更有力',
    'lighten': '降低本章沉重感，增加轻松或暧昧的片段',
  };
  const session = await post('/api/sessions/create', {
    project_id: state.currentProject.project_id,
    initial_idea: instructions[action],
    task_type: 'rewrite',
  });
  state.currentSession = session;
  const chPath = `manuscript/volume_001/ch${String(state.currentChapter).padStart(3,'0')}.md`;
  setStatus('重写中…', 'yellow');
  const { task_id } = await post(`/api/sessions/${session.session_id}/generate`, {
    task: 'rewrite', params: { file_path: `manuscript/volume_001/ch${String(state.currentChapter).padStart(3,'0')}.md`, instruction: instructions[action] }
  });
  pollTask(task_id, '重写完成，查看沙盒结果', async () => {
    showPage('sessions');
    await loadSessionsPage();
  });
}

// ── 健康度页 ──────────────────────────────────────────────────────────────────
async function loadHealthPage() {
  const { projects } = await get('/api/projects');
  const sel = document.getElementById('health-project-select');
  sel.innerHTML = projects.map(p => `<option value="${p.project_id}">${p.name}</option>`).join('');
  sel.onchange = () => fetchHealthData(sel.value);
  document.getElementById('btn-run-health').onclick = () => fetchHealthData(sel.value);
  if (projects.length) fetchHealthData(projects[0].project_id);
}

async function fetchHealthData(projectId) {
  if (!projectId) return;
  setStatus('检查中…', 'yellow');
  try {
    const h = await get(`/api/projects/${projectId}/health`);
    renderHealthDashboard(h);
    setStatus('就绪', 'green');
  } catch(e) {
    toast('检查失败: ' + e.message, 'error');
    setStatus('就绪', 'green');
  }
}

function renderHealthDashboard(h) {
  const d = document.getElementById('health-dashboard');
  const s = h.status;
  const color = { green: 'var(--green)', yellow: 'var(--yellow)', red: 'var(--red)' }[s] || 'var(--text)';

  d.innerHTML = `
    <div class="health-overview">
      <div class="health-card ${s}">
        <div class="health-card-label">整体状态</div>
        <div class="health-card-value ${s}">${{'green':'健康','yellow':'注意','red':'危险'}[s]||s}</div>
        <div class="health-card-sub">${h.total_words.toLocaleString()}字 / ${h.total_chapters}章</div>
      </div>
      <div class="health-card ${h.overdue_promises > 0 ? 'red' : 'green'}">
        <div class="health-card-label">承诺健康度</div>
        <div class="health-card-value ${h.overdue_promises > 0 ? 'red' : 'green'}">${h.open_promises}</div>
        <div class="health-card-sub">开放 / 逾期 ${h.overdue_promises}</div>
      </div>
      <div class="health-card ${h.water_chapter_ratio > 0.25 ? 'yellow' : 'green'}">
        <div class="health-card-label">水章比例</div>
        <div class="health-card-value ${h.water_chapter_ratio > 0.25 ? 'yellow' : 'green'}">${(h.water_chapter_ratio*100).toFixed(0)}%</div>
        <div class="health-card-sub">建议低于 25%</div>
      </div>
      <div class="health-card ${h.hook_pass_rate < 0.7 ? 'yellow' : 'green'}">
        <div class="health-card-label">钩子合格率</div>
        <div class="health-card-value ${h.hook_pass_rate < 0.7 ? 'yellow' : 'green'}">${(h.hook_pass_rate*100).toFixed(0)}%</div>
        <div class="health-card-sub">建议高于 70%</div>
      </div>
    </div>
    ${h.issues.length ? `
    <div class="health-issues">
      <h3>🚨 需要处理的问题</h3>
      ${h.issues.map(i => `<div class="issue-item">• ${i}</div>`).join('')}
    </div>` : `<div style="color:var(--green);padding:16px">✅ 当前无严重问题</div>`}
    <div style="text-align:center;margin-top:12px">
      <button class="btn-secondary" onclick="startHealthSession('${state.currentProject?.project_id || ''}')">生成详细健康报告</button>
    </div>`;
}

async function startHealthSession(projectId) {
  if (!projectId) { toast('请先选择项目', 'warn'); return; }
  const session = await post('/api/sessions/create', { project_id: projectId, initial_idea: '健康度检查', task_type: 'health' });
  state.currentSession = session;
  setStatus('检查中…', 'yellow');
  const { task_id } = await post(`/api/sessions/${session.session_id}/generate`, { task: 'health', params: {} });
  pollTask(task_id, '健康报告已生成', async () => { showPage('sessions'); await loadSessionsPage(); });
}

// ── 沙盒历史页 ────────────────────────────────────────────────────────────────
async function loadSessionsPage() {
  const { sessions } = await get('/api/sessions');
  const list = document.getElementById('sessions-list');
  if (!sessions.length) {
    list.innerHTML = '<p style="color:var(--text3);padding:40px">还没有沙盒记录</p>';
    return;
  }
  list.innerHTML = sessions.map(s => `
    <div class="session-card">
      <div class="session-card-header">
        <span class="session-id">${s.session_id}</span>
        <span class="session-phase">${s.phase}</span>
        <span style="flex:1"></span>
        <span style="font-size:11px;color:var(--text3)">${(s.updated_at||'').slice(0,16)}</span>
      </div>
      <div class="session-idea">${s.initial_idea}</div>
      <div class="session-files">
        ${(s.generated_files||[]).map(f => `
          <span class="file-chip" onclick="previewSessionFile('${s.session_id}','${f}')">${f.split('/').pop()}</span>
        `).join('')}
      </div>
      <div class="session-actions">
        ${s.project_id ? `<button class="btn-primary btn-sm" onclick="showAcceptPanel('${s.session_id}','${s.project_id}',this)">采纳到项目</button>` : ''}
        <button class="btn-sm" onclick="deleteSession('${s.session_id}')">删除</button>
      </div>
    </div>`).join('');
}

async function previewSessionFile(sessionId, filePath) {
  try {
    const { content } = await get(`/api/sessions/${sessionId}/file?path=${encodeURIComponent(filePath)}`);
    document.getElementById('preview-title').textContent = filePath.split('/').pop();
    document.getElementById('preview-content').textContent = content;
    document.getElementById('modal-file-preview').style.display = 'flex';
    document.getElementById('btn-accept-file').onclick = () => {
      document.getElementById('modal-file-preview').style.display = 'none';
      showAcceptPanel(sessionId, state.currentProject?.project_id, null, [filePath]);
    };
  } catch(e) {
    toast('读取失败: ' + e.message, 'error');
  }
}

document.getElementById('close-preview').addEventListener('click', () => {
  document.getElementById('modal-file-preview').style.display = 'none';
});

async function showAcceptPanel(sessionId, projectId, btnEl, preselected) {
  if (!projectId) { toast('此 session 没有关联项目，无法采纳', 'warn'); return; }
  const { files } = await get(`/api/sessions/${sessionId}/files`);
  const generated = files.filter(f => f.path.startsWith('generated/'));
  if (!generated.length) { toast('没有可采纳的生成文件', 'warn'); return; }

  const panel = document.createElement('div');
  panel.className = 'modal-overlay';
  panel.style.display = 'flex';
  panel.innerHTML = `
    <div class="modal">
      <div class="modal-header">
        <h3>采纳文件到项目</h3>
        <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">✕</button>
      </div>
      <div class="modal-body">
        <p style="font-size:12px;color:var(--text2);margin-bottom:8px">选择要采纳的文件（将写入 project_repo）：</p>
        ${generated.map(f => `
          <label style="flex-direction:row;align-items:center;gap:8px;cursor:pointer">
            <input type="checkbox" value="${f.path}" ${preselected?.includes(f.path) ? 'checked' : ''} />
            <span>${f.path.split('/').pop()}</span>
            <span style="font-size:10px;color:var(--text3)">${f.size}B</span>
          </label>`).join('')}
        <label>采纳类型
          <select id="accept-type-select">
            <option value="official">正式设定</option>
            <option value="draft">草稿候选</option>
            <option value="archive">废案存档</option>
          </select>
        </label>
      </div>
      <div class="modal-footer">
        <button class="btn-secondary" onclick="this.closest('.modal-overlay').remove()">取消</button>
        <button class="btn-primary" onclick="doAccept('${sessionId}','${projectId}',this)">确认采纳</button>
      </div>
    </div>`;
  document.body.appendChild(panel);
}

async function doAccept(sessionId, projectId, btn) {
  const panel = btn.closest('.modal-overlay');
  const checked = [...panel.querySelectorAll('input[type=checkbox]:checked')].map(c => c.value);
  const acceptType = panel.querySelector('#accept-type-select').value;
  if (!checked.length) { toast('请至少选择一个文件', 'warn'); return; }
  try {
    const log = await post(`/api/sessions/${sessionId}/accept`, {
      project_id: projectId, files: checked, accept_type: acceptType,
    });
    panel.remove();
    toast(`✅ 已采纳 ${log.accepted_files.length} 个文件到项目`);
    await loadProjectsPage();
  } catch(e) {
    toast('采纳失败: ' + e.message, 'error');
  }
}

async function deleteSession(sessionId) {
  toast(`沙盒 ${sessionId.slice(-8)} 已标记（实际文件保留）`, 'warn');
}

// ── 任务轮询 ──────────────────────────────────────────────────────────────────
function pollTask(taskId, doneMsg, onDone) {
  state.pendingTaskId = taskId;
  let attempts = 0;
  const timer = setInterval(async () => {
    attempts++;
    if (attempts > 180) { clearInterval(timer); setStatus('超时', 'red'); return; }
    try {
      const t = await get(`/api/tasks/${taskId}`);
      if (t.status === 'done') {
        clearInterval(timer);
        setStatus('就绪', 'green');
        toast(doneMsg);
        if (onDone) await onDone(t);
        await loadSessionsPage();
      } else if (t.status === 'failed') {
        clearInterval(timer);
        setStatus('失败', 'red');
        toast('任务失败: ' + t.error.slice(0, 100), 'error');
      } else {
        setStatus('运行中…', 'yellow');
      }
    } catch(e) { /* 忽略轮询错误 */ }
  }, 2000);
  state.taskPollTimer = timer;
}

// ── 导航 ──────────────────────────────────────────────────────────────────────
document.querySelectorAll('.nav-btn').forEach(btn => {
  btn.addEventListener('click', () => showPage(btn.dataset.page));
});

// ── 初始化 ─────────────────────────────────────────────────────────────────────
(async () => {
  try {
    await get('/api/genres');
    setStatus('就绪', 'green');
  } catch(e) {
    setStatus('API 未连接', 'red');
    toast('后端 API 连接失败，请确认 Studio 服务已启动', 'error');
  }
  showPage('home');
})();
