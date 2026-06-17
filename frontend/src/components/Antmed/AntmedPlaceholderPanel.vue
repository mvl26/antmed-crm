<template>
  <!-- Panel lớn chưa có nguồn dữ liệu (Top 10 BV / Pipeline / Cảnh báo).
       Render placeholder VI rõ ràng — KHÔNG bịa bảng/funnel/số. -->
  <article
    class="flex min-h-[160px] flex-col gap-3 rounded-xl border border-outline-gray-1 bg-surface-white p-4"
  >
    <h2 class="text-p-base font-semibold text-ink-gray-8">
      {{ title }}
    </h2>
    <div
      class="flex flex-1 flex-col items-center justify-center gap-1 rounded-lg bg-surface-gray-1 py-6 text-center"
    >
      <p class="text-p-sm font-medium text-ink-gray-5">
        {{ __('Chưa có dữ liệu') }}
      </p>
      <p class="text-p-xs text-ink-gray-4">
        {{ hint || __('Sắp có') }}
      </p>
    </div>
  </article>
</template>

<script setup>
defineProps({
  /** Tiêu đề panel (tiếng Việt). */
  title: { type: String, required: true },
  /** Gợi ý placeholder (mặc định "Sắp có"). */
  hint: { type: String, default: '' },
})
</script>
