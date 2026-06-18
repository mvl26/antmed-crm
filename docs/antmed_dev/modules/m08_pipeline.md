# M08 — Sales Pipeline · Phát triển Khách hàng mới (Core Doc)

| Mục | Giá trị |
|---|---|
| Module folder | `crm/antmed/` (module Frappe **`AntMed`**, scrubbed = `antmed`) — DocType AntMed mới đặt ở `crm/antmed/doctype/<snake>/` |
| Mở rộng core CRM | `crm/fcrm/doctype/crm_lead/` + `crm/fcrm/doctype/crm_deal/` (chỉ THÊM Custom Field qua fixtures — **KHÔNG sửa JSON gốc**) |
| Code path BE | `crm/api/antmed/pipeline.py` → đường gọi `antmed_crm.api.antmed.pipeline.<fn>` · business rules ở `crm/antmed/pipeline_hooks.py` wire qua `doc_events` |
| FE pages | `frontend/src/pages/AntmedPipeline*.vue` + route `/antmed/pipeline`, `/antmed/pipeline/forecast`, `/antmed/tenders`, `/antmed/tenders/:name` |
| Wave (PLAN) | **W4 — Tăng trưởng & kiểm soát** (Phase 3) |
| Role chính (VI) | `NV kinh doanh`, `Quản lý` · [PLANNED] `Trưởng KD` / `CEO` (xem §4, §7 — đề xuất role VI mới) |
| Phụ thuộc | **M01** (Customer 360°: `AntMed Hospital`, `AntMed Doctor`) |
| Cấp dữ liệu cho | **M02** (Hợp đồng & Quota — lead/thầu trúng → hợp đồng) |
| Site dev | `miyano` |
| Trạng thái | **PLANNED — chưa code** (W4, sau M01..M07) |
| Cập nhật | 2026-06-17 |

> **Trạng thái: [PLANNED — chưa code]**
> Toàn bộ DocType / API / Workflow / BR dưới đây là **DESIGN (đề xuất)**, ground trên: PLAN dòng 50 (`mở rộng CRM Lead/CRM Deal + AntMed Tender`), `AntMed_CRM_Modules.md §8`, scaffold cũ `m08_pipeline/doctype/` (separate-app, prefix `AM `, reuse `Opportunity/Customer/Employee` của ERPNext — đã ADAPT sang in-place + native-lite), `AntMed_CRM_UI_Design.md` (hàng 3 dashboard + bảng module #8). Chưa có dòng code nào trên site `miyano`.

---

## 1. Overview

M08 là module **phát triển khách hàng mới** — phễu (pipeline) đưa một **bệnh viện chưa ký hợp đồng** đi từ tiếp cận đến trúng/trượt thầu, rồi **bàn giao sang M02** để lập `AntMed Contract` + quota. Trong 14 module, M08 nằm ở **đầu vòng đời thương mại**: M01 (master BV/bác sỹ) → **M08 (lead → thầu → trúng)** → M02 (hợp đồng/quota) → M09 (đơn/AR). Đây là một trong số ít module **mở rộng trực tiếp Frappe CRM gốc** — lợi thế in-place: tái dùng nguyên `CRM Lead` / `CRM Deal` (đã có status, pipeline, owner, activity timeline, kanban) và chỉ **THÊM** lớp y tế (BV mục tiêu, nguồn thầu, ngày mở thầu) + DocType `AntMed Tender` để theo dõi gói thầu công (cổng muasamcong).

**Vai trò khác biệt vs CRM thường:** CRM gốc dừng ở "Deal Won". Ngành VTYT thì "won" = **trúng gói thầu công** → cần theo dõi *lịch mở thầu*, *số quyết định phê duyệt KQLCNT*, *giá trị gói*, *xác suất trúng theo giai đoạn* để **forecast doanh thu trọng số**, và khi trúng thì **derive sang hợp đồng (M02)**.

**Business value:**
- NV kinh doanh có một phễu trực quan (kanban) theo 5 giai đoạn ngành VTYT: **Tiếp cận → Khảo sát → Báo giá → Dự thầu → Trúng/Trượt**.
- Trưởng KD / CEO nhìn **forecast theo xác suất** (weighted pipeline) để dự báo doanh số quý.
- Khi một thầu **Trúng**, hệ thống gợi ý tạo `AntMed Contract` (M02) — nối liền lead→hợp đồng, không nhập tay lại.

**User stories:**
- *NV kinh doanh* mở **Pipeline kanban**, kéo một bệnh viện tiềm năng từ "Khảo sát" sang "Báo giá", đính kèm hồ sơ báo giá, set xác suất trúng 60%.
- *NV kinh doanh* tạo một **AntMed Tender** cho gói thầu công của BV mục tiêu (nguồn muasamcong, ngày mở thầu), nộp hồ sơ dự thầu, cập nhật kết quả **Trúng**.
- *Trưởng KD* mở **trang Forecast**, xem tổng doanh thu dự báo (Σ giá trị × xác suất) theo kỳ/vùng/NV để báo cáo BGĐ.

---

## 2. DocTypes (native-lite, [PLANNED])

> Nguyên tắc: **tái dùng tối đa core CRM**, chỉ thêm trường y tế qua **Custom Field (fixtures)** lên `CRM Lead`/`CRM Deal` (additive, không sửa JSON gốc), và thêm DocType AntMed mới cho phần gói thầu/forecast. Scaffold cũ dùng ERPNext `Opportunity`/`Customer`/`Employee` → ADAPT: `Opportunity`→`CRM Deal`, `Customer`→`AntMed Hospital`, `Employee`→`User` (NV kinh doanh là Frappe `User`, khớp M01/M14).

### 2a. Mở rộng core CRM (Custom Field — additive)

| DocType core | Custom Field ĐỀ XUẤT (fieldname · label · type · options) | Nguồn | Ghi chú |
|---|---|---|---|
| `CRM Lead` | `antmed_target_hospital` · BV mục tiêu · Link → `AntMed Hospital` | scaffold `am_tender_lead_info.target_hospital` (Customer→AntMed Hospital) | thay cho child doctype `AM Tender Lead Info` — gộp thẳng vào Lead |
| `CRM Lead` | `antmed_tender_source` · Nguồn thầu · Select `muasamcong\nGiới thiệu\nHội nghị\nGọi nguội\nWeb\nKhác` | scaffold `tender_source` + Modules §8 | options tiếng Việt |
| `CRM Lead` | `antmed_expected_bid_open_date` · Ngày dự kiến mở thầu · Date | scaffold `expected_bid_open_date` | — |
| `CRM Deal` | `antmed_pipeline_stage` · Giai đoạn VTYT · Select `Tiếp cận\nKhảo sát\nBáo giá\nDự thầu\nTrúng\nTrượt` | scaffold `am_tender_opportunity.stage` | xem §3 (giai đoạn ↔ workflow) |
| `CRM Deal` | `antmed_win_probability_pct` · Xác suất trúng % · Percent | scaffold `win_probability_pct` | nhập tay HOẶC derive theo stage (xem BR-M08-02) |
| `CRM Deal` | `antmed_forecast_value` · Doanh thu dự báo · Currency | scaffold `forecast_value` | giá trị kỳ vọng gói thầu |
| `CRM Deal` | `antmed_hospital` · Bệnh viện · Link → `AntMed Hospital` | adapt `Customer` | nối Deal về master BV (M01) |
| `CRM Deal` | `antmed_tender` · Gói thầu · Link → `AntMed Tender` | mới | Deal ↔ Tender (1 Deal có thể gắn 1 gói thầu) |

> [cần khảo sát] Có thể tái dùng **status có sẵn** của `CRM Deal` (`CRM Deal Status` là DocType cấu hình được) thay vì thêm `antmed_pipeline_stage`. Đề xuất mặc định: thêm field riêng `antmed_pipeline_stage` để **không đụng** danh sách status gốc mà đội CRM thường đang dùng (additive an toàn). Quyết định cuối → ADR-M08-01.

### 2b. DocType AntMed mới

| DocType | Loại | Field chính ĐỀ XUẤT | naming series | Nguồn |
|---|---|---|---|---|
| **`AntMed Tender`** | txn | `tender_no` (Data, unique — mã KHLCNT/gói thầu), `tender_name` (Data, title), `hospital` (Link→`AntMed Hospital`, reqd), `deal` (Link→`CRM Deal`), `source` (Select `muasamcong\nGiới thiệu\nHội nghị\nKhác`), `bid_open_date` (Date — ngày mở thầu), `bid_close_date` (Date — hạn nộp HSDT), `estimated_value` (Currency — giá gói thầu), `win_probability_pct` (Percent), `workflow_state` (xem §3), `decision_no` (Data — số QĐ phê duyệt KQLCNT), `result` (Select `Đang theo dõi\nTrúng\nTrượt`), `won_contract` (Link→`AntMed Contract` — M02), `bid_documents` (Attach — HSDT) | `AM-TND-.YYYY.-.####` | scaffold `am_tender_opportunity` + `am_tender_bid` gộp lại; ADAPT `won_contract`: `AM Tender Contract`→`AntMed Contract` (M02) |
| **`AntMed Sales Forecast`** [PLANNED] | log/snapshot | `period` (Data — kỳ, vd `2026-Q3`), `sales_rep` (Link→`User` — thay `Employee`), `region` (Data — vùng), `weighted_value` (Currency — Σ giá trị×xác suất), `deal_count` (Int), `computed_at` (Datetime) | `hash` (Random) | scaffold `am_sales_forecast` (Employee→User) |

> **Đã loại khỏi scaffold:**
> - `AM Tender Lead Info` (autoname `field:lead`, child của Lead) → **gộp vào Custom Field trên `CRM Lead`** (§2a) — đơn giản hơn, tránh DocType vệ tinh.
> - `AM Tender Opportunity` (autoname `field:opportunity`) → các trường (stage/win%/forecast/bid_documents) **chuyển vào `CRM Deal` Custom Field** + `AntMed Tender`. Không tạo DocType `AntMed Tender Opportunity` riêng (tránh trùng `CRM Deal`).
> - `AM Tender Bid` (is_submittable) → **gộp vào `AntMed Tender`** (các field `bid_no`/`submitted_at`/`result`/`won_contract`); một gói thầu = một bản ghi `AntMed Tender` có workflow, không tách bid riêng cho slice đầu.
> - **KHÔNG** reuse ERPNext `Opportunity`/`Customer`/`Employee` (native-lite D1). `Opportunity`→`CRM Deal`; `Customer`→`AntMed Hospital`; `Employee`→`User`.

> `AntMed Sales Forecast` đánh dấu [PLANNED] và có thể thay bằng **report thuần** (tính on-the-fly từ `CRM Deal` qua API `forecast`, không snapshot) cho slice đầu — xem §8 Build slices. Snapshot DocType chỉ cần khi muốn lưu lịch sử forecast theo thời gian.

---

## 3. Workflow

M08 có **một** state machine cho `AntMed Tender` (gói thầu) = **Frappe-native Workflow** (fixture `crm/fixtures/workflow.json` + `docstatus`). `CRM Lead`/`CRM Deal` **giữ nguyên** status/pipeline gốc của Frappe CRM (KHÔNG thêm workflow lên doctype gốc — chỉ Custom Field hiển thị).

**Workflow `AntMed Tender Workflow`** — field trạng thái: `workflow_state`. Giai đoạn ngành VTYT theo Modules §8 + UI hàng 3:

| State (VI) | docstatus | Mô tả | Role được vào |
|---|---|---|---|
| `Tiếp cận` | 0 (Draft) | Đã xác định gói thầu/BV mục tiêu | NV kinh doanh |
| `Khảo sát` | 0 | Khảo sát nhu cầu, danh mục VTYT BV cần | NV kinh doanh |
| `Báo giá` | 0 | Đã gửi báo giá / mẫu thử | NV kinh doanh |
| `Dự thầu` | 0 | Đã nộp HSDT (hồ sơ dự thầu) | NV kinh doanh |
| `Trúng` | 1 (Submitted) | Trúng thầu — có số QĐ KQLCNT → khoá, bàn giao M02 | Quản lý / Trưởng KD |
| `Trượt` | 1 (Submitted) | Trượt thầu — đóng phễu | Quản lý / Trưởng KD |

**Transitions ĐỀ XUẤT (tuyến tính + nhánh kết quả):**

| Từ | Hành động | Đến | Role | Điều kiện |
|---|---|---|---|---|
| `Tiếp cận` | Khảo sát | `Khảo sát` | NV kinh doanh | — |
| `Khảo sát` | Báo giá | `Báo giá` | NV kinh doanh | — |
| `Báo giá` | Dự thầu | `Dự thầu` | NV kinh doanh | `bid_documents` đã đính kèm (BR-M08-03) |
| `Dự thầu` | Ghi nhận trúng | `Trúng` | Quản lý / Trưởng KD | `decision_no` reqd (BR-M08-04) |
| `Dự thầu` | Ghi nhận trượt | `Trượt` | Quản lý / Trưởng KD | — |
| `Tiếp cận`/`Khảo sát`/`Báo giá` | Hủy theo dõi | `Trượt` | Quản lý | (đóng sớm gói không khả thi) |

> Trạng thái `Trúng`/`Trượt` đặt `docstatus=1` (submit) để **khoá** gói thầu sau khi có kết quả (chứng từ pháp lý). Amend/cancel chỉ `Quản lý`.

---

## 4. Business Rules

> M08 chưa có BR-01..15 nào trong danh sách chuẩn (README dòng 203–217 — các BR đó thuộc M02/M03/M04/M05/M06/M09/M14). M08 đề xuất **BR cấp module** `BR-M08-xx` (enforce trong `crm/antmed/pipeline_hooks.py` qua `doc_events`, hoặc controller `AntMed Tender.validate`). Tất cả message tiếng Việt, prefix mã BR.

| Mã | Mô tả | Nơi enforce |
|---|---|---|
| **BR-M08-01** | Mã gói thầu `tender_no` không trùng (chống nhập 2 lần cùng KHLCNT). | `AntMed Tender.validate` (controller) — hoặc `unique:1` trên field |
| **BR-M08-02** | Khi `result` = `Trúng` → `decision_no` (số QĐ phê duyệt KQLCNT) **bắt buộc**. `frappe.throw(_("BR-M08-02: Phải nhập số quyết định phê duyệt kết quả lựa chọn nhà thầu khi ghi nhận Trúng"))`. | `AntMed Tender.validate` (gate state `Trúng`) |
| **BR-M08-03** | Chuyển sang `Dự thầu` yêu cầu có hồ sơ dự thầu (`bid_documents` attach). `frappe.throw(_("BR-M08-03: Phải đính kèm hồ sơ dự thầu trước khi chuyển trạng thái Dự thầu"))`. | transition gate (`pipeline_hooks.before_workflow_action`) |
| **BR-M08-04** | `win_probability_pct` ∈ [0,100]; khi state `Trúng`→100, `Trượt`→0 (derive, chống lệch forecast). | `AntMed Tender.validate` / `CRM Deal` doc_events `validate` |
| **BR-M08-05** | Khi `AntMed Tender` đạt `Trúng` (on_submit) → **gợi ý/auto tạo** `AntMed Contract` (M02) với `hospital`, `tender` link. Không tạo trùng nếu `won_contract` đã set. | `pipeline_hooks.on_submit_tender` (lazy-import M02 — xem §6) |
| **BR-M08-06** | [PLANNED] Data-scope: NV kinh doanh chỉ thấy Tender/Deal mình phụ trách (`owner`/`lead_owner`). | `permission_query_conditions` (M14/W4 — đồng bộ BR-13; **hoãn** như ADR-M01-05) |

> **Tái dùng business logic core CRM:** chuyển status, kanban, assignment, activity timeline của `CRM Lead`/`CRM Deal` là **của Frappe CRM gốc** — M08 KHÔNG viết lại, chỉ THÊM validate trên Custom Field (vd BR-M08-04 trên `CRM Deal.validate` qua `doc_events`, KHÔNG sửa controller gốc).

---

## 5. API

> File: `crm/api/antmed/pipeline.py`. Mọi hàm `@frappe.whitelist(methods=["GET"|"POST"])`, **type-annotated** (`crm/hooks.py:28`), trả **RAW dict/list** (KHÔNG `_ok/_err` envelope). Lỗi nghiệp vụ = `frappe.throw(_("BR-M08-..."))`. List endpoint giữ invariant **count == rows** (`get_list(pluck=…, limit_page_length=0)` để đếm, không cắt bởi page_length).

| Endpoint (`antmed_crm.api.antmed.pipeline.<fn>`) | Verb | Mô tả |
|---|---|---|
| `list_pipeline` | GET | List `CRM Deal` (lọc các deal có `antmed_pipeline_stage`) cho kanban — trả `{data, total_count}`; mỗi item: `name`, `organization`/`antmed_hospital`, `antmed_pipeline_stage`, `antmed_win_probability_pct`, `antmed_forecast_value`, `deal_owner`. **count==rows**. |
| `get_pipeline_board` | GET | Trả deal **gom theo giai đoạn** cho kanban: `{ "Tiếp cận": [...], "Khảo sát": [...], ... }`. Tổng số item = count (invariant). |
| `move_stage` | POST | Đổi `antmed_pipeline_stage` của 1 `CRM Deal` (kéo-thả kanban). Params: `deal`, `stage`. Áp BR-M08-04 (derive win%). Trả deal đã cập nhật. |
| `list_tenders` | GET | List `AntMed Tender` — `{data, total_count}`; item: `name`, `tender_no`, `tender_name`, `hospital`, `bid_open_date`, `estimated_value`, `workflow_state`, `result`. **count==rows**. Lọc theo `hospital`/`workflow_state`/`result`. |
| `get_tender` | GET | Chi tiết 1 gói thầu + resolve `hospital_name` (Link M01) + `deal` info. Throw `PermissionError` nếu thiếu read-perm. |
| `create_tender` | POST | Tạo `AntMed Tender` (kèm validate BR-M08-01). Trả `{name}`. |
| `set_tender_result` | POST | Ghi nhận kết quả (`Trúng`/`Trượt`) + `decision_no` → trigger workflow action (BR-M08-02). Trả tender đã submit. |
| `forecast` | GET | Tính **doanh thu dự báo trọng số** = Σ(`antmed_forecast_value` × `antmed_win_probability_pct`/100) trên các `CRM Deal` đang mở, gom theo `period`/`region`/`sales_rep`. Trả `{ "rows": [...], "total_weighted": <currency> }`. (Nếu có `AntMed Sales Forecast` thì đọc snapshot; mặc định tính on-the-fly.) |

> **Lưu ý FE shape** (như M01): list trả dict bọc `{data, total_count}` → FE dùng `createResource` đọc `r.data.data`, KHÔNG để frappe-ui coi response là array thuần.

---

## 6. Integration (doc_events vào/ra theo DAG)

Dependency DAG (PLAN dòng 63): `M01 ─► M08 ─► M02`.

**Vào (M08 phụ thuộc M01):**
- `AntMed Tender.hospital` + `CRM Deal.antmed_hospital`/`CRM Lead.antmed_target_hospital` Link→`AntMed Hospital` (M01). M08 chỉ **đọc** master BV — không sửa.

**Ra (M08 cấp dữ liệu cho M02):**
- `pipeline_hooks.on_submit_tender` (doc_event `AntMed Tender` → `on_submit`): khi `result=Trúng` → **lazy-import** module M02 và tạo/gợi ý `AntMed Contract`, truyền **PK** (`hospital`, `tender.name`, `estimated_value`), set `won_contract` ngược lại. Pattern: `from crm.antmed import contract_hooks` *bên trong hàm* (lazy) để tránh import vòng + giữ M08 chạy được cả khi M02 chưa land (guard `if frappe.db.exists("DocType", "AntMed Contract")`).

**Wiring `crm/hooks.py` (THÊM key — KHÔNG sửa key gốc):**
```python
doc_events = {
  "AntMed Tender": {
    "validate": "crm.antmed.pipeline_hooks.validate_tender",
    "on_submit": "crm.antmed.pipeline_hooks.on_submit_tender",
  },
  "CRM Deal": {  # additive — chỉ validate Custom Field AntMed, KHÔNG đụng logic gốc
    "validate": "crm.antmed.pipeline_hooks.validate_deal_forecast",
  },
}
```
- Fixtures: `crm/fixtures/workflow.json` (+ `AntMed Tender Workflow`), `crm/fixtures/custom_field.json` (Custom Field §2a trên `CRM Lead`/`CRM Deal`), `crm/fixtures/role.json` (nếu thêm role VI mới `Trưởng KD`/`CEO`), `crm/fixtures/workflow_state.json`/`workflow_action_master.json` cho state/action VI.
- **Gate compliance:** M08 không có gate CO/CQ/HĐĐT (đó là M03/M06). Gate duy nhất = BR-M08-02 (decision_no khi Trúng) + BR-M08-05 (bàn giao M02).

---

## 7. UI

> Vue 3 + frappe-ui SPA. Route APPEND vào `frontend/src/router.js` (lazy). Gọi `antmed_crm.api.antmed.pipeline.*`. KHÔNG đụng route/page CRM gốc (Leads/Deals gốc vẫn chạy song song). Nguồn màn hình: `AntMed_CRM_UI_Design.md` hàng 3 dashboard (Funnel: Lead→Khảo sát→Báo giá→Dự thầu→Trúng) + bảng module #8 (Kanban pipeline, Báo giá; role NV KD, Trưởng KD, CEO).

### Routes (THÊM mới — lazy)

| path | name | component | mô tả | role |
|---|---|---|---|---|
| `/antmed/pipeline` | `AntmedPipeline` | `pages/AntmedPipeline.vue` | **Kanban** 6 cột (Tiếp cận→…→Trúng/Trượt), kéo-thả deal | NV kinh doanh, Trưởng KD |
| `/antmed/pipeline/forecast` | `AntmedForecast` | `pages/AntmedForecast.vue` | Bảng/biểu đồ **forecast trọng số** theo kỳ/vùng/NV | Trưởng KD, CEO |
| `/antmed/tenders` | `AntmedTenders` | `pages/AntmedTenders.vue` | List gói thầu công (muasamcong) + lọc theo BV/trạng thái | NV kinh doanh, Trưởng KD |
| `/antmed/tenders/:name` | `AntmedTenderDetail` | `pages/AntmedTenderDetail.vue` | Chi tiết gói thầu + workflow action (Khảo sát→…→Trúng) + đính kèm HSDT | NV kinh doanh, Quản lý |

- **Kanban** (`AntmedPipeline.vue`): `createResource` gọi `get_pipeline_board`; kéo-thả → `move_stage` (POST). Mỗi card: tên BV, giá trị dự báo, xác suất %. Badge màu theo giai đoạn (design token frappe-ui, KHÔNG hex thô).
- **Forecast** (`AntmedForecast.vue`): `createResource` gọi `forecast`; hiển thị tổng `total_weighted` + breakdown. Nhãn VN qua `__()`.
- **Tender detail**: nút workflow theo state hiện tại (frappe-ui), form `decision_no` khi chọn "Ghi nhận trúng" (BR-M08-02), Attach HSDT (BR-M08-03).
- A11y: aria-live cho cập nhật kanban, role=alert cho lỗi BR, focus-ring. Loading/error/empty cho mỗi resource.

---

## 8. Build slices (vertical, cho factory — mỗi slice 1 vòng)

1. **Slice 8.1 — Pipeline trên core CRM (Lead/Deal extend).** Custom Field §2a (fixtures `custom_field.json`) lên `CRM Lead`/`CRM Deal`; API `list_pipeline` + `get_pipeline_board` + `move_stage`; `pipeline_hooks.validate_deal_forecast` (BR-M08-04); FE `AntmedPipeline.vue` kanban. TDD BE + vitest FE. *Lợi thế in-place: tái dùng toàn bộ Deal gốc.*
2. **Slice 8.2 — AntMed Tender + Workflow.** DocType `AntMed Tender` + workflow fixture (6 state VI); controller `validate` (BR-M08-01/02/03); API `list_tenders`/`get_tender`/`create_tender`/`set_tender_result`; FE `AntmedTenders.vue` + `AntmedTenderDetail.vue` (workflow action).
3. **Slice 8.3 — Forecast.** API `forecast` (tính trọng số on-the-fly); FE `AntmedForecast.vue`. (Tùy chọn: thêm DocType `AntMed Sales Forecast` snapshot + scheduler tính định kỳ — [PLANNED], chỉ khi cần lịch sử.)
4. **Slice 8.4 — Bàn giao M02 (integration).** `pipeline_hooks.on_submit_tender` (BR-M08-05) lazy-import M02 tạo `AntMed Contract` khi Trúng. *Chỉ chạy được sau khi M02 land — guard `frappe.db.exists`.*

---

## 9. ADRs

### ADR-M08-01: Mở rộng `CRM Lead`/`CRM Deal` bằng Custom Field, thêm `AntMed Tender` (KHÔNG tạo DocType `Opportunity` mới)
- **Status**: Proposed
- **Date**: 2026-06-17
- **Context**: Scaffold cũ (separate-app) dựng `AM Tender Opportunity`/`AM Tender Lead Info` quanh ERPNext `Opportunity`/`Lead`. In-place, Frappe CRM **đã có** `CRM Lead`/`CRM Deal` với pipeline/status/kanban/owner/timeline đầy đủ. Tái dựng DocType phễu riêng = trùng lặp + bỏ phí hạ tầng CRM gốc.
- **Decision**: Phần phễu (lead→deal→won) **dùng nguyên `CRM Lead`/`CRM Deal`**, chỉ THÊM Custom Field y tế (BV mục tiêu, nguồn thầu, giai đoạn VTYT, xác suất, forecast). Phần **gói thầu công** (lịch mở thầu, số QĐ KQLCNT, kết quả, có workflow + docstatus) tách thành DocType mới **`AntMed Tender`**.
- **Alternatives**: (a) DocType phễu AntMed riêng — loại: trùng `CRM Deal`, mất kanban/timeline gốc, đụng nguyên tắc tận-dụng in-place. (b) Nhồi cả gói thầu vào `CRM Deal` — loại: gói thầu cần workflow submit/khoá + field pháp lý (QĐ KQLCNT) không hợp với Deal gốc.
- **Consequences**: (+) Tận dụng tối đa CRM gốc, additive thuần (no-regression). (+) Tender độc lập có workflow/audit. (−) Phải đồng bộ `antmed_pipeline_stage` (Deal) ↔ `workflow_state` (Tender) khi 2 thực thể gắn nhau — quy ước: Tender là nguồn chân lý của giai đoạn thầu, Deal mirror để kanban.

### ADR-M08-02: Forecast tính on-the-fly trước, snapshot DocType sau ([PLANNED])
- **Status**: Proposed
- **Context**: Scaffold có `AM Sales Forecast` (snapshot, autoname hash). Slice đầu chỉ cần xem forecast hiện tại.
- **Decision**: API `forecast` **tính trọng số on-the-fly** từ `CRM Deal` đang mở. `AntMed Sales Forecast` (snapshot lịch sử + scheduler) là [PLANNED], chỉ thêm khi cần so sánh forecast theo thời gian.
- **Consequences**: (+) Slice gọn, không scheduler/migration sớm. (−) Chưa có lịch sử forecast cho tới khi land snapshot.

> Kế thừa: **ADR-M01-01** (in-place), **ADR-M01-02** (prefix `AntMed `), **ADR-M01-05** (hoãn data-scope BR-13 → áp cho BR-M08-06), **DEC-A** (role VI), **DEC-B** (route `/antmed/*` riêng). D1 (native-lite, KHÔNG ERPNext) + D2 (Frappe Workflow gốc) chi phối §2/§3.

---

## 10. Acceptance / DoD (theo SPEC §6)

**BE (TDD — `Ran N OK`, 0 fail):** `bench --site miyano run-tests --module crm.tests.test_antmed_pipeline`
1. Custom Field §2a tồn tại trên `CRM Lead`/`CRM Deal` sau migrate (`frappe.get_meta` chứa `antmed_pipeline_stage`, `antmed_win_probability_pct`, `antmed_forecast_value`, `antmed_hospital`).
2. `AntMed Tender` tồn tại + naming `AM-TND-…`; `tender_no` unique (BR-M08-01 → DuplicateEntryError).
3. Workflow `AntMed Tender Workflow` có 6 state VI; transition `Dự thầu`→`Trúng` set `docstatus=1`.
4. `set_tender_result(result="Trúng")` **không có** `decision_no` → raise BR-M08-02 (`frappe.throw`). Có `decision_no` → submit OK.
5. `list_pipeline`/`list_tenders` trả `{data, total_count}`, **`len(data) == total_count`** khi không phân trang (count==rows).
6. `get_pipeline_board` tổng item các cột == count.
7. `forecast` trả `total_weighted` = Σ(forecast×prob/100) đúng trên fixture deal.
8. Permission: user thiếu read-perm gọi `get_tender` → `frappe.PermissionError`.
9. BR-M08-05: tender Trúng (on_submit) tạo/gợi ý `AntMed Contract` (test với guard `exists`; nếu M02 chưa land → no-op không lỗi).

**No-regression:** `test_antmed_bootstrap` + `test_antmed_customer` + 4 test gốc CRM (Lead/Task/Territory/org_hierarchy) còn xanh; pipeline/kanban **Deal gốc** không đổi hành vi.

**FE (vitest + build):** `yarn vitest run` xanh — 4 route mới tồn tại (path/name/lazy), page gọi đúng `antmed_crm.api.antmed.pipeline.*`, kanban gọi `get_pipeline_board`+`move_stage`, KHÔNG `antmed_crm.api`/axios/tanstack; `yarn build` emit chunk `AntmedPipeline*` không vỡ.

**Pixel (sau USER reload, Playwright cổng 80 login):** `/antmed/pipeline` render kanban thật, kéo-thả cập nhật stage (API 200); `/antmed/tenders` list + detail workflow action; `/antmed/pipeline/forecast` hiện tổng trọng số; 0 console error.

> Chưa pixel-verify ⇒ chỉ "contract verified", chưa "xong" (SPEC §6).

---

## Tham chiếu chéo
- Spec dự án: `../SPEC_AntMed_CRM.md` (§2 stack, §5 convention, §6 DoD, §8 ADR/DEC).
- Kế hoạch/Wave/DAG: `../PLAN_AntMed_CRM.md` (dòng 50 M08 row · dòng 63 DAG `M01→M08→M02` · dòng 79 W4).
- Nghiệp vụ: `../../antmed_crm/docs/AntMed_CRM_Modules.md` §8 (Sales Pipeline — 5 giai đoạn, forecast, lịch đấu thầu công, báo giá).
- UI: `../../antmed_crm/docs/AntMed_CRM_UI_Design.md` (dashboard hàng 3 funnel · bảng module #8 Kanban/Báo giá).
- House style: `./m01_customer360.md` (metadata table, ADR block, count==rows, RAW dict, DoD).
- Scaffold tham khảo (ADAPT, KHÔNG copy): `docs/antmed_crm/antmed_crm/m08_pipeline/doctype/` — `am_tender_opportunity`, `am_tender_bid`, `am_tender_lead_info`, `am_sales_forecast`.
- Module liên quan: M01 (`AntMed Hospital`/`AntMed Doctor`), M02 (`AntMed Contract`/quota — consumer của tender Trúng), M14 (data-scope BR-13/BR-M08-06).
