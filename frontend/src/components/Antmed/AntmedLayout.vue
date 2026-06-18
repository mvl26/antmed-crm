<template>
  <div class="flex h-screen w-screen flex-col">
    <!-- Topbar (mockup A1: teal-900; vai trò Portal G = nền trắng border) -->
    <header
      class="flex items-center gap-3.5 px-4 py-2.5 text-xs"
      :class="
        isPortal
          ? 'border-b border-outline-gray-2 bg-white text-teal-900'
          : 'bg-teal-900 text-white'
      "
    >
      <RouterLink
        to="/antmed"
        class="flex items-center gap-1.5 text-sm font-bold focus-visible:rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
      >
        <span aria-hidden="true">⚕</span>
        <span>{{ isPortal ? __('AntMed Portal') : __('AntMed CRM') }}</span>
      </RouterLink>

      <span
        v-if="!isPortal"
        class="hidden items-center gap-1 rounded-full bg-white/[0.14] px-2.5 py-0.5 text-[11px] sm:inline-flex"
      >
        <FeatherIcon name="calendar" class="h-3 w-3" aria-hidden="true" />{{
          periodLabel
        }}
      </span>

      <button
        v-if="!isPortal"
        type="button"
        class="ml-2 hidden h-6 max-w-[300px] flex-1 items-center gap-1.5 rounded-full bg-white/[0.12] px-2.5 text-[11px] text-white/70 transition hover:bg-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-300 sm:flex"
        :aria-label="__('Tìm kiếm nhanh')"
        @click="searchOpen = true"
      >
        <FeatherIcon
          name="search"
          class="h-3.5 w-3.5 shrink-0 text-white/80"
          aria-hidden="true"
        />
        <span class="flex-1 truncate text-left">{{
          __('Tìm chức năng, bệnh viện, hợp đồng...')
        }}</span>
        <span
          class="shrink-0 rounded bg-white/20 px-1 py-0.5 text-[9px] font-medium leading-none"
          >⌘K</span
        >
      </button>

      <!-- Nhóm phải: chuông (popup thông báo) + avatar -->
      <div class="ml-auto flex items-center gap-2.5">
        <!-- Chuông thông báo — popup dropdown (frappe-ui Popover) + badge chưa đọc -->
        <Popover>
          <template #target="{ togglePopover }">
            <button
              id="notifications-btn"
              type="button"
              class="relative flex h-6 w-6 items-center justify-center rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
              :class="isPortal ? 'hover:bg-surface-gray-2' : 'hover:bg-white/15'"
              :aria-label="
                unreadNotificationsCount
                  ? unreadNotificationsCount + ' ' + __('thông báo chưa đọc')
                  : __('Thông báo')
              "
              @click="togglePopover"
            >
              <NotificationsIcon class="h-4 w-4" aria-hidden="true" />
              <span
                v-if="unreadNotificationsCount"
                class="absolute -right-1 -top-1 flex h-3.5 min-w-[14px] items-center justify-center rounded-full bg-red-500 px-0.5 text-[9px] font-semibold leading-none text-white"
              >
                {{ unreadNotificationsCount > 9 ? '9+' : unreadNotificationsCount }}
              </span>
            </button>
          </template>
          <template #body="{ close }">
            <div
              class="mt-2 w-[360px] overflow-hidden rounded-xl border border-outline-gray-2 bg-surface-white text-ink-gray-9 shadow-2xl"
            >
              <div
                class="flex items-center justify-between border-b border-outline-gray-modals px-4 py-2.5"
              >
                <span class="text-p-base font-semibold">{{ __('Thông báo') }}</span>
                <button
                  v-if="unreadNotificationsCount"
                  type="button"
                  class="rounded text-p-sm font-medium text-teal-700 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
                  @click="markAllRead"
                >
                  {{ __('Đánh dấu đã đọc') }}
                </button>
              </div>
              <div class="max-h-[60vh] overflow-auto">
                <template v-if="notifications.data && notifications.data.length">
                  <button
                    v-for="n in notifications.data"
                    :key="n.comment || n.creation"
                    type="button"
                    class="flex w-full items-start gap-2.5 border-b border-outline-gray-1 px-4 py-3 text-left hover:bg-surface-gray-2 focus-visible:bg-surface-gray-2 focus-visible:outline-none"
                    @click="openNotification(n, close)"
                  >
                    <span
                      class="mt-1.5 size-2 shrink-0 rounded-full"
                      :class="n.read ? 'bg-transparent' : 'bg-teal-600'"
                    />
                    <div class="min-w-0 flex-1">
                      <!-- eslint-disable-next-line vue/no-v-html -->
                      <div
                        v-if="n.notification_text"
                        class="text-p-sm text-ink-gray-8"
                        v-html="sanitizeHTML(n.notification_text)"
                      />
                      <div v-else class="text-p-sm text-ink-gray-8">
                        {{ n.subject || n.from_user?.full_name || __('Thông báo mới') }}
                      </div>
                      <div class="mt-0.5 text-p-xs text-ink-gray-5">
                        {{ timeAgo(n.creation) }}
                      </div>
                    </div>
                  </button>
                </template>
                <div
                  v-else
                  class="flex flex-col items-center gap-2 px-4 py-10 text-center text-ink-gray-5"
                >
                  <NotificationsIcon
                    class="h-7 w-7 text-ink-gray-4"
                    aria-hidden="true"
                  />
                  <span class="text-p-sm">{{ __('Chưa có thông báo nào') }}</span>
                </div>
              </div>
            </div>
          </template>
        </Popover>

        <!-- Avatar người dùng THẬT → Trang cá nhân (profile.me); Đăng xuất nằm trong profile. -->
        <RouterLink
          to="/antmed/profile"
          class="rounded-full ring-2 ring-white/40 transition hover:ring-white/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-300"
          :aria-label="__('Trang cá nhân của tôi')"
          :title="userFullName || __('Trang cá nhân')"
        >
          <img
            v-if="userImage"
            :src="userImage"
            :alt="userFullName"
            class="h-7 w-7 rounded-full object-cover"
          />
          <span
            v-else
            class="flex h-7 w-7 select-none items-center justify-center rounded-full bg-white text-[12px] font-bold uppercase text-teal-900"
          >
            {{ userInitials }}
          </span>
        </RouterLink>
      </div>
    </header>

    <!-- Body: sidebar 200px (grouped, toàn diện) + main -->
    <div class="flex min-h-0 flex-1">
      <nav
        class="w-[200px] shrink-0 overflow-y-auto border-r border-outline-gray-1 bg-surface-gray-1 p-1.5"
        :aria-label="__('Điều hướng AntMed')"
      >
        <template v-for="sec in displaySections" :key="sec.title">
          <div
            class="px-2.5 pb-1 pt-3 text-[10px] font-semibold uppercase tracking-wide text-ink-gray-5"
          >
            {{ __(sec.title) }}
          </div>
          <template v-for="item in sec.items" :key="item.key">
            <RouterLink
              v-if="item.enabled"
              :to="item.to"
              class="mb-0.5 flex items-center gap-2 rounded-md px-2.5 py-2 text-p-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
              :class="
                isNavActive(item, route.path)
                  ? 'bg-teal-50 font-semibold text-teal-900'
                  : 'text-ink-gray-7 hover:bg-surface-gray-3'
              "
              :aria-current="isNavActive(item, route.path) ? 'page' : undefined"
            >
              <component
                :is="iconFor(item.icon)"
                class="h-4 w-4 shrink-0"
                aria-hidden="true"
              />
              <span>{{ __(item.label) }}</span>
            </RouterLink>

            <div
              v-else
              class="mb-0.5 flex items-center gap-2 rounded-md px-2.5 py-2 text-p-sm text-ink-gray-4"
              aria-disabled="true"
              :title="__('Sắp có')"
            >
              <component
                :is="iconFor(item.icon)"
                class="h-4 w-4 shrink-0"
                aria-hidden="true"
              />
              <span class="flex-1">{{ __(item.label) }}</span>
              <span
                class="rounded bg-ink-gray-2 px-1 py-0.5 text-[10px] font-medium text-ink-gray-5"
              >
                {{ __('Sắp có') }}
              </span>
            </div>
          </template>
        </template>
      </nav>

      <main class="min-w-0 flex-1 overflow-auto bg-surface-white">
        <slot />
      </main>
    </div>

    <AntmedQuickSearch v-model:open="searchOpen" />
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ANTMED_ROLES,
  ANTMED_SECTIONS,
  ROLE_NAV,
  navForRole,
  isNavActive,
} from '@/data/antmedNav'
import { Dropdown, FeatherIcon, Popover } from 'frappe-ui'
import {
  notifications,
  notificationsStore,
  unreadNotificationsCount,
} from '@/stores/notifications'
import { timeAgo, sanitizeHTML } from '@/utils'
import { sessionStore } from '@/stores/session'
import { usersStore } from '@/stores/users'

// Icon THƯ VIỆN (lucide-based SVG component có sẵn @/components/Icons/*) — thay emoji
// tự chế trong nav data. Map icon-key (emoji legacy hoặc tên) → component; unmapped → List.
import DashboardIcon from '@/components/Icons/DashboardIcon.vue'
import ActivityIcon from '@/components/Icons/ActivityIcon.vue'
import MoneyIcon from '@/components/Icons/MoneyIcon.vue'
import NotificationsIcon from '@/components/Icons/NotificationsIcon.vue'
import OrganizationsIcon from '@/components/Icons/OrganizationsIcon.vue'
import FileTextIcon from '@/components/Icons/FileTextIcon.vue'
import KanbanIcon from '@/components/Icons/KanbanIcon.vue'
import ContactsIcon from '@/components/Icons/ContactsIcon.vue'
import ExportIcon from '@/components/Icons/ExportIcon.vue'
import InboxIcon from '@/components/Icons/InboxIcon.vue'
import LinkIcon from '@/components/Icons/LinkIcon.vue'
import CalendarIcon from '@/components/Icons/CalendarIcon.vue'
import AppsIcon from '@/components/Icons/AppsIcon.vue'
import WebsiteIcon from '@/components/Icons/WebsiteIcon.vue'
import EditIcon from '@/components/Icons/EditIcon.vue'
import ListIcon from '@/components/Icons/ListIcon.vue'
import AntmedQuickSearch from '@/components/Antmed/AntmedQuickSearch.vue'

const ICON_BY_KEY = {
  // điều hành / tài chính
  '📊': DashboardIcon,
  '🩺': ActivityIcon,
  '💰': MoneyIcon,
  '💳': MoneyIcon,
  '💼': MoneyIcon,
  '📈': ActivityIcon,
  '⚠': NotificationsIcon,
  // khách hàng / chứng từ
  '🏥': OrganizationsIcon,
  '📋': FileTextIcon,
  '📄': FileTextIcon,
  '📜': FileTextIcon,
  '📂': FileTextIcon,
  '🧾': FileTextIcon,
  '✍': EditIcon,
  // kinh doanh / kho
  '🎯': KanbanIcon,
  '👥': ContactsIcon,
  '👨‍⚕️': ContactsIcon,
  '🚚': ExportIcon,
  '📤': ExportIcon,
  '📦': InboxIcon,
  '📥': InboxIcon,
  '🔍': LinkIcon,
  '🔌': LinkIcon,
  '⏰': CalendarIcon,
  '🧰': AppsIcon,
  '🏠': WebsiteIcon,
}
const iconFor = (key) => ICON_BY_KEY[key] || ListIcon

const route = useRoute()
const router = useRouter()

// ── Quick-search command palette (⌘/Ctrl+K) ──
const searchOpen = ref(false)
function onGlobalKeydown(e) {
  if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) {
    e.preventDefault()
    searchOpen.value = true
  }
}
onMounted(() => window.addEventListener('keydown', onGlobalKeydown))
onUnmounted(() => window.removeEventListener('keydown', onGlobalKeydown))

// Thông báo (store CRM gốc, resource auto:true) + avatar user THẬT từ session cookie.
const { mark_as_read } = notificationsStore()
const { user: currentUser, logout } = sessionStore()
const { getUser } = usersStore()

// ── Popup thông báo (frappe-ui Popover) ──
function markAllRead() {
  mark_as_read.params = {}
  mark_as_read.reload()
}
function notificationRoute(n) {
  const params =
    n.route_name === 'Deal'
      ? { dealId: n.reference_name }
      : { leadId: n.reference_name }
  return { name: n.route_name, params, hash: n.hash }
}
function openNotification(n, close) {
  const doc = n.comment || n.notification_type_doc
  if (doc) {
    mark_as_read.params = { doc }
    mark_as_read.reload()
  }
  if (n.route_name) {
    try {
      router.push(notificationRoute(n))
    } catch (e) {
      // thông báo không có route khớp (vd thông báo AntMed) → bỏ điều hướng.
    }
  }
  if (close) close()
}

// ── Avatar: initials nền trắng/teal (tương phản trên header teal) hoặc ảnh nếu có ──
const userFullName = computed(
  () => getUser(currentUser.value)?.full_name || currentUser.value || '',
)
const userImage = computed(() => getUser(currentUser.value)?.user_image || '')
const userInitials = computed(() => {
  const parts = (userFullName.value || '?').trim().split(/\s+/).filter(Boolean)
  const ini = parts
    .slice(0, 2)
    .map((w) => w[0])
    .join('')
  return (ini || '?').toUpperCase()
})

function openProfile() {
  // Trang cá nhân TRONG SPA (profile.me) — xem được cho MỌI user (kể cả không có quyền Desk),
  // thay vì mở /app/user-profile (Desk) dễ bị "Not permitted".
  router.push('/antmed/profile')
}
const userMenu = computed(() => [
  {
    group:
      getUser(currentUser.value)?.full_name ||
      currentUser.value ||
      __('Tài khoản'),
    items: [
      { label: __('Hồ sơ người dùng'), icon: 'user', onClick: openProfile },
      { label: __('Đăng xuất'), icon: 'log-out', onClick: () => logout.submit() },
    ],
  },
])

// Bộ lọc vai trò TUỲ CHỌN (switcher-only, KHÔNG auto theo route.meta.role) →
// mặc định sidebar TOÀN DIỆN (mọi tính năng truy cập được từ /antmed).
const selectedRole = ref('')
const effectiveRole = computed(() => selectedRole.value || '')

// Sidebar grouped: rỗng → tất cả section (toàn diện); chọn role → 1 section nav vai trò đó.
const displaySections = computed(() => {
  const role = effectiveRole.value
  if (role && ROLE_NAV[role]) {
    const r = ANTMED_ROLES.find((x) => x.key === role)
    return [{ title: r ? r.label : role, items: navForRole(role) }]
  }
  return ANTMED_SECTIONS
})

const currentRole = computed(() =>
  ANTMED_ROLES.find((r) => r.key === effectiveRole.value),
)
const isPortal = computed(() => currentRole.value?.variant === 'portal')
const currentAvatar = computed(() => currentRole.value?.avatar || 'AM')

const periodLabel = computed(() => {
  const d = new Date()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  return `${__('Tháng')} ${mm}/${d.getFullYear()}`
})
</script>
