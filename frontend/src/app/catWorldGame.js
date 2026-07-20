import * as Phaser from "phaser";

const GAME_WIDTH = 1280;
const GAME_HEIGHT = 560;
const FLOOR_TOP = 260;
const FLOOR_BOTTOM = 522;
const ROOM_BORDER = 12;
const INK = 0x2c2f3a;
const CREAM = 0xfff8df;
const CAT_INTERACTION_DEPTH = 980;
const CAT_HITBOX = { x: -58, y: -74, width: 232, height: 184 };
const ACTIVE_FOOD_SPOT = { x: GAME_WIDTH - 260, y: 408, width: 118, height: 46 };
const ROOM_TOY_TARGETS = {
  "rolling-ball": { label: "滚滚球", x: 334, y: 414 },
  "scratch-board": { label: "猫抓板", x: 164, y: 418 },
  "feather-wand": { label: "逗猫棒", x: GAME_WIDTH - 120, y: 320 },
};

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
  "maine-coon": { body: 0xae7c4f, shade: 0x754926, stripe: 0xf1c17f, belly: 0xd6a06b, nose: 0xf08a7c },
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
    dailyLogs: snapshot.dailyLogs || {},
    damagedItems: snapshot.damagedItems || {},
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

function isDamaged(snapshot, itemId) {
  return Boolean(snapshot?.damagedItems?.[itemId]);
}

function hashText(text) {
  return String(text || "").split("").reduce((hash, char) => ((hash << 5) - hash + char.charCodeAt(0)) | 0, 0);
}

function seededRatio(seed) {
  const value = Math.sin(seed) * 10000;
  return value - Math.floor(value);
}

function seededOffset(seed, span) {
  return Math.round((seededRatio(Math.abs(hashText(seed))) * 2 - 1) * span);
}

function isSleepHour(hour, start, end) {
  if (start === end) return false;
  if (start < end) return hour >= start && hour < end;
  return hour >= start || hour < end;
}

function shortCatText(text, max = 8) {
  const value = String(text || "").trim();
  if (value.length <= max) return value;
  return `${value.slice(0, max)}...`;
}

function catEnergyForSnapshot(snapshot, cat) {
  const log = snapshot?.dailyLogs?.[cat?.id];
  const value = Number(log?.energyScore);
  if (Number.isFinite(value)) return value;
  if (cat?.id === snapshot?.selectedCatId) return Number(snapshot?.mood?.catEnergy ?? 50);
  return 50;
}

function catMoodForSnapshot(snapshot, cat) {
  const log = snapshot?.dailyLogs?.[cat?.id];
  const value = Number(log?.moodScore);
  if (Number.isFinite(value)) return value;
  if (cat?.id === snapshot?.selectedCatId) return Number(snapshot?.mood?.score ?? 50);
  return 50;
}

function catAgentForSnapshot(snapshot, cat) {
  return snapshot?.dailyLogs?.[cat?.id]?.agentState || {};
}

function catDailyGoalForSnapshot(snapshot, cat) {
  return catAgentForSnapshot(snapshot, cat).dailyGoal || {};
}

function catTraitNumber(cat, key, fallback = 1) {
  const value = Number(cat?.traits?.[key]);
  return Number.isFinite(value) ? value : fallback;
}

function uniqueLines(lines) {
  return [...new Set(lines.filter(Boolean).map((line) => String(line).trim()).filter(Boolean))];
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
      const damaged = isDamaged(snapshot, decorId);
      const tone = snapshot.roomStyles?.[decorId] || "default";
      const position = this.positionForDecor(decorId, spec);
      const container = this.add.container(position.x, position.y);
      container.setSize(spec.width, spec.height);
      container.setData("kind", "decor");
      container.setData("id", decorId);
      container.setData("damaged", damaged);
      container.setData("width", spec.width);
      container.setData("height", spec.height);
      container.setDepth(position.y + 20);
      container.setInteractive(new Phaser.Geom.Rectangle(0, 0, spec.width, spec.height), Phaser.Geom.Rectangle.Contains);
      if (!damaged) {
        this.input.setDraggable(container);
      }
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
      if (damaged) {
        container.setAlpha(0.74);
        this.drawDamagedOverlay(container, spec.width, spec.height);
      }
      this.decorContainers.set(decorId, container);
    }
  }

  drawInventoryItems(snapshot) {
    const lastPlayItem = snapshot.mood?.lastPlayItem || "";
    if (snapshot.activeFood?.active) {
      const foodLabel = snapshot.activeFood.label || "食物";
      const targetLabel = snapshot.activeFood.targetCatLabel || "";
      const foodEnergy = Number(snapshot.activeFood.catEnergyEffective ?? snapshot.activeFood.catEnergy ?? 0);
      const bowlX = ACTIVE_FOOD_SPOT.x;
      const bowl = this.add.graphics();
      drawPixelRect(bowl, bowlX + 8, ACTIVE_FOOD_SPOT.y, ACTIVE_FOOD_SPOT.width, ACTIVE_FOOD_SPOT.height, 0xff8cad);
      bowl.fillStyle(0xfff07d, 1);
      bowl.fillRect(bowlX + 24, 416, 76, 10);
      bowl.fillStyle(0xfff8df, 1);
      bowl.fillRect(bowlX + 42, 432, 40, 8);
      bowl.setDepth(720);
      this.add
        .text(bowlX + 68, 380, `${foodLabel}\n${targetLabel ? `给${targetLabel} ` : ""}+${foodEnergy} 体力`, {
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
      const damaged = isDamaged(snapshot, "rolling-ball");
      const active = lastPlayItem === "rolling-ball";
      const ballX = 312;
      const ballY = 392;
      const ball = this.add.graphics();
      ball.setAlpha(damaged ? 0.56 : 1);
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
      if (active && !damaged) {
        this.tweens.add({
          targets: ball,
          x: 26,
          yoyo: true,
          repeat: 5,
          duration: 260,
          ease: "Sine.easeInOut",
        });
      }
      this.drawRoomItemLabel(damaged ? "滚滚球 损坏" : "滚滚球", ballX + 22, ballY - 7, 706);
      if (damaged) this.drawDamagedMark(ballX - 10, ballY - 8, 72, 64, 709);
      this.addRoomHitZone("rolling-ball", ballX - 20, ballY - 14, 88, 88, 708);
    }
    if (owned(snapshot.inventory, "scratch-board")) {
      const damaged = isDamaged(snapshot, "scratch-board");
      const scratcher = this.add.graphics();
      scratcher.setAlpha(damaged ? 0.56 : 1);
      drawPixelRect(scratcher, 96, 426, 136, 26, 0xe6b06f);
      scratcher.lineStyle(1, 0x7a573b, 0.45);
      for (let x = 108; x < 218; x += 12) scratcher.lineBetween(x, 431, x + 8, 445);
      scratcher.setDepth(464);
      this.drawRoomItemLabel(damaged ? "猫抓板 损坏" : "猫抓板", 164, 406, 468);
      if (damaged) this.drawDamagedMark(92, 416, 146, 48, 470);
      this.addRoomHitZone("scratch-board", 90, 418, 150, 44, 466);
    }
    if (owned(snapshot.inventory, "feather-wand")) {
      const damaged = isDamaged(snapshot, "feather-wand");
      const wandX = GAME_WIDTH - 208;
      const wand = this.add.graphics();
      wand.setAlpha(damaged ? 0.56 : 1);
      wand.lineStyle(6, 0x7b5834, 1);
      wand.lineBetween(wandX + 28, 320, wandX + 142, 280);
      wand.fillStyle(0xff8cad, 1);
      wand.fillTriangle(wandX + 136, 263, wandX + 163, 274, wandX + 142, 304);
      wand.fillStyle(0xa9e8c8, 1);
      wand.fillTriangle(wandX + 112, 262, wandX + 143, 272, wandX + 125, 298);
      wand.setDepth(330);
      this.drawRoomItemLabel(damaged ? "逗猫棒 损坏" : "逗猫棒", wandX + 88, 236, 334);
      if (damaged) this.drawDamagedMark(wandX, 250, 172, 70, 336);
      this.addRoomHitZone("feather-wand", wandX, 250, 172, 70, 332);
    }
  }

  drawDamagedOverlay(container, width, height) {
    const graphics = makeLocalGraphics(this, container);
    graphics.lineStyle(5, 0xdb2777, 0.95);
    graphics.lineBetween(10, 10, width - 14, height - 12);
    graphics.lineBetween(width - 22, 12, width - 38, 31);
    graphics.lineBetween(width - 44, 30, width - 35, 48);
    graphics.lineStyle(3, 0x2c2f3a, 0.85);
    graphics.strokeRect(5, 5, width - 10, height - 10);
    const label = this.add
      .text(width / 2, -16, "损坏 · 点击维修", {
        color: "#fff8df",
        backgroundColor: "#db2777",
        fontFamily: "Consolas, monospace",
        fontSize: "11px",
        fontStyle: "bold",
        padding: { x: 5, y: 2 },
      })
      .setOrigin(0.5);
    container.add(label);
  }

  drawDamagedMark(x, y, width, height, depth) {
    const mark = this.add.graphics();
    mark.lineStyle(5, 0xdb2777, 0.95);
    mark.lineBetween(x + 6, y + 6, x + width - 6, y + height - 7);
    mark.lineBetween(x + width - 12, y + 8, x + width - 26, y + 24);
    mark.lineBetween(x + width - 30, y + 24, x + width - 18, y + 40);
    mark.setDepth(depth);
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
      const behavior = this.catBehavior(cat, index);
      const position = this.initialCatPosition(snapshot, cat, index, behavior);
      const container = this.add.container(position.x, position.y);
      container.setSize(100, 70);
      container.setData("kind", "cat");
      container.setData("id", cat.id);
      container.setData("behavior", behavior);
      container.setDepth(CAT_INTERACTION_DEPTH + index);
      container.setInteractive(
        new Phaser.Geom.Rectangle(CAT_HITBOX.x, CAT_HITBOX.y, CAT_HITBOX.width, CAT_HITBOX.height),
        Phaser.Geom.Rectangle.Contains,
      );
      if (container.input) container.input.cursor = "pointer";
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
      this.drawCatShape(container, cat, snapshot.selectedCatId === cat.id, snapshot, behavior);
      this.catContainers.set(cat.id, container);
      this.scheduleCatWalk(container, index, cat);
    });
  }

  defaultCatPosition(index) {
    return {
      x: 150 + (index % 6) * 176,
      y: FLOOR_BOTTOM - 68 - Math.floor(index / 5) * 56,
    };
  }

  initialCatPosition(snapshot, cat, index, behavior = {}) {
    const fallback = this.defaultCatPosition(index);
    if (behavior.sleeping) {
      return this.restDecorPosition(cat, index, ["cloud-rug", "sun-window", "book-shelf"]) || fallback;
    }
    if (behavior.key === "resting") {
      return this.foodRestPosition(cat, index)
        || this.restDecorPosition(cat, index, ["cloud-rug", "sun-window", "study-desk"])
        || fallback;
    }
    if (snapshot.activeFood?.active && snapshot.activeFood.targetCatId === cat.id) {
      return this.foodRestPosition(cat, index) || fallback;
    }
    const goal = this.dailyGoalForCat(cat);
    if (Number(goal.priority || 0) >= 76) {
      return this.stableAgentGoalPosition(cat, index, goal) || fallback;
    }
    return fallback;
  }

  dailyGoalForCat(cat = {}) {
    return catDailyGoalForSnapshot(this.owner.snapshot, cat);
  }

  foodRestPosition(cat, index) {
    const activeFood = this.owner.snapshot.activeFood || {};
    if (!activeFood.active || Number(activeFood.remainingEnergy || 0) <= 0) return null;
    if (activeFood.targetCatId && activeFood.targetCatId !== cat.id) return null;
    const side = index % 2 === 0 ? -1 : 1;
    return {
      x: clamp(ACTIVE_FOOD_SPOT.x + 52 + side * (34 + (index % 3) * 12), 38, GAME_WIDTH - 132),
      y: clamp(ACTIVE_FOOD_SPOT.y + 62 + (index % 3) * 8, FLOOR_TOP + 52, FLOOR_BOTTOM - 70),
    };
  }

  restDecorPosition(cat, index, fallbackDecorIds = []) {
    const preferred = Array.isArray(cat.favoriteDecorIds) ? cat.favoriteDecorIds : [];
    const decorIds = [...preferred, ...fallbackDecorIds].filter((decorId, decorIndex, all) => all.indexOf(decorId) === decorIndex);
    const decorId = decorIds.find(
      (candidate) => owned(this.owner.snapshot.inventory, candidate) && DECOR_SPECS[candidate] && !isDamaged(this.owner.snapshot, candidate),
    );
    if (!decorId) return null;
    return this.nearDecorPosition(decorId, index);
  }

  stableAgentGoalPosition(cat, index, goal = {}) {
    const targetItemId = goal.targetItemId || "";
    if (!targetItemId || isDamaged(this.owner.snapshot, targetItemId)) return null;
    const seed = `${cat.id || "cat"}:${targetItemId}:${goal.key || "goal"}:${index}`;
    if (goal.targetType === "toy" && owned(this.owner.snapshot.inventory, targetItemId) && ROOM_TOY_TARGETS[targetItemId]) {
      const target = ROOM_TOY_TARGETS[targetItemId];
      return {
        x: clamp(target.x + seededOffset(`${seed}:x`, 38), 38, GAME_WIDTH - 132),
        y: clamp(target.y + seededOffset(`${seed}:y`, 20), FLOOR_TOP + 52, FLOOR_BOTTOM - 70),
      };
    }
    if (owned(this.owner.snapshot.inventory, targetItemId) && DECOR_SPECS[targetItemId]) {
      const spec = DECOR_SPECS[targetItemId];
      const position = this.positionForDecor(targetItemId, spec);
      return {
        x: clamp(position.x + spec.width / 2 - 45 + seededOffset(`${seed}:x`, 40), 38, GAME_WIDTH - 132),
        y: clamp(Math.max(FLOOR_TOP + 52, position.y + spec.height + 22) + seededOffset(`${seed}:y`, 18), FLOOR_TOP + 52, FLOOR_BOTTOM - 70),
      };
    }
    return null;
  }

  nearDecorPosition(decorId, index) {
    const spec = DECOR_SPECS[decorId];
    if (!spec) return null;
    const position = this.positionForDecor(decorId, spec);
    const lane = index % 3;
    return {
      x: clamp(position.x + spec.width / 2 - 45 + (lane - 1) * 34, 38, GAME_WIDTH - 132),
      y: clamp(Math.max(FLOOR_TOP + 52, position.y + spec.height + 24) + (lane - 1) * 8, FLOOR_TOP + 52, FLOOR_BOTTOM - 70),
    };
  }

  drawCatShape(container, cat, selected, snapshot, behavior = {}) {
    const colors = CAT_COLORS[cat.id] || CAT_COLORS.mimi;
    const graphics = makeLocalGraphics(this, container);
    const energyScore = catEnergyForSnapshot(snapshot, cat);
    const moodScore = catMoodForSnapshot(snapshot, cat);
    graphics.fillStyle(0x203041, 0.18);
    graphics.fillRect(7, 49, 82, 7);
    this.drawCatPixels(graphics, cat, colors);
    this.drawStatusBars(graphics, energyScore, moodScore);
    this.drawCatMoodCue(graphics, behavior, energyScore, moodScore);

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
    if (behavior.sleeping) {
      const sleepText = this.add
        .text(78, -28, "Zzz", {
          color: "#263047",
          backgroundColor: "#fff8df",
          fontFamily: "Consolas, monospace",
          fontSize: "11px",
          fontStyle: "bold",
          padding: { x: 4, y: 2 },
        })
        .setOrigin(0.5);
      this.pinCatTextOverlay(sleepText);
      container.add(sleepText);
    }
    if (behavior.key === "resting") {
      graphics.fillStyle(0xffffff, 1);
      graphics.fillRect(76, 2, 18, 10);
      graphics.fillStyle(INK, 1);
      graphics.fillRect(79, 5, 4, 2);
      graphics.fillRect(84, 3, 4, 2);
      graphics.fillRect(89, 5, 4, 2);
    }
    const dailyGoal = catDailyGoalForSnapshot(snapshot, cat);
    if (dailyGoal.key === "mischief-watch") {
      graphics.fillStyle(0xdb2777, 1);
      graphics.fillRect(76, -35, 18, 18);
      graphics.lineStyle(2, INK, 1);
      graphics.strokeRect(76, -35, 18, 18);
      const warning = this.add
        .text(85, -26, "!", {
          color: "#fff8df",
          fontFamily: "Consolas, monospace",
          fontSize: "14px",
          fontStyle: "bold",
        })
        .setOrigin(0.5);
      this.pinCatTextOverlay(warning);
      container.add(warning);
    }
    this.drawCatIntentBadge(container, cat, snapshot, behavior);
    this.syncCatTextOverlays(container);
  }

  drawCatMoodCue(graphics, behavior, energyScore, moodScore) {
    if (behavior.sleeping) return;
    if (energyScore < Number(behavior.restThreshold || 34)) {
      graphics.fillStyle(0x87d9ff, 0.95);
      graphics.fillRect(82, 10, 8, 8);
      graphics.fillRect(90, 14, 8, 8);
      graphics.fillStyle(INK, 0.9);
      graphics.fillRect(84, 13, 3, 2);
      return;
    }
    if (moodScore < 38) {
      graphics.fillStyle(0x2c2f3a, 0.88);
      graphics.fillRect(78, 2, 20, 9);
      graphics.fillRect(82, -2, 13, 13);
      graphics.fillStyle(0x87d9ff, 1);
      graphics.fillRect(82, 15, 3, 7);
      graphics.fillRect(92, 17, 3, 7);
      return;
    }
    if (moodScore >= 82) {
      graphics.fillStyle(0xff6f9f, 1);
      graphics.fillRect(80, 1, 6, 6);
      graphics.fillRect(88, 1, 6, 6);
      graphics.fillRect(82, 7, 10, 6);
    }
  }

  catIntentInfo(cat, snapshot, behavior = {}) {
    const agent = catAgentForSnapshot(snapshot, cat);
    const goal = agent.dailyGoal || {};
    const targetLabel = shortCatText(goal.targetLabel || "", 5);
    if (behavior.sleeping || goal.key === "sleep") {
      return { text: "睡觉", color: "#263047", background: "#fff8df" };
    }
    if (behavior.key === "resting" || goal.key === "rest") {
      return { text: "休息", color: "#263047", background: "#d9f6ff" };
    }
    if (goal.key === "mischief-watch") {
      return { text: targetLabel ? `盯着${targetLabel}` : "想捣蛋", color: "#fff8df", background: "#db2777" };
    }
    if (goal.key === "toy-play") {
      return { text: targetLabel ? `想玩${targetLabel}` : "想玩", color: "#263047", background: "#fff07d" };
    }
    if (goal.key === "favorite-decor") {
      return { text: targetLabel ? `喜欢${targetLabel}` : "去喜欢处", color: "#fff8df", background: "#1d7f5b" };
    }
    if (goal.key === "room-patrol" || behavior.key === "night-watch") {
      return { text: behavior.key === "night-watch" ? "夜巡" : "巡逻", color: "#fff8df", background: "#236b55" };
    }
    if (behavior.key === "exploring") {
      return { text: "探索", color: "#263047", background: "#87d9ff" };
    }
    if (behavior.key === "sulking") {
      return { text: "闹情绪", color: "#fff8df", background: "#db2777" };
    }
    if (behavior.key === "slow") {
      return { text: "慢走", color: "#263047", background: "#f6d48f" };
    }
    const label = String(agent.dailyMoodLabel || behavior.dailyLabel || "").replace(/^今天/, "");
    return { text: shortCatText(label || "活动", 6), color: "#263047", background: "#fff8df" };
  }

  drawCatIntentBadge(container, cat, snapshot, behavior = {}) {
    const intent = this.catIntentInfo(cat, snapshot, behavior);
    if (!intent.text) return;
    const badge = this.add
      .text(45, -43, intent.text, {
        color: intent.color,
        backgroundColor: intent.background,
        fontFamily: "Consolas, monospace",
        fontSize: "10px",
        fontStyle: "bold",
        padding: { x: 5, y: 2 },
      })
      .setOrigin(0.5);
    badge.setData("catIntentBadge", true);
    this.pinCatTextOverlay(badge);
    container.add(badge);
  }

  pinCatTextOverlay(textObject) {
    textObject.setData("catTextOverlay", true);
    textObject.setData("baseX", Number(textObject.x || 0));
    return textObject;
  }

  catTextOverlays(container) {
    return (container.list || []).filter((child) => child.getData?.("catTextOverlay"));
  }

  hideCatTextOverlays(container) {
    this.catTextOverlays(container).forEach((child) => child.setVisible(false));
  }

  syncCatTextOverlays(container) {
    const facing = container.scaleX < 0 ? -1 : 1;
    this.catTextOverlays(container).forEach((child) => {
      const baseX = Number(child.getData("baseX") ?? child.x ?? 0);
      child.setX(baseX * facing);
      child.setScale(facing, 1);
      child.setVisible(true);
    });
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

  catBehavior(cat = {}, index = 0) {
    const log = this.owner.snapshot?.dailyLogs?.[cat.id] || {};
    const agent = log.agentState || {};
    const serverBehavior = agent.currentBehavior || {};
    const traits = cat.traits || {};
    const now = new Date();
    const hour = now.getHours();
    const daySeed = Math.floor(now.getTime() / 86400000) + Math.abs(hashText(cat.id || "cat")) + index * 31;
    const dailyRoll = seededRatio(daySeed);
    const moodLabels = ["今天很高兴", "今天想探索", "今天有点黏人", "今天想慢慢来", "今天不太高兴"];
    const dailyLabel = agent.dailyMoodLabel || moodLabels[Math.floor(dailyRoll * moodLabels.length)] || moodLabels[0];
    const sleepStart = Number(traits.sleepStart ?? 23);
    const sleepEnd = Number(traits.sleepEnd ?? 7);
    const nightOwl = Boolean(traits.nightOwl);
    const sleeping = Boolean(serverBehavior.sleeping || (isSleepHour(hour, sleepStart, sleepEnd) && !nightOwl));
    const energy = catEnergyForSnapshot(this.owner.snapshot, cat);
    const mood = catMoodForSnapshot(this.owner.snapshot, cat);
    const restThreshold = Number(traits.restThreshold ?? 34);
    let key = serverBehavior.key || "active";
    if (sleeping) key = "sleeping";
    else if (energy < restThreshold) key = "resting";
    else if (nightOwl && (hour >= 22 || hour < 5)) key = "night-watch";
    const moodFactor = mood < 38 ? 0.72 : mood < 56 ? 0.84 : 1;
    const energyFactor = energy < restThreshold + 8 ? 0.58 : energy < 58 ? 0.78 : 1;
    const behaviorFactor = key === "slow" ? 0.72 : key === "exploring" ? 1.04 : key === "night-watch" ? 0.94 : 1;
    const walkSpeed = clamp(catTraitNumber(cat, "movement", 1) * moodFactor * energyFactor * behaviorFactor, 0.34, 0.92);
    const idleChance = sleeping
      ? 100
      : key === "resting"
        ? 92
        : energy < restThreshold + 8
          ? 72
          : mood < 38
            ? 54
            : key === "slow"
              ? 38
              : key === "night-watch"
                ? 18
                : 24;
    return {
      key,
      sleeping,
      nightOwl,
      dailyLabel,
      routine: agent.routine || traits.routine || "观察房间里的学习节奏",
      canWalk: !sleeping && energy >= restThreshold,
      energy,
      mood,
      restThreshold,
      walkSpeed,
      idleChance,
      restless: nightOwl && (hour >= 22 || hour < 5),
    };
  }

  turnCat(container, nextX) {
    const nextScale = nextX < container.x ? -1 : 1;
    const currentSign = container.scaleX < 0 ? -1 : 1;
    if (currentSign === nextScale) return;
    this.spawnTurnPuff(container);
    this.hideCatTextOverlays(container);
    this.tweens.add({
      targets: container,
      scaleX: currentSign * 0.16,
      duration: 120,
      ease: "Sine.easeInOut",
      onComplete: () => {
        if (!container.active) return;
        this.tweens.add({
          targets: container,
          scaleX: nextScale,
          duration: 140,
          ease: "Sine.easeInOut",
          onComplete: () => {
            if (!container.active) return;
            this.syncCatTextOverlays(container);
          },
        });
      },
    });
  }

  spawnTurnPuff(container) {
    if (!container.active) return;
    const puff = this.add.graphics();
    puff.fillStyle(0xfff8df, 0.92);
    puff.fillRect(container.x + 26, container.y + 44, 9, 9);
    puff.fillRect(container.x + 42, container.y + 49, 7, 7);
    puff.lineStyle(2, 0x2c2f3a, 0.42);
    puff.strokeRect(container.x + 26, container.y + 44, 9, 9);
    puff.setDepth(CAT_INTERACTION_DEPTH + 110);
    this.tweens.add({
      targets: puff,
      y: puff.y - 10,
      alpha: 0,
      duration: 520,
      ease: "Cubic.easeOut",
      onComplete: () => puff.destroy(),
    });
  }

  scheduleCatWalk(container, index, cat = {}) {
    const behavior = this.catBehavior(cat, index);
    const movement = Number(behavior.walkSpeed || 0.62);
    container.setData("behavior", behavior);
    if (!behavior.canWalk) {
      this.tweens.add({
        targets: container,
        y: container.y - 3,
        yoyo: true,
        repeat: -1,
        duration: Math.round((2100 + index * 220) / Math.max(movement, 0.72)),
        ease: "Sine.easeInOut",
        onUpdate: () => container.setDepth(CAT_INTERACTION_DEPTH + index),
      });
      if (behavior.sleeping) {
        this.time.delayedCall(Phaser.Math.Between(1200, 2600), () => this.spawnRestBubble(container, cat, "睡觉中..."));
      }
      return;
    }
    const delay = Math.round((Phaser.Math.Between(5800, 12200) + index * 780) / Math.max(movement, 0.38));
    this.time.delayedCall(delay, () => {
      if (!container.active) return;
      const latestBehavior = this.catBehavior(cat, index);
      container.setData("behavior", latestBehavior);
      if (this.shouldCatIdle(latestBehavior)) {
        this.playCatIdle(container, index, cat, latestBehavior);
        return;
      }
      const foodTarget = this.foodTargetForCat(cat);
      const goalTarget = this.agentGoalTarget(cat);
      const favoriteTarget = this.favoriteItemTarget(cat);
      const shouldVisitFood = Boolean(foodTarget && Phaser.Math.Between(1, 100) <= foodTarget.priority);
      const shouldVisitGoal = !shouldVisitFood && Boolean(goalTarget && Phaser.Math.Between(1, 100) <= goalTarget.priority);
      const shouldVisitFavorite = !shouldVisitFood && !shouldVisitGoal && Boolean(favoriteTarget && Phaser.Math.Between(1, 100) <= favoriteTarget.priority);
      const nextX = shouldVisitFood
        ? foodTarget.x
        : shouldVisitGoal
          ? goalTarget.x
          : shouldVisitFavorite
            ? favoriteTarget.x
            : Phaser.Math.Between(38, GAME_WIDTH - 132);
      const nextY = shouldVisitFood
        ? foodTarget.y
        : shouldVisitGoal
          ? goalTarget.y
          : shouldVisitFavorite
            ? favoriteTarget.y
            : Phaser.Math.Between(FLOOR_TOP + 52, FLOOR_BOTTOM - 70);
      const duration = Math.round(Phaser.Math.Between(34000, 56000) / Math.max(Number(latestBehavior.walkSpeed || movement), 0.34));
      this.turnCat(container, nextX);
      this.tweens.add({
        targets: container,
        x: nextX,
        y: nextY,
        duration,
        ease: "Sine.easeInOut",
        onUpdate: () => container.setDepth(CAT_INTERACTION_DEPTH + index),
        onComplete: () => {
          if (shouldVisitFood) {
            this.spawnFoodPlayBubble(container, cat, foodTarget);
          } else if (shouldVisitGoal) {
            if (goalTarget.kind === "mischief") {
              this.spawnMischiefBubble(container, cat, goalTarget);
            } else {
              this.spawnGoalBubble(container, cat, goalTarget);
            }
          } else if (shouldVisitFavorite) {
            this.spawnFavoritePlayBubble(container, cat, favoriteTarget);
          }
          this.scheduleCatWalk(container, index, cat);
        },
      });
    });
  }

  shouldCatIdle(behavior = {}) {
    return Phaser.Math.Between(1, 100) <= Number(behavior.idleChance || 20);
  }

  playCatIdle(container, index, cat = {}, behavior = {}) {
    const message = this.catIdleMessage(cat, behavior);
    if (message) this.spawnRestBubble(container, cat, message);
    const idleMs = Phaser.Math.Between(3600, 7600) + index * 280;
    this.tweens.add({
      targets: container,
      y: container.y + Phaser.Math.Between(-2, 3),
      yoyo: true,
      repeat: 1,
      duration: 520,
      ease: "Sine.easeInOut",
    });
    this.time.delayedCall(idleMs, () => {
      if (container.active) this.scheduleCatWalk(container, index, cat);
    });
  }

  catIdleMessage(cat = {}, behavior = {}) {
    const goal = this.dailyGoalForCat(cat);
    if (behavior.energy < Number(behavior.restThreshold || 34) + 8) return "体力有点低，先坐一会儿。";
    if (behavior.mood < 38) return "今天心情不太好，想安静一下。";
    if (goal.key === "mischief-watch") return `正在犹豫要不要碰${goal.targetLabel || "那个道具"}。`;
    if (goal.key === "favorite-decor") return `在想${goal.targetLabel || "喜欢的角落"}。`;
    if (behavior.key === "slow") return "今天想慢慢走。";
    if (behavior.key === "night-watch") return "夜巡路线确认中。";
    return Phaser.Math.Between(1, 100) <= 45 ? "停下来观察房间。" : "";
  }

  agentGoalTarget(cat = {}) {
    const log = this.owner.snapshot?.dailyLogs?.[cat.id] || {};
    const goal = log.agentState?.dailyGoal || {};
    const targetItemId = goal.targetItemId || "";
    if (!targetItemId || isDamaged(this.owner.snapshot, targetItemId)) return null;
    const isMischiefWatch = goal.key === "mischief-watch";
    if (goal.targetType === "toy" && owned(this.owner.snapshot.inventory, targetItemId) && ROOM_TOY_TARGETS[targetItemId]) {
      const target = ROOM_TOY_TARGETS[targetItemId];
      return {
        itemId: targetItemId,
        label: goal.targetLabel || target.label,
        message: goal.message || "",
        kind: isMischiefWatch ? "mischief" : "toy",
        itemKind: "toy",
        priority: isMischiefWatch ? Math.max(Number(goal.priority || 86), 88) : Number(goal.priority || 72),
        x: clamp(target.x + Phaser.Math.Between(-42, 42), 38, GAME_WIDTH - 132),
        y: clamp(target.y + Phaser.Math.Between(-22, 24), FLOOR_TOP + 52, FLOOR_BOTTOM - 70),
      };
    }
    if (owned(this.owner.snapshot.inventory, targetItemId) && DECOR_SPECS[targetItemId]) {
      const spec = DECOR_SPECS[targetItemId];
      const position = this.positionForDecor(targetItemId, spec);
      return {
        itemId: targetItemId,
        label: goal.targetLabel || spec.label,
        message: goal.message || "",
        kind: isMischiefWatch ? "mischief" : goal.targetType || "decor",
        itemKind: "decor",
        priority: isMischiefWatch ? Math.max(Number(goal.priority || 86), 88) : Number(goal.priority || 72),
        x: clamp(position.x + spec.width / 2 - 45 + Phaser.Math.Between(-44, 44), 38, GAME_WIDTH - 132),
        y: clamp(Math.max(FLOOR_TOP + 52, position.y + spec.height + 18) + Phaser.Math.Between(-18, 24), FLOOR_TOP + 52, FLOOR_BOTTOM - 70),
      };
    }
    return null;
  }

  favoriteItemTarget(cat = {}) {
    const toyTarget = this.favoriteToyTarget(cat);
    const decorTarget = this.favoriteDecorTarget(cat);
    if (toyTarget && decorTarget) {
      const agent = this.owner.snapshot?.dailyLogs?.[cat.id]?.agentState || {};
      const curious = Number(agent.curiosity || 50);
      return Phaser.Math.Between(1, 100) <= 48 + Math.round(curious / 5) ? toyTarget : decorTarget;
    }
    return toyTarget || decorTarget;
  }

  favoriteToyTarget(cat = {}) {
    const favoriteToyIds = Array.isArray(cat.favoriteToyIds) ? cat.favoriteToyIds : [];
    const ownedFavorites = favoriteToyIds.filter(
      (toyId) => owned(this.owner.snapshot.inventory, toyId) && ROOM_TOY_TARGETS[toyId] && !isDamaged(this.owner.snapshot, toyId),
    );
    if (!ownedFavorites.length) return null;
    const itemId = ownedFavorites[Phaser.Math.Between(0, ownedFavorites.length - 1)];
    const target = ROOM_TOY_TARGETS[itemId];
    const agent = this.owner.snapshot?.dailyLogs?.[cat.id]?.agentState || {};
    const energy = catEnergyForSnapshot(this.owner.snapshot, cat);
    const mood = catMoodForSnapshot(this.owner.snapshot, cat);
    const curiosity = clamp(Number(agent.curiosity || 45), 0, 100);
    const priority = clamp(42 + Math.round(curiosity / 4) + (mood < 56 ? 16 : 0) - (energy < 38 ? 18 : 0), 18, 78);
    return {
      itemId,
      label: target.label,
      kind: "favorite-toy",
      priority,
      x: clamp(target.x + Phaser.Math.Between(-48, 48), 38, GAME_WIDTH - 132),
      y: clamp(target.y + Phaser.Math.Between(-24, 26), FLOOR_TOP + 52, FLOOR_BOTTOM - 70),
    };
  }

  favoriteDecorTarget(cat = {}) {
    const favoriteDecorIds = Array.isArray(cat.favoriteDecorIds) ? cat.favoriteDecorIds : [];
    const ownedFavorites = favoriteDecorIds.filter(
      (decorId) => owned(this.owner.snapshot.inventory, decorId) && DECOR_SPECS[decorId] && !isDamaged(this.owner.snapshot, decorId),
    );
    if (!ownedFavorites.length) return null;
    const decorId = ownedFavorites[Phaser.Math.Between(0, ownedFavorites.length - 1)];
    const spec = DECOR_SPECS[decorId];
    const position = this.positionForDecor(decorId, spec);
    const nearX = position.x + spec.width / 2 - 45 + Phaser.Math.Between(-38, 38);
    const nearY = Math.max(FLOOR_TOP + 52, position.y + spec.height + 18) + Phaser.Math.Between(-16, 18);
    return {
      decorId,
      label: spec.label,
      kind: "favorite-decor",
      priority: 64,
      x: clamp(nearX, 38, GAME_WIDTH - 132),
      y: clamp(nearY, FLOOR_TOP + 52, FLOOR_BOTTOM - 70),
    };
  }

  foodTargetForCat(cat = {}) {
    const activeFood = this.owner.snapshot.activeFood || {};
    if (!activeFood.active || Number(activeFood.remainingEnergy || 0) <= 0) return null;
    const targetCatId = activeFood.targetCatId || "";
    if (targetCatId) {
      return {
        label: activeFood.label || "食物",
        priority: cat.id === targetCatId ? 96 : 12,
        x: clamp(ACTIVE_FOOD_SPOT.x + 58 + Phaser.Math.Between(-28, 28), 38, GAME_WIDTH - 132),
        y: clamp(ACTIVE_FOOD_SPOT.y + 52 + Phaser.Math.Between(-14, 20), FLOOR_TOP + 52, FLOOR_BOTTOM - 70),
      };
    }
    const ownedCats = new Set(this.owner.snapshot.ownedCats || []);
    const visibleCats = (this.owner.snapshot.cats || []).filter((candidate) => ownedCats.has(candidate.id));
    const energy = catEnergyForSnapshot(this.owner.snapshot, cat);
    const lowestEnergy = visibleCats.length
      ? Math.min(...visibleCats.map((candidate) => catEnergyForSnapshot(this.owner.snapshot, candidate)))
      : energy;
    const priority = energy <= lowestEnergy + 4 ? 92 : energy < 42 ? 78 : energy < 66 ? 48 : 18;
    return {
      label: activeFood.label || "食物",
      priority,
      x: clamp(ACTIVE_FOOD_SPOT.x + 58 + Phaser.Math.Between(-28, 28), 38, GAME_WIDTH - 132),
      y: clamp(ACTIVE_FOOD_SPOT.y + 52 + Phaser.Math.Between(-14, 20), FLOOR_TOP + 52, FLOOR_BOTTOM - 70),
    };
  }

  spawnRestBubble(container, cat, message) {
    if (!container.active) return;
    const bubble = this.add
      .text(container.x + 34, container.y - 25, `${cat?.label || "猫咪"} ${message}`, {
        color: "#263047",
        backgroundColor: "#fff8df",
        fontFamily: "Consolas, monospace",
        fontSize: "12px",
        fontStyle: "bold",
        padding: { x: 8, y: 5 },
      })
      .setOrigin(0.5)
      .setDepth(CAT_INTERACTION_DEPTH + 130);
    this.tweens.add({
      targets: bubble,
      y: bubble.y - 18,
      alpha: 0,
      duration: 1500,
      ease: "Cubic.easeOut",
      onComplete: () => bubble.destroy(),
    });
  }

  spawnFoodPlayBubble(container, cat, target) {
    const message = `${cat?.label || "猫咪"} 先去吃${target.label}。`;
    const bubble = this.add
      .text(container.x + 36, container.y - 28, message, {
        color: "#263047",
        backgroundColor: "#fff8df",
        fontFamily: "Consolas, monospace",
        fontSize: "12px",
        fontStyle: "bold",
        padding: { x: 8, y: 5 },
      })
      .setOrigin(0.5)
      .setDepth(CAT_INTERACTION_DEPTH + 140);
    this.tweens.add({
      targets: container,
      y: container.y - 7,
      yoyo: true,
      repeat: 2,
      duration: 240,
      ease: "Sine.easeInOut",
    });
    this.tweens.add({
      targets: bubble,
      y: bubble.y - 22,
      alpha: 0,
      duration: 1800,
      ease: "Cubic.easeOut",
      onComplete: () => bubble.destroy(),
    });
    this.owner.handlers.onCatThought?.(cat, message);
  }

  spawnFavoritePlayBubble(container, cat, target) {
    const action = target.kind === "favorite-toy" ? "玩最喜欢的" : "跑到喜欢的";
    const message = `${cat?.label || "猫咪"} ${action}${target.label}。`;
    const bubble = this.add
      .text(container.x + 36, container.y - 28, message, {
        color: "#263047",
        backgroundColor: "#fff8df",
        fontFamily: "Consolas, monospace",
        fontSize: "12px",
        fontStyle: "bold",
        padding: { x: 8, y: 5 },
      })
      .setOrigin(0.5)
      .setDepth(CAT_INTERACTION_DEPTH + 140);
    this.tweens.add({
      targets: container,
      y: container.y - 8,
      yoyo: true,
      repeat: 1,
      duration: 260,
      ease: "Sine.easeInOut",
    });
    this.tweens.add({
      targets: bubble,
      y: bubble.y - 22,
      alpha: 0,
      duration: 1800,
      ease: "Cubic.easeOut",
      onComplete: () => bubble.destroy(),
    });
    this.owner.handlers.onCatThought?.(cat, message);
    this.owner.handlers.onCatAmbient?.(cat, {
      kind: target.kind,
      itemId: target.itemId || target.decorId,
      label: target.label,
    });
  }

  spawnGoalBubble(container, cat, target) {
    const fallback = target.kind === "toy"
      ? `${cat?.label || "猫咪"} 今天想玩${target.label}。`
      : `${cat?.label || "猫咪"} 今天想去${target.label}附近。`;
    const message = target.message || fallback;
    const bubble = this.add
      .text(container.x + 36, container.y - 28, message, {
        color: "#263047",
        backgroundColor: "#fff8df",
        fontFamily: "Consolas, monospace",
        fontSize: "12px",
        fontStyle: "bold",
        padding: { x: 8, y: 5 },
        wordWrap: { width: 260 },
        align: "center",
      })
      .setOrigin(0.5)
      .setDepth(CAT_INTERACTION_DEPTH + 145);
    this.tweens.add({
      targets: container,
      y: container.y - (target.kind === "mischief" ? 4 : 8),
      yoyo: true,
      repeat: target.kind === "toy" ? 3 : 1,
      duration: target.kind === "toy" ? 220 : 280,
      ease: "Sine.easeInOut",
    });
    this.tweens.add({
      targets: bubble,
      y: bubble.y - 22,
      alpha: 0,
      duration: 2200,
      ease: "Cubic.easeOut",
      onComplete: () => bubble.destroy(),
    });
    this.owner.handlers.onCatThought?.(cat, message);
  }

  spawnMischiefBubble(container, cat, target) {
    const message = target.message || `${cat?.label || "猫咪"}今天心情不太好，正在盯着${target.label}。`;
    const bubble = this.add
      .text(container.x + 38, container.y - 31, message, {
        color: "#fff8df",
        backgroundColor: "#db2777",
        fontFamily: "Consolas, monospace",
        fontSize: "12px",
        fontStyle: "bold",
        padding: { x: 8, y: 5 },
        wordWrap: { width: 270 },
        align: "center",
      })
      .setOrigin(0.5)
      .setDepth(CAT_INTERACTION_DEPTH + 150);
    this.spawnMischiefMarks(target.x + 48, target.y - 18);
    this.tweens.add({
      targets: container,
      x: container.x + 6,
      yoyo: true,
      repeat: 5,
      duration: 90,
      ease: "Sine.easeInOut",
    });
    this.tweens.add({
      targets: bubble,
      y: bubble.y - 24,
      alpha: 0,
      duration: 2400,
      ease: "Cubic.easeOut",
      onComplete: () => bubble.destroy(),
    });
    this.owner.handlers.onCatThought?.(cat, message);
  }

  spawnMischiefMarks(x, y) {
    for (let index = 0; index < 3; index += 1) {
      const mark = this.add
        .text(x + index * 18, y - index * 8, "!", {
          color: "#fff8df",
          backgroundColor: "#db2777",
          fontFamily: "Consolas, monospace",
          fontSize: "13px",
          fontStyle: "bold",
          padding: { x: 4, y: 1 },
        })
        .setOrigin(0.5)
        .setDepth(CAT_INTERACTION_DEPTH + 146 + index);
      this.tweens.add({
        targets: mark,
        y: mark.y - 20,
        alpha: 0,
        duration: 900 + index * 180,
        ease: "Cubic.easeOut",
        onComplete: () => mark.destroy(),
      });
    }
  }

  spawnCatBubble(container, cat) {
    const behavior = container.getData("behavior") || this.catBehavior(cat);
    const lines = this.catThoughtLines(cat, behavior);
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

  catThoughtLines(cat = {}, behavior = {}) {
    const agent = catAgentForSnapshot(this.owner.snapshot, cat);
    const goal = agent.dailyGoal || {};
    const activeFood = this.owner.snapshot.activeFood || {};
    const lines = [
      ...(cat?.thoughts?.length ? cat.thoughts : [
        "我想听一个新单词。",
        "能量已同步，今天也很棒。",
        "摸摸接收成功。",
        "我在检查书桌路线。",
      ]),
    ];
    if (agent.dailyMoodLabel) lines.unshift(`${agent.dailyMoodLabel}，${behavior.routine || "想按自己的节奏活动"}。`);
    if (goal.message) lines.unshift(goal.message);
    if (activeFood.active && activeFood.targetCatId === cat.id) {
      lines.unshift(`那份${activeFood.label || "食物"}是给我的，我会慢慢吃。`);
    }
    if (behavior.energy < Number(behavior.restThreshold || 34) + 8) {
      lines.unshift("体力低的时候，我会先休息再走动。");
    }
    if (behavior.mood < 38) {
      lines.unshift("今天心情不太好，陪我玩一下会好很多。");
    }
    if (agent.hourlyReason) lines.push(`现在的节奏: ${agent.hourlyReason}。`);
    return uniqueLines(lines).slice(0, 8);
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
