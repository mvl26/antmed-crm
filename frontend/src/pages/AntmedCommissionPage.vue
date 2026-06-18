<template>
  <main class="flex h-full flex-col" aria-labelledby="antmed-commission-title">
    <!-- Header + breadcrumb 'Trang chủ › Hoa hồng NV' -->
    <header class="flex flex-col gap-2 border-b border-outline-gray-modals px-6 py-4">
      <nav class="text-p-xs text-ink-gray-5" :aria-label="__('Đường dẫn')">
        <RouterLink
          to="/antmed"
          class="rounded text-ink-gray-6 hover:text-ink-gray-8 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
        >
          {{ __('Trang chủ') }}
        </RouterLink>
        <span class="px-1.5 text-ink-gray-4" aria-hidden="true">›</span>
        <span class="text-ink-gray-7">{{ __('Hoa hồng NV') }}</span>
      </nav>
      <div class="flex flex-col gap-1">
        <h1 id="antmed-commission-title" class="text-xl font-semibold text-ink-gray-9">
          {{ __('Hoa hồng Nhân viên') }}
        </h1>
        <p class="text-p-sm text-ink-gray-6">
          {{ __('Tổng hoa hồng kỳ và quy tắc tính theo doanh thu Won đóng trong kỳ') }}
        </p>
      </div>
    </header>

    <section class="flex-1 overflow-auto px-6 py-5">
      <!-- 2 card header (mockup F2): trái "Tổng hoa hồng kỳ" · phải "Quy tắc kỳ" -->
      <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <!-- ── Card trái: Tổng hoa hồng kỳ ─────────────────────────────────── -->
        <article
          class="flex flex-col gap-1 rounded-xl border border-outline-gray-1 bg-surface-white p-4"
        >
          <h2 class="text-p-sm font-medium text-ink-gray-6">
            {{ __('Tổng hoa hồng kỳ') }}
          </h2>

          <!-- Tri-branch: loading → error → data -->
          <div
            v-if="commission.loading"
            class="flex items-center gap-2 py-3 text-ink-gray-5"
            aria-live="polite"
          >
            <LoadingIndicator class="h-4 w-4" />
            <span class="text-p-base">{{ __('Đang tải…') }}</span>
          </div>

          <div v-else-if="commission.error" class="py-3" role="alert">
            <Badge variant="subtle" theme="red" size="lg" :label="__('Lỗi tải hoa hồng')" />
          </div>

          <template v-else>
            <!-- total_commission=0 → '0 ₫' (số THẬT, formatVnMoney(0)='0'); KHÔNG 'Sắp có'/'Chưa có'. -->
            <p class="text-2xl font-semibold tabular-nums text-ink-gray-9">
              {{ formatVnMoney(totalCommission) }} ₫
            </p>
            <p class="text-p-xs text-ink-gray-5">
              {{ repCount }} {{ __('NV') }} · {{ groupCount }} {{ __('nhóm vật tư') }}
            </p>
          </template>
        </article>

        <!-- ── Card phải: Quy tắc kỳ <period_label> ────────────────────────── -->
        <article
          class="flex flex-col gap-2 rounded-xl border border-outline-gray-1 bg-surface-white p-4"
        >
          <h2 class="text-p-sm font-medium text-ink-gray-6">
            {{ __('Quy tắc kỳ') }} {{ periodLabel }}
          </h2>

          <!-- Tri-branch: loading → error → data -->
          <div
            v-if="commission.loading"
            class="flex items-center gap-2 py-3 text-ink-gray-5"
            aria-live="polite"
          >
            <LoadingIndicator class="h-4 w-4" />
            <span class="text-p-base">{{ __('Đang tải…') }}</span>
          </div>

          <div v-else-if="commission.error" class="py-3" role="alert">
            <Badge variant="subtle" theme="red" size="lg" :label="__('Lỗi tải hoa hồng')" />
          </div>

          <!-- Data — danh sách quy tắc kỳ render TỪ data THẬT (KHÔNG hardcode JSX) -->
          <ul v-else class="flex flex-col gap-1.5" :aria-label="__('Quy tắc tính hoa hồng kỳ')">
            <li
              v-for="(rule, i) in rules"
              :key="rule.label + '-' + i"
              class="flex items-baseline justify-between gap-3 text-p-sm"
            >
              <span class="text-ink-gray-7">{{ rule.label }}</span>
              <b class="tabular-nums text-ink-gray-9">{{ rule.rate_pct }}%</b>
            </li>
            <li v-if="!rules.length" class="text-p-sm text-ink-gray-5">
              {{ __('Chưa có quy tắc cho kỳ này') }}
            </li>
          </ul>
        </article>
      </div>
    </section>
  </main>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { Badge, toast } from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import { getCommissionSummary } from '@/data/antmed'
import { formatVnMoney } from '@/utils/antmedUi'

// M09-1: KPI "Tổng hoa hồng kỳ" + "Quy tắc kỳ" (Kế toán, mockup F2) — THẬT từ
// finance.commission_summary. Dict THƯỜNG { total_commission, total_revenue, rep_count,
// group_count, period_label, flat_rate_pct, currency, rules } → đọc commission.data.* TRỰC TIẾP
// (KHÔNG .data.data). method GET BẮT BUỘC (endpoint period optional → POST mặc định → BE 403).
// FE KHÔNG sort/reduce/aggregate (BE đã gộp) — chỉ format VND + render rules từ data THẬT.
const commission = getCommissionSummary({
  auto: true,
  onError(err) {
    toast.error(err.messages?.[0] || __('Không tải được hoa hồng'))
  },
})

// total_commission=0 → '0 ₫' (số thật); chưa load (null/undefined) → 0 (card vẫn ở nhánh loading
// trước đó). FE KHÔNG tính lại (BR rollup ở BE) — chỉ đọc thẳng + format VND.
const totalCommission = computed(() => commission.data?.total_commission ?? 0)
const totalRevenue = computed(() => commission.data?.total_revenue ?? 0)
const repCount = computed(() => commission.data?.rep_count ?? 0)
const groupCount = computed(() => commission.data?.group_count ?? 0)
const periodLabel = computed(() => commission.data?.period_label || '')
// Danh sách quy tắc kỳ — đọc thẳng từ data THẬT (KHÔNG hardcode trong template).
const rules = computed(() => commission.data?.rules || [])
</script>
