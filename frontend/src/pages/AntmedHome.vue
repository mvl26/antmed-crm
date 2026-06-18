<template>
  <main
    class="flex h-full flex-col gap-4 overflow-y-auto p-4 sm:p-6"
    aria-labelledby="antmed-home-title"
  >
    <header class="flex flex-col gap-1">
      <h1
        id="antmed-home-title"
        class="text-xl font-semibold text-ink-gray-9"
      >
        {{ __('Dashboard điều hành') }}
      </h1>
      <p class="text-p-sm text-ink-gray-6">
        {{ __('Tổng quan AntMed CRM') }}
      </p>
    </header>

    <!-- Tri-branch: loading / error / data (reuse pattern AntmedHome cũ) -->

    <!-- Loading -->
    <section
      v-if="overview.loading"
      class="flex items-center justify-center gap-2 rounded-xl bg-surface-gray-1 py-10 text-ink-gray-6"
      aria-live="polite"
    >
      <LoadingIndicator class="h-4 w-4" />
      <span class="text-p-base">{{ __('Đang tải số liệu…') }}</span>
    </section>

    <!-- Error -->
    <section
      v-else-if="overview.error"
      class="flex flex-col items-center gap-3 rounded-xl bg-surface-gray-1 py-8 text-center"
      role="alert"
    >
      <Badge
        variant="subtle"
        theme="red"
        :label="__('Không tải được số liệu')"
        size="lg"
      />
      <p class="text-p-sm text-ink-gray-6">
        {{ errorMessage }}
      </p>
      <Button
        variant="outline"
        :label="__('Thử lại')"
        @click="overview.reload()"
      />
    </section>

    <!-- Data -->
    <template v-else>
      <!-- Hàng 1 — KPI lớn (4 thẻ). 2 thẻ ĐẦU = số THẬT từ endpoint;
           2 thẻ sau = placeholder (chưa có module nguồn). -->
      <section
        class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4"
        :aria-label="__('Chỉ số tổng quan')"
      >
        <AntmedKpiCard
          tone="teal"
          icon="🏥"
          :label="__('Số bệnh viện')"
          :value="overview.data?.hospital_count"
        />
        <AntmedKpiCard
          tone="blue"
          icon="👨‍⚕️"
          :label="__('Số bác sỹ')"
          :value="overview.data?.doctor_count"
        />
        <!-- 'Doanh thu tháng' — số THẬT THÁNG hiện tại + delta MoM (M02-8, contract.monthly_revenue).
             loading → 'Đang tải…' (KHÔNG bịa số) · error → 'Lỗi tải doanh thu' (KHÔNG vỡ 4 cột) ·
             data → formatVnMoney(current)+'₫' (current=0 vẫn '0 ₫', số thật) + dòng phụ ▲/▼/— MoM. -->
        <AntmedKpiCard
          v-if="monthlyRevenue.loading"
          :label="__('Doanh thu tháng')"
          empty
          :placeholder-hint="__('Đang tải…')"
        />
        <AntmedKpiCard
          v-else-if="monthlyRevenue.error"
          :label="__('Doanh thu tháng')"
          empty
          :placeholder-hint="__('Lỗi tải doanh thu')"
        />
        <AntmedKpiCard
          v-else
          tone="green"
          icon="💰"
          :label="__('Doanh thu tháng')"
          :value="revenueValue"
          :sub="revenueSub"
        />
        <!-- 'Quota đã dùng' — số THẬT: ring % avg + dòng phụ 'N HĐ > 90%' (M02 land). -->
        <AntmedQuotaRing
          :label="__('Quota đã dùng')"
          :avg-pct="quotaSummary.data?.avg_quota_used_pct"
          :over-count="quotaSummary.data?.contracts_over_90_count"
        />
      </section>

      <!-- KPI phụ — SLA giao PT + Bộ DC lưu hành (placeholder) -->
      <section
        class="grid grid-cols-1 gap-4 sm:grid-cols-2"
        :aria-label="__('Chỉ số vận hành')"
      >
        <AntmedKpiCard
          tone="teal"
          icon="⏱️"
          :label="__('SLA giao phòng mổ')"
          empty
          :placeholder-hint="__('Sắp có (cần module Giao phòng mổ)')"
        />
        <AntmedKpiCard
          tone="blue"
          icon="🧰"
          :label="__('Bộ DC lưu hành')"
          empty
          :placeholder-hint="__('Sắp có (cần module Bộ dụng cụ)')"
        />
      </section>

      <!-- Hàng 2 — 2-col ≥lg: widget xếp hạng BV theo doanh thu HĐ (M02-4) + Cơ cấu doanh thu
           theo phân loại VTYT (M02-7). 2 resource fetch ĐỘC LẬP (mỗi card tự tri-branch
           loading/error(Thử lại)/empty). Xếp dọc mobile, cùng hàng từ lg. -->
      <section
        class="grid grid-cols-1 gap-4 lg:grid-cols-2"
        :aria-label="__('Xếp hạng bệnh viện và cơ cấu doanh thu')"
      >
        <AntmedTopHospitalsCard
          :items="topHospitals.data?.data || []"
          :total-count="topHospitals.data?.total_count || 0"
          :loading="topHospitals.loading"
          :error="!!topHospitals.error"
          @retry="topHospitals.reload()"
          @open="openHospital"
        />
        <AntmedRevenueMixCard
          :items="revenueMix.data?.data || []"
          :total-revenue="revenueMix.data?.total_revenue || 0"
          :loading="revenueMix.loading"
          :error="!!revenueMix.error"
          @retry="revenueMix.reload()"
        />
      </section>

      <!-- Hàng 3 — 2-col: Pipeline gói thầu (số THẬT, funnel 5 tầng) + Cảnh báo điều hành (số thật) -->
      <section
        class="grid grid-cols-1 gap-4 lg:grid-cols-2"
        :aria-label="__('Pipeline và cảnh báo')"
      >
        <!-- 'Pipeline gói thầu' — funnel 5 tầng đếm THẬT từ CRM Lead+Deal (tender_pipeline, M08).
             Dict THƯỜNG { stages, total } → đọc tenderPipeline.data.stages / .total TRỰC TIẾP
             (KHÔNG .data.data). Tri-branch loading/error(Thử lại)/empty xử lý trong card. -->
        <AntmedTenderFunnelCard
          :stages="tenderPipeline.data?.stages || []"
          :total="tenderPipeline.data?.total || 0"
          :loading="tenderPipeline.loading"
          :error="!!tenderPipeline.error"
          @retry="tenderPipeline.reload()"
        />
        <!-- '⚠ Cảnh báo điều hành' — số THẬT: pill alerts đỏ/cam từ quota_summary (M02 land).
             Tri-branch loading/error(Thử lại)/empty xử lý trong AntmedAlertsPanel. -->
        <AntmedAlertsPanel
          :alerts="quotaSummary.data?.alerts || []"
          :loading="quotaSummary.loading"
          :error="!!quotaSummary.error"
          @retry="quotaSummary.reload()"
        />
      </section>
    </template>
  </main>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import AntmedKpiCard from '@/components/Antmed/AntmedKpiCard.vue'
import AntmedQuotaRing from '@/components/Antmed/AntmedQuotaRing.vue'
import AntmedAlertsPanel from '@/components/Antmed/AntmedAlertsPanel.vue'
import AntmedTenderFunnelCard from '@/components/Antmed/AntmedTenderFunnelCard.vue'
import AntmedTopHospitalsCard from '@/components/Antmed/AntmedTopHospitalsCard.vue'
import AntmedRevenueMixCard from '@/components/Antmed/AntmedRevenueMixCard.vue'
import {
  getDashboardOverview,
  getQuotaSummary,
  getTenderPipeline,
  getTopHospitals,
  getRevenueMix,
  getMonthlyRevenue,
} from '@/data/antmed'
import { formatVnMoney, formatRevenueSub } from '@/utils/antmedUi'

const router = useRouter()

// M11 Slice 2: KPI nền đếm THẬT (BV/Bác sỹ) từ antmed_crm.api.antmed.dashboard.overview.
// overview trả RAW dict THƯỜNG { hospital_count, doctor_count } → đọc overview.data.* TRỰC TIẾP
// (KHÔNG .data.data — khác list endpoint bọc). Các card chưa-nguồn = placeholder, KHÔNG bịa số.
const overview = getDashboardOverview({
  auto: true,
  onError(err) {
    toast.error(err.messages?.[0] || __('Không tải được số liệu dashboard'))
  },
})

// M11 Slice M11-3: KPI quota + cảnh báo điều hành THẬT từ quota_summary (gộp HĐ/quota M02).
// Dict THƯỜNG { avg_quota_used_pct, contracts_over_90_count, alerts } → đọc quotaSummary.data.*
// TRỰC TIẾP (KHÔNG .data.data). Fetch ĐỘC LẬP với overview (panel tự tri-branch loading/error).
const quotaSummary = getQuotaSummary({
  auto: true,
  onError(err) {
    toast.error(err.messages?.[0] || __('Không tải được cảnh báo điều hành'))
  },
})

// M08 Slice 1: funnel "Pipeline gói thầu" (A1 Hàng 3) — đếm THẬT từ CRM Lead+Deal qua
// tender_pipeline. Dict THƯỜNG { stages, total } → đọc tenderPipeline.data.stages / .total
// TRỰC TIẾP (KHÔNG .data.data). Fetch ĐỘC LẬP (card AntmedTenderFunnelCard tự tri-branch
// loading/error/empty). FE KHÔNG đếm/map status (BR ở BE) — chỉ vẽ width bar theo count.
const tenderPipeline = getTenderPipeline({
  auto: true,
  onError(err) {
    toast.error(err.messages?.[0] || __('Không tải được pipeline gói thầu'))
  },
})

// M02-4: widget "Top 10 Bệnh viện" (A1 CEO — xếp hạng theo doanh thu HĐ) từ contract.top_hospitals.
// Dict bọc { data, total_count } → đọc topHospitals.data.data (list, sort GIẢM revenue ở BE) +
// topHospitals.data.total_count. Fetch ĐỘC LẬP (card tự tri-branch loading/error/empty).
// FE KHÔNG sort lại + KHÔNG tính ngưỡng màu (dùng health_color BE qua healthBarClass — card).
const topHospitals = getTopHospitals({
  auto: true,
  onError(err) {
    toast.error(err.messages?.[0] || __('Không tải được Top bệnh viện'))
  },
})

// M02-7: widget "Cơ cấu doanh thu" (A2 CEO — gộp cross-contract theo classification VTYT A/B/C/D)
// từ contract.revenue_mix. Dict bọc { data (4 dòng cố định A→B→C→D), total_revenue } → đọc
// revenueMix.data.data + revenueMix.data.total_revenue. Fetch ĐỘC LẬP với topHospitals (card tự
// tri-branch). method:'GET' đã set trong getRevenueMix (ADR-M02-14). FE KHÔNG sort/tính lại.
const revenueMix = getRevenueMix({
  auto: true,
  onError(err) {
    toast.error(err.messages?.[0] || __('Không tải được doanh thu tháng'))
  },
})

// M02-8: KPI lớn hàng 1 "Doanh thu tháng" — doanh thu THÁNG hiện tại + delta MoM THẬT từ
// contract.monthly_revenue. Dict THƯỜNG { current, previous, delta_pct, month_label, currency }
// → đọc monthlyRevenue.data.* TRỰC TIẾP (KHÔNG .data.data). FE KHÔNG tính lại current/previous/
// delta (BR rollup ở BE) — chỉ format VND (formatVnMoney) + dòng phụ (formatRevenueSub: ▲/▼/—
// theo dấu delta_pct). value=0 vẫn là SỐ THẬT '0 ₫' (KHÔNG placeholder 'Sắp có').
const monthlyRevenue = getMonthlyRevenue({
  auto: true,
  onError(err) {
    toast.error(err.messages?.[0] || __('Không tải được doanh thu tháng'))
  },
})

// value KPI: number THẬT → 'X tr/tỷ ₫' (formatVnMoney); current=0 → '0 ₫' (số thật, KHÔNG bịa).
// null/undefined (chưa có data) → null để card rơi nhánh empty 'Đang tải…' (KHÔNG hiện '— ₫').
const revenueValue = computed(() => {
  const cur = monthlyRevenue.data?.current
  if (cur === null || cur === undefined) return null
  return `${formatVnMoney(cur)} ₫`
})

// Dòng phụ 'T<m>/<yyyy> · ▲/▼ X% vs tháng trước' (mũi tên theo dấu; delta null → '— vs tháng trước').
const revenueSub = computed(() =>
  formatRevenueSub(
    monthlyRevenue.data?.month_label,
    monthlyRevenue.data?.delta_pct,
  ),
)

const errorMessage = computed(
  () =>
    overview.error?.messages?.[0] ||
    overview.error?.message ||
    __('Không tải được số liệu dashboard'),
)

// Drill-down → Chi tiết BV (route AntmedHospitalDetail /antmed/hospitals/:name đã đăng ký).
function openHospital(name) {
  router.push({ name: 'AntmedHospitalDetail', params: { name } })
}
</script>
