<template>
  <div class="flex h-screen w-screen flex-col">
    <!-- Topbar (mockup A1: thanh thương hiệu teal-900) -->
    <header
      class="flex items-center gap-3 bg-teal-900 px-4 py-2.5 text-white"
    >
      <RouterLink
        to="/antmed"
        class="flex items-center gap-1.5 font-semibold focus-visible:rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/70"
      >
        <span aria-hidden="true">⚕</span>
        <span>AntMed CRM</span>
      </RouterLink>

      <div
        class="ml-2 hidden max-w-xs flex-1 items-center gap-2 rounded-full bg-white/10 px-3 py-1.5 text-sm sm:flex"
      >
        <span aria-hidden="true">🔍</span>
        <input
          class="w-full bg-transparent text-white placeholder:text-white/60 focus:outline-none"
          :placeholder="__('Tìm bệnh viện / vật tư / NV...')"
          :aria-label="__('Tìm kiếm')"
        />
      </div>

      <span class="ml-auto rounded-full bg-white/15 px-2.5 py-1 text-xs">
        {{ periodLabel }}
      </span>
      <button
        type="button"
        class="rounded-full px-1.5 py-1 text-base hover:bg-white/15 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/70"
        :aria-label="__('Thông báo')"
      >
        <span aria-hidden="true">🔔</span>
      </button>
      <div
        class="flex h-7 w-7 items-center justify-center rounded-full bg-white text-xs font-bold text-teal-900"
        aria-hidden="true"
      >
        AM
      </div>
    </header>

    <!-- Body: sidebar 180px + main -->
    <div class="flex min-h-0 flex-1">
      <nav
        class="w-[180px] shrink-0 overflow-y-auto border-r border-outline-gray-1 bg-surface-gray-1 p-1.5"
        :aria-label="__('Điều hướng AntMed')"
      >
        <template v-for="item in nav" :key="item.key">
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
            <span aria-hidden="true">{{ item.icon }}</span>
            <span>{{ __(item.label) }}</span>
          </RouterLink>

          <div
            v-else
            class="mb-0.5 flex items-center gap-2 rounded-md px-2.5 py-2 text-p-sm text-ink-gray-4"
            aria-disabled="true"
            :title="__('Sắp có')"
          >
            <span aria-hidden="true">{{ item.icon }}</span>
            <span class="flex-1">{{ __(item.label) }}</span>
            <span
              class="rounded bg-ink-gray-2 px-1 py-0.5 text-[10px] font-medium text-ink-gray-5"
            >
              {{ __('Sắp có') }}
            </span>
          </div>
        </template>
      </nav>

      <main class="min-w-0 flex-1 overflow-auto bg-surface-white">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { ANTMED_NAV, isNavActive } from '@/data/antmedNav'

// Sidebar lấy từ single-source ANTMED_NAV (không lặp danh sách cứng ở template).
const nav = ANTMED_NAV
const route = useRoute()

// Chip kỳ báo cáo (mockup: "Tháng 05/2026"). Hiển thị tháng/năm hiện tại.
const periodLabel = computed(() => {
  const d = new Date()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  return `${__('Tháng')} ${mm}/${d.getFullYear()}`
})
</script>
