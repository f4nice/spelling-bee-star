<script setup>
import { computed } from "vue";

const props = defineProps({
  value: {
    type: Object,
    required: true,
  },
});

const formattedValue = computed(() => JSON.stringify(props.value, null, 2));
</script>

<template>
  <pre class="booklearner-json">{{ formattedValue }}</pre>
</template>
