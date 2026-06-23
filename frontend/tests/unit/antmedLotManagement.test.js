import { readFileSync } from 'fs'
import path from 'path'
import { describe, it, expect } from 'vitest'

// M03 D3 — Truy vết lot làm giàu (phả hệ ca mổ + CO/CQ tải + SL tách kho + lưu vết) + Quản lý lot.
// Idiom content-assert nguồn (KHÔNG @vue/test-utils) — khớp antmedStockWizard.test.js.

const srcDir = path.resolve(__dirname, '../../src')
const read = (p) => readFileSync(path.join(srcDir, p), 'utf8')

const dataSrc = read('data/antmed.js')
const traceSrc = read('pages/AntmedLotTrace.vue')
const listSrc = read('pages/AntmedLotList.vue')
const routerSrc = read('router.js')
const navSrc = read('data/antmedNav.js')

describe('data/antmed.js — factory truy vết/quản lý lot (url + method khớp BE)', () => {
  const cases = [
    ['getLotGenealogy', 'antmed_crm.api.antmed.inventory.lot_genealogy', 'GET'],
    ['saveLotTrace', 'antmed_crm.api.antmed.inventory.save_lot_trace', 'POST'],
    ['listLots', 'antmed_crm.api.antmed.inventory.list_lots', 'GET'],
    ['listItems', 'antmed_crm.api.antmed.inventory.list_items', 'GET'],
    [
      'exportLotTracePdf',
      'antmed_crm.api.antmed.inventory.export_lot_trace_pdf',
      'POST',
    ],
  ]
  it.each(cases)('%s → url %s method %s', (fn, url, method) => {
    const m = dataSrc.match(
      new RegExp(`export function ${fn}\\([\\s\\S]*?\\n}`),
    )
    expect(m, `thiếu factory ${fn}`).toBeTruthy()
    expect(m[0]).toContain(`url: '${url}'`)
    expect(m[0]).toContain(`method: '${method}'`)
  })
})

describe('AntmedLotTrace.vue — enrich phả hệ + CO/CQ tải + SL tách kho + lưu vết', () => {
  it('dùng getLotGenealogy (cây phả hệ ca mổ)', () => {
    expect(traceSrc).toMatch(/getLotGenealogy/)
    expect(traceSrc).toMatch(/genealogy\.submit\(/)
  })
  it('CO/CQ render link tải file_url', () => {
    expect(traceSrc).toMatch(/data\.co_file_url/)
    expect(traceSrc).toMatch(/data\.cq_file_url/)
  })
  it('SL còn tách theo loại kho (balance_by_warehouse_type)', () => {
    expect(traceSrc).toMatch(/balance_by_warehouse_type/)
  })
  it('nút Lưu vết (saveLotTrace) + auto-trace từ ?lot=', () => {
    expect(traceSrc).toMatch(/saveLotTrace|saveTrace\.submit/)
    expect(traceSrc).toMatch(/route\.query\.lot/)
  })
  it('hiển thị hóa đơn (einvoice) trong phả hệ', () => {
    expect(traceSrc).toMatch(/einvoice/)
  })
  it('export PDF (exportLotTracePdf) + recall toast BV ảnh hưởng', () => {
    expect(traceSrc).toMatch(/exportLotTracePdf|exportPdf\.submit/)
    expect(traceSrc).toMatch(/savedTraceName/)
    // Recall onSuccess đọc affected_hospitals + recall_notification từ response.
    expect(traceSrc).toMatch(/affected_hospitals/)
    expect(traceSrc).toMatch(/recall_notification/)
  })
  it('KHÔNG gọi crm.api / axios', () => {
    expect(traceSrc).not.toMatch(/crm\.api\./)
    expect(traceSrc).not.toMatch(/axios/)
  })
})

describe('AntmedLotList.vue — màn quản lý lô', () => {
  it('gọi list_lots + listItems', () => {
    expect(listSrc).toMatch(/listLots/)
    expect(listSrc).toMatch(/listItems/)
  })
  it('drill Truy vết → route name AntmedLotTrace với query.lot', () => {
    expect(listSrc).toMatch(/name:\s*['"]AntmedLotTrace['"]/)
    expect(listSrc).toMatch(/query:\s*\{\s*lot:/)
  })
  it('filters object JSON.stringify (recall_status)', () => {
    expect(listSrc).toMatch(/JSON\.stringify\(\{\s*recall_status/)
  })
  it('KHÔNG gọi crm.api / axios', () => {
    expect(listSrc).not.toMatch(/crm\.api\./)
    expect(listSrc).not.toMatch(/axios/)
  })
})

describe('router + nav — màn quản lý lô', () => {
  it('router có route AntmedLotList /antmed/warehouse/lots', () => {
    expect(routerSrc).toMatch(/name:\s*['"]AntmedLotList['"]/)
    expect(routerSrc).toMatch(/\/antmed\/warehouse\/lots/)
  })
  it('nav warehouse có wh-lots trỏ /antmed/warehouse/lots', () => {
    expect(navSrc).toMatch(/wh-lots/)
    expect(navSrc).toMatch(/\/antmed\/warehouse\/lots/)
  })
})
