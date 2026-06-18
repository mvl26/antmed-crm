<template>
  <!-- Panel '⚠ Cảnh báo điều hành' (A1) — danh sách pill từ alerts (quota_summary).
       Tri-branch loading / error(nút Thử lại) / empty 'Không có cảnh báo'. Presentational:
       nhận alerts + loading + error từ container; KHÔNG tự fetch, KHÔNG bịa dữ liệu. -->
  <article
    class="flex min-h-[160px] flex-col gap-3 rounded-xl border border-outline-gray-1 bg-surface-white p-4"
  >
    <h2 class="text-p-base font-semibold text-ink-gray-8">
      {{ __('⚠ Cảnh báo điều hành') }}
    </h2>

    <!-- Loading -->
    <div
      v-if="loading"
      class="flex flex-1 items-center justify-center gap-2 text-ink-gray-6"
      aria-live="polite"
    >
      <LoadingIndicator class="h-4 w-4" />
      <span class="text-p-sm">{{ __('Đang tải cảnh báo…') }}</span>
    </div>

    <!-- Error -->
    <div
      v-else-if="error"
      class="flex flex-1 flex-col items-center justify-center gap-2 text-center"
      role="alert"
    >
      <Badge variant="subtle" theme="red" :label="__('Không tải được cảnh báo')" size="sm" />
      <Button variant="outline" size="sm" :label="__('Thử lại')" @click="$emit('retry')" />
    </div>

    <!-- Empty -->
    <div
      v-else-if="!alerts.length"
      class="flex flex-1 flex-col items-center justify-center gap-1 rounded-lg bg-surface-gray-1 py-6 text-center"
    >
      <p class="text-p-sm font-medium text-ink-gray-5">
        {{ __('Không có cảnh báo') }}
      </p>
      <p class="text-p-xs text-ink-gray-4">
        {{ __('Tất cả hợp đồng đang trong ngưỡng an toàn') }}
      </p>
    </div>

    <!-- Data — danh sách pill alert-box theo severity (đỏ=danger/cam=warn), label VI từ BE.
         Style qua helper alertClass (SSoT mockup A1 §.alert-box) — KHÔNG hex thô; label chữ
         luôn hiển thị (WCAG: không phân biệt chỉ bằng màu). -->
    <ul v-else class="flex flex-1 flex-col gap-2" :aria-label="__('Danh sách cảnh báo')">
      <li
        v-for="a in alerts"
        :key="`${a.contract}-${a.type}`"
        class="rounded-lg border-l-4 px-3 py-2 text-p-sm"
        :class="alertClass(a.severity)"
      >
        {{ a.label }}
      </li>
    </ul>
  </article>
</template>

<script setup>
import { Badge, Button } from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import { alertClass } from '@/utils/antmedUi'

defineProps({
  /** alerts[] từ quota_summary — { type, severity, contract, label }. Rỗng → empty-state. */
  alerts: { type: Array, default: () => [] },
  /** Đang tải. */
  loading: { type: Boolean, default: false },
  /** Có lỗi tải. */
  error: { type: Boolean, default: false },
})

defineEmits(['retry'])
</script>
