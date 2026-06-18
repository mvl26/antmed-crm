import { readFileSync } from 'fs'
import path from 'path'
import { isAntmedOnlyKeptRoute } from '../../src/utils/antmed'

// Phase 1 — CHỈ DÙNG UI AntMed (bỏ UI CRM gốc): / + mọi route CRM gốc (/leads,/deals,
// /contacts,/organizations,/notes,/tasks,/call-logs,/dashboard,/data-import) + mock
// prototype cũ (/ceo,/sales/*,/rep/*,/warehouse/*,/docs/*,/finance/*,/portal,/admin/*)
// → redirect /antmed. GIỮ: khu /antmed/*, login AntMed, trang lỗi hệ thống.
// LƯU Ý: mock prototype có name 'Antmed*Mock' nhưng path KHÔNG /antmed → PHẢI redirect
// ⇒ keep theo PATH (/antmed/*) + keep-list hệ thống, KHÔNG theo tiền tố tên 'Antmed'.

describe('isAntmedOnlyKeptRoute — chỉ giữ khu /antmed/* + trang hệ thống', () => {
  it('giữ route khu /antmed/* (path-based)', () => {
    expect(isAntmedOnlyKeptRoute({ path: '/antmed', name: 'AntmedHome' })).toBe(
      true,
    )
    expect(
      isAntmedOnlyKeptRoute({
        path: '/antmed/sales/dispatch',
        name: 'AntmedDispatch',
      }),
    ).toBe(true)
  })
  it('giữ login AntMed + trang lỗi hệ thống (keep-list)', () => {
    expect(isAntmedOnlyKeptRoute({ path: '/login', name: 'AntmedLogin' })).toBe(
      true,
    )
    expect(isAntmedOnlyKeptRoute({ path: '/', name: 'Not Permitted' })).toBe(
      true,
    )
    expect(isAntmedOnlyKeptRoute({ path: '/', name: 'Invalid Page' })).toBe(
      true,
    )
  })
  it('KHÔNG giữ Home + CRM gốc + mock prototype (kể cả name Antmed*Mock ở path non-/antmed)', () => {
    for (const r of [
      { path: '/', name: 'Home' },
      { path: '/leads/view', name: 'Leads' },
      { path: '/deals/view', name: 'Deals' },
      { path: '/contacts/view', name: 'Contacts' },
      { path: '/organizations/view', name: 'Organizations' },
      { path: '/dashboard', name: 'Dashboard' },
      { path: '/notifications', name: 'Notifications' },
      { path: '/ceo', name: 'AntmedCeoMock' },
      { path: '/sales/dispatch', name: 'AntmedDispatchMock' },
    ]) {
      expect(isAntmedOnlyKeptRoute(r)).toBe(false)
    }
  })
  it('an toàn input xấu', () => {
    expect(isAntmedOnlyKeptRoute(null)).toBe(false)
    expect(isAntmedOnlyKeptRoute(undefined)).toBe(false)
    expect(isAntmedOnlyKeptRoute({})).toBe(false)
  })
})

describe('router.js — beforeEach redirect mọi route non-AntMed → AntmedHome', () => {
  const routerSrc = readFileSync(
    path.resolve(__dirname, '../../src/router.js'),
    'utf8',
  )
  it('import + dùng isAntmedOnlyKeptRoute, redirect AntmedHome', () => {
    expect(routerSrc).toMatch(/isAntmedOnlyKeptRoute/)
    expect(routerSrc).toMatch(/name:\s*['"]AntmedHome['"]/)
  })
})
