<template>
  <main class="flex h-full flex-col" aria-labelledby="antmed-dr-dispatch-title">
    <!-- Header + breadcrumb (mockup B1) -->
    <header
      class="flex flex-col gap-2 border-b border-outline-gray-modals px-6 py-4"
    >
      <nav class="text-p-xs text-ink-gray-5" :aria-label="__('Đường dẫn')">
        <RouterLink
          to="/antmed"
          class="rounded text-ink-gray-6 hover:text-ink-gray-8 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
        >
          {{ __('Trang chủ') }}
        </RouterLink>
        <span class="px-1.5 text-ink-gray-4" aria-hidden="true">›</span>
        <span class="text-ink-gray-7" aria-current="page">{{
          __('Điều phối')
        }}</span>
      </nav>
      <div class="flex flex-col gap-1">
        <h1
          id="antmed-dr-dispatch-title"
          class="text-xl font-semibold text-ink-gray-9"
        >
          {{ __('Bảng điều phối ca giao phòng mổ') }}
        </h1>
        <p class="text-p-sm text-ink-gray-6">
          {{
            __(
              'Kanban ca giao theo trạng thái — chỉ xem, dữ liệu thời gian thực',
            )
          }}
        </p>
      </div>
    </header>

    <!-- KPI: tổng ca + khẩn (số = totals BE) -->
    <section
      class="grid grid-cols-2 gap-3 px-6 pt-4 sm:max-w-md"
      :aria-label="__('Chỉ số điều phối')"
    >
      <AntmedKpiCard
        :label="__('Tổng ca giao')"
        :value="totals.total"
        :empty="board.loading || !!board.error"
        :placeholder-hint="__('Đang tải…')"
      />
      <AntmedKpiCard
        :label="__('Ca khẩn (≤1h / quá giờ)')"
        :value="totals.urgent"
        value-class="text-red-600"
        :empty="board.loading || !!board.error"
        :placeholder-hint="__('Đang tải…')"
      />
    </section>

    <!-- Tri-branch: loading / error / empty / data -->
    <section class="flex-1 overflow-auto px-6 pb-6 pt-4" aria-live="polite">
      <div
        v-if="board.loading"
        class="flex items-center justify-center gap-2 py-16 text-ink-gray-6"
      >
        <LoadingIndicator class="h-4 w-4" />
        <span class="text-p-base">{{ __('Đang tải…') }}</span>
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
        <p class="max-w-md text-p-sm text-ink-gray-6">{{ errorMessage }}</p>
        <Button
          variant="outline"
          :label="__('Thử lại')"
          @click="board.reload()"
        />
      </div>

      <div
        v-else-if="!hasCards"
        class="flex flex-col items-center gap-2 py-16 text-center text-ink-gray-6"
      >
        <p class="text-p-base">{{ __('Chưa có ca giao nào') }}</p>
        <p class="text-p-sm">
          {{ __('Chưa có phiếu giao phòng mổ trong phạm vi của bạn.') }}
        </p>
      </div>

      <!-- Kanban 4 cột B1 (BE đã gom lanes + sort theo giờ mổ) -->
      <div
        v-else
        class="flex gap-4 overflow-x-auto pb-2"
        role="list"
        :aria-label="__('Các cột điều phối ca giao')"
      >
        <div
          v-for="lane in lanes"
          :key="lane.key"
          class="flex w-72 shrink-0 flex-col rounded-lg bg-surface-gray-1"
          role="listitem"
        >
          <div
            class="flex items-center justify-between gap-2 border-b border-outline-gray-modals px-3 py-2"
          >
            <h2 class="truncate text-p-sm font-semibold text-ink-gray-8">
              {{ lane.label }}
            </h2>
            <Badge
              variant="subtle"
              theme="gray"
              size="sm"
              :label="String(lane.count)"
              :aria-label="__('{0} ca ở cột {1}', [lane.count, lane.label])"
            />
          </div>

          <div class="flex flex-col gap-2 p-2">
            <p
              v-if="!lane.cards.length"
              class="px-1 py-3 text-center text-p-xs text-ink-gray-4"
            >
              {{ __('Không có ca') }}
            </p>
            <article
              v-for="card in lane.cards"
              :key="card.delivery"
              class="flex flex-col gap-1.5 rounded-md border-l-2 bg-surface-white p-3 shadow-sm"
              :class="urgencyBorder(card.urgency)"
            >
              <!-- BV + giờ ca mổ -->
              <div class="flex items-start justify-between gap-2">
                <p class="text-p-base font-medium text-ink-gray-9">
                  {{ card.hospital_name || card.hospital || '—' }}
                </p>
                <span
                  class="shrink-0 text-p-xs tabular-nums text-ink-gray-6"
                  :title="__('Giờ ca mổ')"
                >
                  {{ fmtTime(card.surgery_datetime) }}
                </span>
              </div>

              <!-- BS + số SKU -->
              <p class="text-p-xs text-ink-gray-6">
                {{ __('BS') }}: {{ card.doctor_name || '—' }} ·
                {{ card.sku_count }} {{ __('SKU') }}
              </p>

              <!-- NV phụ trách (full_name) -->
              <p class="text-p-xs text-ink-gray-7">
                {{ __('NV') }}:
                {{ card.assigned_employee_name || __('— chưa gán —') }}
              </p>

              <!-- Badge khẩn / cảnh báo -->
              <div v-if="urgencyInfo(card.urgency)" class="pt-0.5">
                <Badge
                  variant="subtle"
                  size="sm"
                  :theme="urgencyInfo(card.urgency).theme"
                  :label="urgencyInfo(card.urgency).label"
                />
              </div>
            </article>
          </div>
        </div>
      </div>
    </section>
  </main>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { Badge, Button, toast } from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import AntmedKpiCard from '@/components/Antmed/AntmedKpiCard.vue'
import { getDeliveryDispatchBoard } from '@/data/antmed'

// Endpoint trả RAW dict THƯỜNG { lanes, totals, columns, total } → đọc board.data.* TRỰC TIẾP
// (KHÔNG bọc lồng 2 lớp — cùng idiom getDashboardOverview). FE KHÔNG group/sort lại (BE gom 4 lane).
const board = getDeliveryDispatchBoard({ auto: true })

const lanes = computed(() => board.data?.lanes || [])
const totals = computed(() => board.data?.totals || { total: 0, urgent: 0 })
const hasCards = computed(() =>
  lanes.value.some((l) => (l.cards || []).length > 0),
)

const URGENCY = {
  urgent: { theme: 'red', label: 'Khẩn (≤1h)' },
  warn: { theme: 'orange', label: 'Cảnh báo SLA' },
}
const urgencyInfo = (u) => URGENCY[u] || null
const urgencyBorder = (u) =>
  u === 'urgent'
    ? 'border-red-500'
    : u === 'warn'
      ? 'border-amber-500'
      : 'border-outline-gray-2'

// Giờ ca mổ: "YYYY-MM-DD HH:MM:SS" → "HH:MM DD/MM" (string-op, KHÔNG cần Date).
function fmtTime(dt) {
  if (!dt) return '—'
  const [d, t] = String(dt).split(' ')
  if (!d || !d.includes('-')) return String(dt)
  const [, mo, da] = d.split('-')
  return `${(t || '').slice(0, 5)} ${da}/${mo}`
}

board.onError = (err) => {
  toast.error(err?.messages?.[0] || __('Không tải được bảng điều phối'))
}
const errorMessage = computed(
  () =>
    board.error?.messages?.[0] ||
    board.error?.message ||
    __('Không tải được bảng điều phối'),
)
</script>
