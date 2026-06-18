import { readFileSync } from 'fs'
import path from 'path'
import { formatRevenueSub, formatVnMoney } from '../../src/utils/antmedUi'

// M02-8 — KPI "Doanh thu tháng" (mockup A1 hàng 1, Dashboard CEO /antmed).
// Idiom test (= antmedRevenueMix.test.js): content-assert nguồn (data/antmed.js, AntmedHome.vue)
// + behavior-assert helper THUẦN (antmedUi.js không import frappe-ui → import trực tiếp; data/antmed.js
// + .vue KÉO frappe-ui nên vitest KHÔNG mount → assert chuỗi nguồn).

const srcDir = path.resolve(__dirname, '../../src')
const dataSrc = readFileSync(path.join(srcDir, 'data/antmed.js'), 'utf8')
const homeSrc = readFileSync(path.join(srcDir, 'pages/AntmedHome.vue'), 'utf8')

// ── (1) Data layer — getMonthlyRevenue url + method GET (naming contract) ─────
describe('M02-8 data layer — getMonthlyRevenue url monthly_revenue + method GET', () => {
  it('export function getMonthlyRevenue', () => {
    expect(dataSrc).toMatch(/export function getMonthlyRevenue/)
  })

  it("url == 'antmed_crm.api.antmed.contract.monthly_revenue' (KHÔNG prefix sai)", () => {
    expect(dataSrc).toMatch(/antmed_crm\.api\.antmed\.contract\.monthly_revenue/)
    // KHÔNG dùng prefix app 'crm' (repo này là app riêng antmed_crm).
    expect(dataSrc).not.toMatch(/['"]crm\.api\.antmed\.contract\.monthly_revenue/)
  })

  it("resource có method === 'GET' (endpoint KHÔNG params → mặc định POST → 403)", () => {
    const start = dataSrc.indexOf('export function getMonthlyRevenue')
    // Cắt khối hàm tới '\n}\n' kết thúc body (KHÔNG dừng ở '}' của destructure tham số).
    const block = dataSrc.slice(start, dataSrc.indexOf('\n}', start))
    expect(block).toMatch(/method:\s*'GET'/)
    expect(block).toMatch(/antmed_crm\.api\.antmed\.contract\.monthly_revenue/)
  })

  it('dùng createResource (đọc dict THƯỜNG), KHÔNG createListResource', () => {
    expect(dataSrc).not.toMatch(/import[^\n]*createListResource/)
  })

  it('KHÔNG axios / TanStack trong data layer', () => {
    expect(dataSrc).not.toMatch(/axios|@tanstack/)
  })
})

// ── (2) AntmedHome — đọc monthlyRevenue.data.current TRỰC TIẾP (KHÔNG .data.data) ──
describe('M02-8 AntmedHome — wire KPI Doanh thu tháng THẬT', () => {
  it('import getMonthlyRevenue từ @/data/antmed', () => {
    expect(homeSrc).toMatch(/getMonthlyRevenue/)
    expect(homeSrc).toMatch(/from '@\/data\/antmed'/)
  })

  it('khai báo resource monthlyRevenue = getMonthlyRevenue({ auto: true }) + onError toast', () => {
    expect(homeSrc).toMatch(/const monthlyRevenue = getMonthlyRevenue\(\{[\s\S]*?auto:\s*true/)
    expect(homeSrc).toMatch(/getMonthlyRevenue\(\{[\s\S]*?onError/)
  })

  it('đọc monthlyRevenue.data.current (KHÔNG .data.data — dict THƯỜNG)', () => {
    expect(homeSrc).toMatch(/monthlyRevenue\.data\?\.current/)
    expect(homeSrc).toMatch(/monthlyRevenue\.data\?\.month_label/)
    expect(homeSrc).toMatch(/monthlyRevenue\.data\?\.delta_pct/)
    expect(homeSrc).not.toMatch(/monthlyRevenue\.data\?\.data/)
  })

  it('value qua formatVnMoney(current) + nối " ₫" (KHÔNG tự tính/aggregate)', () => {
    expect(homeSrc).toMatch(/formatVnMoney\(cur\)/)
    expect(homeSrc).toMatch(/₫/)
  })

  it('dòng phụ qua formatRevenueSub(month_label, delta_pct) (chỉ format, KHÔNG tính lại)', () => {
    expect(homeSrc).toMatch(/formatRevenueSub\(/)
  })
})

// ── (3) Thẻ 'Doanh thu tháng' KHÔNG còn empty placeholder khi có data ─────────
describe('M02-8 AntmedHome — thẻ Doanh thu tháng có nhánh data (KHÔNG còn placeholder cứng)', () => {
  it('thẻ data bind :value=revenueValue + :sub=revenueSub (v-else nhánh có data)', () => {
    expect(homeSrc).toMatch(/:value="revenueValue"/)
    expect(homeSrc).toMatch(/:sub="revenueSub"/)
  })

  it("KHÔNG còn placeholder 'Sắp có (cần module Doanh thu)' cho thẻ Doanh thu tháng", () => {
    expect(homeSrc).not.toMatch(/Sắp có \(cần module Doanh thu\)/)
  })

  it("loading → placeholder 'Đang tải…' (KHÔNG bịa số); error → 'Lỗi tải doanh thu' (KHÔNG vỡ layout)", () => {
    expect(homeSrc).toMatch(/monthlyRevenue\.loading/)
    expect(homeSrc).toMatch(/Đang tải…/)
    expect(homeSrc).toMatch(/monthlyRevenue\.error/)
    expect(homeSrc).toMatch(/Lỗi tải doanh thu/)
  })
})

// ── (6) Regression — 3 KPI khác + 2 placeholder hàng 2 KHÔNG đổi ─────────────
describe('M02-8 regression — KPI khác + placeholder hàng 2 GIỮ NGUYÊN', () => {
  it("vẫn còn 'Số bệnh viện' (KPI thật) + 'Số bác sỹ' + ring 'Quota đã dùng'", () => {
    expect(homeSrc).toMatch(/Số bệnh viện/)
    expect(homeSrc).toMatch(/Số bác sỹ/)
    expect(homeSrc).toMatch(/Quota đã dùng/)
  })

  it("placeholder hàng 2 GIỮ: 'Sắp có (cần module Giao phòng mổ)' + 'Sắp có (cần module Bộ dụng cụ)'", () => {
    expect(homeSrc).toMatch(/Sắp có \(cần module Giao phòng mổ\)/)
    expect(homeSrc).toMatch(/Sắp có \(cần module Bộ dụng cụ\)/)
  })

  it('các widget hàng dưới (Top BV / Cơ cấu DT / Pipeline / Cảnh báo) KHÔNG bị xoá', () => {
    expect(homeSrc).toMatch(/AntmedTopHospitalsCard/)
    expect(homeSrc).toMatch(/AntmedRevenueMixCard/)
    expect(homeSrc).toMatch(/AntmedTenderFunnelCard/)
    expect(homeSrc).toMatch(/AntmedAlertsPanel/)
  })
})

// ── (7) no-mock / no-aggregate guard — FE KHÔNG reduce/hardcode tiền ─────────
describe('M02-8 guard — KHÔNG mock / KHÔNG aggregate FE', () => {
  it('AntmedHome KHÔNG .reduce / .sort / hardcode số tiền cho doanh thu', () => {
    // KHÔNG tự gộp doanh thu ở FE (BR rollup ở BE).
    expect(homeSrc).not.toMatch(/monthlyRevenue[\s\S]{0,80}\.reduce\(/)
    expect(homeSrc).not.toMatch(/antmedMock|mockData/)
  })
})

// ── (4) formatRevenueSub — mũi tên theo dấu + null → '—' (PURE) ──────────────
describe('formatRevenueSub — dòng phụ MoM (PURE)', () => {
  it("delta_pct > 0 → '▲' + '% vs tháng trước'", () => {
    const s = formatRevenueSub('T6/2026', 14)
    expect(s).toContain('▲')
    expect(s).toContain('14% vs tháng trước')
    expect(s).toContain('T6/2026')
    expect(s).not.toContain('▼')
  })

  it("delta_pct < 0 → '▼' + giá trị tuyệt đối (KHÔNG dấu trừ)", () => {
    const s = formatRevenueSub('T6/2026', -8.5)
    expect(s).toContain('▼')
    expect(s).toContain('8.5% vs tháng trước')
    expect(s).not.toContain('-8.5')
    expect(s).not.toContain('▲')
  })

  it("delta_pct == null → '— vs tháng trước' (KHÔNG mũi tên, KHÔNG NaN)", () => {
    const s = formatRevenueSub('T6/2026', null)
    expect(s).toContain('— vs tháng trước')
    expect(s).not.toContain('▲')
    expect(s).not.toContain('▼')
    expect(s).not.toContain('NaN')
  })

  it("delta_pct == undefined → '— vs tháng trước' (KHÔNG NaN)", () => {
    const s = formatRevenueSub('T6/2026', undefined)
    expect(s).toContain('— vs tháng trước')
    expect(s).not.toContain('NaN')
  })

  it("delta_pct == 0 → '0% vs tháng trước' (KHÔNG mũi tên)", () => {
    const s = formatRevenueSub('T6/2026', 0)
    expect(s).toContain('0% vs tháng trước')
    expect(s).not.toContain('▲')
    expect(s).not.toContain('▼')
  })

  it('month_label rỗng → chỉ render phần MoM (KHÔNG tiền tố lủng lẳng " · ")', () => {
    const s = formatRevenueSub('', 14)
    expect(s).not.toMatch(/^ · /)
    expect(s).toContain('14% vs tháng trước')
  })
})

// ── (5) current==0 → '0 ₫' (số thật, KHÔNG 'Sắp có') ─────────────────────────
describe('M02-8 value KPI — current=0 là số THẬT, KHÔNG placeholder', () => {
  it("formatVnMoney(0) + ' ₫' === '0 ₫' (empty-state vẫn là số thật)", () => {
    expect(`${formatVnMoney(0)} ₫`).toBe('0 ₫')
  })

  it("formatVnMoney(120000000) === '120 tr' (số THẬT, không bịa)", () => {
    expect(formatVnMoney(120_000_000)).toBe('120 tr')
  })

  it("formatVnMoney(2100000000) === '2,1 tỷ'", () => {
    expect(formatVnMoney(2_100_000_000)).toBe('2,1 tỷ')
  })
})
