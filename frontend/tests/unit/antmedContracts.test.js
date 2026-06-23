import { readFileSync } from 'fs'
import path from 'path'
import { ANTMED_NAV, isNavActive } from '../../src/data/antmedNav'
import { shouldRedirectNotPermitted } from '../../src/utils/antmedGuard'
import {
  quotaUsedPct,
  quotaBarTheme,
  quotaBarClass,
  BAR_THEME,
} from '../../src/utils/antmedUi'

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
const detailSrc = readFileSync(
  path.join(srcDir, 'pages/AntmedContractDetail.vue'),
  'utf8',
)

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

  // ĐẢO CÓ CHỦ ĐÍCH (Slice M02-1b): ADR-M02-06 được ĐẢO — route Detail nay ĐÃ đăng ký.
  // (assertion cũ `.not.toMatch` của vòng M02-1 bị thay bằng `.toMatch`; KHÔNG xóa câu khác.)
  it('ĐÃ đăng ký route Detail (AntmedContractDetail / :name) — ĐẢO ADR-M02-06 ở Slice M02-1b', () => {
    expect(routerSrc).toMatch(/name:\s*['"]AntmedContractDetail['"]/)
    expect(routerSrc).toMatch(/\/antmed\/contracts\/:name/)
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
  it('listContracts → createResource url antmed_crm.api.antmed.contract.list_contracts', () => {
    expect(dataSrc).toMatch(/export function listContracts/)
    expect(dataSrc).toMatch(/antmed_crm\.api\.antmed\.contract\.list_contracts/)
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
    expect(dataSrc).toMatch(
      /import\s*\{\s*createResource\s*\}\s*from\s*'frappe-ui'/,
    )
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
    // refetch gửi buildParams() — gom search + filters (JSON-string) một chỗ
    expect(pageSrc).toMatch(/function buildParams/)
    expect(pageSrc).toMatch(/contracts\.submit\(buildParams\(\)\)/)
    // GUARD bug "[object Object]": filters PHẢI JSON.stringify trước khi gửi GET
    // (createResource GET serialize object thô → "[object Object]" → BE _coerce_filters parse lỗi → mất data)
    expect(pageSrc).toMatch(/filters:\s*JSON\.stringify\(filters\)/)
  })

  it('statusOptions = 5 giá trị VI + "Tất cả" (khớp options DocType, KHÔNG chuỗi EN)', () => {
    for (const s of ['Nháp', 'Hiệu lực', 'Sắp hết hạn', 'Hết hạn', 'Đã huỷ']) {
      expect(pageSrc).toContain(`'${s}'`)
    }
  })

  // ĐẢO CÓ CHỦ ĐÍCH (Slice M02-1b): drill-down mở lại — openContract nay ĐIỀU HƯỚNG
  // router.push name 'AntmedContractDetail' params name=row.name (assertion cũ no-op bị thay).
  it('row-click drill-down: openContract router.push name AntmedContractDetail params name=row.name', () => {
    expect(pageSrc).toMatch(/function openContract/)
    // Bỏ comment rồi assert có lệnh router.push THỰC THI tới route Detail.
    const codeNoComments = pageSrc
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .replace(/<!--[\s\S]*?-->/g, '')
      .replace(/^\s*\/\/.*$/gm, '')
    expect(codeNoComments).toMatch(/router\.push/)
    expect(codeNoComments).toMatch(
      /router\.push\(\s*\{\s*name:\s*['"]AntmedContractDetail['"]/,
    )
    expect(codeNoComments).toMatch(/params:\s*\{\s*name/)
  })

  it('<tr> dữ liệu MỞ LẠI affordance click (cursor-pointer + role=link + tabindex + @click + @keydown.enter + aria-label)', () => {
    // Lấy block <tbody>…</tbody>, GỠ comment HTML rồi assert hàng dữ liệu gợi ý bấm được.
    const tbody = pageSrc
      .slice(pageSrc.indexOf('<tbody>'), pageSrc.indexOf('</tbody>') + 8)
      .replace(/<!--[\s\S]*?-->/g, '')
    expect(tbody).toMatch(/@click/)
    expect(tbody).toMatch(/@keydown\.enter/)
    expect(tbody).toMatch(/role="link"/)
    expect(tbody).toMatch(/cursor-pointer/)
    expect(tbody).toMatch(/tabindex/)
    expect(tbody).toMatch(/aria-label/)
    expect(tbody).toMatch(/openContract\(\s*row\.name\s*\)/)
  })
})

// ── Slice M02-1b — màn CHI TIẾT Hợp đồng (AntmedContractDetail.vue) ──────────

describe('M02 data layer — getContract gọi đúng endpoint get_contract + param name', () => {
  it('getContract → createResource url antmed_crm.api.antmed.contract.get_contract', () => {
    expect(dataSrc).toMatch(/export function getContract/)
    expect(dataSrc).toMatch(/antmed_crm\.api\.antmed\.contract\.get_contract/)
  })

  it('Detail page truyền param { name } qua getContract({ params: { name: ... } })', () => {
    expect(detailSrc).toMatch(/getContract\(/)
    expect(detailSrc).toMatch(/params:\s*\{\s*name:\s*props\.name\s*\}/)
  })
})

describe('M02 route Detail — guard /antmed/contracts/:name allow như list', () => {
  it('guard: AntMed user + CRM user mở /antmed/contracts/AM-HD-0001 KHÔNG redirect', () => {
    expect(
      shouldRedirectNotPermitted(
        { path: '/antmed/contracts/AM-HD-0001' },
        antmed(),
      ),
    ).toBe(false)
    expect(
      shouldRedirectNotPermitted(
        { path: '/antmed/contracts/AM-HD-0001' },
        crm(),
      ),
    ).toBe(false)
  })

  it('guard: outsider mở /antmed/contracts/AM-HD-0001 bị redirect', () => {
    expect(
      shouldRedirectNotPermitted(
        { path: '/antmed/contracts/AM-HD-0001' },
        outsider(),
      ),
    ).toBe(true)
  })

  it('route Detail lazy import AntmedContractDetail.vue + props:true', () => {
    expect(routerSrc).toMatch(
      /import\(['"]@\/pages\/AntmedContractDetail\.vue['"]\)/,
    )
    // props:true nằm trong block route Detail (sau name AntmedContractDetail).
    const block = routerSrc.slice(
      routerSrc.indexOf("name: 'AntmedContractDetail'"),
    )
    expect(block.slice(0, 200)).toMatch(/props:\s*true/)
  })
})

describe('quota bar — ngưỡng màu theo % ĐÃ DÙNG (helper thuần antmedUi)', () => {
  it('quotaUsedPct = 100 - remaining_pct, clamp 0–100, null→0 (không vỡ)', () => {
    expect(quotaUsedPct(28)).toBe(72) // remaining 28 → đã dùng 72
    expect(quotaUsedPct(5)).toBe(95) // remaining 5 → đã dùng 95
    expect(quotaUsedPct(100)).toBe(0) // chưa dùng
    expect(quotaUsedPct(0)).toBe(100) // dùng hết
    expect(quotaUsedPct(null)).toBe(0) // null → 0 (xanh)
    expect(quotaUsedPct(undefined)).toBe(0)
    expect(quotaUsedPct(-10)).toBe(100) // clamp trên
    expect(quotaUsedPct(150)).toBe(0) // clamp dưới
  })

  it('quotaBarTheme: >=95 danger, >=72 warn, còn lại default (brand xanh)', () => {
    expect(quotaBarTheme(95)).toBe('danger')
    expect(quotaBarTheme(99)).toBe('danger')
    expect(quotaBarTheme(72)).toBe('warn')
    expect(quotaBarTheme(80)).toBe('warn')
    expect(quotaBarTheme(50)).toBe('default')
    expect(quotaBarTheme(0)).toBe('default')
  })

  it('quotaBarClass(remaining_pct): remaining=5 (đã dùng 95) → class danger (đỏ)', () => {
    // remaining_pct=5 → usedPct=95 → theme danger → BAR_THEME.danger (đỏ)
    expect(quotaBarClass(5)).toBe(BAR_THEME.danger)
    // remaining_pct=28 → usedPct=72 → warn (cam)
    expect(quotaBarClass(28)).toBe(BAR_THEME.warn)
    // remaining_pct=100 → usedPct=0 → default (brand xanh)
    expect(quotaBarClass(100)).toBe(BAR_THEME.default)
  })
})

describe('AntmedContractDetail.vue — render header + bảng quota (content-assert)', () => {
  it('đọc r.data.items TRỰC TIẾP (KHÔNG r.data.data — get_contract không phải list-wrap)', () => {
    expect(detailSrc).toMatch(/contract\.data\?\.items/)
    expect(detailSrc).not.toMatch(/contract\.data\?\.data/)
  })

  it('header HĐ: contract_no / hospital_name / signed_date / valid_from / valid_to / total_value / status', () => {
    expect(detailSrc).toMatch(/contract\.data\.contract_no/)
    expect(detailSrc).toMatch(/contract\.data\.hospital_name/)
    expect(detailSrc).toMatch(/contract\.data\.signed_date/)
    expect(detailSrc).toMatch(/contract\.data\.valid_from/)
    expect(detailSrc).toMatch(/contract\.data\.valid_to/)
    expect(detailSrc).toMatch(/contract\.data\.total_value/)
    expect(detailSrc).toMatch(/contract\.data\.status/)
  })

  it('total_value qua formatCurrency (định dạng VND), badge status qua theme map', () => {
    expect(detailSrc).toMatch(/formatCurrency\(contract\.data\.total_value\)/)
    expect(detailSrc).toMatch(/currency:\s*'VND'/)
    expect(detailSrc).toMatch(/statusTheme\(contract\.data\.status\)/)
    expect(detailSrc).toMatch(/CONTRACT_WORKFLOW_THEME/)
  })

  it('bảng quota: item_name fallback item, uom, unit_price formatCurrency, quota_qty, used_qty', () => {
    expect(detailSrc).toMatch(/row\.item_name\s*\|\|\s*row\.item/)
    expect(detailSrc).toMatch(/row\.uom/)
    expect(detailSrc).toMatch(/formatCurrency\(row\.unit_price\)/)
    expect(detailSrc).toMatch(/row\.quota_qty/)
    expect(detailSrc).toMatch(/row\.used_qty/)
  })

  it('thanh % dùng usedPct(row.remaining_pct) cho width + barClass màu theo ngưỡng', () => {
    expect(detailSrc).toMatch(/usedPct\(row\.remaining_pct\)/)
    expect(detailSrc).toMatch(/barClass\(row\.remaining_pct\)/)
    // helper thuần được import (ngưỡng đỏ≥95/cam≥72/xanh sống ở antmedUi).
    expect(detailSrc).toMatch(/quotaUsedPct|quotaBarClass/)
  })

  it('cờ lock_at_100 → chip "Khóa khi đủ 100%" khi truthy (ẩn khi false)', () => {
    expect(detailSrc).toMatch(/row\.lock_at_100/)
    expect(detailSrc).toMatch(/Khóa khi đủ 100%/)
  })
})

describe('AntmedContractDetail.vue — tri-branch loading/error/empty', () => {
  it('tri-branch: loading / error (banner + Thử lại reload) / data', () => {
    expect(detailSrc).toMatch(/contract\.loading/)
    expect(detailSrc).toMatch(/contract\.error/)
    expect(detailSrc).toMatch(/Thử lại/)
    expect(detailSrc).toMatch(/contract\.reload\(\)/)
  })

  it('empty-state quota "Chưa có dòng quota" khi items rỗng (không vỡ render)', () => {
    expect(detailSrc).toMatch(/Chưa có dòng quota/)
    expect(detailSrc).toMatch(/!items\.length/)
  })

  it('error-state KHÔNG leak stacktrace: dùng error.messages[0]/message + fallback VI', () => {
    expect(detailSrc).toMatch(/contract\.error\?\.messages\?\.\[0\]/)
    expect(detailSrc).toMatch(/Không tải được chi tiết hợp đồng/)
  })

  it('breadcrumb: nút quay lại điều hướng router.push name AntmedContracts', () => {
    expect(detailSrc).toMatch(/Quay lại danh sách hợp đồng/)
    expect(detailSrc).toMatch(
      /router\.push\(\s*\{\s*name:\s*['"]AntmedContracts['"]/,
    )
  })

  it('KHÔNG createListResource / axios / .ts (idiom frappe-ui thuần)', () => {
    expect(detailSrc).not.toMatch(/createListResource/)
    expect(detailSrc).not.toMatch(/axios|@tanstack\/vue-query|useApi\(/)
  })
})
