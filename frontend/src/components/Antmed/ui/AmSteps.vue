<template>
  <!-- Steps wizard (mockup .steps). steps: [{ label, status:'done'|'current'|'todo' }]. -->
  <div class="flex gap-1.5">
    <div
      v-for="(s, i) in steps"
      :key="i"
      class="flex-1 rounded-md px-2 py-2 text-center text-xs"
      :class="stageClass(s.status)"
    >
      {{ s.label }}<span v-if="s.status === 'done'"> ✓</span>
    </div>
  </div>
</template>

<script setup>
import { stageClass } from '@/utils/antmedUi'

defineProps({
  steps: { type: Array, default: () => [] },
})
</script>
