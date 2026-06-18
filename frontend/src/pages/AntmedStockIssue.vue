<template>
  <main class="flex h-full flex-col" aria-labelledby="antmed-stock-issue-title">
    <!-- Header + breadcrumb: Trang chủ › Kho › Xuất cho NV -->
    <header class="flex flex-col gap-2 border-b border-outline-gray-modals px-6 py-4">
      <nav class="text-p-xs text-ink-gray-5" :aria-label="__('Đường dẫn')">
        <RouterLink
          to="/antmed"
          class="rounded text-ink-gray-6 hover:text-ink-gray-8 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
        >
          {{ __('Trang chủ') }}
        </RouterLink>
        <span class="px-1.5 text-ink-gray-4" aria-hidden="true">›</span>
        <span class="text-ink-gray-6">{{ __('Kho') }}</span>
        <span class="px-1.5 text-ink-gray-4" aria-hidden="true">›</span>
        <span class="text-ink-gray-7" aria-current="page">{{ __('Xuất cho NV') }}</span>
      </nav>
      <div class="flex flex-col gap-1">
        <h1 id="antmed-stock-issue-title" class="text-xl font-semibold text-ink-gray-9">
          {{ __('Xuất vật tư cho Nhân viên') }}
        </h1>
        <p class="text-p-sm text-ink-gray-6">
          {{ __('Quét/nhập mã vật tư, kiểm CO/CQ + FIFO, rồi lập phiếu xuất kho.') }}
        </p>
      </div>
    </header>

    <section class="flex-1 overflow-auto px-6 py-5">
      <div class="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
        <!-- ── CỘT TRÁI: form phiếu + bảng vật tư đã quét ─────────────────── -->
        <div class="flex flex-col gap-4">
          <!-- Card thông tin phiếu -->
          <div class="flex flex-col gap-4 rounded-lg border border-outline-gray-modals bg-surface-white p-4 sm:flex-row">
            <div class="flex flex-1 flex-col gap-1">
              <label for="si-employee" class="text-p-xs font-medium text-ink-gray-6">
                {{ __('NV nhận') }} <span class="text-red-600" aria-hidden="true">*</span>
              </label>
              <FormControl
                id="si-employee"
                type="select"
                :options="employeeOptions"
                :modelValue="nvEmployee"
                :disabled="!employeeOptions.length"
                :aria-label="__('Chọn nhân viên nhận vật tư')"
                @update:modelValue="(v) => (nvEmployee = v)"
              />
              <p v-if="employees.error" class="text-p-xs text-red-600">
                {{ __('Không tải được danh sách NV.') }}
              </p>
            </div>

            <div class="flex flex-1 flex-col gap-1">
              <label for="si-purpose" class="text-p-xs font-medium text-ink-gray-6">
                {{ __('Mục đích') }}
              </label>
              <FormControl
                id="si-purpose"
                type="select"
                :options="purposeOptions"
                :modelValue="purpose"
                :aria-label="__('Mục đích xuất kho')"
                @update:modelValue="(v) => (purpose = v)"
              />
            </div>

            <div class="flex flex-1 flex-col gap-1">
              <label for="si-warehouse" class="text-p-xs font-medium text-ink-gray-6">
                {{ __('Kho nguồn') }} <span class="text-red-600" aria-hidden="true">*</span>
              </label>
              <FormControl
                id="si-warehouse"
                type="select"
                :options="warehouseOptions"
                :modelValue="fromWarehouse"
                :disabled="!warehouseOptions.length"
                :aria-label="__('Chọn kho nguồn (kho Tổng)')"
                @update:modelValue="(v) => (fromWarehouse = v)"
              />
              <p v-if="warehouses.error" class="text-p-xs text-red-600">
                {{ __('Không tải được danh sách kho.') }}
              </p>
            </div>
          </div>

          <!-- Alert đỏ: ≥1 dòng thiếu CO/CQ → không thể xuất -->
          <div
            v-for="r in blockedRows"
            :key="`blk-${r.lot || r.item}`"
            class="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-p-sm text-red-800"
            role="alert"
          >
            {{
              __('⚠ {0} thiếu CO/CQ — không thể xuất. Gọi Pháp lý đính file trước.', [
                r.item_name || r.item || r.lot,
              ])
            }}
          </div>

          <!-- Bảng "Vật tư đã quét" -->
          <div class="overflow-x-auto rounded-lg border border-outline-gray-modals bg-surface-white">
            <table class="w-full border-separate border-spacing-0 text-left">
              <caption class="sr-only">
                {{ __('Bảng vật tư đã quét chờ xuất') }}
              </caption>
              <thead>
                <tr class="text-p-xs text-ink-gray-6">
                  <th class="border-b border-outline-gray-1 px-3 py-2 font-medium">{{ __('SKU') }}</th>
                  <th class="border-b border-outline-gray-1 px-3 py-2 font-medium">{{ __('Tên VT') }}</th>
                  <th class="border-b border-outline-gray-1 px-3 py-2 font-medium">{{ __('Lot') }}</th>
                  <th class="border-b border-outline-gray-1 px-3 py-2 font-medium">{{ __('HSD') }}</th>
                  <th class="border-b border-outline-gray-1 px-3 py-2 text-right font-medium">{{ __('SL') }}</th>
                  <th class="border-b border-outline-gray-1 px-3 py-2 text-right font-medium">{{ __('Giá trị') }}</th>
                  <th class="border-b border-outline-gray-1 px-3 py-2 font-medium">{{ __('CO/CQ') }}</th>
                  <th class="border-b border-outline-gray-1 px-3 py-2 font-medium"><span class="sr-only">{{ __('Xoá') }}</span></th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!rows.length">
                  <td colspan="8" class="px-3 py-8 text-center text-p-sm text-ink-gray-5">
                    {{ __('Chưa có vật tư. Quét QR hoặc nhập mã ở cột bên phải.') }}
                  </td>
                </tr>
                <tr
                  v-for="(row, idx) in rows"
                  :key="`${row.lot}-${idx}`"
                  class="text-p-sm text-ink-gray-8"
                  :class="rowBlockedByCocq(row) ? 'bg-red-50' : ''"
                >
                  <td class="border-b border-outline-gray-1 px-3 py-2.5 font-mono text-p-xs text-ink-gray-7">
                    {{ row.item || '—' }}
                  </td>
                  <td class="border-b border-outline-gray-1 px-3 py-2.5 font-medium text-ink-gray-9">
                    {{ row.item_name || row.item || '—' }}
                  </td>
                  <td class="border-b border-outline-gray-1 px-3 py-2.5 text-ink-gray-7">
                    {{ row.lot_no || row.lot || '—' }}
                  </td>
                  <td class="border-b border-outline-gray-1 px-3 py-2.5 tabular-nums text-ink-gray-7">
                    {{ formatExpiryMonthYear(row.expiry_date) || fmtDate(row.expiry_date) }}
                  </td>
                  <td class="border-b border-outline-gray-1 px-3 py-2.5 text-right">
                    <input
                      type="number"
                      min="1"
                      step="1"
                      :value="row.qty"
                      class="w-16 rounded border border-outline-gray-2 px-2 py-1 text-right text-p-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
                      :aria-label="__('Số lượng xuất {0}', [row.item_name || row.item])"
                      @input="(e) => setQty(idx, e.target.value)"
                    />
                  </td>
                  <td class="border-b border-outline-gray-1 px-3 py-2.5 text-right tabular-nums text-ink-gray-8">
                    {{ formatVnMoney(lineValue(row)) }}
                  </td>
                  <td class="border-b border-outline-gray-1 px-3 py-2.5">
                    <div class="flex flex-col gap-1">
                      <span
                        class="inline-flex w-fit items-center rounded-full px-2 py-0.5 text-p-xs font-medium"
                        :class="cocqChipClass(row.cocq_ok)"
                      >
                        {{ cocqChipLabel(row.cocq_ok) }}
                      </span>
                      <span
                        v-if="row.is_fifo_priority === false"
                        class="inline-flex w-fit items-center rounded-full px-2 py-0.5 text-p-xs font-medium"
                        :class="pillClass('warn')"
                      >
                        {{ __('Không ưu tiên FIFO') }}
                      </span>
                      <span
                        v-if="row.recall_status === 'Theo dõi'"
                        class="inline-flex w-fit items-center rounded-full px-2 py-0.5 text-p-xs font-medium"
                        :class="pillClass('warn')"
                      >
                        {{ __('Theo dõi recall') }}
                      </span>
                      <span
                        v-if="row.days_to_expiry != null && row.days_to_expiry <= 30"
                        class="inline-flex w-fit items-center rounded-full px-2 py-0.5 text-p-xs font-medium"
                        :class="pillClass('warn')"
                      >
                        {{ __('Cận date {0}n', [row.days_to_expiry]) }}
                      </span>
                    </div>
                  </td>
                  <td class="border-b border-outline-gray-1 px-3 py-2.5">
                    <button
                      type="button"
                      class="rounded p-1.5 text-ink-gray-5 hover:bg-surface-gray-2 hover:text-red-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
                      :aria-label="__('Xoá dòng {0}', [row.item_name || row.item])"
                      @click="removeRow(idx)"
                    >
                      ✕
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Nút Xuất & in phiếu -->
          <div class="flex items-center justify-end gap-3">
            <p v-if="rows.length" class="text-p-sm text-ink-gray-5">
              {{ __('Tổng giá trị') }}: <span class="font-medium text-ink-gray-8">{{ formatVnMoney(totalValue) }}</span>
            </p>
            <Button
              variant="solid"
              :label="__('✓ Xuất & in phiếu')"
              :loading="entry.loading"
              :disabled="!canSubmit"
              :aria-label="__('Xuất phiếu và in')"
              @click="submitIssue"
            />
          </div>
        </div>

        <!-- ── CỘT PHẢI: quét QR + nhập tay + phiếu gần đây ──────────────── -->
        <aside class="flex flex-col gap-4">
          <div class="flex flex-col gap-3 rounded-lg border border-outline-gray-modals bg-surface-white p-4">
            <QrScanner :active="true" @scan="onScan" />

            <div class="flex flex-col gap-1">
              <label for="si-manual" class="text-p-xs font-medium text-ink-gray-6">
                {{ __('Nhập mã thủ công') }}
              </label>
              <form class="flex gap-2" @submit.prevent="onManualEnter">
                <FormControl
                  id="si-manual"
                  v-model="manualCode"
                  type="text"
                  class="flex-1"
                  :placeholder="__('Mã lô hoặc mã VTYT')"
                  :aria-label="__('Nhập mã lô hoặc mã vật tư')"
                />
                <Button
                  variant="outline"
                  type="submit"
                  :label="__('Thêm')"
                  :loading="scan.loading"
                  :disabled="!manualCode.trim() || !fromWarehouse"
                />
              </form>
              <p v-if="!fromWarehouse" class="text-p-xs text-amber-700">
                {{ __('Chọn kho nguồn trước khi quét.') }}
              </p>
            </div>
          </div>

          <!-- Phiếu xuất gần đây -->
          <div class="flex flex-col gap-2 rounded-lg border border-outline-gray-modals bg-surface-white p-4">
            <h2 class="text-p-sm font-semibold text-ink-gray-8">{{ __('Phiếu xuất gần đây') }}</h2>
            <div v-if="recent.loading" class="py-4 text-center text-p-xs text-ink-gray-5">
              {{ __('Đang tải…') }}
            </div>
            <div v-else-if="recent.error" class="py-4 text-center text-p-xs text-red-600">
              {{ __('Không tải được.') }}
            </div>
            <p v-else-if="!recentRows.length" class="py-4 text-center text-p-xs text-ink-gray-5">
              {{ __('Chưa có phiếu xuất.') }}
            </p>
            <ul v-else class="flex flex-col divide-y divide-outline-gray-1">
              <li v-for="p in recentRows" :key="p.name" class="flex items-center justify-between gap-2 py-2">
                <RouterLink
                  :to="{ name: 'AntmedStockEntryDetail', params: { name: p.name } }"
                  class="rounded text-p-sm text-teal-700 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
                  :aria-label="__('Xem chi tiết phiếu') + ' ' + p.name"
                >
                  {{ p.name }}
                </RouterLink>
                <span class="text-p-xs tabular-nums text-ink-gray-5">{{ formatStockTime(p.posting_datetime) }}</span>
              </li>
            </ul>
          </div>
        </aside>
      </div>
    </section>
  </main>
</template>

<script setup>
import { ref, computed } from 'vue'
import { RouterLink } from 'vue-router'
import { Button, FormControl, toast } from 'frappe-ui'
import QrScanner from '@/components/Antmed/QrScanner.vue'
import {
  scanLot,
  createStockEntry,
  listWarehouses,
  listAssignableEmployees,
  listStockEntries,
} from '@/data/antmed'
import {
  fmtDate,
  formatExpiryMonthYear,
  formatVnMoney,
  formatStockTime,
  pillClass,
  cocqChipClass,
  cocqChipLabel,
  rowBlockedByCocq,
  blockedCocqRows,
} from '@/utils/antmedUi'

// ── State form ───────────────────────────────────────────────────────────────
const nvEmployee = ref('')
// Mục đích = 2 option tĩnh (gửi BE qua `reason`). KEY == nhãn VI hiển thị.
const purpose = ref('Giao ca mổ')
const fromWarehouse = ref('')
const manualCode = ref('')
// rows = vật tư đã quét; mỗi dòng giữ nguyên cờ từ scan_lot (item, lot, cocq_ok, requires_cocq…).
const rows = ref([])

const purposeOptions = [
  { value: 'Giao ca mổ', label: __('Giao ca mổ') },
  { value: 'Bổ sung kho cá nhân', label: __('Bổ sung kho cá nhân') },
]

// ── Resources ─────────────────────────────────────────────────────────────────
// NV nhận (dropdown) — { data:[{value,label}] } → đọc r.data.data.
const employees = listAssignableEmployees({ auto: true })
const employeeOptions = computed(() => employees.data?.data || [])

// Kho nguồn = kho Tổng. List bọc { data, total_count } → r.data.data.
const warehouses = listWarehouses({ params: { warehouse_type: 'Tổng', page_length: 100 }, auto: true })
const warehouseOptions = computed(() =>
  (warehouses.data?.data || []).map((w) => ({ value: w.name, label: w.warehouse_name || w.name })),
)
// Mặc định chọn kho Tổng đầu tiên khi load.
warehouses.onSuccess = (data) => {
  const list = data?.data || []
  if (!fromWarehouse.value && list.length) fromWarehouse.value = list[0].name
}
warehouses.onError = (err) => toast.error(err?.messages?.[0] || __('Không tải được danh sách kho'))
employees.onError = (err) => toast.error(err?.messages?.[0] || __('Không tải được danh sách NV'))

// Quét/nhập mã → scan_lot (RAW dict THƯỜNG, đọc r.data.* trực tiếp).
const scan = scanLot()

// Phiếu xuất gần đây (dict bọc → r.data.data).
const recent = listStockEntries({ params: { entry_type: 'Xuất cho NV', start: 0, page_length: 8 }, auto: true })
const recentRows = computed(() => recent.data?.data || [])

// Mutation lập phiếu.
const entry = createStockEntry()

// ── Computed gate ────────────────────────────────────────────────────────────
const blockedRows = computed(() => blockedCocqRows(rows.value))
function lineValue(row) {
  const qty = Number(row.qty) || 0
  const price = Number(row.unit_price) || 0
  return qty * price
}
const totalValue = computed(() => rows.value.reduce((sum, r) => sum + lineValue(r), 0))
const canSubmit = computed(
  () => !!nvEmployee.value && !!fromWarehouse.value && rows.value.length > 0 && blockedRows.value.length === 0,
)

// ── Quét / thêm dòng ─────────────────────────────────────────────────────────
function addScanned(data) {
  // found=false → toast theo reason (not_found / no_perm).
  if (!data || !data.found) {
    if (data?.reason === 'no_perm') toast.error(__('Bạn không có quyền đọc lô này.'))
    else toast.error(__('Không tìm thấy mã.'))
    return
  }
  // An toàn recall: lô 'Đã thu hồi' → KHÔNG thêm (BE cũng chặn cứng khi submit).
  if (data.recall_status === 'Đã thu hồi') {
    toast.error(__('Lô {0} đã bị thu hồi — không thể xuất.', [data.lot_no || data.lot]))
    return
  }
  // An toàn HSD: lô đã hết hạn (days_to_expiry < 0) → KHÔNG thêm (BE cũng chặn cứng khi submit).
  if (data.days_to_expiry != null && data.days_to_expiry < 0) {
    toast.error(__('Lô {0} đã hết hạn — không thể xuất.', [data.lot_no || data.lot]))
    return
  }
  // Lot trùng → tăng SL thay vì thêm dòng mới.
  const existing = rows.value.find((r) => r.lot === data.lot)
  if (existing) {
    existing.qty = (Number(existing.qty) || 0) + 1
    return
  }
  rows.value.push({
    item: data.item,
    item_name: data.item_name,
    lot: data.lot,
    lot_no: data.lot_no,
    expiry_date: data.expiry_date,
    uom: data.uom,
    unit_price: data.unit_price,
    requires_cocq: data.requires_cocq,
    cocq_ok: data.cocq_ok,
    is_fifo_priority: data.is_fifo_priority,
    recall_status: data.recall_status,
    days_to_expiry: data.days_to_expiry,
    qty: 1,
  })
}

function doScan(code) {
  if (!fromWarehouse.value) {
    toast.error(__('Chọn kho nguồn trước khi quét.'))
    return
  }
  scan.submit(
    { code: code.trim(), warehouse: fromWarehouse.value },
    {
      onSuccess: (data) => addScanned(data),
      onError: (err) => toast.error(err?.messages?.[0] || __('Không quét được mã')),
    },
  )
}

function onScan(decodedText) {
  doScan(decodedText)
}
function onManualEnter() {
  const code = manualCode.value.trim()
  if (!code) return
  doScan(code)
  manualCode.value = ''
}

function setQty(idx, value) {
  const n = Math.max(1, Math.floor(Number(value) || 1))
  rows.value[idx].qty = n
}
function removeRow(idx) {
  rows.value.splice(idx, 1)
}

// ── Submit ───────────────────────────────────────────────────────────────────
function submitIssue() {
  if (!canSubmit.value) return
  entry.submit(
    {
      entry_type: 'Xuất cho NV',
      from_warehouse: fromWarehouse.value,
      nv_employee: nvEmployee.value,
      reason: purpose.value,
      items: rows.value.map((r) => ({
        item: r.item,
        lot: r.lot,
        qty: Number(r.qty) || 1,
        uom: r.uom,
        unit_price: r.unit_price,
      })),
    },
    {
      onSuccess: (data) => {
        toast.success(__('Đã xuất phiếu {0}', [data?.name || '']))
        rows.value = []
        recent.reload()
      },
      onError: (err) => toast.error(err?.messages?.[0] || __('Không xuất được phiếu')),
    },
  )
}
</script>
