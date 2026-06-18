import { readFileSync } from 'fs'
import path from 'path'

// Slice port FCRM→AntMed: Ghi chú + Dòng thời gian hoạt động (FCRM Note + CRM Task) gắn bản ghi
// AntMed (Hợp đồng/Bệnh viện/Phiếu giao) qua reference_doctype/docname, render bằng AmTimeline.
// Idiom: content-assert nguồn (data/component/wiring) — KHÔNG @vue/test-utils.

const srcDir = path.resolve(__dirname, '../../src')
const dataSrc = readFileSync(path.join(srcDir, 'data/antmed.js'), 'utf8')
const panelSrc = readFileSync(
  path.join(srcDir, 'components/Antmed/AntmedActivityPanel.vue'),
  'utf8',
)
const contractDetailSrc = readFileSync(
  path.join(srcDir, 'pages/AntmedContractDetail.vue'),
  'utf8',
)
const hospitalDetailSrc = readFileSync(
  path.join(srcDir, 'pages/AntmedHospitalDetail.vue'),
  'utf8',
)
const deliveryDetailSrc = readFileSync(
  path.join(srcDir, 'pages/AntmedDeliveryDetail.vue'),
  'utf8',
)

describe('Activity — resources getActivity (GET) + addNote (POST)', () => {
  it('getActivity → notes.activity, method GET', () => {
    const idx = dataSrc.indexOf('export function getActivity')
    expect(idx).toBeGreaterThan(-1)
    const block = dataSrc.slice(idx, idx + 420)
    expect(block).toMatch(
      /url:\s*['"]antmed_crm\.api\.antmed\.notes\.activity['"]/,
    )
    expect(block).toMatch(/method:\s*['"]GET['"]/)
  })
  it('addNote → notes.add_note, method POST (mutation)', () => {
    const idx = dataSrc.indexOf('export function addNote')
    expect(idx).toBeGreaterThan(-1)
    const block = dataSrc.slice(idx, idx + 320)
    expect(block).toMatch(
      /url:\s*['"]antmed_crm\.api\.antmed\.notes\.add_note['"]/,
    )
    expect(block).toMatch(/method:\s*['"]POST['"]/)
  })
})

describe('AntmedActivityPanel — timeline AmTimeline + thêm ghi chú + tri-branch', () => {
  it('dùng getActivity + AmTimeline + đọc board.data.events', () => {
    expect(panelSrc).toMatch(/getActivity/)
    expect(panelSrc).toMatch(/AmTimeline/)
    expect(panelSrc).toMatch(/board\.data\?\.events/)
  })
  it('có form thêm ghi chú (addNote.submit) + props reference', () => {
    expect(panelSrc).toMatch(/addNote/)
    expect(panelSrc).toMatch(/\.submit\(/)
    expect(panelSrc).toMatch(/referenceDoctype/)
    expect(panelSrc).toMatch(/referenceDocname/)
  })
  it('tri-branch loading/error/empty + KHÔNG dính bug __ placeholder thiếu replace[]', () => {
    expect(panelSrc).toMatch(/board\.loading/)
    expect(panelSrc).toMatch(/board\.error/)
    expect(panelSrc).not.toMatch(/__\(\s*['"][^'"]*\{\d+\}[^'"]*['"]\s*\)/)
  })
})

describe('Wiring — panel hoạt động gắn lên HĐ + Bệnh viện + Phiếu giao', () => {
  const IMPORT =
    /import AntmedActivityPanel from '@\/components\/Antmed\/AntmedActivityPanel\.vue'/
  it('AntmedContractDetail — reference-doctype="AntMed Contract"', () => {
    expect(contractDetailSrc).toMatch(IMPORT)
    expect(contractDetailSrc).toMatch(/<AntmedActivityPanel/)
    expect(contractDetailSrc).toMatch(/reference-doctype="AntMed Contract"/)
  })
  it('AntmedHospitalDetail — reference-doctype="AntMed Hospital"', () => {
    expect(hospitalDetailSrc).toMatch(IMPORT)
    expect(hospitalDetailSrc).toMatch(/<AntmedActivityPanel/)
    expect(hospitalDetailSrc).toMatch(/reference-doctype="AntMed Hospital"/)
  })
  it('AntmedDeliveryDetail — reference-doctype="AntMed Delivery"', () => {
    expect(deliveryDetailSrc).toMatch(IMPORT)
    expect(deliveryDetailSrc).toMatch(/<AntmedActivityPanel/)
    expect(deliveryDetailSrc).toMatch(/reference-doctype="AntMed Delivery"/)
  })
})
