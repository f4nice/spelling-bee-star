<script setup>
import { computed } from "vue";
import {
  Bath,
  Bed,
  BookOpen,
  BrushCleaning,
  Cat,
  CircleDot,
  Cloud,
  ContactRound,
  CookingPot,
  Egg,
  Feather,
  Fish,
  Gift,
  Hammer,
  House,
  Image as ImageIcon,
  LampDesk,
  Laptop,
  Library,
  Milk,
  Moon,
  Package,
  PackageCheck,
  PackageOpen,
  Palette,
  RectangleHorizontal,
  Shovel,
  Soup,
  SprayCan,
  Sprout,
  Star,
  Sun,
  Trees,
  Waves,
} from "lucide-vue-next";
import { catWorldProductIconSpec } from "../catWorldProductIcons.js";

const props = defineProps({
  item: {
    type: Object,
    required: true,
  },
  compact: {
    type: Boolean,
    default: false,
  },
});

const ICONS = Object.freeze({
  bath: Bath,
  bed: Bed,
  "book-open": BookOpen,
  "brush-cleaning": BrushCleaning,
  cat: Cat,
  "circle-dot": CircleDot,
  cloud: Cloud,
  "contact-round": ContactRound,
  "cooking-pot": CookingPot,
  egg: Egg,
  feather: Feather,
  fish: Fish,
  gift: Gift,
  hammer: Hammer,
  house: House,
  image: ImageIcon,
  "lamp-desk": LampDesk,
  laptop: Laptop,
  library: Library,
  milk: Milk,
  moon: Moon,
  package: Package,
  "package-check": PackageCheck,
  "package-open": PackageOpen,
  palette: Palette,
  "rectangle-horizontal": RectangleHorizontal,
  shovel: Shovel,
  soup: Soup,
  "spray-can": SprayCan,
  sprout: Sprout,
  star: Star,
  sun: Sun,
  trees: Trees,
  waves: Waves,
});

const iconSpec = computed(() => catWorldProductIconSpec(props.item));
const iconComponent = computed(() => ICONS[iconSpec.value.icon] || Package);
const iconStyle = computed(() => ({
  "--product-icon-bg": iconSpec.value.background,
  "--product-icon-accent": iconSpec.value.accent,
  "--product-icon-detail": iconSpec.value.detail,
}));
</script>

<template>
  <span
    :class="['cat-world-product-icon', `is-${iconSpec.category}`, { compact }]"
    :style="iconStyle"
    :data-product-item="iconSpec.itemId"
    role="img"
    :aria-label="`${iconSpec.label}像素图标`"
  >
    <component :is="iconComponent" :size="compact ? 22 : 29" :stroke-width="3" aria-hidden="true" />
    <i aria-hidden="true"></i>
    <b aria-hidden="true"></b>
  </span>
</template>
