import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { prepareApp, runtime } from "./fixtures/everyday-app.mjs";

for (const name of ["ledger", "notes", "calendar"])
  test(`${name}: built source association, account provider and SQLite persistence`, async (t) => {
    const fixture = await prepareApp(name);
    t.after(() => fixture.cleanup());
    const oldFetch = globalThis.fetch,
      oldWindow = globalThis.window;
    globalThis.fetch = (...args) => fixture.fetch(...args);
    globalThis.window = {};
    t.after(() => {
      globalThis.fetch = oldFetch;
      globalThis.window = oldWindow;
    });
    await assert.rejects(() => fixture.store.get("first"), /账号连接未就绪/);
    assert.equal(fixture.calls.length, 0);
    globalThis.window = { tiana: runtime() };
    const provider = globalThis.window.tiana.auth;
    const getToken = provider.getAccessToken;
    provider.getAccessToken = async () => {
      throw new Error("重新登录");
    };
    await assert.rejects(() => fixture.store.get("first"));
    assert.equal(fixture.calls.length, 0);
    provider.getAccessToken = getToken;
    const common = {
      id: "first",
      title: "中文 O'Reilly",
      note: "记下 100% 的生活",
    };
    const record =
      name === "ledger"
        ? {
            ...common,
            amount: 0.1,
            type: "expense",
            category: "餐饮",
            date: "2026-09-29",
          }
        : name === "notes"
          ? {
              ...common,
              body: "自己的正文",
              folder: "生活",
              pinned: false,
              updated: 1,
            }
          : {
              ...common,
              date: "2026-09-29",
              start: "09:00",
              end: "10:00",
              category: "生活",
              location: "窗边",
            };
    await fixture.store.save(record, true);
    assert.ok(fixture.store.same(await fixture.store.get(record.id), record));
    const write = fixture.calls.find((call) => call.sql.startsWith("INSERT"));
    assert.ok(!write.sql.includes(record.title));
    assert.ok(write.args.some((arg) => arg.value === record.title));
    const changed = { ...record, title: "更新后的标题" };
    fixture.failNext("after-write");
    await fixture.store.save(changed);
    assert.ok(fixture.store.same(await fixture.store.get(record.id), changed));
    assert.equal(
      fixture.calls.filter((call) => call.sql.startsWith("UPDATE")).length,
      1,
      "lost response verified without replay",
    );
    fixture.failNext("before-write");
    await assert.rejects(() =>
      fixture.store.save({ ...changed, title: "尚未保存" }),
    );
    assert.equal((await fixture.store.get(record.id)).title, changed.title);
    if (name === "ledger") {
      await fixture.store.save({ ...record, id: "second", amount: 0.2 }, true);
      const rows = await fixture.store.list("2026-09-01", "2026-10-01");
      assert.equal(
        rows.reduce((sum, row) => sum + row.cents, 0),
        30,
      );
      assert.equal(
        (await fixture.store.list("2026-10-01", "2026-11-01")).length,
        0,
      );
      fixture.db
        .prepare("INSERT INTO ledger_entries VALUES (?,?,?,?,?,?,?,?)")
        .run(
          "other-app",
          "foreign",
          "不可见",
          100,
          "expense",
          "生活",
          "2026-09-29",
          "",
        );
      assert.equal(
        (await fixture.store.list("2026-09-01", "2026-10-01")).length,
        2,
      );
    } else if (name === "notes") {
      for (let i = 0; i < 52; i++)
        await fixture.store.save(
          { ...record, id: `note-${i}`, title: `笔记 ${i}`, updated: i + 2 },
          true,
        );
      const first = await fixture.store.list(),
        next = await fixture.store.list("all", "", 50);
      assert.equal(first.rows.length, 50);
      assert.equal(first.more, true);
      assert.equal(next.rows.length, 3);
      assert.equal(
        new Set([...first.rows, ...next.rows].map((row) => row.id)).size,
        53,
      );
      const searched = await fixture.store.list("all", "自己的正文");
      assert.equal(searched.rows.length, 50);
      await fixture.store.save({ ...changed, pinned: true });
      assert.equal((await fixture.store.list("pinned")).rows[0].id, "first");
    } else {
      await fixture.store.save(
        { ...record, id: "next", date: "2026-10-01" },
        true,
      );
      assert.equal(
        (await fixture.store.list("2026-09-01", "2026-10-01")).length,
        1,
      );
      assert.equal(
        (await fixture.store.list("2026-09-28", "2026-10-05")).length,
        2,
      );
    }
    await fixture.store.remove(record.id);
    assert.equal(await fixture.store.get(record.id), null);
    const manifest = JSON.parse(
      await readFile(
        path.join(fixture.directory, "dist/tiana.app.json"),
        "utf8",
      ),
    );
    assert.equal(manifest.git_instance_id, "git-fixture");
    assert.equal(manifest.source_commit, fixture.commit);
    const module = await readFile(
      path.join(fixture.directory, "dist", manifest.entry),
      "utf8",
    );
    assert.ok(!module.includes("process.env.NODE_ENV"));
    for (const style of manifest.styles)
      await readFile(path.join(fixture.directory, "dist", style));
  });
