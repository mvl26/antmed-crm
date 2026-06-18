import { readFileSync } from 'fs'
import path from 'path'
import { ROLE_NAV, isNavActive } from '../../src/data/antmedNav'
import { shouldRedirectNotPermitted } from '../../src/utils/antmedGuard'
import {
  formatVnMoney,
  formatStockTime,
  entryTypeChipTheme,
  ENTRY_TYPE_THEME,
} from '../../src/utils/antmedUi'

// M03-1 — màn "Phiếu xuất gần đây" (Thủ kho, /antmed/warehouse/stock-entries, AntmedStockEntries.vue).
// Idiom test = behavior-assert helper THUẦN (antmedUi.js không import frappe-ui → import trực tiếp)
// + content-assert nguồn (router/nav/page/data) cho url & wiring (data/antmed.js KÉO frappe-ui nên
// vitest KHÔNG load được → assert chuỗi nguồn cho url, như antmedContractHealth.test.js).

const srcDir = path.resolve(__dirname, '../../src')
const routerSrc = readFileSync(path.join(srcDir, 'router.js'), 'utf8')
const navSrc = readFileSync(path.join(srcDir, 'data/antmedNav.js'), 'utf8')
const pageSrc = readFileSync(
  path.join(srcDir, 'pages/AntmedStockEntries.vue'),
  'utf8',
)
const dataSrc = readFileSync(path.join(srcDir, 'data/antmed.js'), 'utf8')

const antmed = () => ({ isCrmUser: () => false, isAntmedUser: () => true })
const crm = () => ({ isCrmUser: () => true, isAntmedUser: () => false })
const outsider = () => ({ isCrmUser: () => false, isAntmedUser: () => false })

// ── Helper thuần formatVnMoney — tiền VN gọn 'X,Y tr' / 'X,Y tỷ' ──────────────
describe('formatVnMoney — định dạng tiền VN gọn', () => {
  it("1.900.000 → '1,9 tr'", () => {
    expect(formatVnMoney(1_900_000)).toBe('1,9 tr')
  })
  it("1.200.000.000 → '1,2 tỷ'", () => {
    expect(formatVnMoney(1_200_000_000)).toBe('1,2 tỷ')
  })
  it("đúng 1 triệu → '1 tr' (bỏ ,0)", () => {
    expect(formatVnMoney(1_000_000)).toBe('1 tr')
  })
  it("đúng 1 tỷ → '1 tỷ' (bỏ ,0)", () => {
    expect(formatVnMoney(1_000_000_000)).toBe('1 tỷ')
  })
  it("< 1 triệu → số nguyên đồng phân tách VI", () => {
    expect(formatVnMoney(950_000)).toBe((950000).toLocaleString('vi-VN'))
  })
  it("null/undefined/''/NaN → '— '", () => {
    expect(formatVnMoney(null)).toBe('— ')
    expect(formatVnMoney(undefined)).toBe('— ')
    expect(formatVnMoney('')).toBe('— ')
    expect(formatVnMoney('abc')).toBe('— ')
  })
})

// ── Helper thuần formatStockTime — HH:mm dd/MM/yyyy ──────────────────────────
describe('formatStockTime — định dạng HH:mm dd/MM/yyyy', () => {
  it("'2026-06-17 09:05:00' → '09:05 17/06/2026'", () => {
    expect(formatStockTime('2026-06-17 09:05:00')).toBe('09:05 17/06/2026')
  })
  it('Date object cũng format đúng', () => {
    expect(formatStockTime(new Date(2026, 0, 3, 14, 7))).toBe('14:07 03/01/2026')
  })
  it("thiếu / parse fail → '—'", () => {
    expect(formatStockTime(null)).toBe('—')
    expect(formatStockTime(undefined)).toBe('—')
    expect(formatStockTime('')).toBe('—')
    expect(formatStockTime('not-a-date')).toBe('—')
  })
})

// ── Helper thuần entryTypeChipTheme — map loại phiếu → theme Badge ────────────
describe('entryTypeChipTheme — map entry_type (VI) → theme Badge', () => {
  it("'Xuất cho NV' → blue", () => {
    expect(entryTypeChipTheme('Xuất cho NV')).toBe('blue')
  })
  it("'Nhập NCC' → green", () => {
    expect(entryTypeChipTheme('Nhập NCC')).toBe('green')
  })
  it('loại lạ/rỗng → gray (an toàn, không vỡ render)', () => {
    expect(entryTypeChipTheme('Foo')).toBe('gray')
    expect(entryTypeChipTheme(null)).toBe('gray')
    expect(entryTypeChipTheme(undefined)).toBe('gray')
  })
  it('KEY map khớp EXACT options DocType (VI có dấu)', () => {
    expect(Object.keys(ENTRY_TYPE_THEME)).toEqual([
      'Nhập NCC',
      'Xuất cho NV',
      'Chuyển kho',
      'Nhập ký gửi BV',
      'Điều chỉnh',
    ])
  })
})

// ── Data layer — listStockEntries gọi đúng endpoint (naming contract BE-FE) ───
describe('M03-1 data layer — listStockEntries url list_stock_entries', () => {
  it('listStockEntries → createResource url antmed_crm.api.antmed.inventory.list_stock_entries', () => {
    expect(dataSrc).toMatch(/export function listStockEntries/)
    expect(dataSrc).toMatch(
      /antmed_crm\.api\.antmed\.inventory\.list_stock_entries/,
    )
  })
  it('dùng createResource (đọc dict bọc), KHÔNG createListResource', () => {
    expect(dataSrc).toMatch(/import\s*\{\s*createResource\s*\}\s*from\s*'frappe-ui'/)
    expect(dataSrc).not.toMatch(/import[^\n]*createListResource/)
  })
})

// ── Nav — ROLE_NAV.warehouse wh-export trỏ Wizard /antmed/warehouse/issue ─────
// (M03-S4: nav 'Xuất cho NV' nâng cấp trỏ Wizard quét QR; list "Phiếu xuất gần đây"
//  /antmed/warehouse/stock-entries vẫn truy cập được qua RouterLink trong wizard + detail.)
describe('M03-S4 nav — wh-export enabled tới Wizard /antmed/warehouse/issue', () => {
  it("ROLE_NAV.warehouse 'wh-export' to=/antmed/warehouse/issue, enabled=true", () => {
    const whExport = ROLE_NAV.warehouse.find((i) => i.key === 'wh-export')
    expect(whExport).toMatchObject({
      to: '/antmed/warehouse/issue',
      enabled: true,
      label: 'Xuất cho NV',
    })
  })
  it('isNavActive: active ở /antmed/warehouse/issue, KHÔNG active ở /antmed', () => {
    const item = { to: '/antmed/warehouse/issue' }
    expect(isNavActive(item, '/antmed/warehouse/issue')).toBe(true)
    expect(isNavActive({ to: '/antmed' }, '/antmed/warehouse/issue')).toBe(false)
  })
})

// ── Route — /antmed/warehouse/stock-entries đăng ký, name unique, guard allow ─
describe('M03-1 route — /antmed/warehouse/stock-entries đăng ký + guard', () => {
  it('router.js đăng ký AntmedStockEntries → /antmed/warehouse/stock-entries (lazy page real-data)', () => {
    expect(routerSrc).toMatch(/path:\s*['"]\/antmed\/warehouse\/stock-entries['"]/)
    expect(routerSrc).toMatch(/name:\s*['"]AntmedStockEntries['"]/)
    expect(routerSrc).toMatch(/import\(['"]@\/pages\/AntmedStockEntries\.vue['"]\)/)
  })
  it('name AntmedStockEntries DUY NHẤT', () => {
    const matches = routerSrc.match(/name:\s*['"]AntmedStockEntries['"]/g) || []
    expect(matches).toHaveLength(1)
  })
  // Phase 2: route prototype /warehouse/export ĐÃ GỠ (chỉ còn /antmed/warehouse/* thật).
  it('meta.role=warehouse ⇒ sidebar Thủ kho', () => {
    const block = routerSrc.slice(
      routerSrc.indexOf("'/antmed/warehouse/stock-entries'"),
      routerSrc.indexOf("'/antmed/warehouse/stock-entries'") + 260,
    )
    expect(block).toMatch(/role:\s*['"]warehouse['"]/)
  })
  it('guard: AntMed user + CRM user mở route KHÔNG redirect; outsider bị redirect', () => {
    const p = { path: '/antmed/warehouse/stock-entries' }
    expect(shouldRedirectNotPermitted(p, antmed())).toBe(false)
    expect(shouldRedirectNotPermitted(p, crm())).toBe(false)
    expect(shouldRedirectNotPermitted(p, outsider())).toBe(true)
  })
})

// ── Page — đọc dict bọc + cột widget + tri-branch + default entry_type ───────
describe('AntmedStockEntries.vue — đọc r.data.data + tri-branch + cột widget', () => {
  it('đọc list dict bọc: r.data.data + r.data.total_count (KHÔNG r.data trực tiếp)', () => {
    expect(pageSrc).toMatch(/entries\.data\?\.data/)
    expect(pageSrc).toMatch(/entries\.data\?\.total_count/)
  })
  it("default lọc entry_type='Xuất cho NV'", () => {
    expect(pageSrc).toMatch(/entry_type:\s*['"]Xuất cho NV['"]/)
  })
  it('tri-branch: loading / error (banner + Thử lại reload) / empty (Chưa có phiếu xuất)', () => {
    expect(pageSrc).toMatch(/entries\.loading/)
    expect(pageSrc).toMatch(/entries\.error/)
    expect(pageSrc).toMatch(/Thử lại/)
    expect(pageSrc).toMatch(/entries\.reload\(\)/)
    expect(pageSrc).toMatch(/Chưa có phiếu xuất/)
    expect(pageSrc).toMatch(/!rows\.length/)
  })
  it('cột widget đọc ĐÚNG field BE: name/nv_employee(_name)/entry_type/total_value/posting_datetime', () => {
    expect(pageSrc).toMatch(/row\.name/)
    expect(pageSrc).toMatch(/row\.nv_employee_name/)
    expect(pageSrc).toMatch(/row\.entry_type/)
    expect(pageSrc).toMatch(/row\.total_value/)
    expect(pageSrc).toMatch(/row\.posting_datetime/)
  })
  it('header cột đủ: Số phiếu / NV / Loại phiếu / Giá trị / Lúc', () => {
    for (const h of ['Số phiếu', 'NV', 'Loại phiếu', 'Giá trị', 'Lúc']) {
      expect(pageSrc).toContain(h)
    }
  })
  it('Giá trị qua formatVnMoney; Lúc qua formatStockTime; loại phiếu qua entryTypeChipTheme', () => {
    expect(pageSrc).toMatch(/formatVnMoney\(row\.total_value\)/)
    expect(pageSrc).toMatch(/formatStockTime\(row\.posting_datetime\)/)
    expect(pageSrc).toMatch(/entryTypeChipTheme\(row\.entry_type\)/)
    expect(pageSrc).toMatch(
      /import[^\n]*formatVnMoney[^\n]*from\s*'@\/utils\/antmedUi'/,
    )
  })
  it('KHÔNG hardcode mock / KHÔNG createListResource·axios (code, không tính comment)', () => {
    const code = pageSrc
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .replace(/<!--[\s\S]*?-->/g, '')
      .replace(/^\s*\/\/.*$/gm, '')
    expect(code).not.toMatch(/createListResource/)
    expect(code).not.toMatch(/axios|@tanstack\/vue-query|useApi\(/)
    expect(code).not.toMatch(/antmedMock/)
  })
})
