import { readFileSync } from 'fs'
import path from 'path'
import { barHeightPct } from '../../src/utils/antmedUi'

// M02-6 — widget "Tiêu hao HĐ theo tháng" (mockup A1, render trên màn Chi tiết HĐ
// /antmed/contracts/:name → AntmedContractDetail.vue + AntmedConsumptionChartCard.vue).
// Idiom test (= antmedTopHospitals.test.js): content-assert nguồn (data/antmed.js, page, card)
// + behavior-assert helper THUẦN barHeightPct (antmedUi.js không import frappe-ui → import
// trực tiếp được; data/antmed.js + .vue KÉO frappe-ui nên vitest KHÔNG mount → assert chuỗi).

const srcDir = path.resolve(__dirname, '../../src')
const dataSrc = readFileSync(path.join(srcDir, 'data/antmed.js'), 'utf8')
const pageSrc = readFileSync(
  path.join(srcDir, 'pages/AntmedContractDetail.vue'),
  'utf8',
)
const cardSrc = readFileSync(
  path.join(srcDir, 'components/Antmed/AntmedConsumptionChartCard.vue'),
  'utf8',
)

// ── Data layer — getContractConsumptionByMonth gọi đúng endpoint (naming contract BE-FE) ──
describe('M02-6 data layer — getContractConsumptionByMonth url contract_consumption_by_month', () => {
  it('export function getContractConsumptionByMonth', () => {
    expect(dataSrc).toMatch(/export function getContractConsumptionByMonth/)
  })

  it('url == antmed_crm.api.antmed.contract.contract_consumption_by_month (KHÔNG prefix sai)', () => {
    expect(dataSrc).toMatch(
      /antmed_crm\.api\.antmed\.contract\.contract_consumption_by_month/,
    )
    // KHÔNG dùng 'crm.api.antmed' (idiom app khác)
    expect(dataSrc).not.toMatch(
      /['"]crm\.api\.antmed\.contract\.contract_consumption_by_month/,
    )
  })

  it('dùng createResource (mirror getContract), KHÔNG import createListResource', () => {
    expect(dataSrc).toMatch(
      /import\s*\{\s*createResource\s*\}\s*from\s*'frappe-ui'/,
    )
    expect(dataSrc).not.toMatch(/import[^\n]*createListResource/)
  })

  it('KHÔNG axios / TanStack trong data layer', () => {
    expect(dataSrc).not.toMatch(/axios|@tanstack/)
  })
})

// ── AntmedContractDetail.vue — wire card DƯỚI bảng quota, fetch ĐỘC LẬP getContract ───────
describe('M02-6 AntmedContractDetail — wire widget tiêu hao THẬT', () => {
  it('import getContractConsumptionByMonth + AntmedConsumptionChartCard', () => {
    expect(pageSrc).toMatch(/getContractConsumptionByMonth/)
    expect(pageSrc).toMatch(/AntmedConsumptionChartCard/)
    expect(pageSrc).toMatch(/<AntmedConsumptionChartCard/)
  })

  it('gọi getContractConsumptionByMonth với contract = route param (props.name) + auto:true', () => {
    expect(pageSrc).toMatch(
      /getContractConsumptionByMonth\(\{[\s\S]*?contract:\s*props\.name[\s\S]*?auto:\s*true/,
    )
  })

  it('fetch ĐỘC LẬP với getContract (consumption là resource RIÊNG, không nằm trong contract.data)', () => {
    // tồn tại biến resource riêng cho consumption (KHÔNG đọc contract.data.* cho widget)
    expect(pageSrc).toMatch(/const consumption = getContractConsumptionByMonth/)
  })

  it('bind data/total-qty/loading/error + @retry reload (lỗi widget KHÔNG vỡ trang)', () => {
    expect(pageSrc).toMatch(/:data="consumption\.data\?\.data/)
    expect(pageSrc).toMatch(/:total-qty="consumption\.data\?\.total_qty/)
    expect(pageSrc).toMatch(/:loading="consumption\.loading"/)
    expect(pageSrc).toMatch(/:error="consumption\.error"/)
    expect(pageSrc).toMatch(/@retry="consumption\.reload\(\)"/)
  })

  it('truyền số HĐ + tên BV vào title card', () => {
    expect(pageSrc).toMatch(/:contract-no=/)
    expect(pageSrc).toMatch(/:hospital-name=/)
  })

  it('toast lỗi VI cho widget (onError) — KHÔNG nuốt lỗi', () => {
    expect(pageSrc).toMatch(/toast\.error/)
  })
})

// ── AntmedConsumptionChartCard.vue — bar chart 12 cột + tri-branch + a11y ─────────────────
describe('M02-6 AntmedConsumptionChartCard — bar chart 12 cột, tri-branch, a11y', () => {
  it("title 'Tiêu hao <số HĐ> (<BV>) theo tháng'", () => {
    expect(cardSrc).toMatch(/Tiêu hao/)
    expect(cardSrc).toMatch(/theo tháng/)
    // bind số HĐ + tên BV qua props
    expect(cardSrc).toMatch(/contractNo|contract-no|contract_no/)
    expect(cardSrc).toMatch(/hospitalName|hospital-name|hospital_name/)
  })

  it('dùng barHeightPct cho chiều cao cột (KHÔNG tự tính qty/max ở template)', () => {
    expect(cardSrc).toMatch(/barHeightPct/)
  })

  it('nhãn trục X từ bar.label (T1..T12), KHÔNG hardcode tháng', () => {
    expect(cardSrc).toMatch(/\.label/)
  })

  it('màu bar token AntMed teal (BAR_THEME.default / bg-teal)', () => {
    expect(cardSrc).toMatch(/teal|BAR_THEME/)
  })

  it('a11y: bar role=img/progressbar + aria hiển thị qty thực', () => {
    expect(cardSrc).toMatch(/role="img"|role="progressbar"/)
    expect(cardSrc).toMatch(/aria-label|aria-valuenow/)
  })

  it('tri-branch: loading (Đang tải…) / error (Thử lại) / empty (Chưa có dữ liệu tiêu hao)', () => {
    expect(cardSrc).toMatch(/v-if="loading"/)
    expect(cardSrc).toMatch(/Đang tải/)
    expect(cardSrc).toMatch(/v-else-if="error"/)
    expect(cardSrc).toMatch(/Thử lại/)
    expect(cardSrc).toMatch(/Chưa có dữ liệu tiêu hao/)
  })

  it('error nút Thử lại emit retry', () => {
    expect(cardSrc).toMatch(/\$emit\('retry'\)/)
  })

  it('FE KHÔNG sort lại (giữ thứ tự BE) — không .sort( trong card', () => {
    expect(cardSrc).not.toMatch(/\.sort\(/)
  })

  it('KHÔNG hardcode mock số liệu trong UI', () => {
    expect(cardSrc).not.toMatch(/antmedMock|mockData|MOCK/)
  })
})

// ── Helper thuần barHeightPct — qty/max*100 (max<=0 → 0, no ZeroDivision) ─────────────────
describe('barHeightPct — chiều cao cột bar (pure)', () => {
  it('(qty=50, max=100) → 50', () => {
    expect(barHeightPct(50, 100)).toBe(50)
  })
  it('(qty=100, max=100) → 100', () => {
    expect(barHeightPct(100, 100)).toBe(100)
  })
  it('(qty=0, max=0) → 0 (KHÔNG ZeroDivision)', () => {
    expect(barHeightPct(0, 0)).toBe(0)
  })
  it('(qty=10, max=0) → 0 (max<=0 fail-safe)', () => {
    expect(barHeightPct(10, 0)).toBe(0)
  })
  it('(qty=0, max=100) → 0', () => {
    expect(barHeightPct(0, 100)).toBe(0)
  })
  it('round: (qty=1, max=3) → 33', () => {
    expect(barHeightPct(1, 3)).toBe(33)
  })
  it('null/undefined/NaN → 0 (không vỡ)', () => {
    expect(barHeightPct(null, 100)).toBe(0)
    expect(barHeightPct(50, null)).toBe(0)
    expect(barHeightPct(undefined, undefined)).toBe(0)
    expect(barHeightPct('x', 100)).toBe(0)
  })
  it('clamp: qty > max → 100 (không vượt 100%)', () => {
    expect(barHeightPct(150, 100)).toBe(100)
  })
})
