<template>
  <main class="flex h-full flex-col" aria-labelledby="antmed-stock-receipt-title">
    <!-- Header + breadcrumb: Trang chủ › Kho › Nhập kho -->
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
        <span class="text-ink-gray-7" aria-current="page">{{ __('Nhập kho') }}</span>
      </nav>
      <div class="flex flex-col gap-1">
        <h1 id="antmed-stock-receipt-title" class="text-xl font-semibold text-ink-gray-9">
          {{ __('Nhập kho từ Nhà cung cấp') }}
        </h1>
        <p class="text-p-sm text-ink-gray-6">
          {{ __('Quét/nhập mã vật tư, nhập số lượng + đơn giá, rồi lập phiếu nhập kho.') }}
        </p>
      </div>
    </header>

    <section class="flex-1 overflow-auto px-6 py-5">
      <div class="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
        <!-- ── CỘT TRÁI: form + bảng vật tư ──────────────────────────────── -->
        <div class="flex flex-col gap-4">
          <div class="flex flex-col gap-1 rounded-lg border border-outline-gray-modals bg-surface-white p-4 sm:max-w-md">
            <label for="sr-warehouse" class="text-p-xs font-medium text-ink-gray-6">
              {{ __('Kho đến') }} <span class="text-red-600" aria-hidden="true">*</span>
            </label>
            <FormControl
              id="sr-warehouse"
              type="select"
              :options="warehouseOptions"
              :modelValue="toWarehouse"
              :disabled="!warehouseOptions.length"
              :aria-label="__('Chọn kho đến (kho Tổng)')"
              @update:modelValue="(v) => (toWarehouse = v)"
            />
            <p v-if="warehouses.error" class="text-p-xs text-red-600">
              {{ __('Không tải được danh sách kho.') }}
            </p>
          </div>

          <div class="overflow-x-auto rounded-lg border border-outline-gray-modals bg-surface-white">
            <table class="w-full border-separate border-spacing-0 text-left">
              <caption class="sr-only">{{ __('Bảng vật tư nhập kho') }}</caption>
              <thead>
                <tr class="text-p-xs text-ink-gray-6">
                  <th class="border-b border-outline-gray-1 px-3 py-2 font-medium">{{ __('SKU') }}</th>
                  <th class="border-b border-outline-gray-1 px-3 py-2 font-medium">{{ __('Tên VT') }}</th>
                  <th class="border-b border-outline-gray-1 px-3 py-2 font-medium">{{ __('Lot') }}</th>
                  <th class="border-b border-outline-gray-1 px-3 py-2 font-medium">{{ __('HSD') }}</th>
                  <th class="border-b border-outline-gray-1 px-3 py-2 text-right font-medium">{{ __('SL') }}</th>
                  <th class="border-b border-outline-gray-1 px-3 py-2 text-right font-medium">{{ __('Đơn giá') }}</th>
                  <th class="border-b border-outline-gray-1 px-3 py-2 text-right font-medium">{{ __('Giá trị') }}</th>
                  <th class="border-b border-outline-gray-1 px-3 py-2 font-medium"><span class="sr-only">{{ __('Xoá') }}</span></th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!rows.length">
                  <td colspan="8" class="px-3 py-8 text-center text-p-sm text-ink-gray-5">
                    {{ __('Chưa có vật tư. Quét QR hoặc nhập mã ở cột bên phải.') }}
                  </td>
                </tr>
                <tr v-for="(row, idx) in rows" :key="`${row.lot}-${idx}`" class="text-p-sm text-ink-gray-8">
                  <td class="border-b border-outline-gray-1 px-3 py-2.5 font-mono text-p-xs text-ink-gray-7">{{ row.item || '—' }}</td>
                  <td class="border-b border-outline-gray-1 px-3 py-2.5 font-medium text-ink-gray-9">{{ row.item_name || row.item || '—' }}</td>
                  <td class="border-b border-outline-gray-1 px-3 py-2.5 text-ink-gray-7">{{ row.lot_no || row.lot || '—' }}</td>
                  <td class="border-b border-outline-gray-1 px-3 py-2.5 tabular-nums text-ink-gray-7">
                    {{ formatExpiryMonthYear(row.expiry_date) || fmtDate(row.expiry_date) }}
                  </td>
                  <td class="border-b border-outline-gray-1 px-3 py-2.5 text-right">
                    <input
                      type="number" min="1" step="1" :value="row.qty"
                      class="w-16 rounded border border-outline-gray-2 px-2 py-1 text-right text-p-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
                      :aria-label="__('Số lượng nhập {0}', [row.item_name || row.item])"
                      @input="(e) => setQty(idx, e.target.value)"
                    />
                  </td>
                  <td class="border-b border-outline-gray-1 px-3 py-2.5 text-right">
                    <input
                      type="number" min="0" step="1000" :value="row.unit_price"
                      class="w-28 rounded border border-outline-gray-2 px-2 py-1 text-right text-p-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
                      :aria-label="__('Đơn giá {0}', [row.item_name || row.item])"
                      @input="(e) => setPrice(idx, e.target.value)"
                    />
                  </td>
                  <td class="border-b border-outline-gray-1 px-3 py-2.5 text-right tabular-nums text-ink-gray-8">{{ formatVnMoney(lineValue(row)) }}</td>
                  <td class="border-b border-outline-gray-1 px-3 py-2.5">
                    <button
                      type="button"
                      class="rounded p-1.5 text-ink-gray-5 hover:bg-surface-gray-2 hover:text-red-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
                      :aria-label="__('Xoá dòng {0}', [row.item_name || row.item])"
                      @click="removeRow(idx)"
                    >✕</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="flex items-center justify-end gap-3">
            <p v-if="rows.length" class="text-p-sm text-ink-gray-5">
              {{ __('Tổng giá trị') }}: <span class="font-medium text-ink-gray-8">{{ formatVnMoney(totalValue) }}</span>
            </p>
            <Button
              variant="solid"
              :label="__('✓ Nhập & in phiếu')"
              :loading="entry.loading"
              :disabled="!canSubmit"
              :aria-label="__('Nhập phiếu kho')"
              @click="submitReceipt"
            />
          </div>
        </div>

        <!-- ── CỘT PHẢI: quét QR + nhập tay ─────────────────────────────── -->
        <aside class="flex flex-col gap-4">
          <div class="flex flex-col gap-3 rounded-lg border border-outline-gray-modals bg-surface-white p-4">
            <QrScanner :active="true" @scan="onScan" />
            <div class="flex flex-col gap-1">
              <label for="sr-manual" class="text-p-xs font-medium text-ink-gray-6">{{ __('Nhập mã thủ công') }}</label>
              <form class="flex gap-2" @submit.prevent="onManualEnter">
                <FormControl
                  id="sr-manual" v-model="manualCode" type="text" class="flex-1"
                  :placeholder="__('Mã lô hoặc mã VTYT')"
                  :aria-label="__('Nhập mã lô hoặc mã vật tư')"
                />
                <Button variant="outline" type="submit" :label="__('Thêm')" :loading="scan.loading" :disabled="!manualCode.trim() || !toWarehouse" />
              </form>
              <p v-if="!toWarehouse" class="text-p-xs text-amber-700">{{ __('Chọn kho đến trước khi quét.') }}</p>
            </div>
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
import { scanLot, createStockEntry, listWarehouses } from '@/data/antmed'
import { fmtDate, formatExpiryMonthYear, formatVnMoney } from '@/utils/antmedUi'

const toWarehouse = ref('')
const manualCode = ref('')
const rows = ref([])

const warehouses = listWarehouses({ params: { warehouse_type: 'Tổng', page_length: 100 }, auto: true })
const warehouseOptions = computed(() =>
  (warehouses.data?.data || []).map((w) => ({ value: w.name, label: w.warehouse_name || w.name })),
)
warehouses.onSuccess = (data) => {
  const list = data?.data || []
  if (!toWarehouse.value && list.length) toWarehouse.value = list[0].name
}
warehouses.onError = (err) => toast.error(err?.messages?.[0] || __('Không tải được danh sách kho'))

const scan = scanLot()
const entry = createStockEntry()

function lineValue(row) {
  return (Number(row.qty) || 0) * (Number(row.unit_price) || 0)
}
const totalValue = computed(() => rows.value.reduce((s, r) => s + lineValue(r), 0))
const canSubmit = computed(() => !!toWarehouse.value && rows.value.length > 0)

function addScanned(data) {
  if (!data || !data.found) {
    if (data?.reason === 'no_perm') toast.error(__('Bạn không có quyền đọc lô này.'))
    else toast.error(__('Không tìm thấy mã.'))
    return
  }
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
    unit_price: data.unit_price || 0,
    qty: 1,
  })
}

function doScan(code) {
  if (!toWarehouse.value) {
    toast.error(__('Chọn kho đến trước khi quét.'))
    return
  }
  scan.submit(
    { code: code.trim(), warehouse: toWarehouse.value },
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
  rows.value[idx].qty = Math.max(1, Math.floor(Number(value) || 1))
}
function setPrice(idx, value) {
  rows.value[idx].unit_price = Math.max(0, Number(value) || 0)
}
function removeRow(idx) {
  rows.value.splice(idx, 1)
}

function submitReceipt() {
  if (!canSubmit.value) return
  entry.submit(
    {
      entry_type: 'Nhập NCC',
      to_warehouse: toWarehouse.value,
      items: rows.value.map((r) => ({
        item: r.item,
        lot: r.lot,
        qty: Number(r.qty) || 1,
        uom: r.uom,
        unit_price: Number(r.unit_price) || 0,
      })),
    },
    {
      onSuccess: (data) => {
        toast.success(__('Đã nhập phiếu {0}', [data?.name || '']))
        rows.value = []
      },
      onError: (err) => toast.error(err?.messages?.[0] || __('Không nhập được phiếu')),
    },
  )
}
</script>
