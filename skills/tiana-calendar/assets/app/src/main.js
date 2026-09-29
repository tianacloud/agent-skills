import "./style.css";
import {
  $,
  esc,
  iso,
  now,
  today,
  toast,
  showModal,
  submitForm,
  confirmDelete,
} from "./ui.js";
import { dropdown, closeDropdown } from "./dropdown.js";
import { newId } from "./id.js";
import * as store from "./store.js";
const uid = newId;
let view = "all",
  filter = "all";
let month = new Date(now.getFullYear(), now.getMonth(), 1),
  selectedDate = today;
let rows = [],
  loading = true,
  ready = false,
  loadError = "",
  loadSequence = 0;
const read = () => rows;
const identity = ["朝夕", "MAKE ROOM FOR LIFE", "我的日历"];
document.getElementById("app").innerHTML =
  '<div class="app-status" id="app-status" role="status"><span id="status-text"></span><button id="reload-data" type="button">重新加载</button></div><div id="workspace"></div><dialog id="modal"></dialog><div id="toast" role="status"></div>';
function setStatus() {
  $("#app-status").hidden = !loading && !loadError;
  $("#status-text").textContent = loading ? "正在读取你的记录…" : loadError;
  $("#reload-data").hidden = loading;
  const shell = $(".shell");
  shell?.setAttribute("aria-busy", String(loading));
  if (shell) shell.inert = loading || !ready;
}
function navButton(id, icon, title) {
  return `<button data-view="${id}" class="${view === id ? "selected" : ""}"><span class="nav-icon" aria-hidden="true">${icon}</span>${title}</button>`;
}
function shell(content) {
  const [name, en, space] = identity;
  const nav =
    navButton("all", "▦", "月历") + navButton("agenda", "☷", "日程列表");
  return `<div class="shell calendar"><aside class="sidebar"><div class="brand"><span class="brandmark" aria-hidden="true">朝</span><div>${name}<small>${en}</small></div></div><nav class="side-nav" aria-label="应用导航">${nav}</nav><div class="side-bottom"><div class="side-note">把重要的事，放进日子里。</div><div class="profile"><span class="avatar">我</span><span>${space}<br><small>个人空间</small></span></div></div></aside><main class="main">${content}</main></div>`;
}
function monthEntries() {
  const prefix = iso(month).slice(0, 7);
  return read().filter((e) => e.date.startsWith(prefix));
}
function render() {
  closeDropdown();
  document.documentElement.style.setProperty("--accent", "#c56340");
  document.documentElement.style.setProperty("--soft", "#faeee8");
  document.title = identity[0];
  $("#workspace").innerHTML = shell(calendar());
  setStatus();
  bind();
}
function eventItems(date) {
  return read()
    .filter((e) => e.date === date)
    .sort((a, b) => a.start.localeCompare(b.start));
}
function agendaRow(e) {
  return `<button class="agenda-item" data-event="${e.id}"><small>${e.start} — ${e.end} · ${esc(e.category)}</small><strong>${esc(e.title)}</strong><small>${esc(e.location || "未设置地点")}</small></button>`;
}
function calendar() {
  let year = month.getFullYear(),
    m = month.getMonth(),
    start = new Date(year, m, 1),
    offset = (start.getDay() + 6) % 7,
    total = new Date(year, m + 1, 0).getDate(),
    cells = Math.ceil((total + offset) / 7) * 7;
  let selected = new Date(`${selectedDate}T12:00:00`),
    events = eventItems(selectedDate);
  return `<header class="topline"><div><p class="eyebrow">留出时间，好好生活</p><h1>让日子有点期待</h1><p class="subtitle">工作、生活，还有留给自己的时间。</p></div><button class="primary" data-new-event>＋ 新建日程</button></header>${read().length ? "" : `<div class="start-strip"><div><strong>从一个确定的小计划开始</strong><p>点一下日期，安排散步、阅读，或下一次见面。</p></div><button data-event-template="阅读时间">安排阅读时间 ↗</button></div>`}<div class="calendar-layout"><section class="calendar-board"><header class="calendar-head"><h2>${year} 年 ${m + 1} 月</h2><div class="month-nav"><button data-month="-1" aria-label="上个月">‹</button><button id="today">今天</button><button data-month="1" aria-label="下个月">›</button></div></header>${
    view === "agenda"
      ? `<div style="padding:0 24px 24px">${
          monthEntries()
            .sort(
              (a, b) =>
                a.date.localeCompare(b.date) || a.start.localeCompare(b.start),
            )
            .map(
              (e) => `<div><p class="micro">${e.date}</p>${agendaRow(e)}</div>`,
            )
            .join("") ||
          '<div class="welcome"><h2>这个月，还留着很多可能</h2><p>新建一个日程，为重要的事情留出时间。</p><button class="primary" data-new-event>添加第一个日程</button></div>'
        }</div>`
      : `<div class="weekdays">${["一", "二", "三", "四", "五", "六", "日"].map((d) => `<span>周${d}</span>`).join("")}</div><div class="month-grid">${Array.from(
          { length: cells },
          (_, i) => {
            let d = new Date(year, m, i - offset + 1),
              date = iso(d),
              items = eventItems(date);
            return `<button class="day ${d.getMonth() !== m ? "outside" : ""} ${date === today ? "today" : ""} ${date === selectedDate ? "chosen" : ""}" data-date="${date}" aria-label="${date}，${items.length}个日程"><span class="day-number">${d.getDate()}</span>${items
              .slice(0, 2)
              .map(
                (e) =>
                  `<span class="event-chip ${e.category === "工作" ? "work" : e.category === "生活" ? "life" : ""}">${e.start} ${esc(e.title)}</span>`,
              )
              .join(
                "",
              )}${items.length > 2 ? `<small>另 ${items.length - 2} 项</small>` : ""}</button>`;
          },
        ).join("")}</div>`
  }</section><aside class="aside-stack"><section class="panel"><small>${selected.toLocaleDateString("zh-CN", { month: "long", weekday: "long" })}</small><div class="agenda-date">${selected.getDate()}<span style="font-size:14px;letter-spacing:0;color:var(--muted);margin-left:10px">${selectedDate === today ? "今天" : ""}</span></div><div class="panel-heading" style="margin:20px 0 0"><h3>这一天的安排</h3><small>${events.length} 项</small></div>${events.map(agendaRow).join("") || '<p class="day-empty">还没有安排。<br>留白很好，也可以放进一件期待的事。</p>'}<button class="secondary" data-new-event style="width:100%;margin-top:20px;color:var(--accent)">＋ 添加日程</button></section><section class="panel"><h3>给生活一点位置</h3><p class="micro">一个小计划，也值得被认真安排。</p><div class="template-tags">${["阅读时间", "出门散步", "朋友聚餐"].map((t) => `<button data-event-template="${t}">${t} ＋</button>`).join("")}</div></section></aside></div>`;
}
async function load() {
  const sequence = ++loadSequence;
  loading = true;
  loadError = "";
  render();
  let from = new Date(month.getFullYear(), month.getMonth(), 1);
  let to = new Date(month.getFullYear(), month.getMonth() + 1, 1);
  {
    from.setDate(from.getDate() - ((from.getDay() + 6) % 7));
    const days =
      Math.ceil(
        (new Date(month.getFullYear(), month.getMonth() + 1, 0).getDate() +
          ((month.getDay() + 6) % 7)) /
          7,
      ) * 7;
    to = new Date(from);
    to.setDate(to.getDate() + days);
  }
  try {
    const result = await store.list(iso(from), iso(to));
    if (sequence !== loadSequence) return;
    rows = result;
    ready = true;
  } catch (error) {
    if (sequence !== loadSequence) return;
    ready = false;
    loadError = `记录加载失败：${error.message}`;
  } finally {
    if (sequence === loadSequence) {
      loading = false;
      render();
    }
  }
}
function bind() {
  document.querySelectorAll("[data-month]").forEach(
    (button) =>
      (button.onclick = () => {
        month = new Date(
          month.getFullYear(),
          month.getMonth() + Number(button.dataset.month),
          1,
        );
        selectedDate = iso(month);
        load();
      }),
  );
  $("#today")?.addEventListener("click", () => {
    month = new Date(now.getFullYear(), now.getMonth(), 1);
    selectedDate = today;
    load();
  });
}
$("#reload-data").onclick = load;
function route() {
  const next = location.hash.slice(1);
  view = ["all", "agenda"].includes(next) ? next : "all";
  render();
}
window.addEventListener("hashchange", route);
route();
load();
$("#workspace").addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button || !ready || loading) return;
  const data = button.dataset;
  if ("view" in data) {
    location.hash = data.view;
  } else if ("filter" in data) {
    filter = data.filter;
    render();
  } else if ("date" in data) {
    selectedDate = data.date;
    render();
  } else if ("newEvent" in data) eventForm();
  else if ("eventTemplate" in data) eventForm(null, data.eventTemplate);
  else if ("event" in data) eventForm(data.event);
});
function eventForm(id, title = "") {
  const existing = read().find((entry) => entry.id === id);
  const e = existing || {
    title,
    date: selectedDate,
    start: "19:00",
    end: "20:00",
    category: "生活",
    location: "",
    note: "",
  };
  const recordId = id || uid();
  let attempted = false;
  closeDropdown();
  showModal(
    `<form id="event-form"><div class="dialog-top"><div><h2>${existing ? "编辑日程" : "留出一段时间"}</h2><small>为重要的小事，留一个位置。</small></div><button type="button" data-close aria-label="关闭">✕</button></div><div class="form-grid"><label class="full">日程名称<input name="title" value="${esc(e.title)}" required placeholder="准备做点什么？" autofocus></label><label>日期<input name="date" type="date" value="${e.date}" required></label><div class="field"><span>分类</span>${dropdown("category", "分类", e.category, ["工作", "生活", "个人"])}</div><label>开始时间<input name="start" type="time" value="${e.start}" required></label><label>结束时间<input name="end" type="time" value="${e.end}" required></label><label class="full">地点<input name="location" value="${esc(e.location)}" placeholder="在家、线上，或某个地方（可不填）"></label><label class="full">备注<textarea name="note" placeholder="想提前记住的事（可不填）">${esc(e.note)}</textarea></label></div><p class="micro">单日定时日程，按本地时间记录。</p><div class="dialog-actions">${existing ? '<button type="button" class="danger" id="delete-event">删除日程</button>' : ""}<div class="inline"><button type="button" onclick="document.querySelector('dialog').close()">取消</button><button class="primary" type="submit">保存日程</button></div></div></form>`,
  );
  $("#event-form").oninput = () => $("[name=end]").setCustomValidity("");
  $("#event-form").onsubmit = (event) => {
    event.preventDefault();
    const record = {
      ...Object.fromEntries(new FormData(event.target)),
      id: recordId,
    };
    if (record.end <= record.start) {
      $("[name=end]").setCustomValidity("结束时间需要晚于开始时间");
      $("[name=end]").reportValidity();
      return;
    }
    submitForm(event.target, async () => {
      const actual = attempted ? await store.get(recordId) : null;
      const verified = attempted && store.same(actual, record);
      attempted = true;
      if (!verified) await store.save(record, !existing && !actual);
      selectedDate = record.date;
      month = new Date(`${record.date}T12:00:00`);
      month.setDate(1);
      $("#modal").close();
      await load();
      toast("日程已保存");
    });
  };
  $("#delete-event")?.addEventListener("click", () =>
    confirmDelete("删除这个日程？", async () => {
      await store.get(id);
      await store.remove(id);
      await load();
      toast("日程已删除");
    }),
  );
}
