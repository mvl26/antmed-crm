import { readFileSync } from 'fs'
import path from 'path'

// B1 — Bảng điều phối CA GIAO PHÒNG MỔ (Trưởng phòng KD, /antmed/sales/dispatch).
// Kanban AntMed Delivery theo trạng thái → gom 4 cột B1 (Mới tiếp nhận/Đã gán NV/Đang giao/
// Đã bàn giao). Đổi concept pipeline→delivery cho khớp mockup B1; pipeline cũ dời /antmed/sales/pipeline.
// Idiom: content-assert nguồn (router/page/data) — KHÔNG @vue/test-utils.

const srcDir = path.resolve(__dirname, '../../src')
const routerSrc = readFileSync(path.join(srcDir, 'router.js'), 'utf8')
const dataSrc = readFileSync(path.join(srcDir, 'data/antmed.js'), 'utf8')
const pageSrc = readFileSync(
  path.join(srcDir, 'pages/AntmedDeliveryDispatch.vue'),
  'utf8',
)

describe('B1 route — /antmed/sales/dispatch = delivery board, pipeline dời /sales/pipeline', () => {
  it('/antmed/sales/dispatch nạp AntmedDeliveryDispatch.vue (B1 delivery)', () => {
    expect(routerSrc).toMatch(
      /import\(['"]@\/pages\/AntmedDeliveryDispatch\.vue['"]\)/,
    )
    const idx = routerSrc.indexOf("'/antmed/sales/dispatch'")
    expect(idx).toBeGreaterThan(-1)
    // trong block route /antmed/sales/dispatch phải trỏ AntmedDeliveryDispatch.vue
    const block = routerSrc.slice(idx, idx + 260)
    expect(block).toMatch(/AntmedDeliveryDispatch\.vue/)
  })
  it('pipeline cũ (AntmedDispatch.vue) còn truy cập tại /antmed/sales/pipeline', () => {
    expect(routerSrc).toMatch(/path:\s*['"]\/antmed\/sales\/pipeline['"]/)
    expect(routerSrc).toMatch(/import\(['"]@\/pages\/AntmedDispatch\.vue['"]\)/)
  })
})

describe('B1 resource — getDeliveryDispatchBoard (GET, đúng endpoint)', () => {
  it('data/antmed.js có getDeliveryDispatchBoard → delivery.dispatch_board, method GET', () => {
    expect(dataSrc).toMatch(/export function getDeliveryDispatchBoard/)
    const idx = dataSrc.indexOf('getDeliveryDispatchBoard')
    const block = dataSrc.slice(idx, idx + 320)
    expect(block).toMatch(
      /url:\s*['"]antmed_crm\.api\.antmed\.delivery\.dispatch_board['"]/,
    )
    expect(block).toMatch(/method:\s*['"]GET['"]/)
  })
})

describe('B1 page — kanban 4 lane + đọc lanes/totals + i18n đúng dạng', () => {
  it('đọc board.data.lanes + board.data.totals (RAW dict, KHÔNG .data.data)', () => {
    expect(pageSrc).toMatch(/getDeliveryDispatchBoard/)
    expect(pageSrc).toMatch(/board\.data\?\.lanes/)
    expect(pageSrc).toMatch(/board\.data\?\.totals/)
    expect(pageSrc).not.toMatch(/\.data\.data/)
  })
  it('render lane.cards + field B1 (hospital_name, doctor_name, sku_count, urgency)', () => {
    expect(pageSrc).toMatch(/v-for="lane in lanes"/)
    expect(pageSrc).toMatch(/v-for="card in lane\.cards"/)
    for (const f of [
      'hospital_name',
      'doctor_name',
      'sku_count',
      'assigned_employee_name',
      'surgery_datetime',
      'urgency',
    ]) {
      expect(pageSrc).toContain(f)
    }
  })
  it('tri-branch loading/error/empty + KHÔNG dính bug __ placeholder thiếu replace[]', () => {
    expect(pageSrc).toMatch(/board\.loading/)
    expect(pageSrc).toMatch(/board\.error/)
    expect(pageSrc).toMatch(/hasCards/)
    // __('...{N}...') PHẢI kèm mảng replace (tránh crash translation đã gặp ở pipeline cũ)
    expect(pageSrc).not.toMatch(/__\(\s*['"][^'"]*\{\d+\}[^'"]*['"]\s*\)/)
  })
})
