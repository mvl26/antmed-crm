<template>
  <!-- Cột kanban (mockup .kcol). title + count badge + slot thẻ. -->
  <div class="min-h-[220px] rounded-lg bg-surface-gray-1 p-2">
    <h3 class="mb-1.5 flex items-center justify-between text-p-xs font-medium text-ink-gray-7">
      <span>{{ title }}</span>
      <span class="rounded-full bg-ink-gray-2 px-1.5 py-0.5 text-[9px] text-ink-gray-7">{{ count }}</span>
    </h3>
    <slot />
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  count: { type: [Number, String], default: 0 },
})
</script>
