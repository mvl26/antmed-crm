import { readFileSync } from 'fs'
import path from 'path'
import { ANTMED_NAV, ROLE_NAV, isNavActive } from '../../src/data/antmedNav'
import { shouldRedirectNotPermitted } from '../../src/utils/antmedGuard'
import {
  alertPillTheme,
  alertPillLabel,
  alertText,
  PILL_THEME,
} from '../../src/utils/antmedUi'

// M02-3 — màn "Cảnh báo điều hành" (mockup A1 widget ⚠, /antmed/alerts, AntmedAlerts.vue).
// Idiom test = content-assert nguồn (router/nav/page/data) + behavior-assert helper THUẦN
// (antmedUi.js không import frappe-ui → import trực tiếp được; data/antmed.js KÉO frappe-ui
// nên vitest KHÔNG load được → assert chuỗi nguồn cho url, như antmedContractHealth.test.js).

const srcDir = path.resolve(__dirname, '../../src')
const routerSrc = readFileSync(path.join(srcDir, 'router.js'), 'utf8')
const navSrc = readFileSync(path.join(srcDir, 'data/antmedNav.js'), 'utf8')
const pageSrc = readFileSync(path.join(srcDir, 'pages/AntmedAlerts.vue'), 'utf8')
const dataSrc = readFileSync(path.join(srcDir, 'data/antmed.js'), 'utf8')

const antmed = () => ({ isCrmUser: () => false, isAntmedUser: () => true })
const crm = () => ({ isCrmUser: () => true, isAntmedUser: () => false })
const outsider = () => ({ isCrmUser: () => false, isAntmedUser: () => false })

// Fixture alert shape 10-key (Hyrum) — khớp BE contract.list_quota_alerts.
const quota100 = {
  kind: 'quota',
  contract: 'CT-001',
  contract_no: 'HD-2026-001',
  hospital: 'BV-001',
  hospital_name: 'BV Chợ Rẫy',
  item: 'IT-001',
  item_name: 'Stent mạch vành',
  used_pct: 103.5,
  threshold: 100,
  days_to_expiry: null,
}
const quota90 = { ...quota100, threshold: 90, used_pct: 92, item_name: 'Catheter' }
const quota70 = { ...quota100, threshold: 70, used_pct: 73.2, item_name: 'Guidewire' }
const expiryPast = {
  kind: 'expiry',
  contract: 'CT-002',
  contract_no: 'HD-2026-002',
  hospital: 'BV-002',
  hospital_name: 'BV Bạch Mai',
  item: null,
  item_name: null,
  used_pct: null,
  threshold: null,
  days_to_expiry: -5,
}
const expirySoon = { ...expiryPast, days_to_expiry: 12 }
const expiryEdge = { ...expiryPast, days_to_expiry: 30 }

// ── Helper thuần alertPillTheme — map kind+threshold+dấu days → theme pill ────
describe('alertPillTheme — màu pill theo kind/threshold/days (KHÔNG tự tính từ used_pct)', () => {
  it('quota threshold=100 → danger (đỏ)', () => {
    expect(alertPillTheme(quota100)).toBe('danger')
  })
  it('quota threshold=90 → danger (đỏ)', () => {
    expect(alertPillTheme(quota90)).toBe('danger')
  })
  it('quota threshold=70 → warn (cam)', () => {
    expect(alertPillTheme(quota70)).toBe('warn')
  })
  it('expiry days=-5 (đã quá hạn) → danger (đỏ)', () => {
    expect(alertPillTheme(expiryPast)).toBe('danger')
  })
  it('expiry days=12 → warn (cam, còn trong ngưỡng)', () => {
    expect(alertPillTheme(expirySoon)).toBe('warn')
  })
  it('expiry days=30 (biên trên inclusive) → warn (cam)', () => {
    expect(alertPillTheme(expiryEdge)).toBe('warn')
  })
  it('expiry days=0 (hết hạn hôm nay) → warn (cam, chưa âm)', () => {
    expect(alertPillTheme({ ...expiryPast, days_to_expiry: 0 })).toBe('warn')
  })
  it('alert lạ/rỗng → warn (an toàn, không vỡ)', () => {
    expect(alertPillTheme(null)).toBe('warn')
    expect(alertPillTheme({})).toBe('warn')
    expect(alertPillTheme({ kind: 'quota', threshold: null })).toBe('warn')
  })
})

// ── Helper thuần alertPillLabel — nhãn pill VI (luôn có CHỮ, WCAG) ────────────
describe('alertPillLabel — nhãn pill có CHỮ (không chỉ phân biệt bằng màu)', () => {
  it("quota → 'QUOTA'", () => {
    expect(alertPillLabel(quota100)).toBe('QUOTA')
    expect(alertPillLabel(quota70)).toBe('QUOTA')
  })
  it("expiry days<0 → 'ĐÃ HẾT HẠN'", () => {
    expect(alertPillLabel(expiryPast)).toBe('ĐÃ HẾT HẠN')
  })
  it("expiry days>=0 → 'HẾT HẠN'", () => {
    expect(alertPillLabel(expirySoon)).toBe('HẾT HẠN')
    expect(alertPillLabel(expiryEdge)).toBe('HẾT HẠN')
    expect(alertPillLabel({ ...expiryPast, days_to_expiry: 0 })).toBe('HẾT HẠN')
  })
  it('alert lạ/rỗng → chuỗi (không vỡ render)', () => {
    expect(typeof alertPillLabel(null)).toBe('string')
    expect(typeof alertPillLabel({})).toBe('string')
  })
})

// ── Helper thuần alertText — câu VI theo 2 mẫu quota / expiry ─────────────────
describe('alertText — câu VI theo mẫu quota / expiry', () => {
  it('quota: chứa contract_no + hospital_name + item_name + used_pct + threshold', () => {
    const t = alertText(quota100)
    expect(t).toContain('HD-2026-001')
    expect(t).toContain('BV Chợ Rẫy')
    expect(t).toContain('Stent mạch vành')
    expect(t).toContain('103.5')
    expect(t).toContain('100')
    // mẫu quota có chữ '% (ngưỡng' theo acceptance
    expect(t).toMatch(/đã dùng .*% \(ngưỡng .*%\)/)
  })
  it("expiry days>=0: chứa 'còn N ngày'", () => {
    const t = alertText(expirySoon)
    expect(t).toContain('HD-2026-002')
    expect(t).toContain('BV Bạch Mai')
    expect(t).toContain('còn 12 ngày')
  })
  it("expiry days<0: chứa 'quá hạn N ngày' (giá trị tuyệt đối)", () => {
    const t = alertText(expiryPast)
    expect(t).toContain('quá hạn 5 ngày')
    expect(t).not.toContain('-5')
  })
  it('alert lạ/rỗng → chuỗi (không vỡ render)', () => {
    expect(typeof alertText(null)).toBe('string')
    expect(typeof alertText({})).toBe('string')
  })
})

// ── Data layer — getQuotaAlerts gọi đúng endpoint (naming contract BE-FE) ─────
describe('M02-3 data layer — getQuotaAlerts url list_quota_alerts', () => {
  it('getQuotaAlerts → createResource url antmed_crm.api.antmed.contract.list_quota_alerts', () => {
    expect(dataSrc).toMatch(/export function getQuotaAlerts/)
    expect(dataSrc).toMatch(/antmed_crm\.api\.antmed\.contract\.list_quota_alerts/)
  })
  it('dùng createResource (đọc dict bọc r.data.data), KHÔNG createListResource', () => {
    expect(dataSrc).toMatch(/import\s*\{\s*createResource\s*\}\s*from\s*'frappe-ui'/)
    expect(dataSrc).not.toMatch(/import[^\n]*createListResource/)
  })
})

// ── Nav — item "Cảnh báo" enabled tới /antmed/alerts (ROLE_NAV.ceo) ──────────
describe('M02-3 nav — entry Cảnh báo (ceo) enabled tới /antmed/alerts', () => {
  it("ROLE_NAV.ceo có item 'ceo-alerts' to=/antmed/alerts enabled=true", () => {
    const item = ROLE_NAV.ceo.find((i) => i.key === 'ceo-alerts')
    expect(item).toMatchObject({
      to: '/antmed/alerts',
      enabled: true,
    })
    expect(item.label).toBeTruthy()
  })
  it('isNavActive: active ở /antmed/alerts, KHÔNG active ở /antmed (dashboard)', () => {
    const item = { to: '/antmed/alerts' }
    expect(isNavActive(item, '/antmed/alerts')).toBe(true)
    expect(isNavActive({ to: '/antmed' }, '/antmed/alerts')).toBe(false)
  })
})

// ── Route — /antmed/alerts đăng ký + guard allow + KHÔNG trùng name ───────────
describe('M02-3 route — /antmed/alerts đăng ký + guard + name uniqueness', () => {
  it('router.js đăng ký route AntmedAlerts → /antmed/alerts (lazy page real-data)', () => {
    expect(routerSrc).toMatch(/path:\s*['"]\/antmed\/alerts['"]/)
    expect(routerSrc).toMatch(/name:\s*['"]AntmedAlerts['"]/)
    expect(routerSrc).toMatch(/import\(['"]@\/pages\/AntmedAlerts\.vue['"]\)/)
  })
  it('name AntmedAlerts là DUY NHẤT', () => {
    const matches = routerSrc.match(/name:\s*['"]AntmedAlerts['"]/g) || []
    expect(matches).toHaveLength(1)
    // Phase 2: mock /admin/audit (AntmedAudit) ĐÃ GỠ — không còn để đối chiếu.
    expect(routerSrc).not.toMatch(/name:\s*['"]AntmedAlerts['"][\s\S]{0,200}name:\s*['"]AntmedAlerts['"]/)
  })
  it('guard: AntMed user + CRM user mở /antmed/alerts KHÔNG redirect', () => {
    expect(shouldRedirectNotPermitted({ path: '/antmed/alerts' }, antmed())).toBe(false)
    expect(shouldRedirectNotPermitted({ path: '/antmed/alerts' }, crm())).toBe(false)
  })
  it('guard: outsider mở /antmed/alerts bị redirect', () => {
    expect(shouldRedirectNotPermitted({ path: '/antmed/alerts' }, outsider())).toBe(true)
  })
})

// ── Page — đọc dict bọc + tri-branch + render khớp mockup A1 ──────────────────
describe('AntmedAlerts.vue — đọc r.data.data + tri-branch + pill+text', () => {
  it('đọc list dict bọc: r.data.data + r.data.total_count (KHÔNG r.data trực tiếp)', () => {
    expect(pageSrc).toMatch(/alerts\.data\?\.data/)
    expect(pageSrc).toMatch(/alerts\.data\?\.total_count/)
  })
  it('tri-branch: loading / error (banner + Thử lại reload) / empty (Không có cảnh báo)', () => {
    expect(pageSrc).toMatch(/alerts\.loading/)
    expect(pageSrc).toMatch(/alerts\.error/)
    expect(pageSrc).toMatch(/Thử lại/)
    expect(pageSrc).toMatch(/alerts\.reload\(\)/)
    expect(pageSrc).toMatch(/Không có cảnh báo/)
    expect(pageSrc).toMatch(/!rows\.length/)
  })
  it('breadcrumb A1: "Trang chủ" › "Cảnh báo điều hành"', () => {
    expect(pageSrc).toMatch(/Trang chủ/)
    expect(pageSrc).toMatch(/Cảnh báo điều hành/)
  })
  it('mỗi dòng dùng helper thuần: alertPillTheme + alertPillLabel + alertText', () => {
    expect(pageSrc).toMatch(/alertPillTheme\(/)
    expect(pageSrc).toMatch(/alertPillLabel\(/)
    expect(pageSrc).toMatch(/alertText\(/)
    expect(pageSrc).toMatch(/import[^\n]*alertPillTheme[^\n]*from\s*'@\/utils\/antmedUi'/)
  })
  it("FE KHÔNG sort lại — render rows theo thứ tự BE (v-for trên 'rows' không .sort/.slice().sort)", () => {
    const code = pageSrc
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .replace(/<!--[\s\S]*?-->/g, '')
      .replace(/^\s*\/\/.*$/gm, '')
    expect(code).not.toMatch(/\.sort\(/)
    expect(code).toMatch(/v-for="[^"]*in rows"/)
  })
  it('pill border-l-4 + nhãn CHỮ (WCAG) qua pillClass/alertPillTheme', () => {
    expect(pageSrc).toMatch(/border-l-4/)
    expect(pageSrc).toMatch(/alertPillLabel\(/)
  })
})

describe('AntmedAlerts.vue — drill-down KHÔNG dead-end + a11y', () => {
  it('click dòng: openContract router.push name AntmedContractDetail params { name: alert.contract }', () => {
    expect(pageSrc).toMatch(/function openContract/)
    const codeNoComments = pageSrc
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .replace(/<!--[\s\S]*?-->/g, '')
      .replace(/^\s*\/\/.*$/gm, '')
    expect(codeNoComments).toMatch(/router\.push\(\s*\{\s*name:\s*['"]AntmedContractDetail['"]/)
    expect(codeNoComments).toMatch(/params:\s*\{\s*name:/)
  })
  it('<li> affordance: role=link + tabindex + @click + @keydown.enter + aria-label', () => {
    expect(pageSrc).toMatch(/role="link"/)
    expect(pageSrc).toMatch(/tabindex/)
    expect(pageSrc).toMatch(/@click="openContract\(/)
    expect(pageSrc).toMatch(/@keydown\.enter/)
    expect(pageSrc).toMatch(/aria-label/)
  })
  it('KHÔNG hardcode mock / KHÔNG status EN raw / KHÔNG createListResource·axios (code, không tính comment)', () => {
    const code = pageSrc
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .replace(/<!--[\s\S]*?-->/g, '')
      .replace(/^\s*\/\/.*$/gm, '')
    expect(code).not.toMatch(/createListResource/)
    expect(code).not.toMatch(/axios|@tanstack\/vue-query|useApi\(/)
    expect(code).not.toMatch(/['"](Active|Pending|Ready|Draft|Expired)['"]/)
  })
})
