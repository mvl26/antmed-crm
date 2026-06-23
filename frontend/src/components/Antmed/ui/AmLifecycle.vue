<template>
  <!-- Vòng đời chevron (mockup .lifecycle). steps: [{ label, status:'done'|'current'|'todo' }]. -->
  <div class="flex gap-0.5 text-[9px]" :aria-label="ariaLabel">
    <div
      v-for="(s, i) in steps"
      :key="i"
      class="flex-1 px-1 py-1 text-center"
      :class="stageClass(s.status)"
      style="
        clip-path: polygon(
          0 0,
          calc(100% - 7px) 0,
          100% 50%,
          calc(100% - 7px) 100%,
          0 100%,
          7px 50%
        );
      "
    >
      {{ s.label }}
    </div>
  </div>
</template>

<script setup>
import { stageClass } from '@/utils/antmedUi'

defineProps({
  steps: { type: Array, default: () => [] },
  ariaLabel: { type: String, default: 'Vòng đời' },
})
</script>
