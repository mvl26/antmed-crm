<template>
  <main class="flex h-full flex-col" aria-labelledby="antmed-tasks-title">
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
          __('Công việc')
        }}</span>
      </nav>
      <div class="flex flex-col gap-1">
        <h1
          id="antmed-tasks-title"
          class="text-xl font-semibold text-ink-gray-9"
        >
          {{ __('Công việc') }}
        </h1>
        <p class="text-p-sm text-ink-gray-6">
          {{
            __(
              'Việc cần làm — CSKH bác sỹ, hồ sơ thầu, theo dõi hợp đồng/giao hàng',
            )
          }}
        </p>
      </div>
    </header>

    <!-- KPI: tổng + đang mở (số = BE) -->
    <section
      class="grid grid-cols-2 gap-3 px-6 pt-4 sm:max-w-md"
      :aria-label="__('Chỉ số công việc')"
    >
      <AntmedKpiCard
        :label="__('Tổng công việc')"
        :value="totalCount"
        :empty="board.loading || !!board.error"
        :placeholder-hint="__('Đang tải…')"
      />
      <AntmedKpiCard
        :label="__('Đang mở')"
        :value="openCount"
        :empty="board.loading || !!board.error"
        :placeholder-hint="__('Đang tải…')"
      />
    </section>

    <section class="flex flex-1 flex-col gap-3 overflow-hidden px-6 pb-6 pt-4">
      <!-- Bộ lọc trạng thái (client-side trên data đã tải) -->
      <label class="flex items-center gap-2 text-p-sm">
        <span class="text-ink-gray-6">{{ __('Trạng thái') }}:</span>
        <select
          v-model="statusFilter"
          class="rounded-md border border-outline-gray-2 bg-surface-white px-2.5 py-1 text-p-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
          :aria-label="__('Lọc theo trạng thái')"
        >
          <option value="">{{ __('Tất cả') }}</option>
          <option v-for="s in STATUSES" :key="s" :value="s">
            {{ statusLabel(s) }}
          </option>
        </select>
        <span class="text-p-xs text-ink-gray-5"
          >{{ tasks.length }} {{ __('việc') }}</span
        >
      </label>

      <div class="min-h-0 flex-1 overflow-auto" aria-live="polite">
        <div
          v-if="board.loading"
          class="flex items-center justify-center gap-2 py-16 text-ink-gray-6"
        >
          <LoadingIndicator class="h-4 w-4" />
          <span class="text-p-base">{{ __('Đang tải…') }}</span>
        </div>

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

        <div
          v-else-if="!hasTasks"
          class="flex flex-col items-center gap-2 py-16 text-center text-ink-gray-6"
        >
          <p class="text-p-base">{{ __('Chưa có công việc') }}</p>
          <p class="text-p-sm">
            {{ __('Chưa có công việc nào trong phạm vi của bạn.') }}
          </p>
        </div>

        <table
          v-else
          class="w-full border-collapse text-p-sm"
          :aria-label="__('Danh sách công việc')"
        >
          <thead>
            <tr
              class="border-b border-outline-gray-2 text-left text-ink-gray-6"
            >
              <th class="px-2 py-2 font-medium">{{ __('Tiêu đề') }}</th>
              <th class="px-2 py-2 font-medium">{{ __('Trạng thái') }}</th>
              <th class="px-2 py-2 font-medium">{{ __('Ưu tiên') }}</th>
              <th class="px-2 py-2 font-medium">{{ __('Hạn') }}</th>
              <th class="px-2 py-2 font-medium">{{ __('Phụ trách') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="task in tasks"
              :key="task.name"
              class="border-b border-outline-gray-1 hover:bg-surface-gray-1"
            >
              <td class="px-2 py-2 font-medium text-ink-gray-9">
                {{ task.title || '—' }}
              </td>
              <td class="px-2 py-2">
                <Badge
                  variant="subtle"
                  size="sm"
                  :theme="statusTheme(task.status)"
                  :label="statusLabel(task.status)"
                />
              </td>
              <td class="px-2 py-2">
                <Badge
                  variant="subtle"
                  size="sm"
                  :theme="priorityTheme(task.priority)"
                  :label="task.priority || '—'"
                />
              </td>
              <td class="px-2 py-2 tabular-nums text-ink-gray-7">
                {{ fmtDue(task.due_date) }}
              </td>
              <td class="px-2 py-2 text-ink-gray-7">
                {{ task.assigned_to_name || '—' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </main>
</template>

<script setup>
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { Badge, Button, toast } from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import AntmedKpiCard from '@/components/Antmed/AntmedKpiCard.vue'
import { getTasks, TASK_STATUS_THEME, TASK_PRIORITY_THEME } from '@/data/antmed'

// Endpoint trả RAW dict { data, total_count, open_count } → đọc board.data.* TRỰC TIẾP.
const board = getTasks({ auto: true })

const STATUSES = ['Backlog', 'Todo', 'In Progress', 'Done', 'Canceled']
const STATUS_LABEL = {
  Backlog: 'Tồn đọng',
  Todo: 'Cần làm',
  'In Progress': 'Đang làm',
  Done: 'Hoàn thành',
  Canceled: 'Đã huỷ',
}
const statusLabel = (s) => STATUS_LABEL[s] || s || '—'
const statusTheme = (s) => TASK_STATUS_THEME[s] || 'gray'
const priorityTheme = (p) => TASK_PRIORITY_THEME[p] || 'gray'

const statusFilter = ref('')
const allTasks = computed(() => board.data?.data || [])
const tasks = computed(() =>
  statusFilter.value
    ? allTasks.value.filter((t) => t.status === statusFilter.value)
    : allTasks.value,
)
const totalCount = computed(() => board.data?.total_count ?? 0)
const openCount = computed(() => board.data?.open_count ?? 0)
const hasTasks = computed(() => tasks.value.length > 0)

// Hạn: "YYYY-MM-DD HH:MM:SS" → "HH:MM DD/MM" (string-op, KHÔNG cần Date).
function fmtDue(dt) {
  if (!dt) return '—'
  const [d, t] = String(dt).split(' ')
  if (!d || !d.includes('-')) return String(dt)
  const [, mo, da] = d.split('-')
  const hm = (t || '').slice(0, 5)
  return hm ? `${hm} ${da}/${mo}` : `${da}/${mo}`
}

board.onError = (err) => {
  toast.error(err?.messages?.[0] || __('Không tải được công việc'))
}
const errorMessage = computed(
  () =>
    board.error?.messages?.[0] ||
    board.error?.message ||
    __('Không tải được công việc'),
)
</script>
