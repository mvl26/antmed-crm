# M02 — Hợp đồng & Gói thầu + Quota (Core Doc)

| Mục | Giá trị |
|---|---|
| Module folder | `crm/antmed/` (module Frappe **`AntMed`**, scrubbed = `antmed`) |
| DocType folder | `crm/antmed/doctype/antmed_contract/`, `crm/antmed/doctype/antmed_quota_item/` (+ `[PLANNED]` `antmed_contract_amendment/`, `antmed_quota_usage_log/`) |
| API package | `crm/api/antmed/contract.py` (đường gọi `crm.api.antmed.contract.<fn>`) |
| FE pages | `frontend/src/pages/AntmedContracts.vue` (vòng này, route `/antmed/contracts`) · `[NEXT]` `AntmedContractDetail.vue` (`/antmed/contracts/:name`) · `[PLANNED]` `AntmedContractHealth.vue` (`/antmed/contract-health`) |
| Vị trí code thật (repo) | Python package `crm` = `apps/antmed-crm/antmed-crm/` (nested) → DocType `…/antmed/doctype/antmed_contract`, API `…/api/antmed/contract.py`. FE = `apps/antmed-crm/frontend/`. Core Doc = `apps/antmed-crm/docs/antmed_dev/modules/`. (Đường import logic vẫn là `crm.api.antmed.contract.*` / `crm.antmed.doctype…`.) |
| Wave (PLAN) | **W1 — Master data & catalog** (chạy ‖ M01-full ‖ M03, sau M01 core) |
| Role chính | `Quản lý`, `NV kinh doanh` (DEC-A — xem `./m14_rbac_w0_role_naming.md`); `[PLANNED]` `Pháp lý`, `Kế toán` cho duyệt/đối soát quota |
| Phụ thuộc | **M01** (`AntMed Hospital`) |
| Cấp dữ liệu cho | **M04** (đối chiếu DR vs danh mục trúng thầu), **M08** (pipeline → thầu → won → HĐ), **M09** (đơn/AR theo đơn giá trúng) |
| Site dev | `miyano` |
| Trạng thái docs | DESIGN — Slice **M02-1 FROZEN** (spec-contract chốt, BE/FE code được). **Vòng 1 = màn DANH SÁCH only** (FE Detail defer → Slice M02-1b, ADR-M02-06); M02-2/3/4 đề xuất |
| Cập nhật | 2026-06-17 (BA vòng 1 — Self-Correction Detail scope) |

> **Trạng thái: [PLANNED — chưa code]. Slice M02-1 = spec-contract FROZEN (xem §1bis).**
>
> Module M02 CHƯA có DocType/endpoint/test nào trong `crm/antmed/`. Hiện `crm/antmed/doctype/` mới chỉ có `antmed_hospital`, `antmed_doctor` (M01) và `crm/api/antmed/` mới có `customer.py`, `health.py`, `rbac.py`. Toàn bộ schema/API/workflow dưới đây là **ĐỀ XUẤT thiết kế**, ground trên scaffold cũ (`docs/antmed_crm/antmed_crm/m02_contract/doctype/`, prefix `AM `, đã ADAPT sang `AntMed ` + native-lite) + `AntMed_CRM_Modules.md §2` + `UI_Design §1.2/§1.3`.
>
> 🟢 **DELTA 2026-06-17 (BA Bước 2 — vòng 1 factory):** đóng các `[cần khảo sát]` cho **chỉ Slice M02-1** (read-only) thành spec-contract FROZEN ở **§1bis** — đủ để BE+FE code không suy diễn. M02-2/3/4 (workflow / enforce BR / amendment) GIỮ nguyên đề xuất §3–§6 (chưa freeze). Quyết định freeze: ADR-M02-02 (item=Data tạm) + ADR-M02-04 (status Select read-only, KHÔNG Workflow ở M02-1) + ADR-M02-05 (DocPerm NV read-only).

> 🔗 **Tiền đề (đã land @ M01)**: `AntMed Hospital` tồn tại (`crm/antmed/doctype/antmed_hospital/`), khoá tự nhiên `hospital_code`; namespace `crm.api.antmed.*` + route `/antmed/*` đã mở; 3 Role VI (`NV kinh doanh`/`Thủ kho`/`Quản lý`) đã có trong DB. M02 **mở rộng** namespace này, KHÔNG dựng lại nền.

> ⚠️ **ADAPT từ scaffold cũ (bắt buộc đọc)**: scaffold `m02_contract` dùng `AM Tender Contract`/`AM Tender Contract Item`/`AM Quota Usage Log`/`AM Contract Amendment`, Link→`Customer` (ERPNext), Link→`Item` (ERPNext), `module = "M02 Contract"`, Role `AM System Admin`, naming `TC-…`. Tất cả PHẢI đổi: prefix `AM `→`AntMed `; `Customer`→`AntMed Hospital`; `Item`→`AntMed Item` (M03 native-lite); `module`→`AntMed`; Role→VI (DEC-A); KHÔNG dùng `AM-DR` naming (reserve cho M04). Xem §2 + §9 ADR-M02-01.

---

## 1. Overview

M02 là **module nền vận hành** của Wave 1: số hoá **hợp đồng / gói thầu trúng** giữa AntMed và bệnh viện, kèm **hạn ngạch (quota) theo SKU trúng thầu** và **đơn giá trúng**. Trong DAG 14 module, M02 đứng sau M01 (Customer) và là **cổng kiểm soát thương mại** cho toàn chuỗi giao hàng: M04 (giao phòng mổ) phải đối chiếu mỗi yêu cầu vật tư với danh mục trúng thầu + quota còn lại của HĐ; M09 (đơn/AR) lấy **đơn giá trúng** từ HĐ; M08 (pipeline/thầu) đổ kết quả "Trúng" thành HĐ.

Theo `AntMed_CRM_Modules.md §2` (mô tả nghiệp vụ ground-truth):
- **Danh mục hợp đồng/gói thầu**: số HĐ, bệnh viện, hiệu lực, danh mục vật tư trúng thầu, **đơn giá trúng**, **hạn ngạch (quota)**.
- **Theo dõi tỷ lệ sử dụng quota** theo tháng/quý — cảnh báo khi sắp chạm trần (rủi ro hết quota) hoặc dư nhiều (rủi ro mất quota lần sau).
- **Cảnh báo hết hạn hợp đồng / gia hạn / tái đấu thầu**.
- **Đính kèm** văn bản gốc, phụ lục, biên bản thương thảo.
- **Liên kết 2 chiều với M03 (Vật tư)** để chỉ cho phép xuất đúng SKU trong danh mục trúng thầu.

**Business value**: NV kinh doanh tra cứu nhanh đơn giá/quota khi bác sỹ hỏi tại phòng mổ; Quản lý/CEO nhìn "sức khoẻ hợp đồng" (quota 70/90/100%, HĐ sắp hết hạn) để ra quyết định tái thầu; hệ thống **chặn tự động** việc giao vật tư ngoài HĐ hoặc vượt trần quota (BR-02, BR-06) — giảm rủi ro pháp lý/tài chính.

### User stories (lát cắt M02)
- *NV kinh doanh* mở danh sách **Hợp đồng**, lọc theo bệnh viện/trạng thái, mở 1 HĐ để xem danh mục SKU trúng thầu + đơn giá + quota còn lại.
- *Quản lý* mở màn **"Sức khoẻ hợp đồng"**: thấy thanh tiến độ quota (xanh ≤80% / cam 80–100% / đỏ >100%), HĐ sắp hết hạn → quyết định gia hạn / tái thầu.
- *Hệ thống* (khi M04 tạo yêu cầu giao): tra cứu HĐ active của BV → nếu vật tư **ngoài danh mục** → chặn (BR-02, trừ `Quản lý`); nếu quota item **chạm trần** → khoá item đó (BR-06).

### 6 câu hỏi domain — feasibility check (BA Bước 2)

| # | Câu hỏi | Trả lời cho M02 |
|---|---|---|
| 1 | **CRM stage?** | Giai đoạn **hợp đồng/quota** — sau lead/thầu (M08), trước giao hàng (M04). M02 là **master + ràng buộc thương mại**, KHÔNG tự giao hàng/sinh chứng từ. |
| 2 | **Ràng buộc hợp đồng/quota?** | **CÓ — đây là module chủ của ràng buộc**. M02 định nghĩa danh mục trúng thầu + quota; enforce BR-01 (đối chiếu danh mục), BR-02 (chặn item ngoài HĐ), BR-06 (khoá khi chạm trần). Việc *gọi* các ràng buộc này từ M04 = doc_events ở M04 (xem §6). |
| 3 | **Actor là bệnh viện hay bác sỹ?** | **Bệnh viện (pháp nhân)** — HĐ ký với BV; Link→`AntMed Hospital`. Quota theo cặp (HĐ × SKU). |
| 4 | **Nghĩa vụ chứng từ / HĐĐT?** | **KHÔNG** ở M02. CO/CQ/HĐĐT là M06. M02 chỉ `Attach` văn bản HĐ/phụ lục gốc (file đính kèm, không phải chứng từ pháp lý sinh tự động). |
| 5 | **Truy vết lot / thu hồi?** | **KHÔNG** trực tiếp. M02 chỉ giữ quota theo **SKU** (Link→`AntMed Item`), không theo lot. Truy vết lot là M03. |
| 6 | **Hậu quả nếu data sai?** | **Cao**: đơn giá/quota sai → giao sai giá hoặc vượt trần thầu (rủi ro pháp lý, mất quota lần sau). → bắt buộc `is_submittable` (docstatus) cho HĐ + audit `track_changes`; `used_qty`/`remaining_pct` **read-only, derive** từ usage log (không nhập tay). |

---

## 1bis. Slice M02-1 — Spec-contract FROZEN (read-only) ✅

> **Boundaries của slice này** (dev KHÔNG suy diễn ngoài đây):
> - **Always**: tạo đúng 2 DocType (`AntMed Contract` submittable + `AntMed Quota Item` child) + đúng 2 endpoint đọc (`list_contracts`/`get_contract`) + DocPerm VI theo ma trận §1bis.4 + naming sinh `AM-HD-2026-00001`. **FE: chỉ màn DANH SÁCH** `/antmed/contracts` (`AntmedContracts.vue`, đã build) render read-only + 1 nav-entry "Hợp đồng" enabled. `get_contract` BE vẫn ship (test cover + dùng cho vòng Detail) nhưng KHÔNG có FE Detail page/route trong vòng này.
> - **Never**: KHÔNG fixture `workflow.json`; KHÔNG enforce BR-01/02/06; KHÔNG `AntMed Quota Usage Log`/`AntMed Contract Amendment`; KHÔNG endpoint `get_contract_health`/`list_quota_alerts`/`check_item_in_contract`; KHÔNG route `/antmed/contract-health`; **KHÔNG route `/antmed/contracts/:name` (`AntmedContractDetail`) — màn Detail thuộc vòng SAU** (xem ADR-M02-06); KHÔNG `doc_events` mới trong `crm/hooks.py`; KHÔNG Link→`AntMed Item` (M03 chưa land → dùng `Data`); KHÔNG `createListResource` (list trả dict bọc); KHÔNG axios / `antmed_crm.api.*`; KHÔNG Role `AM System Admin`.
> - **Ask-first**: muốn thêm Workflow/usage-log/enforce → đó là Slice M02-2/3 (mở vòng factory mới), KHÔNG nhét vào M02-1. Muốn build FE Detail (`AntmedContractDetail`) → mở vòng riêng (Slice M02-1b), KHÔNG nhét vào vòng danh sách này.

### 1bis.1 — DocType `AntMed Contract` (FROZEN cho M02-1)

| Thuộc tính | Giá trị CHỐT |
|---|---|
| `name` (label) | `AntMed Contract` |
| `module` | `AntMed` |
| `autoname` | `naming_series:` |
| `naming_rule` | `By "Naming Series" field` |
| `is_submittable` | **1** |
| `track_changes` | **1** |
| `title_field` | `contract_no` |
| `sort_field` / `sort_order` | `modified` / `DESC` |
| `search_fields` | `contract_no,hospital` |

**Naming series — CHỐT**: field `naming_series` (Select, `reqd=1`) options + default = **`AM-HD-.YYYY.-.#####`** (5 dấu `#`). → sinh `AM-HD-2026-00001`. **KHÔNG** `TC-` (scaffold cũ), **KHÔNG** `AM-DR-` (reserve M04), **KHÔNG** `AM-DOC-` (M01 doctor). *(Lưu ý: doctor M01 dùng 4 `#` `AM-DOC-.YYYY.-.####`; HĐ dùng 5 `#` để khớp acceptance `00001`.)*

**field_order + fields (CHỐT — tối thiểu acceptance, đủ render):**

| # | fieldname | label | fieldtype | options / thuộc tính | reqd | unique | in_list_view |
|---|---|---|---|---|---|---|---|
| 1 | `naming_series` | Series | Select | `AM-HD-.YYYY.-.#####` (default) | 1 | — | — |
| 2 | `contract_no` | Số hợp đồng | Data | — | **1** | **1** | 1 |
| 3 | `hospital` | Bệnh viện | Link | `AntMed Hospital` | **1** | — | 1 |
| 4 | `status` | Trạng thái | Select | `\nNháp\nHiệu lực\nSắp hết hạn\nHết hạn\nĐã huỷ` (default `Nháp`) | — | — | 1 |
| 5 | `column_break_main` | — | Column Break | — | — | — | — |
| 6 | `signed_date` | Ngày ký | Date | — | **1** | — | — |
| 7 | `valid_from` | Hiệu lực từ | Date | — | — | — | — |
| 8 | `valid_to` | Hiệu lực đến | Date | — | — | — | 1 |
| 9 | `total_value` | Giá trị HĐ | Currency | (VND, mặc định hệ thống) | — | — | 1 |
| 10 | `section_break_items` | Danh mục SKU & Quota | Section Break | — | — | — | — |
| 11 | `items` | Danh mục SKU & Quota | Table | `AntMed Quota Item` | — | — | — |

> **`status` (Select read-only display) — KHÔNG Workflow ở M02-1** (ADR-M02-04). `status` chỉ để hiển thị badge + cho `list_contracts` lọc; transition/role/`workflow_state` thật để Slice M02-2. `is_submittable=1` GIỮ để verify submit → docstatus 1 (acceptance), nhưng KHÔNG có UI transition trong slice này. Các field `has_amendment`/`attachment_main`/`notes`/`workflow_state` ở §2 = **scope M02-2+**, KHÔNG tạo ở M02-1.

### 1bis.2 — DocType `AntMed Quota Item` (FROZEN cho M02-1)

| Thuộc tính | Giá trị CHỐT |
|---|---|
| `name` (label) | `AntMed Quota Item` · `module` = `AntMed` |
| `istable` | **1** · `autoname` = hash (mặc định child) |

**fields (CHỐT):**

| # | fieldname | label | fieldtype | options / thuộc tính | reqd | in_list_view |
|---|---|---|---|---|---|---|
| 1 | `item` | Vật tư (SKU) | **Data** | — (ADR-M02-02: Data tạm, M03 chưa land) | **1** | 1 |
| 2 | `item_name` | Tên VT | Data | — | — | 1 |
| 3 | `uom` | ĐVT | Data | — | — | 1 |
| 4 | `unit_price` | Đơn giá trúng | Currency | — | — | 1 |
| 5 | `quota_qty` | Quota SL | Float | — | — | 1 |
| 6 | `used_qty` | Đã dùng | Float | `read_only=1`, `default=0` | — | — |
| 7 | `remaining_pct` | Còn lại % | Percent | `read_only=1` | — | 1 |
| 8 | `lock_at_100` | Khoá khi 100% | Check | `default=1` | — | — |

> **M02-1: `item` = `Data`** (KHÔNG Link `AntMed Item` — M03 chưa land, ADR-M02-02). `used_qty`/`remaining_pct` = read-only nhưng ở M02-1 **chưa có cơ chế derive** (chưa có usage log) → giá trị do người nhập/seed test set, dev KHÔNG viết logic recompute ở slice này. `unit_price`/`quota_qty` KHÔNG đặt `reqd` ở M02-1 (acceptance chỉ liệt kê chúng tồn tại; siết `reqd` để Slice M02-3 khi enforce BR).

### 1bis.3 — Endpoints (FROZEN — file `crm/api/antmed/contract.py`)

> Theo pattern `crm/api/antmed/customer.py` (đã verify live R2): `@frappe.whitelist(methods=["GET"])`, type-annotated, trả **RAW dict** (KHÔNG envelope), đếm count==rows qua `frappe.get_list(pluck="name", limit_page_length=0)` (**KHÔNG `frappe.db.count`** — phải tôn trọng permission cho BR-13 sau này), detail throw `frappe.PermissionError`.

**`list_contracts(filters=None, start=0, page_length=20, search=None) -> dict`** (GET)
- `filters`: dict|JSON-string → chuẩn hoá qua helper kiểu `_coerce_filters` (mượn từ customer.py). Hỗ trợ key `hospital` và `status` (acceptance gọi "workflow_state/status" — ở M02-1 field là `status`; nếu FE/caller truyền key `workflow_state`, map về `status`).
- `search`: LIKE `%search%` trên `contract_no`.
- `page_length=0` → không phân trang → **`len(data) == total_count`** (BR-13 count==rows; đếm bằng `get_list(pluck="name", limit_page_length=0)`).
- Mỗi item trong `data` gồm **đúng** field: `name`, `contract_no`, `hospital`, `hospital_name`, `valid_to`, `total_value`, `status`.
  - `hospital_name` resolve qua Link: dùng `fields=[..., "hospital.hospital_name as hospital_name"]` (fetch qua child-link trong `get_list`) HOẶC enrich vòng lặp `frappe.db.get_value` (như `get_doctor`). Chốt: dùng dotted-fetch trong `get_list` cho list (1 query), enrich thủ công cho detail.
- Trả: `{ "data": [ {name, contract_no, hospital, hospital_name, valid_to, total_value, status}, ... ], "total_count": int }`.

**`get_contract(name: str) -> dict`** (GET)
- Guard: `if not frappe.has_permission("AntMed Contract", "read", doc=name): frappe.throw(_("Bạn không có quyền xem hợp đồng này."), frappe.PermissionError)`.
- Trả RAW dict: field HĐ (`name, contract_no, hospital, hospital_name, signed_date, valid_from, valid_to, total_value, status, docstatus`) + `hospital_name` resolve qua Link (`frappe.db.get_value` null-guard FK orphan) + `items`: list mỗi dòng `{item, item_name, uom, unit_price, quota_qty, used_qty, remaining_pct, lock_at_100}`.

> Shape `get_contract` (RAW, M02-1):
> ```json
> { "name": "AM-HD-2026-00001", "contract_no": "01/2026/HĐ-AntMed",
>   "hospital": "BVTW-HUE", "hospital_name": "BV TW Huế",
>   "signed_date": "2026-01-05", "valid_from": "2026-01-05", "valid_to": "2026-12-31",
>   "total_value": 1500000000, "status": "Hiệu lực", "docstatus": 1,
>   "items": [ {"item": "VTYT-001", "item_name": "Stent ...", "uom": "Cái",
>               "unit_price": 12000000, "quota_qty": 100, "used_qty": 0,
>               "remaining_pct": 100.0, "lock_at_100": 1} ] }
> ```

> **403 phân biệt** (DONE-gate): guest/no-session → dispatcher-403 (Frappe tự trả trước khi vào handler); user có session nhưng thiếu DocPerm read / ngoài data-scope → in-handler `frappe.PermissionError` (handler tự throw). Test cả 2.

### 1bis.4 — DocPerm VI (FROZEN — đặt trong DocType JSON, KHÔNG fixture role-permission riêng)

| Role | read | write | create | delete | submit | cancel | amend | print/report/export/email/share |
|---|---|---|---|---|---|---|---|---|
| `System Manager` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `Quản lý` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `NV kinh doanh` | ✓ | — | — | — | — | — | — | ✓ (print/report/export — KHÔNG write/create/delete) |
| `Thủ kho` | ✓ | — | — | — | — | — | — | ✓ (read-only) |

> **Khác M01**: ở M01 `NV kinh doanh` có create/write (tạo BV/bác sỹ). Ở M02 `NV kinh doanh` = **read-only** (ADR-M02-05) — tránh NV tự sửa quota/đơn giá trúng thầu (hậu quả data sai = cao, câu hỏi #6). `Thủ kho` cần đọc quota khi xuất kho → thêm read. **KHÔNG** dùng Role `AM System Admin` (scaffold cũ). 3 Role VI đã có trong DB (`crm/fixtures/role.json`).

### 1bis.5 — FE (FROZEN — read-only, **chỉ màn DANH SÁCH** trong vòng này)

> 🟢 **Self-Correction 2026-06-17 (ADR-M02-06):** vòng này chỉ làm màn **DANH SÁCH** (`/antmed/contracts`). Màn **Detail** (`/antmed/contracts/:name`, `AntmedContractDetail`) **KHÔNG** thuộc vòng → KHÔNG đăng ký route, KHÔNG tạo page. Bản trước liệt kê Detail là "FROZEN cho M02-1" → **sai scope** so với acceptance vòng 1 ("route AntmedContractDetail CHƯA thuộc vòng này"). Đã sửa.

| Route (APPEND lazy vào `frontend/src/router.js`) | name | page | Vòng |
|---|---|---|---|
| `/antmed/contracts` | `AntmedContracts` | `frontend/src/pages/AntmedContracts.vue` (đã build) | **Vòng này** |
| `/antmed/contracts/:name` | `AntmedContractDetail` | `frontend/src/pages/AntmedContractDetail.vue` | **Vòng SAU** (KHÔNG đăng ký bây giờ) |

- **Route đăng ký (chỉ 1)**: APPEND vào `routes` của `frontend/src/router.js` block `{ path: '/antmed/contracts', name: 'AntmedContracts', component: () => import('@/pages/AntmedContracts.vue') }` — đặt cạnh các route `/antmed/*` khác (cho phép CRM HOẶC AntMed user qua `shouldRedirectNotPermitted` đã có, **KHÔNG** thêm allow-check mới). KHÔNG route `:name`/Detail.
- **List** (`AntmedContracts.vue`, đã build — KHÔNG viết lại): dùng `listContracts` từ `@/data/antmed` (`createResource` → `crm.api.antmed.contract.list_contracts`), đọc **`r.data.data`** + `r.data.total_count` (list trả dict bọc — pattern verified R2, KHÔNG `createListResource`). Cột: Số HĐ / Bệnh viện (hospital_name) / Hiệu lực đến / Giá trị / badge `status` (theme `CONTRACT_WORKFLOW_THEME`). Lọc theo BV + status, search số HĐ (debounce 300ms). Tri-branch loading/error/empty + dòng "Tổng cộng: {total_count}".
- **Row-click KHÔNG dead-end (BẮT BUỘC vòng này)**: vì route `AntmedContractDetail` chưa tồn tại, `openContract` hiện push tới route đó (AntmedContracts.vue dòng 264-266) → sẽ rơi vào `Invalid Page`/no-match = **dead-end**. Vòng này phải **vô hiệu điều hướng chi tiết**: biến `openContract` thành **no-op** (giữ chữ ký hàm cho vòng sau) **và** gỡ affordance click ở `<tr>` (bỏ `cursor-pointer`, `role="link"`, `tabindex="0"`, `@click`/`@keydown` openContract, `:aria-label` "Xem chi tiết") để dòng không gợi ý có thể bấm. Khi vòng Detail mở (Slice M02-1b) sẽ khôi phục `router.push({name:'AntmedContractDetail', params:{name}})` + các affordance này. Trang LIST vẫn dùng được đầy đủ (lọc/search/đọc).
- **Nhãn 100% tiếng Việt qua `__()`**: badge status (Nháp/Hiệu lực/Sắp hết hạn/Hết hạn/Đã huỷ) + header cột. KHÔNG hardcode chuỗi EN.
- **KHÔNG** route `/antmed/contract-health` (M02-2). Sidebar `frontend/src/data/antmedNav.js`: mục `{ key: 'contracts', label: 'Hợp đồng', to: '/antmed/contracts' }` chuyển `enabled: false` → **`enabled: true`** (đây là nav-entry tới Hợp đồng — không thêm item mới).
- **KHÔNG** axios, KHÔNG `antmed_crm.api.*`, KHÔNG TanStack, KHÔNG `.ts`.

---

## 2. DocTypes (native-lite, [PLANNED])

> Field set = **đề xuất**, ground @ scaffold `m02_contract` (đã ADAPT `AM `→`AntMed `, ERPNext-reuse→native-lite) + `AntMed_CRM_Modules.md §2`. Đơn vị tiền VND. **KHÔNG** dùng naming series `AM-DR-…` (reserve M04). `[cần khảo sát]` các điểm đánh dấu.

| DocType | Loại | Field chính (ĐỀ XUẤT) | Naming series |
|---|---|---|---|
| `AntMed Contract` | txn (submittable) | `contract_no`, `hospital`(Link→AntMed Hospital), `signed_date`, `valid_from`, `valid_to`, `total_value`, `status`/`workflow_state`, `has_amendment`, `items`(Table→AntMed Quota Item), `attachment_main`, `notes` | `AM-HD-.YYYY.-.#####` |
| `AntMed Quota Item` | child (istable) | `item`(Link→AntMed Item), `item_name`(ro), `uom`, `unit_price`(Currency), `quota_qty`(Float), `used_qty`(Float, ro), `remaining_pct`(Percent, ro), `lock_at_100`(Check, default 1) | — (hash) |
| `AntMed Contract Amendment` `[PLANNED]` | txn (submittable) | `parent_contract`(Link→AntMed Contract), `signed_date`, `new_quota_table`(Table→AntMed Quota Item), `file_attach`, `reason` | `AM-PL-.YYYY.-.####` |
| `AntMed Quota Usage Log` `[PLANNED]` | log/txn | `contract`(Link), `item`(Link→AntMed Item), `do_ref`(Data — tham chiếu Delivery M04), `qty`(Float), `snapshot_pct`(Percent), `ts`(Datetime, default now) | — (hash) |

### DocType `AntMed Contract` (master HĐ — submittable)

| Thuộc tính DocType | Giá trị |
|---|---|
| `name` (label) | `AntMed Contract` |
| Module | `AntMed` |
| `autoname` | **`naming_series:`** với series **`AM-HD-.YYYY.-.#####`** (HĐ = Hợp Đồng). KHÔNG `TC-` (scaffold cũ), KHÔNG `AM-DR`. |
| `naming_rule` | `By "Naming Series" field` |
| `title_field` | `contract_no` |
| `is_submittable` | **1** (docstatus 0/1/2 — HĐ phải duyệt mới có hiệu lực ràng buộc; xem §3) |
| `track_changes` | 1 (audit thương mại — bắt buộc, hậu quả data sai cao) |

**Fields (đề xuất — ground @ scaffold `am_tender_contract`, adapt):**

| fieldname | label | fieldtype | options / ràng buộc | reqd | unique | Ghi chú |
|---|---|---|---|---|---|---|
| `naming_series` | Series | Select | `AM-HD-.YYYY.-.#####` | — | — | field hệ thống naming |
| `contract_no` | Số hợp đồng | Data | — | **1** | **1** | khoá nghiệp vụ; `title_field`; unique chặn trùng số HĐ |
| `hospital` | Bệnh viện | Link | **`AntMed Hospital`** | **1** | — | ADAPT: scaffold cũ Link→`Customer` (ERPNext) → đổi sang M01 native |
| `signed_date` | Ngày ký | Date | — | **1** | — | — |
| `valid_from` | Hiệu lực từ | Date | — | — | — | — |
| `valid_to` | Hiệu lực đến | Date | — | — | — | dùng cho cảnh báo hết hạn (scheduler) |
| `total_value` | Giá trị HĐ | Currency | VND | — | — | — |
| `workflow_state` | Trạng thái | Select | xem §3 (states VI) | — | — | **ĐỀ XUẤT** field workflow (thay `status` EN của scaffold). `[cần khảo sát]`: giữ tên `status` hay `workflow_state` — chốt ở §3 |
| `has_amendment` | Có phụ lục | Check | — | — | — | set khi có Amendment submit |
| `items` | Danh mục SKU & Quota | Table | **`AntMed Quota Item`** | — | — | child quota |
| `attachment_main` | Văn bản gốc | Attach | — | — | — | file HĐ gốc (KHÔNG phải chứng từ M06) |
| `notes` | Ghi chú | Long Text | — | — | — | biên bản thương thảo |

### DocType `AntMed Quota Item` (child — istable)

| Thuộc tính | Giá trị |
|---|---|
| `name` (label) | `AntMed Quota Item` |
| Module | `AntMed` · `istable = 1` · `autoname = hash` |

**Fields (đề xuất — ground @ scaffold `am_tender_contract_item`, adapt):**

| fieldname | label | fieldtype | options / ràng buộc | reqd | Ghi chú |
|---|---|---|---|---|---|
| `item` | Vật tư (SKU) | Link | **`AntMed Item`** | **1** | ADAPT: scaffold Link→`Item` (ERPNext) → `AntMed Item` (M03 native-lite). `[cần khảo sát]`: M03 chưa code → khi M02 chạy trước M03, tạm để `Data`/`Link` mềm rồi siết khi M03 land (xem ADR-M02-02) |
| `item_name` | Tên VT | Data | read_only | — | fetch từ `AntMed Item` |
| `uom` | ĐVT | Data | — | — | — |
| `unit_price` | Đơn giá trúng | Currency | VND | **1** | giá trúng thầu — M09 lấy từ đây |
| `quota_qty` | Quota SL | Float | — | **1** | trần số lượng trúng thầu |
| `used_qty` | Đã dùng | Float | read_only, default 0 | — | **derive** từ Quota Usage Log (KHÔNG nhập tay) |
| `remaining_pct` | Còn lại % | Percent | read_only | — | derive = (1 − used/quota)·100 |
| `lock_at_100` | Khoá khi 100% | Check | default 1 | — | cờ bật BR-06 cho item này |

### DocType `AntMed Contract Amendment` `[PLANNED]` (phụ lục — submittable)
Ground @ scaffold `am_contract_amendment`. Adapt: Link→`AntMed Contract`; naming `AM-PL-.YYYY.-.####` (PL = Phụ Lục, thay `TC-AM-`); `new_quota_table`→`AntMed Quota Item`. Khi submit → cộng/ghi đè quota vào HĐ gốc + set `has_amendment=1` (logic ở module hooks, §6).

### DocType `AntMed Quota Usage Log` `[PLANNED]` (log tiêu hao quota)
Ground @ scaffold `am_quota_usage_log`. Adapt: `item`→Link `AntMed Item`; `do_ref` = tham chiếu `AntMed Delivery` (M04). Mỗi lần M04 giao 1 vật tư trong HĐ → ghi 1 dòng log + cập nhật `used_qty`/`remaining_pct` của Quota Item tương ứng (single source of truth cho quota đã dùng → bảo đảm `used_qty` không lệch). Đây là **đường đối chiếu DR** giữa M02↔M04.

> **Permissions (DocPerm, đề xuất — VI roles):** `Quản lý` = read/write/create/delete/submit/cancel/amend; `NV kinh doanh` = read (+ create/write `[cần khảo sát]` — mặc định **chỉ read** HĐ, tránh NV tự sửa quota/đơn giá); `Thủ kho` = read (cần biết quota khi xuất kho); `System Manager` = full. KHÔNG dùng Role `AM System Admin` (scaffold cũ). `[PLANNED]` thêm `Pháp lý` (quản HĐ/phụ lục), `Kế toán` (đọc đơn giá).

---

## 3. Workflow

M02 **CÓ state machine** cho `AntMed Contract` (vòng đời hợp đồng) — dùng **Frappe-native Workflow** (D2): fixture `crm/fixtures/workflow.json` + `docstatus`. Scaffold cũ dùng Select `status` (`Draft\nActive\nExpiring\nExpired\nRenewed\nCancelled`) **không có transition/role** → nâng cấp thành Workflow thật, states tiếng Việt.

> `[cần khảo sát]` Tên state field: đề xuất **`workflow_state`** (chuẩn Frappe Workflow). Nếu muốn giữ `status` của scaffold, set `Workflow.workflow_state_field = "status"`. Chốt 1 phương án trước khi code (ADR-M02-03).

**States (đề xuất, VI) + docstatus:**

| State (workflow_state) | docstatus | Ý nghĩa | Ràng buộc ràng buộc nghiệp vụ |
|---|---|---|---|
| `Nháp` | 0 (Draft) | Đang nhập danh mục/đơn giá/quota | Chưa enforce BR-01/02/06 (HĐ chưa hiệu lực) |
| `Chờ duyệt` | 0 | Đã nhập xong, chờ Quản lý duyệt | — |
| `Hiệu lực` | 1 (Submitted) | HĐ active — **enforce BR-01/02/06** | M04 chỉ đối chiếu HĐ ở state này |
| `Sắp hết hạn` | 1 | `valid_to` còn ≤ 30 ngày (set bởi scheduler) | vẫn enforce; cảnh báo gia hạn |
| `Hết hạn` | 1 | Quá `valid_to` | **KHÔNG** còn đối chiếu được (M04 chặn) |
| `Đã gia hạn` | 1 | Có HĐ/phụ lục thay thế | — |
| `Đã huỷ` | 2 (Cancelled) | Huỷ HĐ | — |

**Transitions (đề xuất):**

| Từ → Đến | Action | Role cho phép | Điều kiện |
|---|---|---|---|
| `Nháp` → `Chờ duyệt` | Gửi duyệt | `NV kinh doanh`, `Quản lý` | có ≥1 dòng `items` |
| `Chờ duyệt` → `Hiệu lực` | Duyệt (submit) | `Quản lý` | docstatus 0→1; chạy validate danh mục/đơn giá |
| `Chờ duyệt` → `Nháp` | Trả lại | `Quản lý` | — |
| `Hiệu lực` → `Sắp hết hạn` | (scheduler) | System | `valid_to − today ≤ 30` |
| `Sắp hết hạn` → `Hết hạn` | (scheduler) | System | `today > valid_to` |
| `Hiệu lực`/`Sắp hết hạn` → `Đã gia hạn` | Gia hạn | `Quản lý` | có Amendment/HĐ mới |
| bất kỳ (docstatus 1) → `Đã huỷ` | Huỷ | `Quản lý` | docstatus 1→2 (cancel) |

> Chuyển `Sắp hết hạn`/`Hết hạn` do **scheduler job** (`AntMed Contract.daily` qua `hooks.scheduler_events`) so `valid_to` với `today`, KHÔNG do người dùng bấm — xem §6.

---

## 4. Business Rules

> Enforce trong **module hooks** (`crm/antmed/doctype/antmed_contract/antmed_contract.py` controller hoặc `crm/antmed/contract_hooks.py` wired qua `doc_events`). Lỗi nghiệp vụ = `frappe.throw(_("BR-XX: …tiếng Việt"))`. Các BR *được gọi từ M04* (giao hàng) sẽ wiring tại doc_events của `AntMed Delivery`, nhưng **logic thuộc M02** (lazy-import hàm kiểm tra của M02) — xem §6.

| BR | Mô tả | Nơi enforce (đề xuất) | Trạng thái |
|---|---|---|---|
| **BR-01** | **Đối chiếu danh mục trúng thầu**: vật tư giao phải thuộc `items` của 1 HĐ `Hiệu lực` của đúng BV đó | hàm `assert_item_in_contract(hospital, item)` trong M02 controller; gọi từ `AntMed Delivery.validate` (M04) | `[PLANNED]` |
| **BR-02** | **Item ngoài HĐ → chặn** (trừ `Quản lý`): nếu vật tư không có trong danh mục trúng thầu → `frappe.throw`; user có Role `Quản lý` được ghi đè (cảnh báo, cho qua) | cùng hàm BR-01: `if "Quản lý" not in frappe.get_roles(): frappe.throw(...)` | `[PLANNED]` |
| **BR-06** | **Quota chạm trần → lock**: khi `used_qty ≥ quota_qty` và `lock_at_100=1` → chặn giao thêm item đó | `assert_quota_available(contract, item, qty)`; gọi trước khi cộng usage log | `[PLANNED]` |
| **Quota alert 70/90/100%** | Cảnh báo khi `remaining_pct` vượt ngưỡng sử dụng 70/90/100% (không chặn ở 70/90, chỉ notify; 100% → BR-06 lock) | scheduler `AntMed Contract.daily` + on usage-log insert → tạo notification / cờ màu cho UI | `[PLANNED]` |
| **Cảnh báo hết hạn HĐ** | `valid_to` còn ≤ 30 ngày → state `Sắp hết hạn` + alert gia hạn/tái thầu | scheduler `AntMed Contract.daily` | `[PLANNED]` |
| **Quota derive (invariant)** | `used_qty`/`remaining_pct` **chỉ** được tính từ `AntMed Quota Usage Log` (read-only field) — không nhập tay; tổng usage == `used_qty` | `recompute_quota_usage(contract, item)` gọi sau mỗi insert/cancel usage log | `[PLANNED]` |
| BR-13 | Data-scope: NV chỉ thấy HĐ của BV được giao | `permission_query_conditions` cho `AntMed Contract` (M14/W4) — kế thừa ADR-M01-05 (hoãn); invariant `count == rows` vẫn enforce ngay M02 | `[ROADMAP]` |

> **Tách logic vs trigger**: BR-01/02/06 là **logic M02** (biết về quota/danh mục), nhưng **điểm kích hoạt** nằm ở M04 (lúc tạo yêu cầu giao). M02 expose hàm kiểm tra thuần (nhận PK `hospital`/`item`/`qty`, trả kết quả/throw); M04 lazy-import + gọi. Tránh M02 import ngược M04 (DAG 1 chiều).

---

## 5. API

> File: `crm/api/antmed/contract.py`. Mọi hàm `@frappe.whitelist(methods=["GET"|"POST"])`, **type-annotated** (`crm/hooks.py:28 require_type_annotated_api_methods = True`), trả **RAW dict/list** (KHÔNG `_ok/_err`/envelope). Lỗi = `frappe.throw(...)`. List endpoint giữ invariant **count == rows** (đếm qua `get_list(pluck=…, limit_page_length=0)`).

| Endpoint (`crm.api.antmed.contract.<fn>`) | Verb | Mô tả | Trả về |
|---|---|---|---|
| `list_contracts` | GET | List HĐ (filter: hospital/workflow_state/search số HĐ); phân trang | `{ "data": [...], "total_count": int }` — **count == rows** khi không phân trang |
| `get_contract` | GET | Chi tiết 1 HĐ + danh mục `items` (quota, đơn giá, used/remaining) | RAW dict (field HĐ + `items` list + `hospital_name` resolve) |
| `get_contract_health` | GET | Dữ liệu màn "Sức khoẻ hợp đồng": mỗi HĐ kèm `quota_used_pct` tổng, cờ màu (xanh/cam/đỏ), `days_to_expiry` | `{ "data": [...] , "total_count": int }` |
| `check_item_in_contract` | GET | Tra cứu BR-01: vật tư X có trong HĐ active của BV Y không + quota còn lại (cho M04/mobile tra trước khi giao) | `{ "in_contract": bool, "contract": str\|None, "unit_price": float\|None, "remaining_qty": float\|None }` |
| `list_quota_alerts` | GET | Quota chạm 70/90/100% + HĐ sắp hết hạn (cho dashboard/cảnh báo điều hành) | `{ "data": [...], "total_count": int }` |

**Đề xuất hàm hỗ trợ nội bộ (không whitelist — gọi từ M04 qua import):**
- `assert_item_in_contract(hospital: str, item: str) -> str` → trả `contract name` hoặc `frappe.throw` (BR-01/02).
- `assert_quota_available(contract: str, item: str, qty: float) -> None` → throw nếu chạm trần (BR-06).
- `recompute_quota_usage(contract: str, item: str) -> None` → derive `used_qty`/`remaining_pct` từ usage log.

> `get_contract` shape (RAW, rút gọn):
> ```json
> { "name": "AM-HD-2026-00001", "contract_no": "01/2026/HĐ-AntMed",
>   "hospital": "BVTW-HUE", "hospital_name": "BV TW Huế",
>   "workflow_state": "Hiệu lực", "valid_to": "2026-12-31", "total_value": 1500000000,
>   "items": [ {"item": "VTYT-001", "item_name": "Stent ...", "unit_price": 12000000,
>               "quota_qty": 100, "used_qty": 72, "remaining_pct": 28.0, "lock_at_100": 1} ] }
> ```

---

## 6. Integration

**doc_events vào/ra theo Dependency DAG** (DAG: `M01 → M02 → M04 → …`; `M08 → M02`):

| Hướng | Sự kiện | Hành vi | Wiring |
|---|---|---|---|
| **M02 ra → M04** | `AntMed Delivery.validate` / `before_submit` (M04) | M4 lazy-import `crm.antmed.contract_hooks` → gọi `assert_item_in_contract` (BR-01/02) + `assert_quota_available` (BR-06) cho từng dòng giao | `doc_events["AntMed Delivery"]` (định nghĩa ở M04 hooks; logic ở M02) |
| **M04 → M02** | `AntMed Delivery.on_submit` (M04) | M04 gọi `crm.antmed.contract_hooks.consume_quota(contract, item, qty, do_ref)` → tạo `AntMed Quota Usage Log` + `recompute_quota_usage` | lazy-import, truyền **PK** (string names), KHÔNG truyền doc object |
| **M02 nội bộ** | `AntMed Contract.on_submit` | validate danh mục (item unique trong HĐ, đơn giá>0, quota>0); set state `Hiệu lực` | `doc_events["AntMed Contract"]["on_submit"]` |
| **M02 nội bộ** | `AntMed Contract Amendment.on_submit` `[PLANNED]` | cộng/ghi đè quota vào HĐ gốc + `has_amendment=1` | doc_events |
| **M08 → M02** | (manual / `[PLANNED]`) khi `CRM Deal`/`AntMed Tender` = "Trúng" | tạo nháp `AntMed Contract` từ kết quả thầu (đơn giá/SKU thắng) | `[PLANNED]` — M08 W4 |
| **M02 → M09** | (đọc) | M09 đọc `unit_price` từ Quota Item khi lập đơn | đọc trực tiếp qua `get_value`/API, không doc_event |
| **Scheduler** | `hooks.scheduler_events["daily"]` | `crm.antmed.contract_hooks.daily_contract_check` → cập nhật state `Sắp hết hạn`/`Hết hạn`, sinh quota/expiry alert | `[PLANNED]` |

**Nguyên tắc tích hợp (kế thừa SPEC §5/§7):**
- **Lazy-import + truyền PK**: hàm cross-module nhận string `name` (vd `hospital`, `contract`, `item`), không nhận doc object → tránh vòng import, giữ DAG 1 chiều.
- **Gate compliance**: BR-01/02/06 là **gate trước khi M04 cho submit DO** — Delivery không submit được nếu vi phạm (trừ override `Quản lý` cho BR-02).
- **Additive `hooks.py`**: M02 chỉ THÊM key vào `crm/hooks.py` (`doc_events` cho `AntMed Contract`/`AntMed Contract Amendment`, `scheduler_events.daily`, fixtures `workflow.json`). KHÔNG sửa key gốc CRM.

---

## 7. UI

> Vue 3 + frappe-ui SPA. `createResource` (list trả dict `{data,total_count}` → đọc `r.data.data`). Route `/antmed/*` APPEND vào `frontend/src/router.js` (lazy). Nhãn 100% tiếng Việt qua `__()`. KHÔNG đụng route CRM gốc, KHÔNG `antmed_crm.api.*`, KHÔNG axios.

Màn hình từ `UI_Design §1.2` (Dashboard CEO widget "% Quota đã dùng" ngưỡng 70/90/100) + `§1.3` ("Sức khoẻ hợp đồng"):

> §7 = bản đồ UI **toàn module M02** (forward-looking). **Phạm vi từng vòng** chốt ở **§1bis.5** + §8: vòng 1 chỉ ship route LIST; Detail/Health là vòng sau (ADR-M02-06).

| Route (THÊM, lazy) | name | page | Mô tả | Role dùng | Vòng |
|---|---|---|---|---|---|
| `/antmed/contracts` | `AntmedContracts` | `pages/AntmedContracts.vue` | List HĐ: cột Số HĐ, BV, hiệu lực đến, giá trị, trạng thái; lọc BV/trạng thái; search | `Quản lý`, `NV kinh doanh` | **Vòng 1** |
| `/antmed/contracts/:name` | `AntmedContractDetail` | `pages/AntmedContractDetail.vue` | Chi tiết HĐ: header + danh mục SKU/đơn giá/quota (progress bar/item), timeline ký→hiệu lực, đính kèm | `Quản lý`, `NV kinh doanh` | `[NEXT]` M02-1b |
| `/antmed/contract-health` | `AntmedContractHealth` | `pages/AntmedContractHealth.vue` | "Sức khoẻ hợp đồng": list HĐ + progress bar 2 màu (xanh ≤80% / cam 80–100% / đỏ >100% hoặc <30% còn ≤30 ngày) | `Quản lý`, CEO | `[PLANNED]` M02-2 |

- **List** (`/antmed/contracts`, **vòng 1**): `createResource` → `crm.api.antmed.contract.list_contracts`; **row-click vô hiệu** ở vòng 1 (Detail chưa có — ADR-M02-06); khôi phục `router.push` detail ở Slice M02-1b.
- **Detail** (`/antmed/contracts/:name`): `createResource` → `get_contract`; mỗi dòng quota hiển thị thanh tiến độ + nhãn % còn lại; badge trạng thái VI.
- **Sức khoẻ HĐ** (`/antmed/contract-health`): `createResource` → `get_contract_health`; progress bar theo ngưỡng màu; cột "còn N ngày" đỏ khi ≤30.
- Widget Dashboard "% Quota đã dùng" (vòng tròn 70/90/100) = M11 tiêu thụ `list_quota_alerts`/`get_contract_health` — `[cross-ref M11]`.

---

## 8. Build slices (cho factory — KHÔNG commit)

> Mỗi slice = 1 vòng factory (BA spec → BE+FE → QA → user). TDD failing-first. M02 chạy ở W1 (sau M01 core, ‖ M03). Vì M03 (`AntMed Item`) có thể chưa land khi M02 bắt đầu → xem ADR-M02-02 cho field `item`.

1. **Slice M02-1 — Contract master + quota (đọc), màn DANH SÁCH ✅ spec FROZEN §1bis**: DocType `AntMed Contract` (submittable, `track_changes=1`, naming `AM-HD-.YYYY.-.#####`, Select `status` read-only — KHÔNG Workflow) + `AntMed Quota Item` child (`item`=Data tạm) + DocPerm VI (NV read-only); API `list_contracts`+`get_contract` (RAW dict, count==rows — cả 2 ship & test); **FE chỉ 1 route LIST** (`/antmed/contracts`, `AntmedContracts.vue` đã build) read-only + nav enabled + **row-click vô hiệu** (ADR-M02-06); test BE (tồn tại + naming AM-HD + unique contract_no + count==rows + filter/search + submit→docstatus 1 + permission 403), FE vitest + build. *(KHÔNG FE Detail/route `:name`; KHÔNG enforce BR; KHÔNG workflow.json; KHÔNG usage-log; KHÔNG contract-health.)*
   - **Slice M02-1b — FE Detail Hợp đồng** `[NEXT]`: route `AntmedContractDetail` (`/antmed/contracts/:name`) + `AntmedContractDetail.vue` (`createResource` → `get_contract` đã có, read-only: header + bảng quota) + khôi phục `router.push` & affordance click ở list. *(BE đã sẵn — chỉ FE.)*
2. **Slice M02-2 — Workflow hợp đồng**: fixture `workflow.json` (states/transitions VI, §3) + scheduler `daily_contract_check` (state Sắp hết hạn/Hết hạn) + API `get_contract_health`/`list_quota_alerts`; FE màn "Sức khoẻ HĐ"; test transition smoke.
3. **Slice M02-3 — Quota enforce + usage log**: `AntMed Quota Usage Log` + hàm `assert_item_in_contract`/`assert_quota_available`/`consume_quota`/`recompute_quota_usage`; API `check_item_in_contract`; test BR-01/02/06 (chặn item ngoài HĐ, override `Quản lý`, lock 100%). *(Wiring doc_events sang M04 thực hiện khi M04 land — chỉ cần hàm sẵn sàng.)*
4. **Slice M02-4 `[PLANNED]` — Phụ lục (Amendment)**: `AntMed Contract Amendment` + logic cộng quota + `has_amendment`; FE form phụ lục.

---

## 9. ADRs

### ADR-M02-01: ADAPT scaffold `AM `→`AntMed ` + native-lite (KHÔNG ERPNext)
- **Status**: Accepted (kế thừa ADR-M01-02, DEC D1)
- **Date**: 2026-06-17
- **Context**: Scaffold `docs/antmed_crm/antmed_crm/m02_contract` (app riêng cũ) dùng `AM Tender Contract`/`AM Tender Contract Item`, Link→`Customer`/`Item` (ERPNext), `module="M02 Contract"`, Role `AM System Admin`, naming `TC-`. Quyết định khoá: in-place fork, prefix `AntMed `, native-lite (KHÔNG ERPNext).
- **Decision**: Đổi tên DocType→`AntMed Contract`/`AntMed Quota Item`/`AntMed Contract Amendment`/`AntMed Quota Usage Log`; `hospital` Link→`AntMed Hospital` (M01); `item` Link→`AntMed Item` (M03 native-lite); `module=AntMed`; Role→VI (DEC-A); naming `AM-HD-`/`AM-PL-` (KHÔNG `TC-`, KHÔNG `AM-DR`).
- **Consequences**: (+) Đồng nhất với M01, không phụ thuộc ERPNext. (−) Phải đợi/đồng bộ M03 cho Link `item` (xem ADR-M02-02).

### ADR-M02-02: Link `item` khi M03 chưa land (W1 song song)
- **Status**: Accepted
- **Date**: 2026-06-17
- **Context**: M02 và M03 cùng W1, có thể M02 (Contract) bắt đầu trước khi `AntMed Item` (M03) tồn tại → Link options trỏ doctype chưa có sẽ lỗi migrate.
- **Decision (CHỐT cho M02-1)**: Slice M02-1 tạo `item` = **`Data`** (mã SKU), KHÔNG còn "Data hoặc Link". Khi `AntMed Item` land (M03), patch đổi fieldtype→Link `AntMed Item` + backfill (Slice M02-3 cần Link thật để enforce BR-01). Enforce BR-01 KHÔNG nằm trong M02-1.
- **Alternatives**: (a) đợi M03 land trước — loại vì block M02-1 read-only không cần catalog; (b) Link mềm trỏ doctype chưa tồn tại — loại vì lỗi migrate.
- **Consequences**: (+) M02-1 không bị chặn bởi M03. (−) cần 1 patch đổi fieldtype `Data`→Link khi M03 land.

### ADR-M02-03: Workflow Frappe-native + chốt state field
- **Status**: Accepted (kế thừa DEC D2)
- **Date**: 2026-06-17
- **Context**: Scaffold dùng Select `status` EN không có transition/role. SPEC chốt Frappe Workflow gốc.
- **Decision**: Dùng `Workflow` fixture (`workflow.json`) + `docstatus`; states/transitions tiếng Việt (§3); đề xuất state field **`workflow_state`** (chuẩn). `[cần khảo sát]`: nếu giữ `status` thì set `workflow_state_field="status"` — chốt 1 lần trước khi code slice M02-2.
- **Consequences**: (+) chuẩn Frappe, audit qua docstatus. (−) cần fixture + smoke test mỗi transition.

### ADR-M02-04: M02-1 dùng Select `status` read-only — KHÔNG Workflow fixture
- **Status**: Accepted (chỉ phạm vi Slice M02-1; M02-2 sẽ nâng lên Workflow theo ADR-M02-03)
- **Date**: 2026-06-17
- **Context**: Acceptance M02-1 yêu cầu list lọc theo "workflow_state/status" + verify submit→docstatus 1, nhưng KHÔNG yêu cầu transition/role/state-machine. ADR-M02-03 (Workflow `workflow_state` thật) cần fixture `workflow.json` + smoke test mỗi transition → quá tải cho slice read-only.
- **Decision**: M02-1 dùng **Select `status`** (`Nháp/Hiệu lực/Sắp hết hạn/Hết hạn/Đã huỷ`, default `Nháp`, read-only display) — KHÔNG tạo `workflow.json`, KHÔNG field `workflow_state`. `is_submittable=1` GIỮ để test submit→docstatus 1 (không cần Workflow để submit). `list_contracts` lọc theo `status`; nếu caller truyền key `workflow_state` thì map về `status` (backward-friendly với acceptance wording).
- **Alternatives**: (a) tạo Workflow ngay M02-1 — loại: vi phạm scope-slice (Never §1bis), tốn fixture+smoke; (b) bỏ hẳn status — loại: acceptance cần badge + filter trạng thái.
- **Consequences**: (+) M02-1 nhẹ, không fixture mới. (−) Slice M02-2 cần migrate `status`→`workflow_state` (hoặc set `Workflow.workflow_state_field="status"`) — ghi vào ADR-M02-03 khi thực thi. KHÔNG Supersede ADR-M02-03 (chỉ defer).

### ADR-M02-05: `NV kinh doanh` = read-only trên `AntMed Contract` (khác M01)
- **Status**: Accepted
- **Date**: 2026-06-17
- **Context**: Ở M01 `NV kinh doanh` có create/write (quản khách hàng). HĐ chứa **đơn giá trúng thầu + quota** — hậu quả data sai = cao (câu hỏi #6): NV sửa quota/đơn giá → giao sai giá / vượt trần thầu (rủi ro pháp lý).
- **Decision**: DocPerm M02: `NV kinh doanh` = **read** (+ print/report/export/email/share), KHÔNG write/create/delete/submit. `Thủ kho` = read (cần biết quota khi xuất kho). `Quản lý` + `System Manager` = full. Đặt trong DocType JSON (như M01), KHÔNG fixture role-permission riêng. KHÔNG dùng Role `AM System Admin`.
- **Alternatives**: NV được create HĐ nháp — loại: trộn quyền nhập đơn giá thầu vào sales rep, rủi ro compliance.
- **Consequences**: (+) khoá sửa quota/giá khỏi NV. (−) tạo/sửa HĐ chỉ `Quản lý`+ → quy trình nhập HĐ phải có `Quản lý` (đúng nghiệp vụ thầu).

### ADR-M02-06: Vòng 1 = chỉ màn DANH SÁCH; defer FE Detail + vô hiệu row-click
- **Status**: Accepted (chỉ phạm vi vòng-factory hiện tại; KHÔNG Supersede ADR-M02-04/05)
- **Date**: 2026-06-17
- **Context**: Acceptance vòng 1 carve **Detail OUT** ("route `AntmedContractDetail` CHƯA thuộc vòng này → tạm vô hiệu điều hướng chi tiết"). Nhưng §1bis.5 bản trước liệt kê CẢ `/antmed/contracts/:name` (`AntmedContractDetail`) là "FROZEN cho M02-1" và yêu cầu "Click dòng → router.push detail". `AntmedContracts.vue` (đã build) ở `openContract` (dòng 264-266) **đang** `router.push({name:'AntmedContractDetail', ...})` → route chưa tồn tại ⇒ no-match ⇒ rơi `Invalid Page` = **dead-end** (vi phạm Red Flag "row-click dead-end"). Đây là **lỗi thiết kế gốc trong Core Doc** → Self-Correction: sửa doc TRƯỚC, mô tả delta cho FE dev.
- **Decision**: (1) Vòng này **chỉ** đăng ký route `AntmedContracts` (`/antmed/contracts`); KHÔNG đăng ký `:name`/Detail, KHÔNG tạo `AntmedContractDetail.vue`. (2) FE phải **vô hiệu điều hướng chi tiết**: `openContract` → **no-op** (giữ chữ ký) + gỡ affordance click ở `<tr>` (`cursor-pointer`/`role="link"`/`tabindex`/`@click`/`@keydown`/`:aria-label` "Xem chi tiết"). (3) BE endpoint `get_contract` **vẫn ship** (đã có test cover) — dùng cho vòng Detail kế (Slice M02-1b) mà không phải sửa BE lại.
- **Alternatives**: (a) đăng ký luôn route Detail trỏ page rỗng/placeholder — loại: tạo dead page (Red Flag), ngược acceptance; (b) ẩn nguyên cột/dòng không cho click nhưng vẫn để route push tới name chưa có — loại: vẫn dead-end nếu user gõ URL hoặc còn sót handler; (c) bỏ `get_contract` khỏi vòng này — loại: FE Detail vòng sau sẽ phải mở lại BE, tốn 1 vòng.
- **Consequences**: (+) Trang LIST chạy thật, không dead-end, không dead page; FE Detail tách thành Slice M02-1b sạch sẽ. (−) `get_contract` tạm "ship nhưng chưa có FE tiêu thụ" trong 1 vòng (chấp nhận — đã có BE test bảo vệ contract). (−) Khi mở Slice M02-1b phải khôi phục lại `router.push` + affordance đã gỡ (delta nhỏ, đã ghi rõ ở §1bis.5).

> Kế thừa: **ADR-M01-01** (in-place), **ADR-M01-02** (prefix `AntMed `), **ADR-M01-05** (hoãn data-scope BR-13, giữ invariant count==rows), **DEC-A** (role VI), **D1/D2** (native-lite + Frappe Workflow). Không Supersede.

---

## 10. Acceptance / DoD

> Theo SPEC §6. Một slice "xong" = BE test xanh THẬT + FE vitest + build + (sau USER reload) pixel verify + no-regression.

**BE (TDD — `Ran N tests OK`):** file `crm/tests/test_antmed_contract.py`, lệnh `bench --site miyano run-tests --module crm.tests.test_antmed_contract`.

*TC Slice M02-1 (FROZEN — bắt buộc xanh):*
1. `AntMed Contract`/`AntMed Quota Item` tồn tại sau migrate; `AntMed Contract`: `is_submittable==1`, `track_changes==1`, `naming_rule=='By "Naming Series" field'`; `AntMed Quota Item`: `istable==1`. Đủ field tối thiểu (§1bis.1/§1bis.2).
2. Naming: tạo HĐ → `name` khớp regex `^AM-HD-2026-\d{5}$` (KHÔNG `TC-`/`AM-DR-`/`AM-DOC-`).
3. `contract_no` `reqd=1`+`unique=1`: tạo 2 HĐ cùng `contract_no` → raise `DuplicateEntryError`/`ValidationError`.
4. `list_contracts()` trả `{data,total_count}`; mỗi item gồm `name/contract_no/hospital/hospital_name/valid_to/total_value/status`; **`len(data)==total_count`** khi `page_length=0` (count==rows, đếm qua `get_list` dưới permission — KHÔNG `db.count`). Filter `hospital` + `status` (+ map `workflow_state`→`status`) + search `contract_no` hoạt động.
5. `get_contract(name)` trả RAW dict field HĐ + `hospital_name` resolve qua Link + `items[]` (mỗi dòng `unit_price/quota_qty/used_qty/remaining_pct/lock_at_100`); user không read → `frappe.throw(PermissionError)`.
6. Submit 1 HĐ → `docstatus==1` (verify submittable hoạt động — KHÔNG enforce BR ở slice này).
7. DocPerm: `Quản lý` full (incl submit/cancel/amend); `NV kinh doanh` read-only (KHÔNG write/create/delete); `Thủ kho` read; `System Manager` full. (test có thể assert DocPerm JSON như `test_docperm_roles_are_vietnamese` của M01.)

*TC Slice M02-2/3 (sau, KHÔNG thuộc M02-1):*
8. Submit → state `Hiệu lực`; transition Workflow (M02-2).
9. `assert_item_in_contract` chặn item ngoài HĐ, `Quản lý` override (BR-01/02, M02-3).
10. `assert_quota_available` throw khi chạm trần (BR-06, M02-3); `consume_quota`+`recompute_quota_usage` invariant tổng usage==used_qty (M02-3).
- **No-regression**: `test_antmed_bootstrap` + `test_antmed_customer` + `test_antmed_rbac_boot` + test gốc CRM (org_hierarchy/crm_lead/crm_task) vẫn xanh.

**FE (vitest + build) — Slice M02-1:** `frontend/tests/unit/antmedContract.test.js` — route `AntmedContracts` (`/antmed/contracts`, lazy) **tồn tại**; route `AntmedContractDetail` (`/antmed/contracts/:name`) **KHÔNG tồn tại** ở vòng này (assert vắng mặt → bằng chứng Detail deferred, ADR-M02-06); `@/data/antmed` export `listContracts`/`getContract`/`CONTRACT_WORKFLOW_THEME`; page list gọi `crm.api.antmed.contract.list_contracts` đọc `r.data.data`; KHÔNG `antmed_crm.api`/axios/tanstack/`createListResource`. `vue-tsc`/`yarn build` không lỗi mới + emit chunk `Antmed*` không vỡ + `crm.html` regenerate. *(route/page Detail + `/antmed/contract-health` + `get_contract_health` = vòng sau, KHÔNG test ở vòng này.)*

**Pixel (Playwright, sau USER reload) — Slice M02-1:** `http://miyano:8000/crm/antmed/contracts` render list HĐ thật (loading→data/empty, KHÔNG dead page) → filter BV/status + search số HĐ (param phát đi == UI selection) → verify count==rows trên UI; **row-click KHÔNG điều hướng** (no-op, không rơi `Invalid Page` — không dead-end); 0 console error; network API 200; permission 403 khi user thiếu read. *(màn Detail + contract-health = vòng sau.)*

---

## Tham chiếu chéo
- Spec dự án: `../SPEC_AntMed_CRM.md` (§5 code style, §6 DoD, §8 ADR/DEC, D1/D2)
- Plan/wave/DAG: `../PLAN_AntMed_CRM.md` (§2 component inventory M02, §3 W1, §4 song song)
- Mô tả nghiệp vụ: `../../antmed_crm/docs/AntMed_CRM_Modules.md §2` (Hợp đồng & Gói thầu — ground-truth field)
- UI: `../../antmed_crm/docs/AntMed_CRM_UI_Design.md` §1.2 (widget % Quota 70/90/100), §1.3 (Sức khoẻ hợp đồng)
- House style + tiền đề M01: `./m01_customer360.md`, `./m01_bootstrap.md`, `./m01_naming_conventions.md`
- RBAC role VI: `./m14_rbac_w0_role_naming.md` (DEC-A)
- Scaffold tham chiếu (ADAPT, KHÔNG copy): `docs/antmed_crm/antmed_crm/m02_contract/doctype/{am_tender_contract,am_tender_contract_item,am_quota_usage_log,am_contract_amendment}/`
- Module liên quan (downstream): M03 (`AntMed Item` cho Link quota), M04 (giao phòng mổ — enforce BR-01/02/06 + usage log), M08 (pipeline→thầu→HĐ), M09 (đơn/AR theo đơn giá trúng)
</content>
</invoke>
