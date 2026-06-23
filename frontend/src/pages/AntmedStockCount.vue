<template>
  <main class="flex h-full flex-col" aria-labelledby="antmed-stock-count-title">
    <!-- Header + breadcrumb: Trang chủ › Kho › Kiểm kê -->
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
          <span class="text-ink-gray-6">{{ __('Kho') }}</span>
          <span class="px-1.5 text-ink-gray-4" aria-hidden="true">›</span>
          <span class="text-ink-gray-7" aria-current="page">{{
            __('Kiểm kê')
          }}</span>
        </nav>
        <div class="flex flex-col gap-1">
          <h1
            id="antmed-stock-count-title"
            class="text-xl font-semibold text-ink-gray-9"
          >
            {{ __('Kiểm kê kho') }}
          </h1>
          <p class="text-p-sm text-ink-gray-6">
            {{
              __(
                'Đối chiếu tồn hệ thống với số thực đếm; chốt để điều chỉnh sổ tồn.',
              )
            }}
          </p>
        </div>
      </div>

      <!-- Dropdown chọn Kho (param phát đi == lựa chọn UI — chống dead-control) -->
      <div class="flex flex-col gap-1 sm:w-72">
        <label
          for="sc-warehouse"
          class="text-p-xs font-medium text-ink-gray-6"
          >{{ __('Kho') }}</label
        >
        <FormControl
          id="sc-warehouse"
          type="select"
          :options="warehouseOptions"
          :modelValue="activeWarehouse"
          :disabled="!warehouseOptions.length"
          :aria-label="__('Chọn kho cần kiểm kê')"
          @update:modelValue="setWarehouse"
        />
      </div>
    </header>

    <section class="flex-1 overflow-auto px-6 py-5">
      <div class="flex flex-col gap-5">
        <!-- ── Bảng kiểm kê ──────────────────────────────────────────────── -->
        <div class="flex flex-col gap-3">
          <!-- Tri-branch snapshot: chưa chọn / loading / error / empty / data -->
          <div
            v-if="!activeWarehouse"
            class="flex flex-col items-center gap-2 rounded-lg border border-dashed border-outline-gray-2 py-16 text-center text-ink-gray-6"
          >
            <p class="text-p-base">{{ __('Chọn kho để bắt đầu kiểm kê') }}</p>
            <p class="text-p-sm">
              {{ __('Chọn một kho ở trên để tải tồn hệ thống.') }}
            </p>
          </div>

          <div
            v-else-if="snapshot.loading"
            class="flex items-center justify-center gap-2 py-16 text-ink-gray-6"
          >
            <LoadingIndicator class="h-4 w-4" />
            <span class="text-p-base">{{ __('Đang tải tồn kho…') }}</span>
          </div>

          <div
            v-else-if="snapshot.error"
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
              {{ snapshotError }}
            </p>
            <Button
              variant="outline"
              :label="__('Thử lại')"
              @click="snapshot.reload()"
            />
          </div>

          <div
            v-else-if="!rows.length"
            class="flex flex-col items-center gap-2 py-16 text-center text-ink-gray-6"
          >
            <p class="text-p-base">{{ __('Kho trống') }}</p>
            <p class="text-p-sm">
              {{ __('Kho này không có vật tư còn tồn để kiểm kê.') }}
            </p>
          </div>

          <template v-else>
            <div
              class="overflow-x-auto rounded-lg border border-outline-gray-modals bg-surface-white"
            >
              <table class="w-full border-separate border-spacing-0 text-left">
                <caption class="sr-only">
                  {{
                    __('Bảng kiểm kê tồn kho')
                  }}
                </caption>
                <thead>
                  <tr class="text-p-xs text-ink-gray-6">
                    <th
                      class="border-b border-outline-gray-1 px-3 py-2 font-medium"
                    >
                      {{ __('SKU') }}
                    </th>
                    <th
                      class="border-b border-outline-gray-1 px-3 py-2 font-medium"
                    >
                      {{ __('Tên VT') }}
                    </th>
                    <th
                      class="border-b border-outline-gray-1 px-3 py-2 font-medium"
                    >
                      {{ __('Lot') }}
                    </th>
                    <th
                      class="border-b border-outline-gray-1 px-3 py-2 font-medium"
                    >
                      {{ __('HSD') }}
                    </th>
                    <th
                      class="border-b border-outline-gray-1 px-3 py-2 text-right font-medium"
                    >
                      {{ __('SL hệ thống') }}
                    </th>
                    <th
                      class="border-b border-outline-gray-1 px-3 py-2 text-right font-medium"
                    >
                      {{ __('SL thực đếm') }}
                    </th>
                    <th
                      class="border-b border-outline-gray-1 px-3 py-2 text-right font-medium"
                    >
                      {{ __('Chênh lệch') }}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="(row, idx) in rows"
                    :key="`${row.item}-${row.lot}-${idx}`"
                    class="text-p-sm text-ink-gray-8"
                  >
                    <td
                      class="border-b border-outline-gray-1 px-3 py-2.5 font-mono text-p-xs text-ink-gray-7"
                    >
                      {{ row.item || '—' }}
                    </td>
                    <td
                      class="border-b border-outline-gray-1 px-3 py-2.5 font-medium text-ink-gray-9"
                    >
                      {{ row.item_name || row.item || '—' }}
                    </td>
                    <td
                      class="border-b border-outline-gray-1 px-3 py-2.5 text-ink-gray-7"
                    >
                      {{ row.lot_no || row.lot || '—' }}
                    </td>
                    <td
                      class="border-b border-outline-gray-1 px-3 py-2.5 tabular-nums text-ink-gray-7"
                    >
                      {{
                        formatExpiryMonthYear(row.expiry_date) ||
                        fmtDate(row.expiry_date)
                      }}
                    </td>
                    <td
                      class="border-b border-outline-gray-1 px-3 py-2.5 text-right tabular-nums text-ink-gray-7"
                    >
                      {{ fmtQty(row.system_qty) }}
                    </td>
                    <td
                      class="border-b border-outline-gray-1 px-3 py-2.5 text-right"
                    >
                      <input
                        type="number"
                        step="1"
                        :value="row.counted_qty"
                        class="w-20 rounded border border-outline-gray-2 px-2 py-1 text-right text-p-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
                        :aria-label="
                          __('Số lượng thực đếm {0}', [
                            row.item_name || row.item,
                          ])
                        "
                        @input="(e) => setCounted(idx, e.target.value)"
                      />
                    </td>
                    <td
                      class="border-b border-outline-gray-1 px-3 py-2.5 text-right tabular-nums font-medium"
                      :class="varianceTextClass(variance(row))"
                    >
                      {{ variance(row) > 0 ? '+' : ''
                      }}{{ fmtQty(variance(row)) }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div
              class="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between"
            >
              <div class="flex flex-1 flex-col gap-1 sm:max-w-md">
                <label
                  for="sc-note"
                  class="text-p-xs font-medium text-ink-gray-6"
                  >{{ __('Ghi chú') }}</label
                >
                <FormControl
                  id="sc-note"
                  v-model="note"
                  type="text"
                  :placeholder="__('Lý do kiểm kê (tuỳ chọn)')"
                />
              </div>
              <div class="flex items-center gap-3">
                <p class="text-p-sm text-ink-gray-5">
                  {{ __('Tổng chênh') }}:
                  <span
                    class="font-medium"
                    :class="varianceTextClass(totalVariance)"
                    >{{ totalVariance > 0 ? '+' : ''
                    }}{{ fmtQty(totalVariance) }}</span
                  >
                </p>
                <Button
                  variant="solid"
                  :label="__('Chốt kiểm kê')"
                  :loading="counting.loading"
                  :disabled="!rows.length"
                  :aria-label="__('Chốt phiếu kiểm kê')"
                  @click="submitCount"
                />
              </div>
            </div>
          </template>
        </div>

        <!-- ── Lịch sử kiểm kê ───────────────────────────────────────────── -->
        <div
          class="flex flex-col gap-2 rounded-lg border border-outline-gray-modals bg-surface-white p-4"
        >
          <h2 class="text-p-sm font-semibold text-ink-gray-8">
            {{ __('Lịch sử kiểm kê') }}
          </h2>
          <div
            v-if="history.loading"
            class="py-3 text-center text-p-xs text-ink-gray-5"
          >
            {{ __('Đang tải…') }}
          </div>
          <div
            v-else-if="history.error"
            class="py-3 text-center text-p-xs text-red-600"
          >
            {{ __('Không tải được.') }}
          </div>
          <p
            v-else-if="!historyRows.length"
            class="py-3 text-center text-p-xs text-ink-gray-5"
          >
            {{ __('Chưa có phiếu kiểm kê.') }}
          </p>
          <table
            v-else
            class="w-full border-separate border-spacing-0 text-left"
          >
            <caption class="sr-only">
              {{
                __('Bảng lịch sử phiếu kiểm kê')
              }}
            </caption>
            <thead>
              <tr class="text-p-xs text-ink-gray-6">
                <th
                  class="border-b border-outline-gray-1 py-2 pr-4 font-medium"
                >
                  {{ __('Số phiếu') }}
                </th>
                <th
                  class="border-b border-outline-gray-1 py-2 pr-4 font-medium"
                >
                  {{ __('Người đếm') }}
                </th>
                <th
                  class="border-b border-outline-gray-1 py-2 pr-4 font-medium"
                >
                  {{ __('Lúc') }}
                </th>
                <th
                  class="border-b border-outline-gray-1 py-2 pr-4 text-right font-medium"
                >
                  {{ __('Tổng chênh') }}
                </th>
                <th class="border-b border-outline-gray-1 py-2 font-medium">
                  {{ __('Trạng thái') }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="h in historyRows"
                :key="h.name"
                class="text-p-sm text-ink-gray-8"
              >
                <td
                  class="border-b border-outline-gray-1 py-2.5 pr-4 font-medium"
                >
                  {{ h.name }}
                </td>
                <td
                  class="border-b border-outline-gray-1 py-2.5 pr-4 text-ink-gray-7"
                >
                  {{ h.counted_by_name || h.counted_by || '—' }}
                </td>
                <td
                  class="border-b border-outline-gray-1 py-2.5 pr-4 tabular-nums text-ink-gray-7"
                >
                  {{ formatStockTime(h.count_datetime) }}
                </td>
                <td
                  class="border-b border-outline-gray-1 py-2.5 pr-4 text-right tabular-nums"
                  :class="varianceTextClass(h.total_variance_qty)"
                >
                  {{ Number(h.total_variance_qty) > 0 ? '+' : ''
                  }}{{ fmtQty(h.total_variance_qty) }}
                </td>
                <td class="border-b border-outline-gray-1 py-2.5">
                  <Badge
                    variant="subtle"
                    size="sm"
                    :theme="docstatusTheme(h.docstatus)"
                    :label="docstatusLabel(h.docstatus)"
                  />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>
  </main>
</template>

<script setup>
import { ref, computed } from 'vue'
import { RouterLink } from 'vue-router'
import { Badge, Button, FormControl, toast } from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import {
  listWarehouses,
  stockCountSnapshot,
  createStockCount,
  listStockCounts,
} from '@/data/antmed'
import {
  fmtDate,
  fmtQty,
  formatExpiryMonthYear,
  formatStockTime,
  countVariance,
  varianceTextClass,
  docstatusLabel,
  docstatusTheme,
} from '@/utils/antmedUi'

const activeWarehouse = ref('')
const note = ref('')
// rows = snapshot + counted_qty (default = system_qty) đan xen state local.
const rows = ref([])

// Mọi loại kho (Tổng / Cá nhân NV / Ký gửi BV — kiểm kê được mọi kho).
const warehouses = listWarehouses({ params: { page_length: 200 }, auto: true })
const warehouseOptions = computed(() =>
  (warehouses.data?.data || []).map((w) => ({
    value: w.name,
    label: w.warehouse_name || w.name,
  })),
)
warehouses.onSuccess = (data) => {
  const list = data?.data || []
  if (!activeWarehouse.value && list.length) {
    activeWarehouse.value = list[0].name
    loadSnapshot(list[0].name)
  }
}
warehouses.onError = (err) =>
  toast.error(err?.messages?.[0] || __('Không tải được danh sách kho'))

// Snapshot tồn (RAW dict THƯỜNG → r.data.rows).
const snapshot = stockCountSnapshot()
const snapshotError = computed(
  () =>
    snapshot.error?.messages?.[0] ||
    snapshot.error?.message ||
    __('Không tải được tồn kho'),
)

// Lịch sử (dict bọc → r.data.data).
const history = listStockCounts({ params: { page_length: 10 }, auto: false })
const historyRows = computed(() => history.data?.data || [])

const counting = createStockCount()

function variance(row) {
  return countVariance(row.counted_qty, row.system_qty)
}
const totalVariance = computed(() =>
  rows.value.reduce((s, r) => s + variance(r), 0),
)

function setCounted(idx, value) {
  rows.value[idx].counted_qty = Number(value)
}

function loadSnapshot(warehouse) {
  snapshot.submit(
    { warehouse },
    {
      onSuccess: (data) => {
        // counted_qty default = system_qty (mockup: ô thực đếm prefill SL hệ thống).
        rows.value = (data?.rows || []).map((r) => ({
          ...r,
          counted_qty: r.system_qty,
        }))
      },
      onError: (err) =>
        toast.error(err?.messages?.[0] || __('Không tải được tồn kho')),
    },
  )
  history.update({ params: { warehouse, page_length: 10 } })
  history.reload()
}

// Param phát đi == UI selection (chống dead-control LL-FE-13).
function setWarehouse(value) {
  activeWarehouse.value = value
  note.value = ''
  loadSnapshot(value)
}

function submitCount() {
  if (!rows.value.length) return
  counting.submit(
    {
      warehouse: activeWarehouse.value,
      note: note.value || null,
      items: rows.value.map((r) => ({
        item: r.item,
        lot: r.lot,
        counted_qty: Number(r.counted_qty),
      })),
    },
    {
      onSuccess: (data) => {
        const v = Number(data?.total_variance_qty) || 0
        toast.success(__('Đã kiểm kê, tổng chênh {0}', [fmtQty(v)]))
        note.value = ''
        loadSnapshot(activeWarehouse.value)
      },
      onError: (err) =>
        toast.error(err?.messages?.[0] || __('Không chốt được kiểm kê')),
    },
  )
}
</script>
