<template>
  <main class="flex h-full flex-col" aria-labelledby="antmed-revenue-title">
    <!-- Header + breadcrumb 'Trang chủ › Doanh thu' -->
    <header class="flex flex-col gap-2 border-b border-outline-gray-modals px-6 py-4">
      <nav class="text-p-xs text-ink-gray-5" :aria-label="__('Đường dẫn')">
        <RouterLink
          to="/antmed"
          class="rounded text-ink-gray-6 hover:text-ink-gray-8 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
        >
          {{ __('Trang chủ') }}
        </RouterLink>
        <span class="px-1.5 text-ink-gray-4" aria-hidden="true">›</span>
        <span class="text-ink-gray-7">{{ __('Doanh thu') }}</span>
      </nav>
      <div class="flex flex-col gap-1">
        <h1 id="antmed-revenue-title" class="text-xl font-semibold text-ink-gray-9">
          {{ __('Doanh thu') }}
        </h1>
        <p class="text-p-sm text-ink-gray-6">
          {{ __('Doanh thu thực theo nhóm phân loại vật tư trong 12 tháng gần nhất') }}
        </p>
      </div>
    </header>

    <section class="flex-1 overflow-auto px-6 py-5">
      <!-- Card "Doanh thu theo Nhóm vật tư" (mockup A3) -->
      <div class="rounded-lg border border-outline-gray-2 bg-surface-white p-4">
        <div class="mb-3 flex flex-wrap items-baseline justify-between gap-2">
          <h2 class="text-base font-semibold text-teal-900">
            {{ __('Doanh thu theo Nhóm vật tư') }}
          </h2>
          <span
            v-if="!revenue.loading && !revenue.error"
            class="text-p-sm text-ink-gray-6"
          >
            {{ __('Tổng 12 tháng') }}:
            <b class="tabular-nums text-ink-gray-8">{{ formatVnMoney(grandTotal) }}</b>
          </span>
        </div>

        <!-- Tri-branch: loading / error(+Thử lại) / data -->
        <!-- Loading -->
        <div
          v-if="revenue.loading"
          class="flex items-center justify-center gap-2 py-16 text-ink-gray-6"
          aria-live="polite"
        >
          <LoadingIndicator class="h-4 w-4" />
          <span class="text-p-base">{{ __('Đang tải…') }}</span>
        </div>

        <!-- Error + nút Thử lại -->
        <div
          v-else-if="revenue.error"
          class="flex flex-col items-center gap-3 py-16 text-center"
          role="alert"
        >
          <Badge variant="subtle" theme="red" size="lg" :label="__('Lỗi tải doanh thu')" />
          <Button variant="outline" :label="__('Thử lại')" @click="revenue.reload()" />
        </div>

        <!-- Data — stacked bar 12 cột × tối đa 5 segment nhóm -->
        <div v-else>
          <!-- Legend 5 nhóm -->
          <ul
            class="mb-4 flex flex-wrap gap-x-4 gap-y-1.5"
            :aria-label="__('Chú giải nhóm vật tư')"
          >
            <li
              v-for="g in groups"
              :key="g.classification"
              class="flex items-center gap-1.5 text-p-xs text-ink-gray-7"
            >
              <span
                class="inline-block h-3 w-3 rounded-sm"
                :class="swatchClass(g.classification)"
                aria-hidden="true"
              />
              <span>{{ g.label }}</span>
            </li>
          </ul>

          <!-- Bar chart 12 cột (1 cột / tháng), mỗi cột chồng tối đa 5 segment -->
          <div
            class="flex h-56 items-end gap-1.5"
            role="img"
            :aria-label="
              __('Biểu đồ cột chồng doanh thu theo nhóm vật tư, 12 tháng gần nhất')
            "
          >
            <div
              v-for="(month, i) in months"
              :key="month + '-' + i"
              class="flex h-full flex-1 flex-col items-center justify-end gap-1"
            >
              <!-- Cột chồng: vẽ từ trên xuống theo thứ tự nhóm; mỗi segment cao theo % giá trị -->
              <div
                class="flex w-full flex-col-reverse overflow-hidden rounded-t-sm"
                :style="{ height: '100%' }"
              >
                <div
                  v-for="g in groups"
                  :key="g.classification + '-' + i"
                  class="w-full"
                  :class="barClass(g.classification)"
                  :style="{ height: segmentHeight(g.monthly[i]) + '%' }"
                  :title="
                    g.label + ': ' + formatVnMoney(g.monthly[i]) + ' (' + month + ')'
                  "
                />
              </div>
              <!-- Nhãn tháng trục X -->
              <span class="text-p-xs tabular-nums text-ink-gray-5">{{ month }}</span>
            </div>
          </div>

          <!-- Empty hint khi không có doanh thu (mọi cột 0 nhưng vẫn render khung 12 cột) -->
          <p
            v-if="!grandTotal"
            class="pt-3 text-center text-p-sm text-ink-gray-5"
          >
            {{ __('Chưa có dữ liệu doanh thu trong 12 tháng gần nhất.') }}
          </p>
        </div>
      </div>

      <!-- Card "Doanh thu theo NV Kinh doanh × Bệnh viện" (mockup A3 dòng 325-334) -->
      <div class="mt-5 rounded-lg border border-outline-gray-2 bg-surface-white p-4">
        <div class="mb-3 flex flex-wrap items-baseline justify-between gap-2">
          <h2 class="text-base font-semibold text-teal-900">
            {{ __('Doanh thu theo NV Kinh doanh × Bệnh viện') }}
          </h2>
          <span
            v-if="!repHosp.loading && !repHosp.error"
            class="text-p-sm text-ink-gray-6"
          >
            {{ __('Tổng') }}:
            <b class="tabular-nums text-ink-gray-8">{{ formatVnMoney(repHospGrand) }}</b>
          </span>
        </div>

        <!-- Tri-branch: loading / error(+Thử lại) / data -->
        <div
          v-if="repHosp.loading"
          class="flex items-center justify-center gap-2 py-12 text-ink-gray-6"
          aria-live="polite"
        >
          <LoadingIndicator class="h-4 w-4" />
          <span class="text-p-base">{{ __('Đang tải…') }}</span>
        </div>

        <div
          v-else-if="repHosp.error"
          class="flex flex-col items-center gap-3 py-12 text-center"
          role="alert"
        >
          <Badge variant="subtle" theme="red" size="lg" :label="__('Lỗi tải doanh thu')" />
          <Button variant="outline" :label="__('Thử lại')" @click="repHosp.reload()" />
        </div>

        <!-- Empty-state: không có Deal Won nào → KHÔNG vỡ layout -->
        <div
          v-else-if="!repHospRows.length"
          class="py-12 text-center text-p-sm text-ink-gray-5"
        >
          {{ __('Chưa có dữ liệu doanh thu') }}
        </div>

        <!-- Data — ma trận heat NV × BV (hàng = NV, cột = BV + cột Tổng (tr)) -->
        <div v-else class="overflow-x-auto">
          <table class="w-full border-separate border-spacing-1 text-p-xs">
            <thead>
              <tr>
                <th class="px-2 py-1 text-left font-semibold text-ink-gray-7">
                  {{ __('NV') }}
                </th>
                <th
                  v-for="h in repHospHospitals"
                  :key="h.key"
                  class="px-2 py-1 text-center font-semibold text-ink-gray-7"
                >
                  {{ h.label }}
                </th>
                <th class="px-2 py-1 text-right font-semibold text-ink-gray-7">
                  {{ __('Tổng (tr)') }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in repHospRows" :key="row.deal_owner">
                <td class="whitespace-nowrap px-2 py-1 text-left text-ink-gray-8">
                  {{ row.full_name }}
                </td>
                <td
                  v-for="(cell, ci) in row.cells"
                  :key="row.deal_owner + '-' + ci"
                  class="rounded px-2 py-1 text-center tabular-nums"
                  :class="cell ? heatCellClass(cell.heat) : 'text-ink-gray-4'"
                >
                  {{ cell ? formatTrieu(cell.value) : '—' }}
                </td>
                <td class="px-2 py-1 text-right tabular-nums text-ink-gray-9">
                  <b>{{ formatTrieu(row.total) }}</b>
                </td>
              </tr>
            </tbody>
          </table>

          <!-- Legend 4 mức heat (mockup A3 .legend) -->
          <ul
            class="mt-3 flex flex-wrap gap-x-4 gap-y-1.5"
            :aria-label="__('Chú giải mức doanh thu')"
          >
            <li
              v-for="lv in heatLegend"
              :key="lv.key"
              class="flex items-center gap-1.5 text-p-xs text-ink-gray-7"
            >
              <span
                class="inline-block h-3 w-3 rounded-sm"
                :class="lv.swatch"
                aria-hidden="true"
              />
              <span>{{ lv.label }}</span>
            </li>
          </ul>
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
import { getRevenueByGroup, getRevenueByRepHospital } from '@/data/antmed'
import {
  formatVnMoney,
  revenueGroupBarClass,
  revenueGroupSwatchClass,
  stackSegmentHeightPct,
  stackColumnTotals,
  stackColumnMax,
  heatCellClass,
  HEAT_LEGEND,
  formatTrieu,
} from '@/utils/antmedUi'

// Resource — dict THƯỜNG (KHÔNG bọc list) → đọc r.data.months / r.data.groups / r.data.grand_total
// TRỰC TIẾP (idiom dict thường, KHÁC list bọc 2 tầng). method GET BẮT BUỘC (revenue_by_group KHÔNG
// params → POST mặc định → BE 403). FE KHÔNG sort/reduce/aggregate doanh thu — đọc thẳng groups[].monthly
// (BE đã gộp bucket + classification).
const revenue = getRevenueByGroup({ auto: true })
revenue.onError = (err) => {
  toast.error(err?.messages?.[0] || __('Không tải được doanh thu theo nhóm vật tư'))
}

const months = computed(() => revenue.data?.months || [])
const groups = computed(() => revenue.data?.groups || [])
const grandTotal = computed(() => revenue.data?.grand_total ?? 0)

// Scale trục Y (THUẦN TRÌNH BÀY qua helper PURE — KHÔNG aggregate doanh thu nghiệp vụ ở page).
const columnMax = computed(() =>
  stackColumnMax(stackColumnTotals(groups.value, months.value.length)),
)

function segmentHeight(value) {
  return stackSegmentHeightPct(value, columnMax.value)
}
function barClass(classification) {
  return revenueGroupBarClass(classification)
}
function swatchClass(classification) {
  return revenueGroupSwatchClass(classification)
}

// ── Widget heat "Doanh thu theo NV Kinh doanh × Bệnh viện" (mockup A3) — resource ĐỘC LẬP ──
// Dict THƯỜNG → đọc r.data.rows / hospitals / max_cell / grand_total TRỰC TIẾP (KHÔNG bọc 2 tầng).
// FE KHÔNG reduce/sort/aggregate — BE đã gộp (owner×hospital), sort rows DESC, tính heat/total.
const repHosp = getRevenueByRepHospital({ auto: true })
repHosp.onError = (err) => {
  toast.error(err?.messages?.[0] || __('Không tải được doanh thu theo NV × Bệnh viện'))
}

const repHospRows = computed(() => repHosp.data?.rows || [])
const repHospHospitals = computed(() => repHosp.data?.hospitals || [])
const repHospGrand = computed(() => repHosp.data?.grand_total ?? 0)
const heatLegend = HEAT_LEGEND
</script>
