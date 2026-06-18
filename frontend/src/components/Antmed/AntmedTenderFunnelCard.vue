<template>
  <!-- Widget 'Pipeline gói thầu' (A1 Hàng 3) — funnel 5 tầng (Lead→Khảo sát→Báo giá→Dự thầu→Trúng).
       Mỗi tầng = bar ngang (width giảm dần theo count/max, không nhỏ hơn min-floor) + nhãn VI + count.
       Presentational: nhận stages/total/loading/error từ container; KHÔNG tự fetch, KHÔNG bịa số.
       Tri-branch loading / error(nút Thử lại) / empty (total===0) / data. -->
  <article
    class="flex min-h-[160px] flex-col gap-3 rounded-xl border border-outline-gray-1 bg-surface-white p-4"
  >
    <h2 class="text-p-base font-semibold text-ink-gray-8">
      {{ __('Pipeline gói thầu') }}
    </h2>

    <!-- Loading -->
    <div
      v-if="loading"
      class="flex flex-1 items-center justify-center gap-2 text-ink-gray-6"
      aria-live="polite"
    >
      <LoadingIndicator class="h-4 w-4" />
      <span class="text-p-sm">{{ __('Đang tải pipeline…') }}</span>
    </div>

    <!-- Error -->
    <div
      v-else-if="error"
      class="flex flex-1 flex-col items-center justify-center gap-2 text-center"
      role="alert"
    >
      <Badge variant="subtle" theme="red" :label="__('Không tải được pipeline')" size="sm" />
      <Button variant="outline" size="sm" :label="__('Thử lại')" @click="$emit('retry')" />
    </div>

    <!-- Empty — total === 0: KHÔNG vẽ funnel rỗng méo -->
    <div
      v-else-if="total === 0"
      class="flex flex-1 flex-col items-center justify-center gap-1 rounded-lg bg-surface-gray-1 py-6 text-center"
    >
      <p class="text-p-sm font-medium text-ink-gray-5">
        {{ __('Chưa có dữ liệu pipeline') }}
      </p>
      <p class="text-p-xs text-ink-gray-4">
        {{ __('Chưa có lead/thầu nào trong phạm vi của bạn') }}
      </p>
    </div>

    <!-- Data — funnel 5 tầng xếp dọc, width bar GIẢM DẦN (funnelBarWidth), nền teal nhạt dần.
         Nhãn + count luôn hiển thị chữ (WCAG: không phân biệt chỉ bằng kích thước/màu). -->
    <ul
      v-else
      class="flex flex-1 flex-col items-center gap-1.5 pt-1"
      :aria-label="__('Phễu pipeline gói thầu')"
    >
      <li
        v-for="(s, i) in stages"
        :key="s.key"
        class="flex items-center justify-between gap-2 rounded-md px-3 py-2 text-p-sm font-medium"
        :class="funnelBarClass(i)"
        :style="{ width: funnelBarWidth(s.count, maxCount) + '%' }"
      >
        <span class="truncate">{{ s.label }}</span>
        <span class="shrink-0 tabular-nums font-semibold">{{ s.count }}</span>
      </li>
    </ul>
  </article>
</template>

<script setup>
import { computed } from 'vue'
import { Badge, Button } from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import { funnelBarWidth, funnelBarClass } from '@/utils/antmedUi'

const props = defineProps({
  /** stages[] từ tender_pipeline — { key, label, count } (đúng 5 tầng, đúng thứ tự BE). */
  stages: { type: Array, default: () => [] },
  /** Tổng số bản ghi toàn funnel — total===0 → empty-state. */
  total: { type: Number, default: 0 },
  /** Đang tải. */
  loading: { type: Boolean, default: false },
  /** Có lỗi tải. */
  error: { type: Boolean, default: false },
})

defineEmits(['retry'])

// Mẫu số tỉ lệ width = count lớn nhất trong funnel (tầng đỉnh = 100%). Tính ở FE chỉ để VẼ
// (không phải business-logic) — số đếm vẫn 100% từ BE.
const maxCount = computed(() =>
  props.stages.reduce((m, s) => Math.max(m, s.count || 0), 0),
)
</script>
