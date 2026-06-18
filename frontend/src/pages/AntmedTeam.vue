<template>
  <main class="flex h-full flex-col" aria-labelledby="antmed-team-title">
    <!-- Header + breadcrumb: Trang chủ › Đội ngũ -->
    <header class="flex flex-col gap-2 border-b border-outline-gray-modals px-6 py-4">
      <nav class="text-p-xs text-ink-gray-5" :aria-label="__('Đường dẫn')">
        <RouterLink
          to="/antmed"
          class="rounded text-ink-gray-6 hover:text-ink-gray-8 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
        >
          {{ __('Trang chủ') }}
        </RouterLink>
        <span class="px-1.5 text-ink-gray-4" aria-hidden="true">›</span>
        <span class="text-ink-gray-7" aria-current="page">{{ __('Đội ngũ') }}</span>
      </nav>
      <div class="flex flex-col gap-1">
        <h1 id="antmed-team-title" class="text-xl font-semibold text-ink-gray-9">
          {{ __('Quản lý Đội ngũ') }}
        </h1>
        <p class="text-p-sm text-ink-gray-6">
          {{ __('Doanh số tháng & SLA của từng NV kinh doanh trong đội') }}
        </p>
      </div>
    </header>

    <!-- 3 KPI card thật ở đầu màn (số = kpis BE, KHÔNG hardcode) -->
    <section
      class="grid grid-cols-1 gap-3 px-6 pt-4 sm:grid-cols-3"
      :aria-label="__('Chỉ số đội ngũ')"
    >
      <AntmedKpiCard
        :label="__('Số NV')"
        :value="kpis.total_reps"
        :empty="roster.loading || !!roster.error"
        :placeholder-hint="__('Đang tải…')"
      />
      <AntmedKpiCard
        :label="__('DS tháng (đội)')"
        :value="formatVnMoney(kpis.total_month_sales)"
        :empty="roster.loading || !!roster.error"
        :placeholder-hint="__('Đang tải…')"
      />
      <AntmedKpiCard
        :label="__('SLA đúng giờ TB')"
        :value="`${kpis.avg_sla}%`"
        :empty="roster.loading || !!roster.error"
        :placeholder-hint="__('Đang tải…')"
      />
    </section>

    <!-- Tri-branch: loading / error / empty / data -->
    <section class="flex-1 overflow-auto px-6 pb-6 pt-4" aria-live="polite">
      <!-- Loading -->
      <div
        v-if="roster.loading"
        class="flex items-center justify-center gap-2 py-16 text-ink-gray-6"
      >
        <LoadingIndicator class="h-4 w-4" />
        <span class="text-p-base">{{ __('Đang tải…') }}</span>
      </div>

      <!-- Error: banner + nút Thử lại reload -->
      <div
        v-else-if="roster.error"
        class="flex flex-col items-center gap-3 py-16 text-center"
        role="alert"
      >
        <Badge variant="subtle" theme="red" size="lg" :label="__('Không tải được')" />
        <p class="max-w-md text-p-sm text-ink-gray-6">{{ errorMessage }}</p>
        <Button variant="outline" :label="__('Thử lại')" @click="roster.reload()" />
      </div>

      <!-- Empty -->
      <div
        v-else-if="!rows.length"
        class="flex flex-col items-center gap-2 py-16 text-center text-ink-gray-6"
      >
        <p class="text-p-base">{{ __('Chưa có dữ liệu đội ngũ') }}</p>
        <p class="text-p-sm">
          {{ __('Chưa có NV kinh doanh hoặc deal nào trong phạm vi của bạn.') }}
        </p>
      </div>

      <!-- Data table: 6 cột NV / Tuyến BV / DS tháng / Số deal mở / SLA đúng giờ / Cảnh báo -->
      <table v-else class="w-full border-separate border-spacing-0 text-left">
        <caption class="sr-only">
          {{ __('Bảng KPI doanh số & SLA của từng NV kinh doanh') }}
        </caption>
        <thead>
          <tr class="text-p-sm text-ink-gray-6">
            <th class="border-b border-outline-gray-modals py-2 pr-4 font-medium">
              {{ __('NV') }}
            </th>
            <th class="border-b border-outline-gray-modals py-2 pr-4 font-medium">
              {{ __('Tuyến BV') }}
            </th>
            <th class="border-b border-outline-gray-modals py-2 pr-4 font-medium">
              {{ __('DS tháng') }}
            </th>
            <th class="border-b border-outline-gray-modals py-2 pr-4 text-right font-medium">
              {{ __('Số deal mở') }}
            </th>
            <th class="border-b border-outline-gray-modals py-2 pr-4 text-right font-medium">
              {{ __('SLA đúng giờ') }}
            </th>
            <th class="border-b border-outline-gray-modals py-2 font-medium">
              {{ __('Cảnh báo') }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in rows"
            :key="row.deal_owner"
            class="text-p-base text-ink-gray-8"
          >
            <!-- NV: full_name (KHÔNG lộ email/ID thô) — link drill-down sang Hồ sơ NV (B2). -->
            <td class="border-b border-outline-gray-1 py-3 pr-4 font-medium text-ink-gray-9">
              <RouterLink
                :to="`/antmed/sales/team/${encodeURIComponent(row.deal_owner)}`"
                class="rounded text-teal-700 hover:text-teal-800 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
                :aria-label="__('Xem hồ sơ NV {0}', [row.full_name || ''])"
              >
                {{ row.full_name || '—' }}
              </RouterLink>
            </td>

            <!-- Tuyến BV (territory) -->
            <td class="border-b border-outline-gray-1 py-3 pr-4 text-ink-gray-7">
              {{ row.territory || '—' }}
            </td>

            <!-- DS tháng: thanh % (teamBarClass + width sales_pct) + số tiền formatVnMoney -->
            <td class="border-b border-outline-gray-1 py-3 pr-4 text-ink-gray-8">
              <div class="flex flex-col gap-1">
                <span class="font-medium tabular-nums">{{ formatVnMoney(row.month_sales) }}</span>
                <div
                  class="h-2 w-full overflow-hidden rounded-full bg-ink-gray-2"
                  role="progressbar"
                  :aria-valuenow="Math.round(row.sales_pct)"
                  aria-valuemin="0"
                  aria-valuemax="100"
                  :aria-label="
                    __('Doanh số {0} đạt {1}% so với mức cao nhất đội', [row.full_name || '', Math.round(row.sales_pct)])
                  "
                >
                  <div
                    class="h-full rounded-full"
                    :class="teamBarClass(row.bar_theme)"
                    :style="{ width: barWidth(row.sales_pct) }"
                  ></div>
                </div>
              </div>
            </td>

            <!-- Số deal mở -->
            <td class="border-b border-outline-gray-1 py-3 pr-4 text-right tabular-nums text-ink-gray-8">
              {{ row.open_deals }}
            </td>

            <!-- SLA đúng giờ (%) -->
            <td class="border-b border-outline-gray-1 py-3 pr-4 text-right tabular-nums text-ink-gray-8">
              {{ row.sla_ontime_pct }}%
            </td>

            <!-- Cảnh báo: chip 'DS thấp' (chỉ render khi alert != '') -->
            <td class="border-b border-outline-gray-1 py-3">
              <span
                v-if="teamAlertLabel(row.alert)"
                class="inline-flex items-center rounded-full px-2 py-0.5 text-p-xs font-medium"
                :class="teamAlertChipClass(row.alert)"
              >
                {{ teamAlertLabel(row.alert) }}
              </span>
              <span v-else class="text-p-sm text-ink-gray-4" aria-hidden="true">—</span>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Tổng số NV -->
      <p
        v-if="!roster.loading && !roster.error && rows.length"
        class="pt-3 text-p-sm text-ink-gray-5"
      >
        {{ __('Tổng cộng') }}: {{ rows.length }} {{ __('NV kinh doanh') }}
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
import { getTeamRoster } from '@/data/antmed'
import { teamBarClass, teamAlertChipClass, teamAlertLabel, formatVnMoney } from '@/utils/antmedUi'

// Endpoint trả RAW dict THƯỜNG { rows, kpis } → đọc r.data.* TRỰC TIẾP
// (KHÔNG .data.data — cùng idiom getExpiryAlerts/getDashboardOverview).
const roster = getTeamRoster({ auto: true })

// rows BE đã sort desc theo month_sales → FE KHÔNG sort lại.
const rows = computed(() => roster.data?.rows || [])
const kpis = computed(
  () => roster.data?.kpis || { total_reps: 0, total_month_sales: 0, avg_sla: 0 },
)

// Width thanh DS tháng: clamp 0–100 (BE đã tính sales_pct so đỉnh đội).
function barWidth(pct) {
  const p = Number(pct)
  const clamped = Number.isFinite(p) ? Math.max(0, Math.min(100, p)) : 0
  return `${clamped}%`
}

roster.onError = (err) => {
  toast.error(err?.messages?.[0] || __('Không tải được dữ liệu đội ngũ'))
}

const errorMessage = computed(
  () =>
    roster.error?.messages?.[0] ||
    roster.error?.message ||
    __('Không tải được dữ liệu đội ngũ'),
)
</script>
