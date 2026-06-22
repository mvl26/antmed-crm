<template>
  <main class="flex min-h-screen w-screen">
    <!-- Panel thương hiệu (desktop) -->
    <aside
      class="relative hidden w-1/2 flex-col justify-between overflow-hidden bg-gradient-to-br from-teal-700 via-teal-800 to-teal-950 p-12 text-white lg:flex"
    >
      <!-- Hình nền trang trí -->
      <div aria-hidden="true" class="pointer-events-none absolute inset-0">
        <div class="absolute -left-24 -top-24 h-80 w-80 rounded-full bg-teal-400/20 blur-3xl" />
        <div class="absolute -bottom-32 -right-10 h-96 w-96 rounded-full bg-emerald-300/10 blur-3xl" />
        <div class="absolute right-8 top-10 select-none text-[13rem] font-bold leading-none text-white/[0.06]">
          ⚕
        </div>
      </div>

      <div class="relative flex items-center gap-2 text-2xl font-bold">
        <span aria-hidden="true">⚕</span><span>AntMed CRM</span>
      </div>

      <div class="relative flex flex-col gap-6">
        <h2 class="max-w-md text-3xl font-semibold leading-snug">
          {{ __('Quản lý kinh doanh thiết bị & vật tư y tế') }}
        </h2>
        <ul class="flex flex-col gap-3 text-p-base text-white/85">
          <li
            v-for="feat in features"
            :key="feat"
            class="flex items-center gap-2.5"
          >
            <span class="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-white/15">
              <FeatherIcon name="check" class="h-3 w-3" aria-hidden="true" />
            </span>
            {{ feat }}
          </li>
        </ul>
      </div>

      <p class="relative text-p-xs text-white/60">
        © AntMed — {{ __('Phần mềm CRM ngành thiết bị & vật tư y tế') }}
      </p>
    </aside>

    <!-- Panel form -->
    <section
      class="flex w-full items-center justify-center bg-surface-gray-1 px-4 py-10 lg:w-1/2"
    >
      <div class="w-full max-w-sm">
        <div class="mb-7 flex flex-col items-center gap-1 text-center lg:items-start lg:text-left">
          <div class="mb-1 flex items-center gap-1.5 text-2xl font-bold text-teal-800 lg:hidden">
            <span aria-hidden="true">⚕</span><span>AntMed CRM</span>
          </div>
          <h1 class="text-xl font-semibold text-ink-gray-9">{{ __('Đăng nhập') }}</h1>
          <p class="text-p-sm text-ink-gray-6">
            {{ __('Nhập tài khoản để vào hệ thống') }}
          </p>
        </div>

        <div
          class="rounded-2xl border border-outline-gray-2 bg-surface-white p-6 shadow-sm sm:p-7"
        >
          <form class="flex flex-col gap-4" @submit.prevent="doLogin">
            <FormControl
              v-model="email"
              type="email"
              :label="__('Email')"
              :placeholder="__('ten@congty.com')"
              autocomplete="username"
              :disabled="loginRes.loading"
              required
            />

            <FormControl
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              :label="__('Mật khẩu')"
              placeholder="••••••••"
              autocomplete="current-password"
              :disabled="loginRes.loading"
              required
            >
              <template #suffix>
                <button
                  type="button"
                  class="rounded text-ink-gray-5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
                  :aria-label="showPassword ? __('Ẩn mật khẩu') : __('Hiện mật khẩu')"
                  tabindex="-1"
                  @click="showPassword = !showPassword"
                >
                  <FeatherIcon
                    :name="showPassword ? 'eye-off' : 'eye'"
                    class="h-4 w-4"
                  />
                </button>
              </template>
            </FormControl>

            <!-- Nhớ tài khoản (cache email vào localStorage) -->
            <label
              class="flex cursor-pointer select-none items-center gap-2 text-p-sm text-ink-gray-7"
            >
              <input
                v-model="remember"
                type="checkbox"
                class="h-4 w-4 rounded border-outline-gray-3 text-teal-600 focus-visible:ring-2 focus-visible:ring-teal-500"
              />
              {{ __('Nhớ tài khoản trên thiết bị này') }}
            </label>

            <p
              v-if="errorMessage"
              class="rounded-md bg-surface-red-1 px-3 py-2 text-p-sm text-ink-red-3"
              role="alert"
              aria-live="assertive"
            >
              {{ errorMessage }}
            </p>

            <Button
              variant="solid"
              type="submit"
              class="w-full !bg-teal-700 !text-white hover:!bg-teal-800"
              :loading="loginRes.loading"
              :disabled="!email || !password"
              :label="__('Đăng nhập')"
            />
          </form>

          <p class="mt-5 text-center text-p-sm text-ink-gray-5">
            {{ __('Quên mật khẩu? Vui lòng liên hệ quản trị viên.') }}
          </p>
        </div>
      </div>
    </section>
  </main>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { Button, FormControl, FeatherIcon, createResource } from 'frappe-ui'
import { sessionStore } from '@/stores/session'

const route = useRoute()
const session = sessionStore()

// Tính năng tóm tắt (panel thương hiệu trái).
const features = [
  __('Hợp đồng · gói thầu · quota'),
  __('Kho đa cấp · Quản lý lô · Truy vết lô'),
  __('Giao phòng mổ · bộ dụng cụ · chứng từ'),
]

const email = ref('')
const password = ref('')
const showPassword = ref(false)
const remember = ref(false)

// "Nhớ tài khoản" = cache EMAIL (KHÔNG mật khẩu — bảo mật) vào localStorage trình duyệt.
const REMEMBER_KEY = 'antmed_login_email'
function safeLocal(fn, fallback = null) {
  try {
    return fn()
  } catch (e) {
    return fallback
  }
}

// Đích sau đăng nhập: query `redirect-to` (path SPA, vd /antmed/deliveries) → path (base '/').
// Mặc định /antmed. Chỉ chấp nhận path nội bộ bắt đầu bằng '/' (chống open-redirect).
const redirectTarget = computed(() => {
  const rt = route.query['redirect-to']
  const path = typeof rt === 'string' && rt.startsWith('/') ? rt : '/antmed'
  return path
})

// Login resource RIÊNG (KHÔNG dùng session.login — onSuccess của nó router.replace, còn ở
// đây SPA đang chạy boot GUEST nên phải reload đầy đủ để lấy boot đã xác thực).
const loginRes = createResource({
  url: 'login',
  onSuccess() {
    window.location.href = redirectTarget.value
  },
  onError() {
    // Lỗi hiển thị qua errorMessage (đọc loginRes.error). Nuốt để tránh unhandled rejection.
  },
})

const errorMessage = computed(() =>
  loginRes.error ? __('Email hoặc mật khẩu không đúng.') : '',
)

function doLogin() {
  if (!email.value || !password.value || loginRes.loading) return
  // Lưu / xoá email ghi nhớ TRƯỚC khi submit (giữ kể cả khi đăng nhập sai để đỡ gõ lại).
  safeLocal(() => {
    if (remember.value) localStorage.setItem(REMEMBER_KEY, email.value)
    else localStorage.removeItem(REMEMBER_KEY)
  })
  loginRes.submit({ usr: email.value, pwd: password.value })
}

onMounted(() => {
  // Đã đăng nhập mà mở trang login → về thẳng app (full reload lấy boot xác thực).
  if (session.isLoggedIn) {
    window.location.href = '/antmed'
    return
  }
  // Prefill email đã ghi nhớ (nếu có) → tick sẵn "Nhớ tài khoản".
  const saved = safeLocal(() => localStorage.getItem(REMEMBER_KEY))
  if (saved) {
    email.value = saved
    remember.value = true
  }
})
</script>
