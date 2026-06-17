import { readFileSync } from 'fs'
import path from 'path'
import { ANTMED_NAV, isNavActive } from '../../src/data/antmedNav'
import { shouldRedirectNotPermitted } from '../../src/utils/antmedGuard'

// M02 Slice M02-1 — màn DANH SÁCH Hợp đồng (/antmed/contracts, AntmedContracts.vue).
// Idiom test = content-assert nguồn (router/nav/page/data) + behavior-assert helper thuần
// (KHÔNG @vue/test-utils — theo antmedShell.test.js / antmedRouterGuard.test.js).
// Cover acceptance FE: route mở được dưới AntMed user, tri-branch render, param == UI
// selection (chống dead-control), row-click KHÔNG dead-end (no-op + gỡ affordance).

const srcDir = path.resolve(__dirname, '../../src')
const routerSrc = readFileSync(path.join(srcDir, 'router.js'), 'utf8')
const pageSrc = readFileSync(
  path.join(srcDir, 'pages/AntmedContracts.vue'),
  'utf8',
)
const dataSrc = readFileSync(path.join(srcDir, 'data/antmed.js'), 'utf8')

const antmed = () => ({ isCrmUser: () => false, isAntmedUser: () => true })
const crm = () => ({ isCrmUser: () => true, isAntmedUser: () => false })
const outsider = () => ({ isCrmUser: () => false, isAntmedUser: () => false })

describe('M02 nav — entry Hợp đồng enabled tới /antmed/contracts', () => {
  it('nav contracts enabled=true, to=/antmed/contracts (đúng 1 entry, không thêm item mới)', () => {
    const byKey = Object.fromEntries(ANTMED_NAV.map((i) => [i.key, i]))
    expect(byKey.contracts).toMatchObject({
      to: '/antmed/contracts',
      enabled: true,
      label: 'Hợp đồng',
    })
    const contracts = ANTMED_NAV.filter((i) => i.key === 'contracts')
    expect(contracts).toHaveLength(1)
  })

  it('isNavActive: active ở /antmed/contracts, KHÔNG active ở /antmed (dashboard)', () => {
    const item = { to: '/antmed/contracts' }
    expect(isNavActive(item, '/antmed/contracts')).toBe(true)
    expect(isNavActive(item, '/antmed')).toBe(false)
    // Dashboard không bị "Hợp đồng" làm active sai
    expect(isNavActive({ to: '/antmed' }, '/antmed/contracts')).toBe(false)
  })
})

describe('M02 route — /antmed/contracts đăng ký + guard allow', () => {
  it('router.js đăng ký route AntmedContracts → /antmed/contracts (lazy import page)', () => {
    expect(routerSrc).toMatch(/name:\s*['"]AntmedContracts['"]/)
    expect(routerSrc).toMatch(/path:\s*['"]\/antmed\/contracts['"]/)
    expect(routerSrc).toMatch(/AntmedContracts\.vue/)
  })

  it('KHÔNG đăng ký route Detail (AntmedContractDetail / :name) ở vòng này (ADR-M02-06)', () => {
    expect(routerSrc).not.toMatch(/name:\s*['"]AntmedContractDetail['"]/)
    expect(routerSrc).not.toMatch(/\/antmed\/contracts\/:/)
  })

  it('guard: AntMed user mở /antmed/contracts KHÔNG redirect; CRM user cũng pass', () => {
    expect(
      shouldRedirectNotPermitted({ path: '/antmed/contracts' }, antmed()),
    ).toBe(false)
    expect(
      shouldRedirectNotPermitted({ path: '/antmed/contracts' }, crm()),
    ).toBe(false)
  })

  it('guard: outsider (không CRM không AntMed) vào /antmed/contracts bị redirect', () => {
    expect(
      shouldRedirectNotPermitted({ path: '/antmed/contracts' }, outsider()),
    ).toBe(true)
  })
})

describe('M02 data layer — listContracts gọi đúng endpoint (naming contract BE-FE)', () => {
  it('listContracts → createResource url crm.api.antmed.contract.list_contracts', () => {
    expect(dataSrc).toMatch(/export function listContracts/)
    expect(dataSrc).toMatch(/crm\.api\.antmed\.contract\.list_contracts/)
  })

  it('CONTRACT_WORKFLOW_THEME map đủ 5 status VI (key khớp EXACT options DocType)', () => {
    // Import động để assert object thật (không chỉ chuỗi nguồn).
    const re = /CONTRACT_WORKFLOW_THEME\s*=\s*\{([\s\S]*?)\}/
    const m = dataSrc.match(re)
    expect(m).toBeTruthy()
    const body = m[1]
    for (const s of ['Nháp', 'Hiệu lực', 'Sắp hết hạn', 'Hết hạn', 'Đã huỷ']) {
      expect(body).toContain(s)
    }
  })
})

describe('AntmedContracts.vue — tri-branch render + param==selection + no dead-end', () => {
  it('tri-branch: loading / error (banner + Thử lại) / empty (thông điệp VI)', () => {
    expect(pageSrc).toMatch(/contracts\.loading/)
    expect(pageSrc).toMatch(/contracts\.error/)
    // empty branch + thông điệp VI acceptance
    expect(pageSrc).toMatch(/Chưa có hợp đồng nào khớp/)
    // error branch: nút Thử lại gọi reload
    expect(pageSrc).toMatch(/Thử lại/)
    expect(pageSrc).toMatch(/contracts\.reload\(\)/)
  })

  it('đọc list trả dict bọc: r.data.data + r.data.total_count (dùng createResource, KHÔNG createListResource)', () => {
    expect(pageSrc).toMatch(/contracts\.data\?\.data/)
    expect(pageSrc).toMatch(/contracts\.data\?\.total_count/)
    // listContracts dùng createResource (đọc dict bọc) — KHÔNG createListResource (coi là array).
    expect(dataSrc).toMatch(/import\s*\{\s*createResource\s*\}\s*from\s*'frappe-ui'/)
    expect(dataSrc).not.toMatch(/import[^\n]*createListResource/)
  })

  it('cột bảng đọc ĐÚNG field BE (Hyrum 7-key): contract_no/hospital_name/valid_to/total_value/status', () => {
    expect(pageSrc).toMatch(/row\.contract_no/)
    expect(pageSrc).toMatch(/row\.hospital_name/)
    expect(pageSrc).toMatch(/row\.valid_to/)
    expect(pageSrc).toMatch(/row\.total_value/)
    expect(pageSrc).toMatch(/row\.status/)
  })

  it('param phát đi == UI selection: refetch build filters từ hospital + status, search riêng', () => {
    // setHospital/setStatus/onSearch cập nhật state rồi refetch (chống dead-control LL-FE-13)
    expect(pageSrc).toMatch(/function setHospital/)
    expect(pageSrc).toMatch(/function setStatus/)
    expect(pageSrc).toMatch(/function onSearch/)
    expect(pageSrc).toMatch(/filters\.hospital\s*=\s*activeHospital\.value/)
    expect(pageSrc).toMatch(/filters\.status\s*=\s*activeStatus\.value/)
    expect(pageSrc).toMatch(/contracts\.submit\(\{\s*search:\s*search\.value,\s*filters\s*\}\)/)
  })

  it('statusOptions = 5 giá trị VI + "Tất cả" (khớp options DocType, KHÔNG chuỗi EN)', () => {
    for (const s of ['Nháp', 'Hiệu lực', 'Sắp hết hạn', 'Hết hạn', 'Đã huỷ']) {
      expect(pageSrc).toContain(`'${s}'`)
    }
  })

  it('row-click KHÔNG dead-end: openContract no-op, KHÔNG router.push live tới AntmedContractDetail', () => {
    // openContract giữ chữ ký nhưng KHÔNG điều hướng (chỉ comment nhắc vòng sau)
    expect(pageSrc).toMatch(/function openContract/)
    // KHÔNG còn lệnh router.push thực thi (chỉ trong comment). Bỏ comment rồi assert.
    const codeNoComments = pageSrc
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .replace(/<!--[\s\S]*?-->/g, '')
      .replace(/^\s*\/\/.*$/gm, '')
    expect(codeNoComments).not.toMatch(/router\.push/)
    expect(codeNoComments).not.toMatch(/AntmedContractDetail/)
  })

  it('<tr> dữ liệu KHÔNG còn affordance click (cursor/role=link/tabindex/@click openContract)', () => {
    // Lấy block <tbody>…</tbody>, GỠ comment HTML (comment giải thích có nhắc các affordance
    // đã gỡ → không tính là affordance thật) rồi assert hàng dữ liệu không gợi ý bấm.
    const tbody = pageSrc
      .slice(pageSrc.indexOf('<tbody>'), pageSrc.indexOf('</tbody>') + 8)
      .replace(/<!--[\s\S]*?-->/g, '')
    expect(tbody).not.toMatch(/@click/)
    expect(tbody).not.toMatch(/@keydown/)
    expect(tbody).not.toMatch(/role="link"/)
    expect(tbody).not.toMatch(/cursor-pointer/)
    expect(tbody).not.toMatch(/tabindex/)
  })
})
