import { readFileSync } from 'fs'
import path from 'path'
import {
  funnelBarWidth,
  funnelBarClass,
  FUNNEL_BAR_MIN_FLOOR,
} from '../../src/utils/antmedUi'

// M08-S3 FE — màn Lead pipeline (AntmedLeads.vue): phễu Pipeline gói thầu (lead_funnel) +
// drawer chi tiết (get_lead) + nút "Qualify → Tạo gói thầu" (convert_lead_to_tender).
// Idiom dự án (antmedTenderPipeline): test tầng thuần (funnelBarWidth — antmedUi.js KHÔNG import
// frappe-ui) + content-assert nguồn (grep) cho url & wiring & render (data/antmed.js KÉO frappe-ui
// nên vitest KHÔNG load được module; dự án KHÔNG dùng @vue/test-utils).

const srcDir = path.resolve(__dirname, '../../src')
const read = (rel) => readFileSync(path.join(srcDir, rel), 'utf8')

const dataSrc = read('data/antmed.js')
const pageSrc = read('pages/AntmedLeads.vue')

// ── (1) resource factory — 3 url khớp EXACT whitelist BE + method đúng ────────────────────────
describe('data/antmed.js — resource Lead pipeline (url + method khớp BE whitelist)', () => {
  it("getLeadFunnel → url 'antmed_crm.api.antmed.pipeline.lead_funnel', method GET", () => {
    const m = dataSrc.match(/export function getLeadFunnel[\s\S]*?\n}/)
    expect(m).toBeTruthy()
    expect(m[0]).toMatch(
      /url:\s*['"]antmed_crm\.api\.antmed\.pipeline\.lead_funnel['"]/,
    )
    expect(m[0]).toMatch(/method:\s*['"]GET['"]/)
  })

  it("getLead → url 'antmed_crm.api.antmed.pipeline.get_lead', method GET, nhận params", () => {
    const m = dataSrc.match(/export function getLead\b[\s\S]*?\n}/)
    expect(m).toBeTruthy()
    expect(m[0]).toMatch(
      /url:\s*['"]antmed_crm\.api\.antmed\.pipeline\.get_lead['"]/,
    )
    expect(m[0]).toMatch(/method:\s*['"]GET['"]/)
    expect(m[0]).toMatch(/params/)
  })

  it("convertLeadToTender → url 'antmed_crm.api.antmed.pipeline.convert_lead_to_tender', method POST", () => {
    // Hàm này có destructure nhiều dòng ({ params, auto, onSuccess, onError }) → bắt từ tên hàm
    // tới ngoặc đóng createResource (})\n}) thay vì '\n}' đầu tiên (sẽ trúng } của destructure).
    const m = dataSrc.match(
      /export function convertLeadToTender[\s\S]*?createResource\([\s\S]*?\)\n}/,
    )
    expect(m).toBeTruthy()
    expect(m[0]).toMatch(
      /url:\s*['"]antmed_crm\.api\.antmed\.pipeline\.convert_lead_to_tender['"]/,
    )
    expect(m[0]).toMatch(/method:\s*['"]POST['"]/)
    expect(m[0]).toMatch(/onSuccess/)
  })

  it('KHÔNG dùng url legacy crm.api.* / app riêng cho 3 hàm này', () => {
    const slice = dataSrc.slice(
      dataSrc.indexOf('export function getLeadFunnel'),
    )
    expect(slice).not.toMatch(/url:\s*['"]crm\.api\./)
  })
})

// ── (2) helper thuần funnelBarWidth — phễu 5 tầng (PURE, tái dùng từ M08-1) ───────────────────
describe('funnelBarWidth — bề rộng bar phễu Lead pipeline (count/max + min-floor)', () => {
  it('tầng đỉnh (count==max) → 100%', () => {
    expect(funnelBarWidth(65, 65)).toBe(100)
  })

  it('count==0 (max>0) → MIN-FLOOR (tầng rỗng vẫn đọc được nhãn)', () => {
    expect(funnelBarWidth(0, 65)).toBe(FUNNEL_BAR_MIN_FLOOR)
  })

  it('mọi tầng 0 (max<=0) → 0 (KHÔNG NaN)', () => {
    expect(funnelBarWidth(0, 0)).toBe(0)
    expect(Number.isNaN(funnelBarWidth(1, 0))).toBe(false)
  })

  it('funnelBarClass dải teal nhạt dần — index hợp lệ trả token teal', () => {
    expect(funnelBarClass(0)).toMatch(/bg-teal-/)
    // ngoài range vẫn an toàn (fallback teal nhạt nhất, KHÔNG undefined).
    expect(funnelBarClass(99)).toMatch(/bg-teal-/)
  })
})

// ── (3) AntmedLeads.vue — phễu header, drawer, nút qualify, a11y, grep-gate ───────────────────
describe('AntmedLeads.vue — phễu + drawer + qualify (render wiring)', () => {
  it('import + tạo 3 resource pipeline (getLeadFunnel/getLead/convertLeadToTender)', () => {
    expect(pageSrc).toMatch(/getLeadFunnel/)
    expect(pageSrc).toMatch(/getLead\b/)
    expect(pageSrc).toMatch(/convertLeadToTender/)
    expect(pageSrc).toMatch(/const funnel = getLeadFunnel/)
  })

  it('filter "Tất cả": BỎ key status (KHÔNG status:undefined → GET serialize "undefined" → 0 lead)', () => {
    // regression: `status: s || undefined` → GET gửi status="undefined" → BE lọc 0 lead.
    expect(pageSrc).not.toMatch(/status:\s*s\s*\|\|\s*undefined/)
    // s rỗng → params chỉ { page_length }; có s mới kèm status.
    expect(pageSrc).toMatch(/s\s*\?\s*\{\s*status:\s*s/)
  })

  it('phễu: đọc funnel.data.stages TRỰC TIẾP (RAW dict — KHÔNG .data.data) + tiêu đề VI', () => {
    expect(pageSrc).toMatch(/funnel\.data\?\.stages/)
    expect(pageSrc).not.toMatch(/funnel\.data\?\.data/)
    expect(pageSrc).toMatch(/Pipeline gói thầu/)
  })

  it('phễu: render s.label + s.count từ BE (KHÔNG hardcode nhãn/số mockup)', () => {
    expect(pageSrc).toMatch(/v-for=["'][^"']*\bfunnelStages\b/)
    expect(pageSrc).toMatch(/\.label/)
    expect(pageSrc).toMatch(/\.count/)
    // bar width dùng helper thuần, KHÔNG tính tay.
    expect(pageSrc).toMatch(/funnelBarWidth\(/)
    expect(pageSrc).toMatch(/funnelBarClass\(/)
  })

  it('row click → drawer get_lead (openDetail + detail.submit({ name }))', () => {
    expect(pageSrc).toMatch(/@click="openDetail\(/)
    expect(pageSrc).toMatch(/detail\.submit\(\{\s*name\s*\}\)/)
    // a11y: dòng bàn-phím-được (Enter/Space) + role button.
    expect(pageSrc).toMatch(/@keydown\.enter="openDetail/)
    expect(pageSrc).toMatch(/role="button"/)
  })

  it('drawer: hiện email_id (đúng field BE) + lead_owner_name (KHÔNG lộ email owner)', () => {
    expect(pageSrc).toMatch(/lead\.email_id/)
    expect(pageSrc).toMatch(/lead\.lead_owner_name/)
  })

  it('tender set → badge "Đã tạo gói thầu" + link /antmed/tenders/<tender>; null → nút qualify', () => {
    expect(pageSrc).toMatch(/v-if="lead\.tender"/)
    expect(pageSrc).toMatch(/Đã tạo gói thầu/)
    expect(pageSrc).toMatch(/\/antmed\/tenders\//)
    expect(pageSrc).toMatch(/Qualify → Tạo gói thầu/)
  })

  it('qualify: gửi estimated_value optional + reload funnel/detail/list khi success', () => {
    expect(pageSrc).toMatch(/estimated_value/)
    expect(pageSrc).toMatch(/funnel\.reload\(\)/)
    expect(pageSrc).toMatch(/leads\.reload\(\)/)
    // idempotent-safe: phân biệt created true/false ở toast.
    expect(pageSrc).toMatch(/data\?\.created/)
  })

  it('GREP-GATE: KHÔNG crm.api / createListResource / axios trong trang', () => {
    expect(pageSrc).not.toMatch(/crm\.api(?!\.antmed)/) // chỉ antmed_crm.api.antmed.* được phép
    expect(pageSrc).not.toMatch(/\bcreateListResource\b/)
    expect(pageSrc).not.toMatch(/\baxios\b/)
  })

  it('mọi __("…{0}…") có placeholder đều kèm mảng [args] (chống vỡ trang trắng)', () => {
    // Bắt mọi lời gọi __('...') có {0}/{1}... → phải theo sau bởi , [ (replace array).
    const calls =
      pageSrc.match(/__\(\s*['"][^'"]*\{\d+\}[^'"]*['"]\s*[^)]*\)/g) || []
    for (const c of calls) {
      expect(c).toMatch(/\{\d+\}[\s\S]*,\s*\[/)
    }
  })
})
