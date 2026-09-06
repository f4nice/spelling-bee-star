<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { Archive as ArchiveIcon, Award as AwardIcon, Cat as CatIcon, Check as CheckIcon, ChevronDown, ChevronLeft, ChevronRight, Flame as FlameIcon, Hammer as HammerIcon, House as HouseIcon, LockKeyhole as LockIcon, MapPin as MapPinIcon, MessageCircle as MessageCircleIcon, MoveRight as MoveRightIcon, PawPrint as PawPrintIcon, ShoppingBag as ShoppingBagIcon, Shovel as ShovelIcon, X as XIcon } from "lucide-vue-next";
import {
  foodEnergyGainForCat,
  foodFavoriteBonusPercent,
  foodMoodGainForCat,
  foodTypeLabel,
} from "../catWorldFoodRules.js";
import {
  bathStatusLabel,
  litterBathAccelerationLabel,
  litterMoodPenalty,
  neglectCountdownLabel,
} from "../catWorldHygieneRules.js";
import {
  collectionRegionMeta,
  resolveCollectionCat,
  resolveCollectionSection,
} from "../catWorldCollectionAtlas.js";
import { CAT_BUBBLE_TOTAL_MS } from "../catWorldBubbleState.js";
import { catPortraitModel } from "../catWorldPortrait.js";
import { catRarityBadge } from "../catWorldRarity.js";
import {
  buildCatWorldLearningRoute,
  buildCatWorldRoomLearningSignal,
  buildCatWorldWeekTrail,
  catWorldLearningCompanionGrowthLabel,
  catWorldLearningCompanionToken,
  catWorldWeekMemory,
} from "../catWorldLearningRoute.js";
import {
  formatCatWorldPlayTime,
  formatCatWorldPlayTimeProgress,
  formatCatWorldPlayTimeTiers,
  isCatWorldPlayTimeLocked,
  projectCatWorldPlayTime,
} from "../catWorldPlayTime.js";
import { routeApiPaths } from "../routeApiPaths.js";
import { fetchJson } from "../utils.js";
import CatWorldProductIcon from "../components/CatWorldProductIcon.vue";

const props = defineProps({
  data: {
    type: Object,
    required: true,
  },
});

const payload = ref(props.data || {});
const activeCategory = ref("food");
const activeWorldView = ref("room");
const bagExpanded = ref(false);
const busyItemId = ref("");
const notice = ref("");
const catReaction = ref("");
const catReactionAnchored = ref(false);
const catPetSequence = ref(0);
const focusedCatId = ref("");
const openCatDiaryId = ref("");
const gameMountRef = ref(null);
const catWorldGame = ref(null);
const layoutDraft = ref({});
const selectedDecorId = ref("");
const layoutDirty = ref(false);
const savingRoomLayout = ref(false);
const roomEditMode = ref(false);
const repairMode = ref(false);
const scoopMode = ref(false);
const renameMode = ref(false);
const toolCursorVisible = ref(false);
const toolCursorX = ref(0);
const toolCursorY = ref(0);
const renameCursorVisible = ref(false);
const renameCursorX = ref(0);
const renameCursorY = ref(0);
const renameModalOpen = ref(false);
const renameTargetCatId = ref("");
const renameDraft = ref("");
const renameInputRef = ref(null);
const renameBusy = ref(false);
const activeToolCategory = ref("decor");
const clockNow = ref(Date.now());
const playTimeSyncedAt = ref(Date.now());
const playTimeSessionActive = ref(false);
const energyModalOpen = ref(false);
const scenePurchaseTarget = ref(null);
const openedBlindBox = ref(null);
const activeHandbook = ref("");
const selectedCollectionRegionKey = ref("");
const selectedCollectionCatId = ref("");
const petBusyCatId = ref("");
const roomCanPan = ref(false);
const roomPanActive = ref(false);
const catOsExpanded = ref(false);
const learningWeekExpanded = ref(false);
const selectedLearningWeekDate = ref("");
const busySceneId = ref("");
const busyLocationItemId = ref("");
const ambientEventCooldowns = new Map();
const foodNibbleCooldowns = new Map();
const catPositionSyncs = new Map();

const catReactionTexts = [
  "收到摸摸指令，开心值上升",
  "启动陪读模式，正在靠近你",
  "尾巴雷达晃了晃，发现新单词",
  "想法缓存刷新，准备继续陪你学",
];
let catReactionTimer = 0;
let learningCompanionReactionTimer = 0;
let activeFoodClockTimer = 0;
let playTimeHeartbeatTimer = 0;
let playTimeSyncBusy = false;
let gameMountActive = false;

watch(
  () => props.data,
  (nextData) => {
    payload.value = nextData || {};
    playTimeSyncedAt.value = Date.now();
  },
);

onBeforeUnmount(() => {
  gameMountActive = false;
  endPlayTimeSession();
  window.clearTimeout(catReactionTimer);
  window.clearTimeout(learningCompanionReactionTimer);
  window.clearInterval(activeFoodClockTimer);
  window.clearInterval(playTimeHeartbeatTimer);
  window.removeEventListener("keydown", handleGlobalKeydown);
  window.removeEventListener("pagehide", endPlayTimeSession);
  document.removeEventListener("visibilitychange", handlePlayTimeVisibilityChange);
  catPositionSyncs.forEach((entry) => window.clearTimeout(entry.timer));
  catPositionSyncs.clear();
  catWorldGame.value?.destroy();
  catWorldGame.value = null;
});

onMounted(async () => {
  window.addEventListener("keydown", handleGlobalKeydown);
  window.addEventListener("pagehide", endPlayTimeSession);
  document.addEventListener("visibilitychange", handlePlayTimeVisibilityChange);
  playTimeSessionActive.value = document.visibilityState === "visible"
    && Number(payload.value.playTime?.remainingSeconds || 0) > 0;
  activeFoodClockTimer = window.setInterval(() => {
    clockNow.value = Date.now();
  }, 1000);
  playTimeHeartbeatTimer = window.setInterval(() => {
    if (document.visibilityState === "visible") syncPlayTimeSession(true);
  }, 10000);
  syncPlayTimeSession(true);
  if (!gameMountRef.value) return;
  gameMountActive = true;
  const { CatWorldGame } = await import("../catWorldGame.js");
  if (!gameMountActive || !gameMountRef.value) return;
  catWorldGame.value = new CatWorldGame(gameMountRef.value, {
    onCatPet: (cat, message) => {
      if (!roomEditMode.value && !repairMode.value && !scoopMode.value) {
        petCat(cat, { message, anchor: false });
      }
    },
    onCatCarryStart: (_cat, interaction) => {
      if (interaction?.message) notice.value = interaction.message;
    },
    onCatDrop: (_cat, interaction) => {
      if (interaction?.message) notice.value = interaction.message;
    },
    onCatPositionChange: syncCatPosition,
    onDecorClick: handleDecorClick,
    onDecorSelect: (decorId) => {
      selectedDecorId.value = decorId || "";
    },
    onLayoutChange: handleGameLayoutChange,
    onToyClick: handleRoomToyClick,
    onToyDrop: handleRoomToyDrop,
    onCatWandJoin: (interaction) => {
      if (interaction?.message) notice.value = interaction.message;
    },
    onLitterClick: cleanLitter,
    onBathtubBath: (bath) => useConsumable(shopById.value["cat-bath-kit"], { targetCatId: bath?.catId }),
    onItemInteractionEnd: (interaction) => {
      if (interaction?.message) notice.value = interaction.message;
    },
    onCatThought: (cat, message) => {
      if (!roomEditMode.value) showCatReaction(cat, message, { anchor: false });
    },
    onLearningBoardClick: openRoomLearningProgress,
    onCatAmbient: recordCatAmbientEvent,
    onFoodVisit: recordCatFoodNibble,
    onCameraPanState: (active) => {
      roomPanActive.value = active;
    },
  });
  updateCatWorldGame();
  announceLearningCompanionOnEntry();
});

const categories = [
  { key: "food", label: "猫粮" },
  { key: "consumable", label: "消耗品" },
  { key: "toy", label: "玩具" },
  { key: "decor", label: "装修" },
  { key: "color", label: "配色" },
  { key: "cat", label: "名猫" },
  { key: "blind-box", label: "限定盲盒" },
  { key: "handbook", label: "收藏手册" },
];
const REPAIR_HAMMER_ITEM_ID = "repair-hammer";
const LITTER_SCOOP_ITEM_ID = "litter-scoop";
const CAT_RENAME_CARD_ITEM_ID = "cat-rename-card";
const toolIconItems = Object.freeze({
  repair: { id: REPAIR_HAMMER_ITEM_ID, category: "consumable", label: "一次性维修锤" },
  scoop: { id: LITTER_SCOOP_ITEM_ID, category: "consumable", label: "一次性铲屎铲" },
  rename: { id: CAT_RENAME_CARD_ITEM_ID, category: "consumable", label: "猫咪改名卡" },
});

const toolCategories = [
  { key: "decor", label: "装饰" },
  { key: "food", label: "食物" },
  { key: "toy", label: "玩具" },
  { key: "consumable", label: "消耗品" },
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

const catIconColors = {
  mimi: "#ffc46b",
  "british-shorthair": "#b9c2c8",
  ragdoll: "#f4e5cf",
  "maine-coon": "#ae7c4f",
  siamese: "#f1ddbd",
  "china-lihua": "#8b765f",
  "linqing-lion": "#f2eee5",
  "jianzhou-cat": "#d6a06b",
  "japanese-bobtail": "#fff3dc",
  "turkish-van": "#fff4dc",
  "turkish-angora": "#f8fbff",
};

const energy = computed(() => payload.value.energy || {});
const todayEnergy = computed(() => Math.max(Number(energy.value.today || 0), 0));
const todayEnergySources = computed(() => Array.isArray(energy.value.todaySources) ? energy.value.todaySources : []);
const playTime = computed(() => payload.value.playTime || {});
const playTimeRemainingSeconds = computed(() =>
  projectCatWorldPlayTime(
    playTime.value,
    playTimeSyncedAt.value,
    clockNow.value,
    playTimeSessionActive.value && document.visibilityState === "visible",
  ),
);
const playTimeClock = computed(() => formatCatWorldPlayTime(playTimeRemainingSeconds.value));
const playTimeLocked = computed(() => isCatWorldPlayTimeLocked(playTimeRemainingSeconds.value));
const playTimeTierLabel = computed(() => formatCatWorldPlayTimeTiers(playTime.value));
const playTimeProgressLabel = computed(() => formatCatWorldPlayTimeProgress(playTime.value));
const playTimeCardState = computed(() => {
  if (Number(playTime.value.earnedSeconds || 0) <= 0) return "waiting";
  if (playTimeRemainingSeconds.value <= 0) return "finished";
  return "running";
});

watch(playTimeLocked, (locked) => {
  if (!locked) return;
  roomEditMode.value = false;
  repairMode.value = false;
  scoopMode.value = false;
  renameMode.value = false;
  toolCursorVisible.value = false;
  renameCursorVisible.value = false;
  renameModalOpen.value = false;
  selectedDecorId.value = "";
  layoutDirty.value = false;
  activeHandbook.value = "";
  openCatDiaryId.value = "";
  scenePurchaseTarget.value = null;
  openedBlindBox.value = null;
  catWorldGame.value?.cancelCatCarry?.();
});
const state = computed(() => payload.value.state || {});
const scenes = computed(() => payload.value.scenes || []);
const currentScene = computed(
  () => state.value.currentScene || scenes.value.find((scene) => scene.id === state.value.currentSceneId) || {},
);
const inventory = computed(() => state.value.inventory || {});
const usableInventory = computed(() => state.value.usableInventory || inventory.value);
const sceneInventory = computed(() => state.value.sceneInventory || inventory.value);
const damagedItems = computed(() => state.value.damagedItems || {});
const roomStyles = computed(() => state.value.roomStyles || {});
const roomLayout = computed(() => state.value.roomLayout || {});
const styleOptions = computed(() => state.value.styleOptions || {});
const dailyLogs = computed(() => state.value.dailyLogs || {});
const catBonds = computed(() => state.value.catBonds || {});
const lostCats = computed(() => state.value.lostCats || {});
const lostCatRows = computed(() => Object.values(lostCats.value));
const hygiene = computed(() => state.value.hygiene || {});
const hygieneMoodPenalty = computed(() => Number(hygiene.value.moodDecayBonus ?? litterMoodPenalty(hygiene.value.count)));
const litterBathAccelerationText = computed(() => litterBathAccelerationLabel(hygiene.value));
const ownedCats = computed(() => state.value.ownedCats || []);
const cats = computed(() => payload.value.cats || []);
const catProfiles = computed(() => payload.value.catProfiles || []);
const shop = computed(() => payload.value.shop || []);
const blindBoxCatalog = computed(() => payload.value.blindBoxCatalog || { series: [] });
const catCollectionCatalog = computed(() => payload.value.catCollectionCatalog || {
  ownedCount: 0,
  totalCount: 0,
  sections: [],
});
const currentBlindSeries = computed(
  () => blindBoxCatalog.value.series?.find((series) => series.key === blindBoxCatalog.value.currentSeriesKey) || {},
);
const activeCollectionSection = computed(() =>
  resolveCollectionSection(
    catCollectionCatalog.value.sections,
    selectedCollectionRegionKey.value,
    currentBlindSeries.value.region,
  ),
);
const activeCollectionCat = computed(() =>
  resolveCollectionCat(activeCollectionSection.value, selectedCollectionCatId.value),
);
const currentBlindRarityLabel = computed(() => {
  const rarities = [...new Set((currentBlindSeries.value.cats || []).map((cat) => cat.rarity).filter(Boolean))];
  return rarities.length ? rarities.join(" / ") : "限定";
});
const gameSettings = computed(() => payload.value.gameSettings || {});
const shopById = computed(() => Object.fromEntries(shop.value.map((item) => [item.id, item])));
const selectedCat = computed(() =>
  catProfiles.value.find((cat) => cat.id === state.value.selectedCatProfile && cat.currentSceneId === currentScene.value.id)
  || catProfiles.value.find((cat) => cat.currentSceneId === currentScene.value.id)
  || catProfiles.value.find((cat) => cat.id === state.value.selectedCatProfile)
  || catProfiles.value.find((cat) => cat.breedId === state.value.selectedCat)
  || cats.value.find((cat) => cat.id === state.value.selectedCat && ownedCats.value.includes(cat.id))
  || {},
);
const roomCats = computed(() => {
  if (catProfiles.value.length) {
    const roomIds = new Set(state.value.roomCatIds || []);
    return catProfiles.value.filter((cat) =>
      roomIds.size ? roomIds.has(cat.id) : cat.currentSceneId === currentScene.value.id,
    );
  }
  if (currentScene.value.id && currentScene.value.id !== "main-room") return [];
  const owned = new Set(ownedCats.value);
  const visibleCats = cats.value.filter((cat) => owned.has(cat.id));
  return visibleCats;
});
const focusedCat = computed(
  () =>
    roomCats.value.find((cat) => cat.id === focusedCatId.value) ||
    roomCats.value.find((cat) => cat.id === state.value.selectedCatProfile) ||
    roomCats.value.find((cat) => (cat.breedId || cat.id) === state.value.selectedCat) ||
    roomCats.value[0] ||
    {},
);
const learningCompanion = computed(() => payload.value.learningCompanion || {});
const learningGuideCat = computed(() => catForId(learningCompanion.value.catId) || focusedCat.value);
const learningRoute = computed(() => {
  const route = buildCatWorldLearningRoute(energy.value.habit || {}, learningGuideCat.value);
  return {
    ...route,
    coachLine: learningCompanion.value.message || route.coachLine,
  };
});
const learningRoomSignal = computed(() =>
  buildCatWorldRoomLearningSignal(
    energy.value.habit || {},
    learningGuideCat.value,
    learningCompanion.value,
  ),
);
const learningGuidePortrait = computed(() => catPortraitModel(learningGuideCat.value));
const learningCompanionGrowthLabel = computed(() =>
  catWorldLearningCompanionGrowthLabel(learningCompanion.value),
);
const learningWeekTrail = computed(() => buildCatWorldWeekTrail(energy.value.habit || {}));
const selectedLearningWeekDay = computed(() =>
  learningWeekTrail.value.days.find((day) => day.date === selectedLearningWeekDate.value)
  || learningWeekTrail.value.days.find((day) => day.today)
  || learningWeekTrail.value.days.at(-1)
  || {},
);
const learningWeekMemory = computed(() =>
  catWorldWeekMemory(selectedLearningWeekDay.value, learningGuideCat.value),
);
const mood = computed(() => state.value.mood || {});
const focusedDailyLog = computed(
  () => individualizeCatLog(
    focusedCat.value,
    dailyLogs.value[focusedCat.value.id]
      || dailyLogs.value[focusedCat.value.breedId]
      || dailyLogs.value[state.value.selectedCat]
      || mood.value.dailyLog
      || {},
  ),
);
const focusedAgentState = computed(() => focusedDailyLog.value.agentState || {});
const focusedBond = computed(() =>
  catBonds.value[focusedCat.value.id]
  || catBonds.value[focusedCat.value.breedId]
  || {},
);
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
const rawActiveCare = computed(() => state.value.activeCare || {});
const activeCareRemainingSeconds = computed(() => {
  if (!rawActiveCare.value?.active) return 0;
  const expiresAt = parseUtcTimestamp(rawActiveCare.value.expiresAt);
  if (Number.isFinite(expiresAt)) return Math.max(Math.ceil((expiresAt - clockNow.value) / 1000), 0);
  return Math.max(Number(rawActiveCare.value.remainingSeconds || 0), 0);
});
const activeCare = computed(() => ({
  ...rawActiveCare.value,
  active: Boolean(rawActiveCare.value?.active && activeCareRemainingSeconds.value > 0),
  remainingSeconds: activeCareRemainingSeconds.value,
}));
const catEnergyScore = computed(() => Number(mood.value.catEnergy ?? 0));
const moodScore = computed(() => Number(mood.value.score ?? 0));
const selectedItems = computed(() => shop.value.filter((item) => item.category === activeCategory.value));
const ownsCatHandbook = computed(() => itemCount("cat-collection-handbook") > 0);
const ownsFoodHandbook = computed(() => itemCount("cat-food-handbook") > 0);
const foodHandbookItems = computed(() => shop.value.filter((item) => item.category === "food"));
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
    return (catProfiles.value.length ? catProfiles.value : roomCats.value)
      .map((cat) => ({
        ...cat,
        category: "cat",
        count: 1,
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
    }));
});
const ownedToolTotal = computed(() =>
  toolCategories.reduce((total, category) => total + ownedToolCount(category.key), 0),
);
const focusedCatThought = computed(() => {
  if (!focusedCat.value?.id) return "活动室里暂时没有猫咪，可以去商店重新领养一只。";
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
  if (!focusedCat.value?.id) return "猫咪离家后会从已拥有列表移除；重新领养会恢复基础体力和心情。";
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
  if (Array.isArray(tags)) return [focusedCat.value.personality, ...tags].filter(Boolean).slice(0, 4);
  return [focusedCat.value.personality, focusedAgentState.value.personaLabel, focusedAgentState.value.playStyleLabel, focusedAgentState.value.socialStyleLabel]
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

function catBreedId(cat) {
  return cat?.breedId || cat?.id || "";
}

function catProfileCount(breedId) {
  return catProfiles.value.filter((cat) => cat.breedId === breedId).length;
}

function catForId(catId) {
  return catProfiles.value.find((cat) => cat.id === catId)
    || catProfiles.value.find(
      (cat) => cat.id === state.value.selectedCatProfile && cat.breedId === catId,
    )
    || catProfiles.value.find((cat) => cat.breedId === catId)
    || cats.value.find((cat) => cat.id === catId)
    || null;
}

function individualizeCatLog(cat, sourceLog = {}) {
  const traits = cat?.traits || {};
  const sourceAgent = sourceLog?.agentState || {};
  const sourceTags = Array.isArray(sourceAgent.profileTags) ? sourceAgent.profileTags : [];
  return {
    ...(sourceLog || {}),
    agentState: {
      ...sourceAgent,
      temperament: traits.temperament || sourceAgent.temperament || "balanced",
      routine: traits.routine || sourceAgent.routine || "观察房间里的学习节奏",
      personaLabel: cat?.personality || sourceAgent.personaLabel || "学习陪伴型",
      profileTags: [cat?.personality, ...sourceTags].filter(Boolean).slice(0, 4),
    },
  };
}

const catAgentCards = computed(() =>
  (catProfiles.value.length ? catProfiles.value : roomCats.value).map((cat) => {
    const breedId = catBreedId(cat);
    const owned = ownsCat(breedId);
    const log = individualizeCatLog(cat, dailyLogs.value[cat.id] || dailyLogs.value[breedId] || {});
    const agent = log.agentState || {};
    const behavior = agent.currentBehavior || {};
    const bond = catBonds.value[cat.id] || catBonds.value[breedId] || {};
    const careNeed = agent.careNeed || {};
    const lostInfo = lostCats.value[breedId] || null;
    const agentEvents = Array.isArray(agent.events) ? agent.events.filter((event) => event?.message) : [];
    const latestEvent = agentEvents.length ? agentEvents[agentEvents.length - 1] : null;
    return {
      ...cat,
      portrait: catPortraitModel(cat),
      rarityBadge: catRarityBadge(cat.rarity),
      owned,
      escaped: Boolean(lostInfo),
      lostInfo,
      log,
      agent,
      behaviorLabel: behavior.label || (owned ? "自由活动" : lostInfo ? "已经离家" : "未解锁"),
      moodScore: clampCatScore(log.moodScore ?? agent.adjustedMoodScore ?? 0),
      energyScore: clampCatScore(log.energyScore ?? agent.adjustedEnergyScore ?? 0),
      bondScore: clampCatScore(bond.score ?? 18),
      bondLabel: bond.levelLabel || "刚开始熟悉",
      bondDetailLabel: bond.detailLabel || "还没有照顾记录",
      needLabel: careNeed.label || "",
      needActionLabel: careNeed.actionLabel || "",
      needMessage: careNeed.message || "",
      needStatus: careNeed.status || "calm",
      needPriority: clampCatScore(careNeed.priority ?? 0),
      dailyMoodLabel: agent.dailyMoodLabel || (owned ? "今天状态稳定" : lostInfo ? "已经离家" : "等待解锁"),
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
      const hygieneInfo = log.hygiene || agent.hygiene || {};
      const neglect = log.neglect || agent.neglect || {};
      return {
        ...cat,
        attention: clampCatScore(agent.attention ?? 0),
        curiosity: clampCatScore(agent.curiosity ?? 0),
        mischief: clampCatScore(agent.mischief ?? 0),
        stamina: clampCatScore(agent.stamina ?? 0),
        activityBias: clampCatScore(agent.activityBias ?? 0),
        socialNeed: clampCatScore(agent.socialNeed ?? 0),
        cleanliness: clampCatScore(agent.cleanliness ?? hygieneInfo.cleanliness ?? 0),
        cleanlinessLabel: agent.cleanlinessLabel || hygieneInfo.cleanlinessLabel || "普通讲究",
        bathIntervalDays: Number(agent.bathIntervalDays || hygieneInfo.bathIntervalDays || 4),
        hygiene: hygieneInfo,
        hygieneStatusLabel: hygieneInfo.statusLabel || "干净清爽",
        bathScheduleLabel: bathStatusLabel(hygieneInfo),
        needsBath: Boolean(hygieneInfo.needsBath),
        bathKitCount: itemCount("cat-bath-kit"),
        neglect,
        neglectStatusLabel: neglect.statusLabel || "照护安全",
        neglectCountdownLabel: neglectCountdownLabel(neglect),
        neglectWarning: Boolean(neglect.isWarning),
        neglectCritical: Boolean(neglect.isCritical),
        dailyProfileLabel: [agent.staminaLabel, agent.activityLabel, agent.socialNeedLabel].filter(Boolean).join(" · "),
        personaLabel: cat.personality || agent.personaLabel || "学习陪伴型",
        dailyWish: agent.dailyWish || dailyGoal.message || "",
        voiceLine: agent.voiceLine || "",
        playStyleLabel: agent.playStyleLabel || "玩耍节奏稳定",
        socialStyleLabel: agent.socialStyleLabel || "陪伴需求稳定",
        carePreferenceLabel: traits.label || agent.carePreferenceLabel || "",
        sleepLabel: traits.nightOwl ? `夜猫子 · ${sleepStart}-${sleepEnd}` : `${sleepStart}-${sleepEnd}`,
        routineLabel: traits.routine || agent.routine || "观察房间里的学习节奏",
        goalLabel: dailyGoal.label || "自由散步",
        goalMessage: dailyGoal.message || "",
        careTip: agent.careTip || "",
        needLabel: cat.needLabel || "状态稳定",
        needActionLabel: cat.needActionLabel || "自由活动",
        needMessage: cat.needMessage || "",
        needStatus: cat.needStatus || "calm",
        needPriority: cat.needPriority || 0,
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
const activeCatDiary = computed(() =>
  catAgentDiaries.value.find((cat) => cat.id === openCatDiaryId.value) || null,
);
const gameDailyLogs = computed(() =>
  Object.fromEntries(
    roomCats.value.map((cat) => [
      cat.id,
      individualizeCatLog(cat, dailyLogs.value[cat.id] || dailyLogs.value[catBreedId(cat)] || {}),
    ]),
  ),
);
const selectedProfileId = computed(() =>
  roomCats.value.find((cat) => cat.id === state.value.selectedCatProfile)?.id
  || roomCats.value.find((cat) => catBreedId(cat) === state.value.selectedCat)?.id
  || roomCats.value[0]?.id
  || "",
);
function gameTargetProfileId(targetBreedId) {
  if (!targetBreedId) return "";
  if (roomCats.value.some((cat) => cat.id === targetBreedId)) return targetBreedId;
  const selected = roomCats.value.find(
    (cat) => cat.id === selectedProfileId.value && catBreedId(cat) === targetBreedId,
  );
  return selected?.id || roomCats.value.find((cat) => catBreedId(cat) === targetBreedId)?.id || targetBreedId;
}
const gameActiveFood = computed(() => ({
  ...activeFood.value,
  targetCatId: gameTargetProfileId(activeFood.value.targetCatId),
}));
const gameActiveCare = computed(() => ({
  ...activeCare.value,
  targetCatId: gameTargetProfileId(activeCare.value.targetCatId),
}));
const gameSnapshot = computed(() => ({
  cats: roomCats.value,
  inventory: sceneInventory.value,
  damagedItems: damagedItems.value,
  layout: roomLayout.value,
  mood: mood.value,
  activeFood: gameActiveFood.value,
  activeCare: gameActiveCare.value,
  hygiene: hygiene.value,
  dailyLogs: gameDailyLogs.value,
  ownedCats: roomCats.value.map((cat) => cat.id),
  ownedFoodCount: ownedFoodCount.value,
  roomStyles: roomStyles.value,
  selectedCatId: selectedProfileId.value,
  gameSettings: gameSettings.value,
  learningSignal: learningRoomSignal.value,
  scene: currentScene.value,
  editMode: roomEditMode.value,
  observationMode: playTimeLocked.value,
  toolMode: repairMode.value ? "repair" : scoopMode.value ? "scoop" : "",
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
    playTimeSyncedAt.value = Date.now();
  }
}

function setPlayTime(nextPlayTime) {
  if (!nextPlayTime || typeof nextPlayTime !== "object") return;
  payload.value = {
    ...payload.value,
    playTime: nextPlayTime,
  };
  playTimeSyncedAt.value = Date.now();
}

async function syncPlayTimeSession(active = true) {
  if (playTimeSyncBusy || (active && document.visibilityState !== "visible")) return;
  playTimeSyncBusy = true;
  try {
    const result = await fetchJson(routeApiPaths.catWorldPlayTime(), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ active }),
      keepalive: !active,
    });
    setPlayTime(result?.playTime);
    playTimeSessionActive.value = Boolean(active && Number(result?.playTime?.remainingSeconds || 0) > 0);
  } catch {
    playTimeSessionActive.value = Boolean(active && playTimeRemainingSeconds.value > 0);
  } finally {
    playTimeSyncBusy = false;
  }
}

function endPlayTimeSession() {
  const remainingSeconds = playTimeRemainingSeconds.value;
  setPlayTime({
    ...playTime.value,
    remainingSeconds,
    sessionActive: false,
  });
  playTimeSessionActive.value = false;
  const body = JSON.stringify({ active: false });
  if (navigator.sendBeacon) {
    navigator.sendBeacon(
      routeApiPaths.catWorldPlayTime(),
      new Blob([body], { type: "application/json" }),
    );
    return;
  }
  fetch(routeApiPaths.catWorldPlayTime(), {
    method: "POST",
    headers: { "content-type": "application/json" },
    body,
    credentials: "same-origin",
    keepalive: true,
  }).catch(() => {});
}

function handlePlayTimeVisibilityChange() {
  if (document.visibilityState === "visible") {
    clockNow.value = Date.now();
    syncPlayTimeSession(true);
    return;
  }
  endPlayTimeSession();
}

function updateCatWorldGame() {
  catWorldGame.value?.update(gameSnapshot.value);
  roomCanPan.value = Boolean(catWorldGame.value?.canPan?.());
}

function openRoomLearningProgress(signal = learningRoomSignal.value) {
  const completed = Math.max(Number(signal?.completedCount || 0), 0);
  notice.value = `今日学习灯牌已亮 ${completed}/3 格。完成单词热身和一次英语说写，就能点亮闭环。`;
  energyModalOpen.value = true;
}

function syncCatPosition(cat, position) {
  const profileId = cat?.profileId || cat?.id;
  const sceneId = currentScene.value.id;
  if (!profileId || !sceneId || cat?.currentSceneId !== sceneId || !position) return;
  const previous = catPositionSyncs.get(profileId);
  if (previous?.timer) window.clearTimeout(previous.timer);
  const timer = window.setTimeout(() => {
    const pending = catPositionSyncs.get(profileId);
    if (!pending || pending.timer !== timer || pending.sceneId !== currentScene.value.id) return;
    catPositionSyncs.delete(profileId);
    fetchJson(routeApiPaths.catWorldCatPosition(), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ profileId, sceneId: pending.sceneId, position: pending.position }),
    }).catch(() => {});
  }, 900);
  catPositionSyncs.set(profileId, { timer, sceneId, position });
}

function panRoomBy(delta) {
  if (roomEditMode.value) return;
  catWorldGame.value?.panBy?.(delta);
}

function panRoomPage(direction) {
  if (roomEditMode.value) return;
  catWorldGame.value?.panPage?.(direction);
}

function handleRoomWheel(event) {
  if (roomEditMode.value || !catWorldGame.value?.canPan?.()) return;
  const delta = Math.abs(event.deltaX) >= Math.abs(event.deltaY) ? event.deltaX : event.shiftKey ? event.deltaY : 0;
  if (!delta) return;
  catWorldGame.value.panBy(delta);
  event.preventDefault();
  event.stopPropagation();
}

function handleGameLayoutChange(nextLayout, itemId) {
  selectedDecorId.value = itemId || selectedDecorId.value;
  layoutDraft.value = normalizeLayoutDraft(nextLayout);
  layoutDirty.value = true;
}

async function handleRoomToyDrop(itemId, nextLayout, interaction = {}) {
  if (!itemId || savingRoomLayout.value) return;
  selectedDecorId.value = itemId;
  layoutDraft.value = normalizeLayoutDraft(nextLayout);
  savingRoomLayout.value = true;
  notice.value = interaction.message || "玩具已放下，正在保存位置。";
  try {
    const nextPayload = await fetchJson(routeApiPaths.catWorldRoomLayout(), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ sceneId: currentScene.value.id, layout: layoutDraft.value }),
    });
    replacePayload(nextPayload);
    layoutDirty.value = false;
    notice.value = interaction.message || "玩具位置已保存。";
  } catch (error) {
    layoutDirty.value = true;
    notice.value = error.message || "玩具已经放下，但位置保存失败，请点击保存重试。";
  } finally {
    savingRoomLayout.value = false;
  }
}

function itemCount(itemId) {
  return Number(inventory.value[itemId] || 0);
}

function catIconColor(catId) {
  const profile = catProfiles.value.find((cat) => cat.id === catId);
  return catIconColors[profile?.breedId || catId] || "#ffbfd7";
}

function selectCollectionRegion(section) {
  if (!section?.key) return;
  selectedCollectionRegionKey.value = section.key;
  selectedCollectionCatId.value = section.cats?.[0]?.id || "";
}

function selectCollectionCat(cat) {
  selectedCollectionCatId.value = cat?.id || "";
}

function toggleCatDiary(cat) {
  if (!cat?.id) return;
  openCatDiaryId.value = cat.id;
  focusedCatId.value = cat.id;
}

function closeCatDiary() {
  openCatDiaryId.value = "";
}

function handleGlobalKeydown(event) {
  if (event.key !== "Escape") return;
  if (renameModalOpen.value) {
    closeRenameModal();
    return;
  }
  if (renameMode.value) {
    setRenameMode(false);
    notice.value = "已收起改名卡。";
    return;
  }
  if (repairMode.value) {
    setRepairMode(false);
    notice.value = "已收起维修锤。";
    return;
  }
  if (scoopMode.value) {
    setScoopMode(false);
    notice.value = "已收起铲子。";
    return;
  }
  const carryResult = catWorldGame.value?.cancelCatCarry?.();
  if (carryResult?.handled) {
    notice.value = carryResult.message || "猫咪已放回原处。";
    return;
  }
  if (activeCatDiary.value) {
    closeCatDiary();
    return;
  }
  energyModalOpen.value = false;
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

function handleDecorClick(decorId, interaction = null) {
  const item = shopById.value[decorId];
  if (item && handleRepairTargetClick(item)) return;
  if (repairMode.value) {
    notice.value = `${item?.label || "这个道具"}不需要维修，维修锤没有消耗。`;
    return;
  }
  if (scoopMode.value) {
    notice.value = `${item?.label || "这个道具"}不是猫屎，铲子没有消耗。`;
    return;
  }
  if (!roomEditMode.value && interaction?.handled) {
    selectedDecorId.value = decorId;
    notice.value = interaction.message || `${item?.label || "道具"} 已互动。`;
    return;
  }
  if (!roomEditMode.value) {
    selectedDecorId.value = decorId;
    notice.value = `点击“编辑物品”后，可以拖动 ${item?.label || "这个道具"} 或切换已解锁配色。`;
    return;
  }
  selectedDecorId.value = decorId;
  cycleDecorStyle(decorId);
}

function handleRoomToyClick(itemId, interaction = null) {
  const item = shopById.value[itemId];
  if (item && ["food", "toy"].includes(item.category)) {
    if (handleRepairTargetClick(item)) return;
    if (repairMode.value) {
      notice.value = `${item.label}不需要维修，维修锤没有消耗。`;
      return;
    }
    if (scoopMode.value) {
      notice.value = `${item.label}不是猫屎，铲子没有消耗。`;
      return;
    }
    if (roomEditMode.value) {
      selectedDecorId.value = item.id;
      notice.value = item.category === "toy"
        ? `已选中 ${item.label}，可以拖动它，保存后猫咪会回到活动室。`
        : `${item.label} 会被猫咪慢慢吃完，暂时不能拖动。`;
      return;
    }
    if (!roomEditMode.value && interaction?.handled) {
      selectedDecorId.value = item.id;
      notice.value = interaction.message || `${item.label} 已互动。`;
      return;
    }
    if (item.category === "food" && activeFood.value.active && activeFood.value.itemId === item.id) {
      notice.value = `${item.label} 正在房间里，优先给${activeFood.value.targetCatLabel || "体力最低的小猫"}慢慢吃，剩余可补体力 ${activeFood.value.remainingEnergy || 0}，还剩 ${formatSeconds(activeFood.value.remainingSeconds)}。`;
      const targetCat = catForId(activeFood.value.targetCatId) || focusedCat.value;
      showCatReaction(targetCat, `${item.label}还在房间里，我会慢慢吃完。`);
      return;
    }
    play(item);
  }
}

function recordCatAmbientEvent(cat, event = {}) {
  if (roomEditMode.value) return;
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
    if (roomEditMode.value) return;
    if (nextPayload?.energy && nextPayload?.state) {
      replacePayload(nextPayload);
    }
    if (event.kind === "rest-spot" && nextPayload?.recorded && nextPayload?.event?.message) {
      showCatReaction(cat, nextPayload.event.message);
    }
  }).catch(() => {
    ambientEventCooldowns.delete(key);
  });
}

function recordCatFoodNibble(cat, event = {}) {
  if (roomEditMode.value) return;
  if (!cat?.id || !activeFood.value.active) return;
  if (
    activeFood.value.targetCatId
    && activeFood.value.targetCatId !== cat.id
    && activeFood.value.targetCatId !== catBreedId(cat)
  ) return;
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
    if (roomEditMode.value) return;
    replacePayload(nextPayload);
    const effect = nextPayload?.effect || {};
    if (effect.recorded && effect.message) {
      showCatReaction(cat, effect.message);
    }
  }).catch(() => {
    foodNibbleCooldowns.delete(key);
  });
}

function ownedToolCount(categoryKey) {
  if (categoryKey === "cat") return catProfiles.value.length || roomCats.value.length;
  return shop.value.filter((item) => item.category === categoryKey && itemCount(item.id) > 0).length;
}

function ownedToolSubtext(item) {
  const damaged = damageInfo(item);
  if (damaged) return `损坏 · 维修需 1 把锤子 + ${damaged.repairCost || 0} 能量`;
  if (item.category === "cat") {
    const profile = [item.genderLabel, item.patternLabel, item.featureLabel].filter(Boolean).join(" · ")
      || item.personality
      || "正在陪读";
    return `${profile} · 位于${item.currentSceneLabel || "一楼活动室"}`;
  }
  const suffix = item.favoriteLabel ? ` · ${item.favoriteLabel}` : "";
  if (item.category === "food") return `拥有 ${item.count} · ${foodTypeLabel(item)}${suffix}`;
  if (item.category === "consumable") {
    if (item.useType === "litter-clean") {
      return scoopMode.value ? `已装备 · 拥有 ${item.count}` : `拥有 ${item.count} · 点击装备`;
    }
    if (item.useType === "litter-prevent") return `拥有 ${item.count} · 点击放进活动室`;
    if (item.useType === "cat-bath") return `拥有 ${item.count} · 给当前档案猫咪洗澡`;
    if (item.useType === "cat-rename") {
      return renameMode.value ? `已选择 · 拥有 ${item.count}` : `拥有 ${item.count} · 点击改名`;
    }
    if (item.useType === "repair-tool") {
      return repairMode.value ? `已装备 · 拥有 ${item.count}` : `拥有 ${item.count} · 点击装备`;
    }
    return `拥有 ${item.count} · 使用一次消耗 1 个`;
  }
  const location = item.locationLabel ? ` · ${item.locationLabel}` : "";
  return `拥有 ${item.count}${location}${suffix}`;
}

function bringCatToCurrentScene(cat) {
  closeCatDiary();
  selectCat(cat, { carry: true });
}

function itemIsInCurrentScene(item) {
  return item?.locationId === currentScene.value.id;
}

function itemCanEnterCurrentScene(item) {
  return Boolean(item?.allowedInCurrentScene);
}

function foodFavoriteCat(item) {
  return cats.value.find((cat) => cat.id === item?.favoriteCatId) || null;
}

function foodEnergyGainValue(item, cat = selectedCat.value) {
  return foodEnergyGainForCat(item, cat);
}

function foodMoodGainValue(item, cat = selectedCat.value) {
  return foodMoodGainForCat(item, cat);
}

function foodSpecialtyGainValue(item) {
  return foodEnergyGainValue(item, foodFavoriteCat(item) || selectedCat.value);
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

function setWorldView(view, options = {}) {
  const nextView = ["room", "shop", "cats"].includes(view) ? view : "room";
  if (nextView !== "room" && (roomEditMode.value || layoutDirty.value)) {
    notice.value = "请先保存并退出物品编辑，再离开活动室。";
    return false;
  }
  if (nextView !== "room") {
    repairMode.value = false;
    scoopMode.value = false;
    toolCursorVisible.value = false;
    catWorldGame.value?.cancelCatCarry?.();
  }
  activeWorldView.value = nextView;
  nextTick(() => {
    if (nextView === "room") catWorldGame.value?.refreshViewport?.();
    if (options.scroll) {
      document.getElementById(`cat-world-view-${nextView}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  });
  return true;
}

function openShopCategory(category) {
  activeCategory.value = category || "food";
  setWorldView("shop", { scroll: true });
}

function setRepairMode(enabled) {
  const nextEnabled = Boolean(enabled);
  if (nextEnabled && itemCount(REPAIR_HAMMER_ITEM_ID) <= 0) {
    repairMode.value = false;
    toolCursorVisible.value = false;
    openShopCategory("consumable");
    notice.value = "背包里没有维修锤，请先在消耗品商店购买。";
    return;
  }
  if (nextEnabled && roomEditMode.value) {
    notice.value = "请先完成物品编辑，再装备维修锤。";
    return;
  }
  if (nextEnabled) {
    scoopMode.value = false;
    renameMode.value = false;
    renameCursorVisible.value = false;
  }
  repairMode.value = nextEnabled;
  toolCursorVisible.value = false;
  selectedDecorId.value = "";
  notice.value = nextEnabled ? "维修模式已开启。" : "已收起维修锤。";
}

function setScoopMode(enabled) {
  const nextEnabled = Boolean(enabled);
  if (nextEnabled && itemCount(LITTER_SCOOP_ITEM_ID) <= 0) {
    scoopMode.value = false;
    toolCursorVisible.value = false;
    activeToolCategory.value = "consumable";
    notice.value = "背包里没有铲子，请先在消耗品商店购买。";
    return;
  }
  if (nextEnabled && roomEditMode.value) {
    notice.value = "请先完成物品编辑，再装备铲子。";
    return;
  }
  if (nextEnabled) {
    repairMode.value = false;
    renameMode.value = false;
    renameCursorVisible.value = false;
  }
  scoopMode.value = nextEnabled;
  toolCursorVisible.value = false;
  selectedDecorId.value = "";
  notice.value = nextEnabled
    ? "铲屎模式已开启，请点击房间里冒烟的猫屎。"
    : "已收起铲子。";
}

function setRenameMode(enabled) {
  const nextEnabled = Boolean(enabled);
  if (nextEnabled && itemCount(CAT_RENAME_CARD_ITEM_ID) <= 0) {
    renameMode.value = false;
    renameCursorVisible.value = false;
    activeToolCategory.value = "consumable";
    notice.value = "背包里没有改名卡，请先在消耗品商店购买。";
    return;
  }
  if (nextEnabled && roomEditMode.value) {
    notice.value = "请先完成物品编辑，再使用改名卡。";
    return;
  }
  if (nextEnabled) {
    repairMode.value = false;
    scoopMode.value = false;
    toolCursorVisible.value = false;
    catWorldGame.value?.cancelCatCarry?.();
  }
  renameMode.value = nextEnabled;
  renameCursorVisible.value = false;
  renameModalOpen.value = false;
  notice.value = nextEnabled
    ? "改名卡已拿起，请点击下方“我的猫咪”中的一张猫卡。"
    : "已收起改名卡。";
}

function openRenameCardModal() {
  setRenameMode(true);
  if (!renameMode.value) return;
  const target = catForId(state.value.selectedCatProfile)
    || selectedCat.value
    || catProfiles.value[0];
  if (!target?.id) {
    renameMode.value = false;
    notice.value = "还没有可以改名的猫咪。";
    return;
  }
  openRenameModal(target);
}

function handlePagePointerMove(event) {
  if (!renameMode.value || renameModalOpen.value) return;
  renameCursorX.value = event.clientX;
  renameCursorY.value = event.clientY;
  renameCursorVisible.value = true;
}

function hideRenameCursor() {
  renameCursorVisible.value = false;
}

function handleRepairTargetClick(item) {
  if (!isDamagedItem(item)) return false;
  if (scoopMode.value) {
    notice.value = `${item.label}需要维修锤，铲子没有消耗。`;
    return true;
  }
  if (!repairMode.value) {
    activeToolCategory.value = "consumable";
    notice.value = "请先在右侧消耗品里点击维修锤，再维修损坏的道具。";
    return true;
  }
  repairItem(item);
  return true;
}

function handleRoomToolPointerMove(event) {
  if (!repairMode.value && !scoopMode.value) return;
  const rect = event.currentTarget.getBoundingClientRect();
  toolCursorX.value = event.clientX - rect.left;
  toolCursorY.value = event.clientY - rect.top;
  toolCursorVisible.value = true;
}

function hideRoomToolCursor() {
  toolCursorVisible.value = false;
}

async function moveOwnedItem(item, locationId) {
  if (!item?.id || busyLocationItemId.value) return;
  if (roomEditMode.value || layoutDirty.value) {
    notice.value = "请先保存当前布局，再移动物品所在区域。";
    return;
  }
  busyLocationItemId.value = item.id;
  notice.value = "";
  try {
    const nextPayload = await fetchJson(routeApiPaths.catWorldItemLocation(), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ itemId: item.id, locationId }),
    });
    replacePayload(nextPayload);
    selectedDecorId.value = "";
    const effect = nextPayload.itemLocation || {};
    notice.value = locationId === "storage"
      ? `${effect.label || item.label} 已收进收纳箱。`
      : `${effect.label || item.label} 已放到${effect.locationLabel || currentScene.value.label}，进入编辑模式后可以继续调整位置。`;
  } catch (error) {
    notice.value = error.message || "物品位置保存失败，请稍后再试。";
  } finally {
    busyLocationItemId.value = "";
  }
}

function handleOwnedToolClick(item) {
  if (!item?.id || busyItemId.value) return;
  if (item.useType === "repair-tool") {
    setRepairMode(!repairMode.value);
    return;
  }
  if (item.useType === "litter-clean") {
    setScoopMode(!scoopMode.value);
    return;
  }
  if (item.useType === "cat-rename") {
    openRenameCardModal();
    return;
  }
  if (handleRepairTargetClick(item)) return;
  if (item.category === "decor") {
    if (!itemIsInCurrentScene(item)) {
      notice.value = `${item.label}现在${item.locationLabel || "在其他区域"}；可以用右侧按钮收纳或放到当前区域。`;
      return;
    }
    selectedDecorId.value = item.id;
    notice.value = roomEditMode.value
      ? `已选中 ${item.label}，在左侧房间里拖动它后点击保存并退出。`
      : `已选中 ${item.label}。点击“编辑物品”后，猫咪会暂时隐藏，就可以拖动它。`;
    return;
  }
  if (item.category === "toy") {
    if (!itemIsInCurrentScene(item)) {
      notice.value = `${item.label}现在${item.locationLabel || "在其他区域"}；可以用右侧按钮收纳或放到当前区域。`;
      return;
    }
    selectedDecorId.value = item.id;
    notice.value = roomEditMode.value
      ? `${item.label} 可以在左侧房间拖动保存。`
      : `${item.label} 正常模式下点击会和猫咪互动；点击“编辑物品”后可以拖动。`;
    return;
  }
  if (item.category === "food") {
    play(item);
    return;
  }
  if (item.category === "consumable") {
    if (item.useType === "litter-prevent") {
      useConsumable(item);
      return;
    }
    useConsumable(item);
    return;
  }
  if (item.category === "cat") {
    selectCat(item, { carry: true });
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
  if (savingRoomLayout.value) return false;
  if (!layoutDirty.value) {
    roomEditMode.value = false;
    selectedDecorId.value = "";
    notice.value = "已退出编辑模式，猫咪回到活动室。";
    return true;
  }
  savingRoomLayout.value = true;
  notice.value = "";
  try {
    const nextLayout = catWorldGame.value?.getLayout() || layoutDraft.value;
    layoutDraft.value = normalizeLayoutDraft(nextLayout);
    const nextPayload = await fetchJson(routeApiPaths.catWorldRoomLayout(), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ sceneId: currentScene.value.id, layout: layoutDraft.value }),
    });
    replacePayload(nextPayload);
    layoutDirty.value = false;
    roomEditMode.value = false;
    selectedDecorId.value = "";
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
    return true;
  } catch (error) {
    notice.value = error.message || "布局保存失败，请稍后再试。";
    return false;
  } finally {
    savingRoomLayout.value = false;
  }
}

async function selectScene(scene) {
  if (!scene?.id || !scene.available || busySceneId.value || scene.id === currentScene.value.id) return false;
  if (roomEditMode.value || layoutDirty.value) {
    const saved = await saveRoomLayout();
    if (!saved) return false;
  }
  busySceneId.value = scene.id;
  notice.value = "";
  try {
    const nextPayload = await fetchJson(routeApiPaths.catWorldSelectScene(), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ sceneId: scene.id }),
    });
    replacePayload(nextPayload);
    roomEditMode.value = false;
    setRepairMode(false);
    setScoopMode(false);
    setRenameMode(false);
    layoutDirty.value = false;
    roomPanActive.value = false;
    notice.value = `已进入${nextPayload.state?.currentScene?.label || scene.label}。`;
    return true;
  } catch (error) {
    notice.value = error.message || "场景切换失败，请稍后再试。";
    return false;
  } finally {
    busySceneId.value = "";
  }
}

function handleSceneAction(scene) {
  if (!scene?.id || busySceneId.value || scene.id === currentScene.value.id) return;
  if (scene.available) {
    selectScene(scene);
    return;
  }
  if (scene.enabled && scene.purchasable && !scene.unlocked) {
    scenePurchaseTarget.value = scene;
  }
}

async function purchaseScene() {
  const scene = scenePurchaseTarget.value;
  if (!scene?.id || busySceneId.value) return;
  if (roomEditMode.value || layoutDirty.value) {
    const saved = await saveRoomLayout();
    if (!saved) return;
  }
  busySceneId.value = scene.id;
  notice.value = "";
  try {
    const nextPayload = await fetchJson(routeApiPaths.catWorldPurchaseScene(), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ sceneId: scene.id }),
    });
    replacePayload(nextPayload);
    scenePurchaseTarget.value = null;
    roomPanActive.value = false;
    notice.value = `${scene.label} 已永久解锁，消耗 ${Number(scene.purchaseCost || 0).toLocaleString()} 能量。`;
  } catch (error) {
    notice.value = error.message || "场景购买失败，请稍后再试。";
  } finally {
    busySceneId.value = "";
  }
}

function startRoomEditMode() {
  if (savingRoomLayout.value) return;
  setRepairMode(false);
  setScoopMode(false);
  setRenameMode(false);
  roomEditMode.value = true;
  catReaction.value = "";
  catReactionAnchored.value = false;
  window.clearTimeout(catReactionTimer);
  notice.value = "已进入编辑模式，猫咪先躲到旁边；现在可以拖动家具和玩具，保存后猫咪会回来。";
}

function handleRoomEditButton() {
  if (roomEditMode.value) {
    saveRoomLayout();
    return;
  }
  startRoomEditMode();
}

function roomEditButtonText() {
  if (savingRoomLayout.value) return "保存中...";
  if (!roomEditMode.value) return "编辑物品";
  return layoutDirty.value ? "保存并退出" : "完成编辑";
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
  return ["toy", "decor", "color", "handbook"].includes(item?.category) && itemCount(item.id) > 0;
}

function canPurchase(item) {
  if (!item?.id) return false;
  if (item.category === "blind-box") return !item.drawn && Number(item.remainingStock || 0) > 0 && canAfford(item);
  if (item.limited) {
    return !isOneTimeOwned(item) && item.isActive !== false && Number(item.remainingStock || 0) > 0 && canAfford(item);
  }
  if (item.category === "cat") return canAfford(item);
  if (item.category === "color") return targetDecorOwned(item) && (itemCount(item.id) > 0 || canAfford(item));
  if (item.category === "handbook") return !isOneTimeOwned(item) && canAfford(item);
  if (["toy", "decor"].includes(item.category)) return !isOneTimeOwned(item) && canAfford(item);
  return canAfford(item);
}

function purchaseHint(item) {
  if (!item?.id) return "";
  if (item.category === "handbook" && isOneTimeOwned(item)) {
    return "已永久拥有，点击打开手册";
  }
  if (item.limited) {
    if (isOneTimeOwned(item)) return "已拥有 1 件，本期不能重复购买";
    if (item.isActive === false) return "这件限定礼物暂时没有上架";
    if (Number(item.remainingStock || 0) <= 0) return "这件限定礼物已经售罄";
    return `全站仅剩 ${item.remainingStock} 件 · 每个账号限购 ${item.maxOwned || 1} 件`;
  }
  if (item.category === "cat") {
    const weights = gameSettings.value.genderDrawWeights || {};
    const remaining = Math.max(Number(energy.value.available || 0) - Number(item.cost || 0), 0);
    const returnText = lostCats.value[item.id]
      ? `${lostCats.value[item.id].escapeLabel || "长期缺少照护"}后离家 · 本次会恢复品种状态 · `
      : "";
    return `${returnText}公猫 ${weights.malePercent ?? 50}% · 母猫 ${weights.femalePercent ?? 50}% · 随机花纹和特点 · 扣 ${item.cost} 能量 · 剩余 ${remaining}`;
  }
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
  if (item.category === "blind-box") {
    if (item.drawn) return `本期已开启，获得了 ${currentBlindSeries.value.cats?.find((cat) => cat.id === item.drawnCatId)?.label || "限定猫咪"}`;
    if (Number(item.remainingStock || 0) <= 0) return "本期限定猫咪已经售罄";
    return `${item.region || "地区"} ${item.issue || "限定"} · 全站剩余 ${item.remainingStock} 只 · 本期每个账号限开一次`;
  }
  if (item.category === "handbook") {
    return isOneTimeOwned(item) ? "已永久拥有" : `扣 ${item.cost} 能量 · 购买后永久解锁`;
  }
  const remaining = Math.max(Number(energy.value.available || 0) - Number(item.cost || 0), 0);
  if (item.category === "food") {
    if (item.foodType === "specialty" && item.favoriteCatLabel) {
      return `扣 ${item.cost} 能量 · ${item.favoriteCatLabel}食用约体力 +${foodSpecialtyGainValue(item)}，食品基础值 +${item.catEnergy} · 剩余 ${remaining}`;
    }
    return `扣 ${item.cost} 能量 · 基础体力 +${item.catEnergy}、心情 +${item.mood} · 剩余 ${remaining}`;
  }
  if (item.category === "consumable") {
    const effect = item.useType === "litter-prevent"
      ? "放进活动室，猫咪使用后自动消失"
      : item.useType === "litter-clean"
        ? "可清理一堆猫屎"
        : item.useType === "cat-rename"
          ? "选择一只自己的猫咪修改名字"
          : item.useType === "repair-tool"
            ? "维修损坏道具时自动消耗 1 把"
            : item.useType === "cat-bath"
              ? `给当前猫洗澡、解除炸毛并增加心情 +${item.mood || 0}`
              : item.useType === "room-care"
                ? `所有猫心情 +${item.mood || 0}`
                : `当前猫心情 +${item.mood || 0}`;
    return `扣 ${item.cost} 能量 · ${effect} · 剩余 ${remaining}`;
  }
  return `将扣 ${item.cost} 积分 · 购买后剩余 ${remaining}`;
}

function purchaseButtonText(item) {
  if (busyItemId.value === item.id) return "处理中...";
  if (item.category === "handbook" && isOneTimeOwned(item)) return "打开手册";
  if (item.limited && isOneTimeOwned(item)) return "已拥有 1 件";
  if (item.limited && item.isActive === false) return "暂停领取";
  if (item.limited && Number(item.remainingStock || 0) <= 0) return "已售罄";
  if (item.category === "cat" && lostCats.value[item.id]) return canAfford(item) ? `扣 ${item.cost} 能量重新领养` : "能量不足";
  if (item.category === "cat" && ownsCat(item.id)) return canAfford(item) ? `再领养一只` : "能量不足";
  if (item.category === "color" && !targetDecorOwned(item)) return "先买家具";
  if (item.category === "blind-box" && item.drawn) return "本期已开启";
  if (item.category === "blind-box" && Number(item.remainingStock || 0) <= 0) return "本期已售罄";
  if (item.category === "color" && colorApplied(item)) return "已应用";
  if (item.category === "color" && itemCount(item.id) > 0) return "应用配色";
  if (isDamagedItem(item)) return "去右侧维修";
  if (isOneTimeOwned(item)) return "已拥有";
  if (item.category === "blind-box") return canAfford(item) ? `消耗 ${item.cost} 能量开启` : "能量不足";
  return canAfford(item) ? `扣 ${item.cost} 能量购买` : "能量不足";
}

function handbookType(item) {
  return item?.handbookType === "food" ? "food" : "cats";
}

function openHandbook(type) {
  const nextType = type === "food" ? "food" : "cats";
  if (nextType === "cats") {
    const section = resolveCollectionSection(
      catCollectionCatalog.value.sections,
      selectedCollectionRegionKey.value,
      currentBlindSeries.value.region,
    );
    selectedCollectionRegionKey.value = section.key || "";
    selectedCollectionCatId.value = resolveCollectionCat(section, selectedCollectionCatId.value).id || "";
  }
  activeHandbook.value = nextType;
}

function shopItemActionAvailable(item) {
  return item?.category === "handbook" && isOneTimeOwned(item) ? true : canPurchase(item);
}

function handleShopItemAction(item) {
  if (item?.category === "handbook" && isOneTimeOwned(item)) {
    openHandbook(handbookType(item));
    return;
  }
  purchase(item);
}

function showCatReaction(cat = selectedCat.value, message = "", options = {}) {
  if (roomEditMode.value) return;
  const catLabel = cat?.displayLabel || cat?.nickname || cat?.label || "猫咪";
  const nextIndex = catPetSequence.value % catReactionTexts.length;
  const reactionMessage = message || catReactionTexts[nextIndex];
  focusedCatId.value = cat?.id || "";
  catReaction.value = `${catLabel}: ${reactionMessage}`;
  catReactionAnchored.value = options.anchor === false
    ? true
    : Boolean(catWorldGame.value?.showCatReaction(cat?.id, reactionMessage, {
        pause: options.pause !== false,
      }));
  catPetSequence.value += 1;
  window.clearTimeout(catReactionTimer);
  catReactionTimer = window.setTimeout(() => {
    catReaction.value = "";
    catReactionAnchored.value = false;
  }, CAT_BUBBLE_TOTAL_MS);
}

function selectLearningWeekDay(day = {}) {
  if (!day.date) return;
  selectedLearningWeekDate.value = day.date;
  const memory = catWorldWeekMemory(day, learningGuideCat.value);
  showCatReaction(learningGuideCat.value, memory.catMessage);
}

async function showLearningCompanionReaction(options = {}) {
  const companion = learningCompanion.value;
  let cat = catForId(companion.catId) || learningGuideCat.value;
  if (!cat?.id) return;
  const catIsInRoom = roomCats.value.some((roomCat) => roomCat.id === cat.id);
  if (!catIsInRoom) {
    if (options.locate === false) return;
    const targetScene = scenes.value.find((scene) => scene.id === cat.currentSceneId);
    if (!targetScene?.available) {
      notice.value = `${cat.displayLabel || cat.label || "今日陪学猫"}暂时不在可进入的房间。`;
      return;
    }
    const switched = await selectScene(targetScene);
    if (!switched) return;
    await nextTick();
    updateCatWorldGame();
    cat = catForId(companion.catId) || cat;
  }
  catWorldGame.value?.focusCat(cat.id);
  showCatReaction(cat, companion.message || learningRoute.value.coachLine);
  if (options.scroll !== false) {
    nextTick(() => gameMountRef.value?.scrollIntoView({ behavior: "smooth", block: "center" }));
  }
}

function announceLearningCompanionOnEntry() {
  const token = catWorldLearningCompanionToken(learningCompanion.value);
  if (!token) return;
  const storageKey = `speakeasy:cat-world-learning-companion:${token}`;
  try {
    if (window.sessionStorage.getItem(storageKey)) return;
    window.sessionStorage.setItem(storageKey, "1");
  } catch {
    // A speech bubble is still useful when storage is unavailable.
  }
  window.clearTimeout(learningCompanionReactionTimer);
  learningCompanionReactionTimer = window.setTimeout(() => {
    showLearningCompanionReaction({ scroll: false, locate: false });
  }, 450);
}

async function petCat(cat = selectedCat.value, options = {}) {
  if (roomEditMode.value) return;
  if (!cat?.id) return;
  showCatReaction(cat, options.message || "", { anchor: options.anchor });
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
  const wasLost = Boolean(lostCats.value[item.id]);
  busyItemId.value = item.id;
  notice.value = "";
  try {
    const nextPayload = await fetchJson(routeApiPaths.catWorldPurchase(), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ itemId: item.id }),
    });
    replacePayload(nextPayload);
    if (nextPayload.blindBoxResult?.cat) {
      openedBlindBox.value = nextPayload.blindBoxResult;
      const profile = nextPayload.blindBoxResult.profile || nextPayload.adoptedCatProfile || {};
      notice.value = `抽中了 ${nextPayload.blindBoxResult.cat.rarity} · ${nextPayload.blindBoxResult.cat.label}，${profile.genderLabel || "随机性别"} · ${profile.patternLabel || "随机花纹"} · ${profile.featureLabel || "随机特点"} · ${profile.personality || "独立个性"}！`;
      return;
    }
    if (item.category === "handbook") {
      openHandbook(handbookType(item));
      notice.value = `${item.label} 已永久解锁。`;
      return;
    }
    const adopted = nextPayload.adoptedCatProfile || {};
    const profileText = [adopted.genderLabel, adopted.patternLabel, adopted.featureLabel, adopted.personality].filter(Boolean).join(" · ");
    notice.value = wasLost
      ? `${item.label} 已重新回到活动室，${profileText}，体力和心情恢复到安全状态。`
      : `${adopted.displayLabel || item.label} 已加入猫咪世界：${profileText}。`;
  } catch (error) {
    notice.value = error.message || "购买失败，请稍后再试。";
  } finally {
    busyItemId.value = "";
  }
}

async function play(item) {
  if (!item?.id || busyItemId.value) return;
  if (roomEditMode.value) {
    notice.value = "编辑物品时猫咪互动暂停；保存或完成编辑后再陪猫咪玩。";
    return;
  }
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
      const targetCat = catForId(effect.catId) || focusedCat.value;
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
      const targetCat = catForId(effect.catId) || selectedCat.value;
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

async function cleanLitter() {
  if (roomEditMode.value || busyItemId.value) return;
  if (!scoopMode.value) {
    activeToolCategory.value = "consumable";
    notice.value = repairMode.value
      ? "猫屎需要用铲子清理，维修锤没有消耗。"
      : "请先在右侧消耗品里点击铲子，再清理猫屎。";
    return;
  }
  if (itemCount(LITTER_SCOOP_ITEM_ID) <= 0) {
    setScoopMode(false);
    notice.value = "背包里没有铲子，请先在消耗品商店购买。";
    return;
  }
  busyItemId.value = "litter-clean";
  notice.value = "";
  try {
    const nextPayload = await fetchJson(routeApiPaths.catWorldCleanLitter(), { method: "POST" });
    replacePayload(nextPayload);
    const effect = nextPayload.effect || {};
    notice.value = `${effect.message || "猫屎已经清理好了。"} 剩余 ${effect.remainingLitter || 0} 堆，铲子 ${effect.scoopRemaining || 0} 把。`;
    scoopMode.value = false;
    toolCursorVisible.value = false;
  } catch (error) {
    notice.value = error.message || "清理失败，请先检查铲子库存。";
  } finally {
    busyItemId.value = "";
  }
}

async function useConsumable(item, options = {}) {
  if (!item?.id || busyItemId.value || roomEditMode.value) return;
  busyItemId.value = item.id;
  notice.value = "";
  const targetProfileId = options.targetCatId || openCatDiaryId.value || focusedCat.value.id;
  const targetCatId = catForId(targetProfileId)?.id || state.value.selectedCatProfile || state.value.selectedCat;
  try {
    const nextPayload = await fetchJson(routeApiPaths.catWorldUseConsumable(), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ itemId: item.id, catId: targetCatId }),
    });
    replacePayload(nextPayload);
    const effect = nextPayload.effect || {};
    notice.value = `${effect.message || `${item.label}已经使用。`} 剩余 ${effect.remaining || 0} 个。`;
    const targetCat = catForId(effect.catId) || focusedCat.value;
    const targetEffect = Array.isArray(effect.effects)
      ? effect.effects.find((row) => row.catId === targetCat.id || row.catId === catBreedId(targetCat))
      : null;
    if (targetEffect?.message) showCatReaction(targetCat, targetEffect.message);
  } catch (error) {
    notice.value = error.message || "消耗品使用失败，请稍后再试。";
  } finally {
    busyItemId.value = "";
  }
}

async function repairItem(item) {
  if (!item?.id || busyItemId.value) return;
  const damaged = damageInfo(item);
  if (!damaged) return;
  if (itemCount(REPAIR_HAMMER_ITEM_ID) <= 0) {
    openShopCategory("consumable");
    notice.value = "维修需要 1 把一次性维修锤，请先在下方消耗品商店购买。";
    return;
  }
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
    notice.value = `${repair.label || item.label} 已维修好，消耗 1 把维修锤和 ${cost} 能量，背包还剩 ${repair.hammerRemaining || 0} 把。`;
    showCatReaction(targetCat, `${repair.label || item.label}修好了，我会小心一点。`);
    repairMode.value = false;
    toolCursorVisible.value = false;
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
      body: JSON.stringify({ sceneId: currentScene.value.id, decorId }),
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
      body: JSON.stringify({ sceneId: currentScene.value.id, decorId, tone: option.tone }),
    });
    replacePayload(nextPayload);
    notice.value = `${nextPayload.style?.label || option.label || "配色"} 已应用，拖动家具后可以保存布局。`;
  } catch (error) {
    notice.value = error.message || "颜色切换失败，请先购买这个配色。";
  } finally {
    busyItemId.value = "";
  }
}

function openRenameModal(cat) {
  const ownedProfile = catProfiles.value.find((profile) => profile.id === cat?.id);
  if (!renameMode.value || !ownedProfile) return;
  renameTargetCatId.value = ownedProfile.id;
  renameDraft.value = ownedProfile.nickname || "";
  renameModalOpen.value = true;
  renameCursorVisible.value = false;
  nextTick(() => renameInputRef.value?.focus());
}

function chooseRenameTarget(cat) {
  if (!cat?.id || renameBusy.value) return;
  renameTargetCatId.value = cat.id;
  renameDraft.value = cat.nickname || "";
  nextTick(() => renameInputRef.value?.focus());
}

function closeRenameModal() {
  if (renameBusy.value) return;
  renameModalOpen.value = false;
  renameMode.value = false;
  renameCursorVisible.value = false;
  renameTargetCatId.value = "";
  renameDraft.value = "";
  notice.value = "已收起改名卡，卡片没有消耗。";
}

async function submitCatRename() {
  const targetCat = catForId(renameTargetCatId.value);
  const nickname = renameDraft.value.trim();
  if (!targetCat?.id || renameBusy.value) return;
  if (!nickname || nickname.length > 12) {
    notice.value = "猫咪名字需要 1 至 12 个字符。";
    renameInputRef.value?.focus();
    return;
  }
  renameBusy.value = true;
  notice.value = "";
  try {
    const nextPayload = await fetchJson(routeApiPaths.catWorldRenameCat(), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ profileId: targetCat.id, nickname }),
    });
    replacePayload(nextPayload);
    const effect = nextPayload.effect || {};
    renameModalOpen.value = false;
    renameMode.value = false;
    renameCursorVisible.value = false;
    renameTargetCatId.value = "";
    renameDraft.value = "";
    notice.value = `${effect.previousLabel || targetCat.displayLabel || targetCat.label} 已改名为 ${effect.nickname || nickname}，还剩 ${effect.remaining || 0} 张改名卡。`;
  } catch (error) {
    notice.value = error.message || "改名失败，请稍后再试。";
  } finally {
    renameBusy.value = false;
  }
}

async function handleCatCardClick(cat) {
  if (renameMode.value) {
    openRenameModal(cat);
    return;
  }
  if (!setWorldView("room")) return;
  await nextTick();
  await selectCat(cat, { carry: true });
}

async function selectCat(catOrId, options = {}) {
  const profile = typeof catOrId === "object" ? catOrId : catForId(catOrId);
  const catId = catBreedId(profile) || String(catOrId || "");
  const profileId = profile?.profileId || (profile?.breedId ? profile.id : "");
  if (!catId || busyItemId.value) return;
  const carry = Boolean(options.carry);
  if (carry) {
    repairMode.value = false;
    scoopMode.value = false;
    toolCursorVisible.value = false;
  }
  busyItemId.value = profileId || catId;
  notice.value = "";
  try {
    const nextPayload = await fetchJson(routeApiPaths.catWorldSelectCat(), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ catId, profileId, moveToCurrentScene: carry }),
    });
    replacePayload(nextPayload);
    const cat = profile || catForId(nextPayload.state?.selectedCatProfile) || catForId(catId);
    const roomCatId = profileId || cat?.id || catId;
    focusedCatId.value = roomCatId;
    await nextTick();
    const carryInteraction = carry ? catWorldGame.value?.carryCat?.(roomCatId) : null;
    const locked = carry
      ? Boolean(carryInteraction?.handled)
      : Boolean(catWorldGame.value?.focusCat?.(roomCatId));
    if (locked) {
      gameMountRef.value?.scrollIntoView({ behavior: "smooth", block: "center" });
      showCatReaction(cat, carryInteraction?.carrying ? "被抱起来啦，带我去想去的地方吧。" : "镜头找到我啦，我会在这里陪着你。");
    }
    notice.value = carryInteraction?.message
      || `${cat?.displayLabel || cat?.label || "猫咪"}${nextPayload.catMoved ? ` 已来到${currentScene.value.label}` : " 已设为主猫"}${locked ? "，活动室镜头已锁定" : ""}。`;
  } catch (error) {
    notice.value = error.message || "切换猫咪失败，请稍后再试。";
  } finally {
    busyItemId.value = "";
  }
}
</script>

<template>
  <section
    :class="['cat-world-page', { 'is-renaming': renameMode && !renameModalOpen }]"
    @pointermove="handlePagePointerMove"
    @pointerleave="hideRenameCursor"
  >
    <span
      v-if="renameMode && !renameModalOpen && renameCursorVisible"
      class="cat-world-rename-cursor"
      :style="{ left: `${renameCursorX}px`, top: `${renameCursorY}px` }"
      aria-hidden="true"
    >
      <CatWorldProductIcon :item="toolIconItems.rename" compact aria-hidden="true" />
    </span>
    <section class="cat-world-hero">
      <div class="cat-world-copy">
        <p class="section-kicker">Cat World</p>
        <h1>猫咪能量世界</h1>
        <p>把今天练过的英文变成软绵绵的能量，给猫咪买小鱼干、玩具和漂亮家具，把她的房间一点点装可爱。</p>
      </div>
      <div class="cat-world-hero-status">
        <section
          class="cat-world-play-time"
          :class="`is-${playTimeCardState}`"
          aria-label="今日猫咪世界倒计时"
        >
          <span>今日陪伴倒计时</span>
          <strong>{{ playTimeClock }}</strong>
          <em>{{ playTimeProgressLabel }}</em>
          <small>{{ playTimeTierLabel }}</small>
        </section>
        <button class="cat-world-wallet" type="button" aria-label="猫咪世界能量" @click="energyModalOpen = true">
          <span>可用能量</span>
          <strong>{{ energy.available || 0 }}</strong>
          <em class="cat-world-wallet-today">今日 +{{ todayEnergy }}</em>
          <small>累计 {{ energy.earned || 0 }} · 已用 {{ energy.spent || 0 }}</small>
        </button>
      </div>
    </section>

    <section class="cat-world-learning-route" aria-labelledby="cat-world-learning-route-title">
      <header class="cat-world-learning-guide">
        <button
          class="cat-world-learning-guide-button"
          type="button"
          :title="`听听${learningCompanion.catLabel || learningRoute.guideName}怎么说`"
          :aria-label="`听听${learningCompanion.catLabel || learningRoute.guideName}的陪学回应`"
          @click="showLearningCompanionReaction"
        >
          <figure
            :class="[
              'cat-world-cat-portrait',
              'cat-world-learning-guide-portrait',
              `pattern-${learningGuidePortrait.pattern}`,
              `feature-${learningGuidePortrait.feature}`,
            ]"
            :style="learningGuidePortrait.style"
            aria-hidden="true"
          >
            <i class="cat-world-cat-portrait-ear left"></i>
            <i class="cat-world-cat-portrait-ear right"></i>
            <i class="cat-world-cat-portrait-face">
              <i class="cat-world-cat-portrait-eye left"></i>
              <i class="cat-world-cat-portrait-eye right"></i>
              <i class="cat-world-cat-portrait-nose"></i>
            </i>
          </figure>
        </button>
        <div>
          <p class="section-kicker">Cat Quest</p>
          <h2 id="cat-world-learning-route-title">{{ learningRoute.title }}</h2>
          <p class="cat-world-learning-coach-line">{{ learningRoute.coachLine }}</p>
          <p class="cat-world-learning-companion-status">
            <MessageCircleIcon :size="13" :stroke-width="2.8" aria-hidden="true" />
            <strong>{{ learningCompanion.statusLabel || "等待一起热身" }}</strong>
            <span>{{ learningCompanionGrowthLabel }}</span>
          </p>
        </div>
        <strong class="cat-world-learning-streak">
          <FlameIcon :size="17" :stroke-width="2.8" aria-hidden="true" />
          {{ learningRoute.streak ? `${learningRoute.streak} 天` : "今天开始" }}
        </strong>
      </header>
      <ol class="cat-world-learning-steps" aria-label="今日英语学习路线">
        <li
          v-for="(step, index) in learningRoute.steps"
          :key="step.key"
          :class="{ complete: step.completed, active: step.active }"
        >
          <span class="cat-world-learning-step-marker" aria-hidden="true">
            <CheckIcon v-if="step.completed" :size="17" :stroke-width="3" />
            <PawPrintIcon v-else :size="17" :stroke-width="2.8" />
          </span>
          <div>
            <small>STEP 0{{ index + 1 }}</small>
            <strong>{{ step.label }}</strong>
            <p>{{ step.detail }}</p>
          </div>
          <span class="cat-world-learning-step-actions">
            <button v-if="step.actionKind === 'energy'" type="button" @click="energyModalOpen = true">
              <MoveRightIcon :size="14" :stroke-width="3" aria-hidden="true" />{{ step.action }}
            </button>
            <a v-else :href="step.href"><MoveRightIcon :size="14" :stroke-width="3" aria-hidden="true" />{{ step.action }}</a>
            <a v-if="step.alternateHref" class="secondary" :href="step.alternateHref">{{ step.alternateAction }}</a>
          </span>
        </li>
      </ol>
      <section
        v-if="learningWeekTrail.days.length"
        :class="['cat-world-learning-week', { 'is-expanded': learningWeekExpanded }]"
        aria-labelledby="cat-world-learning-week-title"
      >
        <header class="cat-world-learning-week-summary">
          <div>
            <small>WEEKLY RHYTHM</small>
            <strong id="cat-world-learning-week-title">最近七天陪学足迹</strong>
          </div>
          <p>{{ learningWeekTrail.summary }}</p>
          <button
            class="cat-world-learning-week-toggle"
            type="button"
            :aria-expanded="learningWeekExpanded"
            aria-controls="cat-world-learning-week-days"
            @click="learningWeekExpanded = !learningWeekExpanded"
          >
            <span>{{ learningWeekExpanded ? "收起记录" : "查看七天" }}</span>
            <ChevronDown :size="16" :stroke-width="3" aria-hidden="true" />
          </button>
          <div v-if="learningWeekExpanded" class="cat-world-learning-week-memory" aria-live="polite">
            <p><span>{{ learningWeekMemory.dateLabel }}</span> · {{ learningWeekMemory.detail }}</p>
            <p>{{ learningWeekMemory.catName }}：{{ learningWeekMemory.catMessage }}</p>
          </div>
        </header>
        <ol v-if="learningWeekExpanded" id="cat-world-learning-week-days" class="cat-world-learning-week-days">
          <li
            v-for="day in learningWeekTrail.days"
            :key="day.date"
            :class="[
              `is-${day.statusKey}`,
              {
                'is-today': day.today,
                'is-selected': day.date === selectedLearningWeekDay.date,
              },
            ]"
          >
            <button
              type="button"
              :title="day.detail"
              :aria-label="`${day.weekdayLabel} ${day.dayLabel}：${day.detail}`"
              :aria-pressed="day.date === selectedLearningWeekDay.date"
              @click="selectLearningWeekDay(day)"
            >
              <span>{{ day.weekdayLabel }}</span>
              <i class="cat-world-learning-week-marker" aria-hidden="true">
                <CheckIcon v-if="day.loopComplete" :size="14" :stroke-width="3" />
                <PawPrintIcon v-else-if="day.active" :size="13" :stroke-width="2.8" />
                <span v-else>·</span>
              </i>
              <strong>{{ day.statusLabel }}</strong>
              <small>{{ day.dayLabel }}</small>
            </button>
          </li>
        </ol>
      </section>
    </section>

    <div class="cat-world-play-area" :class="{ 'is-locked': playTimeLocked }">
      <div v-if="playTimeLocked" class="cat-world-play-lock" role="status" aria-live="polite">
        <section class="cat-world-play-lock-card" aria-labelledby="cat-world-play-lock-title">
          <span class="cat-world-play-lock-icon" aria-hidden="true">
            <LockIcon :size="22" :stroke-width="2.8" />
          </span>
          <div>
            <p class="section-kicker">Observation Mode</p>
            <h2 id="cat-world-play-lock-title">观察模式</h2>
            <p>猫咪仍会照常生活；完成学习任务后即可抱猫、喂食和玩耍。</p>
          </div>
          <div class="cat-world-observation-actions">
            <strong>{{ playTimeProgressLabel }}</strong>
            <span v-if="roomCanPan" aria-label="观察房间镜头">
              <button type="button" title="观察上一屏" aria-label="观察房间上一屏" @click="panRoomPage(-1)">
                <ChevronLeft :size="19" :stroke-width="3" aria-hidden="true" />
              </button>
              <button type="button" title="观察下一屏" aria-label="观察房间下一屏" @click="panRoomPage(1)">
                <ChevronRight :size="19" :stroke-width="3" aria-hidden="true" />
              </button>
            </span>
          </div>
        </section>
      </div>

      <div
        class="cat-world-play-content"
        :inert="playTimeLocked ? '' : null"
        :aria-label="playTimeLocked ? '猫咪世界观察模式，互动暂时锁定' : null"
      >
      <p v-if="notice" class="cat-world-notice" aria-live="polite">{{ notice }}</p>
      <div v-if="lostCatRows.length" class="cat-world-lost-alert" role="status">
      <strong>{{ lostCatRows.map((cat) => cat.catLabel).join("、") }}已经离开活动室</strong>
      <span>{{ lostCatRows[0].escapeLabel }}；需要在猫咪商店重新领养。</span>
      <button type="button" @click="openShopCategory('cat')">查看猫咪商店</button>
      </div>

      <nav class="cat-world-view-switcher" role="tablist" aria-label="猫咪世界功能">
        <button
          id="cat-world-view-room-tab"
          type="button"
          role="tab"
          :class="{ active: activeWorldView === 'room' }"
          :aria-selected="activeWorldView === 'room'"
          aria-controls="cat-world-view-room"
          @click="setWorldView('room')"
        >
          <HouseIcon :size="20" :stroke-width="2.8" aria-hidden="true" />
          <span><strong>活动室</strong><small>{{ currentScene.label }}</small></span>
        </button>
        <button
          id="cat-world-view-shop-tab"
          type="button"
          role="tab"
          :class="{ active: activeWorldView === 'shop' }"
          :aria-selected="activeWorldView === 'shop'"
          aria-controls="cat-world-view-shop"
          @click="setWorldView('shop')"
        >
          <ShoppingBagIcon :size="20" :stroke-width="2.8" aria-hidden="true" />
          <span><strong>猫咪商店</strong><small>{{ categories.length }} 个分类</small></span>
        </button>
        <button
          id="cat-world-view-cats-tab"
          type="button"
          role="tab"
          :class="{ active: activeWorldView === 'cats' }"
          :aria-selected="activeWorldView === 'cats'"
          aria-controls="cat-world-view-cats"
          @click="setWorldView('cats')"
        >
          <CatIcon :size="20" :stroke-width="2.8" aria-hidden="true" />
          <span><strong>我的猫咪</strong><small>{{ catProfiles.length }} 只伙伴</small></span>
        </button>
      </nav>

    <section
      v-show="activeWorldView === 'room'"
      id="cat-world-view-room"
      class="cat-world-layout"
      role="tabpanel"
      aria-labelledby="cat-world-view-room-tab"
    >
      <section class="cat-world-room-panel panel">
        <div v-if="scenes.length > 1" class="cat-world-scene-tabs" role="tablist" aria-label="猫咪世界场景">
          <button
            v-for="scene in scenes"
            :key="scene.id"
            type="button"
            role="tab"
            :aria-selected="scene.id === currentScene.id"
            :class="{ active: scene.id === currentScene.id, locked: scene.enabled && !scene.unlocked }"
            :disabled="!scene.enabled || Boolean(busySceneId)"
            :title="scene.available ? `进入${scene.label}` : scene.enabled ? `购买${scene.label}` : `${scene.label}尚未开放`"
            @click="handleSceneAction(scene)"
          >
            <span>{{ scene.label }}</span>
            <small v-if="scene.enabled && !scene.unlocked">{{ Number(scene.purchaseCost || 0).toLocaleString() }} 能量</small>
            <small v-else-if="!scene.enabled">规划中</small>
            <small v-else>{{ scene.catCount || 0 }}只 · {{ scene.itemCount || 0 }}件</small>
          </button>
        </div>
        <div class="cat-world-room-head">
          <div>
            <p class="section-kicker">{{ currentScene.englishName || "Room" }}</p>
            <h2>{{ currentScene.label || "像素猫活动室" }}</h2>
          </div>
          <div class="cat-world-room-actions">
            <button
              class="cat-world-edit-button"
              type="button"
              :class="{ active: roomEditMode }"
              :disabled="savingRoomLayout"
              @click="handleRoomEditButton"
            >
              {{ roomEditButtonText() }}
            </button>
            <div class="cat-world-mood cat-world-dual-status">
              <span>{{ roomEditMode ? "编辑中 · 猫咪隐藏" : mood.catEnergyLabel || "体力稳定" }}</span>
              <strong>{{ catEnergyScore }}</strong>
              <small>{{ mood.label || "安静陪读" }} · {{ moodScore }}</small>
            </div>
          </div>
        </div>

        <div class="cat-world-ai-panel" :class="{ expanded: catOsExpanded }" aria-live="polite">
          <header class="cat-world-ai-panel-head">
            <div>
              <span>CAT-OS</span>
              <strong>{{ focusedCat.displayLabel || focusedCat.label || "暂无猫咪" }} · {{ focusedCat.personality || "等待重新领养" }}</strong>
            </div>
            <button
              type="button"
              :aria-expanded="catOsExpanded"
              :aria-label="catOsExpanded ? '收起猫咪详细状态' : '展开猫咪详细状态'"
              @click="catOsExpanded = !catOsExpanded"
            >
              <ChevronDown :size="18" :stroke-width="2.8" aria-hidden="true" />
            </button>
          </header>
          <p>{{ focusedCatThought }}</p>
          <div v-if="catOsExpanded" class="cat-world-ai-panel-details">
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
        </div>

        <div
          :class="[
            'cat-world-room',
            {
              'is-editing': roomEditMode,
              'is-panning': roomPanActive,
              'is-repairing': repairMode,
              'is-scooping': scoopMode,
              'can-pan': roomCanPan,
            },
          ]"
          :aria-label="`${currentScene.label || '猫咪房间'}场景，今日学习灯牌已亮 ${learningRoomSignal.completedCount}/3 格`"
          @pointermove="handleRoomToolPointerMove"
          @pointerleave="hideRoomToolCursor"
        >
          <div
            class="cat-world-room-viewport"
            @wheel.capture="handleRoomWheel"
          >
            <div ref="gameMountRef" class="cat-world-game-stage"></div>
          </div>
          <span
            v-if="repairMode && toolCursorVisible"
            class="cat-world-tool-cursor cat-world-repair-cursor"
            :style="{ left: `${toolCursorX}px`, top: `${toolCursorY}px` }"
            aria-hidden="true"
          >
            <CatWorldProductIcon :item="toolIconItems.repair" compact aria-hidden="true" />
          </span>
          <span
            v-if="scoopMode && toolCursorVisible"
            class="cat-world-tool-cursor cat-world-scoop-cursor"
            :style="{ left: `${toolCursorX}px`, top: `${toolCursorY}px` }"
            aria-hidden="true"
          >
            <CatWorldProductIcon :item="toolIconItems.scoop" compact aria-hidden="true" />
          </span>
          <div v-if="repairMode" class="cat-world-repair-mode" role="status">
            <span><HammerIcon :size="18" :stroke-width="3" aria-hidden="true" />维修模式</span>
            <button type="button" title="收起维修锤" aria-label="收起维修锤" @click="setRepairMode(false)">
              <XIcon :size="17" :stroke-width="3" aria-hidden="true" />
            </button>
          </div>
          <div v-if="scoopMode" class="cat-world-repair-mode cat-world-scoop-mode" role="status">
            <span><ShovelIcon :size="18" :stroke-width="3" aria-hidden="true" />铲屎模式</span>
            <button type="button" title="收起铲子" aria-label="收起铲子" @click="setScoopMode(false)">
              <XIcon :size="17" :stroke-width="3" aria-hidden="true" />
            </button>
          </div>
          <button
            v-if="roomCanPan && !roomEditMode"
            class="cat-world-room-pan-button left"
            type="button"
            title="查看上一屏"
            aria-label="查看房间上一屏"
            @click="panRoomPage(-1)"
          >
            <ChevronLeft :size="26" :stroke-width="3" aria-hidden="true" />
          </button>
          <button
            v-if="roomCanPan && !roomEditMode"
            class="cat-world-room-pan-button right"
            type="button"
            title="查看下一屏"
            aria-label="查看房间下一屏"
            @click="panRoomPage(1)"
          >
            <ChevronRight :size="26" :stroke-width="3" aria-hidden="true" />
          </button>
          <div v-if="roomEditMode || layoutDirty" class="cat-world-layout-toolbar">
            <span>{{ roomEditMode ? (layoutDirty ? "编辑中 · 布局有改动" : "编辑中 · 猫咪暂时隐藏") : "点击编辑物品后可拖动" }}</span>
            <button
              type="button"
              :disabled="savingRoomLayout"
              @click="saveRoomLayout"
            >
              {{ savingRoomLayout ? "保存中..." : layoutDirty ? "保存并退出" : "完成编辑" }}
            </button>
          </div>
          <div
            v-if="catReaction && !roomEditMode && !catReactionAnchored"
            :key="`cat-reaction-${catPetSequence}`"
            class="cat-world-reaction"
            aria-live="polite"
          >
            {{ catReaction }}
          </div>
          <div
            v-if="catPetSequence && !roomEditMode && !catReactionAnchored"
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
          <span>猫咪 {{ roomCats.length }}</span>
          <span :class="{ alert: hygiene.count > 0 }">卫生 {{ hygiene.count || 0 }} 堆猫屎</span>
          <span v-if="activeFood.active">食物剩余 {{ formatSeconds(activeFood.remainingSeconds) }}</span>
          <span v-if="activeCare.active">猫草剩余 {{ formatSeconds(activeCare.remainingSeconds) }}</span>
          <span v-if="lastPlayLabel">刚刚玩过 {{ lastPlayLabel }}</span>
        </div>
      </section>

      <aside :class="['cat-world-owned-panel', 'panel', { 'is-drawer-open': bagExpanded }]">
        <button
          class="cat-world-owned-drawer-toggle"
          type="button"
          :aria-expanded="bagExpanded"
          aria-controls="cat-world-owned-drawer-body"
          @click="bagExpanded = !bagExpanded"
        >
          <ShoppingBagIcon :size="20" :stroke-width="2.8" aria-hidden="true" />
          <span>
            <strong>背包与猫咪档案</strong>
            <small>{{ ownedToolTotal }} 项物品 · {{ catProfiles.length }} 只猫咪</small>
          </span>
          <ChevronDown :size="18" :stroke-width="3" aria-hidden="true" />
        </button>
        <div id="cat-world-owned-drawer-body" class="cat-world-owned-drawer-body">
        <div class="cat-world-owned-overview">
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

        <div :class="['cat-world-hygiene-status', { alert: hygiene.count > 0 }]">
          <span>房间卫生</span>
          <strong>{{ hygiene.count ? `${hygiene.count} 堆猫屎` : "干净" }}</strong>
          <small v-if="hygiene.count">每只猫每小时心情额外 -{{ hygieneMoodPenalty }} · 点击房间里的猫屎清理</small>
          <small v-if="litterBathAccelerationText">{{ litterBathAccelerationText }}</small>
          <small v-else>猫砂 {{ hygiene.catLitterCount || 0 }} 包 · 铲子 {{ hygiene.scoopCount || 0 }} 把</small>
          <small v-if="hygiene.hasPlacedCatLitter">已放好豆腐猫砂，等待猫咪使用</small>
        </div>

        <div v-if="activeCare.active" class="cat-world-active-food cat-world-active-care">
          <span>放置中的消耗品</span>
          <strong>{{ activeCare.label }}</strong>
          <small>{{ activeCare.targetCatLabel || "猫咪" }}会慢慢靠近 · {{ formatSeconds(activeCare.remainingSeconds) }} 后消失</small>
        </div>
        </div>

        <div class="cat-world-owned-tools">
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
              {
                active: selectedDecorId === item.id || state.selectedCatProfile === item.id,
                'repair-equipped': repairMode && item.useType === 'repair-tool',
                'scoop-equipped': scoopMode && item.useType === 'litter-clean',
                'rename-equipped': renameMode && item.useType === 'cat-rename',
                damaged: item.damageInfo,
                'has-color-swatches': item.category === 'decor' && item.styleOptions?.length,
              },
            ]"
          >
            <button
              class="cat-world-owned-main"
              type="button"
              :aria-pressed="item.useType === 'repair-tool' ? repairMode : item.useType === 'litter-clean' ? scoopMode : item.useType === 'cat-rename' ? renameMode : null"
              :disabled="busyItemId === item.id || busyLocationItemId === item.id"
              @click="handleOwnedToolClick(item)"
            >
              <CatWorldProductIcon :item="item" compact aria-hidden="true" />
              <span class="cat-world-owned-copy">
                <span>{{ item.englishName || item.rarity || item.category }}</span>
                <strong>{{ item.label }}</strong>
                <small>{{ ownedToolSubtext(item) }}</small>
              </span>
            </button>
            <div v-if="['decor', 'toy'].includes(item.category)" class="cat-world-item-location-actions">
              <em><MapPinIcon :size="14" :stroke-width="2.6" aria-hidden="true" />{{ item.locationLabel || "一楼活动室" }}</em>
              <button
                v-if="itemIsInCurrentScene(item)"
                type="button"
                title="收进收纳箱"
                :disabled="busyLocationItemId === item.id"
                @click.stop="moveOwnedItem(item, 'storage')"
              >
                <ArchiveIcon :size="15" :stroke-width="2.7" aria-hidden="true" />
                <span>{{ busyLocationItemId === item.id ? "保存中" : "收纳" }}</span>
              </button>
              <button
                v-else
                type="button"
                :title="itemCanEnterCurrentScene(item) ? `放到${currentScene.label}` : '这件物品不适合当前区域'"
                :disabled="busyLocationItemId === item.id || !itemCanEnterCurrentScene(item)"
                @click.stop="moveOwnedItem(item, currentScene.id)"
              >
                <MoveRightIcon :size="15" :stroke-width="2.7" aria-hidden="true" />
                <span>{{ busyLocationItemId === item.id ? "保存中" : "放到这里" }}</span>
              </button>
            </div>
            <div v-if="item.category === 'decor' && item.styleOptions?.length && itemIsInCurrentScene(item)" class="cat-world-color-swatches" aria-label="已拥有配色">
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
        </div>

        <section class="cat-world-profile-dock" aria-labelledby="cat-world-profile-dock-title">
          <div class="cat-world-profile-dock-head">
            <div>
              <p class="section-kicker">Agent Diary</p>
              <h3 id="cat-world-profile-dock-title">今日猫咪档案</h3>
            </div>
            <span>{{ catAgentDiaries.length }} 只</span>
          </div>
          <div class="cat-world-profile-icons" role="list" aria-label="选择猫咪档案">
            <button
              v-for="cat in catAgentDiaries"
              :key="`diary-icon-${cat.id}`"
              type="button"
              :class="['cat-world-profile-icon-button', { active: openCatDiaryId === cat.id }]"
              aria-haspopup="dialog"
              :aria-expanded="openCatDiaryId === cat.id"
              :aria-label="`查看${cat.displayLabel || cat.label}的今日档案`"
              aria-controls="cat-world-active-diary"
              @click="toggleCatDiary(cat)"
            >
              <span class="cat-world-profile-icon" :style="{ '--cat-icon-color': catIconColor(cat.id) }">
                <CatIcon :size="20" :stroke-width="2.5" aria-hidden="true" />
              </span>
              <strong>{{ cat.displayLabel || cat.label }}</strong>
              <small>{{ cat.currentSceneLabel }} · {{ cat.genderLabel }} · {{ cat.neglectCritical ? cat.neglectStatusLabel : cat.needsBath ? cat.hygieneStatusLabel : cat.dailyMoodLabel }}</small>
            </button>
          </div>
        </section>
        </div>
      </aside>
    </section>

    <div v-if="activeCatDiary" class="cat-world-modal-backdrop" @click.self="closeCatDiary">
      <section
        class="cat-world-profile-modal panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="cat-world-profile-modal-title"
      >
        <header class="cat-world-profile-modal-head">
          <div>
            <p class="section-kicker">Agent Diary</p>
            <h2 id="cat-world-profile-modal-title">{{ activeCatDiary.displayLabel || activeCatDiary.label }}的今日档案</h2>
          </div>
          <button
            class="cat-world-profile-modal-close"
            type="button"
            title="关闭档案"
            aria-label="关闭猫咪档案"
            autofocus
            @click="closeCatDiary"
          >
            <XIcon :size="22" :stroke-width="3" aria-hidden="true" />
          </button>
        </header>
      <article
        id="cat-world-active-diary"
        :key="`active-diary-${activeCatDiary.id}`"
        class="cat-world-agent-card cat-world-agent-card-expanded"
      >
        <div class="cat-world-cat-location-summary">
          <span><MapPinIcon :size="17" :stroke-width="2.7" aria-hidden="true" />现在位于 <strong>{{ activeCatDiary.currentSceneLabel }}</strong></span>
          <span>喜欢区域 <strong>{{ activeCatDiary.favoriteSceneLabel }}</strong></span>
          <button
            v-if="activeCatDiary.currentSceneId !== currentScene.id"
            type="button"
            :disabled="busyItemId === activeCatDiary.id"
            @click="bringCatToCurrentScene(activeCatDiary)"
          >
            <MoveRightIcon :size="16" :stroke-width="2.7" aria-hidden="true" />带到{{ currentScene.label }}
          </button>
          <em v-else>正在当前区域活动</em>
        </div>
        <header>
          <span>{{ activeCatDiary.displayLabel || activeCatDiary.label }}</span>
          <strong>{{ activeCatDiary.dailyMoodLabel }}</strong>
        </header>
        <p>{{ activeCatDiary.behaviorLabel }} · {{ activeCatDiary.routineLabel }}</p>
        <p class="cat-world-agent-goal">{{ activeCatDiary.goalLabel }} · {{ activeCatDiary.goalMessage }}</p>
        <p :class="['cat-world-agent-need', `need-${activeCatDiary.needStatus}`]">
          <strong>{{ activeCatDiary.needLabel }}</strong>
          <span>{{ activeCatDiary.needActionLabel }}</span>
          <em>{{ activeCatDiary.needMessage }}</em>
        </p>
        <p v-if="activeCatDiary.careTip" class="cat-world-agent-care">{{ activeCatDiary.careTip }}</p>
        <p v-if="activeCatDiary.voiceLine" class="cat-world-agent-voice">{{ activeCatDiary.voiceLine }}</p>
        <div class="cat-world-agent-meter-row" aria-label="猫咪 agent 参数">
          <span class="cat-world-agent-meter energy">体力<i><b :style="{ width: `${activeCatDiary.energyScore}%` }"></b></i></span>
          <span class="cat-world-agent-meter mood">心情<i><b :style="{ width: `${activeCatDiary.moodScore}%` }"></b></i></span>
          <span class="cat-world-agent-meter trust">信任<i><b :style="{ width: `${activeCatDiary.bondScore}%` }"></b></i></span>
          <span class="cat-world-agent-meter focus">专注<i><b :style="{ width: `${activeCatDiary.attention}%` }"></b></i></span>
          <span class="cat-world-agent-meter curious">好奇<i><b :style="{ width: `${activeCatDiary.curiosity}%` }"></b></i></span>
          <span class="cat-world-agent-meter stamina">耐力<i><b :style="{ width: `${activeCatDiary.stamina}%` }"></b></i></span>
          <span class="cat-world-agent-meter activity">活跃<i><b :style="{ width: `${activeCatDiary.activityBias}%` }"></b></i></span>
          <span class="cat-world-agent-meter social">黏人<i><b :style="{ width: `${activeCatDiary.socialNeed}%` }"></b></i></span>
          <span class="cat-world-agent-meter mischief">捣蛋<i><b :style="{ width: `${activeCatDiary.mischief}%` }"></b></i></span>
          <span class="cat-world-agent-meter clean">爱干净<i><b :style="{ width: `${activeCatDiary.cleanliness}%` }"></b></i></span>
        </div>
        <div :class="['cat-world-care-alert', { critical: activeCatDiary.neglectCritical }]">
          <strong>照护安全：{{ activeCatDiary.neglectStatusLabel }}</strong>
          <span>{{ activeCatDiary.neglectCountdownLabel }}</span>
          <em>{{ activeCatDiary.neglect.message }}</em>
        </div>
        <div v-if="activeCatDiary.needsBath" class="cat-world-bath-action">
          <div>
            <strong>毛发状态：{{ activeCatDiary.hygieneStatusLabel }}</strong>
            <span>{{ activeCatDiary.bathScheduleLabel }}</span>
          </div>
          <button
            v-if="activeCatDiary.bathKitCount"
            type="button"
            :disabled="busyItemId === 'cat-bath-kit'"
            @click="useConsumable(shopById['cat-bath-kit'])"
          >
            {{ busyItemId === 'cat-bath-kit' ? "洗澡中..." : `使用泡泡浴套装 (${activeCatDiary.bathKitCount})` }}
          </button>
          <small v-else>背包里没有泡泡浴套装，请到消耗品商店购买。</small>
        </div>
        <dl class="cat-world-agent-facts">
          <div><dt>个体档案</dt><dd>{{ activeCatDiary.genderLabel }} · {{ activeCatDiary.patternLabel }} · {{ activeCatDiary.featureLabel }}</dd></div>
          <div><dt>作息</dt><dd>{{ activeCatDiary.sleepLabel }}</dd></div>
          <div><dt>消耗</dt><dd>{{ activeCatDiary.decayLabel }}</dd></div>
          <div><dt>亲密</dt><dd>{{ activeCatDiary.bondLabel }} · {{ activeCatDiary.bondDetailLabel }}</dd></div>
          <div><dt>今日参数</dt><dd>{{ activeCatDiary.personaLabel }} · {{ activeCatDiary.dailyProfileLabel || "状态稳定" }}</dd></div>
          <div><dt>今日愿望</dt><dd>{{ activeCatDiary.dailyWish || "想安静陪你学习" }}</dd></div>
          <div><dt>相处方式</dt><dd>{{ activeCatDiary.socialStyleLabel }}</dd></div>
          <div><dt>玩耍倾向</dt><dd>{{ activeCatDiary.playStyleLabel }}</dd></div>
          <div><dt>照顾偏好</dt><dd>{{ activeCatDiary.carePreferenceLabel || "保持房间稳定整洁" }}</dd></div>
          <div><dt>卫生性格</dt><dd>{{ activeCatDiary.cleanlinessLabel }} · {{ activeCatDiary.cleanliness }}/100</dd></div>
          <div><dt>洗澡周期</dt><dd>每 {{ activeCatDiary.bathIntervalDays }} 天 · {{ activeCatDiary.bathScheduleLabel }}</dd></div>
          <div><dt>离家风险</dt><dd>{{ activeCatDiary.neglectCountdownLabel }}</dd></div>
          <div><dt>当前需求</dt><dd>{{ activeCatDiary.needLabel }} · {{ activeCatDiary.needActionLabel }}</dd></div>
          <div><dt>减耗</dt><dd>{{ activeCatDiary.comfortLabel }}</dd></div>
          <div><dt>偏好</dt><dd>{{ activeCatDiary.favoriteItemLabel }}</dd></div>
          <div><dt>家具加成</dt><dd>{{ activeCatDiary.activeFavoriteLabel }}</dd></div>
          <div><dt>互动</dt><dd>{{ activeCatDiary.countsLabel }}</dd></div>
          <div><dt>破坏风险</dt><dd>{{ activeCatDiary.damageRiskLabel }}</dd></div>
        </dl>
        <div v-if="activeCatDiary.hourlyHistory.length" class="cat-world-agent-hourly">
          <b>小时记录</b>
          <span v-for="row in activeCatDiary.hourlyHistory" :key="`${activeCatDiary.id}-${row.time}-${row.label}`">
            {{ row.time }} · {{ row.label }} · 体力 {{ signedHourlyValue(row.energyDelta) }} / 心情 {{ signedHourlyValue(row.moodDelta) }}
            <small>现在 {{ row.energyScore }}/{{ row.moodScore }}{{ row.hours > 1 ? ` · ${row.hours} 小时汇总` : "" }}</small>
          </span>
        </div>
        <small>{{ activeCatDiary.damageLabel }}</small>
        <em v-if="activeCatDiary.latestEvent">{{ activeCatDiary.latestEvent.time }} · {{ activeCatDiary.latestEvent.message }}</em>
      </article>
      </section>
    </div>

    <section
      v-show="activeWorldView === 'shop'"
      id="cat-world-view-shop"
      class="cat-world-market panel"
      role="tabpanel"
      aria-labelledby="cat-world-view-shop-tab"
    >
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

      <div class="cat-world-shop-grid">
        <article v-for="item in selectedItems" :key="item.id" class="cat-world-shop-card">
          <div>
            <div class="cat-world-shop-title">
              <CatWorldProductIcon :item="item" />
              <div>
                <span>{{ item.englishName }}</span>
                <h3>{{ item.label }}</h3>
              </div>
            </div>
            <div v-if="item.category === 'food'" class="cat-world-food-tags">
              <span :class="{ specialty: item.foodType === 'specialty' }">{{ foodTypeLabel(item) }}</span>
              <span v-if="item.foodType === 'specialty' && item.favoriteCatLabel" class="favorite">
                {{ item.favoriteCatLabel }}专属 +{{ foodFavoriteBonusPercent(item) }}%
              </span>
              <span>基础体力 +{{ item.catEnergy }}</span>
            </div>
            <div v-else-if="item.category === 'consumable'" class="cat-world-food-tags cat-world-consumable-tags">
              <span>一次性</span>
              <span v-if="item.useType === 'litter-prevent'">点击放置</span>
              <span v-else-if="item.useType === 'litter-clean'">点击猫屎使用</span>
              <span v-else-if="item.useType === 'cat-rename'">选择猫咪改名</span>
              <span v-else-if="item.useType === 'cat-bath'">当前档案猫咪使用</span>
              <span v-else-if="item.useType === 'repair-tool'">维修时自动消耗</span>
              <span v-else>点击背包使用</span>
            </div>
            <div v-else-if="item.limited" class="cat-world-food-tags cat-world-limited-gift-tags">
              <span>限定礼物</span>
              <span>账号限购 {{ item.maxOwned || 1 }} 件</span>
              <span>全站剩余 {{ item.remainingStock || 0 }}</span>
            </div>
            <div v-else-if="item.category === 'blind-box'" class="cat-world-food-tags cat-world-blind-box-tags">
              <span>{{ item.region }}地区</span>
              <span>{{ item.issue }}</span>
              <span>{{ currentBlindRarityLabel }}</span>
            </div>
            <div v-else-if="item.category === 'handbook'" class="cat-world-food-tags cat-world-handbook-tags">
              <span>永久道具</span>
              <span>{{ item.handbookType === 'cats' ? '猫咪卡册' : '食物图鉴' }}</span>
            </div>
            <div v-else-if="item.category === 'cat'" class="cat-world-food-tags cat-world-cat-draw-tags">
              <span>公猫 {{ gameSettings.genderDrawWeights?.malePercent ?? 50 }}%</span>
              <span>母猫 {{ gameSettings.genderDrawWeights?.femalePercent ?? 50 }}%</span>
              <span>随机花纹</span>
              <span>随机特点</span>
              <span>随机个性</span>
            </div>
            <p>{{ item.description }}</p>
          </div>
          <div class="cat-world-shop-meta">
            <strong>{{ item.cost }} 能量</strong>
            <em v-if="item.hasCustomCost">后台价 · 默认 {{ item.defaultCost }}</em>
            <span v-if="item.category === 'cat' && ownsCat(item.id)">
              已领养 {{ catProfileCount(item.id) }} 只
            </span>
            <span v-else-if="item.category === 'cat' && lostCats[item.id]">已离家 · 可重新领养</span>
            <span v-else-if="item.category === 'color' && itemCount(item.id)">
              {{ colorApplied(item) ? "已应用" : "已解锁" }}
            </span>
            <span v-else-if="item.category === 'color' && item.targetDecorLabel">用于 {{ item.targetDecorLabel }}</span>
            <span v-else-if="item.category === 'blind-box'">全站剩余 {{ item.remainingStock || 0 }}</span>
            <span v-else-if="item.limited">全站剩余 {{ item.remainingStock || 0 }}</span>
            <span v-else-if="item.category === 'handbook' && itemCount(item.id)">已永久解锁</span>
            <span v-else-if="item.category !== 'cat' && itemCount(item.id)">已有 {{ itemCount(item.id) }}</span>
            <span v-else>心情 +{{ item.mood }}</span>
          </div>
          <p class="cat-world-cost-preview">{{ purchaseHint(item) }}</p>
          <button
            class="primary-action-button"
            type="button"
            :disabled="busyItemId === item.id || !shopItemActionAvailable(item) || (item.category === 'color' && colorApplied(item))"
            @click="handleShopItemAction(item)"
          >
            {{ purchaseButtonText(item) }}
          </button>
        </article>
      </div>
    </section>

    <div
      v-if="activeHandbook === 'cats' && ownsCatHandbook"
      class="cat-world-modal-backdrop"
      @click.self="activeHandbook = ''"
    >
    <section
      class="cat-world-handbook cat-world-handbook-modal panel"
      role="dialog"
      aria-modal="true"
      aria-labelledby="cat-collection-title"
    >
      <header class="cat-world-handbook-head">
        <div>
          <p class="section-kicker">Collection</p>
          <h2 id="cat-collection-title">猫咪收集手册</h2>
        </div>
        <div class="cat-world-handbook-actions">
          <span>{{ catCollectionCatalog.ownedCount }} / {{ catCollectionCatalog.totalCount }} 只猫咪</span>
          <button class="secondary-button compact-button" type="button" aria-label="关闭猫咪收集手册" @click="activeHandbook = ''">
            <XIcon :size="18" aria-hidden="true" />
          </button>
        </div>
      </header>
      <div class="cat-world-atlas-layout">
        <section class="cat-world-atlas-map-panel" aria-labelledby="cat-world-atlas-map-title">
          <header>
            <div>
              <strong id="cat-world-atlas-map-title">世界猫咪地图</strong>
              <small>点击地区，查看当地可以收集的猫咪。</small>
            </div>
            <span>{{ catCollectionCatalog.sections.length }} 个地区</span>
          </header>
          <div class="cat-world-atlas-map" role="tablist" aria-label="猫咪收藏地区地图">
            <img :src="'/static/cat-world/cat-collection-world-map.png'" alt="" aria-hidden="true" />
            <button
              v-for="(section, index) in catCollectionCatalog.sections"
              :key="section.key"
              :class="['cat-world-atlas-region', { active: activeCollectionSection.key === section.key }]"
              :style="collectionRegionMeta(section, index).style"
              :data-region="section.region"
              type="button"
              role="tab"
              :aria-selected="activeCollectionSection.key === section.key"
              :aria-label="`${section.region}，已收集 ${section.ownedCount} / ${section.totalCount}`"
              @click="selectCollectionRegion(section)"
            >
              <strong>{{ collectionRegionMeta(section, index).shortLabel }}</strong>
              <small>{{ section.ownedCount }}/{{ section.totalCount }}</small>
            </button>
          </div>
          <p>地图上的数字是该地区已收集数量；新限定地区会继续出现在这里。</p>
        </section>

        <article v-if="activeCollectionSection.key" class="cat-world-series-album cat-world-atlas-region-panel">
          <header>
            <div>
              <strong>{{ activeCollectionSection.label }}</strong>
              <small>{{ activeCollectionSection.description }}</small>
            </div>
            <div class="cat-world-collection-progress">
              <span v-if="activeCollectionSection.badge?.unlocked" class="cat-world-collection-badge">
                <AwardIcon :size="16" :stroke-width="2.6" aria-hidden="true" />
                {{ activeCollectionSection.badge.label }}
              </span>
              <span v-else>{{ activeCollectionSection.ownedCount }} / {{ activeCollectionSection.totalCount }} 已收集</span>
            </div>
          </header>
          <div class="cat-world-atlas-cat-tabs" role="tablist" :aria-label="`${activeCollectionSection.region}猫咪种类`">
            <button
              v-for="cat in activeCollectionSection.cats"
              :key="cat.id"
              :class="{ active: activeCollectionCat.id === cat.id, owned: cat.owned }"
              type="button"
              role="tab"
              :aria-selected="activeCollectionCat.id === cat.id"
              @click="selectCollectionCat(cat)"
            >
              <span class="cat-world-atlas-cat-icon" :style="{ '--collection-color': catIconColor(cat.id) }">
                <strong v-if="cat.limited && !cat.owned">?</strong>
                <CatIcon v-else :size="24" :stroke-width="2.4" aria-hidden="true" />
              </span>
              <span>
                <strong>{{ cat.label }}</strong>
                <small>{{ cat.rarity }} · {{ cat.owned ? "已收集" : "未收集" }}</small>
              </span>
            </button>
          </div>
          <article
            v-if="activeCollectionCat.id"
            :class="['cat-world-collection-card', 'cat-world-collection-card-featured', `rarity-${String(activeCollectionCat.rarity || 'r').toLowerCase()}`, { owned: activeCollectionCat.owned }]"
          >
            <div
              :class="['cat-world-collection-art', { mystery: activeCollectionCat.limited && !activeCollectionCat.owned }]"
              :style="{ '--collection-color': catIconColor(activeCollectionCat.id) }"
            >
              <strong v-if="activeCollectionCat.limited && !activeCollectionCat.owned" class="cat-world-mystery-mark">?</strong>
              <CatIcon v-else :size="48" :stroke-width="2.2" aria-hidden="true" />
              <b>{{ activeCollectionCat.limited && !activeCollectionCat.owned ? "?" : activeCollectionCat.rarity }}</b>
            </div>
            <span>{{ activeCollectionCat.collectionTag }}</span>
            <h3>{{ activeCollectionCat.label }}</h3>
            <p>{{ activeCollectionCat.description }}</p>
            <small v-if="activeCollectionCat.owned">已收集</small>
            <small v-else-if="activeCollectionCat.limited">
              未收集 · {{ activeCollectionCat.acquisitionHint }} · 初始概率 {{ activeCollectionCat.oddsPercent }}%
            </small>
            <small v-else>未收集 · {{ activeCollectionCat.acquisitionHint }}</small>
          </article>
        </article>
      </div>
    </section>
    </div>

    <div
      v-if="activeHandbook === 'food' && ownsFoodHandbook"
      class="cat-world-modal-backdrop"
      @click.self="activeHandbook = ''"
    >
    <section
      class="cat-world-handbook cat-world-handbook-modal panel"
      role="dialog"
      aria-modal="true"
      aria-labelledby="cat-food-handbook-title"
    >
      <header class="cat-world-handbook-head">
        <div>
          <p class="section-kicker">Food Guide</p>
          <h2 id="cat-food-handbook-title">猫咪食物手册</h2>
        </div>
        <div class="cat-world-handbook-actions">
          <span>{{ foodHandbookItems.length }} 种食物</span>
          <button class="secondary-button compact-button" type="button" aria-label="关闭猫咪食物手册" @click="activeHandbook = ''">
            <XIcon :size="18" aria-hidden="true" />
          </button>
        </div>
      </header>
      <div class="cat-world-food-album">
        <article v-for="food in foodHandbookItems" :key="food.id" class="cat-world-food-guide-card">
          <span>{{ foodTypeLabel(food) }}</span>
          <h3>{{ food.label }}</h3>
          <p>{{ food.description }}</p>
          <dl>
            <div><dt>基础体力</dt><dd>+{{ food.catEnergy || 0 }}</dd></div>
            <div><dt>基础心情</dt><dd>+{{ food.mood || 0 }}</dd></div>
            <div><dt>偏爱猫咪</dt><dd>{{ food.favoriteCatLabel || "通用" }}</dd></div>
            <div><dt>背包数量</dt><dd>{{ itemCount(food.id) }}</dd></div>
          </dl>
        </article>
      </div>
    </section>
    </div>

    <section
      v-show="activeWorldView === 'cats'"
      id="cat-world-view-cats"
      class="cat-world-cats panel"
      role="tabpanel"
      aria-labelledby="cat-world-view-cats-tab"
    >
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
          :class="[
            'cat-world-cat-chip',
            {
              active: state.selectedCatProfile === cat.id,
              locked: !cat.owned,
              'rarity-frame-sr': cat.rarityBadge.tone === 'sr',
              'rarity-frame-ssr': cat.rarityBadge.tone === 'ssr',
            },
          ]"
          :disabled="!cat.owned || busyItemId === cat.id"
          @click="handleCatCardClick(cat)"
        >
          <div class="cat-world-cat-chip-head">
            <span>{{ cat.owned ? `${cat.genderLabel || "性别待定"} · ${cat.breedLabel || cat.label} · ${cat.profileCode || cat.rarity || cat.englishName}` : cat.escaped ? "已离家" : "未解锁" }}</span>
            <strong>{{ cat.displayLabel || cat.label }}</strong>
            <div class="cat-world-cat-identity">
              <figure
                :class="[
                  'cat-world-cat-portrait',
                  `pattern-${cat.portrait.pattern}`,
                  `feature-${cat.portrait.feature}`,
                ]"
                :style="cat.portrait.style"
                aria-hidden="true"
              >
                <i class="cat-world-cat-portrait-ear left"></i>
                <i class="cat-world-cat-portrait-ear right"></i>
                <i class="cat-world-cat-portrait-face">
                  <i class="cat-world-cat-portrait-eye left"></i>
                  <i class="cat-world-cat-portrait-eye right"></i>
                  <i class="cat-world-cat-portrait-nose"></i>
                </i>
              </figure>
              <b
                :class="['cat-world-cat-rarity', `rarity-${cat.rarityBadge.tone}`]"
                :aria-label="`稀有度 ${cat.rarityBadge.label}`"
              >
                {{ cat.rarityBadge.label }}
              </b>
            </div>
          </div>
          <small>{{ cat.owned ? `${cat.patternLabel || "原生花纹"} · ${cat.featureLabel || "普通特点"} · 个性：${cat.personality || cat.englishName}` : cat.escaped ? `${cat.lostInfo.escapeLabel}，请去商店重新领养` : cat.description }}</small>
          <div v-if="cat.owned" class="cat-world-cat-agent-status">
            <p class="cat-world-cat-card-location">
              <b><MapPinIcon :size="14" :stroke-width="2.6" aria-hidden="true" />{{ cat.currentSceneLabel }}</b>
              <em>喜欢 {{ cat.favoriteSceneLabel }}</em>
            </p>
            <p>
              <b>{{ cat.dailyMoodLabel }}</b>
              <em>{{ cat.behaviorLabel }}</em>
            </p>
            <p class="cat-world-cat-agent-need">
              <b>{{ cat.needLabel || "状态稳定" }}</b>
              <em>{{ cat.needActionLabel || "自由活动" }}</em>
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
      </div>
    </div>

    <div v-if="renameModalOpen" class="cat-world-modal-backdrop" @click.self="closeRenameModal">
      <section class="cat-world-rename-modal panel" role="dialog" aria-modal="true" aria-labelledby="cat-world-rename-title">
        <header>
          <div>
            <p class="section-kicker">Rename Card</p>
            <h2 id="cat-world-rename-title">给猫咪改名</h2>
          </div>
          <button class="secondary-button compact-button" type="button" aria-label="关闭" :disabled="renameBusy" @click="closeRenameModal">
            <XIcon :size="18" aria-hidden="true" />
          </button>
        </header>
        <div class="cat-world-rename-targets" role="list" aria-label="选择要改名的猫咪">
          <button
            v-for="cat in catProfiles"
            :key="cat.id"
            type="button"
            :class="{ active: renameTargetCatId === cat.id }"
            :disabled="renameBusy"
            @click="chooseRenameTarget(cat)"
          >
            <CatIcon :size="22" :stroke-width="2.6" aria-hidden="true" />
            <span>{{ cat.displayLabel || cat.label }}</span>
          </button>
        </div>
        <label class="cat-world-rename-input">
          <span>新名字</span>
          <input
            ref="renameInputRef"
            v-model="renameDraft"
            type="text"
            maxlength="12"
            autocomplete="off"
            placeholder="输入 1 至 12 个字符"
            :disabled="renameBusy"
            @keydown.enter.prevent="submitCatRename"
          />
        </label>
        <p>本次会消耗 1 张改名卡；品种、个性、花纹和成长状态不会改变。</p>
        <div class="cat-world-modal-actions">
          <button class="secondary-button" type="button" :disabled="renameBusy" @click="closeRenameModal">取消</button>
          <button class="primary-action-button" type="button" :disabled="renameBusy || !renameDraft.trim()" @click="submitCatRename">
            {{ renameBusy ? "改名中..." : "确认改名" }}
          </button>
        </div>
      </section>
    </div>

    <div v-if="scenePurchaseTarget" class="cat-world-modal-backdrop" @click.self="scenePurchaseTarget = null">
      <section class="cat-world-scene-purchase-modal panel" role="dialog" aria-modal="true" aria-labelledby="cat-world-scene-purchase-title">
        <header>
          <div>
            <p class="section-kicker">New Scene</p>
            <h2 id="cat-world-scene-purchase-title">解锁{{ scenePurchaseTarget.label }}</h2>
          </div>
          <button class="secondary-button compact-button" type="button" aria-label="关闭" @click="scenePurchaseTarget = null">
            <XIcon :size="18" aria-hidden="true" />
          </button>
        </header>
        <p>{{ scenePurchaseTarget.description }}</p>
        <div class="cat-world-scene-purchase-summary">
          <span>场景价格</span>
          <strong>{{ Number(scenePurchaseTarget.purchaseCost || 0).toLocaleString() }} 能量</strong>
          <small>购买后剩余 {{ Math.max(Number(energy.available || 0) - Number(scenePurchaseTarget.purchaseCost || 0), 0).toLocaleString() }}</small>
        </div>
        <div class="cat-world-modal-actions">
          <button class="secondary-button" type="button" @click="scenePurchaseTarget = null">取消</button>
          <button
            class="primary-action-button"
            type="button"
            :disabled="Boolean(busySceneId) || Number(energy.available || 0) < Number(scenePurchaseTarget.purchaseCost || 0)"
            @click="purchaseScene"
          >
            {{ busySceneId ? "解锁中..." : Number(energy.available || 0) >= Number(scenePurchaseTarget.purchaseCost || 0) ? "确认解锁" : "能量不足" }}
          </button>
        </div>
      </section>
    </div>

    <div v-if="openedBlindBox" class="cat-world-modal-backdrop" @click.self="openedBlindBox = null">
      <section class="cat-world-blind-result-modal panel" role="dialog" aria-modal="true" aria-labelledby="cat-world-blind-result-title">
        <button class="secondary-button compact-button cat-world-modal-close" type="button" aria-label="关闭" @click="openedBlindBox = null">
          <XIcon :size="18" aria-hidden="true" />
        </button>
        <p class="section-kicker">{{ openedBlindBox.seriesLabel }}</p>
        <div class="cat-world-blind-result-art" :style="{ '--collection-color': catIconColor(openedBlindBox.cat.id) }">
          <CatIcon :size="72" :stroke-width="2" aria-hidden="true" />
          <b>{{ openedBlindBox.cat.rarity }}</b>
        </div>
        <h2 id="cat-world-blind-result-title">{{ openedBlindBox.cat.label }}</h2>
        <p v-if="openedBlindBox.profile" class="cat-world-blind-profile">
          {{ openedBlindBox.profile.genderLabel }} · {{ openedBlindBox.profile.patternLabel }} · {{ openedBlindBox.profile.featureLabel }}
        </p>
        <p>{{ openedBlindBox.cat.description }}</p>
        <button class="primary-action-button" type="button" @click="openedBlindBox = null">收入猫咪卡册</button>
      </section>
    </div>

    <div v-if="energyModalOpen" class="cat-world-modal-backdrop" @click.self="energyModalOpen = false">
      <section class="cat-world-energy-modal panel" role="dialog" aria-modal="true" aria-labelledby="cat-world-energy-title">
        <header>
          <div>
            <p class="section-kicker">Energy</p>
            <h2 id="cat-world-energy-title">学习产能</h2>
            <p>这里只显示今天获得的能量，并用额外奖励鼓励少量开始、输入输出结合和连续学习。</p>
          </div>
          <button class="secondary-button compact-button" type="button" @click="energyModalOpen = false">关闭</button>
        </header>
        <div class="cat-world-modal-summary">
          <span>可用 {{ energy.available || 0 }}</span>
          <span>今日 +{{ todayEnergy }}</span>
          <span>累计 {{ energy.earned || 0 }}</span>
          <span>已用 {{ energy.spent || 0 }}</span>
        </div>
        <div v-if="todayEnergySources.length" class="cat-world-energy-list">
          <div v-for="source in todayEnergySources" :key="source.key" class="cat-world-energy-row">
            <span>{{ source.label }}</span>
            <strong>{{ source.energy }}</strong>
            <small>{{ source.detail || `${source.value}${source.unit} x ${source.energyPerUnit}` }}</small>
          </div>
        </div>
        <p v-else class="cat-world-energy-empty">今天还没有获取猫咪能量，先完成 20 个拼写词开始今天的学习节奏。</p>
      </section>
    </div>
  </section>
</template>
