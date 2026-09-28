import markup from './markup.html?raw';
import './style.css';
import { sql } from './db.js';
import { newId } from './id.js';

document.getElementById('app').innerHTML = markup;

const boardId = 'main';
const clientId = localStorage.getItem('fudao-client-id') || newId();
localStorage.setItem('fudao-client-id', clientId);
const viewport = document.getElementById('viewport');
const world = document.getElementById('world');
const notesElement = document.getElementById('notes');
const linesElement = document.getElementById('lines');
const svgNamespace = 'http://www.w3.org/2000/svg';
let board = { notes: [], links: [], strokes: [] };
let selected = null;
let connectFrom = null;
let tool = 'select';
let zoom = window.innerWidth < 760 ? 0.75 : 1;
let pan = { x: window.innerWidth < 760 ? -70 : 42, y: 5 };
let action = null;
let saving = 0;
let displayName = '';
let spaceHeld = false;

function toast(message) {
  const element = document.getElementById('toast');
  element.textContent = message;
  element.classList.remove('hidden');
  clearTimeout(window.boardToastTimer);
  window.boardToastTimer = setTimeout(() => element.classList.add('hidden'), 2700);
}

function worldPoint(event) {
  const rectangle = viewport.getBoundingClientRect();
  return { x: (event.clientX - rectangle.left - pan.x) / zoom, y: (event.clientY - rectangle.top - pan.y) / zoom };
}

function updateTransform() {
  world.style.transform = `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`;
  viewport.style.backgroundSize = `${24 * zoom}px ${24 * zoom}px`;
  viewport.style.backgroundPosition = `${pan.x}px ${pan.y}px`;
  document.getElementById('zoom-label').textContent = `${Math.round(zoom * 100)}%`;
}

function setTool(value) {
  tool = value;
  connectFrom = null;
  document.querySelectorAll('[data-tool]').forEach((button) => button.classList.toggle('active', button.dataset.tool === value));
  viewport.classList.remove('pen', 'note', 'connect');
  if (['pen', 'note', 'connect'].includes(value)) viewport.classList.add(value);
  renderNotes();
  document.getElementById('hint').textContent = {
    select: '选择 · 拖动便签 · 双击空白处新建',
    note: '便签 · 点击画布放置一张便签',
    pen: '按住并移动，画出你的想法',
    connect: '连线 · 依次点击两张便签',
    hand: '移动 · 按住并拖动画布',
  }[value];
}

function centerPoint() {
  const rectangle = viewport.getBoundingClientRect();
  return worldPoint({ clientX: rectangle.left + rectangle.width / 2, clientY: rectangle.top + rectangle.height / 2 });
}

async function createNoteAt(point, title = '新便签', body = '') {
  const note = { id: newId(), x: point.x - 118, y: point.y - 80, title, body, color: ['yellow', 'pink', 'blue', 'green', 'white'][board.notes.length % 5] };
  await saveNote(note);
  board.notes.push(note);
  selected = note.id;
  setTool('select');
  editNote(note, notesElement.querySelector(`[data-id="${note.id}"]`));
  return note;
}

async function loadBoard() {
  if (action || saving || document.querySelector('.note-card.editing')) return;
  try {
    const [notes, links, strokes] = await Promise.all([
      sql('SELECT id, x, y, title, body, color FROM board_notes WHERE board_id = ? ORDER BY rowid', [boardId]),
      sql('SELECT id, from_id, to_id FROM board_links WHERE board_id = ? ORDER BY rowid', [boardId]),
      sql('SELECT id, points_json FROM board_strokes WHERE board_id = ? ORDER BY rowid', [boardId]),
    ]);
    if (action || saving || document.querySelector('.note-card.editing')) return;
    board = {
      notes: notes.rows.map((note) => ({ ...note, x: Number(note.x), y: Number(note.y) })),
      links: links.rows.map((link) => ({ id: link.id, from: link.from_id, to: link.to_id })),
      strokes: strokes.rows.map((stroke) => ({ id: stroke.id, points: JSON.parse(stroke.points_json) })),
    };
    if (!board.notes.some((note) => note.id === selected)) selected = null;
    renderNotes();
    drawLines();
    document.getElementById('saved').textContent = '画布已同步';
  } catch (error) { document.getElementById('saved').textContent = '同步失败'; toast(error.message); }
}

async function write(statement, values) {
  saving += 1;
  document.getElementById('saved').textContent = '正在保存…';
  try {
    await sql(statement, values);
    document.getElementById('saved').textContent = '已保存到 Tiana SQLite';
  } catch (error) {
    document.getElementById('saved').textContent = '保存结果待确认';
    toast(error.message);
    throw error;
  } finally { saving -= 1; }
}

function saveNote(note) {
  return write('INSERT INTO board_notes (id, board_id, x, y, title, body, color, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET x = excluded.x, y = excluded.y, title = excluded.title, body = excluded.body, color = excluded.color, updated_at = excluded.updated_at', [note.id, boardId, note.x, note.y, note.title, note.body, note.color, new Date().toISOString()]);
}

function renderNotes() {
  document.getElementById('board-starter').classList.toggle('hidden', board.notes.length > 0 || board.strokes.length > 0);
  renderOverview();
  document.getElementById('inspector').classList.toggle('hidden', selected === null);
  document.getElementById('inspector').classList.toggle('has-selection', selected !== null);
  notesElement.replaceChildren();
  board.notes.forEach((note) => {
    const element = document.createElement('div');
    element.className = `note-card${note.id === selected ? ' selected' : ''}${note.id === connectFrom ? ' connect-source' : ''}`;
    element.dataset.id = note.id;
    element.dataset.color = note.color;
    element.style.left = `${note.x}px`;
    element.style.top = `${note.y}px`;
    element.innerHTML = '<div class="pin"></div><b></b><p></p><small>双击编辑 ↗</small><textarea aria-label="编辑便签内容"></textarea>';
    element.querySelector('b').textContent = note.title;
    element.querySelector('p').textContent = note.body;
    element.querySelector('textarea').value = `${note.title}\n${note.body}`;
    element.addEventListener('pointerdown', (event) => notePointerDown(event, note, element));
    element.addEventListener('dblclick', (event) => { event.stopPropagation(); editNote(note, element); });
    notesElement.append(element);
  });
  document.querySelectorAll('.swatch').forEach((button) => button.classList.toggle('active', board.notes.find((note) => note.id === selected)?.color === button.dataset.color));
}

function renderOverview() {
  document.getElementById('overview-notes').textContent = board.notes.length;
  document.getElementById('overview-links').textContent = board.links.length;
  document.getElementById('overview-strokes').textContent = board.strokes.length;
  const list = document.getElementById('overview-note-list');
  list.replaceChildren();
  if (!board.notes.length) {
    const empty = document.createElement('div');
    empty.className = 'overview-empty';
    empty.innerHTML = '<span>✳</span><strong>第一张便签，等你贴上</strong><p>写下一个问题，就是一次很好的开始。</p>';
    list.append(empty);
  } else board.notes.slice(-4).reverse().forEach((note) => {
    const item = document.createElement('button');
    item.className = 'overview-note';
    item.innerHTML = '<span></span><div><b></b><small></small></div><em>↗</em>';
    item.querySelector('span').dataset.color = note.color;
    item.querySelector('b').textContent = note.title;
    item.querySelector('small').textContent = note.body || '打开画布查看这张便签';
    item.onclick = () => {
      showSection('canvas');
      zoom = 1;
      pan = { x: viewport.clientWidth / 2 - (note.x + 118), y: viewport.clientHeight / 2 - (note.y + 86) };
      selected = note.id;
      updateTransform();
      renderNotes();
    };
    list.append(item);
  });
}

function showSection(name) {
  document.getElementById('viewport').classList.toggle('hidden', name !== 'canvas');
  document.getElementById('board-overview').classList.toggle('hidden', name !== 'overview');
  document.getElementById('home').classList.toggle('active', name === 'overview');
  document.getElementById('canvas-tab').classList.toggle('active', name === 'canvas');
  document.getElementById('home').setAttribute('aria-label', '白板概览');
  document.getElementById('canvas-tab').setAttribute('aria-label', '当前画布');
}

function drawLines() {
  linesElement.replaceChildren();
  board.links.forEach((link) => {
    const from = board.notes.find((note) => note.id === link.from);
    const to = board.notes.find((note) => note.id === link.to);
    if (!from || !to) return;
    const x1 = from.x + 118, y1 = from.y + 86, x2 = to.x + 118, y2 = to.y + 86;
    const path = document.createElementNS(svgNamespace, 'path');
    path.setAttribute('d', `M ${x1} ${y1} C ${(x1 + x2) / 2} ${y1}, ${(x1 + x2) / 2} ${y2}, ${x2} ${y2}`);
    path.setAttribute('fill', 'none');
    path.setAttribute('stroke', '#709b80');
    path.setAttribute('stroke-width', '2.3');
    path.setAttribute('stroke-linecap', 'round');
    path.setAttribute('opacity', '.65');
    linesElement.append(path);
  });
  board.strokes.forEach((stroke) => {
    if (!stroke.points.length) return;
    const path = document.createElementNS(svgNamespace, 'path');
    path.setAttribute('d', stroke.points.map((point, index) => `${index ? 'L' : 'M'} ${point.x} ${point.y}`).join(' '));
    path.setAttribute('fill', 'none');
    path.setAttribute('stroke', '#547e68');
    path.setAttribute('stroke-width', '3');
    path.setAttribute('stroke-linecap', 'round');
    path.setAttribute('stroke-linejoin', 'round');
    linesElement.append(path);
  });
}

async function notePointerDown(event, note, element) {
  if (event.target.tagName === 'TEXTAREA' || tool === 'hand' || spaceHeld) return;
  event.stopPropagation();
  if (tool === 'connect') {
    if (connectFrom === null) {
      connectFrom = note.id;
      renderNotes();
      toast('现在点击另一张便签');
    } else if (connectFrom !== note.id) {
      const source = connectFrom;
      connectFrom = null;
      if (board.links.some((link) => (link.from === source && link.to === note.id) || (link.from === note.id && link.to === source))) return;
      const link = { id: newId(), from: source, to: note.id };
      try {
        await write('INSERT OR IGNORE INTO board_links (id, board_id, from_id, to_id, created_at) VALUES (?, ?, ?, ?, ?)', [link.id, boardId, link.from, link.to, new Date().toISOString()]);
        board.links.push(link);
        drawLines();
        renderNotes();
        toast('想法已连接');
      } catch { await loadBoard(); }
    }
    return;
  }
  if (tool !== 'select') return;
  selected = note.id;
  document.querySelectorAll('.note-card').forEach((card) => card.classList.toggle('selected', card === element));
  document.getElementById('inspector').classList.add('has-selection');
  document.querySelectorAll('.swatch').forEach((button) => button.classList.toggle('active', button.dataset.color === note.color));
  action = { type: 'drag-note', note, element, startX: event.clientX, startY: event.clientY, originX: note.x, originY: note.y };
  element.classList.add('dragging');
  event.preventDefault();
}

function editNote(note, element) {
  selected = note.id;
  element.classList.add('editing');
  element.classList.remove('dragging');
  const area = element.querySelector('textarea');
  area.focus();
  area.select();
  area.addEventListener('blur', async () => {
    const parts = area.value.split('\n');
    note.title = (parts.shift() || '新想法').trim();
    note.body = parts.join('\n').trim();
    try { await saveNote(note); }
    catch { await loadBoard(); return; }
    renderNotes();
  }, { once: true });
  area.addEventListener('keydown', (event) => { event.stopPropagation(); if (event.key === 'Escape') area.blur(); });
}

viewport.addEventListener('pointerdown', async (event) => {
  if (event.target.closest('.toolbox,.zoom,.inspector,.hint,.toast,.board-starter')) return;
  if (event.target.closest('.note-card') && tool !== 'hand' && !spaceHeld) return;
  const point = worldPoint(event);
  if (tool === 'note' && !spaceHeld) {
    try { await createNoteAt(point); toast('便签已添加，直接输入内容'); }
    catch (error) { toast(error.message); await loadBoard(); }
    return;
  }
  if (tool === 'pen' && !spaceHeld) {
    action = { type: 'draw', stroke: { id: newId(), points: [point] } };
    viewport.setPointerCapture(event.pointerId);
    drawLines();
    return;
  }
  if (tool === 'select' || tool === 'hand' || spaceHeld) {
    selected = null;
    renderNotes();
    action = { type: 'pan', startX: event.clientX, startY: event.clientY, originX: pan.x, originY: pan.y };
    viewport.classList.add('grabbing');
    viewport.setPointerCapture(event.pointerId);
  }
});
viewport.addEventListener('dblclick', async (event) => {
  if (tool !== 'select' || event.target.closest('.note-card,.toolbox,.inspector,.board-starter,.zoom')) return;
  try { await createNoteAt(worldPoint(event)); }
  catch (error) { toast(error.message); await loadBoard(); }
});

window.addEventListener('pointermove', (event) => {
  if (!action) return;
  if (action.type === 'drag-note') {
    action.note.x = action.originX + (event.clientX - action.startX) / zoom;
    action.note.y = action.originY + (event.clientY - action.startY) / zoom;
    action.element.style.left = `${action.note.x}px`;
    action.element.style.top = `${action.note.y}px`;
    drawLines();
  } else if (action.type === 'pan') {
    pan.x = action.originX + event.clientX - action.startX;
    pan.y = action.originY + event.clientY - action.startY;
    updateTransform();
  } else if (action.type === 'draw') {
    action.stroke.points.push(worldPoint(event));
    drawLines();
    const path = document.createElementNS(svgNamespace, 'path');
    path.setAttribute('d', action.stroke.points.map((point, index) => `${index ? 'L' : 'M'} ${point.x} ${point.y}`).join(' '));
    path.setAttribute('fill', 'none');
    path.setAttribute('stroke', '#547e68');
    path.setAttribute('stroke-width', '3');
    path.setAttribute('stroke-linecap', 'round');
    path.setAttribute('stroke-linejoin', 'round');
    linesElement.append(path);
  }
});

window.addEventListener('pointerup', async () => {
  const finished = action;
  action = null;
  viewport.classList.remove('grabbing');
  if (!finished) return;
  if (finished.type === 'drag-note') {
    finished.element.classList.remove('dragging');
    if (finished.note.x !== finished.originX || finished.note.y !== finished.originY) {
      try { await saveNote(finished.note); }
      catch { await loadBoard(); }
    }
  } else if (finished.type === 'draw' && finished.stroke.points.length > 1) {
    try {
      await write('INSERT INTO board_strokes (id, board_id, points_json, created_at) VALUES (?, ?, ?, ?)', [finished.stroke.id, boardId, JSON.stringify(finished.stroke.points), new Date().toISOString()]);
      board.strokes.push(finished.stroke);
      drawLines();
      renderOverview();
    } catch { await loadBoard(); }
  } else drawLines();
});

function zoomAt(factor, clientX, clientY) {
  const rectangle = viewport.getBoundingClientRect();
  const x = clientX - rectangle.left, y = clientY - rectangle.top, previous = zoom;
  zoom = Math.max(0.35, Math.min(2.4, zoom * factor));
  pan.x = x - (x - pan.x) * zoom / previous;
  pan.y = y - (y - pan.y) * zoom / previous;
  updateTransform();
}
viewport.addEventListener('wheel', (event) => { event.preventDefault(); zoomAt(event.deltaY < 0 ? 1.1 : 0.9, event.clientX, event.clientY); }, { passive: false });
document.getElementById('zoom-in').onclick = () => { const rectangle = viewport.getBoundingClientRect(); zoomAt(1.2, rectangle.left + rectangle.width / 2, rectangle.top + rectangle.height / 2); };
document.getElementById('zoom-out').onclick = () => { const rectangle = viewport.getBoundingClientRect(); zoomAt(1 / 1.2, rectangle.left + rectangle.width / 2, rectangle.top + rectangle.height / 2); };
document.getElementById('fit-board').onclick = () => {
  if (!board.notes.length) { zoom = 1; pan = { x: 42, y: 5 }; updateTransform(); return; }
  const left = Math.min(...board.notes.map((note) => note.x));
  const top = Math.min(...board.notes.map((note) => note.y));
  const right = Math.max(...board.notes.map((note) => note.x + 235));
  const bottom = Math.max(...board.notes.map((note) => note.y + 178));
  zoom = Math.max(0.35, Math.min(1.4, Math.min((viewport.clientWidth - 220) / (right - left), (viewport.clientHeight - 160) / (bottom - top))));
  pan = { x: (viewport.clientWidth - (left + right) * zoom) / 2, y: (viewport.clientHeight - (top + bottom) * zoom) / 2 };
  updateTransform();
};
document.querySelectorAll('[data-tool]').forEach((button) => button.onclick = () => setTool(button.dataset.tool));
document.querySelectorAll('.swatch').forEach((button) => button.onclick = async () => {
  const note = board.notes.find((entry) => entry.id === selected);
  if (!note) { toast('先选中一张便签'); return; }
  const previous = note.color;
  note.color = button.dataset.color;
  try { await saveNote(note); renderNotes(); }
  catch { note.color = previous; renderNotes(); }
});
document.getElementById('delete').onclick = async () => {
  if (selected === null) { toast('先选中一张便签'); return; }
  const id = selected;
  try {
    await write('DELETE FROM board_links WHERE board_id = ? AND (from_id = ? OR to_id = ?)', [boardId, id, id]);
    await write('DELETE FROM board_notes WHERE board_id = ? AND id = ?', [boardId, id]);
    selected = null;
    await loadBoard();
    toast('便签已删除');
  } catch { await loadBoard(); }
};
document.getElementById('help').onclick = () => document.getElementById('help-modal').classList.remove('hidden');
document.getElementById('help-close').onclick = () => document.getElementById('help-modal').classList.add('hidden');
document.getElementById('help-modal').onclick = (event) => { if (event.target.id === 'help-modal') event.currentTarget.classList.add('hidden'); };
document.getElementById('home').onclick = () => showSection('overview');
document.getElementById('canvas-tab').onclick = () => showSection('canvas');
document.getElementById('overview-open').onclick = () => showSection('canvas');
document.getElementById('share').onclick = () => {
  const dialog = document.getElementById('share-modal');
  const input = document.getElementById('share-link');
  input.value = location.href;
  dialog.classList.remove('hidden');
  input.focus();
  input.select();
};
document.getElementById('share-close').onclick = () => document.getElementById('share-modal').classList.add('hidden');
document.getElementById('share-modal').onclick = (event) => { if (event.target.id === 'share-modal') event.currentTarget.classList.add('hidden'); };
document.getElementById('quick-add').onclick = async () => {
  showSection('canvas');
  try { await createNoteAt(centerPoint()); }
  catch (error) { toast(error.message); await loadBoard(); }
};
document.getElementById('starter-create').onclick = () => document.getElementById('quick-add').click();
document.querySelectorAll('[data-starter-title]').forEach((button) => button.onclick = async () => {
  try { await createNoteAt(centerPoint(), button.dataset.starterTitle, button.dataset.starterBody); }
  catch (error) { toast(error.message); await loadBoard(); }
});
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
    await sql('INSERT INTO board_profiles (board_id, client_id, display_name) VALUES (?, ?, ?) ON CONFLICT(board_id, client_id) DO UPDATE SET display_name = excluded.display_name', [boardId, clientId, name]);
    displayName = name;
    document.getElementById('profile-label').textContent = name;
    document.getElementById('profile-avatar').textContent = name[0];
    document.getElementById('profile-modal').classList.add('hidden');
    toast('名称已保存');
  } catch (error) { toast(error.message); }
};
async function loadProfile() {
  try {
    displayName = (await sql('SELECT display_name FROM board_profiles WHERE board_id = ? AND client_id = ?', [boardId, clientId])).rows[0]?.display_name || '';
    document.getElementById('profile-label').textContent = displayName || '设置名称';
    document.getElementById('profile-avatar').textContent = displayName ? displayName[0] : '✦';
  } catch (error) { toast(error.message); }
}
window.addEventListener('keydown', (event) => {
  if (['TEXTAREA', 'INPUT'].includes(event.target.tagName)) return;
  if (event.code === 'Space') { event.preventDefault(); spaceHeld = true; viewport.classList.add('space-pan'); return; }
  const tools = { v: 'select', n: 'note', p: 'pen', l: 'connect', c: 'connect', h: 'hand' };
  if (tools[event.key.toLowerCase()]) setTool(tools[event.key.toLowerCase()]);
  if (['Delete', 'Backspace'].includes(event.key) && selected !== null) { event.preventDefault(); document.getElementById('delete').click(); }
  if (event.key === 'Enter' && selected !== null) {
    const note = board.notes.find((entry) => entry.id === selected);
    const element = notesElement.querySelector(`[data-id="${selected}"]`);
    if (note && element) editNote(note, element);
  }
  if (event.key === 'Escape') { connectFrom = null; selected = null; setTool('select'); }
});
window.addEventListener('keyup', (event) => {
  if (event.code === 'Space') { spaceHeld = false; viewport.classList.remove('space-pan'); }
});

updateTransform();
showSection('canvas');
loadBoard();
loadProfile();
setInterval(loadBoard, 1500);
