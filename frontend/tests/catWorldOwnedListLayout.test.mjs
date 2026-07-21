import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const stylesUrl = new URL("../../app/static/styles.css", import.meta.url);

test("owned food items keep their content height when the category has one item", async () => {
  const styles = await readFile(stylesUrl, "utf8");
  const ownedListRule = styles.match(/\.cat-world-owned-list\s*\{([^}]*)\}/)?.[1] || "";

  assert.match(ownedListRule, /grid-auto-rows:\s*max-content\s*;/);
  assert.match(ownedListRule, /align-content:\s*start\s*;/);
});
