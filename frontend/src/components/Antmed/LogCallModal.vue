<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
      @click.self="close"
    >
      <div
        role="dialog"
        aria-modal="true"
        :aria-label="__('Ghi nhật ký cuộc gọi')"
        class="w-full max-w-md rounded-xl border border-outline-gray-2 bg-surface-white p-5 shadow-2xl"
      >
        <h2 class="text-base font-semibold text-ink-gray-9">
          {{ __('Ghi nhật ký cuộc gọi') }}
        </h2>

        <div class="mt-4 space-y-3">
          <FormControl
            type="select"
            :label="__('Kết quả')"
            :options="outcomeOptions"
            v-model="outcome"
          />
          <div class="flex gap-2">
            <FormControl
              type="number"
              :label="__('Phút')"
              v-model="minutes"
              class="flex-1"
            />
            <FormControl
              type="number"
              :label="__('Giây')"
              v-model="seconds"
              class="flex-1"
            />
          </div>
          <FormControl
            type="textarea"
            :label="__('Ghi chú')"
            v-model="note"
            :placeholder="__('Nội dung trao đổi…')"
          />
          <p v-if="errorMsg" class="text-p-sm text-red-600" role="alert">
            {{ errorMsg }}
          </p>
        </div>

        <div class="mt-5 flex justify-end gap-2">
          <Button variant="subtle" :label="__('Hủy')" @click="close" />
          <Button
            variant="solid"
            :label="__('Lưu')"
            :loading="res.loading"
            @click="submit"
          />
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue'
import { Button, FormControl, toast } from 'frappe-ui'
import { logCall } from '@/data/antmed'

const props = defineProps({
  open: { type: Boolean, default: false },
  doctor: { type: String, default: '' },
  phone: { type: String, default: '' },
})
const emit = defineEmits(['update:open', 'logged'])

const OUTCOMES = ['Nghe máy', 'Không nghe', 'Máy bận', 'Hộp thư']
const outcomeOptions = OUTCOMES.map((o) => ({ label: __(o), value: o }))

const outcome = ref('Nghe máy')
const minutes = ref('')
const seconds = ref('')
const note = ref('')
const errorMsg = ref('')

const res = logCall({
  onSuccess() {
    toast.success(__('Đã lưu nhật ký cuộc gọi'))
    emit('logged')
    close()
  },
  onError(err) {
    errorMsg.value = err?.messages?.[0] || __('Không lưu được cuộc gọi')
  },
})

function durationSec() {
  return (parseInt(minutes.value) || 0) * 60 + (parseInt(seconds.value) || 0)
}

function submit() {
  errorMsg.value = ''
  if (!outcome.value) {
    errorMsg.value = __('Vui lòng chọn kết quả cuộc gọi')
    return
  }
  res.submit({
    doctor: props.doctor,
    outcome: outcome.value,
    duration_sec: durationSec(),
    note: note.value || undefined,
  })
}

function close() {
  emit('update:open', false)
}

watch(
  () => props.open,
  (v) => {
    if (v) {
      outcome.value = 'Nghe máy'
      minutes.value = ''
      seconds.value = ''
      note.value = ''
      errorMsg.value = ''
    }
  },
)
</script>
