<script setup>
import { computed } from 'vue';
import ChallengeApp from '../../challenge/ChallengeApp.vue';

const props = defineProps({
  route: {
    type: Object,
    required: true,
  },
});

const wordListId = computed(() => Number(props.route.params.id || 0));
</script>

<template>
  <div id="speakeasy-challenge-app" :data-word-list-id="route.params.id">
    <ChallengeApp :key="wordListId" :word-list-id="wordListId" />
  </div>
</template>
