// AntMed RBAC — FE helper (W0-2 / DEC-B, ADR-M14W0-04).
//
// Đọc cờ AntMed từ BOOT (single-source ở BE: antmed_crm/api/antmed/rbac.py).
// BE `get_boot()` (antmed_crm/www/crm.py) expose `is_antmed_user` (boolean) + `antmed_roles`
// → crm.html inject `window.is_antmed_user` / `window.antmed_roles`.
//
// ⚠️ KHÔNG hardcode danh sách Role AntMed (`NV kinh doanh`/`Thủ kho`/`Quản lý`) lần 2 ở FE.
// FE chỉ đọc cờ boolean đã tính sẵn ở BE — đổi/thêm Role AntMed sau KHÔNG phải sửa FE.
// Fallback an toàn = false (chặn) khi boot chưa có cờ (server chưa wiring / dev cũ).

/** True nếu user hiện tại là AntMed user (đọc cờ boot, KHÔNG suy role ở FE). */
export function isAntmedUser() {
  return Boolean(globalThis.window?.is_antmed_user)
}

/** Danh sách Role AntMed từ boot (chỉ để liệt kê khi cần — vd settings). KHÔNG dùng để so quyền. */
export const antmedRoles = globalThis.window?.antmed_roles || []

/** True nếu path thuộc khu vực SPA AntMed (`/antmed`, `/antmed/...`). */
export function isAntmedPath(path) {
  return typeof path === 'string' && path.startsWith('/antmed')
}

// Phase 1 — CHỈ DÙNG UI AntMed: route hệ thống/login được GIỮ (không redirect về /antmed).
// Mock prototype cũ có name 'Antmed*Mock' nhưng path KHÔNG /antmed → PHẢI redirect ⇒ keep
// theo PATH (/antmed/*) + keep-list này, KHÔNG theo tiền tố tên 'Antmed'.
export const ANTMED_KEEP_ROUTE_NAMES = [
  'Not Permitted',
  'Invalid Page',
  'AntmedLogin',
]

/**
 * True nếu route ĐƯỢC GIỮ khi đã consolidate về UI AntMed (Phase 1):
 * khu /antmed/* (path-based) HOẶC login/trang lỗi hệ thống (keep-list).
 * Mọi route khác (Home, CRM gốc /leads,/deals..., mock prototype /ceo,/sales/*...) → redirect /antmed.
 */
export function isAntmedOnlyKeptRoute(to) {
  if (!to) return false
  if (isAntmedPath(to.path)) return true
  return ANTMED_KEEP_ROUTE_NAMES.includes(to.name)
}
