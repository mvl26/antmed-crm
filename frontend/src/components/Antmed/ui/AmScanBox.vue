<template>
  <!-- Khung quét QR/Barcode (mockup .scan). -->
  <div
    class="rounded-lg border-2 border-dashed border-teal-500 bg-cyan-50 px-4 py-4 text-center text-p-xs text-teal-900"
  >
    <slot>{{ text }}</slot>
  </div>
</template>

<script setup>
defineProps({
  text: { type: String, default: '' },
})
</script>
