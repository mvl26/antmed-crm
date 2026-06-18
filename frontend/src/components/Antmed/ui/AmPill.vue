<template>
  <!-- Pill trạng thái (mockup .pill). LUÔN kèm chữ (label/slot) — không phân biệt chỉ bằng màu. -->
  <span
    class="inline-block rounded-md px-1.5 py-0.5 text-xs font-semibold"
    :class="pillClass(theme)"
  >
    <slot>{{ label }}</slot>
  </span>
</template>

<script setup>
import { pillClass } from '@/utils/antmedUi'

defineProps({
  /** ok | warn | danger | info | neutral */
  theme: { type: String, default: 'neutral' },
  label: { type: String, default: '' },
})
</script>
