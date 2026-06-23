<template>
  <!-- Widget "Cơ cấu doanh thu" (mockup A2 id=ceo, M02-7) — bảng cơ cấu doanh thu theo 4 nhóm
       phân loại VTYT (Loại A/B/C/D) + thanh % tỷ trọng màu brand. Presentational: nhận props,
       emit retry — KHÔNG tự fetch. Token card/bar tái dùng (rounded-xl bg-surface-white) như
       AntmedTopHospitalsCard. BE trả cố định 4 dòng A→B→C→D + pct ⇒ FE KHÔNG sort/tính lại. -->
  <article
    class="flex flex-col gap-3 rounded-xl border border-outline-gray-1 bg-surface-white p-4"
    aria-labelledby="antmed-revenue-mix-title"
  >
    <header class="flex items-baseline justify-between gap-2">
      <h2
        id="antmed-revenue-mix-title"
        class="text-p-base font-semibold text-ink-gray-8"
      >
        {{ __('Cơ cấu doanh thu') }}
      </h2>
      <span
        v-if="!loading && !error && totalRevenue > 0"
        class="text-p-xs text-ink-gray-5"
      >
        {{ __('Tổng cộng') }}: {{ formatCurrencyVi(totalRevenue) }}
      </span>
    </header>

    <!-- Tri-branch riêng cho card -->
    <!-- Loading -->
    <div
      v-if="loading"
      class="flex items-center justify-center gap-2 py-8 text-ink-gray-6"
      aria-live="polite"
    >
      <LoadingIndicator class="h-4 w-4" />
      <span class="text-p-sm">{{ __('Đang tải…') }}</span>
    </div>

    <!-- Error -->
    <div
      v-else-if="error"
      class="flex flex-col items-center gap-3 py-8 text-center"
      role="alert"
    >
      <Badge
        variant="subtle"
        theme="red"
        size="sm"
        :label="__('Không tải được')"
      />
      <Button
        variant="outline"
        size="sm"
        :label="__('Thử lại')"
        @click="$emit('retry')"
      />
    </div>

    <!-- Empty — total_revenue==0 (chưa có doanh thu lớp nào) -->
    <div
      v-else-if="totalRevenue === 0 || !rows.length"
      class="flex flex-col items-center justify-center gap-1 rounded-lg bg-surface-gray-1 py-8 text-center"
    >
      <p class="text-p-sm font-medium text-ink-gray-5">
        {{ __('Chưa có dữ liệu doanh thu') }}
      </p>
    </div>

    <!-- Data — bảng 3 cột Phân loại | Doanh thu | Tỷ trọng (bar) -->
    <table v-else class="w-full border-separate border-spacing-0 text-left">
      <caption class="sr-only">
        {{
          __('Bảng cơ cấu doanh thu theo phân loại VTYT')
        }}
      </caption>
      <thead>
        <tr class="text-p-xs text-ink-gray-6">
          <th class="border-b border-outline-gray-1 py-2 pr-4 font-medium">
            {{ __('Phân loại') }}
          </th>
          <th
            class="border-b border-outline-gray-1 py-2 pr-4 text-right font-medium"
          >
            {{ __('Doanh thu') }}
          </th>
          <th class="border-b border-outline-gray-1 py-2 font-medium">
            {{ __('Tỷ trọng') }}
          </th>
        </tr>
      </thead>
      <tbody>
        <!-- FE KHÔNG sort lại — giữ thứ tự BE (cố định A→B→C→D, kể cả lớp revenue=0). -->
        <tr
          v-for="row in rows"
          :key="row.classification"
          class="text-p-sm text-ink-gray-8"
        >
          <!-- Phân loại (nhãn lớp) -->
          <td
            class="border-b border-outline-gray-1 py-2.5 pr-4 font-medium text-ink-gray-9"
          >
            {{ row.label }}
          </td>

          <!-- Doanh thu (format VI ĐẦY ĐỦ CHỮ triệu/tỷ — mockup A2) — lớp revenue=0 vẫn render số -->
          <td
            class="border-b border-outline-gray-1 py-2.5 pr-4 text-right tabular-nums text-ink-gray-8"
          >
            {{ formatCurrencyVi(row.revenue) }}
          </td>

          <!-- Tỷ trọng — thanh bar màu brand width=pct% + số % cạnh bar -->
          <td class="border-b border-outline-gray-1 py-2.5">
            <div class="flex items-center gap-2">
              <div
                class="h-2 w-24 overflow-hidden rounded-full bg-ink-gray-2"
                role="progressbar"
                :aria-valuenow="pctValue(row.pct)"
                aria-valuemin="0"
                aria-valuemax="100"
                :aria-label="__('Tỷ trọng doanh thu') + ' ' + pctLabel(row.pct)"
              >
                <div
                  class="h-full rounded-full transition-all"
                  :class="barFillClass('default')"
                  :style="revenueMixBarStyle(row.pct)"
                />
              </div>
              <span
                class="min-w-[2.75rem] tabular-nums text-p-xs text-ink-gray-7"
              >
                {{ pctLabel(row.pct) }}
              </span>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </article>
</template>

<script setup>
import { computed } from 'vue'
import { Badge, Button } from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import {
  formatCurrencyVi,
  revenueMixBarStyle,
  barFillClass,
} from '@/utils/antmedUi'

const props = defineProps({
  /** 4 dòng cố định A→B→C→D (BE trả + pct) — FE render nguyên thứ tự, KHÔNG sort lại. */
  items: { type: Array, default: () => [] },
  /** Tổng doanh thu 4 lớp A–D (từ total_revenue BE) — empty branch dựa giá trị này. */
  totalRevenue: { type: Number, default: 0 },
  /** Cờ loading của resource. */
  loading: { type: Boolean, default: false },
  /** Cờ error của resource. */
  error: { type: Boolean, default: false },
})

defineEmits(['retry'])

const rows = computed(() => props.items || [])

// Giá trị aria 0–100 (clamp). PURE.
function pctValue(value) {
  let p = Number(value)
  if (!Number.isFinite(p)) p = 0
  if (p < 0) p = 0
  if (p > 100) p = 100
  return p
}
// Nhãn % cạnh bar — '0%' khi thiếu/NaN (không vỡ render).
function pctLabel(value) {
  const p = Number(value)
  if (!Number.isFinite(p)) return '0%'
  return `${p}%`
}
</script>
