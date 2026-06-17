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
          :label="__('Số bệnh viện')"
          :value="overview.data?.hospital_count"
        />
        <AntmedKpiCard
          :label="__('Số bác sỹ')"
          :value="overview.data?.doctor_count"
        />
        <AntmedKpiCard
          :label="__('Doanh thu tháng')"
          empty
          :placeholder-hint="__('Sắp có (cần module Doanh thu)')"
        />
        <AntmedKpiCard
          :label="__('Quota đã dùng')"
          empty
          :placeholder-hint="__('Sắp có (cần module Hợp đồng & Quota)')"
        />
      </section>

      <!-- KPI phụ — SLA giao PT + Bộ DC lưu hành (placeholder) -->
      <section
        class="grid grid-cols-1 gap-4 sm:grid-cols-2"
        :aria-label="__('Chỉ số vận hành')"
      >
        <AntmedKpiCard
          :label="__('SLA giao phòng mổ')"
          empty
          :placeholder-hint="__('Sắp có (cần module Giao phòng mổ)')"
        />
        <AntmedKpiCard
          :label="__('Bộ DC lưu hành')"
          empty
          :placeholder-hint="__('Sắp có (cần module Bộ dụng cụ)')"
        />
      </section>

      <!-- Hàng 2 — 12-col: Top 10 Bệnh viện theo doanh thu (placeholder) -->
      <section class="grid grid-cols-1 gap-4" :aria-label="__('Xếp hạng bệnh viện')">
        <AntmedPlaceholderPanel
          :title="__('Top 10 Bệnh viện theo doanh thu')"
          :hint="__('Sắp có (cần module Doanh thu)')"
        />
      </section>

      <!-- Hàng 3 — 2-col: Pipeline gói thầu + Cảnh báo điều hành (placeholder) -->
      <section
        class="grid grid-cols-1 gap-4 lg:grid-cols-2"
        :aria-label="__('Pipeline và cảnh báo')"
      >
        <AntmedPlaceholderPanel
          :title="__('Pipeline gói thầu')"
          :hint="__('Sắp có (cần module Pipeline gói thầu)')"
        />
        <AntmedPlaceholderPanel
          :title="__('Cảnh báo điều hành')"
          :hint="__('Sắp có (cần module Công nợ / Bộ dụng cụ)')"
        />
      </section>
    </template>
  </main>
</template>

<script setup>
import { computed } from 'vue'
import { toast } from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import AntmedKpiCard from '@/components/Antmed/AntmedKpiCard.vue'
import AntmedPlaceholderPanel from '@/components/Antmed/AntmedPlaceholderPanel.vue'
import { getDashboardOverview } from '@/data/antmed'

// M11 Slice 2: KPI nền đếm THẬT (BV/Bác sỹ) từ crm.api.antmed.dashboard.overview.
// overview trả RAW dict THƯỜNG { hospital_count, doctor_count } → đọc overview.data.* TRỰC TIẾP
// (KHÔNG .data.data — khác list endpoint bọc). Các card chưa-nguồn = placeholder, KHÔNG bịa số.
const overview = getDashboardOverview({
  auto: true,
  onError(err) {
    toast.error(err.messages?.[0] || __('Không tải được số liệu dashboard'))
  },
})

const errorMessage = computed(
  () =>
    overview.error?.messages?.[0] ||
    overview.error?.message ||
    __('Không tải được số liệu dashboard'),
)
</script>
