// AntMed router guard decision (W0-2 / DEC-B Gate-3, ADR-M14W0-03).
//
// Tách thành hàm THUẦN để vừa testable (vitest) vừa giữ logic CRM gốc NGUYÊN VẸN.
// Chỉ THÊM nhánh `/antmed/*` (allow CRM HOẶC AntMed); route CRM gốc GIỮ `isCrmUser()`.
//
// Invariant (acceptance Gate-3):
//   /antmed/*  + AntMed user           → KHÔNG redirect (pass)
//   /antmed/*  + CRM user              → KHÔNG redirect (pass)
//   /antmed/*  + không-role-nào        → redirect 'Not Permitted'
//   /leads…    + AntMed-thuần          → redirect 'Not Permitted'  (no-regression CRM gốc)
//   /leads…    + CRM user              → KHÔNG redirect            (no-regression CRM gốc)
import { isAntmedPath } from './antmed'

/**
 * Quyết định có redirect 'Not Permitted' không.
 * @param {object} to            route đích (cần `path`).
 * @param {object} deps
 * @param {() => boolean} deps.isCrmUser    helper từ usersStore (giữ nguyên ngữ nghĩa CRM gốc).
 * @param {() => boolean} deps.isAntmedUser helper đọc cờ boot AntMed.
 * @returns {boolean} true nếu phải redirect sang 'Not Permitted'.
 */
export function shouldRedirectNotPermitted(to, { isCrmUser, isAntmedUser }) {
  if (isAntmedPath(to?.path)) {
    // [W0-2 ADDITIVE] route AntMed: cho phép CRM user HOẶC AntMed user.
    return !isCrmUser() && !isAntmedUser()
  }
  // Route CRM gốc: GIỮ NGUYÊN — chỉ CRM user (AntMed-thuần vẫn bị chặn).
  return !isCrmUser()
}
