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
  { key: "cat", label: "名猫" },
];

const energy = computed(() => payload.value.energy || {});
const state = computed(() => payload.value.state || {});
const inventory = computed(() => state.value.inventory || {});
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

function ownsCat(catId) {
  return ownedCats.value.includes(catId);
}

function canAfford(item) {
  return Number(energy.value.available || 0) >= Number(item.cost || 0);
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
            <h2>像素猫小屋</h2>
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
          <div v-if="inventory['sun-window']" class="cat-world-window"></div>
          <div v-if="inventory['book-shelf']" class="cat-world-shelf">
            <span></span><span></span><span></span><span></span>
          </div>
          <div v-if="inventory['cloud-rug']" class="cat-world-rug"></div>
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
            <span v-if="item.category === 'cat' && ownsCat(item.id)">
              {{ state.selectedCat === item.id ? "正在陪读" : "已拥有" }}
            </span>
            <span v-else-if="item.category !== 'cat' && itemCount(item.id)">已有 {{ itemCount(item.id) }}</span>
            <span v-else>心情 +{{ item.mood }}</span>
          </div>
          <button
            class="primary-action-button"
            type="button"
            :disabled="busyItemId === item.id || (item.category === 'cat' && state.selectedCat === item.id) || (item.category !== 'cat' && !canAfford(item)) || (item.category === 'cat' && !ownsCat(item.id) && !canAfford(item))"
            @click="purchase(item)"
          >
            <template v-if="busyItemId === item.id">处理中...</template>
            <template v-else-if="item.category === 'cat' && ownsCat(item.id) && state.selectedCat !== item.id">设为主猫</template>
            <template v-else-if="item.category === 'cat' && ownsCat(item.id)">已选择</template>
            <template v-else-if="canAfford(item)">购买</template>
            <template v-else>能量不足</template>
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
