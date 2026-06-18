<template>
  <main class="flex h-full flex-col" aria-labelledby="antmed-rep-title">
    <!-- Header + breadcrumb: Trang chủ › Đội ngũ › Hồ sơ NV -->
    <header class="flex flex-col gap-2 border-b border-outline-gray-modals px-6 py-4">
      <nav class="text-p-xs text-ink-gray-5" :aria-label="__('Đường dẫn')">
        <RouterLink
          to="/antmed"
          class="rounded text-ink-gray-6 hover:text-ink-gray-8 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
        >
          {{ __('Trang chủ') }}
        </RouterLink>
        <span class="px-1.5 text-ink-gray-4" aria-hidden="true">›</span>
        <RouterLink
          to="/antmed/sales/team"
          class="rounded text-ink-gray-6 hover:text-ink-gray-8 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
        >
          {{ __('Đội ngũ') }}
        </RouterLink>
        <span class="px-1.5 text-ink-gray-4" aria-hidden="true">›</span>
        <span class="text-ink-gray-7" aria-current="page">{{ __('Hồ sơ NV') }}</span>
      </nav>
      <div class="flex items-center justify-between gap-2">
        <h1 id="antmed-rep-title" class="text-xl font-semibold text-ink-gray-9">
          {{ __('Hồ sơ NV kinh doanh') }}
        </h1>
        <RouterLink to="/antmed/sales/team">
          <Button variant="outline" :label="__('Quay lại đội ngũ')">
            <template #prefix>
              <span aria-hidden="true">‹</span>
            </template>
          </Button>
        </RouterLink>
      </div>
    </header>

    <section class="flex-1 overflow-auto px-6 pb-6 pt-4" aria-live="polite">
      <!-- Loading -->
      <div
        v-if="rep.loading"
        class="flex items-center justify-center gap-2 py-16 text-ink-gray-6"
      >
        <LoadingIndicator class="h-4 w-4" />
        <span class="text-p-base">{{ __('Đang tải…') }}</span>
      </div>

      <!-- Error: banner + nút Thử lại reload -->
      <div
        v-else-if="rep.error"
        class="flex flex-col items-center gap-3 py-16 text-center"
        role="alert"
      >
        <Badge variant="subtle" theme="red" size="lg" :label="__('Lỗi tải hồ sơ')" />
        <p class="max-w-md text-p-sm text-ink-gray-6">{{ errorMessage }}</p>
        <Button variant="outline" :label="__('Thử lại')" @click="rep.reload()" />
      </div>

      <!-- Data -->
      <div v-else class="flex flex-col gap-5">
        <!-- Card "Hồ sơ" (B2 left): full_name + ngày vào làm + chips roles -->
        <article
          class="flex flex-col gap-3 rounded-xl border border-outline-gray-1 bg-surface-white p-5"
        >
          <div class="flex items-center gap-3">
            <Avatar
              size="2xl"
              :label="profile.full_name || __('NV kinh doanh')"
            />
            <div class="flex flex-col gap-0.5">
              <!-- full_name (KHÔNG lộ email/ID thô) -->
              <h2 class="text-lg font-semibold text-ink-gray-9">
                {{ profile.full_name || '—' }}
              </h2>
              <p class="text-p-sm text-ink-gray-6">
                {{ __('Ngày vào làm') }}:
                <span class="font-medium text-ink-gray-8">{{ formatJoinDate(profile.joined_on) }}</span>
              </p>
            </div>
          </div>

          <!-- Cấp/vai trò (roles nghiệp vụ). KHÔNG có nguồn → empty-state, KHÔNG bịa. -->
          <div class="flex flex-col gap-1.5">
            <h3 class="text-p-xs font-medium uppercase tracking-wide text-ink-gray-5">
              {{ __('Cấp / Vai trò') }}
            </h3>
            <div v-if="profile.roles && profile.roles.length" class="flex flex-wrap gap-1.5">
              <Badge
                v-for="role in profile.roles"
                :key="role"
                variant="subtle"
                theme="blue"
                size="md"
                :label="role"
              />
            </div>
            <p v-else class="text-p-sm text-ink-gray-4">
              {{ __('Chưa có thông tin vai trò') }}
            </p>
          </div>
        </article>

        <!-- Khối KPI 3 ô (DS tháng / Đơn mở / SLA đúng giờ) — tái dùng AntmedKpiCard + token -->
        <section
          class="grid grid-cols-1 gap-3 sm:grid-cols-3"
          :aria-label="__('Chỉ số tháng của NV')"
        >
          <AntmedKpiCard
            :label="__('DS tháng')"
            :value="formatVnMoney(kpi.month_sales)"
          />
          <AntmedKpiCard
            :label="__('Đơn mở')"
            :value="kpi.open_deals"
          />
          <AntmedKpiCard
            :label="__('SLA đúng giờ')"
            :value="`${kpi.sla_ontime_pct}%`"
          />
        </section>

        <!-- Bảng "Khách hàng phụ trách" -->
        <section class="flex flex-col gap-2">
          <h3 class="text-base font-semibold text-ink-gray-9">
            {{ __('Khách hàng phụ trách') }}
          </h3>

          <!-- Empty deals -->
          <div
            v-if="!deals.length"
            class="flex flex-col items-center gap-2 rounded-xl border border-dashed border-outline-gray-2 py-12 text-center text-ink-gray-6"
          >
            <p class="text-p-base">{{ __('Chưa có deal phụ trách') }}</p>
            <p class="text-p-sm">
              {{ __('NV này chưa có khách hàng/deal nào trong phạm vi của bạn.') }}
            </p>
          </div>

          <!-- Table deals: Khách hàng (organization) / Tuyến BV / Giá trị / Trạng thái -->
          <table v-else class="w-full border-separate border-spacing-0 text-left">
            <caption class="sr-only">
              {{ __('Bảng khách hàng/deal phụ trách của NV kinh doanh') }}
            </caption>
            <thead>
              <tr class="text-p-sm text-ink-gray-6">
                <th class="border-b border-outline-gray-modals py-2 pr-4 font-medium">
                  {{ __('Khách hàng') }}
                </th>
                <th class="border-b border-outline-gray-modals py-2 pr-4 font-medium">
                  {{ __('Tuyến BV') }}
                </th>
                <th class="border-b border-outline-gray-modals py-2 pr-4 text-right font-medium">
                  {{ __('Giá trị deal') }}
                </th>
                <th class="border-b border-outline-gray-modals py-2 font-medium">
                  {{ __('Trạng thái') }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in deals"
                :key="row.deal"
                class="text-p-base text-ink-gray-8"
              >
                <!-- Khách hàng (organization) -->
                <td class="border-b border-outline-gray-1 py-3 pr-4 font-medium text-ink-gray-9">
                  {{ row.organization || '— Chưa có tổ chức —' }}
                </td>

                <!-- Tuyến BV (territory) -->
                <td class="border-b border-outline-gray-1 py-3 pr-4 text-ink-gray-7">
                  {{ row.territory || '—' }}
                </td>

                <!-- Giá trị deal (formatVnMoney) -->
                <td class="border-b border-outline-gray-1 py-3 pr-4 text-right font-medium tabular-nums text-ink-gray-8">
                  {{ formatVnMoney(row.deal_value) }}
                </td>

                <!-- Trạng thái: chip màu theo status_theme BE (kèm CHỮ — WCAG) -->
                <td class="border-b border-outline-gray-1 py-3">
                  <span
                    class="inline-flex items-center rounded-full px-2 py-0.5 text-p-xs font-medium"
                    :class="repStatusChipClass(row.status_theme)"
                  >
                    {{ row.status || '—' }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>

          <p
            v-if="deals.length"
            class="pt-1 text-p-sm text-ink-gray-5"
          >
            {{ __('Tổng cộng') }}: {{ deals.length }} {{ __('deal') }}
          </p>
        </section>
      </div>
    </section>
  </main>
</template>

<script setup>
import { computed, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { Avatar, Badge, Button, toast } from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import AntmedKpiCard from '@/components/Antmed/AntmedKpiCard.vue'
import { getRepProfile } from '@/data/antmed'
import { formatVnMoney, formatJoinDate, repStatusChipClass } from '@/utils/antmedUi'

const props = defineProps({
  // owner = deal_owner (email) từ route param :owner — KHÔNG render email thô (chỉ dùng fetch + key).
  owner: { type: String, required: true },
})

// Endpoint trả RAW dict THƯỜNG { profile, kpi, deals } → đọc r.data.* TRỰC TIẾP
// (KHÔNG .data.data — cùng idiom getTeamRoster/getDashboardOverview).
const rep = getRepProfile(props.owner, {
  auto: true,
  onError(err) {
    toast.error(err?.messages?.[0] || __('Không tải được hồ sơ NV'))
  },
})

// Đổi owner (điều hướng giữa các NV) → fetch lại đúng param mới (param phát đi == route).
watch(
  () => props.owner,
  (next) => {
    rep.update({ params: { owner: next } })
    rep.reload()
  },
)

// BE đã tính/sort sẵn — FE KHÔNG sort/reduce/aggregate (đọc thẳng deals/kpi/profile).
const profile = computed(
  () => rep.data?.profile || { deal_owner: '', full_name: '', joined_on: null, roles: [] },
)
const kpi = computed(
  () => rep.data?.kpi || { month_sales: 0, open_deals: 0, total_deals: 0, sla_ontime_pct: 0 },
)
const deals = computed(() => rep.data?.deals || [])

const errorMessage = computed(
  () =>
    rep.error?.messages?.[0] || rep.error?.message || __('Không tải được hồ sơ NV'),
)
</script>
