import test from "node:test";
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { readFile, mkdir } from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";
import { prepareApp } from "./fixtures/everyday-app.mjs";

test("application templates: browser CRUD, autosave recovery, custom menus and mobile layouts", async (t) => {
  const fixtures = {};
  for (const name of ["ledger", "notes", "calendar"])
    fixtures[name] = await prepareApp(name);
  t.after(async () => {
    for (const fixture of Object.values(fixtures)) await fixture.cleanup();
  });
  const server = createServer(async (req, res) => {
    const url = new URL(req.url, "http://fixture.test");
    const [name, ...parts] = url.pathname.slice(1).split("/");
    const fixture = fixtures[name];
    if (!fixture) {
      res.writeHead(404).end();
      return;
    }
    try {
      if (!parts.length || !parts[0]) {
        res.setHeader("content-type", "text/html; charset=utf-8");
        res.end(
          `<!doctype html><html lang="zh-CN"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/${name}/assets/app.css"><div id="app"></div><script>window.tiana={auth:{getAccessToken:async()=> 'fixture-access-token'},connection:async()=>({origin:'https://ep-00000000000000000000000000.fixture.test',sql_api:'hrana-v3'})}</script><script type="module" src="/${name}/assets/app.js"></script></html>`,
        );
      } else {
        const file = parts.join("/");
        res.setHeader(
          "content-type",
          file.endsWith(".css") ? "text/css" : "text/javascript",
        );
        res.end(await readFile(path.join(fixture.directory, "dist", file)));
      }
    } catch (error) {
      res.writeHead(500).end(error.message);
    }
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  t.after(() => new Promise((resolve) => server.close(resolve)));
  const browser = await chromium.launch();
  t.after(() => browser.close());
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
  });
  page.setDefaultTimeout(10000);
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.route(
    "https://ep-00000000000000000000000000.fixture.test/**",
    async (route) => {
      const name = new URL(page.url()).pathname.split("/")[1];
      try {
        const body = await fixtures[name].handle(
          route.request().postDataBuffer(),
        );
        await route.fulfill({
          status: 200,
          headers: {
            "content-type": "application/vnd.tiana.fetch.v1",
            "cache-control": "no-store",
            "access-control-allow-origin": "*",
          },
          body: Buffer.from(body),
        });
      } catch {
        await route.abort("failed");
      }
    },
  );
  const visit = async (name, hash = "") => {
    await page.goto(`http://127.0.0.1:${server.address().port}/${name}${hash}`);
    await page.waitForFunction(() => !document.querySelector(".shell").inert);
  };
  const ready = async () => {
    await page.locator("dialog").waitFor({ state: "hidden" });
    await page.waitForFunction(() => !document.querySelector(".shell").inert);
  };
  const saved = () =>
    page.waitForFunction(
      () => document.querySelector("#save-state")?.textContent === "已保存",
    );
  const choose = async (label, value) => {
    await page.getByRole("combobox", { name: label, exact: true }).click();
    await page.getByRole("option", { name: value, exact: true }).click();
  };
  await visit("ledger", "#analysis");
  assert.equal(await page.locator("h1").innerText(), "每一笔的去向");
  await page.locator("[data-view=all]").click();
  await page.locator('[data-quick-ledger="餐饮"]').click();
  await page.locator("[name=amount]").fill("12.30");
  await page.locator("[name=title]").fill("午饭 O'Reilly");
  await choose("类型", "收入");
  assert.equal(await page.locator("[name=category]").inputValue(), "收入");
  await choose("类型", "支出");
  await choose("分类", "生活");
  await page.getByRole("button", { name: "保存账单", exact: true }).click();
  await ready();
  assert.equal(
    fixtures.ledger.db.prepare("SELECT cents FROM ledger_entries").get().cents,
    1230,
  );
  await page.reload();
  await ready();
  await page.locator("[data-edit-ledger]").click();
  await page.locator("[name=amount]").fill("0.20");
  fixtures.ledger.failNext("after-write");
  await page.getByRole("button", { name: "保存账单", exact: true }).click();
  await ready();
  assert.equal(
    fixtures.ledger.db.prepare("SELECT cents FROM ledger_entries").get().cents,
    20,
  );
  assert.equal(
    fixtures.ledger.calls.filter((call) => call.sql.startsWith("UPDATE"))
      .length,
    1,
  );
  await page.locator("[data-edit-ledger]").click();
  await page.locator("#delete-entry").click();
  await page.getByRole("button", { name: "确认删除" }).click();
  await ready();
  assert.equal(
    fixtures.ledger.db.prepare("SELECT count(*) AS n FROM ledger_entries").get()
      .n,
    0,
  );

  await visit("notes");
  await page.locator("[data-template=daily]").click();
  await saved();
  await page.locator("#note-title").fill("我的第一篇笔记");
  await page.locator("#note-body").fill("中文正文，保留细节。");
  await choose("收纳到", "工作");
  await saved();
  await page.reload();
  await ready();
  await page.locator(".note-card").click();
  assert.equal(
    await page.locator("#note-body").inputValue(),
    "中文正文，保留细节。",
  );
  const pause = fixtures.notes.pauseNextWrite();
  await page.locator("#note-body").fill("第一份保存中的内容");
  await pause.started;
  await page.locator("#note-body").fill("保存期间继续输入的最终内容");
  pause.resume();
  await saved();
  assert.equal(
    fixtures.notes.db.prepare("SELECT body FROM notebook_notes").get().body,
    "保存期间继续输入的最终内容",
  );
  fixtures.notes.failNext("before-write");
  await page.locator("#note-body").fill("失联时留在编辑区");
  await page.locator("#recover-save").waitFor({ state: "visible" });
  assert.equal(
    await page.locator("#note-body").inputValue(),
    "失联时留在编辑区",
  );
  const beforeRecover = fixtures.notes.calls.filter((call) =>
    call.sql.startsWith("UPDATE"),
  ).length;
  await page.locator("#recover-save").click();
  await saved();
  assert.equal(
    fixtures.notes.calls.filter((call) => call.sql.startsWith("UPDATE")).length,
    beforeRecover + 1,
  );
  fixtures.notes.failNext("after-write");
  await page.locator("#note-body").fill("已经提交，响应丢失");
  await saved();
  assert.equal(
    fixtures.notes.db.prepare("SELECT body FROM notebook_notes").get().body,
    "已经提交，响应丢失",
  );
  await page.locator("#pin-note").click();
  await saved();
  await page.locator("[data-view=pinned]").click();
  await page.waitForFunction(
    () => document.querySelector("h1")?.textContent === "置顶笔记",
  );
  await ready();
  assert.equal(await page.locator(".note-card").count(), 1);
  await page.locator("#note-search").fill("响应丢失");
  await page.waitForFunction(
    () =>
      document.querySelector("#note-search").value === "响应丢失" &&
      !document.querySelector(".shell").inert,
  );
  await page.locator(".note-card").click();
  await page.locator("#delete-note").click();
  await page.getByRole("button", { name: "确认删除" }).click();
  await ready();
  assert.equal(
    fixtures.notes.db.prepare("SELECT count(*) AS n FROM notebook_notes").get()
      .n,
    0,
  );

  await visit("calendar", "#agenda");
  assert.equal(
    await page.locator(".side-nav .selected").innerText(),
    "☷\n日程列表",
  );
  await page.locator("[data-view=all]").click();
  await page.locator(".day:not(.outside)").first().click();
  await page.locator("[data-new-event]").first().click();
  await page.locator("[name=title]").fill("新日程");
  await page.locator("[name=start]").fill("10:00");
  await page.locator("[name=end]").fill("09:00");
  await page.getByRole("button", { name: "保存日程" }).click();
  assert.ok(await page.locator("dialog").isVisible());
  await page.locator("[name=end]").fill("11:00");
  await choose("分类", "个人");
  await page.getByRole("button", { name: "保存日程" }).click();
  await ready();
  assert.equal(
    fixtures.calendar.db.prepare("SELECT category FROM calendar_events").get()
      .category,
    "个人",
  );
  await page.locator("[data-event]").first().click();
  await page.locator("[name=title]").fill("修改后的日程");
  await page.getByRole("button", { name: "保存日程" }).click();
  await ready();
  assert.equal(
    fixtures.calendar.db.prepare("SELECT title FROM calendar_events").get()
      .title,
    "修改后的日程",
  );
  await page.locator("[data-event]").first().click();
  await page.locator("#delete-event").click();
  await page.getByRole("button", { name: "确认删除" }).click();
  await ready();
  assert.equal(
    fixtures.calendar.db
      .prepare("SELECT count(*) AS n FROM calendar_events")
      .get().n,
    0,
  );

  await mkdir("dist/app-previews", { recursive: true });
  for (const name of ["ledger", "notes", "calendar"]) {
    await visit(name);
    if (name === "notes") {
      await page.locator("[data-template=meeting]").click();
      await saved();
      await page.locator("#note-body").click();
    }
    await page.screenshot({
      path: `dist/app-previews/${name}.png`,
      fullPage: true,
    });
    for (const width of [390, 320]) {
      await page.setViewportSize({ width, height: 844 });
      assert.ok(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
        `${name} page fits ${width}`,
      );
    }
    if (name === "notes")
      await page.getByRole("combobox", { name: "收纳到" }).click();
    else {
      await page
        .locator(name === "ledger" ? "[data-add-ledger]" : "[data-new-event]")
        .first()
        .click();
      await page.getByRole("combobox", { name: "分类", exact: true }).click();
    }
    const bounds = await page
      .locator(".dropdown-menu:popover-open")
      .boundingBox();
    assert.ok(
      bounds.x >= 0 &&
        bounds.x + bounds.width <= 320 &&
        bounds.y + bounds.height <= 844,
    );
    await page.keyboard.press("Escape");
    if (name !== "notes") {
      assert.ok(await page.locator("dialog").isVisible());
      await page.locator("[data-close]").click();
    }
    await page.setViewportSize({ width: 1440, height: 1000 });
  }
  assert.deepEqual(errors, []);
});
