<template>
  <main class="flex h-full flex-col overflow-auto" aria-labelledby="antmed-hospital-detail-title">
    <!-- Thanh điều hướng ngược -->
    <div class="px-6 pt-4">
      <Button
        variant="ghost"
        :label="__('Quay lại danh sách bệnh viện')"
        @click="goBack"
      >
        <template #prefix>
          <FeatherIcon name="arrow-left" class="h-4 w-4" />
        </template>
      </Button>
    </div>

    <!-- Loading -->
    <div
      v-if="hospital.loading"
      class="flex items-center justify-center gap-2 py-16 text-ink-gray-6"
      aria-live="polite"
    >
      <LoadingIndicator class="h-4 w-4" />
      <span class="text-p-base">{{ __('Đang tải hồ sơ bệnh viện…') }}</span>
    </div>

    <!-- Error -->
    <div
      v-else-if="hospital.error"
      class="flex flex-col items-center gap-3 py-16 text-center"
      role="alert"
    >
      <Badge variant="subtle" theme="red" size="lg" :label="__('Không tải được')" />
      <p class="max-w-md text-p-sm text-ink-gray-6">{{ errorMessage }}</p>
      <Button variant="outline" :label="__('Thử lại')" @click="hospital.reload()" />
    </div>

    <!-- Data -->
    <template v-else-if="hospital.data">
      <!-- Header 360 -->
      <header class="px-6 py-5">
        <div class="flex flex-wrap items-center gap-3">
          <h1
            id="antmed-hospital-detail-title"
            class="text-2xl font-semibold text-ink-gray-9"
          >
            {{ hospital.data.hospital_name || hospital.data.name }}
          </h1>
          <Badge
            v-if="hospital.data.rank"
            variant="subtle"
            size="md"
            :theme="rankTheme(hospital.data.rank)"
            :label="hospital.data.rank"
          />
          <Badge
            v-if="hospital.data.contract_status"
            variant="subtle"
            size="md"
            :theme="contractTheme(hospital.data.contract_status)"
            :label="hospital.data.contract_status"
          />
        </div>

        <dl class="mt-4 grid grid-cols-1 gap-x-8 gap-y-3 sm:grid-cols-2 lg:grid-cols-3">
          <div class="flex flex-col gap-0.5">
            <dt class="text-p-xs uppercase tracking-wide text-ink-gray-5">
              {{ __('Mã bệnh viện') }}
            </dt>
            <dd class="text-p-base text-ink-gray-8">
              {{ hospital.data.hospital_code || hospital.data.name }}
            </dd>
          </div>
          <div class="flex flex-col gap-0.5">
            <dt class="text-p-xs uppercase tracking-wide text-ink-gray-5">
              {{ __('Mã số thuế') }}
            </dt>
            <dd class="text-p-base text-ink-gray-8">{{ hospital.data.tax_code || '—' }}</dd>
          </div>
          <div class="flex flex-col gap-0.5 sm:col-span-2 lg:col-span-1">
            <dt class="text-p-xs uppercase tracking-wide text-ink-gray-5">
              {{ __('Địa chỉ') }}
            </dt>
            <dd class="text-p-base text-ink-gray-8">{{ hospital.data.address || '—' }}</dd>
          </div>
        </dl>
      </header>

      <!-- Section bác sỹ thuộc BV -->
      <section class="px-6 pb-8" aria-labelledby="antmed-hospital-doctors-title">
        <h2
          id="antmed-hospital-doctors-title"
          class="mb-3 text-base font-semibold text-ink-gray-8"
        >
          {{ __('Bác sỹ thuộc bệnh viện') }}
          <span class="text-ink-gray-5">({{ doctors.length }})</span>
        </h2>

        <div
          v-if="!doctors.length"
          class="rounded-xl bg-surface-gray-1 px-4 py-8 text-center text-p-sm text-ink-gray-6"
        >
          {{ __('Chưa có bác sỹ nào được gắn với bệnh viện này.') }}
        </div>

        <ul v-else class="flex flex-col gap-2">
          <li v-for="doc in doctors" :key="doc.name">
            <button
              type="button"
              class="flex w-full items-center justify-between gap-3 rounded-xl border border-outline-gray-1 bg-surface-white px-4 py-3 text-left transition hover:bg-surface-gray-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
              :aria-label="__('Xem hồ sơ bác sỹ') + ' ' + (doc.full_name || doc.name)"
              @click="openDoctor(doc.name)"
            >
              <span class="flex flex-col gap-0.5">
                <span class="text-p-base font-medium text-ink-gray-9">
                  {{ doc.full_name || doc.name }}
                </span>
                <span class="text-p-sm text-ink-gray-6">
                  {{ doc.specialty || __('Chưa rõ chuyên khoa') }}
                </span>
              </span>
              <span class="flex items-center gap-3">
                <span v-if="doc.phone" class="text-p-sm text-ink-gray-6">{{ doc.phone }}</span>
                <FeatherIcon name="chevron-right" class="h-4 w-4 text-ink-gray-5" />
              </span>
            </button>
          </li>
        </ul>
      </section>
    </template>
  </main>
</template>

<script setup>
import { computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Badge, Button, FeatherIcon, toast } from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import { getHospital, RANK_THEME, CONTRACT_STATUS_THEME } from '@/data/antmed'

const props = defineProps({
  name: { type: String, required: true },
})

const router = useRouter()

const hospital = getHospital({
  params: { name: props.name },
  auto: true,
})

// Re-fetch khi điều hướng giữa các BV (component được tái dùng theo :name).
watch(
  () => props.name,
  (name) => hospital.submit({ name }),
)

const doctors = computed(() => hospital.data?.doctors || [])

const errorMessage = computed(
  () =>
    hospital.error?.messages?.[0] ||
    hospital.error?.message ||
    __('Không tải được hồ sơ bệnh viện'),
)

function rankTheme(rank) {
  return RANK_THEME[rank] || 'gray'
}
function contractTheme(status) {
  return CONTRACT_STATUS_THEME[status] || 'gray'
}

function openDoctor(name) {
  router.push({ name: 'AntmedDoctorDetail', params: { name } })
}

function goBack() {
  router.push({ name: 'AntmedHospitalList' })
}

hospital.onError = (err) => {
  toast.error(err?.messages?.[0] || __('Không tải được hồ sơ bệnh viện'))
}
</script>
