<script setup>
import WrongWordGroupCard from "../components/WrongWordGroupCard.vue";

defineProps([
  "data",
  "go"
]);
</script>

<template>
  <section class="word-grid">
    <WrongWordGroupCard
      v-for="group in data.groups"
      :key="group.date"
      :group="group"
      :go="go"
    />
    <div v-if="!data.groups.length" class="empty-state">生词本还是空的。</div>
  </section>
</template>
