<template>
  <main
    class="flex h-full flex-col overflow-auto"
    aria-labelledby="antmed-contract-detail-title"
  >
    <!-- Breadcrumb: quay lại danh sách hợp đồng -->
    <nav class="px-6 pt-4" :aria-label="__('Đường dẫn')">
      <Button
        variant="ghost"
        :label="__('Quay lại danh sách hợp đồng')"
        @click="goBack"
      >
        <template #prefix>
          <FeatherIcon name="arrow-left" class="h-4 w-4" />
        </template>
      </Button>
    </nav>

    <!-- Loading -->
    <div
      v-if="contract.loading"
      class="flex items-center justify-center gap-2 py-16 text-ink-gray-6"
      aria-live="polite"
    >
      <LoadingIndicator class="h-4 w-4" />
      <span class="text-p-base">{{ __('Đang tải chi tiết hợp đồng…') }}</span>
    </div>

    <!-- Error (KHÔNG leak stacktrace — chỉ message VI / fallback) -->
    <div
      v-else-if="contract.error"
      class="flex flex-col items-center gap-3 py-16 text-center"
      role="alert"
    >
      <Badge
        variant="subtle"
        theme="red"
        size="lg"
        :label="__('Không tải được')"
      />
      <p class="max-w-md text-p-sm text-ink-gray-6">{{ errorMessage }}</p>
      <Button
        variant="outline"
        :label="__('Thử lại')"
        @click="contract.reload()"
      />
    </div>

    <!-- Data -->
    <template v-else-if="contract.data">
      <!-- Header card HĐ -->
      <header class="px-6 py-5">
        <div class="flex flex-wrap items-center gap-3">
          <h1
            id="antmed-contract-detail-title"
            class="text-2xl font-semibold text-ink-gray-9"
          >
            {{ contract.data.contract_no || contract.data.name }}
          </h1>
          <Badge
            v-if="contract.data.status"
            variant="subtle"
            size="md"
            :theme="statusTheme(contract.data.status)"
            :label="contract.data.status"
          />
        </div>

        <dl
          class="mt-4 grid grid-cols-1 gap-x-8 gap-y-3 sm:grid-cols-2 lg:grid-cols-3"
        >
          <div class="flex flex-col gap-0.5">
            <dt class="text-p-xs uppercase tracking-wide text-ink-gray-5">
              {{ __('Bệnh viện') }}
            </dt>
            <dd class="text-p-base text-ink-gray-8">
              {{ contract.data.hospital_name || contract.data.hospital || '—' }}
            </dd>
          </div>
          <div class="flex flex-col gap-0.5">
            <dt class="text-p-xs uppercase tracking-wide text-ink-gray-5">
              {{ __('Ngày ký') }}
            </dt>
            <dd class="text-p-base text-ink-gray-8">
              {{ formatDate(contract.data.signed_date) }}
            </dd>
          </div>
          <div class="flex flex-col gap-0.5">
            <dt class="text-p-xs uppercase tracking-wide text-ink-gray-5">
              {{ __('Hiệu lực') }}
            </dt>
            <dd class="text-p-base text-ink-gray-8">
              {{ formatDate(contract.data.valid_from) }} –
              {{ formatDate(contract.data.valid_to) }}
            </dd>
          </div>
          <div class="flex flex-col gap-0.5">
            <dt class="text-p-xs uppercase tracking-wide text-ink-gray-5">
              {{ __('Tổng giá trị') }}
            </dt>
            <dd class="text-p-base font-medium tabular-nums text-ink-gray-9">
              {{ formatCurrency(contract.data.total_value) }}
            </dd>
          </div>
        </dl>
      </header>

      <!-- Card bảng quota tiêu hao -->
      <section class="px-6 pb-8" aria-labelledby="antmed-contract-quota-title">
        <h2
          id="antmed-contract-quota-title"
          class="mb-3 text-base font-semibold text-ink-gray-8"
        >
          {{ __('Hạn ngạch tiêu hao theo vật tư') }}
          <span class="text-ink-gray-5">({{ items.length }})</span>
        </h2>

        <!-- Empty-state quota (KHÔNG vỡ render) -->
        <div
          v-if="!items.length"
          class="rounded-xl bg-surface-gray-1 px-4 py-8 text-center text-p-sm text-ink-gray-6"
        >
          {{ __('Chưa có dòng quota') }}
        </div>

        <table v-else class="w-full border-separate border-spacing-0 text-left">
          <caption class="sr-only">
            {{
              __('Bảng hạn ngạch tiêu hao theo vật tư')
            }}
          </caption>
          <thead>
            <tr class="text-p-sm text-ink-gray-6">
              <th
                class="border-b border-outline-gray-modals py-2 pr-4 font-medium"
              >
                {{ __('Vật tư') }}
              </th>
              <th
                class="border-b border-outline-gray-modals py-2 pr-4 font-medium"
              >
                {{ __('ĐVT') }}
              </th>
              <th
                class="border-b border-outline-gray-modals py-2 pr-4 text-right font-medium"
              >
                {{ __('Đơn giá') }}
              </th>
              <th
                class="border-b border-outline-gray-modals py-2 pr-4 text-right font-medium"
              >
                {{ __('Quota') }}
              </th>
              <th
                class="border-b border-outline-gray-modals py-2 pr-4 text-right font-medium"
              >
                {{ __('Đã dùng') }}
              </th>
              <th
                class="border-b border-outline-gray-modals py-2 pr-4 font-medium"
              >
                {{ __('Đã tiêu hao') }}
              </th>
              <th class="border-b border-outline-gray-modals py-2 font-medium">
                {{ __('Khóa') }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(row, idx) in items"
              :key="row.item || idx"
              class="text-p-base text-ink-gray-8"
            >
              <td
                class="border-b border-outline-gray-1 py-3 pr-4 font-medium text-ink-gray-9"
              >
                {{ row.item_name || row.item || '—' }}
              </td>
              <td
                class="border-b border-outline-gray-1 py-3 pr-4 text-ink-gray-7"
              >
                {{ row.uom || '—' }}
              </td>
              <td
                class="border-b border-outline-gray-1 py-3 pr-4 text-right tabular-nums text-ink-gray-8"
              >
                {{ formatCurrency(row.unit_price) }}
              </td>
              <td
                class="border-b border-outline-gray-1 py-3 pr-4 text-right tabular-nums text-ink-gray-8"
              >
                {{ formatQty(row.quota_qty) }}
              </td>
              <td
                class="border-b border-outline-gray-1 py-3 pr-4 text-right tabular-nums text-ink-gray-8"
              >
                {{ formatQty(row.used_qty) }}
              </td>
              <!-- Thanh % đã tiêu hao: width + màu theo ngưỡng (đỏ≥95 / cam≥72 / xanh). -->
              <td class="border-b border-outline-gray-1 py-3 pr-4">
                <div class="flex items-center gap-2">
                  <div
                    class="h-2 w-28 overflow-hidden rounded-full bg-ink-gray-2"
                    role="progressbar"
                    :aria-valuenow="usedPct(row.remaining_pct)"
                    aria-valuemin="0"
                    aria-valuemax="100"
                    :aria-label="
                      __('Đã tiêu hao') +
                      ' ' +
                      Math.round(usedPct(row.remaining_pct)) +
                      '%'
                    "
                  >
                    <div
                      class="h-full rounded-full"
                      :class="barClass(row.remaining_pct)"
                      :style="{ width: usedPct(row.remaining_pct) + '%' }"
                    />
                  </div>
                  <span class="text-p-sm tabular-nums text-ink-gray-7">
                    {{ Math.round(usedPct(row.remaining_pct)) }}%
                  </span>
                </div>
              </td>
              <td class="border-b border-outline-gray-1 py-3">
                <Badge
                  v-if="row.lock_at_100"
                  variant="subtle"
                  size="sm"
                  theme="gray"
                  :label="__('Khóa khi đủ 100%')"
                />
                <span v-else class="text-ink-gray-5">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- Widget "Tiêu hao HĐ theo tháng" (mockup A1, M02-6) — DƯỚI bảng quota.
           Fetch ĐỘC LẬP với getContract (resource consumption riêng) → lỗi/loading tách biệt:
           lỗi widget KHÔNG làm vỡ trang chi tiết HĐ. -->
      <section class="px-6 pb-10" aria-labelledby="antmed-consumption-title">
        <AntmedConsumptionChartCard
          :data="consumption.data?.data || []"
          :total-qty="consumption.data?.total_qty || 0"
          :contract-no="contract.data.contract_no || contract.data.name"
          :hospital-name="contract.data.hospital_name || contract.data.hospital"
          :loading="consumption.loading"
          :error="consumption.error"
          @retry="consumption.reload()"
        />
      </section>

      <!-- Hoạt động: dòng thời gian Ghi chú + Công việc gắn HĐ này
           (port FCRM Note + CRM Task → dùng cho AntMed, qua reference_doctype/docname). -->
      <section class="px-6 pb-10" :aria-label="__('Hoạt động hợp đồng')">
        <AntmedActivityPanel
          reference-doctype="AntMed Contract"
          :reference-docname="contract.data.name"
        />
      </section>
    </template>
  </main>
</template>

<script setup>
import { computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Badge, Button, FeatherIcon, toast } from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import AntmedConsumptionChartCard from '@/components/Antmed/AntmedConsumptionChartCard.vue'
import AntmedActivityPanel from '@/components/Antmed/AntmedActivityPanel.vue'
import {
  getContract,
  getContractConsumptionByMonth,
  CONTRACT_WORKFLOW_THEME,
} from '@/data/antmed'
import { quotaUsedPct, quotaBarClass } from '@/utils/antmedUi'

const props = defineProps({
  name: { type: String, required: true },
})

const router = useRouter()

// Endpoint get_contract trả RAW dict { ...header, items: [...] } — đọc r.data.items
// TRỰC TIẾP (KHÔNG r.data.data — đây KHÔNG phải list-wrap endpoint).
const contract = getContract({
  params: { name: props.name },
  auto: true,
})

// Widget "Tiêu hao HĐ theo tháng" (M02-6) — resource RIÊNG, fetch ĐỘC LẬP với getContract
// (lỗi/loading tách biệt → lỗi widget KHÔNG làm vỡ trang chi tiết HĐ). Đọc r.data.data (dict bọc).
const consumption = getContractConsumptionByMonth({
  params: { contract: props.name },
  auto: true,
})
consumption.onError = (err) => {
  toast.error(
    err?.messages?.[0] || __('Không tải được dữ liệu tiêu hao theo tháng'),
  )
}

// Re-fetch khi điều hướng giữa các HĐ (component tái dùng theo :name) — cả 2 resource độc lập.
watch(
  () => props.name,
  (name) => {
    contract.submit({ name })
    consumption.submit({ contract: name })
  },
)

const items = computed(() => contract.data?.items || [])

const errorMessage = computed(
  () =>
    contract.error?.messages?.[0] ||
    contract.error?.message ||
    __('Không tải được chi tiết hợp đồng'),
)

function statusTheme(status) {
  return CONTRACT_WORKFLOW_THEME[status] || 'gray'
}

// % đã tiêu hao + class thanh bar — tầng thuần (utils/antmedUi), ngưỡng đỏ≥95/cam≥72/xanh.
function usedPct(remainingPct) {
  return quotaUsedPct(remainingPct)
}
function barClass(remainingPct) {
  return quotaBarClass(remainingPct)
}

function formatDate(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleDateString('vi-VN')
}

function formatCurrency(value) {
  if (value === null || value === undefined || value === '') return '—'
  const n = Number(value)
  if (Number.isNaN(n)) return String(value)
  return n.toLocaleString('vi-VN', {
    style: 'currency',
    currency: 'VND',
    maximumFractionDigits: 0,
  })
}

function formatQty(value) {
  if (value === null || value === undefined || value === '') return '—'
  const n = Number(value)
  if (Number.isNaN(n)) return String(value)
  return n.toLocaleString('vi-VN')
}

function goBack() {
  router.push({ name: 'AntmedContracts' })
}

contract.onError = (err) => {
  toast.error(err?.messages?.[0] || __('Không tải được chi tiết hợp đồng'))
}
</script>
