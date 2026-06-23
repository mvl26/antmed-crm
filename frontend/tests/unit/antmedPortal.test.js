import { readFileSync } from 'fs'
import path from 'path'
import {
  formatNotifTime,
  PORTAL_QUICK_ACTIONS,
  PILL_THEME,
  tenderQuotaChipClass,
  tenderQuotaChipLabel,
} from '../../src/utils/antmedUi'

// M07-1 — màn "Portal Bệnh viện — Trang chủ" (mockup G1, id=bv, /antmed/portal).
// Idiom test (= antmedCommission.test.js): pure-util test (formatNotifTime) + content-assert nguồn
// (data/antmed.js, AntmedPortalHome.vue, router.js, antmedNav.js) + SSR render-verify harness compile
// <template> THẬT (cuối file) — chứng minh RENDER thật, KHÔNG chỉ structural (LL-FE-14).

const srcDir = path.resolve(__dirname, '../../src')
const dataSrc = readFileSync(path.join(srcDir, 'data/antmed.js'), 'utf8')
const uiSrc = readFileSync(path.join(srcDir, 'utils/antmedUi.js'), 'utf8')
const pageSrc = readFileSync(
  path.join(srcDir, 'pages/AntmedPortalHome.vue'),
  'utf8',
)
const routerSrc = readFileSync(path.join(srcDir, 'router.js'), 'utf8')
const navSrc = readFileSync(path.join(srcDir, 'data/antmedNav.js'), 'utf8')

// Strip comment (JS // + HTML <!-- -->) trước negative content-assert (tránh false-positive do
// chuỗi nằm trong comment giải thích).
function stripComments(src) {
  return src
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/^\s*\/\/.*$/gm, '')
    .replace(/([^:])\/\/.*$/gm, '$1')
}
const pageCode = stripComments(pageSrc)
const routerCode = stripComments(routerSrc)

// ── FE util — formatNotifTime PURE (cùng ngày / hôm qua / dd/mm / null) ───────────────────────
describe('M07-1 util formatNotifTime — relative VI', () => {
  const NOW = new Date('2026-06-18T15:30:00')

  it("cùng ngày → 'hôm nay HH:MM' (zero-pad)", () => {
    expect(formatNotifTime('2026-06-18 09:05:00', NOW)).toBe('hôm nay 09:05')
    expect(formatNotifTime('2026-06-18 23:59:00', NOW)).toBe('hôm nay 23:59')
  })

  it("hôm trước → 'hôm qua'", () => {
    expect(formatNotifTime('2026-06-17 22:00:00', NOW)).toBe('hôm qua')
    // 00:01 hôm qua vẫn 'hôm qua' (so theo ngày lịch, không 24h chênh).
    expect(formatNotifTime('2026-06-17 00:01:00', NOW)).toBe('hôm qua')
  })

  it("xa hơn (>=2 ngày) → 'dd/mm' (zero-pad, KHÔNG năm)", () => {
    expect(formatNotifTime('2026-05-25 10:00:00', NOW)).toBe('25/05')
    expect(formatNotifTime('2026-06-01 08:00:00', NOW)).toBe('01/06')
  })

  it("null/undefined/'' → '—' (KHÔNG NaN)", () => {
    expect(formatNotifTime(null, NOW)).toBe('—')
    expect(formatNotifTime(undefined, NOW)).toBe('—')
    expect(formatNotifTime('', NOW)).toBe('—')
  })

  it("parse-fail → '—' (KHÔNG NaN/Invalid Date)", () => {
    expect(formatNotifTime('không-phải-ngày', NOW)).toBe('—')
    const out = formatNotifTime('2026-06-18 09:05:00', NOW)
    expect(out).not.toMatch(/NaN|Invalid/)
  })

  it('nhận Date object (không chỉ string)', () => {
    expect(formatNotifTime(new Date('2026-06-18T07:08:00'), NOW)).toBe(
      'hôm nay 07:08',
    )
  })
})

// ── 3 quick-action SSoT (nhãn G1 chính xác) ──────────────────────────────────────────────────
describe('M07-1 PORTAL_QUICK_ACTIONS — 3 card tĩnh khớp mockup G1', () => {
  it('đúng 3 card', () => {
    expect(PORTAL_QUICK_ACTIONS).toHaveLength(3)
  })

  it('nhãn + icon + dòng phụ khớp G1', () => {
    const [a, b, c] = PORTAL_QUICK_ACTIONS
    expect(a.icon).toBe('🩺')
    expect(a.title).toBe('Gọi vật tư cho ca mổ')
    expect(a.sub).toBe('Trong danh mục trúng thầu')
    expect(b.icon).toBe('🧰')
    expect(b.title).toBe('Mượn bộ dụng cụ')
    expect(b.sub).toBe('Đặt trước ca mổ')
    expect(c.icon).toBe('📄')
    expect(c.title).toBe('Tra cứu chứng từ')
    expect(c.sub).toBe('Hóa đơn, CO/CQ, phiếu giao')
  })

  it('mỗi card có đích điều hướng (nav-only, KHÔNG dead-link)', () => {
    for (const qa of PORTAL_QUICK_ACTIONS) {
      expect(typeof qa.to).toBe('string')
      expect(qa.to).toMatch(/^\/antmed\//)
    }
  })
})

// ── Data layer — getPortalNotifications url + method GET ──────────────────────────────────────
describe('M07-1 data layer — getPortalNotifications url portal_notifications + GET', () => {
  it('export function getPortalNotifications', () => {
    expect(dataSrc).toMatch(/export function getPortalNotifications/)
  })

  it('url == antmed_crm.api.antmed.customer.portal_notifications (naming contract)', () => {
    expect(dataSrc).toMatch(
      /antmed_crm\.api\.antmed\.customer\.portal_notifications/,
    )
    expect(dataSrc).not.toMatch(
      /['"]crm\.api\.antmed\.customer\.portal_notifications/,
    )
  })

  it("resource có method === 'GET' + truyền params {hospital}", () => {
    const block = dataSrc.slice(
      dataSrc.indexOf('export function getPortalNotifications'),
    )
    expect(block).toMatch(/method:\s*'GET'/)
    expect(block).toMatch(/params/)
  })

  it('dùng createResource (KHÔNG import createListResource — dict bọc qua createResource)', () => {
    expect(dataSrc).toMatch(
      /import\s*\{\s*createResource\s*\}\s*from\s*'frappe-ui'/,
    )
    // createListResource chỉ được nhắc trong COMMENT (KHÔNG import/dùng thật) → assert không import.
    expect(dataSrc).not.toMatch(/import[^\n]*createListResource/)
  })
})

// ── Page — đọc r.data.data + r.data.hospital_name; tri-branch; KHÔNG aggregate ────────────────
describe('M07-1 AntmedPortalHome — binding + tri-branch', () => {
  it('import getPortalNotifications + formatNotifTime + PORTAL_QUICK_ACTIONS', () => {
    expect(pageSrc).toMatch(/getPortalNotifications/)
    expect(pageSrc).toMatch(/formatNotifTime/)
    expect(pageSrc).toMatch(/PORTAL_QUICK_ACTIONS/)
    expect(pageSrc).toMatch(/from '@\/data\/antmed'/)
    expect(pageSrc).toMatch(/from '@\/utils\/antmedUi'/)
  })

  it('đọc notif.data?.data (mảng sự kiện) + notif.data?.hospital_name TRỰC TIẾP', () => {
    expect(pageSrc).toMatch(/\.data\?\.data/)
    expect(pageSrc).toMatch(/\.data\?\.hospital_name/)
  })

  it('tri-branch loading/error/data (Đang tải… / Lỗi tải thông báo / Chưa có thông báo)', () => {
    expect(pageSrc).toMatch(/Đang tải…/)
    expect(pageSrc).toMatch(/Lỗi tải thông báo/)
    expect(pageSrc).toMatch(/Chưa có thông báo/)
    expect(pageSrc).toMatch(/\.loading/)
    expect(pageSrc).toMatch(/\.error/)
  })

  it('timeline class .tl/.e (mockup G1) render v-for từ data thật', () => {
    expect(pageSrc).toMatch(/antmed-tl/)
    expect(pageSrc).toMatch(/antmed-e/)
    expect(pageSrc).toMatch(/v-for=/)
  })

  it('3 quick-action render v-for từ PORTAL_QUICK_ACTIONS (KHÔNG hardcode JSX rời rạc)', () => {
    expect(pageSrc).toMatch(/v-for="qa in quickActions"/)
  })

  it('page KHÔNG reduce/sort dữ liệu (BE đã gộp + sort)', () => {
    const script = pageSrc.slice(pageSrc.indexOf('<script'))
    expect(script).not.toMatch(/\.reduce\(/)
    expect(script).not.toMatch(/\.sort\(/)
  })

  it('KHÔNG axios / TanStack / mock số liệu trong page', () => {
    expect(pageCode).not.toMatch(/axios|@tanstack/)
    expect(pageCode).not.toMatch(/antmedMock|mockData/)
  })

  it("KHÔNG đọc .data.data.data (chỉ 1 lớp bọc) + KHÔNG 'Sắp có'", () => {
    expect(pageCode).not.toMatch(/\.data\?\.data\?\.data/)
    expect(pageCode).not.toMatch(/Sắp có/)
  })
})

// ── Router — route real-data /antmed/portal name AntmedPortalHome + stub rename ────────────────
describe('M07-1 router — /antmed/portal AntmedPortalHome (real) + stub /portal rename', () => {
  it("route name 'AntmedPortalHome' tại path '/antmed/portal'", () => {
    expect(routerSrc).toMatch(/name:\s*'AntmedPortalHome'/)
    expect(routerSrc).toMatch(/path:\s*'\/antmed\/portal'/)
  })

  it("route name 'AntmedPortalHome' === 1 (unique — vue-router cấm trùng name)", () => {
    const m = routerCode.match(/name:\s*'AntmedPortalHome'/g) || []
    expect(m).toHaveLength(1)
  })

  it('meta antmedShell:true + role:portal cho route real-data', () => {
    const idx = routerSrc.indexOf("name: 'AntmedPortalHome'")
    const block = routerSrc.slice(Math.max(0, idx - 320), idx + 320)
    expect(block).toMatch(/antmedShell:\s*true/)
    expect(block).toMatch(/role:\s*'portal'/)
  })

  it('lazy import page real-data (KHÔNG antmedStub cho route /antmed/portal)', () => {
    expect(routerSrc).toMatch(/import\('@\/pages\/AntmedPortalHome\.vue'\)/)
    const idx = routerSrc.indexOf("name: 'AntmedPortalHome'")
    const block = routerSrc.slice(idx, idx + 320)
    expect(block).not.toMatch(/antmedStub/)
  })

  // Phase 2: mock prototype /portal + /portal/history ĐÃ GỠ — chỉ còn /antmed/portal thật.
})

// ── Nav — entry 'Trang chủ Portal' trỏ /antmed/portal (enabled) ──────────────────────────────
describe('M07-1 nav — portal entry Trang chủ Portal → /antmed/portal', () => {
  it("ROLE_NAV.portal có entry trỏ '/antmed/portal' enabled:true", () => {
    const idx = navSrc.indexOf('portal: [')
    const block = navSrc.slice(idx, idx + 600)
    expect(block).toMatch(/to:\s*'\/antmed\/portal'/)
    expect(block).toMatch(/Trang chủ Portal/)
  })
})

// ── SSR render-verify harness — compile TEMPLATE thật + renderToString ────────────────────────
// MIRROR <script setup> AntmedPortalHome.vue: events (notif.data?.data), hospitalName, quickActions,
// formatNotifTime THẬT. Chứng minh RENDER thật (data + empty + loading + error + thiếu hospital).
describe('M07-1 SSR render-verify — AntmedPortalHome render HTML thật', () => {
  async function renderTemplate(
    resourceData,
    {
      loading = false,
      error = null,
      hospital = '_T-BV',
      catalogData = {
        hospital: '_T-BV',
        hospital_name: 'BV Test',
        contract: null,
        items: [],
      },
      catalogLoading = false,
      catalogError = null,
    } = {},
  ) {
    const { parse } = await import('@vue/compiler-sfc')
    const { compile } = await import('@vue/compiler-dom')
    const vue = await import('vue')
    const { renderToString } = await import('@vue/server-renderer')
    const ui = await import('../../src/utils/antmedUi')

    const raw = readFileSync(
      path.join(srcDir, 'pages/AntmedPortalHome.vue'),
      'utf8',
    )
    const { descriptor } = parse(raw, { filename: 'AntmedPortalHome.vue' })
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
        Badge: {
          props: ['label'],
          render() {
            return vue.h('span', {}, this.label)
          },
        },
        Button: {
          props: ['label'],
          emits: ['click'],
          render() {
            return vue.h('button', {}, this.label)
          },
        },
        RouterLink: {
          props: ['to'],
          render() {
            return vue.h('a', {}, this.$slots.default?.())
          },
        },
        LoadingIndicator: {
          render() {
            return vue.h('span', {}, '...')
          },
        },
      },
      setup() {
        const notif = {
          data: resourceData,
          loading,
          error,
          reload() {},
          fetch() {},
        }
        const catalog = {
          data: catalogData,
          loading: catalogLoading,
          error: catalogError,
          reload() {},
          fetch() {},
        }
        const hospitalRef = vue.computed(() => hospital)
        const quickActions = ui.PORTAL_QUICK_ACTIONS
        const events = vue.computed(() => notif.data?.data || [])
        const hospitalName = vue.computed(() => notif.data?.hospital_name || '')
        const catalogItems = vue.computed(() => catalog.data?.items || [])
        const catalogHospitalName = vue.computed(
          () => catalog.data?.hospital_name || '',
        )
        return {
          __: i18n,
          notif,
          catalog,
          hospital: hospitalRef,
          quickActions,
          events,
          hospitalName,
          catalogItems,
          catalogHospitalName,
          formatNotifTime: ui.formatNotifTime,
          fmtQty: ui.fmtQty,
          tenderQuotaChipClass: ui.tenderQuotaChipClass,
          tenderQuotaChipLabel: ui.tenderQuotaChipLabel,
        }
      },
      render: renderFn,
    }
    const app = vue.createSSRApp(comp)
    app.config.warnHandler = () => {}
    return await renderToString(app)
  }

  const NOW = new Date()
  function todayAt(h, m) {
    const d = new Date(NOW)
    d.setHours(h, m, 0, 0)
    const p = (x) => String(x).padStart(2, '0')
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(h)}:${p(m)}:00`
  }

  it('render 3 quick-action card tĩnh đúng nhãn G1', async () => {
    const html = await renderTemplate({
      data: [],
      hospital: '_T-BV',
      hospital_name: 'BV Test',
    })
    expect(html).toContain('Gọi vật tư cho ca mổ')
    expect(html).toContain('Trong danh mục trúng thầu')
    expect(html).toContain('Mượn bộ dụng cụ')
    expect(html).toContain('Đặt trước ca mổ')
    expect(html).toContain('Tra cứu chứng từ')
    expect(html).toContain('Hóa đơn, CO/CQ, phiếu giao')
    expect(html).toContain('📰 Thông báo gần đây')
  })

  it('render timeline v-for từ data THẬT (delivery + quota) + mốc relative VI', async () => {
    const data = {
      hospital: '_T-BV',
      hospital_name: 'BV Bạch Mai',
      data: [
        {
          kind: 'delivery',
          ts: todayAt(10, 30),
          title: 'Phiếu giao AM-SE-2026-00012 đã xuất cho NV',
          ref: 'AM-SE-2026-00012',
        },
        {
          kind: 'quota',
          ts: '2026-05-25 09:00:00',
          title: 'Quota Chỉ Vicryl còn 12%',
          ref: 'VT-0231',
        },
      ],
    }
    const html = await renderTemplate(data)
    // nội dung sự kiện THẬT.
    expect(html).toContain('Phiếu giao AM-SE-2026-00012 đã xuất cho NV')
    expect(html).toContain('Quota Chỉ Vicryl còn 12%')
    // mốc relative VI: delivery hôm nay → 'hôm nay 10:30'.
    expect(html).toContain('hôm nay 10:30')
    // tên BV resolve (hospital_name, KHÔNG mã).
    expect(html).toContain('BV Bạch Mai')
    // timeline class.
    expect(html).toContain('antmed-tl')
    expect(html).toContain('antmed-e')
  })

  it("render empty (data=[]) → 'Chưa có thông báo' (KHÔNG bịa)", async () => {
    const html = await renderTemplate({
      data: [],
      hospital: '_T-BV',
      hospital_name: 'BV Rỗng',
    })
    expect(html).toContain('Chưa có thông báo')
    const visible = html.replace(/<!--[\s\S]*?-->/g, '')
    expect(visible).not.toContain('Sắp có')
  })

  it("render loading → 'Đang tải…' (KHÔNG bịa nội dung)", async () => {
    const html = await renderTemplate(null, { loading: true })
    expect(html).toContain('Đang tải…')
  })

  it("render error → 'Lỗi tải thông báo' + nút thử lại", async () => {
    const html = await renderTemplate(null, { error: { messages: ['x'] } })
    expect(html).toContain('Lỗi tải thông báo')
    expect(html).toContain('Thử lại')
  })

  it('KHÔNG hospital → banner xác định BV (KHÔNG gọi resource / KHÔNG vỡ)', async () => {
    const html = await renderTemplate(null, { hospital: '' })
    expect(html).toContain('Chưa xác định bệnh viện')
    // KHÔNG render timeline khi chưa có BV.
    expect(html).not.toContain('antmed-e')
  })
})

// ── M07-2 util — tenderQuotaChip THẬT (đọc quota_chip BE, KHÔNG tự tính ngưỡng) ────────────────
describe('M07-2 util tenderQuotaChip — chip quota khớp quota_chip BE', () => {
  it('class: ok→green / warn→amber / danger→red (tái dùng PILL_THEME)', () => {
    expect(tenderQuotaChipClass('ok')).toBe(PILL_THEME.ok)
    expect(tenderQuotaChipClass('warn')).toBe(PILL_THEME.warn)
    expect(tenderQuotaChipClass('danger')).toBe(PILL_THEME.danger)
  })

  it('class chip lạ/rỗng → neutral (an toàn, không vỡ)', () => {
    expect(tenderQuotaChipClass('xyz')).toBe(PILL_THEME.neutral)
    expect(tenderQuotaChipClass(null)).toBe(PILL_THEME.neutral)
    expect(tenderQuotaChipClass(undefined)).toBe(PILL_THEME.neutral)
  })

  it("nhãn VI: ok→'Còn quota' / danger→'Hết quota'", () => {
    expect(tenderQuotaChipLabel('ok')).toBe('Còn quota')
    expect(tenderQuotaChipLabel('danger')).toBe('Hết quota')
  })

  it("nhãn warn → 'Còn X%' (X = remaining_pct format VI)", () => {
    expect(tenderQuotaChipLabel('warn', 8)).toBe('Còn 8%')
    expect(tenderQuotaChipLabel('warn', 2.5)).toBe('Còn 2,5%')
  })

  it("nhãn warn remaining_pct null/NaN → 'Còn 0%' (KHÔNG NaN)", () => {
    expect(tenderQuotaChipLabel('warn', null)).toBe('Còn 0%')
    expect(tenderQuotaChipLabel('warn', 'x')).toBe('Còn 0%')
  })

  it('chip lạ → fallback nhãn an toàn (vẫn chữ VI)', () => {
    expect(tenderQuotaChipLabel('xyz')).toBe('Còn quota')
  })
})

// ── M07-2 data layer — getTenderCatalog url tender_catalog + GET ──────────────────────────────
describe('M07-2 data layer — getTenderCatalog url tender_catalog + GET', () => {
  it('export function getTenderCatalog', () => {
    expect(dataSrc).toMatch(/export function getTenderCatalog/)
  })

  it('url == antmed_crm.api.antmed.customer.tender_catalog (naming contract)', () => {
    expect(dataSrc).toMatch(/antmed_crm\.api\.antmed\.customer\.tender_catalog/)
    expect(dataSrc).not.toMatch(
      /['"]crm\.api\.antmed\.customer\.tender_catalog/,
    )
  })

  it("resource có method === 'GET' + truyền params {hospital} + onError", () => {
    const block = dataSrc.slice(
      dataSrc.indexOf('export function getTenderCatalog'),
    )
    expect(block).toMatch(/method:\s*'GET'/)
    expect(block).toMatch(/params/)
    expect(block).toMatch(/onError/)
  })
})

// ── M07-2 Page — binding catalog + tri-branch + KHÔNG unit_price ───────────────────────────────
describe('M07-2 AntmedPortalHome — catalog binding + tri-branch + no unit_price', () => {
  it('import getTenderCatalog + helper chip + fmtQty', () => {
    expect(pageSrc).toMatch(/getTenderCatalog/)
    expect(pageSrc).toMatch(/tenderQuotaChipClass/)
    expect(pageSrc).toMatch(/tenderQuotaChipLabel/)
    expect(pageSrc).toMatch(/fmtQty/)
  })

  it('đọc catalog.data?.items + catalog.data?.hospital_name TRỰC TIẾP (KHÔNG .data.data)', () => {
    expect(pageSrc).toMatch(/catalog\.data\?\.items/)
    expect(pageSrc).toMatch(/catalog\.data\?\.hospital_name/)
    expect(pageCode).not.toMatch(/catalog\.data\?\.data/)
  })

  it('tri-branch catalog loading/error/empty (Đang tải danh mục… / Lỗi tải danh mục / empty)', () => {
    expect(pageSrc).toMatch(/Đang tải danh mục…/)
    expect(pageSrc).toMatch(/Lỗi tải danh mục/)
    expect(pageSrc).toMatch(/BV chưa có hợp đồng trúng thầu hiệu lực/)
    expect(pageSrc).toMatch(/catalog\.loading/)
    expect(pageSrc).toMatch(/catalog\.error/)
  })

  it('watch(hospital) refetch CẢ notif + catalog song song (chống dead-control)', () => {
    const script = pageSrc.slice(pageSrc.indexOf('<script'))
    expect(script).toMatch(/catalog\.fetch\(\{\s*hospital/)
    expect(script).toMatch(/notif\.fetch\(\{\s*hospital/)
  })

  it('page KHÔNG hiển thị unit_price / giá (data-scope portal BV)', () => {
    expect(pageCode).not.toMatch(/unit_price/)
  })

  it('page KHÔNG tự tính ngưỡng chip (đọc quota_chip BE; KHÔNG reduce/sort)', () => {
    const script = pageSrc.slice(pageSrc.indexOf('<script'))
    expect(script).not.toMatch(/\.reduce\(/)
    expect(script).not.toMatch(/\.sort\(/)
    // FE bind quota_chip từ BE (KHÔNG so sánh remaining_pct với 10/0 để tự phân tầng).
    expect(script).not.toMatch(/remaining_pct\s*[<>]=?\s*\d/)
  })
})

// ── M07-2 SSR render-verify — bảng catalog 3 chip + empty + thiếu hospital ────────────────────
// Harness ĐỘC LẬP (compile <template> THẬT của AntmedPortalHome.vue) — chứng minh RENDER thật card
// catalog (data 3 chip + empty + loading + error + thiếu hospital), KHÔNG chỉ structural-assert.
describe('M07-2 SSR render-verify — catalog render HTML thật', () => {
  async function renderCatalog(
    catalogData,
    { hospital = '_T-BV', catalogLoading = false, catalogError = null } = {},
  ) {
    const { parse } = await import('@vue/compiler-sfc')
    const { compile } = await import('@vue/compiler-dom')
    const vue = await import('vue')
    const { renderToString } = await import('@vue/server-renderer')
    const ui = await import('../../src/utils/antmedUi')

    const raw = readFileSync(
      path.join(srcDir, 'pages/AntmedPortalHome.vue'),
      'utf8',
    )
    const { descriptor } = parse(raw, { filename: 'AntmedPortalHome.vue' })
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
        Badge: {
          props: ['label'],
          render() {
            return vue.h('span', {}, this.label)
          },
        },
        Button: {
          props: ['label'],
          emits: ['click'],
          render() {
            return vue.h('button', {}, this.label)
          },
        },
        RouterLink: {
          props: ['to'],
          render() {
            return vue.h('a', {}, this.$slots.default?.())
          },
        },
        LoadingIndicator: {
          render() {
            return vue.h('span', {}, '...')
          },
        },
      },
      setup() {
        const notif = {
          data: { data: [], hospital, hospital_name: 'BV Test' },
          loading: false,
          error: null,
          reload() {},
          fetch() {},
        }
        const catalog = {
          data: catalogData,
          loading: catalogLoading,
          error: catalogError,
          reload() {},
          fetch() {},
        }
        return {
          __: i18n,
          notif,
          catalog,
          hospital: vue.computed(() => hospital),
          quickActions: ui.PORTAL_QUICK_ACTIONS,
          events: vue.computed(() => notif.data?.data || []),
          hospitalName: vue.computed(() => notif.data?.hospital_name || ''),
          catalogItems: vue.computed(() => catalog.data?.items || []),
          catalogHospitalName: vue.computed(
            () => catalog.data?.hospital_name || '',
          ),
          formatNotifTime: ui.formatNotifTime,
          fmtQty: ui.fmtQty,
          tenderQuotaChipClass: ui.tenderQuotaChipClass,
          tenderQuotaChipLabel: ui.tenderQuotaChipLabel,
        }
      },
      render: renderFn,
    }
    const app = vue.createSSRApp(comp)
    app.config.warnHandler = () => {}
    return await renderToString(app)
  }

  it('render bảng catalog 3 item + 3 chip text khớp quota_chip (Còn quota/Còn 8%/Hết quota)', async () => {
    const catalogData = {
      hospital: '_T-BV',
      hospital_name: 'BV Bạch Mai',
      contract: 'AM-HD-2026-00001',
      items: [
        {
          item: 'VT-001',
          item_name: 'Chỉ Vicryl 3-0',
          uom: 'Hộp',
          remaining_qty: 50,
          quota_qty: 100,
          used_qty: 50,
          remaining_pct: 50,
          quota_chip: 'ok',
        },
        {
          item: 'VT-002',
          item_name: 'Stent mạch vành',
          uom: 'Cái',
          remaining_qty: 8,
          quota_qty: 100,
          used_qty: 92,
          remaining_pct: 8,
          quota_chip: 'warn',
        },
        {
          item: 'VT-003',
          item_name: 'Bóng nong',
          uom: 'Cái',
          remaining_qty: 0,
          quota_qty: 100,
          used_qty: 100,
          remaining_pct: 0,
          quota_chip: 'danger',
        },
      ],
    }
    const html = await renderCatalog(catalogData)
    // tiêu đề card + tên BV (KHÔNG mã).
    expect(html).toContain('📋 Danh mục vật tư trúng thầu')
    expect(html).toContain('BV Bạch Mai')
    // tên vật tư (KHÔNG chỉ mã).
    expect(html).toContain('Chỉ Vicryl 3-0')
    expect(html).toContain('Stent mạch vành')
    expect(html).toContain('Bóng nong')
    // ĐVT.
    expect(html).toContain('Hộp')
    // 3 chip text THẬT theo quota_chip.
    expect(html).toContain('Còn quota')
    expect(html).toContain('Còn 8%')
    expect(html).toContain('Hết quota')
    // còn/tổng format VI (50 / 100).
    expect(html).toContain('50 / 100')
    // KHÔNG lộ giá.
    expect(html).not.toContain('unit_price')
  })

  it("render empty (items=[]) → 'BV chưa có hợp đồng trúng thầu hiệu lực'", async () => {
    const html = await renderCatalog({
      hospital: '_T-BV',
      hospital_name: 'BV Rỗng',
      contract: null,
      items: [],
    })
    expect(html).toContain('BV chưa có hợp đồng trúng thầu hiệu lực')
  })

  it("render catalog loading → 'Đang tải danh mục…'", async () => {
    const html = await renderCatalog(null, { catalogLoading: true })
    expect(html).toContain('Đang tải danh mục…')
  })

  it("render catalog error → 'Lỗi tải danh mục' + nút Thử lại", async () => {
    const html = await renderCatalog(null, {
      catalogError: { messages: ['x'] },
    })
    expect(html).toContain('Lỗi tải danh mục')
    expect(html).toContain('Thử lại')
  })

  it("KHÔNG hospital → card catalog hiện note 'Chưa xác định bệnh viện' (KHÔNG render bảng)", async () => {
    const html = await renderCatalog(null, { hospital: '' })
    expect(html).toContain(
      'Chưa xác định bệnh viện. Mở Portal kèm mã bệnh viện để xem danh mục.',
    )
    // KHÔNG render bảng catalog (header cột) khi chưa có BV.
    expect(html).not.toContain('Trạng thái quota')
  })
})
