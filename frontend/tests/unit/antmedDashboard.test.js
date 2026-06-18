import { readFileSync } from 'fs'
import path from 'path'

// TDD-FE (M11 Dashboard FE Slice 2): rewrite AntmedHome.vue health-widget → layout A1
// (KPI row 4 card → row 12-col Top10 BV → row 2-col Pipeline/Cảnh báo, mockup A1
// dòng 252–269). 2 KPI THẬT (Số bệnh viện / Số bác sỹ) từ overview(); card chưa-nguồn
// = empty-state "Chưa có dữ liệu"/"Sắp có"; tri-branch loading/error/data; KHÔNG bịa số.
//
// Idiom test = content-assert nguồn (file grep) — đồng quy ước antmedShell/antmedCustomer
// (dự án KHÔNG cài @vue/test-utils). Acceptance (a)-(d) map xuống các describe dưới.

const srcDir = path.resolve(__dirname, '../../src')
const read = (rel) => readFileSync(path.join(srcDir, rel), 'utf8')

const homeSrc = read('pages/AntmedHome.vue')
const dataSrc = read('data/antmed.js')
const kpiCardSrc = read('components/Antmed/AntmedKpiCard.vue')
const panelSrc = read('components/Antmed/AntmedPlaceholderPanel.vue')
const ringSrc = read('components/Antmed/AntmedQuotaRing.vue')
const alertsSrc = read('components/Antmed/AntmedAlertsPanel.vue')

// ── (a) resource overview + render 2 KPI value THẬT (mock {hospital_count:7,doctor_count:12}) ──
describe('M11 FE Slice 2 — resource overview + 2 KPI thật', () => {
  it('data/antmed.js expose resource url antmed_crm.api.antmed.dashboard.overview', () => {
    expect(dataSrc).toMatch(/url:\s*['"]antmed_crm\.api\.antmed\.dashboard\.overview['"]/)
    expect(dataSrc).toMatch(/getDashboardOverview/)
  })

  it('AntmedHome bind overview.data.hospital_count + doctor_count vào 2 thẻ KPI (số THẬT)', () => {
    expect(homeSrc).toMatch(/getDashboardOverview/)
    // 2 KPI thật bind trực tiếp data endpoint (đọc r.data.* — KHÔNG .data.data, không bọc)
    expect(homeSrc).toMatch(/overview\.data\?\.hospital_count/)
    expect(homeSrc).toMatch(/overview\.data\?\.doctor_count/)
    expect(homeSrc).toMatch(/Số bệnh viện/)
    expect(homeSrc).toMatch(/Số bác sỹ/)
  })

  it('AntmedKpiCard render value THẬT (0 KHÔNG bị nhầm thành placeholder)', () => {
    // displayValue chỉ rơi về "—" khi null/undefined; 0 là số hợp lệ → render '0'.
    expect(kpiCardSrc).toMatch(/value\s*===\s*null/)
    expect(kpiCardSrc).toMatch(/=== undefined/)
    // KHÔNG dùng falsy-check (!props.value) — sẽ nuốt mất 0.
    expect(kpiCardSrc).not.toMatch(/!\s*props\.value/)
  })
})

// ── (b) card chưa-nguồn render "Chưa có dữ liệu"/"Sắp có" + KHÔNG bịa số mockup ──
describe('M11 FE Slice 2 — empty-state trung thực + KHÔNG bịa số', () => {
  it('AntmedKpiCard empty=true → render "Chưa có dữ liệu" (KHÔNG value)', () => {
    expect(kpiCardSrc).toMatch(/v-if="empty"/)
    expect(kpiCardSrc).toMatch(/Chưa có dữ liệu/)
    expect(kpiCardSrc).toMatch(/Sắp có/)
  })

  it('AntmedPlaceholderPanel render "Chưa có dữ liệu" / "Sắp có" cho panel lớn', () => {
    expect(panelSrc).toMatch(/Chưa có dữ liệu/)
    expect(panelSrc).toMatch(/Sắp có/)
  })

  it('AntmedHome render card chưa-nguồn còn lại (Doanh thu/SLA/Bộ DC) qua prop empty', () => {
    // M08-1: Pipeline gói thầu KHÔNG còn placeholder (đã thay bằng AntmedTenderFunnelCard số thật).
    // Còn lại Doanh thu / SLA / Bộ DC VẪN placeholder (chưa có module nguồn) — dùng KpiCard empty.
    expect(homeSrc).toMatch(/Doanh thu tháng/)
    expect(homeSrc).toMatch(/Bộ dụng cụ lưu hành|Bộ DC/)
    expect(homeSrc).toMatch(/Top 10 [Bb]ệnh viện/)
    // card chưa-nguồn dùng prop empty trên AntmedKpiCard.
    expect(homeSrc).toMatch(/empty/)
  })

  it('TUYỆT ĐỐI KHÔNG hardcode số mockup giả (12,8 / 78% / 94,2 / Bạch Mai / Lead — 38 / Chợ Rẫy)', () => {
    expect(homeSrc).not.toMatch(/12,8/)
    expect(homeSrc).not.toMatch(/78%/)
    expect(homeSrc).not.toMatch(/94,2/)
    expect(homeSrc).not.toMatch(/Bạch Mai/)
    expect(homeSrc).not.toMatch(/Lead\s*—\s*38/)
    expect(homeSrc).not.toMatch(/Chợ Rẫy/)
  })
})

// ── (c) tri-branch loading/error/data: error = Badge đỏ + nút Thử lại reload + toast ──
describe('M11 FE Slice 2 — tri-branch loading/error/data', () => {
  it('error branch: Badge theme="red" + nút "Thử lại" gọi overview.reload() + toast.error fallback VN', () => {
    expect(homeSrc).toMatch(/v-else-if="overview\.error"/)
    expect(homeSrc).toMatch(/theme="red"/)
    expect(homeSrc).toMatch(/Thử lại/)
    expect(homeSrc).toMatch(/overview\.reload\(\)/)
    expect(homeSrc).toMatch(/toast\.error/)
    expect(homeSrc).toMatch(/err\.messages\?\.\[0\]/)
  })

  it('loading branch dùng LoadingIndicator + overview.loading', () => {
    expect(homeSrc).toMatch(/v-if="overview\.loading"/)
    expect(homeSrc).toMatch(/LoadingIndicator/)
  })

  it('data branch render KPI (v-else sau loading/error)', () => {
    expect(homeSrc).toMatch(/<template v-else>/)
    expect(homeSrc).toMatch(/AntmedKpiCard/)
  })
})

// ── (d) AntmedKpiCard component wiring (props empty/value/label) ──
describe('M11 FE Slice 2 — AntmedKpiCard props', () => {
  it('AntmedKpiCard có prop label (required) + value + empty', () => {
    expect(kpiCardSrc).toMatch(/label:\s*\{\s*type:\s*String,\s*required:\s*true/)
    expect(kpiCardSrc).toMatch(/value:/)
    expect(kpiCardSrc).toMatch(/empty:\s*\{\s*type:\s*Boolean/)
  })

  it('AntmedHome import + dùng AntmedKpiCard', () => {
    expect(homeSrc).toMatch(/import AntmedKpiCard/)
    expect(homeSrc).toMatch(/<AntmedKpiCard/)
  })
})

// ════════════════════════════════════════════════════════════════════════════
// M11 Slice M11-3 — Quota đã dùng (ring) + ⚠ Cảnh báo điều hành (alerts pill)
// thay 2 placeholder 'Sắp có' bằng số THẬT qua quota_summary.
// ════════════════════════════════════════════════════════════════════════════

describe('M11-3 — resource quota_summary wiring', () => {
  it('data/antmed.js expose getQuotaSummary url antmed_crm.api.antmed.dashboard.quota_summary', () => {
    expect(dataSrc).toMatch(
      /url:\s*['"]antmed_crm\.api\.antmed\.dashboard\.quota_summary['"]/,
    )
    expect(dataSrc).toMatch(/getQuotaSummary/)
  })

  it('AntmedHome import + tạo resource quota_summary (auto) + toast.error fallback VN', () => {
    expect(homeSrc).toMatch(/getQuotaSummary/)
    expect(homeSrc).toMatch(/const quotaSummary = getQuotaSummary/)
    expect(homeSrc).toMatch(/toast\.error/)
  })
})

describe('M11-3 — KPI "Quota đã dùng" = ring % thật (bỏ placeholder "Sắp có")', () => {
  it('AntmedHome bind avg_quota_used_pct + contracts_over_90_count vào AntmedQuotaRing (đọc .data.* trực tiếp)', () => {
    expect(homeSrc).toMatch(/AntmedQuotaRing/)
    expect(homeSrc).toMatch(/quotaSummary\.data\?\.avg_quota_used_pct/)
    expect(homeSrc).toMatch(/quotaSummary\.data\?\.contracts_over_90_count/)
  })

  it('KHÔNG còn placeholder "Sắp có (cần module Hợp đồng & Quota)" cho card Quota đã dùng', () => {
    expect(homeSrc).not.toMatch(/Sắp có \(cần module Hợp đồng & Quota\)/)
  })

  it('AntmedQuotaRing: ring conic-gradient + dòng phụ "N HĐ > 90%" + 0 KHÔNG ra placeholder', () => {
    expect(ringSrc).toMatch(/quotaRingStyle|conic-gradient/)
    expect(ringSrc).toMatch(/HĐ > 90%/)
    // 0 là số THẬT (chỉ null/undefined → '—') — kiểm null/undefined TƯỜNG MINH (=== hoặc !==),
    // KHÔNG falsy-check (!props.avgPct) sẽ nuốt mất 0.
    expect(ringSrc).toMatch(/(===|!==)\s*null/)
    expect(ringSrc).toMatch(/(===|!==)\s*undefined/)
    expect(ringSrc).not.toMatch(/!\s*props\.avgPct\b/)
  })
})

describe('M11-3 — panel "⚠ Cảnh báo điều hành" = alerts pill thật (bỏ placeholder)', () => {
  it('AntmedHome dùng AntmedAlertsPanel + bind alerts/loading/error + @retry reload', () => {
    expect(homeSrc).toMatch(/AntmedAlertsPanel/)
    expect(homeSrc).toMatch(/quotaSummary\.data\?\.alerts/)
    expect(homeSrc).toMatch(/quotaSummary\.loading/)
    expect(homeSrc).toMatch(/quotaSummary\.error/)
    expect(homeSrc).toMatch(/quotaSummary\.reload\(\)/)
  })

  it('AntmedHome KHÔNG còn placeholder "Cảnh báo điều hành" (đã thay bằng AntmedAlertsPanel số thật)', () => {
    // placeholder cũ: <AntmedPlaceholderPanel :title="...Cảnh báo điều hành..." :hint="Sắp có ..." />.
    // hint string là dấu vân tay duy nhất của placeholder cũ → phải biến mất.
    expect(homeSrc).not.toMatch(/Sắp có \(cần module Công nợ \/ Bộ dụng cụ\)/)
    // title 'Cảnh báo điều hành' KHÔNG còn truyền vào PlaceholderPanel (chuyển sang AntmedAlertsPanel).
    expect(homeSrc).not.toMatch(/PlaceholderPanel\s+:title="__\('Cảnh báo điều hành'\)"/)
  })

  it('AntmedAlertsPanel: tri-branch loading/error(Thử lại)/empty "Không có cảnh báo" + render label', () => {
    expect(alertsSrc).toMatch(/⚠ Cảnh báo điều hành/)
    expect(alertsSrc).toMatch(/v-if="loading"/)
    expect(alertsSrc).toMatch(/v-else-if="error"/)
    expect(alertsSrc).toMatch(/Thử lại/)
    expect(alertsSrc).toMatch(/Không có cảnh báo/)
    // render label VI từ BE + style theo severity qua helper alertClass (SSoT mockup A1).
    expect(alertsSrc).toMatch(/a\.label/)
    expect(alertsSrc).toMatch(/alertClass\(a\.severity\)/)
  })
})

// ── grep gate: di sản stack cũ = 0 + KHÔNG còn health-widget cũ ──
describe('M11 FE Slice 2 — grep gate', () => {
  const files = [homeSrc, dataSrc, kpiCardSrc, panelSrc, ringSrc, alertsSrc]
  it('KHÔNG axios / @tanstack/vue-query / @/api / frappe.client.*', () => {
    for (const src of files) {
      expect(src).not.toMatch(/axios/)
      expect(src).not.toMatch(/@tanstack\/vue-query/)
      expect(src).not.toMatch(/from ['"]@\/api\//)
      expect(src).not.toMatch(/frappe\.client\.(get_value|get_list)/)
    }
  })

  it('AntmedHome KHÔNG còn gọi health.ping (đã rewrite từ health-widget → A1)', () => {
    expect(homeSrc).not.toMatch(/health\.ping/)
  })
})
