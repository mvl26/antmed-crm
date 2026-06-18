<template>
  <FrappeUIProvider>
    <NotPermitted v-if="$route.name === 'Not Permitted'" />
    <!-- Guest → render router-view trực tiếp (trang login full-screen, KHÔNG layout shell) -->
    <router-view v-else-if="!session.isLoggedIn" :key="$route.fullPath" />
    <Layout v-else class="isolate">
      <router-view :key="$route.fullPath" />
    </Layout>
    <Dialogs />
    <DoctypeModals />
  </FrappeUIProvider>
</template>

<script setup>
import NotPermitted from '@/pages/NotPermitted.vue'
import DoctypeModals from '@/components/Modals/DoctypeModals.vue'
import { Dialogs } from '@/utils/dialogs'
import { sessionStore } from '@/stores/session'
import { FrappeUIProvider, setConfig, useTheme } from 'frappe-ui'
import { defineAsyncComponent, provide } from 'vue'

const session = sessionStore()
provide('session', session)

const { setTheme } = useTheme()
if (!localStorage.getItem('theme')) {
  setTheme('light')
}

// Phase 2 — CHỈ DÙNG UI AntMed: mọi route đã consolidate về /antmed/* (router guard redirect)
// → một layout shell duy nhất (AntmedLayout). Đã gỡ Mobile/DesktopLayout của CRM gốc.
const Layout = defineAsyncComponent(
  () => import('./components/Antmed/AntmedLayout.vue'),
)

setConfig('systemTimezone', window.timezone?.system || null)
setConfig('localTimezone', window.timezone?.user || null)
setConfig('translatedMessages', window.translated_messages || {})
</script>
