<script setup>
import { ref } from "vue";
import { Eye, EyeOff } from "lucide-vue-next";

const showPassword = ref(false);

defineProps({
  deleteListState: {
    type: Object,
    required: true,
  },
  deleteList: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <div class="delete-list-form" role="group" aria-label="删除单词表">
    <label class="delete-password-field">
      <input
        v-model="deleteListState.password"
        :type="showPassword ? 'text' : 'password'"
        placeholder="删除密码"
        required
      >
    </label>
    <button
      class="password-toggle-button"
      type="button"
      :aria-label="showPassword ? '隐藏删除密码' : '显示删除密码'"
      :title="showPassword ? '隐藏删除密码' : '显示删除密码'"
      @click="showPassword = !showPassword"
    >
      <EyeOff v-if="showPassword" class="password-toggle-icon" :size="24" aria-hidden="true" />
      <Eye v-else class="password-toggle-icon" :size="24" aria-hidden="true" />
    </button>
    <button class="danger-button" type="button" @click="deleteList">删除</button>
  </div>
</template>
