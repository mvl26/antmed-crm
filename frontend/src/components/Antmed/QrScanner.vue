<template>
  <!-- Camera QR/Barcode tái dùng (mockup C2 Wizard "Xuất cho NV" — quét bằng camera).
       Lỗi quyền/không camera → thông báo VI + KHÔNG vỡ trang (parent vẫn cho nhập tay). -->
  <div class="flex flex-col gap-2">
    <div class="flex items-center justify-between gap-2">
      <span class="text-p-sm font-medium text-ink-gray-7">{{ __('Quét mã bằng camera') }}</span>
      <Button
        size="sm"
        :variant="running ? 'outline' : 'solid'"
        :label="running ? __('Tắt camera') : __('Bật camera')"
        :loading="starting"
        :aria-label="running ? __('Tắt camera quét mã') : __('Bật camera quét mã')"
        @click="toggle"
      />
    </div>

    <!-- Vùng video camera (html5-qrcode mount vào element id này) -->
    <div
      :id="elementId"
      class="overflow-hidden rounded-lg border border-outline-gray-2 bg-surface-gray-1"
      :class="running ? 'min-h-[220px]' : 'min-h-0'"
    />

    <!-- Lỗi camera (quyền bị chặn / không có thiết bị) → nhắc nhập tay, KHÔNG chặn flow -->
    <p
      v-if="cameraError"
      class="rounded-md bg-amber-50 px-3 py-2 text-p-xs text-amber-800"
      role="status"
    >
      {{ cameraError }}
    </p>
    <p v-else-if="!running" class="text-p-xs text-ink-gray-5">
      {{ __('Bấm "Bật camera" để quét, hoặc nhập mã thủ công bên dưới.') }}
    </p>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { Button } from 'frappe-ui'

const props = defineProps({
  /** Cho phép bật camera (parent điều khiển — vd ẩn tab phải đang xem thì tắt). */
  active: { type: Boolean, default: true },
})
const emit = defineEmits(['scan'])

// Element id duy nhất/instance (tránh đụng khi có nhiều scanner trên 1 trang).
const elementId = `antmed-qr-${Math.random().toString(36).slice(2, 9)}`

const running = ref(false)
const starting = ref(false)
const cameraError = ref('')

let html5Qrcode = null // instance Html5Qrcode (lazy)
let Html5QrcodeCtor = null // class import động

// Guard chống đọc trùng liên tiếp cùng 1 mã trong ~1.2s (camera bắn nhiều frame/giây).
let lastText = ''
let lastAt = 0
const DEDUPE_MS = 1200

function onScanSuccess(decodedText) {
  const now = Date.now()
  if (decodedText === lastText && now - lastAt < DEDUPE_MS) return
  lastText = decodedText
  lastAt = now
  emit('scan', decodedText)
}

async function ensureCtor() {
  if (Html5QrcodeCtor) return Html5QrcodeCtor
  // Import ĐỘNG — lỗi import (vd thiếu dep) KHÔNG phá build/trang; bắt ở caller.
  const mod = await import('html5-qrcode')
  Html5QrcodeCtor = mod.Html5Qrcode
  return Html5QrcodeCtor
}

async function start() {
  if (running.value || starting.value) return
  cameraError.value = ''
  starting.value = true
  try {
    const Ctor = await ensureCtor()
    html5Qrcode = new Ctor(elementId)
    await html5Qrcode.start(
      { facingMode: 'environment' },
      { fps: 10, qrbox: { width: 240, height: 240 } },
      onScanSuccess,
      // onScanFailure: bỏ qua (mỗi frame không đọc được sẽ gọi → không cần xử lý).
      () => {},
    )
    running.value = true
  } catch (err) {
    // Quyền bị chặn / không có camera / import lỗi → nhắc nhập tay, KHÔNG vỡ trang.
    cameraError.value = __('Không truy cập được camera — nhập mã thủ công.')
    await stop()
  } finally {
    starting.value = false
  }
}

async function stop() {
  running.value = false
  if (!html5Qrcode) return
  try {
    await html5Qrcode.stop()
  } catch (e) {
    // Đã dừng / chưa start → bỏ qua.
  }
  try {
    html5Qrcode.clear()
  } catch (e) {
    // Bỏ qua lỗi clear (tránh leak camera nhưng không vỡ).
  }
  html5Qrcode = null
}

async function toggle() {
  if (running.value) await stop()
  else await start()
}

// Parent tắt active → dừng camera (giải phóng thiết bị).
watch(
  () => props.active,
  (val) => {
    if (!val && running.value) stop()
  },
)

onMounted(() => {
  // KHÔNG auto-start (UX: user chủ động bật để tránh xin quyền camera ngay khi vào trang).
})

onBeforeUnmount(() => {
  stop() // tránh leak camera khi rời trang.
})
</script>
