<template>
  <main
    class="flex h-full flex-col"
    aria-labelledby="antmed-stock-entry-detail-title"
  >
    <!-- Header + breadcrumb: Trang chủ › Tồn kho › Phiếu xuất › <name> -->
    <header
      class="flex flex-col gap-2 border-b border-outline-gray-modals px-6 py-4"
    >
      <nav class="text-p-xs text-ink-gray-5" :aria-label="__('Đường dẫn')">
        <RouterLink
          to="/antmed"
          class="rounded text-ink-gray-6 hover:text-ink-gray-8 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
        >
          {{ __('Trang chủ') }}
        </RouterLink>
        <span class="px-1.5 text-ink-gray-4" aria-hidden="true">›</span>
        <span class="text-ink-gray-6">{{ __('Tồn kho') }}</span>
        <span class="px-1.5 text-ink-gray-4" aria-hidden="true">›</span>
        <RouterLink
          to="/antmed/warehouse/stock-entries"
          class="rounded text-ink-gray-6 hover:text-ink-gray-8 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
        >
          {{ __('Phiếu xuất') }}
        </RouterLink>
        <span class="px-1.5 text-ink-gray-4" aria-hidden="true">›</span>
        <span class="text-ink-gray-7" aria-current="page">{{ routeName }}</span>
      </nav>
      <div class="flex flex-col gap-1">
        <h1
          id="antmed-stock-entry-detail-title"
          class="text-xl font-semibold text-ink-gray-9"
        >
          {{ __('Phiếu') }} {{ routeName }}
        </h1>
        <p class="text-p-sm text-ink-gray-6">
          {{ __('Chi tiết phiếu xuất kho và danh sách vật tư đã chuẩn bị.') }}
        </p>
      </div>
    </header>

    <section class="flex-1 overflow-auto px-6 py-5" aria-live="polite">
      <div class="mx-auto flex max-w-5xl flex-col gap-4">
        <!-- Tri-branch: loading / not-found / error / data -->

        <!-- Loading -->
        <div
          v-if="entry.loading"
          class="flex items-center justify-center gap-2 py-16 text-ink-gray-6"
        >
          <LoadingIndicator class="h-4 w-4" />
          <span class="text-p-base">{{ __('Đang tải phiếu…') }}</span>
        </div>

        <!-- Not-found: phiếu không tồn tại (BE raise DoesNotExistError) HOẶC fail-closed (không quyền) -->
        <div
          v-else-if="isNotFound"
          class="flex flex-col items-center gap-3 py-16 text-center"
          role="alert"
        >
          <Badge
            variant="subtle"
            theme="gray"
            size="lg"
            :label="__('Không tìm thấy')"
          />
          <p class="max-w-md text-p-sm text-ink-gray-6">
            {{ __('Không tìm thấy phiếu') }}
            <span class="font-medium text-ink-gray-8">{{ routeName }}</span
            >.
          </p>
          <Button
            variant="outline"
            :label="__('Về danh sách phiếu')"
            @click="goBackToList"
          />
        </div>

        <!-- Error khác: banner + nút Thử lại reload -->
        <div
          v-else-if="entry.error"
          class="flex flex-col items-center gap-3 py-16 text-center"
          role="alert"
        >
          <Badge
            variant="subtle"
            theme="red"
            size="lg"
            :label="__('Không tải được')"
          />
          <p class="max-w-md text-p-sm text-ink-gray-6">
            {{ __('Lỗi tải phiếu') }}
          </p>
          <Button
            variant="outline"
            :label="__('Thử lại')"
            @click="entry.reload()"
          />
        </div>

        <!-- Data: header card + card "Vật tư đã chuẩn bị" -->
        <template v-else-if="data">
          <!-- Card HEADER: loại / BV / NV / ngày dự kiến dùng / kho / tổng giá trị -->
          <div
            class="rounded-lg border border-outline-gray-modals bg-surface-white p-4"
          >
            <div class="mb-3 flex items-center justify-between gap-3">
              <h2 class="text-base font-semibold text-ink-gray-9">
                {{ __('Thông tin phiếu') }}
              </h2>
              <!-- Chip loại phiếu: KÈM CHỮ (entry_type VI) — không chỉ màu (WCAG AA) -->
              <Badge
                v-if="data.entry_type"
                variant="subtle"
                size="sm"
                :theme="entryTypeChipTheme(data.entry_type)"
                :label="data.entry_type"
              />
            </div>

            <dl class="grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2">
              <!-- Bệnh viện (hospital_name — tên, KHÔNG mã) -->
              <div class="flex flex-col gap-0.5">
                <dt class="text-p-xs text-ink-gray-5">{{ __('Bệnh viện') }}</dt>
                <dd class="text-p-base font-medium text-ink-gray-9">
                  {{ data.hospital_name || '—' }}
                </dd>
              </div>
              <!-- NV kinh doanh (nv_employee_name — tên, KHÔNG email/ID) -->
              <div class="flex flex-col gap-0.5">
                <dt class="text-p-xs text-ink-gray-5">
                  {{ __('NV kinh doanh') }}
                </dt>
                <dd class="text-p-base text-ink-gray-8">
                  {{ data.nv_employee_name || '—' }}
                </dd>
              </div>
              <!-- Ngày dự kiến dùng (expected_use_date dd/MM/yyyy) -->
              <div class="flex flex-col gap-0.5">
                <dt class="text-p-xs text-ink-gray-5">
                  {{ __('Ngày dự kiến dùng') }}
                </dt>
                <dd class="text-p-base tabular-nums text-ink-gray-8">
                  {{ fmtDate(data.expected_use_date) }}
                </dd>
              </div>
              <!-- Thời điểm lập phiếu (posting_datetime) -->
              <div class="flex flex-col gap-0.5">
                <dt class="text-p-xs text-ink-gray-5">{{ __('Lập lúc') }}</dt>
                <dd class="text-p-base tabular-nums text-ink-gray-8">
                  {{ formatStockTime(data.posting_datetime) }}
                </dd>
              </div>
              <!-- Kho xuất (from_warehouse) -->
              <div class="flex flex-col gap-0.5">
                <dt class="text-p-xs text-ink-gray-5">{{ __('Kho xuất') }}</dt>
                <dd class="text-p-base text-ink-gray-8">
                  {{ data.from_warehouse || '—' }}
                </dd>
              </div>
              <!-- Kho nhận (to_warehouse) -->
              <div class="flex flex-col gap-0.5">
                <dt class="text-p-xs text-ink-gray-5">{{ __('Kho nhận') }}</dt>
                <dd class="text-p-base text-ink-gray-8">
                  {{ data.to_warehouse || '—' }}
                </dd>
              </div>
              <!-- Tổng giá trị (total_value, format VI) -->
              <div class="flex flex-col gap-0.5 sm:col-span-2">
                <dt class="text-p-xs text-ink-gray-5">
                  {{ __('Tổng giá trị') }}
                </dt>
                <dd
                  class="text-p-base font-semibold tabular-nums text-ink-gray-9"
                >
                  {{ formatVnMoney(data.total_value) }}
                </dd>
              </div>
            </dl>
          </div>

          <!-- Card "Vật tư đã chuẩn bị — <hospital_name>" (mockup C2): bảng SKU/Tên/Lot/HSD/SL/ĐVT/CO-CQ -->
          <div
            class="rounded-lg border border-outline-gray-modals bg-surface-white p-4"
          >
            <h2 class="mb-3 text-base font-semibold text-ink-gray-9">
              {{ __('Vật tư đã chuẩn bị') }}
              <span v-if="data.hospital_name" class="text-ink-gray-6">
                — {{ data.hospital_name }}
              </span>
            </h2>

            <!-- Empty: phiếu không có dòng vật tư -->
            <div
              v-if="!items.length"
              class="flex flex-col items-center gap-2 rounded-lg border border-dashed border-outline-gray-2 py-12 text-center text-ink-gray-6"
            >
              <p class="text-p-sm">{{ __('Phiếu chưa có vật tư') }}</p>
            </div>

            <!-- Data table mockup C2: SKU / Tên / Lot / HSD / SL / ĐVT / CO-CQ -->
            <table
              v-else
              class="w-full border-separate border-spacing-0 text-left"
            >
              <caption class="sr-only">
                {{
                  __('Bảng vật tư đã chuẩn bị')
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
                    {{ __('Tên') }}
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
                    {{ __('SL') }}
                  </th>
                  <th
                    class="border-b border-outline-gray-modals py-2 pr-4 font-medium"
                  >
                    {{ __('ĐVT') }}
                  </th>
                  <th
                    class="border-b border-outline-gray-modals py-2 font-medium"
                  >
                    {{ __('CO-CQ') }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(row, idx) in items"
                  :key="idx"
                  class="text-p-base text-ink-gray-8"
                >
                  <!-- SKU (item = mã) — phụ trợ, tên là chính ở cột Tên -->
                  <td
                    class="border-b border-outline-gray-1 py-3 pr-4 tabular-nums text-ink-gray-7"
                  >
                    {{ row.item || '—' }}
                  </td>
                  <!-- Tên (item_name — tên VTYT, KHÔNG mã thô) -->
                  <td
                    class="border-b border-outline-gray-1 py-3 pr-4 font-medium text-ink-gray-9"
                  >
                    {{ row.item_name || '—' }}
                  </td>
                  <!-- Lot (lot_no) -->
                  <td
                    class="border-b border-outline-gray-1 py-3 pr-4 tabular-nums text-ink-gray-7"
                  >
                    {{ row.lot_no || '—' }}
                  </td>
                  <!-- HSD (expiry_date dd/MM/yyyy) -->
                  <td
                    class="border-b border-outline-gray-1 py-3 pr-4 tabular-nums text-ink-gray-7"
                  >
                    {{ fmtDate(row.expiry_date) }}
                  </td>
                  <!-- SL (qty) -->
                  <td
                    class="border-b border-outline-gray-1 py-3 pr-4 text-right tabular-nums text-ink-gray-8"
                  >
                    {{ fmtQty(row.qty) }}
                  </td>
                  <!-- ĐVT (uom) -->
                  <td
                    class="border-b border-outline-gray-1 py-3 pr-4 text-ink-gray-7"
                  >
                    {{ row.uom || '—' }}
                  </td>
                  <!-- CO-CQ chip: KÈM CHỮ (cocqChipLabel) — không chỉ màu (WCAG AA) -->
                  <td class="border-b border-outline-gray-1 py-3">
                    <span
                      :class="[
                        'inline-flex items-center rounded-full px-2.5 py-0.5 text-p-xs font-medium',
                        cocqChipClass(row.cocq_ok),
                      ]"
                      :aria-label="
                        __('Chứng từ CO/CQ') + ': ' + cocqChipLabel(row.cocq_ok)
                      "
                    >
                      {{ cocqChipLabel(row.cocq_ok) }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>

            <!-- Tổng số dòng -->
            <p v-if="items.length" class="pt-3 text-p-sm text-ink-gray-5">
              {{ __('Tổng cộng') }}: {{ items.length }} {{ __('vật tư') }}
            </p>
          </div>
        </template>
      </div>
    </section>
  </main>
</template>

<script setup>
import { computed, onMounted, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { Badge, Button, toast } from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import { getStockEntry } from '@/data/antmed'
import {
  fmtDate,
  fmtQty,
  formatVnMoney,
  formatStockTime,
  entryTypeChipTheme,
  cocqChipClass,
  cocqChipLabel,
} from '@/utils/antmedUi'

const route = useRoute()
const router = useRouter()

// Tên phiếu lấy từ route param (drill-down từ list "Phiếu xuất gần đây").
const routeName = computed(() => route.params.name || '')

// auto:false — fetch khi mở route. Endpoint trả dict THƯỜNG → đọc r.data TRỰC TIẾP (KHÔNG .data.data).
const entry = getStockEntry({ auto: false })

const data = computed(() => entry.data || null)
// items đọc thẳng r.data.items (dict THƯỜNG); BE đã chuẩn bị đủ (KHÔNG sort/aggregate ở FE).
const items = computed(() => entry.data?.items || [])

// Not-found: BE raise DoesNotExistError (exc_type 404) HOẶC fail-closed (shape rỗng: có name nhưng
// KHÔNG có dòng + KHÔNG header thật) → coi như "Không tìm thấy phiếu" (không rò header user thiếu quyền).
const isNotFound = computed(() => {
  const err = entry.error
  if (err) {
    const exc = err.exc_type || err.exception || ''
    const msg = err.messages?.[0] || err.message || ''
    return (
      /DoesNotExist/i.test(exc) ||
      /not found|does not exist|không tìm thấy/i.test(msg)
    )
  }
  // Fail-closed shape rỗng: BE trả name nhưng entry_type rỗng + 0 dòng → không có gì để xem.
  const d = entry.data
  if (d && !d.entry_type && !(d.items && d.items.length)) return true
  return false
})

// Fetch theo route.params.name (param phát đi == route — chống dead-control). Đổi route → fetch lại.
function loadEntry() {
  const name = routeName.value
  if (!name) return
  entry.submit({ name })
}

onMounted(loadEntry)
watch(() => route.params.name, loadEntry)

function goBackToList() {
  router.push({ name: 'AntmedStockEntries' })
}

// Lỗi quyền (PermissionError) / lỗi khác → toast (ngoài banner). Not-found đã có nhánh riêng (KHÔNG toast).
entry.onError = (err) => {
  const exc = err?.exc_type || err?.exception || ''
  if (/DoesNotExist/i.test(exc)) return
  toast.error(err?.messages?.[0] || __('Lỗi tải phiếu'))
}
</script>
