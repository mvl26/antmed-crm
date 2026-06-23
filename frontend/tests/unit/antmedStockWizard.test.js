import { readFileSync } from 'fs'
import path from 'path'
import { ROLE_NAV, isNavActive } from '../../src/data/antmedNav'
import { shouldRedirectNotPermitted } from '../../src/utils/antmedGuard'
import {
  rowBlockedByCocq,
  blockedCocqRows,
  countVariance,
  varianceTextClass,
  docstatusLabel,
  docstatusTheme,
  cocqChipLabel,
} from '../../src/utils/antmedUi'

// M03-S4/S5 — Wizard kho (Xuất cho NV / Nhập kho / Kiểm kê) + QrScanner (html5-qrcode).
// Idiom test = behavior-assert helper THUẦN (antmedUi.js không import frappe-ui → import trực tiếp)
// + content-assert nguồn (router/nav/page/data/component) cho url + wiring (data/antmed.js KÉO
// frappe-ui nên vitest KHÔNG load runtime → assert chuỗi nguồn, như antmedStockEntries.test.js).

const srcDir = path.resolve(__dirname, '../../src')
const read = (p) => readFileSync(path.join(srcDir, p), 'utf8')
const routerSrc = read('router.js')
const navSrc = read('data/antmedNav.js')
const dataSrc = read('data/antmed.js')
const qrSrc = read('components/Antmed/QrScanner.vue')
const issueSrc = read('pages/AntmedStockIssue.vue')
const receiptSrc = read('pages/AntmedStockReceipt.vue')
const countSrc = read('pages/AntmedStockCount.vue')

const antmed = () => ({ isCrmUser: () => false, isAntmedUser: () => true })
const crm = () => ({ isCrmUser: () => true, isAntmedUser: () => false })
const outsider = () => ({ isCrmUser: () => false, isAntmedUser: () => false })

// ── Helper thuần — gate CO/CQ (HARD-BLOCK xuất) ──────────────────────────────
describe('rowBlockedByCocq — chặn dòng thiếu CO/CQ bắt buộc', () => {
  it('requires_cocq=1 + cocq_ok!=true → bị chặn', () => {
    expect(rowBlockedByCocq({ requires_cocq: 1, cocq_ok: false })).toBe(true)
    expect(rowBlockedByCocq({ requires_cocq: 1, cocq_ok: null })).toBe(true)
    expect(rowBlockedByCocq({ requires_cocq: true, cocq_ok: undefined })).toBe(
      true,
    )
  })
  it('requires_cocq=1 + cocq_ok=true → KHÔNG chặn', () => {
    expect(rowBlockedByCocq({ requires_cocq: 1, cocq_ok: true })).toBe(false)
  })
  it('requires_cocq=0 → KHÔNG chặn (VTYT không cần CO/CQ)', () => {
    expect(rowBlockedByCocq({ requires_cocq: 0, cocq_ok: false })).toBe(false)
  })
  it('null/không phải object → false (không vỡ)', () => {
    expect(rowBlockedByCocq(null)).toBe(false)
    expect(rowBlockedByCocq(undefined)).toBe(false)
  })
  it('blockedCocqRows: lọc đúng các dòng bị chặn; input lạ → []', () => {
    const rows = [
      { requires_cocq: 1, cocq_ok: false, item: 'A' },
      { requires_cocq: 1, cocq_ok: true, item: 'B' },
      { requires_cocq: 0, cocq_ok: false, item: 'C' },
    ]
    expect(blockedCocqRows(rows).map((r) => r.item)).toEqual(['A'])
    expect(blockedCocqRows(null)).toEqual([])
  })
  it('cocqChipLabel khớp nhãn VI (kèm chữ — WCAG)', () => {
    expect(cocqChipLabel(true)).toBe('CO/CQ ✓')
    expect(cocqChipLabel(false)).toBe('Thiếu CO/CQ')
  })
})

// ── Helper thuần — chênh lệch kiểm kê ────────────────────────────────────────
describe('countVariance + varianceTextClass — chênh lệch live kiểm kê', () => {
  it('counted − system; null/NaN → 0', () => {
    expect(countVariance(10, 7)).toBe(3)
    expect(countVariance(5, 8)).toBe(-3)
    expect(countVariance(null, 8)).toBe(0)
    expect(countVariance('x', 8)).toBe(0)
  })
  it('màu: >0 xanh · <0 đỏ · =0 trung tính', () => {
    expect(varianceTextClass(3)).toBe('text-green-700')
    expect(varianceTextClass(-3)).toBe('text-red-700')
    expect(varianceTextClass(0)).toBe('text-ink-gray-7')
  })
})

// ── Helper thuần — docstatus phiếu kiểm kê (VI, không EN ra UI) ───────────────
describe('docstatusLabel + docstatusTheme — docstatus → VI', () => {
  it('0 Nháp · 1 Đã chốt · 2 Đã huỷ', () => {
    expect(docstatusLabel(0)).toBe('Nháp')
    expect(docstatusLabel(1)).toBe('Đã chốt')
    expect(docstatusLabel(2)).toBe('Đã huỷ')
    expect(docstatusLabel(9)).toBe('Nháp')
  })
  it('theme: 0 gray · 1 green · 2 red', () => {
    expect(docstatusTheme(0)).toBe('gray')
    expect(docstatusTheme(1)).toBe('green')
    expect(docstatusTheme(2)).toBe('red')
  })
})

// ── Data layer — factory mới url + method đúng (naming contract BE-FE) ────────
describe('M03-S4/S5 data layer — factory url antmed_crm.api.antmed.* + method', () => {
  it('scanLot → inventory.scan_lot (GET)', () => {
    expect(dataSrc).toMatch(/export function scanLot/)
    expect(dataSrc).toMatch(/antmed_crm\.api\.antmed\.inventory\.scan_lot/)
  })
  it('createStockEntry → inventory.create_stock_entry (POST)', () => {
    expect(dataSrc).toMatch(/export function createStockEntry/)
    expect(dataSrc).toMatch(
      /antmed_crm\.api\.antmed\.inventory\.create_stock_entry/,
    )
    // Khối ngay sau định nghĩa createStockEntry phải có method POST.
    const blk = dataSrc.slice(
      dataSrc.indexOf('export function createStockEntry'),
      dataSrc.indexOf('export function createStockEntry') + 320,
    )
    expect(blk).toMatch(/method:\s*['"]POST['"]/)
  })
  it('listWarehouses → inventory.list_warehouses (GET)', () => {
    expect(dataSrc).toMatch(/export function listWarehouses/)
    expect(dataSrc).toMatch(
      /antmed_crm\.api\.antmed\.inventory\.list_warehouses/,
    )
  })
  it('listAssignableEmployees → delivery.list_assignable_employees (GET)', () => {
    expect(dataSrc).toMatch(/export function listAssignableEmployees/)
    expect(dataSrc).toMatch(
      /antmed_crm\.api\.antmed\.delivery\.list_assignable_employees/,
    )
  })
  it('stockCountSnapshot → inventory.stock_count_snapshot (GET)', () => {
    expect(dataSrc).toMatch(/export function stockCountSnapshot/)
    expect(dataSrc).toMatch(
      /antmed_crm\.api\.antmed\.inventory\.stock_count_snapshot/,
    )
  })
  it('createStockCount → inventory.create_stock_count (POST)', () => {
    expect(dataSrc).toMatch(/export function createStockCount/)
    expect(dataSrc).toMatch(
      /antmed_crm\.api\.antmed\.inventory\.create_stock_count/,
    )
    const blk = dataSrc.slice(
      dataSrc.indexOf('export function createStockCount'),
      dataSrc.indexOf('export function createStockCount') + 320,
    )
    expect(blk).toMatch(/method:\s*['"]POST['"]/)
  })
  it('listStockCounts → inventory.list_stock_counts (GET)', () => {
    expect(dataSrc).toMatch(/export function listStockCounts/)
    expect(dataSrc).toMatch(
      /antmed_crm\.api\.antmed\.inventory\.list_stock_counts/,
    )
  })
  it('mọi factory GET có method:GET tường minh (tránh POST → 403)', () => {
    for (const fn of [
      'scanLot',
      'listWarehouses',
      'listAssignableEmployees',
      'stockCountSnapshot',
      'listStockCounts',
    ]) {
      const blk = dataSrc.slice(
        dataSrc.indexOf(`export function ${fn}`),
        dataSrc.indexOf(`export function ${fn}`) + 320,
      )
      expect(blk).toMatch(/method:\s*['"]GET['"]/)
    }
  })
})

// ── QrScanner — dùng html5-qrcode (import động) + emit scan + cleanup ─────────
describe('QrScanner.vue — html5-qrcode camera component', () => {
  it("import động 'html5-qrcode' + Html5Qrcode + start(environment)", () => {
    expect(qrSrc).toMatch(/import\(['"]html5-qrcode['"]\)/)
    expect(qrSrc).toMatch(/Html5Qrcode/)
    expect(qrSrc).toMatch(/facingMode:\s*['"]environment['"]/)
  })
  it('emit scan + guard chống đọc trùng (DEDUPE)', () => {
    expect(qrSrc).toMatch(/defineEmits\(\[['"]scan['"]\]\)/)
    expect(qrSrc).toMatch(/emit\(['"]scan['"]/)
    expect(qrSrc).toMatch(/DEDUPE_MS/)
  })
  it('cleanup: onBeforeUnmount → stop() (tránh leak camera)', () => {
    expect(qrSrc).toMatch(/onBeforeUnmount/)
    expect(qrSrc).toMatch(/\.stop\(\)/)
    expect(qrSrc).toMatch(/\.clear\(\)/)
  })
  it('lỗi camera → thông báo VI nhập thủ công (KHÔNG vỡ trang)', () => {
    expect(qrSrc).toMatch(/Không truy cập được camera/)
  })
})

// ── Nav — wh-import enabled + route mới; wh-export → /issue; wh-stock-count tồn tại ──
describe('M03-S4/S5 nav — ROLE_NAV.warehouse cập nhật', () => {
  it('wh-import enabled tới /antmed/warehouse/import', () => {
    const item = ROLE_NAV.warehouse.find((i) => i.key === 'wh-import')
    expect(item).toMatchObject({
      to: '/antmed/warehouse/import',
      enabled: true,
      label: 'Nhập kho',
    })
  })
  it('wh-export trỏ /antmed/warehouse/issue (Wizard mới)', () => {
    const item = ROLE_NAV.warehouse.find((i) => i.key === 'wh-export')
    expect(item).toMatchObject({
      to: '/antmed/warehouse/issue',
      enabled: true,
      label: 'Xuất cho NV',
    })
  })
  it('wh-stock-count tồn tại tới /antmed/warehouse/stock-count', () => {
    const item = ROLE_NAV.warehouse.find((i) => i.key === 'wh-stock-count')
    expect(item).toMatchObject({
      to: '/antmed/warehouse/stock-count',
      enabled: true,
      label: 'Kiểm kê',
    })
  })
  it('thứ tự mockup: Nhập → Xuất → Ký gửi → Kiểm kê → Truy vết → Cảnh báo HSD', () => {
    const keys = ROLE_NAV.warehouse.map((i) => i.key)
    expect(keys.indexOf('wh-stock-count')).toBeGreaterThan(
      keys.indexOf('wh-consignment'),
    )
    expect(keys.indexOf('wh-stock-count')).toBeLessThan(
      keys.indexOf('wh-lot-trace'),
    )
  })
  it('isNavActive hoạt động cho route mới', () => {
    expect(
      isNavActive({ to: '/antmed/warehouse/issue' }, '/antmed/warehouse/issue'),
    ).toBe(true)
    expect(
      isNavActive(
        { to: '/antmed/warehouse/stock-count' },
        '/antmed/warehouse/stock-count',
      ),
    ).toBe(true)
  })
})

// ── Route — 3 route mới đăng ký + name unique + guard ────────────────────────
describe('M03-S4/S5 route — issue / import / stock-count', () => {
  const specs = [
    ['/antmed/warehouse/issue', 'AntmedStockIssue'],
    ['/antmed/warehouse/import', 'AntmedStockReceipt'],
    ['/antmed/warehouse/stock-count', 'AntmedStockCount'],
  ]
  it.each(specs)(
    'route %s → name %s (lazy page, role warehouse)',
    (routePath, name) => {
      expect(routerSrc).toContain(`path: '${routePath}'`)
      expect(routerSrc).toMatch(new RegExp(`name:\\s*['"]${name}['"]`))
      expect(routerSrc).toMatch(
        new RegExp(`import\\(['"]@/pages/${name}\\.vue['"]\\)`),
      )
    },
  )
  it.each(specs)('name %s DUY NHẤT', (_routePath, name) => {
    const matches =
      routerSrc.match(new RegExp(`name:\\s*['"]${name}['"]`, 'g')) || []
    expect(matches).toHaveLength(1)
  })
  it('guard: AntMed + CRM user allow; outsider redirect', () => {
    const p = { path: '/antmed/warehouse/issue' }
    expect(shouldRedirectNotPermitted(p, antmed())).toBe(false)
    expect(shouldRedirectNotPermitted(p, crm())).toBe(false)
    expect(shouldRedirectNotPermitted(p, outsider())).toBe(true)
  })
})

// ── Page wiring — gọi antmed_crm.api.antmed.* + KHÔNG crm.api/axios/createListResource ─
describe('Wizard pages — endpoint đúng + KHÔNG di sản stack cũ', () => {
  const pages = [
    ['AntmedStockIssue.vue', issueSrc],
    ['AntmedStockReceipt.vue', receiptSrc],
    ['AntmedStockCount.vue', countSrc],
  ]
  it.each(pages)(
    '%s import factory từ @/data/antmed (KHÔNG url thô)',
    (_name, src) => {
      expect(src).toMatch(/from\s*['"]@\/data\/antmed['"]/)
      expect(src).not.toMatch(/crm\.api\./)
      expect(src).not.toMatch(/axios|@tanstack\/vue-query|useApi\(/)
      expect(src).not.toMatch(/createListResource/)
    },
  )
  it('AntmedStockIssue: dùng QrScanner + gate CO/CQ + entry_type Xuất cho NV', () => {
    expect(issueSrc).toMatch(/QrScanner/)
    expect(issueSrc).toMatch(/rowBlockedByCocq|blockedCocqRows/)
    expect(issueSrc).toMatch(/entry_type:\s*['"]Xuất cho NV['"]/)
    // Nút Xuất disabled khi có dòng bị chặn (canSubmit phụ thuộc blockedRows).
    expect(issueSrc).toMatch(/blockedRows\.value\.length\s*===\s*0/)
  })
  it('AntmedStockIssue: chặn lô đã thu hồi (recall) khi quét', () => {
    // An toàn recall — KHÔNG cho thêm lô 'Đã thu hồi' (BE cũng chặn cứng khi submit).
    expect(issueSrc).toMatch(/recall_status\s*===\s*['"]Đã thu hồi['"]/)
  })
  it('AntmedStockIssue: chặn lô đã hết hạn (HSD) khi quét', () => {
    // An toàn HSD — KHÔNG cho thêm lô days_to_expiry < 0 (BE cũng chặn cứng khi submit).
    expect(issueSrc).toMatch(/days_to_expiry\s*<\s*0/)
  })
  it('AntmedStockReceipt: entry_type Nhập NCC, KHÔNG gate CO/CQ', () => {
    expect(receiptSrc).toMatch(/entry_type:\s*['"]Nhập NCC['"]/)
    expect(receiptSrc).not.toMatch(/rowBlockedByCocq/)
  })
  it('AntmedStockCount: snapshot + createStockCount + lịch sử', () => {
    expect(countSrc).toMatch(/stockCountSnapshot/)
    expect(countSrc).toMatch(/createStockCount/)
    expect(countSrc).toMatch(/listStockCounts/)
    // counted_qty default = system_qty (prefill).
    expect(countSrc).toMatch(/counted_qty:\s*r\.system_qty/)
  })
})
