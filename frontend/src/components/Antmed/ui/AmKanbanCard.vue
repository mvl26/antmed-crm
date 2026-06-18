<template>
  <!-- Thẻ kanban (mockup .kcard / .urgent .warn .ok). accent → viền trái màu. -->
  <div
    class="mb-1.5 rounded-md border border-outline-gray-1 bg-surface-white p-2 text-[10px]"
    :class="kanbanAccentClass(accent)"
  >
    <div v-if="heading" class="mb-0.5 text-p-xs font-bold text-teal-900">{{ heading }}</div>
    <slot />
  </div>
</template>

<script setup>
import { kanbanAccentClass } from '@/utils/antmedUi'

defineProps({
  /** urgent | warn | ok | '' */
  accent: { type: String, default: '' },
  heading: { type: String, default: '' },
})
</script>
