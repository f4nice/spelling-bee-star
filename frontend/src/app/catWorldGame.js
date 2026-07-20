import * as Phaser from "phaser";

const GAME_WIDTH = 1280;
const GAME_HEIGHT = 560;
const FLOOR_TOP = 260;
const FLOOR_BOTTOM = 522;
const ROOM_BORDER = 12;
const INK = 0x2c2f3a;
const CREAM = 0xfff8df;
const CAT_INTERACTION_DEPTH = 980;
const CAT_HITBOX = { x: -20, y: -42, width: 150, height: 126 };

const DECOR_SPECS = {
  "sun-window": { label: "阳光窗台", width: 150, height: 88, defaultX: 146, defaultY: 34 },
  "book-shelf": { label: "英文书架", width: 170, height: 78, defaultX: 1010, defaultY: 46 },
  "cloud-rug": { label: "云朵地毯", width: 380, height: 78, defaultX: 790, defaultY: 432 },
  "study-desk": { label: "英文书桌", width: 200, height: 96, defaultX: 496, defaultY: 348 },
  "reading-lamp": { label: "阅读台灯", width: 72, height: 118, defaultX: 712, defaultY: 314 },
  "word-gallery": { label: "单词挂画", width: 120, height: 82, defaultX: 360, defaultY: 140 },
};

const CAT_PIXEL_SIZE = 2;

const CAT_COLORS = {
  mimi: { body: 0xffc46b, shade: 0xd88a3d, stripe: 0x7a4a28, belly: 0xffdf9f, nose: 0xf06f91 },
  "british-shorthair": { body: 0xb9c2c8, shade: 0x7e8b95, stripe: 0x4d5962, belly: 0xdde4e8, nose: 0xf08aac },
  ragdoll: { body: 0xf4e5cf, shade: 0xb88663, stripe: 0x79523f, belly: 0xfff4df, nose: 0xf38ca7 },
  maine: { body: 0xae7c4f, shade: 0x754926, stripe: 0xf1c17f, belly: 0xd6a06b, nose: 0xf08a7c },
  siamese: { body: 0xf1ddbd, shade: 0x5c433e, stripe: 0x382c2d, belly: 0xffefd2, nose: 0xf1a2b2 },
};

const TONE_PALETTES = {
  default: { main: 0xffbfd7, alt: 0xfff8df, accent: 0x87d9ff },
  sunset: { main: 0xff9b73, alt: 0xff6f9f, accent: 0xffef82 },
  lavender: { main: 0xbca7ff, alt: 0xf2e9ff, accent: 0xffbfd7 },
  candy: { main: 0xff8cad, alt: 0xfff8df, accent: 0xffd166 },
  sky: { main: 0x9ee7ff, alt: 0xf7fdff, accent: 0x78c7ff },
  cherry: { main: 0xb85a5a, alt: 0x743434, accent: 0xffc2b9 },
  mint: { main: 0x77d7b2, alt: 0x3d8d78, accent: 0xd6fff0 },
  moon: { main: 0xd9f6ff, alt: 0xfff8df, accent: 0x9bd0ff },
  peach: { main: 0xffd7c2, alt: 0xfff3e7, accent: 0xff9d8a },
};

function clamp(value, min, max) {
  return Math.min(Math.max(Number(value) || 0, min), max);
}

function cloneLayout(layout = {}) {
  return Object.fromEntries(
    Object.entries(layout || {}).map(([decorId, position]) => [
      decorId,
      {
        x: clamp(position?.x, 0, 92),
        y: clamp(position?.y, 0, 86),
      },
    ]),
  );
}

function normalizeSnapshot(snapshot = {}) {
  return {
    cats: Array.isArray(snapshot.cats) ? snapshot.cats : [],
    inventory: snapshot.inventory || {},
    layout: cloneLayout(snapshot.layout),
    mood: snapshot.mood || {},
    activeFood: snapshot.activeFood || snapshot.mood?.activeFood || {},
    ownedCats: Array.isArray(snapshot.ownedCats) ? snapshot.ownedCats : [],
    ownedFoodCount: Number(snapshot.ownedFoodCount || 0),
    roomStyles: snapshot.roomStyles || {},
    selectedCatId: snapshot.selectedCatId || "",
  };
}

function percentToX(percent, width = 0) {
  return clamp((Number(percent || 0) / 100) * GAME_WIDTH, ROOM_BORDER, GAME_WIDTH - width - ROOM_BORDER);
}

function percentToY(percent, height = 0) {
  return clamp((Number(percent || 0) / 100) * GAME_HEIGHT, ROOM_BORDER, GAME_HEIGHT - height - ROOM_BORDER);
}

function xToPercent(x) {
  return Math.round((clamp(x, 0, GAME_WIDTH) / GAME_WIDTH) * 1000) / 10;
}

function yToPercent(y) {
  return Math.round((clamp(y, 0, GAME_HEIGHT) / GAME_HEIGHT) * 1000) / 10;
}

function owned(inventory, itemId) {
  return Number(inventory?.[itemId] || 0) > 0;
}

function catTraitNumber(cat, key, fallback = 1) {
  const value = Number(cat?.traits?.[key]);
  return Number.isFinite(value) ? value : fallback;
}

function palette(tone) {
  return TONE_PALETTES[tone] || TONE_PALETTES.default;
}

function drawPixelRect(graphics, x, y, width, height, fill, stroke = INK, lineWidth = 4) {
  graphics.fillStyle(fill, 1);
  graphics.fillRect(x, y, width, height);
  graphics.lineStyle(lineWidth, stroke, 1);
  graphics.strokeRect(x, y, width, height);
}

function pixelBlock(graphics, x, y, width, height, fill) {
  const size = CAT_PIXEL_SIZE;
  graphics.fillStyle(fill, 1);
  graphics.fillRect(x * size, y * size, width * size, height * size);
}

function makeLocalGraphics(scene, container) {
  const graphics = scene.add.graphics();
  container.add(graphics);
  return graphics;
}

class CatWorldScene extends Phaser.Scene {
  constructor(owner) {
    super({ key: "CatWorldScene" });
    this.owner = owner;
    this.decorContainers = new Map();
    this.catContainers = new Map();
  }

  create() {
    this.input.on("dragstart", (_pointer, gameObject) => {
      if (gameObject.getData("kind") !== "decor") return;
      this.children.bringToTop(gameObject);
      gameObject.setData("dragOriginX", gameObject.x);
      gameObject.setData("dragOriginY", gameObject.y);
      gameObject.setData("dragMoved", false);
      gameObject.setAlpha(0.92);
      this.owner.handlers.onDecorSelect?.(gameObject.getData("id"));
    });

    this.input.on("drag", (_pointer, gameObject, dragX, dragY) => {
      if (gameObject.getData("kind") !== "decor") return;
      const width = gameObject.getData("width") || 80;
      const height = gameObject.getData("height") || 60;
      const nextX = clamp(dragX, ROOM_BORDER, GAME_WIDTH - width - ROOM_BORDER);
      const nextY = clamp(dragY, ROOM_BORDER, GAME_HEIGHT - height - ROOM_BORDER);
      const moved =
        Math.abs(nextX - Number(gameObject.getData("dragOriginX") || 0)) +
          Math.abs(nextY - Number(gameObject.getData("dragOriginY") || 0)) >
        5;
      gameObject.setPosition(nextX, nextY);
      gameObject.setDepth(nextY + 30);
      gameObject.setData("dragMoved", moved);
      const decorId = gameObject.getData("id");
      this.owner.layout[decorId] = { x: xToPercent(nextX), y: yToPercent(nextY) };
      if (moved) {
        this.owner.handlers.onLayoutChange?.(this.owner.getLayout(), decorId);
      }
    });

    this.input.on("dragend", (_pointer, gameObject) => {
      if (gameObject.getData("kind") !== "decor") return;
      gameObject.setAlpha(1);
      if (gameObject.getData("dragMoved")) {
        this.owner.handlers.onLayoutChange?.(this.owner.getLayout(), gameObject.getData("id"));
      }
    });

    this.renderSnapshot();
    this.owner.ready = true;
  }

  renderSnapshot() {
    this.tweens.killAll();
    this.time.removeAllEvents();
    this.children.removeAll(true);
    this.decorContainers.clear();
    this.catContainers.clear();
    const snapshot = this.owner.snapshot;
    this.owner.layout = cloneLayout(snapshot.layout);
    this.drawRoom();
    this.drawInventoryItems(snapshot);
    this.drawOwnedDecor(snapshot);
    this.drawCats(snapshot);
  }

  drawRoom() {
    const bg = this.add.graphics();
    bg.fillGradientStyle(0xcff7ee, 0xfff0d0, 0x9be4ff, 0xffd7e7, 1);
    bg.fillRect(0, 0, GAME_WIDTH, FLOOR_TOP);
    bg.fillStyle(0x6bc579, 1);
    bg.fillRect(0, FLOOR_TOP - 10, GAME_WIDTH, 10);
    bg.fillStyle(0xc29258, 1);
    bg.fillRect(0, FLOOR_TOP, GAME_WIDTH, GAME_HEIGHT - FLOOR_TOP);

    bg.lineStyle(1, 0x2c2f3a, 0.12);
    for (let x = 0; x <= GAME_WIDTH; x += 12) bg.lineBetween(x, 0, x, GAME_HEIGHT);
    for (let y = 0; y <= GAME_HEIGHT; y += 12) bg.lineBetween(0, y, GAME_WIDTH, y);

    bg.lineStyle(5, INK, 1);
    bg.strokeRect(2, 2, GAME_WIDTH - 4, GAME_HEIGHT - 4);
    bg.lineStyle(3, 0xfff8df, 0.5);
    bg.strokeRect(11, 11, GAME_WIDTH - 22, GAME_HEIGHT - 22);
  }

  drawOwnedDecor(snapshot) {
    for (const [decorId, spec] of Object.entries(DECOR_SPECS)) {
      if (!owned(snapshot.inventory, decorId)) continue;
      const tone = snapshot.roomStyles?.[decorId] || "default";
      const position = this.positionForDecor(decorId, spec);
      const container = this.add.container(position.x, position.y);
      container.setSize(spec.width, spec.height);
      container.setData("kind", "decor");
      container.setData("id", decorId);
      container.setData("width", spec.width);
      container.setData("height", spec.height);
      container.setDepth(position.y + 20);
      container.setInteractive(new Phaser.Geom.Rectangle(0, 0, spec.width, spec.height), Phaser.Geom.Rectangle.Contains);
      this.input.setDraggable(container);
      container.on("pointerdown", (_pointer, _localX, _localY, event) => {
        this.stopPointerEvent(event);
      });
      container.on("pointerup", (_pointer, _localX, _localY, event) => {
        this.stopPointerEvent(event);
        if (!container.getData("dragMoved")) {
          this.owner.handlers.onDecorClick?.(decorId);
        }
      });
      this.drawDecorShape(container, decorId, spec, palette(tone));
      this.decorContainers.set(decorId, container);
    }
  }

  drawInventoryItems(snapshot) {
    const lastPlayItem = snapshot.mood?.lastPlayItem || "";
    if (snapshot.activeFood?.active) {
      const foodLabel = snapshot.activeFood.label || "食物";
      const foodEnergy = Number(snapshot.activeFood.catEnergyEffective ?? snapshot.activeFood.catEnergy ?? 0);
      const bowlX = GAME_WIDTH - 260;
      const bowl = this.add.graphics();
      drawPixelRect(bowl, bowlX + 8, 408, 118, 46, 0xff8cad);
      bowl.fillStyle(0xfff07d, 1);
      bowl.fillRect(bowlX + 24, 416, 76, 10);
      bowl.fillStyle(0xfff8df, 1);
      bowl.fillRect(bowlX + 42, 432, 40, 8);
      bowl.setDepth(720);
      this.add
        .text(bowlX + 68, 380, `${foodLabel}\n+${foodEnergy} 体力`, {
          color: "#263047",
          backgroundColor: "#fff8df",
          fontFamily: "Consolas, monospace",
          fontSize: "12px",
          fontStyle: "bold",
          padding: { x: 4, y: 2 },
          align: "center",
        })
        .setOrigin(0.5)
        .setDepth(726);
      this.addRoomHitZone(snapshot.activeFood.itemId || "active-food", bowlX, 374, 142, 86, 728);
    }
    if (owned(snapshot.inventory, "rolling-ball")) {
      const active = lastPlayItem === "rolling-ball";
      const ballX = 312;
      const ballY = 392;
      const ball = this.add.graphics();
      ball.fillStyle(0x2c2f3a, 0.22);
      ball.fillEllipse(ballX + 22, ballY + 44, 60, 12);
      ball.fillStyle(0xfff07d, 1);
      ball.fillCircle(ballX + 22, ballY + 22, 22);
      ball.lineStyle(5, INK, 1);
      ball.strokeCircle(ballX + 22, ballY + 22, 22);
      ball.lineStyle(3, 0xff8cad, 1);
      ball.lineBetween(ballX + 4, ballY + 22, ballX + 40, ballY + 22);
      ball.lineBetween(ballX + 22, ballY + 4, ballX + 22, ballY + 40);
      ball.fillStyle(0x87d9ff, 1);
      ball.fillCircle(ballX + 22, ballY + 22, 7);
      ball.setDepth(690);
      if (active) {
        this.tweens.add({
          targets: ball,
          x: 26,
          yoyo: true,
          repeat: 5,
          duration: 260,
          ease: "Sine.easeInOut",
        });
      }
      this.drawRoomItemLabel("滚滚球", ballX + 22, ballY - 7, 706);
      this.addRoomHitZone("rolling-ball", ballX - 20, ballY - 14, 88, 88, 708);
    }
    if (owned(snapshot.inventory, "scratch-board")) {
      const scratcher = this.add.graphics();
      drawPixelRect(scratcher, 96, 426, 136, 26, 0xe6b06f);
      scratcher.lineStyle(1, 0x7a573b, 0.45);
      for (let x = 108; x < 218; x += 12) scratcher.lineBetween(x, 431, x + 8, 445);
      scratcher.setDepth(464);
      this.drawRoomItemLabel("猫抓板", 164, 406, 468);
      this.addRoomHitZone("scratch-board", 90, 418, 150, 44, 466);
    }
    if (owned(snapshot.inventory, "feather-wand")) {
      const wandX = GAME_WIDTH - 208;
      const wand = this.add.graphics();
      wand.lineStyle(6, 0x7b5834, 1);
      wand.lineBetween(wandX + 28, 320, wandX + 142, 280);
      wand.fillStyle(0xff8cad, 1);
      wand.fillTriangle(wandX + 136, 263, wandX + 163, 274, wandX + 142, 304);
      wand.fillStyle(0xa9e8c8, 1);
      wand.fillTriangle(wandX + 112, 262, wandX + 143, 272, wandX + 125, 298);
      wand.setDepth(330);
      this.drawRoomItemLabel("逗猫棒", wandX + 88, 236, 334);
      this.addRoomHitZone("feather-wand", wandX, 250, 172, 70, 332);
    }
  }

  drawRoomItemLabel(label, x, y, depth) {
    this.add
      .text(x, y, label, {
        color: "#263047",
        backgroundColor: "#fff8df",
        fontFamily: "Consolas, monospace",
        fontSize: "10px",
        fontStyle: "bold",
        padding: { x: 4, y: 2 },
      })
      .setOrigin(0.5)
      .setDepth(depth);
  }

  drawDecorShape(container, decorId, spec, colors) {
    const graphics = makeLocalGraphics(this, container);
    if (decorId === "sun-window") {
      drawPixelRect(graphics, 0, 0, spec.width, spec.height, 0xfff8df);
      graphics.fillStyle(colors.accent, 1);
      graphics.fillRect(8, 8, spec.width - 16, spec.height - 16);
      graphics.lineStyle(4, INK, 1);
      graphics.lineBetween(spec.width / 2, 8, spec.width / 2, spec.height - 8);
      graphics.lineBetween(8, spec.height / 2, spec.width - 8, spec.height / 2);
      graphics.fillStyle(0xfff07d, 1);
      graphics.fillCircle(29, 27, 13);
    } else if (decorId === "book-shelf") {
      graphics.fillStyle(colors.main, 1);
      graphics.fillRect(8, 8, 28, 48);
      graphics.fillStyle(0xffd166, 1);
      graphics.fillRect(42, 0, 18, 58);
      graphics.fillStyle(colors.accent, 1);
      graphics.fillRect(66, 13, 22, 45);
      graphics.fillStyle(0x1d7f5b, 1);
      graphics.fillRect(94, 5, 42, 53);
      drawPixelRect(graphics, 0, 56, spec.width, 12, 0x7d5735);
    } else if (decorId === "cloud-rug") {
      drawPixelRect(graphics, 0, 0, spec.width, spec.height, colors.alt);
      for (let x = 8; x < spec.width - 8; x += 32) {
        graphics.fillStyle((x / 32) % 2 === 0 ? colors.main : 0xfff8df, 1);
        graphics.fillRect(x, 6, 16, spec.height - 12);
      }
    } else if (decorId === "study-desk") {
      drawPixelRect(graphics, 0, 0, spec.width, 48, colors.main);
      drawPixelRect(graphics, 20, 48, 22, 36, colors.alt);
      drawPixelRect(graphics, spec.width - 42, 48, 22, 36, colors.alt);
      drawPixelRect(graphics, 26, 12, 44, 16, 0xfff8df, INK, 3);
      drawPixelRect(graphics, spec.width - 54, 10, 23, 26, colors.accent, INK, 3);
    } else if (decorId === "reading-lamp") {
      graphics.lineStyle(6, INK, 1);
      graphics.lineBetween(30, 36, 30, 94);
      graphics.lineBetween(15, 98, 48, 98);
      drawPixelRect(graphics, 6, 0, 50, 32, colors.main);
      graphics.fillStyle(colors.accent, 0.22);
      graphics.fillCircle(31, 46, 42);
    } else if (decorId === "word-gallery") {
      drawPixelRect(graphics, 0, 0, spec.width, spec.height, colors.alt);
      drawPixelRect(graphics, 10, 10, spec.width - 20, spec.height - 20, colors.main, INK, 3);
      const text = this.add
        .text(spec.width / 2, spec.height / 2, "ABC", {
          color: "#236b55",
          fontFamily: "Consolas, monospace",
          fontSize: "18px",
          fontStyle: "bold",
        })
        .setOrigin(0.5);
      container.add(text);
    }
  }

  drawCats(snapshot) {
    const ownedCatIds = new Set(snapshot.ownedCats);
    const cats = snapshot.cats.filter((cat) => ownedCatIds.has(cat.id));
    const visibleCats = cats.length ? cats : snapshot.cats.slice(0, 1);
    visibleCats.forEach((cat, index) => {
      const x = 150 + (index % 6) * 176;
      const y = FLOOR_BOTTOM - 68 - Math.floor(index / 5) * 56;
      const container = this.add.container(x, y);
      container.setSize(100, 70);
      container.setData("kind", "cat");
      container.setData("id", cat.id);
      container.setDepth(CAT_INTERACTION_DEPTH + index);
      container.setInteractive(
        new Phaser.Geom.Rectangle(CAT_HITBOX.x, CAT_HITBOX.y, CAT_HITBOX.width, CAT_HITBOX.height),
        Phaser.Geom.Rectangle.Contains,
      );
      container.on("pointerdown", (_pointer, _localX, _localY, event) => {
        this.children.bringToTop(container);
        this.stopPointerEvent(event);
      });
      container.on("pointerup", (_pointer, _localX, _localY, event) => {
        this.children.bringToTop(container);
        this.stopPointerEvent(event);
        this.spawnCatBubble(container, cat);
        this.owner.handlers.onCatPet?.(cat);
      });
      this.drawCatShape(container, cat, snapshot.selectedCatId === cat.id, snapshot);
      this.catContainers.set(cat.id, container);
      this.scheduleCatWalk(container, index, cat);
    });
  }

  drawCatShape(container, cat, selected, snapshot) {
    const colors = CAT_COLORS[cat.id] || CAT_COLORS.mimi;
    const graphics = makeLocalGraphics(this, container);
    graphics.fillStyle(0x203041, 0.18);
    graphics.fillRect(7, 49, 82, 7);
    this.drawCatPixels(graphics, cat, colors);
    this.drawStatusBars(graphics, snapshot?.mood?.catEnergy ?? 50, snapshot?.mood?.score ?? 50);

    graphics.fillStyle(selected ? 0xfff07d : 0xff8cad, 1);
    graphics.fillRect(42, -24, selected ? 18 : 10, 8);
    graphics.lineStyle(2, INK, 1);
    graphics.strokeRect(42, -24, selected ? 18 : 10, 8);
    if (selected) {
      graphics.fillStyle(0x2c2f3a, 1);
      graphics.fillRect(46, -21, 2, 3);
      graphics.fillRect(52, -21, 2, 3);
      graphics.fillRect(58, -21, 2, 3);
    }
    if (snapshot?.mood?.canWalk === false) {
      graphics.fillStyle(0xffffff, 1);
      graphics.fillRect(76, 2, 18, 10);
      graphics.fillStyle(INK, 1);
      graphics.fillRect(79, 5, 4, 2);
      graphics.fillRect(84, 3, 4, 2);
      graphics.fillRect(89, 5, 4, 2);
    }
  }

  drawStatusBars(graphics, catEnergy, moodScore) {
    this.drawTinyBar(graphics, 4, -17, 72, 5, catEnergy, 0xff4f6d);
    this.drawTinyBar(graphics, 4, -10, 72, 5, moodScore, 0x54b7ff);
  }

  drawTinyBar(graphics, x, y, width, height, value, color) {
    const ratio = clamp(value, 0, 100) / 100;
    graphics.fillStyle(0xfff8df, 1);
    graphics.fillRect(x, y, width, height);
    graphics.fillStyle(0x2c2f3a, 1);
    graphics.fillRect(x - 1, y - 1, width + 2, 1);
    graphics.fillRect(x - 1, y + height, width + 2, 1);
    graphics.fillRect(x - 1, y - 1, 1, height + 2);
    graphics.fillRect(x + width, y - 1, 1, height + 2);
    graphics.fillStyle(color, 1);
    graphics.fillRect(x + 1, y + 1, Math.max(Math.round((width - 2) * ratio), 1), height - 2);
  }

  addRoomHitZone(itemId, x, y, width, height, depth = 420) {
    const zone = this.add.zone(x, y, width, height);
    zone.setOrigin(0, 0);
    zone.setDepth(depth);
    zone.setData("kind", "room-item");
    zone.setData("id", itemId);
    zone.setInteractive(new Phaser.Geom.Rectangle(0, 0, width, height), Phaser.Geom.Rectangle.Contains);
    zone.on("pointerdown", (_pointer, _localX, _localY, event) => {
      this.stopPointerEvent(event);
    });
    zone.on("pointerup", (_pointer, _localX, _localY, event) => {
      this.stopPointerEvent(event);
      this.owner.handlers.onToyClick?.(itemId);
    });
  }

  stopPointerEvent(event) {
    event?.stopPropagation?.();
  }

  drawCatPixels(graphics, cat, colors) {
    const body = colors.body;
    const shade = colors.shade;
    const stripe = colors.stripe;
    const belly = colors.belly;
    const nose = colors.nose;
    pixelBlock(graphics, 4, 15, 8, 5, INK);
    pixelBlock(graphics, 2, 12, 6, 5, INK);
    pixelBlock(graphics, 3, 9, 5, 4, INK);
    pixelBlock(graphics, 6, 8, 7, 3, INK);
    pixelBlock(graphics, 5, 15, 6, 3, body);
    pixelBlock(graphics, 3, 13, 4, 3, body);
    pixelBlock(graphics, 4, 10, 3, 2, body);
    pixelBlock(graphics, 7, 9, 5, 1, body);

    pixelBlock(graphics, 11, 11, 25, 14, INK);
    pixelBlock(graphics, 13, 9, 20, 4, INK);
    pixelBlock(graphics, 15, 25, 15, 3, INK);
    pixelBlock(graphics, 12, 13, 23, 10, body);
    pixelBlock(graphics, 15, 20, 16, 4, belly);
    pixelBlock(graphics, 15, 13, 3, 4, shade);
    pixelBlock(graphics, 22, 12, 3, 4, shade);
    pixelBlock(graphics, 29, 13, 3, 4, shade);
    pixelBlock(graphics, 13, 24, 5, 6, INK);
    pixelBlock(graphics, 14, 24, 3, 5, body);
    pixelBlock(graphics, 28, 24, 5, 6, INK);
    pixelBlock(graphics, 29, 24, 3, 5, body);
    pixelBlock(graphics, 13, 29, 6, 2, INK);
    pixelBlock(graphics, 28, 29, 6, 2, INK);

    pixelBlock(graphics, 34, 7, 14, 15, INK);
    pixelBlock(graphics, 35, 8, 12, 13, body);
    pixelBlock(graphics, 35, 3, 6, 6, INK);
    pixelBlock(graphics, 37, 5, 3, 4, body);
    pixelBlock(graphics, 37, 6, 2, 2, 0xffbfd7);
    pixelBlock(graphics, 43, 3, 6, 6, INK);
    pixelBlock(graphics, 44, 5, 3, 4, body);
    pixelBlock(graphics, 45, 6, 2, 2, 0xffbfd7);
    pixelBlock(graphics, 38, 12, 2, 2, 0x111827);
    pixelBlock(graphics, 44, 12, 2, 2, 0x111827);
    pixelBlock(graphics, 41, 15, 2, 2, nose);
    pixelBlock(graphics, 39, 17, 5, 1, stripe);
    pixelBlock(graphics, 35, 16, 3, 2, 0xffbfd7);
    pixelBlock(graphics, 45, 16, 3, 2, 0xffbfd7);
    pixelBlock(graphics, 32, 14, 4, 1, INK);
    pixelBlock(graphics, 47, 14, 4, 1, INK);
    pixelBlock(graphics, 31, 17, 4, 1, INK);
    pixelBlock(graphics, 48, 17, 4, 1, INK);
  }

  scheduleCatWalk(container, index, cat = {}) {
    const movement = clamp(catTraitNumber(cat, "movement", 1), 0.62, 1.2);
    if (this.owner.snapshot?.mood?.canWalk === false) {
      this.tweens.add({
        targets: container,
        y: container.y - 3,
        yoyo: true,
        repeat: -1,
        duration: Math.round((1650 + index * 180) / Math.max(movement, 0.82)),
        ease: "Sine.easeInOut",
        onUpdate: () => container.setDepth(CAT_INTERACTION_DEPTH + index),
      });
      return;
    }
    const delay = Math.round((Phaser.Math.Between(2200, 4600) + index * 430) / Math.max(movement, 0.72));
    this.time.delayedCall(delay, () => {
      if (!container.active) return;
      const nextX = Phaser.Math.Between(38, GAME_WIDTH - 132);
      const nextY = Phaser.Math.Between(FLOOR_TOP + 52, FLOOR_BOTTOM - 70);
      const duration = Math.round(Phaser.Math.Between(9000, 15000) / movement);
      this.tweens.add({
        targets: container,
        x: nextX,
        y: nextY,
        duration,
        ease: "Sine.easeInOut",
        onUpdate: () => container.setDepth(CAT_INTERACTION_DEPTH + index),
        onComplete: () => this.scheduleCatWalk(container, index, cat),
      });
    });
  }

  spawnCatBubble(container, cat) {
    const lines = cat?.thoughts?.length ? cat.thoughts : [
      "我想听一个新单词。",
      "能量已同步，今天也很棒。",
      "摸摸接收成功。",
      "我在检查书桌路线。",
    ];
    const message = lines[Math.floor(Math.random() * lines.length)];
    const bubble = this.add
      .text(container.x + 34, container.y - 24, message, {
        color: "#263047",
        backgroundColor: "#fff8df",
        fontFamily: "Consolas, monospace",
        fontSize: "12px",
        fontStyle: "bold",
        padding: { x: 8, y: 5 },
      })
      .setOrigin(0.5)
      .setDepth(CAT_INTERACTION_DEPTH + 120);
    this.tweens.add({
      targets: bubble,
      y: bubble.y - 22,
      alpha: 0,
      duration: 1500,
      ease: "Cubic.easeOut",
      onComplete: () => bubble.destroy(),
    });
    this.owner.handlers.onCatThought?.(cat, message);
  }

  positionForDecor(decorId, spec) {
    const position = this.owner.layout[decorId];
    if (!position) {
      return { x: spec.defaultX, y: spec.defaultY };
    }
    return {
      x: percentToX(position.x, spec.width),
      y: percentToY(position.y, spec.height),
    };
  }
}

export class CatWorldGame {
  constructor(parent, handlers = {}) {
    this.handlers = handlers;
    this.layout = {};
    this.ready = false;
    this.snapshot = normalizeSnapshot();
    this.game = new Phaser.Game({
      type: Phaser.AUTO,
      parent,
      width: GAME_WIDTH,
      height: GAME_HEIGHT,
      backgroundColor: "#fff8df",
      pixelArt: true,
      render: {
        antialias: false,
        roundPixels: true,
      },
      scale: {
        mode: Phaser.Scale.FIT,
        autoCenter: Phaser.Scale.CENTER_BOTH,
      },
      scene: [new CatWorldScene(this)],
    });
  }

  update(snapshot) {
    this.snapshot = normalizeSnapshot(snapshot);
    this.layout = cloneLayout(this.snapshot.layout);
    if (this.ready) {
      this.game.scene.getScene("CatWorldScene")?.renderSnapshot();
      this.game.scale.refresh();
    }
  }

  getLayout() {
    return cloneLayout(this.layout);
  }

  destroy() {
    this.game?.destroy(true);
  }
}
