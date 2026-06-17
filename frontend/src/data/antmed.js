/**
 * AntMed CRM — neo dữ liệu nền (M01 Customer 360°).
 *
 * R1 (bootstrap): resource health.ping chứng minh đường FE → BE callable.
 * R2 (Customer 360°): factory tạo resource list/detail cho Bệnh viện + Bác sỹ,
 *   gọi đúng naming contract `crm.api.antmed.customer.<fn>` (in-place app crm).
 *
 * Convention (xem docs/antmed_crm/docs/m01_naming_conventions.md §5):
 *   - Resource url: 'crm.api.antmed.<module>.<fn>'  (in-place app crm, KHÔNG app riêng)
 *   - DocType (Frappe CRUD nếu cần): 'AntMed <DocType>'
 *
 * ⚠️ Endpoint list trả RAW dict bọc { data: list, total_count: int } — KHÔNG phải
 *    list thuần. Vì vậy dùng `createResource` (đọc `r.data.data` + `r.data.total_count`),
 *    KHÔNG dùng list-resource (frappe-ui coi response là array sẽ vỡ shape bọc).
 *
 * KHÔNG nhồi business-logic ở FE: BR-xx sống ở BE (crm/antmed module hooks).
 * List/dict params phải JSON.stringify (BE param *_json) — R2 chỉ truyền scalar/dict đơn,
 * `filters` truyền dạng dict (frappe-ui tự serialize query-param) hoặc JSON string khi cần.
 */
import { createResource } from 'frappe-ui'

/**
 * Health-check nền AntMed — GET crm.api.antmed.health.ping.
 * Trả RAW dict { app, status, version }. Caller bật `auto: true` hoặc `.fetch()`.
 */
export function getAntmedHealth() {
  return createResource({
    url: 'crm.api.antmed.health.ping',
  })
}

// ── M01 R2: Customer 360° — Bệnh viện + Bác sỹ ──────────────────────────────

/**
 * Danh sách Bệnh viện — crm.api.antmed.customer.list_hospitals.
 * BE: list_hospitals(filters?, start?, page_length?, search?) -> { data, total_count }.
 * Item: name, hospital_name, rank, contract_status, tax_code. Invariant count==rows.
 *
 * @param {object} [opts]
 * @param {object} [opts.params] - params khởi tạo (search/filters/start/page_length).
 * @param {boolean} [opts.auto] - auto-fetch.
 */
export function listHospitals({ params = {}, auto = false } = {}) {
  return createResource({
    url: 'crm.api.antmed.customer.list_hospitals',
    params,
    auto,
  })
}

/**
 * Chi tiết Bệnh viện ("mặt 360") — crm.api.antmed.customer.get_hospital.
 * BE: get_hospital(name) -> field BV + doctors[] (name/full_name/specialty/phone).
 * throw frappe.PermissionError nếu không read được.
 */
export function getHospital({ params = {}, auto = false } = {}) {
  return createResource({
    url: 'crm.api.antmed.customer.get_hospital',
    params,
    auto,
  })
}

/**
 * Danh sách Bác sỹ — crm.api.antmed.customer.list_doctors.
 * BE: list_doctors(filters?, hospital?, start?, page_length?) -> { data, total_count }.
 * Item: name, full_name, specialty, hospital, phone (+ hospital_name nếu rẻ).
 */
export function listDoctors({ params = {}, auto = false } = {}) {
  return createResource({
    url: 'crm.api.antmed.customer.list_doctors',
    params,
    auto,
  })
}

/**
 * Chi tiết Bác sỹ — crm.api.antmed.customer.get_doctor.
 * BE: get_doctor(name) -> field bác sỹ + hospital_name (resolve qua Link).
 * throw frappe.PermissionError nếu không read được.
 */
export function getDoctor({ params = {}, auto = false } = {}) {
  return createResource({
    url: 'crm.api.antmed.customer.get_doctor',
    params,
    auto,
  })
}

// ── M02 Slice M02-1: Hợp đồng & Quota (read-only) ───────────────────────────

/**
 * Danh sách Hợp đồng — crm.api.antmed.contract.list_contracts.
 * BE: list_contracts(filters?, start?, page_length?, search?) -> { data, total_count }.
 * Item: name, contract_no, hospital, hospital_name, valid_to, total_value, status.
 *   - hiển thị hospital_name (KHÔNG mã hospital), badge theo status (Select VI).
 *   - search lọc theo contract_no (LIKE). filters hỗ trợ key hospital + status.
 * ⚠️ List trả dict bọc → createResource đọc r.data.data (KHÔNG createListResource).
 *
 * @param {object} [opts]
 * @param {object} [opts.params] - params khởi tạo (search/filters/start/page_length).
 * @param {boolean} [opts.auto] - auto-fetch.
 */
export function listContracts({ params = {}, auto = false } = {}) {
  return createResource({
    url: 'crm.api.antmed.contract.list_contracts',
    params,
    auto,
  })
}

/**
 * Chi tiết Hợp đồng — crm.api.antmed.contract.get_contract.
 * BE: get_contract(name) -> field HĐ + hospital_name (resolve qua Link) + items[]
 *     (mỗi dòng item/item_name/uom/unit_price/quota_qty/used_qty/remaining_pct/lock_at_100).
 * throw frappe.PermissionError nếu không read được (FE bắt qua onError → toast).
 */
export function getContract({ params = {}, auto = false } = {}) {
  return createResource({
    url: 'crm.api.antmed.contract.get_contract',
    params,
    auto,
  })
}

// ── M11 Slice 2: Dashboard A1 — số liệu tổng quan ───────────────────────────

/**
 * Số liệu tổng quan dashboard A1 — crm.api.antmed.dashboard.overview (GET).
 * BE: overview() -> RAW dict THƯỜNG { hospital_count: int, doctor_count: int }
 *     (đếm DƯỚI permission user — invariant count==rows như customer.py).
 *
 * ⚠️ KHÁC list endpoint (list_hospitals/list_doctors bọc { data, total_count } → đọc r.data.data):
 *    overview trả dict THƯỜNG, KHÔNG bọc → FE đọc `r.data.hospital_count` / `r.data.doctor_count`
 *    TRỰC TIẾP (r.data CHÍNH LÀ payload). Tránh tái phạm LL list-wrap (đừng .data.data ở đây).
 */
export function getDashboardOverview({ auto = false, onError } = {}) {
  return createResource({
    url: 'crm.api.antmed.dashboard.overview',
    auto,
    onError,
  })
}

// ── Label maps (nhãn TĨNH khớp 100% options DocType JSON BE — VN có dấu) ─────
// Key tra cứu = giá trị EXACT BE; chỉ ánh xạ THEME/biến thể hiển thị, KHÔNG đổi key.

/** Theme Badge cho contract_status (Select: Đã ký / Tiềm năng / Hết hạn). */
export const CONTRACT_STATUS_THEME = {
  'Đã ký': 'green',
  'Tiềm năng': 'blue',
  'Hết hạn': 'red',
}

/** Theme Badge cho rank (Select: Đặc biệt / I / II / III / Khác). */
export const RANK_THEME = {
  'Đặc biệt': 'orange',
  I: 'blue',
  II: 'teal',
  III: 'gray',
  Khác: 'gray',
}

/**
 * Theme Badge cho status hợp đồng (M02 Select read-only — KHÔNG workflow ở M02-1).
 * KEY khớp EXACT options DocType `AntMed Contract.status` (VI có dấu — ADR-M02-04):
 *   Nháp / Hiệu lực / Sắp hết hạn / Hết hạn / Đã huỷ.
 * Status PHẢI kèm label chữ (Badge :label) — không phân biệt chỉ bằng màu (WCAG AA).
 */
export const CONTRACT_WORKFLOW_THEME = {
  Nháp: 'gray',
  'Hiệu lực': 'green',
  'Sắp hết hạn': 'orange',
  'Hết hạn': 'red',
  'Đã huỷ': 'gray',
}
