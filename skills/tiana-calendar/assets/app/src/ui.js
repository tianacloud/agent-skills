export const $ = (selector, root = document) => root.querySelector(selector);
export const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ],
  );
export const iso = (date) =>
  `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
export const now = new Date();
export const today = iso(now);
export function toast(message) {
  $("#toast").textContent = message;
  $("#toast").classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => $("#toast").classList.remove("show"), 3500);
}
export function showModal(html) {
  $("#modal").innerHTML = html;
  $("#modal").showModal();
  $("[data-close]", $("#modal"))?.addEventListener("click", () =>
    $("#modal").close(),
  );
}
export function formMessage(message) {
  let element = $(".form-message", $("#modal"));
  if (!element) {
    element = document.createElement("p");
    element.className = "form-message";
    element.setAttribute("role", "status");
    $("#modal").append(element);
  }
  element.textContent = message;
}
export async function submitForm(form, action) {
  if (form.dataset.saving) return;
  form.dataset.saving = "true";
  const controls = [...form.querySelectorAll("button,input,textarea")];
  controls.forEach((control) => (control.disabled = true));
  const cancel = (event) => event.preventDefault();
  $("#modal").addEventListener("cancel", cancel);
  formMessage("正在保存…");
  try {
    await action();
  } catch (error) {
    formMessage(error.message);
  } finally {
    delete form.dataset.saving;
    controls.forEach((control) => (control.disabled = false));
    $("#modal").removeEventListener("cancel", cancel);
  }
}
export function confirmDelete(title, action) {
  $("#modal").close();
  showModal(
    `<form id="delete-form"><div class="dialog-top"><h2>${esc(title)}</h2><button type="button" data-close aria-label="关闭">✕</button></div><p class="subtitle">这条记录将从当前应用中删除。</p><div class="dialog-actions"><button type="button" id="confirm-cancel">取消</button><button class="primary" type="submit">确认删除</button></div></form>`,
  );
  $("#confirm-cancel").onclick = () => $("#modal").close();
  $("#delete-form").onsubmit = (event) => {
    event.preventDefault();
    submitForm(event.target, async () => {
      await action();
      $("#modal").close();
    });
  };
}
