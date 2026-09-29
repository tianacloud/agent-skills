import "./style.css";
import { $, esc, toast, confirmDelete } from "./ui.js";
import { dropdown, closeDropdown } from "./dropdown.js";
import { newId } from "./id.js";
import * as store from "./store.js";
const uid = newId;
let view = "all",
  query = "",
  selectedNote = null;
let rows = [],
  loading = true,
  ready = false,
  loadError = "",
  loadSequence = 0;
const read = () => rows;
const identity = ["一页", "ROOM FOR THOUGHT", "我的记事本"];
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
    navButton("all", "▤", "全部笔记") +
    navButton("pinned", "⌑", "置顶笔记") +
    ["生活", "工作", "灵感"].map((n) => navButton(n, "▱", n)).join("");
  return `<div class="shell notes"><aside class="sidebar"><div class="brand"><span class="brandmark" aria-hidden="true">页</span><div>${name}<small>${en}</small></div></div><nav class="side-nav" aria-label="应用导航">${nav}</nav><div class="side-bottom"><div class="side-note">给想到的事，留一页空间。</div><div class="profile"><span class="avatar">我</span><span>${space}<br><small>个人空间</small></span></div></div></aside><main class="main">${content}</main></div>`;
}
function render() {
  closeDropdown();
  document.documentElement.style.setProperty("--accent", "#7457a1");
  document.documentElement.style.setProperty("--soft", "#f1ecf8");
  document.title = identity[0];
  $("#workspace").innerHTML = shell(notes());
  setStatus();
  bind();
}
const templates = {
  blank: { title: "", body: "", folder: "生活" },
  daily: {
    title: "今天，想记下这些",
    body: "今天的一件小事\n\n\n此刻的心情\n\n\n想留给明天的话\n",
    folder: "生活",
  },
  meeting: {
    title: "会议记录",
    body: "讨论主题\n\n\n关键结论\n\n\n接下来要做的事\n☐ \n",
    folder: "工作",
  },
  idea: {
    title: "一个新想法",
    body: "突然想到\n\n\n为什么值得试试\n\n\n可以迈出的第一步\n",
    folder: "灵感",
  },
};
function noteItems() {
  return read();
}
function noteCards() {
  return (
    noteItems()
      .map(
        (n) =>
          `<button class="note-card ${n.id === selectedNote ? "selected" : ""}" data-note="${n.id}"><strong>${n.pinned ? "⌑ " : ""}${esc(n.title || "无标题笔记")}</strong><p>${esc(n.body || "还没有写下内容")}</p><small>${esc(n.folder)} · ${new Date(n.updated).toLocaleDateString("zh-CN", { month: "long", day: "numeric" })}</small></button>`,
      )
      .join("") ||
    `<div class="empty-hint">${query ? "没有找到匹配的笔记。" : view === "pinned" ? "把常用的笔记置顶，就能在这里快速找到。" : "这里等着你的第一篇笔记。"}</div>`
  );
}
function notes() {
  let n = read().find((n) => n.id === selectedNote);
  return `<header class="notes-top"><div><p class="eyebrow">思绪有地方落下</p><h1>${view === "all" ? "全部笔记" : view === "pinned" ? "置顶笔记" : esc(view)}</h1></div><div class="inline"><input id="note-search" type="search" aria-label="搜索笔记" placeholder="搜索标题或内容" value="${esc(query)}"><button class="primary" data-template="blank">＋ 新建</button></div></header><div class="notes-workspace ${n ? "has-note" : ""}"><section class="note-list"><div class="note-list-head"><span id="note-count">${noteItems().length} 篇笔记</span><span>置顶优先 · 最近编辑</span></div><div id="note-cards">${noteCards()}</div>${hasMore ? '<button class="secondary load-more" id="load-more">加载更多</button>' : ""}</section><section class="editor ${n ? "has-content" : ""}">${
    n
      ? `<div class="editor-toolbar"><div class="inline"><button class="mobile-back" id="notes-back">‹ 列表</button><span id="save-state" role="status">${saving ? "正在保存…" : saveError ? "有修改尚未确认" : dirty ? "等待保存…" : "已保存"}</span><button id="recover-save" class="save-recover" hidden>检查保存状态</button></div><div><button id="pin-note">${n.pinned ? "取消置顶" : "置顶"}</button><button class="danger" id="delete-note">删除</button></div></div><input class="editor-title" id="note-title" value="${esc(n.title)}" placeholder="给这一页起个名字" aria-label="笔记标题"><div class="editor-meta"><div class="inline"><span>收纳到</span>${dropdown("folder", "收纳到", n.folder, ["生活", "工作", "灵感"], "note-folder", true)}</div><span id="word-count">${n.body.length} 字 · 输入后自动保存</span></div><textarea id="note-body" class="editor-body" placeholder="从想到的第一句话开始……" aria-label="笔记内容">${esc(n.body)}</textarea>`
      : `<div class="welcome"><div class="welcome-symbol">页</div><h2>${read().length ? "打开一页，继续写" : "第一篇，不用想好才开始"}</h2><p>记一个念头，留一份会议记录，或者只是写下今天。</p><div class="template-list">${[
          ["blank", "＋", "空白一页", "没有格式，想到什么就写什么"],
          ["daily", "☀", "随手记", "从今天的一件小事开始"],
          ["meeting", "▤", "会议记录", "主题、结论与下一步"],
          ["idea", "◇", "灵感便笺", "把一闪而过的念头留住"],
        ]
          .map(
            ([k, i, t, s]) =>
              `<button data-template="${k}"><span class="template-number">${i}</span><span><b>${t}</b><small>${s}</small></span><span style="margin-left:auto">↗</span></button>`,
          )
          .join(
            "",
          )}</div><p class="micro">选择后生成可编辑草稿，写下的内容会自动保存。</p></div>`
  }</section></div>`;
}
let hasMore = false,
  dirty = false,
  saving = null,
  saveError = "",
  isNewNote = false,
  editVersion = 0;
let saveTimer,
  searchTimer,
  currentHash = location.hash,
  navigating = false;
function updateSaveState() {
  const status = $("#save-state");
  if (!status) return;
  status.textContent =
    saveError || (saving ? "正在保存…" : dirty ? "等待保存…" : "已保存");
  status.classList.toggle("save-warning", Boolean(saveError));
  $("#recover-save").hidden = !saveError;
  $("#recover-save").textContent = "检查并保存";
}
function refreshCards() {
  rows.sort(
    (a, b) =>
      Number(b.pinned) - Number(a.pinned) ||
      b.updated - a.updated ||
      a.id.localeCompare(b.id),
  );
  $("#note-cards").innerHTML = noteCards();
  $("#note-count").textContent =
    `${rows.length} 篇${hasMore ? "已加载" : ""}笔记`;
}
function saveNote() {
  const note = rows.find((note) => note.id === selectedNote);
  if (!note) return;
  note.title = $("#note-title").value;
  note.body = $("#note-body").value;
  note.folder = $("#note-folder").value;
  note.updated = Date.now();
  dirty = true;
  editVersion++;
  $("#word-count").textContent = `${note.body.length} 字 · 输入后自动保存`;
  refreshCards();
  updateSaveState();
  clearTimeout(saveTimer);
  if (!saveError) saveTimer = setTimeout(flushNote, 600);
}
async function flushNote() {
  clearTimeout(saveTimer);
  if (saving) {
    await saving;
    return saveError ? false : dirty ? flushNote() : true;
  }
  if (saveError) {
    toast("请先检查当前笔记的保存状态。");
    return false;
  }
  if (!dirty || !selectedNote) return true;
  const snapshot = { ...rows.find((note) => note.id === selectedNote) };
  const version = editVersion;
  saving = (async () => {
    try {
      await store.save(snapshot, isNewNote);
      isNewNote = false;
      if (editVersion === version) dirty = false;
    } catch (error) {
      saveError = error.message;
    }
  })();
  updateSaveState();
  await saving;
  saving = null;
  updateSaveState();
  if (!saveError && dirty) return flushNote();
  return !saveError;
}
async function recoverSave() {
  const button = $("#recover-save");
  button.disabled = true;
  try {
    const actual = await store.get(selectedNote);
    const expected = rows.find((note) => note.id === selectedNote);
    if (store.same(actual, expected)) {
      dirty = false;
      isNewNote = false;
      saveError = "";
    } else {
      isNewNote = !actual;
      saveError = "";
      await flushNote();
    }
  } catch (error) {
    saveError = error.message;
  } finally {
    button.disabled = false;
    updateSaveState();
  }
}
async function loadList({ more = false, search = false } = {}) {
  const sequence = ++loadSequence;
  loading = true;
  loadError = "";
  setStatus();
  try {
    const result = await store.list(view, query, more ? rows.length : 0);
    if (sequence !== loadSequence) return;
    rows = more ? [...rows, ...result.rows] : result.rows;
    hasMore = result.more;
    ready = true;
    if (!rows.some((note) => note.id === selectedNote)) selectedNote = null;
  } catch (error) {
    if (sequence !== loadSequence) return;
    loadError = `笔记加载失败：${error.message}`;
  } finally {
    if (sequence === loadSequence) {
      loading = false;
      render();
      updateSaveState();
      if (search) {
        $("#note-search").focus();
      }
    }
  }
}
async function createNote(template) {
  if (!(await flushNote())) return;
  const note = {
    ...templates[template],
    id: uid(),
    pinned: false,
    updated: Date.now(),
  };
  if (["生活", "工作", "灵感"].includes(view)) note.folder = view;
  rows.unshift(note);
  selectedNote = note.id;
  view = "all";
  query = "";
  history.replaceState(null, "", "#all");
  currentHash = "#all";
  dirty = true;
  isNewNote = true;
  editVersion++;
  render();
  $("#note-title").focus();
  await flushNote();
}
function bind() {
  for (const id of ["note-title", "note-body", "note-folder"])
    $("#" + id)?.addEventListener("input", saveNote);
  $("#recover-save")?.addEventListener("click", recoverSave);
  $("#load-more")?.addEventListener("click", async () => {
    if (await flushNote()) await loadList({ more: true });
  });
  $("#note-search")?.addEventListener("input", (event) => {
    const nextQuery = event.target.value;
    clearTimeout(searchTimer);
    searchTimer = setTimeout(async () => {
      if (!(await flushNote())) return;
      query = nextQuery;
      selectedNote = null;
      await loadList({ search: true });
    }, 300);
  });
  $("#pin-note")?.addEventListener("click", async () => {
    if (!(await flushNote())) return;
    const note = rows.find((note) => note.id === selectedNote);
    note.pinned = !note.pinned;
    note.updated = Date.now();
    dirty = true;
    editVersion++;
    render();
    await flushNote();
  });
  $("#notes-back")?.addEventListener("click", async () => {
    if (await flushNote()) {
      selectedNote = null;
      render();
    }
  });
  $("#delete-note")?.addEventListener("click", async () => {
    if (!(await flushNote())) return;
    const id = selectedNote;
    closeDropdown();
    confirmDelete("删除这篇笔记？", async () => {
      await store.get(id);
      await store.remove(id);
      selectedNote = null;
      await loadList();
      toast("笔记已删除");
    });
  });
}
async function navigate(action) {
  if (navigating) return;
  navigating = true;
  try {
    if (await flushNote()) await action();
  } finally {
    navigating = false;
  }
}
$("#workspace").addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button || !ready || loading) return;
  const data = button.dataset;
  if ("view" in data)
    navigate(async () => {
      view = data.view;
      query = "";
      selectedNote = null;
      currentHash = "#" + encodeURIComponent(view);
      history.pushState(null, "", currentHash);
      await loadList();
    });
  else if ("template" in data) navigate(() => createNote(data.template));
  else if ("note" in data)
    navigate(() => {
      selectedNote = data.note;
      render();
    });
});
async function route() {
  if (!(await flushNote())) {
    history.replaceState(null, "", currentHash || "#all");
    return;
  }
  let next;
  try {
    next = decodeURIComponent(location.hash.slice(1));
  } catch {
    next = "all";
  }
  view = ["all", "pinned", "生活", "工作", "灵感"].includes(next)
    ? next
    : "all";
  currentHash = location.hash;
  selectedNote = null;
  query = "";
  await loadList();
}
$("#reload-data").onclick = () => navigate(() => loadList());
window.addEventListener("hashchange", route);
window.addEventListener("beforeunload", (event) => {
  if (dirty || saving) {
    event.preventDefault();
    event.returnValue = "";
  }
});
render();
route();
