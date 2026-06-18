<template>
  <main class="flex h-full flex-col" aria-labelledby="antmed-hospitals-title">
    <!-- Header -->
    <header
      class="flex flex-col gap-3 border-b border-outline-gray-modals px-6 py-4 sm:flex-row sm:items-center sm:justify-between"
    >
      <div class="flex flex-col gap-1">
        <h1 id="antmed-hospitals-title" class="text-xl font-semibold text-ink-gray-9">
          {{ __('Bệnh viện') }}
        </h1>
        <p class="text-p-sm text-ink-gray-6">
          {{ __('Danh mục khách hàng bệnh viện — Customer 360°') }}
        </p>
      </div>
      <div class="flex w-full items-center gap-2 sm:w-auto">
        <div class="w-full sm:w-64">
          <FormControl
            type="text"
            :placeholder="__('Tìm theo tên bệnh viện…')"
            :modelValue="search"
            :aria-label="__('Tìm theo tên bệnh viện')"
            @update:modelValue="onSearch"
          >
            <template #prefix>
              <FeatherIcon name="search" class="h-4 w-4 text-ink-gray-5" />
            </template>
          </FormControl>
        </div>
        <Button
          variant="solid"
          theme="teal"
          class="shrink-0"
          :label="__('+ Tạo bệnh viện')"
          @click="openCreate"
        />
      </div>
    </header>

    <!-- Chip lọc theo hạng -->
    <div
      class="flex flex-wrap items-center gap-2 px-6 py-3"
      role="group"
      :aria-label="__('Lọc theo hạng bệnh viện')"
    >
      <button
        v-for="opt in rankOptions"
        :key="opt.value || 'all'"
        type="button"
        :aria-pressed="activeRank === opt.value"
        class="rounded-full px-3 py-1 text-p-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
        :class="
          activeRank === opt.value
            ? 'bg-surface-gray-7 text-ink-white'
            : 'bg-surface-gray-2 text-ink-gray-7 hover:bg-surface-gray-3'
        "
        @click="setRank(opt.value)"
      >
        {{ opt.label }}
      </button>
    </div>

    <!-- Tri-branch: loading / error / data -->
    <section class="flex-1 overflow-auto px-6 pb-6" aria-live="polite">
      <!-- Loading -->
      <div
        v-if="hospitals.loading"
        class="flex items-center justify-center gap-2 py-16 text-ink-gray-6"
      >
        <LoadingIndicator class="h-4 w-4" />
        <span class="text-p-base">{{ __('Đang tải danh sách bệnh viện…') }}</span>
      </div>

      <!-- Error -->
      <div
        v-else-if="hospitals.error"
        class="flex flex-col items-center gap-3 py-16 text-center"
        role="alert"
      >
        <Badge variant="subtle" theme="red" size="lg" :label="__('Không tải được')" />
        <p class="max-w-md text-p-sm text-ink-gray-6">{{ errorMessage }}</p>
        <Button variant="outline" :label="__('Thử lại')" @click="hospitals.reload()" />
      </div>

      <!-- Empty -->
      <div
        v-else-if="!rows.length"
        class="flex flex-col items-center gap-2 py-16 text-center text-ink-gray-6"
      >
        <p class="text-p-base">{{ __('Chưa có bệnh viện nào khớp điều kiện.') }}</p>
        <Button variant="outline" :label="__('+ Tạo bệnh viện')" @click="openCreate" />
      </div>

      <!-- Data table -->
      <table v-else class="w-full border-separate border-spacing-0 text-left">
        <caption class="sr-only">
          {{ __('Danh sách bệnh viện') }}
        </caption>
        <thead>
          <tr class="text-p-sm text-ink-gray-6">
            <th class="border-b border-outline-gray-modals py-2 pr-4 font-medium">
              {{ __('Tên bệnh viện') }}
            </th>
            <th class="border-b border-outline-gray-modals py-2 pr-4 font-medium">
              {{ __('Hạng') }}
            </th>
            <th class="border-b border-outline-gray-modals py-2 pr-4 font-medium">
              {{ __('Mã số thuế') }}
            </th>
            <th class="border-b border-outline-gray-modals py-2 font-medium">
              {{ __('Trạng thái HĐ') }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in rows"
            :key="row.name"
            tabindex="0"
            role="link"
            :aria-label="__('Xem chi tiết') + ' ' + row.hospital_name"
            class="cursor-pointer text-p-base text-ink-gray-8 transition hover:bg-surface-gray-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
            @click="openHospital(row.name)"
            @keydown.enter="openHospital(row.name)"
            @keydown.space.prevent="openHospital(row.name)"
          >
            <td class="border-b border-outline-gray-1 py-3 pr-4 font-medium text-ink-gray-9">
              {{ row.hospital_name || row.name }}
            </td>
            <td class="border-b border-outline-gray-1 py-3 pr-4">
              <Badge
                v-if="row.rank"
                variant="subtle"
                size="sm"
                :theme="rankTheme(row.rank)"
                :label="row.rank"
              />
              <span v-else class="text-ink-gray-5">—</span>
            </td>
            <td class="border-b border-outline-gray-1 py-3 pr-4 text-ink-gray-7">
              {{ row.tax_code || '—' }}
            </td>
            <td class="border-b border-outline-gray-1 py-3">
              <Badge
                v-if="row.contract_status"
                variant="subtle"
                size="sm"
                :theme="contractTheme(row.contract_status)"
                :label="row.contract_status"
              />
              <span v-else class="text-ink-gray-5">—</span>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Tổng số (count==rows) -->
      <p
        v-if="!hospitals.loading && !hospitals.error && rows.length"
        class="pt-3 text-p-sm text-ink-gray-5"
      >
        {{ __('Tổng cộng') }}: {{ totalCount }} {{ __('bệnh viện') }}
      </p>
    </section>

    <!-- Dialog tạo bệnh viện -->
    <Dialog v-model="createDlg" :options="{ title: __('Tạo bệnh viện mới'), size: 'xl' }">
      <template #body-content>
        <div class="bg-surface-modal px-4 pb-6 pt-5 sm:px-6">
          <div class="flex flex-col gap-4">
            <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <FormControl
                :label="__('Mã bệnh viện') + ' *'"
                v-model="cForm.hospital_code"
                placeholder="BV-XXX"
                required
              />
              <FormControl
                :label="__('Tên bệnh viện') + ' *'"
                v-model="cForm.hospital_name"
                :placeholder="__('Bệnh viện Đa khoa…')"
                required
              />
            </div>
            <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <FormControl
                type="select"
                :label="__('Hạng')"
                v-model="cForm.rank"
                :options="rankSelectOptions"
              />
              <FormControl
                type="select"
                :label="__('Trạng thái HĐ')"
                v-model="cForm.contract_status"
                :options="contractStatusOptions"
              />
            </div>
            <FormControl :label="__('Mã số thuế')" v-model="cForm.tax_code" />
            <FormControl
              type="textarea"
              :label="__('Địa chỉ')"
              v-model="cForm.address"
              :rows="2"
            />
          </div>
          <div class="mt-6 flex justify-end gap-2 border-t border-outline-gray-1 pt-4">
            <Button :label="__('Huỷ')" @click="createDlg = false" />
            <Button
              variant="solid"
              theme="teal"
              :loading="createRes.loading"
              :label="__('Tạo bệnh viện')"
              @click="onCreate"
            />
          </div>
        </div>
      </template>
    </Dialog>
  </main>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Badge, Button, Dialog, FormControl, FeatherIcon, createResource, toast } from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import { listHospitals, RANK_THEME, CONTRACT_STATUS_THEME } from '@/data/antmed'

const router = useRouter()

// Options hạng (value rỗng = Tất cả). Value khớp EXACT options DocType BE (VN có dấu).
const rankOptions = [
  { value: '', label: __('Tất cả') },
  { value: 'Đặc biệt', label: __('Đặc biệt') },
  { value: 'I', label: __('Hạng I') },
  { value: 'II', label: __('Hạng II') },
  { value: 'III', label: __('Hạng III') },
  { value: 'Khác', label: __('Khác') },
]

const search = ref('')
const activeRank = ref('')

// FE→BE contract: filters PHẢI là JSON-string (BE _coerce_filters dùng frappe.parse_json).
// Truyền object thô → createResource GET serialize thành "[object Object]" → BE parse lỗi → mất data.
function buildParams() {
  const filters = activeRank.value ? { rank: activeRank.value } : {}
  return { search: search.value, filters: JSON.stringify(filters) }
}

// Resource list — endpoint trả dict bọc { data, total_count }, đọc r.data.data.
const hospitals = listHospitals({
  params: buildParams(),
  auto: true,
})

const rows = computed(() => hospitals.data?.data || [])
const totalCount = computed(() => hospitals.data?.total_count ?? rows.value.length)

const errorMessage = computed(
  () =>
    hospitals.error?.messages?.[0] ||
    hospitals.error?.message ||
    __('Không tải được danh sách bệnh viện'),
)

function rankTheme(rank) {
  return RANK_THEME[rank] || 'gray'
}
function contractTheme(status) {
  return CONTRACT_STATUS_THEME[status] || 'gray'
}

// Param phát đi == UI selection (chống dead-control): rebuild params từ search + rank.
function refetch() {
  hospitals.submit(buildParams())
}

let searchTimer = null
function onSearch(value) {
  search.value = value
  clearTimeout(searchTimer)
  searchTimer = setTimeout(refetch, 300)
}

function setRank(value) {
  activeRank.value = value
  refetch()
}

function openHospital(name) {
  router.push({ name: 'AntmedHospitalDetail', params: { name } })
}

// Surface lỗi BR-XX từ BE qua toast (ngoài banner tri-branch).
hospitals.onError = (err) => {
  toast.error(err?.messages?.[0] || __('Không tải được danh sách bệnh viện'))
}

// ── Tạo bệnh viện (BE customer.create_hospital) ──
const rankSelectOptions = [
  { value: '', label: __('— Chọn hạng —') },
  { value: 'Đặc biệt', label: __('Đặc biệt') },
  { value: 'I', label: __('Hạng I') },
  { value: 'II', label: __('Hạng II') },
  { value: 'III', label: __('Hạng III') },
  { value: 'Khác', label: __('Khác') },
]
const contractStatusOptions = [
  { value: '', label: __('— Chọn trạng thái —') },
  { value: 'Tiềm năng', label: __('Tiềm năng') },
  { value: 'Đã ký', label: __('Đã ký') },
  { value: 'Hết hạn', label: __('Hết hạn') },
]
const createDlg = ref(false)
const emptyHospital = () => ({
  hospital_code: '',
  hospital_name: '',
  rank: '',
  contract_status: '',
  tax_code: '',
  address: '',
})
const cForm = ref(emptyHospital())
const createRes = createResource({
  url: 'antmed_crm.api.antmed.customer.create_hospital',
  method: 'POST',
  onSuccess() {
    toast.success(__('Đã tạo bệnh viện mới'))
    createDlg.value = false
    hospitals.reload()
  },
  onError: (err) => toast.error(err?.messages?.[0] || __('Không tạo được bệnh viện')),
})
function openCreate() {
  cForm.value = emptyHospital()
  createDlg.value = true
}
function onCreate() {
  if (!cForm.value.hospital_code || !cForm.value.hospital_name) {
    toast.error(__('Nhập mã và tên bệnh viện'))
    return
  }
  createRes.submit({ ...cForm.value })
}
</script>
