<template>
  <!-- Thanh tiến độ quota/% (mockup .bar). pct 0..100, theme default/warn/danger. -->
  <div class="flex items-center gap-1.5">
    <div class="h-1.5 flex-1 overflow-hidden rounded-full bg-ink-gray-2">
      <div
        class="h-full rounded-full"
        :class="barFillClass(theme)"
        :style="{ width: clamped + '%' }"
      />
    </div>
    <span v-if="showLabel" class="text-[10px] tabular-nums text-ink-gray-6"
      >{{ clamped }}%</span
    >
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { barFillClass } from '@/utils/antmedUi'

const props = defineProps({
  pct: { type: Number, default: 0 },
  theme: { type: String, default: 'default' },
  showLabel: { type: Boolean, default: true },
})

const clamped = computed(() =>
  Math.max(0, Math.min(100, Math.round(props.pct))),
)
</script>
