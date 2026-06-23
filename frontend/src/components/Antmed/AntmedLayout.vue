<template>
  <div class="flex h-screen w-screen flex-col">
    <!-- Topbar (mockup A1: teal-900; vai trò Portal G = nền trắng border) -->
    <header
      class="flex items-center gap-2 px-3 py-2.5 text-xs sm:gap-3.5 sm:px-4"
      :class="
        isPortal
          ? 'border-b border-outline-gray-2 bg-white text-teal-900'
          : 'bg-teal-900 text-white'
      "
    >
      <!-- Hamburger (mobile/tablet) — mở drawer sidebar -->
      <button
        type="button"
        class="-ml-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-300 lg:hidden"
        :class="isPortal ? 'hover:bg-surface-gray-2' : 'hover:bg-white/15'"
        :aria-label="__('Mở menu')"
        @click="mobileOpen = true"
      >
        <FeatherIcon name="menu" class="h-5 w-5" aria-hidden="true" />
      </button>

      <RouterLink
        to="/antmed"
        class="flex items-center gap-1.5 text-sm font-bold focus-visible:rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
      >
        <span aria-hidden="true">⚕</span>
        <span class="truncate">{{
          isPortal ? __('AntMed Portal') : __('AntMed CRM')
        }}</span>
      </RouterLink>

      <span
        v-if="!isPortal"
        class="hidden items-center gap-1 rounded-full bg-white/[0.14] px-2.5 py-0.5 text-[11px] md:inline-flex"
      >
        <FeatherIcon name="calendar" class="h-3 w-3" aria-hidden="true" />{{
          periodLabel
        }}
      </span>

      <button
        v-if="!isPortal"
        type="button"
        class="ml-2 hidden h-6 max-w-[300px] flex-1 items-center gap-1.5 rounded-full bg-white/[0.12] px-2.5 text-[11px] text-white/70 transition hover:bg-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-300 md:flex"
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

      <!-- Nhóm phải: tìm (mobile icon) + chuông + avatar -->
      <div class="ml-auto flex items-center gap-2 sm:gap-2.5">
        <button
          v-if="!isPortal"
          type="button"
          class="flex h-6 w-6 items-center justify-center rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-300 md:hidden"
          :class="isPortal ? 'hover:bg-surface-gray-2' : 'hover:bg-white/15'"
          :aria-label="__('Tìm kiếm')"
          @click="searchOpen = true"
        >
          <FeatherIcon name="search" class="h-4 w-4" aria-hidden="true" />
        </button>

        <!-- Chuông thông báo — popup dropdown (frappe-ui Popover) + badge chưa đọc -->
        <Popover>
          <template #target="{ togglePopover }">
            <button
              id="notifications-btn"
              type="button"
              class="relative flex h-6 w-6 items-center justify-center rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
              :class="
                isPortal ? 'hover:bg-surface-gray-2' : 'hover:bg-white/15'
              "
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
                {{
                  unreadNotificationsCount > 9 ? '9+' : unreadNotificationsCount
                }}
              </span>
            </button>
          </template>
          <template #body="{ close }">
            <div
              class="mt-2 w-[92vw] max-w-[360px] overflow-hidden rounded-xl border border-outline-gray-2 bg-surface-white text-ink-gray-9 shadow-2xl"
            >
              <div
                class="flex items-center justify-between border-b border-outline-gray-modals px-4 py-2.5"
              >
                <span class="text-p-base font-semibold">{{
                  __('Thông báo')
                }}</span>
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
                <template
                  v-if="notifications.data && notifications.data.length"
                >
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
                        {{
                          n.subject ||
                          n.from_user?.full_name ||
                          __('Thông báo mới')
                        }}
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
                  <span class="text-p-sm">{{
                    __('Chưa có thông báo nào')
                  }}</span>
                </div>
              </div>
            </div>
          </template>
        </Popover>

        <!-- Avatar người dùng THẬT → Trang cá nhân (profile.me) -->
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

    <!-- Body: sidebar (responsive: drawer mobile / collapsible desktop) + main -->
    <div class="relative flex min-h-0 flex-1">
      <!-- Backdrop drawer (mobile/tablet) -->
      <div
        v-if="mobileOpen"
        class="absolute inset-0 z-30 bg-black/40 lg:hidden"
        aria-hidden="true"
        @click="mobileOpen = false"
      />

      <nav
        class="absolute inset-y-0 left-0 z-40 flex w-64 flex-col overflow-hidden border-r border-outline-gray-1 bg-surface-gray-1 transition-all duration-200 ease-out lg:static lg:z-auto lg:translate-x-0"
        :class="[
          mobileOpen
            ? 'translate-x-0 shadow-2xl'
            : '-translate-x-full lg:translate-x-0',
          collapsed ? 'lg:w-[60px]' : 'lg:w-[240px]',
        ]"
        :aria-label="__('Điều hướng AntMed')"
      >
        <div class="flex-1 overflow-y-auto overflow-x-hidden p-1.5">
          <template v-for="sec in displaySections" :key="sec.title">
            <div
              class="px-2.5 pb-1 pt-3 text-[10px] font-semibold uppercase tracking-wide text-ink-gray-5"
              :class="collapsed ? 'lg:hidden' : ''"
            >
              {{ __(sec.title) }}
            </div>
            <!-- Khi thu gọn (desktop): 1 đường kẻ ngăn nhóm thay tiêu đề -->
            <div
              v-if="collapsed"
              class="mx-2 my-1 hidden border-t border-outline-gray-2 lg:block"
              aria-hidden="true"
            />

            <template v-for="item in sec.items" :key="item.key">
              <RouterLink
                v-if="item.enabled"
                :to="item.to"
                class="mb-0.5 flex items-center gap-2 rounded-md py-2 text-p-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
                :class="[
                  isNavActive(item, route.path)
                    ? 'bg-teal-50 font-semibold text-teal-900'
                    : 'text-ink-gray-7 hover:bg-surface-gray-3',
                  collapsed ? 'px-2.5 lg:justify-center lg:px-0' : 'px-2.5',
                ]"
                :aria-current="
                  isNavActive(item, route.path) ? 'page' : undefined
                "
                :title="collapsed ? __(item.label) : undefined"
                @click="mobileOpen = false"
              >
                <component
                  :is="iconFor(item.icon)"
                  class="h-4 w-4 shrink-0"
                  aria-hidden="true"
                />
                <span :class="collapsed ? 'lg:hidden' : ''">{{
                  __(item.label)
                }}</span>
              </RouterLink>

              <div
                v-else
                class="mb-0.5 flex items-center gap-2 rounded-md px-2.5 py-2 text-p-sm text-ink-gray-4"
                :class="collapsed ? 'lg:justify-center lg:px-0' : ''"
                aria-disabled="true"
                :title="__('Sắp có')"
              >
                <component
                  :is="iconFor(item.icon)"
                  class="h-4 w-4 shrink-0"
                  aria-hidden="true"
                />
                <span class="flex-1" :class="collapsed ? 'lg:hidden' : ''">{{
                  __(item.label)
                }}</span>
                <span
                  class="rounded bg-ink-gray-2 px-1 py-0.5 text-[10px] font-medium text-ink-gray-5"
                  :class="collapsed ? 'lg:hidden' : ''"
                >
                  {{ __('Sắp có') }}
                </span>
              </div>
            </template>
          </template>
        </div>

        <!-- Nút thu gọn / mở rộng (đáy sidebar) — desktop toggle icon-only; mobile = đóng drawer -->
        <button
          type="button"
          class="hidden items-center gap-2 border-t border-outline-gray-1 px-3 py-2.5 text-p-xs font-medium text-ink-gray-6 transition hover:bg-surface-gray-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 lg:flex"
          :class="collapsed ? 'lg:justify-center lg:px-0' : ''"
          :aria-label="collapsed ? __('Mở rộng menu') : __('Thu gọn menu')"
          @click="toggleCollapsed"
        >
          <FeatherIcon
            :name="collapsed ? 'chevrons-right' : 'chevrons-left'"
            class="h-4 w-4 shrink-0"
            aria-hidden="true"
          />
          <span :class="collapsed ? 'lg:hidden' : ''">{{ __('Thu gọn') }}</span>
        </button>
        <!-- Đóng drawer (mobile) -->
        <button
          type="button"
          class="flex items-center justify-center gap-2 border-t border-outline-gray-1 px-3 py-3 text-p-sm font-medium text-ink-gray-7 hover:bg-surface-gray-3 lg:hidden"
          @click="mobileOpen = false"
        >
          <FeatherIcon name="x" class="h-4 w-4" aria-hidden="true" />{{
            __('Đóng')
          }}
        </button>
      </nav>

      <main class="min-w-0 flex-1 overflow-auto bg-surface-white">
        <slot />
      </main>
    </div>

    <!-- Command palette overlay (⌘/Ctrl+K) -->
    <AntmedQuickSearch v-model:open="searchOpen" />
  </div>
</template>

<script setup>
import { computed, ref, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ANTMED_ROLES,
  ANTMED_SECTIONS,
  ROLE_NAV,
  navForRole,
  isNavActive,
} from '@/data/antmedNav'
import { FeatherIcon, Popover } from 'frappe-ui'
import {
  notifications,
  notificationsStore,
  unreadNotificationsCount,
} from '@/stores/notifications'
import { timeAgo, sanitizeHTML } from '@/utils'
import { sessionStore } from '@/stores/session'
import { usersStore } from '@/stores/users'

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
  '📊': DashboardIcon,
  '🩺': ActivityIcon,
  '💰': MoneyIcon,
  '💳': MoneyIcon,
  '💼': MoneyIcon,
  '📈': ActivityIcon,
  '⚠': NotificationsIcon,
  '🏥': OrganizationsIcon,
  '📋': FileTextIcon,
  '📄': FileTextIcon,
  '📜': FileTextIcon,
  '📂': FileTextIcon,
  '🧾': FileTextIcon,
  '✍': EditIcon,
  '🎯': KanbanIcon,
  '🧲': KanbanIcon,
  '👥': ContactsIcon,
  '👨‍⚕️': ContactsIcon,
  '🚚': ExportIcon,
  '🚦': KanbanIcon,
  '📤': ExportIcon,
  '📦': InboxIcon,
  '📥': InboxIcon,
  '✅': ListIcon,
  '🔍': LinkIcon,
  '🔌': LinkIcon,
  '⏰': CalendarIcon,
  '🧰': AppsIcon,
  '🏠': WebsiteIcon,
}
const iconFor = (key) => ICON_BY_KEY[key] || ListIcon

const route = useRoute()
const router = useRouter()

// ── Sidebar: thu gọn (desktop, lưu localStorage) + drawer (mobile/tablet) ──
const collapsed = ref(false)
try {
  collapsed.value = localStorage.getItem('antmed-sidebar-collapsed') === '1'
} catch {
  /* SSR / storage chặn → mặc định mở */
}
function toggleCollapsed() {
  collapsed.value = !collapsed.value
  try {
    localStorage.setItem(
      'antmed-sidebar-collapsed',
      collapsed.value ? '1' : '0',
    )
  } catch {
    /* noop */
  }
}
const mobileOpen = ref(false)
// Đổi route → đóng drawer mobile (tránh che nội dung).
watch(
  () => route.path,
  () => (mobileOpen.value = false),
)

// ── Quick-search command palette (⌘/Ctrl+K) ──
const searchOpen = ref(false)
function onGlobalKeydown(e) {
  if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) {
    e.preventDefault()
    searchOpen.value = true
  }
  if (e.key === 'Escape') mobileOpen.value = false
}
onMounted(() => window.addEventListener('keydown', onGlobalKeydown))
onUnmounted(() => window.removeEventListener('keydown', onGlobalKeydown))

// Thông báo + avatar user THẬT từ session cookie.
const { mark_as_read } = notificationsStore()
const { user: currentUser } = sessionStore()
const { getUser } = usersStore()

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
    } catch {
      /* thông báo không có route khớp → bỏ điều hướng */
    }
  }
  if (close) close()
}

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

// Bộ lọc vai trò TUỲ CHỌN → mặc định sidebar TOÀN DIỆN.
const selectedRole = ref('')
const effectiveRole = computed(() => selectedRole.value || '')
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

const periodLabel = computed(() => {
  const d = new Date()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  return `${__('Tháng')} ${mm}/${d.getFullYear()}`
})
</script>
