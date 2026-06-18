<script setup>
defineProps({
  go: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <section class="home-section-head">
    <div>
      <p class="section-kicker">Lists</p>
      <h2>我的单词表</h2>
    </div>
    <button class="ghost-button" type="button" @click="go('/lists')">全部单词表</button>
  </section>
</template>
