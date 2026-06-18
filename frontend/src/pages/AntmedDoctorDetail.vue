<template>
  <main
    class="flex h-full flex-col overflow-auto"
    aria-labelledby="antmed-doctor-detail-title"
  >
    <div class="px-6 pt-4">
      <Button variant="ghost" :label="__('Quay lại')" @click="goBack">
        <template #prefix><FeatherIcon name="arrow-left" class="h-4 w-4" /></template>
      </Button>
    </div>

    <div
      v-if="doctor.loading"
      class="flex items-center justify-center gap-2 py-16 text-ink-gray-6"
      aria-live="polite"
    >
      <LoadingIndicator class="h-4 w-4" />
      <span class="text-p-base">{{ __('Đang tải hồ sơ bác sỹ…') }}</span>
    </div>

    <div
      v-else-if="doctor.error"
      class="flex flex-col items-center gap-3 py-16 text-center"
      role="alert"
    >
      <Badge variant="subtle" theme="red" size="lg" :label="__('Không tải được')" />
      <p class="max-w-md text-p-sm text-ink-gray-6">{{ errorMessage }}</p>
      <Button variant="outline" :label="__('Thử lại')" @click="doctor.reload()" />
    </div>

    <template v-else-if="doctor.data">
      <!-- Header + hành động -->
      <header class="px-6 py-5">
        <h1 id="antmed-doctor-detail-title" class="text-2xl font-semibold text-ink-gray-9">
          {{ doctor.data.full_name || doctor.data.name }}
        </h1>
        <p v-if="doctor.data.specialty" class="mt-1 text-p-base text-ink-gray-6">
          {{ doctor.data.specialty }}
        </p>
        <button
          v-if="doctor.data.hospital"
          type="button"
          class="mt-3 inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-p-sm font-medium text-ink-gray-7 transition hover:bg-surface-gray-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
          :aria-label="__('Mở bệnh viện') + ' ' + (doctor.data.hospital_name || doctor.data.hospital)"
          @click="openHospital"
        >
          <FeatherIcon name="briefcase" class="h-4 w-4 text-ink-gray-5" />
          {{ doctor.data.hospital_name || doctor.data.hospital }}
          <FeatherIcon name="chevron-right" class="h-4 w-4 text-ink-gray-5" />
        </button>

        <div class="mt-4 flex flex-wrap gap-2">
          <Button
            variant="solid"
            :label="__('Gọi')"
            :disabled="!doctor.data.phone"
            :title="doctor.data.phone ? doctor.data.phone : __('Chưa có số điện thoại')"
            @click="startCall"
          >
            <template #prefix><FeatherIcon name="phone" class="h-4 w-4" /></template>
          </Button>
          <Button
            variant="subtle"
            :label="__('Zalo')"
            :disabled="!doctor.data.zalo"
            @click="openZalo"
          >
            <template #prefix><FeatherIcon name="message-circle" class="h-4 w-4" /></template>
          </Button>
          <Button
            variant="subtle"
            :label="__('Check-in')"
            :loading="checkInRes.loading"
            @click="checkIn"
          >
            <template #prefix><FeatherIcon name="map-pin" class="h-4 w-4" /></template>
          </Button>
        </div>
      </header>

      <!-- Tab bar -->
      <div class="border-b border-outline-gray-1 px-6">
        <div class="flex gap-1" role="tablist" :aria-label="__('Hồ sơ CSKH')">
          <button
            v-for="t in tabs"
            :key="t.key"
            type="button"
            role="tab"
            :aria-selected="activeTab === t.key"
            class="-mb-px border-b-2 px-3 py-2 text-p-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
            :class="
              activeTab === t.key
                ? 'border-teal-600 text-teal-800'
                : 'border-transparent text-ink-gray-6 hover:text-ink-gray-8'
            "
            @click="selectTab(t.key)"
          >
            {{ __(t.label) }}
          </button>
        </div>
      </div>

      <section class="flex-1 px-6 py-5">
        <!-- Ghi chú -->
        <AntmedCareList
          v-if="activeTab === 'notes'"
          :resource="careNotes"
          :empty="__('Chưa có ghi chú')"
        >
          <template #row="{ row }">
            <div class="text-p-xs text-ink-gray-5">
              {{ fmtDate(row.note_date) }} · {{ row.category || __('Khác') }}
            </div>
            <div class="mt-0.5 whitespace-pre-line text-p-sm text-ink-gray-8">
              {{ row.content }}
            </div>
          </template>
        </AntmedCareList>

        <!-- Lịch sử (ghé thăm) -->
        <AntmedCareList
          v-else-if="activeTab === 'visits'"
          :resource="visits"
          :empty="__('Chưa có lượt ghé thăm')"
        >
          <template #row="{ row }">
            <div class="text-p-xs text-ink-gray-5">{{ fmtDateTime(row.checked_in_at) }}</div>
            <div class="mt-0.5 text-p-sm font-medium text-ink-gray-8">
              {{ row.status }}<span v-if="row.topic"> · {{ row.topic }}</span>
            </div>
          </template>
        </AntmedCareList>

        <!-- Quà -->
        <AntmedCareList
          v-else-if="activeTab === 'gifts'"
          :resource="gifts"
          :empty="__('Chưa có quà tặng')"
        >
          <template #row="{ row }">
            <div class="text-p-xs text-ink-gray-5">{{ fmtDate(row.gift_date) }}</div>
            <div class="mt-0.5 text-p-sm text-ink-gray-8">
              {{ row.item_or_text }}
              <span v-if="row.value_vnd" class="text-ink-gray-5">
                · {{ Number(row.value_vnd).toLocaleString('vi-VN') }}₫</span
              >
            </div>
          </template>
        </AntmedCareList>

        <!-- Gọi -->
        <div v-else-if="activeTab === 'calls'">
          <div class="mb-3">
            <Button
              variant="solid"
              :label="__('Gọi ngay')"
              :disabled="!doctor.data.phone"
              @click="startCall"
            >
              <template #prefix><FeatherIcon name="phone" class="h-4 w-4" /></template>
            </Button>
          </div>
          <AntmedCareList :resource="callLogs" :empty="__('Chưa có cuộc gọi')">
            <template #row="{ row }">
              <div class="flex items-center gap-2">
                <span
                  class="rounded-full px-2 py-0.5 text-p-xs font-medium"
                  :class="callChipClass(row.status)"
                  >{{ row.outcome }}</span
                >
                <span class="text-p-xs text-ink-gray-5">{{ fmtDateTime(row.start_time) }}</span>
                <span v-if="row.duration" class="text-p-xs text-ink-gray-5"
                  >· {{ fmtDuration(row.duration) }}</span
                >
              </div>
              <div v-if="row.note_text" class="mt-1 text-p-sm text-ink-gray-8">
                {{ row.note_text }}
              </div>
              <div class="mt-0.5 text-p-xs text-ink-gray-5">{{ row.caller_name }}</div>
            </template>
          </AntmedCareList>
        </div>
      </section>
    </template>

    <LogCallModal
      v-model:open="callModalOpen"
      :doctor="props.name"
      :phone="doctor.data?.phone || ''"
      @logged="callLogs.reload()"
    />
  </main>
</template>

<script setup>
import { computed, h, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Badge, Button, FeatherIcon, toast } from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import LogCallModal from '@/components/Antmed/LogCallModal.vue'
import {
  getDoctor,
  listCareNotes,
  listVisits,
  listGifts,
  listCallLogs,
  checkInDoctor,
} from '@/data/antmed'

const props = defineProps({ name: { type: String, required: true } })
const router = useRouter()

const doctor = getDoctor({ params: { name: props.name }, auto: true })

const careNotes = listCareNotes()
const visits = listVisits()
const gifts = listGifts()
const callLogs = listCallLogs()
const checkInRes = checkInDoctor({
  onSuccess() {
    toast.success(__('Đã check-in'))
    if (activeTab.value === 'visits') visits.submit({ doctor: props.name })
  },
  onError(err) {
    toast.error(err?.messages?.[0] || __('Không check-in được'))
  },
})

const tabs = [
  { key: 'notes', label: 'Ghi chú' },
  { key: 'visits', label: 'Lịch sử' },
  { key: 'gifts', label: 'Quà' },
  { key: 'calls', label: 'Gọi' },
]
const activeTab = ref('notes')
const loadedTabs = new Set()
const callModalOpen = ref(false)

const TAB_RESOURCE = { notes: careNotes, visits, gifts, calls: callLogs }

function loadTab(key) {
  if (loadedTabs.has(key)) return
  loadedTabs.add(key)
  TAB_RESOURCE[key].submit({ doctor: props.name })
}
function selectTab(key) {
  activeTab.value = key
  loadTab(key)
}

// Tải tab mặc định + tải lại khi đổi bác sỹ.
watch(
  () => props.name,
  (name) => {
    doctor.submit({ name })
    loadedTabs.clear()
    loadTab(activeTab.value)
  },
  { immediate: true },
)

function startCall() {
  const phone = doctor.data?.phone
  if (!phone) return
  window.open('tel:' + phone, '_self')
  callModalOpen.value = true
}
function openZalo() {
  const z = doctor.data?.zalo
  if (!z) return
  const url = /^https?:\/\//.test(z) ? z : `https://zalo.me/${z}`
  window.open(url, '_blank')
}
function checkIn() {
  checkInRes.submit({ doctor: props.name })
}

function callChipClass(status) {
  if (status === 'Completed') return 'bg-green-100 text-green-700'
  if (status === 'Busy') return 'bg-amber-100 text-amber-700'
  return 'bg-ink-gray-2 text-ink-gray-6'
}
function fmtDuration(sec) {
  const s = Number(sec) || 0
  const m = Math.floor(s / 60)
  const r = s % 60
  return m ? `${m}p${r ? ' ' + r + 's' : ''}` : `${r}s`
}
function fmtDate(d) {
  if (!d) return '—'
  const [y, m, day] = String(d).split(' ')[0].split('-')
  return y && m && day ? `${day}/${m}/${y}` : d
}
function fmtDateTime(d) {
  if (!d) return '—'
  const [date, time] = String(d).split(' ')
  return `${fmtDate(date)}${time ? ' ' + time.slice(0, 5) : ''}`
}

const errorMessage = computed(
  () =>
    doctor.error?.messages?.[0] ||
    doctor.error?.message ||
    __('Không tải được hồ sơ bác sỹ'),
)

function openHospital() {
  if (doctor.data?.hospital)
    router.push({ name: 'AntmedHospitalDetail', params: { name: doctor.data.hospital } })
}
function goBack() {
  if (doctor.data?.hospital)
    router.push({ name: 'AntmedHospitalDetail', params: { name: doctor.data.hospital } })
  else router.push({ name: 'AntmedHospitalList' })
}
doctor.onError = (err) => {
  toast.error(err?.messages?.[0] || __('Không tải được hồ sơ bác sỹ'))
}

// Inline list renderer (loading/error/empty/rows) dùng chung 4 tab.
const AntmedCareList = {
  props: { resource: { type: Object, required: true }, empty: { type: String, default: '' } },
  setup(p, { slots }) {
    return () => {
      const r = p.resource
      if (r.loading)
        return h('div', { class: 'py-8 text-center text-p-sm text-ink-gray-5' }, __('Đang tải…'))
      if (r.error)
        return h('div', { class: 'py-8 text-center text-p-sm text-red-600', role: 'alert' }, __('Lỗi tải dữ liệu'))
      const rows = r.data?.data || []
      if (!rows.length)
        return h('div', { class: 'py-8 text-center text-p-sm text-ink-gray-5' }, p.empty)
      return h(
        'ul',
        { class: 'space-y-3' },
        rows.map((row) =>
          h(
            'li',
            { key: row.name, class: 'rounded-lg border border-outline-gray-1 p-3' },
            slots.row ? slots.row({ row }) : row.name,
          ),
        ),
      )
    }
  },
}
</script>
