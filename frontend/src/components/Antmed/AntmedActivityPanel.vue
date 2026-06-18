<template>
  <section
    class="flex flex-col gap-3 rounded-lg border border-outline-gray-1 bg-surface-white p-4"
    :aria-label="__('Hoạt động')"
  >
    <header class="flex items-center justify-between gap-2">
      <h3 class="text-p-base font-semibold text-ink-gray-9">
        {{ __('Hoạt động') }}
      </h3>
      <span class="text-p-xs text-ink-gray-5">
        {{ noteCount }} {{ __('ghi chú') }} · {{ taskCount }} {{ __('việc') }}
      </span>
    </header>

    <!-- Thêm ghi chú -->
    <form class="flex flex-col gap-2" @submit.prevent="submitNote">
      <textarea
        v-model="noteText"
        rows="2"
        class="w-full resize-y rounded-md border border-outline-gray-2 bg-surface-gray-1 px-3 py-2 text-p-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
        :placeholder="__('Thêm ghi chú cho bản ghi này…')"
        :aria-label="__('Nội dung ghi chú')"
      />
      <div class="flex justify-end">
        <Button
          variant="solid"
          theme="gray"
          :loading="adder.loading"
          :disabled="!noteText.trim() || adder.loading"
          :label="__('Thêm ghi chú')"
          @click="submitNote"
        />
      </div>
    </form>

    <!-- Timeline (tri-branch) -->
    <div
      v-if="board.loading"
      class="flex items-center gap-2 py-6 text-p-sm text-ink-gray-6"
    >
      <LoadingIndicator class="h-4 w-4" />
      <span>{{ __('Đang tải…') }}</span>
    </div>

    <div
      v-else-if="board.error"
      class="py-4 text-p-sm text-ink-gray-6"
      role="alert"
    >
      {{ errorMessage }}
    </div>

    <p
      v-else-if="!events.length"
      class="py-6 text-center text-p-sm text-ink-gray-5"
    >
      {{ __('Chưa có hoạt động — thêm ghi chú hoặc công việc đầu tiên.') }}
    </p>

    <AmTimeline v-else :events="events" />
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { Button, toast } from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import AmTimeline from '@/components/Antmed/ui/AmTimeline.vue'
import { getActivity, addNote } from '@/data/antmed'

// Panel TÁI DÙNG: gắn dòng thời gian (Ghi chú + Công việc) lên BẤT KỲ bản ghi AntMed
// (Hợp đồng/Bệnh viện/Phiếu giao…) qua reference_doctype + reference_docname.
const props = defineProps({
  referenceDoctype: { type: String, required: true },
  referenceDocname: { type: String, required: true },
})

const board = getActivity({
  referenceDoctype: props.referenceDoctype,
  referenceDocname: props.referenceDocname,
  auto: true,
})
// Endpoint trả RAW dict { events, note_count, task_count } → đọc board.data.* TRỰC TIẾP.
const events = computed(() => board.data?.events || [])
const noteCount = computed(() => board.data?.note_count ?? 0)
const taskCount = computed(() => board.data?.task_count ?? 0)

const noteText = ref('')
const adder = addNote({
  onSuccess() {
    noteText.value = ''
    board.reload()
    toast.success(__('Đã thêm ghi chú'))
  },
  onError(err) {
    toast.error(err?.messages?.[0] || __('Không thêm được ghi chú'))
  },
})
function submitNote() {
  const content = noteText.value.trim()
  if (!content || adder.loading) return
  adder.submit({
    reference_doctype: props.referenceDoctype,
    reference_docname: props.referenceDocname,
    content,
  })
}

const errorMessage = computed(
  () => board.error?.messages?.[0] || __('Không tải được hoạt động'),
)
</script>
