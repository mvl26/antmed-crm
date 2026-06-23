import { readFileSync } from 'fs'
import path from 'path'
import { describe, it, expect } from 'vitest'

const srcDir = path.resolve(__dirname, '../../src')
const routerSrc = readFileSync(path.join(srcDir, 'router.js'), 'utf8')
const appSrc = readFileSync(path.join(srcDir, 'App.vue'), 'utf8')
const loginSrc = readFileSync(
  path.join(srcDir, 'pages/AntmedLogin.vue'),
  'utf8',
)

describe('AntMed Login — routing + guest access', () => {
  it('router đăng ký route AntmedLogin (/antmed/login, lazy)', () => {
    expect(routerSrc).toMatch(/path:\s*'\/antmed\/login'/)
    expect(routerSrc).toMatch(/name:\s*'AntmedLogin'/)
    expect(routerSrc).toMatch(/import\('@\/pages\/AntmedLogin\.vue'\)/)
  })

  it('guard: guest → AntmedLogin trong SPA (KHÔNG đẩy /login Frappe)', () => {
    expect(routerSrc).toMatch(/name:\s*'AntmedLogin',\s*\n?\s*query/)
    // không redirect-loop khi đã ở AntmedLogin
    expect(routerSrc).toMatch(/to\.name === 'AntmedLogin'/)
  })

  it('App.vue render router-view cho guest (KHÔNG bọc layout)', () => {
    expect(appSrc).toMatch(/!session\.isLoggedIn/)
    expect(appSrc).toMatch(/<router-view/)
  })
})

describe('AntMed Login — page behavior', () => {
  it('gọi endpoint login (usr/pwd) + reload đầy đủ khi thành công', () => {
    expect(loginSrc).toMatch(/url:\s*'login'/)
    expect(loginSrc).toMatch(/usr:\s*email\.value/)
    expect(loginSrc).toMatch(/pwd:\s*password\.value/)
    expect(loginSrc).toMatch(
      /window\.location\.href\s*=\s*redirectTarget\.value/,
    )
  })

  it('redirect-to an toàn (chỉ path nội bộ "/") + mặc định /antmed', () => {
    expect(loginSrc).toMatch(/redirect-to/)
    expect(loginSrc).toMatch(/startsWith\('\/'\)/)
    expect(loginSrc).toMatch(/'\/antmed'/)
  })

  it('có toggle hiện/ẩn mật khẩu + vùng báo lỗi', () => {
    expect(loginSrc).toMatch(/showPassword/)
    expect(loginSrc).toMatch(/errorMessage/)
    expect(loginSrc).toMatch(/role="alert"/)
  })

  it('đã đăng nhập mở trang login → redirect về app', () => {
    expect(loginSrc).toMatch(/session\.isLoggedIn/)
    expect(loginSrc).toMatch(/onMounted/)
  })
})
