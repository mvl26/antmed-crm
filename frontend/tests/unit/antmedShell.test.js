import { readFileSync } from 'fs'
import path from 'path'
import { ANTMED_NAV, isNavActive } from '../../src/data/antmedNav'

// Slice 1 — AntMed app shell (topbar + sidebar) khớp mockup A1
// (docs/docs/AntMed_CRM_Full_Mockups.html). Idiom test = content-assert nguồn +
// behavior-assert helper thuần (KHÔNG @vue/test-utils — theo antmedRouterGuard.test.js).

const srcDir = path.resolve(__dirname, '../../src')
const layoutSrc = readFileSync(
  path.join(srcDir, 'components/Antmed/AntmedLayout.vue'),
  'utf8',
)
const appSrc = readFileSync(path.join(srcDir, 'App.vue'), 'utf8')

describe('AntMed nav config — single source cho sidebar shell', () => {
  it('Dashboard + Bệnh viện là route thật đã có (enabled)', () => {
    const byKey = Object.fromEntries(ANTMED_NAV.map((i) => [i.key, i]))
    expect(byKey.dashboard).toMatchObject({ to: '/antmed', enabled: true })
    expect(byKey.hospitals).toMatchObject({
      to: '/antmed/hospitals',
      enabled: true,
    })
  })

  it('mỗi item có label/icon/to/enabled hợp lệ', () => {
    for (const i of ANTMED_NAV) {
      expect(i.label).toBeTruthy()
      expect(i.icon).toBeTruthy()
      expect(typeof i.to).toBe('string')
      expect(typeof i.enabled).toBe('boolean')
    }
  })

  it('có stub module sắp tới (Hợp đồng / Tồn kho / Bộ dụng cụ) — disabled', () => {
    const labels = ANTMED_NAV.map((i) => i.label)
    expect(labels).toEqual(
      expect.arrayContaining(['Hợp đồng', 'Tồn kho', 'Bộ dụng cụ']),
    )
    expect(ANTMED_NAV.some((i) => !i.enabled)).toBe(true)
  })
})

describe('isNavActive — dashboard exact, sub-route theo prefix', () => {
  const dash = { to: '/antmed' }
  const hosp = { to: '/antmed/hospitals' }

  it('Dashboard chỉ active khi path đúng /antmed (không active ở sub-route)', () => {
    expect(isNavActive(dash, '/antmed')).toBe(true)
    expect(isNavActive(dash, '/antmed/hospitals')).toBe(false)
  })

  it('Bệnh viện active ở /antmed/hospitals và trang chi tiết con', () => {
    expect(isNavActive(hosp, '/antmed/hospitals')).toBe(true)
    expect(isNavActive(hosp, '/antmed/hospitals/BV-001')).toBe(true)
    expect(isNavActive(hosp, '/antmed')).toBe(false)
  })

  it('an toàn với input xấu', () => {
    expect(isNavActive(null, '/antmed')).toBe(false)
    expect(isNavActive(hosp, undefined)).toBe(false)
  })
})

describe('AntmedLayout.vue — cấu trúc shell mockup', () => {
  it('có topbar thương hiệu (logo AntMed CRM)', () => {
    expect(layoutSrc).toMatch(/AntMed CRM/)
  })

  it('sidebar lấy từ ANTMED_NAV (single source, không lặp danh sách cứng)', () => {
    expect(layoutSrc).toMatch(/antmedNav/)
    expect(layoutSrc).toMatch(/ANTMED_NAV/)
  })

  it('dùng RouterLink cho item enabled + có slot nội dung', () => {
    expect(layoutSrc).toMatch(/RouterLink|router-link/)
    expect(layoutSrc).toMatch(/<slot/)
  })

  it('đánh dấu active qua isNavActive', () => {
    expect(layoutSrc).toMatch(/isNavActive/)
  })
})

describe('App.vue — route /antmed/* render trong shell AntMed', () => {
  it('chọn layout theo isAntmedPath + dùng AntmedLayout', () => {
    expect(appSrc).toMatch(/isAntmedPath/)
    expect(appSrc).toMatch(/AntmedLayout/)
  })
})
