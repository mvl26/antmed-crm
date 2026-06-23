<template>
  <!-- Card trắng viền (mockup .card). title (tùy chọn) → h2 teal-dark. -->
  <article class="rounded-lg border border-outline-gray-1 bg-surface-white p-3">
    <div
      v-if="title || $slots.title"
      class="mb-2 flex items-center justify-between gap-2"
    >
      <h2 class="text-p-sm font-semibold text-teal-900">
        <slot name="title">{{ title }}</slot>
      </h2>
      <slot name="actions" />
    </div>
    <slot />
  </article>
</template>

<script setup>
defineProps({
  title: { type: String, default: '' },
})
</script>
