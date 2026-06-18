import { defineStore } from 'pinia'
import { createResource } from 'frappe-ui'
import router from '@/router'
import { ref, computed } from 'vue'

export const sessionStore = defineStore('crm-session', () => {
  function sessionUser() {
    let cookies = new URLSearchParams(document.cookie.split('; ').join('&'))
    let _sessionUser = cookies.get('user_id')
    if (_sessionUser === 'Guest') {
      _sessionUser = null
    }
    return _sessionUser
  }

  let user = ref(sessionUser())
  const isLoggedIn = computed(() => !!user.value)

  const login = createResource({
    url: 'login',
    onError() {
      throw new Error(__('Invalid Email or Password'))
    },
    onSuccess() {
      user.value = sessionUser()
      login.reset()
      router.replace({ path: '/' })
    },
  })

  const logout = createResource({
    url: 'logout',
    onSuccess() {
      // KHÔNG set user.value=null TRƯỚC redirect: nó lật isLoggedIn (reactive) → App.vue
      // remount router-view như Guest → AntmedProfile gọi lại getMyProfile khi session đã hết
      // → "Không tải được hồ sơ". Full reload bên dưới tự xoá toàn bộ state (cookie đã clear).
      const inAntmed = window.location.pathname.startsWith('/crm/antmed')
      if (inAntmed) {
        window.location.replace('/crm/antmed/login')
      } else {
        window.location.replace(
          '/login?redirect-to=' + encodeURIComponent('/crm'),
        )
      }
    },
  })

  return {
    user,
    isLoggedIn,
    login,
    logout,
  }
})
