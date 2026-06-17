<template>
  <main class="flex h-full flex-col overflow-auto" aria-labelledby="antmed-doctor-detail-title">
    <!-- Điều hướng ngược -->
    <div class="px-6 pt-4">
      <Button variant="ghost" :label="__('Quay lại')" @click="goBack">
        <template #prefix>
          <FeatherIcon name="arrow-left" class="h-4 w-4" />
        </template>
      </Button>
    </div>

    <!-- Loading -->
    <div
      v-if="doctor.loading"
      class="flex items-center justify-center gap-2 py-16 text-ink-gray-6"
      aria-live="polite"
    >
      <LoadingIndicator class="h-4 w-4" />
      <span class="text-p-base">{{ __('Đang tải hồ sơ bác sỹ…') }}</span>
    </div>

    <!-- Error -->
    <div
      v-else-if="doctor.error"
      class="flex flex-col items-center gap-3 py-16 text-center"
      role="alert"
    >
      <Badge variant="subtle" theme="red" size="lg" :label="__('Không tải được')" />
      <p class="max-w-md text-p-sm text-ink-gray-6">{{ errorMessage }}</p>
      <Button variant="outline" :label="__('Thử lại')" @click="doctor.reload()" />
    </div>

    <!-- Data -->
    <template v-else-if="doctor.data">
      <header class="px-6 py-5">
        <h1 id="antmed-doctor-detail-title" class="text-2xl font-semibold text-ink-gray-9">
          {{ doctor.data.full_name || doctor.data.name }}
        </h1>
        <p v-if="doctor.data.specialty" class="mt-1 text-p-base text-ink-gray-6">
          {{ doctor.data.specialty }}
        </p>

        <!-- Link ngược về BV -->
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
      </header>

      <!-- Profile -->
      <section class="px-6 pb-8" aria-labelledby="antmed-doctor-profile-title">
        <h2
          id="antmed-doctor-profile-title"
          class="mb-3 text-base font-semibold text-ink-gray-8"
        >
          {{ __('Thông tin bác sỹ') }}
        </h2>
        <dl class="grid grid-cols-1 gap-x-8 gap-y-4 sm:grid-cols-2">
          <div class="flex flex-col gap-0.5">
            <dt class="text-p-xs uppercase tracking-wide text-ink-gray-5">
              {{ __('Chuyên khoa') }}
            </dt>
            <dd class="text-p-base text-ink-gray-8">{{ doctor.data.specialty || '—' }}</dd>
          </div>
          <div class="flex flex-col gap-0.5">
            <dt class="text-p-xs uppercase tracking-wide text-ink-gray-5">
              {{ __('Sinh nhật') }}
            </dt>
            <dd class="text-p-base text-ink-gray-8">{{ formattedBirthday }}</dd>
          </div>
          <div class="flex flex-col gap-0.5">
            <dt class="text-p-xs uppercase tracking-wide text-ink-gray-5">
              {{ __('Điện thoại') }}
            </dt>
            <dd class="text-p-base text-ink-gray-8">
              <a
                v-if="doctor.data.phone"
                :href="`tel:${doctor.data.phone}`"
                class="text-ink-gray-8 underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
              >
                {{ doctor.data.phone }}
              </a>
              <span v-else>—</span>
            </dd>
          </div>
          <div class="flex flex-col gap-0.5">
            <dt class="text-p-xs uppercase tracking-wide text-ink-gray-5">
              {{ __('Email') }}
            </dt>
            <dd class="text-p-base text-ink-gray-8">
              <a
                v-if="doctor.data.email"
                :href="`mailto:${doctor.data.email}`"
                class="text-ink-gray-8 underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
              >
                {{ doctor.data.email }}
              </a>
              <span v-else>—</span>
            </dd>
          </div>
          <div class="flex flex-col gap-0.5">
            <dt class="text-p-xs uppercase tracking-wide text-ink-gray-5">
              {{ __('Zalo') }}
            </dt>
            <dd class="text-p-base text-ink-gray-8">{{ doctor.data.zalo || '—' }}</dd>
          </div>
          <div class="flex flex-col gap-0.5 sm:col-span-2">
            <dt class="text-p-xs uppercase tracking-wide text-ink-gray-5">
              {{ __('Ghi chú') }}
            </dt>
            <dd class="whitespace-pre-line text-p-base text-ink-gray-8">
              {{ doctor.data.notes || '—' }}
            </dd>
          </div>
        </dl>
      </section>
    </template>
  </main>
</template>

<script setup>
import { computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Badge, Button, FeatherIcon, toast } from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import { getDoctor } from '@/data/antmed'

const props = defineProps({
  name: { type: String, required: true },
})

const router = useRouter()

const doctor = getDoctor({
  params: { name: props.name },
  auto: true,
})

watch(
  () => props.name,
  (name) => doctor.submit({ name }),
)

const errorMessage = computed(
  () =>
    doctor.error?.messages?.[0] ||
    doctor.error?.message ||
    __('Không tải được hồ sơ bác sỹ'),
)

const formattedBirthday = computed(() => {
  const b = doctor.data?.birthday
  if (!b) return '—'
  // birthday dạng ISO 'YYYY-MM-DD' → hiển thị DD/MM/YYYY (chuẩn VN).
  const [y, m, d] = String(b).split('-')
  if (y && m && d) return `${d}/${m}/${y}`
  return b
})

function openHospital() {
  if (doctor.data?.hospital) {
    router.push({
      name: 'AntmedHospitalDetail',
      params: { name: doctor.data.hospital },
    })
  }
}

function goBack() {
  // Ưu tiên về BV của bác sỹ; nếu không có thì về danh sách BV.
  if (doctor.data?.hospital) {
    router.push({
      name: 'AntmedHospitalDetail',
      params: { name: doctor.data.hospital },
    })
  } else {
    router.push({ name: 'AntmedHospitalList' })
  }
}

doctor.onError = (err) => {
  toast.error(err?.messages?.[0] || __('Không tải được hồ sơ bác sỹ'))
}
</script>
