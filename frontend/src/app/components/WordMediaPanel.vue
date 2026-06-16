<script setup>
defineProps({
  data: {
    type: Object,
    required: true,
  },
  imageCandidates: {
    type: Array,
    default: () => [],
  },
  fallbackLetter: {
    type: Function,
    required: true,
  },
  uploadWordImage: {
    type: Function,
    required: true,
  },
  findImages: {
    type: Function,
    required: true,
  },
  chooseNetworkImage: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <div class="detail-media-panel">
    <div class="detail-media">
      <span v-if="data.navigation.index" class="word-index-badge">#{{ data.navigation.index }}</span>
      <img v-if="data.word.image_url" :src="data.word.image_url" :alt="data.word.word">
      <div v-else class="image-fallback large">{{ fallbackLetter(data.word) }}</div>
    </div>

    <div v-if="data.can_edit" class="image-replace-form">
      <label>
        替换图片
        <input type="file" accept="image/*" @change="$event.target.files[0] && uploadWordImage($event.target.files[0])">
      </label>
      <button type="button" class="secondary-button" @click="findImages">网络找图</button>
      <span v-if="data.word.image_locked" class="lock-badge">已锁定</span>
    </div>

    <div v-if="imageCandidates.length" class="image-picker-grid inline-image-grid">
      <button
        v-for="(item, index) in imageCandidates"
        :key="item.url"
        type="button"
        class="image-picker-option"
        @click="chooseNetworkImage(item.url)"
      >
        <img :src="item.url" :alt="`候选图 ${index + 1}`">
        <span>{{ item.source || "网络图片" }}</span>
      </button>
    </div>
  </div>
</template>
