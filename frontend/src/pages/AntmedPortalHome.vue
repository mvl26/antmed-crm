<template>
  <main class="flex h-full flex-col" aria-labelledby="antmed-portal-title">
    <!-- Header + breadcrumb -->
    <header class="flex flex-col gap-2 border-b border-outline-gray-modals px-6 py-4">
      <nav class="text-p-xs text-ink-gray-5" :aria-label="__('Đường dẫn')">
        <span class="text-ink-gray-7">{{ __('Portal Bệnh viện') }}</span>
        <span class="px-1.5 text-ink-gray-4" aria-hidden="true">›</span>
        <span class="text-ink-gray-7">{{ __('Trang chủ') }}</span>
      </nav>
      <div class="flex flex-col gap-1">
        <h1 id="antmed-portal-title" class="text-xl font-semibold text-ink-gray-9">
          {{ __('Trang chủ Portal') }}
          <span v-if="hospitalName" class="text-ink-gray-6">· {{ hospitalName }}</span>
        </h1>
        <p class="text-p-sm text-ink-gray-6">
          {{ __('Gọi vật tư, mượn bộ dụng cụ và tra cứu chứng từ cho bệnh viện của bạn') }}
        </p>
      </div>
    </header>

    <section class="flex-1 overflow-auto px-6 py-5">
      <!-- ── Header: 3 quick-action card TĨNH (mockup G1 .cardrow.cols-3) ─────── -->
      <div class="mb-5 grid grid-cols-1 gap-4 sm:grid-cols-3" :aria-label="__('Thao tác nhanh')">
        <RouterLink
          v-for="qa in quickActions"
          :key="qa.key"
          :to="qa.to"
          class="flex flex-col items-center gap-1.5 rounded-xl border p-5 text-center transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
          :class="
            qa.primary
              ? 'border-teal-600 bg-teal-50 hover:bg-teal-100'
              : 'border-outline-gray-1 bg-surface-white hover:bg-surface-gray-1'
          "
        >
          <span class="text-3xl" aria-hidden="true">{{ qa.icon }}</span>
          <span
            class="text-p-base font-semibold"
            :class="qa.primary ? 'text-teal-900' : 'text-ink-gray-9'"
          >
            {{ __(qa.title) }}
          </span>
          <span class="text-p-xs text-ink-gray-5">{{ __(qa.sub) }}</span>
        </RouterLink>
      </div>

      <!-- ── Card "📰 Thông báo gần đây" (mockup G1 .tl/.e timeline) ──────────── -->
      <article
        class="flex flex-col gap-3 rounded-xl border border-outline-gray-1 bg-surface-white p-4"
      >
        <h2 class="text-p-base font-semibold text-ink-gray-9">
          {{ __('📰 Thông báo gần đây') }}
        </h2>

        <!-- Chưa chọn bệnh viện (giả định tạm: hospital qua query param tới khi có mapping user→BV) -->
        <div
          v-if="!hospital"
          class="rounded-lg border border-dashed border-outline-gray-2 px-3 py-6 text-center"
          role="note"
        >
          <p class="text-p-sm text-ink-gray-6">
            {{ __('Chưa xác định bệnh viện. Mở Portal kèm mã bệnh viện để xem thông báo.') }}
          </p>
        </div>

        <template v-else>
          <!-- Tri-branch: loading → error → data/empty -->
          <div
            v-if="notif.loading"
            class="flex items-center gap-2 py-4 text-ink-gray-5"
            aria-live="polite"
          >
            <LoadingIndicator class="h-4 w-4" />
            <span class="text-p-base">{{ __('Đang tải…') }}</span>
          </div>

          <div v-else-if="notif.error" class="flex flex-col items-start gap-2 py-3" role="alert">
            <Badge variant="subtle" theme="red" size="lg" :label="__('Lỗi tải thông báo')" />
            <Button variant="subtle" :label="__('Thử lại')" @click="notif.reload()" />
          </div>

          <template v-else>
            <!-- Timeline .tl > .e (mockup G1) — render v-for từ data THẬT, BE đã sort ts giảm dần -->
            <div v-if="events.length" class="antmed-tl flex flex-col" :aria-label="__('Dòng thời gian thông báo')">
              <div
                v-for="(ev, i) in events"
                :key="(ev.ref || ev.kind) + '-' + i"
                class="antmed-e flex flex-wrap items-baseline gap-x-1.5 py-1 text-p-sm"
              >
                <b class="text-teal-900">{{ formatNotifTime(ev.ts) }}</b>
                <span class="text-ink-gray-7">{{ ev.title }}</span>
              </div>
            </div>

            <!-- Empty actionable: chưa có sự kiện THẬT -->
            <div
              v-else
              class="rounded-lg border border-dashed border-outline-gray-2 px-3 py-6 text-center"
              role="note"
            >
              <p class="text-p-sm text-ink-gray-6">{{ __('Chưa có thông báo') }}</p>
            </div>
          </template>
        </template>
      </article>

      <!-- ── Card "📋 Danh mục vật tư trúng thầu" (mockup G1 "Form gọi vật tư" .pill) ─── -->
      <article
        class="mt-5 flex flex-col gap-3 rounded-xl border border-outline-gray-1 bg-surface-white p-4"
      >
        <h2 class="text-p-base font-semibold text-ink-gray-9">
          {{ __('📋 Danh mục vật tư trúng thầu') }}
          <span v-if="catalogHospitalName" class="text-ink-gray-6">· {{ catalogHospitalName }}</span>
        </h2>

        <!-- Chưa chọn bệnh viện (cùng giả định card thông báo: hospital qua query param). -->
        <div
          v-if="!hospital"
          class="rounded-lg border border-dashed border-outline-gray-2 px-3 py-6 text-center"
          role="note"
        >
          <p class="text-p-sm text-ink-gray-6">
            {{ __('Chưa xác định bệnh viện. Mở Portal kèm mã bệnh viện để xem danh mục.') }}
          </p>
        </div>

        <template v-else>
          <!-- Tri-branch: loading → error → data/empty -->
          <div
            v-if="catalog.loading"
            class="flex items-center gap-2 py-4 text-ink-gray-5"
            aria-live="polite"
          >
            <LoadingIndicator class="h-4 w-4" />
            <span class="text-p-base">{{ __('Đang tải danh mục…') }}</span>
          </div>

          <div v-else-if="catalog.error" class="flex flex-col items-start gap-2 py-3" role="alert">
            <Badge variant="subtle" theme="red" size="lg" :label="__('Lỗi tải danh mục')" />
            <Button variant="subtle" :label="__('Thử lại')" @click="catalog.reload()" />
          </div>

          <template v-else>
            <!-- Bảng danh mục SKU trúng thầu (mockup G1): SKU · tên · ĐVT · còn/tổng + chip quota. -->
            <div v-if="catalogItems.length" class="overflow-x-auto">
              <table class="w-full text-p-sm" :aria-label="__('Danh mục vật tư trúng thầu')">
                <thead>
                  <tr class="border-b border-outline-gray-1 text-left text-ink-gray-5">
                    <th scope="col" class="py-2 pr-3 font-medium">{{ __('Mã VT') }}</th>
                    <th scope="col" class="py-2 pr-3 font-medium">{{ __('Tên vật tư') }}</th>
                    <th scope="col" class="py-2 pr-3 font-medium">{{ __('ĐVT') }}</th>
                    <th scope="col" class="py-2 pr-3 text-right font-medium">
                      {{ __('Còn / Tổng quota') }}
                    </th>
                    <th scope="col" class="py-2 font-medium">{{ __('Trạng thái quota') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="(it, i) in catalogItems"
                    :key="(it.item || it.item_name || 'vt') + '-' + i"
                    class="border-b border-outline-gray-1 last:border-0"
                  >
                    <td class="py-2 pr-3 text-ink-gray-6">{{ it.item || '—' }}</td>
                    <td class="py-2 pr-3 font-medium text-ink-gray-8">{{ it.item_name || '—' }}</td>
                    <td class="py-2 pr-3 text-ink-gray-6">{{ it.uom || '—' }}</td>
                    <td class="py-2 pr-3 text-right tabular-nums text-ink-gray-7">
                      {{ fmtQty(it.remaining_qty) }} / {{ fmtQty(it.quota_qty) }}
                    </td>
                    <td class="py-2">
                      <span
                        class="inline-flex items-center rounded-full px-2 py-0.5 text-p-xs font-medium"
                        :class="tenderQuotaChipClass(it.quota_chip)"
                      >
                        {{ tenderQuotaChipLabel(it.quota_chip, it.remaining_pct) }}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Empty actionable: BV chưa có HĐ trúng thầu hiệu lực. -->
            <div
              v-else
              class="rounded-lg border border-dashed border-outline-gray-2 px-3 py-6 text-center"
              role="note"
            >
              <p class="text-p-sm text-ink-gray-6">
                {{ __('BV chưa có hợp đồng trúng thầu hiệu lực') }}
              </p>
            </div>
          </template>
        </template>
      </article>
    </section>
  </main>
</template>

<script setup>
import { computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { RouterLink } from 'vue-router'
import { Badge, Button, toast } from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import { getPortalNotifications, getTenderCatalog } from '@/data/antmed'
import {
  formatNotifTime,
  fmtQty,
  tenderQuotaChipClass,
  tenderQuotaChipLabel,
  PORTAL_QUICK_ACTIONS,
} from '@/utils/antmedUi'

// M07-1 — Portal Bệnh viện · Trang chủ (mockup G1, id=bv). Header 3 quick-action card TĨNH
// (nav-only vòng này) + card "📰 Thông báo gần đây" wire customer.portal_notifications (rollup THẬT:
// Stock Entry 'Xuất cho NV' + quota-alert của BV). FE KHÔNG sort/aggregate — BE đã gộp; chỉ format
// ts (formatNotifTime) + render timeline.
//
// ⚠️ ASSUMPTION (ghi rõ để BA chốt): chưa có mapping session-user → AntMed Hospital. Vòng này lấy
// hospital TẠM qua query param `?hospital=<mã BV>` (control THẬT: param phát đi == query người dùng).
// Khi BA chốt mapping (vd User Permission AntMed Hospital / field trên User), thay nguồn ở computed
// `hospital` — KHÔNG đổi binding resource/template.
const route = useRoute()
const hospital = computed(() => route.query.hospital || '')

// 3 quick-action card TĨNH header (SSoT nhãn VI ở utils — render v-for, KHÔNG hardcode rời rạc).
const quickActions = PORTAL_QUICK_ACTIONS

const notif = getPortalNotifications({
  params: { hospital: hospital.value },
  auto: !!hospital.value,
  onError(err) {
    toast.error(err.messages?.[0] || __('Không tải được thông báo'))
  },
})

// M07-2 — card "📋 Danh mục vật tư trúng thầu" (mockup G1) wire customer.tender_catalog: bảng SKU
// thuộc HĐ active của BV + chip quota phân tầng THẬT (BE đọc quota_chip; FE KHÔNG tính lại ngưỡng).
const catalog = getTenderCatalog({
  params: { hospital: hospital.value },
  auto: !!hospital.value,
  onError(err) {
    toast.error(err.messages?.[0] || __('Không tải được danh mục vật tư trúng thầu'))
  },
})

// Đổi BV (query param) → cập nhật param + fetch lại CẢ 2 widget SONG SONG (param phát đi == lựa
// chọn UI — chống dead-control).
watch(hospital, (h) => {
  if (h) {
    notif.fetch({ hospital: h })
    catalog.fetch({ hospital: h })
  }
})

// Dict THƯỜNG { data:[...], hospital, hospital_name } → đọc r.data.data + r.data.hospital_name TRỰC TIẾP.
// FE KHÔNG sort/reduce (BE đã merge + sort ts desc + cắt LIMIT).
const events = computed(() => notif.data?.data || [])
const hospitalName = computed(() => notif.data?.hospital_name || '')

// M07-2 — Dict THƯỜNG { hospital, hospital_name, contract, items:[...] } → đọc r.data.items +
// r.data.hospital_name TRỰC TIẾP (KHÔNG .data.data). FE KHÔNG aggregate (BE đã gộp HĐ active).
const catalogItems = computed(() => catalog.data?.items || [])
const catalogHospitalName = computed(() => catalog.data?.hospital_name || '')
</script>

<style scoped>
/* Timeline mockup G1 (.tl/.e): trục dọc + chấm tròn brand bên trái mỗi sự kiện (token màu). */
.antmed-tl {
  position: relative;
  padding-left: 18px;
}
.antmed-tl::before {
  content: '';
  position: absolute;
  left: 5px;
  top: 0;
  bottom: 0;
  width: 2px;
  background: var(--surface-gray-3, #e5e7eb);
}
.antmed-e {
  position: relative;
}
.antmed-e::before {
  content: '';
  position: absolute;
  left: -17px;
  top: 10px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--teal-600, #0d9488);
  border: 2px solid var(--surface-white, #fff);
}
</style>
