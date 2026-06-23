<template>
  <main class="flex h-full flex-col" aria-labelledby="antmed-lot-list-title">
    <!-- Header + breadcrumb: Trang chủ › Tồn kho › Quản lý lot -->
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
        <span class="text-ink-gray-7" aria-current="page">{{
          __('Quản lý lot')
        }}</span>
      </nav>
      <div class="flex flex-col gap-1">
        <h1
          id="antmed-lot-list-title"
          class="text-xl font-semibold text-ink-gray-9"
        >
          {{ __('Quản lý lô vật tư') }}
        </h1>
        <p class="text-p-sm text-ink-gray-6">
          {{
            __(
              'Tra cứu, lọc lô theo vật tư / HSD / trạng thái thu hồi và truy vết từng lô.',
            )
          }}
        </p>
      </div>
    </header>

    <section class="flex-1 overflow-auto px-6 py-5">
      <div class="flex flex-col gap-4">
        <!-- Bộ lọc -->
        <div
          class="flex flex-col gap-3 rounded-lg border border-outline-gray-modals bg-surface-white p-4 sm:flex-row sm:items-end"
        >
          <div class="flex flex-1 flex-col gap-1">
            <label
              for="lot-search"
              class="text-p-xs font-medium text-ink-gray-6"
              >{{ __('Tìm số lô') }}</label
            >
            <FormControl
              id="lot-search"
              v-model="search"
              type="text"
              :placeholder="__('Nhập số lô')"
              :aria-label="__('Tìm theo số lô')"
              @keyup.enter="applyFilters"
            />
          </div>
          <div class="flex flex-1 flex-col gap-1">
            <label
              for="lot-item"
              class="text-p-xs font-medium text-ink-gray-6"
              >{{ __('Vật tư') }}</label
            >
            <FormControl
              id="lot-item"
              type="select"
              :options="itemOptions"
              :modelValue="itemFilter"
              :aria-label="__('Lọc theo vật tư')"
              @update:modelValue="
                (v) => {
                  itemFilter = v
                  applyFilters()
                }
              "
            />
          </div>
          <div class="flex flex-1 flex-col gap-1">
            <label
              for="lot-recall"
              class="text-p-xs font-medium text-ink-gray-6"
              >{{ __('Trạng thái thu hồi') }}</label
            >
            <FormControl
              id="lot-recall"
              type="select"
              :options="recallOptions"
              :modelValue="recallFilter"
              :aria-label="__('Lọc theo trạng thái thu hồi')"
              @update:modelValue="
                (v) => {
                  recallFilter = v
                  applyFilters()
                }
              "
            />
          </div>
          <Button
            variant="solid"
            :label="__('Lọc')"
            :loading="lots.loading"
            @click="applyFilters"
          />
        </div>

        <!-- loading / error / empty / data -->
        <div
          v-if="lots.loading && !rows.length"
          class="flex items-center justify-center gap-2 py-16 text-ink-gray-6"
          aria-live="polite"
        >
          <LoadingIndicator class="h-4 w-4" />
          <span class="text-p-base">{{ __('Đang tải danh sách lô…') }}</span>
        </div>
        <div
          v-else-if="lots.error"
          class="flex flex-col items-center gap-3 py-16 text-center"
          role="alert"
        >
          <Badge
            variant="subtle"
            theme="red"
            size="lg"
            :label="__('Không tải được danh sách lô')"
          />
          <Button
            variant="outline"
            :label="__('Thử lại')"
            @click="lots.reload()"
          />
        </div>
        <div
          v-else-if="!rows.length"
          class="flex flex-col items-center gap-2 rounded-lg border border-dashed border-outline-gray-2 py-16 text-center text-ink-gray-6"
        >
          <p class="text-p-base">{{ __('Không có lô nào khớp bộ lọc') }}</p>
        </div>

        <!-- Bảng lô -->
        <div
          v-else
          class="overflow-x-auto rounded-lg border border-outline-gray-modals bg-surface-white"
        >
          <table class="w-full border-separate border-spacing-0 text-left">
            <caption class="sr-only">
              {{
                __('Danh sách lô vật tư')
              }}
            </caption>
            <thead>
              <tr class="text-p-xs text-ink-gray-6">
                <th
                  class="border-b border-outline-gray-1 px-3 py-2 font-medium"
                >
                  {{ __('Số lô') }}
                </th>
                <th
                  class="border-b border-outline-gray-1 px-3 py-2 font-medium"
                >
                  {{ __('Vật tư') }}
                </th>
                <th
                  class="border-b border-outline-gray-1 px-3 py-2 font-medium"
                >
                  {{ __('NCC') }}
                </th>
                <th
                  class="border-b border-outline-gray-1 px-3 py-2 font-medium"
                >
                  {{ __('HSD') }}
                </th>
                <th
                  class="border-b border-outline-gray-1 px-3 py-2 font-medium"
                >
                  {{ __('Thu hồi') }}
                </th>
                <th
                  class="border-b border-outline-gray-1 px-3 py-2 text-right font-medium"
                >
                  {{ __('Hành động') }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in rows"
                :key="row.name"
                class="text-p-sm text-ink-gray-8"
              >
                <td
                  class="border-b border-outline-gray-1 px-3 py-2.5 font-medium text-ink-gray-9"
                >
                  {{ row.lot_no }}
                </td>
                <td class="border-b border-outline-gray-1 px-3 py-2.5">
                  {{ row.item_name || row.item || '—' }}
                </td>
                <td
                  class="border-b border-outline-gray-1 px-3 py-2.5 text-ink-gray-7"
                >
                  {{ row.supplier || '—' }}
                </td>
                <td
                  class="border-b border-outline-gray-1 px-3 py-2.5 tabular-nums"
                >
                  {{ fmtDate(row.expiry_date) }}
                </td>
                <td class="border-b border-outline-gray-1 px-3 py-2.5">
                  <span
                    :class="[
                      'inline-flex items-center rounded-full px-2.5 py-0.5 text-p-xs font-medium',
                      recallChipClass(row.recall_status),
                    ]"
                  >
                    {{ row.recall_status || '—' }}
                  </span>
                </td>
                <td
                  class="border-b border-outline-gray-1 px-3 py-2.5 text-right"
                >
                  <RouterLink
                    :to="{ name: 'AntmedLotTrace', query: { lot: row.lot_no } }"
                    class="rounded text-p-sm text-teal-700 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
                    :aria-label="__('Truy vết lô') + ' ' + row.lot_no"
                  >
                    {{ __('Truy vết') }}
                  </RouterLink>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="rows.length" class="text-p-xs text-ink-gray-5">
          {{ __('Tổng {0} lô', [totalCount]) }}
        </p>
      </div>
    </section>
  </main>
</template>

<script setup>
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { Badge, Button, FormControl } from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import { listLots, listItems } from '@/data/antmed'
import { fmtDate, recallChipClass } from '@/utils/antmedUi'

const search = ref('')
const itemFilter = ref('')
const recallFilter = ref('')

// Trạng thái thu hồi khớp EXACT options DocType AntMed Lot.recall_status (VI có dấu).
const recallOptions = [
  { value: '', label: __('Tất cả trạng thái') },
  { value: 'Bình thường', label: __('Bình thường') },
  { value: 'Theo dõi', label: __('Theo dõi') },
  { value: 'Đã thu hồi', label: __('Đã thu hồi') },
]

// Params phát đi == UI selection (chống dead-control). filters object PHẢI JSON.stringify (LL).
function buildParams() {
  const p = { page_length: 200, start: 0 }
  if (search.value.trim()) p.search = search.value.trim()
  if (itemFilter.value) p.item = itemFilter.value
  if (recallFilter.value)
    p.filters = JSON.stringify({ recall_status: recallFilter.value })
  return p
}

const lots = listLots({ params: buildParams(), auto: true })
const rows = computed(() => lots.data?.data || [])
const totalCount = computed(() => lots.data?.total_count ?? rows.value.length)

function applyFilters() {
  lots.submit(buildParams())
}

// Dropdown VTYT (lọc theo vật tư).
const items = listItems({ params: { page_length: 0 }, auto: true })
const itemOptions = computed(() => [
  { value: '', label: __('Tất cả vật tư') },
  ...(items.data?.data || []).map((it) => ({
    value: it.name,
    label: it.item_name || it.item_code,
  })),
])
</script>
