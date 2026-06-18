<template>
  <!-- Widget "Tiêu hao HĐ theo tháng" (mockup A1, M02-6) — bar chart 12 cột tháng,
       chiều cao = qty/max(qty)*100% (helper thuần barHeightPct). Presentational: nhận props
       data/totalQty/loading/error + emit retry — KHÔNG tự fetch. Màu bar token AntMed teal.
       Token card/bar tái dùng (rounded-xl bg-surface-white, không hex thô). -->
  <article
    class="flex flex-col gap-3 rounded-xl border border-outline-gray-1 bg-surface-white p-4"
    aria-labelledby="antmed-consumption-title"
  >
    <header class="flex flex-wrap items-baseline justify-between gap-2">
      <h2
        id="antmed-consumption-title"
        class="text-p-base font-semibold text-ink-gray-8"
      >
        {{ cardTitle }}
      </h2>
      <span
        v-if="!loading && !error && rows.length"
        class="text-p-xs text-ink-gray-5"
      >
        {{ __('Tổng tiêu hao') }}:
        <span class="font-medium tabular-nums text-ink-gray-7">{{ totalQtyText }}</span>
      </span>
    </header>

    <!-- Loading -->
    <div
      v-if="loading"
      class="flex items-center justify-center gap-2 py-10 text-ink-gray-6"
      aria-live="polite"
    >
      <LoadingIndicator class="h-4 w-4" />
      <span class="text-p-sm">{{ __('Đang tải…') }}</span>
    </div>

    <!-- Error (KHÔNG leak stacktrace — chỉ message VI + nút Thử lại) -->
    <div
      v-else-if="error"
      class="flex flex-col items-center gap-3 py-10 text-center"
      role="alert"
    >
      <Badge variant="subtle" theme="red" size="sm" :label="__('Không tải được')" />
      <p class="max-w-xs text-p-sm text-ink-gray-6">
        {{ __('Không tải được dữ liệu tiêu hao theo tháng.') }}
      </p>
      <Button
        variant="outline"
        size="sm"
        :label="__('Thử lại')"
        @click="$emit('retry')"
      />
    </div>

    <!-- Empty -->
    <div
      v-else-if="!rows.length"
      class="flex flex-col items-center justify-center gap-1 rounded-lg bg-surface-gray-1 py-10 text-center"
    >
      <p class="text-p-sm font-medium text-ink-gray-5">
        {{ __('Chưa có dữ liệu tiêu hao') }}
      </p>
    </div>

    <!-- Data — bar chart 12 cột thuần CSS (flex), chiều cao = barHeightPct(qty, maxQty). -->
    <div v-else>
      <!-- Vùng cột: cao cố định để tránh layout shift (CLS). aria mô tả tổng quát biểu đồ. -->
      <div
        class="flex h-40 items-end gap-1.5 sm:gap-2"
        role="img"
        :aria-label="chartAriaLabel"
      >
        <!-- FE KHÔNG sort lại — giữ thứ tự BE (đã sort tăng dần theo tháng). -->
        <div
          v-for="bar in rows"
          :key="bar.month"
          class="flex h-full flex-1 flex-col items-center justify-end"
        >
          <!-- Cột: height theo %; min-height nhỏ để cột 0 vẫn thấy đường nền (token teal). -->
          <div
            class="flex w-full items-end justify-center"
            :style="{ height: '100%' }"
          >
            <div
              class="w-full rounded-t bg-teal-600 transition-[height]"
              :class="bar.qty > 0 ? '' : 'bg-ink-gray-2'"
              :style="{ height: barStyleHeight(bar.qty) }"
              :title="barTooltip(bar)"
              :aria-label="barTooltip(bar)"
            />
          </div>
        </div>
      </div>
      <!-- Nhãn trục X = bar.label (T1..T12 từ BE). Căn cột với vùng cột phía trên. -->
      <div class="mt-1.5 flex gap-1.5 sm:gap-2">
        <div
          v-for="bar in rows"
          :key="bar.month + '-x'"
          class="flex-1 text-center text-p-xs tabular-nums text-ink-gray-5"
        >
          {{ bar.label }}
        </div>
      </div>
    </div>
  </article>
</template>

<script setup>
import { computed } from 'vue'
import { Badge, Button } from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import { barHeightPct } from '@/utils/antmedUi'

const props = defineProps({
  // Mảng 12 bucket { month, label, qty } — BE đã gộp + sort (FE KHÔNG sort/tính lại).
  data: { type: Array, default: () => [] },
  totalQty: { type: [Number, String], default: 0 },
  contractNo: { type: String, default: '' },
  hospitalName: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  error: { type: [Boolean, Object, String], default: false },
})

defineEmits(['retry'])

const rows = computed(() => props.data || [])

// max(qty) trong cửa sổ — để quy đổi chiều cao cột. max==0 → barHeightPct trả 0 (no ZeroDivision).
const maxQty = computed(() =>
  rows.value.reduce((m, b) => Math.max(m, Number(b.qty) || 0), 0),
)

// Title 'Tiêu hao <số HĐ> (<BV>) theo tháng' — *_name (KHÔNG mã thô); thiếu → bỏ phần ngoặc.
const cardTitle = computed(() => {
  const cno = props.contractNo || ''
  const hosp = props.hospitalName ? ` (${props.hospitalName})` : ''
  return cno
    ? `${__('Tiêu hao')} ${cno}${hosp} ${__('theo tháng')}`
    : `${__('Tiêu hao hợp đồng theo tháng')}`
})

const totalQtyText = computed(() => formatQty(props.totalQty))

const chartAriaLabel = computed(
  () =>
    `${cardTitle.value}. ` +
    rows.value.map((b) => `${b.label}: ${formatQty(b.qty)}`).join(', '),
)

function barStyleHeight(qty) {
  return barHeightPct(qty, maxQty.value) + '%'
}

function barTooltip(bar) {
  return `${bar.label}: ${formatQty(bar.qty)}`
}

function formatQty(value) {
  if (value === null || value === undefined || value === '') return '0'
  const n = Number(value)
  if (!Number.isFinite(n)) return '0'
  return n.toLocaleString('vi-VN')
}
</script>
