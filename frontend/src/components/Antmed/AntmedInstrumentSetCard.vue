<template>
  <RouterLink
    :to="`/antmed/instruments/${encodeURIComponent(set.name)}`"
    class="flex flex-col gap-2 rounded-xl border border-outline-gray-2 bg-surface-white p-3.5 transition-all duration-200 ease-out hover:-translate-y-0.5 hover:border-teal-400 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
    :aria-label="__('Xem bộ {0}', [set.set_code])"
  >
    <div class="flex items-start justify-between gap-2">
      <div class="min-w-0">
        <h3 class="truncate text-p-base font-semibold text-teal-800">
          🧰 {{ set.set_code }} · {{ set.surgery_type || '—' }}
        </h3>
        <p class="mt-0.5 truncate text-p-xs text-ink-gray-5">
          {{ set.item_count }} {{ __('món') }}
          <template v-if="set.hospital_name"
            >· {{ set.hospital_name }}</template
          >
          <template v-if="set.doctor_name">· {{ set.doctor_name }}</template>
        </p>
      </div>
      <Badge
        v-if="isIssue"
        variant="subtle"
        theme="red"
        size="sm"
        :label="set.current_status"
      />
    </div>

    <AmLifecycleBar v-if="!isIssue" :state="set.current_status" />

    <!-- Dòng hoạt động: NV giữ + ETA / cảnh báo quá hạn -->
    <p
      v-if="set.is_overdue"
      class="text-p-xs font-medium text-red-600"
      role="status"
    >
      ⚠ {{ __('Quá hạn trả') }}
      <template v-if="set.holder_name">· {{ set.holder_name }}</template>
    </p>
    <p v-else-if="activityText" class="text-p-xs text-ink-gray-6">
      {{ activityText }}
    </p>
  </RouterLink>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { Badge } from 'frappe-ui'
import AmLifecycleBar from '@/components/Antmed/AmLifecycleBar.vue'

const props = defineProps({
  set: { type: Object, required: true },
})

const isIssue = computed(() =>
  ['Mất', 'Hỏng'].includes(props.set.current_status),
)

// Mô tả ngắn hoạt động hiện tại (NV giữ / sẵn sàng tại kho).
const activityText = computed(() => {
  const s = props.set
  if (s.current_status === 'Sẵn sàng') {
    return __('Sẵn sàng tại kho · {0} lượt mượn', [s.lifetime_loans || 0])
  }
  if (s.holder_name) return __('NV: {0}', [s.holder_name])
  return ''
})
</script>
