<template>
  <!-- Funnel pipeline (mockup .funnel). stages: [{ label, count, width(%) }]. -->
  <div class="flex flex-col gap-1">
    <div
      v-for="(s, i) in stages"
      :key="i"
      class="self-center rounded px-1 py-1 text-center text-[10px] text-white"
      :class="i === stages.length - 1 ? 'text-teal-900' : ''"
      :style="{ width: (s.width ?? 100) + '%', background: shade(i) }"
    >
      {{ s.label }} — {{ s.count }}
    </div>
  </div>
</template>

<script setup>
defineProps({
  stages: { type: Array, default: () => [] },
})

// Dải teal nhạt dần theo tầng (mockup dùng #0EA5A4 → #9EDDDC).
const SHADES = ['#0EA5A4', '#26A4A3', '#3FB8B6', '#6BC9C8', '#9EDDDC']
function shade(i) {
  return SHADES[Math.min(i, SHADES.length - 1)]
}
</script>
