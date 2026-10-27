import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { catPortraitModel } from "../src/app/catWorldPortrait.js";
import { catWorldProductIconSpec } from "../src/app/catWorldProductIcons.js";

const source = (await readFile(new URL("../src/app/catWorldGame.js", import.meta.url), "utf8")).replace(/\r\n/g, "\n");

function constant(name) {
  const start = source.indexOf(`const ${name} = {`);
  const end = source.indexOf("\n};", start) + 3;
  assert.ok(start >= 0 && end > start);
  return Function("GAME_WIDTH", `${source.slice(start, end)}; return ${name}`)(1600);
}

function sceneMethod(name, dependencies = {}) {
  const start = source.indexOf(`\n  ${name}(`);
  const end = source.indexOf("\n  }\n", start) + 5;
  assert.ok(start >= 0 && end > start);
  return Function(...Object.keys(dependencies), `return class { ${source.slice(start, end)} }`)(...Object.values(dependencies));
}

test("all Halloween objects have room geometry and independent product icons", () => {
  const decor = constant("DECOR_SPECS");
  const toys = constant("ROOM_TOY_TARGETS");
  for (const [id, spec, category, icon] of [
    ["halloween-pumpkin-lantern", decor["halloween-pumpkin-lantern"], "decor", "flame"],
    ["halloween-candy-bowl", decor["halloween-candy-bowl"], "decor", "candy"],
    ["halloween-ghost-plush", toys["halloween-ghost-plush"], "toy", "ghost"],
  ]) {
    assert.ok(spec.width > 0 && spec.height > 0, id);
    assert.ok(Number.isFinite(spec.defaultX) && Number.isFinite(spec.defaultY), id);
    assert.equal(catWorldProductIconSpec({ id, category }).icon, icon);
  }
  assert.equal(catWorldProductIconSpec({ id: "halloween-2026-blind-box", category: "blind-box" }).icon, "ghost");
});

test("Halloween room cats and portraits share distinct palettes instead of falling back to Mimi", () => {
  const colors = constant("CAT_COLORS");
  for (const breedId of ["festival-pumpkin", "festival-ghost"]) {
    const portrait = catPortraitModel({ id: `${breedId}-individual`, breedId, patternKey: "white-socks", featureKey: "pink-paws" });
    assert.notEqual(colors[breedId].body, colors.mimi.body);
    for (const part of ["body", "shade", "stripe", "belly"]) {
      assert.equal(portrait.style[`--cat-portrait-${part}`], `#${colors[breedId][part].toString(16).padStart(6, "0")}`);
    }
    assert.equal(portrait.pattern, "white-socks");
    assert.equal(portrait.feature, "pink-paws");
  }
  assert.notEqual(colors["festival-pumpkin"].body, colors["festival-ghost"].body);
});

test("Halloween decor and plush produce real drawing commands rather than only hitboxes", () => {
  const commands = [];
  const graphics = new Proxy({}, { get: (_target, name) => (...args) => { commands.push([name, ...args]); return graphics; } });
  const dependencies = {
    INK: 0x2c2f3a,
    makeLocalGraphics: () => graphics,
    drawPixelRect: (...args) => commands.push(["pixel", ...args.slice(1)]),
    WINDOW_DECOR_VARIANTS: {},
  };
  const DecorScene = sceneMethod("drawDecorShape", dependencies);
  const scene = new DecorScene();
  for (const id of ["halloween-pumpkin-lantern", "halloween-candy-bowl"]) {
    commands.length = 0;
    scene.drawDecorShape({}, id, constant("DECOR_SPECS")[id], {});
    assert.ok(commands.filter(([name]) => name === "pixel").length >= 3, id);
    assert.ok(commands.some(([name]) => name === "fillTriangle"), id);
  }
  const ToyScene = sceneMethod("drawToyShape", dependencies);
  const toyScene = new ToyScene();
  toyScene.owner = { wandMode: false };
  toyScene.add = { text: () => ({ setOrigin() { return this; } }) };
  commands.length = 0;
  toyScene.drawToyShape({ add() {} }, "halloween-ghost-plush", constant("ROOM_TOY_TARGETS")["halloween-ghost-plush"], false);
  assert.ok(commands.filter(([name]) => name === "pixel").length >= 5);
});

test("Halloween cat stem and cape overlays are drawn without changing saved individual traits", () => {
  const blocks = [];
  const Scene = sceneMethod("drawCatProfileVariation", { INK: 0x2c2f3a, pixelBlock: (...args) => blocks.push(args.slice(1)) });
  const scene = new Scene();
  for (const breedId of ["festival-pumpkin", "festival-ghost"]) {
    blocks.length = 0;
    const cat = { breedId, patternKey: "white-socks", featureKey: "pink-paws" };
    scene.drawCatProfileVariation({}, cat, constant("CAT_COLORS")[breedId]);
    assert.ok(blocks.length >= 8, breedId);
    assert.deepEqual(cat, { breedId, patternKey: "white-socks", featureKey: "pink-paws" });
  }
});

test("pumpkin clicks toggle only its local glow and preserve other interaction states", () => {
  const Scene = sceneMethod("interactWithDecor", { itemInteractionFor: () => null });
  const scene = new Scene();
  scene.owner = { itemInteractionStates: new Map([["reading-lamp", { active: true }]]) };
  const lantern = {};
  scene.decorContainers = new Map([["halloween-pumpkin-lantern", lantern]]);
  const changes = [];
  scene.applyHalloweenLanternGlow = (target, active) => changes.push({ target, active });
  assert.equal(scene.interactWithDecor("halloween-pumpkin-lantern").active, true);
  assert.equal(scene.interactWithDecor("halloween-pumpkin-lantern").active, false);
  assert.deepEqual(changes, [{ target: lantern, active: true }, { target: lantern, active: false }]);
  assert.equal(scene.owner.itemInteractionStates.get("reading-lamp").active, true);
});

test("candy basket click is a visual interaction with no cat selection or purchase mutation", () => {
  const Scene = sceneMethod("interactWithDecor", { itemInteractionFor: () => null });
  const scene = new Scene();
  const basket = { active: true, setScale(value) { this.scale = value; } };
  scene.decorContainers = new Map([["halloween-candy-bowl", basket]]);
  const animations = [];
  scene.tweens = { killTweensOf() {}, add(value) { animations.push(value); } };
  const result = scene.interactWithDecor("halloween-candy-bowl");
  assert.equal(result.handled, true);
  assert.match(result.message, /不给小猫吃糖/);
  assert.equal(animations.length, 1);
  assert.equal(animations[0].targets, basket);
  assert.equal(basket.scale, 1);
});

test("Halloween ghost plush keeps the ordinary toy play path and explicit cat targeting", () => {
  const Scene = sceneMethod("interactWithToy", { itemInteractionFor: () => null });
  const scene = new Scene();
  scene.owner = { wandMode: false };
  assert.equal(scene.interactWithToy("halloween-ghost-plush"), null);
  assert.match(source, /Object\.entries\(ROOM_TOY_TARGETS\)/);
  assert.match(source, /this\.owner\.handlers\.onToyClick\?\.\(itemId, interaction\)/);
});
