<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";
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
const pettedCatId = ref("");
const focusedCatId = ref("");

const catReactionTexts = [
  "收到摸摸指令，开心值上升",
  "启动陪读模式，正在靠近你",
  "尾巴雷达晃了晃，发现新单词",
  "想法缓存刷新，准备继续陪你学",
];
let catReactionTimer = 0;

watch(
  () => props.data,
  (nextData) => {
    payload.value = nextData || {};
  },
);

onBeforeUnmount(() => {
  window.clearTimeout(catReactionTimer);
});

const categories = [
  { key: "food", label: "猫粮" },
  { key: "toy", label: "玩具" },
  { key: "decor", label: "装修" },
  { key: "color", label: "配色" },
  { key: "cat", label: "名猫" },
];

const energy = computed(() => payload.value.energy || {});
const state = computed(() => payload.value.state || {});
const inventory = computed(() => state.value.inventory || {});
const roomStyles = computed(() => state.value.roomStyles || {});
const styleOptions = computed(() => state.value.styleOptions || {});
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
const focusedCatThought = computed(() => {
  const thoughts = focusedCat.value.thoughts || [];
  if (!thoughts.length) {
    return "正在观察你的学习节奏。";
  }
  return thoughts[catPetSequence.value % thoughts.length];
});

function replacePayload(nextPayload) {
  if (nextPayload?.energy && nextPayload?.state) {
    payload.value = nextPayload;
  }
}

function itemCount(itemId) {
  return Number(inventory.value[itemId] || 0);
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
    return "已拥有，不会重复扣分";
  }
  if (item.category === "color" && itemCount(item.id) > 0) {
    return colorApplied(item) ? "当前正在使用" : "已拥有，点击应用";
  }
  const remaining = Math.max(Number(energy.value.available || 0) - Number(item.cost || 0), 0);
  return `将扣 ${item.cost} 积分 · 购买后剩余 ${remaining}`;
}

function purchaseButtonText(item) {
  if (busyItemId.value === item.id) return "处理中...";
  if (item.category === "cat" && ownsCat(item.id) && state.value.selectedCat !== item.id) return "设为主猫";
  if (item.category === "cat" && ownsCat(item.id)) return "已选择";
  if (item.category === "color" && !targetDecorOwned(item)) return "先买家具";
  if (item.category === "color" && colorApplied(item)) return "已应用";
  if (item.category === "color" && itemCount(item.id) > 0) return "应用配色";
  if (isOneTimeOwned(item)) return "已拥有";
  return canAfford(item) ? `扣 ${item.cost} 积分购买` : "能量不足";
}

function petCat(cat = selectedCat.value) {
  const catLabel = cat?.label || "猫咪";
  const nextIndex = catPetSequence.value % catReactionTexts.length;
  focusedCatId.value = cat?.id || "";
  pettedCatId.value = cat?.id || "";
  catReaction.value = `${catLabel}: ${catReactionTexts[nextIndex]}`;
  catPetSequence.value += 1;
  window.clearTimeout(catReactionTimer);
  catReactionTimer = window.setTimeout(() => {
    catReaction.value = "";
    pettedCatId.value = "";
  }, 2200);
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
    notice.value = `${selectedCat.value.label || "猫咪"} 和 ${item.label} 玩了一会儿。`;
  } catch (error) {
    notice.value = error.message || "互动失败，请稍后再试。";
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
      <div class="cat-world-wallet" aria-label="猫咪世界能量">
        <span>可用能量</span>
        <strong>{{ energy.available || 0 }}</strong>
        <small>累计 {{ energy.earned || 0 }} · 已用 {{ energy.spent || 0 }}</small>
      </div>
    </section>

    <section class="cat-world-layout">
      <section class="cat-world-room-panel panel">
        <div class="cat-world-room-head">
          <div>
            <p class="section-kicker">Room</p>
            <h2>像素猫活动室</h2>
          </div>
          <div class="cat-world-mood">
            <span>{{ mood.label || "安静陪读" }}</span>
            <strong>{{ mood.score || 50 }}</strong>
          </div>
        </div>

        <div class="cat-world-ai-panel" aria-live="polite">
          <span>CAT-OS</span>
          <strong>{{ focusedCat.label || "猫咪" }} · {{ focusedCat.personality || "学习陪伴型" }}</strong>
          <p>{{ focusedCatThought }}</p>
        </div>

        <div class="cat-world-room" aria-label="猫咪房间场景">
          <button
            v-if="inventory['sun-window']"
            type="button"
            :class="['cat-world-window', 'cat-world-decor-item', `decor-tone-${decorTone('sun-window')}`]"
            :aria-label="`切换阳光窗台颜色，已解锁 ${styleOptions['sun-window']?.length || 1} 款`"
            @click="cycleDecorStyle('sun-window')"
          ></button>
          <button
            v-if="inventory['book-shelf']"
            type="button"
            :class="['cat-world-shelf', 'cat-world-decor-item', `decor-tone-${decorTone('book-shelf')}`]"
            :aria-label="`切换英文书架颜色，已解锁 ${styleOptions['book-shelf']?.length || 1} 款`"
            @click="cycleDecorStyle('book-shelf')"
          >
            <span></span><span></span><span></span><span></span>
          </button>
          <button
            v-if="inventory['cloud-rug']"
            type="button"
            :class="['cat-world-rug', 'cat-world-decor-item', `decor-tone-${decorTone('cloud-rug')}`]"
            :aria-label="`切换云朵地毯颜色，已解锁 ${styleOptions['cloud-rug']?.length || 1} 款`"
            @click="cycleDecorStyle('cloud-rug')"
          ></button>
          <button
            v-if="inventory['study-desk']"
            type="button"
            :class="['cat-world-desk', 'cat-world-decor-item', `decor-tone-${decorTone('study-desk')}`]"
            :aria-label="`切换英文书桌颜色，已解锁 ${styleOptions['study-desk']?.length || 1} 款`"
            @click="cycleDecorStyle('study-desk')"
          >
            <span class="cat-world-desk-book"></span>
            <span class="cat-world-desk-cup"></span>
          </button>
          <button
            v-if="inventory['reading-lamp']"
            type="button"
            :class="['cat-world-lamp', 'cat-world-decor-item', `decor-tone-${decorTone('reading-lamp')}`]"
            :aria-label="`切换阅读台灯颜色，已解锁 ${styleOptions['reading-lamp']?.length || 1} 款`"
            @click="cycleDecorStyle('reading-lamp')"
          >
            <span></span>
          </button>
          <button
            v-if="inventory['word-gallery']"
            type="button"
            :class="['cat-world-gallery', 'cat-world-decor-item', `decor-tone-${decorTone('word-gallery')}`]"
            :aria-label="`切换单词挂画颜色，已解锁 ${styleOptions['word-gallery']?.length || 1} 款`"
            @click="cycleDecorStyle('word-gallery')"
          >
            <span>ABC</span>
          </button>
          <div v-if="ownedFoodCount" class="cat-world-bowl"></div>
          <div v-if="inventory['scratch-board']" class="cat-world-scratcher"></div>
          <div v-if="inventory['feather-wand']" class="cat-world-wand"></div>
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
          <button
            v-for="(cat, index) in roomCats"
            :key="`${cat.id}-${catReaction && cat.id === pettedCatId ? catPetSequence : 0}`"
            type="button"
            :class="[
              'cat-world-cat-sprite',
              `cat-tone-${cat.id || 'mimi'}`,
              `cat-slot-${index % 5}`,
              { 'is-selected': state.selectedCat === cat.id, 'is-petted': catReaction && cat.id === pettedCatId },
            ]"
            :aria-label="`摸摸${cat.label || '猫咪'}`"
            @click="petCat(cat)"
          >
            <span class="cat-pixel-shadow"></span>
            <span class="cat-pixel-tail"></span>
            <span class="cat-pixel-body"></span>
            <span class="cat-pixel-head"></span>
            <span class="cat-pixel-ear cat-pixel-ear-left"></span>
            <span class="cat-pixel-ear cat-pixel-ear-right"></span>
            <span class="cat-pixel-eye cat-pixel-eye-left"></span>
            <span class="cat-pixel-eye cat-pixel-eye-right"></span>
            <span class="cat-pixel-nose"></span>
            <span class="cat-pixel-paw cat-pixel-paw-left"></span>
            <span class="cat-pixel-paw cat-pixel-paw-right"></span>
            <span v-if="state.selectedCat === cat.id" class="cat-pixel-marker">主</span>
            <span class="cat-pixel-label">{{ cat.label }}</span>
          </button>
        </div>

        <div class="cat-world-room-status">
          <span>已拥有装饰 {{ ownedDecor.length }}</span>
          <span>食物 {{ ownedFoodCount }}</span>
          <span>猫咪 {{ ownedCats.length }}</span>
          <span v-if="lastPlayLabel">刚刚玩过 {{ lastPlayLabel }}</span>
        </div>

        <div v-if="ownedToys.length" class="cat-world-play-row" aria-label="猫咪玩具">
          <button
            v-for="toy in ownedToys"
            :key="toy.id"
            class="secondary-button"
            type="button"
            :disabled="busyItemId === toy.id"
            @click="play(toy)"
          >
            {{ busyItemId === toy.id ? "互动中..." : `用${toy.label}逗猫` }}
          </button>
        </div>
      </section>

      <aside class="cat-world-ledger panel">
        <p class="section-kicker">Energy</p>
        <h2>学习产能</h2>
        <div class="cat-world-energy-list">
          <div v-for="source in energy.sources || []" :key="source.key" class="cat-world-energy-row">
            <span>{{ source.label }}</span>
            <strong>{{ source.energy }}</strong>
            <small>{{ source.value }}{{ source.unit }} x {{ source.energyPerUnit }}</small>
          </div>
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

    <section class="cat-world-cats panel">
      <div class="cat-world-market-head">
        <div>
          <p class="section-kicker">Cats</p>
          <h2>我的猫咪</h2>
        </div>
      </div>
      <div class="cat-world-cat-list">
        <button
          v-for="cat in cats"
          :key="cat.id"
          type="button"
          :class="['cat-world-cat-chip', { active: state.selectedCat === cat.id, locked: !ownsCat(cat.id) }]"
          :disabled="!ownsCat(cat.id) || busyItemId === cat.id"
          @click="selectCat(cat.id)"
        >
          <strong>{{ cat.label }}</strong>
          <span>{{ ownsCat(cat.id) ? cat.personality || cat.englishName : "未解锁" }}</span>
        </button>
      </div>
    </section>
  </section>
</template>
