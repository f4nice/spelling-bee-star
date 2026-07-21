<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { routeApiPaths } from "../routeApiPaths.js";
import { fetchJson } from "../utils.js";

const props = defineProps({
  data: {
    type: Object,
    required: true,
  },
});

const payload = ref(props.data || {});
const activeCategory = ref("food");
const busyItemId = ref("");
const notice = ref("");
const catReaction = ref("");
const catPetSequence = ref(0);
const focusedCatId = ref("");
const gameMountRef = ref(null);
const catWorldGame = ref(null);
const layoutDraft = ref({});
const selectedDecorId = ref("");
const layoutDirty = ref(false);
const savingRoomLayout = ref(false);
const activeToolCategory = ref("decor");
const clockNow = ref(Date.now());
const energyModalOpen = ref(false);
const petBusyCatId = ref("");
const ambientEventCooldowns = new Map();
const foodNibbleCooldowns = new Map();

const catReactionTexts = [
  "收到摸摸指令，开心值上升",
  "启动陪读模式，正在靠近你",
  "尾巴雷达晃了晃，发现新单词",
  "想法缓存刷新，准备继续陪你学",
];
let catReactionTimer = 0;
let activeFoodClockTimer = 0;
let gameMountActive = false;

watch(
  () => props.data,
  (nextData) => {
    payload.value = nextData || {};
  },
);

onBeforeUnmount(() => {
  gameMountActive = false;
  window.clearTimeout(catReactionTimer);
  window.clearInterval(activeFoodClockTimer);
  catWorldGame.value?.destroy();
  catWorldGame.value = null;
});

onMounted(async () => {
  activeFoodClockTimer = window.setInterval(() => {
    clockNow.value = Date.now();
  }, 10000);
  if (!gameMountRef.value) return;
  gameMountActive = true;
  const { CatWorldGame } = await import("../catWorldGame.js");
  if (!gameMountActive || !gameMountRef.value) return;
  catWorldGame.value = new CatWorldGame(gameMountRef.value, {
    onCatPet: petCat,
    onDecorClick: handleDecorClick,
    onDecorSelect: (decorId) => {
      selectedDecorId.value = decorId || "";
    },
    onLayoutChange: handleGameLayoutChange,
    onToyClick: handleRoomToyClick,
    onCatThought: (cat, message) => showCatReaction(cat, message),
    onCatAmbient: recordCatAmbientEvent,
    onFoodVisit: recordCatFoodNibble,
  });
  updateCatWorldGame();
});

const categories = [
  { key: "food", label: "猫粮" },
  { key: "toy", label: "玩具" },
  { key: "decor", label: "装修" },
  { key: "color", label: "配色" },
  { key: "cat", label: "名猫" },
];

const toolCategories = [
  { key: "decor", label: "装饰" },
  { key: "food", label: "食物" },
  { key: "toy", label: "玩具" },
  { key: "cat", label: "猫咪" },
];

const decorToneColors = {
  default: "#ffbfd7",
  sunset: "#ff9b73",
  lavender: "#bca7ff",
  candy: "#ff8cad",
  sky: "#9ee7ff",
  cherry: "#b85a5a",
  mint: "#77d7b2",
  moon: "#d9f6ff",
  peach: "#ffd7c2",
};

const energy = computed(() => payload.value.energy || {});
const state = computed(() => payload.value.state || {});
const inventory = computed(() => state.value.inventory || {});
const usableInventory = computed(() => state.value.usableInventory || inventory.value);
const damagedItems = computed(() => state.value.damagedItems || {});
const roomStyles = computed(() => state.value.roomStyles || {});
const roomLayout = computed(() => state.value.roomLayout || {});
const styleOptions = computed(() => state.value.styleOptions || {});
const dailyLogs = computed(() => state.value.dailyLogs || {});
const catBonds = computed(() => state.value.catBonds || {});
const ownedCats = computed(() => state.value.ownedCats || ["mimi"]);
const cats = computed(() => payload.value.cats || []);
const shop = computed(() => payload.value.shop || []);
const shopById = computed(() => Object.fromEntries(shop.value.map((item) => [item.id, item])));
const selectedCat = computed(() => cats.value.find((cat) => cat.id === state.value.selectedCat) || cats.value[0] || {});
const roomCats = computed(() => {
  const owned = new Set(ownedCats.value);
  const visibleCats = cats.value.filter((cat) => owned.has(cat.id));
  return visibleCats.length ? visibleCats : [selectedCat.value].filter((cat) => cat?.id);
});
const focusedCat = computed(
  () =>
    roomCats.value.find((cat) => cat.id === focusedCatId.value) ||
    roomCats.value.find((cat) => cat.id === state.value.selectedCat) ||
    roomCats.value[0] ||
    {},
);
const mood = computed(() => state.value.mood || {});
const focusedDailyLog = computed(
  () =>
    dailyLogs.value[focusedCat.value.id] ||
    dailyLogs.value[state.value.selectedCat] ||
    mood.value.dailyLog ||
    {},
);
const focusedAgentState = computed(() => focusedDailyLog.value.agentState || {});
const focusedBond = computed(() => catBonds.value[focusedCat.value.id] || {});
const rawActiveFood = computed(() => mood.value.activeFood || {});
const activeFoodRemainingSeconds = computed(() => {
  const food = rawActiveFood.value || {};
  if (!food.active) return 0;
  const expiresAt = parseUtcTimestamp(food.expiresAt);
  if (Number.isFinite(expiresAt)) {
    return Math.max(Math.ceil((expiresAt - clockNow.value) / 1000), 0);
  }
  return Math.max(Number(food.remainingSeconds || 0), 0);
});
const activeFood = computed(() => ({
  ...rawActiveFood.value,
  active: Boolean(rawActiveFood.value?.active && activeFoodRemainingSeconds.value > 0 && Number(rawActiveFood.value?.remainingEnergy ?? 1) > 0),
  remainingSeconds: activeFoodRemainingSeconds.value,
  moodEffective: Number(rawActiveFood.value?.moodEffective || 0),
  catEnergyEffective: Number(rawActiveFood.value?.catEnergyEffective || 0),
  remainingEnergy: Number(rawActiveFood.value?.remainingEnergy || 0),
  targetCatId: rawActiveFood.value?.targetCatId || "",
  targetCatLabel: rawActiveFood.value?.targetCatLabel || "",
}));
const activeFoodEnergyGain = computed(() => Number(activeFood.value.catEnergyEffective || 0));
const activeFoodMoodGain = computed(() => Number(activeFood.value.moodEffective || 0));
const catEnergyScore = computed(() => Number(mood.value.catEnergy ?? 50));
const moodScore = computed(() => Number(mood.value.score ?? 50));
const selectedItems = computed(() => shop.value.filter((item) => item.category === activeCategory.value));
const ownedDecor = computed(() =>
  Object.entries(inventory.value)
    .filter(([itemId, count]) => count > 0 && shopById.value[itemId]?.category === "decor")
    .map(([itemId]) => shopById.value[itemId]),
);
const ownedToys = computed(() =>
  Object.entries(inventory.value)
    .filter(([itemId, count]) => count > 0 && shopById.value[itemId]?.category === "toy")
    .map(([itemId]) => shopById.value[itemId]),
);
const ownedFoodCount = computed(() =>
  Object.entries(inventory.value)
    .filter(([itemId]) => shopById.value[itemId]?.category === "food")
    .reduce((sum, [, count]) => sum + Number(count || 0), 0),
);
const lastPlayLabel = computed(() => shopById.value[mood.value.lastPlayItem]?.label || "");
const activeToolItems = computed(() => {
  if (activeToolCategory.value === "cat") {
    return cats.value
      .filter((cat) => ownsCat(cat.id))
      .map((cat) => ({
        ...cat,
        category: "cat",
        count: 1,
        actionLabel: state.value.selectedCat === cat.id ? "正在陪读" : "切换主猫",
      }));
  }
  return shop.value
    .filter((item) => item.category === activeToolCategory.value && itemCount(item.id) > 0)
    .map((item) => ({
      ...item,
      count: itemCount(item.id),
      damageInfo: damagedItems.value[item.id] || null,
      styleOptions: item.category === "decor" ? decorStyleOptions(item.id) : [],
      favoriteLabel: itemFavoriteLabel(item),
      actionLabel: ownedToolActionText(item),
    }));
});
const focusedCatThought = computed(() => {
  const agent = focusedAgentState.value || {};
  const behavior = agent.currentBehavior || {};
  if (agent.voiceLine || agent.dailyWish) {
    return [
      agent.voiceLine,
      agent.dailyWish ? `今日愿望：${agent.dailyWish}` : "",
      behavior.label ? `当前${behavior.label}` : "",
    ].filter(Boolean).join("。") + "。";
  }
  if (agent.dailyMoodLabel || behavior.label) {
    return `${agent.dailyMoodLabel || "今天状态稳定"}，${behavior.label || "自由活动"}。${agent.routine || "正在观察房间里的学习节奏"}。`;
  }
  const thoughts = focusedCat.value.thoughts || [];
  if (!thoughts.length) {
    return "正在观察你的学习节奏。";
  }
  return thoughts[catPetSequence.value % thoughts.length];
});
const focusedCatDailyNote = computed(() => {
  const log = focusedDailyLog.value || {};
  const agent = focusedAgentState.value || {};
  const favoriteDecorLabels = focusedCat.value.favoriteDecorLabels || [];
  const damaged = agent.mischiefLabel
    ? ` · 今天弄坏过 ${agent.mischiefLabel}`
    : agent.mischiefRepairedLabel
      ? ` · 已维修 ${agent.mischiefRepairedLabel}，花费 ${agent.mischiefRepairCost || 0} 能量`
    : agent.mischiefAttemptReason
      ? ` · 捣蛋观察: ${agent.mischiefAttemptReason}`
      : "";
  const comfort = agent.comfortLabel || "暂无道具减耗";
  const reason = agent.hourlyReason || "自由活动";
  const bondText = focusedBond.value.levelLabel ? ` · 信任 ${focusedBond.value.levelLabel} ${focusedBond.value.score || 18}` : "";
  return `每小时 体力 ${signedHourlyValue(log.hourlyEnergyDecay)} / 心情 ${signedHourlyValue(log.hourlyMoodDecay)} · ${reason} · ${comfort} · 独立状态 ${agent.dailyMoodLabel || "稳定"} · 喜欢 ${favoriteDecorLabels.join("、") || "安静角落"}${bondText}${damaged}`;
});
const focusedAgentEvents = computed(() => {
  const events = focusedAgentState.value.events;
  if (!Array.isArray(events)) return [];
  return events.filter((event) => event?.message).slice(-4).reverse();
});
const focusedAgentProfileTags = computed(() => {
  const tags = focusedAgentState.value.profileTags;
  if (Array.isArray(tags)) return tags.filter(Boolean).slice(0, 4);
  return [focusedAgentState.value.personaLabel, focusedAgentState.value.playStyleLabel, focusedAgentState.value.socialStyleLabel]
    .filter(Boolean)
    .slice(0, 4);
});
function clampCatScore(value) {
  const score = Number(value);
  if (!Number.isFinite(score)) return 0;
  return Math.max(0, Math.min(100, score));
}

function formatCatHour(value) {
  const hour = Math.max(0, Math.min(23, Number(value) || 0));
  return `${String(hour).padStart(2, "0")}:00`;
}

function decorLabel(decorId) {
  return shopById.value[decorId]?.label
    || (payload.value.decorFavorites || []).find((favorite) => favorite.decorId === decorId)?.decorLabel
    || decorId;
}

function signedHourlyValue(value) {
  const numeric = Number(value || 0);
  if (!Number.isFinite(numeric) || numeric === 0) return "0";
  return numeric > 0 ? `+${numeric}` : `${numeric}`;
}

const catAgentCards = computed(() =>
  cats.value.map((cat) => {
    const owned = ownsCat(cat.id);
    const log = dailyLogs.value[cat.id] || {};
    const agent = log.agentState || {};
    const behavior = agent.currentBehavior || {};
    const bond = catBonds.value[cat.id] || {};
    const agentEvents = Array.isArray(agent.events) ? agent.events.filter((event) => event?.message) : [];
    const latestEvent = agentEvents.length ? agentEvents[agentEvents.length - 1] : null;
    return {
      ...cat,
      owned,
      log,
      agent,
      behaviorLabel: behavior.label || (owned ? "自由活动" : "未解锁"),
      moodScore: clampCatScore(log.moodScore ?? agent.adjustedMoodScore ?? 0),
      energyScore: clampCatScore(log.energyScore ?? agent.adjustedEnergyScore ?? 0),
      bondScore: clampCatScore(bond.score ?? 18),
      bondLabel: bond.levelLabel || "刚开始熟悉",
      bondDetailLabel: bond.detailLabel || "还没有照顾记录",
      dailyMoodLabel: agent.dailyMoodLabel || (owned ? "今天状态稳定" : "等待解锁"),
      latestEvent,
    };
  }),
);
const catAgentDiaries = computed(() =>
  catAgentCards.value
    .filter((cat) => cat.owned)
    .map((cat) => {
      const traits = cat.traits || {};
      const agent = cat.agent || {};
      const log = cat.log || {};
      const dailyGoal = agent.dailyGoal || {};
      const activeFavoriteLabels = (log.favoriteActiveDecorIds || []).map(decorLabel);
      const favoriteItemLabel = (cat.favoriteItemLabels || []).join("、") || "偏好待发现";
      const sleepStart = formatCatHour(traits.sleepStart ?? 23);
      const sleepEnd = formatCatHour(traits.sleepEnd ?? 7);
      const damagedItem = log.damagedItemId ? shopById.value[log.damagedItemId]?.label || log.damagedItemId : "";
      const repairedItem = agent.mischiefRepairedLabel || "";
      const mischiefAttemptReason = agent.mischiefAttemptReason || "";
      const hourlyHistory = Array.isArray(agent.hourlyHistory)
        ? agent.hourlyHistory.filter((row) => row?.label).slice(-3).reverse()
        : [];
      return {
        ...cat,
        attention: clampCatScore(agent.attention ?? 0),
        curiosity: clampCatScore(agent.curiosity ?? 0),
        mischief: clampCatScore(agent.mischief ?? 0),
        stamina: clampCatScore(agent.stamina ?? 0),
        activityBias: clampCatScore(agent.activityBias ?? 0),
        socialNeed: clampCatScore(agent.socialNeed ?? 0),
        dailyProfileLabel: [agent.staminaLabel, agent.activityLabel, agent.socialNeedLabel].filter(Boolean).join(" · "),
        personaLabel: agent.personaLabel || cat.personality || "学习陪伴型",
        dailyWish: agent.dailyWish || dailyGoal.message || "",
        voiceLine: agent.voiceLine || "",
        playStyleLabel: agent.playStyleLabel || "玩耍节奏稳定",
        socialStyleLabel: agent.socialStyleLabel || "陪伴需求稳定",
        carePreferenceLabel: agent.carePreferenceLabel || traits.label || "",
        sleepLabel: traits.nightOwl ? `夜猫子 · ${sleepStart}-${sleepEnd}` : `${sleepStart}-${sleepEnd}`,
        routineLabel: agent.routine || traits.routine || "观察房间里的学习节奏",
        goalLabel: dailyGoal.label || "自由散步",
        goalMessage: dailyGoal.message || "",
        careTip: agent.careTip || "",
        damageRiskLabel: dailyGoal.damageRiskReason
          ? `${dailyGoal.damageRiskLabel || "很低"} · ${dailyGoal.damageRiskReason}`
          : dailyGoal.damageRiskLabel || "很低",
        decayLabel: `体力 ${signedHourlyValue(log.hourlyEnergyDecay)}/h · 心情 ${signedHourlyValue(log.hourlyMoodDecay)}/h`,
        comfortLabel: agent.comfortLabel || "暂无道具减耗",
        favoriteItemLabel,
        activeFavoriteLabel: activeFavoriteLabels.length ? activeFavoriteLabels.join("、") : "喜欢的家具还没摆出来",
        countsLabel: `食物 ${log.foodCount || 0} · 玩具 ${log.toyCount || 0} · 摸摸 ${agent.petCount || 0}`,
        bondLabel: `${cat.bondLabel} · ${cat.bondScore}/100`,
        bondDetailLabel: cat.bondDetailLabel,
        damageLabel: damagedItem
          ? `今天弄坏过 ${damagedItem}`
          : repairedItem
            ? `今天已维修 ${repairedItem}，花费 ${agent.mischiefRepairCost || 0} 能量`
          : mischiefAttemptReason
            ? `今天有捣蛋冲动: ${mischiefAttemptReason}，但没有弄坏东西`
            : "今天没有破坏记录",
        hourlyHistory,
      };
    }),
);
const gameSnapshot = computed(() => ({
  cats: cats.value,
  inventory: inventory.value,
  damagedItems: damagedItems.value,
  layout: roomLayout.value,
  mood: mood.value,
  activeFood: activeFood.value,
  dailyLogs: dailyLogs.value,
  ownedCats: ownedCats.value,
  ownedFoodCount: ownedFoodCount.value,
  roomStyles: roomStyles.value,
  selectedCatId: state.value.selectedCat,
}));

watch(
  gameSnapshot,
  () => {
    updateCatWorldGame();
  },
  { deep: true },
);

watch(
  roomLayout,
  (nextLayout) => {
    layoutDraft.value = normalizeLayoutDraft(nextLayout);
    layoutDirty.value = false;
    selectedDecorId.value = "";
  },
  { immediate: true },
);

function replacePayload(nextPayload) {
  if (nextPayload?.energy && nextPayload?.state) {
    payload.value = nextPayload;
  }
}

function updateCatWorldGame() {
  catWorldGame.value?.update(gameSnapshot.value);
}

function handleGameLayoutChange(nextLayout, itemId) {
  selectedDecorId.value = itemId || selectedDecorId.value;
  layoutDraft.value = normalizeLayoutDraft(nextLayout);
  layoutDirty.value = true;
}

function itemCount(itemId) {
  return Number(inventory.value[itemId] || 0);
}

function clampNumber(value, min, max) {
  return Math.min(Math.max(Number(value) || 0, min), max);
}

function parseUtcTimestamp(value) {
  const raw = String(value || "").trim();
  if (!raw) return Number.NaN;
  return Date.parse(/(?:z|[+-]\d{2}:?\d{2})$/i.test(raw) ? raw : `${raw}Z`);
}

function normalizeLayoutDraft(layout) {
  const nextLayout = {};
  for (const [decorId, position] of Object.entries(layout || {})) {
    nextLayout[decorId] = {
      x: clampNumber(position?.x, 0, 92),
      y: clampNumber(position?.y, 0, 86),
    };
  }
  return nextLayout;
}

function handleDecorClick(decorId) {
  const item = shopById.value[decorId];
  if (item && damageInfo(item)) {
    repairItem(item);
    return;
  }
  selectedDecorId.value = decorId;
  cycleDecorStyle(decorId);
}

function handleRoomToyClick(itemId) {
  const item = shopById.value[itemId];
  if (item && ["food", "toy"].includes(item.category)) {
    if (damageInfo(item)) {
      repairItem(item);
      return;
    }
    if (item.category === "food" && activeFood.value.active && activeFood.value.itemId === item.id) {
      notice.value = `${item.label} 正在房间里，优先给${activeFood.value.targetCatLabel || "体力最低的小猫"}慢慢吃，剩余可补体力 ${activeFood.value.remainingEnergy || 0}，还剩 ${formatSeconds(activeFood.value.remainingSeconds)}。`;
      const targetCat = cats.value.find((cat) => cat.id === activeFood.value.targetCatId) || focusedCat.value;
      showCatReaction(targetCat, `${item.label}还在房间里，我会慢慢吃完。`);
      return;
    }
    play(item);
  }
}

function recordCatAmbientEvent(cat, event = {}) {
  if (!cat?.id || !event?.kind || !event?.itemId) return;
  const key = `${cat.id}:${event.kind}:${event.itemId}`;
  const now = Date.now();
  if (now - Number(ambientEventCooldowns.get(key) || 0) < 4 * 60 * 1000) return;
  ambientEventCooldowns.set(key, now);
  fetchJson(routeApiPaths.catWorldAgentEvent(), {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      catId: cat.id,
      kind: event.kind,
      itemId: event.itemId,
      label: event.label || "",
    }),
  }).then((nextPayload) => {
    if (nextPayload?.energy && nextPayload?.state) {
      replacePayload(nextPayload);
    }
    if (event.kind === "rest-spot" && nextPayload?.recorded && nextPayload?.event?.message) {
      const targetCat = cats.value.find((item) => item.id === nextPayload.effect?.catId) || cat;
      showCatReaction(targetCat, nextPayload.event.message);
    }
  }).catch(() => {
    ambientEventCooldowns.delete(key);
  });
}

function recordCatFoodNibble(cat, event = {}) {
  if (!cat?.id || !activeFood.value.active) return;
  if (activeFood.value.targetCatId && activeFood.value.targetCatId !== cat.id) return;
  const token = rawActiveFood.value?.expiresAt || activeFood.value.itemId || "active-food";
  const key = `${cat.id}:${token}`;
  const now = Date.now();
  if (now - Number(foodNibbleCooldowns.get(key) || 0) < 45 * 1000) return;
  foodNibbleCooldowns.set(key, now);
  fetchJson(routeApiPaths.catWorldFoodNibble(), {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      catId: cat.id,
      itemId: event.itemId || activeFood.value.itemId,
    }),
  }).then((nextPayload) => {
    replacePayload(nextPayload);
    const effect = nextPayload?.effect || {};
    if (effect.recorded && effect.message) {
      const targetCat = cats.value.find((item) => item.id === effect.catId) || cat;
      showCatReaction(targetCat, effect.message);
    }
  }).catch(() => {
    foodNibbleCooldowns.delete(key);
  });
}

function ownedToolCount(categoryKey) {
  if (categoryKey === "cat") return ownedCats.value.length;
  return shop.value.filter((item) => item.category === categoryKey && itemCount(item.id) > 0).length;
}

function ownedToolActionText(item) {
  const damaged = damageInfo(item);
  if (damaged) return `维修 ${damaged.repairCost || 0} 能量`;
  if (item.category === "decor") return selectedDecorId.value === item.id ? "已选中" : "选择拖动";
  if (item.category === "food") return `摆进房间 +${foodEnergyGainValue(item)}体力`;
  if (item.category === "toy") return "房间可拖动";
  if (item.category === "cat") return state.value.selectedCat === item.id ? "正在陪读" : "切换主猫";
  return "使用";
}

function ownedToolSubtext(item) {
  const damaged = damageInfo(item);
  if (damaged) return `损坏 · ${damaged.reason || "需要维修后才能使用"}`;
  if (item.category === "cat") return item.personality || "正在陪读";
  const suffix = item.favoriteLabel ? ` · ${item.favoriteLabel}` : "";
  return `拥有 ${item.count}${suffix}`;
}

function catFoodTraitMultiplier() {
  return Number(selectedCat.value?.traits?.foodEnergyGain || 1);
}

function foodEnergyGainValue(item) {
  return Math.round(Number(item?.catEnergy || 0) * catFoodTraitMultiplier());
}

function foodMoodGainValue(item) {
  return Math.round(Number(item?.mood || 0) * catFoodTraitMultiplier());
}

function decorStyleOptions(decorId) {
  const options = styleOptions.value[decorId];
  if (Array.isArray(options) && options.length) return options;
  return [{ itemId: "default", tone: "default", label: "默认色" }];
}

function decorToneColor(tone) {
  return decorToneColors[tone] || decorToneColors.default;
}

function itemFavoriteLabel(item) {
  if (item?.favoriteCatLabel) return `${item.favoriteCatLabel}喜欢`;
  if (item?.category !== "decor") return "";
  const matched = (payload.value.decorFavorites || []).find((favorite) => favorite.decorId === item.id);
  return matched?.catLabel ? `${matched.catLabel}喜欢` : "";
}

function damageInfo(item) {
  return item?.id ? damagedItems.value[item.id] || null : null;
}

function isDamagedItem(item) {
  return Boolean(damageInfo(item));
}

function handleOwnedToolClick(item) {
  if (!item?.id || busyItemId.value) return;
  if (isDamagedItem(item)) {
    repairItem(item);
    return;
  }
  if (item.category === "decor") {
    selectedDecorId.value = item.id;
    notice.value = `已选中 ${item.label}，在左侧房间里拖动它后点击保存布局。`;
    return;
  }
  if (item.category === "toy") {
    selectedDecorId.value = item.id;
    notice.value = `${item.label} 可以直接在左侧房间里拖动保存；点击房间里的它会和猫咪互动。`;
    return;
  }
  if (item.category === "food") {
    play(item);
    return;
  }
  if (item.category === "cat") {
    selectCat(item.id);
  }
}

function formatSeconds(seconds) {
  const total = Math.max(Number(seconds || 0), 0);
  const minutes = Math.floor(total / 60);
  const rest = Math.floor(total % 60);
  if (minutes <= 0) return `${rest} 秒`;
  return `${minutes} 分 ${String(rest).padStart(2, "0")} 秒`;
}

async function saveRoomLayout() {
  if (savingRoomLayout.value || !layoutDirty.value) return;
  savingRoomLayout.value = true;
  notice.value = "";
  try {
    const nextLayout = catWorldGame.value?.getLayout() || layoutDraft.value;
    layoutDraft.value = normalizeLayoutDraft(nextLayout);
    const nextPayload = await fetchJson(routeApiPaths.catWorldRoomLayout(), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ layout: layoutDraft.value }),
    });
    replacePayload(nextPayload);
    layoutDirty.value = false;
    const rewards = Array.isArray(nextPayload.layoutRewards) ? nextPayload.layoutRewards : [];
    if (rewards.length) {
      const firstReward = rewards[0];
      const rewardText = rewards
        .slice(0, 3)
        .map((reward) => `${reward.catLabel || "猫咪"}喜欢${reward.decorLabel || "这件家具"}，心情 +${reward.moodGain || 0}`)
        .join("；");
      notice.value = `房间布局已保存。${rewardText}${rewards.length > 3 ? "……" : ""}。`;
      const rewardCat = cats.value.find((cat) => cat.id === firstReward.catId) || focusedCat.value;
      showCatReaction(rewardCat, `喜欢${firstReward.decorLabel || "这个布置"}，心情 +${firstReward.moodGain || 0}。`);
    } else {
      notice.value = "房间布局已保存。";
    }
  } catch (error) {
    notice.value = error.message || "布局保存失败，请稍后再试。";
  } finally {
    savingRoomLayout.value = false;
  }
}

function decorTone(decorId) {
  return roomStyles.value[decorId] || "default";
}

function ownsCat(catId) {
  return ownedCats.value.includes(catId);
}

function canAfford(item) {
  return Number(energy.value.available || 0) >= Number(item.cost || 0);
}

function targetDecorOwned(item) {
  return !item?.targetDecor || itemCount(item.targetDecor) > 0;
}

function colorApplied(item) {
  return item?.category === "color" && decorTone(item.targetDecor) === item.tone;
}

function isOneTimeOwned(item) {
  return ["toy", "decor", "color"].includes(item?.category) && itemCount(item.id) > 0;
}

function canPurchase(item) {
  if (!item?.id) return false;
  if (item.category === "cat") return ownsCat(item.id) ? state.value.selectedCat !== item.id : canAfford(item);
  if (item.category === "color") return targetDecorOwned(item) && (itemCount(item.id) > 0 || canAfford(item));
  if (["toy", "decor"].includes(item.category)) return !isOneTimeOwned(item) && canAfford(item);
  return canAfford(item);
}

function purchaseHint(item) {
  if (!item?.id) return "";
  if (item.category === "color" && !targetDecorOwned(item)) {
    return `需要先购买${item.targetDecorLabel || "对应家具"}`;
  }
  if (isOneTimeOwned(item) && item.category !== "color") {
    if (isDamagedItem(item)) return "已拥有但被弄坏了，去右侧背包维修";
    return "已拥有，不会重复扣分";
  }
  if (item.category === "color" && itemCount(item.id) > 0) {
    return colorApplied(item) ? "当前正在使用" : "已拥有，点击应用";
  }
  const remaining = Math.max(Number(energy.value.available || 0) - Number(item.cost || 0), 0);
  if (item.category === "food") {
    return `扣 ${item.cost} 能量 · 摆放后体力 +${foodEnergyGainValue(item)}、心情 +${foodMoodGainValue(item)} · 剩余 ${remaining}`;
  }
  return `将扣 ${item.cost} 积分 · 购买后剩余 ${remaining}`;
}

function purchaseButtonText(item) {
  if (busyItemId.value === item.id) return "处理中...";
  if (item.category === "cat" && ownsCat(item.id) && state.value.selectedCat !== item.id) return "设为主猫";
  if (item.category === "cat" && ownsCat(item.id)) return "已选择";
  if (item.category === "color" && !targetDecorOwned(item)) return "先买家具";
  if (item.category === "color" && colorApplied(item)) return "已应用";
  if (item.category === "color" && itemCount(item.id) > 0) return "应用配色";
  if (isDamagedItem(item)) return "去右侧维修";
  if (isOneTimeOwned(item)) return "已拥有";
  return canAfford(item) ? `扣 ${item.cost} 积分购买` : "能量不足";
}

function showCatReaction(cat = selectedCat.value, message = "") {
  const catLabel = cat?.label || "猫咪";
  const nextIndex = catPetSequence.value % catReactionTexts.length;
  focusedCatId.value = cat?.id || "";
  catReaction.value = `${catLabel}: ${message || catReactionTexts[nextIndex]}`;
  catPetSequence.value += 1;
  window.clearTimeout(catReactionTimer);
  catReactionTimer = window.setTimeout(() => {
    catReaction.value = "";
  }, 2200);
}

async function petCat(cat = selectedCat.value, options = {}) {
  if (!cat?.id) return;
  showCatReaction(cat, options.message || "");
  if (options.sync === false || petBusyCatId.value === cat.id) return;
  petBusyCatId.value = cat.id;
  try {
    const nextPayload = await fetchJson(routeApiPaths.catWorldPet(), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ catId: cat.id }),
    });
    replacePayload(nextPayload);
    if (nextPayload.effect?.message) {
      showCatReaction(cat, nextPayload.effect.message);
    }
  } catch (error) {
    notice.value = error.message || "猫咪互动失败，请稍后再试。";
  } finally {
    petBusyCatId.value = "";
  }
}

async function purchase(item) {
  if (!item?.id || busyItemId.value) return;
  if (item.category === "cat" && ownsCat(item.id)) {
    await selectCat(item.id);
    return;
  }
  busyItemId.value = item.id;
  notice.value = "";
  try {
    const nextPayload = await fetchJson(routeApiPaths.catWorldPurchase(), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ itemId: item.id }),
    });
    replacePayload(nextPayload);
    notice.value = `${item.label} 已加入猫咪世界。`;
  } catch (error) {
    notice.value = error.message || "购买失败，请稍后再试。";
  } finally {
    busyItemId.value = "";
  }
}

async function play(item) {
  if (!item?.id || busyItemId.value) return;
  busyItemId.value = item.id;
  notice.value = "";
  try {
    const nextPayload = await fetchJson(routeApiPaths.catWorldPlay(), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ itemId: item.id }),
    });
    replacePayload(nextPayload);
    if (item.category === "food") {
      const active = nextPayload.state?.mood?.activeFood;
      const effect = nextPayload.effect || {};
      const targetCat = cats.value.find((cat) => cat.id === effect.catId) || focusedCat.value;
      const energyGain = Number(effect.energyGain ?? 0);
      const moodGain = Number(effect.moodGain ?? 0);
      const totalEnergyGain = Number(effect.totalEnergyGain ?? active?.catEnergyEffective ?? foodEnergyGainValue(item));
      const totalMoodGain = Number(effect.totalMoodGain ?? active?.moodEffective ?? foodMoodGainValue(item));
      const remainingEnergy = Number(effect.remainingEnergy ?? active?.remainingEnergy ?? 0);
      const remainingSeconds = Number(effect.remainingSeconds ?? active?.remainingSeconds ?? 0);
      const targetName = effect.catLabel || active?.targetCatLabel || "体力最低的小猫";
      const favoriteText = effect.favoriteMatch || active?.favoriteMatch ? "（正好是它喜欢的）" : "";
      const restText = effect.finished
        ? "已经吃完，食物从房间里消失了"
        : `剩余可补体力 ${remainingEnergy}，约 ${formatSeconds(remainingSeconds)} 后吃完`;
      notice.value = `${item.label} 已摆进房间${favoriteText}，优先给${targetName}，库存 -1，本次吃掉体力 +${energyGain}、心情 +${moodGain}，总计体力 +${totalEnergyGain}、心情 +${totalMoodGain}，${restText}。`;
      showCatReaction(targetCat, `先吃了一口${item.label}${favoriteText}，体力 +${energyGain}，心情 +${moodGain}。`);
    } else {
      const effect = nextPayload.effect || {};
      const targetCat = cats.value.find((cat) => cat.id === effect.catId) || selectedCat.value;
      const favoriteText = effect.favoriteMatch ? "最喜欢的" : "";
      notice.value = `${effect.catLabel || targetCat.label || "猫咪"} 和 ${favoriteText}${item.label} 玩了一会儿，心情 +${effect.moodGain ?? item.mood ?? 0}，体力 ${effect.energyGain ?? 0}。`;
      showCatReaction(targetCat, `玩了${favoriteText}${item.label}，心情 +${effect.moodGain ?? item.mood ?? 0}。`);
    }
  } catch (error) {
    notice.value = error.message || "互动失败，请稍后再试。";
  } finally {
    busyItemId.value = "";
  }
}

async function repairItem(item) {
  if (!item?.id || busyItemId.value) return;
  const damaged = damageInfo(item);
  if (!damaged) return;
  busyItemId.value = item.id;
  notice.value = "";
  try {
    const nextPayload = await fetchJson(routeApiPaths.catWorldRepair(), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ itemId: item.id }),
    });
    replacePayload(nextPayload);
    const repair = nextPayload.repair || {};
    const cost = repair.cost ?? damaged.repairCost ?? 0;
    const targetCat = cats.value.find((cat) => cat.id === repair.catId) || focusedCat.value;
    notice.value = `${repair.label || item.label} 已维修好，扣 ${cost} 能量，已记录到${repair.catLabel || targetCat.label || "猫咪"}今天的档案。`;
    showCatReaction(targetCat, `${repair.label || item.label}修好了，我会小心一点。`);
  } catch (error) {
    notice.value = error.message || "维修失败，请稍后再试。";
  } finally {
    busyItemId.value = "";
  }
}

async function cycleDecorStyle(decorId) {
  if (!decorId || busyItemId.value) return;
  busyItemId.value = decorId;
  notice.value = "";
  try {
    const nextPayload = await fetchJson(routeApiPaths.catWorldDecorStyle(), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ decorId }),
    });
    replacePayload(nextPayload);
    notice.value = nextPayload.style?.label ? `已切换为${nextPayload.style.label}。` : "装修颜色已切换。";
  } catch (error) {
    notice.value = error.message || "颜色切换失败，请先购买更多配色。";
  } finally {
    busyItemId.value = "";
  }
}

async function applyDecorStyle(decorId, option) {
  if (!decorId || !option?.tone || busyItemId.value) return;
  busyItemId.value = decorId;
  selectedDecorId.value = decorId;
  notice.value = "";
  try {
    const nextPayload = await fetchJson(routeApiPaths.catWorldDecorStyle(), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ decorId, tone: option.tone }),
    });
    replacePayload(nextPayload);
    notice.value = `${nextPayload.style?.label || option.label || "配色"} 已应用，拖动家具后可以保存布局。`;
  } catch (error) {
    notice.value = error.message || "颜色切换失败，请先购买这个配色。";
  } finally {
    busyItemId.value = "";
  }
}

async function selectCat(catId) {
  if (!catId || busyItemId.value) return;
  busyItemId.value = catId;
  notice.value = "";
  try {
    const nextPayload = await fetchJson(routeApiPaths.catWorldSelectCat(), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ catId }),
    });
    replacePayload(nextPayload);
    const cat = cats.value.find((item) => item.id === catId);
    focusedCatId.value = catId;
    notice.value = `${cat?.label || "猫咪"} 正在房间里陪读。`;
  } catch (error) {
    notice.value = error.message || "切换猫咪失败，请稍后再试。";
  } finally {
    busyItemId.value = "";
  }
}
</script>

<template>
  <section class="cat-world-page">
    <section class="cat-world-hero">
      <div class="cat-world-copy">
        <p class="section-kicker">Cat World</p>
        <h1>猫咪能量世界</h1>
        <p>把今天练过的英文变成软绵绵的能量，给猫咪买小鱼干、玩具和漂亮家具，把她的房间一点点装可爱。</p>
      </div>
      <button class="cat-world-wallet" type="button" aria-label="猫咪世界能量" @click="energyModalOpen = true">
        <span>可用能量</span>
        <strong>{{ energy.available || 0 }}</strong>
        <small>累计 {{ energy.earned || 0 }} · 已用 {{ energy.spent || 0 }}</small>
      </button>
    </section>

    <section class="cat-world-layout">
      <section class="cat-world-room-panel panel">
        <div class="cat-world-room-head">
          <div>
            <p class="section-kicker">Room</p>
            <h2>像素猫活动室</h2>
          </div>
          <div class="cat-world-mood cat-world-dual-status">
            <span>{{ mood.catEnergyLabel || "体力稳定" }}</span>
            <strong>{{ catEnergyScore }}</strong>
            <small>{{ mood.label || "安静陪读" }} · {{ moodScore }}</small>
          </div>
        </div>

        <div class="cat-world-ai-panel" aria-live="polite">
          <span>CAT-OS</span>
          <strong>{{ focusedCat.label || "猫咪" }} · {{ focusedCat.personality || "学习陪伴型" }}</strong>
          <p>{{ focusedCatThought }}</p>
          <div v-if="focusedAgentProfileTags.length" class="cat-world-agent-profile-tags">
            <span v-for="tag in focusedAgentProfileTags" :key="tag">{{ tag }}</span>
          </div>
          <small>{{ focusedCatDailyNote }}</small>
          <ul v-if="focusedAgentEvents.length" class="cat-world-agent-events">
            <li v-for="event in focusedAgentEvents" :key="`${event.time}-${event.kind}-${event.message}`">
              <b>{{ event.time }}</b>
              <span>{{ event.label }}</span>
              <em>{{ event.message }}</em>
            </li>
          </ul>
        </div>

        <div class="cat-world-room" aria-label="猫咪房间场景">
          <div ref="gameMountRef" class="cat-world-game-stage"></div>
          <div v-if="selectedDecorId || layoutDirty" class="cat-world-layout-toolbar">
            <span>{{ layoutDirty ? "布局有改动" : "拖动道具后可保存布局" }}</span>
            <button
              type="button"
              :disabled="!layoutDirty || savingRoomLayout"
              @click="saveRoomLayout"
            >
              {{ savingRoomLayout ? "保存中..." : "保存布局" }}
            </button>
          </div>
          <div
            v-if="catReaction"
            :key="`cat-reaction-${catPetSequence}`"
            class="cat-world-reaction"
            aria-live="polite"
          >
            {{ catReaction }}
          </div>
          <div
            v-if="catPetSequence"
            :key="`cat-sparkles-${catPetSequence}`"
            class="cat-world-sparkles"
            aria-hidden="true"
          >
            <span></span><span></span><span></span><span></span>
          </div>
        </div>

        <div class="cat-world-room-status">
          <span>已拥有装饰 {{ ownedDecor.length }}</span>
          <span>食物 {{ ownedFoodCount }}</span>
          <span>猫咪 {{ ownedCats.length }}</span>
          <span v-if="activeFood.active">食物剩余 {{ formatSeconds(activeFood.remainingSeconds) }}</span>
          <span v-if="lastPlayLabel">刚刚玩过 {{ lastPlayLabel }}</span>
        </div>
      </section>

      <aside class="cat-world-owned-panel panel">
        <div class="cat-world-owned-head">
          <div>
            <p class="section-kicker">Bag</p>
            <h2>已拥有道具</h2>
          </div>
          <span>{{ activeToolItems.length }} 个</span>
        </div>

        <div class="cat-world-status-bars" aria-label="猫咪状态">
          <div class="cat-world-status-bar energy">
            <span>能量</span>
            <strong>{{ catEnergyScore }}</strong>
            <i :style="{ width: `${catEnergyScore}%` }"></i>
          </div>
          <div class="cat-world-status-bar mood">
            <span>心情</span>
            <strong>{{ moodScore }}</strong>
            <i :style="{ width: `${moodScore}%` }"></i>
          </div>
        </div>

        <div v-if="activeFood.active" class="cat-world-active-food">
          <span>当前食物</span>
          <strong>{{ activeFood.label }}</strong>
          <small>优先给 {{ activeFood.targetCatLabel || "体力最低的小猫" }} · 剩余可补体力 {{ activeFood.remainingEnergy || 0 }} · 总计体力 +{{ activeFoodEnergyGain }} · 总计心情 +{{ activeFoodMoodGain }} · {{ formatSeconds(activeFood.remainingSeconds) }}</small>
        </div>

        <div class="cat-world-tool-tabs" role="tablist" aria-label="已拥有道具分类">
          <button
            v-for="category in toolCategories"
            :key="category.key"
            type="button"
            :class="{ active: activeToolCategory === category.key }"
            @click="activeToolCategory = category.key"
          >
            {{ category.label }}
            <span>{{ ownedToolCount(category.key) }}</span>
          </button>
        </div>

        <div class="cat-world-owned-list">
          <article
            v-for="item in activeToolItems"
            :key="`${activeToolCategory}-${item.id}`"
            :class="[
              'cat-world-owned-item',
              { active: selectedDecorId === item.id || state.selectedCat === item.id, damaged: item.damageInfo },
            ]"
          >
            <button
              class="cat-world-owned-main"
              type="button"
              :disabled="busyItemId === item.id"
              @click="handleOwnedToolClick(item)"
            >
              <span>{{ item.englishName || item.rarity || item.category }}</span>
              <strong>{{ item.label }}</strong>
              <small>{{ ownedToolSubtext(item) }}</small>
              <em>{{ busyItemId === item.id ? "处理中..." : item.actionLabel }}</em>
            </button>
            <div v-if="item.category === 'decor' && item.styleOptions?.length" class="cat-world-color-swatches" aria-label="已拥有配色">
              <button
                v-for="option in item.styleOptions"
                :key="`${item.id}-${option.tone}`"
                type="button"
                class="cat-world-color-swatch"
                :class="{ active: decorTone(item.id) === option.tone }"
                :style="{ '--swatch-color': decorToneColor(option.tone) }"
                :title="option.label"
                :aria-label="`应用${option.label}`"
                :disabled="busyItemId === item.id"
                @click.stop="applyDecorStyle(item.id, option)"
              ></button>
            </div>
          </article>
          <p v-if="!activeToolItems.length" class="cat-world-owned-empty">这个分类还没有道具，可以在下方商店购买。</p>
        </div>
      </aside>
    </section>

    <section class="cat-world-market panel">
      <div class="cat-world-market-head">
        <div>
          <p class="section-kicker">Shop</p>
          <h2>猫咪商店</h2>
        </div>
        <div class="cat-world-tabs" role="tablist" aria-label="商店分类">
          <button
            v-for="category in categories"
            :key="category.key"
            type="button"
            :class="{ active: activeCategory === category.key }"
            @click="activeCategory = category.key"
          >
            {{ category.label }}
          </button>
        </div>
      </div>

      <p v-if="notice" class="cat-world-notice">{{ notice }}</p>

      <div class="cat-world-shop-grid">
        <article v-for="item in selectedItems" :key="item.id" class="cat-world-shop-card">
          <div>
            <span>{{ item.englishName }}</span>
            <h3>{{ item.label }}</h3>
            <p>{{ item.description }}</p>
          </div>
          <div class="cat-world-shop-meta">
            <strong>{{ item.cost }} 能量</strong>
            <em v-if="item.hasCustomCost">后台价 · 默认 {{ item.defaultCost }}</em>
            <span v-if="item.category === 'cat' && ownsCat(item.id)">
              {{ state.selectedCat === item.id ? "正在陪读" : "已拥有" }}
            </span>
            <span v-else-if="item.category === 'color' && itemCount(item.id)">
              {{ colorApplied(item) ? "已应用" : "已解锁" }}
            </span>
            <span v-else-if="item.category === 'color' && item.targetDecorLabel">用于 {{ item.targetDecorLabel }}</span>
            <span v-else-if="item.category !== 'cat' && itemCount(item.id)">已有 {{ itemCount(item.id) }}</span>
            <span v-else>心情 +{{ item.mood }}</span>
          </div>
          <p class="cat-world-cost-preview">{{ purchaseHint(item) }}</p>
          <button
            class="primary-action-button"
            type="button"
            :disabled="busyItemId === item.id || !canPurchase(item) || (item.category === 'color' && colorApplied(item))"
            @click="purchase(item)"
          >
            {{ purchaseButtonText(item) }}
          </button>
        </article>
      </div>
    </section>

    <section class="cat-world-agent-diary panel">
      <div class="cat-world-market-head">
        <div>
          <p class="section-kicker">Agent Diary</p>
          <h2>今日猫咪档案</h2>
        </div>
      </div>
      <div class="cat-world-agent-diary-grid">
        <button
          v-for="cat in catAgentDiaries"
          :key="`diary-${cat.id}`"
          type="button"
          :class="['cat-world-agent-card', { active: state.selectedCat === cat.id }]"
          :disabled="busyItemId === cat.id"
          @click="selectCat(cat.id)"
        >
          <header>
            <span>{{ cat.label }}</span>
            <strong>{{ cat.dailyMoodLabel }}</strong>
          </header>
          <p>{{ cat.behaviorLabel }} · {{ cat.routineLabel }}</p>
          <p class="cat-world-agent-goal">{{ cat.goalLabel }} · {{ cat.goalMessage }}</p>
          <p v-if="cat.careTip" class="cat-world-agent-care">{{ cat.careTip }}</p>
          <p v-if="cat.voiceLine" class="cat-world-agent-voice">{{ cat.voiceLine }}</p>
          <div class="cat-world-agent-meter-row" aria-label="猫咪 agent 参数">
            <span class="cat-world-agent-meter energy">
              体力
              <i><b :style="{ width: `${cat.energyScore}%` }"></b></i>
            </span>
            <span class="cat-world-agent-meter mood">
              心情
              <i><b :style="{ width: `${cat.moodScore}%` }"></b></i>
            </span>
            <span class="cat-world-agent-meter trust">
              信任
              <i><b :style="{ width: `${cat.bondScore}%` }"></b></i>
            </span>
            <span class="cat-world-agent-meter focus">
              专注
              <i><b :style="{ width: `${cat.attention}%` }"></b></i>
            </span>
            <span class="cat-world-agent-meter curious">
              好奇
              <i><b :style="{ width: `${cat.curiosity}%` }"></b></i>
            </span>
            <span class="cat-world-agent-meter stamina">
              耐力
              <i><b :style="{ width: `${cat.stamina}%` }"></b></i>
            </span>
            <span class="cat-world-agent-meter activity">
              活跃
              <i><b :style="{ width: `${cat.activityBias}%` }"></b></i>
            </span>
            <span class="cat-world-agent-meter social">
              黏人
              <i><b :style="{ width: `${cat.socialNeed}%` }"></b></i>
            </span>
            <span class="cat-world-agent-meter mischief">
              捣蛋
              <i><b :style="{ width: `${cat.mischief}%` }"></b></i>
            </span>
          </div>
          <dl class="cat-world-agent-facts">
            <div>
              <dt>作息</dt>
              <dd>{{ cat.sleepLabel }}</dd>
            </div>
            <div>
              <dt>消耗</dt>
              <dd>{{ cat.decayLabel }}</dd>
            </div>
            <div>
              <dt>亲密</dt>
              <dd>{{ cat.bondLabel }} · {{ cat.bondDetailLabel }}</dd>
            </div>
            <div>
              <dt>今日参数</dt>
              <dd>{{ cat.personaLabel }} · {{ cat.dailyProfileLabel || "状态稳定" }}</dd>
            </div>
            <div>
              <dt>今日愿望</dt>
              <dd>{{ cat.dailyWish || "想安静陪你学习" }}</dd>
            </div>
            <div>
              <dt>相处方式</dt>
              <dd>{{ cat.socialStyleLabel }}</dd>
            </div>
            <div>
              <dt>玩耍倾向</dt>
              <dd>{{ cat.playStyleLabel }}</dd>
            </div>
            <div>
              <dt>照顾偏好</dt>
              <dd>{{ cat.carePreferenceLabel || "保持房间稳定整洁" }}</dd>
            </div>
            <div>
              <dt>减耗</dt>
              <dd>{{ cat.comfortLabel }}</dd>
            </div>
            <div>
              <dt>偏好</dt>
              <dd>{{ cat.favoriteItemLabel }}</dd>
            </div>
            <div>
              <dt>家具加成</dt>
              <dd>{{ cat.activeFavoriteLabel }}</dd>
            </div>
            <div>
              <dt>互动</dt>
              <dd>{{ cat.countsLabel }}</dd>
            </div>
            <div>
              <dt>破坏风险</dt>
              <dd>{{ cat.damageRiskLabel }}</dd>
            </div>
          </dl>
          <div v-if="cat.hourlyHistory.length" class="cat-world-agent-hourly">
            <b>小时记录</b>
            <span v-for="row in cat.hourlyHistory" :key="`${cat.id}-${row.time}-${row.label}`">
              {{ row.time }} · {{ row.label }} · 体力 {{ signedHourlyValue(row.energyDelta) }} / 心情 {{ signedHourlyValue(row.moodDelta) }}
              <small>现在 {{ row.energyScore }}/{{ row.moodScore }}{{ row.hours > 1 ? ` · ${row.hours} 小时汇总` : "" }}</small>
            </span>
          </div>
          <small>{{ cat.damageLabel }}</small>
          <em v-if="cat.latestEvent">{{ cat.latestEvent.time }} · {{ cat.latestEvent.message }}</em>
        </button>
      </div>
    </section>

    <section class="cat-world-cats panel">
      <div class="cat-world-market-head">
        <div>
          <p class="section-kicker">Cats</p>
          <h2>我的猫咪</h2>
        </div>
      </div>
      <div class="cat-world-cat-list">
        <button
          v-for="cat in catAgentCards"
          :key="cat.id"
          type="button"
          :class="['cat-world-cat-chip', { active: state.selectedCat === cat.id, locked: !cat.owned }]"
          :disabled="!cat.owned || busyItemId === cat.id"
          @click="selectCat(cat.id)"
        >
          <span>{{ cat.owned ? cat.rarity || cat.englishName : "未解锁" }}</span>
          <strong>{{ cat.label }}</strong>
          <small>{{ cat.owned ? cat.personality || cat.englishName : cat.description }}</small>
          <div v-if="cat.owned" class="cat-world-cat-agent-status">
            <p>
              <b>{{ cat.dailyMoodLabel }}</b>
              <em>{{ cat.behaviorLabel }}</em>
            </p>
            <div class="cat-world-cat-agent-bars" aria-label="猫咪状态">
              <i class="energy" :style="{ width: `${cat.energyScore}%` }"></i>
              <i class="mood" :style="{ width: `${cat.moodScore}%` }"></i>
            </div>
            <p v-if="cat.latestEvent" class="cat-world-cat-agent-event">
              {{ cat.latestEvent.time }} · {{ cat.latestEvent.message }}
            </p>
          </div>
        </button>
      </div>
    </section>

    <div v-if="energyModalOpen" class="cat-world-modal-backdrop" @click.self="energyModalOpen = false">
      <section class="cat-world-energy-modal panel" role="dialog" aria-modal="true" aria-labelledby="cat-world-energy-title">
        <header>
          <div>
            <p class="section-kicker">Energy</p>
            <h2 id="cat-world-energy-title">学习产能</h2>
            <p>能量只通过学习获得，猫粮、玩具、装修和配色都会消耗这里的能量。</p>
          </div>
          <button class="secondary-button compact-button" type="button" @click="energyModalOpen = false">关闭</button>
        </header>
        <div class="cat-world-modal-summary">
          <span>可用 {{ energy.available || 0 }}</span>
          <span>累计 {{ energy.earned || 0 }}</span>
          <span>已用 {{ energy.spent || 0 }}</span>
        </div>
        <div class="cat-world-energy-list">
          <div v-for="source in energy.sources || []" :key="source.key" class="cat-world-energy-row">
            <span>{{ source.label }}</span>
            <strong>{{ source.energy }}</strong>
            <small>{{ source.value }}{{ source.unit }} x {{ source.energyPerUnit }}</small>
          </div>
        </div>
      </section>
    </div>
  </section>
</template>
