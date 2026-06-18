<template>
  <main class="flex h-full flex-col" aria-labelledby="antmed-profile-title">
    <header class="flex flex-col gap-2 border-b border-outline-gray-modals px-6 py-4">
      <nav class="text-p-xs text-ink-gray-5" :aria-label="__('Đường dẫn')">
        <RouterLink to="/antmed" class="rounded text-ink-gray-6 hover:text-ink-gray-8">{{ __('Trang chủ') }}</RouterLink>
        <span class="px-1.5 text-ink-gray-4" aria-hidden="true">›</span>
        <span class="text-ink-gray-7" aria-current="page">{{ __('Trang cá nhân') }}</span>
      </nav>
      <h1 id="antmed-profile-title" class="text-xl font-semibold text-ink-gray-9">{{ __('Trang cá nhân') }}</h1>
    </header>

    <section class="flex-1 overflow-auto px-6 pb-8 pt-5">
      <div v-if="profile.loading" class="flex items-center justify-center gap-2 py-16 text-ink-gray-6">
        <LoadingIndicator class="h-4 w-4" /><span>{{ __('Đang tải…') }}</span>
      </div>
      <div v-else-if="profile.error" class="flex flex-col items-center gap-3 py-16 text-center" role="alert">
        <Badge variant="subtle" theme="red" size="lg" :label="__('Không tải được hồ sơ')" />
        <Button variant="outline" :label="__('Thử lại')" @click="profile.reload()" />
      </div>

      <div v-else class="mx-auto max-w-2xl">
        <!-- Thẻ hồ sơ (hero gradient teal) -->
        <div class="flex items-center gap-4 rounded-2xl bg-gradient-to-br from-teal-600 to-teal-800 p-5 text-white shadow-sm ring-1 ring-teal-900/10">
          <div class="flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-white/20 text-xl font-bold text-white ring-2 ring-white/40">
            {{ initials }}
          </div>
          <div class="min-w-0">
            <h2 class="truncate text-lg font-semibold">{{ me.full_name }}</h2>
            <p class="truncate text-p-sm text-white/85">{{ me.email }}</p>
            <div class="mt-2 flex flex-wrap gap-1">
              <Badge v-for="r in me.managed_roles" :key="r" variant="subtle" :theme="roleTheme(r)" size="sm" :label="r" />
              <Badge v-if="me.is_admin" variant="subtle" theme="red" size="sm" :label="__('System Manager')" />
              <Badge :theme="me.enabled ? 'green' : 'red'" variant="subtle" size="sm" :label="me.enabled ? __('Active') : __('Khoá')" />
            </div>
          </div>
        </div>

        <!-- Thông tin chi tiết -->
        <dl class="mt-5 grid grid-cols-1 gap-x-8 gap-y-4 rounded-xl border border-outline-gray-2 bg-surface-white p-5 sm:grid-cols-2">
          <div>
            <dt class="text-p-xs uppercase text-ink-gray-5">{{ __('Phạm vi dữ liệu') }}</dt>
            <dd class="text-p-base text-ink-gray-9">{{ me.data_scope }}</dd>
          </div>
          <div>
            <dt class="text-p-xs uppercase text-ink-gray-5">{{ __('2FA') }}</dt>
            <dd><Badge variant="subtle" :theme="me.two_factor ? 'green' : 'gray'" size="sm" :label="me.two_factor ? __('Bật') : __('Tắt')" /></dd>
          </div>
          <div>
            <dt class="text-p-xs uppercase text-ink-gray-5">{{ __('Đăng nhập gần nhất') }}</dt>
            <dd class="text-p-base text-ink-gray-9">{{ fmtDate(me.last_login) }}</dd>
          </div>
          <div>
            <dt class="text-p-xs uppercase text-ink-gray-5">{{ __('Múi giờ') }}</dt>
            <dd class="text-p-base text-ink-gray-9">{{ me.time_zone || '—' }}</dd>
          </div>
        </dl>

        <div class="mt-5 flex flex-wrap gap-3">
          <Button variant="solid" theme="red" :label="__('Đăng xuất')" :loading="session.logout.loading" @click="onLogout" />
        </div>
      </div>
    </section>
  </main>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { Badge, Button, toast } from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import { sessionStore } from '@/stores/session'
import { getMyProfile, userInitials, ROLE_PILL_THEME } from '@/data/antmed'

const session = sessionStore()
const profile = getMyProfile({ auto: true, onError: (err) => toast.error(err?.messages?.[0] || __('Không tải được hồ sơ')) })

const me = computed(() => profile.data || {})
const initials = computed(() => userInitials(me.value.full_name))

function roleTheme(r) {
  return ROLE_PILL_THEME[r] || 'gray'
}
function fmtDate(v) {
  if (!v) return '—'
  const d = new Date(String(v).replace(' ', 'T'))
  if (Number.isNaN(d.getTime())) return String(v)
  const p = (n) => String(n).padStart(2, '0')
  return `${p(d.getDate())}/${p(d.getMonth() + 1)}/${d.getFullYear()} ${p(d.getHours())}:${p(d.getMinutes())}`
}
function onLogout() {
  session.logout.submit()
}
</script>
