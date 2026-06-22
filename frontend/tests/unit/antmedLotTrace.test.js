import { readFileSync } from 'fs'
import path from 'path'
import { ROLE_NAV, isNavActive } from '../../src/data/antmedNav'
import { shouldRedirectNotPermitted } from '../../src/utils/antmedGuard'
import {
  fmtDate,
  recallChipClass,
  recallChipTheme,
  RECALL_THEME,
  PILL_THEME,
  entryDirectionLabel,
  ENTRY_DIRECTION_LABEL,
  traceDirectionChipTheme,
  traceDirectionChipClass,
  traceDirectionLabel,
  TRACE_DIRECTION_THEME,
  RECALL_INITIATE_STATUSES,
  RECALL_INITIATE_DEFAULT,
} from '../../src/utils/antmedUi'

// M03-2 — màn "Thông tin lot" (Thủ kho, /antmed/warehouse/lot-trace, AntmedLotTrace.vue, mockup D3).
// Idiom test = behavior-assert helper THUẦN (antmedUi.js không import frappe-ui → import trực tiếp)
// + content-assert nguồn (router/nav/page/data) cho url & wiring (data/antmed.js KÉO frappe-ui nên
// vitest KHÔNG load được → assert chuỗi nguồn cho url, như antmedStockEntries.test.js).

const srcDir = path.resolve(__dirname, '../../src')
const routerSrc = readFileSync(path.join(srcDir, 'router.js'), 'utf8')
const navSrc = readFileSync(path.join(srcDir, 'data/antmedNav.js'), 'utf8')
const pageSrc = readFileSync(
  path.join(srcDir, 'pages/AntmedLotTrace.vue'),
  'utf8',
)
const dataSrc = readFileSync(path.join(srcDir, 'data/antmed.js'), 'utf8')

const antmed = () => ({ isCrmUser: () => false, isAntmedUser: () => true })
const crm = () => ({ isCrmUser: () => true, isAntmedUser: () => false })
const outsider = () => ({ isCrmUser: () => false, isAntmedUser: () => false })

// ── Helper thuần fmtDate — dd/MM/yyyy ─────────────────────────────────────────
describe('fmtDate — định dạng dd/MM/yyyy (NSX/HSD)', () => {
  it("ISO 'yyyy-MM-dd' → dd/MM/yyyy (parse thủ công, không lệch TZ)", () => {
    expect(fmtDate('2025-03-01')).toBe('01/03/2025')
    expect(fmtDate('2027-10-31')).toBe('31/10/2027')
  })
  it('ISO có phần giờ vẫn lấy đúng ngày', () => {
    expect(fmtDate('2026-01-05 09:30:00')).toBe('05/01/2026')
  })
  it('Date object cũng format đúng', () => {
    expect(fmtDate(new Date(2026, 5, 17))).toBe('17/06/2026')
  })
  it("thiếu / parse fail → '—'", () => {
    expect(fmtDate(null)).toBe('—')
    expect(fmtDate(undefined)).toBe('—')
    expect(fmtDate('')).toBe('—')
    expect(fmtDate('not-a-date')).toBe('—')
  })
})

// ── Helper thuần recallChipClass — map recall_status → class chip (3 nhánh) ────
describe('recallChipClass — map recall_status (VI) → class chip', () => {
  it("'Bình thường' → neutral (PILL_THEME.neutral)", () => {
    expect(recallChipTheme('Bình thường')).toBe('neutral')
    expect(recallChipClass('Bình thường')).toBe(PILL_THEME.neutral)
  })
  it("'Theo dõi' → warn (PILL_THEME.warn)", () => {
    expect(recallChipTheme('Theo dõi')).toBe('warn')
    expect(recallChipClass('Theo dõi')).toBe(PILL_THEME.warn)
  })
  it("'Đã thu hồi' → danger (PILL_THEME.danger)", () => {
    expect(recallChipTheme('Đã thu hồi')).toBe('danger')
    expect(recallChipClass('Đã thu hồi')).toBe(PILL_THEME.danger)
  })
  it('trạng thái lạ/rỗng → neutral (an toàn, không vỡ render)', () => {
    expect(recallChipTheme('Foo')).toBe('neutral')
    expect(recallChipTheme(null)).toBe('neutral')
    expect(recallChipTheme(undefined)).toBe('neutral')
    expect(recallChipClass('Foo')).toBe(PILL_THEME.neutral)
  })
  it('KEY map khớp EXACT options DocType AntMed Lot.recall_status (VI có dấu)', () => {
    expect(Object.keys(RECALL_THEME)).toEqual([
      'Bình thường',
      'Theo dõi',
      'Đã thu hồi',
    ])
  })
})

// ── Data layer — getLot gọi đúng endpoint (naming contract BE-FE) ─────────────
describe('M03-2 data layer — getLot url get_lot', () => {
  it('getLot → createResource url antmed_crm.api.antmed.inventory.get_lot', () => {
    expect(dataSrc).toMatch(/export function getLot/)
    expect(dataSrc).toMatch(/antmed_crm\.api\.antmed\.inventory\.get_lot/)
  })
  it('auto:false (chỉ fetch khi bấm Truy vết) — mặc định trong factory', () => {
    const block = dataSrc.slice(
      dataSrc.indexOf('export function getLot'),
      dataSrc.indexOf('export function getLot') + 320,
    )
    expect(block).toMatch(/auto\s*=\s*false/)
  })
  it('dùng createResource (đọc dict THƯỜNG r.data), KHÔNG createListResource', () => {
    expect(dataSrc).toMatch(
      /import\s*\{\s*createResource\s*\}\s*from\s*'frappe-ui'/,
    )
    expect(dataSrc).not.toMatch(/import[^\n]*createListResource/)
  })
})

// ── Nav — ROLE_NAV.warehouse wh-lot-trace trỏ /antmed/warehouse/lot-trace ──────
describe('M03-2 nav — wh-lot-trace enabled tới /antmed/warehouse/lot-trace', () => {
  it("ROLE_NAV.warehouse 'wh-lot-trace' to=/antmed/warehouse/lot-trace, enabled=true", () => {
    const item = ROLE_NAV.warehouse.find((i) => i.key === 'wh-lot-trace')
    expect(item).toMatchObject({
      to: '/antmed/warehouse/lot-trace',
      enabled: true,
      label: 'Truy vết lot',
    })
  })
  it('isNavActive: active ở /antmed/warehouse/lot-trace, KHÔNG active ở /antmed', () => {
    const item = { to: '/antmed/warehouse/lot-trace' }
    expect(isNavActive(item, '/antmed/warehouse/lot-trace')).toBe(true)
    expect(isNavActive({ to: '/antmed' }, '/antmed/warehouse/lot-trace')).toBe(
      false,
    )
  })
  it('no-regression: wh-lot-trace giữ nguyên đích + enabled (sau khi thêm wh-stock-count)', () => {
    const whLotTrace = ROLE_NAV.warehouse.find((i) => i.key === 'wh-lot-trace')
    expect(whLotTrace.to).toBe('/antmed/warehouse/lot-trace')
    expect(whLotTrace.enabled).toBe(true)
  })
})

// ── Route — /antmed/warehouse/lot-trace đăng ký, name unique, guard allow ──────
describe('M03-2 route — /antmed/warehouse/lot-trace đăng ký + guard', () => {
  it('router.js đăng ký AntmedLotTrace → /antmed/warehouse/lot-trace (lazy page real-data)', () => {
    expect(routerSrc).toMatch(/path:\s*['"]\/antmed\/warehouse\/lot-trace['"]/)
    expect(routerSrc).toMatch(/name:\s*['"]AntmedLotTrace['"]/)
    expect(routerSrc).toMatch(/import\(['"]@\/pages\/AntmedLotTrace\.vue['"]\)/)
  })
  it('name AntmedLotTrace DUY NHẤT', () => {
    const matches = routerSrc.match(/name:\s*['"]AntmedLotTrace['"]/g) || []
    expect(matches).toHaveLength(1)
  })
  // Phase 2: mock prototype /warehouse/lot-trace ĐÃ GỠ (chỉ còn /antmed/warehouse/lot-trace).
  it('meta.role=warehouse ⇒ sidebar Thủ kho', () => {
    const idx = routerSrc.indexOf("'/antmed/warehouse/lot-trace'")
    const block = routerSrc.slice(idx, idx + 260)
    expect(block).toMatch(/role:\s*['"]warehouse['"]/)
  })
  it('guard: AntMed user + CRM user mở route KHÔNG redirect; outsider bị redirect', () => {
    const p = { path: '/antmed/warehouse/lot-trace' }
    expect(shouldRedirectNotPermitted(p, antmed())).toBe(false)
    expect(shouldRedirectNotPermitted(p, crm())).toBe(false)
    expect(shouldRedirectNotPermitted(p, outsider())).toBe(true)
  })
})

// ── Page — search card + card "Thông tin lot" + tri-branch + đọc r.data ───────
describe('AntmedLotTrace.vue — search + card thông tin lot + tri-branch', () => {
  it('đọc dict THƯỜNG: lot.data trực tiếp (KHÔNG .data.data của list bọc)', () => {
    expect(pageSrc).toMatch(/lot\.data\b/)
    expect(pageSrc).not.toMatch(/lot\.data\?\.data/)
  })
  it('card search: input Mã Lot + nút Truy vết (submit gọi lot.submit({ name }))', () => {
    expect(pageSrc).toContain('Mã Lot')
    expect(pageSrc).toContain('Truy vết')
    expect(pageSrc).toMatch(/lot\.submit\(\{\s*name\s*\}\)/)
  })
  it('nhãn VI bắt buộc của card D3: SKU/NCC/NSX/HSD/SL nhập/SL đã xuất/SL còn/CO/CQ', () => {
    for (const label of [
      'Thông tin lot',
      'SKU',
      'NCC',
      'NSX',
      'HSD',
      'SL nhập',
      'SL đã xuất',
      'SL còn',
      'CO',
      'CQ',
    ]) {
      expect(pageSrc).toContain(label)
    }
  })
  it('đọc ĐÚNG field BE: item_name/supplier_name/mfg_date/expiry_date/qty_*/co_cert/cq_cert/recall_status', () => {
    expect(pageSrc).toMatch(/data\.item_name/)
    expect(pageSrc).toMatch(/data\.supplier_name/)
    expect(pageSrc).toMatch(/data\.mfg_date/)
    expect(pageSrc).toMatch(/data\.expiry_date/)
    expect(pageSrc).toMatch(/data\.qty_in/)
    expect(pageSrc).toMatch(/data\.qty_out/)
    expect(pageSrc).toMatch(/data\.qty_remaining/)
    expect(pageSrc).toMatch(/data\.co_cert/)
    expect(pageSrc).toMatch(/data\.cq_cert/)
    expect(pageSrc).toMatch(/data\.recall_status/)
  })
  it('NSX/HSD qua fmtDate; chip recall qua recallChipClass (import từ antmedUi)', () => {
    expect(pageSrc).toMatch(/fmtDate\(data\.mfg_date\)/)
    expect(pageSrc).toMatch(/fmtDate\(data\.expiry_date\)/)
    expect(pageSrc).toMatch(/recallChipClass\(data\.recall_status\)/)
    // import có thể multi-line (prettier wrap nhiều named import) → khớp xuyên dòng.
    expect(pageSrc).toMatch(
      /import\s*\{[\s\S]*?recallChipClass[\s\S]*?\}\s*from\s*'@\/utils\/antmedUi'/,
    )
  })
  it('SKU hiển thị item_name (tên), KHÔNG chỉ mã item thô đứng riêng', () => {
    // item_name là giá trị chính; data.item chỉ làm sub-text (sau dấu ·).
    expect(pageSrc).toMatch(/data\.item_name/)
  })
  it('tri-branch: empty (Chưa truy vết) / loading / not-found (Không tìm thấy lot) / error (Thử lại)', () => {
    expect(pageSrc).toMatch(/hasSubmitted/)
    expect(pageSrc).toMatch(/Chưa truy vết/)
    expect(pageSrc).toMatch(/lot\.loading/)
    expect(pageSrc).toMatch(/isNotFound/)
    expect(pageSrc).toContain('Không tìm thấy lot')
    expect(pageSrc).toMatch(/lot\.error/)
    expect(pageSrc).toContain('Thử lại')
    expect(pageSrc).toMatch(/lot\.reload\(\)/)
  })
  it('chip recall KÈM CHỮ recall_status (không chỉ màu — WCAG AA)', () => {
    expect(pageSrc).toMatch(/data\.recall_status\s*\|\|\s*'—'/)
    expect(pageSrc).toMatch(/aria-label/)
  })
  it('KHÔNG hardcode mock / KHÔNG createListResource·axios (code, không tính comment)', () => {
    const code = pageSrc
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .replace(/<!--[\s\S]*?-->/g, '')
      .replace(/^\s*\/\/.*$/gm, '')
    expect(code).not.toMatch(/createListResource/)
    expect(code).not.toMatch(/axios|@tanstack\/vue-query|useApi\(/)
    expect(code).not.toMatch(/antmedMock/)
    // KHÔNG hardcode dữ liệu mockup D3 (L-22834 / Vicryl / số 1.000-847-153).
    expect(code).not.toMatch(/L-22834|Vicryl|VT-0231/)
  })
})

// ── M03-6 helper thuần — nhãn chiều + chip direction (entryDirectionLabel/traceDirection*) ──
describe('M03-6 helper thuần — entryDirectionLabel + traceDirection chip', () => {
  it('entryDirectionLabel map đúng nhãn VI theo entry_type (KEY khớp DocType)', () => {
    expect(entryDirectionLabel('Nhập NCC')).toBe('Nhập từ NCC')
    expect(entryDirectionLabel('Xuất cho NV')).toBe('Xuất cho NV')
    expect(entryDirectionLabel('Chuyển kho')).toBe('Chuyển kho')
    expect(entryDirectionLabel('Nhập ký gửi BV')).toBe('Nhập ký gửi BV')
    expect(entryDirectionLabel('Điều chỉnh')).toBe('Điều chỉnh')
  })
  it('entryDirectionLabel lạ → trả thẳng giá trị; rỗng → "Di chuyển"', () => {
    expect(entryDirectionLabel('Foo')).toBe('Foo')
    expect(entryDirectionLabel('')).toBe('Di chuyển')
    expect(entryDirectionLabel(null)).toBe('Di chuyển')
  })
  it('ENTRY_DIRECTION_LABEL KEY khớp EXACT options entry_type DocType (VI có dấu)', () => {
    expect(Object.keys(ENTRY_DIRECTION_LABEL)).toEqual([
      'Nhập NCC',
      'Xuất cho NV',
      'Chuyển kho',
      'Nhập ký gửi BV',
      'Điều chỉnh',
    ])
  })
  it('traceDirectionChipTheme: in→ok, out→warn, lạ→neutral', () => {
    expect(traceDirectionChipTheme('in')).toBe('ok')
    expect(traceDirectionChipTheme('out')).toBe('warn')
    expect(traceDirectionChipTheme('foo')).toBe('neutral')
    expect(traceDirectionChipTheme(null)).toBe('neutral')
  })
  it('traceDirectionChipClass map theme → PILL_THEME class', () => {
    expect(traceDirectionChipClass('in')).toBe(PILL_THEME.ok)
    expect(traceDirectionChipClass('out')).toBe(PILL_THEME.warn)
    expect(traceDirectionChipClass('foo')).toBe(PILL_THEME.neutral)
  })
  it('traceDirectionLabel: in→Nhập, out→Xuất, lạ→Di chuyển (kèm chữ — WCAG)', () => {
    expect(traceDirectionLabel('in')).toBe('Nhập')
    expect(traceDirectionLabel('out')).toBe('Xuất')
    expect(traceDirectionLabel('foo')).toBe('Di chuyển')
  })
  it('TRACE_DIRECTION_THEME KEY khớp EXACT direction BE (in|out)', () => {
    expect(Object.keys(TRACE_DIRECTION_THEME)).toEqual(['in', 'out'])
  })
})

// ── M03-6 data layer — getLotTrace gọi đúng endpoint lot_trace ─────────────────
describe('M03-6 data layer — getLotTrace url lot_trace', () => {
  it('getLotTrace → createResource url antmed_crm.api.antmed.inventory.lot_trace', () => {
    expect(dataSrc).toMatch(/export function getLotTrace/)
    expect(dataSrc).toMatch(/antmed_crm\.api\.antmed\.inventory\.lot_trace/)
  })
  it('auto:false (fetch cùng lúc Truy vết) — mặc định trong factory', () => {
    const block = dataSrc.slice(
      dataSrc.indexOf('export function getLotTrace'),
      dataSrc.indexOf('export function getLotTrace') + 320,
    )
    expect(block).toMatch(/auto\s*=\s*false/)
  })
})

// ── Page M03-6 — cardrow cols-2 + right-card "Cây truy vết" (timeline events) ──
describe('AntmedLotTrace.vue — M03-6 right-card "Cây truy vết" (cardrow cols-2)', () => {
  it('import getLotTrace + helper chiều di chuyển từ data/antmed + antmedUi', () => {
    // import có thể multi-line (prettier wrap) → khớp xuyên dòng [\s\S].
    expect(pageSrc).toMatch(
      /import\s*\{[\s\S]*?getLotTrace[\s\S]*?\}\s*from\s*'@\/data\/antmed'/,
    )
    expect(pageSrc).toMatch(
      /import\s*\{[\s\S]*?(entryDirectionLabel|traceDirectionChipClass|traceDirectionLabel)[\s\S]*?\}\s*from\s*'@\/utils\/antmedUi'/,
    )
  })
  it('khởi tạo resource getLotTrace (auto:false) + submit cùng mã lô khi Truy vết', () => {
    expect(pageSrc).toMatch(/getLotTrace\(\{\s*auto:\s*false\s*\}\)/)
    // submit truy vết phát đi name cho CẢ getLot và getLotTrace (cùng mã lô — chống dead-control).
    expect(pageSrc).toMatch(/trace\.submit\(\{\s*name\s*\}\)/)
  })
  it('layout 2 card: cardrow cols-2 (grid 2 cột) chứa left "Thông tin lot" + right "Cây truy vết"', () => {
    // cardrow cols-2 = grid 2 cột ở breakpoint lớn (lg:grid-cols-2 / md:grid-cols-2).
    expect(pageSrc).toMatch(/grid-cols-2|md:grid-cols-2|lg:grid-cols-2/)
    expect(pageSrc).toContain('Thông tin lot')
    expect(pageSrc).toContain('Cây truy vết')
  })
  it('đọc ĐÚNG field event BE: posting_datetime/entry_type/direction/warehouse_name/qty/voucher_no', () => {
    expect(pageSrc).toMatch(/trace\.data\b/)
    expect(pageSrc).not.toMatch(/trace\.data\?\.data/)
    expect(pageSrc).toMatch(/\.posting_datetime/)
    expect(pageSrc).toMatch(/\.entry_type/)
    expect(pageSrc).toMatch(/\.direction/)
    expect(pageSrc).toMatch(/\.warehouse_name/)
    expect(pageSrc).toMatch(/\.qty\b/)
    expect(pageSrc).toMatch(/\.voucher_no/)
    // BV/NV nếu có (hospital/nv_employee).
    expect(pageSrc).toMatch(/\.hospital|\.nv_employee/)
  })
  it('event ngày qua fmtDate(posting_datetime) — dd/MM/yyyy, KHÔNG render ISO thô', () => {
    expect(pageSrc).toMatch(/fmtDate\([^)]*posting_datetime\)/)
  })
  it('chip chiều qua traceDirectionChipClass/Label + chip loại kho (warehouse_type)', () => {
    expect(pageSrc).toMatch(/traceDirectionChipClass\(|traceDirectionLabel\(/)
    expect(pageSrc).toMatch(/warehouse_type/)
  })
  it('empty-sub khi events rỗng: "Chưa có lịch sử di chuyển"', () => {
    expect(pageSrc).toContain('Chưa có lịch sử di chuyển')
  })
  it('tri-branch riêng cho card trace: loading / error / empty (events.length)', () => {
    // card trace có nhánh loading + error + empty (dùng events list).
    expect(pageSrc).toMatch(/trace\.loading/)
    expect(pageSrc).toMatch(/trace\.error/)
    expect(pageSrc).toMatch(/events\.length|events\?\.length|!events/)
  })
  it('recall_status (chip read-only, M03-2 left-card) VẪN render — sanity giữ slice trước', () => {
    expect(pageSrc).toMatch(/recall_status/)
  })
})

// ── M03-7 helper thuần — RECALL_INITIATE_STATUSES đồng bộ BE export + recallChipClass đủ 3 trạng thái ──
describe('M03-7 helper thuần — RECALL_INITIATE_STATUSES + recallChipClass 3 trạng thái', () => {
  it("RECALL_INITIATE_STATUSES == ('Theo dõi','Đã thu hồi') — đồng bộ BE RECALL_STATUS_OPTIONS", () => {
    expect(RECALL_INITIATE_STATUSES).toEqual(['Theo dõi', 'Đã thu hồi'])
    // KHÔNG gồm 'Bình thường' (không recall ngược về bình thường khi KHỞI TẠO).
    expect(RECALL_INITIATE_STATUSES).not.toContain('Bình thường')
  })
  it("RECALL_INITIATE_DEFAULT == 'Đã thu hồi' (mockup D3 mức mặc định)", () => {
    expect(RECALL_INITIATE_DEFAULT).toBe('Đã thu hồi')
    expect(RECALL_INITIATE_STATUSES).toContain(RECALL_INITIATE_DEFAULT)
  })
  it('recallChipClass map đủ 3 trạng thái đúng theme (Theo dõi=warn, Đã thu hồi=danger, Bình thường=neutral)', () => {
    expect(recallChipTheme('Bình thường')).toBe('neutral')
    expect(recallChipTheme('Theo dõi')).toBe('warn')
    expect(recallChipTheme('Đã thu hồi')).toBe('danger')
    expect(recallChipClass('Theo dõi')).toBe(PILL_THEME.warn)
    expect(recallChipClass('Đã thu hồi')).toBe(PILL_THEME.danger)
  })
})

// ── M03-7 data layer — initiateRecall gọi đúng endpoint initiate_recall (POST mutation) ──
describe('M03-7 data layer — initiateRecall url initiate_recall + method POST', () => {
  it('initiateRecall → createResource url antmed_crm.api.antmed.inventory.initiate_recall', () => {
    expect(dataSrc).toMatch(/export function initiateRecall/)
    expect(dataSrc).toMatch(
      /antmed_crm\.api\.antmed\.inventory\.initiate_recall/,
    )
  })
  it("method: 'POST' (MUTATION — KHÔNG GET mặc định)", () => {
    const block = dataSrc.slice(
      dataSrc.indexOf('export function initiateRecall'),
      dataSrc.indexOf('export function initiateRecall') + 360,
    )
    expect(block).toMatch(/method:\s*['"]POST['"]/)
  })
  it('dùng createResource (đọc dict THƯỜNG r.data), KHÔNG createListResource', () => {
    // Toàn file data dùng createResource; sanity riêng block initiateRecall không kéo list-resource.
    const block = dataSrc.slice(
      dataSrc.indexOf('export function initiateRecall'),
      dataSrc.indexOf('export function initiateRecall') + 360,
    )
    expect(block).toMatch(/createResource\(/)
    expect(block).not.toMatch(/createListResource/)
  })
})

// ── M03-7 Page — nút "⚠ Khởi tạo Recall theo lot này" ở chân card + confirm-modal Dialog ──
describe('AntmedLotTrace.vue — M03-7 nút Khởi tạo Recall + confirm-modal', () => {
  it('import initiateRecall (data/antmed) + Dialog (frappe-ui) + RECALL_INITIATE_STATUSES (antmedUi)', () => {
    expect(pageSrc).toMatch(
      /import\s*\{[\s\S]*?initiateRecall[\s\S]*?\}\s*from\s*'@\/data\/antmed'/,
    )
    expect(pageSrc).toMatch(
      /import\s*\{[\s\S]*?\bDialog\b[\s\S]*?\}\s*from\s*'frappe-ui'/,
    )
    expect(pageSrc).toMatch(
      /import\s*\{[\s\S]*?RECALL_INITIATE_STATUSES[\s\S]*?\}\s*from\s*'@\/utils\/antmedUi'/,
    )
  })
  it('nút "⚠ Khởi tạo Recall theo lot này" (theme red) ở CHÂN card "Cây truy vết"', () => {
    expect(pageSrc).toContain('⚠ Khởi tạo Recall theo lot này')
    expect(pageSrc).toMatch(/theme=['"]red['"]/)
    // Nút nằm SAU block trace (timeline </ol>) — chân card.
    const olIdx = pageSrc.indexOf('</ol>')
    const btnIdx = pageSrc.indexOf('Khởi tạo Recall theo lot này')
    expect(olIdx).toBeGreaterThan(-1)
    expect(btnIdx).toBeGreaterThan(olIdx)
  })
  it('nút disabled khi chưa load lô (!data) HOẶC recall_status === "Đã thu hồi"', () => {
    expect(pageSrc).toMatch(
      /:disabled=['"]!data \|\| data\.recall_status === 'Đã thu hồi'['"]/,
    )
  })
  it('tri-state nút: loading bind initiateRecall.loading', () => {
    expect(pageSrc).toMatch(/:loading=['"]initiateRecall\.loading['"]/)
  })
  it('confirm-modal Dialog: hiện mã lô (lot_no) + SKU (item_name)', () => {
    expect(pageSrc).toMatch(/<Dialog\b/)
    expect(pageSrc).toMatch(/data\?\.lot_no/)
    expect(pageSrc).toMatch(/data\?\.item_name/)
  })
  it('FormControl lý do recall (textarea, v-model recallReason, label bắt buộc)', () => {
    expect(pageSrc).toContain('Lý do recall')
    expect(pageSrc).toMatch(/v-model=['"]recallReason['"]/)
    expect(pageSrc).toMatch(/type=['"]textarea['"]/)
  })
  it('FormControl mức recall (select, v-model recallStatus, options từ RECALL_INITIATE_STATUSES)', () => {
    expect(pageSrc).toContain('Mức recall')
    expect(pageSrc).toMatch(/v-model=['"]recallStatus['"]/)
    expect(pageSrc).toMatch(/recallStatusOptions/)
    // options build từ RECALL_INITIATE_STATUSES (đồng bộ BE) — KHÔNG hardcode array literal.
    expect(pageSrc).toMatch(/RECALL_INITIATE_STATUSES\.map/)
  })
  it("mức recall default = 'Đã thu hồi' (RECALL_INITIATE_DEFAULT)", () => {
    expect(pageSrc).toMatch(/recallStatus\s*=\s*ref\(RECALL_INITIATE_DEFAULT\)/)
  })
  it('nút Hủy + Xác nhận khởi tạo; Xác nhận disabled khi reason rỗng HOẶC đang submit', () => {
    expect(pageSrc).toContain('Hủy')
    expect(pageSrc).toContain('Xác nhận khởi tạo')
    expect(pageSrc).toMatch(
      /:disabled=['"]!recallReason\.trim\(\) \|\| initiateRecall\.loading['"]/,
    )
  })
  it('submit chặn FE khi reason rỗng (return sớm trong submitRecall)', () => {
    expect(pageSrc).toMatch(/function submitRecall/)
    expect(pageSrc).toMatch(/recallReason\.value\.trim\(\)/)
    // có nhánh return sớm khi reason rỗng.
    expect(pageSrc).toMatch(/if\s*\(!reason[^)]*\)\s*return/)
  })
  it('submit phát đi param == lựa chọn UI (lot/reason/status) — chống dead-control', () => {
    expect(pageSrc).toMatch(
      /initiateRecall\.submit\(\s*\{\s*lot:\s*data\.value\.name,\s*reason,\s*status:\s*recallStatus\.value/,
    )
  })
  it('success → toast + đóng modal + reset reason + lot.reload() (chip recall_status đổi)', () => {
    expect(pageSrc).toMatch(
      /toast\.success\(\s*__\('Đã khởi tạo recall cho lô /,
    )
    expect(pageSrc).toMatch(/showRecallModal\.value\s*=\s*false/)
    expect(pageSrc).toMatch(/lot\.reload\(\)/)
  })
  it('error → toast.error(err.messages[0]) KHÔNG đổi chip (không reload trong onError)', () => {
    expect(pageSrc).toMatch(
      /onError\([\s\S]*?toast\.error\(\s*err\?\.messages\?\.\[0\]/,
    )
  })
  it('KHÔNG mock / KHÔNG createListResource / KHÔNG window.confirm (Dialog thay confirm)', () => {
    const code = pageSrc
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .replace(/<!--[\s\S]*?-->/g, '')
      .replace(/^\s*\/\/.*$/gm, '')
    expect(code).not.toMatch(/createListResource/)
    expect(code).not.toMatch(/window\.confirm|alert\(/)
    expect(code).not.toMatch(/antmedMock/)
  })
})
