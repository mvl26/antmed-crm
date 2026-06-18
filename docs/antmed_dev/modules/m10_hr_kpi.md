# M10 — Nhân sự Kinh doanh & KPI lai (Core Doc)

| Mục | Giá trị |
|---|---|
| Module folder | `crm/antmed/` (module Frappe **`AntMed`**, scrubbed = `antmed`) |
| DocType folder | `crm/antmed/doctype/antmed_kpi_definition/`, `…/antmed_kpi_score/`, `…/antmed_commission/`, `…/antmed_sales_employee/`, `…/antmed_employee_route/` |
| API package | `crm/api/antmed/hr_kpi.py` (đường gọi `antmed_crm.api.antmed.hr_kpi.<fn>`) |
| FE pages | `frontend/src/pages/AntmedTeam.vue`, `AntmedSalesEmployeeDetail.vue`, `AntmedKpiBoard.vue`, `AntmedCommission.vue` + route `/antmed/team`, `/antmed/team/:name`, `/antmed/kpi`, `/antmed/commission` |
| Wave (PLAN) | **W4 — Tăng trưởng & kiểm soát** |
| Role chính (VI) | `Quản lý` (xem KPI đội + khóa kỳ hoa hồng); `NV kinh doanh` (xem KPI/hoa hồng của chính mình) — DEC-A. Có thể cần `Kế toán` [PLANNED] cho khóa kỳ + đẩy lương |
| Phụ thuộc | **M04** (SLA giao đúng giờ ca), **M05** (tỷ lệ bộ dụng cụ trả đủ-đúng-hạn), **M09** (doanh số / đơn / AR) — và gián tiếp M01 (BV/bác sỹ), M07 (hài lòng bác sỹ) |
| Cấp dữ liệu cho | **M11** (Dashboard điều hành — top NV, KPI tổng hợp) |
| Site dev | `miyano` |
| Trạng thái | **[PLANNED — chưa code]** |
| Cập nhật | 2026-06-17 |

> **Trạng thái: [PLANNED — chưa code]**
> Toàn bộ DocType / API / Workflow / BR dưới đây là **DESIGN (đề xuất)**, ground @ scaffold cũ `m10_hr_kpi/` (separate-app `AM …`, reuse ERPNext `Employee`/`Item Group`/`Warehouse`) đã được **ADAPT** sang in-place `AntMed `, native-lite (KHÔNG ERPNext), Frappe-standard BE. Chưa có DocType nào tồn tại trên site `miyano`. Mọi chỗ chưa source được đánh `[UNVERIFIED]` / `[cần khảo sát]`.

---

## 1. Overview

M10 là module **đo lường & thưởng** của AntMed CRM — đứng ở **Wave 4**, sau khi chuỗi vận hành lõi (M04 giao phòng mổ, M09 đơn/AR) và đặc thù (M05 bộ dụng cụ) đã chạy thật và sinh ra dữ liệu sự kiện. M10 KHÔNG tạo dữ liệu nghiệp vụ mới; nó **tổng hợp (aggregate) sự kiện từ các module nguồn** thành **điểm KPI đa chiều** cho từng NV kinh doanh và thành **hoa hồng theo nhóm vật tư**.

Theo `AntMed_CRM_Modules.md §10` (mô tả nghiệp vụ ground-truth):
- **Hồ sơ NV**: tuyến phụ trách (bệnh viện/khoa), kho cá nhân đang giữ, bộ dụng cụ đang quản lý.
- **KPI đa chiều**: doanh số · số lần giao đúng SLA (M04) · tỷ lệ bộ dụng cụ trả đủ-đúng-hạn (M05) · tỷ lệ khách hàng mới · hài lòng bác sỹ (M07).
- **Bảng lương / hoa hồng theo nhóm vật tư**.
- (Lịch công tác + check-in/out GPS được mô tả ở §10 nhưng thuộc về **M07/M12** — xem §Boundaries.)

**Vai trò kép của Tuyến/route NV** (`AntMed Employee Route`): vừa là **chiều phân tích KPI** (KH mới theo tuyến), vừa là **nền dữ liệu cho data-scope BR-13** (M14) — "NV chỉ thấy BV được giao". Đây là lý do M10 đặt ở W4 cạnh M14: bảng phân công NV↔BV chính là thứ M01 (ADR-M01-05) đã hoãn.

**Business value:** Trưởng phòng KD nhìn một bảng KPI tổng hợp toàn đội theo kỳ; NV kinh doanh thấy điểm + hoa hồng của chính mình minh bạch; Kế toán khóa kỳ hoa hồng và đẩy sang lương.

### User stories
1. *Là `Quản lý`*, tôi mở **Bảng KPI** theo kỳ (tháng) để thấy mỗi NV đạt bao nhiêu % ở từng chiều (doanh số / SLA giao / trả bộ đúng hạn / KH mới), để xếp hạng đội.
2. *Là `NV kinh doanh`*, tôi mở trang cá nhân để thấy KPI tháng của **chính tôi** + **hoa hồng** ước tính theo nhóm vật tư đã bán.
3. *Là `Quản lý`/`Kế toán`*, tôi **khóa kỳ** hoa hồng tháng → số liệu đóng băng, đẩy sang module lương ([PLANNED]).

### 6 câu hỏi domain — feasibility check (BA Bước 2)
| # | Câu hỏi | Trả lời cho M10 |
|---|---|---|
| 1 | **CRM stage?** | Giai đoạn **hậu-vận-hành / báo cáo** — M10 đọc kết quả của M04/M05/M09, không chạm lead/giao hàng trực tiếp. |
| 2 | **Ràng buộc hợp đồng/quota?** | Gián tiếp: doanh số chiều KPI lấy từ đơn M09 (đã qua quota M02). M10 KHÔNG tự khóa quota. |
| 3 | **Actor là BV hay bác sỹ?** | Actor chính = **NV kinh doanh** (nhân sự nội bộ). BV/bác sỹ chỉ là chiều phân tích (tuyến, KH mới, hài lòng bác sỹ). |
| 4 | **Nghĩa vụ chứng từ / HĐĐT?** | KHÔNG. M10 không sinh CO/CQ/HĐĐT. |
| 5 | **Truy vết lot / thu hồi?** | KHÔNG. |
| 6 | **Hậu quả nếu data sai?** | **Trung bình–cao**: KPI/hoa hồng sai → tranh chấp lương. ⇒ tính KPI phải **tái lập được** (idempotent), **khóa kỳ** chống sửa hồi tố, và mọi nguồn aggregate phải đếm đúng (`count == rows`). Sai data-scope (NV thấy KPI người khác) = rò rỉ → BR-13. |

---

## 2. DocTypes (native-lite, [PLANNED])

> Adapt từ scaffold cũ `m10_hr_kpi/doctype/*` (prefix `AM `, reuse ERPNext `Employee`/`Item Group`/`Warehouse`/`Customer`). **Thay đổi lock:** `AM `→`AntMed `; reuse ERPNext → native-lite (`AntMed Item Group`/`AntMed Warehouse`/`AntMed Hospital`); actor "NV" giữ **Link → `User`** (Frappe core, KHÔNG ERPNext `Employee`) hoặc DocType native `AntMed Sales Employee` làm hồ sơ NV. Tập field = **tối thiểu** theo acceptance; field mở rộng = backlog.

| DocType | Loại | Field chính (ĐỀ XUẤT — ground scaffold + Modules §10) | Naming |
|---|---|---|---|
| **AntMed Sales Employee** | master | `user` (Link→`User`, reqd, unique — định danh đăng nhập NV) · `employee_name` (Data) · `personal_warehouse` (Link→`AntMed Warehouse` — kho cá nhân, M03) · `manager` (Link→`AntMed Sales Employee` — quản lý trực tiếp) · `max_holding_value` (Currency — trần giá trị được giữ, dùng cho M03/M05) · `active` (Check) | `autoname: field:user` (hoặc series `AntMed-SE-.####`) [cần khảo sát: NV nội bộ map 1-1 với `User` desk hay portal] |
| **AntMed Employee Route** | master/txn | `sales_employee` (Link→`AntMed Sales Employee`, reqd) · `hospital` (Link→`AntMed Hospital`, reqd) · `route_role` (Select: `Chính`\|`Backup`, default `Chính`) · `valid_from` (Date) · `valid_to` (Date) | `autoname: hash` (cặp NV–BV–kỳ; không có khóa tự nhiên gọn) |
| **AntMed KPI Definition** | master | `kpi_code` (Data, reqd, unique) · `kpi_name` (Data, reqd) · `dimension` (Select: `Doanh số`\|`SLA giao`\|`Trả bộ đúng hạn`\|`KH mới`\|`Hài lòng bác sỹ` — chiều đa chiều) · `source_module` (Select: `M09`\|`M04`\|`M05`\|`M01`\|`M07`) · `target` (Float — mục tiêu) · `weight` (Percent — trọng số tổng KPI) · `period` (Select: `Monthly`\|`Quarterly`\|`Yearly`, default `Monthly`) · `active` (Check, default 1) | `autoname: field:kpi_code` |
| **AntMed KPI Score** | txn/log | `sales_employee` (Link→`AntMed Sales Employee`, reqd) · `kpi_definition` (Link→`AntMed KPI Definition`, reqd) · `period` (Data — nhãn kỳ `YYYY-MM` / `YYYY-Qn` / `YYYY`) · `actual_value` (Float) · `achievement_pct` (Percent) · `computed_at` (Datetime) · `is_locked` (Check — khóa kỳ) | `autoname: hash` (idempotent upsert theo bộ ba NV+KPI+period — xem BR-M10-01) |
| **AntMed Commission** | txn | `sales_employee` (Link→`AntMed Sales Employee`, reqd) · `period` (Data `YYYY-MM`) · `item_group` (Link→`AntMed Item Group` — nhóm vật tư, M03) · `base` (Select: `Doanh thu`\|`Lợi nhuận gộp`, default `Doanh thu`) · `base_amount` (Currency — căn cứ tính) · `commission_pct` (Percent — bậc áp dụng) · `commission_amount` (Currency — tiền hoa hồng) · `is_locked` (Check — đã khóa kỳ) · `locked_by` (Link→`User`) · `locked_at` (Datetime) | `autoname: hash` (NV+kỳ+nhóm VT) |
| **AntMed Commission Rule** | master | `rule_name` (Data, reqd, unique) · `item_group` (Link→`AntMed Item Group`) · `base` (Select: `Doanh thu`\|`Lợi nhuận gộp`, default `Doanh thu`) · `tier_table` (child `AntMed Commission Tier` — thay scaffold cũ `tier_table` Long Text JSON, xem ghi chú) · `active` (Check, default 1) | `autoname: field:rule_name` |
| **AntMed Commission Tier** | child | `from_amount` (Currency) · `to_amount` (Currency) · `commission_pct` (Percent) | child của `AntMed Commission Rule` |

> **Adapt note 1 — actor:** scaffold cũ Link → ERPNext `Employee`. Native-lite KHÔNG có ERPNext ⇒ thay bằng DocType native **`AntMed Sales Employee`** (hồ sơ NV) + Link `user`→`User` core. Mọi Link "NV" trong M10 trỏ `AntMed Sales Employee`.
> **Adapt note 2 — nhóm vật tư:** scaffold cũ `Item Group` (ERPNext). Native-lite ⇒ **`AntMed Item Group`** (master nhóm VTYT của M03). Nếu M03 chưa khai nhóm dưới dạng DocType riêng → [cần khảo sát] dùng field Select trên `AntMed Item`.
> **Adapt note 3 — `AntMed Hospital` thay `Customer`:** scaffold `AM Employee Route.hospital` Link→`Customer`; in-place đã có `AntMed Hospital` (M01) ⇒ trỏ về đó.
> **Adapt note 4 — tier_table:** scaffold cũ là `Long Text` chứa JSON `[{qty_from,qty_to,pct}]`. ĐỀ XUẤT nâng thành **child table `AntMed Commission Tier`** (validate được, tránh parse JSON thủ công). Nếu factory muốn giữ MVP nhanh → tạm Long Text JSON, đánh dấu nợ kỹ thuật.
> **Adapt note 5 — `formula` Python expr:** scaffold `AM KPI Definition.formula` là `Long Text` chứa `SELECT …` eval qua `frappe.db.sql`. **CẢNH BÁO BẢO MẬT [UNVERIFIED]:** eval SQL/Python expr từ field do người dùng nhập = SQL injection. ĐỀ XUẤT bỏ `formula` tự do; thay bằng **`dimension` + `source_module` enum** rồi map sang hàm aggregate Python **cố định trong code** (xem §5 `compute_kpi`). Đây là khác biệt thiết kế chính so với scaffold.

---

## 3. Workflow

**Không có Frappe Workflow / state machine cho các txn KPI/Score.** `AntMed KPI Score` và `AntMed Commission` là bản ghi tính-toán (log/txn), không qua chuỗi duyệt nhiều trạng thái.

Cơ chế "khóa kỳ" (period lock) KHÔNG dùng `workflow_state` mà dùng **field cờ `is_locked`** + chặn ghi trong controller (BR-M10-03). Lý do: lock áp cho **một lô bản ghi cùng `period`**, không phải vòng đời từng doc → field-flag + hook hợp hơn workflow. `[cần khảo sát]` nếu nghiệp vụ muốn quy trình duyệt "đề nghị khóa → Quản lý duyệt → Kế toán chốt" thì khi đó mới cân nhắc Frappe Workflow trên một DocType `AntMed Commission Period` [PLANNED].

DocType M10 **không submit** (`is_submittable: 0`) → không dùng `docstatus`.

---

## 4. Business Rules

> Module hooks tại `crm/antmed/hr_kpi/hooks.py` (hoặc gộp `crm/antmed/doctype/<dt>/<dt>.py` controller `validate`), wire qua `doc_events` trong `crm/hooks.py` (chỉ THÊM key). BR liên-module (BR-01..15) M10 **đọc đầu ra**, không enforce; BR riêng module đánh số `BR-M10-xx`.

| BR | Mô tả | Nơi enforce |
|---|---|---|
| **BR-M10-01** | **KPI Score idempotent:** với bộ ba (`sales_employee`,`kpi_definition`,`period`) chỉ tồn tại 1 bản ghi; tính lại = **upsert** (cập nhật `actual_value`/`achievement_pct`/`computed_at`), KHÔNG tạo trùng. | `scheduler.compute_kpi` (upsert) + controller `AntMed KPI Score.validate` chặn duplicate bộ ba |
| **BR-M10-02** | **Công thức KPI từ enum, KHÔNG eval tự do:** `achievement_pct = actual_value / target * 100` (target>0, else 0); `actual_value` lấy từ hàm aggregate cố định theo `dimension`+`source_module` (không SQL/expr người dùng). | `scheduler.compute_kpi` (map enum→hàm) — thay `formula` của scaffold |
| **BR-M10-03** | **Khóa kỳ bất biến:** khi `is_locked=1`, mọi sửa `actual_value`/`achievement_pct`/`base_amount`/`commission_amount` → `frappe.throw(_("BR-M10-03: Kỳ … đã khóa, không thể sửa"))`. Chỉ `Quản lý`/`Kế toán` được set khóa. | controller `validate` của `AntMed KPI Score` + `AntMed Commission` |
| **BR-M10-04** | **Hoa hồng theo bậc đúng nhóm VT:** `commission_pct` chọn theo tier mà `base_amount` rơi vào (`from_amount ≤ base_amount ≤ to_amount`) của `AntMed Commission Rule` active khớp `item_group`; `commission_amount = base_amount * pct`. Không có rule khớp → 0 + cảnh báo. | `compute_commission` (api/scheduler) + `AntMed Commission.validate` |
| **BR-M10-05 (= BR-13)** | **Data-scope KPI/hoa hồng:** `NV kinh doanh` chỉ đọc `AntMed KPI Score`/`AntMed Commission` của **chính mình** (`sales_employee.user == frappe.session.user`); `Quản lý` thấy đội mình (theo `manager`). | `permission_query_conditions` cho 2 DocType (M14/W4) — **nền = `AntMed Employee Route`** (NV↔BV) |
| BR-13 (liên-module) | M10 **cấp dữ liệu nền** cho data-scope toàn hệ qua `AntMed Employee Route` (NV phụ trách BV nào). M01 ADR-M01-05 đã hoãn — M10 W4 land bảng này. | `permission_query_conditions` (5 doctype) — README dòng 215 |

> **Invariant kỹ thuật (gate, không phải BR nghiệp vụ):** mọi list/aggregate endpoint giữ `count == rows` (đếm qua `get_list(limit_page_length=0)`); tổng hoa hồng theo NV = Σ dòng nhóm-VT (không thất thoát).

---

## 5. API

> File `crm/api/antmed/hr_kpi.py`. Mọi hàm `@frappe.whitelist(methods=["GET"|"POST"])`, **type-annotated** (`crm/hooks.py` `require_type_annotated_api_methods`), trả **RAW dict/list**. Lỗi nghiệp vụ = `frappe.throw(_("BR-M10-xx: …"))`. Aggregate nguồn dùng **lazy-import** module M04/M05/M09 (xem §6).

| Endpoint (`antmed_crm.api.antmed.hr_kpi.…`) | Verb | Mô tả |
|---|---|---|
| `list_team` | GET | Danh sách NV của đội (`AntMed Sales Employee`): `name`, `employee_name`, `personal_warehouse`, `manager`, `active`. Lọc theo `manager` cho `Quản lý`. **count==rows.** Trả `{data, total_count}`. |
| `get_sales_employee` | GET | `get_sales_employee(name: str) -> dict`: hồ sơ NV + tuyến (`routes` từ `AntMed Employee Route`) + KPI kỳ hiện tại (list) + hoa hồng kỳ. `frappe.has_permission`/`PermissionError` nếu không read được. |
| `kpi_board` | GET | `kpi_board(period: str, manager: str\|None=None) -> dict`: ma trận KPI đa chiều cho 1 kỳ — mỗi NV × mỗi `dimension` (achievement_pct) + điểm tổng (Σ pct×weight). Nguồn = `AntMed KPI Score`. count==rows theo số NV. |
| `compute_kpi` | POST | `compute_kpi(period: str\|None=None) -> dict`: chạy tính KPI cho kỳ (idempotent upsert, BR-M10-01/02). Chặn nếu kỳ đã khóa (BR-M10-03). Trả `{computed: int, period: str}`. (Cũng được scheduler gọi — xem §6.) Role: `Quản lý`. |
| `list_commission` | GET | `list_commission(period: str, sales_employee: str\|None=None) -> dict`: hoa hồng theo NV × nhóm VT × kỳ; tổng theo NV. Data-scope BR-M10-05. count==rows. |
| `compute_commission` | POST | `compute_commission(period: str) -> dict`: tính lại hoa hồng kỳ theo `AntMed Commission Rule` (BR-M10-04). Chặn nếu khóa. Role: `Quản lý`. |
| `lock_period` | POST | `lock_period(period: str) -> dict`: set `is_locked=1` + `locked_by/locked_at` cho mọi `AntMed KPI Score`/`AntMed Commission` của kỳ → đẩy sang lương ([PLANNED]). Role: `Quản lý`/`Kế toán`. Idempotent. |

> **Invariant count==rows** áp cho `list_team`, `kpi_board`, `list_commission`: `len(data) == total_count` khi không phân trang. Aggregate (`kpi_board`/`list_commission`) phải đếm số NV/dòng khớp filter, không bị cắt trang.

---

## 6. Integration

M10 là **consumer cuối DAG** (PLAN §2): `M04, M05, M09 → M10 → M11`. M10 **đọc** đầu ra các module nguồn, **không** ghi ngược.

**doc_events VÀO (M10 nhận tín hiệu để tính):**
- KHÔNG cần `doc_events` đồng bộ-thời-gian-thực cho MVP. Tính KPI/hoa hồng theo **scheduler** (batch cuối kỳ / hằng ngày). `[cần khảo sát]` nếu cần realtime: hook `AntMed Order.on_submit` (M09) / `AntMed Delivery.on_update` (M04) / `AntMed Instrument Set` trả (M05) → enqueue tính lại KPI NV liên quan.

**doc_events RA:** không có (M10 không trigger module khác; M11 đọc bảng KPI/hoa hồng của M10 qua API).

**Aggregate cross-module (lazy-import + truyền PK):** trong `compute_kpi`/`compute_commission`, mỗi `dimension` map sang một hàm đọc module nguồn — import **bên trong hàm** (lazy) để tránh phụ thuộc vòng + tránh tải khi không cần:
| dimension | Nguồn (lazy-import) | Đại lượng |
|---|---|---|
| Doanh số | M09 `AntMed Order`/`AntMed AR Entry` | Σ doanh thu đơn của NV trong kỳ |
| SLA giao | M04 `AntMed Delivery` | tỷ lệ giao đúng giờ ca / tổng ca |
| Trả bộ đúng hạn | M05 `AntMed Instrument Set` | tỷ lệ bộ trả đủ-đúng-hạn |
| KH mới | M01 `AntMed Hospital` (qua `AntMed Employee Route`) | số BV mới phụ trách trong kỳ |
| Hài lòng bác sỹ | M07 `AntMed Doctor Visit`/`Care Note` | điểm/tỷ lệ hài lòng |

> Truyền **PK (name)** giữa module, KHÔNG truyền doc object. Nếu module nguồn **chưa land** (W4 chạy trước W2/W3 hoàn tất ở một số nhánh) → hàm aggregate trả 0 + `frappe.log_error` (không crash KPI). Đây là **compliance gate mềm**: KPI chỉ "đủ" khi tất cả nguồn đã land.

**Scheduler** (`crm/hooks.py` `scheduler_events`, THÊM key):
- `cron`/`daily`: `crm.antmed.hr_kpi.scheduler.compute_kpi` — tính KPI kỳ hiện tại (idempotent). Adapt từ scaffold `m10_hr_kpi/scheduler.py::compute_kpi` nhưng **bỏ eval SQL tự do** (BR-M10-02).
- `monthly`: `…compute_commission` cho kỳ tháng trước (gợi ý). `[cần khảo sát]` lịch chốt.

**Auto-tạo hồ sơ NV:** scaffold cũ `ensure_sales_employee` hook trên `Employee.after_insert`. Native-lite KHÔNG có ERPNext `Employee` ⇒ ĐỀ XUẤT bỏ auto-hook, tạo `AntMed Sales Employee` thủ công / qua M14 khi cấp role `NV kinh doanh`. `[cần khảo sát]` có gắn `User.on_update` để auto-tạo khi user nhận role `NV kinh doanh` không.

---

## 7. UI

> Vue 3 + frappe-ui SPA. `createResource` gọi `antmed_crm.api.antmed.hr_kpi.*`, đọc `r.data.data`. Route APPEND vào `frontend/src/router.js` (lazy). Nhãn 100% tiếng Việt qua `__()`. KHÔNG đụng route CRM gốc; KHÔNG `crm.api.*`.

Màn hình ground @ `AntMed_CRM_UI_Design.md`:
- **§2.3 "Đội ngũ"** (Trưởng phòng KD): bảng NV — ảnh, tuyến BV, kho cá nhân (số SKU + giá trị), bộ dụng cụ đang quản lý, KPI tháng (thanh ngang). Click NV → trang cá nhân (timeline check-in, lịch sử giao, công nợ giúp thu, doanh thu, khiếu nại).
- **§6.3 "Hoa hồng NV"** (Kế toán): theo nhóm vật tư × NV × tháng; quy tắc cấu hình ở Settings; nút **"Khóa kỳ" → đẩy sang module lương**.
- **§ bảng quyền dòng "10. KPI NS"**: "Trang NV, Bảng KPI" — dùng bởi **Trưởng KD, CEO**.

| Route | Page | Role | Mô tả |
|---|---|---|---|
| `/antmed/team` | `AntmedTeam.vue` | `Quản lý` | Bảng đội ngũ NV (§2.3) — `list_team` + KPI tháng inline |
| `/antmed/team/:name` | `AntmedSalesEmployeeDetail.vue` | `Quản lý`, NV (chính mình) | Trang cá nhân NV — `get_sales_employee` (tuyến + KPI + hoa hồng) |
| `/antmed/kpi` | `AntmedKpiBoard.vue` | `Quản lý`, CEO | Bảng KPI đa chiều theo kỳ — `kpi_board` |
| `/antmed/commission` | `AntmedCommission.vue` | `Kế toán`, `Quản lý` | Hoa hồng NV × nhóm VT × kỳ (§6.3) — `list_commission` + nút "Khóa kỳ" (`lock_period`) |

> Mobile (NV kinh doanh xem KPI/hoa hồng của chính mình) = phần của M12 PWA / hoặc widget trong trang cá nhân; M10 cung cấp endpoint, FE mobile thuộc M12.

---

## 8. Build slices (cho factory — mỗi slice 1 vòng, KHÔNG commit)

1. **Slice A — Hồ sơ NV + Tuyến (nền data-scope):** DocType `AntMed Sales Employee` + `AntMed Employee Route` + DocPerm; API `list_team`/`get_sales_employee`; FE `/antmed/team` + `/antmed/team/:name`. TDD: tạo NV, gán tuyến BV, list count==rows. *(Slice này gỡ nợ ADR-M01-05 — bảng NV↔BV cho BR-13.)*
2. **Slice B — KPI engine:** DocType `AntMed KPI Definition` + `AntMed KPI Score`; `scheduler.compute_kpi` (enum→hàm aggregate, lazy-import nguồn, idempotent BR-M10-01/02); API `kpi_board`/`compute_kpi`; FE `/antmed/kpi`. TDD: tính 2 lần → 1 bản ghi/bộ ba; target=0 → pct=0.
3. **Slice C — Hoa hồng:** `AntMed Commission Rule` + `AntMed Commission Tier` (child) + `AntMed Commission`; `compute_commission` (BR-M10-04 chọn bậc); API `list_commission`/`compute_commission`; FE `/antmed/commission`. TDD: base_amount rơi đúng tier; không rule → 0.
4. **Slice D — Khóa kỳ + data-scope:** `lock_period` (BR-M10-03), cờ `is_locked` chặn sửa; `permission_query_conditions` BR-M10-05 (NV thấy của mình, Quản lý thấy đội). TDD: sau khóa sửa → throw; NV A không đọc Score của NV B (count==rows theo từng user).

---

## 9. ADRs

### ADR-M10-01: KPI từ enum `dimension`+`source_module`, KHÔNG eval công thức tự do
- **Status**: Proposed
- **Date**: 2026-06-17
- **Context**: Scaffold cũ `AM KPI Definition.formula` (Long Text) chứa `SELECT …` rồi `frappe.db.sql(formula, …)` trong `scheduler._eval_formula`. Đây là **lỗ SQL injection / RCE** — field do người dùng nhập chạy thẳng vào DB. Vi phạm Frappe-standard + security (M14).
- **Decision**: Bỏ `formula`. Định nghĩa KPI bằng cặp **`dimension` (enum 5 chiều)** + **`source_module`** + `target`/`weight`. Code map mỗi enum → một hàm aggregate Python **cố định, đã review** (lazy-import module nguồn). Người dùng chỉ chọn từ danh sách, không nhập SQL.
- **Consequences**: (+) An toàn, tái lập được, test được; (−) thêm chiều KPI mới phải sửa code (chấp nhận — chiều KPI ít, ổn định). Tham chiếu DEC-A (role VI) cho phân quyền tính/khóa.

### ADR-M10-02: Hồ sơ NV native (`AntMed Sales Employee` + Link `User`), KHÔNG ERPNext `Employee`
- **Status**: Proposed
- **Date**: 2026-06-17
- **Context**: Scaffold reuse ERPNext `Employee`/`Item Group`/`Warehouse`. Quyết định nền **D1 = native-lite (KHÔNG ERPNext)** (PLAN §16, SPEC §2) ⇒ không có `Employee`.
- **Decision**: Tạo `AntMed Sales Employee` (Link `user`→`User` core) làm actor NV; nhóm VT = `AntMed Item Group` (M03); BV = `AntMed Hospital` (M01); kho = `AntMed Warehouse` (M03). Bỏ auto-hook `ensure_sales_employee` trên `Employee`.
- **Consequences**: (+) Nhất quán native-lite, không kéo ERPNext; (−) phải tự quản vòng đời hồ sơ NV (tạo khi cấp role) — wiring ở M14. Kế thừa ADR-M01-02 (prefix `AntMed `).

### ADR-M10-03: Khóa kỳ bằng field-flag `is_locked`, KHÔNG Frappe Workflow
- **Status**: Proposed
- **Date**: 2026-06-17
- **Context**: "Khóa kỳ" áp cho **một lô bản ghi cùng `period`** rồi đẩy lương, không phải vòng đời nhiều trạng thái của từng doc.
- **Decision**: Dùng cờ `is_locked` + `locked_by`/`locked_at`, chặn sửa trong controller `validate` (BR-M10-03), set qua `lock_period`. Không tạo Workflow (D2) cho M10 trừ khi nghiệp vụ yêu cầu quy trình duyệt khóa nhiều bước (khi đó cân nhắc `AntMed Commission Period` [PLANNED]).
- **Consequences**: (+) Đơn giản, idempotent; (−) không có lịch sử chuyển trạng thái chuẩn workflow — bù bằng `track_changes` + audit (BR-10).

> Kế thừa: ADR-M01-01 (in-place), ADR-M01-02 (prefix `AntMed `), ADR-M01-05 (data-scope hoãn ở M01 → **M10 Slice A/D gỡ nợ**); DEC-A (role VI), D1 (native-lite), D2 (Frappe Workflow).

---

## 10. Acceptance / DoD

Theo SPEC §6 — một slice "xong" khi: **BE run-tests `Ran N OK`** + **FE vitest xanh** + **`yarn build` xanh** + (sau USER reload) **pixel verify** + **no-regression**.

**BE test** (`crm/tests/test_antmed_hr_kpi.py`, chạy chung `before_tests`):
- DocType tồn tại sau migrate + đủ field tối thiểu (`frappe.get_meta`): `AntMed Sales Employee`, `AntMed Employee Route`, `AntMed KPI Definition`, `AntMed KPI Score`, `AntMed Commission`, `AntMed Commission Rule` (+child `AntMed Commission Tier`).
- `AntMed Sales Employee.user` unique; KHÔNG Link tới `Employee` (assert meta options = `User`).
- BR-M10-01: `compute_kpi(period)` chạy 2 lần → đúng 1 `AntMed KPI Score`/bộ ba (idempotent).
- BR-M10-02: `target=0` → `achievement_pct=0` (không chia 0); KHÔNG còn field `formula`/eval SQL.
- BR-M10-04: `base_amount` rơi đúng tier → `commission_pct`/`commission_amount` đúng; không rule khớp → 0.
- BR-M10-03: set `is_locked=1` rồi sửa `actual_value` → `frappe.throw` (PermissionError/ValidationError).
- API: `kpi_board`/`list_team`/`list_commission` trả `{data,total_count}`, **`len(data)==total_count`** không phân trang.
- BR-M10-05: user NV A gọi `list_commission` không thấy bản ghi của NV B (data-scope; count==rows theo user).
- **No-regression**: `test_antmed_bootstrap` + `test_antmed_customer` + 4 test gốc CRM xanh.

**FE test** (`frontend/tests/unit/antmedHrKpi.test.js`): 4 route mới tồn tại (path/name/lazy); page gọi đúng `antmed_crm.api.antmed.hr_kpi.*`; route CRM gốc còn; KHÔNG `antmed_crm.api`/axios. `yarn build` emit chunk `Antmed*` không vỡ.

**Pixel (Playwright, sau reload)**: `/antmed/kpi` render bảng KPI đa chiều theo kỳ; `/antmed/commission` render hoa hồng + nút "Khóa kỳ"; 0 console error; API 200.

---

## Tham chiếu chéo
- **SSoT cấp dự án**: `../SPEC_AntMed_CRM.md` (§2 native-lite D1, §5 Frappe-standard BE, §6 DoD), `../PLAN_AntMed_CRM.md` (§2 DAG M04/M05/M09→M10→M11, §3 Wave W4, D1/D2).
- **Mô tả nghiệp vụ**: `../../antmed_crm/docs/AntMed_CRM_Modules.md §10` (hồ sơ NV, KPI đa chiều, hoa hồng theo nhóm VT) + §11 (Dashboard tiêu thụ KPI).
- **UI**: `../../antmed_crm/docs/AntMed_CRM_UI_Design.md` §2.3 "Đội ngũ", §6.3 "Hoa hồng NV", bảng quyền dòng "10. KPI NS".
- **House style**: `./m01_customer360.md`.
- **Module liên quan**: M01 (`./m01_customer360.md` — `AntMed Hospital`/`AntMed Doctor`, ADR-M01-05 data-scope hoãn → M10 gỡ); M04/M05/M09 (nguồn KPI — [PLANNED]); M11 (Dashboard tiêu thụ); M14 (BR-13 `permission_query_conditions`, BR-10 audit — [PLANNED]).
- **Scaffold tham chiếu (separate-app cũ, đã ADAPT)**: `docs/antmed_crm/antmed_crm/m10_hr_kpi/doctype/{am_sales_employee,am_employee_route,am_kpi_definition,am_kpi_score,am_commission_rule}/*.json`, `…/scheduler.py`, `…/hooks.py`.
- **BR map**: `docs/antmed_crm/README.md` (BR-10 audit, BR-13 data-scope 5 doctype).
