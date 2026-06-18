<template>
  <main
    class="flex h-full flex-col"
    aria-labelledby="antmed-delivery-detail-title"
  >
    <!-- Header -->
    <header
      class="flex flex-col gap-3 border-b border-outline-gray-modals px-6 py-4"
    >
      <div class="flex items-center gap-2">
        <Button variant="ghost" :label="__('Quay lại')" @click="goBack">
          <template #prefix>
            <FeatherIcon name="arrow-left" class="h-4 w-4" />
          </template>
        </Button>
      </div>
      <div
        class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between"
      >
        <div class="flex flex-col gap-1">
          <h1
            id="antmed-delivery-detail-title"
            class="text-xl font-semibold text-ink-gray-9"
          >
            {{ __('Phiếu giao') }} {{ name }}
          </h1>
          <p class="text-p-sm text-ink-gray-6">
            {{ detail.data?.hospital_name || detail.data?.hospital || '—' }}
          </p>
        </div>
        <div class="flex items-center gap-2">
          <Badge
            v-if="detail.data?.status"
            variant="subtle"
            size="lg"
            :theme="statusTheme(detail.data.status)"
            :label="detail.data.status"
          />
          <Badge
            v-if="detail.data?.sla_status"
            variant="subtle"
            size="lg"
            :theme="slaTheme(detail.data.sla_status)"
            :label="slaLabel(detail.data.sla_status)"
          />
        </div>
      </div>

      <!-- S2: hành động vòng đời (BE assign / start_transit / handover) — hiện theo state hiện tại -->
      <div
        v-if="detail.data && (canAssign || canStart || canHandover)"
        class="flex flex-wrap items-end gap-2"
      >
        <template v-if="canAssign">
          <FormControl
            type="select"
            class="min-w-[12rem]"
            :options="employeeOptions"
            :modelValue="selectedEmployee"
            :aria-label="__('Chọn NV phụ trách')"
            @update:modelValue="(v) => (selectedEmployee = v)"
          />
          <Button
            variant="solid"
            :label="__('Gán NV')"
            :loading="assignRes.loading"
            :disabled="!selectedEmployee"
            @click="doAssign"
          />
        </template>
        <Button
          v-if="canStart"
          variant="solid"
          :label="__('Bắt đầu giao')"
          :loading="startRes.loading"
          @click="doStart"
        />
        <Button
          v-if="canHandover"
          variant="solid"
          :label="__('Bàn giao phòng mổ')"
          :loading="handoverRes.loading"
          @click="doHandover"
        />
      </div>
    </header>

    <section class="flex-1 overflow-auto px-6 py-5" aria-live="polite">
      <!-- Loading -->
      <div
        v-if="detail.loading"
        class="flex items-center justify-center gap-2 py-16 text-ink-gray-6"
      >
        <LoadingIndicator class="h-4 w-4" />
        <span class="text-p-base">{{
          __('Đang tải chi tiết phiếu giao…')
        }}</span>
      </div>

      <!-- Error -->
      <div
        v-else-if="detail.error"
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
          @click="detail.reload()"
        />
      </div>

      <!-- Data -->
      <div v-else-if="detail.data" class="flex flex-col gap-6">
        <!-- Thông tin chung -->
        <dl
          class="grid grid-cols-1 gap-x-8 gap-y-4 sm:grid-cols-2 lg:grid-cols-3"
        >
          <div v-for="f in fields" :key="f.label" class="flex flex-col gap-0.5">
            <dt class="text-p-sm text-ink-gray-5">{{ f.label }}</dt>
            <dd class="text-p-base text-ink-gray-8">{{ f.value }}</dd>
          </div>
        </dl>

        <!-- Items -->
        <div class="flex flex-col gap-2">
          <h2 class="text-p-base font-semibold text-ink-gray-9">
            {{ __('Vật tư trong phiếu') }}
          </h2>
          <div
            v-if="!items.length"
            class="rounded-lg border border-outline-gray-1 px-4 py-6 text-center text-p-sm text-ink-gray-5"
          >
            {{ __('Phiếu chưa có dòng vật tư nào.') }}
          </div>
          <table
            v-else
            class="w-full border-separate border-spacing-0 text-left"
          >
            <caption class="sr-only">
              {{
                __('Danh sách vật tư trong phiếu giao')
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
                  {{ __('Lô') }}
                </th>
                <th
                  class="border-b border-outline-gray-modals py-2 pr-4 font-medium"
                >
                  {{ __('ĐVT') }}
                </th>
                <th
                  class="border-b border-outline-gray-modals py-2 pr-4 font-medium text-right"
                >
                  {{ __('SL yêu cầu') }}
                </th>
                <th
                  class="border-b border-outline-gray-modals py-2 pr-4 font-medium text-right"
                >
                  {{ __('SL giao') }}
                </th>
                <th
                  class="border-b border-outline-gray-modals py-2 pr-4 font-medium text-right"
                >
                  {{ __('SL dùng') }}
                </th>
                <th
                  class="border-b border-outline-gray-modals py-2 font-medium text-right"
                >
                  {{ __('SL trả') }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(it, idx) in items"
                :key="idx"
                class="text-p-base text-ink-gray-8"
              >
                <td
                  class="border-b border-outline-gray-1 py-3 pr-4 font-medium text-ink-gray-9"
                >
                  {{ it.item_name || it.item || '—' }}
                </td>
                <td
                  class="border-b border-outline-gray-1 py-3 pr-4 text-ink-gray-7"
                >
                  {{ it.lot || '—' }}
                </td>
                <td
                  class="border-b border-outline-gray-1 py-3 pr-4 text-ink-gray-7"
                >
                  {{ it.uom || '—' }}
                </td>
                <td class="border-b border-outline-gray-1 py-3 pr-4 text-right">
                  {{ fmtQty(it.requested_qty) }}
                </td>
                <td class="border-b border-outline-gray-1 py-3 pr-4 text-right">
                  {{ fmtQty(it.delivered_qty) }}
                </td>
                <td class="border-b border-outline-gray-1 py-3 pr-4 text-right">
                  {{ fmtQty(it.consumed_qty) }}
                </td>
                <td class="border-b border-outline-gray-1 py-3 text-right">
                  {{ fmtQty(it.returned_qty) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Hoạt động: Ghi chú + Công việc gắn phiếu giao này (port FCRM Note + CRM Task → AntMed). -->
        <AntmedActivityPanel
          reference-doctype="AntMed Delivery"
          :reference-docname="name"
        />
      </div>
    </section>
  </main>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  Badge,
  Button,
  FeatherIcon,
  FormControl,
  createResource,
  toast,
} from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import AntmedActivityPanel from '@/components/Antmed/AntmedActivityPanel.vue'
import {
  getDelivery,
  DELIVERY_STATUS_THEME,
  SLA_STATUS_THEME,
  SLA_STATUS_LABEL,
} from '@/data/antmed'

const props = defineProps({ name: { type: String, required: true } })
const router = useRouter()

// Resource chi tiết — get_delivery(name) trả dict THƯỜNG (KHÔNG bọc { data }).
const detail = getDelivery({
  params: { name: props.name },
  auto: true,
})

const items = computed(() => detail.data?.items || [])

// ── S2: hành động vòng đời (BE delivery.assign / start_transit / handover, POST qua .submit) ──
const status = computed(() => detail.data?.status || '')
const canAssign = computed(() =>
  ['Nháp', 'Đã phân loại'].includes(status.value),
)
const canStart = computed(() => status.value === 'Đã gán NV')
const canHandover = computed(() => status.value === 'Đang giao')

// Nguồn NV cho dropdown 'Gán NV' — value=user gửi BE, label=full_name hiển thị (KHÔNG leak email).
const assignableEmployees = createResource({
  url: 'antmed_crm.api.antmed.delivery.list_assignable_employees',
  method: 'GET',
  auto: true,
})
const employeeOptions = computed(() => [
  { label: __('— Chọn NV phụ trách —'), value: '' },
  ...(assignableEmployees.data?.data || []),
])
const selectedEmployee = ref('')

function reloadAfter(msg) {
  toast.success(msg)
  detail.reload()
}

const assignRes = createResource({
  url: 'antmed_crm.api.antmed.delivery.assign',
  onSuccess: () => reloadAfter(__('Đã gán NV phụ trách')),
  onError: (err) => toast.error(err?.messages?.[0] || __('Gán NV thất bại')),
})
function doAssign() {
  if (!selectedEmployee.value) return
  assignRes.submit({
    name: props.name,
    assigned_employee: selectedEmployee.value,
  })
}

const startRes = createResource({
  url: 'antmed_crm.api.antmed.delivery.start_transit',
  onSuccess: () => reloadAfter(__('Đã bắt đầu giao')),
  onError: (err) => toast.error(err?.messages?.[0] || __('Không bắt đầu được')),
})
function doStart() {
  startRes.submit({ name: props.name })
}

const handoverRes = createResource({
  url: 'antmed_crm.api.antmed.delivery.handover',
  onSuccess: () => reloadAfter(__('Đã bàn giao phòng mổ')),
  onError: (err) =>
    toast.error(err?.messages?.[0] || __('Không bàn giao được')),
})
function doHandover() {
  handoverRes.submit({ name: props.name })
}

// Thông tin chung — KHÔNG leak email NV (assigned_employee = Link User): hiển thị "Đã gán/Chưa gán".
const fields = computed(() => {
  const d = detail.data || {}
  return [
    { label: __('Bệnh viện'), value: d.hospital_name || d.hospital || '—' },
    { label: __('Bác sỹ'), value: d.doctor_name || d.doctor || '—' },
    { label: __('Phòng mổ'), value: d.surgery_room || '—' },
    { label: __('Giờ phẫu thuật'), value: formatDateTime(d.surgery_datetime) },
    { label: __('SLA (phút)'), value: d.sla_minutes ?? '—' },
    { label: __('Hợp đồng'), value: d.contract || '—' },
    {
      label: __('Nhân viên'),
      value: d.assigned_employee_name || __('Chưa gán'),
    },
    { label: __('Đã giao lúc'), value: formatDateTime(d.delivered_at) },
    { label: __('Ghi chú'), value: d.notes || '—' },
  ]
})

const errorMessage = computed(
  () =>
    detail.error?.messages?.[0] ||
    detail.error?.message ||
    __('Không tải được chi tiết phiếu giao'),
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
function fmtQty(value) {
  if (value === null || value === undefined || value === '') return '—'
  const n = Number(value)
  return Number.isNaN(n) ? String(value) : n.toLocaleString('vi-VN')
}

function goBack() {
  router.push({ name: 'AntmedDeliveries' })
}

detail.onError = (err) => {
  toast.error(err?.messages?.[0] || __('Không tải được chi tiết phiếu giao'))
}
</script>
