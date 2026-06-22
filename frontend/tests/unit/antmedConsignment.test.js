import { readFileSync } from 'fs'
import path from 'path'
import { ROLE_NAV, isNavActive } from '../../src/data/antmedNav'
import { shouldRedirectNotPermitted } from '../../src/utils/antmedGuard'
import {
  nearExpiryChipClass,
  nearExpiryLabel,
  formatExpiryMonthYear,
  pillClass,
} from '../../src/utils/antmedUi'

// M03-3 — màn "Kho ký gửi tại Bệnh viện" (Thủ kho, /antmed/warehouse/consignment, AntmedConsignment.vue).
// Idiom test = behavior-assert helper THUẦN (antmedUi.js không import frappe-ui → import trực tiếp)
// + content-assert nguồn (router/nav/page/data) cho url & wiring (data/antmed.js KÉO frappe-ui nên
// vitest KHÔNG load được → assert chuỗi nguồn cho url, như antmedStockEntries.test.js).

const srcDir = path.resolve(__dirname, '../../src')
const routerSrc = readFileSync(path.join(srcDir, 'router.js'), 'utf8')
const navSrc = readFileSync(path.join(srcDir, 'data/antmedNav.js'), 'utf8')
const pageSrc = readFileSync(
  path.join(srcDir, 'pages/AntmedConsignment.vue'),
  'utf8',
)
const dataSrc = readFileSync(path.join(srcDir, 'data/antmed.js'), 'utf8')

const antmed = () => ({ isCrmUser: () => false, isAntmedUser: () => true })
const crm = () => ({ isCrmUser: () => true, isAntmedUser: () => false })
const outsider = () => ({ isCrmUser: () => false, isAntmedUser: () => false })

// ── Helper thuần nearExpiryChipClass — chip HSD cận date → token (danger) / xa → ok ─────
describe('nearExpiryChipClass — chip cận date → token màu (WCAG kèm chữ ở component)', () => {
  it('near=true → danger token (đỏ)', () => {
    expect(nearExpiryChipClass(true)).toBe(pillClass('danger'))
  })
  it('near=false → ok token (xanh)', () => {
    expect(nearExpiryChipClass(false)).toBe(pillClass('ok'))
  })
  it('giá trị lạ (null/undefined) → ok token (an toàn, không vỡ render)', () => {
    expect(nearExpiryChipClass(null)).toBe(pillClass('ok'))
    expect(nearExpiryChipClass(undefined)).toBe(pillClass('ok'))
  })
})

// ── Helper thuần nearExpiryLabel — nhãn VI chip ─────────────────────────────────────────
describe('nearExpiryLabel — nhãn VI cận date / bình thường', () => {
  it("near=true → 'Cận date'", () => {
    expect(nearExpiryLabel(true)).toBe('Cận date')
  })
  it("near=false → 'Bình thường'", () => {
    expect(nearExpiryLabel(false)).toBe('Bình thường')
  })
  it("null/undefined → 'Bình thường' (an toàn)", () => {
    expect(nearExpiryLabel(null)).toBe('Bình thường')
    expect(nearExpiryLabel(undefined)).toBe('Bình thường')
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
  it("null/undefined/'' → '' (null-guard, không ZeroDiv/crash)", () => {
    expect(formatExpiryMonthYear(null)).toBe('')
    expect(formatExpiryMonthYear(undefined)).toBe('')
    expect(formatExpiryMonthYear('')).toBe('')
  })
  it('Date object cũng format đúng', () => {
    expect(formatExpiryMonthYear(new Date(2028, 11, 31))).toBe('12/2028')
  })
  it("chuỗi không parse được → '' (không crash)", () => {
    expect(formatExpiryMonthYear('not-a-date')).toBe('')
  })
})

// ── Data layer — getConsignmentStock gọi đúng endpoint MỚI (naming contract BE-FE) ─────
describe('M03-3 data layer — getConsignmentStock url consignment_stock', () => {
  it('getConsignmentStock → createResource url antmed_crm.api.antmed.inventory.consignment_stock', () => {
    expect(dataSrc).toMatch(/export function getConsignmentStock/)
    expect(dataSrc).toMatch(
      /antmed_crm\.api\.antmed\.inventory\.consignment_stock/,
    )
  })
  it('nhận params { hospital } + auto (mirror getContractConsumptionByMonth)', () => {
    const block = dataSrc.slice(
      dataSrc.indexOf('export function getConsignmentStock'),
      dataSrc.indexOf('export function getConsignmentStock') + 400,
    )
    expect(block).toMatch(/params/)
    expect(block).toMatch(/auto/)
  })
  it('dùng createResource (đọc dict RAW), KHÔNG createListResource', () => {
    expect(dataSrc).toMatch(
      /import\s*\{\s*createResource\s*\}\s*from\s*'frappe-ui'/,
    )
    expect(dataSrc).not.toMatch(/import[^\n]*createListResource/)
  })
})

// ── Nav — ROLE_NAV.warehouse wh-consignment trỏ /antmed/warehouse/consignment, enabled ─
describe('M03-3 nav — wh-consignment enabled tới /antmed/warehouse/consignment', () => {
  it("ROLE_NAV.warehouse 'wh-consignment' to=/antmed/warehouse/consignment, enabled=true", () => {
    const item = ROLE_NAV.warehouse.find((i) => i.key === 'wh-consignment')
    expect(item).toMatchObject({
      to: '/antmed/warehouse/consignment',
      enabled: true,
      label: 'Kho ký gửi BV',
    })
  })
  it('isNavActive: active ở /antmed/warehouse/consignment, KHÔNG active ở /antmed', () => {
    const item = { to: '/antmed/warehouse/consignment' }
    expect(isNavActive(item, '/antmed/warehouse/consignment')).toBe(true)
    expect(
      isNavActive({ to: '/antmed' }, '/antmed/warehouse/consignment'),
    ).toBe(false)
  })
})

// ── Route — /antmed/warehouse/consignment đăng ký, name AntmedConsignment unique, guard ─
describe('M03-3 route — /antmed/warehouse/consignment đăng ký + guard', () => {
  it('router.js đăng ký AntmedConsignment → /antmed/warehouse/consignment (lazy page real-data)', () => {
    expect(routerSrc).toMatch(
      /path:\s*['"]\/antmed\/warehouse\/consignment['"]/,
    )
    expect(routerSrc).toMatch(/name:\s*['"]AntmedConsignment['"]/)
    expect(routerSrc).toMatch(
      /import\(['"]@\/pages\/AntmedConsignment\.vue['"]\)/,
    )
  })
  it('name AntmedConsignment DUY NHẤT (stub cũ đã đổi name → KHÔNG trùng)', () => {
    const matches = routerSrc.match(/name:\s*['"]AntmedConsignment['"]/g) || []
    expect(matches).toHaveLength(1)
  })
  // Phase 2: mock prototype /warehouse/consignment ĐÃ GỠ — chỉ còn /antmed/warehouse/consignment thật.
  it('meta.role=warehouse ⇒ sidebar Thủ kho', () => {
    const block = routerSrc.slice(
      routerSrc.indexOf("'/antmed/warehouse/consignment'"),
      routerSrc.indexOf("'/antmed/warehouse/consignment'") + 260,
    )
    expect(block).toMatch(/role:\s*['"]warehouse['"]/)
  })
  it('guard: AntMed user + CRM user mở route KHÔNG redirect; outsider bị redirect', () => {
    const p = { path: '/antmed/warehouse/consignment' }
    expect(shouldRedirectNotPermitted(p, antmed())).toBe(false)
    expect(shouldRedirectNotPermitted(p, crm())).toBe(false)
    expect(shouldRedirectNotPermitted(p, outsider())).toBe(true)
  })
})

// ── Page — đọc RAW dict + dropdown BV + KPI + bảng + tri-branch ─────────────────────────
describe('AntmedConsignment.vue — đọc r.data.{rows,kpis,hospitals,hospital} + tri-branch', () => {
  it('đọc RAW dict: r.data.rows + r.data.kpis + r.data.hospitals + r.data.hospital', () => {
    expect(pageSrc).toMatch(/\.data\?\.rows/)
    expect(pageSrc).toMatch(/\.data\?\.kpis/)
    expect(pageSrc).toMatch(/\.data\?\.hospitals/)
    expect(pageSrc).toMatch(/\.data\?\.hospital/)
  })
  it('dropdown BV: @change → resource.update params + reload (param phát đi == UI selection)', () => {
    // Đổi BV phải cập nhật param hospital rồi reload (chống dead-control LL-FE-13).
    expect(pageSrc).toMatch(/hospital/)
    expect(pageSrc).toMatch(/reload\(\)/)
  })
  it('tri-branch: loading (Đang tải) / error (Thử lại reload) / empty (Chưa có tồn ký gửi)', () => {
    expect(pageSrc).toMatch(/\.loading/)
    expect(pageSrc).toMatch(/\.error/)
    expect(pageSrc).toMatch(/Đang tải/)
    expect(pageSrc).toMatch(/Thử lại/)
    expect(pageSrc).toMatch(/reload\(\)/)
    expect(pageSrc).toMatch(/Chưa có tồn ký gửi/)
  })
  it('cột bảng đọc ĐÚNG field BE: sku/item_name/lot/expiry_date/system_qty/near_expiry', () => {
    expect(pageSrc).toMatch(/row\.sku/)
    expect(pageSrc).toMatch(/row\.item_name/)
    expect(pageSrc).toMatch(/row\.lot/)
    expect(pageSrc).toMatch(/row\.expiry_date/)
    expect(pageSrc).toMatch(/row\.system_qty/)
    expect(pageSrc).toMatch(/row\.near_expiry/)
  })
  it('header cột đủ (VI): SKU / Tên VT / Lot / HSD / SL hệ thống', () => {
    for (const h of ['SKU', 'Tên VT', 'Lot', 'HSD', 'SL hệ thống']) {
      expect(pageSrc).toContain(h)
    }
  })
  it('HSD qua formatExpiryMonthYear; chip qua nearExpiryChipClass + nearExpiryLabel', () => {
    expect(pageSrc).toMatch(/formatExpiryMonthYear\(row\.expiry_date\)/)
    expect(pageSrc).toMatch(/nearExpiryChipClass\(row\.near_expiry\)/)
    expect(pageSrc).toMatch(/nearExpiryLabel\(row\.near_expiry\)/)
    // Import helper từ @/utils/antmedUi (block import có thể multi-line).
    expect(pageSrc).toMatch(/nearExpiryChipClass/)
    expect(pageSrc).toMatch(/from\s*'@\/utils\/antmedUi'/)
  })
  it("3 KPI card thật: 'Bệnh viện có ký gửi' + 'Tồn ký gửi' + 'Cận date (≤90 ngày)' (tone danger)", () => {
    expect(pageSrc).toContain('Bệnh viện có ký gửi')
    expect(pageSrc).toContain('Tồn ký gửi')
    expect(pageSrc).toContain('Cận date (≤90 ngày)')
    expect(pageSrc).toMatch(/hospitals_with_consignment/)
    expect(pageSrc).toMatch(/near_expiry_lots/)
    expect(pageSrc).toMatch(/AntmedKpiCard/)
  })
  it('row near_expiry highlight nền đỏ nhạt (token bg danger nhạt)', () => {
    expect(pageSrc).toMatch(/near_expiry/)
    expect(pageSrc).toMatch(/bg-red-50/)
  })
  it('breadcrumb: Trang chủ › Kho ký gửi BV', () => {
    expect(pageSrc).toContain('Trang chủ')
    expect(pageSrc).toContain('Kho ký gửi BV')
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

// ── M03-5 — hàng KPI 3 thẻ (mockup D2): thẻ giữa 'Tồn ký gửi' (total_value/total_sku/total_lots) ──
describe("AntmedConsignment.vue — KPI card 'Tồn ký gửi' (M03-5, thẻ giữa hàng 3 thẻ)", () => {
  it('grid KPI dùng sm:grid-cols-3 (3 thẻ), KHÔNG còn sm:grid-cols-2', () => {
    expect(pageSrc).toMatch(/sm:grid-cols-3/)
    expect(pageSrc).not.toMatch(/sm:grid-cols-2/)
  })
  it("thẻ giữa label 'Tồn ký gửi' nằm GIỮA 'Bệnh viện có ký gửi' và 'Cận date (≤90 ngày)'", () => {
    const iHosp = pageSrc.indexOf('Bệnh viện có ký gửi')
    const iValue = pageSrc.indexOf('Tồn ký gửi')
    const iNear = pageSrc.indexOf('Cận date (≤90 ngày)')
    expect(iHosp).toBeGreaterThan(-1)
    expect(iValue).toBeGreaterThan(-1)
    expect(iNear).toBeGreaterThan(-1)
    // Thứ tự render trong template: hospitals → Tồn ký gửi → Cận date.
    expect(iHosp).toBeLessThan(iValue)
    expect(iValue).toBeLessThan(iNear)
  })
  it("value thẻ 'Tồn ký gửi' = formatVnMoney(total_value) (tái dùng helper tiền VI gọn)", () => {
    expect(pageSrc).toMatch(/formatVnMoney/)
    // import từ @/utils/antmedUi.
    expect(pageSrc).toMatch(
      /formatVnMoney[\s\S]*from\s*'@\/utils\/antmedUi'|from\s*'@\/utils\/antmedUi'[\s\S]*formatVnMoney/,
    )
    // bind total_value qua formatVnMoney (số tiền tồn).
    expect(pageSrc).toMatch(/formatVnMoney\([^)]*total_value[^)]*\)/)
  })
  it("dòng phụ '<total_sku> SKU · <total_lots> lô' (khớp mockup '487 SKU · 1.240 lot')", () => {
    expect(pageSrc).toMatch(/total_sku/)
    expect(pageSrc).toMatch(/total_lots/)
    expect(pageSrc).toContain('SKU')
    // Đơn vị 'lô' (chữ thường, không dấu mũ) trong dòng phụ.
    expect(pageSrc).toMatch(/lô/)
  })
  it("tri-branch: loading/error → thẻ 'Tồn ký gửi' hiển thị '—' (không số rác)", () => {
    // Anchor vào LABEL trong article (__('Tồn ký gửi')), KHÔNG comment header.
    const start = pageSrc.indexOf("__('Tồn ký gửi')")
    expect(start).toBeGreaterThan(-1)
    // Quét xuôi đủ phủ phần value+subline của thẻ (formatVnMoney(total_value) + SKU/lô).
    const block = pageSrc.slice(start, start + 700)
    expect(block).toMatch(/consignment\.loading|\.loading/)
    expect(block).toMatch(/consignment\.error|\.error/)
    expect(block).toMatch(/—/)
    // value của thẻ này phải đi qua formatVnMoney(total_value).
    expect(block).toMatch(/formatVnMoney\([^)]*total_value[^)]*\)/)
  })
  it('computed kpis default ĐỦ 5 key (FE bind không KeyError khi data chưa về)', () => {
    // Fallback object trong computed kpis phải gồm cả total_value/total_sku/total_lots.
    expect(pageSrc).toMatch(/hospitals_with_consignment:\s*0/)
    expect(pageSrc).toMatch(/near_expiry_lots:\s*0/)
    expect(pageSrc).toMatch(/total_value:\s*0/)
    expect(pageSrc).toMatch(/total_sku:\s*0/)
    expect(pageSrc).toMatch(/total_lots:\s*0/)
  })
})
