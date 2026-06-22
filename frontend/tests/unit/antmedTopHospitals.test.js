import { readFileSync } from 'fs'
import path from 'path'
import {
  healthBarClass,
  formatVnMoney,
  BAR_THEME,
} from '../../src/utils/antmedUi'

// M02-4 — widget "Top 10 Bệnh viện" (mockup A1, Dashboard CEO /antmed).
// Idiom test (= antmedContractHealth.test.js): content-assert nguồn (data/antmed.js, AntmedHome.vue,
// AntmedTopHospitalsCard.vue) + behavior-assert helper THUẦN (antmedUi.js không import frappe-ui →
// import trực tiếp được; data/antmed.js + .vue KÉO frappe-ui nên vitest KHÔNG mount được → assert chuỗi).

const srcDir = path.resolve(__dirname, '../../src')
const dataSrc = readFileSync(path.join(srcDir, 'data/antmed.js'), 'utf8')
const homeSrc = readFileSync(path.join(srcDir, 'pages/AntmedHome.vue'), 'utf8')
const cardSrc = readFileSync(
  path.join(srcDir, 'components/Antmed/AntmedTopHospitalsCard.vue'),
  'utf8',
)

// ── Data layer — getTopHospitals gọi đúng endpoint (naming contract BE-FE) ────
describe('M02-4 data layer — getTopHospitals url top_hospitals', () => {
  it('export function getTopHospitals', () => {
    expect(dataSrc).toMatch(/export function getTopHospitals/)
  })

  it('url == antmed_crm.api.antmed.contract.top_hospitals (KHÔNG prefix sai)', () => {
    expect(dataSrc).toMatch(/antmed_crm\.api\.antmed\.contract\.top_hospitals/)
    // KHÔNG dùng 'crm.api.antmed' (idiom app khác) trong khối getTopHospitals
    expect(dataSrc).not.toMatch(/['"]crm\.api\.antmed\.contract\.top_hospitals/)
  })

  it('dùng createResource (đọc dict bọc), KHÔNG import createListResource', () => {
    expect(dataSrc).toMatch(
      /import\s*\{\s*createResource\s*\}\s*from\s*'frappe-ui'/,
    )
    // chỉ chặn IMPORT createListResource (docstring nhắc tên là OK)
    expect(dataSrc).not.toMatch(/import[^\n]*createListResource/)
  })

  it('KHÔNG axios / TanStack trong data layer', () => {
    expect(dataSrc).not.toMatch(/axios|@tanstack/)
  })
})

// ── AntmedHome.vue — wire widget THẬT, thay placeholder, drill-down ───────────
describe('M02-4 AntmedHome — wire widget Top 10 Bệnh viện THẬT', () => {
  it('import getTopHospitals từ @/data/antmed', () => {
    expect(homeSrc).toMatch(/getTopHospitals/)
    expect(homeSrc).toMatch(/from '@\/data\/antmed'/)
  })

  it('import + render AntmedTopHospitalsCard (KHÔNG còn AntmedPlaceholderPanel Top 10)', () => {
    expect(homeSrc).toMatch(/AntmedTopHospitalsCard/)
    expect(homeSrc).toMatch(/<AntmedTopHospitalsCard/)
    // placeholder Top 10 cũ đã bị thay: không còn <AntmedPlaceholderPanel title="…Top 10…">
    expect(homeSrc).not.toMatch(/<AntmedPlaceholderPanel[\s\S]{0,120}Top 10/)
  })

  it("render tiêu đề widget 'Top 10 Bệnh viện' (qua card hoặc trực tiếp)", () => {
    // tiêu đề sống trong card; Home truyền data → tiêu đề ở card source
    expect(cardSrc).toMatch(/Top 10 Bệnh viện/)
  })

  it('đọc r.data.data cho list (KHÔNG r.data trực tiếp), + total_count', () => {
    expect(homeSrc).toMatch(/topHospitals\.data\?\.data/)
    expect(homeSrc).toMatch(/topHospitals\.data\?\.total_count/)
  })

  it('drill-down router.push name AntmedHospitalDetail params {name: row.hospital}', () => {
    expect(homeSrc).toMatch(/router\.push/)
    expect(homeSrc).toMatch(/AntmedHospitalDetail/)
    // openHospital nhận hospital → push params.name
    expect(homeSrc).toMatch(/openHospital/)
    expect(homeSrc).toMatch(/params:\s*\{\s*name\s*\}/)
  })

  it('fetch ĐỘC LẬP (auto:true) + onError toast', () => {
    expect(homeSrc).toMatch(/getTopHospitals\(\{[\s\S]*?auto:\s*true/)
    expect(homeSrc).toMatch(/toast\.error/)
  })

  it('KHÔNG tự tính ngưỡng quota ở FE (>=70/>=90/>=95 literal) trong Home', () => {
    expect(homeSrc).not.toMatch(/>=\s*70|>=\s*90|>=\s*95/)
  })
})

// ── AntmedTopHospitalsCard.vue — bảng 3 cột + bar màu + tri-branch + a11y ─────
describe('M02-4 AntmedTopHospitalsCard — bảng 3 cột, bar màu, tri-branch', () => {
  it('dùng healthBarClass cho bar (map cờ BE, KHÔNG tính ngưỡng)', () => {
    expect(cardSrc).toMatch(/healthBarClass/)
    expect(cardSrc).toMatch(/:class="healthBarClass\(row\.health_color\)"/)
    // KHÔNG literal ngưỡng trong card
    expect(cardSrc).not.toMatch(/>=\s*70|>=\s*90|>=\s*95/)
  })

  it('dùng formatVnMoney cho doanh thu (tỷ/tr)', () => {
    expect(cardSrc).toMatch(/formatVnMoney\(row\.revenue\)/)
  })

  it('hiển thị hospital_name (KHÔNG mã hospital thô)', () => {
    expect(cardSrc).toMatch(/row\.hospital_name/)
  })

  it('3 cột BV | DT | Quota', () => {
    expect(cardSrc).toMatch(/Bệnh viện/)
    expect(cardSrc).toMatch(/Doanh thu/)
    expect(cardSrc).toMatch(/Quota/)
  })

  it('tri-branch: loading / error(Thử lại) / empty (Chưa có dữ liệu bệnh viện)', () => {
    expect(cardSrc).toMatch(/v-if="loading"/)
    expect(cardSrc).toMatch(/v-else-if="error"/)
    expect(cardSrc).toMatch(/Thử lại/)
    expect(cardSrc).toMatch(/Chưa có dữ liệu bệnh viện/)
  })

  it('drill-down: <tr> role=link + tabindex + @click/@keydown.enter emit open(row.hospital)', () => {
    expect(cardSrc).toMatch(/role="link"/)
    expect(cardSrc).toMatch(/tabindex="0"/)
    expect(cardSrc).toMatch(/\$emit\('open',\s*row\.hospital\)/)
    expect(cardSrc).toMatch(/@keydown\.enter/)
  })

  it('a11y: progressbar aria-valuenow cho bar', () => {
    expect(cardSrc).toMatch(/role="progressbar"/)
    expect(cardSrc).toMatch(/aria-valuenow/)
    expect(cardSrc).toMatch(/aria-valuemin="0"/)
    expect(cardSrc).toMatch(/aria-valuemax="100"/)
  })

  it('FE KHÔNG sort lại (giữ thứ tự BE) — không có .sort( trong card', () => {
    expect(cardSrc).not.toMatch(/\.sort\(/)
  })
})

// ── Helper thuần healthBarClass — map cờ màu BE → class fill (3 nhánh) ────────
describe('healthBarClass — 3 nhánh map health_color BE → class bar', () => {
  it("'green' → BAR_THEME.default (brand teal)", () => {
    expect(healthBarClass('green')).toBe(BAR_THEME.default)
  })
  it("'orange' → BAR_THEME.warn (amber)", () => {
    expect(healthBarClass('orange')).toBe(BAR_THEME.warn)
  })
  it("'red' → BAR_THEME.danger (đỏ)", () => {
    expect(healthBarClass('red')).toBe(BAR_THEME.danger)
  })
  it('cờ lạ/null/undefined → default (xanh, không vỡ)', () => {
    expect(healthBarClass('xyz')).toBe(BAR_THEME.default)
    expect(healthBarClass(null)).toBe(BAR_THEME.default)
    expect(healthBarClass(undefined)).toBe(BAR_THEME.default)
  })
})

// ── Helper thuần formatVnMoney — doanh thu gọn 'X,Y tỷ' / 'X,Y tr' ────────────
describe('formatVnMoney — format doanh thu HĐ (tỷ/tr)', () => {
  it('1,2 tỷ', () => {
    expect(formatVnMoney(1_200_000_000)).toBe('1,2 tỷ')
  })
  it('5 tỷ (bỏ .0)', () => {
    expect(formatVnMoney(5_000_000_000)).toBe('5 tỷ')
  })
  it('1,9 tr', () => {
    expect(formatVnMoney(1_900_000)).toBe('1,9 tr')
  })
  it('null/undefined → "— " (placeholder thiếu)', () => {
    expect(formatVnMoney(null)).toBe('— ')
    expect(formatVnMoney(undefined)).toBe('— ')
  })
})
