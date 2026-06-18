<template>
  <!-- Khung điện thoại (mockup .phone). Caller đặt header/body/tabbar vào slot. -->
  <div class="w-[320px] rounded-[32px] bg-ink-gray-9 p-3 shadow-xl">
    <div class="overflow-hidden rounded-[22px] bg-surface-gray-1">
      <slot />
    </div>
  </div>
</template>

<script setup></script>
