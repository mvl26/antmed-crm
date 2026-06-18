<template>
  <!-- KPI card (presentational — KHÔNG tự fetch). empty=true → placeholder VI, KHÔNG bịa số.
       tone = màu nhấn (viền trái + value + icon); icon = emoji nhỏ góc phải. Hover nhấc nhẹ. -->
  <article
    class="group relative flex flex-col gap-1 rounded-xl border border-l-4 border-outline-gray-1 bg-surface-white p-4 transition-all duration-200 ease-out hover:-translate-y-0.5 hover:shadow-md"
    :class="[toneCfg.accent, { 'opacity-70': empty }]"
  >
    <div class="flex items-start justify-between gap-2">
      <h3 class="text-p-sm font-medium text-ink-gray-6">
        {{ label }}
      </h3>
      <span
        v-if="icon"
        class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-sm transition-transform duration-200 group-hover:scale-110"
        :class="toneCfg.icon"
        aria-hidden="true"
      >
        {{ icon }}
      </span>
    </div>

    <!-- Empty: chưa có nguồn dữ liệu → placeholder tiếng Việt, KHÔNG số bịa -->
    <template v-if="empty">
      <p class="text-base font-semibold text-ink-gray-5">
        {{ __('Chưa có dữ liệu') }}
      </p>
      <p class="text-p-xs text-ink-gray-4">
        {{ placeholderHint || __('Sắp có') }}
      </p>
    </template>

    <!-- Data: KPI value THẬT từ endpoint -->
    <template v-else>
      <p class="text-2xl font-bold tabular-nums tracking-tight" :class="toneCfg.value">
        {{ displayValue }}
      </p>
      <p v-if="sub" class="text-p-xs text-ink-gray-5">
        {{ sub }}
      </p>
    </template>
  </article>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  /** Nhãn KPI (tiếng Việt). */
  label: { type: String, required: true },
  /** Giá trị THẬT (số/chuỗi). Bỏ qua khi empty=true. */
  value: { type: [Number, String], default: null },
  /** Dòng phụ dưới value (vd "vs T4"). */
  sub: { type: String, default: '' },
  /** Chưa có nguồn dữ liệu → render placeholder thay vì value. */
  empty: { type: Boolean, default: false },
  /** Gợi ý placeholder khi empty (mặc định "Sắp có"). */
  placeholderHint: { type: String, default: '' },
  /** Màu nhấn: teal | green | red | blue | orange | gray (mặc định gray — giữ look cũ). */
  tone: { type: String, default: 'gray' },
  /** Emoji nhỏ minh hoạ (tuỳ chọn). */
  icon: { type: String, default: '' },
})

// Class literal đầy đủ để Tailwind JIT quét được (KHÔNG ghép chuỗi động).
const TONES = {
  teal: { accent: 'border-l-teal-500', value: 'text-teal-700', icon: 'bg-teal-50 text-teal-600' },
  green: { accent: 'border-l-green-500', value: 'text-green-700', icon: 'bg-green-50 text-green-600' },
  red: { accent: 'border-l-red-500', value: 'text-red-700', icon: 'bg-red-50 text-red-600' },
  blue: { accent: 'border-l-blue-500', value: 'text-blue-700', icon: 'bg-blue-50 text-blue-600' },
  orange: { accent: 'border-l-orange-500', value: 'text-orange-700', icon: 'bg-orange-50 text-orange-600' },
  gray: { accent: 'border-l-outline-gray-2', value: 'text-ink-gray-9', icon: 'bg-surface-gray-2 text-ink-gray-6' },
}
const toneCfg = computed(() => TONES[props.tone] || TONES.gray)

// value=0 là số THẬT → render '0'; chỉ null/undefined mới ra dấu trung tính '—'.
const displayValue = computed(() => {
  if (props.value === null || props.value === undefined) return '—'
  return props.value
})
</script>
