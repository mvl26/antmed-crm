<template>
  <!-- Vùng ký số (mockup .sig) — prototype tĩnh, không bắt nét thật. -->
  <div
    class="rounded-md border border-dashed border-outline-gray-2 bg-surface-white px-4 py-4 text-center text-p-xs italic text-ink-gray-5"
  >
    <slot>{{ label }}</slot>
  </div>
</template>

<script setup>
defineProps({
  label: { type: String, default: '✍ Vùng vẽ chữ ký' },
})
</script>
