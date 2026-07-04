<script setup>
defineProps({
  canEdit: {
    type: Boolean,
    required: true,
  },
  refreshWord: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <div class="detail-heading-actions">
    <button v-if="canEdit" type="button" @click="refreshWord">补全当前词</button>
  </div>
</template>
