import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const gameUrl = new URL("../src/app/catWorldGame.js", import.meta.url);

test("a waking cat looks calm before low mood cues can appear", async () => {
  const game = await readFile(gameUrl, "utf8");
  const moodCue = game.match(/drawCatMoodCue\([\s\S]*?\n  catIntentInfo\(/)?.[0] || "";

  assert.match(moodCue, /behavior\.key === "waking"/);
  assert.ok(moodCue.indexOf('behavior.key === "waking"') < moodCue.indexOf("moodScore < 38"));
  assert.match(game, /return \{ text: "刚睡醒", color: "#263047", background: "#fff07d" \}/);
  assert.match(game, /if \(behavior\.key === "waking"\) return "刚睡醒，先伸个懒腰。"/);
});

test("wake recovery slows roaming and favors stretch animations", async () => {
  const game = await readFile(gameUrl, "utf8");

  assert.match(game, /key === "waking"[\s\S]*?\? 0\.68/);
  assert.match(game, /key === "waking"[\s\S]*?\? 68/);
  assert.match(game, /behavior\.key === "waking"\) return Phaser\.Math\.RND\.pick\(\["stretch", "blink", "groom"\]\)/);
  assert.match(game, /我刚睡醒，先伸个懒腰，再慢慢想今天去哪里/);
});
