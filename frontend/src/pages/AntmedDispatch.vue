<template>
  <main class="flex h-full flex-col" aria-labelledby="antmed-dispatch-title">
    <!-- Header + breadcrumb: Trang chủ › Điều phối -->
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
          __('Điều phối')
        }}</span>
      </nav>
      <div class="flex flex-col gap-1">
        <h1
          id="antmed-dispatch-title"
          class="text-xl font-semibold text-ink-gray-9"
        >
          {{ __('Bảng điều phối ca giao phòng mổ') }}
        </h1>
        <p class="text-p-sm text-ink-gray-6">
          {{ __('Pipeline gói thầu theo giai đoạn — chỉ xem, không kéo-thả') }}
        </p>
      </div>
    </header>

    <!-- 3 KPI card thật ở đầu màn (số = totals BE, KHÔNG hardcode) -->
    <section
      class="grid grid-cols-1 gap-3 px-6 pt-4 sm:grid-cols-3"
      :aria-label="__('Chỉ số pipeline')"
    >
      <AntmedKpiCard
        :label="__('Tổng số deal')"
        :value="totals.total_deals"
        :empty="board.loading || !!board.error"
        :placeholder-hint="__('Đang tải…')"
      />
      <AntmedKpiCard
        :label="__('Giá trị đang mở')"
        :value="formatVnMoney(totals.open_value)"
        :empty="board.loading || !!board.error"
        :placeholder-hint="__('Đang tải…')"
      />
      <AntmedKpiCard
        :label="__('Giá trị đã thắng')"
        :value="formatVnMoney(totals.won_value)"
        :empty="board.loading || !!board.error"
        :placeholder-hint="__('Đang tải…')"
      />
    </section>

    <!-- Tri-branch: loading / error / empty / data -->
    <section class="flex-1 overflow-auto px-6 pb-6 pt-4" aria-live="polite">
      <!-- Loading -->
      <div
        v-if="board.loading"
        class="flex items-center justify-center gap-2 py-16 text-ink-gray-6"
      >
        <LoadingIndicator class="h-4 w-4" />
        <span class="text-p-base">{{ __('Đang tải…') }}</span>
      </div>

      <!-- Error: banner + nút Thử lại reload -->
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

      <!-- Empty: không lane nào có card (BR-13 fail-closed cũng rơi vào đây) -->
      <div
        v-else-if="!hasCards"
        class="flex flex-col items-center gap-2 py-16 text-center text-ink-gray-6"
      >
        <p class="text-p-base">{{ __('Chưa có deal nào trong pipeline') }}</p>
        <p class="text-p-sm">
          {{ __('Chưa có gói thầu nào trong phạm vi của bạn.') }}
        </p>
      </div>

      <!-- Kanban: N cột = lanes (BE đã lọc type Open/Ongoing/Won + sort theo position) -->
      <div
        v-else
        class="flex gap-4 overflow-x-auto pb-2"
        role="list"
        :aria-label="__('Các giai đoạn pipeline gói thầu')"
      >
        <!-- 1 cột / lane. BE đã group + sort → FE KHÔNG sort/aggregate lại. -->
        <div
          v-for="lane in lanes"
          :key="lane.status"
          class="flex w-72 shrink-0 flex-col rounded-lg bg-surface-gray-1"
          role="listitem"
        >
          <!-- Header cột: nhãn VI + badge số deal trong cột -->
          <div
            class="flex items-center justify-between gap-2 border-b border-outline-gray-modals px-3 py-2"
          >
            <h2 class="truncate text-p-sm font-semibold text-ink-gray-8">
              {{ lane.label }}
            </h2>
            <Badge
              variant="subtle"
              theme="gray"
              size="sm"
              :label="String(lane.count)"
              :aria-label="
                __('{0} deal trong giai đoạn {1}', [lane.count, lane.label])
              "
            />
          </div>

          <!-- Cards trong cột (sort desc deal_value bởi BE) -->
          <div class="flex flex-col gap-2 p-2">
            <article
              v-for="card in lane.cards"
              :key="card.deal"
              class="flex flex-col gap-2 rounded-md border border-outline-gray-1 bg-surface-white p-3 shadow-sm"
            >
              <!-- organization (fallback khi null) -->
              <p class="text-p-base font-medium text-ink-gray-9">
                {{ card.organization || '— Chưa có tổ chức —' }}
              </p>

              <!-- territory (fallback '—') -->
              <p class="text-p-xs text-ink-gray-6">
                {{ __('Tuyến') }}: {{ card.territory || '—' }}
              </p>

              <!-- Tên NV phụ trách (full_name — KHÔNG lộ email) -->
              <p class="text-p-xs text-ink-gray-7">
                {{ __('Phụ trách') }}: {{ card.deal_owner_name || '—' }}
              </p>

              <!-- Giá trị deal (VND) -->
              <p class="text-p-sm font-semibold tabular-nums text-ink-gray-8">
                {{ formatVnMoney(card.deal_value) }}
              </p>

              <!-- Thanh khả năng chốt (probability) — dispatchBarClass theo bar_theme BE -->
              <div class="flex items-center gap-2">
                <div
                  class="h-2 flex-1 overflow-hidden rounded-full bg-ink-gray-2"
                  role="progressbar"
                  :aria-valuenow="Math.round(Number(card.probability) || 0)"
                  aria-valuemin="0"
                  aria-valuemax="100"
                  :aria-label="
                    __('Khả năng chốt {0}%', [
                      Math.round(Number(card.probability) || 0),
                    ])
                  "
                >
                  <div
                    class="h-full rounded-full"
                    :class="dispatchBarClass(card.bar_theme)"
                    :style="{ width: barWidth(card.probability) }"
                  ></div>
                </div>
                <span class="shrink-0 text-p-xs tabular-nums text-ink-gray-6">
                  {{ Math.round(Number(card.probability) || 0) }}%
                </span>
              </div>
            </article>
          </div>
        </div>
      </div>
    </section>
  </main>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { Badge, Button, toast } from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import AntmedKpiCard from '@/components/Antmed/AntmedKpiCard.vue'
import { getDispatchBoard } from '@/data/antmed'
import { dispatchBarClass, formatVnMoney } from '@/utils/antmedUi'

// Endpoint trả RAW dict THƯỜNG { lanes, totals } → đọc r.data.* TRỰC TIẾP
// (KHÔNG .data.data — cùng idiom getTeamRoster/getDashboardOverview).
const board = getDispatchBoard({ auto: true })

// lanes BE đã lọc type (Open/Ongoing/Won) + sort theo position; cards sort desc deal_value.
// FE KHÔNG sort/aggregate lại.
const lanes = computed(() => board.data?.lanes || [])
const totals = computed(
  () => board.data?.totals || { total_deals: 0, open_value: 0, won_value: 0 },
)

// Có ít nhất 1 card trong toàn bộ pipeline? (lane rỗng vẫn render cột, nhưng board hoàn
// toàn trống → empty-state). Dùng .some (không aggregate giá trị) — BE đã tính totals.
const hasCards = computed(() =>
  lanes.value.some((l) => (l.cards || []).length > 0),
)

// Width thanh probability: clamp 0–100.
function barWidth(prob) {
  const p = Number(prob)
  const clamped = Number.isFinite(p) ? Math.max(0, Math.min(100, p)) : 0
  return `${clamped}%`
}

board.onError = (err) => {
  toast.error(err?.messages?.[0] || __('Không tải được bảng điều phối'))
}

const errorMessage = computed(
  () =>
    board.error?.messages?.[0] ||
    board.error?.message ||
    __('Không tải được bảng điều phối'),
)
</script>
