import test from "node:test";
import assert from "node:assert/strict";

import {
  catWorldResponsiveViewportWidth,
  normalizeCatWorldScene,
  sceneAllowsItem,
  sceneColor,
  sceneInitialScroll,
  scenePageTarget,
} from "../src/app/catWorldSceneConfig.js";

test("scene configuration clamps unsafe dimensions and keeps database metadata", () => {
  const scene = normalizeCatWorldScene({
    id: "yard",
    label: "Cat Yard",
    world: {
      width: 2200,
      height: 560,
      viewportWidth: 1280,
      viewportHeight: 560,
      floorTop: 236,
      floorBottom: 522,
    },
  });

  assert.equal(scene.id, "yard");
  assert.equal(scene.world.width, 2200);
  assert.equal(scene.world.viewportWidth, 1280);
  assert.equal(scene.world.floorTop, 236);
});

test("scene item rules can exclude indoor furniture without affecting toys", () => {
  const scene = {
    itemRules: {
      allowedCategories: ["decor", "toy"],
      excludedItemIds: ["sun-window"],
    },
  };

  assert.equal(sceneAllowsItem(scene, "sun-window", "decor"), false);
  assert.equal(sceneAllowsItem(scene, "rolling-ball", "toy"), true);
  assert.equal(sceneAllowsItem(scene, "salmon-bowl", "food"), false);
});

test("scene colors only accept six-digit hex values", () => {
  assert.equal(sceneColor("#12abef", 0), 0x12abef);
  assert.equal(sceneColor("not-a-color", 0x123456), 0x123456);
});

test("scene paging moves by one viewport-sized page", () => {
  const scene = {
    world: { width: 2560, viewportWidth: 1280 },
    camera: { pageWidth: 1280, initialPage: 0 },
  };

  assert.equal(sceneInitialScroll(scene), 0);
  assert.equal(scenePageTarget(scene, 0, 1), 1280);
  assert.equal(scenePageTarget(scene, 1280, -1), 0);
  assert.equal(scenePageTarget(scene, 1280, 1), 1280);
  assert.equal(scenePageTarget(scene, 0, 1, 480), 480);
  assert.equal(scenePageTarget(scene, 480, 1, 480), 960);
});

test("scene initial page follows the active mobile viewport", () => {
  const scene = {
    world: { width: 2560, viewportWidth: 1280 },
    camera: { pageWidth: 1280, initialPage: 1 },
  };

  assert.equal(sceneInitialScroll(scene), 1280);
  assert.equal(sceneInitialScroll(scene, 480), 480);
});

test("cat world uses a narrow virtual viewport only on small rendered rooms", () => {
  const scene = { world: { width: 2560, viewportWidth: 1280 } };

  assert.equal(catWorldResponsiveViewportWidth(scene, 320), 480);
  assert.equal(catWorldResponsiveViewportWidth(scene, 560), 480);
  assert.equal(catWorldResponsiveViewportWidth(scene, 561), 1280);
  assert.equal(catWorldResponsiveViewportWidth(scene, 960), 1280);
  assert.equal(catWorldResponsiveViewportWidth(scene), 1280);
});

test("scene purchase metadata survives normalization", () => {
  const scene = normalizeCatWorldScene({
    id: "kitchen",
    description: "A bright kitchen",
    purchasable: true,
    purchaseCost: 50000,
    unlocked: false,
  });

  assert.equal(scene.description, "A bright kitchen");
  assert.equal(scene.purchasable, true);
  assert.equal(scene.purchaseCost, 50000);
  assert.equal(scene.unlocked, false);
});
