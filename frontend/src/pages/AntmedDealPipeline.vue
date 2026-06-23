<template>
  <main class="flex h-full flex-col" aria-labelledby="antmed-deal-title">
    <header
      class="flex flex-col gap-2 border-b border-outline-gray-modals px-6 py-4"
    >
      <nav class="text-p-xs text-ink-gray-5" :aria-label="__('Đường dẫn')">
        <RouterLink
          to="/antmed"
          class="rounded text-ink-gray-6 hover:text-ink-gray-8"
          >{{ __('Trang chủ') }}</RouterLink
        >
        <span class="px-1.5 text-ink-gray-4" aria-hidden="true">›</span>
        <span class="text-ink-gray-7" aria-current="page">{{
          __('Pipeline cơ hội')
        }}</span>
      </nav>
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1
            id="antmed-deal-title"
            class="text-xl font-semibold text-ink-gray-9"
          >
            📈 {{ __('Pipeline cơ hội (Deal)') }}
          </h1>
          <p class="text-p-sm text-ink-gray-6">
            {{
              __(
                'Kéo thả thẻ giữa các giai đoạn (2 chiều). Kế thừa CRM Deal — lọc theo tuyến của bạn.',
              )
            }}
          </p>
        </div>
        <Button
          variant="solid"
          theme="teal"
          :label="__('+ Tạo cơ hội')"
          @click="openCreate"
        />
      </div>
    </header>

    <!-- Dự báo doanh số (weighted theo xác suất) -->
    <section
      class="flex flex-wrap items-center gap-x-6 gap-y-2 border-b border-outline-gray-1 bg-surface-gray-1 px-6 py-3"
    >
      <div>
        <span class="text-p-xs uppercase text-ink-gray-5">{{
          __('Dự báo (trọng số xác suất)')
        }}</span>
        <div class="text-lg font-bold tabular-nums text-teal-700">
          {{ formatVnMoney(board.data?.forecast?.total_weighted || 0) }} ₫
        </div>
      </div>
      <div class="flex flex-wrap gap-1.5">
        <span
          v-for="b in board.data?.forecast?.by_stage || []"
          :key="b.stage"
          class="rounded-full border border-outline-gray-2 bg-surface-white px-2.5 py-1 text-p-xs text-ink-gray-7"
        >
          {{ stageLabel(b.stage) }}:
          <strong class="tabular-nums">{{ formatVnMoney(b.weighted) }}</strong>
        </span>
      </div>
    </section>

    <section class="flex-1 overflow-auto p-4" aria-live="polite">
      <div
        v-if="board.loading"
        class="flex items-center justify-center gap-2 py-16 text-ink-gray-6"
      >
        <LoadingIndicator class="h-4 w-4" /><span>{{ __('Đang tải…') }}</span>
      </div>
      <div
        v-else-if="board.error"
        class="flex flex-col items-center gap-3 py-16 text-center"
        role="alert"
      >
        <Badge
          variant="subtle"
          theme="red"
          size="lg"
          :label="__('Không tải được')"
        />
        <Button
          variant="outline"
          :label="__('Thử lại')"
          @click="board.reload()"
        />
      </div>

      <!-- Kanban — HTML5 native drag, 2 chiều, theo CRM Deal Status -->
      <div v-else class="flex gap-3 overflow-x-auto pb-2">
        <div
          v-for="s in stages"
          :key="s.name"
          class="flex w-72 shrink-0 flex-col rounded-xl bg-surface-gray-1 p-2 transition-colors"
          :class="
            dragOverStage === s.name ? 'ring-2 ring-teal-400 ring-offset-1' : ''
          "
          @dragover="onDragOver(s.name, $event)"
          @dragleave="onDragLeave(s.name)"
          @drop="onDrop(s.name, $event)"
        >
          <div class="mb-2 flex items-center justify-between px-1.5 pt-1">
            <span
              class="flex items-center gap-1.5 text-p-sm font-semibold text-ink-gray-8"
            >
              <span
                class="inline-block h-2 w-2 rounded-full"
                :class="dotClass(s.name)"
                aria-hidden="true"
              />
              {{ stageLabel(s.name) }}
            </span>
            <span
              class="rounded-full bg-ink-gray-2 px-2 py-0.5 text-p-xs font-medium text-ink-gray-6"
            >
              {{ (cards[s.name] || []).length }}
            </span>
          </div>

          <div class="flex min-h-[80px] flex-1 flex-col gap-2">
            <article
              v-for="c in cards[s.name] || []"
              :key="c.name"
              draggable="true"
              class="cursor-grab select-none rounded-lg border border-outline-gray-2 bg-surface-white p-3 transition-all duration-150 hover:shadow-md active:cursor-grabbing"
              :class="dragged && dragged.name === c.name ? 'opacity-40' : ''"
              @dragstart="onDragStart(c, $event)"
              @dragend="onDragEnd"
            >
              <p class="text-p-sm font-semibold text-ink-gray-9">
                {{ c.am_hospital_name || c.organization || c.name }}
              </p>
              <p
                class="mt-0.5 text-p-sm font-medium tabular-nums text-ink-gray-8"
              >
                {{ formatVnMoney(c.deal_value || 0) }} ₫
              </p>
              <div class="mt-1 flex flex-wrap items-center gap-1.5">
                <Badge
                  variant="subtle"
                  :theme="stageTheme(c.status)"
                  size="sm"
                  :label="(c.probability != null ? c.probability : 0) + '%'"
                />
                <span
                  v-if="c.am_tender_no"
                  class="rounded bg-ink-gray-2 px-1.5 py-0.5 text-[10px] text-ink-gray-6"
                  >🎯 {{ c.am_tender_no }}</span
                >
              </div>
              <p class="mt-1 text-p-xs text-ink-gray-5">
                {{ __('NV') }}: {{ c.deal_owner_name || '—' }}
              </p>
              <RouterLink
                :to="`/antmed/deals/${encodeURIComponent(c.name)}`"
                class="mt-2 inline-flex items-center gap-1 rounded text-p-xs font-medium text-teal-700 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
                draggable="false"
                @click.stop
              >
                {{ __('Xem chi tiết') }} →
              </RouterLink>
            </article>

            <p
              v-if="!(cards[s.name] || []).length"
              class="px-1.5 py-2 text-center text-p-xs text-ink-gray-4"
            >
              {{ __('Kéo thẻ vào đây') }}
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- Dialog tạo cơ hội -->
    <Dialog v-model="createDlg" :options="{ title: __('Tạo cơ hội mới') }">
      <template #body-content>
        <div class="bg-surface-modal px-4 pb-6 pt-5 sm:px-6">
          <div class="flex flex-col gap-4">
            <FormControl
              v-model="cForm.am_hospital"
              type="select"
              :label="__('Bệnh viện (khách hàng)')"
              :options="hospitalOptions"
            />
            <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <FormControl
                v-model="cForm.deal_value"
                type="number"
                :label="__('Giá trị (₫)')"
              />
              <FormControl
                v-model="cForm.am_tender_no"
                :label="__('Số gói thầu (nếu có)')"
                placeholder="TND-2026-…"
              />
            </div>
            <FormControl
              v-model="cForm.status"
              type="select"
              :label="__('Giai đoạn')"
              :options="
                stages.map((s) => ({
                  label: stageLabel(s.name),
                  value: s.name,
                }))
              "
            />
          </div>
          <div
            class="mt-6 flex justify-end gap-2 border-t border-outline-gray-1 pt-4"
          >
            <Button :label="__('Huỷ')" @click="createDlg = false" />
            <Button
              variant="solid"
              theme="teal"
              :loading="createRes.loading"
              :label="__('Tạo cơ hội')"
              @click="onCreate"
            />
          </div>
        </div>
      </template>
    </Dialog>
  </main>
</template>

<script setup>
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import {
  Badge,
  Button,
  Dialog,
  FormControl,
  createResource,
  toast,
} from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import {
  getDealBoard,
  listHospitals,
  DEAL_STAGE_LABEL,
  DEAL_STAGE_THEME,
  DEAL_STAGE_DOT,
} from '@/data/antmed'
import { formatVnMoney } from '@/utils/antmedUi'

const PIPE = 'antmed_crm.api.antmed.pipeline'

const board = getDealBoard({ auto: true })
board.onError = (err) =>
  toast.error(err?.messages?.[0] || __('Không tải được pipeline cơ hội'))
const hospitals = listHospitals({ params: { page_length: 0 }, auto: true })

const stages = computed(() => board.data?.stages || [])
const cards = computed(() => board.data?.by_stage || {})
const hospitalOptions = computed(() =>
  (hospitals.data?.data || []).map((h) => ({
    label: h.hospital_name || h.name,
    value: h.name,
  })),
)

function stageLabel(s) {
  return DEAL_STAGE_LABEL[s] || s
}
function stageTheme(s) {
  return DEAL_STAGE_THEME[s] || 'gray'
}
function dotClass(s) {
  return DEAL_STAGE_DOT[s] || 'bg-ink-gray-4'
}

// ── HTML5 native drag-and-drop (2 chiều, mọi giai đoạn) ──────────────────────
const dragged = ref(null)
const dragOverStage = ref('')
function onDragStart(c, e) {
  dragged.value = c
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    try {
      e.dataTransfer.setData('text/plain', c.name)
    } catch {
      /* noop */
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
  const c = dragged.value
  dragged.value = null
  if (!c || c.status === stage) return
  moveRes.submit({ deal: c.name, status: stage })
}

const moveRes = createResource({
  url: `${PIPE}.move_deal`,
  method: 'POST',
  onSuccess() {
    toast.success(__('Đã chuyển giai đoạn'))
    board.reload()
  },
  onError: (err) => toast.error(err?.messages?.[0] || __('Không chuyển được')),
})

// Tạo cơ hội
const createDlg = ref(false)
const cForm = ref({
  am_hospital: '',
  deal_value: null,
  am_tender_no: '',
  status: '',
})
const createRes = createResource({
  url: `${PIPE}.create_deal`,
  method: 'POST',
  onSuccess() {
    toast.success(__('Đã tạo cơ hội'))
    createDlg.value = false
    board.reload()
  },
  onError: (err) =>
    toast.error(err?.messages?.[0] || __('Không tạo được cơ hội')),
})
function openCreate() {
  cForm.value = {
    am_hospital: hospitalOptions.value[0]?.value || '',
    deal_value: null,
    am_tender_no: '',
    status: stages.value[0]?.name || '',
  }
  createDlg.value = true
}
function onCreate() {
  createRes.submit({ ...cForm.value })
}
</script>
