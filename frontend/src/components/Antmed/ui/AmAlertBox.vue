<template>
  <!-- Hộp cảnh báo (mockup .alert-box / .info / .danger). Viền trái màu + nền nhạt. -->
  <div
    class="my-2 rounded border-l-[3px] px-3 py-2 text-p-xs"
    :class="alertClass(theme)"
    role="note"
  >
    <slot>{{ text }}</slot>
  </div>
</template>

<script setup>
import { alertClass } from '@/utils/antmedUi'

defineProps({
  /** info | warn | danger */
  theme: { type: String, default: 'warn' },
  text: { type: String, default: '' },
})
</script>
