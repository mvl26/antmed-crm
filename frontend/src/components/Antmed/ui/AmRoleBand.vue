<template>
  <!-- Dải tiêu đề vai trò (mockup .role-band). title + tag mô tả thiết bị/ngữ cảnh. -->
  <div
    class="flex items-center justify-between rounded-lg bg-teal-900 px-4 py-2.5 text-sm font-bold text-white"
  >
    <span
      ><slot>{{ title }}</slot></span
    >
    <span
      v-if="tag"
      class="rounded-full bg-white/20 px-2.5 py-0.5 text-[11px] font-medium"
    >
      {{ tag }}
    </span>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: '' },
  tag: { type: String, default: '' },
})
</script>
