<template>
  <!-- Widget "Top 10 Bệnh viện" (mockup A1 line 261, M02-4) — bảng xếp hạng BV theo
       doanh thu HĐ + thanh % quota màu (green/warn/danger). Presentational: nhận props,
       emit retry/open — KHÔNG tự fetch. Token card/bar tái dùng (rounded-xl bg-surface-white). -->
  <article
    class="flex flex-col gap-3 rounded-xl border border-outline-gray-1 bg-surface-white p-4"
    aria-labelledby="antmed-top-hospitals-title"
  >
    <header class="flex items-baseline justify-between gap-2">
      <h2 id="antmed-top-hospitals-title" class="text-p-base font-semibold text-ink-gray-8">
        {{ __('Top 10 Bệnh viện') }}
      </h2>
      <span
        v-if="!loading && !error && rows.length"
        class="text-p-xs text-ink-gray-5"
      >
        {{ __('Tổng cộng') }}: {{ totalCount }} {{ __('bệnh viện') }}
      </span>
    </header>

    <!-- Tri-branch riêng cho card (không dùng tri-branch chung overview) -->
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
      <Badge variant="subtle" theme="red" size="sm" :label="__('Không tải được')" />
      <Button variant="outline" size="sm" :label="__('Thử lại')" @click="$emit('retry')" />
    </div>

    <!-- Empty -->
    <div
      v-else-if="!rows.length"
      class="flex flex-col items-center justify-center gap-1 rounded-lg bg-surface-gray-1 py-8 text-center"
    >
      <p class="text-p-sm font-medium text-ink-gray-5">
        {{ __('Chưa có dữ liệu bệnh viện') }}
      </p>
    </div>

    <!-- Data — bảng 3 cột BV | DT | Quota -->
    <table v-else class="w-full border-separate border-spacing-0 text-left">
      <caption class="sr-only">
        {{ __('Bảng xếp hạng bệnh viện theo doanh thu') }}
      </caption>
      <thead>
        <tr class="text-p-xs text-ink-gray-6">
          <th class="border-b border-outline-gray-1 py-2 pr-4 font-medium">
            {{ __('Bệnh viện') }}
          </th>
          <th class="border-b border-outline-gray-1 py-2 pr-4 text-right font-medium">
            {{ __('Doanh thu') }}
          </th>
          <th class="border-b border-outline-gray-1 py-2 font-medium">
            {{ __('Quota') }}
          </th>
        </tr>
      </thead>
      <tbody>
        <!-- FE KHÔNG sort lại — giữ thứ tự BE (đã sort GIẢM revenue). -->
        <tr
          v-for="row in rows"
          :key="row.hospital"
          role="link"
          tabindex="0"
          :aria-label="__('Xem chi tiết bệnh viện') + ' ' + (row.hospital_name || row.hospital)"
          class="cursor-pointer text-p-sm text-ink-gray-8 transition hover:bg-surface-gray-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
          @click="$emit('open', row.hospital)"
          @keydown.enter="$emit('open', row.hospital)"
        >
          <!-- BV (tên, KHÔNG mã) -->
          <td class="border-b border-outline-gray-1 py-2.5 pr-4 font-medium text-ink-gray-9">
            {{ row.hospital_name || row.hospital }}
          </td>

          <!-- DT — doanh thu HĐ (format VN gọn tr/tỷ) -->
          <td class="border-b border-outline-gray-1 py-2.5 pr-4 text-right tabular-nums text-ink-gray-8">
            {{ formatVnMoney(row.revenue) }}
          </td>

          <!-- Quota — thanh bar màu theo health_color BE + số % cạnh bar -->
          <td class="border-b border-outline-gray-1 py-2.5">
            <div class="flex items-center gap-2">
              <div
                class="h-2 w-24 overflow-hidden rounded-full bg-ink-gray-2"
                role="progressbar"
                :aria-valuenow="clampPct(row.quota_used_pct)"
                aria-valuemin="0"
                aria-valuemax="100"
                :aria-label="__('Quota đã dùng') + ' ' + pctLabel(row.quota_used_pct)"
              >
                <div
                  class="h-full rounded-full transition-all"
                  :class="healthBarClass(row.health_color)"
                  :style="{ width: clampPct(row.quota_used_pct) + '%' }"
                />
              </div>
              <span class="min-w-[2.75rem] tabular-nums text-p-xs text-ink-gray-7">
                {{ pctLabel(row.quota_used_pct) }}
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
import { healthBarClass, formatVnMoney } from '@/utils/antmedUi'

const props = defineProps({
  /** Danh sách BV (đã sort GIẢM revenue + cắt limit ở BE) — FE render nguyên thứ tự. */
  items: { type: Array, default: () => [] },
  /** Tổng số BV phân biệt trong scope (từ total_count BE). */
  totalCount: { type: Number, default: 0 },
  /** Cờ loading của resource. */
  loading: { type: Boolean, default: false },
  /** Cờ error của resource. */
  error: { type: Boolean, default: false },
})

defineEmits(['retry', 'open'])

const rows = computed(() => props.items || [])

// Clamp 0–100 cho width thanh (BE >100 → màu đã red; clamp để bar không tràn). PURE.
function clampPct(value) {
  let p = Number(value)
  if (!Number.isFinite(p)) p = 0
  if (p < 0) p = 0
  if (p > 100) p = 100
  return Math.round(p)
}
// Nhãn số % cạnh bar — '0%' khi thiếu/NaN (không vỡ render).
function pctLabel(value) {
  const p = Number(value)
  if (!Number.isFinite(p)) return '0%'
  return `${Math.round(p)}%`
}
</script>
