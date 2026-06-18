import { readFileSync } from 'fs'
import path from 'path'

// TDD-FE-1 (M01 R1 smoke): route '/antmed' resolve tới AntmedHome.vue trong
// router.js. Kiểm bằng nội dung file (grep nhẹ), KHÔNG cần e2e.
//
// ⚠️ M11 FE Slice 2: AntmedHome.vue ĐÃ rewrite từ health-widget → layout dashboard A1
// (gọi antmed_crm.api.antmed.dashboard.overview, KHÔNG còn health.ping). Smoke health.ping R1
// nay test ở: BE crm/tests/test_antmed_bootstrap.py (ping()) + FE data/antmed.js export
// getAntmedHealth + suite antmedDashboard.test.js. Assertion AntmedHome bên dưới cập nhật
// theo contract MỚI (overview) — KHÔNG mất coverage health.ping.

const srcDir = path.resolve(__dirname, '../../src')
const routerSrc = readFileSync(path.join(srcDir, 'router.js'), 'utf8')
const pageSrc = readFileSync(path.join(srcDir, 'pages/AntmedHome.vue'), 'utf8')

describe('AntMed FE bootstrap (M01 R1)', () => {
  it('route /antmed tồn tại trong router.js', () => {
    expect(routerSrc).toMatch(/path:\s*['"]\/antmed['"]/)
  })

  it('route /antmed có name AntmedHome', () => {
    expect(routerSrc).toMatch(/name:\s*['"]AntmedHome['"]/)
  })

  it('route /antmed trỏ tới AntmedHome.vue (lazy import)', () => {
    expect(routerSrc).toMatch(
      /component:\s*\(\)\s*=>\s*import\(['"]@\/pages\/AntmedHome\.vue['"]\)/,
    )
  })

  it('Phase 2 (bỏ UI CRM gốc): route Frappe CRM (Leads/Deals/Contacts/Organizations) ĐÃ GỠ', () => {
    expect(routerSrc).not.toMatch(/name:\s*['"]Leads['"]/)
    expect(routerSrc).not.toMatch(/name:\s*['"]Deals['"]/)
    expect(routerSrc).not.toMatch(/name:\s*['"]Contacts['"]/)
    expect(routerSrc).not.toMatch(/name:\s*['"]Organizations['"]/)
  })

  it('AntmedHome.vue (Slice 2) gọi resource dashboard.overview qua data layer', () => {
    // Sau rewrite A1: AntmedHome fetch số liệu qua getDashboardOverview (data/antmed.js),
    // KHÔNG tự createResource health.ping nữa. Health.ping vẫn callable + test ở BE + data layer.
    expect(pageSrc).toMatch(/getDashboardOverview/)
    const dataSrc = readFileSync(path.join(srcDir, 'data/antmed.js'), 'utf8')
    expect(dataSrc).toMatch(/url:\s*['"]antmed_crm\.api\.antmed\.dashboard\.overview['"]/)
  })

  it('AntmedHome.vue KHÔNG dùng axios/TanStack/api-ts layer (di sản stack cũ)', () => {
    expect(pageSrc).not.toMatch(/axios/)
    expect(pageSrc).not.toMatch(/@tanstack\/vue-query/)
    expect(pageSrc).not.toMatch(/from ['"]@\/api\//)
  })
})
