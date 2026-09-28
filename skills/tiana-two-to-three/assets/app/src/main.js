import markup from './markup.html?raw';
import './style.css';
import { sql } from './db.js';
import { newId } from './id.js';
import weeklyPlans from './week-plans.json';

document.getElementById('app').innerHTML = markup;

const stageNames = { prepare: '备孕准备', early: '孕早期', middle: '孕中期', late: '孕晚期' };
const weekRanges = { prepare: [1, 12], early: [1, 12], middle: [13, 27], late: [28, 40] };
let phase = 'prepare';
let week = 1;
let role = 'all';
let names = { mom: '妈妈', dad: '爸爸' };
let completed = new Set();
let comments = [];
let activeTask = null;

function toast(message) {
  const element = document.getElementById('reward');
  element.textContent = message;
  element.classList.remove('hidden');
  clearTimeout(window.rewardTimer);
  window.rewardTimer = setTimeout(() => element.classList.add('hidden'), 3300);
}

function renderComments() {
  document.getElementById('moments-count').textContent = `${comments.length} 条留言`;
  ['comments', 'moments-comments'].forEach((id) => {
    const list = document.getElementById(id);
    list.replaceChildren();
    if (!comments.length) {
      const empty = document.createElement('div');
      empty.className = 'comments-empty';
      empty.innerHTML = '<span>♡</span><strong>第一句话，等你们写下</strong><p>记录今天的小期待，留给以后的你们看。</p>';
      list.append(empty);
    }
    comments.slice(0, id === 'comments' ? 3 : 20).forEach((comment) => {
      const item = document.createElement('div');
      item.className = 'comment';
      item.innerHTML = '<span class="avatar"></span><div><b></b><time></time><p></p></div>';
      item.querySelector('.avatar').textContent = comment.author[0];
      item.querySelector('b').textContent = comment.author;
      item.querySelector('time').textContent = new Date(comment.created_at).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' });
      item.querySelector('p').textContent = comment.body;
      list.append(item);
    });
  });
}

function renderTaskList(list) {
  const tasks = weeklyPlans[phase][week].tasks;
  list.replaceChildren();
  tasks.forEach(([who, title, detail], index) => {
    if (role !== 'all' && role !== who) return;
    const taskId = `${phase}-${week}-${index}`;
    const isDone = completed.has(taskId);
    const item = document.createElement('article');
    item.className = `task${isDone ? ' done' : ''}`;
    item.innerHTML = `<button class="check" aria-label="完成任务">${isDone ? '✓' : ''}</button><div class="task-copy"><div class="task-top"><h3></h3><span class="badge ${who === 'dad' ? 'dad' : ''}">${who === 'dad' ? '爸爸' : '妈妈'}</span></div><p></p></div><button class="comment-btn">写评论 ↗</button>`;
    item.querySelector('h3').textContent = title;
    item.querySelector('p').textContent = detail;
    item.querySelector('.check').onclick = async () => {
      try {
        if (isDone) {
          await sql('DELETE FROM journey_progress WHERE journey_id = ? AND task_id = ?', ['main', taskId]);
          completed.delete(taskId);
        } else {
          await sql('INSERT INTO journey_progress (journey_id, task_id, completed_at) VALUES (?, ?, ?)', ['main', taskId, new Date().toISOString()]);
          completed.add(taskId);
          toast('✦ 又完成了一件事，你们真的很棒！');
        }
        render();
      } catch (error) { toast(error.message); }
    };
    item.querySelector('.comment-btn').onclick = () => openModal(taskId, title);
    list.append(item);
  });
}

function render() {
  const plan = weeklyPlans[phase][week];
  const tasks = plan.tasks;
  renderTaskList(document.getElementById('task-list'));
  renderTaskList(document.getElementById('tasks-view-list'));
  const count = tasks.filter((_, index) => completed.has(`${phase}-${week}-${index}`)).length;
  document.getElementById('metric-count').textContent = count;
  document.getElementById('hero-count').textContent = count;
  document.getElementById('tasks-view-count').textContent = count;
  document.getElementById('week-theme').textContent = plan.theme;
  document.getElementById('week-note').textContent = plan.note;
  document.getElementById('tasks-week-theme').textContent = plan.theme;
  document.getElementById('tasks-week-note').textContent = plan.note;
  document.querySelectorAll('.task-total').forEach((element) => { element.textContent = tasks.length; });
  document.getElementById('tasks-stage-label').textContent = stageNames[phase];
  document.getElementById('tasks-week-label').textContent = `${phase === 'prepare' ? '备孕' : '怀孕'}第 ${week} 周`;
  document.getElementById('tasks-previous-week').disabled = week <= weekRanges[phase][0];
  document.getElementById('tasks-next-week').disabled = week >= weekRanges[phase][1];
  document.getElementById('stage-name').textContent = stageNames[phase];
  document.getElementById('week-label').textContent = `${phase === 'prepare' ? '备孕' : '怀孕'}第 ${week} 周`;
  document.getElementById('previous-week').disabled = week <= weekRanges[phase][0];
  document.getElementById('next-week').disabled = week >= weekRanges[phase][1];
  document.querySelector('.hero .overline').textContent = `OUR LITTLE JOURNEY · WEEK ${week}`;
  const phaseIndex = ['prepare', 'early', 'middle', 'late'].indexOf(phase);
  document.querySelector('.timeline').style.setProperty('--journey-progress', `${phaseIndex * 33}%`);
  document.querySelectorAll('.timeline .step').forEach((step, index) => {
    step.classList.toggle('past', index < phaseIndex);
    step.classList.toggle('now', index === phaseIndex);
    step.querySelector('span').textContent = index < phaseIndex ? '已走过' : index === phaseIndex ? '现在' : '接下来';
  });
  document.querySelectorAll('[data-phase]').forEach((button) => button.classList.toggle('active', button.dataset.phase === phase));
  document.querySelectorAll('[data-role]').forEach((button) => button.classList.toggle('active', button.dataset.role === role));
  document.querySelectorAll('[data-task-phase]').forEach((button) => button.classList.toggle('active', button.dataset.taskPhase === phase));
  document.querySelectorAll('[data-task-role]').forEach((button) => button.classList.toggle('active', button.dataset.taskRole === role));
  document.getElementById('mom-avatar').textContent = names.mom[0];
  document.getElementById('dad-avatar').textContent = names.dad[0];
  document.querySelector('[data-role="mom"]').textContent = `给${names.mom}`;
  document.querySelector('[data-role="dad"]').textContent = `给${names.dad}`;
  document.querySelector('[data-task-role="mom"]').textContent = `给${names.mom}`;
  document.querySelector('[data-task-role="dad"]').textContent = `给${names.dad}`;
  document.querySelector('#comment-author [value="mom"]').textContent = names.mom;
  document.querySelector('#comment-author [value="dad"]').textContent = names.dad;
  renderComments();
  renderRewards();
}

function renderRewards() {
  const total = completed.size;
  document.getElementById('rewards-total').textContent = total;
  const milestones = [1, 3, 6, 12];
  document.getElementById('rewards-next').textContent = total >= 12 ? '这一程的每一步，都值得被记住。' : `再完成 ${milestones.find((value) => value > total) - total} 件事，点亮下一枚纪念。`;
  const list = document.getElementById('reward-grid');
  list.replaceChildren();
  milestones.forEach((target, index) => {
    const item = document.createElement('div');
    item.className = `reward-card${total >= target ? ' earned' : ''}`;
    item.innerHTML = '<span class="reward-icon"></span><small></small><strong></strong><p></p>';
    item.querySelector('.reward-icon').textContent = ['✦', '♡', '❋', '✿'][index];
    item.querySelector('small').textContent = `${target} 件小事`;
    item.querySelector('strong').textContent = ['第一步', '并肩向前', '一周的温柔', '一路相伴'][index];
    item.querySelector('p').textContent = total >= target ? '已经点亮，记得夸夸彼此。' : '等待你们一起点亮。';
    list.append(item);
  });
}

function openModal(taskId = null, title = '') {
  activeTask = taskId;
  document.getElementById('modal-title').textContent = title ? `给「${title}」留句话` : '写下一句话';
  document.getElementById('modal-subtitle').textContent = title ? '分享你的想法，给彼此一点支持。' : '小小的分享，会让共同的旅程更有温度。';
  document.getElementById('comment-text').value = '';
  document.getElementById('modal').classList.remove('hidden');
  document.getElementById('comment-text').focus();
}

async function start() {
  try {
    const settings = (await sql('SELECT phase, week_number, started_at, mom_name, dad_name FROM journey_settings WHERE id = ?', ['main'])).rows[0];
    phase = settings?.phase in weeklyPlans ? settings.phase : 'prepare';
    names = { mom: settings?.mom_name || '妈妈', dad: settings?.dad_name || '爸爸' };
    week = settings ? Number(settings.week_number) : weekRanges[phase][0];
    completed = new Set((await sql('SELECT task_id FROM journey_progress WHERE journey_id = ?', ['main'])).rows.map((row) => row.task_id));
    comments = (await sql('SELECT author, body, created_at FROM journey_comments WHERE journey_id = ? ORDER BY created_at DESC LIMIT 20', ['main'])).rows;
    const days = settings ? Math.max(1, Math.floor((Date.now() - new Date(settings.started_at).getTime()) / 86400000)) : 1;
    document.getElementById('streak-count').textContent = days;
    document.getElementById('streak-side').textContent = `一起走过的第 ${days} 天`;
    document.querySelector('.date').textContent = new Date().toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', weekday: 'long' });
    render();
  } catch (error) { toast(`数据加载失败：${error.message}`); }
}

async function changePhase(nextPhase) {
  try {
    const firstWeek = weekRanges[nextPhase][0];
    await sql('UPDATE journey_settings SET phase = ?, week_number = ? WHERE id = ?', [nextPhase, firstWeek, 'main']);
    phase = nextPhase;
    week = firstWeek;
    render();
  } catch (error) { toast(error.message); }
}
document.querySelectorAll('[data-phase]').forEach((button) => button.onclick = () => changePhase(button.dataset.phase));
document.querySelectorAll('[data-task-phase]').forEach((button) => button.onclick = () => changePhase(button.dataset.taskPhase));
async function moveWeek(delta) {
  const next = week + delta;
  if (next < weekRanges[phase][0] || next > weekRanges[phase][1]) return;
  try {
    await sql('UPDATE journey_settings SET week_number = ? WHERE id = ?', [next, 'main']);
    week = next;
    render();
  } catch (error) { toast(error.message); }
}
document.getElementById('previous-week').onclick = () => moveWeek(-1);
document.getElementById('next-week').onclick = () => moveWeek(1);
document.getElementById('tasks-previous-week').onclick = () => moveWeek(-1);
document.getElementById('tasks-next-week').onclick = () => moveWeek(1);
document.querySelectorAll('[data-role]').forEach((button) => button.onclick = () => { role = button.dataset.role; render(); });
document.querySelectorAll('[data-task-role]').forEach((button) => button.onclick = () => { role = button.dataset.taskRole; render(); });
function showView(name) {
  document.querySelectorAll('[data-nav]').forEach((button) => {
    const active = button.dataset.nav === name;
    button.classList.toggle('active', active);
    if (active) button.setAttribute('aria-current', 'page');
    else button.removeAttribute('aria-current');
    if (active) document.getElementById('crumb').textContent = button.textContent.trim();
  });
  document.querySelectorAll('.journey-view').forEach((view) => view.classList.toggle('hidden', view.id !== `${name}-view`));
  window.scrollTo({ top: 0, behavior: 'instant' });
}
document.querySelectorAll('[data-nav]').forEach((button) => button.onclick = () => showView(button.dataset.nav));
document.getElementById('add-note').onclick = () => openModal();
document.getElementById('moments-add-note').onclick = () => openModal();
document.getElementById('cancel').onclick = () => document.getElementById('modal').classList.add('hidden');
document.getElementById('modal').onclick = (event) => { if (event.target.id === 'modal') event.currentTarget.classList.add('hidden'); };
document.getElementById('save-comment').onclick = async () => {
  const body = document.getElementById('comment-text').value.trim();
  if (!body) return;
  try {
    const comment = { id: newId(), author: names[document.getElementById('comment-author').value], body, created_at: new Date().toISOString() };
    await sql('INSERT INTO journey_comments (id, journey_id, task_id, author, body, created_at) VALUES (?, ?, ?, ?, ?, ?)', [comment.id, 'main', activeTask, comment.author, comment.body, comment.created_at]);
    comments.unshift(comment);
    renderComments();
    document.getElementById('modal').classList.add('hidden');
    toast('♡ 这句话已留在你们的旅程里');
  } catch (error) { toast(error.message); }
};

document.getElementById('profile-trigger').onclick = () => {
  document.getElementById('mom-name').value = names.mom;
  document.getElementById('dad-name').value = names.dad;
  document.getElementById('profile-modal').classList.remove('hidden');
  document.getElementById('mom-name').focus();
};
document.getElementById('profile-cancel').onclick = () => document.getElementById('profile-modal').classList.add('hidden');
document.getElementById('profile-modal').onclick = (event) => { if (event.target.id === 'profile-modal') event.currentTarget.classList.add('hidden'); };
document.getElementById('profile-save').onclick = async () => {
  const mom = document.getElementById('mom-name').value.trim() || '妈妈';
  const dad = document.getElementById('dad-name').value.trim() || '爸爸';
  try {
    await sql('UPDATE journey_settings SET mom_name = ?, dad_name = ? WHERE id = ?', [mom, dad, 'main']);
    names = { mom, dad };
    document.getElementById('profile-modal').classList.add('hidden');
    render();
    toast('称呼已保存');
  } catch (error) { toast(error.message); }
};

showView('journey');
start();
