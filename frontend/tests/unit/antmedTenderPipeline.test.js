import { existsSync, readFileSync } from 'fs'
import path from 'path'
import { funnelBarWidth, FUNNEL_BAR_MIN_FLOOR } from '../../src/utils/antmedUi'

// M08-1 — widget "Pipeline gói thầu" (CEO A1 Hàng 3, funnel 5 tầng số THẬT từ CRM Lead+Deal).
// Idiom dự án (antmedDashboard/antmedExpiryAlerts): test tầng thuần (funnelBarWidth — antmedUi.js
// KHÔNG import frappe-ui → import trực tiếp) + content-assert nguồn (grep) cho url & wiring & render
// (data/antmed.js KÉO frappe-ui nên vitest KHÔNG load được; KHÔNG @vue/test-utils trong dự án).

const srcDir = path.resolve(__dirname, '../../src')
const read = (rel) => readFileSync(path.join(srcDir, rel), 'utf8')

const dataSrc = read('data/antmed.js')
const homeSrc = read('pages/AntmedHome.vue')
const cardPath = path.join(srcDir, 'components/Antmed/AntmedTenderFunnelCard.vue')
const cardSrc = read('components/Antmed/AntmedTenderFunnelCard.vue')

// ── (1) helper thuần funnelBarWidth — tỉ lệ count/max + min-floor (PURE) ─────────────────────
describe('funnelBarWidth — bề rộng bar funnel theo tỉ lệ count/max + min-floor', () => {
  it('count == max → 100 (tầng đầu / lớn nhất chiếm full)', () => {
    expect(funnelBarWidth(38, 38)).toBe(100)
    expect(funnelBarWidth(6, 6)).toBe(100)
  })

  it('tỉ lệ đúng giữa 0 và 100 (không min-floor khi count > 0 đủ lớn)', () => {
    // 24/38 ≈ 63.16 — phải phản ánh tỉ lệ thật (không phải 100, không phải floor).
    const w = funnelBarWidth(24, 38)
    expect(w).toBeGreaterThan(60)
    expect(w).toBeLessThan(70)
    // nửa max → ~50.
    expect(funnelBarWidth(50, 100)).toBe(50)
  })

  it('count == 0 (max>0) → trả MIN-FLOOR (đọc được nhãn, KHÔNG bar 0px biến mất)', () => {
    const w = funnelBarWidth(0, 38)
    expect(w).toBeGreaterThan(0)
    // floor = FUNNEL_BAR_MIN_FLOOR — đủ để hiển thị nhãn tầng rỗng.
    expect(w).toBe(FUNNEL_BAR_MIN_FLOOR)
  })

  it('max <= 0 (mọi tầng count 0) → 0 (KHÔNG NaN, KHÔNG ZeroDivisionError)', () => {
    expect(funnelBarWidth(0, 0)).toBe(0)
    expect(funnelBarWidth(0, -1)).toBe(0)
    expect(Number.isNaN(funnelBarWidth(5, 0))).toBe(false)
    expect(funnelBarWidth(5, 0)).toBe(0)
  })

  it('clamp KHÔNG vượt 100 (count >= max → 100)', () => {
    expect(funnelBarWidth(50, 38)).toBe(100)
  })

  it('count nhỏ vẫn >= min-floor (không nhỏ hơn floor để đọc được nhãn)', () => {
    const tiny = funnelBarWidth(1, 1000)
    expect(tiny).toBeGreaterThanOrEqual(FUNNEL_BAR_MIN_FLOOR)
    expect(tiny).toBeGreaterThanOrEqual(funnelBarWidth(0, 1000))
  })
})

// ── (2) resource getTenderPipeline — url đúng + method GET ───────────────────────────────────
describe('getTenderPipeline — resource wiring (url + method GET)', () => {
  it("url == 'antmed_crm.api.antmed.dashboard.tender_pipeline'", () => {
    expect(dataSrc).toMatch(
      /url:\s*['"]antmed_crm\.api\.antmed\.dashboard\.tender_pipeline['"]/,
    )
    expect(dataSrc).toMatch(/export function getTenderPipeline/)
  })

  it("method: 'GET' (endpoint không params → mặc định POST sẽ 403 GET-only)", () => {
    // Trích đoạn hàm getTenderPipeline để chắc method GET nằm TRONG nó (không lẫn hàm khác).
    const m = dataSrc.match(/export function getTenderPipeline[\s\S]*?\n}/)
    expect(m).toBeTruthy()
    expect(m[0]).toMatch(/method:\s*['"]GET['"]/)
    expect(m[0]).toMatch(/tender_pipeline/)
  })
})

// ── (3) AntmedTenderFunnelCard — 5 tầng nhãn VI + count, tri-branch, empty ────────────────────
describe('AntmedTenderFunnelCard — funnel 5 tầng real-data', () => {
  it('component tồn tại', () => {
    expect(existsSync(cardPath)).toBe(true)
  })

  it('tiêu đề "Pipeline gói thầu"', () => {
    expect(cardSrc).toMatch(/Pipeline gói thầu/)
  })

  it('render nhãn VI 5 tầng từ stages (KHÔNG hardcode mock số) + count', () => {
    // nhãn đến từ s.label của BE (render thẳng) — component lặp v-for stages.
    expect(cardSrc).toMatch(/v-for=["'][^"']*\bstages\b/)
    expect(cardSrc).toMatch(/\.label/)
    expect(cardSrc).toMatch(/\.count/)
    // KHÔNG hardcode số mockup (38/24/18/11/6) trong UI.
    expect(cardSrc).not.toMatch(/—\s*38|Lead\s*—\s*38/)
    expect(cardSrc).not.toMatch(/\b24\b.*\b18\b.*\b11\b/)
  })

  it('bar width = funnelBarWidth(count,max) — tái dùng helper thuần, KHÔNG tính tay trong template', () => {
    expect(cardSrc).toMatch(/funnelBarWidth/)
  })

  it('dùng token màu brand teal nhạt dần (funnelBarClass → dải teal), KHÔNG hex thô lạ', () => {
    // brand token reuse qua helper funnelBarClass (TENDER_STAGE_THEME = bg-teal-* nhạt dần),
    // KHÔNG nhúng hex thô tuỳ tiện trong component.
    expect(cardSrc).toMatch(/funnelBarClass/)
  })

  it('tri-branch loading "Đang tải pipeline…"', () => {
    expect(cardSrc).toMatch(/v-if="loading"/)
    expect(cardSrc).toMatch(/Đang tải pipeline…/)
  })

  it('tri-branch error: Badge đỏ + nút "Thử lại" phát @retry', () => {
    expect(cardSrc).toMatch(/v-else-if="error"/)
    expect(cardSrc).toMatch(/theme="red"/)
    expect(cardSrc).toMatch(/Thử lại/)
    expect(cardSrc).toMatch(/\$emit\(['"]retry['"]\)/)
  })

  it('empty-state khi total=0: "Chưa có dữ liệu pipeline" (KHÔNG vẽ funnel rỗng méo)', () => {
    expect(cardSrc).toMatch(/Chưa có dữ liệu pipeline/)
    // empty quyết theo total (0) — không render funnel khi total falsy.
    expect(cardSrc).toMatch(/total/)
  })

  it('props presentational: stages + total + loading + error (KHÔNG tự fetch trong card)', () => {
    expect(cardSrc).toMatch(/stages:/)
    expect(cardSrc).toMatch(/total:/)
    expect(cardSrc).toMatch(/loading:/)
    expect(cardSrc).toMatch(/error:/)
    expect(cardSrc).not.toMatch(/createResource|createListResource/)
  })
})

// ── (4) AntmedHome — thay placeholder bằng card real-data, đọc .data.stages TRỰC TIẾP ─────────
describe('AntmedHome — wire tender_pipeline thay placeholder Hàng 3', () => {
  it('import + tạo resource getTenderPipeline (auto)', () => {
    expect(homeSrc).toMatch(/getTenderPipeline/)
    expect(homeSrc).toMatch(/const tenderPipeline = getTenderPipeline/)
  })

  it('đọc tenderPipeline.data.stages TRỰC TIẾP (KHÔNG .data.data — RAW dict thường)', () => {
    expect(homeSrc).toMatch(/tenderPipeline\.data\?\.stages/)
    expect(homeSrc).toMatch(/tenderPipeline\.data\?\.total/)
    // KHÔNG .data.data (list-wrap LL) cho dict thường.
    expect(homeSrc).not.toMatch(/tenderPipeline\.data\?\.data/)
  })

  it('dùng AntmedTenderFunnelCard + bind loading/error/@retry reload', () => {
    expect(homeSrc).toMatch(/AntmedTenderFunnelCard/)
    expect(homeSrc).toMatch(/tenderPipeline\.loading/)
    expect(homeSrc).toMatch(/tenderPipeline\.error/)
    expect(homeSrc).toMatch(/tenderPipeline\.reload\(\)/)
  })

  it('KHÔNG còn AntmedPlaceholderPanel "Pipeline gói thầu" (đã thay bằng card số thật)', () => {
    // dấu vân tay placeholder cũ Hàng 3: hint 'Sắp có (cần module Pipeline gói thầu)'.
    expect(homeSrc).not.toMatch(/Sắp có \(cần module Pipeline gói thầu\)/)
    // title 'Pipeline gói thầu' KHÔNG còn truyền vào PlaceholderPanel.
    expect(homeSrc).not.toMatch(/PlaceholderPanel\s+:title="__\('Pipeline gói thầu'\)"/)
  })

  it('KHÔNG mock / createListResource trong AntmedHome cho pipeline', () => {
    expect(homeSrc).not.toMatch(/antmedMock/)
    expect(homeSrc).not.toMatch(/createListResource/)
  })
})
