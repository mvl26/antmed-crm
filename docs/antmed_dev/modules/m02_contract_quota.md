# M02 — Hợp đồng & Gói thầu + Quota (Core Doc)

| Mục | Giá trị |
|---|---|
| Module folder | `crm/antmed/` (module Frappe **`AntMed`**, scrubbed = `antmed`) |
| DocType folder | `crm/antmed/doctype/antmed_contract/`, `crm/antmed/doctype/antmed_quota_item/` (+ `[PLANNED]` `antmed_contract_amendment/`, `antmed_quota_usage_log/`) |
| API package | `crm/api/antmed/contract.py` (đường gọi `antmed_crm.api.antmed.contract.<fn>`) |
| FE pages | `frontend/src/pages/AntmedContracts.vue` (route `/antmed/contracts`, đã build) · **`AntmedContractDetail.vue`** (route `/antmed/contracts/:name` — **Slice M02-1b, vòng này**) · `[PLANNED]` `AntmedContractHealth.vue` (`/antmed/contract-health`) |
| Vị trí code thật (repo) | ⚠️ Python package **`antmed_crm`** (underscore) = `apps/antmed-crm/antmed_crm/` → DocType `antmed_crm/antmed/doctype/antmed_contract`, API **`antmed_crm/api/antmed/contract.py`** (đã land M02-1a), test `antmed_crm/tests/test_antmed_contract.py` (12/12 OK). FE = `apps/antmed-crm/frontend/`. Core Doc = `apps/antmed-crm/docs/antmed_dev/modules/`. (Đường gọi API từ FE/test vẫn là chuỗi `antmed_crm.api.antmed.contract.*` — Frappe map app `antmed_crm` qua tên app cài đặt; KHÔNG nhầm với app `crm` riêng.) |
| Wave (PLAN) | **W1 — Master data & catalog** (chạy ‖ M01-full ‖ M03, sau M01 core) |
| Role chính | `Quản lý`, `NV kinh doanh` (DEC-A — xem `./m14_rbac_w0_role_naming.md`); `[PLANNED]` `Pháp lý`, `Kế toán` cho duyệt/đối soát quota |
| Phụ thuộc | **M01** (`AntMed Hospital`) |
| Cấp dữ liệu cho | **M04** (đối chiếu DR vs danh mục trúng thầu), **M08** (pipeline → thầu → won → HĐ), **M09** (đơn/AR theo đơn giá trúng) |
| Site dev | `miyano` |
| Trạng thái docs | DESIGN — Slice **M02-1a SHIPPED** · **M02-1b FROZEN** (FE Detail) · **M02-4 FROZEN** (vòng 10 — endpoint MỚI `top_hospitals` + widget "Top 10 Bệnh viện" CEO, §1quater) · **M02-5 FROZEN** (vòng 11 — endpoint MỚI `top_quota_items` + widget "Danh mục VT trúng thầu — top 5" ở chân màn `/antmed/contract-health`, §1quint; + BE cleanup gỡ `top_hospitals` trùng — ADR-M02-10) · **M02-7 FROZEN** (vòng 15 — endpoint MỚI `revenue_mix` + widget "Cơ cấu doanh thu" CEO trên `/antmed`, §1sext). M02-2/3 đề xuất; Amendment `[PLANNED]` (Slice M02-8) |
| Cập nhật | 2026-06-18 (BA vòng 15 — Slice M02-7 widget Cơ cấu doanh thu theo phân loại VTYT A/B/C/D) |

> **Trạng thái: Slice M02-1a SHIPPED. Slice M02-1b = spec-contract FROZEN (xem §1bis + §1ter).**
>
> Slice M02-1a ĐÃ LAND: DocType `AntMed Contract` + `AntMed Quota Item` (`antmed_crm/antmed/doctype/`), API `antmed_crm/api/antmed/contract.py` (`list_contracts` + `get_contract`, RAW dict, count==rows), test `antmed_crm/tests/test_antmed_contract.py` **12/12 OK**, FE màn DANH SÁCH `AntmedContracts.vue` (route `/antmed/contracts`). M02-2/3/4 (workflow / enforce BR / amendment) vẫn là **ĐỀ XUẤT thiết kế** ở §2–§6 (chưa freeze), ground trên scaffold cũ + `AntMed_CRM_Modules.md §2` + `UI_Design §1.2/§1.3`.
>
> 🟢 **DELTA 2026-06-17 (BA Bước 2 — vòng 2 factory, Slice M02-1b):** mở lại màn **CHI TIẾT Hợp đồng** (`/antmed/contracts/:name`, `AntmedContractDetail.vue`) **đảo quyết định defer của ADR-M02-06** (Self-Correction) → ADR-M02-07 (Accepted, Supersede ADR-M02-06). Spec-contract FE Detail FROZEN ở **§1ter** (mới). **BE KHÔNG đổi** — `get_contract` đã ship & test cover (acceptance "GIỮ 12/12 OK, không sửa BE"). Đồng thời cập nhật §1bis.5 + §7 + §8 cho khớp scope mới.
>
> 🟢 **DELTA 2026-06-17 (BA Bước 2 — vòng 10 factory, Slice M02-4):** thêm **endpoint MỚI** `top_hospitals(limit=10)` (BE — APPEND `contract.py`) + wire **widget "Top 10 Bệnh viện"** vào `AntmedHome.vue` (Dashboard `/antmed` CEO, mockup A1 line 261), thay placeholder `AntmedPlaceholderPanel "Top 10 Bệnh viện theo doanh thu"`. Gộp BV theo `SUM(total_value)` + `quota_used_pct`; `health_color = _health_color(pct, None)` (ADR-M02-08); bar màu FE qua `healthBarClass` PURE (tái dùng, KHÔNG ngưỡng mới); RAW `{data, total_count}` sort GIẢM revenue, cắt ≤limit, dùng `frappe.get_list` (BR-13, KHÔNG raw SQL — ADR-M02-09 vì sao count≠rows ở đây). Spec FROZEN **§1quater**; ADR mới **M02-08/09**; cập nhật §5 (+ dòng `top_hospitals`) + §7 + §8 (Slice M02-4; **đổi** nhãn Amendment cũ "M02-4" → **M02-5** tránh trùng). **Endpoint cũ KHÔNG đổi** (`list_contracts`/`get_contract`/`get_contract_health`/`list_quota_alerts` no-regression).
>
> 🟢 **DELTA 2026-06-17 (BA Bước 2 — vòng 11 factory, Slice M02-5):** thêm **endpoint MỚI** `top_quota_items(limit=5)` (BE — APPEND `contract.py`) + wire **widget "Danh mục VT trúng thầu — top 5"** vào **chân màn** `AntmedContractHealth.vue` (route `/antmed/contract-health`, mockup A2 id=ceo), card MỚI **dưới** bảng "Sức khỏe HĐ". Khác `top_hospitals`: gộp **CROSS-CONTRACT theo `item` (SKU)** — `used_pct = 100*SUM(used_qty)/SUM(quota_qty)` trên TẤT CẢ dòng quota cùng `item` của mọi HĐ user ĐỌC ĐƯỢC; `health_color = _health_color(used_pct, None)` (tái dùng — như ADR-M02-08); RAW `{data, total_count}` sort **GIẢM theo `used_pct`** cắt ≤`limit` (mặc định 5); `frappe.get_list` (BR-13, KHÔNG raw SQL — fail-closed `{data:[],total_count:0}`); SUM(quota_qty)==0 → `used_pct=0.0` (fail-safe). FE: `getTopQuotaItems` (data/antmed.js MỚI) fetch **ĐỘC LẬP** với `getContractHealth` (lỗi 1 không vỡ cái kia); bar màu qua `healthBarClass` PURE (tái dùng, KHÔNG ngưỡng/sort FE); tri-branch loading/error(Thử lại)/empty 'Chưa có vật tư trúng thầu'. **BE cleanup kèm vòng này (ADR-M02-10):** GỠ 1 trong 2 `def top_hospitals` trùng trong `contract.py` (giữ bản fail-closed try/except) + gỡ `test_top_hospitals_*` trùng tên giữa `TestAntMedContract` và `TestAntMedTopHospitals` → sau cleanup `top_hospitals` + `top_quota_items` đều resolve đúng. Spec FROZEN **§1quint**; ADR mới **M02-10** (cleanup) + **M02-11** (`top_quota_items` gộp-theo-item, count==rows N/A). Cập nhật §5 (+ dòng `top_quota_items`) + §7 + §8 (Slice M02-5; Amendment đẩy → **M02-7**). **Endpoint cũ KHÔNG đổi** (`list_contracts`/`get_contract`/`get_contract_health`/`list_quota_alerts`/`top_hospitals` no-regression hành vi).

> 🟢 **DELTA 2026-06-18 (BA Bước 2 — vòng 15 factory, Slice M02-7):** thêm **endpoint MỚI** `revenue_mix()` (BE — APPEND `contract.py`) + wire **widget "Cơ cấu doanh thu"** vào `AntmedHome.vue` (Dashboard `/antmed` CEO, mockup A2 id=ceo), card MỚI **cùng hàng / ngay sau** "Top 10 Bệnh viện" (KHÔNG đụng card Top 10 hiện có). Khác `top_quota_items`: gộp **CROSS-CONTRACT theo `classification` của `AntMed Item`** (4 lớp **Loại A/B/C/D**) — `revenue = SUM(used_qty × unit_price)` trên TẤT CẢ dòng `AntMed Quota Item` (mọi HĐ user ĐỌC ĐƯỢC) có item thuộc lớp đó. Trả RAW `{data, total_revenue}` với `data` **đúng 4 phần tử cố định thứ tự A→B→C→D** (kể cả lớp revenue=0 vẫn render); `pct = round(100*revenue/total_revenue, 1)` (`total_revenue==0 ⇒ mọi pct=0.0`, KHÔNG ZeroDivisionError); item thiếu classification → gộp nhóm `'Khác'` **KHÔNG render & KHÔNG cộng vào `total_revenue`** (total = SUM 4 lớp A–D để pct cộng ~100% — ADR-M02-12). Resolve item→classification **BATCH 1 query** `frappe.get_all("AntMed Item", filters={"item_code":("in", skus)})` — KHÔNG N+1, KHÔNG raw SQL. **BR-13 fail-closed**: user KHÔNG read-perm `AntMed Contract` → trả `{data: 4 dòng revenue=0/pct=0, total_revenue:0}` (KHÔNG raise, KHÔNG leak). FE: `getRevenueMix` (data/antmed.js MỚI) fetch **ĐỘC LẬP** với `getTopHospitals`; tiền VI gọn qua **`formatVnMoney`** đã có (`'2,1 tỷ'`/`'186,4 tr'` — ADR-M02-13); bar width=`pct%` màu brand qua `revenueMixBarStyle` PURE (KHÔNG ngưỡng/sort FE); tri-branch loading/error(Thử lại)/empty (`total_revenue==0` → 'Chưa có dữ liệu doanh thu'). Spec FROZEN **§1sext**; ADR mới **M02-12** (rollup theo classification + 'Khác' loại khỏi total) + **M02-13** (tái dùng `formatVnMoney`) + **M02-14** (Self-Correction: FE read-resource set `method:'GET'` chống defect POST→403 systemic, §1sext.bis). Cập nhật §5 (+ dòng `revenue_mix`) + §7 + §8 (Slice M02-7; Amendment đẩy → **M02-8**). **Endpoint cũ KHÔNG đổi** (`list_contracts`/`get_contract`/`get_contract_health`/`list_quota_alerts`/`top_hospitals`/`top_quota_items` no-regression hành vi).

> 🔗 **Tiền đề (đã land @ M01)**: `AntMed Hospital` tồn tại (`crm/antmed/doctype/antmed_hospital/`), khoá tự nhiên `hospital_code`; namespace `antmed_crm.api.antmed.*` + route `/antmed/*` đã mở; 3 Role VI (`NV kinh doanh`/`Thủ kho`/`Quản lý`) đã có trong DB. M02 **mở rộng** namespace này, KHÔNG dựng lại nền.

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

> **Boundaries Slice M02-1a (đã SHIPPED — giữ làm tham chiếu, KHÔNG sửa lại):**
> - **Always**: 2 DocType (`AntMed Contract` submittable + `AntMed Quota Item` child) + 2 endpoint đọc (`list_contracts`/`get_contract`) + DocPerm VI (§1bis.4) + naming `AM-HD-2026-00001`. FE màn DANH SÁCH `/antmed/contracts` + nav-entry "Hợp đồng" enabled.
> - **Never**: KHÔNG fixture `workflow.json`; KHÔNG enforce BR-01/02/06; KHÔNG usage-log/amendment; KHÔNG endpoint `get_contract_health`/`list_quota_alerts`/`check_item_in_contract`; KHÔNG route `/antmed/contract-health`; KHÔNG `doc_events` mới; KHÔNG Link→`AntMed Item` (dùng `Data`); KHÔNG `createListResource`; KHÔNG axios; KHÔNG Role `AM System Admin`.
>
> **Boundaries Slice M02-1b — FE Detail (VÒNG NÀY)** (dev KHÔNG suy diễn ngoài đây — chi tiết §1ter):
> - **Always**: tạo **đúng 1 page** `frontend/src/pages/AntmedContractDetail.vue` + đăng ký **đúng 1 route** `/antmed/contracts/:name` (name `AntmedContractDetail`, lazy, `props: true`) trong `frontend/src/router.js` (đặt cạnh các route Detail `/antmed/*/:name` đã có); wire vào endpoint **`antmed_crm.api.antmed.contract.get_contract` ĐÃ CÓ** qua `getContract` (đã export ở `@/data/antmed`); render header HĐ + bảng quota (% bar màu theo ngưỡng) + tri-branch loading/error(reload)/data + empty-state quota + breadcrumb link về `/antmed/contracts`; **khôi phục** affordance click + `router.push({name:'AntmedContractDetail', params:{name: row.name}})` ở `AntmedContracts.vue` (đảo no-op của M02-1a). Cập nhật FE test `antmedContracts.test.js` (đảo các assert "Detail vắng mặt") + thêm test page Detail.
> - **Never**: **KHÔNG sửa BE** (`contract.py` / DocType / `test_antmed_contract.py` — giữ 12/12 OK); KHÔNG đổi guard chung (`shouldRedirectNotPermitted`/`beforeEach`); KHÔNG `createListResource`; KHÔNG axios/`crm.api.*`/TanStack/`.ts`; KHÔNG fixture/workflow/usage-log; KHÔNG enforce BR; KHÔNG route `/antmed/contract-health`; KHÔNG hardcode chuỗi EN (mọi nhãn qua `__()`); KHÔNG leak stacktrace ở error-state.
> - **Ask-first**: muốn thêm Workflow/usage-log/enforce/contract-health → Slice M02-2/3 (vòng factory mới), KHÔNG nhét vào M02-1b.

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

### 1bis.5 — FE màn DANH SÁCH (Slice M02-1a — đã SHIPPED)

> 🟢 **Self-Correction 2026-06-17 (ADR-M02-06):** Slice M02-1a chỉ làm màn **DANH SÁCH** (`/antmed/contracts`); màn Detail defer. Bản trước liệt kê Detail là "FROZEN cho M02-1" → sai scope vòng 1, đã sửa.
>
> 🟢 **UPDATE 2026-06-17 (vòng 2 — ADR-M02-07 Supersede ADR-M02-06):** Slice **M02-1b mở lại màn Detail** (`/antmed/contracts/:name`). Spec Detail FROZEN ở **§1ter** (mới). M02-1b phải **khôi phục** ở `AntmedContracts.vue`: (1) `openContract(name)` → `router.push({ name: 'AntmedContractDetail', params: { name } })` (đảo no-op M02-1a dòng 265-267); (2) affordance click ở `<tr>` dữ liệu: `cursor-pointer` + `role="link"` + `tabindex="0"` + `@click="openContract(row.name)"` + `@keydown.enter="openContract(row.name)"` + `:aria-label` "Xem chi tiết hợp đồng {contract_no}". Phần list-resource/cột/lọc/search GIỮ NGUYÊN (đã verified, KHÔNG viết lại).

| Route (APPEND lazy vào `frontend/src/router.js`) | name | page | Vòng |
|---|---|---|---|
| `/antmed/contracts` | `AntmedContracts` | `frontend/src/pages/AntmedContracts.vue` (đã build) | **M02-1a (đã ship)** |
| `/antmed/contracts/:name` | `AntmedContractDetail` | `frontend/src/pages/AntmedContractDetail.vue` | **M02-1b (vòng này — §1ter)** |

- **Route LIST (M02-1a, đã đăng ký)**: block `{ path: '/antmed/contracts', name: 'AntmedContracts', component: () => import('@/pages/AntmedContracts.vue') }` — đặt cạnh các route `/antmed/*` khác (cho phép CRM HOẶC AntMed user qua `shouldRedirectNotPermitted` đã có, **KHÔNG** thêm allow-check mới).
- **List** (`AntmedContracts.vue`, đã build — KHÔNG viết lại logic resource): dùng `listContracts` từ `@/data/antmed` (`createResource` → `antmed_crm.api.antmed.contract.list_contracts`), đọc **`r.data.data`** + `r.data.total_count` (list trả dict bọc — pattern verified R2, KHÔNG `createListResource`). Cột: Số HĐ / Bệnh viện (hospital_name) / Hiệu lực đến / Giá trị / badge `status` (theme `CONTRACT_WORKFLOW_THEME`). Lọc theo BV + status, search số HĐ (debounce 300ms). Tri-branch loading/error/empty + dòng "Tổng cộng: {total_count}".
- **Row-click — M02-1b KHÔI PHỤC điều hướng chi tiết**: M02-1a đã `openContract` = no-op + gỡ affordance để tránh dead-end (route Detail chưa có). M02-1b đăng ký route Detail (§1ter) → **mở lại**: `openContract(name)` → `router.push({ name: 'AntmedContractDetail', params: { name } })`; thêm lại affordance ở `<tr>` dữ liệu (`cursor-pointer`, `role="link"`, `tabindex="0"`, `@click="openContract(row.name)"`, `@keydown.enter="openContract(row.name)"`, `:aria-label` "Xem chi tiết hợp đồng {contract_no || name}"). Không còn dead-end vì route đã tồn tại.
- **Nhãn 100% tiếng Việt qua `__()`**: badge status (Nháp/Hiệu lực/Sắp hết hạn/Hết hạn/Đã huỷ) + header cột. KHÔNG hardcode chuỗi EN.
- **KHÔNG** route `/antmed/contract-health` (M02-2). Sidebar `frontend/src/data/antmedNav.js`: mục `{ key: 'contracts', label: 'Hợp đồng', to: '/antmed/contracts' }` chuyển `enabled: false` → **`enabled: true`** (đây là nav-entry tới Hợp đồng — không thêm item mới).
- **KHÔNG** axios, KHÔNG `crm.api.*`, KHÔNG TanStack, KHÔNG `.ts`.

---

## 1ter. Slice M02-1b — Spec-contract FROZEN: FE màn CHI TIẾT Hợp đồng ✅

> **Mục tiêu vòng**: tạo trang CHI TIẾT 1 HĐ (`/antmed/contracts/:name`) tiêu thụ endpoint `get_contract` **đã có** (BE KHÔNG đổi), render header HĐ + bảng quota có thanh % màu theo ngưỡng, và mở lại drill-down từ danh sách. **Self-Correction**: đảo defer của ADR-M02-06 → ADR-M02-07.
>
> **Boundaries** (dev KHÔNG suy diễn ngoài đây):
> - **Always**: 1 page `AntmedContractDetail.vue` + 1 route `/antmed/contracts/:name` (lazy, `props: true`, qua guard chung đã có) + khôi phục drill-down ở list + cập nhật FE test. Mọi nhãn qua `__()`.
> - **Never**: KHÔNG sửa BE (`contract.py`/DocType/`test_antmed_contract.py` — 12/12 OK); KHÔNG đổi guard chung; KHÔNG endpoint mới; KHÔNG `createListResource`/axios/`.ts`/TanStack; KHÔNG enforce BR/workflow/usage-log; KHÔNG leak stacktrace.

### 1ter.1 — Endpoint tiêu thụ (ĐÃ CÓ — KHÔNG đổi)

`antmed_crm.api.antmed.contract.get_contract(name)` (GET) → RAW dict (verify @ `antmed_crm/api/antmed/contract.py:125-155`):

```json
{ "name": "AM-HD-2026-00001", "contract_no": "01/2026/HĐ-AntMed",
  "hospital": "BVTW-HUE", "hospital_name": "BV TW Huế",
  "signed_date": "2026-01-05", "valid_from": "2026-01-05", "valid_to": "2026-12-31",
  "total_value": 1500000000, "status": "Hiệu lực", "docstatus": 1,
  "items": [ {"item": "VTYT-001", "item_name": "Stent ...", "uom": "Cái",
              "unit_price": 12000000, "quota_qty": 100, "used_qty": 72,
              "remaining_pct": 28.0, "lock_at_100": 1} ] }
```

- FE gọi qua **`getContract`** (đã export `@/data/antmed:118-124`, `createResource` → `antmed_crm.api.antmed.contract.get_contract`). **KHÔNG** thêm hàm data mới.
- Đọc payload: `getContract` trả dict THƯỜNG (KHÔNG bọc `{data,total_count}` như list) → FE đọc **`r.data.<field>`** + **`r.data.items`** TRỰC TIẾP (KHÔNG `r.data.data`). Tránh tái phạm LL list-wrap.
- **403 / not-found**: BE throw `frappe.PermissionError` (user thiếu read) → resource vào nhánh `.error`; doc không tồn tại → `frappe.DoesNotExistError`/`get_doc` raise → cũng `.error`. FE hiển thị **error-state** chung (KHÔNG phân biệt 403 vs 404 ở UI — chỉ thông điệp VI + nút "Thử lại"), **KHÔNG leak stacktrace** (chỉ đọc `error.messages?.[0]` / fallback chuỗi VI).

### 1ter.2 — Route (FROZEN — APPEND vào `frontend/src/router.js`)

| path | name | component | props |
|---|---|---|---|
| `/antmed/contracts/:name` | `AntmedContractDetail` | `() => import('@/pages/AntmedContractDetail.vue')` | `true` |

- **Vị trí**: APPEND vào mảng `routes`, đặt **cạnh** các route Detail `/antmed/*/:name` đã có (`AntmedHospitalDetail` `/antmed/hospitals/:name`, `AntmedDoctorDetail` `/antmed/doctors/:name` — cùng pattern `props: true`, lazy). KHÔNG đặt trước `/antmed/contracts` (Vue Router match cụ thể; thứ tự không vỡ vì path khác segment, nhưng giữ gần nhóm cho dễ đọc).
- **Guard**: đi qua `router.beforeEach` + `shouldRedirectNotPermitted(to, {isCrmUser, isAntmedUser})` **đã có** (router.js:159-184) — route `/antmed/*` cho phép CRM HOẶC AntMed user, outsider redirect. **KHÔNG** thêm allow-check mới, **KHÔNG** đổi guard. (Đã verify guard match theo prefix path `/antmed`, không liệt kê từng route → route mới tự động được bảo vệ.)
- **Nhận `name` (idiom CHỐT — theo `AntmedHospitalDetail.vue` đã ship, verify @ file đó)**: `defineProps({ name: { type: String, required: true } })` + route `props: true`; resource `getContract({ params: { name: props.name }, auto: true })`; `watch(() => props.name, () => contract.reload())` để fetch lại khi đổi `:name`. Nút quay lại dùng `import { useRouter } from 'vue-router'` → `router.push('/antmed/contracts')` (hoặc `router.push({ name: 'AntmedContracts' })`).

### 1ter.3 — Page `AntmedContractDetail.vue` (FROZEN — layout & binding)

> Pattern bám `AntmedDoctorDetail.vue` / `AntmedHospitalDetail.vue` (cùng app, đã ship): nút "Quay lại" + tri-branch loading/error/data, `createResource` auto-fetch theo `name`.

**Cấu trúc:**

1. **Breadcrumb / quay lại** (đầu trang): link/nút về `/antmed/contracts` — `router.push('/antmed/contracts')` hoặc `<router-link to="/antmed/contracts">` — nhãn `__('Hợp đồng')` (về danh sách). Acceptance: "breadcrumb có link quay lại danh sách".
2. **Tri-branch** (`aria-live="polite"`):
   - **loading**: `contract.loading` → `LoadingIndicator` + `__('Đang tải hợp đồng…')`.
   - **error**: `contract.error` → `role="alert"`, Badge red `__('Không tải được')` + thông điệp VI (`errorMessage` = `contract.error?.messages?.[0] || __('Không tải được hợp đồng')`) + Button `__('Thử lại')` `@click="contract.reload()"`. **KHÔNG** in `error.stack`/`error.exc`.
   - **data**: `contract.data` → header + bảng quota.
3. **Header HĐ** (đọc `contract.data.*` TRỰC TIẾP):
   | Trường UI | Nguồn | Format |
   |---|---|---|
   | Tiêu đề | `contract_no` (fallback `name`) | text 2xl semibold |
   | Bệnh viện | `hospital_name` (fallback `hospital`, fallback `—`) | text |
   | Ngày ký | `signed_date` | `formatDate` (vi-VN) |
   | Hiệu lực | `valid_from` – `valid_to` | `formatDate` 2 đầu (null → `—`) |
   | Tổng giá trị | `total_value` | `formatCurrency` VND (`toLocaleString('vi-VN',{style:'currency',currency:'VND',maximumFractionDigits:0})`) |
   | Trạng thái | `status` | `<Badge :theme="CONTRACT_WORKFLOW_THEME[status]||'gray'" :label="status">` |
   - Reuse helper `formatDate`/`formatCurrency` + `CONTRACT_WORKFLOW_THEME` (đã có ở list/`@/data/antmed`) — copy helper vào page (idiom hiện tại) HOẶC import theme từ `@/data/antmed`. KHÔNG hardcode VND/locale string khác.
4. **Bảng Quota** (`contract.data.items`):
   - Cột: Vật tư (`item_name` fallback `item`) · ĐVT (`uom`) · Đơn giá (`unit_price`, `formatCurrency`) · Quota (`quota_qty`) · Đã dùng (`used_qty`) · **Còn lại %** (thanh bar) · cờ **Khóa 100%**.
   - **Thanh % (bar) — ngưỡng màu theo "% đã dùng"** (CHỐT, khớp mockup A2): gọi `usedPct` = phần trăm ĐÃ DÙNG. Acceptance phát biểu theo "danh sách màu" theo % đã tiêu hao:
     - `usedPct >= 95` → **danger/đỏ** (theme `red`).
     - `usedPct >= 72` → **warn/cam** (theme `orange`).
     - còn lại → **brand/xanh** (theme `green`).
   - **Nguồn `usedPct`**: `remaining_pct` của BE = "% CÒN LẠI" → `usedPct = 100 - remaining_pct`. (Vd `remaining_pct=28` → đã dùng 72% → cam; `remaining_pct<=5` → ≥95% → đỏ.) Width bar = `usedPct%` (clamp 0–100). *(Lưu ý ngữ nghĩa: ngưỡng acceptance 95/72 áp lên **% đã dùng** = `100 - remaining_pct`. Nếu BE trả `remaining_pct=null` → coi `usedPct=0` → xanh, KHÔNG vỡ.)*
   - **Cờ `lock_at_100`**: khi truthy (`1`/true) hiển thị chip `__('Khóa khi đủ 100%')` (Badge gray/subtle). Khi false → ẩn chip.
   - **Empty-state quota**: `items` rỗng/`undefined` → khối `__('Chưa có dòng quota')` (KHÔNG render bảng rỗng, KHÔNG vỡ). Acceptance.
5. **Không màn trắng / không no-match**: truy cập trực tiếp URL `/antmed/contracts/<name>` phải render (route tồn tại + page mount + resource auto-fetch theo `name`). Khi `name` hợp lệ nhưng lỗi → error-state (không trắng). Khi `name` không tồn tại → BE raise → error-state.

### 1ter.4 — Wire drill-down ở `AntmedContracts.vue` (khôi phục)

- `openContract(name)` (dòng 265-267, hiện no-op) → đổi thành `router.push({ name: 'AntmedContractDetail', params: { name } })` (cần `import { useRouter } from 'vue-router'` + `const router = useRouter()` — kiểm tra đã import chưa).
- `<tr v-for>` dữ liệu: thêm lại `class="... cursor-pointer ..."`, `role="link"`, `tabindex="0"`, `@click="openContract(row.name)"`, `@keydown.enter="openContract(row.name)"`, `:aria-label="__('Xem chi tiết hợp đồng') + ' ' + (row.contract_no || row.name)"`. Gỡ comment "row-click VÔ HIỆU" (M02-1a) — thay bằng comment mô tả drill-down đã mở.

### 1ter.5 — FE test delta (`frontend/tests/unit/antmedContracts.test.js`) — BẮT BUỘC cập nhật

> ⚠️ Test M02-1a hiện **assert Detail VẮNG MẶT** (dòng 52-55 `not.toMatch AntmedContractDetail`, dòng 134-144 `openContract` no-op không `router.push`, dòng 146-157 `<tr>` không affordance). M02-1b **đảo** các assert này — nếu không sửa, test sẽ đỏ.

| Test cũ (M02-1a) | Hành động M02-1b |
|---|---|
| `KHÔNG đăng ký route Detail (... :name) (ADR-M02-06)` (dòng 52-55) | **ĐẢO**: assert router.js CÓ `name: 'AntmedContractDetail'` + path `/antmed/contracts/:name` + lazy import `AntmedContractDetail.vue`. |
| `row-click KHÔNG dead-end: openContract no-op, KHÔNG router.push` (134-144) | **ĐẢO**: assert `openContract` CÓ `router.push({ name: 'AntmedContractDetail'... })`. |
| `<tr> KHÔNG còn affordance click` (146-157) | **ĐẢO**: assert `<tbody>` CÓ `@click`/`@keydown`/`role="link"`/`cursor-pointer`/`tabindex` + `openContract`. |
| (mới) | **THÊM** test page `AntmedContractDetail.vue`: gọi `antmed_crm.api.antmed.contract.get_contract` qua `getContract`; đọc `r.data.items` (KHÔNG `r.data.data`); tri-branch loading/error(reload)/data; empty-state `Chưa có dòng quota`; ngưỡng màu bar (chuỗi nguồn chứa 95/72 + theme red/orange/green); chip `Khóa khi đủ 100%`; breadcrumb link `/antmed/contracts`; nút Thử lại `contract.reload()`; KHÔNG `createListResource`/axios. |
| (mới) | **THÊM** guard test: `shouldRedirectNotPermitted({ path: '/antmed/contracts/AM-HD-2026-00001' }, antmed())` === false; `crm()` === false; `outsider()` === true (route Detail qua cùng guard prefix). |

- `@/data/antmed` đã export `getContract` (KHÔNG cần thêm) — test có thể assert `dataSrc` chứa `export function getContract` + `antmed_crm.api.antmed.contract.get_contract` (đã có sẵn ở data layer M02-1a).

### 1ter.6 — DoD Slice M02-1b

- **BE**: `bench --site miyano run-tests --module antmed_crm.tests.test_antmed_contract` → **12/12 OK** (KHÔNG sửa BE, no-regression).
- **FE**: `cd frontend && yarn test` (vitest) xanh (đã đảo + thêm test); `yarn vue-tsc --noEmit` (typecheck) xanh; `yarn build` không lỗi mới (emit chunk `AntmedContractDetail*`).
- **Pixel (Playwright, sau USER reload)**: truy cập trực tiếp `http://miyano:8000/crm/antmed/contracts/<name>` → render header + bảng quota (bar màu đúng ngưỡng, chip khóa) — KHÔNG màn trắng, KHÔNG `Invalid Page`; items rỗng → empty-state; URL name sai → error-state + "Thử lại" (không stacktrace); từ list bấm dòng → điều hướng tới Detail (không dead-end); breadcrumb về list; 0 console error.

---

## 1quater. Slice M02-4 — Spec-contract FROZEN: widget "Top 10 Bệnh viện" (CEO) ✅

> 🟢 **DELTA 2026-06-17 (BA Bước 2 — vòng 10 factory, Slice M02-4):** thêm **endpoint MỚI** `top_hospitals` (BE) + **wire widget "Top 10 Bệnh viện"** vào `AntmedHome.vue` (Dashboard `/antmed`, mockup A1 line 261), thay **placeholder cũ** `AntmedPlaceholderPanel "Top 10 Bệnh viện theo doanh thu"` (AntmedHome.vue:99-104) bằng **card dữ liệu THẬT**. Đây là endpoint M02 đầu tiên ghi/đọc **gộp theo BV** (cross-HĐ). ADR mới: **ADR-M02-08** (chốt cách tính `health_color` cho widget).
>
> **Mục tiêu vòng**: bảng xếp hạng BV theo doanh thu HĐ (`SUM(total_value)`) + thanh % quota màu (green/warn/danger), wire qua endpoint MỚI `top_hospitals`, render trong card trên Dashboard CEO.
>
> **Boundaries** (dev KHÔNG suy diễn ngoài đây):
> - **Always**: 1 endpoint BE MỚI `top_hospitals` (RAW `{data, total_count}`, dùng `frappe.get_list` tôn trọng permission — BR-13, KHÔNG raw SQL) · 1 card widget trong `AntmedHome.vue` (thay placeholder Top 10 cũ) wire `getTopHospitals` (data/antmed.js MỚI) · helper bar màu **PURE** trong `utils/antmedUi.js` (tái dùng `healthBarClass`, KHÔNG tính ngưỡng lại ở FE) · tri-branch loading/error(nút Thử lại)/empty · drill-down `router.push({ name: 'AntmedHospitalDetail', params: { name: row.hospital } })` · test BE (module `test_antmed_contract`) + FE vitest mới · mọi nhãn qua `__()`.
> - **Ask-first**: muốn đổi cách tính revenue (vd chỉ HĐ docstatus=1, hay loại HĐ Hết hạn) → cần PM chốt rồi cập nhật ADR-M02-08; thêm filter kỳ/vùng (top bar mockup) → Slice riêng.
> - **Never**: KHÔNG hardcode mock data trong UI · KHÔNG `frappe.db.sql`/raw SQL bỏ qua permission (rò rỉ BR-13) · KHÔNG để FE tự tính ngưỡng màu hoặc sort lại (giữ thứ tự + cờ BE) · KHÔNG `createListResource`/axios/`.ts`/TanStack · KHÔNG đụng `get_contract`/`get_contract_health`/`list_quota_alerts` (no-regression) · KHÔNG endpoint envelope `_ok/_err`.

### 1quater.1 — Endpoint MỚI `top_hospitals` (FROZEN — APPEND vào `antmed_crm/api/antmed/contract.py`)

```python
@frappe.whitelist(methods=["GET"])
def top_hospitals(limit: int = 10) -> dict:
    """Xếp hạng BV theo doanh thu HĐ (widget "Top 10 Bệnh viện" — Dashboard CEO, mockup A1).

    Gộp theo hospital trên các HĐ user ĐỌC ĐƯỢC (frappe.get_list → tôn trọng DocPerm +
    permission_query_conditions BR-13, KHÔNG raw SQL):
      - revenue        = SUM(total_value) các HĐ của BV đó.
      - quota_used_pct = 100*SUM(used_qty)/SUM(quota_qty) trên TẤT CẢ dòng quota của
                         các HĐ thuộc BV (0.0 nếu BV chưa có quota / sum_quota==0).
      - health_color   = _health_color(quota_used_pct, days_to_expiry=None) — rank-by-revenue
                         KHÔNG xét hạn (ADR-M02-08) ⇒ chỉ ngưỡng quota: green ≤80 / orange >80–100 / red >100.
      - hospital_name  = resolve qua dotted-fetch (hospital.hospital_name).
    Trả RAW {data, total_count}. data sort GIẢM theo revenue, cắt tối đa `limit` dòng.
    total_count = số BV phân biệt trong scope (KHÔNG cắt limit) → drill "xem tất cả" về sau.
    Quota gộp BATCH (1 get_all theo parent IN names) — KHÔNG N+1.
    """
```

**Thuật toán (FROZEN):**
1. `limit = max(1, int(limit))` (chặn limit ≤ 0; mặc định 10).
2. Lấy HĐ trong scope: `rows = frappe.get_list(CONTRACT_DOCTYPE, fields=["name", "hospital", "hospital.hospital_name as hospital_name", "total_value"], limit_page_length=0)` — `limit_page_length=0` để gộp ĐỦ mọi HĐ (không bỏ sót BV); permission tự áp.
3. Gộp revenue theo `hospital`: `rev[h] += (total_value or 0)`; nhớ `name_map[h] = hospital_name` (lấy lần đầu, không None).
4. Gộp quota BATCH: `names = [r.name for r in rows]`; nếu `names` → `frappe.get_all(QUOTA_ITEM_DOCTYPE, filters={"parenttype": CONTRACT_DOCTYPE, "parentfield": "items", "parent": ("in", names)}, fields=["parent", "quota_qty", "used_qty"])`. Map `parent`(HĐ)→`hospital` (từ rows) rồi cộng dồn `sum_q[h] += quota_qty`, `sum_u[h] += used_qty`.
5. Với mỗi BV: `used_pct = round(100*sum_u[h]/sum_q[h], 2) if sum_q[h] else 0.0`; `health_color = _health_color(used_pct, None)`.
6. `data = [{hospital, hospital_name, revenue, quota_used_pct, health_color} for h in ...]`.
7. `total_count = len(data)` (số BV phân biệt, trước khi cắt).
8. Sort GIẢM theo `revenue` (tie-break ổn định: `(-revenue, hospital)` để output deterministic cho test); cắt `data = data[:limit]`.
9. `return {"data": data, "total_count": total_count}`.

> ⚠️ **Sort SAU khi tính total_count** rồi mới cắt limit → `total_count` = tổng BV trong scope (có thể > 10), còn `len(data) ≤ limit`. Đây là endpoint **xếp-hạng-cắt-top**, KHÔNG phải list phân trang ⇒ invariant **count == rows KHÔNG áp dụng** ở đây (rows bị cắt cố ý). Ghi rõ docstring để khỏi nhầm với `list_contracts`.

**Item shape (Hyrum — 5 key, FROZEN, FE bind trực tiếp):**

| Key | Kiểu | Ý nghĩa |
|---|---|---|
| `hospital` | str | PK BV (`AntMed Hospital.name`) — dùng cho drill-down `params.name` |
| `hospital_name` | str | Tên hiển thị BV |
| `revenue` | float | `SUM(total_value)` các HĐ của BV (VND) |
| `quota_used_pct` | float | `100*SUM(used_qty)/SUM(quota_qty)` (0.0 nếu chưa có quota), 2 chữ số thập phân |
| `health_color` | `'green'\|'orange'\|'red'` | Cờ màu thanh, do `_health_color(quota_used_pct, None)` quyết (BE owns ngưỡng) |

### 1quater.2 — FE data resource MỚI (`frontend/src/data/antmed.js`)

```js
/**
 * Top 10 Bệnh viện theo doanh thu (mockup A1 widget, M02-4) —
 *   antmed_crm.api.antmed.contract.top_hospitals.
 * BE: top_hospitals(limit=10) -> RAW dict bọc { data, total_count }.
 *   Mỗi item (Hyrum 5-key): hospital · hospital_name · revenue · quota_used_pct · health_color.
 *   data ĐÃ sort GIẢM theo revenue + cắt ≤ limit ở BE ⇒ FE KHÔNG sort lại.
 * ⚠️ Cùng idiom getContractHealth: list bọc dict → đọc r.data.data + r.data.total_count
 *    (createResource, KHÔNG createListResource).
 */
export function getTopHospitals({ params = {}, auto = false } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.contract.top_hospitals',
    params,        // { limit: 10 } mặc định (có thể bỏ — BE default 10)
    auto,
  })
}
```

### 1quater.3 — FE helper bar màu (TÁI DÙNG `utils/antmedUi.js`, KHÔNG thêm ngưỡng)

- FE **KHÔNG** tính ngưỡng quota — dùng cờ `health_color` BE trả. Map qua **`healthBarClass(healthColor)`** đã có (antmedUi.js:91 — `green→default(brand teal)` / `orange→warn(amber-500)` / `red→danger(red-600)`). Đây chính là helper PURE yêu cầu trong acceptance ("map theo health_color/ngưỡng BE qua helper PURE trong utils/antmedUi.js"). KHÔNG cần thêm hàm mới; nếu muốn alias rõ nghĩa có thể export `topHospitalBarClass = healthBarClass` (tùy chọn, không bắt buộc).
- Số `%` hiển thị cạnh bar = `row.quota_used_pct` (format `{{ row.quota_used_pct }}%`).

### 1quater.4 — Wire widget vào `AntmedHome.vue` (thay placeholder Top 10 cũ)

- **Thay** block `AntmedPlaceholderPanel title="Top 10 Bệnh viện theo doanh thu"` (AntmedHome.vue:99-104) bằng **1 card widget** mới (giữ `<section class="grid grid-cols-1 gap-4" :aria-label="__('Xếp hạng bệnh viện')">` làm container — tái dùng row 2 12-col).
- Card: tiêu đề **'Top 10 Bệnh viện'** (khớp mockup A1 line 261, KHÔNG "…theo doanh thu") + bảng **3 cột**: **BV** (`hospital_name`) | **DT** (`revenue`, format `formatVnMoney`) | **Quota** (`<div class="bar [healthBarClass]"><i :style="width: pct%">` + số `%` cạnh bar).
- Tái dùng token màu/card/bar hiện có (`BAR_THEME`/`barFillClass` qua `healthBarClass`; class card `rounded-xl bg-surface-white …` như panel khác). KHÔNG hardcode mock.
- **Fetch ĐỘC LẬP** (như `quotaSummary`): `const topHospitals = getTopHospitals({ auto: true, onError(err){ toast.error(...) } })`. Đọc `topHospitals.data?.data` (list) + `topHospitals.data?.total_count`.
- **Tri-branch trong card** (KHÔNG dùng tri-branch chung của `overview`): `topHospitals.loading` → spinner "Đang tải…"; `topHospitals.error` → "Không tải được" + `Button "Thử lại"` `@click="topHospitals.reload()"`; data rỗng (`!list.length`) → empty **'Chưa có dữ liệu bệnh viện'**.
- **Drill-down**: mỗi dòng `<tr>` `cursor-pointer` + `role="link"` + `tabindex="0"` + `@click="openHospital(row.hospital)"` + `@keydown.enter="openHospital(row.hospital)"` + `:aria-label="__('Xem chi tiết bệnh viện') + ' ' + row.hospital_name"`; `openHospital(name){ router.push({ name: 'AntmedHospitalDetail', params: { name } }) }` (route `AntmedHospitalDetail` `/antmed/hospitals/:name` **ĐÃ CÓ** router.js:161-164 — verify trước khi code, KHÔNG tạo route mới).
- **FE KHÔNG sort lại** — render theo thứ tự BE trả. Bar width = `quota_used_pct` (clamp 0–100 ở style nếu >100 để bar không tràn; màu đã là red khi >100).

### 1quater.5 — Test (BẮT BUỘC xanh THẬT)

**BE** (`antmed_crm/tests/test_antmed_contract.py` — APPEND test mới, KHÔNG sửa 12 test cũ):
- `test_top_hospitals_shape`: trả dict có `data`(list) + `total_count`(int); mỗi item đúng 5 key (`hospital`/`hospital_name`/`revenue`/`quota_used_pct`/`health_color`).
- `test_top_hospitals_sort_desc_revenue`: tạo ≥3 BV với revenue khác nhau → `data` sort GIẢM theo `revenue` (assert `revenue[i] >= revenue[i+1]`).
- `test_top_hospitals_limit`: tạo ≥11 BV có HĐ → `len(data) == 10` khi `limit` mặc định; `total_count >= 11`; `top_hospitals(limit=3)` → `len(data)==3`.
- `test_top_hospitals_aggregate_by_bv`: 1 BV có ≥2 HĐ → `revenue` = tổng `total_value`; `quota_used_pct` = `100*sum(used)/sum(quota)` gộp mọi dòng quota của mọi HĐ BV đó.
- `test_top_hospitals_health_color`: used_pct ≤80 → `green`; 80<pct≤100 → `orange`; pct>100 → `red`; BV không quota → `quota_used_pct==0.0` & `health_color=='green'`.
- `test_top_hospitals_empty`: scope rỗng (hoặc user noperm) → `{"data": [], "total_count": 0}` (fail-closed, dùng `get_list` — KHÔNG raw SQL).
- `test_top_hospitals_respects_permission` (data-scope BR-13): user chỉ thấy BV được giao → BV ngoài scope KHÔNG xuất hiện trong `data`; KHÔNG `frappe.db.sql`.

**FE** (`frontend/tests/unit/antmedHome.test.js` MỚI hoặc bổ sung file Home hiện có):
- `data/antmed` export `getTopHospitals`; url == `antmed_crm.api.antmed.contract.top_hospitals`.
- `AntmedHome.vue` import `getTopHospitals`, đọc `r.data.data` (KHÔNG `r.data` trực tiếp cho list), gọi `healthBarClass` cho bar; có drill-down `router.push name 'AntmedHospitalDetail' params {name: row.hospital}`.
- KHÔNG còn `AntmedPlaceholderPanel "Top 10"` trong source (assert đã thay).
- Tri-branch: source có nhánh `loading`/`error`(Thử lại)/empty('Chưa có dữ liệu bệnh viện').
- KHÔNG `antmed_crm.api` sai prefix / axios / `createListResource` / tự tính ngưỡng (`>= 70`/`>= 90`/`>= 95` literal) trong `AntmedHome.vue`.
- `healthBarClass` behavior (PURE): `green→bg-...(default)` / `orange→bg-amber-500` / `red→bg-red-600` (đã có test antmedUi — bổ sung nếu thiếu).

### 1quater.6 — DoD Slice M02-4

- **BE**: `bench --site miyano run-tests --module antmed_crm.tests.test_antmed_contract` → `Ran N OK` (12 cũ + ~7 mới `top_hospitals`).
- **FE**: `cd frontend && yarn test` (vitest) file Home pass; `yarn build` ✓ (chunk `AntmedHome*` re-emit).
- **Invariant data-scope (BR-13)**: BV/HĐ chỉ tính dưới permission user (`frappe.get_list`, KHÔNG raw SQL) — verify ở `test_top_hospitals_respects_permission`.
- **Pixel (Playwright, sau USER reload)**: `/antmed` (hoặc `/crm/antmed`) render thêm card 'Top 10 Bệnh viện' (3 cột BV|DT|Quota bar màu + số %), thứ tự giảm theo DT, bấm dòng → `/antmed/hospitals/<name>` (không dead-end); scope rỗng → empty 'Chưa có dữ liệu bệnh viện'; 0 console error.

---

## 1quint. Slice M02-5 — Spec-contract FROZEN: widget "Danh mục VT trúng thầu — top 5" (CEO) ✅

> 🟢 **DELTA 2026-06-17 (BA Bước 2 — vòng 11 factory, Slice M02-5):** thêm **endpoint MỚI** `top_quota_items(limit=5)` (BE — APPEND `contract.py`) + **wire widget "Danh mục VT trúng thầu — top 5"** vào **chân màn** `AntmedContractHealth.vue` (route `/antmed/contract-health`, mockup A2 id=ceo), card MỚI **dưới** bảng "Sức khỏe HĐ". Đây là endpoint M02 đầu tiên gộp **cross-contract theo `item` (SKU)** (khác `top_hospitals` gộp theo BV). Kèm **BE cleanup** gỡ `top_hospitals` định nghĩa trùng (ADR-M02-10). ADR mới: **ADR-M02-10** (cleanup) + **ADR-M02-11** (gộp-theo-item, count==rows N/A).
>
> **Mục tiêu vòng**: bảng top SKU theo **% quota đã dùng** (cross-contract rollup) ở chân màn Sức khỏe HĐ; wire qua endpoint MỚI `top_quota_items`; render trong card MỚI; route `/antmed/contract-health` mở trong `AntmedLayout` (KHÔNG vào màn CRM gốc).
>
> **Boundaries** (dev KHÔNG suy diễn ngoài đây):
> - **Always**: 1 endpoint BE MỚI `top_quota_items(limit=5)` (RAW `{data, total_count}`, `frappe.get_list` tôn trọng permission — BR-13, KHÔNG raw SQL, fail-closed) · 1 card widget MỚI **dưới** bảng trong `AntmedContractHealth.vue` (KHÔNG đụng bảng Sức khỏe HĐ hiện có) wire `getTopQuotaItems` (data/antmed.js MỚI) · bar màu qua `healthBarClass` đã có (PURE, tái dùng — KHÔNG tính ngưỡng/sort lại ở FE) · fetch **ĐỘC LẬP** với `getContractHealth` (lỗi 1 cái không vỡ cái kia) · tri-branch loading/error(nút Thử lại reload)/empty · test BE (module `test_antmed_contract`) + FE vitest mới · mọi nhãn qua `__()` · **BE cleanup** gỡ `top_hospitals` trùng + test trùng tên (ADR-M02-10).
> - **Ask-first**: đổi cách gộp `used_pct` (vd weighted theo `unit_price`, hay chỉ HĐ `docstatus=1`) → cần PM chốt rồi cập nhật ADR-M02-11; thêm cột đơn giá/HĐ vào card → Slice riêng; thêm drill-down từ SKU → màn item (M03 chưa land route) → defer.
> - **Never**: KHÔNG hardcode mock data trong UI · KHÔNG `frappe.db.sql`/raw SQL bỏ permission (rò rỉ BR-13) · KHÔNG để FE tự đặt ngưỡng màu hoặc sort lại (giữ thứ tự + cờ BE) · KHÔNG `createListResource`/axios/`.ts`/TanStack · KHÔNG đụng `get_contract`/`get_contract_health`/`list_quota_alerts`/`top_hospitals` (no-regression hành vi) · KHÔNG endpoint envelope `_ok/_err` · KHÔNG để fetch widget này làm vỡ bảng Sức khỏe HĐ (2 resource độc lập).

### 1quint.1 — Endpoint MỚI `top_quota_items` (FROZEN — APPEND vào `antmed_crm/api/antmed/contract.py`)

```python
@frappe.whitelist(methods=["GET"])
def top_quota_items(limit: int = 5) -> dict:
    """Xếp hạng SKU theo % quota đã dùng — gộp CROSS-CONTRACT theo item
    (widget "Danh mục VT trúng thầu — top 5", chân màn /antmed/contract-health, mockup A2 CEO).

    Gộp theo `item` trên các dòng quota của các HĐ user ĐỌC ĐƯỢC (frappe.get_list lấy HĐ
    trong scope → tôn trọng DocPerm + permission_query_conditions BR-13, KHÔNG raw SQL):
      - quota_qty = SUM(quota_qty) các dòng quota cùng item (mọi HĐ trong scope).
      - used_qty  = SUM(used_qty)  các dòng quota cùng item (mọi HĐ trong scope).
      - used_pct  = 100*SUM(used_qty)/SUM(quota_qty)  (0.0 nếu SUM(quota_qty)==0 — fail-safe, KHÔNG chia 0).
      - health_color = _health_color(used_pct, None) — tái dùng (ADR-M02-11/ADR-M02-08): green ≤80 / orange >80–100 / red >100.
      - item_name = lấy lần đầu gặp (dòng quota lưu sẵn item_name; fallback item nếu trống).
    Trả RAW {data, total_count}. data sort GIẢM theo used_pct, cắt tối đa `limit` dòng (mặc định 5).
    total_count = số SKU phân biệt trong scope (KHÔNG cắt limit). Quota gộp BATCH (1 get_all
    theo parent IN names) — KHÔNG N+1.

    Fail-closed BR-13: user KHÔNG read-perm AntMed Contract → get_list raise PermissionError →
    trả {"data": [], "total_count": 0} (KHÔNG rò, KHÔNG leak). Endpoint xếp-hạng-cắt-top ⇒
    invariant count==rows KHÔNG áp dụng (ADR-M02-11).
    """
```

**Thuật toán (FROZEN):**
1. `limit = max(1, int(limit))` (chặn limit ≤ 0; mặc định 5).
2. Lấy HĐ trong scope: `rows = frappe.get_list(CONTRACT_DOCTYPE, fields=["name"], limit_page_length=0)` (chỉ cần `name` — quota gộp theo item KHÔNG cần field HĐ khác). **Bọc `try/except frappe.PermissionError` → trả `{"data": [], "total_count": 0}`** (fail-closed, mirror `top_hospitals` bản giữ).
3. `names = [r["name"] for r in rows]`; nếu rỗng → trả `{"data": [], "total_count": 0}`.
4. Gộp quota BATCH theo `item`: `frappe.get_all(QUOTA_ITEM_DOCTYPE, filters={"parenttype": CONTRACT_DOCTYPE, "parentfield": "items", "parent": ("in", names)}, fields=["item", "item_name", "quota_qty", "used_qty"])`. Bỏ dòng `item` trống. Cộng dồn `sum_q[item] += quota_qty`, `sum_u[item] += used_qty`; nhớ `name_map[item] = item_name` (lấy lần đầu, không None).
5. Với mỗi SKU: `used_pct = round(100*sum_u[item]/sum_q[item], 2) if sum_q[item] else 0.0`; `health_color = _health_color(used_pct, None)`.
6. `data = [{item, item_name, quota_qty, used_qty, used_pct, health_color} for item in ...]`.
7. `total_count = len(data)` (số SKU phân biệt, TRƯỚC khi cắt).
8. Sort GIẢM theo `used_pct` (tie-break ổn định: `(-used_pct, item)` để output deterministic cho test); cắt `data = data[:limit]`.
9. `return {"data": data, "total_count": total_count}`.

> ⚠️ **Sort SAU khi tính `total_count`** rồi mới cắt limit → `total_count` = tổng SKU trong scope (có thể > 5), `len(data) ≤ limit`. Endpoint **xếp-hạng-cắt-top** (như `top_hospitals`) ⇒ invariant **count == rows KHÔNG áp dụng** ở đây (rows cắt cố ý). Ghi rõ docstring (ADR-M02-11).

**Item shape (Hyrum — 6 key, FROZEN, FE bind trực tiếp):**

| Key | Kiểu | Ý nghĩa | Cột mockup A2 |
|---|---|---|---|
| `item` | str | Mã SKU (`AntMed Quota Item.item`) — `item_code` hiển thị | SKU (item_code · item_name) |
| `item_name` | str | Tên VTYT (fallback `item` nếu trống) | SKU (item_code · item_name) |
| `quota_qty` | float | `SUM(quota_qty)` cross-contract (tổng hạn mức trúng thầu) | Quota |
| `used_qty` | float | `SUM(used_qty)` cross-contract (đã xuất) | Đã xuất |
| `used_pct` | float | `100*SUM(used_qty)/SUM(quota_qty)` (0.0 nếu SUM quota==0), 2 chữ số thập phân | % (bar + số %) |
| `health_color` | `'green'\|'orange'\|'red'` | Cờ màu thanh, `_health_color(used_pct, None)` (BE owns ngưỡng) | % (màu bar) |

### 1quint.2 — FE data resource MỚI (`frontend/src/data/antmed.js`)

```js
/**
 * Danh mục VT trúng thầu — top 5 theo % quota đã dùng (mockup A2 widget chân màn
 * contract-health, M02-5) — antmed_crm.api.antmed.contract.top_quota_items.
 * BE: top_quota_items(limit=5) -> RAW dict bọc { data, total_count }.
 *   Mỗi item (Hyrum 6-key): item · item_name · quota_qty · used_qty · used_pct · health_color.
 *   data ĐÃ gộp cross-contract theo item + sort GIẢM theo used_pct + cắt ≤ limit ở BE ⇒ FE KHÔNG sort lại.
 *   total_count = số SKU phân biệt trong scope (xếp-hạng-cắt-top ⇒ có thể > len(data); ADR-M02-11).
 *
 * ⚠️ Cùng idiom getContractHealth: list bọc dict → đọc r.data.data + r.data.total_count
 *    (createResource, KHÔNG createListResource). Gộp DƯỚI permission (get_list, BR-13) →
 *    noperm/scope rỗng → { data: [], total_count: 0 } (fail-closed).
 *
 * @param {object} [opts]
 * @param {object} [opts.params] - { limit: 5 } mặc định (bỏ được — BE default 5).
 * @param {boolean} [opts.auto] - auto-fetch.
 */
export function getTopQuotaItems({ params = {}, auto = false } = {}) {
  return createResource({
    url: 'antmed_crm.api.antmed.contract.top_quota_items',
    params,
    auto,
  })
}
```

### 1quint.3 — FE helper bar màu (TÁI DÙNG `utils/antmedUi.js`, KHÔNG thêm ngưỡng)

- FE **KHÔNG** tính ngưỡng quota — dùng cờ `health_color` BE trả. Map qua **`healthBarClass(healthColor)`** đã có (antmedUi.js:91 — `green→default(brand teal)` / `orange→warn(amber-500)` / `red→danger(red-600)`). Đây chính là helper PURE yêu cầu trong acceptance ("Bar màu dùng `health_color` BE map qua `healthBarClass` đã có"). **KHÔNG** thêm hàm mới, **KHÔNG** literal ngưỡng (`>=70`/`>=90`/`>=95`) trong component.
- Số `%` hiển thị cạnh bar = `row.used_pct` (format `{{ Math.round(row.used_pct) }}%`); width bar = `used_pct` clamp 0–100 (style) để >100% không tràn (màu đã là red khi >100).

### 1quint.4 — Wire widget vào CHÂN màn `AntmedContractHealth.vue`

- **Vị trí**: card MỚI đặt **DƯỚI** `<table>` Sức khỏe HĐ (sau dòng "Tổng cộng … hợp đồng" @AntmedContractHealth.vue:180-186), **TRONG** `<section class="flex-1 overflow-auto px-6 pb-6">` hiện có (hoặc thêm 1 block riêng cuối `<section>`). KHÔNG đụng bảng Sức khỏe HĐ hiện có.
- **Tiêu đề card**: **'Danh mục VT trúng thầu — top 5'** (khớp mockup A2). Bảng **4 cột** (mockup A2):
  1. **SKU** — `{{ row.item }} · {{ row.item_name }}` (item_code · item_name).
  2. **Quota** — `row.quota_qty` (tabular-nums).
  3. **Đã xuất** — `row.used_qty` (tabular-nums).
  4. **%** — `<div class="bar"><i :class="healthBarClass(row.health_color)" :style="width: clamp(used_pct)%">` + số `%` cạnh bar (`Math.round(row.used_pct)%`), `role="progressbar"` `aria-valuenow`.
- Tái dùng token màu/card/bar hiện có (`healthBarClass` đã import; class card/bar như block "Sức khỏe HĐ"). KHÔNG hardcode mock.
- **Fetch ĐỘC LẬP** với `getContractHealth`: `const topQuotaItems = getTopQuotaItems({ params: { limit: 5 }, auto: true })`. Đọc `topQuotaItems.data?.data` (list) + `topQuotaItems.data?.total_count`. **2 resource tách biệt** — `health.error` KHÔNG ảnh hưởng card này và ngược lại (acceptance: "fetch ĐỘC LẬP với bảng getContractHealth — lỗi 1 cái không vỡ cái kia").
- **Tri-branch RIÊNG trong card** (KHÔNG dùng tri-branch chung của `health`):
  - `topQuotaItems.loading` → spinner "Đang tải…".
  - `topQuotaItems.error` → "Không tải được" + `Button "Thử lại"` `@click="topQuotaItems.reload()"`.
  - data rỗng (`!list.length`) → empty **'Chưa có vật tư trúng thầu'**.
- **FE KHÔNG sort lại** — render theo thứ tự BE (đã sort GIẢM `used_pct`). **KHÔNG** drill-down ở slice này (route màn item M03 chưa có) — chỉ là bảng đọc.
- Surface lỗi BR-XX/permission qua `topQuotaItems.onError` (toast) độc lập, không dùng chung `health.onError`.

### 1quint.5 — BE cleanup BẮT BUỘC (ADR-M02-10) — gỡ `top_hospitals` + test trùng

> Vòng 10 land 2 lần `def top_hospitals` trong `antmed_crm/api/antmed/contract.py` (dòng ~262 và ~443) — Python chỉ giữ **def cuối** (line 443), def đầu là **dead code gây nhầm**. Tương tự `test_antmed_contract.py` có `test_top_hospitals_*` trùng tên trong cả `TestAntMedContract` (line ~306) lẫn `TestAntMedTopHospitals` (line ~543).

- **`contract.py`**: GIỮ **1** `def top_hospitals` = bản **fail-closed** (`try/except frappe.PermissionError → {"data": [], "total_count": 0}`, `name_map[h] = hospital_name` KHÔNG `or h`) — đây là bản đúng theo acceptance M02-4 ("fail-closed"). XOÁ def đầu (không try/except). Sau cleanup file chỉ còn **1** `top_hospitals` + **1** `top_quota_items`; `grep -c "^def top_hospitals" → 1`.
- **`test_antmed_contract.py`**: gỡ các `test_top_hospitals_*` **trùng tên** giữa 2 class. Giữ bộ test ở **`TestAntMedTopHospitals`** (class chuyên, có `setUpClass` build fixture riêng) — xoá các `test_top_hospitals_*` định nghĩa lại trong `TestAntMedContract` (line ~306–~440) NẾU trùng tên/ý nghĩa (tránh che khuất + chạy 2 lần fixture khác nhau). *(BE dev xác nhận bằng `grep -n "def test_top_hospitals" test_antmed_contract.py` còn mỗi tên 1 lần.)*
- **DoD cleanup**: sau gỡ, `bench --site miyano run-tests --module antmed_crm.tests.test_antmed_contract` vẫn `Ran N OK`; `top_hospitals` + `top_quota_items` đều import/resolve đúng (smoke gọi qua `frappe.get_attr("antmed_crm.api.antmed.contract.top_hospitals")` không lỗi).

### 1quint.6 — Test (BẮT BUỘC xanh THẬT)

**BE** (`antmed_crm/tests/test_antmed_contract.py` — APPEND test mới cho `top_quota_items`; KHÔNG sửa logic test cũ ngoài việc gỡ trùng tên §1quint.5):
- `test_top_quota_items_shape`: trả dict có `data`(list) + `total_count`(int); mỗi item đúng 6 key (`item`/`item_name`/`quota_qty`/`used_qty`/`used_pct`/`health_color`).
- `test_top_quota_items_sort_desc_used_pct`: tạo ≥3 SKU với `used_pct` khác nhau → `data` sort GIẢM theo `used_pct` (assert `used_pct[i] >= used_pct[i+1]`).
- `test_top_quota_items_limit`: tạo ≥6 SKU → `len(data) == 5` khi `limit` mặc định; `total_count >= 6`; `top_quota_items(limit=3)` → `len(data)==3`.
- `test_top_quota_items_cross_contract_rollup`: 1 SKU xuất hiện ở ≥2 HĐ → `quota_qty`=tổng quota, `used_qty`=tổng used, `used_pct = 100*SUM(used)/SUM(quota)` gộp mọi dòng quota cùng item của các HĐ trong scope (assert gộp ĐÚNG, không tính riêng từng HĐ).
- `test_top_quota_items_zero_quota_failsafe`: SKU có `SUM(quota_qty)==0` → `used_pct == 0.0` (KHÔNG `ZeroDivisionError`).
- `test_top_quota_items_health_color`: used_pct ≤80 → `green`; 80<pct≤100 → `orange`; pct>100 → `red`.
- `test_top_quota_items_empty_fail_closed`: scope rỗng (hoặc user noperm) → `{"data": [], "total_count": 0}` (fail-closed, dùng `get_list` — KHÔNG raw SQL).
- `test_top_quota_items_respects_permission` (data-scope BR-13): user chỉ thấy BV/HĐ được giao → SKU CHỈ thuộc HĐ ngoài scope KHÔNG xuất hiện; SKU dùng chung được gộp CHỈ phần quota của HĐ trong scope; KHÔNG `frappe.db.sql` (test chứng minh không rò: tổng `used_qty` chỉ từ HĐ user đọc được).
- *(cleanup §1quint.5)* sau gỡ trùng: `top_hospitals` test vẫn xanh; KHÔNG còn 2 def `test_top_hospitals_*` cùng tên trong cùng/khác class gây che khuất.

**FE** (`frontend/tests/unit/antmedContractHealth.test.js` bổ sung, HOẶC file mới `antmedTopQuotaItems.test.js`):
- `data/antmed` export `getTopQuotaItems`; url == `antmed_crm.api.antmed.contract.top_quota_items`.
- `AntmedContractHealth.vue` import `getTopQuotaItems`, đọc `r.data.data` (KHÔNG `r.data` trực tiếp cho list), gọi `healthBarClass(row.health_color)` cho bar.
- Source có card tiêu đề `'Danh mục VT trúng thầu — top 5'` + 4 cột SKU/Quota/Đã xuất/% (assert text/binding `item`/`item_name`/`quota_qty`/`used_qty`/`used_pct`).
- Tri-branch RIÊNG: source có nhánh `topQuotaItems.loading`/`topQuotaItems.error`(Thử lại → `topQuotaItems.reload()`)/empty('Chưa có vật tư trúng thầu'); **fetch độc lập** (2 resource tách: `health` + `topQuotaItems`).
- KHÔNG `antmed_crm.api` sai prefix / axios / `createListResource` / tự đặt ngưỡng (`>= 70`/`>= 90`/`>= 95` literal) / `.sort(` trên list quota-items trong `AntmedContractHealth.vue`.
- `healthBarClass` behavior (PURE) đã có test ở `antmedUi.test.js` — bổ sung nếu thiếu.

### 1quint.7 — DoD Slice M02-5

- **Cleanup (ADR-M02-10)**: `grep -c "^def top_hospitals" antmed_crm/api/antmed/contract.py` == **1**; `grep -c "^def top_quota_items" …` == **1**; `grep -c "def test_top_hospitals" antmed_crm/tests/test_antmed_contract.py` — mỗi tên còn 1 (không trùng).
- **BE**: `bench --site miyano run-tests --module antmed_crm.tests.test_antmed_contract` → `Ran N OK` (test cũ giữ xanh + ~8 mới `top_quota_items`); `top_hospitals` + `top_quota_items` đều resolve.
- **FE**: `cd frontend && yarn test` (vitest) file mới/bổ sung pass; `yarn build` ✓ (chunk `AntmedContractHealth*` re-emit).
- **Invariant data-scope (BR-13)**: SKU/quota chỉ gộp dưới permission user (`frappe.get_list`, KHÔNG raw SQL) — verify ở `test_top_quota_items_respects_permission` (chứng minh không rò: SKU/quota ngoài scope không lọt).
- **Pixel (Playwright, sau USER reload)**: `/antmed/contract-health` mở trong `AntmedLayout` (KHÔNG vào màn CRM gốc); **dưới** bảng Sức khỏe HĐ xuất hiện card 'Danh mục VT trúng thầu — top 5' (4 cột SKU|Quota|Đã xuất|% bar màu + số %), thứ tự giảm theo %; scope rỗng → empty 'Chưa có vật tư trúng thầu'; lỗi bảng Sức khỏe HĐ KHÔNG làm vỡ card này (và ngược lại); 0 console error.

---

## 1sext. Slice M02-7 — Spec-contract FROZEN: widget "Cơ cấu doanh thu" (CEO) ✅

> 🟢 **DELTA 2026-06-18 (BA Bước 2 — vòng 15 factory, Slice M02-7):** thêm **endpoint MỚI** `revenue_mix()` (BE — APPEND `contract.py`) + **wire widget "Cơ cấu doanh thu"** vào `AntmedHome.vue` (Dashboard `/antmed` CEO, mockup A2 id=ceo), card MỚI **cùng hàng / ngay sau** "Top 10 Bệnh viện". Đây là endpoint M02 đầu tiên gộp **theo `classification` của `AntMed Item`** (cross-contract, qua resolve `item` (SKU) → `AntMed Item.classification`). ADR mới: **ADR-M02-12** (rollup theo classification + nhóm 'Khác' loại khỏi `total_revenue`) + **ADR-M02-13** (tái dùng `formatVnMoney`, KHÔNG đẻ formatter 'triệu' verbose).

> **Mục tiêu vòng**: bảng cơ cấu doanh thu theo 4 nhóm phân loại VTYT (Loại A/B/C/D), `revenue = SUM(used_qty × unit_price)` gộp cross-contract theo classification; mỗi dòng kèm `pct` tỷ trọng + bar màu brand width=`pct%`; render card trên Dashboard CEO `/antmed` ngay sau Top 10.

### Boundaries (Always / Ask-first / Never)
> - **Always**: 1 endpoint BE MỚI `revenue_mix()` (RAW `{data, total_revenue}`; `data` **đúng 4 phần tử cố định A→B→C→D**; `frappe.get_list` tôn trọng permission — BR-13 fail-closed, KHÔNG raw SQL; resolve item→classification **BATCH 1 query**, KHÔNG N+1) · 1 card widget MỚI trong `AntmedHome.vue` **cùng hàng / ngay sau** Top 10 (tái dùng token card/bar mockup A2) wire `getRevenueMix` (data/antmed.js MỚI) fetch **ĐỘC LẬP** với `getTopHospitals` · tiền VI gọn qua `formatVnMoney` đã có (tái dùng — ADR-M02-13) · bar width=`pct%` màu brand qua helper **PURE** `revenueMixBarStyle` trong `utils/antmedUi.js` (KHÔNG sort/tính lại FE) · tri-branch loading/error(nút Thử lại reload)/empty (`total_revenue==0`) · test BE (module `test_antmed_contract`, class MỚI `TestAntMedRevenueMix`) + FE vitest mới · mọi nhãn qua `__()`.
> - **Ask-first**: đổi nguồn classification (vd thêm "Loại E" hoặc gộp theo `am_item_group` khác) → cần PM chốt rồi cập nhật ADR-M02-12 + Select option `AntMed Item.classification`; đổi `revenue` sang `quota_qty × unit_price` (giá trị trúng thầu) thay vì `used_qty × unit_price` (đã tiêu thụ) → cần PM chốt; thêm filter kỳ/quý → Slice riêng; render nhóm 'Khác' thành dòng thứ 5 → cần PM chốt (mặc định LOẠI khỏi 4 dòng & total).
> - **Never**: KHÔNG hardcode mock data trong UI · KHÔNG `frappe.db.sql`/raw SQL bỏ permission (rò rỉ BR-13) · KHÔNG N+1 (1 query gộp item→classification) · KHÔNG để FE tự đặt màu/sort hay đổi thứ tự A→B→C→D (BE trả cố định 4 dòng) · KHÔNG bỏ dòng lớp revenue=0 (luôn render đủ 4) · KHÔNG cộng nhóm 'Khác' vào `total_revenue` · KHÔNG `createListResource`/axios/`.ts`/TanStack · KHÔNG đụng `top_hospitals`/`top_quota_items`/`get_contract*`/`list_quota_alerts` (no-regression) · KHÔNG endpoint envelope `_ok/_err` · KHÔNG để fetch widget này làm vỡ card Top 10 (2 resource độc lập).

### 1sext.1 — Endpoint MỚI `revenue_mix` (FROZEN — APPEND vào `antmed_crm/api/antmed/contract.py`)

```python
# 4 lớp phân loại VTYT cố định (= Select options AntMed Item.classification). THỨ TỰ A→B→C→D
# load-bearing (FE bind theo index/thứ tự, mockup A2). KHÔNG đổi/đảo. Nhãn = chính classification.
REVENUE_MIX_CLASSES = ("Loại A", "Loại B", "Loại C", "Loại D")


@frappe.whitelist(methods=["GET"])
def revenue_mix() -> dict:
    """Cơ cấu doanh thu theo nhóm phân loại VTYT (widget "Cơ cấu doanh thu" — Dashboard CEO,
    mockup A2 id=ceo, Slice M02-7). KHÔNG DocType mới, KHÔNG module mới.

    Gộp CROSS-CONTRACT theo `classification` của AntMed Item trên các HĐ user ĐỌC ĐƯỢC
    (frappe.get_list → tôn trọng DocPerm + permission_query_conditions BR-13, KHÔNG raw SQL):
      - revenue (mỗi lớp) = SUM(used_qty × unit_price) trên TẤT CẢ dòng AntMed Quota Item
                            (mọi HĐ trong scope) có `item` (SKU) thuộc classification đó.
      - item thiếu classification (hoặc SKU không tồn tại trong AntMed Item) → gộp nhóm 'Khác'
        → KHÔNG render trong 4 dòng chuẩn & KHÔNG cộng vào total_revenue (ADR-M02-12).
      - total_revenue = SUM revenue của ĐÚNG 4 lớp A–D (để Σpct ~100%); KHÔNG gồm 'Khác'.
      - pct = round(100 * revenue / total_revenue, 1) nếu total_revenue > 0 ELSE 0.0
              (total==0 ⇒ MỌI pct=0.0 — KHÔNG ZeroDivisionError).

    Trả RAW {data, total_revenue}. `data` = ĐÚNG 4 phần tử cố định thứ tự A→B→C→D
    (kể cả lớp revenue=0 vẫn xuất hiện — KHÔNG bỏ dòng). Mỗi dòng 4-key (FROZEN Hyrum §1sext.shape):
      classification (str: "Loại A".. "Loại D") · label (str = classification) · revenue (float) · pct (float).

    Resolve item→classification BATCH (1 frappe.get_all theo item_code IN skus) — KHÔNG N+1.

    Fail-closed BR-13: user KHÔNG read-perm AntMed Contract → frappe.get_list raise
    PermissionError → trả {"data": [4 dòng A–D revenue=0/pct=0], "total_revenue": 0.0}
    (KHÔNG raise ra ngoài, KHÔNG leak stacktrace).
    """
```

**Thuật toán (FROZEN — dev triển khai đúng các bước; KHÔNG raw SQL, KHÔNG N+1):**
1. **HĐ trong scope** (fail-closed): `try: contracts = frappe.get_list(CONTRACT_DOCTYPE, fields=["name"], limit_page_length=0)` — `except frappe.PermissionError: return _empty_revenue_mix()` (helper trả 4 dòng A–D revenue=0/pct=0, total_revenue=0.0). Nếu `not contracts` → cũng trả `_empty_revenue_mix()` (4 dòng 0).
2. **Gộp quota theo SKU** (BATCH `get_all` theo `parent IN names`): với mỗi dòng `AntMed Quota Item` lấy `item, used_qty, unit_price` → `rev_by_sku[item] += (used_qty or 0) * (unit_price or 0)`. Dòng quota thiếu `item` → bỏ (không gộp vào None). 1 query.
3. **Map SKU→classification BATCH 1 query**: `skus = list(rev_by_sku)`; nếu `skus`: `for it in frappe.get_all("AntMed Item", filters={"item_code": ("in", skus)}, fields=["item_code", "classification"]): cls_by_sku[it.item_code] = it.classification`. *(Lưu ý `AntMed Quota Item.item` = `Data` chứa **item_code** — autoname `AntMed Item` = `field:item_code`, ADR-M02-12.)* **`ignore_permissions=True`** cho query metadata classification (lý do + rủi ro: ADR-M02-12 §Consequences) — vì BR-13 fail-closed đã chốt **trên `AntMed Contract`**; classification là metadata tham chiếu, KHÔNG phải dữ liệu phạm vi NV.
4. **Cộng revenue theo lớp**: khởi tạo `rev_by_cls = {c: 0.0 for c in REVENUE_MIX_CLASSES}` + `other = 0.0`. Với mỗi `sku, rev` trong `rev_by_sku`: `cls = cls_by_sku.get(sku)`; nếu `cls in rev_by_cls` → `rev_by_cls[cls] += rev`; ELSE → `other += rev` (gồm SKU thiếu classification HOẶC không tồn tại trong AntMed Item). `other` KHÔNG vào output, KHÔNG vào total.
5. **total_revenue** = `sum(rev_by_cls.values())` (chỉ 4 lớp A–D).
6. **Build `data` cố định thứ tự**: `data = [{"classification": c, "label": c, "revenue": rev_by_cls[c], "pct": round(100*rev_by_cls[c]/total_revenue, 1) if total_revenue else 0.0} for c in REVENUE_MIX_CLASSES]`.
7. `return {"data": data, "total_revenue": total_revenue}`.

> ⚠️ Endpoint **KHÔNG cắt-top, KHÔNG phân trang** → `data` LUÔN đúng 4 dòng. Invariant `count==rows` của `list_contracts` KHÔNG áp dụng kiểu list (4 dòng cố định ≠ số bản ghi); nhưng **data-scope BR-13 vẫn áp**: revenue chỉ cộng từ HĐ user đọc được (test `respects_permission`).

### 1sext.2 — FE data resource MỚI (`frontend/src/data/antmed.js`)

```js
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
 * ⚠️⚠️ BẮT BUỘC `method: 'GET'` (xem §1sext.bis). `revenue_mix()` KHÔNG có params → frappe-ui
 *    createResource MẶC ĐỊNH gửi **POST** → BE `@frappe.whitelist(methods=["GET"])` reject **403
 *    "Not permitted"** (đã quan sát LIVE ở M02-4/M03-1/M02-5 — USER eval R11). PHẢI set method:'GET'.
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
```

### 1sext.bis — Self-Correction (ADR-M02-14): defect verb POST→403 systemic ở data/antmed.js
> 🔴 **Lỗi thiết kế gốc đã quan sát LIVE (USER eval R11, tái diễn từ M02-4 + M03-1):** mọi `createResource` trong `frontend/src/data/antmed.js` **KHÔNG set `method`** → frappe-ui mặc định **POST** khi không có params → BE `@frappe.whitelist(methods=["GET"])` trả **403 "Not permitted"** (dispatcher reject HTTP method, KHÔNG phải lỗi permission). Widget hiện "Không tải được" dù manual GET cùng cookie → 200. `revenue_mix()` **KHÔNG có params** ⇒ chắc chắn dính nếu không xử lý.
> **Quyết định (ADR-M02-14, Accepted)**: `getRevenueMix` set **`method: 'GET'`** ngay trong spec (đã nhúng ở §1sext.2). FE test BẮT BUỘC assert resource có `method === 'GET'` (thêm vào `antmedRevenueMix.test.js`). *(Sửa lan sang 24 endpoint cũ = Slice FE riêng — KHÔNG gộp vào M02-7 để giữ phạm vi; nhưng endpoint MỚI vòng này PHẢI đúng từ đầu, KHÔNG kế thừa defect.)*

### 1sext.3 — FE helper bar màu/style (TÁI DÙNG `utils/antmedUi.js`)
- **Tiền VI**: tái dùng `formatVnMoney` đã có (`'2,1 tỷ'` / `'186,4 tr'`). KHÔNG đẻ formatter mới (ADR-M02-13). *(Acceptance ví dụ '186,4 triệu' = nhãn verbose; quyết định dùng **'tr'** gọn cho nhất quán Top 10 — ADR-M02-13; nếu PM bắt buộc 'triệu' verbose → đổi 1 chỗ trong `formatVnMoney` hoặc thêm tham số, ghi vào ADR.)*
- **Bar màu brand** (MỚI, PURE — KHÔNG import frappe-ui → unit-test trực tiếp): `revenueMixBarStyle(pct) => ({ width: `${Math.max(0, Math.min(100, Number(pct) || 0))}%` })` (clamp 0–100). Màu brand đặt qua class cố định (vd `bg-surface-gray-7`/token brand mockup A2) trên thanh — KHÔNG đổi màu theo lớp (cơ cấu doanh thu là 1 màu brand, KHÔNG ngưỡng green/orange/red như health).

### 1sext.4 — Wire widget vào `AntmedHome.vue` (cùng hàng / ngay sau Top 10)
- Component MỚI `components/Antmed/AntmedRevenueMixCard.vue` (presentational — nhận props `items`/`totalRevenue`/`loading`/`error`, emit `retry`; KHÔNG tự fetch; tái dùng token card `rounded-xl border border-outline-gray-1 bg-surface-white p-4` như `AntmedTopHospitalsCard`).
- Đặt trong `AntmedHome.vue` **Hàng 2**: đổi section Top 10 (`grid grid-cols-1`) thành `grid grid-cols-1 gap-4 lg:grid-cols-2` chứa `<AntmedTopHospitalsCard>` + `<AntmedRevenueMixCard>` (cùng hàng trên ≥lg; xếp dọc mobile). KHÔNG đụng props/binding card Top 10.
- Resource: `const revenueMix = getRevenueMix({ auto: true })`; bind `:items="revenueMix.data?.data || []"` `:total-revenue="revenueMix.data?.total_revenue || 0"` `:loading="revenueMix.loading"` `:error="!!revenueMix.error"` `@retry="revenueMix.reload()"`.
- Bảng trong card: 4 dòng (loop `items`), mỗi dòng: **nhãn lớp** (`label`) · **doanh thu** (`formatVnMoney(revenue)`) · **% tỷ trọng** (`pct` + '%') · **bar** `:style="revenueMixBarStyle(pct)"` màu brand. Render đủ 4 dòng kể cả `revenue==0`.
- Tri-branch RIÊNG cho card: loading 'Đang tải…' / error Badge + nút 'Thử lại' (`@retry`→reload) / empty (`totalRevenue===0` || `!items.length`) 'Chưa có dữ liệu doanh thu'. KHÔNG mock.

### 1sext.5 — Test (BẮT BUỘC xanh THẬT)

**BE** (`antmed_crm/tests/test_antmed_contract.py`, class MỚI `TestAntMedRevenueMix`):
- `test_revenue_mix_shape`: trả dict có `data`(list len==4) + `total_revenue`(float/int); mỗi dòng đúng 4 key (`classification`/`label`/`revenue`/`pct`); `classification` theo thứ tự đúng `["Loại A","Loại B","Loại C","Loại D"]`; `label==classification`.
- `test_revenue_mix_four_rows_even_when_zero`: lớp không có doanh thu vẫn xuất hiện với `revenue==0.0` & `pct==0.0` (KHÔNG bỏ dòng).
- `test_revenue_mix_aggregate_cross_contract`: seed ≥2 HĐ + AntMed Item các lớp khác nhau; `revenue` mỗi lớp = `SUM(used_qty*unit_price)` gộp cross-contract đúng số.
- `test_revenue_mix_pct`: `pct == round(100*revenue/total_revenue, 1)`; Σ pct của 4 lớp ≈ 100 (±làm tròn) khi total>0.
- `test_revenue_mix_total_zero_safe`: scope rỗng / mọi `used_qty==0` → `total_revenue==0` & mọi `pct==0.0` (KHÔNG ZeroDivisionError); vẫn 4 dòng.
- `test_revenue_mix_unclassified_to_other`: item thiếu `classification` (hoặc SKU không có trong AntMed Item) → revenue đó KHÔNG vào 4 dòng & KHÔNG vào `total_revenue` (total chỉ = SUM 4 lớp; chứng minh bằng so sánh total trước/sau khi thêm 1 dòng quota item-không-phân-loại — total KHÔNG đổi).
- `test_revenue_mix_fail_closed` (BR-13): user KHÔNG read-perm `AntMed Contract` → trả `{data: 4 dòng revenue=0/pct=0, total_revenue:0}` (KHÔNG raise, dùng `get_list` — KHÔNG raw SQL).
- `test_revenue_mix_respects_permission` (data-scope BR-13): user chỉ thấy BV/HĐ được giao → revenue từ HĐ ngoài scope KHÔNG cộng vào; KHÔNG `frappe.db.sql`.
- `test_revenue_mix_no_raw_sql_no_n_plus_1`: assert source `revenue_mix` KHÔNG chứa `frappe.db.sql`; classification resolve 1 lần (`get_all` 1 lần — assert qua đếm hoặc inspect, mirror pattern test M03-4 `no_n_plus_1`).

**FE** (`frontend/tests/unit/antmedRevenueMix.test.js` MỚI):
- `data/antmed` export `getRevenueMix`; url == `antmed_crm.api.antmed.contract.revenue_mix`; **resource có `method === 'GET'`** (chống defect POST→403, ADR-M02-14); đọc `r.data.data` + `r.data.total_revenue` (KHÔNG `.data.data.data`); KHÔNG `createListResource`.
- `revenueMixBarStyle(pct)`: width clamp 0–100 (`-5→0%`, `120→100%`, `42.5→42.5%`, `null/NaN→0%`); PURE.
- `formatVnMoney` tái dùng (đã có test riêng — KHÔNG đẻ formatter mới).
- Card render 4 dòng; nhãn lớp + `formatVnMoney(revenue)` + `pct%` + bar `:style` width; render đủ 4 dòng khi 1 lớp revenue=0; tri-branch empty `total_revenue===0` → 'Chưa có dữ liệu doanh thu'; KHÔNG sort/mock.
- `yarn build` → chunk chứa nhãn `'Cơ cấu doanh thu'`.

### 1sext.6 — DoD Slice M02-7
- **BE**: `bench --site miyano run-tests --module antmed_crm.tests.test_antmed_contract` → `Ran N OK` (test cũ giữ xanh + ~9 mới `revenue_mix` trong class `TestAntMedRevenueMix`); `revenue_mix` resolve; `grep -c "^def revenue_mix" antmed_crm/api/antmed/contract.py` == 1.
- **FE**: `cd frontend && yarn test` (vitest) file mới `antmedRevenueMix.test.js` xanh; `yarn build` ✓ (chunk chứa 'Cơ cấu doanh thu').
- **Invariant data-scope (BR-13)**: revenue chỉ gộp dưới permission user (`frappe.get_list`, KHÔNG raw SQL) — verify ở `test_revenue_mix_respects_permission` + `test_revenue_mix_fail_closed`.
- **Pixel (Playwright, sau USER reload)**: `/antmed` (AntmedHome) render card 'Cơ cấu doanh thu' **cùng hàng / ngay sau** 'Top 10 Bệnh viện'; bảng ĐÚNG 4 dòng Loại A/B/C/D (kể cả lớp 0), mỗi dòng nhãn + tiền VI gọn + % + bar màu brand width=%; total_revenue==0 → empty 'Chưa có dữ liệu doanh thu'; lỗi card Top 10 KHÔNG làm vỡ card này (2 resource độc lập); 0 console error.

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

| Endpoint (`antmed_crm.api.antmed.contract.<fn>`) | Verb | Mô tả | Trả về |
|---|---|---|---|
| `list_contracts` | GET | List HĐ (filter: hospital/workflow_state/search số HĐ); phân trang | `{ "data": [...], "total_count": int }` — **count == rows** khi không phân trang |
| `get_contract` | GET | Chi tiết 1 HĐ + danh mục `items` (quota, đơn giá, used/remaining) | RAW dict (field HĐ + `items` list + `hospital_name` resolve) |
| `get_contract_health` | GET | Dữ liệu màn "Sức khoẻ hợp đồng": mỗi HĐ kèm `quota_used_pct` tổng, cờ màu (xanh/cam/đỏ), `days_to_expiry` | `{ "data": [...] , "total_count": int }` |
| `check_item_in_contract` | GET | Tra cứu BR-01: vật tư X có trong HĐ active của BV Y không + quota còn lại (cho M04/mobile tra trước khi giao) | `{ "in_contract": bool, "contract": str\|None, "unit_price": float\|None, "remaining_qty": float\|None }` |
| `list_quota_alerts` | GET | Quota chạm 70/90/100% + HĐ sắp hết hạn (cho dashboard/cảnh báo điều hành) | `{ "data": [...], "total_count": int }` |
| `top_hospitals` ✅ **Slice M02-4** | GET | Xếp hạng BV theo **doanh thu HĐ** (`SUM(total_value)`) + `quota_used_pct` gộp, cho widget "Top 10 Bệnh viện" (Dashboard CEO mockup A1). Tham số `limit` (mặc định 10). Spec FROZEN §1quater | `{ "data": [...], "total_count": int }` — `data` sort GIẢM theo `revenue`, ≤ `limit` dòng |
| `top_quota_items` ✅ **Slice M02-5** | GET | Xếp hạng SKU theo **% quota đã dùng** gộp **CROSS-CONTRACT theo item** (`used_pct = 100*SUM(used_qty)/SUM(quota_qty)`), cho widget "Danh mục VT trúng thầu — top 5" (chân màn `/antmed/contract-health`, mockup A2 CEO). Tham số `limit` (mặc định 5). `frappe.get_list` BR-13 fail-closed; SUM quota==0 → `used_pct=0.0`. Spec FROZEN §1quint | `{ "data": [...], "total_count": int }` — mỗi dòng 6-key (`item`/`item_name`/`quota_qty`/`used_qty`/`used_pct`/`health_color`), `data` sort GIẢM theo `used_pct`, ≤ `limit` dòng |
| `revenue_mix` ✅ **Slice M02-7** | GET | Cơ cấu doanh thu theo **`classification` AntMed Item** (4 lớp Loại A/B/C/D), `revenue = SUM(used_qty × unit_price)` gộp **CROSS-CONTRACT** theo lớp; cho widget "Cơ cấu doanh thu" (Dashboard `/antmed` CEO, mockup A2). KHÔNG tham số. Resolve item→classification BATCH 1 query (KHÔNG N+1). `frappe.get_list` BR-13 **fail-closed** (noperm → 4 dòng 0). item thiếu classification → nhóm 'Khác' (loại khỏi data & total). Spec FROZEN §1sext | `{ "data": [4 dòng], "total_revenue": float }` — `data` **ĐÚNG 4 phần tử cố định A→B→C→D**, mỗi dòng 4-key (`classification`/`label`/`revenue`/`pct`); `pct = round(100*revenue/total_revenue, 1)` (total==0 ⇒ pct=0.0) |

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

> Vue 3 + frappe-ui SPA. `createResource` (list trả dict `{data,total_count}` → đọc `r.data.data`). Route `/antmed/*` APPEND vào `frontend/src/router.js` (lazy). Nhãn 100% tiếng Việt qua `__()`. KHÔNG đụng route CRM gốc, KHÔNG `crm.api.*`, KHÔNG axios.

Màn hình từ `UI_Design §1.2` (Dashboard CEO widget "% Quota đã dùng" ngưỡng 70/90/100) + `§1.3` ("Sức khoẻ hợp đồng"):

> §7 = bản đồ UI **toàn module M02** (forward-looking). **Phạm vi từng vòng** chốt ở **§1bis.5** (LIST, M02-1a) + **§1ter** (DETAIL, M02-1b) + §8: M02-1a ship route LIST; M02-1b ship route DETAIL (ADR-M02-07 đảo defer của ADR-M02-06); Health là M02-2.

| Route (THÊM, lazy) | name | page | Mô tả | Role dùng | Vòng |
|---|---|---|---|---|---|
| `/antmed/contracts` | `AntmedContracts` | `pages/AntmedContracts.vue` | List HĐ: cột Số HĐ, BV, hiệu lực đến, giá trị, trạng thái; lọc BV/trạng thái; search | `Quản lý`, `NV kinh doanh` | **M02-1a (ship)** |
| `/antmed/contracts/:name` | `AntmedContractDetail` | `pages/AntmedContractDetail.vue` | Chi tiết HĐ: header (số HĐ/BV/ngày ký/hiệu lực/giá trị/badge trạng thái) + bảng quota (thanh % màu ngưỡng 95/72, chip Khóa 100%); breadcrumb về list | `Quản lý`, `NV kinh doanh` | **M02-1b (vòng này — §1ter)** |
| `/antmed/contract-health` | `AntmedContractHealth` | `pages/AntmedContractHealth.vue` | "Sức khoẻ hợp đồng": list HĐ + progress bar 2 màu (xanh ≤80% / cam 80–100% / đỏ >100% hoặc <30% còn ≤30 ngày) | `Quản lý`, CEO | `[PLANNED]` M02-2 |

- **List** (`/antmed/contracts`, M02-1a): `createResource` → `antmed_crm.api.antmed.contract.list_contracts`; **row-click khôi phục** drill-down ở M02-1b (`router.push` Detail — ADR-M02-07).
- **Detail** (`/antmed/contracts/:name`, M02-1b): `createResource` → `get_contract` (đọc `r.data.items` TRỰC TIẾP, KHÔNG `r.data.data`); mỗi dòng quota hiển thị thanh % theo **% đã dùng** = `100 - remaining_pct` (đỏ ≥95 / cam ≥72 / xanh còn lại); chip `Khóa khi đủ 100%` khi `lock_at_100`; badge trạng thái VI; empty-state `Chưa có dòng quota`; error-state có "Thử lại" (KHÔNG leak stacktrace). Spec FROZEN §1ter.
- **Sức khoẻ HĐ** (`/antmed/contract-health`): `createResource` → `get_contract_health`; progress bar theo ngưỡng màu; cột "còn N ngày" đỏ khi ≤30.
- Widget Dashboard "% Quota đã dùng" (vòng tròn 70/90/100) = M11 tiêu thụ `list_quota_alerts`/`get_contract_health` — `[cross-ref M11]`.
- **Widget "Top 10 Bệnh viện"** (Dashboard `/antmed` CEO, mockup A1 line 261 — **Slice M02-4**): card trong `AntmedHome.vue` (thay placeholder cũ), `createResource` → `top_hospitals`; bảng 3 cột BV | DT (`formatVnMoney`) | Quota (bar màu qua `healthBarClass`, số % cạnh bar); tri-branch loading/error(Thử lại)/empty 'Chưa có dữ liệu bệnh viện'; FE giữ thứ tự + cờ màu BE (KHÔNG sort/tính lại); drill-down dòng → `AntmedHospitalDetail` (`/antmed/hospitals/:name`, route đã có). Spec FROZEN §1quater.
- **Widget "Danh mục VT trúng thầu — top 5"** (chân màn `/antmed/contract-health` CEO, mockup A2 — **Slice M02-5**): card MỚI **dưới** bảng Sức khỏe HĐ trong `AntmedContractHealth.vue`, `createResource` → `top_quota_items`; bảng 4 cột SKU (`item · item_name`) | Quota (`quota_qty`) | Đã xuất (`used_qty`) | % (bar màu qua `healthBarClass` + số %); fetch **ĐỘC LẬP** với bảng Sức khỏe HĐ (lỗi 1 không vỡ cái kia); tri-branch RIÊNG loading/error(Thử lại)/empty 'Chưa có vật tư trúng thầu'; FE giữ thứ tự (sort GIẢM `used_pct` ở BE) + cờ màu BE (KHÔNG sort/tính lại); KHÔNG drill-down (route màn item M03 chưa có). Spec FROZEN §1quint.
- **Widget "Cơ cấu doanh thu"** (Dashboard `/antmed` CEO, mockup A2 id=ceo — **Slice M02-7**): card MỚI `AntmedRevenueMixCard.vue` trong `AntmedHome.vue` **cùng hàng / ngay sau** card Top 10 (Hàng 2 đổi sang `lg:grid-cols-2`), `createResource` → `revenue_mix`; bảng 4 dòng cố định **Loại A/B/C/D** (kể cả lớp revenue=0 vẫn render) — mỗi dòng nhãn lớp · doanh thu (`formatVnMoney` gọn '2,1 tỷ'/'186,4 tr') · % tỷ trọng · bar màu brand width=`pct%` (`revenueMixBarStyle` PURE); fetch **ĐỘC LẬP** với `getTopHospitals`; tri-branch RIÊNG loading/error(Thử lại)/empty (`total_revenue==0` → 'Chưa có dữ liệu doanh thu'); FE KHÔNG sort/đổi thứ tự (BE trả cố định A→B→C→D); KHÔNG drill-down. Spec FROZEN §1sext.

---

## 8. Build slices (cho factory — KHÔNG commit)

> Mỗi slice = 1 vòng factory (BA spec → BE+FE → QA → user). TDD failing-first. M02 chạy ở W1 (sau M01 core, ‖ M03). Vì M03 (`AntMed Item`) có thể chưa land khi M02 bắt đầu → xem ADR-M02-02 cho field `item`.

1. **Slice M02-1a — Contract master + quota (đọc), màn DANH SÁCH ✅ SHIPPED (spec §1bis)**: DocType `AntMed Contract` (submittable, `track_changes=1`, naming `AM-HD-.YYYY.-.#####`, Select `status` read-only — KHÔNG Workflow) + `AntMed Quota Item` child (`item`=Data tạm) + DocPerm VI (NV read-only); API `list_contracts`+`get_contract` (RAW dict, count==rows — cả 2 ship & test); FE 1 route LIST (`/antmed/contracts`, `AntmedContracts.vue`) read-only + nav enabled + row-click no-op (M02-1a); test BE **12/12 OK**, FE vitest + build xanh.
   - **Slice M02-1b — FE Detail Hợp đồng ✅ spec FROZEN §1ter (VÒNG NÀY)**: route `AntmedContractDetail` (`/antmed/contracts/:name`, lazy, `props:true`, qua guard chung) + page `AntmedContractDetail.vue` (`getContract` → `get_contract` đã có; header HĐ + bảng quota thanh % màu ngưỡng 95/72 + chip Khóa 100% + empty-state + error-state "Thử lại" + breadcrumb) + **khôi phục** `router.push` & affordance click ở list (đảo no-op M02-1a) + **đảo + thêm** FE test (`antmedContracts.test.js`: đảo 3 assert "Detail vắng mặt" + thêm test page Detail + guard route :name). **BE KHÔNG đổi** (12/12 OK). ADR-M02-07 (Supersede ADR-M02-06).
2. **Slice M02-2 — Workflow hợp đồng**: fixture `workflow.json` (states/transitions VI, §3) + scheduler `daily_contract_check` (state Sắp hết hạn/Hết hạn) + API `get_contract_health`/`list_quota_alerts`; FE màn "Sức khoẻ HĐ"; test transition smoke.
3. **Slice M02-3 — Quota enforce + usage log**: `AntMed Quota Usage Log` + hàm `assert_item_in_contract`/`assert_quota_available`/`consume_quota`/`recompute_quota_usage`; API `check_item_in_contract`; test BR-01/02/06 (chặn item ngoài HĐ, override `Quản lý`, lock 100%). *(Wiring doc_events sang M04 thực hiện khi M04 land — chỉ cần hàm sẵn sàng.)*
4. **Slice M02-4 — Widget "Top 10 Bệnh viện" (CEO) ✅ spec FROZEN §1quater (VÒNG 10)**: endpoint MỚI `top_hospitals(limit=10)` (RAW `{data, total_count}`, gộp BV theo `SUM(total_value)` + `quota_used_pct`, `health_color`=`_health_color(pct, None)`, `frappe.get_list` BR-13 — KHÔNG raw SQL) + wire widget card 'Top 10 Bệnh viện' (3 cột BV|DT|Quota bar màu) vào `AntmedHome.vue` (thay placeholder Top 10 cũ) + `getTopHospitals` (data/antmed.js) + bar màu qua `healthBarClass` PURE (tái dùng) + tri-branch + drill-down `AntmedHospitalDetail` + test BE (~7 mới trong `test_antmed_contract`) + FE vitest. **ADR-M02-08** (chốt cách tính `health_color`).
5. **Slice M02-5 — Widget "Danh mục VT trúng thầu — top 5" (CEO) ✅ spec FROZEN §1quint (VÒNG 11 — VÒNG NÀY)**: endpoint MỚI `top_quota_items(limit=5)` (RAW `{data, total_count}`, gộp **CROSS-CONTRACT theo item**, `used_pct=100*SUM(used)/SUM(quota)` fail-safe 0 khi SUM quota==0, `health_color`=`_health_color(used_pct, None)`, `frappe.get_list` BR-13 fail-closed — KHÔNG raw SQL) + wire card MỚI 'Danh mục VT trúng thầu — top 5' (4 cột SKU|Quota|Đã xuất|% bar màu) vào **chân màn** `AntmedContractHealth.vue` + `getTopQuotaItems` (data/antmed.js) + bar màu qua `healthBarClass` PURE (tái dùng) + fetch ĐỘC LẬP với `getContractHealth` + tri-branch RIÊNG (empty 'Chưa có vật tư trúng thầu') + test BE (~8 mới) + FE vitest. **BE cleanup**: gỡ `top_hospitals` def trùng + `test_top_hospitals_*` trùng tên (**ADR-M02-10**). **ADR-M02-11** (gộp-theo-item, count==rows N/A).
6. **Slice M02-7 — Widget "Cơ cấu doanh thu" (CEO) ✅ spec FROZEN §1sext (VÒNG 15 — VÒNG NÀY)**: endpoint MỚI `revenue_mix()` (RAW `{data, total_revenue}`, `data` ĐÚNG 4 dòng cố định Loại A→B→C→D, `revenue=SUM(used_qty×unit_price)` gộp **CROSS-CONTRACT theo classification AntMed Item**, resolve item→classification BATCH 1 query — KHÔNG N+1, `pct=round(100*rev/total,1)` total==0→0.0, item thiếu classification → nhóm 'Khác' loại khỏi data & total, `frappe.get_list` BR-13 **fail-closed** noperm→4 dòng 0 — KHÔNG raw SQL) + wire card MỚI 'Cơ cấu doanh thu' (`AntmedRevenueMixCard.vue`) vào `AntmedHome.vue` **cùng hàng / ngay sau** Top 10 (Hàng 2 → `lg:grid-cols-2`) + `getRevenueMix` (data/antmed.js) + bar màu brand qua `revenueMixBarStyle` PURE + tiền VI tái dùng `formatVnMoney` + fetch ĐỘC LẬP với `getTopHospitals` + tri-branch RIÊNG (empty `total_revenue==0` 'Chưa có dữ liệu doanh thu') + test BE (~9 mới, class `TestAntMedRevenueMix`) + FE vitest mới. **ADR-M02-12** (rollup theo classification + 'Khác' loại khỏi total) + **ADR-M02-13** (tái dùng `formatVnMoney`).
7. **Slice M02-8 `[PLANNED]` — Phụ lục (Amendment)** *(đẩy số: M02-5 = widget VT trúng thầu vòng 11; M02-7 = widget Cơ cấu doanh thu vòng 15; M02-6 reserve)*: `AntMed Contract Amendment` + logic cộng quota + `has_amendment`; FE form phụ lục.

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

### ADR-M02-07: Mở lại FE Detail Hợp đồng (Slice M02-1b) — Supersede ADR-M02-06
- **Status**: Accepted — **Supersedes ADR-M02-06**
- **Date**: 2026-06-17
- **Context**: ADR-M02-06 (vòng 1) **defer** màn Detail (`/antmed/contracts/:name`) để tránh dead-end khi route chưa tồn tại → M02-1a ship list với `openContract`=no-op + gỡ affordance click. Đó là quyết định **đúng cho vòng 1** (route Detail chưa có ⇒ row-click sẽ rơi no-match). Nay vòng 2 (M02-1b) có acceptance yêu cầu **tạo trang Detail + đăng ký route + mở lại drill-down**. BE `get_contract` đã ship & test cover (12/12) → không cần đụng BE. Điều kiện gây dead-end của ADR-M02-06 (route thiếu) **đã được giải quyết** trong chính vòng này (route được đăng ký) → no-op không còn lý do tồn tại.
- **Decision**: (1) Tạo `frontend/src/pages/AntmedContractDetail.vue` + đăng ký route `/antmed/contracts/:name` (name `AntmedContractDetail`, lazy, `props:true`) cạnh các route Detail `/antmed/*/:name` đã có; đi qua **guard chung đã có** (KHÔNG đổi `shouldRedirectNotPermitted`/`beforeEach`). (2) **Khôi phục** ở `AntmedContracts.vue`: `openContract`→`router.push({name:'AntmedContractDetail', params:{name}})` + affordance click ở `<tr>` (`cursor-pointer`/`role="link"`/`tabindex`/`@click`/`@keydown.enter`/`:aria-label`). (3) **Đảo** 3 assert "Detail vắng mặt" trong `antmedContracts.test.js` + thêm test page Detail. (4) **KHÔNG sửa BE** — `get_contract` + 12/12 test giữ nguyên (acceptance "không sửa BE").
- **Alternatives**: (a) giữ ADR-M02-06 + làm Detail ở vòng riêng — loại: acceptance vòng này chính là Detail; (b) modal thay vì route Detail — loại: acceptance yêu cầu URL trực tiếp `/antmed/contracts/<name>` render được (deep-link) → cần route thật; (c) sửa BE thêm field — loại: `get_contract` đã đủ shape (header + items với remaining_pct/lock_at_100), acceptance cấm sửa BE.
- **Consequences**: (+) drill-down list→detail hoạt động, deep-link URL render, `get_contract` (ship từ M02-1a) có FE tiêu thụ. (+) Không chạm BE → no-regression BE chắc chắn. (−) Phải đảo 3 test FE M02-1a (đã ghi rõ delta §1ter.5) — test cũ KHÔNG còn đúng sau khi Detail land (đây là Self-Correction hợp lệ, không phải breakage). (−) Ngưỡng màu bar áp lên **% đã dùng** (`100-remaining_pct`) — cần FE map đúng ngữ nghĩa "remaining_pct = % còn lại" của BE (§1ter.3 ghi rõ để dev không nhầm).

### ADR-M02-08: `top_hospitals` — tính `health_color` qua `_health_color(pct, None)` (rank-by-revenue KHÔNG xét hạn)
- **Status**: Accepted (Slice M02-4)
- **Date**: 2026-06-17
- **Context**: Acceptance M02-4 cho 2 lựa chọn cho cờ màu bar quota của widget Top 10: (a) tái dùng `_health_color(used_pct, days_to_expiry)` đã có với `days_to_expiry=None` (vì xếp theo doanh thu, KHÔNG theo HĐ đơn lẻ ⇒ không có "hạn" của 1 BV); (b) helper ngưỡng quota thuần mới (green<70 / warn 70–89 / danger≥90). Yêu cầu **chốt 1 cách, ghi rõ**.
- **Decision**: Chọn **(a)** — `health_color = _health_color(quota_used_pct, None)`. Ngưỡng hiệu dụng: **green ≤80% · orange >80–100% · red >100%** (nhánh `days_to_expiry` bị vô hiệu vì truyền `None`). FE map qua `healthBarClass` đã có (`green→default/orange→warn/red→danger`).
- **Alternatives**: (b) helper ngưỡng thuần green<70/warn70-89/danger≥90 — **loại**: (1) đẻ ngưỡng thứ 2 lệch với toàn bộ M02 (`get_contract_health`, FE `healthBarClass`/`HEALTH_COLOR_THEME`) ⇒ 2 nguồn-sự-thật về "đỏ là bao nhiêu %", dễ drift; (2) FE phải thêm hàm/ngưỡng mới, vi phạm tinh thần "tái dùng token + helper PURE hiện có"; (3) ngưỡng quota của 1 BV gộp-cross-HĐ vốn ít ý nghĩa pháp lý hơn ngưỡng per-HĐ — không đáng đẻ ngưỡng riêng. Mockup A1 (line 261, bar 88%=brand/72%=plain/95%=danger) là **prototype minh hoạ**, KHÔNG phải spec ngưỡng ⇒ không ràng buộc chọn (b).
- **Consequences**: (+) 1 nguồn ngưỡng duy nhất (`_health_color`) cho cả contract-health lẫn top-hospitals; FE 0 hàm mới (tái dùng `healthBarClass`). (+) Đổi ngưỡng sau này chỉ sửa 1 nơi. (−) Ngưỡng quota của widget = ngưỡng per-HĐ (>80/>100), KHÔNG phải 70/90 như band cảnh báo `list_quota_alerts` (`QUOTA_ALERT_BANDS=100/90/70`) — chấp nhận: widget là "sức khỏe màu" nhanh, không phải bảng cảnh báo chi tiết; nếu PM sau muốn đồng bộ 70/90 thì là 1 ADR mới (đổi `_health_color` ảnh hưởng cả contract-health → cân nhắc tác động chéo).

### ADR-M02-09: `top_hospitals` là endpoint xếp-hạng-cắt-top — KHÔNG áp invariant count==rows
- **Status**: Accepted (Slice M02-4)
- **Date**: 2026-06-17
- **Context**: Mọi list endpoint M02 (`list_contracts`/`get_contract_health`/`list_quota_alerts`) giữ invariant **count == rows** (BR-13 — `total_count` đếm qua `get_list` dưới permission, khớp số dòng trả khi không phân trang). `top_hospitals` cố ý **cắt top `limit` (10)** ⇒ `len(data)` có thể < `total_count`.
- **Decision**: `top_hospitals` trả `total_count` = **số BV phân biệt trong scope user** (đếm sau gộp, TRƯỚC khi cắt limit); `data` = top `limit` dòng. Invariant count==rows **KHÔNG áp** cho endpoint này (đã cắt cố ý). Vẫn dùng `frappe.get_list` (tôn trọng permission BR-13) — fail-closed: noperm/scope rỗng → `{"data": [], "total_count": 0}`.
- **Alternatives**: trả `total_count == len(data)` (đếm sau cắt) — **loại**: mất thông tin "còn bao nhiêu BV nữa" cho nút "xem tất cả" tương lai; dùng `frappe.db.count`/raw SQL bỏ permission để đếm tổng — **loại tuyệt đối** (rò rỉ BR-13, Red Flag). FE KHÔNG được giả định `total_count == data.length`.
- **Consequences**: (+) Giữ data-scope BR-13 nguyên vẹn (đếm dưới `get_list`). (+) Endpoint self-describe qua docstring ("xếp-hạng-cắt-top"). (−) Test KHÔNG được assert `len(data)==total_count` cho endpoint này (assert riêng: `len(data) ≤ limit` và `total_count ≥ số BV thật`). Đã ghi rõ ở §1quater.1 cảnh báo ⚠ + §1quater.5 test.

### ADR-M02-10: Cleanup `top_hospitals` định nghĩa trùng — giữ bản fail-closed, xoá def chết
- **Status**: Accepted (Slice M02-5)
- **Date**: 2026-06-17
- **Context**: Vòng 10 append `def top_hospitals` **2 lần** vào `antmed_crm/api/antmed/contract.py` (line ~262 và ~443). Python chỉ giữ **def định nghĩa cuối** (line 443) — def đầu là dead code (gây nhầm khi đọc/review, và làm `grep` ra 2 kết quả). Tương tự `test_antmed_contract.py` có `test_top_hospitals_*` trùng tên trong cả `TestAntMedContract` (~line 306) lẫn `TestAntMedTopHospitals` (~line 543) — trùng tên method trong cùng class sẽ che khuất nhau; ở 2 class khác nhau thì chạy 2 lần với fixture khác (lãng phí, dễ lệch ý nghĩa).
- **Decision**: GIỮ **1** `def top_hospitals` = bản **fail-closed** (`try/except frappe.PermissionError → {"data": [], "total_count": 0}`; `name_map[h] = hospital_name` KHÔNG `or h`) vì khớp acceptance M02-4 ("fail-closed BR-13"); XOÁ def đầu (không try/except). Bộ test `top_hospitals` giữ ở `TestAntMedTopHospitals` (class chuyên, `setUpClass` riêng); gỡ các `test_top_hospitals_*` trùng tên/ý ở `TestAntMedContract`. Sau cleanup: `grep -c "^def top_hospitals" == 1`, mỗi tên test còn 1 lần.
- **Alternatives**: giữ cả 2 def — **loại** (dead code + nhầm lẫn review); giữ bản KHÔNG fail-closed (def đầu) — **loại** (vi phạm acceptance fail-closed BR-13). Bỏ qua cleanup, để vòng sau — **loại** (acceptance M02-5 yêu cầu cleanup kèm + hai endpoint phải resolve đúng).
- **Consequences**: (+) `top_hospitals` + `top_quota_items` đều resolve rõ ràng, `grep` 1 kết quả. (+) Test deterministic, không che khuất. (−) Là sửa code-cũ trong vòng spec mới (không phải pure-additive) — đã giới hạn phạm vi chặt ở §1quint.5 + DoD §1quint.7 để BE không "refactor lan". *(Self-Correction: lỗi do quy trình append vòng 10, sửa Core Doc trước rồi mới cho dev gỡ.)*

### ADR-M02-11: `top_quota_items` gộp cross-contract theo `item`, dùng `_health_color(pct, None)`, count==rows N/A
- **Status**: Accepted (Slice M02-5)
- **Date**: 2026-06-17
- **Context**: Widget "Danh mục VT trúng thầu — top 5" cần % quota theo **SKU** chứ không theo HĐ hay BV. 1 SKU có thể nằm ở nhiều HĐ (nhiều BV) → cần **rollup cross-contract**: gộp mọi dòng quota cùng `item` của các HĐ user đọc được. Cờ màu bar: tái dùng `_health_color` (như ADR-M02-08) hay đẻ ngưỡng riêng? Và endpoint cắt top `limit` (5) → invariant count==rows có áp không?
- **Decision**: (1) `used_pct = 100*SUM(used_qty)/SUM(quota_qty)` gộp theo `item` trên scope user (`frappe.get_list` lấy HĐ → `get_all` quota theo `parent IN names`); `SUM(quota_qty)==0 → used_pct=0.0` (fail-safe). (2) `health_color = _health_color(used_pct, None)` — **tái dùng** (1 nguồn ngưỡng green≤80/orange>80–100/red>100 cho cả contract-health + top-hospitals + top-quota-items; FE 0 hàm mới). (3) Là endpoint **xếp-hạng-cắt-top** như `top_hospitals` ⇒ `total_count` = số SKU phân biệt trong scope (TRƯỚC cắt), `len(data) ≤ limit`; **invariant count==rows KHÔNG áp** (ADR-M02-09 áp dụng tương tự). Vẫn `frappe.get_list` fail-closed (BR-13).
- **Alternatives**: gộp theo `(hospital,item)` thay vì chỉ `item` — **loại** (mockup A2 là danh mục VT toàn cục, không tách BV; tách BV là widget khác); weighted theo `unit_price` — **loại** (acceptance ghi rõ `100*SUM(used)/SUM(quota)` thuần lượng); đẻ ngưỡng màu riêng cho SKU — **loại** (drift ngưỡng, vi phạm "FE KHÔNG tự đặt ngưỡng, map qua `healthBarClass` đã có"); `frappe.db.sql` để gộp nhanh — **loại tuyệt đối** (rò rỉ BR-13, Red Flag).
- **Consequences**: (+) Cùng helper ngưỡng + helper FE với 2 widget trước → nhất quán, dễ bảo trì. (+) Data-scope BR-13 giữ nguyên (gộp dưới `get_list`; test `respects_permission` chứng minh không rò: SKU/quota ngoài scope không lọt). (−) Test KHÔNG assert `len(data)==total_count` (assert `len(data) ≤ limit`, `total_count ≥ số SKU thật`). (−) `used_pct` cross-contract của 1 SKU pha trộn nhiều HĐ/giá — chấp nhận: widget là "sức khỏe danh mục" tổng quan, không phải bảng chi tiết per-HĐ.

### ADR-M02-12: `revenue_mix` gộp doanh thu theo `classification` AntMed Item; nhóm 'Khác' loại khỏi `total_revenue`
- **Status**: Accepted (Slice M02-7)
- **Date**: 2026-06-18
- **Context**: Widget "Cơ cấu doanh thu" (mockup A2 CEO) cần doanh thu theo **nhóm phân loại VTYT** (Loại A/B/C/D) — frame quản lý rủi ro thiết bị y tế (Loại A thấp nhất → Loại D cao nhất). `AntMed Item.classification` là Select **đúng 4 option** `Loại A/B/C/D` (verified: `antmed_crm/antmed/doctype/antmed_item/antmed_item.json`). `AntMed Quota Item.item` là **Data** chứa **item_code** (autoname `AntMed Item` = `field:item_code`) — KHÔNG Link (ADR-M02-02, M03 native-lite). Cần: (1) gộp revenue theo lớp nào (4 cố định hay động?), (2) doanh thu = đại lượng nào, (3) xử lý item thiếu classification ra sao, (4) BR-13 fail-closed đặt ở đâu, (5) resolve item→classification tránh N+1.
- **Decision**: (1) `data` = **ĐÚNG 4 dòng cố định** theo hằng `REVENUE_MIX_CLASSES = ("Loại A","Loại B","Loại C","Loại D")` — render đủ kể cả lớp revenue=0 (FE bind theo thứ tự, KHÔNG bỏ cột). (2) `revenue = SUM(used_qty × unit_price)` = **doanh thu đã tiêu thụ thực tế** (khớp acceptance), KHÔNG phải `quota_qty × unit_price` (giá trị trúng thầu — để Slice khác nếu PM cần). (3) item **thiếu classification** HOẶC **SKU không tồn tại** trong AntMed Item → gộp nhóm `'Khác'` → **LOẠI khỏi 4 dòng & LOẠI khỏi `total_revenue`** (total chỉ = SUM 4 lớp A–D ⇒ Σpct ≈ 100%). (4) BR-13 fail-closed đặt trên **`AntMed Contract`** (`frappe.get_list` HĐ trong scope; noperm → 4 dòng 0, KHÔNG raise). (5) Resolve item→classification **BATCH 1 query** `frappe.get_all("AntMed Item", filters={"item_code": ("in", skus)}, fields=["item_code","classification"], ignore_permissions=True)` — `ignore_permissions=True` vì classification là **metadata tham chiếu phân loại VTYT**, KHÔNG phải dữ liệu phạm vi NV; nếu để DocPerm chặn (user đọc Contract nhưng không đọc AntMed Item → map rỗng → mọi item về 'Khác' → 4 dòng 0 dù có HĐ) thì widget vô dụng sai-âm. Phạm vi đã được giới hạn đúng bằng fail-closed trên Contract.
- **Alternatives**: gộp theo `am_item_group` / nhóm động từ DB — **loại** (mockup A2 cố định 4 lớp A/B/C/D; động = drift, FE khó bind cố định). Render 'Khác' thành dòng thứ 5 — **loại** (acceptance ghi rõ đúng 4 dòng A–D; 'Khác' loại khỏi data & total). Cộng 'Khác' vào total nhưng không render — **loại** (Σpct 4 dòng sẽ <100, gây nhầm "thiếu %"). `revenue = quota_qty × unit_price` — **loại** (acceptance ghi `used_qty × unit_price`). N+1 (mỗi SKU 1 `get_value` classification) — **loại tuyệt đối** (Red Flag perf). `frappe.db.sql` JOIN nhanh — **loại tuyệt đối** (rò rỉ BR-13). Để DocPerm chặn AntMed Item (KHÔNG `ignore_permissions`) — **loại** (sai-âm: user đọc HĐ nhưng vai trò không có read AntMed Item → widget rỗng dù có doanh thu).
- **Consequences**: (+) `data` shape ổn định 4 dòng (FE bind index/thứ tự an toàn — Hyrum). (+) BR-13 giữ trên Contract (test `respects_permission`/`fail_closed`); 1 query gộp quota + 1 query classification (KHÔNG N+1). (+) Σpct ≈ 100 dễ đọc cho CEO. (−) `ignore_permissions=True` trên AntMed Item: revenue phản ánh đúng classification kể cả khi vai trò user không có DocPerm read AntMed Item — chấp nhận vì classification là metadata công khai trong tổ chức, KHÔNG lộ dữ liệu HĐ/BV (chỉ map SKU→lớp). (−) item gõ sai SKU / chưa khai báo trong AntMed Item rơi vào 'Khác' bị ẩn → cơ cấu có thể <100% tổng doanh thu thực; chấp nhận: widget là "cơ cấu theo lớp đã phân loại", không phải báo cáo doanh thu tổng (báo cáo tổng ở M09/M11). (−) Endpoint KHÔNG có invariant count==rows kiểu list (4 dòng cố định) — test assert `len(data)==4`, KHÔNG assert == số bản ghi.

### ADR-M02-13: Tái dùng `formatVnMoney` cho tiền VI gọn (KHÔNG đẻ formatter 'triệu' verbose)
- **Status**: Accepted (Slice M02-7)
- **Date**: 2026-06-18
- **Context**: Acceptance ví dụ nhãn tiền `'2,1 tỷ'` / `'186,4 triệu'`. FE đã có helper `formatVnMoney` (`utils/antmedUi.js`) dùng cho widget Top 10 (M02-4) + widget kho M03-1, output `'X,Y tỷ'` (≥1 tỷ) / `'X,Y tr'` (1 triệu–<1 tỷ) / số nguyên đồng (<1 triệu) — tức **'tr'** chứ không **'triệu'** verbose. Có nên đẻ formatter mới để khớp chữ 'triệu'?
- **Decision**: **Tái dùng `formatVnMoney`** nguyên trạng (output '186,4 tr'); KHÔNG đẻ formatter 'triệu' verbose. Nhãn '186,4 triệu' trong acceptance = mô tả ý (đơn vị triệu), không phải hợp đồng chuỗi cứng. Ưu tiên **nhất quán hiển thị tiền toàn Dashboard** (Top 10 + Cơ cấu doanh thu cùng màn `/antmed` phải đồng dạng).
- **Alternatives**: thêm formatter `formatVnMoneyVerbose` ('tỷ'/'triệu'/'nghìn') — **loại** (2 cách hiển thị tiền lệch nhau trên cùng Dashboard, drift; trừ khi PM bắt buộc chữ 'triệu'). Đổi `formatVnMoney` thành 'triệu' — **loại** (regression Top 10 + M03-1 đã ship & test 'tr').
- **Consequences**: (+) 1 formatter tiền duy nhất, nhất quán. (−) Nếu PM/QA bắt buộc đúng chữ 'triệu' verbose → cần Slice/PM-decision nhỏ: thêm tham số `verbose` cho `formatVnMoney` (additive) + cập nhật ADR này (Supersede), KHÔNG đổi hành vi mặc định (giữ no-regression Top 10/M03-1). *(Ask-first đã ghi ở §1sext Boundaries.)*

### ADR-M02-14: FE read-resource set `method: 'GET'` — chống defect POST→403 (Self-Correction)
- **Status**: Accepted (Slice M02-7)
- **Date**: 2026-06-18
- **Context**: USER eval LIVE (R11) cho thấy widget M02-4/M02-5 + M03-1 trả **403 "Not permitted"** khi page-load: frappe-ui `createResource` KHÔNG set `method` → gửi **POST** (mặc định khi không params), trong khi BE `@frappe.whitelist(methods=["GET"])` reject POST ở tầng **dispatcher** (KHÔNG phải in-handler permission). Cả `data/antmed.js` (≥24 endpoint GET-only) không endpoint nào set `method`. `revenue_mix()` KHÔNG params ⇒ chắc chắn POST ⇒ chắc chắn 403 nếu không sửa.
- **Decision**: Endpoint MỚI vòng này (`getRevenueMix`) set **`method: 'GET'`** ngay từ spec (§1sext.2) + FE test assert `method==='GET'`. Phân biệt 2 loại 403 ghi rõ trong doc: **dispatcher-403** (HTTP verb sai — đây là loại này, sửa bằng `method:'GET'`) vs **in-handler permission-403** (`frappe.PermissionError` từ `get_list` — fail-closed BR-13 trả 4 dòng 0, KHÔNG để raise). Sửa lan 24 endpoint cũ = **Slice FE riêng** (không gộp M02-7, giữ phạm vi), nhưng endpoint mới KHÔNG kế thừa defect.
- **Alternatives**: đổi BE sang `methods=["GET","POST"]` cho khớp POST mặc định — **loại** (làm yếu contract GET-only, che giấu defect FE, lan sang 24 endpoint; semantic GET đúng cho read). Để FE tự "thử lại" — **loại** (vẫn POST, vẫn 403). Bỏ qua, để Slice sau — **loại** (acceptance M02-7 yêu cầu widget render LIVE, không render = fail gate).
- **Consequences**: (+) `revenue_mix` LIVE đúng từ vòng đầu (page-load GET → 200). (+) Doc phân biệt rõ 2 loại 403 cho QA/BE. (−) 24 endpoint cũ vẫn dính defect → cần Slice FE remediation riêng (ghi vào backlog/STATE để PM ưu tiên). (−) Là sửa idiom FE (thêm 1 key) — additive, không đổi shape resource.

> Kế thừa: **ADR-M01-01** (in-place), **ADR-M01-02** (prefix `AntMed `), **ADR-M01-05** (hoãn data-scope BR-13, giữ invariant count==rows), **DEC-A** (role VI), **D1/D2** (native-lite + Frappe Workflow). Không Supersede các ADR này. **ADR-M02-07 Supersede ADR-M02-06** (defer Detail) — ADR-M02-06 GIỮ trong doc làm lịch sử quyết định, không xoá. **ADR-M02-08/09** (Slice M02-4) + **ADR-M02-10/11** (Slice M02-5) + **ADR-M02-12/13/14** (Slice M02-7) bổ sung, KHÔNG Supersede ADR nào.

---

## 10. Acceptance / DoD

> Theo SPEC §6. Một slice "xong" = BE test xanh THẬT + FE vitest + build + (sau USER reload) pixel verify + no-regression.

**BE (TDD — `Ran N tests OK`):** file `antmed_crm/tests/test_antmed_contract.py`, lệnh `bench --site miyano run-tests --module antmed_crm.tests.test_antmed_contract` (M02-1a = **12/12 OK**; M02-1b KHÔNG sửa BE → giữ 12/12). *(Lưu ý: package thật là `antmed_crm`, không phải `crm` — bản cũ ghi `crm.tests.*` là stale.)*

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

**FE (vitest + build) — Slice M02-1a (đã đạt, no-regression):** `frontend/tests/unit/antmedContracts.test.js` — route `AntmedContracts` tồn tại; `@/data/antmed` export `listContracts`/`getContract`/`CONTRACT_WORKFLOW_THEME`; page list gọi `antmed_crm.api.antmed.contract.list_contracts` đọc `r.data.data`; KHÔNG `antmed_crm.api`/axios/tanstack/`createListResource`.

**FE (vitest + build) — Slice M02-1b (VÒNG NÀY — §1ter.5):** trong `antmedContracts.test.js`:
- **ĐẢO** (M02-1b): route `AntmedContractDetail` (`/antmed/contracts/:name`, lazy) **TỒN TẠI** (đảo assert "vắng mặt" của M02-1a); `openContract` **CÓ** `router.push({ name: 'AntmedContractDetail' ... })`; `<tbody>` **CÓ** affordance click (`@click`/`@keydown`/`role="link"`/`cursor-pointer`/`tabindex`).
- **THÊM** test page `AntmedContractDetail.vue`: gọi `antmed_crm.api.antmed.contract.get_contract` qua `getContract`; đọc `r.data.items` (KHÔNG `r.data.data`); tri-branch loading/error(reload `contract.reload()`)/data; empty-state `Chưa có dòng quota`; ngưỡng màu bar (nguồn chứa 95 + 72 + theme red/orange/green); chip `Khóa khi đủ 100%`; breadcrumb link `/antmed/contracts`; KHÔNG `createListResource`/axios/`.ts`.
- **THÊM** guard test: `shouldRedirectNotPermitted({path:'/antmed/contracts/AM-HD-2026-00001'}, antmed())===false`, `crm()===false`, `outsider()===true`.
- `vue-tsc --noEmit` + `yarn build` không lỗi mới + emit chunk `AntmedContractDetail*` + `crm.html` regenerate.

**Pixel (Playwright, sau USER reload) — Slice M02-1b:** truy cập trực tiếp `http://miyano:8000/crm/antmed/contracts/<name>` render header HĐ (số HĐ/BV/ngày ký/hiệu lực/giá trị VND/badge trạng thái) + bảng quota (bar màu đúng ngưỡng đỏ≥95/cam≥72/xanh + chip Khóa khi đủ 100%) — **KHÔNG màn trắng, KHÔNG `Invalid Page`/no-match**; items rỗng → empty-state `Chưa có dòng quota`; URL name sai/không quyền → error-state + "Thử lại" (**KHÔNG leak stacktrace**); từ `/antmed/contracts` bấm dòng → điều hướng tới Detail (không dead-end); breadcrumb về list; 0 console error; network `get_contract` 200 (hoặc 417/exception khi PermissionError → error-state). *(contract-health = vòng sau.)*

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
