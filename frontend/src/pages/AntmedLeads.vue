<template>
  <main class="flex h-full flex-col" aria-labelledby="antmed-leads-title">
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
        <span class="text-ink-gray-7" aria-current="page">{{
          __('Khách hàng tiềm năng (Lead)')
        }}</span>
      </nav>
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1
            id="antmed-leads-title"
            class="text-xl font-semibold text-ink-gray-9"
          >
            🧲 {{ __('Quản lý Lead') }}
          </h1>
          <p class="text-p-sm text-ink-gray-6">
            {{
              __(
                'Khách hàng tiềm năng — kế thừa CRM Lead, lọc theo tuyến phụ trách của bạn',
              )
            }}
          </p>
        </div>
        <Button
          variant="solid"
          theme="teal"
          :label="__('+ Tạo lead')"
          @click="openCreate"
        />
      </div>
    </header>

    <!-- Phễu Pipeline gói thầu (Lead → Khảo sát → Báo giá → Dự thầu → Trúng) -->
    <section
      class="border-b border-outline-gray-1 px-6 py-4"
      aria-labelledby="antmed-funnel-title"
    >
      <div class="mb-2 flex items-center justify-between">
        <h2
          id="antmed-funnel-title"
          class="text-p-sm font-medium text-ink-gray-7"
        >
          {{ __('Pipeline gói thầu') }}
        </h2>
        <button
          v-if="funnel.error"
          type="button"
          class="rounded text-p-xs text-teal-700 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
          @click="funnel.reload()"
        >
          {{ __('Thử lại') }}
        </button>
      </div>

      <div
        v-if="funnel.loading"
        class="flex items-center gap-2 py-2 text-p-sm text-ink-gray-5"
      >
        <LoadingIndicator class="h-4 w-4" /><span>{{
          __('Đang tải phễu…')
        }}</span>
      </div>
      <p
        v-else-if="funnel.error"
        class="py-2 text-p-sm text-ink-gray-5"
        role="alert"
      >
        {{ __('Không tải được phễu pipeline.') }}
      </p>
      <ol
        v-else-if="funnelStages.length"
        class="flex flex-col gap-1.5 sm:flex-row sm:items-stretch sm:gap-2"
        :aria-label="__('Các giai đoạn pipeline')"
      >
        <li v-for="(s, i) in funnelStages" :key="s.key" class="flex-1">
          <div
            class="flex h-full flex-col justify-between rounded-md px-3 py-2.5 shadow-sm transition-[width]"
            :class="funnelBarClass(i)"
            :style="{
              width: '100%',
              minWidth: funnelBarWidth(s.count, funnelMax) + '%',
            }"
          >
            <span
              class="text-p-xs font-medium uppercase tracking-wide opacity-90"
              >{{ s.label }}</span
            >
            <span class="text-lg font-semibold tabular-nums">{{
              s.count
            }}</span>
          </div>
        </li>
      </ol>
      <p v-else class="py-2 text-p-sm text-ink-gray-5">
        {{ __('Chưa có dữ liệu pipeline.') }}
      </p>
    </section>

    <!-- Filter trạng thái -->
    <section
      class="flex flex-wrap items-center gap-1.5 border-b border-outline-gray-1 px-6 py-2.5"
    >
      <button
        type="button"
        class="rounded-full px-3 py-1 text-p-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
        :class="
          !statusFilter
            ? 'bg-teal-700 text-white'
            : 'bg-surface-gray-2 text-ink-gray-7 hover:bg-surface-gray-3'
        "
        @click="setStatus('')"
      >
        {{ __('Tất cả') }}
      </button>
      <button
        v-for="s in statusOptions"
        :key="s"
        type="button"
        class="rounded-full px-3 py-1 text-p-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
        :class="
          statusFilter === s
            ? 'bg-teal-700 text-white'
            : 'bg-surface-gray-2 text-ink-gray-7 hover:bg-surface-gray-3'
        "
        @click="setStatus(s)"
      >
        {{ s }}
      </button>
    </section>

    <section class="flex-1 overflow-auto px-6 pb-6 pt-4" aria-live="polite">
      <div
        v-if="leads.loading"
        class="flex items-center justify-center gap-2 py-16 text-ink-gray-6"
      >
        <LoadingIndicator class="h-4 w-4" /><span>{{ __('Đang tải…') }}</span>
      </div>
      <div
        v-else-if="leads.error"
        class="flex flex-col items-center gap-3 py-16 text-center"
        role="alert"
      >
        <Badge
          variant="subtle"
          theme="red"
          size="lg"
          :label="__('Không tải được')"
        />
        <Button
          variant="outline"
          :label="__('Thử lại')"
          @click="leads.reload()"
        />
      </div>
      <div
        v-else-if="!rows.length"
        class="py-16 text-center text-p-sm text-ink-gray-6"
      >
        {{ __('Chưa có lead nào trong phạm vi của bạn.') }}
      </div>

      <table v-else class="w-full border-separate border-spacing-0 text-left">
        <thead>
          <tr class="text-p-xs uppercase text-ink-gray-5">
            <th
              class="border-b border-outline-gray-modals py-2 pr-4 font-medium"
            >
              {{ __('Lead / Tổ chức') }}
            </th>
            <th
              class="border-b border-outline-gray-modals py-2 pr-4 font-medium"
            >
              {{ __('Trạng thái') }}
            </th>
            <th
              class="border-b border-outline-gray-modals py-2 pr-4 font-medium"
            >
              {{ __('Tuyến') }}
            </th>
            <th
              class="border-b border-outline-gray-modals py-2 pr-4 font-medium"
            >
              {{ __('NV phụ trách') }}
            </th>
            <th
              class="border-b border-outline-gray-modals py-2 pr-4 font-medium"
            >
              {{ __('Liên hệ') }}
            </th>
            <th
              class="border-b border-outline-gray-modals py-2 text-right font-medium"
            >
              {{ __('Doanh thu năm') }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="l in rows"
            :key="l.name"
            class="cursor-pointer text-p-sm text-ink-gray-8 transition-colors hover:bg-surface-gray-1 focus-within:bg-surface-gray-1"
            role="button"
            tabindex="0"
            :aria-label="__('Xem chi tiết lead {0}', [l.lead_name])"
            @click="openDetail(l.name)"
            @keydown.enter="openDetail(l.name)"
            @keydown.space.prevent="openDetail(l.name)"
          >
            <td class="border-b border-outline-gray-1 py-2.5 pr-4">
              <div class="font-medium text-ink-gray-9">{{ l.lead_name }}</div>
              <div class="text-p-xs text-ink-gray-5">
                {{ l.organization || '—' }}
              </div>
            </td>
            <td class="border-b border-outline-gray-1 py-2.5 pr-4">
              <Badge
                variant="subtle"
                :theme="statusTheme(l.status)"
                size="sm"
                :label="l.status || '—'"
              />
            </td>
            <td
              class="border-b border-outline-gray-1 py-2.5 pr-4 text-ink-gray-7"
            >
              {{ l.territory || '—' }}
            </td>
            <td
              class="border-b border-outline-gray-1 py-2.5 pr-4 text-ink-gray-7"
            >
              {{ l.lead_owner_name || '—' }}
            </td>
            <td
              class="border-b border-outline-gray-1 py-2.5 pr-4 text-ink-gray-7"
            >
              <div>{{ l.mobile_no || '—' }}</div>
              <div class="text-p-xs text-ink-gray-5">
                {{ l.email_id || '' }}
              </div>
            </td>
            <td
              class="border-b border-outline-gray-1 py-2.5 text-right tabular-nums text-ink-gray-8"
            >
              {{ l.annual_revenue ? formatVnMoney(l.annual_revenue) : '—' }}
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="rows.length" class="pt-3 text-p-sm text-ink-gray-5">
        {{ __('Tổng cộng') }}: {{ leads.data?.total_count }} {{ __('lead') }}
      </p>
    </section>

    <!-- Dialog tạo lead -->
    <Dialog
      v-model="createDlg"
      :options="{ title: __('Tạo lead mới'), size: 'xl' }"
    >
      <template #body-content>
        <div class="bg-surface-modal px-4 pb-6 pt-5 sm:px-6">
          <div class="flex flex-col gap-5">
            <!-- Nhóm: Người liên hệ -->
            <fieldset class="flex flex-col gap-3">
              <legend
                class="mb-1 text-p-xs font-semibold uppercase tracking-wide text-ink-gray-5"
              >
                {{ __('Người liên hệ') }}
              </legend>
              <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <FormControl
                  v-model="cForm.lead_name"
                  :label="__('Tên lead') + ' *'"
                  :placeholder="__('Nguyễn Văn A')"
                  required
                />
                <FormControl
                  v-model="cForm.job_title"
                  :label="__('Chức danh')"
                  :placeholder="__('VD: Trưởng khoa')"
                />
                <FormControl
                  v-model="cForm.mobile_no"
                  :label="__('Di động')"
                  :placeholder="__('09xx xxx xxx')"
                />
                <FormControl
                  v-model="cForm.phone"
                  :label="__('Điện thoại cố định')"
                />
                <FormControl
                  v-model="cForm.email"
                  type="email"
                  :label="__('Email')"
                  :placeholder="__('ten@benhvien.vn')"
                />
              </div>
            </fieldset>

            <!-- Nhóm: Tổ chức & phân loại -->
            <fieldset
              class="flex flex-col gap-3 border-t border-outline-gray-1 pt-4"
            >
              <legend
                class="mb-1 text-p-xs font-semibold uppercase tracking-wide text-ink-gray-5"
              >
                {{ __('Tổ chức & phân loại') }}
              </legend>
              <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <FormControl
                  v-model="cForm.organization"
                  :label="__('Tổ chức / Bệnh viện')"
                />
                <FormControl
                  v-model="cForm.website"
                  :label="__('Website')"
                  :placeholder="__('https://...')"
                />
                <FormControl
                  v-model="cForm.source"
                  type="select"
                  :label="__('Nguồn')"
                  :options="sourceOptions"
                />
                <FormControl
                  v-model="cForm.territory"
                  type="select"
                  :label="__('Khu vực / Tuyến')"
                  :options="territoryOptions"
                />
                <FormControl
                  v-model="cForm.status"
                  type="select"
                  :label="__('Trạng thái')"
                  :options="statusOptions.map((s) => ({ label: s, value: s }))"
                />
              </div>
            </fieldset>
          </div>
          <div
            class="mt-6 flex justify-end gap-2 border-t border-outline-gray-1 pt-4"
          >
            <Button :label="__('Huỷ')" @click="createDlg = false" />
            <Button
              variant="solid"
              theme="teal"
              :loading="createRes.loading"
              :label="__('Tạo lead')"
              @click="onCreate"
            />
          </div>
        </div>
      </template>
    </Dialog>

    <!-- Drawer chi tiết Lead -->
    <Dialog
      v-model="detailDlg"
      :options="{ title: __('Chi tiết Lead'), size: 'lg' }"
    >
      <template #body-content>
        <div class="bg-surface-modal px-4 pb-6 pt-5 sm:px-6">
          <div
            v-if="detail.loading"
            class="flex items-center justify-center gap-2 py-12 text-ink-gray-6"
          >
            <LoadingIndicator class="h-4 w-4" /><span>{{
              __('Đang tải…')
            }}</span>
          </div>
          <div
            v-else-if="detail.error"
            class="flex flex-col items-center gap-3 py-12 text-center"
            role="alert"
          >
            <Badge
              variant="subtle"
              theme="red"
              size="lg"
              :label="__('Không tải được lead')"
            />
            <Button
              variant="outline"
              :label="__('Thử lại')"
              @click="detail.reload()"
            />
          </div>
          <div v-else-if="lead" class="flex flex-col gap-4">
            <div>
              <div class="text-lg font-semibold text-ink-gray-9">
                {{ lead.lead_name || '—' }}
              </div>
              <div class="text-p-sm text-ink-gray-6">
                {{ lead.organization || __('Chưa có tổ chức') }}
              </div>
            </div>

            <dl class="grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2">
              <div>
                <dt class="text-p-xs uppercase text-ink-gray-5">
                  {{ __('Trạng thái') }}
                </dt>
                <dd class="mt-0.5">
                  <Badge
                    variant="subtle"
                    :theme="statusTheme(lead.status)"
                    size="sm"
                    :label="lead.status || '—'"
                  />
                </dd>
              </div>
              <div>
                <dt class="text-p-xs uppercase text-ink-gray-5">
                  {{ __('Tuyến') }}
                </dt>
                <dd class="mt-0.5 text-p-sm text-ink-gray-8">
                  {{ lead.territory || '—' }}
                </dd>
              </div>
              <div>
                <dt class="text-p-xs uppercase text-ink-gray-5">
                  {{ __('NV phụ trách') }}
                </dt>
                <dd class="mt-0.5 text-p-sm text-ink-gray-8">
                  {{ lead.lead_owner_name || '—' }}
                </dd>
              </div>
              <div>
                <dt class="text-p-xs uppercase text-ink-gray-5">
                  {{ __('Doanh thu năm') }}
                </dt>
                <dd class="mt-0.5 text-p-sm tabular-nums text-ink-gray-8">
                  {{
                    lead.annual_revenue
                      ? formatVnMoney(lead.annual_revenue)
                      : '—'
                  }}
                </dd>
              </div>
              <div>
                <dt class="text-p-xs uppercase text-ink-gray-5">
                  {{ __('Liên hệ') }}
                </dt>
                <dd class="mt-0.5 text-p-sm text-ink-gray-8">
                  <div>{{ lead.mobile_no || '—' }}</div>
                  <div class="text-p-xs text-ink-gray-5">
                    {{ lead.email_id || '' }}
                  </div>
                </dd>
              </div>
              <div>
                <dt class="text-p-xs uppercase text-ink-gray-5">
                  {{ __('Nguồn') }}
                </dt>
                <dd class="mt-0.5 text-p-sm text-ink-gray-8">
                  {{ lead.source || '—' }}
                </dd>
              </div>
            </dl>

            <!-- Đã qualify → badge gói thầu; chưa → nút qualify -->
            <div class="border-t border-outline-gray-1 pt-4">
              <div v-if="lead.tender" class="flex flex-wrap items-center gap-2">
                <Badge
                  variant="subtle"
                  theme="green"
                  size="lg"
                  :label="__('Đã tạo gói thầu')"
                />
                <RouterLink
                  :to="`/antmed/tenders/${encodeURIComponent(lead.tender)}`"
                  class="rounded text-p-sm font-medium text-teal-700 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
                >
                  {{ lead.tender }} →
                </RouterLink>
              </div>
              <div v-else class="flex flex-col gap-3">
                <p class="text-p-sm text-ink-gray-6">
                  {{ __('Lead chưa được qualify thành gói thầu.') }}
                </p>
                <div class="flex flex-wrap items-end gap-3">
                  <FormControl
                    v-model="estimatedValue"
                    type="number"
                    class="w-48"
                    :label="__('Giá trị dự kiến (VNĐ)')"
                    :placeholder="__('Không bắt buộc')"
                  />
                  <Button
                    variant="solid"
                    theme="teal"
                    :loading="convertRes.loading"
                    :label="__('Qualify → Tạo gói thầu')"
                    @click="onQualify"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </Dialog>
  </main>
</template>

<script setup>
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import {
  Badge,
  Button,
  Dialog,
  FormControl,
  createResource,
  toast,
} from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import {
  listLeads,
  getLeadStatuses,
  getLeadFunnel,
  getLead,
  convertLeadToTender,
  LEAD_STATUS_THEME,
} from '@/data/antmed'
import { formatVnMoney, funnelBarWidth, funnelBarClass } from '@/utils/antmedUi'

const PIPE = 'antmed_crm.api.antmed.pipeline'

const statusFilter = ref('')
const leads = listLeads({ params: { page_length: 0 }, auto: true })
leads.onError = (err) =>
  toast.error(err?.messages?.[0] || __('Không tải được danh sách lead'))
const statusesRes = getLeadStatuses({ auto: true })

// Option form tạo lead: nguồn (CRM Lead Source) + khu vực (CRM Territory) — endpoint riêng.
const formOptions = createResource({
  url: `${PIPE}.lead_form_options`,
  method: 'GET',
  auto: true,
})
const sourceOptions = computed(() => [
  { label: __('— Không chọn —'), value: '' },
  ...(formOptions.data?.sources || []).map((s) => ({ label: s, value: s })),
])
const territoryOptions = computed(() => [
  { label: __('— Không chọn —'), value: '' },
  ...(formOptions.data?.territories || []).map((t) => ({ label: t, value: t })),
])

// Phễu pipeline (header)
const funnel = getLeadFunnel({
  auto: true,
  onError: (err) =>
    toast.error(err?.messages?.[0] || __('Không tải được phễu pipeline')),
})
const funnelStages = computed(() => funnel.data?.stages || [])
const funnelMax = computed(() =>
  funnelStages.value.reduce((m, s) => Math.max(m, Number(s.count) || 0), 0),
)

const rows = computed(() => leads.data?.data || [])
const statusOptions = computed(() => statusesRes.data?.statuses || [])

function statusTheme(s) {
  return LEAD_STATUS_THEME[s] || 'gray'
}
function setStatus(s) {
  statusFilter.value = s
  // "Tất cả" (s rỗng) → BỎ HẲN key status (KHÔNG gửi status:undefined → GET serialize thành
  // chuỗi "undefined" → BE lọc status="undefined" → 0 lead). Có status mới gửi.
  leads.params = s ? { status: s, page_length: 0 } : { page_length: 0 }
  leads.reload()
}

// Chi tiết lead (drawer) + qualify
const detailDlg = ref(false)
const estimatedValue = ref('')
const detail = getLead({
  onError: (err) =>
    toast.error(err?.messages?.[0] || __('Không tải được lead')),
})
const lead = computed(() => detail.data || null)

const convertRes = convertLeadToTender({
  onSuccess(data) {
    toast.success(
      data?.created ? __('Đã tạo gói thầu mới') : __('Lead đã có gói thầu'),
    )
    estimatedValue.value = ''
    // Làm mới: chi tiết lead (hiện tender) + phễu + danh sách.
    if (detail.params?.name) detail.reload()
    funnel.reload()
    leads.reload()
  },
  onError: (err) =>
    toast.error(err?.messages?.[0] || __('Không tạo được gói thầu')),
})

function openDetail(name) {
  estimatedValue.value = ''
  detailDlg.value = true
  detail.submit({ name })
}
function onQualify() {
  if (!lead.value?.name) return
  const payload = { name: lead.value.name }
  const ev = Number(estimatedValue.value)
  if (estimatedValue.value !== '' && Number.isFinite(ev) && ev > 0) {
    payload.estimated_value = ev
  }
  convertRes.submit(payload)
}

// Tạo lead
const createDlg = ref(false)
const emptyLead = () => ({
  lead_name: '',
  organization: '',
  job_title: '',
  mobile_no: '',
  phone: '',
  email: '',
  website: '',
  source: '',
  territory: '',
  status: statusOptions.value.includes('New')
    ? 'New'
    : statusOptions.value[0] || 'New',
})
const cForm = ref(emptyLead())
const createRes = createResource({
  url: `${PIPE}.create_lead`,
  method: 'POST',
  onSuccess() {
    toast.success(__('Đã tạo lead mới'))
    createDlg.value = false
    leads.reload()
    funnel.reload()
  },
  onError: (err) =>
    toast.error(err?.messages?.[0] || __('Không tạo được lead')),
})
function openCreate() {
  cForm.value = emptyLead()
  createDlg.value = true
}
function onCreate() {
  if (!cForm.value.lead_name) {
    toast.error(__('Nhập tên lead'))
    return
  }
  createRes.submit({ ...cForm.value })
}
</script>
