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
const money = (n) =>
  Number(n).toLocaleString("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
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
const identity = ["拾账", "MONEY, MADE CLEAR", "日常账本"];
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
    navButton("all", "▤", "收支明细") + navButton("analysis", "◷", "分类统计");
  return `<div class="shell ledger"><aside class="sidebar"><div class="brand"><span class="brandmark" aria-hidden="true">拾</span><div>${name}<small>${en}</small></div></div><nav class="side-nav" aria-label="应用导航">${nav}</nav><div class="side-bottom"><div class="side-note">每一笔，都让生活更清楚。</div><div class="profile"><span class="avatar">我</span><span>${space}<br><small>个人空间</small></span></div></div></aside><main class="main">${content}</main></div>`;
}
function monthControl() {
  return `<div class="month-nav"><button data-month="-1" aria-label="上个月">‹</button><strong>${month.getFullYear()} 年 ${month.getMonth() + 1} 月</strong><button data-month="1" aria-label="下个月">›</button></div>`;
}
function monthEntries() {
  const prefix = iso(month).slice(0, 7);
  return read().filter((e) => e.date.startsWith(prefix));
}
function render() {
  closeDropdown();
  document.documentElement.style.setProperty("--accent", "#315fda");
  document.documentElement.style.setProperty("--soft", "#eaf0ff");
  document.title = identity[0];
  $("#workspace").innerHTML = shell(ledger());
  setStatus();
  bind();
}
function ledger() {
  let entries = monthEntries(),
    expense =
      entries
        .filter((e) => e.type === "expense")
        .reduce((n, e) => n + Math.round(e.amount * 100), 0) / 100,
    income =
      entries
        .filter((e) => e.type === "income")
        .reduce((n, e) => n + Math.round(e.amount * 100), 0) / 100;
  const categories = ["餐饮", "交通", "购物", "生活", "其他"];
  const sums = categories
    .map((c) => [
      c,
      entries
        .filter((e) => e.type === "expense" && e.category === c)
        .reduce((n, e) => n + Math.round(e.amount * 100), 0) / 100,
    ])
    .filter(([, n]) => n > 0)
    .sort((a, b) => b[1] - a[1]);
  const chart = sums.length
    ? sums
        .map(
          ([c, n]) =>
            `<div class="bar-row"><div class="bar-meta"><span>${c}</span><span>¥ ${money(n)} · ${Math.round((n / expense) * 100)}%</span></div><div class="track"><i style="width:${(n / expense) * 100}%"></i></div></div>`,
        )
        .join("")
    : '<div class="empty-hint">记下第一笔支出后，这里会告诉你钱花在了哪里。</div>';
  let rows = entries
    .filter((e) => filter === "all" || e.type === filter)
    .sort((a, b) => b.date.localeCompare(a.date));
  return `<header class="topline"><div><p class="eyebrow">把生活，记清楚</p><h1>${view === "analysis" ? "每一笔的去向" : "我的日常账本"}</h1><p class="subtitle">从一杯咖啡开始，慢慢了解自己的生活。</p></div><button class="primary" data-add-ledger>＋ 记一笔</button></header><div class="ledger-layout"><section><div class="panel balance"><div><small>本月支出</small><div class="big"><span>¥</span>${money(expense)}</div>${monthControl()}</div><div class="balance-right"><div class="stat-row"><span>本月收入</span><strong class="green">+ ${money(income)}</strong></div><div class="stat-row"><span>本月结余</span><strong>${money(income - expense)}</strong></div></div></div>${
    view === "analysis"
      ? `<div class="panel"><div class="panel-heading"><h2>支出构成</h2><small>${entries.filter((e) => e.type === "expense").length} 笔支出</small></div>${chart}<p class="summary-foot">按所选月份的实际支出计算，收入不计入支出占比。</p></div>`
      : `<div class="panel"><div class="panel-heading"><h2>收支明细</h2><div class="filters" aria-label="收支筛选">${[
          ["all", "全部"],
          ["expense", "支出"],
          ["income", "收入"],
        ]
          .map(
            ([k, t]) =>
              `<button data-filter="${k}" class="${filter === k ? "selected" : ""}">${t}</button>`,
          )
          .join(
            "",
          )}</div></div>${rows.length ? `<table class="ledger-table"><thead><tr><th>账单</th><th class="category-column">分类</th><th style="text-align:right">金额</th><th><span class="muted">操作</span></th></tr></thead><tbody>${rows.map((e) => `<tr><td><div class="entry-title"><span class="category-icon">${e.type === "income" ? "↙" : { 餐饮: "◒", 交通: "↗", 购物: "▱", 生活: "⌂" }[e.category] || "◇"}</span><div>${esc(e.title)}<small>${esc(e.date)}</small></div></div></td><td class="category-column muted">${esc(e.category)}</td><td class="amount ${e.type === "income" ? "green" : ""}">${e.type === "income" ? "+" : "−"} ${money(e.amount)}</td><td><button class="edit-link" data-edit-ledger="${e.id}" aria-label="编辑${esc(e.title)}">编辑</button></td></tr>`).join("")}</tbody></table>` : `<div class="welcome"><div class="welcome-symbol">＋</div><h2>${entries.length ? "没有这类账单" : "今天的第一笔，从这里开始"}</h2><p>${entries.length ? "试试其他筛选，或添加一笔新的记录。" : "不用先建账户或设置预算。选一个分类，记下金额，就开始了。"}</p><button class="primary" data-add-ledger>记下第一笔</button></div>`}</div>`
  }</section><aside class="aside-stack"><section class="panel"><div class="panel-heading"><h3>从一笔小事开始</h3><small>快速记账</small></div><div class="quick-buttons">${[
    ["餐饮", "一杯咖啡"],
    ["交通", "一段通勤"],
    ["购物", "买点喜欢的"],
    ["收入", "一份收获"],
  ]
    .map(
      ([c, t]) =>
        `<button data-quick-ledger="${c}"><b>${c}</b><small>${t}</small></button>`,
    )
    .join(
      "",
    )}</div><p class="micro">分类已选好，填个金额就能记。</p></section><section class="panel"><h3>钱花在了哪里</h3>${chart}</section><p class="micro" style="padding:0 8px">每一笔小记录，都是更了解自己的开始。</p></aside></div>`;
}
async function load() {
  const sequence = ++loadSequence;
  loading = true;
  loadError = "";
  render();
  let from = new Date(month.getFullYear(), month.getMonth(), 1);
  let to = new Date(month.getFullYear(), month.getMonth() + 1, 1);

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
  view = ["all", "analysis"].includes(next) ? next : "all";
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
  } else if ("addLedger" in data) ledgerForm();
  else if ("quickLedger" in data) ledgerForm(null, data.quickLedger);
  else if ("editLedger" in data) ledgerForm(data.editLedger);
});
function ledgerForm(id, category = "餐饮") {
  const existing = read().find((entry) => entry.id === id);
  const e = existing || {
    title: "",
    amount: "",
    type: category === "收入" ? "income" : "expense",
    category,
    date: today,
    note: "",
  };
  const recordId = id || uid();
  let attempted = false;
  closeDropdown();
  showModal(
    `<form id="entry-form"><div class="dialog-top"><div><h2>${existing ? "编辑账单" : "记下这一笔"}</h2><small>不用复杂，记清楚就好。</small></div><button type="button" data-close aria-label="关闭">✕</button></div><div class="form-grid"><div class="field"><span>类型</span>${dropdown(
      "type",
      "类型",
      e.type,
      [
        ["expense", "支出"],
        ["income", "收入"],
      ],
    )}</div><label>金额（元）<input name="amount" type="number" min="0.01" step="0.01" required value="${e.amount}" placeholder="0.00" autofocus></label><label class="full">这笔是什么<input name="title" value="${esc(e.title)}" placeholder="例如：午后的咖啡（可不填）"></label><div class="field"><span>分类</span>${dropdown("category", "分类", e.category, e.type === "income" ? ["收入"] : ["餐饮", "交通", "购物", "生活", "其他"])}</div><label>日期<input name="date" type="date" value="${e.date}" required></label><label class="full">备注<input name="note" value="${esc(e.note)}" placeholder="再记一点细节（可不填）"></label></div><div class="dialog-actions">${existing ? '<button type="button" class="danger" id="delete-entry">删除账单</button>' : ""}<div class="inline"><button type="button" onclick="document.querySelector('dialog').close()">取消</button><button class="primary" type="submit">保存账单</button></div></div></form>`,
  );
  $("[name=type]").onchange = (event) => {
    const categories =
      event.target.value === "income"
        ? ["收入"]
        : ["餐饮", "交通", "购物", "生活", "其他"];
    $("[name=category]").closest(".dropdown").outerHTML = dropdown(
      "category",
      "分类",
      categories[0],
      categories,
    );
  };
  $("#entry-form").onsubmit = (event) => {
    event.preventDefault();
    const fields = Object.fromEntries(new FormData(event.target));
    const record = {
      ...fields,
      id: recordId,
      amount: Math.round(Number(fields.amount) * 100) / 100,
      title: fields.title.trim() || fields.category,
    };
    submitForm(event.target, async () => {
      const actual = attempted ? await store.get(recordId) : null;
      const verified = attempted && store.same(actual, record);
      attempted = true;
      if (!verified) await store.save(record, !existing && !actual);
      month = new Date(`${record.date}T12:00:00`);
      month.setDate(1);
      $("#modal").close();
      await load();
      toast("账单已保存");
    });
  };
  $("#delete-entry")?.addEventListener("click", () =>
    confirmDelete("删除这笔账单？", async () => {
      await store.get(id);
      await store.remove(id);
      await load();
      toast("账单已删除");
    }),
  );
}
