import { readFileSync } from 'fs'
import path from 'path'
import { revenueMixBarStyle, formatCurrencyVi } from '../../src/utils/antmedUi'

// M02-7 — widget "Cơ cấu doanh thu" (mockup A2, Dashboard CEO /antmed).
// Idiom test (= antmedTopHospitals.test.js): content-assert nguồn (data/antmed.js, AntmedHome.vue,
// AntmedRevenueMixCard.vue) + behavior-assert helper THUẦN (antmedUi.js không import frappe-ui →
// import trực tiếp được; data/antmed.js + .vue KÉO frappe-ui nên vitest KHÔNG mount được → assert chuỗi).

const srcDir = path.resolve(__dirname, '../../src')
const dataSrc = readFileSync(path.join(srcDir, 'data/antmed.js'), 'utf8')
const homeSrc = readFileSync(path.join(srcDir, 'pages/AntmedHome.vue'), 'utf8')
const cardSrc = readFileSync(
  path.join(srcDir, 'components/Antmed/AntmedRevenueMixCard.vue'),
  'utf8',
)

// ── Data layer — getRevenueMix gọi đúng endpoint + method GET (naming contract + ADR-M02-14) ──
describe('M02-7 data layer — getRevenueMix url revenue_mix + method GET', () => {
  it('export function getRevenueMix', () => {
    expect(dataSrc).toMatch(/export function getRevenueMix/)
  })

  it('url == antmed_crm.api.antmed.contract.revenue_mix (KHÔNG prefix sai)', () => {
    expect(dataSrc).toMatch(/antmed_crm\.api\.antmed\.contract\.revenue_mix/)
    expect(dataSrc).not.toMatch(/['"]crm\.api\.antmed\.contract\.revenue_mix/)
  })

  it("resource có method === 'GET' (chống defect POST→403, ADR-M02-14)", () => {
    // Khối getRevenueMix phải set method:'GET' (revenue_mix() KHÔNG có params → mặc định POST vỡ).
    const block = dataSrc.slice(dataSrc.indexOf('export function getRevenueMix'))
    expect(block).toMatch(/method:\s*'GET'/)
  })

  it('dùng createResource (đọc dict bọc), KHÔNG import createListResource', () => {
    expect(dataSrc).toMatch(
      /import\s*\{\s*createResource\s*\}\s*from\s*'frappe-ui'/,
    )
    expect(dataSrc).not.toMatch(/import[^\n]*createListResource/)
  })

  it('KHÔNG axios / TanStack trong data layer', () => {
    expect(dataSrc).not.toMatch(/axios|@tanstack/)
  })
})

// ── AntmedHome.vue — wire widget THẬT cùng hàng / ngay sau Top 10 ─────────────
describe('M02-7 AntmedHome — wire widget Cơ cấu doanh thu THẬT', () => {
  it('import getRevenueMix từ @/data/antmed', () => {
    expect(homeSrc).toMatch(/getRevenueMix/)
    expect(homeSrc).toMatch(/from '@\/data\/antmed'/)
  })

  it('import + render AntmedRevenueMixCard (cùng hàng Top 10 — grid lg:grid-cols-2)', () => {
    expect(homeSrc).toMatch(/AntmedRevenueMixCard/)
    expect(homeSrc).toMatch(/<AntmedRevenueMixCard/)
    // Section Top 10 đã thành 2-col chứa cả 2 card (cùng hàng ≥lg).
    expect(homeSrc).toMatch(
      /<AntmedTopHospitalsCard[\s\S]*?<AntmedRevenueMixCard|<AntmedRevenueMixCard[\s\S]*?<AntmedTopHospitalsCard/,
    )
  })

  it('đọc r.data.data + r.data.total_revenue (KHÔNG .data.data.data)', () => {
    expect(homeSrc).toMatch(/revenueMix\.data\?\.data/)
    expect(homeSrc).toMatch(/revenueMix\.data\?\.total_revenue/)
  })

  it('fetch ĐỘC LẬP (auto:true) — KHÔNG đụng card Top 10', () => {
    expect(homeSrc).toMatch(/getRevenueMix\(\{[\s\S]*?auto:\s*true/)
    // Top 10 vẫn còn nguyên (no-regression).
    expect(homeSrc).toMatch(/getTopHospitals/)
  })
})

// ── AntmedRevenueMixCard.vue — 4 dòng A–D + bar màu brand + tri-branch ────────
describe('M02-7 AntmedRevenueMixCard — bảng 4 lớp, bar brand, tri-branch', () => {
  it("tiêu đề widget 'Cơ cấu doanh thu'", () => {
    expect(cardSrc).toMatch(/Cơ cấu doanh thu/)
  })

  it('render label lớp + dùng formatCurrencyVi cho doanh thu (chữ ĐẦY ĐỦ triệu/tỷ — mockup A2)', () => {
    expect(cardSrc).toMatch(/formatCurrencyVi\(row\.revenue\)/)
    expect(cardSrc).toMatch(/row\.label/)
  })

  it('bar width qua revenueMixBarStyle(pct) — KHÔNG tự tính/sort/đổi màu theo lớp', () => {
    expect(cardSrc).toMatch(/revenueMixBarStyle\(row\.pct\)/)
    // KHÔNG ngưỡng health green/orange/red trong card cơ cấu (1 màu brand).
    expect(cardSrc).not.toMatch(/healthBarClass/)
    expect(cardSrc).not.toMatch(/>=\s*70|>=\s*80|>=\s*90|>=\s*100/)
    // FE KHÔNG sort lại (BE trả cố định 4 dòng A→B→C→D).
    expect(cardSrc).not.toMatch(/\.sort\(/)
  })

  it('hiển thị % tỷ trọng (pct) cạnh bar', () => {
    expect(cardSrc).toMatch(/row\.pct/)
  })

  it('tri-branch: loading(Đang tải) / error(Thử lại) / empty (Chưa có dữ liệu doanh thu)', () => {
    expect(cardSrc).toMatch(/v-if="loading"/)
    expect(cardSrc).toMatch(/Đang tải/)
    expect(cardSrc).toMatch(/v-else-if="error"/)
    expect(cardSrc).toMatch(/Thử lại/)
    expect(cardSrc).toMatch(/Chưa có dữ liệu doanh thu/)
  })

  it('empty branch dựa total_revenue===0 (KHÔNG mock hardcode)', () => {
    expect(cardSrc).toMatch(/totalRevenue/)
    // KHÔNG nhúng mock số liệu trong card.
    expect(cardSrc).not.toMatch(/antmedMock|mockData/)
  })

  it('mọi nhãn qua __()', () => {
    expect(cardSrc).toMatch(/__\('Cơ cấu doanh thu'\)/)
  })
})

// ── Helper thuần revenueMixBarStyle — width clamp 0–100 (PURE) ────────────────
describe('revenueMixBarStyle — width clamp 0–100 (PURE)', () => {
  it('42.5 → 42.5%', () => {
    expect(revenueMixBarStyle(42.5)).toEqual({ width: '42.5%' })
  })
  it('-5 → 0% (clamp dưới)', () => {
    expect(revenueMixBarStyle(-5)).toEqual({ width: '0%' })
  })
  it('120 → 100% (clamp trên)', () => {
    expect(revenueMixBarStyle(120)).toEqual({ width: '100%' })
  })
  it('0 → 0%', () => {
    expect(revenueMixBarStyle(0)).toEqual({ width: '0%' })
  })
  it('null/undefined/NaN → 0% (không vỡ)', () => {
    expect(revenueMixBarStyle(null)).toEqual({ width: '0%' })
    expect(revenueMixBarStyle(undefined)).toEqual({ width: '0%' })
    expect(revenueMixBarStyle(NaN)).toEqual({ width: '0%' })
    expect(revenueMixBarStyle('abc')).toEqual({ width: '0%' })
  })
})

// ── formatCurrencyVi — tiền VI chữ ĐẦY ĐỦ (mockup A2 — khớp acceptance verbose) ──
describe('formatCurrencyVi — doanh thu cơ cấu (tỷ/triệu chữ đầy đủ)', () => {
  it("2_100_000_000 → '2,1 tỷ'", () => {
    expect(formatCurrencyVi(2_100_000_000)).toBe('2,1 tỷ')
  })
  it("186_400_000 → '186,4 triệu' (chữ đầy đủ — acceptance A2)", () => {
    expect(formatCurrencyVi(186_400_000)).toBe('186,4 triệu')
  })
  it("0 → '0 đ' (lớp revenue=0 vẫn render số)", () => {
    expect(formatCurrencyVi(0)).toBe('0 đ')
  })
  it("null/undefined → '— ' (placeholder thiếu)", () => {
    expect(formatCurrencyVi(null)).toBe('— ')
    expect(formatCurrencyVi(undefined)).toBe('— ')
  })
})
