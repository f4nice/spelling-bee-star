<script setup>
defineProps({
  kicker: {
    type: String,
    default: "Create",
  },
  title: {
    type: String,
    default: "新建单词表",
  },
  description: {
    type: String,
    default: "导入 Excel 创建或更新单词表，也可以批量上传图片匹配已有单词。",
  },
});
</script>

<template>
  <div class="lists-create-backdrop" role="dialog" aria-modal="true" aria-labelledby="listsCreateTitle">
    <section class="lists-create-modal">
      <header class="lists-create-heading">
        <div>
          <p class="section-kicker">{{ kicker }}</p>
          <h2 id="listsCreateTitle">{{ title }}</h2>
          <p>{{ description }}</p>
        </div>
        <button class="secondary-button compact-button" type="button" @click="$emit('close')">关闭</button>
      </header>
      <div class="lists-create-body">
        <slot />
      </div>
    </section>
  </div>
</template>
