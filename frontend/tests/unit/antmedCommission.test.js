import { readFileSync } from 'fs'
import path from 'path'
import { formatVnMoney } from '../../src/utils/antmedUi'

// M09-1 — widget "Tổng hoa hồng kỳ" + "Quy tắc kỳ" (Kế toán, mockup F2, màn /antmed/finance/commission).
// Idiom test (= antmedRevenueByGroup.test.js): content-assert nguồn (data/antmed.js, AntmedCommissionPage.vue,
// router.js) + SSR render-verify harness compile <template> THẬT (cuối file). data/antmed.js + .vue kéo
// frappe-ui nên vitest KHÔNG mount trực tiếp → assert chuỗi + SSR compile template.

const srcDir = path.resolve(__dirname, '../../src')
const dataSrc = readFileSync(path.join(srcDir, 'data/antmed.js'), 'utf8')
const pageSrc = readFileSync(path.join(srcDir, 'pages/AntmedCommissionPage.vue'), 'utf8')
const routerSrc = readFileSync(path.join(srcDir, 'router.js'), 'utf8')

// Negative content-asserts (KHÔNG .data.data / KHÔNG 'Sắp có'...) phải chạy trên CODE thật, KHÔNG dính
// comment giải thích (vd "// KHÔNG .data.data"). Strip comment JS (// …) + HTML (<!-- … -->) trước assert.
function stripComments(src) {
  return src
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/^\s*\/\/.*$/gm, '')
    .replace(/([^:])\/\/.*$/gm, '$1')
}
const pageCode = stripComments(pageSrc)
const routerCode = stripComments(routerSrc)

// ── Data layer — getCommissionSummary url + method GET (naming contract + GET-only) ───────────
describe('M09-1 data layer — getCommissionSummary url commission_summary + method GET', () => {
  it('export function getCommissionSummary', () => {
    expect(dataSrc).toMatch(/export function getCommissionSummary/)
  })

  it('url == antmed_crm.api.antmed.finance.commission_summary (naming contract)', () => {
    expect(dataSrc).toMatch(/antmed_crm\.api\.antmed\.finance\.commission_summary/)
    // KHÔNG prefix sai crm.api.* (thiếu antmed_crm) cho commission_summary.
    expect(dataSrc).not.toMatch(/['"]crm\.api\.antmed\.finance\.commission_summary/)
  })

  it("resource có method === 'GET' (chống defect POST→403)", () => {
    const block = dataSrc.slice(dataSrc.indexOf('export function getCommissionSummary'))
    expect(block).toMatch(/method:\s*'GET'/)
  })

  it('dùng createResource (dict THƯỜNG), KHÔNG createListResource', () => {
    expect(dataSrc).toMatch(/import\s*\{\s*createResource\s*\}\s*from\s*'frappe-ui'/)
    expect(dataSrc).not.toMatch(/import[^\n]*createListResource/)
  })
})

// ── Page reads r.data.<key> — KHÔNG .data.data (dict THƯỜNG) ──────────────────────────────────
describe('M09-1 AntmedCommissionPage — đọc r.data.total_commission KHÔNG .data.data', () => {
  it('import getCommissionSummary từ @/data/antmed', () => {
    expect(pageSrc).toMatch(/getCommissionSummary/)
    expect(pageSrc).toMatch(/from '@\/data\/antmed'/)
  })

  it('đọc commission.data?.total_commission / rep_count / group_count / rules / period_label TRỰC TIẾP', () => {
    expect(pageSrc).toMatch(/\.data\?\.total_commission/)
    expect(pageSrc).toMatch(/\.data\?\.rep_count/)
    expect(pageSrc).toMatch(/\.data\?\.group_count/)
    expect(pageSrc).toMatch(/\.data\?\.rules/)
    expect(pageSrc).toMatch(/\.data\?\.period_label/)
  })

  it('KHÔNG đọc .data.data (idiom list bọc, KHÔNG phải dict THƯỜNG) — trong CODE', () => {
    expect(pageCode).not.toMatch(/\.data\?\.data/)
    expect(pageCode).not.toMatch(/\.data\.data/)
  })

  it('fetch auto:true', () => {
    expect(pageSrc).toMatch(/getCommissionSummary\(\{[\s\S]*?auto:\s*true/)
  })
})

// ── Page render — 2 card F2 (Tổng hoa hồng kỳ + Quy tắc kỳ) ───────────────────────────────────
describe('M09-1 AntmedCommissionPage — render 2 card F2 + sub rep/nhóm + v-for rules', () => {
  it("card trái 'Tổng hoa hồng kỳ' + formatVnMoney + ' ₫'", () => {
    expect(pageSrc).toMatch(/Tổng hoa hồng kỳ/)
    expect(pageSrc).toMatch(/formatVnMoney/)
    expect(pageSrc).toMatch(/₫/)
  })

  it("dòng phụ '<rep_count> NV · <group_count> nhóm vật tư' (bind data THẬT)", () => {
    expect(pageSrc).toMatch(/NV/)
    expect(pageSrc).toMatch(/nhóm vật tư/)
  })

  it("card phải 'Quy tắc kỳ' bind period_label", () => {
    expect(pageSrc).toMatch(/Quy tắc kỳ/)
  })

  it('v-for rules (label · rate_pct%) — KHÔNG hardcode JSX', () => {
    expect(pageSrc).toMatch(/v-for="[^"]*in rules"/)
    expect(pageSrc).toMatch(/rate_pct/)
    expect(pageSrc).toMatch(/\.label/)
  })

  it('format tiền qua formatVnMoney (KHÔNG tự format)', () => {
    expect(pageSrc).toMatch(/formatVnMoney/)
  })
})

// ── Tri-branch loading / error / data ─────────────────────────────────────────────────────────
describe('M09-1 AntmedCommissionPage — tri-branch loading/error/data', () => {
  it("loading → 'Đang tải…'", () => {
    expect(pageSrc).toMatch(/loading/)
    expect(pageSrc).toMatch(/Đang tải…/)
  })

  it("error → 'Lỗi tải hoa hồng'", () => {
    expect(pageSrc).toMatch(/Lỗi tải hoa hồng/)
  })

  it('v-else render data (data branch sau loading/error)', () => {
    expect(pageSrc).toMatch(/\.loading/)
    expect(pageSrc).toMatch(/\.error/)
    expect(pageSrc).toMatch(/v-else/)
  })
})

// ── No mock / no aggregate guard (FE chỉ trình bày) ──────────────────────────────────────────
describe('M09-1 AntmedCommissionPage — KHÔNG mock/aggregate số liệu', () => {
  it('KHÔNG hardcode số mock / import antmedMock', () => {
    expect(pageCode).not.toMatch(/antmedMock|mockData/)
  })

  it("KHÔNG 'Sắp có' cho giá trị số (0 → '0 ₫' số thật) — trong CODE render", () => {
    expect(pageCode).not.toMatch(/Sắp có/)
  })

  it('page KHÔNG reduce/sort dữ liệu (BE đã gộp)', () => {
    const script = pageSrc.slice(pageSrc.indexOf('<script'))
    expect(script).not.toMatch(/\.reduce\(/)
    expect(script).not.toMatch(/\.sort\(/)
  })

  it('KHÔNG axios / TanStack trong page', () => {
    expect(pageSrc).not.toMatch(/axios|@tanstack/)
  })
})

// ── Router — route real-data /antmed/finance/commission + stub GIỮ /finance/commission ────────
describe('M09-1 router — AntmedCommissionPage /antmed/finance/commission + stub regression', () => {
  it("route name 'AntmedCommissionPage' tại path '/antmed/finance/commission'", () => {
    expect(routerSrc).toMatch(/name:\s*'AntmedCommissionPage'/)
    expect(routerSrc).toMatch(/path:\s*'\/antmed\/finance\/commission'/)
  })

  it("route name 'AntmedCommissionPage' === 1 (unique, trong CODE — bỏ comment)", () => {
    const m = routerCode.match(/name:\s*'AntmedCommissionPage'/g) || []
    expect(m).toHaveLength(1)
  })

  it('meta antmedShell:true + role:finance cho route real-data', () => {
    const idx = routerSrc.indexOf("name: 'AntmedCommissionPage'")
    const block = routerSrc.slice(Math.max(0, idx - 300), idx + 300)
    expect(block).toMatch(/antmedShell:\s*true/)
    expect(block).toMatch(/role:\s*'finance'/)
  })

  it('lazy import page real-data (route trỏ AntmedCommissionPage.vue, KHÔNG antmedStub)', () => {
    expect(routerSrc).toMatch(/import\('@\/pages\/AntmedCommissionPage\.vue'\)/)
    const idx = routerSrc.indexOf("name: 'AntmedCommissionPage'")
    const block = routerSrc.slice(idx, idx + 300)
    expect(block).not.toMatch(/antmedStub/)
  })

  // Phase 2: mock prototype /finance/commission ĐÃ GỠ — chỉ còn /antmed/finance/commission thật.
})

// ── SSR render-verify harness — compile TEMPLATE thật + renderToString (data + 0 + loading/error) ─
// MIRROR <script setup> AntmedCommissionPage.vue: expose totalCommission/totalRevenue/repCount/
// groupCount/periodLabel/rules (đọc thẳng resourceData, KHÔNG aggregate) + formatVnMoney THẬT.
describe('M09-1 SSR render-verify — AntmedCommissionPage render HTML thật', () => {
  async function renderTemplate(resourceData, { loading = false, error = null } = {}) {
    const { parse } = await import('@vue/compiler-sfc')
    const { compile } = await import('@vue/compiler-dom')
    const vue = await import('vue')
    const { renderToString } = await import('@vue/server-renderer')
    const ui = await import('../../src/utils/antmedUi')

    const raw = readFileSync(path.join(srcDir, 'pages/AntmedCommissionPage.vue'), 'utf8')
    const { descriptor } = parse(raw, { filename: 'AntmedCommissionPage.vue' })
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
        Button: { props: ['label'], emits: ['click'], render() { return vue.h('button', {}, this.label) } },
        RouterLink: { render() { return vue.h('a', {}, this.$slots.default?.()) } },
        LoadingIndicator: { render() { return vue.h('span', {}, '...') } },
      },
      setup() {
        const commission = { data: resourceData, loading, error, reload() {} }
        const totalCommission = vue.computed(() => commission.data?.total_commission ?? 0)
        const totalRevenue = vue.computed(() => commission.data?.total_revenue ?? 0)
        const repCount = vue.computed(() => commission.data?.rep_count ?? 0)
        const groupCount = vue.computed(() => commission.data?.group_count ?? 0)
        const periodLabel = vue.computed(() => commission.data?.period_label || '')
        const rules = vue.computed(() => commission.data?.rules || [])
        return {
          __: i18n,
          commission,
          totalCommission,
          totalRevenue,
          repCount,
          groupCount,
          periodLabel,
          rules,
          formatVnMoney: ui.formatVnMoney,
        }
      },
      render: renderFn,
    }
    const app = vue.createSSRApp(comp)
    app.config.warnHandler = () => {}
    return await renderToString(app)
  }

  const RULES = [
    { label: 'Chỉ PT', rate_pct: 3.0 },
    { label: 'Dao mổ', rate_pct: 2.0 },
    { label: 'Lưới', rate_pct: 4.0 },
    { label: 'Tiêu hao', rate_pct: 1.5 },
  ]

  it('render data: tổng hoa hồng + sub rep/nhóm + 4 quy tắc + period_label', async () => {
    const data = {
      total_commission: 9_000_000,
      total_revenue: 360_000_000,
      rep_count: 2,
      group_count: 4,
      period_label: 'T6/2026',
      flat_rate_pct: 2.5,
      currency: 'VND',
      rules: RULES,
    }
    const html = await renderTemplate(data)
    expect(html).toContain('Tổng hoa hồng kỳ')
    expect(html).toContain('Quy tắc kỳ')
    expect(html).toContain('T6/2026')
    // tiền format VND + ' ₫' (9.000.000 → '9 tr').
    expect(html).toContain(formatVnMoney(9_000_000))
    expect(html).toContain('₫')
    // dòng phụ rep/nhóm.
    expect(html).toContain('NV')
    expect(html).toContain('nhóm vật tư')
    // 4 quy tắc render từ data THẬT.
    for (const r of RULES) expect(html).toContain(r.label)
  })

  it("render total_commission=0 → '0 ₫' (số thật, KHÔNG 'Sắp có'/'Chưa có dữ liệu số')", async () => {
    const data = {
      total_commission: 0,
      total_revenue: 0,
      rep_count: 0,
      group_count: 4,
      period_label: 'T6/2026',
      flat_rate_pct: 2.5,
      currency: 'VND',
      rules: RULES,
    }
    const html = await renderTemplate(data)
    expect(html).toContain('0 ₫')
    // Vue SSR giữ HTML comment trong output → strip comment trước assert "no placeholder value text".
    const visible = html.replace(/<!--[\s\S]*?-->/g, '')
    expect(visible).not.toContain('Sắp có')
    expect(visible).not.toContain('Chưa có dữ liệu')
    // rules vẫn render đủ 4 (KHÔNG ẩn khi 0).
    for (const r of RULES) expect(html).toContain(r.label)
  })

  it("render loading → 'Đang tải…' (KHÔNG bịa số)", async () => {
    const html = await renderTemplate(null, { loading: true })
    expect(html).toContain('Đang tải…')
  })

  it("render error → 'Lỗi tải hoa hồng'", async () => {
    const html = await renderTemplate(null, { error: { messages: ['x'] } })
    expect(html).toContain('Lỗi tải hoa hồng')
  })
})
