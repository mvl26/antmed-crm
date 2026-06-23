<template>
  <main
    class="flex h-full flex-col"
    aria-labelledby="antmed-stock-entries-title"
  >
    <!-- Header + breadcrumb: Trang chủ › Tồn kho › Phiếu xuất -->
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
          <span class="text-ink-gray-6">{{ __('Tồn kho') }}</span>
          <span class="px-1.5 text-ink-gray-4" aria-hidden="true">›</span>
          <span class="text-ink-gray-7" aria-current="page">{{
            __('Phiếu xuất')
          }}</span>
        </nav>
        <div class="flex flex-col gap-1">
          <h1
            id="antmed-stock-entries-title"
            class="text-xl font-semibold text-ink-gray-9"
          >
            {{ __('Phiếu xuất gần đây') }}
          </h1>
          <p class="text-p-sm text-ink-gray-6">
            {{ __('Các phiếu xuất kho cho nhân viên (mới nhất trước)') }}
          </p>
        </div>
      </div>

      <!-- Bộ lọc loại phiếu (param phát đi == lựa chọn UI — chống dead-control) -->
      <div class="flex flex-col gap-1 sm:w-56">
        <label
          for="se-filter-entry-type"
          class="text-p-xs font-medium text-ink-gray-6"
        >
          {{ __('Loại phiếu') }}
        </label>
        <FormControl
          id="se-filter-entry-type"
          type="select"
          :options="entryTypeOptions"
          :modelValue="activeEntryType"
          :aria-label="__('Lọc theo loại phiếu')"
          @update:modelValue="setEntryType"
        />
      </div>
    </header>

    <!-- Tri-branch: loading / error / empty / data -->
    <section class="flex-1 overflow-auto px-6 pb-6" aria-live="polite">
      <!-- Loading -->
      <div
        v-if="entries.loading"
        class="flex items-center justify-center gap-2 py-16 text-ink-gray-6"
      >
        <LoadingIndicator class="h-4 w-4" />
        <span class="text-p-base">{{ __('Đang tải phiếu xuất…') }}</span>
      </div>

      <!-- Error: banner + nút Thử lại reload -->
      <div
        v-else-if="entries.error"
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
          @click="entries.reload()"
        />
      </div>

      <!-- Empty -->
      <div
        v-else-if="!rows.length"
        class="flex flex-col items-center gap-2 py-16 text-center text-ink-gray-6"
      >
        <p class="text-p-base">{{ __('Chưa có phiếu xuất') }}</p>
        <p class="text-p-sm">
          {{
            __(
              'Phiếu xuất kho cho NV sẽ hiển thị ở đây sau khi Thủ kho lập phiếu.',
            )
          }}
        </p>
      </div>

      <!-- Data table (widget "Phiếu xuất gần đây"): Số phiếu / NV / Loại / Giá trị / Lúc -->
      <table v-else class="w-full border-separate border-spacing-0 text-left">
        <caption class="sr-only">
          {{
            __('Bảng phiếu xuất kho gần đây')
          }}
        </caption>
        <thead>
          <tr class="text-p-sm text-ink-gray-6">
            <th
              class="border-b border-outline-gray-modals py-2 pr-4 font-medium"
            >
              {{ __('Số phiếu') }}
            </th>
            <th
              class="border-b border-outline-gray-modals py-2 pr-4 font-medium"
            >
              {{ __('NV') }}
            </th>
            <th
              class="border-b border-outline-gray-modals py-2 pr-4 font-medium"
            >
              {{ __('Loại phiếu') }}
            </th>
            <th
              class="border-b border-outline-gray-modals py-2 pr-4 text-right font-medium"
            >
              {{ __('Giá trị') }}
            </th>
            <th
              class="border-b border-outline-gray-modals py-2 text-right font-medium"
            >
              {{ __('Lúc') }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in rows"
            :key="row.name"
            class="text-p-base text-ink-gray-8"
          >
            <!-- Số phiếu (name = naming series AM-SE) — drill-down chi tiết phiếu (mockup C2) -->
            <td class="border-b border-outline-gray-1 py-3 pr-4 font-medium">
              <RouterLink
                :to="{
                  name: 'AntmedStockEntryDetail',
                  params: { name: row.name },
                }"
                class="rounded text-teal-700 hover:text-teal-900 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
                :aria-label="__('Xem chi tiết phiếu') + ' ' + row.name"
              >
                {{ row.name }}
              </RouterLink>
            </td>

            <!-- NV: tên user (nv_employee_name), KHÔNG lộ email/ID -->
            <td
              class="border-b border-outline-gray-1 py-3 pr-4 text-ink-gray-7"
            >
              {{ row.nv_employee_name || row.nv_employee || '—' }}
            </td>

            <!-- Loại phiếu: chip theme, kèm CHỮ (không chỉ màu — WCAG AA) -->
            <td class="border-b border-outline-gray-1 py-3 pr-4">
              <Badge
                v-if="row.entry_type"
                variant="subtle"
                size="sm"
                :theme="entryTypeChipTheme(row.entry_type)"
                :label="row.entry_type"
              />
              <span v-else class="text-ink-gray-5">—</span>
            </td>

            <!-- Giá trị (total_value, format VI 'X,Y tr / X,Y tỷ') -->
            <td
              class="border-b border-outline-gray-1 py-3 pr-4 text-right tabular-nums text-ink-gray-8"
            >
              {{ formatVnMoney(row.total_value) }}
            </td>

            <!-- Lúc (posting_datetime, HH:mm dd/MM/yyyy) -->
            <td
              class="border-b border-outline-gray-1 py-3 text-right tabular-nums text-ink-gray-7"
            >
              {{ formatStockTime(row.posting_datetime) }}
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Tổng số (count==rows) -->
      <p
        v-if="!entries.loading && !entries.error && rows.length"
        class="pt-3 text-p-sm text-ink-gray-5"
      >
        {{ __('Tổng cộng') }}: {{ totalCount }} {{ __('phiếu') }}
      </p>
    </section>
  </main>
</template>

<script setup>
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { Badge, Button, FormControl, toast } from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import { listStockEntries } from '@/data/antmed'
import {
  formatVnMoney,
  formatStockTime,
  entryTypeChipTheme,
} from '@/utils/antmedUi'

// Options loại phiếu — value khớp EXACT options DocType `AntMed Stock Entry.entry_type`
// (VI có dấu, KHÔNG chuỗi EN). 'Xuất cho NV' đặt đầu (mặc định widget Thủ kho); '' = Tất cả.
const entryTypeOptions = [
  { value: 'Xuất cho NV', label: __('Xuất cho NV') },
  { value: '', label: __('Tất cả loại phiếu') },
  { value: 'Nhập NCC', label: __('Nhập NCC') },
  { value: 'Chuyển kho', label: __('Chuyển kho') },
  { value: 'Nhập ký gửi BV', label: __('Nhập ký gửi BV') },
  { value: 'Điều chỉnh', label: __('Điều chỉnh') },
]

// Mặc định lọc 'Xuất cho NV' (acceptance widget kho).
const activeEntryType = ref('Xuất cho NV')

// Widget Thủ kho "Phiếu xuất gần đây" → param entry_type='Xuất cho NV' phát đi NGAY fetch đầu.
// Endpoint trả dict bọc { data, total_count } → đọc r.data.data (KHÔNG createListResource).
const entries = listStockEntries({
  params: { entry_type: 'Xuất cho NV', start: 0, page_length: 50 },
  auto: true,
})

const rows = computed(() => entries.data?.data || [])
const totalCount = computed(
  () => entries.data?.total_count ?? rows.value.length,
)

const errorMessage = computed(
  () =>
    entries.error?.messages?.[0] ||
    entries.error?.message ||
    __('Không tải được phiếu xuất'),
)

// Param phát đi == UI selection (chống dead-control LL-FE-13): chọn loại → submit lại.
// '' ('Tất cả') → KHÔNG truyền key entry_type (BE coi None = mọi loại).
function setEntryType(value) {
  activeEntryType.value = value
  const params = { start: 0, page_length: 50 }
  if (value) params.entry_type = value
  entries.submit(params)
}

// Surface lỗi BR-XX / permission từ BE qua toast (ngoài banner tri-branch).
entries.onError = (err) => {
  toast.error(err?.messages?.[0] || __('Không tải được phiếu xuất'))
}
</script>
