<template>
  <main class="flex h-full flex-col" aria-labelledby="antmed-checklist-title">
    <header class="flex flex-col gap-2 border-b border-outline-gray-modals px-6 py-4">
      <nav class="text-p-xs text-ink-gray-5" :aria-label="__('Đường dẫn')">
        <RouterLink to="/antmed" class="rounded text-ink-gray-6 hover:text-ink-gray-8">{{ __('Trang chủ') }}</RouterLink>
        <span class="px-1.5 text-ink-gray-4" aria-hidden="true">›</span>
        <RouterLink to="/antmed/instruments" class="rounded text-ink-gray-6 hover:text-ink-gray-8">{{ __('Bộ dụng cụ') }}</RouterLink>
        <span class="px-1.5 text-ink-gray-4" aria-hidden="true">›</span>
        <span class="text-ink-gray-7" aria-current="page">{{ __('Checklist') }} {{ name }}</span>
      </nav>
      <div class="flex flex-wrap items-center gap-3">
        <h1 id="antmed-checklist-title" class="text-xl font-semibold text-ink-gray-9">
          🧰 {{ loan.set_code || loan.instrument_set || '—' }}
          <span v-if="loan.surgery_type" class="text-ink-gray-6">· {{ loan.surgery_type }}</span>
        </h1>
        <Badge v-if="loan.status" variant="subtle" :theme="statusTheme(loan.status)" size="md" :label="loan.status" />
        <Badge v-if="loan.is_overdue" variant="subtle" theme="red" size="md" :label="__('Quá hạn')" />
      </div>
    </header>

    <section class="flex-1 overflow-auto px-6 pb-8 pt-4" aria-live="polite">
      <div v-if="resource.loading" class="flex items-center justify-center gap-2 py-16 text-ink-gray-6">
        <LoadingIndicator class="h-4 w-4" />
        <span class="text-p-base">{{ __('Đang tải…') }}</span>
      </div>

      <div v-else-if="resource.error" class="flex flex-col items-center gap-3 py-16 text-center" role="alert">
        <Badge variant="subtle" theme="red" size="lg" :label="__('Không tải được')" />
        <p class="max-w-md text-p-sm text-ink-gray-6">{{ errorMessage }}</p>
        <Button variant="outline" :label="__('Thử lại')" @click="resource.reload()" />
      </div>

      <template v-else>
        <!-- Bối cảnh ca mổ -->
        <div class="mb-5 rounded-lg border border-outline-gray-2 bg-surface-white p-4">
          <p class="text-p-xs uppercase text-ink-gray-5">{{ __('Ca mổ') }}</p>
          <p class="text-p-base font-semibold text-ink-gray-9">{{ loan.surgery_case || '—' }}</p>
          <p class="mt-1 text-p-sm text-ink-gray-6">
            <template v-if="loan.hospital_name">🏥 {{ loan.hospital_name }}</template>
            <template v-if="loan.doctor_name"> · 👨‍⚕️ {{ loan.doctor_name }}</template>
            <template v-if="loan.employee_name"> · NV: {{ loan.employee_name }}</template>
          </p>
          <p class="mt-1 text-p-xs text-ink-gray-5">
            {{ __('Đặt') }}: {{ fmtDate(loan.booked_at) }} · {{ __('Hẹn trả') }}: {{ fmtDate(loan.due_return_at) }}
          </p>
        </div>

        <!-- Checklist nhận / bàn giao -->
        <div class="rounded-lg border border-outline-gray-2 bg-surface-white p-4">
          <div class="mb-3 flex items-center justify-between gap-2">
            <h2 class="text-p-base font-semibold text-ink-gray-8">
              {{ __('Checklist bộ dụng cụ') }} · {{ __('đủ {0}/{1} món', [okCount, editItems.length]) }}
            </h2>
            <Button
              v-if="canEdit"
              variant="subtle"
              :loading="saveChecklist.loading"
              :label="__('Lưu checklist')"
              @click="onSave"
            />
          </div>

          <p v-if="!editItems.length" class="text-p-sm text-ink-gray-5">{{ __('Lượt mượn này chưa có danh mục món.') }}</p>

          <ul v-else class="flex flex-col divide-y divide-outline-gray-1">
            <li
              v-for="(it, i) in editItems"
              :key="it.component_name + i"
              class="flex flex-wrap items-center gap-x-3 gap-y-1 py-2"
            >
              <span class="min-w-0 flex-1 text-p-base text-ink-gray-8">
                {{ it.component_name }}
                <span class="text-p-xs text-ink-gray-4">× {{ it.expected }}</span>
              </span>
              <span v-if="it.photo" class="text-p-xs text-teal-600" :title="__('Có ảnh đính kèm')">📷</span>

              <!-- Control tình trạng (live): chọn → editItems cập nhật → save gửi đúng giá trị -->
              <label v-if="canEdit" class="flex items-center gap-1.5">
                <span class="sr-only">{{ __('Tình trạng món {0}', [it.component_name]) }}</span>
                <select
                  v-model="it.condition"
                  class="rounded-md border border-outline-gray-2 px-2 py-1 text-p-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
                  :aria-label="__('Tình trạng món {0}', [it.component_name])"
                >
                  <option v-for="opt in CONDITION_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
                </select>
              </label>
              <Badge
                v-else
                variant="subtle"
                :theme="conditionTheme(it.condition)"
                size="sm"
                :label="conditionLabel(it.condition)"
              />
            </li>
          </ul>
        </div>

        <!-- Hành động vòng đời (1 nút chính theo trạng thái) -->
        <div v-if="primaryAction" class="mt-5 flex flex-wrap items-center gap-3">
          <Button
            variant="solid"
            theme="teal"
            :loading="actionLoading"
            :label="primaryAction.label"
            @click="primaryAction.run()"
          />
          <span class="text-p-xs text-ink-gray-5">{{ primaryAction.hint }}</span>
        </div>
        <p v-else class="mt-5 text-p-sm text-ink-gray-5">{{ __('Lượt mượn đã khép vòng đời — không còn thao tác.') }}</p>
      </template>
    </section>
  </main>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { Badge, Button, createResource, toast } from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import {
  getInstrumentLoan,
  INSTRUMENT_STATUS_THEME,
  COMPONENT_CONDITION_THEME,
} from '@/data/antmed'

const props = defineProps({ name: { type: String, required: true } })

const BASE = 'antmed_crm.api.antmed.instrument_loan'
const CONDITION_OPTIONS = [
  { value: 'OK', label: __('Đủ') },
  { value: 'Missing', label: __('Thiếu') },
  { value: 'Damaged', label: __('Hỏng') },
]

const resource = getInstrumentLoan({ params: { name: props.name }, auto: true })
resource.onError = (err) => toast.error(err?.messages?.[0] || __('Không tải được lượt mượn'))

const loan = computed(() => resource.data || {})

// Bản sao cục bộ checklist nhận để chỉnh tình trạng trước khi lưu.
const editItems = ref([])
watch(
  () => resource.data,
  (d) => {
    editItems.value = (d?.handover_checklist || []).map((c) => ({
      component_name: c.component_name,
      expected: c.expected,
      condition: c.condition || 'OK',
      photo: c.photo,
    }))
  },
  { immediate: true },
)

const okCount = computed(() => editItems.value.filter((it) => it.condition === 'OK').length)
// Sửa được khi lượt mới ở 'Đã đặt' và chưa submit (sau bàn giao → khoá).
const canEdit = computed(() => loan.value.status === 'Đã đặt' && loan.value.docstatus === 0)

function statusTheme(s) {
  return INSTRUMENT_STATUS_THEME[s] || 'gray'
}
function conditionTheme(c) {
  return COMPONENT_CONDITION_THEME[c] || 'gray'
}
function conditionLabel(c) {
  return CONDITION_OPTIONS.find((o) => o.value === c)?.label || c || '—'
}

// ── Action resources (POST) — mỗi action reload + toast ──────────────────────
const saveChecklist = createResource({
  url: `${BASE}.save_checklist`,
  method: 'POST',
  onSuccess() {
    toast.success(__('Đã lưu checklist'))
    resource.reload()
  },
  onError: (err) => toast.error(err?.messages?.[0] || __('Lưu checklist thất bại')),
})
function onSave() {
  saveChecklist.submit({
    loan: props.name,
    kind: 'handover',
    items_json: JSON.stringify(
      editItems.value.map((it) => ({ component_name: it.component_name, condition: it.condition })),
    ),
  })
}

function makeAction(fn, successMsg, extra = {}) {
  const r = createResource({
    url: `${BASE}.${fn}`,
    method: 'POST',
    onSuccess() {
      toast.success(successMsg)
      resource.reload()
    },
    onError: (err) => toast.error(err?.messages?.[0] || __('Thao tác thất bại')),
  })
  return { r, run: () => r.submit({ loan: props.name, ...extra }) }
}

const handover = makeAction('handover', __('Đã hoàn tất bàn giao mượn'))
const receiveReturn = makeAction('receive_return', __('Đã nhận bộ về kho NV'))
const sterilize = makeAction('sterilize', __('Đã ghi nhận tiệt khuẩn'), { method: 'Hấp', result: 'Pass' })
const markReady = makeAction('mark_ready', __('Bộ đã sẵn sàng cho lượt mượn kế'))

const ACTION_BY_STATUS = {
  'Đã đặt': { a: handover, label: __('Hoàn tất bàn giao mượn'), hint: __('Ký nhận & chuyển sang Đang sử dụng tại BV') },
  'Đang sử dụng tại BV': { a: receiveReturn, label: __('Nhận bộ về kho NV'), hint: __('Sau ca mổ — chuyển sang Đã trả về NV KD') },
  'Đã trả về NV KD': { a: sterilize, label: __('Gửi tiệt khuẩn (Hấp)'), hint: __('Ghi nhận tiệt khuẩn để chuẩn bị sẵn sàng') },
  'Đang xử lý/tiệt khuẩn': { a: markReady, label: __('Đánh dấu sẵn sàng'), hint: __('Yêu cầu có kết quả tiệt khuẩn Pass (BR-09)') },
}

const primaryAction = computed(() => {
  const cfg = ACTION_BY_STATUS[loan.value.status]
  if (!cfg) return null
  return { label: cfg.label, hint: cfg.hint, run: cfg.a.run }
})
const actionLoading = computed(() =>
  [handover, receiveReturn, sterilize, markReady].some((x) => x.r.loading),
)

const errorMessage = computed(
  () => resource.error?.messages?.[0] || resource.error?.message || __('Không tải được lượt mượn'),
)
</script>
