<template>
  <main class="flex h-full flex-col" aria-labelledby="antmed-consignment-title">
    <!-- Header + breadcrumb: Trang chủ › Kho ký gửi BV -->
    <header
      class="flex flex-col gap-3 border-b border-outline-gray-modals px-6 py-4 sm:flex-row sm:items-end sm:justify-between"
    >
      <div class="flex flex-col gap-2">
        <nav class="text-p-xs text-ink-gray-5" :aria-label="__('Đường dẫn')">
          <RouterLink
            to="/antmed"
            class="rounded text-ink-gray-6 hover:text-ink-gray-8 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
          >
            {{ __('Trang chủ') }}
          </RouterLink>
          <span class="px-1.5 text-ink-gray-4" aria-hidden="true">›</span>
          <span class="text-ink-gray-7" aria-current="page">{{
            __('Kho ký gửi BV')
          }}</span>
        </nav>
        <div class="flex flex-col gap-1">
          <h1
            id="antmed-consignment-title"
            class="text-xl font-semibold text-ink-gray-9"
          >
            {{ __('Kho ký gửi tại Bệnh viện') }}
          </h1>
          <p class="text-p-sm text-ink-gray-6">
            {{
              __(
                'Tồn vật tư ký gửi theo từng Bệnh viện (Lô / HSD / SL hệ thống)',
              )
            }}
          </p>
        </div>
      </div>

      <!-- Dropdown chọn Bệnh viện (param phát đi == lựa chọn UI — chống dead-control) -->
      <div class="flex flex-col gap-1 sm:w-72">
        <label
          for="cg-filter-hospital"
          class="text-p-xs font-medium text-ink-gray-6"
        >
          {{ __('Bệnh viện') }}
        </label>
        <FormControl
          id="cg-filter-hospital"
          type="select"
          :options="hospitalOptions"
          :modelValue="activeHospital"
          :disabled="!hospitalOptions.length"
          :aria-label="__('Chọn Bệnh viện có kho ký gửi')"
          @update:modelValue="setHospital"
        />
      </div>
    </header>

    <!-- Hàng KPI 3 thẻ thật (mockup D2): BV có ký gửi · giá trị tồn · cận date ≤90 ngày -->
    <section
      class="grid grid-cols-1 gap-3 px-6 pt-4 sm:grid-cols-3"
      :aria-label="__('Chỉ số kho ký gửi')"
    >
      <AntmedKpiCard
        :label="__('Bệnh viện có ký gửi')"
        :value="kpis.hospitals_with_consignment"
        :empty="consignment.loading || !!consignment.error"
        :placeholder-hint="__('Đang tải…')"
      />

      <!-- Tồn ký gửi (GIỮA): giá trị tồn tiền VI gọn + dòng phụ '<SKU> SKU · <lô> lô' -->
      <article
        class="flex flex-col gap-1 rounded-xl border border-outline-gray-1 bg-surface-white p-4"
      >
        <h3 class="text-p-sm font-medium text-ink-gray-6">
          {{ __('Tồn ký gửi') }}
        </h3>
        <p class="text-2xl font-semibold tabular-nums text-ink-gray-9">
          <template v-if="consignment.loading || consignment.error">—</template>
          <template v-else>{{ formatVnMoney(kpis.total_value) }}</template>
        </p>
        <p class="text-p-xs text-ink-gray-5">
          <template v-if="consignment.loading || consignment.error">—</template>
          <template v-else>
            {{ kpis.total_sku }} {{ __('SKU') }} · {{ kpis.total_lots }}
            {{ __('lô') }}
          </template>
        </p>
      </article>

      <!-- Cận date: tone danger (số lô tồn>0 cận date ≤90 ngày) -->
      <article
        class="flex flex-col gap-1 rounded-xl border p-4"
        :class="
          nearExpiryCount > 0
            ? 'border-red-200 bg-red-50'
            : 'border-outline-gray-1 bg-surface-white'
        "
      >
        <h3
          class="text-p-sm font-medium"
          :class="nearExpiryCount > 0 ? 'text-red-700' : 'text-ink-gray-6'"
        >
          {{ __('Cận date (≤90 ngày)') }}
        </h3>
        <p
          class="text-2xl font-semibold tabular-nums"
          :class="nearExpiryCount > 0 ? 'text-red-700' : 'text-ink-gray-9'"
        >
          <template v-if="consignment.loading || consignment.error">—</template>
          <template v-else>{{ nearExpiryCount }}</template>
        </p>
        <p
          class="text-p-xs"
          :class="nearExpiryCount > 0 ? 'text-red-600' : 'text-ink-gray-5'"
        >
          {{ __('Số lô tồn cận hạn sử dụng') }}
        </p>
      </article>
    </section>

    <!-- Tri-branch: loading / error / empty / data -->
    <section class="flex-1 overflow-auto px-6 pb-6 pt-4" aria-live="polite">
      <!-- Loading -->
      <div
        v-if="consignment.loading"
        class="flex items-center justify-center gap-2 py-16 text-ink-gray-6"
      >
        <LoadingIndicator class="h-4 w-4" />
        <span class="text-p-base">{{ __('Đang tải…') }}</span>
      </div>

      <!-- Error: banner + nút Thử lại reload -->
      <div
        v-else-if="consignment.error"
        class="flex flex-col items-center gap-3 py-16 text-center"
        role="alert"
      >
        <Badge
          variant="subtle"
          theme="red"
          size="lg"
          :label="__('Không tải được')"
        />
        <p class="max-w-md text-p-sm text-ink-gray-6">{{ errorMessage }}</p>
        <Button
          variant="outline"
          :label="__('Thử lại')"
          @click="consignment.reload()"
        />
      </div>

      <!-- Empty -->
      <div
        v-else-if="!rows.length"
        class="flex flex-col items-center gap-2 py-16 text-center text-ink-gray-6"
      >
        <p class="text-p-base">{{ __('Chưa có tồn ký gửi') }}</p>
        <p class="text-p-sm">
          {{ __('Bệnh viện này chưa có vật tư ký gửi còn tồn trong kho.') }}
        </p>
      </div>

      <!-- Data table: SKU / Tên VT / Lot / HSD / SL hệ thống / chip HSD -->
      <table v-else class="w-full border-separate border-spacing-0 text-left">
        <caption class="sr-only">
          {{
            __('Bảng tồn vật tư ký gửi tại Bệnh viện')
          }}
        </caption>
        <thead>
          <tr class="text-p-sm text-ink-gray-6">
            <th
              class="border-b border-outline-gray-modals py-2 pr-4 font-medium"
            >
              {{ __('SKU') }}
            </th>
            <th
              class="border-b border-outline-gray-modals py-2 pr-4 font-medium"
            >
              {{ __('Tên VT') }}
            </th>
            <th
              class="border-b border-outline-gray-modals py-2 pr-4 font-medium"
            >
              {{ __('Lot') }}
            </th>
            <th
              class="border-b border-outline-gray-modals py-2 pr-4 font-medium"
            >
              {{ __('HSD') }}
            </th>
            <th
              class="border-b border-outline-gray-modals py-2 pr-4 text-right font-medium"
            >
              {{ __('SL hệ thống') }}
            </th>
            <th class="border-b border-outline-gray-modals py-2 font-medium">
              {{ __('Trạng thái HSD') }}
            </th>
          </tr>
        </thead>
        <tbody>
          <!-- Row near_expiry → highlight nền đỏ nhạt (mockup D2 dòng cận date) -->
          <tr
            v-for="row in rows"
            :key="`${row.sku}|${row.lot}`"
            class="text-p-base text-ink-gray-8"
            :class="row.near_expiry ? 'bg-red-50' : ''"
          >
            <!-- SKU (item_code) — mã nhỏ phụ trợ -->
            <td
              class="border-b border-outline-gray-1 py-3 pr-4 font-mono text-p-sm text-ink-gray-7"
            >
              {{ row.sku || '—' }}
            </td>

            <!-- Tên VT: item_name (hiển thị tên, KHÔNG chỉ mã) -->
            <td
              class="border-b border-outline-gray-1 py-3 pr-4 font-medium text-ink-gray-9"
            >
              {{ row.item_name || row.sku || '—' }}
            </td>

            <!-- Lot -->
            <td
              class="border-b border-outline-gray-1 py-3 pr-4 text-ink-gray-7"
            >
              {{ row.lot || '—' }}
            </td>

            <!-- HSD: định dạng MM/YYYY -->
            <td
              class="border-b border-outline-gray-1 py-3 pr-4 tabular-nums text-ink-gray-7"
            >
              {{ formatExpiryMonthYear(row.expiry_date) || '—' }}
            </td>

            <!-- SL hệ thống -->
            <td
              class="border-b border-outline-gray-1 py-3 pr-4 text-right tabular-nums text-ink-gray-8"
            >
              {{ row.system_qty }}
            </td>

            <!-- Chip HSD: kèm CHỮ (không chỉ màu — WCAG AA) -->
            <td class="border-b border-outline-gray-1 py-3">
              <span
                class="inline-flex items-center rounded-full px-2 py-0.5 text-p-xs font-medium"
                :class="nearExpiryChipClass(row.near_expiry)"
              >
                {{ nearExpiryLabel(row.near_expiry) }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Tổng số dòng -->
      <p
        v-if="!consignment.loading && !consignment.error && rows.length"
        class="pt-3 text-p-sm text-ink-gray-5"
      >
        {{ __('Tổng cộng') }}: {{ rows.length }} {{ __('dòng tồn') }}
      </p>
    </section>
  </main>
</template>

<script setup>
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { Badge, Button, FormControl, toast } from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import AntmedKpiCard from '@/components/Antmed/AntmedKpiCard.vue'
import { getConsignmentStock } from '@/data/antmed'
import {
  formatExpiryMonthYear,
  formatVnMoney,
  nearExpiryChipClass,
  nearExpiryLabel,
} from '@/utils/antmedUi'

// BV đang xem (đồng bộ với r.data.hospital BE chọn khi None → BV đầu tiên).
const activeHospital = ref('')

// Endpoint trả RAW dict THƯỜNG { hospital, hospitals, kpis, rows } → đọc r.data.* TRỰC TIẾP
// (KHÔNG .data.data — cùng idiom getLot/getDashboardOverview). hospital None → BE lấy BV đầu tiên.
const consignment = getConsignmentStock({
  params: { hospital: null },
  auto: true,
})

// rows BE đã sort HSD sớm nhất trước → FE KHÔNG sort lại.
const rows = computed(() => consignment.data?.rows || [])
// Default ĐỦ 5 key khớp shape BE (CONSIGNMENT_KPI_KEYS) → KHÔNG undefined khi chưa load.
const kpis = computed(
  () =>
    consignment.data?.kpis || {
      hospitals_with_consignment: 0,
      near_expiry_lots: 0,
      total_value: 0,
      total_sku: 0,
      total_lots: 0,
    },
)
const nearExpiryCount = computed(() => kpis.value.near_expiry_lots ?? 0)
const hospitals = computed(() => consignment.data?.hospitals || [])

// Options dropdown: hiển thị hospital_name (KHÔNG lộ mã); value = name (khớp BE filter).
const hospitalOptions = computed(() =>
  hospitals.value.map((h) => ({
    value: h.name,
    label: h.hospital_name || h.name,
  })),
)

// Đồng bộ activeHospital theo BV BE đã chọn (lần fetch đầu hospital=null → BE trả BV đầu tiên).
consignment.onSuccess = (data) => {
  if (data?.hospital) activeHospital.value = data.hospital
}
consignment.onError = (err) => {
  toast.error(err?.messages?.[0] || __('Không tải được tồn ký gửi'))
}

const errorMessage = computed(
  () =>
    consignment.error?.messages?.[0] ||
    consignment.error?.message ||
    __('Không tải được tồn ký gửi'),
)

// Param phát đi == UI selection (chống dead-control LL-FE-13): chọn BV → update params + reload.
function setHospital(value) {
  activeHospital.value = value
  consignment.update({ params: { hospital: value } })
  consignment.reload()
}
</script>
