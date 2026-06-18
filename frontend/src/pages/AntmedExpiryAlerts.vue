<template>
  <main class="flex h-full flex-col" aria-labelledby="antmed-expiry-title">
    <!-- Header + breadcrumb: Trang chủ › Kho › Cảnh báo HSD -->
    <header class="flex flex-col gap-2 border-b border-outline-gray-modals px-6 py-4">
      <nav class="text-p-xs text-ink-gray-5" :aria-label="__('Đường dẫn')">
        <RouterLink
          to="/antmed"
          class="rounded text-ink-gray-6 hover:text-ink-gray-8 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
        >
          {{ __('Trang chủ') }}
        </RouterLink>
        <span class="px-1.5 text-ink-gray-4" aria-hidden="true">›</span>
        <span class="text-ink-gray-6">{{ __('Kho') }}</span>
        <span class="px-1.5 text-ink-gray-4" aria-hidden="true">›</span>
        <span class="text-ink-gray-7" aria-current="page">{{ __('Cảnh báo HSD') }}</span>
      </nav>
      <div class="flex flex-col gap-1">
        <h1 id="antmed-expiry-title" class="text-xl font-semibold text-ink-gray-9">
          {{ __('Cảnh báo HSD') }}
        </h1>
        <p class="text-p-sm text-ink-gray-6">
          {{ __('Lô cận / quá hạn sử dụng trên toàn bộ kho (Tổng / Cá nhân NV / Ký gửi BV)') }}
        </p>
      </div>
    </header>

    <!-- 4 KPI card thật ở đầu màn (số = kpis BE, KHÔNG hardcode) -->
    <section
      class="grid grid-cols-1 gap-3 px-6 pt-4 sm:grid-cols-2 lg:grid-cols-4"
      :aria-label="__('Chỉ số cảnh báo HSD')"
    >
      <AntmedKpiCard
        :label="__('Đã hết hạn')"
        :value="kpis.expired"
        :empty="alerts.loading || !!alerts.error"
        :placeholder-hint="__('Đang tải…')"
      />
      <AntmedKpiCard
        :label="__('≤30 ngày')"
        :value="kpis.d30"
        :empty="alerts.loading || !!alerts.error"
        :placeholder-hint="__('Đang tải…')"
      />
      <AntmedKpiCard
        :label="__('≤60 ngày')"
        :value="kpis.d60"
        :empty="alerts.loading || !!alerts.error"
        :placeholder-hint="__('Đang tải…')"
      />
      <AntmedKpiCard
        :label="__('≤90 ngày')"
        :value="kpis.d90"
        :empty="alerts.loading || !!alerts.error"
        :placeholder-hint="__('Đang tải…')"
      />
    </section>

    <!-- Tri-branch: loading / error / empty / data -->
    <section class="flex-1 overflow-auto px-6 pb-6 pt-4" aria-live="polite">
      <!-- Loading -->
      <div
        v-if="alerts.loading"
        class="flex items-center justify-center gap-2 py-16 text-ink-gray-6"
      >
        <LoadingIndicator class="h-4 w-4" />
        <span class="text-p-base">{{ __('Đang tải…') }}</span>
      </div>

      <!-- Error: banner + nút Thử lại reload -->
      <div
        v-else-if="alerts.error"
        class="flex flex-col items-center gap-3 py-16 text-center"
        role="alert"
      >
        <Badge variant="subtle" theme="red" size="lg" :label="__('Không tải được')" />
        <p class="max-w-md text-p-sm text-ink-gray-6">{{ errorMessage }}</p>
        <Button variant="outline" :label="__('Thử lại')" @click="alerts.reload()" />
      </div>

      <!-- Empty -->
      <div
        v-else-if="!rows.length"
        class="flex flex-col items-center gap-2 py-16 text-center text-ink-gray-6"
      >
        <p class="text-p-base">{{ __('Không có lot cận date') }}</p>
        <p class="text-p-sm">
          {{ __('Không có lô nào cận hoặc quá hạn sử dụng trong toàn bộ kho.') }}
        </p>
      </div>

      <!-- Data table: 7 cột SKU / Tên VT / Lot / Kho / HSD / SL còn / Mức độ -->
      <table v-else class="w-full border-separate border-spacing-0 text-left">
        <caption class="sr-only">
          {{ __('Bảng lô cận / quá hạn sử dụng trên toàn bộ kho') }}
        </caption>
        <thead>
          <tr class="text-p-sm text-ink-gray-6">
            <th class="border-b border-outline-gray-modals py-2 pr-4 font-medium">
              {{ __('SKU') }}
            </th>
            <th class="border-b border-outline-gray-modals py-2 pr-4 font-medium">
              {{ __('Tên VT') }}
            </th>
            <th class="border-b border-outline-gray-modals py-2 pr-4 font-medium">
              {{ __('Lot') }}
            </th>
            <th class="border-b border-outline-gray-modals py-2 pr-4 font-medium">
              {{ __('Kho') }}
            </th>
            <th class="border-b border-outline-gray-modals py-2 pr-4 font-medium">
              {{ __('HSD') }}
            </th>
            <th class="border-b border-outline-gray-modals py-2 pr-4 text-right font-medium">
              {{ __('SL còn') }}
            </th>
            <th class="border-b border-outline-gray-modals py-2 font-medium">
              {{ __('Mức độ') }}
            </th>
          </tr>
        </thead>
        <tbody>
          <!-- Dòng severity expired || d30 → highlight nền đỏ nhạt (cảnh báo nguy cấp) -->
          <tr
            v-for="row in rows"
            :key="`${row.warehouse}|${row.sku}|${row.lot}`"
            class="text-p-base text-ink-gray-8"
            :class="row.severity === 'expired' || row.severity === 'd30' ? 'bg-red-50' : ''"
          >
            <!-- SKU (item_code) — mã nhỏ phụ trợ -->
            <td class="border-b border-outline-gray-1 py-3 pr-4 font-mono text-p-sm text-ink-gray-7">
              {{ row.sku || '—' }}
            </td>

            <!-- Tên VT: item_name (hiển thị tên, KHÔNG chỉ mã) -->
            <td class="border-b border-outline-gray-1 py-3 pr-4 font-medium text-ink-gray-9">
              {{ row.item_name || row.sku || '—' }}
            </td>

            <!-- Lot -->
            <td class="border-b border-outline-gray-1 py-3 pr-4 text-ink-gray-7">
              {{ row.lot || '—' }}
            </td>

            <!-- Kho: tên kho + chip loại kho (warehouse_name, KHÔNG lộ mã) -->
            <td class="border-b border-outline-gray-1 py-3 pr-4 text-ink-gray-8">
              <div class="flex flex-col gap-1">
                <span class="font-medium">{{ row.warehouse_name || row.warehouse || '—' }}</span>
                <span
                  v-if="row.warehouse_type"
                  class="inline-flex w-fit items-center rounded-full bg-ink-gray-2 px-2 py-0.5 text-p-xs font-medium text-ink-gray-7"
                >
                  {{ row.warehouse_type }}
                </span>
              </div>
            </td>

            <!-- HSD: định dạng MM/YYYY -->
            <td class="border-b border-outline-gray-1 py-3 pr-4 tabular-nums text-ink-gray-7">
              {{ formatExpiryMonthYear(row.expiry_date) || '—' }}
            </td>

            <!-- SL còn (balance_qty) -->
            <td class="border-b border-outline-gray-1 py-3 pr-4 text-right tabular-nums text-ink-gray-8">
              {{ row.balance_qty }}
            </td>

            <!-- Chip MỨC ĐỘ: kèm CHỮ (không chỉ màu — WCAG AA) -->
            <td class="border-b border-outline-gray-1 py-3">
              <span
                class="inline-flex items-center rounded-full px-2 py-0.5 text-p-xs font-medium"
                :class="expirySeverityChipClass(row.severity)"
              >
                {{ expirySeverityLabel(row.severity) }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Tổng số dòng -->
      <p
        v-if="!alerts.loading && !alerts.error && rows.length"
        class="pt-3 text-p-sm text-ink-gray-5"
      >
        {{ __('Tổng cộng') }}: {{ rows.length }} {{ __('lô cận / quá date') }}
      </p>
    </section>
  </main>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { Badge, Button, toast } from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import AntmedKpiCard from '@/components/Antmed/AntmedKpiCard.vue'
import { getExpiryAlerts } from '@/data/antmed'
import {
  formatExpiryMonthYear,
  expirySeverityChipClass,
  expirySeverityLabel,
} from '@/utils/antmedUi'

// Endpoint trả RAW dict THƯỜNG { kpis, rows } → đọc r.data.* TRỰC TIẾP
// (KHÔNG .data.data — cùng idiom getLot/getConsignmentStock).
const alerts = getExpiryAlerts({ auto: true })

// rows BE đã sort days_to_expiry tăng dần (quá hạn lên đầu) → FE KHÔNG sort lại.
const rows = computed(() => alerts.data?.rows || [])
const kpis = computed(
  () => alerts.data?.kpis || { expired: 0, d30: 0, d60: 0, d90: 0, total_lots: 0 },
)

alerts.onError = (err) => {
  toast.error(err?.messages?.[0] || __('Không tải được cảnh báo HSD'))
}

const errorMessage = computed(
  () =>
    alerts.error?.messages?.[0] ||
    alerts.error?.message ||
    __('Không tải được cảnh báo HSD'),
)
</script>
