<template>
  <main class="flex h-full flex-col" aria-labelledby="antmed-instruments-title">
    <!-- Header + breadcrumb: Trang chủ › Bộ dụng cụ -->
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
        <span class="text-ink-gray-7" aria-current="page">{{
          __('Bộ dụng cụ')
        }}</span>
      </nav>
      <div class="flex flex-col gap-1">
        <h1
          id="antmed-instruments-title"
          class="text-xl font-semibold text-ink-gray-9"
        >
          🧰 {{ __('Quản lý vòng đời bộ dụng cụ') }}
        </h1>
        <p class="text-p-sm text-ink-gray-6">
          {{
            __(
              'Theo dõi vòng đời 7 trạng thái của bộ phẫu thuật mượn — đặt · giao · dùng · trả · tiệt khuẩn',
            )
          }}
        </p>
      </div>
    </header>

    <!-- 4 KPI thật (số = board.kpis BE, KHÔNG hardcode) -->
    <section
      class="grid grid-cols-2 gap-3 px-6 pt-4 lg:grid-cols-4"
      :aria-label="__('Chỉ số bộ dụng cụ')"
    >
      <AntmedKpiCard
        tone="teal"
        icon="🧰"
        :label="__('Tổng bộ')"
        :value="kpis.total"
        :empty="loadingOrError"
        :placeholder-hint="__('Đang tải…')"
      />
      <AntmedKpiCard
        tone="blue"
        icon="🔄"
        :label="__('Đang lưu hành')"
        :value="kpis.in_circulation"
        :sub="__('đang trong vòng mượn')"
        :empty="loadingOrError"
        :placeholder-hint="__('Đang tải…')"
      />
      <AntmedKpiCard
        tone="green"
        icon="✅"
        :label="__('Tại kho — Sẵn sàng')"
        :value="kpis.ready"
        :sub="__('sẵn sàng cho mượn')"
        :empty="loadingOrError"
        :placeholder-hint="__('Đang tải…')"
      />
      <AntmedKpiCard
        tone="red"
        icon="⚠️"
        :label="__('Quá hạn / Thất lạc')"
        :value="kpis.issue"
        :sub="__('cần xử lý')"
        :empty="loadingOrError"
        :placeholder-hint="__('Đang tải…')"
      />
    </section>

    <section class="flex-1 overflow-auto px-6 pb-6 pt-4" aria-live="polite">
      <!-- Loading -->
      <div
        v-if="board.loading"
        class="flex items-center justify-center gap-2 py-16 text-ink-gray-6"
      >
        <LoadingIndicator class="h-4 w-4" />
        <span class="text-p-base">{{ __('Đang tải…') }}</span>
      </div>

      <!-- Error -->
      <div
        v-else-if="board.error"
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
          @click="board.reload()"
        />
      </div>

      <!-- Empty -->
      <div
        v-else-if="!sets.length"
        class="flex flex-col items-center gap-2 py-16 text-center text-ink-gray-6"
      >
        <p class="text-p-base">{{ __('Chưa có bộ dụng cụ') }}</p>
        <p class="text-p-sm">
          {{ __('Chưa có bộ dụng cụ nào trong phạm vi của bạn.') }}
        </p>
      </div>

      <!-- Data: grid card + báo cáo tần suất -->
      <template v-else>
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <AntmedInstrumentSetCard v-for="s in sets" :key="s.name" :set="s" />
        </div>

        <!-- Báo cáo tần suất sử dụng (gợi ý mua thêm bộ) -->
        <div
          class="mt-6 rounded-lg border border-outline-gray-2 bg-surface-white p-4"
        >
          <h2 class="mb-3 text-p-base font-semibold text-ink-gray-8">
            {{ __('Báo cáo tần suất sử dụng (gợi ý mua thêm bộ)') }}
          </h2>
          <table class="w-full border-separate border-spacing-0 text-left">
            <thead>
              <tr class="text-p-xs uppercase text-ink-gray-5">
                <th
                  class="border-b border-outline-gray-modals py-2 pr-4 font-medium"
                >
                  {{ __('Loại bộ') }}
                </th>
                <th
                  class="border-b border-outline-gray-modals py-2 pr-4 text-right font-medium"
                >
                  {{ __('Số bộ') }}
                </th>
                <th
                  class="border-b border-outline-gray-modals py-2 pr-4 text-right font-medium"
                >
                  {{ __('Lượt mượn/tháng') }}
                </th>
                <th
                  class="border-b border-outline-gray-modals py-2 pr-4 text-right font-medium"
                >
                  {{ __('Avg vòng quay (ngày)') }}
                </th>
                <th
                  class="border-b border-outline-gray-modals py-2 font-medium"
                >
                  {{ __('Đề xuất') }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="f in frequency"
                :key="f.surgery_type"
                class="text-p-base text-ink-gray-8"
              >
                <td
                  class="border-b border-outline-gray-1 py-2.5 pr-4 font-medium text-ink-gray-9"
                >
                  {{ f.surgery_type }}
                </td>
                <td
                  class="border-b border-outline-gray-1 py-2.5 pr-4 text-right tabular-nums"
                >
                  {{ f.set_count }}
                </td>
                <td
                  class="border-b border-outline-gray-1 py-2.5 pr-4 text-right tabular-nums"
                >
                  {{ f.loans_month }}
                </td>
                <td
                  class="border-b border-outline-gray-1 py-2.5 pr-4 text-right tabular-nums"
                >
                  {{ f.avg_cycle_days ?? '—' }}
                </td>
                <td class="border-b border-outline-gray-1 py-2.5">
                  <Badge
                    variant="subtle"
                    :theme="freqTheme(f.theme)"
                    size="sm"
                    :label="f.suggestion"
                  />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </section>
  </main>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { Badge, Button, toast } from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import AntmedKpiCard from '@/components/Antmed/AntmedKpiCard.vue'
import AntmedInstrumentSetCard from '@/components/Antmed/AntmedInstrumentSetCard.vue'
import { getInstrumentBoard } from '@/data/antmed'

// RAW dict { kpis, sets, frequency } → đọc r.data.* TRỰC TIẾP (KHÔNG .data.data).
const board = getInstrumentBoard({ auto: true })

const kpis = computed(
  () => board.data?.kpis || { total: 0, in_circulation: 0, ready: 0, issue: 0 },
)
const sets = computed(() => board.data?.sets || [])
const frequency = computed(() => board.data?.frequency || [])

const loadingOrError = computed(() => board.loading || !!board.error)

board.onError = (err) => {
  toast.error(err?.messages?.[0] || __('Không tải được dữ liệu bộ dụng cụ'))
}

const errorMessage = computed(
  () =>
    board.error?.messages?.[0] ||
    board.error?.message ||
    __('Không tải được dữ liệu bộ dụng cụ'),
)

// theme từ BE ('ok'/'warn'/'danger') → theme Badge frappe-ui.
const FREQ_THEME = { ok: 'green', warn: 'orange', danger: 'red' }
function freqTheme(t) {
  return FREQ_THEME[t] || 'gray'
}
</script>
