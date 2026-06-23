<template>
  <!-- Widget "Danh mục VT trúng thầu — top 5" (mockup A2, M02-5) — bảng top SKU theo
       % quota đã dùng (cross-contract rollup) + thanh % màu (green/warn/danger).
       Presentational: nhận props, emit retry — KHÔNG tự fetch, KHÔNG sort lại (giữ thứ tự BE).
       Token card/bar tái dùng (rounded-xl bg-surface-white) như AntmedTopHospitalsCard. -->
  <article
    class="flex flex-col gap-3 rounded-xl border border-outline-gray-1 bg-surface-white p-4"
    aria-labelledby="antmed-top-quota-items-title"
  >
    <header class="flex items-baseline justify-between gap-2">
      <h2
        id="antmed-top-quota-items-title"
        class="text-p-base font-semibold text-ink-gray-8"
      >
        {{ __('Danh mục VT trúng thầu — top 5') }}
      </h2>
      <span
        v-if="!loading && !error && rows.length"
        class="text-p-xs text-ink-gray-5"
      >
        {{ __('Tổng cộng') }}: {{ totalCount }} {{ __('vật tư') }}
      </span>
    </header>

    <!-- Tri-branch riêng cho card (fetch ĐỘC LẬP với bảng Sức khỏe HĐ) -->
    <!-- Loading -->
    <div
      v-if="loading"
      class="flex items-center justify-center gap-2 py-8 text-ink-gray-6"
      aria-live="polite"
    >
      <LoadingIndicator class="h-4 w-4" />
      <span class="text-p-sm">{{ __('Đang tải…') }}</span>
    </div>

    <!-- Error — nút Thử lại reload card này (không vỡ bảng Sức khỏe HĐ) -->
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

    <!-- Empty -->
    <div
      v-else-if="!rows.length"
      class="flex flex-col items-center justify-center gap-1 rounded-lg bg-surface-gray-1 py-8 text-center"
    >
      <p class="text-p-sm font-medium text-ink-gray-5">
        {{ __('Chưa có vật tư trúng thầu') }}
      </p>
    </div>

    <!-- Data — bảng 4 cột SKU | Quota | Đã xuất | % -->
    <table v-else class="w-full border-separate border-spacing-0 text-left">
      <caption class="sr-only">
        {{
          __('Bảng danh mục vật tư trúng thầu theo % quota đã dùng')
        }}
      </caption>
      <thead>
        <tr class="text-p-xs text-ink-gray-6">
          <th class="border-b border-outline-gray-1 py-2 pr-4 font-medium">
            {{ __('SKU') }}
          </th>
          <th
            class="border-b border-outline-gray-1 py-2 pr-4 text-right font-medium"
          >
            {{ __('Quota') }}
          </th>
          <th
            class="border-b border-outline-gray-1 py-2 pr-4 text-right font-medium"
          >
            {{ __('Đã xuất') }}
          </th>
          <th class="border-b border-outline-gray-1 py-2 font-medium">
            {{ __('%') }}
          </th>
        </tr>
      </thead>
      <tbody>
        <!-- FE KHÔNG sort lại — giữ thứ tự BE (đã sort GIẢM used_pct). -->
        <tr
          v-for="row in rows"
          :key="row.item"
          class="text-p-sm text-ink-gray-8"
        >
          <!-- SKU: item_code · item_name (mã đậm + tên phụ) -->
          <td class="border-b border-outline-gray-1 py-2.5 pr-4">
            <div class="flex flex-col">
              <span class="font-medium text-ink-gray-9">{{ row.item }}</span>
              <span v-if="row.item_name" class="text-p-xs text-ink-gray-5">
                {{ row.item_name }}
              </span>
            </div>
          </td>

          <!-- Quota (quota_qty) -->
          <td
            class="border-b border-outline-gray-1 py-2.5 pr-4 text-right tabular-nums text-ink-gray-8"
          >
            {{ qtyLabel(row.quota_qty) }}
          </td>

          <!-- Đã xuất (used_qty) -->
          <td
            class="border-b border-outline-gray-1 py-2.5 pr-4 text-right tabular-nums text-ink-gray-8"
          >
            {{ qtyLabel(row.used_qty) }}
          </td>

          <!-- % — thanh bar màu theo health_color BE + số % cạnh bar -->
          <td class="border-b border-outline-gray-1 py-2.5">
            <div class="flex items-center gap-2">
              <div
                class="h-2 w-24 overflow-hidden rounded-full bg-ink-gray-2"
                role="progressbar"
                :aria-valuenow="clampPct(row.used_pct)"
                aria-valuemin="0"
                aria-valuemax="100"
                :aria-label="__('Quota đã dùng') + ' ' + pctLabel(row.used_pct)"
              >
                <div
                  class="h-full rounded-full transition-all"
                  :class="healthBarClass(row.health_color)"
                  :style="{ width: clampPct(row.used_pct) + '%' }"
                />
              </div>
              <span
                class="min-w-[2.75rem] tabular-nums text-p-xs text-ink-gray-7"
              >
                {{ pctLabel(row.used_pct) }}
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
import { healthBarClass } from '@/utils/antmedUi'

const props = defineProps({
  /** Danh sách VT (đã sort GIẢM used_pct + cắt limit ở BE) — FE render nguyên thứ tự. */
  items: { type: Array, default: () => [] },
  /** Tổng số VT phân biệt trong scope (từ total_count BE). */
  totalCount: { type: Number, default: 0 },
  /** Cờ loading của resource. */
  loading: { type: Boolean, default: false },
  /** Cờ error của resource. */
  error: { type: Boolean, default: false },
})

defineEmits(['retry'])

const rows = computed(() => props.items || [])

// Số lượng quota/đã-xuất — toLocaleString vi-VN; '—' khi thiếu/NaN. PURE.
function qtyLabel(value) {
  if (value === null || value === undefined || value === '') return '—'
  const n = Number(value)
  if (!Number.isFinite(n)) return '—'
  return n.toLocaleString('vi-VN')
}

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
