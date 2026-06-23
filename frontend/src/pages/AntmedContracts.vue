<template>
  <main class="flex h-full flex-col" aria-labelledby="antmed-contracts-title">
    <!-- Header -->
    <header
      class="flex flex-col gap-3 border-b border-outline-gray-modals px-6 py-4 sm:flex-row sm:items-center sm:justify-between"
    >
      <div class="flex flex-col gap-1">
        <h1
          id="antmed-contracts-title"
          class="text-xl font-semibold text-ink-gray-9"
        >
          {{ __('Hợp đồng') }}
        </h1>
        <p class="text-p-sm text-ink-gray-6">
          {{
            __(
              'Danh mục hợp đồng / gói thầu trúng & hạn ngạch (quota) theo SKU',
            )
          }}
        </p>
      </div>
      <div class="w-full sm:w-72">
        <FormControl
          type="text"
          :placeholder="__('Tìm theo số hợp đồng…')"
          :modelValue="search"
          :aria-label="__('Tìm theo số hợp đồng')"
          @update:modelValue="onSearch"
        >
          <template #prefix>
            <FeatherIcon name="search" class="h-4 w-4 text-ink-gray-5" />
          </template>
        </FormControl>
      </div>
    </header>

    <!-- Bộ lọc: bệnh viện + trạng thái -->
    <div
      class="flex flex-col gap-3 px-6 py-3 sm:flex-row sm:items-end sm:gap-4"
    >
      <div class="flex flex-col gap-1 sm:w-64">
        <label
          for="contract-filter-hospital"
          class="text-p-xs font-medium text-ink-gray-6"
        >
          {{ __('Bệnh viện') }}
        </label>
        <FormControl
          id="contract-filter-hospital"
          type="select"
          :options="hospitalOptions"
          :modelValue="activeHospital"
          :aria-label="__('Lọc theo bệnh viện')"
          @update:modelValue="setHospital"
        />
      </div>
      <div class="flex flex-col gap-1 sm:w-56">
        <label
          for="contract-filter-status"
          class="text-p-xs font-medium text-ink-gray-6"
        >
          {{ __('Trạng thái') }}
        </label>
        <FormControl
          id="contract-filter-status"
          type="select"
          :options="statusOptions"
          :modelValue="activeStatus"
          :aria-label="__('Lọc theo trạng thái hợp đồng')"
          @update:modelValue="setStatus"
        />
      </div>
    </div>

    <!-- Tri-branch: loading / error / data -->
    <section class="flex-1 overflow-auto px-6 pb-6" aria-live="polite">
      <!-- Loading -->
      <div
        v-if="contracts.loading"
        class="flex items-center justify-center gap-2 py-16 text-ink-gray-6"
      >
        <LoadingIndicator class="h-4 w-4" />
        <span class="text-p-base">{{
          __('Đang tải danh sách hợp đồng…')
        }}</span>
      </div>

      <!-- Error -->
      <div
        v-else-if="contracts.error"
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
          @click="contracts.reload()"
        />
      </div>

      <!-- Empty -->
      <div
        v-else-if="!rows.length"
        class="flex flex-col items-center gap-2 py-16 text-center text-ink-gray-6"
      >
        <p class="text-p-base">
          {{ __('Chưa có hợp đồng nào khớp điều kiện.') }}
        </p>
        <p class="text-p-sm">
          {{
            __(
              'Hợp đồng được tạo bởi Quản lý trong Frappe Desk (AntMed Contract) rồi tải lại.',
            )
          }}
        </p>
      </div>

      <!-- Data table -->
      <table v-else class="w-full border-separate border-spacing-0 text-left">
        <caption class="sr-only">
          {{
            __('Danh sách hợp đồng')
          }}
        </caption>
        <thead>
          <tr class="text-p-sm text-ink-gray-6">
            <th
              class="border-b border-outline-gray-modals py-2 pr-4 font-medium"
            >
              {{ __('Số hợp đồng') }}
            </th>
            <th
              class="border-b border-outline-gray-modals py-2 pr-4 font-medium"
            >
              {{ __('Bệnh viện') }}
            </th>
            <th
              class="border-b border-outline-gray-modals py-2 pr-4 font-medium"
            >
              {{ __('Hiệu lực đến') }}
            </th>
            <th
              class="border-b border-outline-gray-modals py-2 pr-4 text-right font-medium"
            >
              {{ __('Giá trị HĐ') }}
            </th>
            <th class="border-b border-outline-gray-modals py-2 font-medium">
              {{ __('Trạng thái') }}
            </th>
          </tr>
        </thead>
        <tbody>
          <!--
            Drill-down ĐÃ MỞ (ADR-M02-07, supersede ADR-M02-06): route
            'AntmedContractDetail' (/antmed/contracts/:name) đã đăng ký ở router.js →
            dòng dữ liệu là affordance click/keyboard điều hướng tới màn Chi tiết HĐ.
          -->
          <tr
            v-for="row in rows"
            :key="row.name"
            role="link"
            tabindex="0"
            :aria-label="
              __('Xem chi tiết hợp đồng') + ' ' + (row.contract_no || row.name)
            "
            class="cursor-pointer text-p-base text-ink-gray-8 transition hover:bg-surface-gray-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
            @click="openContract(row.name)"
            @keydown.enter="openContract(row.name)"
          >
            <td
              class="border-b border-outline-gray-1 py-3 pr-4 font-medium text-ink-gray-9"
            >
              {{ row.contract_no || row.name }}
            </td>
            <td
              class="border-b border-outline-gray-1 py-3 pr-4 text-ink-gray-7"
            >
              {{ row.hospital_name || row.hospital || '—' }}
            </td>
            <td
              class="border-b border-outline-gray-1 py-3 pr-4 text-ink-gray-7"
            >
              {{ formatDate(row.valid_to) }}
            </td>
            <td
              class="border-b border-outline-gray-1 py-3 pr-4 text-right tabular-nums text-ink-gray-8"
            >
              {{ formatCurrency(row.total_value) }}
            </td>
            <td class="border-b border-outline-gray-1 py-3">
              <Badge
                v-if="row.status"
                variant="subtle"
                size="sm"
                :theme="statusTheme(row.status)"
                :label="row.status"
              />
              <span v-else class="text-ink-gray-5">—</span>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Tổng số (count==rows) -->
      <p
        v-if="!contracts.loading && !contracts.error && rows.length"
        class="pt-3 text-p-sm text-ink-gray-5"
      >
        {{ __('Tổng cộng') }}: {{ totalCount }} {{ __('hợp đồng') }}
      </p>
    </section>
  </main>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Badge, Button, FormControl, FeatherIcon, toast } from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import {
  listContracts,
  listHospitals,
  CONTRACT_WORKFLOW_THEME,
} from '@/data/antmed'

const router = useRouter()

// Options trạng thái — value khớp EXACT options DocType `AntMed Contract.status` (VI có dấu).
// value rỗng = Tất cả. KHÔNG hardcode chuỗi EN.
const statusOptions = [
  { value: '', label: __('Tất cả trạng thái') },
  { value: 'Nháp', label: __('Nháp') },
  { value: 'Hiệu lực', label: __('Hiệu lực') },
  { value: 'Sắp hết hạn', label: __('Sắp hết hạn') },
  { value: 'Hết hạn', label: __('Hết hạn') },
  { value: 'Đã huỷ', label: __('Đã huỷ') },
]

const search = ref('')
const activeHospital = ref('')
const activeStatus = ref('')

// Nguồn option BV cho dropdown lọc — permission-aware (chỉ BV user đọc được).
// allSettled-style: lỗi load BV KHÔNG làm sập trang HĐ (dropdown chỉ còn "Tất cả").
const hospitalsRef = listHospitals({
  params: { page_length: 0 },
  auto: true,
})
const hospitalOptions = computed(() => {
  const opts = [{ value: '', label: __('Tất cả bệnh viện') }]
  for (const h of hospitalsRef.data?.data || []) {
    opts.push({ value: h.name, label: h.hospital_name || h.name })
  }
  return opts
})

// FE→BE contract: filters PHẢI là JSON-string (BE _coerce_filters → frappe.parse_json).
// Object thô → createResource GET serialize "[object Object]" → BE parse lỗi → mất data.
function buildParams() {
  const filters = {}
  if (activeHospital.value) filters.hospital = activeHospital.value
  if (activeStatus.value) filters.status = activeStatus.value
  return { search: search.value, filters: JSON.stringify(filters) }
}

// Resource list HĐ — endpoint trả dict bọc { data, total_count }, đọc r.data.data.
const contracts = listContracts({
  params: buildParams(),
  auto: true,
})

const rows = computed(() => contracts.data?.data || [])
const totalCount = computed(
  () => contracts.data?.total_count ?? rows.value.length,
)

const errorMessage = computed(
  () =>
    contracts.error?.messages?.[0] ||
    contracts.error?.message ||
    __('Không tải được danh sách hợp đồng'),
)

function statusTheme(status) {
  return CONTRACT_WORKFLOW_THEME[status] || 'gray'
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

// Param phát đi == UI selection (chống dead-control LL-FE-13): rebuild filters từ
// hospital + status, search riêng → buildParams (JSON-string filters, BE _coerce_filters).
function refetch() {
  contracts.submit(buildParams())
}

let searchTimer = null
function onSearch(value) {
  search.value = value
  clearTimeout(searchTimer)
  searchTimer = setTimeout(refetch, 300)
}

function setHospital(value) {
  activeHospital.value = value
  refetch()
}

function setStatus(value) {
  activeStatus.value = value
  refetch()
}

// Drill-down list → detail (ADR-M02-07): route 'AntmedContractDetail' đã đăng ký →
// điều hướng tới màn Chi tiết HĐ theo name (KHÔNG dead-end no-match).
function openContract(name) {
  router.push({ name: 'AntmedContractDetail', params: { name } })
}

// Surface lỗi BR-XX / permission từ BE qua toast (ngoài banner tri-branch).
contracts.onError = (err) => {
  toast.error(err?.messages?.[0] || __('Không tải được danh sách hợp đồng'))
}
</script>
