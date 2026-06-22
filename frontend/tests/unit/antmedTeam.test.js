import { readFileSync } from 'fs'
import path from 'path'
import { ROLE_NAV, isNavActive } from '../../src/data/antmedNav'
import { shouldRedirectNotPermitted } from '../../src/utils/antmedGuard'
import {
  teamBarClass,
  teamAlertChipClass,
  teamAlertLabel,
  barFillClass,
  pillClass,
} from '../../src/utils/antmedUi'

// M10-1 — màn "Quản lý Đội ngũ" (Trưởng phòng KD, /antmed/sales/team, AntmedTeam.vue).
// Idiom test = behavior-assert helper THUẦN (antmedUi.js không import frappe-ui → import trực tiếp)
// + content-assert nguồn (router/nav/page/data) cho url & wiring (data/antmed.js KÉO frappe-ui nên
// vitest KHÔNG load được → assert chuỗi nguồn cho url, như antmedExpiryAlerts.test.js).

const srcDir = path.resolve(__dirname, '../../src')
const routerSrc = readFileSync(path.join(srcDir, 'router.js'), 'utf8')
const navSrc = readFileSync(path.join(srcDir, 'data/antmedNav.js'), 'utf8')
const pageSrc = readFileSync(path.join(srcDir, 'pages/AntmedTeam.vue'), 'utf8')
const dataSrc = readFileSync(path.join(srcDir, 'data/antmed.js'), 'utf8')

const antmed = () => ({ isCrmUser: () => false, isAntmedUser: () => true })
const crm = () => ({ isCrmUser: () => true, isAntmedUser: () => false })
const outsider = () => ({ isCrmUser: () => false, isAntmedUser: () => false })

// ── Helper thuần teamBarClass — bar_theme BE (green/warn/danger) → class fill ───────────
describe('teamBarClass — bar_theme BE → class fill (tái dùng BAR_THEME)', () => {
  it("green → class default (brand teal, == barFillClass('default'))", () => {
    expect(teamBarClass('green')).toBe(barFillClass('default'))
  })
  it('warn → class warn (cam)', () => {
    expect(teamBarClass('warn')).toBe(barFillClass('warn'))
  })
  it('danger → class danger (đỏ)', () => {
    expect(teamBarClass('danger')).toBe(barFillClass('danger'))
  })
  it('theme lạ/rỗng → default (an toàn, không vỡ)', () => {
    expect(teamBarClass(null)).toBe(barFillClass('default'))
    expect(teamBarClass(undefined)).toBe(barFillClass('default'))
    expect(teamBarClass('xxx')).toBe(barFillClass('default'))
  })
})

// ── Helper thuần teamAlertChipClass — 'DS thấp' → danger pill; '' → '' (no chip) ────────
describe('teamAlertChipClass — chip cảnh báo doanh số (3 nhánh)', () => {
  it("'DS thấp' → class pill danger", () => {
    expect(teamAlertChipClass('DS thấp')).toBe(pillClass('danger'))
  })
  it("'' (rỗng) → '' (KHÔNG render chip)", () => {
    expect(teamAlertChipClass('')).toBe('')
  })
  it('null/undefined → empty string (KHÔNG render chip)', () => {
    expect(teamAlertChipClass(null)).toBe('')
    expect(teamAlertChipClass(undefined)).toBe('')
  })
})

// ── Helper thuần teamAlertLabel — hiển thị chuỗi VI BE, rỗng → '' ───────────────────────
describe('teamAlertLabel — nhãn VI chip cảnh báo (3 nhánh)', () => {
  it("'DS thấp' → 'DS thấp' (hiển thị thẳng chuỗi VI BE)", () => {
    expect(teamAlertLabel('DS thấp')).toBe('DS thấp')
  })
  it("'' → '' (không render)", () => {
    expect(teamAlertLabel('')).toBe('')
  })
  it('null/undefined → empty string (không render)', () => {
    expect(teamAlertLabel(null)).toBe('')
    expect(teamAlertLabel(undefined)).toBe('')
  })
})

// ── Data layer — getTeamRoster gọi đúng endpoint MỚI (naming contract BE-FE) ────────────
describe('M10-1 data layer — getTeamRoster url team_roster', () => {
  it('getTeamRoster → createResource url antmed_crm.api.antmed.sales_team.team_roster', () => {
    expect(dataSrc).toMatch(/export function getTeamRoster/)
    expect(dataSrc).toMatch(/antmed_crm\.api\.antmed\.sales_team\.team_roster/)
  })
  it('nhận opt auto + method GET (endpoint không params → tránh 403 POST)', () => {
    const idx = dataSrc.indexOf('export function getTeamRoster')
    const block = dataSrc.slice(idx, idx + 400)
    expect(block).toMatch(/auto/)
    expect(block).toMatch(/method:\s*'GET'/)
  })
  it('dùng createResource (đọc dict RAW), KHÔNG createListResource', () => {
    expect(dataSrc).toMatch(
      /import\s*\{\s*createResource\s*\}\s*from\s*'frappe-ui'/,
    )
    expect(dataSrc).not.toMatch(/import[^\n]*createListResource/)
  })
})

// ── Nav — ROLE_NAV.sales sales-team trỏ /antmed/sales/team, enabled ─────────────────────
describe('M10-1 nav — sales-team enabled tới /antmed/sales/team', () => {
  it("ROLE_NAV.sales 'sales-team' to=/antmed/sales/team, enabled=true, label 'Đội ngũ'", () => {
    const item = ROLE_NAV.sales.find((i) => i.key === 'sales-team')
    expect(item).toMatchObject({
      to: '/antmed/sales/team',
      enabled: true,
      label: 'Đội ngũ',
    })
  })
  it('isNavActive: active ở /antmed/sales/team, KHÔNG active ở /antmed', () => {
    const item = { to: '/antmed/sales/team' }
    expect(isNavActive(item, '/antmed/sales/team')).toBe(true)
    expect(isNavActive({ to: '/antmed' }, '/antmed/sales/team')).toBe(false)
  })
  it('key sales-team DUY NHẤT trong nav sales (không trùng key)', () => {
    const keys = ROLE_NAV.sales.filter((i) => i.key === 'sales-team')
    expect(keys).toHaveLength(1)
  })
  it('thứ tự sidebar sales khớp mockup B (Điều phối/Duyệt/Đội ngũ/...)', () => {
    const keys = ROLE_NAV.sales.map((i) => i.key)
    expect(keys.indexOf('sales-dispatch')).toBeLessThan(
      keys.indexOf('sales-approvals'),
    )
    expect(keys.indexOf('sales-approvals')).toBeLessThan(
      keys.indexOf('sales-team'),
    )
  })
})

// ── Route — /antmed/sales/team đăng ký, name AntmedTeam unique, mock đổi AntmedTeamMock ──
describe('M10-1 route — /antmed/sales/team real-page + mock renamed', () => {
  it('router.js đăng ký AntmedTeam → /antmed/sales/team (lazy page real-data)', () => {
    expect(routerSrc).toMatch(/path:\s*['"]\/antmed\/sales\/team['"]/)
    expect(routerSrc).toMatch(/name:\s*['"]AntmedTeam['"]/)
    expect(routerSrc).toMatch(/import\(['"]@\/pages\/AntmedTeam\.vue['"]\)/)
  })
  it('name AntmedTeam DUY NHẤT (mock cũ đã đổi AntmedTeamMock)', () => {
    const matches = routerSrc.match(/name:\s*['"]AntmedTeam['"]/g) || []
    expect(matches).toHaveLength(1)
  })
  // Phase 2: mock prototype /sales/team ĐÃ GỠ (chỉ còn /antmed/sales/team thật).
  it('meta.role=sales ⇒ sidebar Trưởng KD', () => {
    const idx = routerSrc.indexOf("'/antmed/sales/team'")
    const block = routerSrc.slice(idx, idx + 220)
    expect(block).toMatch(/role:\s*['"]sales['"]/)
  })
  it('guard: AntMed user + CRM user mở route KHÔNG redirect; outsider bị redirect', () => {
    const p = { path: '/antmed/sales/team' }
    expect(shouldRedirectNotPermitted(p, antmed())).toBe(false)
    expect(shouldRedirectNotPermitted(p, crm())).toBe(false)
    expect(shouldRedirectNotPermitted(p, outsider())).toBe(true)
  })
})

// ── Page — đọc RAW dict + 3 KPI + 6 cột + chip điều kiện + tri-branch ────────────────────
describe('AntmedTeam.vue — đọc r.data.{rows,kpis} + tri-branch + 6 cột + 3 KPI', () => {
  it('đọc RAW dict: r.data.rows + r.data.kpis (KHÔNG .data.data)', () => {
    expect(pageSrc).toMatch(/\.data\?\.rows/)
    expect(pageSrc).toMatch(/\.data\?\.kpis/)
    const code = pageSrc
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .replace(/<!--[\s\S]*?-->/g, '')
      .replace(/^\s*\/\/.*$/gm, '')
    expect(code).not.toMatch(/\.data\.data/)
  })
  it('tri-branch: loading (Đang tải) / error (Thử lại reload) / empty (Chưa có dữ liệu đội ngũ)', () => {
    expect(pageSrc).toMatch(/\.loading/)
    expect(pageSrc).toMatch(/\.error/)
    expect(pageSrc).toMatch(/Đang tải/)
    expect(pageSrc).toMatch(/Thử lại/)
    expect(pageSrc).toMatch(/reload\(\)/)
    expect(pageSrc).toMatch(/Chưa có dữ liệu đội ngũ/)
  })
  it('cột bảng đọc ĐÚNG field BE: full_name/territory/month_sales/open_deals/sla_ontime_pct/bar_theme/sales_pct/alert', () => {
    expect(pageSrc).toMatch(/row\.full_name/)
    expect(pageSrc).toMatch(/row\.territory/)
    expect(pageSrc).toMatch(/row\.month_sales/)
    expect(pageSrc).toMatch(/row\.open_deals/)
    expect(pageSrc).toMatch(/row\.sla_ontime_pct/)
    expect(pageSrc).toMatch(/row\.bar_theme/)
    expect(pageSrc).toMatch(/row\.sales_pct/)
    expect(pageSrc).toMatch(/row\.alert/)
  })
  it('header 6 cột đủ (VI): NV / Tuyến BV / DS tháng / Số deal mở / SLA đúng giờ / Cảnh báo', () => {
    for (const h of [
      'NV',
      'Tuyến BV',
      'DS tháng',
      'Số deal mở',
      'SLA đúng giờ',
      'Cảnh báo',
    ]) {
      expect(pageSrc).toContain(h)
    }
  })
  it('DS tháng qua formatVnMoney + bar teamBarClass(row.bar_theme); chip qua teamAlertChipClass/teamAlertLabel', () => {
    expect(pageSrc).toMatch(/formatVnMoney\(row\.month_sales\)/)
    expect(pageSrc).toMatch(/teamBarClass\(row\.bar_theme\)/)
    expect(pageSrc).toMatch(/teamAlertChipClass\(row\.alert\)/)
    expect(pageSrc).toMatch(/teamAlertLabel\(row\.alert\)/)
    expect(pageSrc).toMatch(/from\s*'@\/utils\/antmedUi'/)
  })
  it('chip Cảnh báo chỉ render khi alert khác rỗng (v-if teamAlertLabel)', () => {
    expect(pageSrc).toMatch(/v-if="teamAlertLabel\(row\.alert\)"/)
  })
  it('3 KPI card thật: Số NV / DS tháng (formatVnMoney) / SLA đúng giờ TB bind kpis BE (KHÔNG hardcode)', () => {
    expect(pageSrc).toMatch(/kpis\.total_reps/)
    expect(pageSrc).toMatch(/formatVnMoney\(kpis\.total_month_sales\)/)
    expect(pageSrc).toMatch(/kpis\.avg_sla/)
    expect(pageSrc).toMatch(/AntmedKpiCard/)
  })
  it('a11y: thanh DS tháng có role=progressbar + aria-valuenow=sales_pct', () => {
    expect(pageSrc).toMatch(/role="progressbar"/)
    expect(pageSrc).toMatch(/aria-valuenow/)
    expect(pageSrc).toMatch(/row\.sales_pct/)
  })
  it('breadcrumb: Trang chủ › Đội ngũ; tiêu đề Quản lý Đội ngũ', () => {
    expect(pageSrc).toContain('Trang chủ')
    expect(pageSrc).toContain('Đội ngũ')
    expect(pageSrc).toContain('Quản lý Đội ngũ')
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
