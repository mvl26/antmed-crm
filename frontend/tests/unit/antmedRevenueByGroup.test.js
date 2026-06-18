import { readFileSync } from 'fs'
import path from 'path'
import {
  REVENUE_GROUP_COLORS,
  revenueGroupBarClass,
  revenueGroupSwatchClass,
  stackSegmentHeightPct,
  stackColumnTotals,
  stackColumnMax,
  formatVnMoney,
} from '../../src/utils/antmedUi'

// M02-9 — widget "Doanh thu theo Nhóm vật tư" (mockup A3, Dashboard CEO, màn /antmed/revenue).
// Idiom test (= antmedRevenueMix.test.js): content-assert nguồn (data/antmed.js, AntmedRevenuePage.vue,
// router.js, antmedNav.js) + behavior-assert helper THUẦN (antmedUi.js không import frappe-ui → import
// trực tiếp). data/antmed.js + .vue KÉO frappe-ui nên vitest KHÔNG mount trực tiếp → assert chuỗi +
// SSR render-verify harness compile SFC thật (cuối file).

const srcDir = path.resolve(__dirname, '../../src')
const dataSrc = readFileSync(path.join(srcDir, 'data/antmed.js'), 'utf8')
const uiSrc = readFileSync(path.join(srcDir, 'utils/antmedUi.js'), 'utf8')
const pageSrc = readFileSync(path.join(srcDir, 'pages/AntmedRevenuePage.vue'), 'utf8')
const routerSrc = readFileSync(path.join(srcDir, 'router.js'), 'utf8')
const navSrc = readFileSync(path.join(srcDir, 'data/antmedNav.js'), 'utf8')

// ── Data layer — getRevenueByGroup url + method GET (naming contract + GET-only) ──────────────
describe('M02-9 data layer — getRevenueByGroup url revenue_by_group + method GET', () => {
  it('export function getRevenueByGroup', () => {
    expect(dataSrc).toMatch(/export function getRevenueByGroup/)
  })

  it('url == antmed_crm.api.antmed.contract.revenue_by_group (KHÔNG prefix sai)', () => {
    expect(dataSrc).toMatch(/antmed_crm\.api\.antmed\.contract\.revenue_by_group/)
    expect(dataSrc).not.toMatch(/['"]crm\.api\.antmed\.contract\.revenue_by_group/)
  })

  it("resource có method === 'GET' (chống defect POST→403)", () => {
    const block = dataSrc.slice(dataSrc.indexOf('export function getRevenueByGroup'))
    expect(block).toMatch(/method:\s*'GET'/)
  })

  it('dùng createResource (dict THƯỜNG), KHÔNG createListResource', () => {
    expect(dataSrc).toMatch(/import\s*\{\s*createResource\s*\}\s*from\s*'frappe-ui'/)
    expect(dataSrc).not.toMatch(/import[^\n]*createListResource/)
  })

  it('KHÔNG axios / TanStack trong data layer', () => {
    expect(dataSrc).not.toMatch(/axios|@tanstack/)
  })
})

// ── Page reads r.data.{months,groups,grand_total} — KHÔNG .data.data (dict THƯỜNG) ────────────
describe('M02-9 AntmedRevenuePage — đọc r.data.months/groups KHÔNG .data.data', () => {
  it('import getRevenueByGroup từ @/data/antmed', () => {
    expect(pageSrc).toMatch(/getRevenueByGroup/)
    expect(pageSrc).toMatch(/from '@\/data\/antmed'/)
  })

  it('đọc revenue.data?.months / groups / grand_total TRỰC TIẾP', () => {
    expect(pageSrc).toMatch(/revenue\.data\?\.months/)
    expect(pageSrc).toMatch(/revenue\.data\?\.groups/)
    expect(pageSrc).toMatch(/revenue\.data\?\.grand_total/)
  })

  it('KHÔNG đọc .data.data (đó là idiom list bọc, KHÔNG phải dict THƯỜNG)', () => {
    expect(pageSrc).not.toMatch(/revenue\.data\?\.data/)
    expect(pageSrc).not.toMatch(/\.data\.data/)
  })

  it('fetch auto:true', () => {
    expect(pageSrc).toMatch(/getRevenueByGroup\(\{[\s\S]*?auto:\s*true/)
  })
})

// ── Page render — breadcrumb, tiêu đề widget, 12 cột bar, legend 5 nhóm ───────────────────────
describe('M02-9 AntmedRevenuePage — render breadcrumb + 12 cột + legend 5 nhóm', () => {
  it("breadcrumb 'Trang chủ › Doanh thu'", () => {
    expect(pageSrc).toMatch(/__\('Trang chủ'\)/)
    expect(pageSrc).toMatch(/__\('Doanh thu'\)/)
    expect(pageSrc).toMatch(/›/)
  })

  it("tiêu đề widget 'Doanh thu theo Nhóm vật tư'", () => {
    expect(pageSrc).toMatch(/Doanh thu theo Nhóm vật tư/)
  })

  it('render 12 cột (v-for tháng từ months) — trục X = months', () => {
    expect(pageSrc).toMatch(/v-for="\(month, i\) in months"/)
  })

  it('mỗi cột chồng segment theo groups (v-for g in groups) — tối đa 5 nhóm', () => {
    // Legend + cột đều lặp theo groups (5 nhóm BE).
    expect(pageSrc).toMatch(/v-for="g in groups"/)
  })

  it('segment height qua helper PURE stackSegmentHeightPct (KHÔNG tự tính %)', () => {
    expect(pageSrc).toMatch(/stackSegmentHeightPct/)
    expect(pageSrc).toMatch(/segmentHeight\(g\.monthly\[i\]\)/)
  })

  it('màu segment + legend qua helper PURE (KHÔNG hardcode hex)', () => {
    expect(pageSrc).toMatch(/revenueGroupBarClass/)
    expect(pageSrc).toMatch(/revenueGroupSwatchClass/)
    expect(pageSrc).not.toMatch(/#[0-9a-fA-F]{6}/)
  })

  it('format tiền qua formatVnMoney (KHÔNG tự format)', () => {
    expect(pageSrc).toMatch(/formatVnMoney/)
  })
})

// ── Tri-branch loading / error(+Thử lại) / data ──────────────────────────────────────────────
describe('M02-9 AntmedRevenuePage — tri-branch loading/error/data', () => {
  it("loading → 'Đang tải…'", () => {
    expect(pageSrc).toMatch(/v-if="revenue\.loading"/)
    expect(pageSrc).toMatch(/Đang tải…/)
  })

  it("error → 'Lỗi tải doanh thu' + nút 'Thử lại' (reload)", () => {
    expect(pageSrc).toMatch(/v-else-if="revenue\.error"/)
    expect(pageSrc).toMatch(/Lỗi tải doanh thu/)
    expect(pageSrc).toMatch(/Thử lại/)
    expect(pageSrc).toMatch(/revenue\.reload\(\)/)
  })

  it('v-else render bar (data branch sau loading/error)', () => {
    const idxLoading = pageSrc.indexOf('v-if="revenue.loading"')
    const idxError = pageSrc.indexOf('v-else-if="revenue.error"')
    expect(idxLoading).toBeGreaterThan(-1)
    expect(idxError).toBeGreaterThan(idxLoading)
    expect(pageSrc).toMatch(/<div v-else>/)
  })
})

// ── No mock / no aggregate / no sort guard (FE chỉ trình bày) ─────────────────────────────────
describe('M02-9 AntmedRevenuePage — KHÔNG mock/aggregate/sort dữ liệu doanh thu', () => {
  it('KHÔNG hardcode số mock / import antmedMock', () => {
    expect(pageSrc).not.toMatch(/antmedMock|mockData/)
    // KHÔNG nhúng mảng số liệu cứng trong UI (vd monthly cứng [12, 34, ...]).
    expect(pageSrc).not.toMatch(/monthly:\s*\[/)
  })

  it('page KHÔNG reduce/sort dữ liệu (aggregate scale qua helper PURE)', () => {
    const script = pageSrc.slice(pageSrc.indexOf('<script'))
    expect(script).not.toMatch(/\.reduce\(/)
    expect(script).not.toMatch(/\.sort\(/)
  })

  it('đọc thẳng groups[].monthly[i] (KHÔNG tự gộp bucket/classification)', () => {
    expect(pageSrc).toMatch(/g\.monthly\[i\]/)
  })

  it('KHÔNG axios / TanStack trong page', () => {
    expect(pageSrc).not.toMatch(/axios|@tanstack/)
  })
})

// ── Router — route real-data unique + mock renamed + path giữ + guard hygiene ─────────────────
describe('M02-9 router — AntmedRevenuePage unique + mock AntmedRevenueMock', () => {
  it("route name 'AntmedRevenuePage' tồn tại tại path '/antmed/revenue'", () => {
    expect(routerSrc).toMatch(/name:\s*'AntmedRevenuePage'/)
    expect(routerSrc).toMatch(/path:\s*'\/antmed\/revenue'/)
  })

  it('route name AntmedRevenuePage count === 1 (unique)', () => {
    const m = routerSrc.match(/['"]AntmedRevenuePage['"]/g) || []
    expect(m).toHaveLength(1)
  })

  // Phase 2: mock prototype /ceo/revenue (AntmedRevenueMock) ĐÃ GỠ — chỉ còn /antmed/revenue thật.

  it('meta antmedShell:true + role:ceo cho route real-data', () => {
    const block = routerSrc.slice(routerSrc.indexOf("name: 'AntmedRevenuePage'") - 200)
    expect(block).toMatch(/antmedShell:\s*true/)
    expect(block).toMatch(/role:\s*'ceo'/)
  })

  it('comment route KHÔNG chứa nhãn VI bị guard chặn (NV kinh doanh/Thủ kho/Quản lý)', () => {
    expect(routerSrc).not.toMatch(/NV kinh doanh|Thủ kho|Quản lý/)
  })

  it('lazy import page real-data (code-split chunk)', () => {
    expect(routerSrc).toMatch(/import\('@\/pages\/AntmedRevenuePage\.vue'\)/)
  })
})

// ── Nav — CEO 'Doanh thu' enabled trỏ /antmed/revenue (giữ item CEO khác) ─────────────────────
describe('M02-9 nav — CEO Doanh thu enabled → /antmed/revenue', () => {
  it("item 'Doanh thu' trỏ to '/antmed/revenue' enabled true", () => {
    const block = navSrc.slice(navSrc.indexOf("key: 'ceo-revenue'"))
    const end = block.indexOf('},')
    const item = block.slice(0, end)
    expect(item).toMatch(/label:\s*'Doanh thu'/)
    expect(item).toMatch(/to:\s*'\/antmed\/revenue'/)
    expect(item).toMatch(/enabled:\s*true/)
  })

  it('GIỮ các item CEO khác (Dashboard/Hợp đồng/Cảnh báo) — KHÔNG đổi item khác', () => {
    expect(navSrc).toMatch(/key:\s*'ceo-dash'/)
    expect(navSrc).toMatch(/key:\s*'ceo-contracts'/)
    expect(navSrc).toMatch(/key:\s*'ceo-alerts'/)
  })
})

// ── Helper PURE — màu segment (REVENUE_GROUP_COLORS map) ──────────────────────────────────────
describe('REVENUE_GROUP_COLORS / revenueGroupBarClass / swatch — PURE map', () => {
  it('map đủ 5 nhóm KEY khớp BE (Loại A/B/C/D/Khác)', () => {
    expect(Object.keys(REVENUE_GROUP_COLORS).sort()).toEqual(
      ['Khác', 'Loại A', 'Loại B', 'Loại C', 'Loại D'].sort(),
    )
  })

  it('mỗi nhóm có { bar, swatch } class token (KHÔNG hex)', () => {
    for (const v of Object.values(REVENUE_GROUP_COLORS)) {
      expect(typeof v.bar).toBe('string')
      expect(typeof v.swatch).toBe('string')
      expect(v.bar).not.toMatch(/#[0-9a-fA-F]{6}/)
    }
    expect(uiSrc).not.toMatch(/REVENUE_GROUP_COLORS[\s\S]{0,400}#[0-9a-fA-F]{6}/)
  })

  it('barClass/swatchClass nhóm lạ/thiếu → fallback Khác (an toàn)', () => {
    expect(revenueGroupBarClass('Loại A')).toBe(REVENUE_GROUP_COLORS['Loại A'].bar)
    expect(revenueGroupBarClass('khong-ton-tai')).toBe(REVENUE_GROUP_COLORS['Khác'].bar)
    expect(revenueGroupBarClass(undefined)).toBe(REVENUE_GROUP_COLORS['Khác'].bar)
    expect(revenueGroupSwatchClass('Loại D')).toBe(REVENUE_GROUP_COLORS['Loại D'].swatch)
    expect(revenueGroupSwatchClass(null)).toBe(REVENUE_GROUP_COLORS['Khác'].swatch)
  })
})

// ── Helper PURE — chiều cao segment + tổng cột (scale trình bày) ──────────────────────────────
describe('stackSegmentHeightPct — clamp 0–100 (PURE)', () => {
  it('value/max → round %', () => {
    expect(stackSegmentHeightPct(50, 100)).toBe(50)
    expect(stackSegmentHeightPct(33, 99)).toBe(33)
  })
  it('max<=0 (mọi cột 0) → 0 (no ZeroDivision)', () => {
    expect(stackSegmentHeightPct(10, 0)).toBe(0)
    expect(stackSegmentHeightPct(0, 0)).toBe(0)
  })
  it('null/NaN → 0; value>max → 100 (clamp)', () => {
    expect(stackSegmentHeightPct(null, 100)).toBe(0)
    expect(stackSegmentHeightPct('x', 100)).toBe(0)
    expect(stackSegmentHeightPct(150, 100)).toBe(100)
    expect(stackSegmentHeightPct(-5, 100)).toBe(0)
  })
})

describe('stackColumnTotals / stackColumnMax — scale trục Y (PURE, không sửa dữ liệu)', () => {
  const groups = [
    { classification: 'Loại A', monthly: [10, 0, 5] },
    { classification: 'Loại B', monthly: [20, 0, 0] },
    { classification: 'Khác', monthly: [0, 0, 5] },
  ]
  it('columnTotals = cộng dọc nhóm theo từng cột', () => {
    expect(stackColumnTotals(groups, 3)).toEqual([30, 0, 10])
  })
  it('groups lỗi / monthsLen 0 → mảng 0 (không vỡ)', () => {
    expect(stackColumnTotals(null, 3)).toEqual([0, 0, 0])
    expect(stackColumnTotals(groups, 0)).toEqual([])
    expect(stackColumnTotals([{}], 2)).toEqual([0, 0])
  })
  it('columnMax = cột cao nhất; rỗng/lỗi → 0', () => {
    expect(stackColumnMax([30, 0, 10])).toBe(30)
    expect(stackColumnMax([])).toBe(0)
    expect(stackColumnMax(null)).toBe(0)
    expect(stackColumnMax([0, 0, 0])).toBe(0)
  })
})

describe('formatVnMoney — render tiền VI (PURE, tái dùng)', () => {
  it('tỷ / triệu / thiếu', () => {
    expect(formatVnMoney(79_000_000)).toBe('79 tr')
    expect(formatVnMoney(2_500_000_000)).toBe('2,5 tỷ')
    expect(formatVnMoney(null)).toBe('— ')
  })
})

// ── SSR render-verify harness — compile TEMPLATE thật + renderToString (data + empty) ─────────
// Bằng chứng render THẬT (KHÔNG chỉ content-assert): compile <template> AntmedRevenuePage.vue qua
// compiler-sfc rồi render bằng 1 component có setup() cung cấp ĐÚNG state mà script setup expose +
// helper antmedUi THẬT. KHÔNG new Function trên script body (an toàn — chỉ template compiled render fn).
describe('M02-9 SSR render-verify — AntmedRevenuePage render HTML thật', () => {
  async function renderTemplate(resourceData, { loading = false, error = null } = {}) {
    const { parse } = await import('@vue/compiler-sfc')
    const { compile } = await import('@vue/compiler-dom')
    const vue = await import('vue')
    const { renderToString } = await import('@vue/server-renderer')
    const ui = await import('../../src/utils/antmedUi')

    const raw = readFileSync(path.join(srcDir, 'pages/AntmedRevenuePage.vue'), 'utf8')
    const { descriptor } = parse(raw, { filename: 'AntmedRevenuePage.vue' })
    // mode:'function' → thân hàm tham chiếu 1 đối số `Vue` (runtime helpers), KHÔNG import/ESM →
    // tránh data:URL không resolve bare specifier. Source là <template> repo của chính ta (KHÔNG
    // untrusted input) — chỉ runtime template compilation chuẩn của Vue.
    const { code } = compile(descriptor.template.content, {
      mode: 'function',
      hoistStatic: false,
      prefixIdentifiers: true,
    })
    // code = "const _Vue = Vue\n...\nreturn function render(_ctx,_cache){...}". Đối số `Vue` =
    // runtime helpers. KHÔNG nội suy untrusted (chuỗi cố định từ compiler trên template repo).
    // eslint-disable-next-line no-new-func
    const renderFn = new Function('Vue', code)(vue)

    const i18n = (s) => s
    const comp = {
      components: {
        Badge: { props: ['label'], render() { return vue.h('span', {}, this.label) } },
        Button: {
          props: ['label'],
          emits: ['click'],
          render() { return vue.h('button', {}, this.label) },
        },
        RouterLink: { render() { return vue.h('a', {}, this.$slots.default?.()) } },
        LoadingIndicator: { render() { return vue.h('span', {}, '...') } },
      },
      setup() {
        // State y hệt script setup expose (đọc thẳng resourceData — KHÔNG aggregate).
        const revenue = { data: resourceData, loading, error, reload() {} }
        const months = vue.computed(() => revenue.data?.months || [])
        const groups = vue.computed(() => revenue.data?.groups || [])
        const grandTotal = vue.computed(() => revenue.data?.grand_total ?? 0)
        const columnMax = vue.computed(() =>
          ui.stackColumnMax(ui.stackColumnTotals(groups.value, months.value.length)),
        )
        // Card NV×BV (M02-10) cùng template — MIRROR loading/error flag của group card + cấp data
        // tối thiểu (1 NV × 1 BV) để khi không loading/error thì card heat render NHÁNH DATA (KHÔNG
        // empty-hint 'Chưa có dữ liệu doanh thu' lẫn vào assertion group card). Card heat NV×BV có
        // test riêng (antmedRevenueByRepHospital.test.js) — ở đây chỉ assert card revenue_by_group.
        const repHosp = {
          data: {
            rows: [{ deal_owner: 'x@y.z', full_name: '_RH', cells: [{ hospital: 'H', hospital_label: 'H', value: 1_000_000, heat: 'h5c' }], total: 1_000_000 }],
            hospitals: [{ key: 'H', label: 'H' }],
            max_cell: 1_000_000,
            grand_total: 1_000_000,
          },
          loading,
          error,
          reload() {},
        }
        const repHospRows = vue.computed(() => repHosp.data?.rows || [])
        const repHospHospitals = vue.computed(() => repHosp.data?.hospitals || [])
        const repHospGrand = vue.computed(() => repHosp.data?.grand_total ?? 0)
        return {
          __: i18n,
          revenue,
          months,
          groups,
          grandTotal,
          formatVnMoney: ui.formatVnMoney,
          segmentHeight: (v) => ui.stackSegmentHeightPct(v, columnMax.value),
          barClass: ui.revenueGroupBarClass,
          swatchClass: ui.revenueGroupSwatchClass,
          repHosp,
          repHospRows,
          repHospHospitals,
          repHospGrand,
          heatCellClass: ui.heatCellClass,
          heatLegend: ui.HEAT_LEGEND,
          formatTrieu: ui.formatTrieu,
        }
      },
      render: renderFn,
    }
    const app = vue.createSSRApp(comp)
    app.config.warnHandler = () => {}
    return await renderToString(app)
  }

  it('render data: 12 cột bar + legend 5 nhóm + nhãn widget + breadcrumb', async () => {
    const data = {
      months: ['T7', 'T8', 'T9', 'T10', 'T11', 'T12', 'T1', 'T2', 'T3', 'T4', 'T5', 'T6'],
      groups: [
        { classification: 'Loại A', label: 'Loại A', monthly: [20e6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8e6], total: 28e6 },
        { classification: 'Loại B', label: 'Loại B', monthly: [20e6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], total: 20e6 },
        { classification: 'Loại C', label: 'Loại C', monthly: [0, 0, 0, 0, 0, 0, 0, 18e6, 0, 0, 0, 0], total: 18e6 },
        { classification: 'Loại D', label: 'Loại D', monthly: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], total: 0 },
        { classification: 'Khác', label: 'Khác', monthly: [13e6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], total: 13e6 },
      ],
      grand_total: 79e6,
      currency: 'VND',
    }
    const html = await renderTemplate(data)
    expect(html).toContain('Doanh thu theo Nhóm vật tư')
    expect(html).toContain('Trang chủ')
    // 12 nhãn tháng trục X render đủ (đếm số <span class chứa nhãn tháng).
    for (const m of data.months) expect(html).toContain('>' + m + '<')
    // legend 5 nhóm render đủ.
    for (const g of data.groups) expect(html).toContain(g.label)
    // tổng 12 tháng format VND (79 tr) render.
    expect(html).toContain('79 tr')
  })

  it('render empty: months 12 + groups 5 nhưng grand_total 0 → hint chưa có dữ liệu', async () => {
    const empty = {
      months: ['T7', 'T8', 'T9', 'T10', 'T11', 'T12', 'T1', 'T2', 'T3', 'T4', 'T5', 'T6'],
      groups: ['Loại A', 'Loại B', 'Loại C', 'Loại D', 'Khác'].map((c) => ({
        classification: c,
        label: c,
        monthly: new Array(12).fill(0),
        total: 0,
      })),
      grand_total: 0,
      currency: 'VND',
    }
    const html = await renderTemplate(empty)
    expect(html).toContain('Doanh thu theo Nhóm vật tư')
    expect(html).toContain('Chưa có dữ liệu doanh thu')
    // groups vẫn render đủ 5 legend (KHÔNG ẩn khi 0).
    for (const c of ['Loại A', 'Loại B', 'Loại C', 'Loại D', 'Khác']) {
      expect(html).toContain(c)
    }
  })

  it('render loading branch → "Đang tải…" (KHÔNG bịa số)', async () => {
    const html = await renderTemplate(null, { loading: true })
    expect(html).toContain('Đang tải…')
    expect(html).not.toContain('Chưa có dữ liệu')
  })

  it('render error branch → "Lỗi tải doanh thu" + nút "Thử lại"', async () => {
    const html = await renderTemplate(null, { error: { messages: ['x'] } })
    expect(html).toContain('Lỗi tải doanh thu')
    expect(html).toContain('Thử lại')
  })
})
