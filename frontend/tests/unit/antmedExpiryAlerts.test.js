import { readFileSync } from 'fs'
import path from 'path'
import { ROLE_NAV, isNavActive } from '../../src/data/antmedNav'
import { shouldRedirectNotPermitted } from '../../src/utils/antmedGuard'
import {
  expirySeverityChipTheme,
  expirySeverityChipClass,
  expirySeverityLabel,
  formatExpiryMonthYear,
  pillClass,
} from '../../src/utils/antmedUi'

// M03-4 — màn "Cảnh báo HSD" (Thủ kho, /antmed/warehouse/expiry-alerts, AntmedExpiryAlerts.vue).
// Idiom test = behavior-assert helper THUẦN (antmedUi.js không import frappe-ui → import trực tiếp)
// + content-assert nguồn (router/nav/page/data) cho url & wiring (data/antmed.js KÉO frappe-ui nên
// vitest KHÔNG load được → assert chuỗi nguồn cho url, như antmedConsignment.test.js).

const srcDir = path.resolve(__dirname, '../../src')
const routerSrc = readFileSync(path.join(srcDir, 'router.js'), 'utf8')
const navSrc = readFileSync(path.join(srcDir, 'data/antmedNav.js'), 'utf8')
const pageSrc = readFileSync(
  path.join(srcDir, 'pages/AntmedExpiryAlerts.vue'),
  'utf8',
)
const dataSrc = readFileSync(path.join(srcDir, 'data/antmed.js'), 'utf8')

const antmed = () => ({ isCrmUser: () => false, isAntmedUser: () => true })
const crm = () => ({ isCrmUser: () => true, isAntmedUser: () => false })
const outsider = () => ({ isCrmUser: () => false, isAntmedUser: () => false })

// ── Helper thuần expirySeverityChipTheme — 4 tầng → token (PILL_THEME key) ──────────────
describe('expirySeverityChipTheme — severity BE → token màu (4 tầng)', () => {
  it("expired → danger (đỏ)", () => {
    expect(expirySeverityChipTheme('expired')).toBe('danger')
  })
  it("d30 → danger (đỏ, sát hạn nguy cấp)", () => {
    expect(expirySeverityChipTheme('d30')).toBe('danger')
  })
  it("d60 → warn (cam)", () => {
    expect(expirySeverityChipTheme('d60')).toBe('warn')
  })
  it("d90 → neutral (xám)", () => {
    expect(expirySeverityChipTheme('d90')).toBe('neutral')
  })
  it('giá trị lạ (null/undefined/khác) → neutral (an toàn)', () => {
    expect(expirySeverityChipTheme(null)).toBe('neutral')
    expect(expirySeverityChipTheme(undefined)).toBe('neutral')
    expect(expirySeverityChipTheme('xxx')).toBe('neutral')
  })
})

// ── Helper thuần expirySeverityChipClass — gộp theme → pill class ───────────────────────
describe('expirySeverityChipClass — class chip theo severity (dùng PILL_THEME)', () => {
  it('expired/d30 → class danger', () => {
    expect(expirySeverityChipClass('expired')).toBe(pillClass('danger'))
    expect(expirySeverityChipClass('d30')).toBe(pillClass('danger'))
  })
  it('d60 → class warn; d90 → class neutral', () => {
    expect(expirySeverityChipClass('d60')).toBe(pillClass('warn'))
    expect(expirySeverityChipClass('d90')).toBe(pillClass('neutral'))
  })
})

// ── Helper thuần expirySeverityLabel — nhãn VI 4 tầng ───────────────────────────────────
describe('expirySeverityLabel — nhãn VI mức độ HSD (kèm chữ, WCAG)', () => {
  it("expired → 'Đã hết hạn'", () => {
    expect(expirySeverityLabel('expired')).toBe('Đã hết hạn')
  })
  it("d30 → '≤30 ngày'", () => {
    expect(expirySeverityLabel('d30')).toBe('≤30 ngày')
  })
  it("d60 → '≤60 ngày'", () => {
    expect(expirySeverityLabel('d60')).toBe('≤60 ngày')
  })
  it("d90 → '≤90 ngày'", () => {
    expect(expirySeverityLabel('d90')).toBe('≤90 ngày')
  })
  it('giá trị lạ → fallback chữ VI (không rỗng, không vỡ)', () => {
    expect(typeof expirySeverityLabel(null)).toBe('string')
    expect(expirySeverityLabel(null).length).toBeGreaterThan(0)
  })
})

// ── Helper thuần formatExpiryMonthYear — Date 'yyyy-MM-dd' → 'MM/YYYY' ───────────────────
describe('formatExpiryMonthYear — HSD định dạng MM/YYYY (null-guard, không crash)', () => {
  it("'2027-10-15' → '10/2027'", () => {
    expect(formatExpiryMonthYear('2027-10-15')).toBe('10/2027')
  })
  it("'2026-01-05' → '01/2026' (zero-pad tháng)", () => {
    expect(formatExpiryMonthYear('2026-01-05')).toBe('01/2026')
  })
  it("null/undefined/'' → '' (null-guard)", () => {
    expect(formatExpiryMonthYear(null)).toBe('')
    expect(formatExpiryMonthYear(undefined)).toBe('')
    expect(formatExpiryMonthYear('')).toBe('')
  })
})

// ── Data layer — getExpiryAlerts gọi đúng endpoint MỚI (naming contract BE-FE) ─────────
describe('M03-4 data layer — getExpiryAlerts url expiry_alerts', () => {
  it('getExpiryAlerts → createResource url antmed_crm.api.antmed.inventory.expiry_alerts', () => {
    expect(dataSrc).toMatch(/export function getExpiryAlerts/)
    expect(dataSrc).toMatch(/antmed_crm\.api\.antmed\.inventory\.expiry_alerts/)
  })
  it('nhận opt auto (mirror getConsignmentStock/getDashboardOverview)', () => {
    const block = dataSrc.slice(
      dataSrc.indexOf('export function getExpiryAlerts'),
      dataSrc.indexOf('export function getExpiryAlerts') + 300,
    )
    expect(block).toMatch(/auto/)
  })
  it('dùng createResource (đọc dict RAW), KHÔNG createListResource', () => {
    expect(dataSrc).toMatch(/import\s*\{\s*createResource\s*\}\s*from\s*'frappe-ui'/)
    expect(dataSrc).not.toMatch(/import[^\n]*createListResource/)
  })
})

// ── Nav — ROLE_NAV.warehouse wh-expiry trỏ /antmed/warehouse/expiry-alerts, enabled ────
describe('M03-4 nav — wh-expiry enabled tới /antmed/warehouse/expiry-alerts', () => {
  it("ROLE_NAV.warehouse 'wh-expiry' to=/antmed/warehouse/expiry-alerts, enabled=true, label 'Cảnh báo HSD'", () => {
    const item = ROLE_NAV.warehouse.find((i) => i.key === 'wh-expiry')
    expect(item).toMatchObject({
      to: '/antmed/warehouse/expiry-alerts',
      enabled: true,
      label: 'Cảnh báo HSD',
    })
  })
  it('isNavActive: active ở /antmed/warehouse/expiry-alerts, KHÔNG active ở /antmed', () => {
    const item = { to: '/antmed/warehouse/expiry-alerts' }
    expect(isNavActive(item, '/antmed/warehouse/expiry-alerts')).toBe(true)
    expect(isNavActive({ to: '/antmed' }, '/antmed/warehouse/expiry-alerts')).toBe(
      false,
    )
  })
  it('key wh-expiry DUY NHẤT trong nav warehouse (không trùng key)', () => {
    const keys = ROLE_NAV.warehouse.filter((i) => i.key === 'wh-expiry')
    expect(keys).toHaveLength(1)
  })
})

// ── Route — /antmed/warehouse/expiry-alerts đăng ký, name AntmedExpiryAlerts unique, guard
describe('M03-4 route — /antmed/warehouse/expiry-alerts đăng ký + guard', () => {
  it('router.js đăng ký AntmedExpiryAlerts → /antmed/warehouse/expiry-alerts (lazy page real-data)', () => {
    expect(routerSrc).toMatch(/path:\s*['"]\/antmed\/warehouse\/expiry-alerts['"]/)
    expect(routerSrc).toMatch(/name:\s*['"]AntmedExpiryAlerts['"]/)
    expect(routerSrc).toMatch(
      /import\(['"]@\/pages\/AntmedExpiryAlerts\.vue['"]\)/,
    )
  })
  it('name AntmedExpiryAlerts DUY NHẤT (không trùng)', () => {
    const matches = routerSrc.match(/name:\s*['"]AntmedExpiryAlerts['"]/g) || []
    expect(matches).toHaveLength(1)
  })
  it('meta.role=warehouse ⇒ sidebar Thủ kho', () => {
    const block = routerSrc.slice(
      routerSrc.indexOf("'/antmed/warehouse/expiry-alerts'"),
      routerSrc.indexOf("'/antmed/warehouse/expiry-alerts'") + 260,
    )
    expect(block).toMatch(/role:\s*['"]warehouse['"]/)
  })
  it('guard: AntMed user + CRM user mở route KHÔNG redirect; outsider bị redirect', () => {
    const p = { path: '/antmed/warehouse/expiry-alerts' }
    expect(shouldRedirectNotPermitted(p, antmed())).toBe(false)
    expect(shouldRedirectNotPermitted(p, crm())).toBe(false)
    expect(shouldRedirectNotPermitted(p, outsider())).toBe(true)
  })
})

// ── Page — đọc RAW dict + 4 KPI + 7 cột + chip 4 mức + highlight + tri-branch ───────────
describe('AntmedExpiryAlerts.vue — đọc r.data.{rows,kpis} + tri-branch + 7 cột', () => {
  it('đọc RAW dict: r.data.rows + r.data.kpis (KHÔNG .data.data)', () => {
    expect(pageSrc).toMatch(/\.data\?\.rows/)
    expect(pageSrc).toMatch(/\.data\?\.kpis/)
    // Strip comment/JSDoc trước khi soi .data.data (comment cảnh báo có chứa chuỗi này).
    const code = pageSrc
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .replace(/<!--[\s\S]*?-->/g, '')
      .replace(/^\s*\/\/.*$/gm, '')
    expect(code).not.toMatch(/\.data\.data/)
  })
  it('tri-branch: loading (Đang tải) / error (Thử lại reload) / empty (Không có lot cận date)', () => {
    expect(pageSrc).toMatch(/\.loading/)
    expect(pageSrc).toMatch(/\.error/)
    expect(pageSrc).toMatch(/Đang tải/)
    expect(pageSrc).toMatch(/Thử lại/)
    expect(pageSrc).toMatch(/reload\(\)/)
    expect(pageSrc).toMatch(/Không có lot cận date/)
  })
  it('cột bảng đọc ĐÚNG field BE: sku/item_name/lot/warehouse(_name/_type)/expiry_date/balance_qty/severity', () => {
    expect(pageSrc).toMatch(/row\.sku/)
    expect(pageSrc).toMatch(/row\.item_name/)
    expect(pageSrc).toMatch(/row\.lot/)
    expect(pageSrc).toMatch(/row\.warehouse_name/)
    expect(pageSrc).toMatch(/row\.warehouse_type/)
    expect(pageSrc).toMatch(/row\.expiry_date/)
    expect(pageSrc).toMatch(/row\.balance_qty/)
    expect(pageSrc).toMatch(/row\.severity/)
  })
  it('header 7 cột đủ (VI): SKU / Tên VT / Lot / Kho / HSD / SL còn / Mức độ', () => {
    for (const h of ['SKU', 'Tên VT', 'Lot', 'Kho', 'HSD', 'SL còn', 'Mức độ']) {
      expect(pageSrc).toContain(h)
    }
  })
  it('HSD qua formatExpiryMonthYear; chip qua expirySeverityChipClass + expirySeverityLabel', () => {
    expect(pageSrc).toMatch(/formatExpiryMonthYear\(row\.expiry_date\)/)
    expect(pageSrc).toMatch(/expirySeverityChipClass\(row\.severity\)/)
    expect(pageSrc).toMatch(/expirySeverityLabel\(row\.severity\)/)
    expect(pageSrc).toMatch(/from\s*'@\/utils\/antmedUi'/)
  })
  it("4 KPI card thật: Đã hết hạn / ≤30 ngày / ≤60 ngày / ≤90 ngày bind kpis BE (KHÔNG hardcode)", () => {
    expect(pageSrc).toContain('Đã hết hạn')
    expect(pageSrc).toContain('≤30 ngày')
    expect(pageSrc).toContain('≤60 ngày')
    expect(pageSrc).toContain('≤90 ngày')
    expect(pageSrc).toMatch(/kpis\.expired/)
    expect(pageSrc).toMatch(/kpis\.d30/)
    expect(pageSrc).toMatch(/kpis\.d60/)
    expect(pageSrc).toMatch(/kpis\.d90/)
    expect(pageSrc).toMatch(/AntmedKpiCard/)
  })
  it("highlight bg-red-50 cho dòng severity expired || d30", () => {
    expect(pageSrc).toMatch(/severity === 'expired'/)
    expect(pageSrc).toMatch(/severity === 'd30'/)
    expect(pageSrc).toMatch(/bg-red-50/)
  })
  it('breadcrumb: Trang chủ › Kho › Cảnh báo HSD', () => {
    expect(pageSrc).toContain('Trang chủ')
    expect(pageSrc).toContain('Cảnh báo HSD')
  })
  it('KHÔNG sort lại rows (BE đã sort); KHÔNG hardcode mock; KHÔNG createListResource/axios', () => {
    const code = pageSrc
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .replace(/<!--[\s\S]*?-->/g, '')
      .replace(/^\s*\/\/.*$/gm, '')
    expect(code).not.toMatch(/\.sort\(/)
    expect(code).not.toMatch(/createListResource/)
    expect(code).not.toMatch(/axios|@tanstack\/vue-query|useApi\(/)
    expect(code).not.toMatch(/antmedMock/)
  })
})
