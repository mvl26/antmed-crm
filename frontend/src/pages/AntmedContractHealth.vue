<template>
  <main class="flex h-full flex-col" aria-labelledby="antmed-contract-health-title">
    <!-- Header + breadcrumb -->
    <header class="flex flex-col gap-2 border-b border-outline-gray-modals px-6 py-4">
      <nav class="text-p-xs text-ink-gray-5" :aria-label="__('Đường dẫn')">
        <RouterLink
          to="/antmed"
          class="rounded text-ink-gray-6 hover:text-ink-gray-8 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
        >
          {{ __('Trang chủ') }}
        </RouterLink>
        <span class="px-1.5 text-ink-gray-4" aria-hidden="true">›</span>
        <span class="text-ink-gray-7">{{ __('Hợp đồng & Gói thầu') }}</span>
      </nav>
      <div class="flex flex-col gap-1">
        <h1 id="antmed-contract-health-title" class="text-xl font-semibold text-ink-gray-9">
          {{ __('Sức khỏe Hợp đồng') }}
        </h1>
        <p class="text-p-sm text-ink-gray-6">
          {{ __('Theo dõi quota đã dùng và hạn hiệu lực của từng hợp đồng / gói thầu') }}
        </p>
      </div>
    </header>

    <!-- Tri-branch: loading / error / data -->
    <section class="flex-1 overflow-auto px-6 pb-6" aria-live="polite">
      <!-- Loading -->
      <div
        v-if="health.loading"
        class="flex items-center justify-center gap-2 py-16 text-ink-gray-6"
      >
        <LoadingIndicator class="h-4 w-4" />
        <span class="text-p-base">{{ __('Đang tải sức khỏe hợp đồng…') }}</span>
      </div>

      <!-- Error -->
      <div
        v-else-if="health.error"
        class="flex flex-col items-center gap-3 py-16 text-center"
        role="alert"
      >
        <Badge variant="subtle" theme="red" size="lg" :label="__('Không tải được')" />
        <p class="max-w-md text-p-sm text-ink-gray-6">{{ errorMessage }}</p>
        <Button variant="outline" :label="__('Thử lại')" @click="health.reload()" />
      </div>

      <!-- Empty -->
      <div
        v-else-if="!rows.length"
        class="flex flex-col items-center gap-2 py-16 text-center text-ink-gray-6"
      >
        <p class="text-p-base">{{ __('Chưa có hợp đồng.') }}</p>
        <p class="text-p-sm">
          {{ __('Hợp đồng được tạo bởi Quản lý trong Frappe Desk (AntMed Contract) rồi tải lại.') }}
        </p>
      </div>

      <!-- Data table A2 -->
      <table v-else class="w-full border-separate border-spacing-0 text-left">
        <caption class="sr-only">
          {{ __('Bảng sức khỏe hợp đồng') }}
        </caption>
        <thead>
          <tr class="text-p-sm text-ink-gray-6">
            <th class="border-b border-outline-gray-modals py-2 pr-4 font-medium">
              {{ __('Số HĐ') }}
            </th>
            <th class="border-b border-outline-gray-modals py-2 pr-4 font-medium">
              {{ __('Bệnh viện') }}
            </th>
            <th class="border-b border-outline-gray-modals py-2 pr-4 font-medium">
              {{ __('Hết hạn') }}
            </th>
            <th class="border-b border-outline-gray-modals py-2 pr-4 text-right font-medium">
              {{ __('Giá trị') }}
            </th>
            <th class="border-b border-outline-gray-modals py-2 pr-4 font-medium">
              {{ __('% Quota') }}
            </th>
            <th class="border-b border-outline-gray-modals py-2 pr-4 font-medium">
              {{ __('Trạng thái') }}
            </th>
            <th class="border-b border-outline-gray-modals py-2 text-right font-medium">
              {{ __('Thao tác') }}
            </th>
          </tr>
        </thead>
        <tbody>
          <!--
            Drill-down: mỗi dòng (và nút Chi tiết) điều hướng tới AntmedContractDetail
            (/antmed/contracts/:name) — tái dùng pattern AntmedContracts (ADR-M02-07).
          -->
          <tr
            v-for="row in rows"
            :key="row.name"
            role="link"
            tabindex="0"
            :aria-label="__('Xem chi tiết hợp đồng') + ' ' + (row.contract_no || row.name)"
            class="cursor-pointer text-p-base text-ink-gray-8 transition hover:bg-surface-gray-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
            @click="openContract(row.name)"
            @keydown.enter="openContract(row.name)"
          >
            <!-- Số HĐ -->
            <td class="border-b border-outline-gray-1 py-3 pr-4 font-medium text-ink-gray-9">
              {{ row.contract_no || row.name }}
            </td>

            <!-- Bệnh viện (tên, KHÔNG mã) -->
            <td class="border-b border-outline-gray-1 py-3 pr-4 text-ink-gray-7">
              {{ row.hospital_name || row.hospital || '—' }}
            </td>

            <!-- Hết hạn dd/MM/yyyy + chip cảnh báo nếu ≤30 ngày / đã hết hạn -->
            <td class="border-b border-outline-gray-1 py-3 pr-4 text-ink-gray-7">
              <div class="flex flex-col gap-1">
                <span>{{ formatDate(row.valid_to) }}</span>
                <span
                  v-if="expiryLabel(row.days_to_expiry)"
                  class="inline-flex w-fit items-center rounded-full bg-red-100 px-2 py-0.5 text-p-xs font-medium text-red-800"
                >
                  {{ expiryLabel(row.days_to_expiry) }}
                </span>
              </div>
            </td>

            <!-- Giá trị -->
            <td class="border-b border-outline-gray-1 py-3 pr-4 text-right tabular-nums text-ink-gray-8">
              {{ formatCurrency(row.total_value) }}
            </td>

            <!-- % Quota: thanh bar màu theo health_color BE + số % -->
            <td class="border-b border-outline-gray-1 py-3 pr-4">
              <div class="flex items-center gap-2">
                <div
                  class="h-2 w-28 overflow-hidden rounded-full bg-ink-gray-2"
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
                <span class="min-w-[3rem] tabular-nums text-p-sm text-ink-gray-7">
                  {{ pctLabel(row.quota_used_pct) }}
                </span>
              </div>
            </td>

            <!-- Trạng thái chip -->
            <td class="border-b border-outline-gray-1 py-3 pr-4">
              <Badge
                v-if="row.status"
                variant="subtle"
                size="sm"
                :theme="statusTheme(row.status)"
                :label="row.status"
              />
              <span v-else class="text-ink-gray-5">—</span>
            </td>

            <!-- Thao tác: nút Chi tiết (stopPropagation để không double-fire row click) -->
            <td class="border-b border-outline-gray-1 py-3 text-right">
              <Button
                variant="outline"
                size="sm"
                :label="__('Chi tiết')"
                :aria-label="__('Xem chi tiết hợp đồng') + ' ' + (row.contract_no || row.name)"
                @click.stop="openContract(row.name)"
              />
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Tổng số (count==rows) -->
      <p
        v-if="!health.loading && !health.error && rows.length"
        class="pt-3 text-p-sm text-ink-gray-5"
      >
        {{ __('Tổng cộng') }}: {{ totalCount }} {{ __('hợp đồng') }}
      </p>

      <!--
        Widget "Danh mục VT trúng thầu — top 5" (mockup A2 chân màn, M02-5) — fetch ĐỘC LẬP
        với bảng Sức khỏe HĐ (lỗi 1 cái không vỡ cái kia). data đã sort GIẢM theo used_pct +
        cắt top ở BE ⇒ card KHÔNG sort lại, KHÔNG tự đặt ngưỡng màu (dùng health_color BE).
      -->
      <div class="pt-6">
        <AntmedTopQuotaItemsCard
          :items="topItems"
          :total-count="topItemsCount"
          :loading="topQuota.loading"
          :error="!!topQuota.error"
          @retry="topQuota.reload()"
        />
      </div>
    </section>
  </main>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { Badge, Button, toast } from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import AntmedTopQuotaItemsCard from '@/components/Antmed/AntmedTopQuotaItemsCard.vue'
import { getContractHealth, getTopQuotaItems, CONTRACT_WORKFLOW_THEME } from '@/data/antmed'
import { healthBarClass, expiryLabel, fmtDate as formatDate } from '@/utils/antmedUi'

const router = useRouter()

// Resource — endpoint trả dict bọc { data, total_count }, đọc r.data.data (KHÔNG createListResource).
const health = getContractHealth({ params: { start: 0, page_length: 50 }, auto: true })

const rows = computed(() => health.data?.data || [])
const totalCount = computed(() => health.data?.total_count ?? rows.value.length)

// Widget "Danh mục VT trúng thầu — top 5" — fetch ĐỘC LẬP (lỗi tách biệt bảng Sức khỏe HĐ).
// data đã sort GIẢM theo used_pct + cắt top ở BE ⇒ đọc r.data.data nguyên thứ tự (KHÔNG sort lại).
const topQuota = getTopQuotaItems({ params: { limit: 5 }, auto: true })
const topItems = computed(() => topQuota.data?.data || [])
const topItemsCount = computed(() => topQuota.data?.total_count ?? topItems.value.length)
topQuota.onError = (err) => {
  toast.error(err?.messages?.[0] || __('Không tải được danh mục vật tư trúng thầu'))
}

const errorMessage = computed(
  () =>
    health.error?.messages?.[0] ||
    health.error?.message ||
    __('Không tải được sức khỏe hợp đồng'),
)

// Surface lỗi BR-XX / permission từ BE qua toast (ngoài banner tri-branch).
health.onError = (err) => {
  toast.error(err?.messages?.[0] || __('Không tải được sức khỏe hợp đồng'))
}

function statusTheme(status) {
  return CONTRACT_WORKFLOW_THEME[status] || 'gray'
}

// formatDate (dd/MM/yyyy) gom về canon fmtDate @/utils/antmedUi (alias — template không đổi).

function formatCurrency(value) {
  if (value === null || value === undefined || value === '') return '—'
  const n = Number(value)
  if (Number.isNaN(n)) return String(value)
  return n.toLocaleString('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 })
}

// % Quota đã dùng (BE đã tính quota_used_pct) — clamp 0–100 cho width thanh; nhãn số.
function clampPct(value) {
  let p = Number(value)
  if (!Number.isFinite(p)) p = 0
  if (p < 0) p = 0
  if (p > 100) p = 100
  return Math.round(p)
}
function pctLabel(value) {
  const p = Number(value)
  if (!Number.isFinite(p)) return '0%'
  return `${Math.round(p)}%`
}

// Drill-down → Chi tiết HĐ (route AntmedContractDetail /antmed/contracts/:name đã đăng ký).
function openContract(name) {
  router.push({ name: 'AntmedContractDetail', params: { name } })
}
</script>
