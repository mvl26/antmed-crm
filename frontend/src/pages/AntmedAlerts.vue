<template>
  <main class="flex h-full flex-col" aria-labelledby="antmed-alerts-title">
    <!-- Header + breadcrumb (mockup A1 widget "⚠ Cảnh báo điều hành") -->
    <header class="flex flex-col gap-2 border-b border-outline-gray-modals px-6 py-4">
      <nav class="text-p-xs text-ink-gray-5" :aria-label="__('Đường dẫn')">
        <RouterLink
          to="/antmed"
          class="rounded text-ink-gray-6 hover:text-ink-gray-8 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
        >
          {{ __('Trang chủ') }}
        </RouterLink>
        <span class="px-1.5 text-ink-gray-4" aria-hidden="true">›</span>
        <span class="text-ink-gray-7">{{ __('Cảnh báo điều hành') }}</span>
      </nav>
      <div class="flex flex-col gap-1">
        <h1 id="antmed-alerts-title" class="text-xl font-semibold text-ink-gray-9">
          {{ __('Cảnh báo điều hành') }}
        </h1>
        <p class="text-p-sm text-ink-gray-6">
          {{ __('Quota chạm ngưỡng 70/90/100% và hợp đồng sắp / đã hết hạn (≤ 30 ngày)') }}
        </p>
      </div>
    </header>

    <!-- Tri-branch: loading / error / data -->
    <section class="flex-1 overflow-auto px-6 pb-6 pt-4" aria-live="polite">
      <!-- Loading -->
      <div
        v-if="alerts.loading"
        class="flex items-center justify-center gap-2 py-16 text-ink-gray-6"
      >
        <LoadingIndicator class="h-4 w-4" />
        <span class="text-p-base">{{ __('Đang tải cảnh báo…') }}</span>
      </div>

      <!-- Error -->
      <div
        v-else-if="alerts.error"
        class="flex flex-col items-center gap-3 py-16 text-center"
        role="alert"
      >
        <Badge variant="subtle" theme="red" size="lg" :label="__('Không tải được')" />
        <p class="max-w-md text-p-sm text-ink-gray-6">{{ errorMessage }}</p>
        <Button variant="outline" :label="__('Thử lại')" @click="alerts.reload()" />
      </div>

      <!-- Empty (total_count = 0) -->
      <div
        v-else-if="!rows.length"
        class="flex flex-col items-center gap-2 py-16 text-center text-ink-gray-6"
      >
        <p class="text-p-base">{{ __('Không có cảnh báo.') }}</p>
        <p class="text-p-sm">
          {{ __('Tất cả hợp đồng trong ngưỡng an toàn.') }}
        </p>
      </div>

      <!--
        Data: danh sách dòng cảnh báo — GIỮ NGUYÊN thứ tự BE trả (quota threshold desc
        trước, rồi expiry gần hạn trước). FE KHÔNG sort lại, KHÔNG tự tính ngưỡng/màu
        ngoài map kind+threshold+dấu days (helper thuần antmedUi).
      -->
      <ul v-else class="flex flex-col gap-2" role="list">
        <li
          v-for="(alert, idx) in rows"
          :key="alert.contract + ':' + alert.kind + ':' + (alert.item || idx)"
          role="link"
          tabindex="0"
          :aria-label="alertPillLabel(alert) + ': ' + alertText(alert)"
          class="flex cursor-pointer items-center gap-3 rounded-r-md border-l-4 px-3 py-2.5 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
          :class="rowAccentClass(alert)"
          @click="openContract(alert)"
          @keydown.enter="openContract(alert)"
        >
          <!-- Pill: màu theo threshold/days + nhãn CHỮ (WCAG, không chỉ màu) -->
          <span
            class="inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-p-xs font-semibold uppercase tracking-wide"
            :class="pillClass(alertPillTheme(alert))"
          >
            {{ alertPillLabel(alert) }}
          </span>
          <!-- Nội dung VI: tên BV / VT (KHÔNG mã thô) -->
          <span class="min-w-0 flex-1 truncate text-p-sm text-ink-gray-8">
            {{ alertText(alert) }}
          </span>
          <span class="shrink-0 text-ink-gray-4" aria-hidden="true">›</span>
        </li>
      </ul>

      <!-- Tổng số (count == rows) -->
      <p
        v-if="!alerts.loading && !alerts.error && rows.length"
        class="pt-3 text-p-sm text-ink-gray-5"
      >
        {{ __('Tổng cộng') }}: {{ totalCount }} {{ __('cảnh báo') }}
      </p>
    </section>
  </main>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { Badge, Button, toast } from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import { getQuotaAlerts } from '@/data/antmed'
// prettier-ignore
import { alertPillTheme, alertPillLabel, alertText, pillClass } from '@/utils/antmedUi'

const router = useRouter()

// Resource — endpoint trả dict bọc { data, total_count }, đọc r.data.data (KHÔNG createListResource).
const alerts = getQuotaAlerts({ auto: true })

// FE GIỮ NGUYÊN thứ tự BE (đã sort: quota threshold desc, rồi expiry gần hạn trước) — KHÔNG sort lại.
const rows = computed(() => alerts.data?.data || [])
const totalCount = computed(() => alerts.data?.total_count ?? rows.value.length)

const errorMessage = computed(
  () =>
    alerts.error?.messages?.[0] ||
    alerts.error?.message ||
    __('Không tải được cảnh báo điều hành'),
)

// Surface lỗi BR-XX / permission từ BE qua toast (ngoài banner tri-branch).
alerts.onError = (err) => {
  toast.error(err?.messages?.[0] || __('Không tải được cảnh báo điều hành'))
}

// Viền trái border-l-4 theo theme pill (danger → đỏ, warn → cam) — token, KHÔNG hex thô.
const ACCENT_CLASS = {
  danger: 'border-l-red-500 bg-red-50 hover:bg-red-100',
  warn: 'border-l-orange-500 bg-amber-50 hover:bg-amber-100',
}
function rowAccentClass(alert) {
  return ACCENT_CLASS[alertPillTheme(alert)] || ACCENT_CLASS.warn
}

// Drill-down → Chi tiết HĐ (route AntmedContractDetail /antmed/contracts/:name đã đăng ký).
// Tái dùng màn chi tiết HĐ đã có; params { name: alert.contract } (KHÔNG mã thô lộ ra UI).
function openContract(alert) {
  if (!alert?.contract) return
  router.push({ name: 'AntmedContractDetail', params: { name: alert.contract } })
}
</script>
