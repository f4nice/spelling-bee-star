import * as Phaser from "phaser";

const GAME_WIDTH = 720;
const GAME_HEIGHT = 460;
const FLOOR_TOP = 214;
const FLOOR_BOTTOM = 424;
const ROOM_BORDER = 10;
const INK = 0x2c2f3a;
const CREAM = 0xfff8df;

const DECOR_SPECS = {
  "sun-window": { label: "阳光窗台", width: 132, height: 78, defaultX: 42, defaultY: 28 },
  "book-shelf": { label: "英文书架", width: 150, height: 72, defaultX: 535, defaultY: 38 },
  "cloud-rug": { label: "云朵地毯", width: 300, height: 70, defaultX: 210, defaultY: 348 },
  "study-desk": { label: "英文书桌", width: 176, height: 86, defaultX: 334, defaultY: 278 },
  "reading-lamp": { label: "阅读台灯", width: 62, height: 108, defaultX: 486, defaultY: 236 },
  "word-gallery": { label: "单词挂画", width: 102, height: 74, defaultX: 215, defaultY: 120 },
};

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

function palette(tone) {
  return TONE_PALETTES[tone] || TONE_PALETTES.default;
}

function drawPixelRect(graphics, x, y, width, height, fill, stroke = INK, lineWidth = 4) {
  graphics.fillStyle(fill, 1);
  graphics.fillRect(x, y, width, height);
  graphics.lineStyle(lineWidth, stroke, 1);
  graphics.strokeRect(x, y, width, height);
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

    bg.lineStyle(1, 0x2c2f3a, 0.18);
    for (let x = 0; x <= GAME_WIDTH; x += 16) bg.lineBetween(x, 0, x, GAME_HEIGHT);
    for (let y = 0; y <= GAME_HEIGHT; y += 16) bg.lineBetween(0, y, GAME_WIDTH, y);

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
      container.on("pointerup", () => {
        if (!container.getData("dragMoved")) {
          this.owner.handlers.onDecorClick?.(decorId);
        }
      });
      this.drawDecorShape(container, decorId, spec, palette(tone));
      this.decorContainers.set(decorId, container);
    }
  }

  drawInventoryItems(snapshot) {
    if (snapshot.ownedFoodCount > 0) {
      const bowl = this.add.graphics();
      drawPixelRect(bowl, 590, 344, 62, 32, 0xff8cad);
      bowl.fillStyle(0xfff07d, 1);
      bowl.fillRect(600, 348, 42, 8);
      bowl.setDepth(380);
    }
    if (owned(snapshot.inventory, "scratch-board")) {
      const scratcher = this.add.graphics();
      drawPixelRect(scratcher, 70, 348, 110, 24, 0xe6b06f);
      scratcher.lineStyle(1, 0x7a573b, 0.45);
      for (let x = 80; x < 170; x += 12) scratcher.lineBetween(x, 352, x + 8, 366);
      scratcher.setDepth(370);
    }
    if (owned(snapshot.inventory, "feather-wand")) {
      const wand = this.add.graphics();
      wand.lineStyle(6, 0x7b5834, 1);
      wand.lineBetween(585, 262, 670, 230);
      wand.fillStyle(0xff8cad, 1);
      wand.fillTriangle(666, 218, 688, 226, 670, 248);
      wand.fillStyle(0xa9e8c8, 1);
      wand.fillTriangle(648, 216, 672, 224, 658, 244);
      wand.setDepth(260);
    }
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
    const label = this.add
      .text(0, spec.height + 4, spec.label, {
        color: "#263047",
        backgroundColor: "#fff8df",
        fontFamily: "Consolas, monospace",
        fontSize: "10px",
        fontStyle: "bold",
        padding: { x: 3, y: 2 },
      })
      .setDepth(999);
    container.add(label);
  }

  drawCats(snapshot) {
    const ownedCatIds = new Set(snapshot.ownedCats);
    const cats = snapshot.cats.filter((cat) => ownedCatIds.has(cat.id));
    const visibleCats = cats.length ? cats : snapshot.cats.slice(0, 1);
    visibleCats.forEach((cat, index) => {
      const x = 96 + (index % 5) * 118;
      const y = FLOOR_BOTTOM - 52 - Math.floor(index / 5) * 46;
      const container = this.add.container(x, y);
      container.setSize(80, 50);
      container.setData("kind", "cat");
      container.setData("id", cat.id);
      container.setDepth(y + 80);
      container.setInteractive(new Phaser.Geom.Rectangle(-12, -16, 104, 74), Phaser.Geom.Rectangle.Contains);
      container.on("pointerup", () => {
        this.spawnCatBubble(container, cat);
        this.owner.handlers.onCatPet?.(cat);
      });
      this.drawCatShape(container, cat, snapshot.selectedCatId === cat.id);
      this.catContainers.set(cat.id, container);
      this.scheduleCatWalk(container, index);
    });
  }

  drawCatShape(container, cat, selected) {
    const colors = CAT_COLORS[cat.id] || CAT_COLORS.mimi;
    const graphics = makeLocalGraphics(this, container);
    graphics.fillStyle(0x203041, 0.18);
    graphics.fillRect(8, 44, 66, 8);

    this.drawPixelBlock(graphics, 4, 23, 8, 8, colors.shade);
    this.drawPixelBlock(graphics, -2, 17, 8, 8, colors.shade);
    this.drawPixelBlock(graphics, -8, 11, 8, 8, colors.shade);
    this.drawPixelBlock(graphics, 10, 18, 47, 24, colors.body);
    this.drawPixelBlock(graphics, 18, 35, 9, 11, colors.shade);
    this.drawPixelBlock(graphics, 43, 35, 9, 11, colors.shade);
    this.drawPixelBlock(graphics, 22, 26, 26, 10, colors.belly);
    this.drawPixelBlock(graphics, 53, 12, 27, 25, colors.body);
    this.drawPixelBlock(graphics, 56, 3, 9, 13, colors.body);
    this.drawPixelBlock(graphics, 68, 3, 9, 13, colors.body);

    graphics.fillStyle(0xffbfd7, 1);
    graphics.fillRect(58, 8, 4, 5);
    graphics.fillRect(71, 8, 4, 5);
    graphics.fillStyle(0x111827, 1);
    graphics.fillRect(60, 22, 4, 4);
    graphics.fillRect(72, 22, 4, 4);
    graphics.fillStyle(colors.nose, 1);
    graphics.fillRect(67, 28, 4, 3);
    graphics.fillStyle(colors.stripe, 1);
    graphics.fillRect(18, 20, 5, 6);
    graphics.fillRect(30, 18, 5, 6);
    graphics.fillRect(42, 20, 5, 6);
    graphics.fillRect(58, 16, 4, 4);
    graphics.fillRect(70, 16, 4, 4);

    graphics.lineStyle(2, INK, 1);
    graphics.lineBetween(66, 30, 58, 29);
    graphics.lineBetween(66, 33, 58, 35);
    graphics.lineBetween(72, 30, 82, 28);
    graphics.lineBetween(72, 33, 82, 35);

    if (cat.id === "siamese") {
      graphics.fillStyle(colors.shade, 1);
      graphics.fillRect(56, 18, 21, 16);
      graphics.fillRect(4, 23, 8, 8);
    }

    graphics.lineStyle(3, INK, 1);
    graphics.strokeRect(10, 18, 47, 24);
    graphics.strokeRect(53, 12, 27, 25);
    graphics.strokeRect(56, 3, 9, 13);
    graphics.strokeRect(68, 3, 9, 13);
    graphics.strokeRect(18, 35, 9, 11);
    graphics.strokeRect(43, 35, 9, 11);
    graphics.strokeRect(4, 23, 8, 8);
    graphics.strokeRect(-2, 17, 8, 8);
    graphics.strokeRect(-8, 11, 8, 8);

    graphics.fillStyle(selected ? 0xfff07d : 0xff8cad, 1);
    graphics.fillRect(22, 0, selected ? 26 : 16, 10);
    graphics.lineStyle(3, INK, 1);
    graphics.strokeRect(22, 0, selected ? 26 : 16, 10);
    if (selected) {
      graphics.fillStyle(0x2c2f3a, 1);
      graphics.fillRect(28, 3, 3, 4);
      graphics.fillRect(36, 3, 3, 4);
      graphics.fillRect(44, 3, 3, 4);
    }
    const label = this.add
      .text(4, 55, cat.label || "猫咪", {
        color: "#263047",
        backgroundColor: "#fff8df",
        fontFamily: "Consolas, monospace",
        fontSize: "10px",
        fontStyle: "bold",
        padding: { x: 3, y: 2 },
      })
      .setDepth(999);
    container.add(label);
  }

  drawPixelBlock(graphics, x, y, width, height, color) {
    graphics.fillStyle(color, 1);
    graphics.fillRect(x, y, width, height);
  }

  scheduleCatWalk(container, index) {
    const delay = Phaser.Math.Between(600, 1800) + index * 220;
    this.time.delayedCall(delay, () => {
      if (!container.active) return;
      const nextX = Phaser.Math.Between(48, GAME_WIDTH - 112);
      const nextY = Phaser.Math.Between(FLOOR_TOP + 42, FLOOR_BOTTOM - 54);
      const duration = Phaser.Math.Between(2600, 5600);
      this.tweens.add({
        targets: container,
        x: nextX,
        y: nextY,
        duration,
        ease: "Sine.easeInOut",
        onUpdate: () => container.setDepth(container.y + 80),
        onComplete: () => this.scheduleCatWalk(container, index),
      });
    });
  }

  spawnCatBubble(container, cat) {
    const lines = [
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
      .setDepth(900);
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
