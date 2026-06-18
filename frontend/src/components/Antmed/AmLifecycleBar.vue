<template>
  <!-- Thanh vòng đời 7 đoạn (mockup I1/C3): 6 bước chuẩn + 'SS' (sẵn sàng lại). -->
  <div class="flex gap-px" role="img" :aria-label="ariaLabel">
    <div
      v-for="(seg, i) in segments"
      :key="i"
      class="flex-1 px-1 py-1 text-center text-[9px] font-semibold leading-tight transition-colors duration-300 first:rounded-l last:rounded-r"
      :class="segClass(i)"
    >
      {{ seg }}
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { INSTRUMENT_LIFECYCLE } from '@/data/antmed'

const props = defineProps({
  // KEY trạng thái VI có dấu (khớp current_status / loan.status BE).
  state: { type: String, default: '' },
})

// 7 đoạn hiển thị: short của 6 bước + 'SS' cuối (đại diện "sẵn sàng cho lượt kế").
const segments = [...INSTRUMENT_LIFECYCLE.map((s) => s.short), 'SS']

// -1 nếu state không nằm trên trục (Mất/Hỏng/Đã đóng) → toàn bộ đoạn xám.
const curIndex = computed(() =>
  INSTRUMENT_LIFECYCLE.findIndex((s) => s.key === props.state),
)

function segClass(i) {
  if (curIndex.value < 0) return 'bg-ink-gray-2 text-ink-gray-5'
  if (i < curIndex.value) return 'bg-green-100 text-green-800' // đã qua
  if (i === curIndex.value) return 'bg-teal-600 text-white' // hiện tại
  return 'bg-ink-gray-2 text-ink-gray-5' // sắp tới
}

const ariaLabel = computed(
  () => `${__('Vòng đời bộ dụng cụ')}: ${props.state || '—'}`,
)
</script>
