/**
 * AntMed CRM — neo dữ liệu nền (M01 Customer 360°).
 *
 * R1 (bootstrap): resource health.ping chứng minh đường FE → BE callable.
 * R2 (Customer 360°): factory tạo resource list/detail cho Bệnh viện + Bác sỹ,
 *   gọi đúng naming contract `antmed_crm.api.antmed.customer.<fn>` (in-place app crm).
 *
 * Convention (xem docs/antmed_crm/docs/m01_naming_conventions.md §5):
 *   - Resource url: 'antmed_crm.api.antmed.<module>.<fn>'  (in-place app crm, KHÔNG app riêng)
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
 * Health-check nền AntMed — GET antmed_crm.api.antmed.health.ping.
 * Trả RAW dict { app, status, version }. Caller bật `auto: true` hoặc `.fetch()`.
 */
export function getAntmedHealth() {
  return createResource({
    url: 'antmed_crm.api.antmed.health.ping',
    method: 'GET',
  })
}

// ── M01 R2: Customer 360° — Bệnh viện + Bác sỹ ──────────────────────────────

/**
 * Danh sách Bệnh viện — antmed_crm.api.antmed.customer.list_hospitals.
 * BE: list_hospitals(filters?, start?, page_length?, search?) -> { data, total_count }.
 * Item: name, hospital_name, rank, contract_status, tax_code. Invariant count==rows.
 *
 * @param {object} [opts]
 * @param {object} [opts.params] - params khởi tạo (search/filters/start/page_length).
 * @param {boolean} [opts.auto] - auto-fetch.
 */
export function listHospitals({ params = {}, auto = false } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.customer.list_hospitals',
    method: 'GET',
    params,
    auto,
  })
}

/**
 * Chi tiết Bệnh viện ("mặt 360") — antmed_crm.api.antmed.customer.get_hospital.
 * BE: get_hospital(name) -> field BV + doctors[] (name/full_name/specialty/phone).
 * throw frappe.PermissionError nếu không read được.
 */
export function getHospital({ params = {}, auto = false } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.customer.get_hospital',
    method: 'GET',
    params,
    auto,
  })
}

/**
 * Danh sách Bác sỹ — antmed_crm.api.antmed.customer.list_doctors.
 * BE: list_doctors(filters?, hospital?, start?, page_length?) -> { data, total_count }.
 * Item: name, full_name, specialty, hospital, phone (+ hospital_name nếu rẻ).
 */
export function listDoctors({ params = {}, auto = false } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.customer.list_doctors',
    method: 'GET',
    params,
    auto,
  })
}

/**
 * Chi tiết Bác sỹ — antmed_crm.api.antmed.customer.get_doctor.
 * BE: get_doctor(name) -> field bác sỹ + hospital_name (resolve qua Link).
 * throw frappe.PermissionError nếu không read được.
 */
export function getDoctor({ params = {}, auto = false } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.customer.get_doctor',
    method: 'GET',
    params,
    auto,
  })
}

// ── M02 Slice M02-1: Hợp đồng & Quota (read-only) ───────────────────────────

/**
 * Danh sách Hợp đồng — antmed_crm.api.antmed.contract.list_contracts.
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
    url: 'antmed_crm.api.antmed.contract.list_contracts',
    method: 'GET',
    params,
    auto,
  })
}

/**
 * Chi tiết Hợp đồng — antmed_crm.api.antmed.contract.get_contract.
 * BE: get_contract(name) -> field HĐ + hospital_name (resolve qua Link) + items[]
 *     (mỗi dòng item/item_name/uom/unit_price/quota_qty/used_qty/remaining_pct/lock_at_100).
 * throw frappe.PermissionError nếu không read được (FE bắt qua onError → toast).
 */
export function getContract({ params = {}, auto = false } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.contract.get_contract',
    method: 'GET',
    params,
    auto,
  })
}

/**
 * Tiêu hao HĐ theo tháng (mockup A1 bar chart, M02-6) —
 *   antmed_crm.api.antmed.contract.contract_consumption_by_month.
 * BE: contract_consumption_by_month(contract) -> RAW dict bọc {data, total_qty, contract}.
 *   data = ĐÚNG 12 bucket tháng (rolling 12 tháng tới tháng hiện tại), mỗi bucket
 *   { month: 'YYYY-MM', label: 'T<m>', qty: <float> }; tháng không có log → qty=0.0
 *   (KHÔNG bỏ cột). total_qty = SUM(qty) toàn cửa sổ. SUM gộp từ AntMed Quota Usage Log
 *   lọc theo contract (BE đã sort tăng dần theo tháng — FE KHÔNG sort lại).
 *
 * ⚠️ Mirror getContract: dict bọc → FE đọc `r.data.data` (mảng 12 bucket) + `r.data.total_qty`.
 *    (createResource, KHÔNG createListResource — frappe-ui coi response array sẽ vỡ shape bọc.)
 * BR-13 fail-closed: user KHÔNG read-perm HĐ → BE trả {data:[], total_qty:0, contract} → FE
 *    render nhánh empty (KHÔNG vỡ). Fetch ĐỘC LẬP với getContract (lỗi widget KHÔNG vỡ trang).
 *
 * @param {object} [opts]
 * @param {object} [opts.params] - params khởi tạo ({ contract }).
 * @param {boolean} [opts.auto] - auto-fetch.
 */
export function getContractConsumptionByMonth({
  params = {},
  auto = false,
} = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.contract.contract_consumption_by_month',
    method: 'GET',
    params,
    auto,
  })
}

/**
 * Sức khoẻ Hợp đồng (mockup A2, M02-2) — antmed_crm.api.antmed.contract.get_contract_health.
 * BE: get_contract_health(start, page_length) -> RAW dict bọc { data, total_count }.
 *   Mỗi item (Hyrum 10-key): name · contract_no · hospital · hospital_name · valid_to ·
 *   total_value · status · quota_used_pct (0–) · days_to_expiry (int|null) ·
 *   health_color ('green'|'orange'|'red' — cờ §7 BE đã quyết, FE chỉ map class).
 *
 * ⚠️ Cùng idiom listContracts: list bọc dict → đọc r.data.data + r.data.total_count
 *    (createResource, KHÔNG createListResource — frappe-ui coi response array sẽ vỡ shape bọc).
 *    Count đếm DƯỚI permission (BR-13) → invariant count==rows; noperm → rỗng (fail-closed).
 */
export function getContractHealth({ params = {}, auto = false } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.contract.get_contract_health',
    method: 'GET',
    params,
    auto,
  })
}

/**
 * Cảnh báo điều hành (mockup A1 widget ⚠, M02-3) — antmed_crm.api.antmed.contract.list_quota_alerts.
 * BE: list_quota_alerts() -> RAW dict bọc { data, total_count } (KHÔNG nhận tham số).
 *   Mỗi alert (Hyrum 10-key, thứ tự BE đã sort — FE GIỮ NGUYÊN, KHÔNG sort lại):
 *     kind ('quota'|'expiry') · contract · contract_no · hospital · hospital_name ·
 *     item · item_name · used_pct (quota) · threshold (quota: 70|90|100) · days_to_expiry (expiry).
 *   - Quota: used_pct ≥ 70 (band threshold cao nhất chạm); expiry: days_to_expiry ≤ 30 (gồm âm = quá hạn).
 *   - Sort BE: quota (threshold desc) trước, rồi expiry (days asc). FE render đúng thứ tự này.
 *
 * ⚠️ Cùng idiom getContractHealth: list bọc dict → đọc r.data.data + r.data.total_count
 *    (createResource, KHÔNG createListResource — frappe-ui coi response array sẽ vỡ shape bọc).
 *    Count đếm DƯỚI permission (BR-13) → invariant count==rows; noperm → rỗng (fail-closed).
 *
 * @param {object} [opts]
 * @param {boolean} [opts.auto] - auto-fetch.
 */
export function getQuotaAlerts({ auto = false } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.contract.list_quota_alerts',
    method: 'GET',
    auto,
  })
}

/**
 * Top 10 Bệnh viện theo doanh thu (mockup A1 widget, M02-4) —
 *   antmed_crm.api.antmed.contract.top_hospitals.
 * BE: top_hospitals(limit=10) -> RAW dict bọc { data, total_count }.
 *   Mỗi item (Hyrum 5-key): hospital · hospital_name · revenue · quota_used_pct · health_color.
 *   data ĐÃ sort GIẢM theo revenue + cắt ≤ limit ở BE ⇒ FE KHÔNG sort lại.
 *   total_count = số BV phân biệt trong scope (xếp-hạng-cắt-top ⇒ có thể > len(data); ADR-M02-09).
 *
 * ⚠️ Cùng idiom getContractHealth: list bọc dict → đọc r.data.data + r.data.total_count
 *    (createResource, KHÔNG createListResource — frappe-ui coi response array sẽ vỡ shape bọc).
 *    Gộp DƯỚI permission user (get_list, BR-13) → noperm → rỗng/raise (fail-closed).
 *
 * @param {object} [opts]
 * @param {object} [opts.params] - params khởi tạo ({ limit: 10 } mặc định; bỏ được — BE default 10).
 * @param {boolean} [opts.auto] - auto-fetch.
 */
export function getTopHospitals({ params = {}, auto = false } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.contract.top_hospitals',
    method: 'GET',
    params,
    auto,
  })
}

/**
 * Danh mục VT trúng thầu — top 5 theo % quota đã dùng (mockup A2 widget, M02-5) —
 *   antmed_crm.api.antmed.contract.top_quota_items.
 * BE: top_quota_items(limit=5) -> RAW dict bọc { data, total_count }.
 *   Mỗi item (Hyrum 6-key): item · item_name · quota_qty · used_qty · used_pct · health_color.
 *   used_pct gộp CROSS-CONTRACT theo item (100*SUM(used)/SUM(quota); 0.0 nếu SUM(quota)==0).
 *   data ĐÃ sort GIẢM theo used_pct + cắt ≤ limit ở BE ⇒ FE KHÔNG sort lại.
 *   total_count = số item phân biệt trong scope (xếp-hạng-cắt-top ⇒ có thể > len(data); ADR-M02-09).
 *
 * ⚠️ Cùng idiom getContractHealth: list bọc dict → đọc r.data.data + r.data.total_count
 *    (createResource, KHÔNG createListResource — frappe-ui coi response array sẽ vỡ shape bọc).
 *    Gộp DƯỚI permission user (get_list, BR-13) → noperm → rỗng/raise (fail-closed).
 *
 * @param {object} [opts]
 * @param {object} [opts.params] - params khởi tạo ({ limit: 5 } mặc định; bỏ được — BE default 5).
 * @param {boolean} [opts.auto] - auto-fetch.
 */
export function getTopQuotaItems({ params = {}, auto = false } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.contract.top_quota_items',
    method: 'GET',
    params,
    auto,
  })
}

/**
 * Cơ cấu doanh thu theo phân loại VTYT (mockup A2 widget CEO, M02-7) —
 *   antmed_crm.api.antmed.contract.revenue_mix.
 * BE: revenue_mix() -> RAW dict bọc { data, total_revenue }.
 *   data ĐÚNG 4 phần tử cố định thứ tự Loại A→B→C→D (kể cả lớp revenue=0 vẫn có).
 *   Mỗi dòng (Hyrum 4-key): classification · label · revenue · pct.
 *   pct = round(100*revenue/total_revenue, 1) (total==0 ⇒ mọi pct=0.0). FE KHÔNG sort/tính lại.
 *
 * ⚠️ Cùng idiom getTopHospitals: list bọc dict → đọc r.data.data + r.data.total_revenue
 *    (createResource, KHÔNG createListResource). Gộp DƯỚI permission user (get_list, BR-13)
 *    → noperm → fail-closed {data: 4 dòng 0, total_revenue: 0} (KHÔNG raise).
 *
 * ⚠️⚠️ BẮT BUỘC `method: 'GET'` (§1sext.bis / ADR-M02-14). `revenue_mix()` KHÔNG có params →
 *    frappe-ui createResource MẶC ĐỊNH gửi POST → BE @frappe.whitelist(methods=["GET"]) reject
 *    403 "Not permitted" (đã quan sát LIVE M02-4/M03-1/M02-5). PHẢI set method:'GET'.
 *
 * @param {object} [opts]
 * @param {boolean} [opts.auto] - auto-fetch.
 */
export function getRevenueMix({ auto = false } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.contract.revenue_mix',
    method: 'GET',
    auto,
  })
}

// ── M02 Slice M02-8: KPI "Doanh thu tháng" (hàng 1 Dashboard CEO — mockup A1) ─

/**
 * Doanh thu THÁNG hiện tại + delta MoM (KPI lớn hàng 1 "Doanh thu tháng — ▲% vs tháng trước",
 * mockup A1, M02-8) — antmed_crm.api.antmed.contract.monthly_revenue (GET).
 * BE: monthly_revenue() -> RAW dict THƯỜNG 5 key (Hyrum, KHÔNG bọc { data, total_count }):
 *   { current: float, previous: float, delta_pct: float|null, month_label: 'T<m>/<yyyy>',
 *     currency: 'VND' }
 *   current  = SUM(qty × unit_price) MỌI log AntMed Quota Usage Log ts trong THÁNG HIỆN TẠI;
 *   previous = cùng công thức cho CẢ THÁNG LIỀN TRƯỚC; delta_pct = round(100*(cur-prev)/prev,1)
 *   khi prev>0, null khi prev==0 (FE render '—' thay %, KHÔNG chia 0 / KHÔNG bịa).
 *
 * ⚠️ Dict THƯỜNG → đọc `r.data.current` / `r.data.delta_pct` / `r.data.month_label` TRỰC TIẾP
 *    (KHÔNG .data.data — cùng idiom getDashboardOverview/getRevenueMix, KHÁC list bọc dict).
 *    createResource (KHÔNG createListResource). FE KHÔNG tính lại current/previous/delta — chỉ
 *    format VND (formatVnMoney) + chọn mũi tên ▲/▼ theo dấu delta_pct (BR rollup ở BE).
 *
 * ⚠️⚠️ BẮT BUỘC `method: 'GET'` (endpoint @frappe.whitelist(methods=["GET"]) + KHÔNG params →
 *    createResource mặc định POST → BE reject 403 "Not permitted", như revenue_mix/team_roster).
 *
 * @param {object} [opts]
 * @param {boolean} [opts.auto] - auto-fetch.
 * @param {function} [opts.onError] - callback lỗi (toast).
 */
export function getMonthlyRevenue({ auto = false, onError } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.contract.monthly_revenue',
    method: 'GET',
    auto,
    onError,
  })
}

// ── M02 Slice M02-9: widget "Doanh thu theo Nhóm vật tư" (stacked-bar CEO — mockup A3) ─

/**
 * Doanh thu THẬT theo Nhóm phân loại VTYT × 12 tháng (widget stacked-bar — Dashboard CEO, mockup A3,
 * màn /antmed/revenue) — antmed_crm.api.antmed.contract.revenue_by_group (GET).
 * BE: revenue_by_group() -> RAW dict THƯỜNG 4 key (Hyrum, KHÔNG bọc { data, total_count }):
 *   {
 *     months: [12 str 'T<m>'],         # trục X, thứ tự thời gian TĂNG dần, cuối = tháng hiện tại
 *     groups: [{ classification, label, monthly: [12 number], total }],  # ĐÚNG 5 group A→B→C→D→Khác
 *     grand_total: number,
 *     currency: 'VND',
 *   }
 *   monthly[i] = SUM(qty × unit_price) các log AntMed Quota Usage Log ts rơi vào tháng bucket i,
 *   gộp theo classification của AntMed Item. groups LUÔN đủ 5 dòng (kể cả revenue=0).
 *
 * ⚠️ Dict THƯỜNG → đọc `r.data.months` / `r.data.groups` / `r.data.grand_total` TRỰC TIẾP
 *    (KHÔNG .data.data — cùng idiom getMonthlyRevenue/getRevenueMix, KHÁC list bọc dict).
 *    createResource (KHÔNG createListResource). FE KHÔNG sort/reduce/aggregate — đọc thẳng
 *    groups[].monthly (BE đã gộp bucket + classification). Chỉ map nhãn VI + vẽ chiều cao bar.
 *
 * ⚠️⚠️ BẮT BUỘC `method: 'GET'` (endpoint @frappe.whitelist(methods=["GET"]) + KHÔNG params →
 *    createResource mặc định gửi POST → BE reject 403 "Not permitted", như revenue_mix/monthly_revenue).
 *
 * @param {object} [opts]
 * @param {boolean} [opts.auto] - auto-fetch.
 * @param {function} [opts.onError] - callback lỗi (toast).
 */
export function getRevenueByGroup({ auto = false, onError } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.contract.revenue_by_group',
    method: 'GET',
    auto,
    onError,
  })
}

// ── M02 Slice M02-10: widget heat "Doanh thu theo NV Kinh doanh × Bệnh viện" (CEO — mockup A3) ─

/**
 * Doanh thu THẬT theo NV Kinh doanh (deal_owner) × Bệnh viện (organization) — ma trận heat
 * (widget Dashboard CEO, mockup A3, màn /antmed/revenue) —
 *   antmed_crm.api.antmed.sales_team.revenue_by_rep_hospital (GET).
 * BE: revenue_by_rep_hospital() -> RAW dict THƯỜNG 4 key (Hyrum, KHÔNG bọc { data, total_count }):
 *   {
 *     rows: [{ deal_owner, full_name, cells:[{hospital,hospital_label,value,heat}|null], total }],
 *     hospitals: [{ key, label }],   # cột BV (union), BE đã sort theo doanh thu cột DESC
 *     max_cell: number,              # cơ sở ngưỡng heat tương đối
 *     currency? KHÔNG có; grand_total: number,
 *   }
 *   - cell value = SUM(deal_value) CRM Deal status type 'Won' theo (deal_owner × organization);
 *     Deal Lost/Open BỊ LOẠI; ô không có Won → null (FE render '—', heat null).
 *   - heat ∈ HEAT_LEVELS (h2c..h5c) — 4 mức tương đối trên max_cell; FE map → heatCellClass.
 *   - rows BE đã sort DESC theo total (NV mạnh nhất lên đầu); total = SUM cells của NV.
 *   - full_name (KHÔNG lộ email deal_owner). FE KHÔNG reduce/sort/aggregate — đọc thẳng cells/total.
 *
 * ⚠️ Dict THƯỜNG → đọc `r.data.rows` / `r.data.hospitals` / `r.data.max_cell` / `r.data.grand_total`
 *    TRỰC TIẾP (KHÔNG .data.data — cùng idiom getRevenueByGroup/getMonthlyRevenue, KHÁC list bọc dict).
 *    createResource (KHÔNG createListResource).
 * ⚠️⚠️ BẮT BUỘC `method: 'GET'` (endpoint @frappe.whitelist(methods=["GET"]) + KHÔNG params →
 *    createResource mặc định POST → BE reject 403 "Not permitted", như revenue_by_group/team_roster).
 * BR-13 fail-closed: user KHÔNG read-perm CRM Deal → BE trả { rows:[], hospitals:[], max_cell:0,
 *    grand_total:0 } → FE render empty-state (KHÔNG vỡ).
 *
 * @param {object} [opts]
 * @param {boolean} [opts.auto] - auto-fetch.
 * @param {function} [opts.onError] - callback lỗi (toast).
 */
export function getRevenueByRepHospital({ auto = false, onError } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.sales_team.revenue_by_rep_hospital',
    method: 'GET',
    auto,
    onError,
  })
}

// ── M09 Slice M09-1: KPI "Tổng hoa hồng kỳ" + "Quy tắc kỳ" (Kế toán — mockup F2) ─

/**
 * Tổng hoa hồng kỳ + quy tắc kỳ (2 card header F2 "Hoa hồng Nhân viên", Kế toán, màn
 * /antmed/finance/commission) — antmed_crm.api.antmed.finance.commission_summary (GET).
 * BE: commission_summary(period?) -> RAW dict THƯỜNG 8 key (Hyrum, KHÔNG bọc { data, total_count }):
 *   {
 *     total_commission: number,   # round(SUM(deal_value × FLAT_RATE) Won kỳ, 0) — VND
 *     total_revenue: number,      # SUM(deal_value) CRM Deal Won closed_date trong kỳ (tháng hiện tại)
 *     rep_count: number,          # số deal_owner phân biệt có Won trong kỳ
 *     group_count: number,        # số nhóm trong quy tắc kỳ = len(rules)
 *     period_label: 'T<m>/<yyyy>',
 *     flat_rate_pct: number,      # FLAT_RATE × 100
 *     currency: 'VND',
 *     rules: [{ label: string, rate_pct: number }],   # mô tả quy tắc kỳ (FE render TỪ data THẬT)
 *   }
 *   total_commission/total_revenue/rep_count = 0 khi kỳ rỗng (KHÔNG null, KHÔNG lỗi).
 *
 * ⚠️ Dict THƯỜNG → đọc `r.data.total_commission` / `r.data.rep_count` / `r.data.rules` … TRỰC TIẾP
 *    (KHÔNG .data.data — cùng idiom getMonthlyRevenue/getRevenueByGroup, KHÁC list bọc dict).
 *    createResource (KHÔNG createListResource). FE KHÔNG sort/reduce/aggregate — BE đã gộp.
 * ⚠️⚠️ BẮT BUỘC `method: 'GET'` (endpoint @frappe.whitelist(methods=["GET"]); period optional →
 *    createResource mặc định POST → BE reject 403 "Not permitted", như monthly_revenue/team_roster).
 * BR-13 fail-closed: user thiếu read-perm CRM Deal → BE trả _empty_commission (mọi số = 0, rules
 *    giữ nguyên) → FE render '0 ₫' + danh sách quy tắc (KHÔNG vỡ, KHÔNG 500).
 *
 * @param {object} [opts]
 * @param {boolean} [opts.auto] - auto-fetch.
 * @param {function} [opts.onError] - callback lỗi (toast).
 */
export function getCommissionSummary({ auto = false, onError } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.finance.commission_summary',
    method: 'GET',
    auto,
    onError,
  })
}

// ── M03 Slice M03-1: Phiếu xuất gần đây (Thủ kho — widget kho) ───────────────

/**
 * Danh sách phiếu kho — antmed_crm.api.antmed.inventory.list_stock_entries (GET).
 * BE: list_stock_entries(entry_type?, filters?, start?, page_length?) -> { data, total_count }.
 *   Mỗi item (Hyrum 9-key): name · entry_type · from_warehouse · to_warehouse ·
 *   posting_datetime · docstatus · nv_employee · nv_employee_name (User.full_name) ·
 *   total_value (SUM child.amount; null nếu phiếu rỗng).
 *
 * Widget "Phiếu xuất gần đây" (Thủ kho) mặc định lọc entry_type='Xuất cho NV'.
 * ⚠️ List trả dict bọc → createResource đọc r.data.data + r.data.total_count
 *    (KHÔNG createListResource — frappe-ui coi response array sẽ vỡ shape bọc).
 *    Count đếm DƯỚI permission (BR-13) → invariant count==rows; noperm → rỗng (fail-closed).
 *
 * @param {object} [opts]
 * @param {object} [opts.params] - params khởi tạo (entry_type/filters/start/page_length).
 * @param {boolean} [opts.auto] - auto-fetch.
 */
export function listStockEntries({ params = {}, auto = false } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.inventory.list_stock_entries',
    method: 'GET',
    params,
    auto,
  })
}

// ── M03 Slice M03-2: Truy vết Lot (Thủ kho — mockup D3 "Thông tin lot") ──────

/**
 * Truy vết 1 lô — antmed_crm.api.antmed.inventory.get_lot (GET).
 * BE: get_lot(name) -> RAW dict THƯỜNG (KHÔNG bọc { data, total_count }):
 *   { name, lot_no, item, item_name, supplier, supplier_name, mfg_date, expiry_date,
 *     co_cert, cq_cert, recall_status, recall_reason, qty_in, qty_out, qty_remaining }.
 *   - item_name/supplier_name resolve qua Link (dotted-fetch, null-guard FK orphan).
 *   - qty_in = SUM(qty_change>0); qty_out = |SUM(qty_change<0)|; qty_remaining = SUM(qty_change)
 *     toàn kho cho lô (khớp sổ tồn AntMed Stock Ledger); lô không ledger → 0/0/0.
 *   - Lô không tồn tại → DoesNotExistError (FE bắt qua onError → nhánh not-found).
 *   - Fail-closed (BR-13): user không quyền đọc AntMed Lot → PermissionError.
 *
 * ⚠️ Dict THƯỜNG, KHÔNG bọc → FE đọc `r.data.qty_in` / `r.data.item_name`… TRỰC TIẾP
 *    (KHÔNG .data.data — cùng idiom getItem/getDashboardOverview, KHÁC list bọc dict).
 * auto:false — chỉ fetch khi bấm 'Truy vết' (`.submit({ name })` / `.fetch()`).
 *
 * @param {object} [opts]
 * @param {object} [opts.params] - params khởi tạo (name).
 * @param {boolean} [opts.auto] - auto-fetch (mặc định false).
 */
export function getLot({ params = {}, auto = false } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.inventory.get_lot',
    method: 'GET',
    params,
    auto,
  })
}

// ── M03 Slice M03-6: Cây truy vết (Thủ kho — mockup D3 right-card) ───────────

/**
 * Cây truy vết 1 lô — antmed_crm.api.antmed.inventory.lot_trace (GET).
 * BE: lot_trace(name) -> RAW dict THƯỜNG (KHÔNG bọc { data, total_count }):
 *   { lot, item, item_name, events:[{ posting_datetime, entry_type, direction(in|out),
 *     warehouse, warehouse_name, warehouse_type, qty, voucher_no, hospital, nv_employee }] }.
 *   - events = dòng thời gian di chuyển của lô (nhập NCC → xuất NV → chuyển kho/ký gửi BV),
 *     đã sort posting_datetime ASC ở BE → FE KHÔNG sort lại.
 *   - direction = 'in' nếu qty_change>0 ngược lại 'out'; qty = ABS(qty_change) (luôn dương).
 *   - Lô không tồn tại → DoesNotExistError (FE dùng chung nhánh not-found với getLot).
 *   - Lô tồn tại nhưng chưa có ledger → events:[] (FE empty-sub 'Chưa có lịch sử di chuyển').
 *   - BR-13 fail-closed: user thiếu read-perm Stock Ledger/Stock Entry/Warehouse → events:[]
 *     (KHÔNG lộ data; KHÔNG throw 500) — vẫn trả lot/item/item_name.
 *
 * ⚠️ Dict THƯỜNG, KHÔNG bọc → FE đọc `r.data.events` / `r.data.lot` / `r.data.item` / `r.data.item_name`
 *    TRỰC TIẾP (KHÔNG .data.data — cùng idiom getLot/getDashboardOverview, KHÁC list bọc dict).
 * auto:false — fetch CÙNG LÚC submit truy vết (cùng mã lô) với getLot. (createResource, KHÔNG list.)
 *
 * @param {object} [opts]
 * @param {object} [opts.params] - params khởi tạo (name == mã lô).
 * @param {boolean} [opts.auto] - auto-fetch (mặc định false).
 */
export function getLotTrace({ params = {}, auto = false } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.inventory.lot_trace',
    method: 'GET',
    params,
    auto,
  })
}

// ── M03 Slice M03-8: Chi tiết phiếu xuất (NV Kinh doanh — mockup C2 "Vật tư đã chuẩn bị") ──

/**
 * Chi tiết 1 phiếu xuất — antmed_crm.api.antmed.inventory.get_stock_entry (GET).
 * BE: get_stock_entry(name) -> RAW dict THƯỜNG (KHÔNG bọc { data, total_count }):
 *   { name, entry_type, posting_datetime, from_warehouse, to_warehouse, nv_employee,
 *     nv_employee_name, hospital, hospital_name, expected_use_date, total_value,
 *     items:[{ item, item_name, lot, lot_no, expiry_date, qty, uom, unit_price, amount, cocq_ok }] }.
 *   - Drill-down từ list "Phiếu xuất gần đây" → header phiếu + bảng dòng vật tư đã chuẩn bị (mockup C2).
 *   - item_name (AntMed Item) + lot_no/expiry_date (AntMed Lot) resolve THEO BATCH ở BE → FE chỉ render.
 *   - total_value = SUM(item.amount); phiếu 0 dòng → items:[] & total_value null (FE empty 'Phiếu chưa có vật tư').
 *   - cocq_ok pass-through (bool) → FE map chip CO/CQ (true→'CO/CQ ✓' / false|None→'Thiếu CO/CQ').
 *   - Phiếu không tồn tại → DoesNotExistError → FE empty-state 'Không tìm thấy phiếu'.
 *   - BR-13 fail-closed: user không read-perm phiếu → shape rỗng (header *_name null, items:[]) /
 *     PermissionError → FE map empty (KHÔNG rò header thật, KHÔNG 500).
 *
 * ⚠️ Dict THƯỜNG, KHÔNG bọc → FE đọc `r.data.items` / `r.data.name` / `r.data.hospital_name`… TRỰC TIẾP
 *    (KHÔNG .data.data — cùng idiom getLot/getLotTrace, KHÁC list bọc dict). method:'GET' tường minh.
 * auto:false — chỉ fetch khi mở route (onMounted/watch route.params.name → entry.submit({ name })).
 *
 * @param {object} [opts]
 * @param {object} [opts.params] - params khởi tạo ({ name == docname phiếu }).
 * @param {boolean} [opts.auto] - auto-fetch (mặc định false — cần params.name).
 */
export function getStockEntry({ params = {}, auto = false } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.inventory.get_stock_entry',
    method: 'GET',
    params,
    auto,
  })
}

// ── M03 Slice M03-7: Khởi tạo Recall theo lô (Thủ kho — mockup D3 chân card "Cây truy vết") ──

/**
 * Khởi tạo recall theo 1 lô — antmed_crm.api.antmed.inventory.initiate_recall (POST, MUTATION).
 * BE: initiate_recall(lot, reason, status) -> RAW dict THƯỜNG (KHÔNG bọc { data, total_count }):
 *   { name, recall_status, recall_reason }.
 *   - Lật AntMed Lot.recall_status sang 'Theo dõi' | 'Đã thu hồi' + ghi recall_reason +
 *     add_comment dòng thời gian (audit) bởi user hiện tại.
 *   - status ∈ {'Theo dõi','Đã thu hồi'} (RECALL_INITIATE_STATUSES); ngoài tập → ValidationError.
 *   - reason BẮT BUỘC; rỗng/khoảng trắng → ValidationError (validate FE + BE).
 *   - one-way: lô đã 'Đã thu hồi' → gọi lại = ValidationError (idempotent, không double-recall).
 *   - BR-13 fail-closed: user KHÔNG write-perm AntMed Lot → PermissionError → FE toast lỗi, KHÔNG đổi chip.
 *
 * ⚠️ MUTATION: gọi `.submit({ lot, reason, status })` (createResource method:'POST'). Dict THƯỜNG →
 *    đọc `r.data.recall_status` / `r.data.recall_reason` TRỰC TIẾP (KHÔNG .data.data — KHÁC list bọc).
 *    Sau success → reload getLot (chip recall_status trên card 'Thông tin lot' đổi màu).
 *
 * @param {object} [opts]
 * @param {object} [opts.params] - params khởi tạo (thường rỗng — truyền qua .submit).
 * @param {boolean} [opts.auto] - auto-fetch (mặc định false — chỉ submit khi xác nhận modal).
 */
export function initiateRecall({ params = {}, auto = false } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.inventory.initiate_recall',
    method: 'POST',
    params,
    auto,
  })
}

// ── M03 Slice M03-3: Kho ký gửi tại Bệnh viện (Thủ kho — mockup D2) ──────────

/**
 * Tồn ký gửi tại 1 BV — antmed_crm.api.antmed.inventory.consignment_stock (GET).
 * BE: consignment_stock(hospital) -> RAW dict THƯỜNG (KHÔNG bọc { data, total_count }):
 *   { hospital, hospitals:[{name, hospital_name}],
 *     kpis:{ hospitals_with_consignment, near_expiry_lots, total_value, total_sku, total_lots },
 *     rows:[{ sku, item_name, lot, expiry_date, system_qty, near_expiry }] }.
 *   - rows = tồn ký gửi của BV chọn (SUM(qty_change) theo kho ký gửi × item × lot, chỉ >0),
 *     đã sort HSD sớm nhất trước ở BE → FE KHÔNG sort lại.
 *   - near_expiry = expiry_date ≤ 90 ngày (cùng ngưỡng KPI + chip/highlight, BE đã quyết).
 *   - kpis (5 key — hàng KPI 3 thẻ mockup D2, toàn kho ký gửi mọi BV):
 *       hospitals_with_consignment = distinct BV có tồn>0; near_expiry_lots = số (BV,lô) cận ≤90 ngày;
 *       total_value = SUM(system_qty × AntMed Item.default_unit_price) (item thiếu giá → 0);
 *       total_sku = số item distinct tồn>0; total_lots = số dòng (item,lot) tồn>0.
 *   - hospital None → BE lấy BV đầu tiên (trả về hospital đã chọn trong r.data.hospital).
 *   - BR-13 fail-closed: user không read-perm AntMed Stock Ledger/Warehouse → {rows:[], kpis 5 key=0}
 *     → FE render nhánh empty + KPI '—'/0 (KHÔNG vỡ).
 *
 * ⚠️ Dict THƯỜNG, KHÔNG bọc → FE đọc `r.data.rows` / `r.data.kpis` / `r.data.hospitals`
 *    / `r.data.hospital` TRỰC TIẾP (KHÔNG .data.data — cùng idiom getLot/getDashboardOverview).
 * Đổi BV: cập nhật param hospital + reload (param phát đi == lựa chọn UI — chống dead-control).
 *
 * @param {object} [opts]
 * @param {object} [opts.params] - params khởi tạo ({ hospital }).
 * @param {boolean} [opts.auto] - auto-fetch.
 */
export function getConsignmentStock({ params = {}, auto = false } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.inventory.consignment_stock',
    method: 'GET',
    params,
    auto,
  })
}

// ── M03 Slice M03-4: Cảnh báo HSD (Thủ kho — mockup D1 sidebar "⚠ Cảnh báo HSD") ─────────

/**
 * Cảnh báo HSD — antmed_crm.api.antmed.inventory.expiry_alerts (GET).
 * BE: expiry_alerts() -> RAW dict THƯỜNG (KHÔNG bọc { data, total_count }):
 *   { kpis:{ expired, d30, d60, d90, total_lots },
 *     rows:[{ sku, item_name, lot, warehouse, warehouse_name, warehouse_type,
 *             expiry_date, balance_qty, days_to_expiry, severity }] }.
 *   - rows = lô CẬN/QUÁ date TOÀN bộ kho (Tổng + Cá nhân NV + Ký gửi BV): chỉ lô có
 *     SUM(balance_qty)>0 VÀ (expiry_date ≤ 90 ngày HOẶC đã quá hạn). BE đã sort
 *     days_to_expiry tăng dần (quá hạn lên đầu) → FE KHÔNG sort lại.
 *   - severity ∈ {expired (<0) / d30 (0..30) / d60 (31..60) / d90 (61..90)} — key kỹ thuật
 *     khớp BE, FE chỉ map sang chip/nhãn VI (expirySeverityChipTheme/Label).
 *   - KPI: expired/d30/d60/d90 = số LOT-warehouse từng tầng; total_lots = tổng dòng.
 *   - BR-13 fail-closed: user thiếu read-perm AntMed Stock Ledger/Lot/Warehouse → {rows:[],
 *     kpis tất cả 0} → FE render nhánh empty (KHÔNG vỡ).
 *
 * ⚠️ Dict THƯỜNG, KHÔNG bọc → FE đọc `r.data.rows` / `r.data.kpis` TRỰC TIẾP
 *    (KHÔNG .data.data — cùng idiom getLot/getConsignmentStock/getDashboardOverview).
 *    createResource (KHÔNG createListResource — frappe-ui coi response array sẽ vỡ shape bọc).
 *
 * @param {object} [opts]
 * @param {boolean} [opts.auto] - auto-fetch.
 */
export function getExpiryAlerts({ auto = false } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.inventory.expiry_alerts',
    method: 'GET',
    auto,
  })
}

// ── M10 Slice M10-1: "Quản lý Đội ngũ" (Trưởng phòng KD — mockup B2) ─────────

/**
 * Roster KPI đội ngũ NV kinh doanh — antmed_crm.api.antmed.sales_team.team_roster (GET).
 * BE: team_roster() -> RAW dict THƯỜNG (KHÔNG bọc { data, total_count }):
 *   { rows:[{ deal_owner, full_name, territory, month_sales, open_deals,
 *             sla_ontime_pct, sales_pct, bar_theme, alert }],
 *     kpis:{ total_reps, total_month_sales, avg_sla } }.
 *   - rows = 1 dòng/NV, gộp từ CRM Deal (deal_owner × deal_value × status × sla_status × territory):
 *       month_sales = SUM(deal_value) deal Won closed trong THÁNG HIỆN TẠI; open_deals = deal NOT IN
 *       Won/Lost; sla_ontime_pct = % deal sla_status != 'Failed'; sales_pct = % so đỉnh đội;
 *       bar_theme green/warn/danger theo ngưỡng 70/50; alert 'DS thấp' khi sales_pct<50 (rỗng nếu ổn).
 *       BE đã sort desc theo month_sales → FE KHÔNG sort lại.
 *   - NV có role 'NV kinh doanh' (kể cả 0 deal) vẫn xuất hiện (month_sales=0).
 *   - kpis: total_reps = số NV; total_month_sales = SUM(month_sales); avg_sla = trung bình sla_ontime_pct.
 *   - BR-13 fail-closed: user thiếu read-perm CRM Deal → { rows:[], kpis 3 key=0 } → FE render empty.
 *
 * ⚠️ Dict THƯỜNG, KHÔNG bọc → FE đọc `r.data.rows` / `r.data.kpis` TRỰC TIẾP
 *    (KHÔNG .data.data — cùng idiom getLot/getExpiryAlerts/getDashboardOverview).
 *    createResource (KHÔNG createListResource — frappe-ui coi response array sẽ vỡ shape bọc).
 *    ⚠️ method:'GET' (endpoint KHÔNG params; mặc định POST → 403 "Not permitted" như revenue_mix).
 *
 * @param {object} [opts]
 * @param {boolean} [opts.auto] - auto-fetch.
 */
export function getTeamRoster({ auto = false } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.sales_team.team_roster',
    method: 'GET',
    auto,
  })
}

// ── M10 Slice M10-2: "Bảng điều phối" (Trưởng phòng KD — mockup B1) ───────────

/**
 * Kanban READ-ONLY pipeline gói thầu — antmed_crm.api.antmed.sales_team.dispatch_board (GET).
 * BE: dispatch_board() -> RAW dict THƯỜNG (KHÔNG bọc { data, total_count }):
 *   { lanes:[{ status, type, label, position, count, cards:[
 *               { deal, organization, territory, deal_owner_name, deal_value,
 *                 probability, bar_theme } ] }],
 *     totals:{ total_deals, open_value, won_value } }.
 *   - lanes = CRM Deal Status type ∈ (Open,Ongoing,Won) — LOẠI Lost; sort tăng theo position
 *     (Qualification → … → Won). label = nhãn VI cấu hình; count = số card trong lane.
 *   - cards = CRM Deal group theo status, BE đã sort DESC deal_value → FE KHÔNG sort/aggregate lại.
 *       deal_owner_name = full_name (KHÔNG lộ email; FE chỉ dùng `deal` làm :key);
 *       bar_theme green/warn/danger theo ngưỡng probability 70/40 (BE quyết, FE chỉ map class).
 *   - totals: total_deals = tổng card; open_value = SUM lane Open/Ongoing; won_value = SUM lane Won.
 *   - BR-13 fail-closed: user thiếu read-perm CRM Deal → { lanes:[], totals zero } → FE render empty.
 *
 * ⚠️ Dict THƯỜNG, KHÔNG bọc → FE đọc `r.data.lanes` / `r.data.totals` TRỰC TIẾP
 *    (KHÔNG .data.data — cùng idiom getTeamRoster/getDashboardOverview).
 *    createResource (KHÔNG createListResource). method:'GET' (endpoint KHÔNG params).
 *
 * @param {object} [opts]
 * @param {boolean} [opts.auto] - auto-fetch.
 */
export function getDispatchBoard({ auto = false } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.sales_team.dispatch_board',
    method: 'GET',
    auto,
  })
}

/**
 * Bảng điều phối ca giao phòng mổ (mockup B1) — antmed_crm.api.antmed.delivery.dispatch_board (GET).
 * BE trả RAW dict { columns, lanes:[{key,label,count,cards:[...]}], total, totals{total,urgent} }.
 * FE đọc r.data.lanes (ĐÚNG 4 cột B1) + r.data.totals TRỰC TIẾP (dict THƯỜNG — KHÔNG .data.data).
 * card: hospital_name, doctor_name, surgery_datetime, sku_count, assigned_employee_name, urgency.
 */
export function getDeliveryDispatchBoard({ auto = false } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.delivery.dispatch_board',
    method: 'GET',
    auto,
  })
}

// ── M10 Slice M10-3: "Hồ sơ NV kinh doanh" (Trưởng phòng KD — mockup B2 left-card) ─

/**
 * Hồ sơ 1 NV kinh doanh (drill-down từ roster) — antmed_crm.api.antmed.sales_team.rep_profile (GET).
 * BE: rep_profile(owner) -> RAW dict THƯỜNG (KHÔNG bọc { data, total_count }):
 *   { profile:{ deal_owner, full_name, joined_on, roles:[...] },
 *     kpi:{ month_sales, open_deals, total_deals, sla_ontime_pct },
 *     deals:[{ deal, organization, territory, deal_value, status, probability }] }.
 *   - kpi tái dùng ĐÚNG công thức team_roster: month_sales = SUM(deal_value) Won closed trong THÁNG
 *     hiện tại; open_deals = deal NOT IN Won/Lost; sla_ontime_pct = % sla_status != 'Failed'
 *     (total=0 → 100.0, KHÔNG chia 0); total_deals = tổng deal của owner.
 *   - deals = CRM Deal của owner đọc DƯỚI permission, BE đã sort DESC deal_value → FE KHÔNG sort lại.
 *     KHÔNG chứa deal_owner (email) — chống lộ email.
 *   - profile.full_name = User.full_name (KHÔNG lộ email); joined_on = User.creation (date);
 *     roles = role nghiệp vụ. owner không-User → full_name fallback owner, joined_on null, roles [].
 *   - BR-13 fail-closed: user thiếu read-perm CRM Deal → kpi zero + deals [] (KHÔNG raise) → FE empty.
 *
 * ⚠️ Dict THƯỜNG, KHÔNG bọc → FE đọc `r.data.profile` / `r.data.kpi` / `r.data.deals` TRỰC TIẾP
 *    (KHÔNG .data.data — cùng idiom getTeamRoster/getDashboardOverview, KHÁC list bọc dict).
 *    createResource (KHÔNG createListResource). method:'GET' + params.owner (truyền 1 param scalar).
 *
 * @param {string} owner - email deal_owner (param scalar; FE KHÔNG hiển thị email thô).
 * @param {object} [opts]
 * @param {boolean} [opts.auto] - auto-fetch.
 * @param {function} [opts.onError] - callback lỗi (toast).
 */
export function getRepProfile(owner, { auto = false, onError } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.sales_team.rep_profile',
    method: 'GET',
    params: { owner },
    auto,
    onError,
  })
}

// ── M11 Slice 2: Dashboard A1 — số liệu tổng quan ───────────────────────────

/**
 * Số liệu tổng quan dashboard A1 — antmed_crm.api.antmed.dashboard.overview (GET).
 * BE: overview() -> RAW dict THƯỜNG { hospital_count: int, doctor_count: int }
 *     (đếm DƯỚI permission user — invariant count==rows như customer.py).
 *
 * ⚠️ KHÁC list endpoint (list_hospitals/list_doctors bọc { data, total_count } → đọc r.data.data):
 *    overview trả dict THƯỜNG, KHÔNG bọc → FE đọc `r.data.hospital_count` / `r.data.doctor_count`
 *    TRỰC TIẾP (r.data CHÍNH LÀ payload). Tránh tái phạm LL list-wrap (đừng .data.data ở đây).
 */
export function getDashboardOverview({ auto = false, onError } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.dashboard.overview',
    method: 'GET',
    auto,
    onError,
  })
}

/**
 * KPI quota + cảnh báo điều hành A1 — antmed_crm.api.antmed.dashboard.quota_summary (GET).
 * BE: quota_summary() -> RAW dict THƯỜNG 3 key:
 *   { avg_quota_used_pct: float, contracts_over_90_count: int,
 *     alerts: [{ type: 'expiry'|'quota'|'over_cap', severity: 'danger'|'warn', contract, label }] (≤6) }
 *   (gộp DƯỚI permission từ get_contract_health — fail-closed: noperm → 0.0/0/[], BR-13).
 *
 * ⚠️ Dict THƯỜNG, KHÔNG bọc { data, total_count } → đọc `r.data.avg_quota_used_pct` /
 *    `r.data.contracts_over_90_count` / `r.data.alerts` TRỰC TIẾP (KHÔNG .data.data) —
 *    cùng idiom getDashboardOverview. label đã là chuỗi VI BE render → hiển thị thẳng.
 */
export function getQuotaSummary({ auto = false, onError } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.dashboard.quota_summary',
    method: 'GET',
    auto,
    onError,
  })
}

/**
 * Funnel "Pipeline gói thầu" A1 (M08) — antmed_crm.api.antmed.dashboard.tender_pipeline (GET).
 * BE: tender_pipeline() -> RAW dict THƯỜNG 2 key:
 *   { stages: [{ key: 'lead'|'survey'|'quote'|'bid'|'won',
 *                label: 'Lead'|'Khảo sát'|'Báo giá'|'Dự thầu'|'Trúng',
 *                count: int }] (đúng 5 phần tử, đúng thứ tự funnel),
 *     total: int }
 *   count = SỐ THẬT đếm từ CRM Lead status (lead/survey) + CRM Deal status (quote/bid/won),
 *   đếm DƯỚI permission (BR-13) — user thiếu read Lead/Deal → tầng đó count=0, total=0 (fail-soft).
 *
 * ⚠️ Dict THƯỜNG, KHÔNG bọc { data, total_count } → đọc `r.data.stages` / `r.data.total`
 *    TRỰC TIẾP (KHÔNG .data.data) — cùng idiom getDashboardOverview/getQuotaSummary.
 *    ⚠️ method:'GET' (endpoint KHÔNG params; mặc định POST → 403 "Not permitted" như revenue_mix).
 */
export function getTenderPipeline({ auto = false, onError } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.dashboard.tender_pipeline',
    method: 'GET',
    auto,
    onError,
  })
}

// ── M07-1: Portal Bệnh viện "📰 Thông báo gần đây" (mockup G1, id=bv) ─────────

/**
 * Thông báo gần đây của 1 bệnh viện (card timeline Portal BV, mockup G1) —
 *   antmed_crm.api.antmed.customer.portal_notifications (GET).
 * BE: portal_notifications(hospital) -> RAW dict THƯỜNG (KHÔNG bọc { data, total_count }):
 *   { data: [{ kind, ts, title, ref }], hospital, hospital_name }.
 *   - data = rollup THẬT các sự kiện của BV (merge → sort ts GIẢM → cắt top PORTAL_NOTIF_LIMIT=10):
 *       delivery = AntMed Stock Entry entry_type='Xuất cho NV' của BV — title 'Phiếu giao <số> đã
 *                  xuất cho NV', ts=posting_datetime, ref=số phiếu.
 *       quota    = quota item HĐ của BV có used_pct ở band cảnh báo (>=70%) — title
 *                  'Quota <item_name> còn <100-used_pct>%', ref=mã item.
 *     Mỗi item shape ổn định (Hyrum) ≥4 key: kind ('delivery'|'quota') · ts (datetime) · title (VI)
 *     · ref (str|None). FE KHÔNG sort/aggregate — BE đã gộp; chỉ format ts (formatNotifTime) + render.
 *   - BR-13 fail-closed: user thiếu read-perm Stock Entry/Contract → BE trả { data:[], hospital,
 *     hospital_name } → FE render nhánh empty 'Chưa có thông báo' (KHÔNG vỡ, KHÔNG 500).
 *
 * ⚠️ Dict THƯỜNG (KHÔNG bọc list) → FE đọc `r.data.data` (mảng sự kiện) + `r.data.hospital_name`
 *    TRỰC TIẾP. Đây LÀ trường hợp shape bọc { data, ... } NHƯNG createResource — frappe-ui
 *    auto-unwrap {message} → r.data == payload BE; payload.data = mảng. Đọc r.data.data (đúng shape BE).
 * ⚠️⚠️ BẮT BUỘC `method: 'GET'` (endpoint @frappe.whitelist(methods=["GET"]); params.hospital scalar
 *    nhưng createResource có thể gửi POST → BE reject 403 — set GET tường minh).
 *
 * @param {object} [opts]
 * @param {object} [opts.params] - params khởi tạo ({ hospital }).
 * @param {boolean} [opts.auto] - auto-fetch.
 * @param {function} [opts.onError] - callback lỗi (toast).
 */
export function getPortalNotifications({
  params = {},
  auto = false,
  onError,
} = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.customer.portal_notifications',
    method: 'GET',
    params,
    auto,
    onError,
  })
}

// ── M07-2: Portal BV widget "📋 Danh mục vật tư trúng thầu" (mockup G1) ───────

/**
 * Danh mục vật tư trúng thầu của 1 bệnh viện (card catalog Portal BV, mockup G1
 * "Form gọi vật tư") — antmed_crm.api.antmed.customer.tender_catalog (GET).
 * BE: tender_catalog(hospital) -> RAW dict THƯỜNG (KHÔNG bọc { data, total_count }):
 *   { hospital, hospital_name, contract, items:[{ item, item_name, uom,
 *     remaining_qty, quota_qty, used_qty, remaining_pct, quota_chip }] }.
 *   - items = TẤT CẢ AntMed Quota Item của HĐ status ∈ {Hiệu lực, Sắp hết hạn} của BV
 *     (gộp nhiều HĐ active; LOẠI Nháp/Hết hạn/Đã huỷ). BE đã gộp — FE KHÔNG aggregate.
 *   - quota_chip phân tầng THẬT theo remaining_pct ('ok' >10 / 'warn' >0 & ≤10 / 'danger' ≤0):
 *     FE đọc thẳng quota_chip → map theme/nhãn (KHÔNG tự tính lại ngưỡng).
 *   - KHÔNG có HĐ active → { contract: null, items: [] } → FE empty-state actionable.
 *   - KHÔNG trả unit_price (data-scope portal BV — KHÔNG hiển thị giá đơn vị).
 *
 * ⚠️ Dict THƯỜNG → FE đọc `r.data.items` / `r.data.hospital_name` / `r.data.contract`
 *    TRỰC TIẾP (KHÔNG .data.data — KHÁC list bọc dict). createResource (KHÔNG list-resource).
 * ⚠️⚠️ BẮT BUỘC `method: 'GET'` (endpoint @frappe.whitelist(methods=["GET"]); params.hospital
 *    scalar nhưng createResource có thể gửi POST → BE reject 403 — set GET tường minh).
 *    auto theo !!hospital (mirror getPortalNotifications) — param phát đi == lựa chọn UI.
 *
 * @param {object} [opts]
 * @param {object} [opts.params] - params khởi tạo ({ hospital }).
 * @param {boolean} [opts.auto] - auto-fetch.
 * @param {function} [opts.onError] - callback lỗi (toast).
 */
export function getTenderCatalog({ params = {}, auto = false, onError } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.customer.tender_catalog',
    method: 'GET',
    params,
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

// ── M04 Slice S1: Giao phòng mổ (Delivery, read-only) ───────────────────────

/**
 * Danh sách phiếu giao phòng mổ — antmed_crm.api.antmed.delivery.list_deliveries.
 * BE: list_deliveries(filters?, status?, hospital?, start?, page_length?) -> { data, total_count }.
 * Item 8 field: name, hospital, hospital_name, doctor, surgery_datetime, status, sla_status, assigned_employee.
 * ⚠️ Lọc trạng thái dùng param `status` (string) — KHÔNG object filters (tránh "[object Object]").
 */
export function listDeliveries({ params = {}, auto = false } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.delivery.list_deliveries',
    method: 'GET',
    params,
    auto,
  })
}

/**
 * Chi tiết phiếu giao — antmed_crm.api.antmed.delivery.get_delivery.
 * BE: get_delivery(name) -> field phiếu giao + hospital_name/doctor_name + items[].
 * throw PermissionError nếu không read (FE bắt qua onError → toast).
 */
export function getDelivery({ params = {}, auto = false } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.delivery.get_delivery',
    method: 'GET',
    params,
    auto,
  })
}

/**
 * Thứ tự + theme Badge cho status phiếu giao. KEY khớp EXACT options DocType
 * `AntMed Delivery.status` (VI có dấu) == delivery.py STATUS_ORDER. WCAG AA: luôn kèm label chữ.
 */
export const DELIVERY_STATUS_ORDER = [
  'Nháp',
  'Đã phân loại',
  'Đã gán NV',
  'Đang giao',
  'Đã bàn giao',
  'Đã đóng',
  'Từ chối',
]

export const DELIVERY_STATUS_THEME = {
  Nháp: 'gray',
  'Đã phân loại': 'blue',
  'Đã gán NV': 'teal',
  'Đang giao': 'orange',
  'Đã bàn giao': 'green',
  'Đã đóng': 'gray',
  'Từ chối': 'red',
}

/** Theme + nhãn VN cho sla_status (Select BE: OnTime / Late). */
export const SLA_STATUS_THEME = {
  OnTime: 'green',
  Late: 'red',
}
export const SLA_STATUS_LABEL = {
  OnTime: 'Đúng giờ',
  Late: 'Trễ',
}

// ── M05: Bộ dụng cụ (Instrument Set/Loan) — màn I1 vòng đời + C3 checklist ───

/**
 * I1 — bảng vòng đời bộ dụng cụ. GET antmed_crm.api.antmed.instrument_loan.board.
 * RAW dict { kpis:{total,in_circulation,ready,issue}, sets:[…], frequency:[…] }
 * → đọc r.data.kpis / r.data.sets / r.data.frequency (KHÔNG .data.data).
 */
export function getInstrumentBoard({ params = {}, auto = false } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.instrument_loan.board',
    method: 'GET',
    params,
    auto,
  })
}

/** Chi tiết 1 bộ + components[] + loans[]. GET ...instrument_loan.get_instrument_set. */
export function getInstrumentSet({ params = {}, auto = false } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.instrument_loan.get_instrument_set',
    method: 'GET',
    params,
    auto,
  })
}

/** Chi tiết 1 lượt mượn (C3) + handover/return checklist. GET ...instrument_loan.get_loan. */
export function getInstrumentLoan({ params = {}, auto = false } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.instrument_loan.get_loan',
    method: 'GET',
    params,
    auto,
  })
}

/**
 * Trục vòng đời chuẩn (6 bước) — KEY khớp EXACT options DocType
 * `AntMed Instrument Set.current_status` / `AntMed Instrument Loan.status` (VI có dấu).
 * `short` = nhãn rút gọn cho thanh lifecycle (mockup I1: SS · Đặt · Giao · SD · Trả · Xử lý).
 */
export const INSTRUMENT_LIFECYCLE = [
  { key: 'Sẵn sàng', short: 'SS' },
  { key: 'Đã đặt', short: 'Đặt' },
  { key: 'Đang giao', short: 'Giao' },
  { key: 'Đang sử dụng tại BV', short: 'SD' },
  { key: 'Đã trả về NV KD', short: 'Trả' },
  { key: 'Đang xử lý/tiệt khuẩn', short: 'Xử lý' },
]

/** Theme Badge cho trạng thái bộ/lượt mượn. WCAG AA: luôn kèm label chữ (status VI). */
export const INSTRUMENT_STATUS_THEME = {
  'Sẵn sàng': 'green',
  'Đã đặt': 'blue',
  'Đang giao': 'orange',
  'Đang sử dụng tại BV': 'teal',
  'Đã trả về NV KD': 'blue',
  'Đang xử lý/tiệt khuẩn': 'orange',
  'Đã đóng': 'gray',
  'Sự cố': 'red',
  Mất: 'red',
  Hỏng: 'red',
}

/** Theme cho tình trạng món trong checklist (Select BE: OK / Missing / Damaged). */
export const COMPONENT_CONDITION_THEME = {
  OK: 'green',
  Missing: 'red',
  Damaged: 'orange',
}

// ── M06-1: màn "Hàng chờ phát hành chứng từ" (persona Chứng từ/Pháp lý — mockup E1) ──

/**
 * KPI rollup màn Hàng chờ phát hành (E1) — antmed_crm.api.antmed.documents.release_queue_summary (GET).
 * BE: release_queue_summary() -> RAW dict THƯỜNG 3 key CỐ ĐỊNH (Hyrum-safe, KHÔNG bọc {data,total_count}):
 *   { missing_co: int, missing_cq: int, ready_to_release: int }
 *   - missing_co       = số hàng chờ có 'CO' trong missing_chips.
 *   - missing_cq       = số hàng chờ có 'CQ' trong missing_chips.
 *   - ready_to_release = số hàng chờ status='Chờ phát hành' AND missing_chips rỗng (đủ CO+CQ).
 *   Đếm DƯỚI DocPerm (BR-13) → khớp số dòng list_release_queue user được phép thấy.
 *   Fail-closed: user KHÔNG read-perm → {0,0,0} (KHÔNG throw) → FE render 3 số 0 (KHÔNG vỡ).
 *
 * ⚠️ Dict THƯỜNG → đọc r.data.missing_co / r.data.missing_cq / r.data.ready_to_release TRỰC TIẾP
 *    (KHÔNG .data.data — khác list bọc dict). createResource (KHÔNG createListResource).
 * ⚠️⚠️ BẮT BUỘC method:'GET' (@frappe.whitelist(methods=["GET"]) + KHÔNG params → createResource
 *    mặc định POST → BE reject 403 "Not permitted").
 *
 * @param {object} [opts]
 * @param {boolean} [opts.auto] - auto-fetch.
 * @param {function} [opts.onError] - callback lỗi (toast).
 */
export function getReleaseQueueSummary({ auto = false, onError } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.documents.release_queue_summary',
    method: 'GET',
    auto,
    onError,
  })
}

/**
 * Worklist Hàng chờ phát hành (E1) — antmed_crm.api.antmed.documents.list_release_queue (GET).
 * BE: list_release_queue(status?, start?, page_length?) -> RAW dict bọc { data, total_count }.
 *   Mỗi dòng: name, delivery, document_bundle, status, missing_chips (chuỗi JSON list),
 *     assigned_to, ts, hospital_name (resolve qua delivery→hospital), assigned_employee (NV — User).
 *   Count==rows dưới DocPerm (BR-13). status (Select VI) filter tuỳ chọn.
 *
 * ⚠️ List bọc dict → đọc r.data.data + r.data.total_count (createResource, KHÔNG createListResource).
 * ⚠️ method:'GET' (@frappe.whitelist(methods=["GET"])). Lọc bằng param `status` (string) — KHÔNG
 *    object filters (createResource GET serialize object thô thành "[object Object]" → BE parse lỗi).
 *
 * @param {object} [opts]
 * @param {object} [opts.params] - params khởi tạo ({ status?, start?, page_length? }).
 * @param {boolean} [opts.auto] - auto-fetch.
 * @param {function} [opts.onError] - callback lỗi (toast).
 */
export function getReleaseQueue({ params = {}, auto = false, onError } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.documents.list_release_queue',
    method: 'GET',
    params,
    auto,
    onError,
  })
}

// ── H1: Quản trị User & Role (admin RBAC) ────────────────────────────────────

/** Danh sách user + role + scope + 2FA + enabled. GET admin.list_users (admin-gated). */
export function getAdminUsers({ params = {}, auto = false, onError } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.admin.list_users',
    method: 'GET',
    params,
    auto,
    onError,
  })
}

/** Role gán được + theme pill. GET admin.list_roles. */
export function getAdminRoles({ auto = false } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.admin.list_roles',
    method: 'GET',
    auto,
  })
}

/** Ma trận quyền (Module × R/C/U/D) cho 1 role. GET admin.role_permissions(role). */
export function getRolePermissions({ params = {}, auto = false } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.admin.role_permissions',
    method: 'GET',
    params,
    auto,
  })
}

/** Theme pill cho role (single-source khớp admin.ROLE_THEME ở BE). */
export const ROLE_PILL_THEME = {
  'Quản lý': 'orange',
  'Sales Manager': 'orange',
  'NV kinh doanh': 'blue',
  'Sales User': 'blue',
  'Thủ kho': 'gray',
}

// ── Hồ sơ user hiện tại (topbar avatar + trang /antmed/profile) ──────────────

/** Hồ sơ user đang đăng nhập (Frappe User). GET profile.me. RAW dict → đọc r.data.* */
export function getMyProfile({ auto = false, onError } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.profile.me',
    method: 'GET',
    auto,
    onError,
  })
}

/** Initials từ full_name (vd "Chu Hiếu" → "CH"). Dùng cho avatar topbar. */
export function userInitials(fullName) {
  const parts = String(fullName || '')
    .trim()
    .split(/\s+/)
    .filter(Boolean)
  if (!parts.length) return 'U'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

// ── M08: Pipeline gói thầu (AntMed Tender) + Lead (kế thừa CRM Lead) ──────────

/** Danh sách gói thầu (RAW {data,total_count}). GET pipeline.list_tenders. */
export function listTenders({ params = {}, auto = false } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.pipeline.list_tenders',
    method: 'GET',
    params,
    auto,
  })
}

/** Dự báo doanh số pipeline (RAW {total_weighted, by_stage}). GET pipeline.forecast. */
export function getTenderForecast({ auto = false } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.pipeline.forecast',
    method: 'GET',
    auto,
  })
}

/** Danh sách Lead (CRM Lead scoped). GET pipeline.list_leads. */
export function listLeads({ params = {}, auto = false } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.pipeline.list_leads',
    method: 'GET',
    params,
    auto,
  })
}

/** Trạng thái Lead (CRM Lead Status). GET pipeline.lead_statuses. */
export function getLeadStatuses({ auto = false } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.pipeline.lead_statuses',
    method: 'GET',
    auto,
  })
}

/** 6 giai đoạn pipeline gói thầu — KEY khớp EXACT status AntMed Tender (pipeline.py _STAGES). */
export const TENDER_STAGES = [
  'Tiếp cận',
  'Khảo sát',
  'Báo giá',
  'Dự thầu',
  'Trúng',
  'Trượt',
]
export const TENDER_STAGE_THEME = {
  'Tiếp cận': 'gray',
  'Khảo sát': 'blue',
  'Báo giá': 'orange',
  'Dự thầu': 'teal',
  Trúng: 'green',
  Trượt: 'red',
}

/** Theme Badge cho status Lead (CRM Lead Status). */
export const LEAD_STATUS_THEME = {
  New: 'blue',
  Contacted: 'orange',
  Nurture: 'purple',
  Qualified: 'teal',
  Converted: 'green',
  Unqualified: 'gray',
  Junk: 'red',
}

/**
 * AntMed — Công việc (Task) trên CRM Task: antmed_crm.api.antmed.tasks.list_tasks (GET).
 * RAW dict { data:[{...,assigned_to_name,is_open}], total_count, open_count }. method:'GET' bắt buộc
 * (endpoint GET-only — POST mặc định của frappe-ui sẽ 403). filters object PHẢI JSON.stringify.
 */
export function getTasks({ auto = false, status, filters } = {}) {
  // CHỈ gửi param ĐÃ định nghĩa — KHÔNG để {status: undefined} → serialize thành chuỗi
  // "undefined" → BE lọc status="undefined" → 0 dòng (dù DB có data). filters PHẢI JSON.stringify.
  const params = {}
  if (status) params.status = status
  if (filters) params.filters = JSON.stringify(filters)
  return createResource({
    url: 'antmed_crm.api.antmed.tasks.list_tasks',
    method: 'GET',
    params,
    auto,
  })
}

/** Theme Badge cho status công việc (CRM Task workflow). */
export const TASK_STATUS_THEME = {
  Backlog: 'gray',
  Todo: 'blue',
  'In Progress': 'orange',
  Done: 'green',
  Canceled: 'red',
}

/** Theme Badge cho mức ưu tiên công việc. */
export const TASK_PRIORITY_THEME = {
  Low: 'gray',
  Medium: 'blue',
  High: 'red',
}

/**
 * Quick-search command palette (header) — antmed_crm.api.antmed.search.global_search (GET).
 * BE trả RAW dict { hospitals: [...], contracts: [...] } (KHÔNG bọc data/total_count) →
 * đọc r.data.hospitals / r.data.contracts trực tiếp. Gọi `.submit({query, limit})` mỗi lần gõ.
 * ⚠️ PHẢI method:'GET' (createResource mặc định POST → BE methods=["GET"] reject 403).
 */
export function useGlobalSearch() {
  return createResource({
    url: 'antmed_crm.api.antmed.search.global_search',
    method: 'GET',
  })
}
