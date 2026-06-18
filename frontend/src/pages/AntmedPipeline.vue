<template>
  <main class="flex h-full flex-col" aria-labelledby="antmed-pipeline-title">
    <header class="flex flex-col gap-2 border-b border-outline-gray-modals px-6 py-4">
      <nav class="text-p-xs text-ink-gray-5" :aria-label="__('Đường dẫn')">
        <RouterLink to="/antmed" class="rounded text-ink-gray-6 hover:text-ink-gray-8">{{ __('Trang chủ') }}</RouterLink>
        <span class="px-1.5 text-ink-gray-4" aria-hidden="true">›</span>
        <span class="text-ink-gray-7" aria-current="page">{{ __('Pipeline gói thầu') }}</span>
      </nav>
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 id="antmed-pipeline-title" class="text-xl font-semibold text-ink-gray-9">🎯 {{ __('Pipeline gói thầu') }}</h1>
          <p class="text-p-sm text-ink-gray-6">{{ __('Kéo thả thẻ giữa các cột để đổi giai đoạn (2 chiều). Thả vào “Trúng/Trượt” để chốt kết quả.') }}</p>
        </div>
        <Button variant="solid" theme="teal" :label="__('+ Tạo gói thầu')" @click="openCreate" />
      </div>
    </header>

    <!-- Dự báo doanh số (weighted) -->
    <section class="flex flex-wrap items-center gap-x-6 gap-y-2 border-b border-outline-gray-1 bg-surface-gray-1 px-6 py-3">
      <div>
        <span class="text-p-xs uppercase text-ink-gray-5">{{ __('Dự báo (trọng số xác suất)') }}</span>
        <div class="text-lg font-bold tabular-nums text-teal-700">{{ formatVnMoney(forecast.data?.total_weighted || 0) }} ₫</div>
      </div>
      <div class="flex flex-wrap gap-1.5">
        <span
          v-for="b in forecast.data?.by_stage || []"
          :key="b.stage"
          class="rounded-full border border-outline-gray-2 bg-surface-white px-2.5 py-1 text-p-xs text-ink-gray-7"
        >
          {{ b.stage }}: <strong class="tabular-nums">{{ formatVnMoney(b.weighted) }}</strong>
        </span>
      </div>
    </section>

    <section class="flex-1 overflow-auto p-4" aria-live="polite">
      <div v-if="tenders.loading" class="flex items-center justify-center gap-2 py-16 text-ink-gray-6">
        <LoadingIndicator class="h-4 w-4" /><span>{{ __('Đang tải…') }}</span>
      </div>
      <div v-else-if="tenders.error" class="flex flex-col items-center gap-3 py-16 text-center" role="alert">
        <Badge variant="subtle" theme="red" size="lg" :label="__('Không tải được')" />
        <Button variant="outline" :label="__('Thử lại')" @click="tenders.reload()" />
      </div>

      <!-- Kanban 6 cột — KÉO THẢ 2 chiều (HTML5 native DnD, không phụ thuộc thư viện) -->
      <div v-else class="flex gap-3 overflow-x-auto pb-2">
        <div
          v-for="stage in TENDER_STAGES"
          :key="stage"
          class="flex w-72 shrink-0 flex-col rounded-xl bg-surface-gray-1 p-2 transition-colors"
          :class="dragOverStage === stage ? 'ring-2 ring-teal-400 ring-offset-1' : ''"
          @dragover="onDragOver(stage, $event)"
          @dragleave="onDragLeave(stage)"
          @drop="onDrop(stage, $event)"
        >
          <div class="mb-2 flex items-center justify-between px-1.5 pt-1">
            <span class="flex items-center gap-1.5 text-p-sm font-semibold text-ink-gray-8">
              <span class="inline-block h-2 w-2 rounded-full" :class="dotClass(stage)" aria-hidden="true" />
              {{ stage }}
            </span>
            <span class="rounded-full bg-ink-gray-2 px-2 py-0.5 text-p-xs font-medium text-ink-gray-6">
              {{ (byStage[stage] || []).length }}
            </span>
          </div>

          <div class="flex min-h-[80px] flex-1 flex-col gap-2">
            <article
              v-for="t in byStage[stage] || []"
              :key="t.name"
              draggable="true"
              class="cursor-grab select-none rounded-lg border border-outline-gray-2 bg-surface-white p-3 transition-all duration-150 hover:shadow-md active:cursor-grabbing"
              :class="dragged && dragged.name === t.name ? 'opacity-40' : ''"
              @dragstart="onDragStart(t, $event)"
              @dragend="onDragEnd"
            >
              <div class="flex items-start justify-between gap-2">
                <span class="text-p-xs font-medium text-teal-700">{{ t.tender_no }}</span>
                <Badge
                  variant="subtle"
                  :theme="stageTheme(t.status)"
                  size="sm"
                  :label="t.win_probability_pct != null ? t.win_probability_pct + '%' : '—'"
                />
              </div>
              <p class="mt-0.5 text-p-sm font-semibold text-ink-gray-9">{{ t.tender_name }}</p>
              <p class="mt-0.5 text-p-xs text-ink-gray-5">🏥 {{ t.hospital_name || '—' }}</p>
              <p class="mt-1 text-p-sm font-medium tabular-nums text-ink-gray-8">{{ formatVnMoney(t.estimated_value || 0) }} ₫</p>
              <p v-if="t.status === 'Trúng' && t.decision_no" class="mt-1 text-p-xs font-medium text-green-700">
                {{ __('QĐ') }}: {{ t.decision_no }}
              </p>

              <!-- Xem chi tiết (click không kích hoạt kéo) -->
              <RouterLink
                :to="`/antmed/tenders/${encodeURIComponent(t.name)}`"
                class="mt-2 inline-flex items-center gap-1 rounded text-p-xs font-medium text-teal-700 hover:text-teal-800 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
                draggable="false"
                :aria-label="__('Xem chi tiết gói thầu {0}', [t.tender_no])"
                @click.stop
              >
                {{ __('Xem chi tiết') }} →
              </RouterLink>
            </article>

            <p v-if="!(byStage[stage] || []).length" class="px-1.5 py-2 text-center text-p-xs text-ink-gray-4">
              {{ __('Kéo thẻ vào đây') }}
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- Dialog tạo gói thầu -->
    <Dialog v-model="createDlg" :options="{ title: __('Tạo gói thầu mới'), size: 'xl' }">
      <template #body-content>
        <div class="bg-surface-modal px-4 pb-6 pt-5 sm:px-6">
          <div class="flex flex-col gap-5">
            <fieldset class="flex flex-col gap-3">
              <legend
                class="mb-1 text-p-xs font-semibold uppercase tracking-wide text-ink-gray-5"
              >
                {{ __('Thông tin gói thầu') }}
              </legend>
              <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <FormControl
                  :label="__('Số gói thầu') + ' *'"
                  v-model="cForm.tender_no"
                  placeholder="TND-2026-008"
                  required
                />
                <FormControl
                  type="select"
                  :label="__('Bệnh viện')"
                  v-model="cForm.hospital"
                  :options="hospitalOptions"
                />
              </div>
              <FormControl
                :label="__('Tên gói thầu') + ' *'"
                v-model="cForm.tender_name"
                :placeholder="__('Gói VTYT…')"
                required
              />
              <FormControl
                :label="__('Nguồn')"
                v-model="cForm.source"
                :placeholder="__('Mời thầu / Tự tìm')"
              />
            </fieldset>
            <fieldset
              class="flex flex-col gap-3 border-t border-outline-gray-1 pt-4"
            >
              <legend
                class="mb-1 text-p-xs font-semibold uppercase tracking-wide text-ink-gray-5"
              >
                {{ __('Tài chính & thời hạn') }}
              </legend>
              <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <FormControl
                  type="number"
                  :label="__('Giá trị ước tính (₫)')"
                  v-model="cForm.estimated_value"
                />
                <FormControl
                  type="date"
                  :label="__('Ngày mở thầu')"
                  v-model="cForm.bid_open_date"
                />
                <FormControl
                  type="date"
                  :label="__('Ngày đóng thầu')"
                  v-model="cForm.bid_close_date"
                />
              </div>
            </fieldset>
          </div>
          <div class="mt-6 flex justify-end gap-2 border-t border-outline-gray-1 pt-4">
            <Button :label="__('Huỷ')" @click="createDlg = false" />
            <Button variant="solid" theme="teal" :loading="createRes.loading" :label="__('Tạo gói thầu')" @click="onCreate" />
          </div>
        </div>
      </template>
    </Dialog>

    <!-- Dialog chốt kết quả (mở khi thả vào cột Trúng hoặc chọn Trúng/Trượt) -->
    <Dialog v-model="resultDlg" :options="{ title: __('Chốt kết quả: {0}', [rForm.tender_no]) }">
      <template #body-content>
        <div class="bg-surface-modal px-4 pb-6 pt-5 sm:px-6">
          <div class="flex flex-col gap-3">
            <label class="flex items-center gap-2 text-p-base">
              <input type="radio" value="Trúng" v-model="rForm.result" /> <Badge variant="subtle" theme="green" size="sm" :label="__('Trúng')" />
            </label>
            <label class="flex items-center gap-2 text-p-base">
              <input type="radio" value="Trượt" v-model="rForm.result" /> <Badge variant="subtle" theme="red" size="sm" :label="__('Trượt')" />
            </label>
            <FormControl v-if="rForm.result === 'Trúng'" :label="__('Số quyết định KQLCNT')" v-model="rForm.decision_no" placeholder="QĐ-2026-…" />
            <p v-if="rForm.result === 'Trúng'" class="text-p-xs text-ink-gray-5">{{ __('BR-M08: Trúng bắt buộc có số quyết định; hệ thống tự tạo HĐ nháp.') }}</p>
          </div>
          <div class="mt-6 flex justify-end gap-2 border-t border-outline-gray-1 pt-4">
            <Button :label="__('Huỷ')" @click="resultDlg = false" />
            <Button variant="solid" theme="teal" :loading="resultRes.loading" :label="__('Xác nhận')" @click="onResult" />
          </div>
        </div>
      </template>
    </Dialog>
  </main>
</template>

<script setup>
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { Badge, Button, Dialog, FormControl, createResource, toast } from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import {
  listTenders,
  getTenderForecast,
  listHospitals,
  TENDER_STAGES,
  TENDER_STAGE_THEME,
} from '@/data/antmed'
import { formatVnMoney } from '@/utils/antmedUi'

const PIPE = 'antmed_crm.api.antmed.pipeline'
const NON_TERMINAL = ['Tiếp cận', 'Khảo sát', 'Báo giá', 'Dự thầu']

const tenders = listTenders({ params: { page_length: 0 }, auto: true })
tenders.onError = (err) => toast.error(err?.messages?.[0] || __('Không tải được pipeline'))
const forecast = getTenderForecast({ auto: true })
const hospitals = listHospitals({ params: { page_length: 0 }, auto: true })

// Nhóm theo giai đoạn — READ-ONLY computed từ data (BE là nguồn sự thật, KHÔNG mutate cục bộ).
const byStage = computed(() => {
  const g = Object.fromEntries(TENDER_STAGES.map((s) => [s, []]))
  for (const t of tenders.data?.data || []) {
    if (g[t.status]) g[t.status].push(t)
  }
  return g
})
const hospitalOptions = computed(() =>
  (hospitals.data?.data || []).map((h) => ({ label: h.hospital_name || h.name, value: h.name })),
)

function stageTheme(s) {
  return TENDER_STAGE_THEME[s] || 'gray'
}
const DOT = {
  'Tiếp cận': 'bg-ink-gray-4',
  'Khảo sát': 'bg-blue-500',
  'Báo giá': 'bg-orange-500',
  'Dự thầu': 'bg-teal-500',
  Trúng: 'bg-green-500',
  Trượt: 'bg-red-500',
}
function dotClass(s) {
  return DOT[s] || 'bg-ink-gray-4'
}

function reloadAll() {
  tenders.reload()
  forecast.reload()
}

// ── HTML5 native drag-and-drop (2 chiều) ─────────────────────────────────────
const dragged = ref(null)
const dragOverStage = ref('')
function onDragStart(t, e) {
  dragged.value = t
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    try {
      e.dataTransfer.setData('text/plain', t.name)
    } catch {
      /* một số trình duyệt chặn setData ngoài user-gesture */
    }
  }
}
function onDragEnd() {
  dragged.value = null
  dragOverStage.value = ''
}
function onDragOver(stage, e) {
  e.preventDefault()
  dragOverStage.value = stage
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'move'
}
function onDragLeave(stage) {
  if (dragOverStage.value === stage) dragOverStage.value = ''
}
function onDrop(stage, e) {
  e.preventDefault()
  dragOverStage.value = ''
  const t = dragged.value
  dragged.value = null
  if (!t || t.status === stage) return
  applyMove(t, stage)
}

const moveRes = createResource({
  url: `${PIPE}.move_stage`,
  method: 'POST',
  onSuccess() {
    toast.success(__('Đã chuyển giai đoạn'))
    reloadAll()
  },
  onError: (err) => toast.error(err?.messages?.[0] || __('Không chuyển được')),
})
const resultRes = createResource({
  url: `${PIPE}.set_tender_result`,
  method: 'POST',
  onSuccess() {
    toast.success(__('Đã chốt kết quả gói thầu'))
    resultDlg.value = false
    reloadAll()
  },
  onError: (err) => toast.error(err?.messages?.[0] || __('Không chốt được kết quả')),
})

function applyMove(t, target) {
  if (NON_TERMINAL.includes(target)) {
    moveRes.submit({ name: t.name, stage: target })
  } else if (target === 'Trượt') {
    resultRes.submit({ name: t.name, result: 'Trượt' })
  } else if (target === 'Trúng') {
    openResult(t) // cần số quyết định → dialog
  }
}

// Tạo gói thầu
const createDlg = ref(false)
const cForm = ref({ tender_no: '', tender_name: '', hospital: '', estimated_value: null, source: '', bid_open_date: '', bid_close_date: '' })
const createRes = createResource({
  url: `${PIPE}.create_tender`,
  method: 'POST',
  onSuccess() {
    toast.success(__('Đã tạo gói thầu'))
    createDlg.value = false
    reloadAll()
  },
  onError: (err) => toast.error(err?.messages?.[0] || __('Không tạo được gói thầu')),
})
function openCreate() {
  cForm.value = { tender_no: '', tender_name: '', hospital: hospitalOptions.value[0]?.value || '', estimated_value: null, source: '', bid_open_date: '', bid_close_date: '' }
  createDlg.value = true
}
function onCreate() {
  if (!cForm.value.tender_no || !cForm.value.tender_name) {
    toast.error(__('Nhập số và tên gói thầu'))
    return
  }
  createRes.submit({ ...cForm.value })
}

// Chốt kết quả
const resultDlg = ref(false)
const rForm = ref({ name: '', tender_no: '', result: 'Trúng', decision_no: '' })
function openResult(t) {
  rForm.value = { name: t.name, tender_no: t.tender_no, result: 'Trúng', decision_no: '' }
  resultDlg.value = true
}
function onResult() {
  resultRes.submit({ name: rForm.value.name, result: rForm.value.result, decision_no: rForm.value.decision_no || undefined })
}
</script>
