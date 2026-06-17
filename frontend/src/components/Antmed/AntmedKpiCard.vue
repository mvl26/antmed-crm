<template>
  <!-- KPI card A1 (presentational — KHÔNG tự fetch). empty=true → placeholder VI,
       KHÔNG bịa số. Container (AntmedHome) truyền value THẬT hoặc empty. -->
  <article
    class="flex flex-col gap-1 rounded-xl border border-outline-gray-1 bg-surface-white p-4"
    :class="{ 'opacity-70': empty }"
  >
    <h3 class="text-p-sm font-medium text-ink-gray-6">
      {{ label }}
    </h3>

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
      <p class="text-2xl font-semibold tabular-nums text-ink-gray-9">
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
})

// value=0 là số THẬT → render '0'; chỉ null/undefined mới ra dấu trung tính '—'.
// (KHÔNG dùng falsy-check — sẽ nuốt mất giá trị 0.)
const displayValue = computed(() => {
  if (props.value === null || props.value === undefined) return '—'
  return props.value
})
</script>
