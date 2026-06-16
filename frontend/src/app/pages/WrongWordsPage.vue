<script setup>
defineProps([
  "data",
  "go"
]);
</script>

<template>
    <section class="word-grid"><article v-for="group in data.groups" :key="group.date" class="word-card list-card"><button class="list-card-link plain-card-button" type="button" @click="go(`/challenge-calendar/${group.date}`)"><div class="image-fallback">×</div><div class="word-card-body"><div class="word-card-title"><strong>{{ group.date }}</strong><span class="status failed">{{ group.count }} 词</span></div><p class="wrong-list-summary">错 {{ group.wrong_total }} 次</p></div></button></article><div v-if="!data.groups.length" class="empty-state">生词本还是空的。</div></section>
</template>
