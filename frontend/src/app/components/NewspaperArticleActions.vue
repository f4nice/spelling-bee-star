<script setup>
defineProps({
  go: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <div class="newspaper-article-actions">
    <button class="ghost-button" type="button" @click="go('/newspaper')">返回英文小报</button>
  </div>
</template>
