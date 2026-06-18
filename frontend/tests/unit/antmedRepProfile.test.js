import { readFileSync } from 'fs'
import path from 'path'
import {
  repStatusChipClass,
  formatJoinDate,
  formatVnMoney,
  pillClass,
  fmtDate,
} from '../../src/utils/antmedUi'

// M10-3 — màn "Hồ sơ NV kinh doanh" (Trưởng phòng KD, /antmed/sales/team/:owner, AntmedRepProfile.vue).
// Drill-down 1 NV từ bảng roster B2 → trang chi tiết. Idiom test = behavior-assert helper THUẦN
// (antmedUi.js không import frappe-ui → import trực tiếp) + content-assert nguồn (router/page/data)
// cho url & wiring (data/antmed.js KÉO frappe-ui nên vitest KHÔNG load được → assert chuỗi nguồn,
// như antmedTeam.test.js).

const srcDir = path.resolve(__dirname, '../../src')
const routerSrc = readFileSync(path.join(srcDir, 'router.js'), 'utf8')
const pageSrc = readFileSync(path.join(srcDir, 'pages/AntmedRepProfile.vue'), 'utf8')
const teamSrc = readFileSync(path.join(srcDir, 'pages/AntmedTeam.vue'), 'utf8')
const dataSrc = readFileSync(path.join(srcDir, 'data/antmed.js'), 'utf8')

// ── Helper thuần repStatusChipClass — status_theme BE (ok/danger/info) → pill class ──────
describe('repStatusChipClass — status_theme BE → pill class (tái dùng pillClass)', () => {
  it("'ok' (Won) → pill ok (xanh)", () => {
    expect(repStatusChipClass('ok')).toBe(pillClass('ok'))
  })
  it("'danger' (Lost) → pill danger (đỏ)", () => {
    expect(repStatusChipClass('danger')).toBe(pillClass('danger'))
  })
  it("'info' (Open/Ongoing) → pill info (xanh dương)", () => {
    expect(repStatusChipClass('info')).toBe(pillClass('info'))
  })
  it('theme lạ/rỗng → neutral (an toàn, không vỡ)', () => {
    expect(repStatusChipClass(null)).toBe(pillClass('neutral'))
    expect(repStatusChipClass(undefined)).toBe(pillClass('neutral'))
    expect(repStatusChipClass('')).toBe(pillClass('neutral'))
  })
})

// ── Helper thuần formatJoinDate — ngày vào làm (joined_on) → dd/MM/yyyy / '—' ────────────
describe('formatJoinDate — ngày vào làm (User.creation) → dd/MM/yyyy', () => {
  it("ISO 'yyyy-MM-dd' → dd/MM/yyyy (== fmtDate)", () => {
    expect(formatJoinDate('2023-04-15')).toBe('15/04/2023')
    expect(formatJoinDate('2023-04-15')).toBe(fmtDate('2023-04-15'))
  })
  it("datetime ISO → tách ngày dd/MM/yyyy", () => {
    expect(formatJoinDate('2022-12-01 09:30:00')).toBe('01/12/2022')
  })
  it('null/undefined/rỗng → — (KHÔNG bịa ngày)', () => {
    expect(formatJoinDate(null)).toBe('—')
    expect(formatJoinDate(undefined)).toBe('—')
    expect(formatJoinDate('')).toBe('—')
  })
})

// ── Data layer — getRepProfile gọi đúng endpoint MỚI (naming contract BE-FE) ─────────────
describe('M10-3 data layer — getRepProfile url rep_profile', () => {
  it('getRepProfile → createResource url antmed_crm.api.antmed.sales_team.rep_profile', () => {
    expect(dataSrc).toMatch(/export function getRepProfile/)
    expect(dataSrc).toMatch(/antmed_crm\.api\.antmed\.sales_team\.rep_profile/)
  })
  it('method GET + truyền params.owner (param scalar)', () => {
    const idx = dataSrc.indexOf('export function getRepProfile')
    const block = dataSrc.slice(idx, idx + 500)
    expect(block).toMatch(/method:\s*'GET'/)
    expect(block).toMatch(/params:\s*\{\s*owner\s*\}/)
    expect(block).toMatch(/auto/)
    expect(block).toMatch(/onError/)
  })
  it('signature getRepProfile(owner, { auto, onError }) — owner là arg đầu', () => {
    expect(dataSrc).toMatch(/getRepProfile\(owner,\s*\{[^)]*auto[^)]*\}\s*=\s*\{\}\)/)
  })
  it('dùng createResource (đọc dict RAW), KHÔNG createListResource', () => {
    expect(dataSrc).not.toMatch(/import[^\n]*createListResource/)
  })
})

// ── Route — /antmed/sales/team/:owner đăng ký, name AntmedRepProfile unique, props ───────
describe('M10-3 route — /antmed/sales/team/:owner real-page (drill-down)', () => {
  it('router.js đăng ký AntmedRepProfile → /antmed/sales/team/:owner (lazy page real-data)', () => {
    expect(routerSrc).toMatch(/path:\s*['"]\/antmed\/sales\/team\/:owner['"]/)
    expect(routerSrc).toMatch(/name:\s*['"]AntmedRepProfile['"]/)
    expect(routerSrc).toMatch(/import\(['"]@\/pages\/AntmedRepProfile\.vue['"]\)/)
  })
  it('route có props:true (nhận :owner làm prop) + antmedShell', () => {
    const idx = routerSrc.indexOf("'/antmed/sales/team/:owner'")
    const block = routerSrc.slice(idx, idx + 320)
    expect(block).toMatch(/props:\s*true/)
    expect(block).toMatch(/antmedShell:\s*true/)
    expect(block).toMatch(/role:\s*['"]sales['"]/)
  })
  it('name AntmedRepProfile DUY NHẤT', () => {
    const matches = routerSrc.match(/name:\s*['"]AntmedRepProfile['"]/g) || []
    expect(matches).toHaveLength(1)
  })
  it('route /antmed/sales/team/:owner thuộc nhóm /antmed (KHÔNG /sales mock)', () => {
    expect(routerSrc).toMatch(/['"]\/antmed\/sales\/team\/:owner['"]/)
    // KHÔNG đăng ký dưới prefix mock /sales/team/:owner.
    expect(routerSrc).not.toMatch(/['"]\/sales\/team\/:owner['"]/)
  })
})

// ── Regression — AntmedTeam dòng NV là link tới /antmed/sales/team/<owner> encode đúng ───
describe('M10-3 regression — AntmedTeam.vue link drill-down', () => {
  it('dòng NV bọc RouterLink :to /antmed/sales/team/${encodeURIComponent(row.deal_owner)}', () => {
    expect(teamSrc).toMatch(/RouterLink/)
    expect(teamSrc).toMatch(
      /\/antmed\/sales\/team\/\$\{encodeURIComponent\(row\.deal_owner\)\}/,
    )
  })
  it('link có aria-label "Xem hồ sơ NV" (a11y) + hiển thị full_name (KHÔNG email)', () => {
    expect(teamSrc).toMatch(/aria-label/)
    expect(teamSrc).toMatch(/Xem hồ sơ NV/)
    expect(teamSrc).toMatch(/row\.full_name/)
    // KHÔNG render row.deal_owner (email) làm text hiển thị (chỉ trong url encode).
    expect(teamSrc).not.toMatch(/\{\{\s*row\.deal_owner\s*\}\}/)
  })
})

// ── Page — đọc RAW dict + card hồ sơ + 3 KPI + bảng deals + tri-branch ───────────────────
describe('AntmedRepProfile.vue — đọc r.data.{profile,kpi,deals} + tri-branch + KPI + bảng', () => {
  it('đọc RAW dict: r.data.profile + r.data.kpi + r.data.deals (KHÔNG .data.data)', () => {
    expect(pageSrc).toMatch(/\.data\?\.profile/)
    expect(pageSrc).toMatch(/\.data\?\.kpi/)
    expect(pageSrc).toMatch(/\.data\?\.deals/)
    const code = pageSrc
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .replace(/<!--[\s\S]*?-->/g, '')
      .replace(/^\s*\/\/.*$/gm, '')
    expect(code).not.toMatch(/\.data\.data/)
  })
  it('tri-branch: loading (Đang tải) / error (Lỗi tải hồ sơ + Thử lại reload) / empty deals', () => {
    expect(pageSrc).toMatch(/\.loading/)
    expect(pageSrc).toMatch(/\.error/)
    expect(pageSrc).toMatch(/Đang tải/)
    expect(pageSrc).toMatch(/Lỗi tải hồ sơ/)
    expect(pageSrc).toMatch(/Thử lại/)
    expect(pageSrc).toMatch(/reload\(\)/)
    expect(pageSrc).toMatch(/Chưa có deal phụ trách/)
  })
  it('card Hồ sơ: full_name + ngày vào làm (formatJoinDate joined_on) + chips roles', () => {
    expect(pageSrc).toMatch(/profile\.full_name/)
    expect(pageSrc).toMatch(/formatJoinDate\(profile\.joined_on\)/)
    expect(pageSrc).toMatch(/profile\.roles/)
    expect(pageSrc).toMatch(/Ngày vào làm/)
    // roles không có nguồn → empty-state (KHÔNG bịa).
    expect(pageSrc).toMatch(/Chưa có thông tin vai trò/)
  })
  it('KHÔNG render email thô (deal_owner) trên màn — chỉ full_name', () => {
    expect(pageSrc).not.toMatch(/\{\{\s*profile\.deal_owner\s*\}\}/)
    expect(pageSrc).not.toMatch(/\{\{\s*owner\s*\}\}/)
  })
  it('3 ô KPI: DS tháng (formatVnMoney month_sales) / Đơn mở (open_deals) / SLA đúng giờ', () => {
    expect(pageSrc).toMatch(/formatVnMoney\(kpi\.month_sales\)/)
    expect(pageSrc).toMatch(/kpi\.open_deals/)
    expect(pageSrc).toMatch(/kpi\.sla_ontime_pct/)
    expect(pageSrc).toMatch(/AntmedKpiCard/)
    expect(pageSrc).toContain('SLA đúng giờ')
  })
  it('bảng deals: organization / territory / deal_value(formatVnMoney) / status-chip màu', () => {
    expect(pageSrc).toMatch(/row\.organization/)
    expect(pageSrc).toMatch(/row\.territory/)
    expect(pageSrc).toMatch(/formatVnMoney\(row\.deal_value\)/)
    expect(pageSrc).toMatch(/repStatusChipClass\(row\.status_theme\)/)
    expect(pageSrc).toMatch(/row\.status/)
    expect(pageSrc).toMatch(/from\s*'@\/utils\/antmedUi'/)
  })
  it("nhãn VI: 'Hồ sơ' + 'Khách hàng phụ trách' + 'SLA đúng giờ'", () => {
    expect(pageSrc).toContain('Hồ sơ')
    expect(pageSrc).toContain('Khách hàng phụ trách')
    expect(pageSrc).toContain('SLA đúng giờ')
  })
  it('back-link về /antmed/sales/team', () => {
    expect(pageSrc).toMatch(/to="\/antmed\/sales\/team"/)
  })
  it('KHÔNG sort/reduce/aggregate FE (BE đã sort/tính); KHÔNG createListResource/axios/mock', () => {
    const code = pageSrc
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .replace(/<!--[\s\S]*?-->/g, '')
      .replace(/^\s*\/\/.*$/gm, '')
    expect(code).not.toMatch(/\.sort\(/)
    expect(code).not.toMatch(/\.reduce\(/)
    expect(code).not.toMatch(/createListResource/)
    expect(code).not.toMatch(/axios|@tanstack\/vue-query|useApi\(/)
    expect(code).not.toMatch(/antmedMock/)
  })
})
