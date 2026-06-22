<template>
  <main class="flex h-full flex-col" aria-labelledby="antmed-tender-title">
    <header class="flex flex-col gap-2 border-b border-outline-gray-modals px-6 py-4">
      <nav class="text-p-xs text-ink-gray-5" :aria-label="__('Đường dẫn')">
        <RouterLink to="/antmed" class="rounded text-ink-gray-6 hover:text-ink-gray-8">{{ __('Trang chủ') }}</RouterLink>
        <span class="px-1.5 text-ink-gray-4" aria-hidden="true">›</span>
        <RouterLink to="/antmed/tenders" class="rounded text-ink-gray-6 hover:text-ink-gray-8">{{ __('Pipeline gói thầu') }}</RouterLink>
        <span class="px-1.5 text-ink-gray-4" aria-hidden="true">›</span>
        <span class="text-ink-gray-7" aria-current="page">{{ d.tender_no || name }}</span>
      </nav>
      <div class="flex flex-wrap items-center gap-3">
        <h1 id="antmed-tender-title" class="text-xl font-semibold text-ink-gray-9">🎯 {{ d.tender_no || name }}</h1>
        <Badge v-if="d.status" variant="subtle" :theme="stageTheme(d.status)" size="md" :label="d.status" />
        <Badge v-if="d.win_probability_pct != null" variant="subtle" theme="blue" size="md" :label="d.win_probability_pct + '%'" />
      </div>
    </header>

    <section class="flex-1 overflow-auto px-6 pb-8 pt-5" aria-live="polite">
      <div v-if="resource.loading" class="flex items-center justify-center gap-2 py-16 text-ink-gray-6">
        <LoadingIndicator class="h-4 w-4" /><span>{{ __('Đang tải…') }}</span>
      </div>
      <div v-else-if="resource.error" class="flex flex-col items-center gap-3 py-16 text-center" role="alert">
        <Badge variant="subtle" theme="red" size="lg" :label="__('Không tải được gói thầu')" />
        <p class="max-w-md text-p-sm text-ink-gray-6">{{ errorMessage }}</p>
        <Button variant="outline" :label="__('Thử lại')" @click="resource.reload()" />
      </div>

      <div v-else class="mx-auto max-w-3xl">
        <h2 class="text-lg font-semibold text-ink-gray-9">{{ d.tender_name }}</h2>

        <dl class="mt-4 grid grid-cols-1 gap-x-8 gap-y-4 rounded-xl border border-outline-gray-2 bg-surface-white p-5 sm:grid-cols-2">
          <div>
            <dt class="text-p-xs uppercase text-ink-gray-5">{{ __('Bệnh viện') }}</dt>
            <dd class="text-p-base text-ink-gray-9">{{ d.hospital_name || d.hospital || '—' }}</dd>
          </div>
          <div>
            <dt class="text-p-xs uppercase text-ink-gray-5">{{ __('Nguồn') }}</dt>
            <dd class="text-p-base text-ink-gray-9">{{ d.source || '—' }}</dd>
          </div>
          <div>
            <dt class="text-p-xs uppercase text-ink-gray-5">{{ __('Giá trị ước tính') }}</dt>
            <dd class="text-p-base font-semibold text-ink-gray-9">{{ d.estimated_value ? formatVnMoney(d.estimated_value) + ' ₫' : '—' }}</dd>
          </div>
          <div>
            <dt class="text-p-xs uppercase text-ink-gray-5">{{ __('Xác suất thắng') }}</dt>
            <dd class="text-p-base text-ink-gray-9">{{ d.win_probability_pct != null ? d.win_probability_pct + '%' : '—' }}</dd>
          </div>
          <div>
            <dt class="text-p-xs uppercase text-ink-gray-5">{{ __('Mở thầu') }}</dt>
            <dd class="text-p-base text-ink-gray-9">{{ fmtDate(d.bid_open_date) }}</dd>
          </div>
          <div>
            <dt class="text-p-xs uppercase text-ink-gray-5">{{ __('Đóng thầu') }}</dt>
            <dd class="text-p-base text-ink-gray-9">{{ fmtDate(d.bid_close_date) }}</dd>
          </div>
          <div v-if="d.result">
            <dt class="text-p-xs uppercase text-ink-gray-5">{{ __('Kết quả') }}</dt>
            <dd><Badge variant="subtle" :theme="d.result === 'Trúng' ? 'green' : 'red'" size="sm" :label="d.result" /></dd>
          </div>
          <div v-if="d.decision_no">
            <dt class="text-p-xs uppercase text-ink-gray-5">{{ __('Số quyết định KQLCNT') }}</dt>
            <dd class="text-p-base font-medium text-green-700">{{ d.decision_no }}</dd>
          </div>
        </dl>

        <!-- Liên kết: Hợp đồng trúng thầu + Deal (CRM Deal) -->
        <div class="mt-5 rounded-xl border border-outline-gray-2 bg-surface-white p-5">
          <h3 class="mb-3 text-p-base font-semibold text-ink-gray-8">{{ __('Liên kết') }}</h3>
          <div class="flex flex-col gap-2">
            <div class="flex items-center justify-between gap-2">
              <span class="text-p-sm text-ink-gray-6">{{ __('Hợp đồng trúng thầu') }}</span>
              <RouterLink
                v-if="d.won_contract"
                :to="`/antmed/contracts/${encodeURIComponent(d.won_contract)}`"
                class="rounded text-p-sm font-medium text-teal-700 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
              >
                {{ d.won_contract }} →
              </RouterLink>
              <span v-else class="text-p-sm text-ink-gray-4">{{ __('Chưa có') }}</span>
            </div>
            <div class="flex items-center justify-between gap-2">
              <span class="text-p-sm text-ink-gray-6">{{ __('Cơ hội (CRM Deal)') }}</span>
              <span v-if="d.deal" class="text-p-sm font-medium text-ink-gray-8">{{ d.deal }}</span>
              <span v-else class="text-p-sm text-ink-gray-4">{{ __('Chưa gắn deal') }}</span>
            </div>
          </div>
        </div>

        <!-- Hành động: chốt kết quả khi đang Dự thầu -->
        <div v-if="d.status === 'Dự thầu'" class="mt-5 flex flex-wrap items-center gap-3">
          <Button variant="solid" theme="teal" :label="__('Chốt kết quả thầu')" @click="resultDlg = true" />
          <span class="text-p-xs text-ink-gray-5">{{ __('Trúng (kèm số QĐ → tự tạo HĐ nháp) hoặc Trượt') }}</span>
        </div>
      </div>
    </section>

    <!-- Dialog chốt kết quả -->
    <Dialog v-model="resultDlg" :options="{ title: __('Chốt kết quả: {0}', [d.tender_no]) }">
      <template #body-content>
        <div class="bg-surface-modal px-4 pb-6 pt-5 sm:px-6">
          <div class="flex flex-col gap-3">
            <label class="flex items-center gap-2 text-p-base">
              <input type="radio" value="Trúng" v-model="rResult" /> <Badge variant="subtle" theme="green" size="sm" :label="__('Trúng')" />
            </label>
            <label class="flex items-center gap-2 text-p-base">
              <input type="radio" value="Trượt" v-model="rResult" /> <Badge variant="subtle" theme="red" size="sm" :label="__('Trượt')" />
            </label>
            <FormControl v-if="rResult === 'Trúng'" :label="__('Số quyết định KQLCNT')" v-model="rDecision" placeholder="QĐ-2026-…" />
          </div>
          <div class="mt-6 flex justify-end gap-2 border-t border-outline-gray-1 pt-4">
            <Button :label="__('Huỷ')" @click="resultDlg = false" />
            <Button variant="solid" theme="teal" :loading="resultRes.loading" :label="__('Xác nhận')" @click="onResult" />
          </div>
        </div>
      </template>
    </Dialog>
  </main>
</template>

<script setup>
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { Badge, Button, Dialog, FormControl, createResource, toast } from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import { getTender, TENDER_STAGE_THEME } from '@/data/antmed'
import { formatVnMoney, fmtDate } from '@/utils/antmedUi'

const props = defineProps({ name: { type: String, required: true } })

const resource = getTender({ params: { name: props.name }, auto: true })
resource.onError = (err) => toast.error(err?.messages?.[0] || __('Không tải được gói thầu'))

const d = computed(() => resource.data || {})

function stageTheme(s) {
  return TENDER_STAGE_THEME[s] || 'gray'
}
// fmtDate (dd/MM/yyyy) gom về canon @/utils/antmedUi (output không đổi với Frappe Date).
const errorMessage = computed(
  () => resource.error?.messages?.[0] || resource.error?.message || __('Không tải được gói thầu'),
)

// Chốt kết quả (từ trang chi tiết)
const resultDlg = ref(false)
const rResult = ref('Trúng')
const rDecision = ref('')
const resultRes = createResource({
  url: 'antmed_crm.api.antmed.pipeline.set_tender_result',
  method: 'POST',
  onSuccess() {
    toast.success(__('Đã chốt kết quả gói thầu'))
    resultDlg.value = false
    resource.reload()
  },
  onError: (err) => toast.error(err?.messages?.[0] || __('Không chốt được kết quả')),
})
function onResult() {
  resultRes.submit({ name: props.name, result: rResult.value, decision_no: rDecision.value || undefined })
}
</script>
