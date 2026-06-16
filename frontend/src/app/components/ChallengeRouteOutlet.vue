<script setup>
import ChallengeApp from '../../challenge/ChallengeApp.vue';

defineProps({
  route: {
    type: Object,
    required: true,
  },
});
</script>

<template>
  <div id="challenge-vue-app" :data-word-list-id="route.params.id">
    <ChallengeApp :word-list-id="route.params.id" />
  </div>
</template>
