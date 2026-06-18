<template>
  <!-- KPI 'Quota đã dùng' (A1) — vòng ring conic-gradient theo % + dòng phụ 'N HĐ > 90%'.
       Presentational: nhận value THẬT từ container (AntmedHome), KHÔNG tự fetch, KHÔNG bịa số. -->
  <article
    class="flex flex-col gap-3 rounded-xl border border-outline-gray-1 bg-surface-white p-4"
  >
    <h3 class="text-p-sm font-medium text-ink-gray-6">
      {{ label }}
    </h3>

    <div class="flex items-center gap-4">
      <!-- Vòng ring: conic-gradient phần đã dùng (theme màu theo ngưỡng) + lỗ trắng giữa. -->
      <div
        class="relative h-20 w-20 shrink-0 rounded-full"
        :style="ringStyle"
        role="img"
        :aria-label="`${__('Quota đã dùng')} ${displayPct}`"
      >
        <div
          class="absolute inset-[10px] flex items-center justify-center rounded-full bg-surface-white"
        >
          <span class="text-base font-semibold tabular-nums text-ink-gray-9">
            {{ displayPct }}
          </span>
        </div>
      </div>

      <div class="flex flex-col gap-0.5">
        <p class="text-p-xs text-ink-gray-5">
          {{ __('Trung bình các HĐ') }}
        </p>
        <p class="text-p-sm font-medium text-ink-gray-7">
          {{ overCountLabel }}
        </p>
      </div>
    </div>
  </article>
</template>

<script setup>
import { computed } from 'vue'
import { quotaRingStyle } from '@/utils/antmedUi'

const props = defineProps({
  /** Nhãn KPI (tiếng Việt). */
  label: { type: String, default: 'Quota đã dùng' },
  /** avg_quota_used_pct THẬT (float). null/undefined → '—' (chưa có số). */
  avgPct: { type: Number, default: null },
  /** contracts_over_90_count THẬT (int). */
  overCount: { type: Number, default: 0 },
})

// 0 là số THẬT → render '0%'; chỉ null/undefined ra '—' (KHÔNG falsy-check nuốt mất 0).
const displayPct = computed(() => {
  if (props.avgPct === null || props.avgPct === undefined) return '—'
  return `${props.avgPct}%`
})

// conic-gradient: màu + góc do helper thuần quotaRingStyle (token CSS var, KHÔNG hex thô;
// ngưỡng đỏ≥95 / cam≥72 / xanh — đồng bộ quotaBarTheme M02 §1ter.3, unit-test trực tiếp).
const ringStyle = computed(() => quotaRingStyle(props.avgPct))

const overCountLabel = computed(
  () => `${props.overCount || 0} ${__('HĐ > 90%')}`,
)
</script>
