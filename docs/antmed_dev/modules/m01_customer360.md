# M01 — Quản lý Khách hàng (Customer 360°) — R2 lát cắt dọc Bệnh viện + Bác sỹ

| Mục | Giá trị |
|---|---|
| Module folder | `crm/antmed/` (module Frappe **`AntMed`**, scrubbed = `antmed`) |
| DocType folder | `crm/antmed/doctype/antmed_hospital/`, `crm/antmed/doctype/antmed_doctor/` |
| API package | `crm/api/antmed/customer.py` (đường gọi `antmed_crm.api.antmed.customer.<fn>`) |
| FE pages | `frontend/src/pages/Antmed*` + route `/antmed/hospitals`, `/antmed/hospitals/:name`, `/antmed/doctors/:name` |
| Phase triển khai | 1 — Lõi vận hành (đây là **feature nghiệp vụ M1 thật**, khác R1 foundation) |
| Round | **R2** (nối tiếp R1 Bootstrap — xem `m01_bootstrap.md`) |
| Role chính | `NV kinh doanh`, `Quản lý` (⚠️ đổi tiếng Việt theo DEC-A — xem `./m14_rbac_w0_role_naming.md`; trước W0-1 là `AntMed Sales Rep`/`AntMed Manager`) |
| Site dev | `miyano` |
| Trạng thái docs | Stable (spec chốt cho R2 — đủ để BE/FE code) |
| Cập nhật | 2026-06-17 |

> 🔗 **Tiền đề (R1 đã land, verified @ source)**: module `AntMed` đã khai trong `crm/modules.txt`; package `crm/api/antmed/` tồn tại (`health.py::ping`); 3 Role fixture đã có (`crm/fixtures/role.json`); FE đã có route `/antmed` + `AntmedHome.vue` + `data/antmed.js`. R2 **mở rộng** namespace này, KHÔNG dựng lại nền.

---

## Overview

R2 là **vertical slice** (lát cắt dọc) đầu tiên có DocType nghiệp vụ thật của Module 1 — Customer 360°. Phạm vi: 2 thực thể lõi của "mặt 360" + đường BE→FE list/detail chạy thật trên site `miyano`.

Theo `AntMed_CRM_Modules.md §1` (mô tả nghiệp vụ ground-truth):
- **Hồ sơ bệnh viện** (dòng 13): mã, hạng, khoa/phòng mổ, địa chỉ, mã số thuế, trạng thái hợp đồng (đã ký / tiềm năng / hết hạn).
- **Hồ sơ bác sỹ — đơn vị chăm sóc cốt lõi** (dòng 14): chuyên khoa, ca mổ thường gặp, vật tư ưa dùng, sở thích bộ dụng cụ, lịch mổ định kỳ, sinh nhật, ghi chú cá nhân.

**Mặt 360 của R2** = bệnh viện (pháp nhân) ⟶ danh sách bác sỹ thuộc bệnh viện đó (cá nhân chăm sóc) ⟶ profile từng bác sỹ + link ngược về BV. Đây là xương sống quan hệ mà các module sau (M02 hợp đồng-quota theo BV, M04 giao phòng mổ theo bác sỹ, M08 pipeline) sẽ "treo" vào.

**Business value (R2)**: NV kinh doanh tra cứu nhanh hồ sơ BV trúng thầu/tiềm năng và cây bác sỹ phụ trách — nền cho chăm sóc bác sỹ (sinh nhật, ghi chú) và cho mọi liên kết hợp đồng/giao hàng về sau.

### 6 câu hỏi domain — feasibility check (BA Bước 2)

| # | Câu hỏi | Trả lời cho R2 |
|---|---|---|
| 1 | **CRM stage?** | Giai đoạn **lead/khách hàng** (hồ sơ BV + bác sỹ). CHƯA chạm hợp đồng/giao phòng mổ/mượn bộ/chứng từ/công nợ. |
| 2 | **Ràng buộc hợp đồng/quota?** | **KHÔNG** ở R2. `contract_status` chỉ là **nhãn Select tĩnh** trên hồ sơ BV (đã ký/tiềm năng/hết hạn), KHÔNG đối chiếu danh mục trúng thầu (BR-01), KHÔNG khoá quota (BR-06). Liên kết quota thật = M02 round sau. |
| 3 | **Actor là bệnh viện hay bác sỹ?** | **Cả hai**: `AntMed Hospital` = pháp nhân BV; `AntMed Doctor` = cá nhân bác sỹ, Link→Hospital. Sơ đồ ra-quyết-định (AM Decision Maker) = **OUT-of-scope R2** (backlog R3+). |
| 4 | **Nghĩa vụ chứng từ / HĐĐT?** | **KHÔNG**. R2 không sinh CO/CQ/ĐKLH/giấy phép NK, không phát hành HĐĐT. Đó là M06. |
| 5 | **Truy vết lot / thu hồi?** | **KHÔNG**. Không có lot/ca mổ/recall ở R2 (M03/M05). |
| 6 | **Hậu quả nếu data sai?** | Thấp ở R2 (master data tra cứu). Nhưng **data-scope BR-13** (NV chỉ thấy BV được giao) **CHƯA wiring** ở R2 → xem ADR-M01-05 + Boundaries. `count == rows` vẫn phải đúng cho list endpoint. |

---

## Scope — Boundaries (Always / Never)

### Always (R2 LUÔN làm)
- **Always** tạo DocType **`AntMed Hospital`** tại `crm/antmed/doctype/antmed_hospital/` với module = `AntMed`, custom = 0 (doctype của app, đi theo code).
- **Always** tạo DocType **`AntMed Doctor`** tại `crm/antmed/doctype/antmed_doctor/`, module = `AntMed`.
- **Always** dùng naming an toàn (xem §DocTypes): Hospital autoname `field:hospital_code` (hoặc series riêng), Doctor naming_series `AM-DOC-.YYYY.-.####`. **Never** dùng `AM-DR` (reserve cho M04 Delivery Request).
- **Always** đặt endpoint trong `crm/api/antmed/customer.py`, đường gọi `antmed_crm.api.antmed.customer.<fn>`, **type-annotated** (vì `crm/hooks.py:28 require_type_annotated_api_methods = True`), trả **RAW dict/list** (KHÔNG envelope).
- **Always** giữ invariant **count == len(data)** ở `list_hospitals` khi không phân trang (BR-13 count==rows).
- **Always** `get_hospital`/`get_doctor` gọi `frappe.has_permission(...)` và `frappe.throw(..., frappe.PermissionError)` khi không read được.
- **Always** thêm DocPerm cho 3 Role R1 trên 2 DocType mới (read tối thiểu cho Sales Rep; read+write cho Manager) — xem §Permissions.
- **Always** thêm route FE mới **chỉ bằng cách APPEND** vào mảng `routes` trong `frontend/src/router.js` (lazy import).

### Never (R2 TUYỆT ĐỐI KHÔNG)
- **Never** extend/sửa `CRM Organization` hay `Contact` để nhồi field y tế (ADR-M01-04). 2 DocType mới là độc lập.
- **Never** dùng naming series `AM-DR-…` (đụng M04). **Never** tái dùng prefix doctype `AM ` (in-place dùng `AntMed ` — ADR-M01-02).
- **Never** tạo child table (departments / decision_makers / preferences / interaction timeline) ở R2 — **OUT-of-scope, backlog R3+**.
- **Never** wiring `contract_status` vào quota/BR-01/BR-06 — nhãn tĩnh thôi.
- **Never** đụng route/page/store Frappe CRM gốc (Leads/Deals/Contacts/Organizations còn NGUYÊN). Chỉ THÊM route `/antmed/...`.
- **Never** wrap response bằng `_ok`/`_err` / `MSG.*`. **Never** trả `frappe.response` thủ công.
- **Never** wiring `permission_query_conditions` data-scope BR-13 ở R2 (chưa có field "NV được giao BV" — backlog, ADR-M01-05). RBAC ở R2 = DocPerm theo Role (toàn quyền read trong role), KHÔNG lọc theo NV.
- **Never** git commit / push / merge / reset DB / drop site (HARD-STOP — thuộc user).

---

## DocTypes

> Field set = **tối thiểu** theo acceptance R2, ground @ `AntMed_CRM_Modules.md §1` dòng 13–14. Field nghiệp vụ mở rộng (ca mổ thường gặp, vật tư ưa dùng, lịch mổ, phân vai KH) = backlog R3+.

### DocType `AntMed Hospital`

| Thuộc tính DocType | Giá trị |
|---|---|
| `name` (label) | `AntMed Hospital` |
| Module | `AntMed` |
| `autoname` | **`field:hospital_code`** (mã BV là khoá tự nhiên, unique) — HOẶC `naming_series` riêng nếu BE muốn. **KHÔNG** `AM-DR`. |
| `naming_rule` | `By fieldname` (nếu chọn autoname `field:hospital_code`) |
| `title_field` | `hospital_name` |
| `track_changes` | 1 (gợi ý — phục vụ audit về sau, KHÔNG bắt buộc R2) |

**Fields (tối thiểu — verify @source M1 doc dòng 13):**

| fieldname | label | fieldtype | options / ràng buộc | reqd | unique | Ghi chú |
|---|---|---|---|---|---|---|
| `hospital_code` | Mã bệnh viện | Data | — | 1 | **1** | Khoá tự nhiên; nếu autoname `field:` thì Frappe tự set reqd+unique |
| `hospital_name` | Tên bệnh viện | Data | — | **1** | — | mandatory; là `title_field` |
| `rank` | Hạng bệnh viện | Select | `Đặc biệt`\n`I`\n`II`\n`III`\n`Khác` | — | — | options tiếng Việt, mỗi giá trị 1 dòng |
| `tax_code` | Mã số thuế | Data | — | — | — | MST pháp nhân BV |
| `address` | Địa chỉ | Small Text | — | — | — | — |
| `contract_status` | Trạng thái hợp đồng | Select | `Đã ký`\n`Tiềm năng`\n`Hết hạn` | — | — | **nhãn tĩnh** R2 — KHÔNG nối quota |

> Boundaries — Ask-first: thêm `default` cho `contract_status` (vd `Tiềm năng`) là tuỳ chọn BE; nếu thêm thì ghi nhận, KHÔNG đổi tập options.

### DocType `AntMed Doctor`

| Thuộc tính DocType | Giá trị |
|---|---|
| `name` (label) | `AntMed Doctor` |
| Module | `AntMed` |
| `autoname` | **`naming_series:`** với series **`AM-DOC-.YYYY.-.####`** (vd `AM-DOC-2026-0001`). **KHÔNG** `AM-DR`. |
| `naming_rule` | `By "Naming Series" field` |
| `title_field` | `full_name` |

**Fields (tối thiểu — verify @source M1 doc dòng 14):**

| fieldname | label | fieldtype | options / ràng buộc | reqd | unique | Ghi chú |
|---|---|---|---|---|---|---|
| `naming_series` | Series | Select | `AM-DOC-.YYYY.-.####` | — | — | field hệ thống cho naming_series |
| `doctor_code` | Mã bác sỹ | Data | — | — | **1** | mã định danh nghiệp vụ, unique (khác `name` series) |
| `full_name` | Họ tên | Data | — | **1** | — | mandatory; `title_field` |
| `hospital` | Bệnh viện | Link | `AntMed Hospital` | — | — | Link tới pháp nhân BV (gốc của 360) |
| `specialty` | Chuyên khoa | Data | — | — | — | — |
| `birthday` | Sinh nhật | Date | — | — | — | phục vụ nhắc chăm sóc (R3+) |
| `phone` | Điện thoại | Data | — | — | — | — |
| `email` | Email | Data | — | — | — | — |
| `zalo` | Zalo | Data | — | — | — | — |
| `notes` | Ghi chú cá nhân | Small Text | — | — | — | — |

> **Lưu ý unique trên `doctor_code`**: vì `name` dùng naming_series (không phải `doctor_code`), nên `doctor_code` cần `unique:1` riêng để chặn trùng mã nghiệp vụ. Nếu BE chọn autoname `field:doctor_code` thay vì series thì bỏ `naming_series` field — nhưng acceptance ưu tiên **naming_series riêng `AM-DOC-`** → giữ phương án series.

---

## Workflow

**KHÔNG có workflow / state machine ở R2.** `contract_status` là Select tĩnh, không phải workflow_state (không có chuyển trạng thái có ràng buộc). Vòng đời hợp đồng thật = M02. Không dùng `docstatus` (2 DocType này là master data, không submit).

---

## API

> File: `crm/api/antmed/customer.py`. Mọi hàm `@frappe.whitelist(methods=["GET"])`, **type-annotated**, trả **RAW**. Lỗi nghiệp vụ/permission = `frappe.throw(...)` in-handler (Frappe trả exception JSON; KHÔNG envelope).

### 1) `antmed_crm.api.antmed.customer.list_hospitals`

| Thuộc tính | Giá trị |
|---|---|
| Signature | `def list_hospitals(filters: dict \| str \| None = None, start: int = 0, page_length: int = 20, search: str \| None = None) -> dict:` |
| Verb | GET |
| Auth | Yêu cầu session (guest → **dispatcher-403**) |
| Trả về | **RAW dict** `{ "data": list[dict], "total_count": int }` — KHÔNG bọc message |

**Field mỗi item trong `data`** (đúng acceptance): `name`, `hospital_name`, `rank`, `contract_status`, `tax_code`.

**Hành vi:**
- `filters`: dict hoặc JSON-string (Frappe truyền query-param dạng string → BE `frappe.parse_json` nếu là str). Áp vào `frappe.get_list("AntMed Hospital", filters=..., ...)`.
- `search`: nếu có, **search theo `hospital_name`** (LIKE `%search%`) — gộp vào filters (`["hospital_name", "like", f"%{search}%"]`). Nếu acceptance chỉ truyền qua `filters`, BE cũng chấp nhận `filters` chứa điều kiện `hospital_name like`.
- `total_count` = tổng số bản ghi **khớp filter/search** (KHÔNG bị cắt bởi `page_length`) — dùng `frappe.db.count("AntMed Hospital", filters=...)`.
- **Invariant BR-13 (count == rows)**: khi gọi **không phân trang** (`page_length` đủ lớn / hoặc page đầu phủ hết), `len(data) == total_count`. Test phải chứng minh điều này.
- `get_list` tự áp DocPerm theo Role của user (Frappe permission engine). R2 chưa có `permission_query_conditions` cho 2 DocType này → tất cả user có read-perm thấy toàn bộ; khi M14/R3 thêm data-scope, invariant `count == rows` vẫn phải giữ qua `permission_query_conditions`.

**Ví dụ shape trả (RAW):**
```json
{
  "data": [
    {"name": "BVTW-HUE", "hospital_name": "BV TW Huế", "rank": "Đặc biệt", "contract_status": "Đã ký", "tax_code": "3300101234"}
  ],
  "total_count": 1
}
```

### 2) `antmed_crm.api.antmed.customer.get_hospital`

| Thuộc tính | Giá trị |
|---|---|
| Signature | `def get_hospital(name: str) -> dict:` |
| Verb | GET |
| Auth | session; **throw `frappe.PermissionError`** nếu `not frappe.has_permission("AntMed Hospital", "read", doc=name)` (in-handler permission-403) |
| Trả về | RAW dict = field BV + `doctors` (list con) |

**Shape (RAW) — "mặt 360" của bệnh viện:**
```json
{
  "name": "BVTW-HUE",
  "hospital_code": "BVTW-HUE",
  "hospital_name": "BV TW Huế",
  "rank": "Đặc biệt",
  "tax_code": "3300101234",
  "address": "...",
  "contract_status": "Đã ký",
  "doctors": [
    {"name": "AM-DOC-2026-0001", "full_name": "Nguyễn Văn A", "specialty": "Ngoại tổng quát", "phone": "09xx"}
  ]
}
```
- `doctors` = `frappe.get_list("AntMed Doctor", filters={"hospital": name}, fields=["name","full_name","specialty","phone"])`. Children fields **đúng acceptance**: `name`, `full_name`, `specialty`, `phone`.
- Nếu `name` không tồn tại → `frappe.DoesNotExistError` (Frappe ném khi `get_doc`). Permission fail → `PermissionError`.

### 3) `antmed_crm.api.antmed.customer.list_doctors`

| Thuộc tính | Giá trị |
|---|---|
| Signature | `def list_doctors(filters: dict \| str \| None = None, hospital: str \| None = None, start: int = 0, page_length: int = 20) -> dict:` |
| Verb | GET |
| Trả về | RAW dict `{ "data": list[dict], "total_count": int }` |

**Field mỗi item**: `name`, `full_name`, `specialty`, `hospital`, `phone` (+ `hospital_name` resolve nếu rẻ — xem note). `hospital` param = lọc nhanh theo 1 BV (gộp vào filters). Cùng quy ước count==rows như `list_hospitals`.

### 4) `antmed_crm.api.antmed.customer.get_doctor`

| Thuộc tính | Giá trị |
|---|---|
| Signature | `def get_doctor(name: str) -> dict:` |
| Verb | GET |
| Auth | throw `PermissionError` nếu `not frappe.has_permission("AntMed Doctor", "read", doc=name)` |
| Trả về | RAW dict = field bác sỹ + **`hospital_name`** (resolve qua Link) |

**Shape (RAW):**
```json
{
  "name": "AM-DOC-2026-0001",
  "doctor_code": "BS-001",
  "full_name": "Nguyễn Văn A",
  "hospital": "BVTW-HUE",
  "hospital_name": "BV TW Huế",
  "specialty": "Ngoại tổng quát",
  "birthday": "1980-05-01",
  "phone": "09xx", "email": "...", "zalo": "...",
  "notes": "..."
}
```
- `hospital_name` resolve: `frappe.db.get_value("AntMed Hospital", doc.hospital, "hospital_name")` (chỉ khi `doc.hospital` set). Đây là "link ngược về BV" cho FE.

### Spec-contract (Frappe-standard — DONE-gate)
- 4 endpoint trả **RAW dict** (KHÔNG `_ok`/`_err`, KHÔNG `MSG.*`).
- **2 loại 403** phân biệt khi đặc tả:
  - **dispatcher-403**: guest/không session cookie gọi endpoint (không `allow_guest`). Áp cho cả 4 endpoint.
  - **in-handler permission-403**: `frappe.throw(_("..."), frappe.PermissionError)` khi `has_permission` fail — áp cho `get_hospital`/`get_doctor`. (Với `list_*`, Frappe permission engine tự lọc; không tồn tại = list rỗng, KHÔNG 403.)
- **Invariant count == rows**: `len(data) == total_count` khi không phân trang. Nếu count ≠ rows → rò rỉ/thiếu data → **fail gate**.
- Message lỗi (nếu cần thông điệp VN, vd permission): `frappe.throw(_("Bạn không có quyền xem hồ sơ này."), frappe.PermissionError)`. R2 chưa có BR-XX nghiệp vụ ném lỗi (đó là M02+).

---

## Business Rules

**R2 chưa thực thi BR nghiệp vụ "cứng" nào** (chưa quota/chứng từ/lot). Đăng ký không gian + nêu rõ cái gì hoãn:

| BR | Mô tả | Trạng thái R2 | Điểm wiring tương lai |
|---|---|---|---|
| BR-13 | Data-scope: NV chỉ thấy BV được giao | **`[ROADMAP]` (hoãn — ADR-M01-05)** | `permission_query_conditions` cho `AntMed Hospital`/`AntMed Doctor` (M14/R3), cần field "NV phụ trách BV" trước |
| BR-01 | Đối chiếu danh mục trúng thầu | `[ROADMAP]` | controller M02/M04 |
| BR-06 | Khoá quota chạm trần | `[ROADMAP]` | controller quota M02 |

> Ở R2, `contract_status` là **nhãn dữ liệu**, KHÔNG có validation nghiệp vụ chuyển trạng thái. Khi M02 land, trạng thái HĐ phải **derive** từ hợp đồng thật (không nhập tay) → khi đó viết ADR Supersede.

> **Invariant kỹ thuật bắt buộc R2 (không phải BR nghiệp vụ nhưng là gate)**: `count == rows` cho mọi list endpoint.

---

## Permissions (DocPerm — R2)

R2 gắn DocPerm tối thiểu cho 2 DocType mới (định nghĩa trong JSON DocType, field `permissions`). KHÔNG data-scope theo NV (xem ADR-M01-05).

> ⚠️ Tên Role trong bảng đã đổi sang **tiếng Việt** (DEC-A / W0-1) — xem `./m14_rbac_w0_role_naming.md`. Ma trận quyền GIỮ NGUYÊN, chỉ đổi chuỗi `role`.

| Role (VI) | (cũ EN) | `AntMed Hospital` | `AntMed Doctor` |
|---|---|---|---|
| `Quản lý` | `AntMed Manager` | read, write, create, delete | read, write, create, delete |
| `NV kinh doanh` | `AntMed Sales Rep` | read, write, create | read, write, create |
| `Thủ kho` | `AntMed Warehouse Keeper` | (không cần — kho không quản KH) | (không cần) |
| `System Manager` | — | full (mặc định Frappe khi tạo doctype trên desk) | full |

> *(Cần khảo sát)*: `NV kinh doanh` có được `delete` hồ sơ BV/bác sỹ không — mặc định **KHÔNG** cho NV kinh doanh delete (chỉ `Quản lý`), tránh mất master data. BE chốt theo bảng trên.
> Boundaries — Ask-first: nếu muốn siết `NV kinh doanh` chỉ `read` (không write/create) thì là quyết định nghiệp vụ → hỏi PM. Mặc định cho `NV kinh doanh` tạo/sửa để nhập liệu.

---

## Integration

- **R2 KHÔNG thêm `doc_events` / `permission_query_conditions` mới vào `crm/hooks.py`.** Chỉ thêm 2 DocType + 1 file API. `hooks.py` chỉ có thể cần append fixtures nếu export DocPerm qua fixture — **KHÔNG bắt buộc**: DocPerm đi trong JSON DocType (theo code), không cần fixture riêng.
- **No-regression bắt buộc** (giữ xanh sau R2):
  - `crm.tests.test_antmed_bootstrap` (6 test R1).
  - 4 test gốc CRM: `crm.permissions.test_org_hierarchy`, `crm.fcrm.doctype.crm_lead.test_crm_lead`, `crm.fcrm.doctype.crm_task.test_crm_task`, `crm.fcrm.doctype.crm_territory.test_crm_territory`.
- FE: `yarn build` emit chunk mới (Antmed*) **không vỡ** chunk cũ; route CRM gốc còn nguyên.
- **Dependency hướng tới**: M02 (hợp đồng) Link→`AntMed Hospital`; M04 (giao phòng mổ) Link→`AntMed Doctor`/`AntMed Hospital`; M08 pipeline phân vai KH dựa trên `contract_status`. Vì vậy 2 DocType này phải **ổn định tên + khoá** ngay R2 (lý do reserve `AM-DR`, chốt naming `AM-DOC-`).

---

## UI

> Vue 3 + frappe-ui SPA. Dùng `createListResource` (hoặc `createResource`) gọi **đúng** endpoint `antmed_crm.api.antmed.customer.*`. Route mới APPEND vào `frontend/src/router.js` (lazy). KHÔNG đụng route CRM gốc.

### Routes (THÊM mới — lazy import)

| path | name | component | mô tả |
|---|---|---|---|
| `/antmed/hospitals` | `AntmedHospitals` | `pages/AntmedHospitals.vue` | List bệnh viện |
| `/antmed/hospitals/:name` | `AntmedHospitalDetail` | `pages/AntmedHospitalDetail.vue` | Detail 360 BV + danh sách bác sỹ |
| `/antmed/doctors/:name` | `AntmedDoctorDetail` | `pages/AntmedDoctorDetail.vue` | Profile bác sỹ + link ngược BV |

> `:name` là route param (doc name). FE điều hướng qua `router.push({ name: 'AntmedHospitalDetail', params: { name } })`.

### Trang `/antmed/hospitals` (list)
- Bảng BV: cột **Tên** (`hospital_name`), **Hạng** (`rank`), **Trạng thái HĐ** (`contract_status`) (+ có thể MST).
- Nguồn dữ liệu: `createListResource` gọi **method-form** `antmed_crm.api.antmed.customer.list_hospitals` (endpoint trả `{data, total_count}` custom — KHÔNG dùng doctype-list-form chuẩn). FE đọc `resource.data.data` (list) + `resource.data.total_count`.

  > ⚠️ **Lưu ý FE (chốt để không đoán)**: vì endpoint trả **dict bọc** `{data, total_count}` (không phải list thuần như `frappe.client.get_list`), nên dùng `createResource({ url: 'antmed_crm.api.antmed.customer.list_hospitals', params: {...}, auto: true })` và đọc `r.data.data`. Nếu muốn dùng `createListResource`, phải set `url` trỏ method này và xử lý shape bọc — KHÔNG để frappe-ui tự coi response là array. **Khuyến nghị R2: dùng `createResource`** cho list (đơn giản, khớp shape `{data,total_count}`).
- Ô **search** `hospital_name`: gõ → gọi lại endpoint với `search`/`filters` (debounce). 
- Click 1 dòng → `router.push` sang `/antmed/hospitals/:name`.

### Trang `/antmed/hospitals/:name` (detail 360)
- Header BV: mã (`hospital_code`/`name`), tên, hạng, MST, trạng thái HĐ.
- Danh sách bác sỹ thuộc BV (từ `doctors` trong `get_hospital`): mỗi dòng tên + chuyên khoa.
- Click 1 bác sỹ → `/antmed/doctors/:name`.
- Nguồn: `createResource({ url: 'antmed_crm.api.antmed.customer.get_hospital', params: { name: route.params.name }, auto: true })`.

### Trang `/antmed/doctors/:name` (profile bác sỹ)
- Profile: chuyên khoa, sinh nhật, liên hệ (phone/email/zalo), ghi chú.
- **Link ngược về BV**: hiển thị `hospital_name` + click → `/antmed/hospitals/:hospital`.
- Nguồn: `createResource({ url: 'antmed_crm.api.antmed.customer.get_doctor', params: { name }, auto: true })`.

### Boundaries UI
- **Always** lazy import 3 page mới; **Always** dùng `__()` cho nhãn VN; trạng thái loading/error/empty cho mỗi resource.
- **Never** sửa layout/sidebar/route CRM gốc; **Never** gọi `crm.api.*` (sai namespace — đúng là `antmed_crm.api.antmed.*`); **Never** axios trực tiếp (dùng frappe-ui resource).

---

## Test harness (acceptance)

### BE test (TDD — phải xanh THẬT)
- File *(BE chốt)*: `crm/tests/test_antmed_customer.py` (chạy chung `before_tests`).
- Lệnh: `bench --site miyano run-tests --module crm.tests.test_antmed_customer` → **`Ran N tests ... OK`**.
- TC tối thiểu (BE viết failing-first):
  1. `AntMed Hospital` tồn tại sau migrate + có đủ field tối thiểu (`frappe.get_meta` chứa `hospital_code`, `hospital_name`, `rank`, `tax_code`, `address`, `contract_status`).
  2. `hospital_code` unique (tạo 2 BV cùng code → `frappe.exceptions.DuplicateEntryError`/ValidationError).
  3. `AntMed Doctor` tồn tại + field tối thiểu + naming_series sinh `AM-DOC-…` (KHÔNG `AM-DR`).
  4. `list_hospitals()` trả dict có key `data`(list) + `total_count`(int); item có đúng 5 field; **`len(data) == total_count`** khi không phân trang (count==rows).
  5. `list_hospitals(search=...)` lọc đúng theo `hospital_name`.
  6. `get_hospital(name)` trả field BV + `doctors` list (children `name/full_name/specialty/phone`) → đúng số bác sỹ thuộc BV.
  7. `get_doctor(name)` trả `hospital_name` resolve đúng qua Link.
  8. Permission: user thiếu read-perm gọi `get_hospital` → raise `frappe.PermissionError`.
- **No-regression**: chạy lại `test_antmed_bootstrap` (6) + 4 test gốc CRM → vẫn xanh.

### FE test (vitest — xanh)
- File *(FE chốt)*: `frontend/tests/unit/antmedCustomer.test.js` (theo idiom content-assert như R1).
- Assertion tối thiểu: 3 route mới tồn tại (path/name/lazy import); page list gọi đúng `antmed_crm.api.antmed.customer.list_hospitals`; detail gọi `get_hospital`/`get_doctor`; route CRM gốc (Leads/Deals/Contacts/Organizations) còn; KHÔNG `antmed_crm.api`/axios/tanstack.
- `yarn build` emit chunk Antmed* không vỡ.

---

## Build sequence (cho BE/FE — KHÔNG commit)

> BA chốt spec; dev thực thi. TDD: viết test failing trước.

1. **BE**: tạo DocType JSON `crm/antmed/doctype/antmed_hospital/antmed_hospital.json` (+ `.py` controller rỗng kế thừa `Document`, `__init__.py`) theo §DocTypes; gắn DocPerm §Permissions.
2. **BE**: tạo DocType `antmed_doctor` tương tự (naming_series `AM-DOC-.YYYY.-.####`).
3. **BE**: `bench --site miyano migrate` → verify `frappe.db.exists("DocType","AntMed Hospital")` & `"AntMed Doctor"`; verify naming sinh `AM-DOC-…`.
4. **BE**: viết `crm/api/antmed/customer.py` 4 hàm (type hint, RAW, count==rows, PermissionError).
5. **BE**: viết `crm/tests/test_antmed_customer.py` (failing-first) → cho xanh; chạy lại no-regression (bootstrap 6 + 4 gốc).
6. **FE**: tạo 3 page Antmed* + APPEND 3 route vào `router.js`; wire `createResource`→`antmed_crm.api.antmed.customer.*`; vitest + `yarn build` xanh.
7. **QA**: sau khi user reload BE (gunicorn --preload), Playwright smoke `/antmed/hospitals` → click → detail → doctor.

> ⚠️ **Reload**: thêm DocType + API mới → cần `bench --site miyano migrate` (DocType) và **user reload BE** (`bench restart`) để HTTP serve endpoint mới. `run-tests`/`execute` chạy live ngay (không cần reload). (Carry-over từ STATE R1.)

---

## ADR

### ADR-M01-04: DocType mới `AntMed Hospital` + `AntMed Doctor` (KHÔNG extend `CRM Organization`/`Contact`)
- **Status**: Accepted
- **Date**: 2026-06-17
- **Context**: Customer 360° cần field y tế đặc thù — hạng BV (Đặc biệt/I/II/III), MST pháp nhân, trạng thái hợp đồng, chuyên khoa, sinh nhật, ghi chú cá nhân, Link bác sỹ→BV. `CRM Organization` (autoname `field:organization_name`) và `Contact` của Frappe **thiếu toàn bộ** field này; ERPNext `Customer` **không cài** trong app `crm` (site `miyano` không có ERPNext) nên reference scaffold `am_hospital_profile` autoname:customer KHÔNG mirror 1:1 được. (Verified @ source: `crm/fcrm/doctype/crm_organization/crm_organization.json` không có rank/tax_code/contract_status; PM đã chốt @ STATE R2.)
- **Decision**: Tạo 2 DocType độc lập `AntMed Hospital` + `AntMed Doctor` trong module `AntMed`, KHÔNG extend/sửa Organization/Contact.
- **Alternatives**:
  - *Custom Field nhồi vào `CRM Organization`/`Contact`* — loại: trộn dữ liệu CRM bán hàng gốc với master data y tế, khó data-scope BR-13 về sau, dễ đụng test gốc, autoname không khớp khoá nghiệp vụ (mã BV).
  - *Tái dùng ERPNext `Customer`* — loại: ERPNext không có trong app `crm`/site `miyano`.
- **Consequences**:
  - (+) Schema sạch, khoá nghiệp vụ tự nhiên (`hospital_code`), độc lập để gắn quota/giao hàng/audit về sau.
  - (−) Không tự hưởng tính năng Contact/Organization gốc (timeline, social) — chấp nhận, timeline hợp nhất là backlog R3+.
  - (−) Phải tự định nghĩa DocPerm + (về sau) `permission_query_conditions` cho data-scope.

### ADR-M01-05: Hoãn data-scope BR-13 ở R2 (RBAC = DocPerm theo Role, chưa lọc theo NV)
- **Status**: Accepted
- **Date**: 2026-06-17
- **Context**: BR-13 yêu cầu "NV chỉ thấy BV được giao". Nhưng R2 chưa có field/quan hệ "NV phụ trách BV" (assignment) — thêm field này + `permission_query_conditions` làm phình scope R2 và cần khảo sát mô hình phân công.
- **Decision**: R2 dùng **DocPerm theo Role** (Sales Rep/Manager read toàn bộ trong quyền role), **KHÔNG** wiring `permission_query_conditions`. BR-13 = `[ROADMAP]` (M14/R3). Invariant `count == rows` vẫn enforce ngay R2 để khi thêm data-scope không vỡ contract.
- **Alternatives**: làm data-scope ngay R2 — loại: chưa có mô hình phân công NV↔BV (cần khảo sát), vượt scope lát-cắt-dọc.
- **Consequences**:
  - (+) R2 gọn, list endpoint chạy thật, test count==rows xanh.
  - (−) Tạm thời mọi Sales Rep thấy mọi BV — chấp nhận ở R2 (master data nội bộ); khi R3 thêm assignment + `permission_query_conditions`, viết ADR Supersede và bổ sung test data-scope (count==rows theo từng NV).

> ADR-M01-01..03 (in-place, prefix `AntMed `, fixtures) ở `m01_bootstrap.md` vẫn áp dụng — R2 kế thừa, không Supersede.

---

## Tham chiếu chéo
- **Boot gate cho pages `/antmed/*` (W0-2, DEC-B)**: `./m14_rbac_w0_antmed_boot.md` — user role AntMed thuần (`NV kinh doanh`) boot được vào các page Customer 360° này qua allow-check additive (mở Gate-1 HTML / Gate-2 session / Gate-3 router cho route `/antmed/*`).
- Foundation R1: `./m01_bootstrap.md` (namespace, 3 Role, ping, ADR-01..03)
- Convention naming FE↔BE: `./m01_naming_conventions.md` (+ `crm/antmed/README.md`)
- Mô tả nghiệp vụ 14 module: `../../antmed_crm/docs/AntMed_CRM_Modules.md` §1 (dòng 13–14 ground-truth field)
- UI 7 vai trò: `../../antmed_crm/docs/AntMed_CRM_UI_Design.md`
- Source thật đã verify: `crm/modules.txt` (module `AntMed`), `crm/api/antmed/` (package), `crm/fixtures/role.json` (3 Role), `crm/fcrm/doctype/crm_organization/crm_organization.json` (autoname `field:`, thiếu field y tế), `frontend/src/router.js` (route `/antmed` đã có), `crm/hooks.py:28` (`require_type_annotated_api_methods`).
