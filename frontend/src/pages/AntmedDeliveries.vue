<template>
  <main class="flex h-full flex-col" aria-labelledby="antmed-deliveries-title">
    <!-- Header -->
    <header
      class="flex flex-col gap-3 border-b border-outline-gray-modals px-6 py-4 sm:flex-row sm:items-center sm:justify-between"
    >
      <div class="flex flex-col gap-1">
        <h1 id="antmed-deliveries-title" class="text-xl font-semibold text-ink-gray-9">
          {{ __('Giao phòng mổ') }}
        </h1>
        <p class="text-p-sm text-ink-gray-6">
          {{ __('Danh sách phiếu giao vật tư tới phòng mổ — vòng đời & SLA') }}
        </p>
      </div>
    </header>

    <!-- Chip lọc theo trạng thái -->
    <div
      class="flex flex-wrap items-center gap-2 px-6 py-3"
      role="group"
      :aria-label="__('Lọc theo trạng thái phiếu giao')"
    >
      <button
        v-for="opt in statusOptions"
        :key="opt.value || 'all'"
        type="button"
        :aria-pressed="activeStatus === opt.value"
        class="rounded-full px-3 py-1 text-p-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
        :class="
          activeStatus === opt.value
            ? 'bg-surface-gray-7 text-ink-white'
            : 'bg-surface-gray-2 text-ink-gray-7 hover:bg-surface-gray-3'
        "
        @click="setStatus(opt.value)"
      >
        {{ opt.label }}
      </button>
    </div>

    <!-- Tri-branch: loading / error / data -->
    <section class="flex-1 overflow-auto px-6 pb-6" aria-live="polite">
      <!-- Loading -->
      <div
        v-if="deliveries.loading"
        class="flex items-center justify-center gap-2 py-16 text-ink-gray-6"
      >
        <LoadingIndicator class="h-4 w-4" />
        <span class="text-p-base">{{ __('Đang tải danh sách phiếu giao…') }}</span>
      </div>

      <!-- Error -->
      <div
        v-else-if="deliveries.error"
        class="flex flex-col items-center gap-3 py-16 text-center"
        role="alert"
      >
        <Badge variant="subtle" theme="red" size="lg" :label="__('Không tải được')" />
        <p class="max-w-md text-p-sm text-ink-gray-6">{{ errorMessage }}</p>
        <Button variant="outline" :label="__('Thử lại')" @click="deliveries.reload()" />
      </div>

      <!-- Empty -->
      <div
        v-else-if="!rows.length"
        class="flex flex-col items-center gap-2 py-16 text-center text-ink-gray-6"
      >
        <p class="text-p-base">{{ __('Chưa có phiếu giao nào khớp điều kiện.') }}</p>
        <p class="text-p-sm">
          {{ __('Tạo phiếu giao trong Frappe Desk (AntMed Delivery) rồi tải lại.') }}
        </p>
      </div>

      <!-- Data table -->
      <table v-else class="w-full border-separate border-spacing-0 text-left">
        <caption class="sr-only">
          {{ __('Danh sách phiếu giao phòng mổ') }}
        </caption>
        <thead>
          <tr class="text-p-sm text-ink-gray-6">
            <th class="border-b border-outline-gray-modals py-2 pr-4 font-medium">
              {{ __('Bệnh viện') }}
            </th>
            <th class="border-b border-outline-gray-modals py-2 pr-4 font-medium">
              {{ __('Bác sỹ') }}
            </th>
            <th class="border-b border-outline-gray-modals py-2 pr-4 font-medium">
              {{ __('Giờ phẫu thuật') }}
            </th>
            <th class="border-b border-outline-gray-modals py-2 pr-4 font-medium">
              {{ __('Trạng thái') }}
            </th>
            <th class="border-b border-outline-gray-modals py-2 pr-4 font-medium">
              {{ __('SLA') }}
            </th>
            <th class="border-b border-outline-gray-modals py-2 font-medium">
              {{ __('Nhân viên') }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in rows"
            :key="row.name"
            tabindex="0"
            role="link"
            :aria-label="__('Xem chi tiết phiếu giao') + ' ' + (row.hospital_name || row.name)"
            class="cursor-pointer text-p-base text-ink-gray-8 transition hover:bg-surface-gray-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
            @click="openDelivery(row.name)"
            @keydown.enter="openDelivery(row.name)"
            @keydown.space.prevent="openDelivery(row.name)"
          >
            <td class="border-b border-outline-gray-1 py-3 pr-4 font-medium text-ink-gray-9">
              {{ row.hospital_name || row.hospital || '—' }}
            </td>
            <td class="border-b border-outline-gray-1 py-3 pr-4 text-ink-gray-7">
              {{ row.doctor_name || '—' }}
            </td>
            <td class="border-b border-outline-gray-1 py-3 pr-4 text-ink-gray-7">
              {{ formatDateTime(row.surgery_datetime) }}
            </td>
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
            <td class="border-b border-outline-gray-1 py-3 pr-4">
              <Badge
                v-if="row.sla_status"
                variant="subtle"
                size="sm"
                :theme="slaTheme(row.sla_status)"
                :label="slaLabel(row.sla_status)"
              />
              <span v-else class="text-ink-gray-5">—</span>
            </td>
            <td class="border-b border-outline-gray-1 py-3">
              <span v-if="row.assigned_employee_name" class="text-ink-gray-8">{{
                row.assigned_employee_name
              }}</span>
              <span v-else class="text-p-sm text-ink-gray-5">{{ __('Chưa gán') }}</span>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Tổng số (count==rows) -->
      <p
        v-if="!deliveries.loading && !deliveries.error && rows.length"
        class="pt-3 text-p-sm text-ink-gray-5"
      >
        {{ __('Tổng cộng') }}: {{ totalCount }} {{ __('phiếu giao') }}
      </p>
    </section>
  </main>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Badge, Button, toast } from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import {
  listDeliveries,
  DELIVERY_STATUS_ORDER,
  DELIVERY_STATUS_THEME,
  SLA_STATUS_THEME,
  SLA_STATUS_LABEL,
} from '@/data/antmed'

const router = useRouter()

// Options trạng thái — value khớp EXACT options DocType `AntMed Delivery.status` (VI có dấu).
// value rỗng = Tất cả. Nhãn = chính giá trị BE (KHÔNG đặt tên "thân thiện" lệch key).
const statusOptions = [
  { value: '', label: __('Tất cả') },
  ...DELIVERY_STATUS_ORDER.map((s) => ({ value: s, label: __(s) })),
]

const activeStatus = ref('')

// FE→BE: lọc theo trạng thái dùng param `status` (string) — KHÔNG object filters
// (createResource GET serialize object thô thành "[object Object]" → BE parse lỗi).
function buildParams() {
  return { status: activeStatus.value }
}

// Resource list — endpoint trả dict bọc { data, total_count }, đọc r.data.data.
const deliveries = listDeliveries({
  params: buildParams(),
  auto: true,
})

const rows = computed(() => deliveries.data?.data || [])
const totalCount = computed(() => deliveries.data?.total_count ?? rows.value.length)

const errorMessage = computed(
  () =>
    deliveries.error?.messages?.[0] ||
    deliveries.error?.message ||
    __('Không tải được danh sách phiếu giao'),
)

function statusTheme(status) {
  return DELIVERY_STATUS_THEME[status] || 'gray'
}
function slaTheme(sla) {
  return SLA_STATUS_THEME[sla] || 'gray'
}
function slaLabel(sla) {
  return SLA_STATUS_LABEL[sla] || sla
}

function formatDateTime(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString('vi-VN')
}

// Param phát đi == UI selection (chống dead-control): rebuild params từ trạng thái đang chọn.
function refetch() {
  deliveries.submit(buildParams())
}

function setStatus(value) {
  activeStatus.value = value
  refetch()
}

function openDelivery(name) {
  router.push({ name: 'AntmedDeliveryDetail', params: { name } })
}

// Surface lỗi BR-XX / permission từ BE qua toast (ngoài banner tri-branch).
deliveries.onError = (err) => {
  toast.error(err?.messages?.[0] || __('Không tải được danh sách phiếu giao'))
}
</script>
