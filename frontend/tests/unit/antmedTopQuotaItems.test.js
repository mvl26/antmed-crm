import { readFileSync } from 'fs'
import path from 'path'
import { healthBarClass, BAR_THEME } from '../../src/utils/antmedUi'

// M02-5 — widget "Danh mục VT trúng thầu — top 5" (mockup A2, chân màn /antmed/contract-health).
// Idiom test (= antmedTopHospitals.test.js): content-assert nguồn (data/antmed.js,
// AntmedContractHealth.vue, AntmedTopQuotaItemsCard.vue) + behavior-assert helper THUẦN
// (antmedUi.js không import frappe-ui → import trực tiếp được; data/antmed.js + .vue KÉO
// frappe-ui nên vitest KHÔNG mount được → assert chuỗi nguồn).

const srcDir = path.resolve(__dirname, '../../src')
const dataSrc = readFileSync(path.join(srcDir, 'data/antmed.js'), 'utf8')
const pageSrc = readFileSync(path.join(srcDir, 'pages/AntmedContractHealth.vue'), 'utf8')
const cardSrc = readFileSync(
  path.join(srcDir, 'components/Antmed/AntmedTopQuotaItemsCard.vue'),
  'utf8',
)

// ── Data layer — getTopQuotaItems gọi đúng endpoint (naming contract BE-FE) ───
describe('M02-5 data layer — getTopQuotaItems url top_quota_items', () => {
  it('export function getTopQuotaItems', () => {
    expect(dataSrc).toMatch(/export function getTopQuotaItems/)
  })

  it('url == antmed_crm.api.antmed.contract.top_quota_items (KHÔNG prefix sai)', () => {
    expect(dataSrc).toMatch(/antmed_crm\.api\.antmed\.contract\.top_quota_items/)
    // KHÔNG dùng 'crm.api.antmed' (idiom app khác) trong khối getTopQuotaItems
    expect(dataSrc).not.toMatch(/['"]crm\.api\.antmed\.contract\.top_quota_items/)
  })

  it('dùng createResource (đọc dict bọc), KHÔNG import createListResource', () => {
    expect(dataSrc).toMatch(/import\s*\{\s*createResource\s*\}\s*from\s*'frappe-ui'/)
    expect(dataSrc).not.toMatch(/import[^\n]*createListResource/)
  })

  it('KHÔNG axios / TanStack trong data layer', () => {
    expect(dataSrc).not.toMatch(/axios|@tanstack/)
  })
})

// ── AntmedContractHealth.vue — wire widget THẬT dưới bảng Sức khỏe HĐ ─────────
describe('M02-5 AntmedContractHealth — wire widget VT trúng thầu top 5', () => {
  it('import getTopQuotaItems từ @/data/antmed', () => {
    expect(pageSrc).toMatch(/getTopQuotaItems/)
    expect(pageSrc).toMatch(/from '@\/data\/antmed'/)
  })

  it('import + render AntmedTopQuotaItemsCard', () => {
    expect(pageSrc).toMatch(/AntmedTopQuotaItemsCard/)
    expect(pageSrc).toMatch(/<AntmedTopQuotaItemsCard/)
  })

  it('đọc r.data.data cho list (KHÔNG r.data trực tiếp), + total_count', () => {
    expect(pageSrc).toMatch(/topQuota\.data\?\.data/)
    expect(pageSrc).toMatch(/topQuota\.data\?\.total_count/)
  })

  it('fetch ĐỘC LẬP (auto:true) — tách biệt getContractHealth', () => {
    expect(pageSrc).toMatch(/getTopQuotaItems\(\{[\s\S]*?auto:\s*true/)
    // Vẫn còn resource Sức khỏe HĐ riêng (2 fetch độc lập)
    expect(pageSrc).toMatch(/getContractHealth\(/)
  })

  it('nút Thử lại reload card này (topQuota.reload)', () => {
    expect(pageSrc).toMatch(/topQuota\.reload\(\)/)
    expect(pageSrc).toMatch(/@retry=/)
  })

  it('KHÔNG tự tính ngưỡng quota ở FE (>=70/>=90/>=95 literal) trong page', () => {
    expect(pageSrc).not.toMatch(/>=\s*70|>=\s*90|>=\s*95/)
  })
})

// ── AntmedTopQuotaItemsCard.vue — bảng 4 cột + bar màu + tri-branch + a11y ────
describe('M02-5 AntmedTopQuotaItemsCard — bảng 4 cột, bar màu, tri-branch', () => {
  it("tiêu đề 'Danh mục VT trúng thầu — top 5'", () => {
    expect(cardSrc).toMatch(/Danh mục VT trúng thầu — top 5/)
  })

  it('4 cột SKU | Quota | Đã xuất | %', () => {
    expect(cardSrc).toMatch(/SKU/)
    expect(cardSrc).toMatch(/Quota/)
    expect(cardSrc).toMatch(/Đã xuất/)
    // cột % (header literal '%')
    expect(cardSrc).toMatch(/__\('%'\)/)
  })

  it('SKU = item (mã) + item_name (tên phụ)', () => {
    expect(cardSrc).toMatch(/row\.item\b/)
    expect(cardSrc).toMatch(/row\.item_name/)
  })

  it('cột Quota = quota_qty, Đã xuất = used_qty', () => {
    expect(cardSrc).toMatch(/row\.quota_qty/)
    expect(cardSrc).toMatch(/row\.used_qty/)
  })

  it('dùng healthBarClass cho bar (map cờ BE, KHÔNG tính ngưỡng)', () => {
    expect(cardSrc).toMatch(/healthBarClass/)
    expect(cardSrc).toMatch(/:class="healthBarClass\(row\.health_color\)"/)
    expect(cardSrc).not.toMatch(/>=\s*70|>=\s*90|>=\s*95/)
  })

  it('bar dùng used_pct (KHÔNG tự tính lại từ qty)', () => {
    expect(cardSrc).toMatch(/clampPct\(row\.used_pct\)/)
    expect(cardSrc).toMatch(/pctLabel\(row\.used_pct\)/)
  })

  it('tri-branch: loading / error(Thử lại) / empty (Chưa có vật tư trúng thầu)', () => {
    expect(cardSrc).toMatch(/v-if="loading"/)
    expect(cardSrc).toMatch(/v-else-if="error"/)
    expect(cardSrc).toMatch(/Thử lại/)
    expect(cardSrc).toMatch(/Chưa có vật tư trúng thầu/)
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

// ── Helper thuần healthBarClass — 3 nhánh map health_color BE → class fill ────
describe('M02-5 healthBarClass — 3 nhánh màu (green/orange/red)', () => {
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
