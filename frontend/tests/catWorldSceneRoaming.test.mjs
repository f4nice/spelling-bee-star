import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const pageUrl = new URL("../src/app/pages/CatWorldPage.vue", import.meta.url);
const stylesUrl = new URL("../../app/static/styles.css", import.meta.url);

test("autonomous room changes are announced without interrupting room controls", async () => {
  const page = await readFile(pageUrl, "utf8");

  assert.match(page, /announceSceneMoves\(payload\.value\)/);
  assert.match(page, /nextPayload\?\.state\?\.sceneMoves/);
  assert.match(page, /moves\.length === 1/);
  assert.match(page, /另外还有 \$\{moves\.length - 1\} 只猫咪去了别的房间/);
  assert.match(page, /class="cat-world-notice" aria-live="polite"/);
});

test("scene map controls the whole room workspace and scrolls on narrow screens", async () => {
  const [page, styles] = await Promise.all([
    readFile(pageUrl, "utf8"),
    readFile(stylesUrl, "utf8"),
  ]);
  const sceneDockIndex = page.indexOf('class="cat-world-scene-dock"');
  const roomPanelIndex = page.indexOf('class="cat-world-room-panel panel"');

  assert.ok(sceneDockIndex > 0);
  assert.ok(roomPanelIndex > sceneDockIndex);
  assert.match(styles, /\.cat-world-scene-dock \{[\s\S]*?grid-column: 1 \/ -1;/);
  assert.match(styles, /\.cat-world-scene-dock \.cat-world-scene-tabs \{[\s\S]*?overflow-x: auto;/);
  assert.match(
    styles,
    /\.cat-world-scene-dock \.cat-world-scene-tabs button:not\(:disabled\):hover,[\s\S]*?color: #fff;/,
  );
});
