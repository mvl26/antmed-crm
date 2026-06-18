<template>
  <!-- Timeline dọc (mockup .tl). events: [{ time, text, sub, muted, highlight }]. -->
  <div class="relative pl-5">
    <span class="absolute bottom-0 left-1.5 top-0 w-0.5 bg-ink-gray-2" aria-hidden="true" />
    <div
      v-for="(e, i) in events"
      :key="i"
      class="relative py-1 text-p-xs"
      :class="[
        e.muted ? 'opacity-40' : '',
        e.highlight ? 'rounded-md bg-teal-50 px-1.5 py-1.5' : '',
      ]"
    >
      <span
        class="absolute left-[-15px] top-2 h-2 w-2 rounded-full border-2 border-surface-white bg-teal-600"
        aria-hidden="true"
      />
      <b v-if="e.time" class="text-teal-900">{{ e.time }}</b>
      <span :class="e.highlight ? 'text-teal-700' : ''"> {{ e.text }}</span>
      <small v-if="e.sub" class="text-ink-gray-5"> {{ e.sub }}</small>
    </div>
  </div>
</template>

<script setup>
defineProps({
  events: { type: Array, default: () => [] },
})
</script>
