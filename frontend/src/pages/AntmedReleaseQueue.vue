<template>
  <main class="flex h-full flex-col" aria-labelledby="antmed-release-queue-title">
    <!-- Header + breadcrumb -->
    <header
      class="flex flex-col gap-2 border-b border-outline-gray-modals px-6 py-4"
    >
      <nav class="text-p-xs text-ink-gray-5" :aria-label="__('Đường dẫn')">
        <span>{{ __('Trang chủ') }}</span>
        <span class="px-1" aria-hidden="true">›</span>
        <span>{{ __('Chứng từ') }}</span>
        <span class="px-1" aria-hidden="true">›</span>
        <span class="text-ink-gray-7">{{ __('Hàng chờ phát hành') }}</span>
      </nav>
      <div class="flex flex-col gap-1">
        <h1
          id="antmed-release-queue-title"
          class="text-xl font-semibold text-ink-gray-9"
        >
          {{ __('Hàng chờ phát hành chứng từ') }}
        </h1>
        <p class="text-p-sm text-ink-gray-6">
          {{
            __(
              'Phiếu giao chờ phát hành — trạng thái CO/CQ & sẵn sàng phát hành HĐĐT',
            )
          }}
        </p>
      </div>
    </header>

    <section class="flex-1 overflow-auto px-6 py-4" aria-live="polite">
      <!-- Hàng KPI 3 thẻ — số THẬT từ release_queue_summary() -->
      <div
        class="grid grid-cols-1 gap-3 sm:grid-cols-3"
        role="group"
        :aria-label="__('Chỉ tiêu hàng chờ phát hành')"
      >
        <AntmedKpiCard
          :label="__('Thiếu CO')"
          :value="summary.loading ? null : kpi.missing_co"
          :empty="summary.error"
          :placeholder-hint="__('Không tải được')"
        />
        <AntmedKpiCard
          :label="__('Thiếu CQ')"
          :value="summary.loading ? null : kpi.missing_cq"
          :empty="summary.error"
          :placeholder-hint="__('Không tải được')"
        />
        <AntmedKpiCard
          :label="__('Sẵn sàng phát hành')"
          :value="summary.loading ? null : kpi.ready_to_release"
          :empty="summary.error"
          :placeholder-hint="__('Không tải được')"
        />
      </div>

      <!-- Banner lỗi KPI (độc lập với worklist — lỗi KPI KHÔNG vỡ bảng) -->
      <div
        v-if="summary.error"
        class="mt-3 flex items-center justify-between gap-3 rounded-lg border border-outline-gray-2 bg-surface-red-1 px-4 py-2"
        role="alert"
      >
        <p class="text-p-sm text-ink-gray-7">
          {{ summaryErrorMessage }}
        </p>
        <Button
          variant="outline"
          size="sm"
          :label="__('Thử lại')"
          @click="summary.reload()"
        />
      </div>

      <!-- Worklist DO chờ phát hành -->
      <div class="mt-5">
        <h2 class="mb-2 text-p-base font-medium text-ink-gray-8">
          {{ __('Phiếu giao chờ phát hành') }}
        </h2>

        <!-- Loading -->
        <div
          v-if="queue.loading"
          class="flex items-center justify-center gap-2 py-16 text-ink-gray-6"
        >
          <LoadingIndicator class="h-4 w-4" />
          <span class="text-p-base">{{ __('Đang tải hàng chờ…') }}</span>
        </div>

        <!-- Error -->
        <div
          v-else-if="queue.error"
          class="flex flex-col items-center gap-3 py-16 text-center"
          role="alert"
        >
          <Badge
            variant="subtle"
            theme="red"
            size="lg"
            :label="__('Không tải được')"
          />
          <p class="max-w-md text-p-sm text-ink-gray-6">{{ queueErrorMessage }}</p>
          <Button
            variant="outline"
            :label="__('Thử lại')"
            @click="queue.reload()"
          />
        </div>

        <!-- Empty -->
        <div
          v-else-if="!rows.length"
          class="flex flex-col items-center gap-2 py-16 text-center text-ink-gray-6"
        >
          <p class="text-p-base">
            {{ __('Không có phiếu giao nào đang chờ phát hành.') }}
          </p>
          <p class="text-p-sm">
            {{
              __(
                'Hàng chờ sinh tự động khi bundle chứng từ được tạo từ phiếu giao.',
              )
            }}
          </p>
        </div>

        <!-- Data table -->
        <table
          v-else
          class="w-full border-separate border-spacing-0 text-left"
        >
          <caption class="sr-only">
            {{
              __('Danh sách phiếu giao chờ phát hành chứng từ')
            }}
          </caption>
          <thead>
            <tr class="text-p-sm text-ink-gray-6">
              <th class="border-b border-outline-gray-modals py-2 pr-4 font-medium">
                {{ __('Phiếu giao') }}
              </th>
              <th class="border-b border-outline-gray-modals py-2 pr-4 font-medium">
                {{ __('Bệnh viện') }}
              </th>
              <th class="border-b border-outline-gray-modals py-2 pr-4 font-medium">
                {{ __('NV') }}
              </th>
              <th class="border-b border-outline-gray-modals py-2 pr-4 font-medium">
                {{ __('Thiếu') }}
              </th>
              <th class="border-b border-outline-gray-modals py-2 pr-4 font-medium">
                {{ __('Ngày') }}
              </th>
              <th class="border-b border-outline-gray-modals py-2 pr-4 font-medium">
                {{ __('Trạng thái') }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in rows"
              :key="row.name"
              class="text-p-sm text-ink-gray-8"
            >
              <!-- Phiếu giao (mã DO) -->
              <td class="border-b border-outline-gray-1 py-2 pr-4 font-medium">
                {{ row.delivery || '—' }}
              </td>
              <!-- Bệnh viện — tên đọc được, KHÔNG mã -->
              <td class="border-b border-outline-gray-1 py-2 pr-4">
                {{ row.hospital_name || '—' }}
              </td>
              <!-- NV (full_name nếu BE resolve được; fallback hiển thị "—", KHÔNG leak email thô) -->
              <td class="border-b border-outline-gray-1 py-2 pr-4">
                {{ employeeLabel(row) }}
              </td>
              <!-- Chips Thiếu CO / Thiếu CQ (parse missing_chips, kèm CHỮ — WCAG AA) -->
              <td class="border-b border-outline-gray-1 py-2 pr-4">
                <div class="flex flex-wrap items-center gap-1.5">
                  <span
                    v-if="flagsFor(row).co"
                    class="inline-flex items-center rounded-full px-2 py-0.5 text-p-xs font-medium"
                    :class="pillClass('danger')"
                  >
                    {{ __('Thiếu CO') }}
                  </span>
                  <span
                    v-if="flagsFor(row).cq"
                    class="inline-flex items-center rounded-full px-2 py-0.5 text-p-xs font-medium"
                    :class="pillClass('warn')"
                  >
                    {{ __('Thiếu CQ') }}
                  </span>
                  <span
                    v-if="!flagsFor(row).co && !flagsFor(row).cq"
                    class="inline-flex items-center rounded-full px-2 py-0.5 text-p-xs font-medium"
                    :class="pillClass('ok')"
                  >
                    {{ __('Đủ CO/CQ') }}
                  </span>
                </div>
              </td>
              <!-- Ngày (định dạng VI từ ts) -->
              <td class="border-b border-outline-gray-1 py-2 pr-4 tabular-nums">
                {{ fmtDateTimeVi(row.ts) }}
              </td>
              <!-- Chip trạng thái Mở ↔ Sẵn sàng phát hành (kèm CHỮ + tone) -->
              <td class="border-b border-outline-gray-1 py-2 pr-4">
                <span
                  class="inline-flex items-center rounded-full px-2.5 py-0.5 text-p-xs font-medium"
                  :class="pillClass(statusChipFor(row).theme)"
                >
                  {{ statusChipFor(row).label }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </main>
</template>

<script setup>
import { computed } from 'vue'
import { Badge, Button, toast } from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import AntmedKpiCard from '@/components/Antmed/AntmedKpiCard.vue'
import { getReleaseQueueSummary, getReleaseQueue } from '@/data/antmed'
import {
  pillClass,
  releaseChipFlags,
  releaseStatusChip,
} from '@/utils/antmedUi'

// KPI rollup — dict thường {missing_co, missing_cq, ready_to_release} → đọc r.data.* trực tiếp.
const summary = getReleaseQueueSummary({
  auto: true,
  onError(err) {
    toast.error(err?.messages?.[0] || __('Không tải được chỉ tiêu hàng chờ'))
  },
})

const kpi = computed(() => ({
  missing_co: summary.data?.missing_co ?? 0,
  missing_cq: summary.data?.missing_cq ?? 0,
  ready_to_release: summary.data?.ready_to_release ?? 0,
}))

const summaryErrorMessage = computed(
  () =>
    summary.error?.messages?.[0] ||
    summary.error?.message ||
    __('Không tải được chỉ tiêu hàng chờ phát hành'),
)

// Worklist — dict bọc {data, total_count} → đọc r.data.data.
const queue = getReleaseQueue({
  params: {},
  auto: true,
  onError(err) {
    toast.error(err?.messages?.[0] || __('Không tải được hàng chờ phát hành'))
  },
})

const rows = computed(() => queue.data?.data || [])

const queueErrorMessage = computed(
  () =>
    queue.error?.messages?.[0] ||
    queue.error?.message ||
    __('Không tải được danh sách hàng chờ phát hành'),
)

// Cờ thiếu CO/CQ theo dòng (parse missing_chips). Helper PURE từ antmedUi.
function flagsFor(row) {
  return releaseChipFlags(row.missing_chips)
}

// Chip trạng thái Mở ↔ Sẵn sàng phát hành (status VI + missing_chips).
function statusChipFor(row) {
  return releaseStatusChip(row.status, row.missing_chips)
}

// NV: BE resolve assigned_employee (User). Hiển thị full_name nếu có; nếu chỉ là email/ID
// thô → vẫn KHÔNG leak (chỉ hiển thị khi BE đã resolve tên); chưa gán → "Chưa gán".
function employeeLabel(row) {
  if (row.assigned_employee_name) return row.assigned_employee_name
  if (row.assigned_employee) return row.assigned_employee
  return __('Chưa gán')
}

// Định dạng ngày giờ VI từ ts (Datetime). null → '—'.
function fmtDateTimeVi(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString('vi-VN')
}
</script>
