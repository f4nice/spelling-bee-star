<script setup>
import NewspaperHero from "../components/NewspaperHero.vue";
import NewspaperSection from "../components/NewspaperSection.vue";

defineProps([
  "data",
  "go"
]);
</script>

<template>
  <NewspaperHero :source-url="data.source_url" />
  <section class="newspaper-layout">
    <NewspaperSection
      v-for="section in data.sections"
      :key="section.key"
      :section="section"
      :go="go"
    />
  </section>
</template>
