import { readFileSync } from 'fs'
import path from 'path'
import {
  HEAT_CELL_COLORS,
  HEAT_LEGEND,
  heatCellClass,
  formatTrieu,
} from '../../src/utils/antmedUi'

// M02-10 — widget heat "Doanh thu theo NV Kinh doanh × Bệnh viện" (mockup A3, Dashboard CEO,
// màn /antmed/revenue). Idiom test (= antmedRevenueByGroup.test.js): content-assert nguồn
// (data/antmed.js, AntmedRevenuePage.vue) + behavior-assert helper THUẦN (antmedUi.js không import
// frappe-ui → import trực tiếp). data/antmed.js + .vue KÉO frappe-ui nên vitest KHÔNG mount trực
// tiếp → assert chuỗi + SSR render-verify harness compile SFC thật (cuối file).

const srcDir = path.resolve(__dirname, '../../src')
const dataSrc = readFileSync(path.join(srcDir, 'data/antmed.js'), 'utf8')
const uiSrc = readFileSync(path.join(srcDir, 'utils/antmedUi.js'), 'utf8')
const pageSrc = readFileSync(path.join(srcDir, 'pages/AntmedRevenuePage.vue'), 'utf8')

// ── (a) data layer — getRevenueByRepHospital url + method GET (naming contract) ────────────────
describe('M02-10 data layer — getRevenueByRepHospital url + method GET', () => {
  it('export function getRevenueByRepHospital', () => {
    expect(dataSrc).toMatch(/export function getRevenueByRepHospital/)
  })

  it('url == antmed_crm.api.antmed.sales_team.revenue_by_rep_hospital (KHÔNG prefix sai)', () => {
    expect(dataSrc).toMatch(/antmed_crm\.api\.antmed\.sales_team\.revenue_by_rep_hospital/)
    expect(dataSrc).not.toMatch(/['"]crm\.api\.antmed\.sales_team\.revenue_by_rep_hospital/)
  })

  it("resource có method === 'GET' (chống defect POST→403)", () => {
    const block = dataSrc.slice(dataSrc.indexOf('export function getRevenueByRepHospital'))
    expect(block).toMatch(/method:\s*'GET'/)
  })

  it('dùng createResource (dict THƯỜNG), KHÔNG createListResource', () => {
    expect(dataSrc).toMatch(/import\s*\{\s*createResource\s*\}\s*from\s*'frappe-ui'/)
    expect(dataSrc).not.toMatch(/import[^\n]*createListResource/)
  })
})

// ── (b) Page đọc r.data.rows/hospitals — KHÔNG .data.data (dict THƯỜNG) ────────────────────────
describe('M02-10 AntmedRevenuePage — đọc r.data.rows/hospitals KHÔNG .data.data', () => {
  it('import getRevenueByRepHospital từ @/data/antmed', () => {
    expect(pageSrc).toMatch(/getRevenueByRepHospital/)
    expect(pageSrc).toMatch(/from '@\/data\/antmed'/)
  })

  it('đọc repHosp.data?.rows / hospitals / grand_total TRỰC TIẾP', () => {
    expect(pageSrc).toMatch(/repHosp\.data\?\.rows/)
    expect(pageSrc).toMatch(/repHosp\.data\?\.hospitals/)
    expect(pageSrc).toMatch(/repHosp\.data\?\.grand_total/)
  })

  it('KHÔNG đọc .data.data (idiom list bọc, KHÔNG phải dict THƯỜNG)', () => {
    expect(pageSrc).not.toMatch(/repHosp\.data\?\.data/)
  })

  it('fetch auto:true (resource ĐỘC LẬP với revenue_by_group)', () => {
    expect(pageSrc).toMatch(/getRevenueByRepHospital\(\{[\s\S]*?auto:\s*true/)
  })
})

// ── (c) Page render card NV×BV — thead BV + 'Tổng (tr)', hàng full_name, cell null→'—' ─────────
describe('M02-10 AntmedRevenuePage — render card NV×BV (thead/hàng/cell)', () => {
  it("tiêu đề card 'Doanh thu theo NV Kinh doanh × Bệnh viện'", () => {
    expect(pageSrc).toMatch(/Doanh thu theo NV Kinh doanh × Bệnh viện/)
  })

  it("cột cuối thead = 'Tổng (tr)' + cột NV", () => {
    expect(pageSrc).toMatch(/Tổng \(tr\)/)
    expect(pageSrc).toMatch(/__\('NV'\)/)
  })

  it('hàng = NV full_name (KHÔNG email), v-for repHospRows', () => {
    expect(pageSrc).toMatch(/v-for="row in repHospRows"/)
    expect(pageSrc).toMatch(/row\.full_name/)
    // KHÔNG render thô deal_owner (email) trong cell hiển thị.
    expect(pageSrc).not.toMatch(/{{\s*row\.deal_owner\s*}}/)
  })

  it("cột BV từ hospitals; cell null → '—' (KHÔNG vỡ); value đơn vị triệu (mockup 'Tổng (tr)')", () => {
    expect(pageSrc).toMatch(/v-for="h in repHospHospitals"/)
    // mockup A3: số trong cell tính theo TRIỆU (formatTrieu) — cell rỗng → '—'.
    expect(pageSrc).toMatch(/cell \? formatTrieu\(cell\.value\) : '—'/)
  })

  it('cột Tổng mỗi NV in đậm (<b>) = row.total (triệu)', () => {
    expect(pageSrc).toMatch(/<b>\{\{ formatTrieu\(row\.total\) \}\}<\/b>/)
  })
})

// ── (d) heatCellClass map 4 mức màu đúng (helper PURE) ─────────────────────────────────────────
describe('M02-10 heatCellClass — map 4 mức heat (PURE, KHÔNG hex)', () => {
  it('HEAT_CELL_COLORS đủ 4 KEY khớp BE (h2c/h3c/h4c/h5c)', () => {
    expect(Object.keys(HEAT_CELL_COLORS).sort()).toEqual(['h2c', 'h3c', 'h4c', 'h5c'])
  })

  it('mỗi mức = class token (KHÔNG hex hardcode)', () => {
    for (const v of Object.values(HEAT_CELL_COLORS)) {
      expect(typeof v).toBe('string')
      expect(v).not.toMatch(/#[0-9a-fA-F]{6}/)
    }
    // KHÔNG hex ngay sau định nghĩa map (chống drift hardcode hex).
    expect(uiSrc).not.toMatch(/HEAT_CELL_COLORS[\s\S]{0,300}#[0-9a-fA-F]{6}/)
  })

  it('heatCellClass(level) đỏ tăng dần h2c→h5c; null/lạ → "" (cell rỗng không tô)', () => {
    expect(heatCellClass('h2c')).toBe(HEAT_CELL_COLORS.h2c)
    expect(heatCellClass('h5c')).toBe(HEAT_CELL_COLORS.h5c)
    expect(heatCellClass(null)).toBe('')
    expect(heatCellClass(undefined)).toBe('')
    expect(heatCellClass('khong-ton-tai')).toBe('')
  })

  it('page dùng heatCellClass (KHÔNG tự suy diễn class theo value)', () => {
    expect(pageSrc).toMatch(/heatCellClass\(cell\.heat\)/)
  })
})

// ── formatTrieu — render giá trị heat theo TRIỆU (PURE, mockup 'Tổng (tr)') ────────────────────
describe('formatTrieu — đơn vị triệu (PURE)', () => {
  it('value/1e6 làm tròn + phân tách VI; 0/null/undefined → "—"', () => {
    expect(formatTrieu(2_140_000_000)).toBe('2.140')
    expect(formatTrieu(680_000_000)).toBe('680')
    expect(formatTrieu(0)).toBe('—')
    expect(formatTrieu(null)).toBe('—')
    expect(formatTrieu(undefined)).toBe('—')
    expect(formatTrieu('')).toBe('—')
  })
})

// ── (e) legend 4 mức render (HEAT_LEGEND SSoT) ─────────────────────────────────────────────────
describe('M02-10 legend 4 mức heat (HEAT_LEGEND SSoT)', () => {
  it('HEAT_LEGEND đúng 4 mục thứ tự Thấp→TB→Cao→Rất cao', () => {
    expect(HEAT_LEGEND.map((l) => l.label)).toEqual(['Thấp', 'TB', 'Cao', 'Rất cao'])
    expect(HEAT_LEGEND.map((l) => l.key)).toEqual(['h2c', 'h3c', 'h4c', 'h5c'])
  })

  it('mỗi mục legend có swatch class token (KHÔNG hex)', () => {
    for (const l of HEAT_LEGEND) {
      expect(typeof l.swatch).toBe('string')
      expect(l.swatch).not.toMatch(/#[0-9a-fA-F]{6}/)
    }
  })

  it('page render legend qua HEAT_LEGEND (v-for heatLegend)', () => {
    expect(pageSrc).toMatch(/v-for="lv in heatLegend"/)
    expect(pageSrc).toMatch(/heatLegend = HEAT_LEGEND/)
  })
})

// ── (f) loading/empty/error tri-branch ────────────────────────────────────────────────────────
describe('M02-10 AntmedRevenuePage — tri-branch loading/empty/error', () => {
  it("loading → 'Đang tải…'", () => {
    expect(pageSrc).toMatch(/v-if="repHosp\.loading"/)
  })

  it("error → 'Lỗi tải doanh thu' + 'Thử lại' (reload)", () => {
    expect(pageSrc).toMatch(/v-else-if="repHosp\.error"/)
    expect(pageSrc).toMatch(/repHosp\.reload\(\)/)
  })

  it("empty → 'Chưa có dữ liệu doanh thu' khi rows rỗng", () => {
    expect(pageSrc).toMatch(/v-else-if="!repHospRows\.length"/)
    expect(pageSrc).toMatch(/Chưa có dữ liệu doanh thu/)
  })

  it('thứ tự nhánh loading → error → empty → data (v-else cuối)', () => {
    const iL = pageSrc.indexOf('v-if="repHosp.loading"')
    const iE = pageSrc.indexOf('v-else-if="repHosp.error"')
    const iEmpty = pageSrc.indexOf('v-else-if="!repHospRows.length"')
    expect(iL).toBeGreaterThan(-1)
    expect(iE).toBeGreaterThan(iL)
    expect(iEmpty).toBeGreaterThan(iE)
  })
})

// ── (g) no-mock / no-aggregate guard (FE KHÔNG reduce/sort heat data) ──────────────────────────
describe('M02-10 AntmedRevenuePage — KHÔNG mock/aggregate/sort dữ liệu heat', () => {
  it('KHÔNG hardcode số mock / import antmedMock', () => {
    expect(pageSrc).not.toMatch(/antmedMock|mockData/)
  })

  it('script KHÔNG reduce/sort dữ liệu (BE đã gộp + sort rows)', () => {
    const script = pageSrc.slice(pageSrc.indexOf('<script'))
    expect(script).not.toMatch(/\.reduce\(/)
    expect(script).not.toMatch(/\.sort\(/)
  })

  it('đọc thẳng row.cells[ci] + row.total (KHÔNG tự cộng cell)', () => {
    expect(pageSrc).toMatch(/v-for="\(cell, ci\) in row\.cells"/)
    expect(pageSrc).toMatch(/row\.total/)
  })
})

// ── (h) regression — card revenue_by_group + KPI revenue cũ vẫn render ─────────────────────────
describe('M02-10 regression — card revenue_by_group cũ KHÔNG bị xoá', () => {
  it("GIỮ card 'Doanh thu theo Nhóm vật tư' (revenue_by_group)", () => {
    expect(pageSrc).toMatch(/Doanh thu theo Nhóm vật tư/)
    expect(pageSrc).toMatch(/getRevenueByGroup/)
    expect(dataSrc).toMatch(/antmed_crm\.api\.antmed\.contract\.revenue_by_group/)
  })

  it('GIỮ helper stack cũ (stackSegmentHeightPct/columnMax) + breadcrumb', () => {
    expect(pageSrc).toMatch(/stackSegmentHeightPct/)
    expect(pageSrc).toMatch(/stackColumnMax/)
    expect(pageSrc).toMatch(/__\('Trang chủ'\)/)
  })
})

// ── (RENDER THẬT) SSR render-verify harness — compile TEMPLATE thật + renderToString ──────────
// Bằng chứng render THẬT (KHÔNG chỉ content-assert): compile <template> AntmedRevenuePage.vue qua
// compiler-dom rồi render bằng component có setup() cung cấp ĐÚNG state script setup expose + helper
// antmedUi THẬT. Nguồn = <template> repo (KHÔNG untrusted) — chỉ runtime template compilation chuẩn.
describe('M02-10 SSR render-verify — card NV×BV render HTML thật (heat + — + Tổng đậm)', () => {
  async function renderTemplate(repData, { loading = false, error = null } = {}) {
    const { parse } = await import('@vue/compiler-sfc')
    const { compile } = await import('@vue/compiler-dom')
    const vue = await import('vue')
    const { renderToString } = await import('@vue/server-renderer')
    const ui = await import('../../src/utils/antmedUi')

    const raw = readFileSync(path.join(srcDir, 'pages/AntmedRevenuePage.vue'), 'utf8')
    const { descriptor } = parse(raw, { filename: 'AntmedRevenuePage.vue' })
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
        // Card revenue_by_group (cũ) — grand_total>0 để KHÔNG render empty-hint của card cũ
        // ('Chưa có dữ liệu doanh thu trong 12 tháng…') gây nhiễu assert card NV×BV (mới).
        const revenue = { data: { months: [], groups: [], grand_total: 1 }, loading: false, error: null, reload() {} }
        const months = vue.computed(() => revenue.data?.months || [])
        const groups = vue.computed(() => revenue.data?.groups || [])
        const grandTotal = vue.computed(() => revenue.data?.grand_total ?? 0)
        const columnMax = vue.computed(() =>
          ui.stackColumnMax(ui.stackColumnTotals(groups.value, months.value.length)),
        )
        // Card NV×BV (mới) — state y hệt script setup expose (đọc thẳng repData, KHÔNG aggregate).
        const repHosp = { data: repData, loading, error, reload() {} }
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

  const liveData = {
    rows: [
      {
        deal_owner: 'an@example.com',
        full_name: 'Nguyễn Văn An',
        cells: [
          { hospital: 'BM', hospital_label: 'Bạch Mai', value: 2_140_000_000, heat: 'h5c' },
          { hospital: 'VD', hospital_label: 'Việt Đức', value: 680_000_000, heat: 'h3c' },
          null,
        ],
        total: 2_820_000_000,
      },
      {
        deal_owner: 'lan@example.com',
        full_name: 'Lê Lan',
        cells: [
          null,
          { hospital: 'VD', hospital_label: 'Việt Đức', value: 410_000_000, heat: 'h2c' },
          { hospital: 'K', hospital_label: 'BV K', value: 980_000_000, heat: 'h4c' },
        ],
        total: 1_390_000_000,
      },
    ],
    hospitals: [
      { key: 'BM', label: 'Bạch Mai' },
      { key: 'VD', label: 'Việt Đức' },
      { key: 'K', label: 'BV K' },
    ],
    max_cell: 2_140_000_000,
    grand_total: 4_210_000_000,
  }

  it('render data: tiêu đề + cột BV + Tổng (tr) + hàng full_name + heat class + cell rỗng —', async () => {
    const html = await renderTemplate(liveData)
    expect(html).toContain('Doanh thu theo NV Kinh doanh × Bệnh viện')
    // header cột BV + cột Tổng.
    expect(html).toContain('Bạch Mai')
    expect(html).toContain('Việt Đức')
    expect(html).toContain('BV K')
    expect(html).toContain('Tổng (tr)')
    // hàng = full_name (KHÔNG email).
    expect(html).toContain('Nguyễn Văn An')
    expect(html).toContain('Lê Lan')
    expect(html).not.toContain('an@example.com')
    // heat class render trên cell (max 2.140 triệu → h5c = bg-red-500).
    expect(html).toContain('bg-red-500')
    // cell rỗng (null) render '—'.
    expect(html).toContain('—')
    // cell value đơn vị TRIỆU (mockup 'Tổng (tr)'): 2.140.000.000 → '2.140'.
    expect(html).toContain('2.140')
    // cột Tổng đậm — <b> bao tổng NV theo triệu (2.820.000.000 → '2.820').
    expect(html).toMatch(/<b>[^<]*2\.820[^<]*<\/b>/)
    // legend 4 mức.
    for (const lbl of ['Thấp', 'TB', 'Cao', 'Rất cao']) expect(html).toContain(lbl)
  })

  it('render empty: rows [] → "Chưa có dữ liệu doanh thu", KHÔNG vỡ bảng', async () => {
    const html = await renderTemplate({ rows: [], hospitals: [], max_cell: 0, grand_total: 0 })
    expect(html).toContain('Doanh thu theo NV Kinh doanh × Bệnh viện')
    expect(html).toContain('Chưa có dữ liệu doanh thu')
  })

  it('render loading → "Đang tải…" (KHÔNG bịa số)', async () => {
    const html = await renderTemplate(null, { loading: true })
    expect(html).toContain('Đang tải…')
    expect(html).not.toContain('Chưa có dữ liệu doanh thu')
  })

  it('render error → "Lỗi tải doanh thu" + "Thử lại"', async () => {
    const html = await renderTemplate(null, { error: { messages: ['x'] } })
    expect(html).toContain('Lỗi tải doanh thu')
    expect(html).toContain('Thử lại')
  })
})
