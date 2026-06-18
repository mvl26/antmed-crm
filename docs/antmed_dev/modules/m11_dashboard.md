# M11 — Báo cáo & Dashboard điều hành (Core Doc)

| Mục | Giá trị |
|---|---|
| Module folder | `crm/antmed/` (module Frappe **`AntMed`**) — **M11 KHÔNG thêm DocType**, chỉ thêm API + (tùy chọn) scheduler |
| Code path | `crm/api/antmed/dashboard.py` (đường gọi `antmed_crm.api.antmed.dashboard.<fn>`) · scheduler `crm/antmed/m11_dashboard.py` (tùy chọn digest) |
| FE pages | **FE Slice 2 (NOW):** viết lại `frontend/src/pages/AntmedHome.vue` (route `/antmed`, shell A1). **W4 [PLANNED]:** `AntmedDashboardCEO.vue`, `AntmedDashboardWarehouse.vue`, `AntmedDashboardInstrument.vue`, `AntmedDashboardSLA.vue`, `AntmedReportCompliance.vue` · route `/antmed/dashboard*`, `/antmed/reports/compliance` |
| Wave (PLAN) | **FE Slice 2 (shell A1 + `overview()` count thật) = BUILDABLE NOW** (chỉ M01) · phần đầy đủ ở **W4 — Tăng trưởng & kiểm soát** |
| Role chính (VI) | `Quản lý` (CEO/BGĐ + Trưởng phòng KD) · đọc-có-scope cho `NV kinh doanh` / `Thủ kho` *(xem §4)* |
| Phụ thuộc (M..) | **M02** (Hợp đồng/Quota), **M04** (Giao phòng mổ/SLA), **M09** (Đơn/Công nợ/AR), **M10** (KPI) — và đọc lan sang M03 (kho/lot), M05 (bộ mượn), M06 (chứng từ), M08 (pipeline) cho widget tương ứng |
| Cấp dữ liệu cho (M..) | — (M11 là tầng tổng hợp/đọc cuối DAG, không feed module khác) |
| Trạng thái | **FE Slice 2 = SPEC CHỐT (codeable now)** — `overview()` + shell A1; phần W4 còn **[PLANNED — chưa code]** · API-only (KHÔNG doctype) |
| Cập nhật | 2026-06-17 |

> **FE Slice 2 (`overview()` + shell A1 trên `AntmedHome`) = spec đầy đủ, codeable ngay** (xem §5.A · §7.A · §8.A · ADR-M11-03). Phần dưới đây (`ceo_kpis` và các dashboard chuyên đề) vẫn ↓
> **Trạng thái: [PLANNED — chưa code]**
> Module này **chưa được code** trong app `crm`. Toàn bộ schema/API/widget dưới đây là **DESIGN (đề xuất)** để factory build, ground trên `../../antmed_crm/docs/AntMed_CRM_Modules.md §11`, `../PLAN_AntMed_CRM.md` (hàng M11), `../../antmed_crm/docs/AntMed_CRM_UI_Design.md §1` (widget CEO) và scaffold tham chiếu `antmed_crm/m11_dashboard/` (bản app-riêng cũ — đã **adapt**: `AM `→`AntMed `, bỏ ERPNext-reuse `Sales Invoice`/`Delivery Note`/`AM Instrument Loan` → native-lite tương đương; `antmed_crm.api.dashboard`→`antmed_crm.api.antmed.dashboard`). M11 nằm cuối DAG → **chỉ build được khi M02/M04/M09/M10 đã có DocType native** để query; nếu build sớm, từng endpoint phải **gate theo độ sẵn sàng** của module nguồn (xem §6 + §8).

---

## 1. Overview

M11 là **tầng đọc-tổng-hợp (read-only aggregate)** của AntMed CRM — không sinh dữ liệu nghiệp vụ mới, mà **đọc & tổng hợp** dữ liệu do M02/M04/M09/M10 (và các module liên quan) tạo ra để dựng **dashboard điều hành** và **báo cáo tuân thủ**. Đây là module cuối DAG (`../PLAN_AntMed_CRM.md §2`: `M09→M10→M11`, "M11 = cross-cutting / aggregate (sau cùng)").

**Vai trò trong 14 module:** cung cấp "mặt điều hành" cho CEO/BGĐ và Trưởng phòng KD — biến số liệu vận hành rời rạc (doanh thu, quota, SLA giao phòng mổ, vòng quay bộ dụng cụ, công nợ, chứng từ) thành **chỉ số + cảnh báo + drilldown** trên một SPA tiếng Việt.

**Business value** (ground `../../antmed_crm/docs/AntMed_CRM_Modules.md §11`):
- **Dashboard CEO:** doanh thu theo HĐ, tỷ lệ hoàn thành quota, top vật tư, top NV.
- **Dashboard kho:** tồn theo lô / cận date / kho ký gửi.
- **Dashboard bộ dụng cụ:** tần suất, vòng quay, sự cố mất/hư.
- **Dashboard SLA giao hàng phòng mổ.**
- **Báo cáo tuân thủ:** chứng từ thiếu, CO/CQ chưa gắn, hợp đồng sắp hết hạn.

**User stories:**
- *CEO/BGĐ* mở Dashboard, chọn kỳ (Tháng/Quý) → thấy 4 thẻ KPI lớn (doanh thu, % quota, SLA giao, bộ DC lưu hành), top 10 BV, top NV, danh sách cảnh báo điều hành; click một thẻ → drilldown bảng chi tiết + "Xuất Excel".
- *Trưởng phòng KD* xem **AR aging** (tuổi nợ 0–30/31–60/61–90/>90) theo BV để đốc thu, và **SLA giao phòng mổ** theo NV để chấn chỉnh.
- *Thủ kho* (qua dashboard kho) thấy danh sách lô **cận hạn dùng (HSD)** và **tồn kho ký gửi BV** cần đối soát.
- *NV chứng từ / Quản lý* mở **Báo cáo tuân thủ** thấy đơn giao **thiếu CO/CQ** chưa gắn và **HĐ sắp hết hạn** để xử lý trước hạn.

---

## 2. DocTypes (native-lite, [PLANNED])

> **KHÔNG có DocType — M11 chỉ là report endpoints (API-only).**
> Module thuần đọc/tổng hợp: mọi số liệu lấy từ DocType **native-lite của module khác** qua `frappe.db.sql` / `frappe.get_all` / `frappe.db.count`, KHÔNG tạo bảng mới, KHÔNG `docstatus`, KHÔNG naming series, KHÔNG fixtures workflow. Đây là quyết định kiến trúc của module (xem ADR-M11-01).

**Nguồn dữ liệu đọc (DocType của module khác — native-lite, KHÔNG ERPNext):**

| Nguồn | DocType native (đề xuất, do module nguồn sở hữu) | Dùng cho widget/báo cáo M11 | Module |
|---|---|---|---|
| Doanh thu / hóa đơn | `AntMed Order`, `AntMed AR Entry` *(thay `Sales Invoice` của scaffold ERPNext)* | doanh thu kỳ, AR aging | M09 |
| Quota gói thầu | `AntMed Contract` + child `AntMed Quota Item` *(thay `AM Tender Contract Item`)* | % quota đã dùng, HĐ sắp hết hạn | M02 |
| Giao phòng mổ + SLA | `AntMed Delivery` (có field `sla_status`/`workflow_state`), `AntMed OR Schedule` *(thay `Delivery Note`+`AM DO Extras`)* | SLA on-time %, kanban điều phối | M04 |
| KPI / hoa hồng | `AntMed KPI`, `AntMed Commission` | top NV, bảng KPI tổng hợp | M10 |
| Kho / lot | `AntMed Item`, `AntMed Warehouse`, `AntMed Lot` (CO/CQ/HSD), `AntMed Stock Entry` | tồn theo lô, cận date, tồn ký gửi | M03 |
| Bộ dụng cụ mượn | `AntMed Instrument Set` (workflow), `AntMed Sterilization` *(thay `AM Instrument Loan`)* | vòng quay, quá hạn trả, mất/hư | M05 |
| Chứng từ / CO-CQ | `AntMed Document`, `AntMed Lot` (gắn CO/CQ) | chứng từ thiếu, CO/CQ chưa gắn | M06 |
| Pipeline / thầu | `CRM Lead`/`CRM Deal` (mở rộng) + `AntMed Tender` | funnel pipeline gói thầu | M08 |

> ⚠️ `[cần khảo sát]`: tên/field chính xác của các DocType nguồn **do từng module M02–M10 chốt khi build**. Bảng trên là **ánh xạ đề xuất**; mỗi endpoint M11 phải kiểm `frappe.db.exists("DocType", …)` (hoặc try/except) và degrade-gracefully nếu nguồn chưa tồn tại (xem §6).

---

## 3. Workflow

**Không có workflow.** M11 không có DocType, không submit (`docstatus`), không state machine. Mọi endpoint là `GET` read-only thuần. (Workflow vòng đời thuộc về module nguồn: M04 giao phòng mổ, M05 bộ mượn — M11 chỉ **đọc** `workflow_state`/`sla_status` của chúng.)

---

## 4. Business Rules

M11 **không enforce BR nghiệp vụ "cứng"** (không validate/chặn ghi — nó chỉ đọc). Thay vào đó M11 **phản chiếu (surface) kết quả của BR** mà module nguồn đã enforce, và áp **2 ràng buộc kỹ thuật bắt buộc**:

| Quy tắc | Mô tả | Nơi enforce |
|---|---|---|
| **Invariant count == rows** | Mọi endpoint trả danh sách (top BV/NV, AR aging, lô cận date, chứng từ thiếu, kanban) phải có `len(rows)` khớp số liệu đếm; KHÔNG cắt ngầm bởi limit khi báo "tổng". Dùng `get_list(pluck=…, limit_page_length=0)` cho phần "đếm/tổng". | trong từng hàm `crm/api/antmed/dashboard.py` |
| **Data-scope BR-13 (đọc)** | `NV kinh doanh` chỉ thấy số liệu của BV được giao; `Quản lý`/CEO thấy toàn bộ. M11 **kế thừa** `permission_query_conditions` mà M14 cài cho DocType nguồn — nên endpoint M11 **phải đi qua `frappe.get_list`/`has_permission`** (KHÔNG `frappe.db.sql` bỏ qua perm) cho dữ liệu nhạy-cảm-theo-NV, để aggregate tự co theo scope. `[ROADMAP]` đến khi M14 bật BR-13 (ADR-M01-05); trước đó CEO-only role-gate. | `frappe.get_list` + role-check đầu hàm |

**BR phản chiếu (surface, không enforce tại M11)** — ground `../../antmed_crm/docs/AntMed_CRM_Modules.md §11` + bảng BR ở `./AntMed_CRM_*` (README BR-01..15):

| BR | Ý nghĩa với dashboard M11 | Widget / báo cáo |
|---|---|---|
| **BR-06** | % quota đã dùng (ngưỡng 70/90/100) — chạm trần do M02 khóa | thẻ "% Quota", "Sức khỏe hợp đồng" |
| **BR-08** | FIFO/HSD — lô **cận date** cần ưu tiên xuất | dashboard kho "cận date" |
| **BR-15** | Nhắc đối soát **kho ký gửi BV** định kỳ (M03 scheduler) | dashboard kho "tồn ký gửi" |
| **BR-01 / BR-03 / BR-04** | Chứng từ thiếu / **CO/CQ chưa gắn** / HĐĐT chưa phát hành | Báo cáo tuân thủ |
| SLA giao (M04) | % giao **đúng giờ ca mổ** | thẻ "SLA giao phòng mổ" + dashboard SLA |
| BR-05/BR-09 (M05) | Bộ DC **quá hạn trả**, mất/hư, vòng quay | dashboard bộ dụng cụ |

> Hệ quả: M11 **không** có `doc_events`/`hooks.py` ghi/chặn dữ liệu. Bug số liệu M11 = "đọc/tổng-hợp sai", KHÔNG phải "vi phạm BR ghi" → DoD nhấn vào **đúng số** (đối chiếu query thủ công) + **count==rows** + **scope đúng role**.

---

## 5. API

> File: `crm/api/antmed/dashboard.py`. Mọi hàm `@frappe.whitelist(methods=["GET"])`, **type-annotated** (vì `crm/hooks.py:28 require_type_annotated_api_methods = True`), trả **RAW dict/list** (KHÔNG `_ok`/`_err` envelope). Lỗi/permission = `frappe.throw(_("…tiếng Việt"), frappe.PermissionError)`. Endpoint danh sách giữ **count == rows**. **Measure-first**: viết query, đo cost, đánh index ở DocType nguồn nếu chậm (xem §8 + ADR-M11-02).
>
> Tham số kỳ chung: `date_from: str | None`, `date_to: str | None` (mặc định = tháng hiện tại), và `hospital: str | None` / `region: str | None` (bộ lọc theo top-bar UI). Param string → `frappe.parse_json` khi nhận dict-string.

### 5.A — `overview()` — KPI nền (BUILDABLE NOW, FE Slice 2) — SPEC ĐẦY ĐỦ

> **Đây là endpoint DUY NHẤT của M11 được code trong vòng này.** Mọi endpoint khác trong §5 vẫn `[PLANNED]` (nguồn M02–M10 chưa land). `overview()` chỉ đọc dữ liệu **M01 Customer 360° đã tồn tại** (`AntMed Hospital`, `AntMed Doctor`) nên codeable ngay mà không vi phạm gate degrade-gracefully. Lý do tách khỏi `ceo_kpis()` → **ADR-M11-03**.

**Signature & file:** `crm/api/antmed/dashboard.py`

```python
@frappe.whitelist(methods=["GET"])
def overview() -> dict:
    """KPI nền dashboard điều hành (A1) — chỉ đếm M01 đã land.

    Đường gọi: antmed_crm.api.antmed.dashboard.overview (GET, yêu cầu session).
    Trả RAW dict thuần (KHÔNG envelope _ok/_err).

    count == rows (BR-13): đếm bằng len(get_list(pluck="name", limit_page_length=0))
    — get_list tôn trọng DocPerm + (khi M14 bật) permission_query_conditions, nên
    số đếm tự co theo scope user. KHÔNG dùng frappe.db.count (bỏ qua permission → rò rỉ).
    """
    return {
        "hospital_count": len(
            frappe.get_list("AntMed Hospital", pluck="name", limit_page_length=0)
        ),
        "doctor_count": len(
            frappe.get_list("AntMed Doctor", pluck="name", limit_page_length=0)
        ),
    }
```

**Hợp đồng trả (RAW dict — KHÔNG bọc `{data,total_count}` vì là thẻ-số, đồng quy ước `ceo_kpis`):**

| Key | Kiểu | Ý nghĩa |
|---|---|---|
| `hospital_count` | `int` | Số `AntMed Hospital` user được phép thấy (count==rows). |
| `doctor_count` | `int` | Số `AntMed Doctor` user được phép thấy (count==rows). |

> **Số THẬT, không bịa.** Trên site `miyano` hiện tại = `{ "hospital_count": 2, "doctor_count": 0 }` (2 BV gồm leftover `_SEC-H1/_SEC-H2` chờ purge — STATE; 0 bác sỹ). FE render đúng số endpoint trả, KHÔNG hardcode con số mockup (12,8 tỷ / 78% / 94,2% / 47).

**Boundaries — `overview()`:**
- **Always:** `@frappe.whitelist(methods=["GET"])` + type-annotate (`-> dict`) · đếm qua `get_list(pluck="name", limit_page_length=0)` (count==rows, tôn trọng permission) · trả RAW dict 2 key đúng tên `hospital_count`/`doctor_count`.
- **Never:** KHÔNG `frappe.db.count(...)` (bỏ qua DocPerm → rò rỉ, fail invariant BR-13) · KHÔNG đếm nguồn M02–M10 chưa tồn tại (degrade-gracefully — slice này KHÔNG chạm) · KHÔNG envelope `_ok/_err`/`MSG.*` · KHÔNG nhận param (slice này không lọc kỳ).

**Phân biệt 403 (đặc tả cho QA):**
- **dispatcher-403:** guest / không session cookie → Frappe chặn ở tầng dispatcher TRƯỚC khi vào handler (endpoint yêu cầu session, đồng quy ước `health.ping`).
- **in-handler permission-403:** KHÔNG áp dụng cho `overview()` — không `frappe.throw(PermissionError)` trong thân hàm. Thiếu quyền `read` trên `AntMed Hospital`/`AntMed Doctor` KHÔNG raise; thay vào đó `get_list` tự trả tập rỗng/co-scope → `count` giảm tương ứng (đó CHÍNH LÀ data-scope đúng, không phải lỗi). Invariant: số endpoint trả == số bản ghi user drill thấy ở list M01.

### Dashboard CEO

| Endpoint (`antmed_crm.api.antmed.dashboard.*`) | Verb | Mô tả / shape trả (RAW) |
|---|---|---|
| **`overview()`** ✅ **[BUILDABLE NOW — FE Slice 2]** | GET | KPI nền chỉ đếm dữ liệu **M01 đã land** (không phụ thuộc M02–M10) → `{ "hospital_count": int, "doctor_count": int }`. Đếm DƯỚI permission user (count==rows pattern, xem §5.A) — KHÔNG `frappe.db.count`. Đây là endpoint **duy nhất codeable ngay** vì nguồn (`AntMed Hospital`/`AntMed Doctor`) đã tồn tại; các endpoint còn lại `[PLANNED]` chờ module nguồn. Chi tiết: **§5.A**. |
| `ceo_kpis(date_from, date_to)` | GET | 4 thẻ KPI lớn → `{ "revenue": {...}, "quota_used_pct": float, "sla_ontime_pct": float, "instrument_in_circulation": {...} }`. `revenue` gồm `amount`, `prev_amount`, `delta_pct`, `sparkline: list[float]` (12 tháng). Ground scaffold `ceo_kpis()` (adapt: `Sales Invoice`→`AntMed Order/AR Entry`; `AM Tender Contract Item`→`AntMed Quota Item`; `AM DO Extras`+`Delivery Note`→`AntMed Delivery.sla_status`; `AM Instrument Loan`→`AntMed Instrument Set`). |
| `revenue_by_supply_group(date_from, date_to)` | GET | Stacked-bar doanh thu theo nhóm vật tư → `list[{group, amount}]`. |
| `top_hospitals(date_from, date_to, limit=10)` | GET | Top 10 BV theo doanh thu → `{ "data": list[{hospital, hospital_name, amount}], "total_count": int }`. |
| `top_sales(date_from, date_to, limit=10)` | GET | Top NV (bảng KPI tổng hợp, đọc M10) → `{ "data": [...], "total_count": int }`. |
| `executive_alerts()` | GET | Cảnh báo điều hành → `{ "contracts_expiring": [...], "ar_overdue": [...], "instruments_lost": [...] }` (HĐ sắp hết hạn / công nợ quá hạn / bộ DC thất lạc). |
| `revenue_heatmap_by_province(date_from, date_to)` | GET | Heatmap doanh thu theo tỉnh (UI bản đồ VN) → `list[{province, amount}]`. `[cần khảo sát]` field tỉnh trên `AntMed Hospital`. |
| `pipeline_funnel(date_from, date_to)` | GET | Funnel gói thầu Lead→Khảo sát→Báo giá→Dự thầu→Trúng (đọc M08) → `list[{stage, count, value}]`. |

### Dashboard điều phối / SLA (M04)

| Endpoint | Verb | Mô tả |
|---|---|---|
| `kanban_b1(date_from, date_to)` | GET | Kanban điều phối ca giao → dict theo cột trạng thái `AntMed Delivery.workflow_state`. Ground scaffold `kanban_b1()` (adapt: `AM Delivery Request`→`AntMed Delivery`, cột = states VI của workflow M04). |
| `sla_delivery(date_from, date_to, group_by="employee")` | GET | % giao đúng giờ ca mổ + xu hướng, group theo NV/BV → `{ "ontime_pct": float, "trend": [...], "by_group": list[...] }`. |

### Dashboard kho (M03)

| Endpoint | Verb | Mô tả |
|---|---|---|
| `stock_by_lot(warehouse=None)` | GET | Tồn theo lô → `{ "data": list[{item, lot, qty, warehouse}], "total_count": int }` (đọc `AntMed Stock Entry`/tồn-bin native). |
| `expiring_lots(days=90)` | GET | Lô **cận hạn dùng (HSD)** trong `days` ngày → `{ "data": list[{item, lot, expiry_date, qty, days_left}], "total_count": int }` (BR-08). |
| `consignment_stock(hospital=None)` | GET | Tồn **kho ký gửi BV** cần đối soát → `{ "data": [...], "total_count": int }` (BR-15; `AntMed Warehouse` cấp "Ký gửi BV"). |

### Dashboard bộ dụng cụ (M05)

| Endpoint | Verb | Mô tả |
|---|---|---|
| `instrument_overview()` | GET | Tần suất + vòng quay + sự cố → `{ "in_circulation": int, "overdue": int, "lost_damaged": int, "turnover": [...] }`. |

### Công nợ / AR (M09)

| Endpoint | Verb | Mô tả |
|---|---|---|
| `ar_aging_buckets(hospital=None)` | GET | Tuổi nợ 0–30 / 31–60 / 61–90 / >90 theo BV → `{ "data": list[{customer, b0_30, b31_60, b61_90, b90_plus}], "total_count": int }`. Ground scaffold `ar_aging_buckets()` (adapt: `Sales Invoice.outstanding_amount`→`AntMed AR Entry`/`AntMed Order` native). |

### Báo cáo tuân thủ (M06)

| Endpoint | Verb | Mô tả |
|---|---|---|
| `compliance_report(date_from, date_to)` | GET | → `{ "missing_documents": [...], "co_cq_unattached": [...], "contracts_expiring": [...] }`: đơn giao **thiếu chứng từ**, lô/đơn **CO/CQ chưa gắn**, HĐ **sắp hết hạn**. Mỗi danh sách giữ count==rows. |

### Drilldown / export

| Endpoint | Verb | Mô tả |
|---|---|---|
| `drilldown(widget, date_from, date_to, filters=None, start=0, page_length=50)` | GET | Bảng chi tiết phía sau mỗi widget (UI "click widget → drilldown full-screen") → `{ "data": [...], "total_count": int }` phân trang; **count==rows** với dữ liệu đã lọc. Tham số `widget` = khóa widget (whitelist enum, throw nếu lạ). |

> **Mọi endpoint danh sách** trả `{ "data": [...], "total_count": int }` và giữ invariant **`len(data) == total_count`** khi không phân trang (đồng quy ước với M01). Endpoint thẻ-đơn (`ceo_kpis`, `sla_delivery`, `instrument_overview`) trả dict số thuần.

---

## 6. Integration

**Hướng phụ thuộc (đọc — KHÔNG ghi):** M11 ở **cuối DAG**, chỉ **đọc xuống** M02/M04/M09/M10 (+ M03/M05/M06/M08). KHÔNG có `doc_events` ra/vào: M11 không sửa doc nào, nên **không đăng ký `doc_events` trong `crm/hooks.py`** và **không** là nguồn của module nào (`Cấp dữ liệu cho: —`).

- **Lazy-import + truyền PK:** mỗi endpoint chỉ cần **tên DocType + tên field** (PK) của nguồn; KHÔNG import controller module nguồn ở top-level. Nếu cần hàm tổng hợp dùng chung của M10 (vd KPI), **lazy-import trong thân hàm** (`from crm.antmed.m10_... import ...`) để M11 không phá vỡ load-order và không hard-fail khi M10 chưa có.
- **Gate độ-sẵn-sàng nguồn (degrade-gracefully):** vì M11 build ở W4 nhưng có thể chạy trước khi mọi nguồn xong, mỗi feeder phải **kiểm `frappe.db.exists("DocType", "AntMed Order")`…** trước khi query; nếu nguồn chưa tồn tại → trả nhánh rỗng (`0` / `[]`) thay vì 500. Cho phép dựng skeleton dashboard sớm, fill dần theo wave.
- **Gate compliance (surface):** `compliance_report` + `executive_alerts` **đọc** kết quả các BR compliance (BR-01/03/04 chứng từ, BR-06 quota, BR-08 HSD) mà M03/M06 enforce — M11 **không** tự gate giao hàng, chỉ liệt kê vi phạm để người điều hành xử lý.
- **Data-scope BR-13 (đọc):** dữ liệu nhạy-cảm-theo-NV đi qua `frappe.get_list` để hưởng `permission_query_conditions` của M14; aggregate tự co theo role. `[ROADMAP]` cho đến khi M14 bật BR-13 → trước đó các dashboard tổng hợp toàn-công-ty là **CEO/`Quản lý`-only**.
- **Scheduler (tùy chọn):** `crm/antmed/m11_dashboard.py::send_weekly_executive_digest` gửi email digest Thứ Hai cho role `Quản lý` (ground scaffold `m11_dashboard/scheduler.py`; adapt role `AM CEO`/`AM Sales Manager`→`Quản lý`, dùng `frappe.get_all("Has Role", …)` thay SQL thô, gọi lại `ceo_kpis()`). Đăng ký qua `scheduler_events` trong `hooks.py` (chỉ THÊM key). `[PLANNED]` — không bắt buộc cho slice đầu.

---

## 7. UI

> Vue 3 + frappe-ui SPA. Gọi **đúng** `antmed_crm.api.antmed.dashboard.*` qua `createResource` (shape dict bọc / số thuần — KHÔNG để frappe-ui coi response là array). Route mới **APPEND** vào `frontend/src/router.js` (lazy). KHÔNG đụng route CRM gốc. Nhãn 100% tiếng Việt qua `__()`, design token frappe-ui (KHÔNG hex thô), trạng thái loading/error/empty mỗi widget, a11y (aria-live cho số liệu cập nhật). Ground `../../antmed_crm/docs/AntMed_CRM_UI_Design.md §1` (widget CEO) + §11 (ma trận màn-hình→vai trò).

### Routes (THÊM mới — lazy import)

| path | name | component | role dùng |
|---|---|---|---|
| `/antmed/dashboard` | `AntmedDashboardCEO` | `pages/AntmedDashboardCEO.vue` | `Quản lý` (CEO/Trưởng KD) |
| `/antmed/dashboard/warehouse` | `AntmedDashboardWarehouse` | `pages/AntmedDashboardWarehouse.vue` | `Thủ kho`, `Quản lý` |
| `/antmed/dashboard/instrument` | `AntmedDashboardInstrument` | `pages/AntmedDashboardInstrument.vue` | `Quản lý` |
| `/antmed/dashboard/sla` | `AntmedDashboardSLA` | `pages/AntmedDashboardSLA.vue` | `Quản lý` |
| `/antmed/reports/compliance` | `AntmedReportCompliance` | `pages/AntmedReportCompliance.vue` | `Quản lý`, `NV chứng từ` *(role VI [PLANNED] — xem ./m14_rbac_w0_role_naming.md)* |

### 7.A — Màn hình "Dashboard A1" trên `AntmedHome` (`/antmed`) — FE Slice 2 (BUILDABLE NOW)

> Slice 2 **không** tạo `AntmedDashboardCEO.vue` — nó **viết lại `frontend/src/pages/AntmedHome.vue`** (route `/antmed`, name `AntmedHome`, item nav `dashboard` đã `enabled:true`) từ health-widget thành **khung A1**. Trang CEO đầy đủ (`/antmed/dashboard`) ở bảng routes trên là [PLANNED] cho slice W4 sau. Ground mockup `AntMed_CRM_Full_Mockups.html` A1 dòng **252–269** (`cardrow cols-4` → `cols-12` → `cols-2`).

**Layout A1 (3 hàng card, dùng grid Tailwind/frappe-ui token, KHÔNG hex thô):**

| Hàng | Cấu trúc mockup | Card | Nguồn dữ liệu |
|---|---|---|---|
| 1 | `cardrow cols-4` (4 thẻ KPI) | **Số bệnh viện** | `overview().hospital_count` — **số THẬT** |
| | | **Số bác sỹ** | `overview().doctor_count` — **số THẬT** |
| | | Doanh thu tháng | empty-state "Chưa có dữ liệu" *(nguồn M09 chưa có)* |
| | | Bộ DC lưu hành | empty-state "Sắp có" *(nguồn M05 chưa có)* |
| 2 | `cardrow cols-12` | Top 10 Bệnh viện | empty-state "Chưa có dữ liệu" *(nguồn `top_hospitals` PLANNED)* |
| 3 | `cardrow cols-2` | Pipeline gói thầu | empty-state "Chưa có dữ liệu" *(nguồn M08)* |
| | | ⚠ Cảnh báo điều hành | empty-state "Chưa có dữ liệu" *(nguồn `executive_alerts` PLANNED)* |

**Card-mapping decision (vì sao 2 KPI thật + 2 KPI empty trong hàng 1):** Mockup A1 hàng 1 có 4 thẻ *Doanh thu / Quota / SLA / Bộ DC* — tất cả phụ thuộc M02/M04/M05/M09 **chưa land**. Để có KPI **thật** ngay (acceptance bắt buộc), 2 ô đầu được thay bằng **Số bệnh viện / Số bác sỹ** (M01 đã có), giữ ô 3–4 ("Doanh thu tháng", "Bộ DC lưu hành") ở empty-state. Đây là *honest placeholder*, không phải đổi mockup vĩnh viễn — khi M02–M09 land, KPI mockup gốc trám lại (Slice W4). *(Cần khảo sát baseline)* cho ngưỡng/đơn vị các KPI mockup khi land.

**Tri-branch (chỉ 2 KPI thật cần — phần empty-state là static):**
- **loading:** `health.loading`-style → `LoadingIndicator` trong 2 ô KPI thật.
- **error:** `Badge` `theme="red"` + `<Button :label="__('Thử lại')" @click="overview.reload()"/>` + `toast.error(overview.error?.messages?.[0] || __('Không tải được số liệu tổng quan'))` (reuse pattern `AntmedHome` cũ dòng 32–52, 94–97).
- **data:** render `overview.data.hospital_count` / `overview.data.doctor_count` (số nguyên; KHÔNG format tiền/%).

**Nhãn tiếng Việt (qua `__()`):** "Số bệnh viện", "Số bác sỹ", "Doanh thu tháng", "Bộ DC lưu hành", "Top 10 Bệnh viện", "Pipeline gói thầu", "Cảnh báo điều hành", "Chưa có dữ liệu", "Sắp có", "Thử lại". KHÔNG hex thô — dùng design token frappe-ui (`text-ink-gray-*`, `bg-surface-gray-*`, `Badge theme`). `aria-live="polite"` cho vùng KPI cập nhật.

### Màn hình "Dashboard CEO" (`/antmed/dashboard`) — ground UI_Design §1.2

- **Top bar:** bộ chọn kỳ (Hôm nay/Tuần/Tháng/Quý/Tùy chỉnh) + bộ lọc BV/Vùng → đổi param `date_from/date_to/hospital/region` cho mọi resource.
- **Hàng 1 — 4 thẻ KPI lớn** (`ceo_kpis`): Doanh thu tháng (số + %so-kỳ-trước + sparkline 12 tháng), % Quota đã dùng (vòng tròn, ngưỡng 70/90/100), SLA giao phòng mổ (% + mũi tên xu hướng), Bộ dụng cụ đang lưu hành (số + số quá hạn trả đỏ).
- **Hàng 2:** Bản đồ VN heatmap doanh thu theo tỉnh (`revenue_heatmap_by_province`, click tỉnh → drill BV) · Top 10 BV (`top_hospitals`, thanh tiến độ trong cell).
- **Hàng 3:** Funnel pipeline gói thầu (`pipeline_funnel`) · Cảnh báo điều hành (`executive_alerts`: HĐ sắp hết hạn / công nợ quá hạn / bộ DC thất lạc).
- **Hàng 4:** Doanh thu theo nhóm vật tư stacked-bar (`revenue_by_supply_group`) · Top NV kinh doanh (`top_sales`).
- **Tương tác:** click widget → drilldown full-screen (`drilldown`) bảng chi tiết + nút "Xuất Excel" / "Chia sẻ link".

### Các dashboard chuyên đề

- **Kho** (`stock_by_lot`, `expiring_lots`, `consignment_stock`): bảng tồn theo lô, danh sách cận-date (tô cam theo `days_left`), tồn ký gửi BV.
- **Bộ dụng cụ** (`instrument_overview`): thẻ lưu hành/quá hạn/mất-hư + biểu đồ vòng quay.
- **SLA giao** (`sla_delivery` + `kanban_b1`): % đúng giờ theo NV/BV + kanban điều phối ca.
- **Báo cáo tuân thủ** (`compliance_report`): 3 bảng — chứng từ thiếu / CO-CQ chưa gắn / HĐ sắp hết hạn, mỗi dòng link sang doc nguồn.

### Boundaries UI
- **Always** lazy import các page mới; `__()` cho nhãn; loading/error/empty mỗi widget; đọc `r.data` đúng shape (dict bọc `{data,total_count}` hoặc số thuần).
- **Never** gọi `crm.api.*` (đúng: `antmed_crm.api.antmed.dashboard.*`); **Never** axios/tanstack/`frappe.client.*` trực tiếp; **Never** sửa layout/route CRM gốc.

---

## 8. Build slices

> M11 = API-only, đọc nhiều nguồn ở W4. Chia slice theo **độ sẵn sàng của module nguồn** (build slice nào mà nguồn của nó đã land). Mỗi slice 1 vòng factory (BA→BE+FE→QA→user). TDD: test failing-first. **Measure-first** mỗi query.

### 8.A — FE Slice 2 (BUILDABLE NOW): Shell A1 trên `AntmedHome` + `overview()` count thật

> ⚠️ Slice này **đứng TRƯỚC** Slice 1–6 ở dưới và là slice DUY NHẤT codeable ngay (nguồn = M01 đã land). KHÔNG đụng các native-lite DocType M02–M10 chưa tồn tại. Mục tiêu: dựng **khung dashboard A1** (mockup A1 dòng 252–269) trên trang `AntmedHome` (`/antmed`) với **2 KPI count thật** + **empty-state trung thực** cho card chưa có nguồn.

**Phạm vi (Always / Never):**
- **Always (làm):**
  - **BE:** thêm 1 hàm `overview()` vào file mới `crm/api/antmed/dashboard.py` (spec §5.A) — count thật `AntMed Hospital`/`AntMed Doctor` qua `get_list(pluck,limit_page_length=0)`.
  - **FE:** viết lại `frontend/src/pages/AntmedHome.vue` từ health-widget → **layout A1** đúng cấu trúc mockup:
    - **Hàng 1 — 4 thẻ KPI** (`cardrow cols-4`): `Số bệnh viện`, `Số bác sỹ` (2 thẻ render số THẬT từ `overview()`), + `Doanh thu tháng`, `Bộ DC lưu hành` (2 thẻ empty-state — mockup A1 có "Doanh thu tháng"/"Quota đã dùng"/"SLA giao PT"/"Bộ DC lưu hành"; ta thay 2 ô đầu bằng KPI thật M01, giữ 2 ô mockup còn lại ở trạng thái "Chưa có dữ liệu"). *(Quyết định card-mapping + vì sao 2/4 thẻ: xem §7.A.)*
    - **Hàng 2 — `cardrow cols-12`:** card "Top 10 Bệnh viện" (empty-state "Chưa có dữ liệu").
    - **Hàng 3 — `cardrow cols-2`:** card "Pipeline gói thầu" + card "⚠ Cảnh báo điều hành" (cả 2 empty-state).
  - **FE thêm resource** `dashboardOverview()` trong `frontend/src/data/antmed.js` (createResource url `antmed_crm.api.antmed.dashboard.overview`, `auto: true`).
  - **Tri-branch mỗi nguồn-có-data:** `loading` = `LoadingIndicator`; `error` = `Badge` đỏ + nút "Thử lại" (`overview.reload()`) + `toast.error(err.messages?.[0] || fallback VN)`; `data` = render 2 KPI thật. (Reuse pattern `AntmedHome` cũ — health-widget đã đúng idiom.)
  - **Empty-state card chưa có nguồn:** render literal tiếng Việt **"Chưa có dữ liệu"** / **"Sắp có"** — KHÔNG fetch, KHÔNG số.
- **Never (cấm):**
  - ❌ Hardcode bất kỳ số mockup nào: `12,8 tỷ`, `78%`, `94,2%`, `47`, `/3 quá hạn`, top-BV "Bạch Mai 2,1", funnel "Lead — 38", cảnh báo "Chợ Rẫy còn 12 ngày" → **tất cả là dữ liệu giả của mockup**, phải thay bằng count thật (2 KPI) hoặc empty-state (phần còn lại).
  - ❌ Gọi `crm.api.*` (đúng: `antmed_crm.api.antmed.dashboard.overview`); ❌ axios/tanstack/`frappe.client.*`.
  - ❌ Đụng route/layout CRM gốc; ❌ thêm route mới (tái dùng route `/antmed` name `AntmedHome` đã có — KHÔNG tạo `AntmedDashboardCEO.vue` ở slice này; trang CEO đầy đủ là Slice 1–2 W4 sau).
  - ❌ `frappe.db.count` ở BE.

**DoD Slice 2 (đo được):**
1. `git diff frontend/` NON-EMPTY: `AntmedHome.vue` bị viết lại thành layout A1 (KPI row 4 + row 12-col Top10 + row 2-col Pipeline/Cảnh báo).
2. **BE:** `bench --site miyano run-tests --module crm.tests.test_antmed_dashboard` → `Ran N OK 0 fail` (≥3 case: shape `{hospital_count:int,doctor_count:int}`; whitelist GET + type-annotated + no-envelope; count khớp `get_list` thật / count==rows; degrade — gọi được khi 0 bác sỹ trả `doctor_count==0` không raise).
3. **FE:** `yarn vitest run` XANH, baseline 154 → **target ≥158** (≥4 case dashboard mới: KPI render số từ resource không hardcode; empty-state literal "Chưa có dữ liệu"/"Sắp có"; tri-branch loading/error/data; gọi đúng url `antmed_crm.api.antmed.dashboard.overview`). `yarn build` XANH (chunk emit + `crm.html` regenerate).
4. **No-regression:** `test_antmed_bootstrap` / `test_antmed_customer` / `test_antmed_rbac_boot` / `test_role_rename_idempotent` + CRM gốc (`org_hierarchy`/`crm_lead`/`crm_task`) giữ xanh; vitest baseline 154 không tụt.
5. **Pixel (sau USER reload BE):** `http://miyano:8000/crm/antmed` render 2 KPI thật (BV=2, BS=0 ở site hiện tại) + các card "Chưa có dữ liệu"; 0 console error; network `overview` 200.

### Slices W4 (PLANNED — chờ module nguồn land):

1. **Slice 1 — Khung dashboard + AR aging (M09 sẵn):** `crm/api/antmed/dashboard.py` với `ar_aging_buckets` (native `AntMed AR Entry`/`Order`) + `executive_alerts` phần công-nợ-quá-hạn; FE `AntmedDashboardCEO.vue` khung + 1 widget AR; route + vitest + build. Gate degrade-gracefully cho nguồn chưa có.
2. **Slice 2 — CEO KPIs + top BV/NV (M02/M10 sẵn):** `ceo_kpis`, `top_hospitals`, `top_sales`, `revenue_by_supply_group`; 4 thẻ + 2 bảng top.
3. **Slice 3 — SLA giao + kanban điều phối (M04 sẵn):** `sla_delivery`, `kanban_b1`; trang `AntmedDashboardSLA.vue`.
4. **Slice 4 — Dashboard kho + bộ dụng cụ (M03/M05 sẵn):** `stock_by_lot`, `expiring_lots`, `consignment_stock`, `instrument_overview`.
5. **Slice 5 — Báo cáo tuân thủ + funnel + heatmap (M06/M08 sẵn):** `compliance_report`, `pipeline_funnel`, `revenue_heatmap_by_province`.
6. **Slice 6 — Drilldown + Export + Weekly digest:** `drilldown` (export Excel), scheduler `send_weekly_executive_digest`, guard regression hiệu năng (index nguồn).

---

## 9. ADRs

### ADR-M11-01: M11 là API-only (KHÔNG DocType), tầng đọc-tổng-hợp
- **Status:** Proposed (chờ build W4)
- **Date:** 2026-06-17
- **Context:** `../PLAN_AntMed_CRM.md` hàng M11 = "report + dashboard config", DAG đặt M11 cuối ("aggregate sau cùng"). Dữ liệu nghiệp vụ đã do M02/M04/M09/M10 sở hữu; M11 chỉ cần tổng hợp/đọc.
- **Decision:** M11 **không tạo DocType/workflow/fixtures**; chỉ thêm `crm/api/antmed/dashboard.py` (read-only `GET`) + scheduler digest tùy chọn. Mọi số liệu đọc từ DocType native-lite của module khác.
- **Alternatives:** (a) tạo DocType "Dashboard Config"/snapshot — loại ở giai đoạn đầu (over-engineer, dữ liệu suy ra được; có thể thêm sau nếu cần cache/snapshot lịch sử). (b) dùng Frappe Number Card/Dashboard desk — loại: UI là SPA Vue tiếng Việt, không dùng desk.
- **Consequences:** (+) gọn, không phình schema, không migrate. (−) phụ thuộc nặng tên/field DocType nguồn → cần gate độ-sẵn-sàng (§6) + đối chiếu khi nguồn đổi schema. (−) báo cáo "thời điểm" (live query), chưa có snapshot lịch sử (backlog).

### ADR-M11-02: Measure-first cho query tổng hợp; tránh `frappe.db.sql` bỏ qua permission
- **Status:** Proposed
- **Date:** 2026-06-17
- **Context:** Aggregate (SUM/GROUP BY trên đơn/hóa đơn/giao) dễ thành N+1 / full-scan; đồng thời data-scope BR-13 cần được tôn trọng khi đọc.
- **Decision:** **Đo trước** (profile từng feeder), đánh index ở DocType **nguồn** (do module nguồn sở hữu) nếu chậm, gắn guard chống regression. Dữ liệu nhạy-cảm-theo-NV đọc qua `frappe.get_list`/`has_permission` (hưởng `permission_query_conditions`), KHÔNG `frappe.db.sql` thô bỏ qua perm; `frappe.db.sql` chỉ dùng cho aggregate **toàn-công-ty** ở endpoint **CEO/`Quản lý`-only** đã role-gate.
- **Consequences:** (+) số đúng + an toàn scope + không regress hiệu năng. (−) một số aggregate "toàn cục" phải gate role thay vì lọc theo NV cho tới khi BR-13 bật.

### ADR-M11-03: Tách endpoint `overview()` (M01-only) khỏi `ceo_kpis()` (W4) để dựng shell A1 sớm
- **Status:** Accepted
- **Date:** 2026-06-17
- **Context:** Acceptance FE Slice 2 yêu cầu dashboard A1 có **KPI count THẬT ngay**, nhưng `ceo_kpis()` (§5 Dashboard CEO) phụ thuộc các DocType native-lite M02/M04/M05/M09 **chưa land** → không thể trả số thật mà không vi phạm gate degrade-gracefully (§6) hoặc bịa số. Duy nhất M01 (`AntMed Hospital`/`AntMed Doctor`) đã có dữ liệu thật.
- **Decision:** Thêm endpoint **mỏng riêng `overview()`** chỉ đếm 2 DocType M01 (count==rows qua `get_list`), tách bạch khỏi `ceo_kpis()`. Shell A1 (`AntmedHome`) render 2 KPI thật từ `overview()` + empty-state trung thực cho mọi card nguồn-chưa-có. KHÔNG nhồi count M01 vào `ceo_kpis()` (giữ `ceo_kpis` thuần "4 thẻ điều hành" cho W4).
- **Alternatives:** (a) Chờ M02–M09 land rồi build thẳng `ceo_kpis()` đầy đủ — loại: chặn tiến độ shell + KPI thật nhiều wave; (b) Hardcode số mockup tạm — loại tuyệt đối: bịa số = vi phạm Verify-Before-Claim + sai sự thật điều hành; (c) Cho `ceo_kpis()` degrade trả 0 cho mọi thẻ — loại: 4 thẻ "0" gây hiểu lầm "doanh thu = 0" thay vì "chưa có nguồn"; empty-state "Chưa có dữ liệu" trung thực hơn.
- **Consequences:** (+) Dashboard A1 codeable ngay với KPI thật, không bịa, không phá gate; (+) `overview()` ổn định, tái dùng được cả khi `ceo_kpis()` land. (−) Hàng 1 mockup tạm thời chỉ 2/4 thẻ có số (2 thẻ empty) cho tới W4 — chấp nhận như *honest placeholder* (§7.A). (−) Có 2 endpoint KPI cùng tồn tại (`overview` nhẹ + `ceo_kpis` đầy đủ) — ghi rõ ranh giới để không trùng lặp.

> Tham chiếu ADR cấp dự án còn hiệu lực: **ADR-M01-01** (in-place app `crm`), **ADR-M01-02** (prefix `AntMed `), **ADR-M01-05** (hoãn data-scope BR-13 → M14), **DEC-2026-06-17-A** (role VI), **DEC-2026-06-17-B** (tách route AntMed). M11 kế thừa, không Supersede.

---

## 10. Acceptance / DoD

Theo SPEC §6 (DoD một lát cắt = BE test xanh + FE vitest + build + pixel + no-regression):

1. **BE:** `bench --site miyano run-tests --module crm.tests.test_antmed_dashboard` → **`Ran N tests … OK`**, 0 fail. TC tối thiểu mỗi slice:
   - Mỗi endpoint `@frappe.whitelist(methods=["GET"])`, type-annotated, trả RAW (dict/list), KHÔNG envelope.
   - Endpoint danh sách: shape `{data, total_count}` + **`len(data) == total_count`** khi không phân trang (count==rows).
   - Số liệu **đúng**: seed dữ liệu nguồn (đơn/quota/giao/lot) → assert giá trị aggregate khớp tính tay (vd `ar_aging_buckets` chia đúng bucket; `ceo_kpis.revenue` đúng tổng kỳ).
   - **Degrade-gracefully:** khi DocType nguồn chưa tồn tại → trả `0`/`[]`, KHÔNG raise 500.
   - **Scope:** user role `Quản lý` thấy toàn bộ; (khi BR-13 bật) `NV kinh doanh` chỉ thấy BV được giao — aggregate co theo scope (count==rows theo từng NV).
2. **FE:** `cd apps/crm/frontend && yarn vitest run` xanh — route mới tồn tại (path/name/lazy), page gọi **đúng** `antmed_crm.api.antmed.dashboard.*`, không `antmed_crm.api`/axios/tanstack; `yarn build` xanh (chunk Antmed* không vỡ).
3. **Pixel (sau USER reload BE):** `http://miyano/crm/antmed/dashboard` render thẻ KPI + bảng top + cảnh báo với dữ liệu thật; đổi kỳ/bộ lọc → số đổi; click widget → drilldown; 0 console error; API 200.
4. **No-regression:** route/test Frappe CRM gốc + các module M02/M04/M09/M10 nguồn còn xanh; M11 không thêm `doc_events` nên không đụng luồng ghi.
5. **Hiệu năng (measure-first):** feeder nặng có số đo (p95) + index nguồn nếu cần; guard chống regression.

---

## Tham chiếu chéo

- Spec cấp dự án: `../SPEC_AntMed_CRM.md` (§5 code style Frappe-standard, §6 DoD, §8 ADR/DEC)
- Kế hoạch/Wave/DAG: `../PLAN_AntMed_CRM.md` (hàng M11, §2 DAG `M09→M10→M11`, §3 W4)
- Nghiệp vụ: `../../antmed_crm/docs/AntMed_CRM_Modules.md` §11 (Báo cáo & Dashboard) + bảng khoảng cách (M11 "có khung")
- UI: `../../antmed_crm/docs/AntMed_CRM_UI_Design.md` §1 (widget Dashboard CEO), §11 (ma trận màn-hình → vai trò; "11. Báo cáo → CEO, Trưởng KD")
- House style / mẫu Core Doc: `./m01_customer360.md`
- RBAC / role VI: `./m14_rbac_w0_role_naming.md`, `./m14_rbac_w0_antmed_boot.md`
- Scaffold tham chiếu (app-riêng cũ, ĐÃ adapt → native-lite + `antmed_crm.api.antmed.*`): `antmed_crm/m11_dashboard/` (`api/dashboard.py`: `ceo_kpis`/`kanban_b1`/`ar_aging_buckets`; `scheduler.py`: weekly digest)
- Module nguồn liên quan (khi có doc): M02 Hợp đồng/Quota · M03 Kho/Lot · M04 Giao phòng mổ/SLA · M05 Bộ mượn · M06 Chứng từ/HĐĐT · M08 Pipeline/Tender · M09 Đơn/AR · M10 KPI · M14 Security/BR-13
