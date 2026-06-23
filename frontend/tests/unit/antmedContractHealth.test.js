import { readFileSync } from 'fs'
import path from 'path'
import { ANTMED_NAV, ROLE_NAV, isNavActive } from '../../src/data/antmedNav'
import { shouldRedirectNotPermitted } from '../../src/utils/antmedGuard'
import {
  healthBarClass,
  expiryLabel,
  BAR_THEME,
} from '../../src/utils/antmedUi'

// M02-2 — màn "Sức khỏe Hợp đồng" (mockup A2, /antmed/contract-health, AntmedContractHealth.vue).
// Idiom test = content-assert nguồn (router/nav/page/data) + behavior-assert helper THUẦN
// (antmedUi.js không import frappe-ui → import trực tiếp được; data/antmed.js KÉO frappe-ui
// nên vitest KHÔNG load được → assert chuỗi nguồn cho url, như antmedContracts.test.js).

const srcDir = path.resolve(__dirname, '../../src')
const routerSrc = readFileSync(path.join(srcDir, 'router.js'), 'utf8')
const navSrc = readFileSync(path.join(srcDir, 'data/antmedNav.js'), 'utf8')
const pageSrc = readFileSync(
  path.join(srcDir, 'pages/AntmedContractHealth.vue'),
  'utf8',
)
const dataSrc = readFileSync(path.join(srcDir, 'data/antmed.js'), 'utf8')

const antmed = () => ({ isCrmUser: () => false, isAntmedUser: () => true })
const crm = () => ({ isCrmUser: () => true, isAntmedUser: () => false })
const outsider = () => ({ isCrmUser: () => false, isAntmedUser: () => false })

// ── Helper thuần expiryLabel — nhãn cảnh báo hết hạn (TDD viết trước) ─────────
describe('expiryLabel — nhãn cảnh báo hết hạn từ days_to_expiry', () => {
  it("d=12 → 'Sắp hết hạn 12 ngày'", () => {
    expect(expiryLabel(12)).toBe('Sắp hết hạn 12 ngày')
  })
  it("d=31 → '' (ngoài ngưỡng 30 ngày, không cảnh báo)", () => {
    expect(expiryLabel(31)).toBe('')
  })
  it("d=0 → 'Sắp hết hạn 0 ngày' (hết hạn hôm nay vẫn cảnh báo)", () => {
    expect(expiryLabel(0)).toBe('Sắp hết hạn 0 ngày')
  })
  it("d=30 → 'Sắp hết hạn 30 ngày' (biên trên inclusive)", () => {
    expect(expiryLabel(30)).toBe('Sắp hết hạn 30 ngày')
  })
  it("d=-3 → 'Đã hết hạn'", () => {
    expect(expiryLabel(-3)).toBe('Đã hết hạn')
  })
  it("null/undefined/NaN → '' (không cảnh báo, không vỡ)", () => {
    expect(expiryLabel(null)).toBe('')
    expect(expiryLabel(undefined)).toBe('')
    expect(expiryLabel('')).toBe('')
    expect(expiryLabel('abc')).toBe('')
  })
})

// ── Helper thuần healthBarClass — map cờ màu BE → class fill ngưỡng ───────────
describe('healthBarClass — map health_color (BE) → class thanh % Quota', () => {
  it("'red' → BAR_THEME.danger (đỏ)", () => {
    expect(healthBarClass('red')).toBe(BAR_THEME.danger)
  })
  it("'orange' → BAR_THEME.warn (cam)", () => {
    expect(healthBarClass('orange')).toBe(BAR_THEME.warn)
  })
  it("'green' → BAR_THEME.default (brand xanh)", () => {
    expect(healthBarClass('green')).toBe(BAR_THEME.default)
  })
  it('cờ lạ/rỗng → default (xanh, không vỡ render)', () => {
    expect(healthBarClass('purple')).toBe(BAR_THEME.default)
    expect(healthBarClass(null)).toBe(BAR_THEME.default)
    expect(healthBarClass(undefined)).toBe(BAR_THEME.default)
  })
})

// ── Data layer — getContractHealth gọi đúng endpoint (naming contract BE-FE) ──
describe('M02-2 data layer — getContractHealth url get_contract_health', () => {
  it('getContractHealth → createResource url antmed_crm.api.antmed.contract.get_contract_health', () => {
    expect(dataSrc).toMatch(/export function getContractHealth/)
    expect(dataSrc).toMatch(
      /antmed_crm\.api\.antmed\.contract\.get_contract_health/,
    )
  })

  it('dùng createResource (đọc dict bọc), KHÔNG createListResource', () => {
    expect(dataSrc).toMatch(
      /import\s*\{\s*createResource\s*\}\s*from\s*'frappe-ui'/,
    )
    expect(dataSrc).not.toMatch(/import[^\n]*createListResource/)
  })
})

// ── Nav — item "Sức khỏe Hợp đồng" enabled tới /antmed/contract-health ───────
describe('M02-2 nav — entry Sức khỏe Hợp đồng enabled tới /antmed/contract-health', () => {
  it('ANTMED_NAV có item contract-health enabled=true, to=/antmed/contract-health', () => {
    const byKey = Object.fromEntries(ANTMED_NAV.map((i) => [i.key, i]))
    expect(byKey['contract-health']).toMatchObject({
      to: '/antmed/contract-health',
      enabled: true,
      label: 'Sức khỏe Hợp đồng',
    })
  })

  it("ROLE_NAV.ceo 'Hợp đồng' (mockup A2) trỏ /antmed/contract-health, enabled=true", () => {
    const ceoContracts = ROLE_NAV.ceo.find((i) => i.key === 'ceo-contracts')
    expect(ceoContracts).toMatchObject({
      to: '/antmed/contract-health',
      enabled: true,
    })
  })

  it('isNavActive: active ở /antmed/contract-health, KHÔNG active ở /antmed (dashboard)', () => {
    const item = { to: '/antmed/contract-health' }
    expect(isNavActive(item, '/antmed/contract-health')).toBe(true)
    expect(isNavActive({ to: '/antmed' }, '/antmed/contract-health')).toBe(
      false,
    )
  })
})

// ── Route — /antmed/contract-health đăng ký + guard allow + KHÔNG trùng name ──
describe('M02-2 route — /antmed/contract-health đăng ký + guard', () => {
  it('router.js đăng ký route AntmedContractHealth → /antmed/contract-health (lazy page real-data)', () => {
    expect(routerSrc).toMatch(/path:\s*['"]\/antmed\/contract-health['"]/)
    expect(routerSrc).toMatch(/name:\s*['"]AntmedContractHealth['"]/)
    expect(routerSrc).toMatch(
      /import\(['"]@\/pages\/AntmedContractHealth\.vue['"]\)/,
    )
  })

  it('name AntmedContractHealth là DUY NHẤT', () => {
    const matches =
      routerSrc.match(/name:\s*['"]AntmedContractHealth['"]/g) || []
    expect(matches).toHaveLength(1)
    // Phase 2: mock /ceo/contract-health (AntmedCeoContractHealthMock) ĐÃ GỠ.
  })

  it('guard: AntMed user + CRM user mở /antmed/contract-health KHÔNG redirect', () => {
    expect(
      shouldRedirectNotPermitted({ path: '/antmed/contract-health' }, antmed()),
    ).toBe(false)
    expect(
      shouldRedirectNotPermitted({ path: '/antmed/contract-health' }, crm()),
    ).toBe(false)
  })

  it('guard: outsider mở /antmed/contract-health bị redirect', () => {
    expect(
      shouldRedirectNotPermitted(
        { path: '/antmed/contract-health' },
        outsider(),
      ),
    ).toBe(true)
  })
})

// ── Page — đọc dict bọc + cột A2 + bar màu health_color + drill-down ─────────
describe('AntmedContractHealth.vue — đọc r.data.data + tri-branch + cột A2', () => {
  it('đọc list dict bọc: r.data.data + r.data.total_count (KHÔNG r.data trực tiếp)', () => {
    expect(pageSrc).toMatch(/health\.data\?\.data/)
    expect(pageSrc).toMatch(/health\.data\?\.total_count/)
  })

  it('tri-branch: loading / error (banner + Thử lại reload) / empty (Chưa có hợp đồng)', () => {
    expect(pageSrc).toMatch(/health\.loading/)
    expect(pageSrc).toMatch(/health\.error/)
    expect(pageSrc).toMatch(/Thử lại/)
    expect(pageSrc).toMatch(/health\.reload\(\)/)
    // empty branch VI acceptance đúng chuỗi 'Chưa có hợp đồng'
    expect(pageSrc).toMatch(/Chưa có hợp đồng/)
    expect(pageSrc).toMatch(/!rows\.length/)
  })

  it('breadcrumb A2: "Trang chủ" › "Hợp đồng & Gói thầu"', () => {
    expect(pageSrc).toMatch(/Trang chủ/)
    expect(pageSrc).toMatch(/Hợp đồng & Gói thầu/)
  })

  it('cột bảng A2 đọc ĐÚNG field BE: contract_no/hospital_name/valid_to/total_value/quota_used_pct/health_color/status', () => {
    expect(pageSrc).toMatch(/row\.contract_no/)
    expect(pageSrc).toMatch(/row\.hospital_name/)
    expect(pageSrc).toMatch(/row\.valid_to/)
    expect(pageSrc).toMatch(/row\.total_value/)
    expect(pageSrc).toMatch(/row\.quota_used_pct/)
    expect(pageSrc).toMatch(/row\.health_color/)
    expect(pageSrc).toMatch(/row\.status/)
  })

  it('header cột A2 đủ: Số HĐ / Bệnh viện / Hết hạn / Giá trị / % Quota / Trạng thái / Thao tác', () => {
    for (const h of [
      'Số HĐ',
      'Bệnh viện',
      'Hết hạn',
      'Giá trị',
      '% Quota',
      'Trạng thái',
      'Thao tác',
    ]) {
      expect(pageSrc).toContain(h)
    }
  })

  it('thanh % Quota: width = clampPct(quota_used_pct), màu = healthBarClass(row.health_color)', () => {
    expect(pageSrc).toMatch(/healthBarClass\(row\.health_color\)/)
    expect(pageSrc).toMatch(/clampPct\(row\.quota_used_pct\)/)
    // import helper thuần (3 nhánh màu green/orange/red sống ở antmedUi).
    expect(pageSrc).toMatch(/healthBarClass/)
    expect(pageSrc).toMatch(
      /import\s*\{[^}]*expiryLabel[^}]*\}\s*from\s*'@\/utils\/antmedUi'/,
    )
  })

  it("chip cảnh báo: expiryLabel(row.days_to_expiry) (đỏ) — 'Sắp hết hạn N ngày' / 'Đã hết hạn'", () => {
    expect(pageSrc).toMatch(/expiryLabel\(row\.days_to_expiry\)/)
    // chip dùng nền đỏ (token red) khi có nhãn.
    expect(pageSrc).toMatch(/bg-red-100/)
  })

  it('Hết hạn định dạng dd/MM/yyyy qua canon fmtDate (alias formatDate, gom hết inline)', () => {
    // Vòng 2 CONSOLIDATE: formatDate inline → import canon fmtDate (dd/MM/yyyy) từ antmedUi.
    expect(pageSrc).toMatch(
      /import\s*\{[^}]*fmtDate as formatDate[^}]*\}\s*from\s*'@\/utils\/antmedUi'/,
    )
    expect(pageSrc).toMatch(/formatDate\(row\.valid_to\)/)
    // KHÔNG còn tự định nghĩa formatDate inline trong page.
    expect(pageSrc).not.toMatch(/function formatDate\(/)
  })

  it('status chip qua theme map (KHÔNG raw màu) + label chữ (WCAG: không chỉ màu)', () => {
    expect(pageSrc).toMatch(/statusTheme\(row\.status\)/)
    expect(pageSrc).toMatch(/CONTRACT_WORKFLOW_THEME/)
    expect(pageSrc).toMatch(/:label="row\.status"/)
  })
})

describe('AntmedContractHealth.vue — drill-down KHÔNG dead-end + a11y', () => {
  it('row-click + nút Chi tiết: openContract router.push name AntmedContractDetail params name', () => {
    expect(pageSrc).toMatch(/function openContract/)
    const codeNoComments = pageSrc
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .replace(/<!--[\s\S]*?-->/g, '')
      .replace(/^\s*\/\/.*$/gm, '')
    expect(codeNoComments).toMatch(
      /router\.push\(\s*\{\s*name:\s*['"]AntmedContractDetail['"]/,
    )
    expect(codeNoComments).toMatch(/params:\s*\{\s*name\s*\}/)
  })

  it('<tr> affordance click: cursor-pointer + role=link + tabindex + @click + @keydown.enter + aria-label', () => {
    const tbody = pageSrc
      .slice(pageSrc.indexOf('<tbody>'), pageSrc.indexOf('</tbody>') + 8)
      .replace(/<!--[\s\S]*?-->/g, '')
    expect(tbody).toMatch(/@click="openContract\(row\.name\)"/)
    expect(tbody).toMatch(/@keydown\.enter/)
    expect(tbody).toMatch(/role="link"/)
    expect(tbody).toMatch(/cursor-pointer/)
    expect(tbody).toMatch(/tabindex/)
    expect(tbody).toMatch(/aria-label/)
    // nút Chi tiết stopPropagation (không double-fire row click).
    expect(tbody).toMatch(/@click\.stop="openContract\(row\.name\)"/)
    expect(tbody).toMatch(/Chi tiết/)
  })

  it('KHÔNG hardcode mock / KHÔNG status EN raw / KHÔNG createListResource·axios (code, không tính comment)', () => {
    // Gỡ comment JS (/* */, //) + comment HTML (<!-- -->) rồi mới assert di sản stack cũ vắng mặt.
    const code = pageSrc
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .replace(/<!--[\s\S]*?-->/g, '')
      .replace(/^\s*\/\/.*$/gm, '')
    expect(code).not.toMatch(/createListResource/)
    expect(code).not.toMatch(/axios|@tanstack\/vue-query|useApi\(/)
    // KHÔNG để lộ status EN (Active/Pending/Ready/Draft…) trong template.
    expect(code).not.toMatch(/['"](Active|Pending|Ready|Draft|Expired)['"]/)
  })
})
