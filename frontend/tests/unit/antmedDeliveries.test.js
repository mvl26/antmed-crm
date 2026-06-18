import { readFileSync } from 'fs'
import path from 'path'
import { describe, it, expect } from 'vitest'
import { ANTMED_NAV, ANTMED_SECTIONS, isNavActive } from '../../src/data/antmedNav'

// M04 Slice S1 — màn DANH SÁCH + CHI TIẾT phiếu Giao phòng mổ
// (/antmed/deliveries, AntmedDeliveries.vue + AntmedDeliveryDetail.vue).
// Idiom test = content-assert nguồn (router/nav/page/data). Cover acceptance FE:
// route đăng ký, nav bật, tri-branch render, param status == UI (chống dead-control),
// KHÔNG leak email NV/mã bác sỹ (GATE-2), không object filters (regression "[object Object]").

const srcDir = path.resolve(__dirname, '../../src')
const routerSrc = readFileSync(path.join(srcDir, 'router.js'), 'utf8')
const dataSrc = readFileSync(path.join(srcDir, 'data/antmed.js'), 'utf8')
const navSrc = readFileSync(path.join(srcDir, 'data/antmedNav.js'), 'utf8')
const listSrc = readFileSync(path.join(srcDir, 'pages/AntmedDeliveries.vue'), 'utf8')
const detailSrc = readFileSync(
  path.join(srcDir, 'pages/AntmedDeliveryDetail.vue'),
  'utf8',
)

describe('M04 S1 — Giao phòng mổ (routing + nav)', () => {
  it('router đăng ký route list + detail (lazy, prefix /antmed)', () => {
    expect(routerSrc).toMatch(/path:\s*'\/antmed\/deliveries'/)
    expect(routerSrc).toMatch(/name:\s*'AntmedDeliveries'/)
    expect(routerSrc).toMatch(/import\('@\/pages\/AntmedDeliveries\.vue'\)/)
    expect(routerSrc).toMatch(/path:\s*'\/antmed\/deliveries\/:name'/)
    expect(routerSrc).toMatch(/name:\s*'AntmedDeliveryDetail'/)
    expect(routerSrc).toMatch(/import\('@\/pages\/AntmedDeliveryDetail\.vue'\)/)
  })

  it('nav deliveries đã bật (enabled:true) — KHÔNG còn "Sắp có"', () => {
    const item = ANTMED_NAV.find((i) => i.key === 'deliveries')
    expect(item).toBeTruthy()
    expect(item.enabled).toBe(true)
    expect(item.to).toBe('/antmed/deliveries')
    expect(isNavActive(item, '/antmed/deliveries')).toBe(true)
    expect(isNavActive(item, '/antmed/deliveries/AM-DR-1')).toBe(true)
  })

  it('ANTMED_SECTIONS (sidebar grouped thật) có item deliveries enabled', () => {
    const all = ANTMED_SECTIONS.flatMap((s) => s.items)
    const item = all.find((i) => i.key === 'deliveries')
    expect(item).toBeTruthy()
    expect(item.enabled).toBe(true)
    expect(item.to).toBe('/antmed/deliveries')
  })
})

describe('M04 S1 — resource data/antmed.js', () => {
  it('listDeliveries + getDelivery: createResource GET, url khớp BE', () => {
    expect(dataSrc).toMatch(/export function listDeliveries/)
    expect(dataSrc).toMatch(
      /url:\s*'antmed_crm\.api\.antmed\.delivery\.list_deliveries'/,
    )
    expect(dataSrc).toMatch(/export function getDelivery/)
    expect(dataSrc).toMatch(
      /url:\s*'antmed_crm\.api\.antmed\.delivery\.get_delivery'/,
    )
    // GET method (BE @whitelist methods=["GET"]) — KHÔNG để POST mặc định.
    expect(dataSrc).toMatch(/list_deliveries'[\s\S]{0,60}method:\s*'GET'/)
  })

  it('theme + thứ tự status khớp EXACT options DocType (7 state VI có dấu)', () => {
    for (const s of [
      'Nháp',
      'Đã phân loại',
      'Đã gán NV',
      'Đang giao',
      'Đã bàn giao',
      'Đã đóng',
      'Từ chối',
    ]) {
      expect(dataSrc).toContain(`'${s}'`)
    }
    expect(dataSrc).toMatch(/export const DELIVERY_STATUS_ORDER/)
    expect(dataSrc).toMatch(/export const DELIVERY_STATUS_THEME/)
  })
})

describe('M04 S1 — list page AntmedDeliveries.vue', () => {
  it('tri-branch loading/error + đọc r.data.data', () => {
    expect(listSrc).toMatch(/deliveries\.loading/)
    expect(listSrc).toMatch(/deliveries\.error/)
    expect(listSrc).toMatch(/deliveries\.data\?\.data/)
  })

  it('param phát đi == UI: lọc bằng param `status` (string), KHÔNG object filters', () => {
    expect(listSrc).toMatch(/function buildParams/)
    expect(listSrc).toMatch(/status:\s*activeStatus\.value/)
    expect(listSrc).toMatch(/deliveries\.submit\(buildParams\(\)\)/)
    // GUARD regression "[object Object]": KHÔNG truyền object filters thô.
    expect(listSrc).not.toMatch(/filters:\s*\{\s*\}/)
  })

  it('S1.1: hiển thị tên BS + tên NV (full_name), KHÔNG leak email/mã', () => {
    expect(listSrc).toMatch(/row\.hospital_name/)
    expect(listSrc).toMatch(/row\.doctor_name/)
    expect(listSrc).toMatch(/row\.assigned_employee_name/)
    // KHÔNG render thô assigned_employee (email) — chỉ *_name
    expect(listSrc).not.toMatch(/\{\{\s*row\.assigned_employee\s*\}\}/)
    expect(listSrc).toContain('Chưa gán')
    expect(listSrc).toMatch(/statusTheme\(row\.status\)/)
  })
})

describe('M04 S1 — detail page AntmedDeliveryDetail.vue', () => {
  it('fetch get_delivery theo name + đọc items[] + doctor_name (không leak)', () => {
    expect(detailSrc).toMatch(/getDelivery\(/)
    expect(detailSrc).toMatch(/name:\s*props\.name/)
    expect(detailSrc).toMatch(/detail\.data\?\.items/)
    expect(detailSrc).toMatch(/doctor_name/)
    // assigned_employee detail cũng không leak email — chỉ Đã gán/Chưa gán
    expect(detailSrc).not.toMatch(/\{\{\s*.*assigned_employee\s*\}\}/)
  })

  it('tri-branch loading/error + nút Quay lại về list', () => {
    expect(detailSrc).toMatch(/detail\.loading/)
    expect(detailSrc).toMatch(/detail\.error/)
    expect(detailSrc).toMatch(/name:\s*'AntmedDeliveries'/)
  })

  it('S1.1: detail hiển thị tên NV (assigned_employee_name), KHÔNG email thô', () => {
    expect(detailSrc).toMatch(/assigned_employee_name/)
    expect(detailSrc).not.toMatch(/\{\{\s*.*\.assigned_employee\s*\}\}/)
  })
})

describe('M04 S2 — hành động vòng đời (detail)', () => {
  it('3 action gọi đúng endpoint BE + handler', () => {
    expect(detailSrc).toContain('antmed_crm.api.antmed.delivery.assign')
    expect(detailSrc).toContain('antmed_crm.api.antmed.delivery.start_transit')
    expect(detailSrc).toContain('antmed_crm.api.antmed.delivery.handover')
    expect(detailSrc).toMatch(/function doAssign/)
    expect(detailSrc).toMatch(/function doStart/)
    expect(detailSrc).toMatch(/function doHandover/)
  })

  it('nút gated theo state hiện tại (canAssign/canStart/canHandover)', () => {
    expect(detailSrc).toMatch(/canAssign/)
    expect(detailSrc).toMatch(/canStart/)
    expect(detailSrc).toMatch(/canHandover/)
    expect(detailSrc).toContain("'Đã gán NV'")
    expect(detailSrc).toContain("'Đang giao'")
  })

  it('Gán NV: dropdown list_assignable_employees + gửi đúng param', () => {
    expect(detailSrc).toContain(
      'antmed_crm.api.antmed.delivery.list_assignable_employees',
    )
    expect(detailSrc).toMatch(/assigned_employee:\s*selectedEmployee\.value/)
  })

  it('feedback bắt buộc: reload detail + toast cho action', () => {
    expect(detailSrc).toMatch(/detail\.reload\(\)/)
    expect(detailSrc).toMatch(/toast\.success/)
    expect(detailSrc).toMatch(/toast\.error/)
  })
})
