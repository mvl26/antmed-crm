<template>
  <main class="flex h-full flex-col" aria-labelledby="antmed-set-title">
    <header class="flex flex-col gap-2 border-b border-outline-gray-modals px-6 py-4">
      <nav class="text-p-xs text-ink-gray-5" :aria-label="__('Đường dẫn')">
        <RouterLink to="/antmed" class="rounded text-ink-gray-6 hover:text-ink-gray-8">{{ __('Trang chủ') }}</RouterLink>
        <span class="px-1.5 text-ink-gray-4" aria-hidden="true">›</span>
        <RouterLink to="/antmed/instruments" class="rounded text-ink-gray-6 hover:text-ink-gray-8">{{ __('Bộ dụng cụ') }}</RouterLink>
        <span class="px-1.5 text-ink-gray-4" aria-hidden="true">›</span>
        <span class="text-ink-gray-7" aria-current="page">{{ name }}</span>
      </nav>
      <div class="flex flex-wrap items-center gap-3">
        <h1 id="antmed-set-title" class="text-xl font-semibold text-ink-gray-9">
          🧰 {{ set.set_code || name }}
          <span v-if="set.surgery_type" class="text-ink-gray-6">· {{ set.surgery_type }}</span>
        </h1>
        <Badge
          v-if="set.current_status"
          variant="subtle"
          :theme="statusTheme(set.current_status)"
          size="md"
          :label="set.current_status"
        />
      </div>
    </header>

    <section class="flex-1 overflow-auto px-6 pb-8 pt-4" aria-live="polite">
      <div v-if="resource.loading" class="flex items-center justify-center gap-2 py-16 text-ink-gray-6">
        <LoadingIndicator class="h-4 w-4" />
        <span class="text-p-base">{{ __('Đang tải…') }}</span>
      </div>

      <div v-else-if="resource.error" class="flex flex-col items-center gap-3 py-16 text-center" role="alert">
        <Badge variant="subtle" theme="red" size="lg" :label="__('Không tải được')" />
        <p class="max-w-md text-p-sm text-ink-gray-6">{{ errorMessage }}</p>
        <Button variant="outline" :label="__('Thử lại')" @click="resource.reload()" />
      </div>

      <template v-else>
        <!-- Thanh vòng đời -->
        <div class="mb-5 max-w-2xl">
          <AmLifecycleBar :state="set.current_status" />
        </div>

        <!-- Thông tin bộ -->
        <dl class="mb-6 grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3">
          <div>
            <dt class="text-p-xs uppercase text-ink-gray-5">{{ __('Số món') }}</dt>
            <dd class="text-p-base font-medium text-ink-gray-9 tabular-nums">{{ components.length }}</dd>
          </div>
          <div>
            <dt class="text-p-xs uppercase text-ink-gray-5">{{ __('Tổng lượt mượn') }}</dt>
            <dd class="text-p-base font-medium text-ink-gray-9 tabular-nums">{{ set.lifetime_loans ?? 0 }}</dd>
          </div>
          <div>
            <dt class="text-p-xs uppercase text-ink-gray-5">{{ __('Giới hạn lượt') }}</dt>
            <dd class="text-p-base font-medium text-ink-gray-9 tabular-nums">{{ set.max_loans || '—' }}</dd>
          </div>
          <div>
            <dt class="text-p-xs uppercase text-ink-gray-5">{{ __('Giá trị tài sản') }}</dt>
            <dd class="text-p-base font-medium text-ink-gray-9">{{ set.asset_value ? formatVnMoney(set.asset_value) : '—' }}</dd>
          </div>
          <div>
            <dt class="text-p-xs uppercase text-ink-gray-5">{{ __('Kho hiện tại') }}</dt>
            <dd class="text-p-base font-medium text-ink-gray-9">{{ set.current_warehouse || '—' }}</dd>
          </div>
          <div>
            <dt class="text-p-xs uppercase text-ink-gray-5">{{ __('NV đang giữ') }}</dt>
            <dd class="text-p-base font-medium text-ink-gray-9">{{ set.current_holder || '—' }}</dd>
          </div>
        </dl>

        <!-- Danh mục món -->
        <div class="mb-6 rounded-lg border border-outline-gray-2 bg-surface-white p-4">
          <h2 class="mb-3 text-p-base font-semibold text-ink-gray-8">{{ __('Danh mục món') }} ({{ components.length }})</h2>
          <p v-if="!components.length" class="text-p-sm text-ink-gray-5">{{ __('Chưa khai báo món nào cho bộ này.') }}</p>
          <table v-else class="w-full border-separate border-spacing-0 text-left">
            <thead>
              <tr class="text-p-xs uppercase text-ink-gray-5">
                <th class="border-b border-outline-gray-modals py-2 pr-4 font-medium">{{ __('Tên món') }}</th>
                <th class="border-b border-outline-gray-modals py-2 pr-4 text-right font-medium">{{ __('SL') }}</th>
                <th class="border-b border-outline-gray-modals py-2 font-medium">{{ __('Mức quan trọng') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(c, i) in components" :key="i" class="text-p-base text-ink-gray-8">
                <td class="border-b border-outline-gray-1 py-2 pr-4">{{ c.component_name }}</td>
                <td class="border-b border-outline-gray-1 py-2 pr-4 text-right tabular-nums">{{ c.qty }}</td>
                <td class="border-b border-outline-gray-1 py-2">
                  <Badge
                    variant="subtle"
                    :theme="c.criticality === 'Critical' ? 'red' : 'gray'"
                    size="sm"
                    :label="c.criticality === 'Critical' ? __('Trọng yếu') : __('Thường')"
                  />
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Lịch sử lượt mượn -->
        <div class="rounded-lg border border-outline-gray-2 bg-surface-white p-4">
          <h2 class="mb-3 text-p-base font-semibold text-ink-gray-8">{{ __('Lịch sử lượt mượn') }}</h2>
          <p v-if="!loans.length" class="text-p-sm text-ink-gray-5">{{ __('Chưa có lượt mượn nào.') }}</p>
          <ul v-else class="flex flex-col gap-2">
            <li v-for="ln in loans" :key="ln.name">
              <RouterLink
                :to="`/antmed/instrument-loans/${encodeURIComponent(ln.name)}`"
                class="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-md border border-outline-gray-1 px-3 py-2 hover:border-teal-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
              >
                <span class="font-medium text-teal-700">{{ ln.name }}</span>
                <Badge variant="subtle" :theme="statusTheme(ln.status)" size="sm" :label="ln.status" />
                <span class="text-p-xs text-ink-gray-5">{{ __('Đặt') }}: {{ fmtDate(ln.booked_at) }}</span>
                <span v-if="ln.returned_at" class="text-p-xs text-ink-gray-5">· {{ __('Trả') }}: {{ fmtDate(ln.returned_at) }}</span>
              </RouterLink>
            </li>
          </ul>
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
import AmLifecycleBar from '@/components/Antmed/AmLifecycleBar.vue'
import { getInstrumentSet, INSTRUMENT_STATUS_THEME } from '@/data/antmed'
import { formatVnMoney } from '@/utils/antmedUi'

const props = defineProps({ name: { type: String, required: true } })

const resource = getInstrumentSet({ params: { name: props.name }, auto: true })
resource.onError = (err) => toast.error(err?.messages?.[0] || __('Không tải được bộ dụng cụ'))

const set = computed(() => resource.data || {})
const components = computed(() => resource.data?.components || [])
const loans = computed(() => resource.data?.loans || [])

function statusTheme(s) {
  return INSTRUMENT_STATUS_THEME[s] || 'gray'
}

function fmtDate(v) {
  if (!v) return '—'
  const d = new Date(String(v).replace(' ', 'T'))
  if (Number.isNaN(d.getTime())) return String(v)
  const p = (n) => String(n).padStart(2, '0')
  return `${p(d.getDate())}/${p(d.getMonth() + 1)} ${p(d.getHours())}:${p(d.getMinutes())}`
}

const errorMessage = computed(
  () => resource.error?.messages?.[0] || resource.error?.message || __('Không tải được bộ dụng cụ'),
)
</script>
