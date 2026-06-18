<template>
  <!-- Ô heatmap (mockup .heat td.h1c..h5c). level 0|null → ô thường. Render <td>. -->
  <td
    class="rounded px-1.5 py-1 text-center text-[10px] font-semibold"
    :class="level ? heatClass(level) : 'text-ink-gray-7'"
  >
    <slot>{{ value }}</slot>
  </td>
</template>

<script setup>
import { heatClass } from '@/utils/antmedUi'

defineProps({
  /** 1..5 ; 0/null = không tô */
  level: { type: Number, default: 0 },
  value: { type: [String, Number], default: '' },
})
</script>
