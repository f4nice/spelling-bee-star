<script setup>
import { computed } from "vue";
import { normalizeVersionMatrix } from "../versionInfo.js";

const props = defineProps({
  version: {
    type: Object,
    default: null,
  },
});

const matrix = computed(() => normalizeVersionMatrix(props.version));
const modules = computed(() => matrix.value.modules || []);
</script>

<template>
  <section class="version-matrix" aria-label="版本矩阵">
    <div class="version-matrix-head">
      <span>版本矩阵</span>
      <strong>{{ matrix.version }}</strong>
    </div>
    <p class="version-release">{{ matrix.releaseName }}</p>
    <div v-if="modules.length" class="version-matrix-list">
      <div v-for="item in modules" :key="item.label" class="version-matrix-row">
        <span>{{ item.label }}</span>
        <strong>{{ item.version }}</strong>
        <em>{{ item.status }}</em>
      </div>
    </div>
    <p v-if="matrix.machineCode" class="version-machine">机器码 {{ matrix.machineCode }}</p>
  </section>
</template>
