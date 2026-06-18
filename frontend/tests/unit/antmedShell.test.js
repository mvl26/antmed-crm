import { readFileSync } from 'fs'
import path from 'path'
import {
  ANTMED_NAV,
  isNavActive,
  ANTMED_ROLES,
  navForRole,
  ANTMED_SECTIONS,
} from '../../src/data/antmedNav'

// Slice 1 — AntMed app shell (topbar + sidebar) khớp mockup A1.
// T3 — shell ROLE-AWARE: nav theo vai trò (ANTMED_ROLES/navForRole) + role switcher +
// App.vue chọn layout theo route.meta.antmedShell. Idiom test = content-assert nguồn +
// behavior-assert helper thuần (KHÔNG @vue/test-utils — theo antmedRouterGuard.test.js).

const srcDir = path.resolve(__dirname, '../../src')
const layoutSrc = readFileSync(
  path.join(srcDir, 'components/Antmed/AntmedLayout.vue'),
  'utf8',
)
const appSrc = readFileSync(path.join(srcDir, 'App.vue'), 'utf8')

// ── FIX điều hướng: sidebar TOÀN DIỆN — mọi màn real-data /antmed/* truy cập được
// từ /antmed (KHÔNG còn ẩn sau role switcher / KHÔNG trỏ stub /ceo,/portal). ──
describe('ANTMED_SECTIONS — sidebar toàn diện (mọi màn real-data)', () => {
  const flat = () => ANTMED_SECTIONS.flatMap((s) => s.items)
  it('mảng section {title, items[]} không rỗng', () => {
    expect(Array.isArray(ANTMED_SECTIONS)).toBe(true)
    expect(ANTMED_SECTIONS.length).toBeGreaterThanOrEqual(5)
    for (const s of ANTMED_SECTIONS) {
      expect(s.title).toBeTruthy()
      expect(Array.isArray(s.items) && s.items.length > 0).toBe(true)
    }
  })
  it('mọi item enabled + to là route /antmed/* THẬT + key duy nhất (KHÔNG stub)', () => {
    const keys = new Set()
    for (const i of flat()) {
      expect(i.label && i.icon).toBeTruthy()
      expect(i.enabled).toBe(true)
      expect(i.to.startsWith('/antmed')).toBe(true)
      expect(keys.has(i.key)).toBe(false)
      keys.add(i.key)
    }
  })
  it('icon là string (data giữ key; layout map sang component thư viện)', () => {
    for (const i of flat()) {
      expect(typeof i.icon).toBe('string')
      expect(i.icon.length).toBeGreaterThan(0)
    }
  })
  it('phủ màn cốt lõi mọi vai trò (CEO/KD/Kho/Tài chính/Portal)', () => {
    const tos = flat().map((i) => i.to)
    for (const t of [
      '/antmed',
      '/antmed/contracts',
      '/antmed/revenue',
      '/antmed/alerts',
      '/antmed/hospitals',
      '/antmed/sales/dispatch',
      '/antmed/sales/team',
      '/antmed/warehouse/stock-entries',
      '/antmed/warehouse/consignment',
      '/antmed/warehouse/lot-trace',
      '/antmed/warehouse/expiry-alerts',
      '/antmed/finance/commission',
      '/antmed/portal',
    ]) {
      expect(tos).toContain(t)
    }
  })
})

describe('AntmedLayout — sidebar mặc định dùng ANTMED_SECTIONS (truy cập đầy đủ)', () => {
  it('layout render ANTMED_SECTIONS (grouped) — không chỉ navForRole', () => {
    expect(layoutSrc).toMatch(/ANTMED_SECTIONS/)
  })
})

describe('AntMed nav config — single source cho sidebar shell', () => {
  it('Dashboard + Bệnh viện là route thật đã có (enabled)', () => {
    const byKey = Object.fromEntries(ANTMED_NAV.map((i) => [i.key, i]))
    expect(byKey.dashboard).toMatchObject({ to: '/antmed', enabled: true })
    expect(byKey.hospitals).toMatchObject({
      to: '/antmed/hospitals',
      enabled: true,
    })
  })

  it('mỗi item có label/icon/to/enabled hợp lệ', () => {
    for (const i of ANTMED_NAV) {
      expect(i.label).toBeTruthy()
      expect(i.icon).toBeTruthy()
      expect(typeof i.to).toBe('string')
      expect(typeof i.enabled).toBe('boolean')
    }
  })

  it('có stub module sắp tới (Hợp đồng / Tồn kho / Bộ dụng cụ) — disabled', () => {
    const labels = ANTMED_NAV.map((i) => i.label)
    expect(labels).toEqual(
      expect.arrayContaining(['Hợp đồng', 'Tồn kho', 'Bộ dụng cụ']),
    )
    expect(ANTMED_NAV.some((i) => !i.enabled)).toBe(true)
  })
})

describe('isNavActive — dashboard exact, sub-route theo prefix', () => {
  const dash = { to: '/antmed' }
  const hosp = { to: '/antmed/hospitals' }

  it('Dashboard chỉ active khi path đúng /antmed (không active ở sub-route)', () => {
    expect(isNavActive(dash, '/antmed')).toBe(true)
    expect(isNavActive(dash, '/antmed/hospitals')).toBe(false)
  })

  it('Bệnh viện active ở /antmed/hospitals và trang chi tiết con', () => {
    expect(isNavActive(hosp, '/antmed/hospitals')).toBe(true)
    expect(isNavActive(hosp, '/antmed/hospitals/BV-001')).toBe(true)
    expect(isNavActive(hosp, '/antmed')).toBe(false)
  })

  it('an toàn với input xấu', () => {
    expect(isNavActive(null, '/antmed')).toBe(false)
    expect(isNavActive(hosp, undefined)).toBe(false)
  })
})

// ── T3: role-aware nav (8 vai trò mockup) ──────────────────────────────────
describe('ANTMED_ROLES — 8 vai trò mockup (CEO..Admin) + portal variant', () => {
  it('đủ 8 vai trò, mỗi role có key + label', () => {
    expect(ANTMED_ROLES).toHaveLength(8)
    for (const r of ANTMED_ROLES) {
      expect(r.key).toBeTruthy()
      expect(r.label).toBeTruthy()
    }
  })

  it('phủ đúng 8 key vai trò theo mockup', () => {
    const keys = ANTMED_ROLES.map((r) => r.key).sort()
    expect(keys).toEqual(
      [
        'admin',
        'ceo',
        'docs',
        'finance',
        'portal',
        'rep',
        'sales',
        'warehouse',
      ].sort(),
    )
  })

  it('role portal đánh dấu variant=portal (topbar trắng); role rep là mobile', () => {
    const byKey = Object.fromEntries(ANTMED_ROLES.map((r) => [r.key, r]))
    expect(byKey.portal.variant).toBe('portal')
    expect(byKey.rep.mobile).toBe(true)
  })
})

describe('navForRole — nav riêng từng vai trò + fallback an toàn', () => {
  it('navForRole(role) trả mảng item hợp lệ cho mọi vai trò', () => {
    for (const r of ANTMED_ROLES) {
      const nav = navForRole(r.key)
      expect(Array.isArray(nav)).toBe(true)
      expect(nav.length).toBeGreaterThan(0)
      for (const i of nav) {
        expect(i.label).toBeTruthy()
        expect(i.icon).toBeTruthy()
        expect(typeof i.to).toBe('string')
        expect(typeof i.enabled).toBe('boolean')
      }
    }
  })

  it('nav khớp sidebar mockup (CEO/TKD/Thủ kho/Chứng từ/Kế toán/Admin)', () => {
    const lbl = (role) => navForRole(role).map((i) => i.label)
    expect(lbl('ceo')).toEqual(
      expect.arrayContaining(['Dashboard', 'Hợp đồng', 'Doanh thu']),
    )
    expect(lbl('sales')).toEqual(
      expect.arrayContaining(['Điều phối', 'Duyệt yêu cầu', 'Đội ngũ']),
    )
    expect(lbl('warehouse')).toEqual(
      expect.arrayContaining(['Xuất cho NV', 'Kho ký gửi BV', 'Truy vết lot']),
    )
    expect(lbl('docs')).toEqual(
      expect.arrayContaining(['Hàng chờ', 'Kho CO/CQ', 'Đối soát ký nhận']),
    )
    expect(lbl('finance')).toEqual(
      expect.arrayContaining(['Công nợ', 'Hoa hồng NV']),
    )
    expect(lbl('admin')).toEqual(
      expect.arrayContaining(['User & Role', 'Audit log']),
    )
  })

  it('fallback: role không xác định → ANTMED_NAV (giữ shell /antmed cũ, no-regression)', () => {
    expect(navForRole('khong-ton-tai')).toBe(ANTMED_NAV)
    expect(navForRole(undefined)).toBe(ANTMED_NAV)
    expect(navForRole('')).toBe(ANTMED_NAV)
  })
})

describe('AntmedLayout.vue — shell mockup + role switcher', () => {
  it('có topbar thương hiệu (logo AntMed CRM)', () => {
    expect(layoutSrc).toMatch(/AntMed CRM/)
  })

  it('sidebar render qua ANTMED_SECTIONS + icon component THƯ VIỆN (KHÔNG emoji)', () => {
    expect(layoutSrc).toMatch(/ANTMED_SECTIONS/)
    // icon dùng component thư viện @/components/Icons/* (xoá emoji render-as-text)
    expect(layoutSrc).toMatch(/@\/components\/Icons\//)
    expect(layoutSrc).toMatch(/iconFor/)
    expect(layoutSrc).toMatch(/:is="iconFor/)
    // KHÔNG còn render emoji thô {{ item.icon }} trong template
    expect(layoutSrc).not.toMatch(/\{\{\s*item\.icon\s*\}\}/)
  })

  it('header: popup thông báo (Popover) + avatar user THẬT, KHÔNG còn role switcher', () => {
    expect(layoutSrc).toMatch(/notificationsStore|unreadNotificationsCount/)
    // thông báo dạng popup dropdown (frappe-ui Popover), KHÔNG panel slide-out
    expect(layoutSrc).toMatch(/Popover/)
    // avatar user thật (initials/ảnh) → trang cá nhân
    expect(layoutSrc).toMatch(/userInitials|userImage/)
    expect(layoutSrc).toMatch(/\/antmed\/profile/)
    // role switcher <select v-model="selectedRole"> đã gỡ khỏi header
    expect(layoutSrc).not.toMatch(/v-model="selectedRole"/)
  })

  it('hỗ trợ portal variant (topbar trắng cho vai trò G)', () => {
    expect(layoutSrc).toMatch(/portal/)
  })

  it('dùng RouterLink cho item enabled + có slot nội dung', () => {
    expect(layoutSrc).toMatch(/RouterLink|router-link/)
    expect(layoutSrc).toMatch(/<slot/)
  })

  it('đánh dấu active qua isNavActive', () => {
    expect(layoutSrc).toMatch(/isNavActive/)
  })
})

describe('App.vue — layout AntMed DUY NHẤT (Phase 2: chỉ UI AntMed)', () => {
  it('render AntmedLayout, đã bỏ import layout Mobile/Desktop của CRM gốc', () => {
    expect(appSrc).toMatch(/AntmedLayout/)
    // khớp đường dẫn import (KHÔNG khớp comment) — đã gỡ ./components/Layouts/{Mobile,Desktop}Layout
    expect(appSrc).not.toMatch(/Layouts\/(Mobile|Desktop)Layout/)
  })
})
