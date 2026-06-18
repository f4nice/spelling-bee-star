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
    <button v-if="canEdit" type="button" @click="refreshWord">重新补全</button>
  </div>
</template>
