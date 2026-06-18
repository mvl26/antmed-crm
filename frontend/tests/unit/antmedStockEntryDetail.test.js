import { readFileSync } from 'fs'
import path from 'path'
import { shouldRedirectNotPermitted } from '../../src/utils/antmedGuard'
import {
  fmtDate,
  fmtQty,
  formatVnMoney,
  cocqChipTheme,
  cocqChipClass,
  cocqChipLabel,
  PILL_THEME,
} from '../../src/utils/antmedUi'

// M03-8 — màn "Chi tiết phiếu xuất / Vật tư đã chuẩn bị" (NV Kinh doanh, drill-down từ
// /antmed/warehouse/stock-entries → /antmed/warehouse/stock-entries/:name, AntmedStockEntryDetail.vue,
// mockup C2 Wizard bước 3 card "Vật tư đã chuẩn bị").
// Idiom test = behavior-assert helper THUẦN (antmedUi.js không import frappe-ui → import trực tiếp)
// + content-assert nguồn (router/page/data) cho url & wiring (data/antmed.js KÉO frappe-ui nên vitest
// KHÔNG load được → assert chuỗi nguồn cho url) + SSR render-verify harness (compile template THẬT).

const srcDir = path.resolve(__dirname, '../../src')
const routerSrc = readFileSync(path.join(srcDir, 'router.js'), 'utf8')
const pageSrc = readFileSync(
  path.join(srcDir, 'pages/AntmedStockEntryDetail.vue'),
  'utf8',
)
const listPageSrc = readFileSync(
  path.join(srcDir, 'pages/AntmedStockEntries.vue'),
  'utf8',
)
const dataSrc = readFileSync(path.join(srcDir, 'data/antmed.js'), 'utf8')

const antmed = () => ({ isCrmUser: () => false, isAntmedUser: () => true })
const crm = () => ({ isCrmUser: () => true, isAntmedUser: () => false })
const outsider = () => ({ isCrmUser: () => false, isAntmedUser: () => false })

// ── (1) Data layer — getStockEntry gọi đúng endpoint + method GET ──────────────
describe('M03-8 data layer — getStockEntry url get_stock_entry + GET', () => {
  it("getStockEntry → createResource url 'antmed_crm.api.antmed.inventory.get_stock_entry'", () => {
    expect(dataSrc).toMatch(/export function getStockEntry/)
    expect(dataSrc).toMatch(/antmed_crm\.api\.antmed\.inventory\.get_stock_entry/)
  })
  it("method: 'GET' (RAW dict THƯỜNG, đọc r.data trực tiếp)", () => {
    const block = dataSrc.slice(
      dataSrc.indexOf('export function getStockEntry'),
      dataSrc.indexOf('export function getStockEntry') + 360,
    )
    expect(block).toMatch(/method:\s*['"]GET['"]/)
    expect(block).toMatch(/auto\s*=\s*false/)
  })
  it('dùng createResource (đọc dict THƯỜNG r.data), KHÔNG createListResource', () => {
    expect(dataSrc).toMatch(/import\s*\{\s*createResource\s*\}\s*from\s*'frappe-ui'/)
    expect(dataSrc).not.toMatch(/import[^\n]*createListResource/)
  })
})

// ── (2) Page đọc entry.data.items KHÔNG .data.data (dict THƯỜNG, KHÔNG list bọc) ─
describe('AntmedStockEntryDetail.vue — đọc entry.data.items (KHÔNG .data.data)', () => {
  it('đọc dict THƯỜNG: entry.data.items + entry.data trực tiếp (KHÔNG .data.data của list bọc)', () => {
    expect(pageSrc).toMatch(/entry\.data\?\.items|entry\.data\.items/)
    expect(pageSrc).not.toMatch(/entry\.data\?\.data/)
  })
  it('import getStockEntry từ data/antmed', () => {
    expect(pageSrc).toMatch(
      /import\s*\{[\s\S]*?getStockEntry[\s\S]*?\}\s*from\s*'@\/data\/antmed'/,
    )
  })
})

// ── (3) Render header keys + bảng cột SKU/Tên/Lot/HSD/SL/ĐVT ───────────────────
describe('AntmedStockEntryDetail.vue — header keys + cột bảng mockup C2', () => {
  it('header card đọc ĐÚNG field BE: entry_type/hospital_name/nv_employee_name/expected_use_date/from_warehouse/to_warehouse/total_value', () => {
    expect(pageSrc).toMatch(/data\.entry_type/)
    expect(pageSrc).toMatch(/data\.hospital_name/)
    expect(pageSrc).toMatch(/data\.nv_employee_name/)
    expect(pageSrc).toMatch(/data\.expected_use_date/)
    expect(pageSrc).toMatch(/data\.from_warehouse/)
    expect(pageSrc).toMatch(/data\.to_warehouse/)
    expect(pageSrc).toMatch(/data\.total_value/)
  })
  it('bảng đọc ĐÚNG field dòng BE: item/item_name/lot_no/expiry_date/qty/uom/cocq_ok', () => {
    expect(pageSrc).toMatch(/row\.item\b/)
    expect(pageSrc).toMatch(/row\.item_name/)
    expect(pageSrc).toMatch(/row\.lot_no/)
    expect(pageSrc).toMatch(/row\.expiry_date/)
    expect(pageSrc).toMatch(/row\.qty/)
    expect(pageSrc).toMatch(/row\.uom/)
    expect(pageSrc).toMatch(/row\.cocq_ok/)
  })
  it('header cột bảng đủ VI: SKU / Tên / Lot / HSD / SL / ĐVT / CO-CQ + card title "Vật tư đã chuẩn bị"', () => {
    for (const label of ['SKU', 'Tên', 'Lot', 'HSD', 'SL', 'ĐVT', 'CO-CQ', 'Vật tư đã chuẩn bị']) {
      expect(pageSrc).toContain(label)
    }
  })
  it('HSD qua fmtDate(row.expiry_date); SL qua fmtQty(row.qty); tiền qua formatVnMoney(total_value)', () => {
    expect(pageSrc).toMatch(/fmtDate\(row\.expiry_date\)/)
    expect(pageSrc).toMatch(/fmtQty\(row\.qty\)/)
    expect(pageSrc).toMatch(/formatVnMoney\(data\.total_value\)/)
    expect(pageSrc).toMatch(
      /import\s*\{[\s\S]*?(fmtDate|fmtQty|cocqChipClass)[\s\S]*?\}\s*from\s*'@\/utils\/antmedUi'/,
    )
  })
  it('SKU hiển thị item_name (tên) ở cột Tên, KHÔNG chỉ mã thô', () => {
    expect(pageSrc).toMatch(/row\.item_name/)
  })
})

// ── (4) Helper thuần cocqChip — 3 nhánh (true/false/None) ──────────────────────
describe('cocqChipLabel/Theme — chip CO/CQ 3 nhánh (true/false/None)', () => {
  it("true → theme 'ok' (green) + nhãn 'CO/CQ ✓'", () => {
    expect(cocqChipTheme(true)).toBe('ok')
    expect(cocqChipClass(true)).toBe(PILL_THEME.ok)
    expect(cocqChipLabel(true)).toBe('CO/CQ ✓')
  })
  it("false → theme 'warn' (cam) + nhãn 'Thiếu CO/CQ'", () => {
    expect(cocqChipTheme(false)).toBe('warn')
    expect(cocqChipClass(false)).toBe(PILL_THEME.warn)
    expect(cocqChipLabel(false)).toBe('Thiếu CO/CQ')
  })
  it("null/undefined → theme 'warn' + nhãn 'Thiếu CO/CQ' (an toàn, không vỡ render)", () => {
    expect(cocqChipTheme(null)).toBe('warn')
    expect(cocqChipTheme(undefined)).toBe('warn')
    expect(cocqChipLabel(null)).toBe('Thiếu CO/CQ')
    expect(cocqChipLabel(undefined)).toBe('Thiếu CO/CQ')
  })
  it('chip CO/CQ render qua cocqChipClass + cocqChipLabel (kèm CHỮ — WCAG AA)', () => {
    expect(pageSrc).toMatch(/cocqChipClass\(row\.cocq_ok\)/)
    expect(pageSrc).toMatch(/cocqChipLabel\(row\.cocq_ok\)/)
    expect(pageSrc).toMatch(/aria-label/)
  })
})

// ── (5) Tri-branch loading / error / empty / not-found ─────────────────────────
describe('AntmedStockEntryDetail.vue — tri-branch loading/error/empty/not-found', () => {
  it("loading: 'Đang tải phiếu…' (entry.loading)", () => {
    expect(pageSrc).toMatch(/entry\.loading/)
    expect(pageSrc).toContain('Đang tải phiếu…')
  })
  it("error: 'Lỗi tải phiếu' + nút 'Thử lại' (entry.reload)", () => {
    expect(pageSrc).toMatch(/entry\.error/)
    expect(pageSrc).toContain('Lỗi tải phiếu')
    expect(pageSrc).toContain('Thử lại')
    expect(pageSrc).toMatch(/entry\.reload\(\)/)
  })
  it("empty (phiếu 0 dòng): 'Phiếu chưa có vật tư' (!items.length)", () => {
    expect(pageSrc).toContain('Phiếu chưa có vật tư')
    expect(pageSrc).toMatch(/!items\.length/)
  })
  it("not-found: 'Không tìm thấy phiếu' (isNotFound — DoesNotExist / fail-closed)", () => {
    expect(pageSrc).toMatch(/isNotFound/)
    expect(pageSrc).toContain('Không tìm thấy phiếu')
    expect(pageSrc).toMatch(/DoesNotExist/)
  })
  it('fetch theo route.params.name: onMounted/watch → entry.submit({ name })', () => {
    expect(pageSrc).toMatch(/route\.params\.name/)
    expect(pageSrc).toMatch(/entry\.submit\(\{\s*name\s*\}\)/)
    expect(pageSrc).toMatch(/onMounted\(/)
    expect(pageSrc).toMatch(/watch\(/)
  })
})

// ── (6) Router — route name AntmedStockEntryDetail path /antmed/warehouse/stock-entries/:name ──
describe('M03-8 route — AntmedStockEntryDetail /antmed/warehouse/stock-entries/:name', () => {
  it('router.js đăng ký AntmedStockEntryDetail → /antmed/warehouse/stock-entries/:name (lazy page)', () => {
    expect(routerSrc).toMatch(
      /path:\s*['"]\/antmed\/warehouse\/stock-entries\/:name['"]/,
    )
    expect(routerSrc).toMatch(/name:\s*['"]AntmedStockEntryDetail['"]/)
    expect(routerSrc).toMatch(/import\(['"]@\/pages\/AntmedStockEntryDetail\.vue['"]\)/)
  })
  it('name AntmedStockEntryDetail DUY NHẤT', () => {
    const matches = routerSrc.match(/name:\s*['"]AntmedStockEntryDetail['"]/g) || []
    expect(matches).toHaveLength(1)
  })
  it('no-regression: route list /antmed/warehouse/stock-entries (name AntmedStockEntries) GIỮ nguyên', () => {
    expect(routerSrc).toMatch(/path:\s*['"]\/antmed\/warehouse\/stock-entries['"]/)
    expect(routerSrc).toMatch(/name:\s*['"]AntmedStockEntries['"]/)
  })
  it('meta.role=warehouse ⇒ sidebar kho', () => {
    const idx = routerSrc.indexOf("'/antmed/warehouse/stock-entries/:name'")
    const block = routerSrc.slice(idx, idx + 260)
    expect(block).toMatch(/role:\s*['"]warehouse['"]/)
  })
  it('guard: AntMed user + CRM user mở route KHÔNG redirect; outsider bị redirect', () => {
    const p = { path: '/antmed/warehouse/stock-entries/AM-SE-2026-00001' }
    expect(shouldRedirectNotPermitted(p, antmed())).toBe(false)
    expect(shouldRedirectNotPermitted(p, crm())).toBe(false)
    expect(shouldRedirectNotPermitted(p, outsider())).toBe(true)
  })
})

// ── (7) List page có drill-down tới AntmedStockEntryDetail ─────────────────────
describe('AntmedStockEntries.vue — drill-down RouterLink tới AntmedStockEntryDetail', () => {
  it("RouterLink/router-link tới name 'AntmedStockEntryDetail' params { name: row.name }", () => {
    expect(listPageSrc).toMatch(/name:\s*['"]AntmedStockEntryDetail['"]/)
    expect(listPageSrc).toMatch(/params:\s*\{\s*name:\s*row\.name\s*\}/)
    expect(listPageSrc).toMatch(/<RouterLink|router-link/)
  })
  it('no-regression: list KHÔNG đổi shape (vẫn đọc r.data.data + cột cũ)', () => {
    expect(listPageSrc).toMatch(/entries\.data\?\.data/)
    expect(listPageSrc).toMatch(/row\.nv_employee_name/)
    expect(listPageSrc).toMatch(/row\.entry_type/)
  })
})

// ── (8) no-mock / no-aggregate guard ──────────────────────────────────────────
describe('AntmedStockEntryDetail.vue — no-mock / no-aggregate (BE đã trả sẵn)', () => {
  it('KHÔNG hardcode mock / KHÔNG createListResource·axios·TanStack (code, không tính comment)', () => {
    const code = pageSrc
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .replace(/<!--[\s\S]*?-->/g, '')
      .replace(/^\s*\/\/.*$/gm, '')
    expect(code).not.toMatch(/createListResource/)
    expect(code).not.toMatch(/axios|@tanstack\/vue-query|useApi\(/)
    expect(code).not.toMatch(/antmedMock/)
    // KHÔNG hardcode dữ liệu mockup C2 (VT-0231 / Vicryl).
    expect(code).not.toMatch(/VT-0231|Vicryl/)
  })
  it('KHÔNG aggregate ở FE (BE đã gộp/sort): page KHÔNG .sort(/.reduce( trên items', () => {
    const code = pageSrc
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .replace(/<!--[\s\S]*?-->/g, '')
      .replace(/^\s*\/\/.*$/gm, '')
    expect(code).not.toMatch(/\.sort\(/)
    expect(code).not.toMatch(/\.reduce\(/)
  })
})

// ── (R) SSR render-verify harness — compile TEMPLATE thật + renderToString (data live-shape) ──
// MIRROR <script setup> AntmedStockEntryDetail.vue: expose data/items (đọc thẳng resourceData) +
// helper THẬT (fmtDate/fmtQty/formatVnMoney/cocqChip*/entryTypeChipTheme/formatStockTime/routeName).
describe('M03-8 SSR render-verify — AntmedStockEntryDetail render HTML thật', () => {
  async function renderTemplate(resourceData, { loading = false, error = null } = {}) {
    const { parse } = await import('@vue/compiler-sfc')
    const { compile } = await import('@vue/compiler-dom')
    const vue = await import('vue')
    const { renderToString } = await import('@vue/server-renderer')
    const ui = await import('../../src/utils/antmedUi')

    const raw = readFileSync(path.join(srcDir, 'pages/AntmedStockEntryDetail.vue'), 'utf8')
    const { descriptor } = parse(raw, { filename: 'AntmedStockEntryDetail.vue' })
    const { code } = compile(descriptor.template.content, {
      mode: 'function',
      hoistStatic: false,
      prefixIdentifiers: true,
    })
    // eslint-disable-next-line no-new-func
    const renderFn = new Function('Vue', code)(vue)

    const i18n = (s) => s
    const comp = {
      components: {
        Badge: { props: ['label', 'theme'], render() { return vue.h('span', {}, this.label) } },
        Button: { props: ['label'], emits: ['click'], render() { return vue.h('button', {}, this.label) } },
        RouterLink: { render() { return vue.h('a', {}, this.$slots.default?.()) } },
        LoadingIndicator: { render() { return vue.h('span', {}, '...') } },
      },
      setup() {
        const entry = { data: resourceData, loading, error, reload() {}, submit() {} }
        const routeName = vue.computed(() => 'AM-SE-2026-00007')
        const data = vue.computed(() => entry.data || null)
        const items = vue.computed(() => entry.data?.items || [])
        const isNotFound = vue.computed(() => {
          if (error) {
            const exc = error.exc_type || ''
            return /DoesNotExist/i.test(exc)
          }
          const d = entry.data
          if (d && !d.entry_type && !(d.items && d.items.length)) return true
          return false
        })
        return {
          __: i18n,
          entry,
          routeName,
          data,
          items,
          isNotFound,
          fmtDate: ui.fmtDate,
          fmtQty: ui.fmtQty,
          formatVnMoney: ui.formatVnMoney,
          formatStockTime: ui.formatStockTime,
          entryTypeChipTheme: ui.entryTypeChipTheme,
          cocqChipClass: ui.cocqChipClass,
          cocqChipLabel: ui.cocqChipLabel,
        }
      },
      render: renderFn,
    }
    const app = vue.createSSRApp(comp)
    app.config.warnHandler = () => {}
    return await renderToString(app)
  }

  const LIVE = {
    name: 'AM-SE-2026-00007',
    entry_type: 'Xuất cho NV',
    posting_datetime: '2026-06-17 09:05:00',
    from_warehouse: 'Kho Tổng HN',
    to_warehouse: 'Kho NV Hùng',
    nv_employee: 'hung@antmed.vn',
    nv_employee_name: 'Nguyễn Văn Hùng',
    hospital: 'BV-K',
    hospital_name: 'BV K',
    expected_use_date: '2026-06-20',
    total_value: 1_310_000,
    items: [
      {
        item: 'VT-0231',
        item_name: 'Chỉ Vicryl 2-0',
        lot: 'L-22834',
        lot_no: 'L-22834',
        expiry_date: '2028-11-30',
        qty: 5,
        uom: 'Sợi',
        unit_price: 190000,
        amount: 950000,
        cocq_ok: true,
      },
      {
        item: 'VT-0188',
        item_name: 'Gạc cầm máu',
        lot: 'L-90011',
        lot_no: 'L-90011',
        expiry_date: '2029-04-30',
        qty: 3,
        uom: 'Gói',
        unit_price: 120000,
        amount: 360000,
        cocq_ok: false,
      },
    ],
  }

  it('render data: header (BV K · NV Hùng) + bảng VT-0231/Chỉ Vicryl 2-0/HSD + chip CO/CQ 2 nhánh', async () => {
    const html = await renderTemplate(LIVE)
    expect(html).toContain('Vật tư đã chuẩn bị')
    // header *_name (KHÔNG mã/email thô).
    expect(html).toContain('BV K')
    expect(html).toContain('Nguyễn Văn Hùng')
    // bảng dòng vật tư live-shape.
    expect(html).toContain('VT-0231')
    expect(html).toContain('Chỉ Vicryl 2-0')
    expect(html).toContain('L-22834')
    // HSD dd/MM/yyyy (KHÔNG ISO thô).
    expect(html).toContain('30/11/2028')
    expect(html).not.toContain('2028-11-30')
    // ngày dự kiến dùng.
    expect(html).toContain('20/06/2026')
    // chip CO/CQ 2 nhánh (true → 'CO/CQ ✓', false → 'Thiếu CO/CQ').
    expect(html).toContain('CO/CQ ✓')
    expect(html).toContain('Thiếu CO/CQ')
    // KHÔNG lộ status EN / loại EN.
    expect(html).not.toMatch(/\bIssue\b|\bReady\b|\bPending\b/)
  })

  it("render phiếu 0 dòng → 'Phiếu chưa có vật tư' (KHÔNG bịa dòng)", async () => {
    const data = { ...LIVE, items: [], total_value: null }
    const html = await renderTemplate(data)
    expect(html).toContain('Phiếu chưa có vật tư')
    // header vẫn render (BV K).
    expect(html).toContain('BV K')
  })

  it("render loading → 'Đang tải phiếu…' (KHÔNG bịa số)", async () => {
    const html = await renderTemplate(null, { loading: true })
    expect(html).toContain('Đang tải phiếu…')
  })

  it("render error → 'Lỗi tải phiếu'", async () => {
    const html = await renderTemplate(null, { error: { messages: ['x'] } })
    expect(html).toContain('Lỗi tải phiếu')
  })

  it("render not-found (DoesNotExistError) → 'Không tìm thấy phiếu'", async () => {
    const html = await renderTemplate(null, { error: { exc_type: 'DoesNotExistError' } })
    expect(html).toContain('Không tìm thấy phiếu')
  })

  it("render fail-closed (shape rỗng: name nhưng KHÔNG entry_type/dòng) → 'Không tìm thấy phiếu' (KHÔNG rò header)", async () => {
    const empty = {
      name: 'AM-SE-2026-00007',
      entry_type: null,
      hospital: null,
      hospital_name: null,
      nv_employee: null,
      nv_employee_name: null,
      expected_use_date: null,
      total_value: null,
      items: [],
    }
    const html = await renderTemplate(empty)
    expect(html).toContain('Không tìm thấy phiếu')
    // KHÔNG rò header thật (không có tên BV/NV nào lọt vì nhánh not-found chiếm trước).
  })
})

// ── Helper thuần fmtQty/fmtDate sanity (cột SL/HSD) ────────────────────────────
describe('fmtQty/fmtDate — cột SL/HSD bảng vật tư', () => {
  it("fmtQty: số nguyên VI có phân tách; thiếu/NaN → '—'", () => {
    expect(fmtQty(5)).toBe((5).toLocaleString('vi-VN'))
    expect(fmtQty(1000)).toBe((1000).toLocaleString('vi-VN'))
    expect(fmtQty(null)).toBe('—')
    expect(fmtQty(undefined)).toBe('—')
    expect(fmtQty('abc')).toBe('—')
  })
  it("fmtDate HSD: '2028-11-30' → '30/11/2028'", () => {
    expect(fmtDate('2028-11-30')).toBe('30/11/2028')
  })
  it("formatVnMoney total_value: 1.310.000 → '1,3 tr'", () => {
    expect(formatVnMoney(1_310_000)).toBe('1,3 tr')
  })
})
