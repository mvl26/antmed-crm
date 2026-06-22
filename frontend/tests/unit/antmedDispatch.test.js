import { readFileSync } from 'fs'
import path from 'path'
import { ROLE_NAV, isNavActive } from '../../src/data/antmedNav'
import { shouldRedirectNotPermitted } from '../../src/utils/antmedGuard'
import { dispatchBarClass, barFillClass } from '../../src/utils/antmedUi'

// M10-2 — màn "Bảng điều phối" (Trưởng phòng KD, /antmed/sales/dispatch, AntmedDispatch.vue).
// Kanban READ-ONLY pipeline gói thầu: group CRM Deal theo CRM Deal Status (lane), KHÔNG drag-drop.
// Idiom test = behavior-assert helper THUẦN (antmedUi.js không import frappe-ui → import trực tiếp)
// + content-assert nguồn (router/nav/page/data) cho url & wiring (data/antmed.js KÉO frappe-ui nên
// vitest KHÔNG load được → assert chuỗi nguồn cho url, như antmedTeam.test.js).

const srcDir = path.resolve(__dirname, '../../src')
const routerSrc = readFileSync(path.join(srcDir, 'router.js'), 'utf8')
const navSrc = readFileSync(path.join(srcDir, 'data/antmedNav.js'), 'utf8')
const pageSrc = readFileSync(
  path.join(srcDir, 'pages/AntmedDispatch.vue'),
  'utf8',
)
const dataSrc = readFileSync(path.join(srcDir, 'data/antmed.js'), 'utf8')

const antmed = () => ({ isCrmUser: () => false, isAntmedUser: () => true })
const crm = () => ({ isCrmUser: () => true, isAntmedUser: () => false })
const outsider = () => ({ isCrmUser: () => false, isAntmedUser: () => false })

// ── Helper thuần dispatchBarClass — bar_theme BE (green/warn/danger) → class fill ───────
describe('dispatchBarClass — bar_theme BE → class fill (3 nhánh, tái dùng BAR_THEME)', () => {
  it("green → class default (brand teal, == barFillClass('default'))", () => {
    expect(dispatchBarClass('green')).toBe(barFillClass('default'))
  })
  it('warn → class warn (cam)', () => {
    expect(dispatchBarClass('warn')).toBe(barFillClass('warn'))
  })
  it('danger → class danger (đỏ)', () => {
    expect(dispatchBarClass('danger')).toBe(barFillClass('danger'))
  })
  it('theme lạ/rỗng → default (an toàn, không vỡ)', () => {
    expect(dispatchBarClass(null)).toBe(barFillClass('default'))
    expect(dispatchBarClass(undefined)).toBe(barFillClass('default'))
    expect(dispatchBarClass('xxx')).toBe(barFillClass('default'))
  })
})

// ── Data layer — getDispatchBoard gọi đúng endpoint MỚI (naming contract BE-FE) ─────────
describe('M10-2 data layer — getDispatchBoard url dispatch_board', () => {
  it('getDispatchBoard → createResource url antmed_crm.api.antmed.sales_team.dispatch_board', () => {
    expect(dataSrc).toMatch(/export function getDispatchBoard/)
    expect(dataSrc).toMatch(
      /antmed_crm\.api\.antmed\.sales_team\.dispatch_board/,
    )
  })
  it('nhận opt auto + method GET (endpoint không params → tránh 403 POST)', () => {
    const idx = dataSrc.indexOf('export function getDispatchBoard')
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

// ── Nav — ROLE_NAV.sales sales-dispatch trỏ /antmed/sales/dispatch, enabled ─────────────
describe('M10-2 nav — sales-dispatch enabled tới /antmed/sales/dispatch', () => {
  it("ROLE_NAV.sales 'sales-dispatch' to=/antmed/sales/dispatch, enabled=true, label 'Điều phối'", () => {
    const item = ROLE_NAV.sales.find((i) => i.key === 'sales-dispatch')
    expect(item).toMatchObject({
      to: '/antmed/sales/dispatch',
      enabled: true,
      label: 'Điều phối',
    })
  })
  it('KHÔNG còn dead-link: sales-dispatch enabled=true (không render "Sắp có")', () => {
    const item = ROLE_NAV.sales.find((i) => i.key === 'sales-dispatch')
    expect(item.enabled).toBe(true)
  })
  it('isNavActive: active ở /antmed/sales/dispatch, KHÔNG active ở /antmed', () => {
    const item = { to: '/antmed/sales/dispatch' }
    expect(isNavActive(item, '/antmed/sales/dispatch')).toBe(true)
    expect(isNavActive({ to: '/antmed' }, '/antmed/sales/dispatch')).toBe(false)
  })
  it('key sales-dispatch DUY NHẤT trong nav sales (không trùng key)', () => {
    const keys = ROLE_NAV.sales.filter((i) => i.key === 'sales-dispatch')
    expect(keys).toHaveLength(1)
  })
  it('thứ tự sidebar sales khớp mockup B (Điều phối trước Đội ngũ)', () => {
    const keys = ROLE_NAV.sales.map((i) => i.key)
    expect(keys.indexOf('sales-dispatch')).toBeLessThan(
      keys.indexOf('sales-team'),
    )
  })
})

// ── Route — /antmed/sales/dispatch đăng ký, name AntmedDispatch unique, mock renamed ────
describe('M10-2 route — /antmed/sales/dispatch real-page + mock renamed', () => {
  it('router.js đăng ký AntmedDispatch → /antmed/sales/dispatch (lazy page real-data)', () => {
    expect(routerSrc).toMatch(/path:\s*['"]\/antmed\/sales\/dispatch['"]/)
    expect(routerSrc).toMatch(/name:\s*['"]AntmedDispatch['"]/)
    expect(routerSrc).toMatch(/import\(['"]@\/pages\/AntmedDispatch\.vue['"]\)/)
  })
  it('name AntmedDispatch DUY NHẤT (mock cũ đã đổi AntmedDispatchMock)', () => {
    const matches = routerSrc.match(/name:\s*['"]AntmedDispatch['"]/g) || []
    expect(matches).toHaveLength(1)
  })
  // Phase 2: mock prototype /sales/dispatch ĐÃ GỠ (chỉ còn /antmed/sales/dispatch thật).
  it('meta.role=sales ⇒ sidebar Trưởng KD', () => {
    const idx = routerSrc.indexOf("'/antmed/sales/dispatch'")
    const block = routerSrc.slice(idx, idx + 220)
    expect(block).toMatch(/role:\s*['"]sales['"]/)
  })
  it('guard: AntMed user + CRM user mở route KHÔNG redirect; outsider bị redirect', () => {
    const p = { path: '/antmed/sales/dispatch' }
    expect(shouldRedirectNotPermitted(p, antmed())).toBe(false)
    expect(shouldRedirectNotPermitted(p, crm())).toBe(false)
    expect(shouldRedirectNotPermitted(p, outsider())).toBe(true)
  })
})

// ── antmedRouterGuard regression — router.js KHÔNG chứa chuỗi VI role-name cấm ───────────
describe('M10-2 router hygiene — không leak chuỗi cấm trong router.js', () => {
  it("router.js KHÔNG chứa 'NV kinh doanh|Thủ kho|Quản lý' (kể cả comment route mới)", () => {
    expect(routerSrc).not.toMatch(/NV kinh doanh|Thủ kho|Quản lý/)
  })
})

// ── Page — đọc RAW dict + kanban lane + card 5 trường + tri-branch ──────────────────────
describe('AntmedDispatch.vue — đọc r.data.{lanes,totals} + tri-branch + lane + card', () => {
  it('đọc RAW dict: r.data.lanes + r.data.totals (KHÔNG .data.data)', () => {
    expect(pageSrc).toMatch(/\.data\?\.lanes/)
    expect(pageSrc).toMatch(/\.data\?\.totals/)
    const code = pageSrc
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .replace(/<!--[\s\S]*?-->/g, '')
      .replace(/^\s*\/\/.*$/gm, '')
    expect(code).not.toMatch(/\.data\.data/)
  })
  it('tri-branch: loading (Đang tải) / error (Thử lại reload) / empty (Chưa có deal nào trong pipeline)', () => {
    expect(pageSrc).toMatch(/\.loading/)
    expect(pageSrc).toMatch(/\.error/)
    expect(pageSrc).toMatch(/Đang tải/)
    expect(pageSrc).toMatch(/Thử lại/)
    expect(pageSrc).toMatch(/reload\(\)/)
    expect(pageSrc).toMatch(/Chưa có deal nào trong pipeline/)
  })
  it('render 1 cột/lane (v-for lane) + header label + badge count', () => {
    expect(pageSrc).toMatch(/v-for="lane in lanes"/)
    expect(pageSrc).toMatch(/lane\.label/)
    expect(pageSrc).toMatch(/lane\.count/)
    expect(pageSrc).toMatch(/lane\.cards/)
  })
  it('card đọc ĐÚNG 5 trường BE: organization / territory / deal_owner_name / deal_value / bar_theme', () => {
    expect(pageSrc).toMatch(/card\.organization/)
    expect(pageSrc).toMatch(/card\.territory/)
    expect(pageSrc).toMatch(/card\.deal_owner_name/)
    expect(pageSrc).toMatch(/card\.deal_value/)
    expect(pageSrc).toMatch(/card\.bar_theme/)
  })
  it("fallback organization '— Chưa có tổ chức —' khi null; territory '—'", () => {
    expect(pageSrc).toContain('Chưa có tổ chức')
  })
  it(':key dùng card.deal (KHÔNG render/leak email deal_owner)', () => {
    expect(pageSrc).toMatch(/:key="card\.deal"/)
    const code = pageSrc
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .replace(/<!--[\s\S]*?-->/g, '')
      .replace(/^\s*\/\/.*$/gm, '')
    expect(code).not.toMatch(/deal_owner[^_]/) // KHÔNG dùng card.deal_owner (email) — chỉ deal_owner_name
  })
  it('deal_value qua formatVnMoney; thanh probability qua dispatchBarClass(card.bar_theme)', () => {
    expect(pageSrc).toMatch(/formatVnMoney\(card\.deal_value\)/)
    expect(pageSrc).toMatch(/dispatchBarClass\(card\.bar_theme\)/)
    expect(pageSrc).toMatch(/from\s*'@\/utils\/antmedUi'/)
  })
  it('a11y: thanh probability có role=progressbar + aria-valuenow', () => {
    expect(pageSrc).toMatch(/role="progressbar"/)
    expect(pageSrc).toMatch(/aria-valuenow/)
    expect(pageSrc).toMatch(/card\.probability/)
  })
  it('breadcrumb: Trang chủ › Điều phối', () => {
    expect(pageSrc).toContain('Trang chủ')
    expect(pageSrc).toContain('Điều phối')
  })
  it('KHÔNG sort/aggregate lại ở FE (BE đã group+sort); KHÔNG drag-drop/ghi; KHÔNG mock', () => {
    const code = pageSrc
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .replace(/<!--[\s\S]*?-->/g, '')
      .replace(/^\s*\/\/.*$/gm, '')
    expect(code).not.toMatch(/\.sort\(/)
    expect(code).not.toMatch(/\.reduce\(/)
    expect(code).not.toMatch(/createListResource/)
    expect(code).not.toMatch(/draggable|vuedraggable|@drop|dragstart/)
    expect(code).not.toMatch(/axios|@tanstack\/vue-query|useApi\(/)
    expect(code).not.toMatch(/antmedMock/)
  })
})
