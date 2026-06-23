<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-50 flex items-start justify-center bg-black/40 px-4 pt-[12vh]"
      @click.self="close"
    >
      <div
        role="dialog"
        aria-modal="true"
        :aria-label="__('Tìm kiếm nhanh')"
        class="w-full max-w-xl overflow-hidden rounded-xl border border-outline-gray-2 bg-surface-white shadow-2xl"
        @keydown="onKeydown"
      >
        <!-- Ô nhập -->
        <div
          class="flex items-center gap-2.5 border-b border-outline-gray-2 px-4 py-3"
        >
          <FeatherIcon
            name="search"
            class="h-4 w-4 shrink-0 text-ink-gray-5"
            aria-hidden="true"
          />
          <input
            ref="inputEl"
            v-model="query"
            type="text"
            role="combobox"
            :aria-expanded="flatItems.length > 0"
            aria-controls="quicksearch-list"
            :aria-activedescendant="activeId"
            class="w-full border-0 bg-transparent text-base text-ink-gray-9 placeholder:text-ink-gray-4 focus:outline-none focus:ring-0"
            :placeholder="
              __(
                'Tìm chức năng, bệnh viện, hợp đồng, bộ dụng cụ, giao phòng mổ...',
              )
            "
            :aria-label="__('Tìm kiếm')"
          />
          <span
            class="rounded bg-ink-gray-2 px-1.5 py-0.5 text-[10px] font-medium text-ink-gray-6"
            >Esc</span
          >
        </div>

        <!-- Kết quả -->
        <ul
          id="quicksearch-list"
          role="listbox"
          class="max-h-[60vh] overflow-auto py-1.5"
        >
          <template v-for="group in groups" :key="group.key">
            <li
              v-if="group.items.length"
              role="presentation"
              class="px-4 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-wide text-ink-gray-5"
            >
              {{ __(group.title) }}
            </li>
            <li
              v-for="item in group.items"
              :id="'qs-' + item._index"
              :key="item._index"
              role="option"
              :aria-selected="item._index === activeIndex"
              class="mx-1.5 flex cursor-pointer items-center gap-2.5 rounded-md px-2.5 py-2 text-p-sm"
              :class="
                item._index === activeIndex
                  ? 'bg-teal-50 text-teal-900'
                  : 'text-ink-gray-7'
              "
              @mousemove="activeIndex = item._index"
              @click="runItem(item)"
            >
              <FeatherIcon
                :name="item.icon"
                class="h-4 w-4 shrink-0"
                aria-hidden="true"
              />
              <span class="min-w-0 flex-1 truncate">{{ item.label }}</span>
              <span
                v-if="item.hint"
                class="shrink-0 truncate text-p-xs text-ink-gray-4"
                >{{ item.hint }}</span
              >
            </li>
          </template>

          <li
            v-if="records.loading"
            role="presentation"
            class="px-4 py-3 text-p-sm text-ink-gray-5"
          >
            {{ __('Đang tìm...') }}
          </li>
          <li
            v-else-if="records.error"
            role="presentation"
            class="px-4 py-3 text-p-sm text-ink-gray-5"
          >
            {{ __('Không tải được kết quả') }}
          </li>
          <li
            v-else-if="!flatItems.length"
            role="presentation"
            class="px-4 py-6 text-center text-p-sm text-ink-gray-5"
          >
            {{
              query
                ? __('Không tìm thấy')
                : __('Gõ để tìm chức năng hoặc bản ghi')
            }}
          </li>
        </ul>

        <!-- Gợi ý phím -->
        <div
          class="flex items-center gap-3 border-t border-outline-gray-2 px-4 py-2 text-p-xs text-ink-gray-5"
        >
          <span>↑↓ {{ __('chọn') }}</span>
          <span>↵ {{ __('mở') }}</span>
          <span>esc {{ __('đóng') }}</span>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { FeatherIcon } from 'frappe-ui'
import { searchFunctions, normalize } from '@/data/antmedSearchSources'
import { useGlobalSearch } from '@/data/antmed'

const props = defineProps({ open: { type: Boolean, default: false } })
const emit = defineEmits(['update:open'])

const router = useRouter()
const inputEl = ref(null)
const query = ref('')
const activeIndex = ref(0)

const records = useGlobalSearch()

// ── Kết quả ──
const functionResults = computed(() => searchFunctions(query.value))
const hospitalResults = computed(() =>
  (records.data?.hospitals || []).map((h) => ({
    type: 'hospital',
    label: h.hospital_name || h.name,
    icon: 'home',
    to: `/antmed/hospitals/${encodeURIComponent(h.name)}`,
  })),
)
const contractResults = computed(() =>
  (records.data?.contracts || []).map((c) => ({
    type: 'contract',
    label: c.contract_no || c.name,
    hint: c.hospital_name || '',
    icon: 'clipboard',
    to: `/antmed/contracts/${encodeURIComponent(c.name)}`,
  })),
)
const instrumentResults = computed(() =>
  (records.data?.instrument_sets || []).map((s) => ({
    type: 'instrument',
    label: s.set_code || s.name,
    hint: s.surgery_type || '',
    icon: 'box',
    to: `/antmed/instruments/${encodeURIComponent(s.name)}`,
  })),
)
const deliveryResults = computed(() =>
  (records.data?.deliveries || []).map((d) => ({
    type: 'delivery',
    label: d.name,
    hint: d.hospital_name || '',
    icon: 'truck',
    to: `/antmed/deliveries/${encodeURIComponent(d.name)}`,
  })),
)

// Mảng phẳng có thứ tự (gắn _index) → điều hướng bàn phím.
const flatItems = computed(() =>
  [
    ...functionResults.value,
    ...hospitalResults.value,
    ...contractResults.value,
    ...instrumentResults.value,
    ...deliveryResults.value,
  ].map((it, i) => ({ ...it, _index: i })),
)

const groups = computed(() => {
  const items = flatItems.value
  return [
    {
      key: 'fn',
      title: 'Chức năng',
      items: items.filter((i) => i.type === 'function'),
    },
    {
      key: 'hosp',
      title: 'Bệnh viện',
      items: items.filter((i) => i.type === 'hospital'),
    },
    {
      key: 'contract',
      title: 'Hợp đồng',
      items: items.filter((i) => i.type === 'contract'),
    },
    {
      key: 'instrument',
      title: 'Bộ dụng cụ',
      items: items.filter((i) => i.type === 'instrument'),
    },
    {
      key: 'delivery',
      title: 'Giao phòng mổ',
      items: items.filter((i) => i.type === 'delivery'),
    },
  ]
})

const activeId = computed(() =>
  flatItems.value[activeIndex.value] ? `qs-${activeIndex.value}` : undefined,
)

// ── Gọi records (debounce, chỉ khi query ≥ 2 ký tự) ──
let debounceTimer = null
watch(query, (q) => {
  activeIndex.value = 0
  if (debounceTimer) clearTimeout(debounceTimer)
  if (normalize(q).length < 2) {
    records.reset()
    return
  }
  debounceTimer = setTimeout(() => {
    records.submit({ query: q, limit: 5 })
  }, 250)
})

onUnmounted(() => {
  if (debounceTimer) clearTimeout(debounceTimer)
})

// ── Bàn phím ──
function move(d) {
  const n = flatItems.value.length
  if (!n) return
  activeIndex.value = (activeIndex.value + d + n) % n
  nextTick(() =>
    document
      .getElementById(`qs-${activeIndex.value}`)
      ?.scrollIntoView({ block: 'nearest' }),
  )
}
function onKeydown(e) {
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    move(1)
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    move(-1)
  } else if (e.key === 'Enter') {
    e.preventDefault()
    const it = flatItems.value[activeIndex.value]
    if (it) runItem(it)
  } else if (e.key === 'Escape') {
    e.preventDefault()
    close()
  }
}

function runItem(it) {
  if (it?.to) {
    try {
      router.push(it.to)
    } catch {
      // đích không hợp lệ → bỏ điều hướng, vẫn đóng palette.
    }
  }
  close()
}

function close() {
  emit('update:open', false)
}

// Mở → reset + focus; đóng → xoá query.
watch(
  () => props.open,
  async (v) => {
    if (v) {
      query.value = ''
      activeIndex.value = 0
      records.reset()
      await nextTick()
      inputEl.value?.focus()
    } else {
      query.value = ''
    }
  },
)
</script>
