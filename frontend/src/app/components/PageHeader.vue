<script setup>
defineProps({
  routeTitle: {
    type: String,
    required: true,
  },
});
</script>

<template>
  <section class="panel app-page-heading">
    <div>
      <p class="section-kicker">SpeakEasy</p>
      <h1>{{ routeTitle }}</h1>
    </div>
  </section>
</template>
