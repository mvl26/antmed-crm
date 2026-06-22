<template>
  <main class="flex h-full flex-col" aria-labelledby="antmed-deal-detail-title">
    <header
      class="flex flex-col gap-2 border-b border-outline-gray-modals px-6 py-4"
    >
      <nav class="text-p-xs text-ink-gray-5" :aria-label="__('Đường dẫn')">
        <RouterLink
          to="/antmed"
          class="rounded text-ink-gray-6 hover:text-ink-gray-8"
          >{{ __('Trang chủ') }}</RouterLink
        >
        <span class="px-1.5 text-ink-gray-4" aria-hidden="true">›</span>
        <RouterLink
          to="/antmed/deals"
          class="rounded text-ink-gray-6 hover:text-ink-gray-8"
          >{{ __('Pipeline cơ hội') }}</RouterLink
        >
        <span class="px-1.5 text-ink-gray-4" aria-hidden="true">›</span>
        <span class="text-ink-gray-7" aria-current="page">{{
          d.am_hospital_name || d.organization || name
        }}</span>
      </nav>
      <div class="flex flex-wrap items-center gap-3">
        <h1
          id="antmed-deal-detail-title"
          class="text-xl font-semibold text-ink-gray-9"
        >
          📈 {{ d.am_hospital_name || d.organization || name }}
        </h1>
        <Badge
          v-if="d.status"
          variant="subtle"
          :theme="stageTheme(d.status)"
          size="md"
          :label="stageLabel(d.status)"
        />
        <Badge
          v-if="d.probability != null"
          variant="subtle"
          theme="blue"
          size="md"
          :label="d.probability + '%'"
        />
      </div>
    </header>

    <section class="flex-1 overflow-auto px-6 pb-8 pt-5" aria-live="polite">
      <div
        v-if="resource.loading"
        class="flex items-center justify-center gap-2 py-16 text-ink-gray-6"
      >
        <LoadingIndicator class="h-4 w-4" /><span>{{ __('Đang tải…') }}</span>
      </div>
      <div
        v-else-if="resource.error"
        class="flex flex-col items-center gap-3 py-16 text-center"
        role="alert"
      >
        <Badge
          variant="subtle"
          theme="red"
          size="lg"
          :label="__('Không tải được cơ hội')"
        />
        <p class="max-w-md text-p-sm text-ink-gray-6">{{ errorMessage }}</p>
        <Button
          variant="outline"
          :label="__('Thử lại')"
          @click="resource.reload()"
        />
      </div>

      <div v-else class="mx-auto max-w-3xl">
        <div class="mb-5 flex items-baseline gap-3">
          <span class="text-2xl font-bold tabular-nums text-teal-700">{{
            d.deal_value ? formatVnMoney(d.deal_value) + ' ₫' : '—'
          }}</span>
          <span class="text-p-sm text-ink-gray-5">{{
            __('Giá trị cơ hội')
          }}</span>
        </div>

        <dl
          class="grid grid-cols-1 gap-x-8 gap-y-4 rounded-xl border border-outline-gray-2 bg-surface-white p-5 sm:grid-cols-2"
        >
          <div>
            <dt class="text-p-xs uppercase text-ink-gray-5">
              {{ __('Bệnh viện (khách hàng)') }}
            </dt>
            <dd class="text-p-base text-ink-gray-9">
              {{ d.am_hospital_name || d.am_hospital || '—' }}
            </dd>
          </div>
          <div>
            <dt class="text-p-xs uppercase text-ink-gray-5">
              {{ __('Giai đoạn') }}
            </dt>
            <dd>
              <Badge
                variant="subtle"
                :theme="stageTheme(d.status)"
                size="sm"
                :label="stageLabel(d.status)"
              />
            </dd>
          </div>
          <div>
            <dt class="text-p-xs uppercase text-ink-gray-5">
              {{ __('Xác suất') }}
            </dt>
            <dd class="text-p-base text-ink-gray-9">
              {{ d.probability != null ? d.probability + '%' : '—' }}
            </dd>
          </div>
          <div>
            <dt class="text-p-xs uppercase text-ink-gray-5">
              {{ __('NV phụ trách') }}
            </dt>
            <dd class="text-p-base text-ink-gray-9">
              {{ d.deal_owner_name || '—' }}
            </dd>
          </div>
          <div>
            <dt class="text-p-xs uppercase text-ink-gray-5">
              {{ __('Tuyến') }}
            </dt>
            <dd class="text-p-base text-ink-gray-9">
              {{ d.territory || '—' }}
            </dd>
          </div>
          <div>
            <dt class="text-p-xs uppercase text-ink-gray-5">
              {{ __('Dự kiến chốt') }}
            </dt>
            <dd class="text-p-base text-ink-gray-9">
              {{ fmtDate(d.expected_closure_date) }}
            </dd>
          </div>
          <div>
            <dt class="text-p-xs uppercase text-ink-gray-5">
              {{ __('Nguồn (Lead)') }}
            </dt>
            <dd class="text-p-base text-ink-gray-9">
              {{ d.lead_name || '—' }}
            </dd>
          </div>
        </dl>

        <!-- Gói thầu VTYT (custom field trên Deal) -->
        <div
          class="mt-5 rounded-xl border border-outline-gray-2 bg-surface-white p-5"
        >
          <h3 class="mb-3 text-p-base font-semibold text-ink-gray-8">
            🎯 {{ __('Gói thầu / VTYT') }}
          </h3>
          <dl class="grid grid-cols-1 gap-x-8 gap-y-4 sm:grid-cols-2">
            <div>
              <dt class="text-p-xs uppercase text-ink-gray-5">
                {{ __('Số gói thầu') }}
              </dt>
              <dd class="text-p-base text-ink-gray-9">
                {{ d.am_tender_no || '—' }}
              </dd>
            </div>
            <div>
              <dt class="text-p-xs uppercase text-ink-gray-5">
                {{ __('Số QĐ KQLCNT') }}
              </dt>
              <dd class="text-p-base font-medium text-green-700">
                {{ d.am_decision_no || '—' }}
              </dd>
            </div>
          </dl>
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
import { getDeal, DEAL_STAGE_LABEL, DEAL_STAGE_THEME } from '@/data/antmed'
import { formatVnMoney, fmtDate } from '@/utils/antmedUi'

const props = defineProps({ name: { type: String, required: true } })

const resource = getDeal({ params: { deal: props.name }, auto: true })
resource.onError = (err) =>
  toast.error(err?.messages?.[0] || __('Không tải được cơ hội'))

const d = computed(() => resource.data || {})

function stageLabel(s) {
  return DEAL_STAGE_LABEL[s] || s
}
function stageTheme(s) {
  return DEAL_STAGE_THEME[s] || 'gray'
}
// fmtDate (dd/MM/yyyy) gom về canon @/utils/antmedUi (output không đổi với Frappe Date).
const errorMessage = computed(
  () =>
    resource.error?.messages?.[0] ||
    resource.error?.message ||
    __('Không tải được cơ hội'),
)
</script>
