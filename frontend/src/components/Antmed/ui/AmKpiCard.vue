<template>
  <!-- KPI tile prototype (mockup .kpi). value tĩnh từ dữ liệu mẫu; delta up/down có màu. -->
  <article class="rounded-lg border border-outline-gray-1 bg-surface-white p-3">
    <div class="text-[10px] font-medium uppercase tracking-wide text-ink-gray-5">
      {{ label }}
    </div>
    <div class="my-1 text-xl font-bold tabular-nums" :class="valueClass || 'text-ink-gray-9'">
      <slot name="value">{{ value }}</slot>
    </div>
    <div v-if="sub || delta" class="text-[10px] text-ink-gray-5">
      <span v-if="delta" :class="delta.dir === 'down' ? 'font-semibold text-red-600' : 'font-semibold text-green-600'">
        {{ delta.dir === 'down' ? '▼' : '▲' }} {{ delta.text }}
      </span>
      {{ sub }}
    </div>
  </article>
</template>

<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], default: '' },
  sub: { type: String, default: '' },
  /** màu value đặc biệt, vd 'text-red-600' cho cảnh báo */
  valueClass: { type: String, default: '' },
  /** { dir: 'up'|'down', text: '14%' } */
  delta: { type: Object, default: null },
})
</script>
