import markup from './markup.html?raw';
import './style.css';
import { sql } from './db.js';
import { newId } from './id.js';

document.getElementById('app').innerHTML = markup;

let tasks = [];
let sessions = [];
let remaining = 1500;
let interval = null;
let displayName = '';
let activeView = 'today';
let taskFilter = 'all';
const suggestions = [
  { title: '安排 25 分钟专注学习', subject: '复习总结', estimated_minutes: 25 },
  { title: '阅读一篇感兴趣的文章', subject: '语言学习', estimated_minutes: 25 },
  { title: '整理今天的新发现', subject: '复习总结', estimated_minutes: 20 },
];

function toast(message) {
  const element = document.getElementById('toast');
  element.textContent = message;
  element.classList.remove('hidden');
  clearTimeout(window.studyToastTimer);
  window.studyToastTimer = setTimeout(() => element.classList.add('hidden'), 3000);
}

function renderTasks() {
  const list = document.getElementById('task-list');
  list.replaceChildren();
  if (!tasks.length) {
    renderSuggestions(list);
  }
  tasks.forEach((task) => list.append(taskRow(task)));
  const completed = tasks.filter((task) => task.done_at).length;
  document.getElementById('count').textContent = completed;
  document.getElementById('total').textContent = tasks.length;
  document.getElementById('encourage').textContent = !tasks.length ? '从一项小任务开始 ✦' : completed === tasks.length ? '清单全部完成，太棒了！' : completed >= 2 ? '节奏很好，继续保持 ✦' : '美好的一天，从第一步开始';
  document.getElementById('review-task-count').textContent = completed;
  renderTaskView();
  renderPlan();
}

function renderSuggestions(list) {
  const intro = document.createElement('div');
  intro.className = 'suggestion-intro';
  intro.innerHTML = '<b>选一个轻松的开始</b><span>点“加入清单”才会成为你的任务。</span>';
  list.append(intro);
  suggestions.forEach((suggestion) => {
    const row = document.createElement('div');
    row.className = 'suggestion';
    row.innerHTML = '<span class="suggestion-mark">✦</span><div><b></b><small></small></div><button>加入清单 ↗</button>';
    row.querySelector('b').textContent = suggestion.title;
    row.querySelector('small').textContent = `${suggestion.subject} · ${suggestion.estimated_minutes} 分钟`;
    row.querySelector('button').onclick = async () => {
      try { await addTask(suggestion); }
      catch (error) { toast(error.message); }
    };
    list.append(row);
  });
}

function taskRow(task) {
    const done = Boolean(task.done_at);
    const row = document.createElement('div');
    row.className = `task${done ? ' done' : ''}`;
    row.innerHTML = `<button class="tick" aria-label="完成任务">${done ? '✓' : ''}</button><div class="task-detail"><div class="task-title"></div><div class="task-meta"></div></div><span class="subject"></span>`;
    row.querySelector('.task-title').textContent = task.title;
    row.querySelector('.task-meta').textContent = `预计 ${task.estimated_minutes} 分钟 · 学习清单`;
    const tag = row.querySelector('.subject');
    tag.textContent = task.subject;
    const tone = task.subject === '语言学习' ? 'green' : task.subject === '复习总结' ? 'orange' : null;
    if (tone) tag.classList.add(tone);
    row.querySelector('.tick').onclick = async () => {
      try {
        const next = done ? null : new Date().toISOString();
        await sql('UPDATE study_tasks SET done_at = ? WHERE workspace_id = ? AND id = ?', [next, 'main', task.id]);
        task.done_at = next;
        renderTasks();
        if (next) toast('✦ 一项任务完成了，你又向目标靠近一点。');
      } catch (error) { toast(error.message); }
    };
    return row;
}

function renderTaskView() {
  const list = document.getElementById('task-view-list');
  list.replaceChildren();
  const visible = tasks.filter((task) => taskFilter === 'all' || (taskFilter === 'done' ? task.done_at : !task.done_at));
  const doneCount = tasks.filter((task) => task.done_at).length;
  document.querySelector('[data-task-filter="all"]').textContent = `全部 ${tasks.length}`;
  document.querySelector('[data-task-filter="open"]').textContent = `待完成 ${tasks.length - doneCount}`;
  document.querySelector('[data-task-filter="done"]').textContent = `已完成 ${doneCount}`;
  document.getElementById('task-view-count').textContent = `${visible.length} 项任务`;
  if (!tasks.length && taskFilter === 'all') renderSuggestions(list);
  else if (!visible.length) {
    const empty = document.createElement('p');
    empty.className = 'view-empty';
    empty.textContent = taskFilter === 'done' ? '还没有完成的任务。完成一项后会显示在这里。' : '当前没有待完成任务。写下下一步，继续前进。';
    list.append(empty);
  } else visible.forEach((task) => list.append(taskRow(task)));
}

function renderPlan() {
  const list = document.getElementById('plan-list');
  list.replaceChildren();
  const next = tasks.filter((task) => !task.done_at).slice(0, 3);
  if (!next.length) {
    const message = document.createElement('p');
    message.className = 'week-note';
    message.textContent = tasks.length ? '当前任务都完成了。给自己一点休息，再写下新的目标。' : '你的下一步还没有写下。从左侧挑一个建议，或新建自己的任务。';
    list.append(message);
    return;
  }
  next.forEach((task, index) => {
    const row = document.createElement('div');
    row.className = 'plan-row';
    row.innerHTML = '<span class="plan-time"></span><span class="plan-dot"></span><div><b></b><small></small></div>';
    row.querySelector('.plan-time').textContent = String(index + 1).padStart(2, '0');
    row.querySelector('b').textContent = task.title;
    row.querySelector('small').textContent = `${task.subject} · ${task.estimated_minutes} 分钟`;
    list.append(row);
  });
}

function dateKey(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

function renderBars() {
  const totals = new Map();
  sessions.forEach((session) => {
    const key = dateKey(new Date(session.started_at));
    totals.set(key, (totals.get(key) || 0) + Number(session.minutes));
  });
  const today = new Date();
  const days = Array.from({ length: 7 }, (_, index) => {
    const date = new Date(today);
    date.setDate(today.getDate() - 6 + index);
    return date;
  });
  const maximum = Math.max(180, ...totals.values());
  ['bars', 'review-bars'].forEach((id) => {
    const bars = document.getElementById(id);
    bars.replaceChildren();
    days.forEach((date, index) => {
      const group = document.createElement('div');
      group.className = 'bar-group';
      const bar = document.createElement('div');
      bar.className = `bar${index === 6 ? ' today' : ''}`;
      bar.style.height = `${Math.max(6, Math.round((totals.get(dateKey(date)) || 0) / maximum * 115))}px`;
      const label = document.createElement('span');
      label.textContent = `周${'日一二三四五六'[date.getDay()]}`;
      group.append(bar, label);
      bars.append(group);
    });
  });
  const minutes = sessions.reduce((sum, session) => sum + Number(session.minutes), 0);
  document.getElementById('overview-week-note').textContent = `✦ 近 7 天已专注 ${Math.round(minutes / 60 * 10) / 10} 小时。持续，比完美更重要。`;
  document.getElementById('review-hours').textContent = (minutes / 60).toFixed(1);
  document.getElementById('review-days').textContent = days.filter((day) => (totals.get(dateKey(day)) || 0) > 0).length;
  document.getElementById('review-note').textContent = minutes ? '哪天更容易进入状态？照着自己的节奏安排下一轮。' : '第一段专注完成后，这里会画出你的学习节奏。';
  document.getElementById('focus-total').textContent = minutes;
  document.getElementById('focus-session-count').textContent = sessions.length;
  const history = document.getElementById('session-list');
  history.replaceChildren();
  if (!sessions.length) {
    const empty = document.createElement('div');
    empty.className = 'view-empty';
    empty.textContent = '完成第一轮专注后，记录会出现在这里。';
    history.append(empty);
  } else sessions.slice(-6).reverse().forEach((session) => {
    const row = document.createElement('div');
    row.className = 'session-row';
    row.innerHTML = '<span class="session-dot">✓</span><div><strong>完成一轮专注</strong><small></small></div><b></b>';
    row.querySelector('small').textContent = new Date(session.started_at).toLocaleString('zh-CN', { month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    row.querySelector('b').textContent = `${session.minutes} 分钟`;
    history.append(row);
  });
}

function renderTimer() {
  const time = `${String(Math.floor(remaining / 60)).padStart(2, '0')}:${String(remaining % 60).padStart(2, '0')}`;
  ['timer-display', 'focus-timer-display'].forEach((id) => { document.getElementById(id).textContent = time; });
  ['timer-toggle', 'focus-timer-toggle'].forEach((id) => { document.getElementById(id).textContent = interval ? '暂停专注' : '开始专注'; });
}

function toggleTimer() {
  if (interval) {
    clearInterval(interval);
    interval = null;
    renderTimer();
    return;
  }
  interval = setInterval(async () => {
    remaining -= 1;
    renderTimer();
    if (remaining > 0) return;
    clearInterval(interval);
    interval = null;
    remaining = 1500;
    renderTimer();
    try {
      const session = { id: newId(), started_at: new Date(Date.now() - 1500_000).toISOString(), minutes: 25 };
      await sql('INSERT INTO study_sessions (id, workspace_id, started_at, minutes) VALUES (?, ?, ?, ?)', [session.id, 'main', session.started_at, session.minutes]);
      sessions.push(session);
      renderBars();
      toast('✦ 完成了 25 分钟专注，休息一下吧！');
    } catch (error) { toast(`专注记录未保存：${error.message}`); }
  }, 1000);
  renderTimer();
}

async function start() {
  try {
    displayName = (await sql('SELECT display_name FROM study_profile WHERE workspace_id = ?', ['main'])).rows[0]?.display_name || '';
    renderProfile();
    tasks = (await sql('SELECT id, title, subject, estimated_minutes, done_at FROM study_tasks WHERE workspace_id = ? ORDER BY rowid', ['main'])).rows;
    const since = new Date();
    since.setDate(since.getDate() - 7);
    sessions = (await sql('SELECT started_at, minutes FROM study_sessions WHERE workspace_id = ? AND started_at >= ? ORDER BY started_at', ['main', since.toISOString()])).rows;
    const today = new Date();
    const longDate = today.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' });
    document.querySelector('.top-right span').textContent = longDate;
    document.querySelector('.eyebrow').textContent = today.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' }).toUpperCase();
    renderTasks();
    renderBars();
  } catch (error) { toast(`数据加载失败：${error.message}`); }
}

function renderProfile() {
  document.getElementById('profile-avatar').textContent = displayName ? displayName[0] : '✦';
  document.getElementById('profile-label').textContent = displayName || '设置名称';
  document.getElementById('greeting').textContent = displayName ? `你好，${displayName}。✦` : '今天，从这里开始。✦';
}

async function addTask({ title, subject, estimated_minutes }) {
  const task = { id: newId(), title, subject, estimated_minutes, done_at: null };
  await sql('INSERT INTO study_tasks (id, workspace_id, title, subject, estimated_minutes) VALUES (?, ?, ?, ?, ?)', [task.id, 'main', title, subject, estimated_minutes]);
  tasks.push(task);
  renderTasks();
  toast('任务已加入学习清单');
}

function openTaskModal() {
  document.getElementById('modal').classList.remove('hidden');
  document.getElementById('task-name').focus();
}
document.getElementById('add-task').onclick = openTaskModal;
document.querySelectorAll('[data-open-task]').forEach((button) => button.onclick = openTaskModal);
document.getElementById('cancel').onclick = () => document.getElementById('modal').classList.add('hidden');
document.getElementById('modal').onclick = (event) => { if (event.target.id === 'modal') event.currentTarget.classList.add('hidden'); };
document.getElementById('save-task').onclick = async () => {
  const title = document.getElementById('task-name').value.trim();
  if (!title) return;
  try {
    await addTask({ title, subject: document.getElementById('task-subject').value, estimated_minutes: 25 });
    document.getElementById('task-name').value = '';
    document.getElementById('modal').classList.add('hidden');
  } catch (error) { toast(error.message); }
};
document.getElementById('profile-trigger').onclick = () => {
  document.getElementById('profile-name').value = displayName;
  document.getElementById('profile-modal').classList.remove('hidden');
  document.getElementById('profile-name').focus();
};
document.getElementById('profile-cancel').onclick = () => document.getElementById('profile-modal').classList.add('hidden');
document.getElementById('profile-modal').onclick = (event) => { if (event.target.id === 'profile-modal') event.currentTarget.classList.add('hidden'); };
document.getElementById('profile-save').onclick = async () => {
  const name = document.getElementById('profile-name').value.trim();
  if (!name) return;
  try {
    await sql('INSERT INTO study_profile (workspace_id, display_name) VALUES (?, ?) ON CONFLICT(workspace_id) DO UPDATE SET display_name = excluded.display_name', ['main', name]);
    displayName = name;
    renderProfile();
    document.getElementById('profile-modal').classList.add('hidden');
    toast('名称已保存');
  } catch (error) { toast(error.message); }
};
function showView(name) {
  activeView = name;
  document.querySelectorAll('[data-nav]').forEach((button) => {
    const active = button.dataset.nav === name;
    button.classList.toggle('active', active);
    if (active) button.setAttribute('aria-current', 'page');
    else button.removeAttribute('aria-current');
    if (active) document.getElementById('crumb').textContent = button.textContent.trim();
  });
  document.querySelectorAll('.view-screen').forEach((screen) => screen.classList.toggle('hidden', screen.id !== `${name}-view`));
  window.scrollTo({ top: 0, behavior: 'instant' });
}
document.querySelectorAll('[data-nav]').forEach((button) => button.onclick = () => showView(button.dataset.nav));
document.querySelectorAll('[data-task-filter]').forEach((button) => button.onclick = () => {
  taskFilter = button.dataset.taskFilter;
  document.querySelectorAll('[data-task-filter]').forEach((entry) => entry.classList.toggle('active', entry === button));
  renderTaskView();
});
['timer-toggle', 'focus-timer-toggle'].forEach((id) => { document.getElementById(id).onclick = toggleTimer; });
document.getElementById('start-focus').onclick = () => {
  showView('focus');
  if (!interval) toggleTimer();
};
document.getElementById('review-start-focus').onclick = () => showView('focus');
function resetTimer() {
  clearInterval(interval);
  interval = null;
  remaining = 1500;
  renderTimer();
}
['timer-reset', 'focus-timer-reset'].forEach((id) => { document.getElementById(id).onclick = resetTimer; });

renderTimer();
showView(activeView);
start();
