import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const pageUrl = new URL("../src/app/pages/CatWorldPage.vue", import.meta.url);
const gameUrl = new URL("../src/app/catWorldGame.js", import.meta.url);
const animationUrl = new URL("../src/app/catWorldIdleAnimation.js", import.meta.url);
const stylesUrl = new URL("../../app/static/styles.css", import.meta.url);

test("each cat can follow a stable personal habit inside the room", async () => {
  const [game, animation] = await Promise.all([
    readFile(gameUrl, "utf8"),
    readFile(animationUrl, "utf8"),
  ]);

  assert.match(game, /individualHabitTarget\(cat = \{\}, index = 0, behavior = \{\}\)/);
  assert.match(game, /chooseCatVisitPlan\(\[/);
  assert.match(game, /\{ kind: "habit", target: individualHabitTarget \}/);
  assert.match(game, /this\.spawnIndividualHabitBubble\(container, cat, visitPlan\.target\)/);
  assert.match(animation, /cat\.individualHabit\?\.animation/);
  assert.match(game, /activity: String\(traits\.activity \|\| "balanced"\)/);
  assert.match(game, /playCatMicroAnimation\(container, cat = \{\}, behavior = \{\}, forcedKind = ""\)/);
  assert.match(game, /catWorldIdleAnimationPlan\(cat, behavior, cycle\)\.kind/);
  assert.match(game, /microAnimationCycle/);
  assert.match(game, /kind === "chirp"/);
  assert.match(game, /kind === "heart"/);
  assert.match(game, /kind === "book"/);
  assert.match(game, /kind === "lookout"/);
  assert.match(game, /kind === "paw"/);
  assert.match(game, /kind === "hop"/);
  assert.match(game, /kind === "sparkle"/);
  assert.match(game, /kind === "question"/);
  assert.match(game, /kind === "yawn"/);
  assert.match(game, /kind === "ellipsis"/);
  assert.match(game, /kind === "huff"/);
  assert.match(animation, /adventurous:\s*Object\.freeze\(\["hop", "lookout", "tail", "stretch"\]\)/);
});

test("the cat profile exposes the individual habit without weakening active-state contrast", async () => {
  const [page, styles] = await Promise.all([
    readFile(pageUrl, "utf8"),
    readFile(stylesUrl, "utf8"),
  ]);

  assert.match(page, /cat\?\.individualHabit\?\.label/);
  assert.match(page, /<dt>个人小习惯<\/dt>/);
  assert.match(page, /<dt>陪学专长<\/dt>/);
  assert.match(page, /class="cat-world-cat-individual-habit"/);
  assert.match(page, /class="cat-world-cat-learning-style"/);
  assert.match(page, /class="cat-world-learning-style"/);
  assert.match(styles, /\.cat-world-cat-individual-habit[,{]/);
  assert.match(styles, /\.cat-world-cat-learning-style \{/);
  assert.match(styles, /\.cat-world-cat-chip\.active \.cat-world-cat-individual-habit,/);
  assert.match(styles, /\.cat-world-cat-chip\.active :where\([^)]+\)[^{]*\{\s*color: #fff;/s);
});
