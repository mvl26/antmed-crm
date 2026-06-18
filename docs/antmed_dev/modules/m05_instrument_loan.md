# M05 — Cho mượn Bộ Dụng cụ Phẫu thuật (Core Doc)

| Mục | Giá trị |
|---|---|
| Module folder | `crm/antmed/` (module Frappe **`AntMed`**, scrubbed = `antmed`) |
| DocType folder | `crm/antmed/doctype/antmed_instrument_set/`, `.../antmed_instrument_loan/`, `.../antmed_sterilization/`, + child `.../antmed_instrument_set_component/`, `.../antmed_loan_checklist_item/`, `.../antmed_loan_incident/` |
| Code path BE | `crm/api/antmed/instrument_loan.py` → `antmed_crm.api.antmed.instrument_loan.<fn>` · module hooks `crm/antmed/instrument_loan_hooks.py` (wired qua `doc_events` trong `crm/hooks.py`) |
| FE pages | `frontend/src/pages/AntmedInstrumentSets.vue`, `AntmedInstrumentLoan.vue` (3 tab), `AntmedInstrumentSetDetail.vue` + route `/antmed/instrument-sets`, `/antmed/loans`, `/antmed/loans/:name` |
| Wave (PLAN) | **W3 — Đặc thù AntMed** (điểm nhấn cạnh tranh; chạy ‖ M07, sau W1) |
| Role chính (VI) | `NV kinh doanh` (đặt/bàn giao/nhận trả), `Thủ kho` (tiệt khuẩn + mark Sẵn sàng), `Quản lý` (giám sát/sự cố) — DEC-A |
| Phụ thuộc | **M01** (`AntMed Hospital`, `AntMed Doctor`) · **M03** (kho — `AntMed Warehouse` để định vị bộ ở kho cá nhân NV) |
| Cấp dữ liệu cho | **M10** (KPI: tỷ lệ bộ trả đủ-đúng-hạn, vòng quay bộ, sự cố mất/hư) |
| Site dev | `miyano` |
| Trạng thái | **PLANNED — chưa code** (xây mới hoàn toàn) |
| Cập nhật | 2026-06-17 |

> **Trạng thái: [PLANNED — chưa code]**
> Toàn bộ schema/API/workflow dưới đây là **DESIGN (đề xuất)**, ground trên scaffold cũ (separate-app, prefix `AM `) đã ADAPT sang in-place native-lite (`AntMed `). Chưa có DocType/endpoint nào tồn tại trên site `miyano`. Mọi mục không truy được nguồn → đánh dấu `[UNVERIFIED]` / `[cần khảo sát]`.

---

## 1. Overview

M05 là **module đặc thù AntMed** — không có trong Frappe CRM gốc, **xây mới hoàn toàn** (`AntMed_CRM_Modules.md §5` + bảng dòng 145). Đây là lợi thế cạnh tranh lõi của AntMed (cùng M04 giao phòng mổ): quản trị **vòng đời bộ dụng cụ phẫu thuật cho bệnh viện mượn**, từ đặt mượn → bàn giao tại phòng mổ → nhận về → làm sạch/tiệt khuẩn → sẵn sàng lại, có **checklist chụp ảnh từng món** và **chứng minh tuân thủ** (ai tiệt khuẩn, kết quả Pass/Fail, ngày sẵn sàng lại) phục vụ thanh kiểm tra ngành y tế.

**Vai trò trong 14 module:** M05 treo vào M01 (BV + bác sỹ) và M03 (kho cá nhân NV nắm giữ bộ); cấp KPI cho M10. Khác biệt vs CRM thường: tài sản giá trị cao (bộ dụng cụ là tài sản, không phải vật tư tiêu hao), vòng đời **7 trạng thái** có ràng buộc tiệt khuẩn (BR-09), và rủi ro mất/hư cần biên bản + tính phí.

**Business value:** giảm thất lạc/hư hỏng bộ giá trị cao; bằng chứng tiệt khuẩn cho BV; cảnh báo trùng lịch (1 bộ không đặt 2 ca cùng giờ) và quá hạn trả; dữ liệu tần suất → quyết định mua thêm bộ.

**User stories:**
- *NV kinh doanh* mở tab **Đang giữ**, chọn 1 bộ → **Bàn giao mượn**: mở checklist từng món, chụp ảnh, ký bác sỹ/điều dưỡng → bộ chuyển *Đang sử dụng tại BV*.
- *NV kinh doanh* **Nhận trả**: checklist nhận lại, đánh dấu đủ/thiếu/hư; nếu thiếu/hư → tạo **Sự cố** (biên bản, tính phí BV).
- *Thủ kho* nhận bộ đã trả, ghi **bản ghi tiệt khuẩn** (phương pháp Hấp/EO/Plasma, Pass/Fail, ảnh) → chỉ khi **Pass** mới được **mark Sẵn sàng** lại (BR-09).
- *Hệ thống* cảnh báo realtime khi bộ **quá hạn trả** và chặn **đặt trùng lịch** cùng bộ (BR-05).

### 6 câu hỏi domain — feasibility check (BA Bước 2)

| # | Câu hỏi | Trả lời M05 |
|---|---|---|
| 1 | **CRM stage?** | Giai đoạn **vận hành dịch vụ** (sau khi có quan hệ BV/bác sỹ M01). Không thuộc lead/thầu. |
| 2 | **Ràng buộc hợp đồng/quota?** | **KHÔNG** trực tiếp. Mượn bộ là dịch vụ kèm, không trừ quota M02. (Nếu BV yêu cầu mượn gắn ca mổ có vật tư → liên kết mềm qua M04, `[cần khảo sát]`.) |
| 3 | **Actor là bệnh viện hay bác sỹ?** | **Cả hai + NV**: bộ thuộc AntMed, NV kinh doanh là người giữ/bàn giao; BV là nơi dùng; bác sỹ ký nhận. |
| 4 | **Nghĩa vụ chứng từ / HĐĐT?** | **KHÔNG** phát hành HĐĐT cho mượn bộ. Chứng từ tuân thủ ở đây = **biên bản bàn giao/nhận trả + bản ghi tiệt khuẩn** (nội bộ, không qua M06). Sự cố mất/hư có thể sinh phí → liên kết M09 `[ROADMAP]`. |
| 5 | **Truy vết lot / thu hồi?** | Không lot vật tư. Nhưng **truy vết bộ + thành phần món** (component) + lịch sử tiệt khuẩn là cốt lõi tuân thủ. |
| 6 | **Hậu quả nếu data sai?** | **Cao**: bộ chưa tiệt khuẩn bị cho mượn = rủi ro nhiễm khuẩn ca mổ → BR-09 là **hard rule**. Mất bộ giá trị cao không có biên bản = thất thoát tài sản. |

---

## 2. DocTypes (native-lite, [PLANNED])

> Ground @ scaffold `docs/antmed_crm/antmed_crm/m05_instrument_loan/doctype/` (prefix cũ `AM `) + `AntMed_CRM_Modules.md §5`. ADAPT: `AM `→`AntMed `; **bỏ Link→`Asset` (ERPNext-reuse)** thay bằng field native; **Link→`Customer`→`AntMed Hospital`**, **Link→`AM Doctor`→`AntMed Doctor`**; module `M05 Instrument Loan`→`AntMed`. Field giữ đúng tinh thần scaffold, chỉ scrub tên.

| DocType | Loại | Field chính (ĐỀ XUẤT — grounded) | Naming |
|---|---|---|---|
| **AntMed Instrument Set** | master | `set_code`(Data, reqd, unique), `surgery_type`(Select: `Chấn thương chỉnh hình`/`Sọ não`/`Tim mạch`/`Tiết niệu`/`Khác`), `asset_value`(Currency), `supplier`(Data — nhà cung cấp), `max_loans`(Int), `lifetime_loans`(Int, read_only, default 0), `current_status`(Select 8 trị — xem §3), `current_holder`(Link→`Employee`), `current_warehouse`(Link→`AntMed Warehouse` — kho cá nhân NV đang giữ, M03), child `components`(Table→`AntMed Instrument Set Component`) | `field:set_code` (naming_rule **By fieldname**) |
| **AntMed Instrument Loan** | txn (submittable) | `naming_series`, `instrument_set`(Link→`AntMed Instrument Set`, reqd), `hospital`(Link→**`AntMed Hospital`**, reqd), `doctor`(Link→**`AntMed Doctor`**), `employee`(Link→`Employee` — NV mang), `surgery_case`(Data — ca mổ), `booked_at`/`loaned_at`/`due_return_at`/`returned_at`(Datetime), `workflow_state`(Select — xem §3), child `handover_checklist` & `return_checklist`(Table→`AntMed Loan Checklist Item`) | `AntMed-LN-.YYYY.-.#####` |
| **AntMed Sterilization** | log (txn) | `naming_series`, `loan`(Link→`AntMed Instrument Loan`, reqd), `instrument_set`(Link→`AntMed Instrument Set` — denorm để truy bộ), `method`(Select: `Hấp`/`EO`/`Plasma`, reqd), `operator`(Link→`Employee` hoặc Data), `started_at`/`ended_at`(Datetime), `result`(Select: `Pass`/`Fail`, reqd), `evidence_photos`(Long Text — JSON urls / hoặc child Attach) | `AntMed-STR-.YYYY.-.#####` |
| **AntMed Instrument Set Component** | child | `component_name`(Data, reqd), `qty`(Int, default 1), `reference_photo`(Attach Image — ảnh chuẩn), `criticality`(Select: `Critical`/`Normal`) | `hash` (istable) |
| **AntMed Loan Checklist Item** | child | `component_name`(Data, reqd), `expected`(Int, default 1), `condition`(Select: `OK`/`Missing`/`Damaged`), `photo`(Attach Image — chụp ảnh từng món), `signed_by`(Data — ký BS/ĐD) | `hash` (istable) |
| **AntMed Loan Incident** | txn (submittable) | `naming_series`, `loan`(Link→`AntMed Instrument Loan`, reqd), `type`(Select: `Missing`/`Damaged`/`Late`, reqd), `value_estimated`(Currency), `bien_ban_file`(Attach — biên bản), `charged_to_hospital`(Check), `description`(Long Text) | `AntMed-INC-.YYYY.-.#####` |

> **ADAPT note (native-lite):** scaffold cũ dùng `asset`(Link→`Asset`) trên Instrument Set + auto-create từ `Asset` (hooks `ensure_instrument_set`). Theo D1 = NATIVE-LITE **bỏ ERPNext Asset** — `AntMed Instrument Set` tự là tài sản (field `asset_value`); KHÔNG auto-create từ Asset. Giá trị tài sản nhập trực tiếp.
> **Hai field trạng thái:** scaffold có `current_status` trên **Set** (8 trị: Ready/Booked/InTransit/InUse/ReturnedToEmployee/InSterilization/Lost/Damaged) và `status` trên **Loan** (7 trị). DESIGN M05 chuẩn hoá: vòng đời 7-state chạy trên **`AntMed Instrument Loan.workflow_state`** (Frappe Workflow); `AntMed Instrument Set.current_status` là **gương phản chiếu** (denorm, set bởi module hooks khi loan đổi state) để biết tức thời 1 bộ đang ở đâu — xem §3, §6. `[cần khảo sát]` nhãn trạng thái Set có cần `Lost`/`Damaged` riêng ngoài 7-state vòng đời (đề xuất: có, vì bộ mất/hư là trạng thái dài hạn của tài sản, không phải state của 1 lượt mượn).

---

## 3. Workflow

**Có state machine** — đây là điểm nhấn M05 (`AntMed_CRM_Modules.md §5` dòng 55). Engine = **Frappe Workflow gốc** (D2): fixture `crm/fixtures/workflow.json` + field `workflow_state` trên `AntMed Instrument Loan`, kết hợp `docstatus` (is_submittable=1). Tên state/transition **tiếng Việt**.

### Vòng đời 7 trạng thái (trên `AntMed Instrument Loan`)

```
Sẵn sàng → Đã đặt → Đang giao → Đang sử dụng tại BV → Đã trả về NV KD
   ↑                                                          │
   └──────────── Đang xử lý/tiệt khuẩn ◄──────────────────────┘
```

| # | State (VI) | docstatus | Ý nghĩa | Set.current_status gương |
|---|---|---|---|---|
| 1 | **Sẵn sàng** | 0 | Bộ rảnh, đã tiệt khuẩn Pass, có thể đặt | `Ready` |
| 2 | **Đã đặt** | 0 | Đã book cho 1 ca/BV (BR-05 chặn trùng) | `Booked` |
| 3 | **Đang giao** | 1 (submit) | NV đang mang tới phòng mổ | `InTransit` |
| 4 | **Đang sử dụng tại BV** | 1 | Đã bàn giao (checklist handover xong), BS đang dùng | `InUse` |
| 5 | **Đã trả về NV KD** | 1 | NV nhận lại (checklist return xong) | `ReturnedToEmployee` |
| 6 | **Đang xử lý/tiệt khuẩn** | 1 | Thủ kho làm sạch + tiệt khuẩn | `InSterilization` |
| 7 | → **Sẵn sàng** (vòng lại) | 0/1 | Sau tiệt khuẩn **Pass** mới quay về Sẵn sàng (BR-09) | `Ready` |

> Nhánh ngoại lệ: từ bất kỳ state đang-giữ → **Sự cố** (tạo `AntMed Loan Incident`) khi mất/hư; bộ chuyển `Lost`/`Damaged` (không quay vòng). `[cần khảo sát]` có dựng state "Sự cố" trong workflow hay xử lý ngoài luồng bằng incident doc — đề xuất: incident doc riêng + module hook set `Set.current_status`, KHÔNG thêm state thứ 8 vào vòng đời lượt mượn.

### Transitions (đề xuất — `workflow.json`)

| Từ → Đến | Action (label VI) | Role được phép | Điều kiện / hiệu lực |
|---|---|---|---|
| Sẵn sàng → Đã đặt | Đặt mượn | `NV kinh doanh` | BR-05: không trùng lịch cùng bộ |
| Đã đặt → Đang giao | Xuất giao | `NV kinh doanh` | submit (docstatus 0→1) |
| Đang giao → Đang sử dụng tại BV | Bàn giao | `NV kinh doanh` | `handover_checklist` đã điền + ký |
| Đang sử dụng tại BV → Đã trả về NV KD | Nhận trả | `NV kinh doanh` | `return_checklist` đã điền; nếu thiếu/hư → gợi ý tạo Sự cố |
| Đã trả về NV KD → Đang xử lý/tiệt khuẩn | Gửi tiệt khuẩn | `Thủ kho` | — |
| Đang xử lý/tiệt khuẩn → Sẵn sàng | Hoàn tất (Sẵn sàng lại) | `Thủ kho` | **BR-09: bắt buộc có `AntMed Sterilization` result=Pass cho loan này** |

> `[UNVERIFIED]` mapping docstatus chính xác cho từng transition (lúc nào submit, có dùng amend khi vòng lại không) — scaffold để `is_submittable=1` nhưng controller rỗng (`on_submit: pass`). DESIGN: submit tại "Xuất giao"; "Sẵn sàng lại" có thể là loan **mới** cho lượt sau (bộ về Ready), thay vì amend cùng doc. Chốt ở slice BE.

---

## 4. Business Rules

| BR | Mô tả | Nơi enforce (DESIGN) |
|---|---|---|
| **BR-05** | **Chặn đặt trùng lịch**: 1 bộ không được đặt cho 2 ca chồng thời gian. Khi book → kiểm tra không tồn tại loan khác cùng `instrument_set` còn hiệu lực (state ∈ {Đã đặt, Đang giao, Đang sử dụng tại BV}) trong khoảng `booked_at..due_return_at` giao nhau. | `antmed_crm.api.antmed.instrument_loan.book` + module hook `validate` trên `AntMed Instrument Loan`. `frappe.throw(_("BR-05: Bộ dụng cụ đã có lịch mượn trùng khoảng thời gian này"))` |
| **BR-09** | **Chỉ "Sẵn sàng" lại sau tiệt khuẩn Pass**: transition "Đang xử lý/tiệt khuẩn → Sẵn sàng" yêu cầu tồn tại ≥1 `AntMed Sterilization` với `loan`=loan hiện tại và `result="Pass"`. | `antmed_crm.api.antmed.instrument_loan.mark_ready` + module hook (kiểm tra trước khi đổi `workflow_state`/`current_status`). `frappe.throw(_("BR-09: Chưa có bản ghi tiệt khuẩn Pass — không thể chuyển về Sẵn sàng"))` |
| **BR (cảnh báo) quá hạn** | Bộ ở {Đang giao, Đang sử dụng tại BV} mà `due_return_at` < now → cảnh báo realtime + đỏ trên UI. **Warn, không chặn.** | Scheduler `check_overdue_loans` (ground @ scaffold `scheduler.py`) → `frappe.publish_realtime("loan_overdue", ...)`; wired qua `scheduler_events` trong `crm/hooks.py`. |
| **BR-13** | **Data-scope**: `NV kinh doanh` chỉ thấy lượt mượn / bộ thuộc tuyến mình (gắn `employee`/`current_holder` = NV đó). | `[ROADMAP]` — `permission_query_conditions` cho `AntMed Instrument Loan`/`AntMed Instrument Set` (M14). Invariant `count==rows` vẫn enforce ngay. |
| **BR-10** | **Audit log** mọi thao tác trên bộ dụng cụ (mượn/trả/tiệt khuẩn/sự cố) — phục vụ thanh kiểm tra. | `[ROADMAP M14]` — hash-chain `AntMed Audit Log`; M05 chỉ phát event/`track_changes=1` ở W3. |

> Checklist nhận-trả: khi `return_checklist` có dòng `condition ∈ {Missing, Damaged}` → controller **không tự chặn** nhưng **gợi ý** tạo `AntMed Loan Incident` (UI prompt). Tính phí BV qua `charged_to_hospital` là quyết định của `Quản lý`. `[cần khảo sát]` có hard-block trả khi thiếu món Critical không — đề xuất: warn + bắt buộc lý do, không block.

---

## 5. API

> File `crm/api/antmed/instrument_loan.py`. Mọi hàm `@frappe.whitelist`, **type-annotated** (`crm/hooks.py:28 require_type_annotated_api_methods=True`), trả **RAW dict/list** (KHÔNG `_ok`/`_err`). Lỗi nghiệp vụ = `frappe.throw(_("BR-XX: …"))`. List giữ bất biến **count == rows** (`get_list(limit_page_length=0)`).

| Endpoint (`antmed_crm.api.antmed.instrument_loan.<fn>`) | Verb | Mô tả |
|---|---|---|
| `list_instrument_sets` | GET | Danh mục bộ + `current_status`, `surgery_type`, `current_holder`, `lifetime_loans`. Trả `{data, total_count}`, **count==rows** khi không phân trang; filter theo `surgery_type`/`current_status`. |
| `get_instrument_set` | GET | Chi tiết 1 bộ + `components` (món) + lịch sử mượn gần đây. `frappe.has_permission(... "read")` → `PermissionError` nếu fail. |
| `list_loans` | GET | Lượt mượn theo tab: `holding` (Đang giữ — state ∈ {Đang giao, Đang sử dụng}), `calendar` (Đã đặt), filter `employee`/`hospital`/`workflow_state`. `{data, total_count}`, count==rows. |
| `get_loan` | GET | Chi tiết lượt mượn + 2 checklist + sự cố (nếu có) + bản ghi tiệt khuẩn liên quan. |
| `book` | POST | Đặt mượn: tạo `AntMed Instrument Loan` state **Đã đặt**. **Enforce BR-05** (chặn trùng lịch). Trả loan name. |
| `handover` | POST | Bàn giao: nhận `handover_checklist` (món + ảnh + ký) → state **Đang sử dụng tại BV**; set `loaned_at`, `Set.current_status=InUse`, `lifetime_loans += 1`. |
| `receive_return` | POST | Nhận trả: nhận `return_checklist` → state **Đã trả về NV KD**; set `returned_at`. Nếu có món Missing/Damaged → trả cờ `suggest_incident=True`. |
| `sterilize` | POST | Tạo `AntMed Sterilization` (method/result/ảnh) cho loan; chuyển loan sang **Đang xử lý/tiệt khuẩn** nếu chưa. |
| `mark_ready` | POST | Chuyển **Đang xử lý/tiệt khuẩn → Sẵn sàng**. **Enforce BR-09** (yêu cầu Sterilization Pass). Set `Set.current_status=Ready`. |
| `report_incident` | POST | Tạo `AntMed Loan Incident` (type/value/biên bản/charged_to_hospital); set `Set.current_status` = Lost/Damaged nếu phù hợp. |

> Ground @ scaffold cũ có route `POST .../instrument_loan.sterilize` + BR-05 `book` + BR-09 `mark_ready` (README dòng 207/211) — giữ tên hàm, scrub namespace `antmed_crm.api.*`→`antmed_crm.api.antmed.*`.

---

## 6. Integration (doc_events / dependency DAG)

- **Vào (phụ thuộc):**
  - **M01**: `AntMed Instrument Loan.hospital`→`AntMed Hospital`, `.doctor`→`AntMed Doctor` (Link). Hai DocType này phải tồn tại trước (W1).
  - **M03**: `AntMed Instrument Set.current_warehouse`→`AntMed Warehouse` (kho cá nhân NV giữ bộ). Nếu M03 chưa land → field optional, set sau `[cần khảo sát]`.
- **Ra (cấp dữ liệu):**
  - **M10 (KPI)**: đọc `AntMed Instrument Loan` (đúng-đủ-hạn: `returned_at` vs `due_return_at`; số sự cố) + `AntMed Instrument Set.lifetime_loans` (vòng quay). M05 KHÔNG gọi M10; M10 query đọc.
- **doc_events (wired trong `crm/hooks.py`, module hooks tại `crm/antmed/instrument_loan_hooks.py`):**

| DocType | event | handler | tác dụng |
|---|---|---|---|
| `AntMed Instrument Loan` | `validate` | `validate_no_conflict` | BR-05 chặn trùng lịch |
| `AntMed Instrument Loan` | `on_update` / `on_update_after_submit` | `sync_set_status` | cập nhật **gương** `AntMed Instrument Set.current_status` + `lifetime_loans` theo `workflow_state` (lazy-import, truyền PK `instrument_set`) |
| `AntMed Sterilization` | `after_insert` | (none — đọc bởi BR-09 khi mark_ready) | — |
| `AntMed Loan Incident` | `on_submit` | `flag_set_lost_or_damaged` | set `Set.current_status` |

- **scheduler_events**: `check_overdue_loans` (hourly/daily) → realtime cảnh báo quá hạn (ground @ scaffold `scheduler.py`).
- **Lazy-import + truyền PK**: hooks chỉ `frappe.get_doc("AntMed Instrument Set", doc.instrument_set)` khi cần, KHÔNG import chéo module Python. Không gate compliance cứng ở M05 (khác M06).

---

## 7. UI

> Ground @ `AntMed_CRM_UI_Design.md §3.3` (màn "Bộ dụng cụ — Cho mượn / Nhận trả") + §sidebar (mục "Bộ dụng cụ"). Vue 3 + frappe-ui; `createResource`/`createListResource` gọi `antmed_crm.api.antmed.instrument_loan.*`. Route APPEND vào `frontend/src/router.js` (lazy). Nhãn 100% tiếng Việt qua `__()`.

| Route | name | component | Mô tả | Role |
|---|---|---|---|---|
| `/antmed/instrument-sets` | `AntmedInstrumentSets` | `pages/AntmedInstrumentSets.vue` | Danh mục bộ (mã, loại PT, trạng thái, người giữ) | `Quản lý`, `NV kinh doanh` |
| `/antmed/instrument-sets/:name` | `AntmedInstrumentSetDetail` | `pages/AntmedInstrumentSetDetail.vue` | Chi tiết bộ + món + ảnh chuẩn + lịch sử mượn | tất cả role M05 |
| `/antmed/loans` | `AntmedInstrumentLoan` | `pages/AntmedInstrumentLoan.vue` | 3 tab: **Đang giữ** / **Lịch hẹn** (calendar) / **Xử lý sau dùng** | `NV kinh doanh`, `Thủ kho` |
| `/antmed/loans/:name` | `AntmedLoanDetail` | `pages/AntmedLoanDetail.vue` | Chi tiết lượt mượn + 2 checklist + tiệt khuẩn + sự cố | — |

- **Tab Đang giữ** (UI_Design §3.3): card mỗi bộ — ảnh, mã, loại PT, ngày dự kiến trả (đỏ nếu quá hạn), nút **Bàn giao mượn** / **Nhận trả**.
- **Tab Lịch hẹn**: calendar tuần, slot bộ đã đặt; click slot → loan detail.
- **Tab Xử lý sau dùng**: todo làm sạch → gửi tiệt khuẩn → kiểm đủ món; mỗi bước **bắt buộc chụp ảnh**.
- **Modal "Checklist bàn giao"** (UI_Design mock dòng 152–158): list món với checkbox đủ/thiếu/hư, ô **[+ chụp]** ảnh từng món, vùng **ký bác sỹ**, nút **[Hoàn tất bàn giao]** → gọi `handover`.
- **Modal "Checklist nhận trả"**: tương tự; nếu đánh Missing/Damaged → nút **Lập biên bản sự cố** (gọi `report_incident`).
- **Cảnh báo realtime** `loan_overdue` → banner/toast đỏ; bộ quá hạn highlight trong tab Đang giữ.

> Boundaries UI: lazy import; loading/error/empty mỗi resource; **Never** gọi `crm.api.*` (đúng là `antmed_crm.api.antmed.*`); **Never** axios trực tiếp; **Never** đụng route/page CRM gốc.

---

## 8. Build slices (vertical, cho factory — mỗi slice 1 vòng)

1. **S1 — Master bộ + thành phần (read path):** DocType `AntMed Instrument Set` + child `AntMed Instrument Set Component` (native, KHÔNG Asset) + DocPerm 3 role; `list_instrument_sets` + `get_instrument_set` (count==rows, PermissionError); FE `/antmed/instrument-sets` list + detail. BE test + vitest + build.
2. **S2 — Lượt mượn + workflow 7-state:** DocType `AntMed Instrument Loan` + 2 child checklist; fixture `workflow.json` 7 state/6 transition (VI, theo role); module hook `sync_set_status` (gương `current_status`); `list_loans`/`get_loan`/`book` (BR-05); FE `/antmed/loans` 3 tab + modal checklist bàn giao (`handover`) + nhận trả (`receive_return`). Smoke mỗi transition.
3. **S3 — Tiệt khuẩn + BR-09:** DocType `AntMed Sterilization`; `sterilize` + `mark_ready` (enforce BR-09 Pass); tab "Xử lý sau dùng". Test BR-09 (Fail → throw; Pass → Sẵn sàng).
4. **S4 — Sự cố + cảnh báo quá hạn:** DocType `AntMed Loan Incident`; `report_incident` + `flag_set_lost_or_damaged`; scheduler `check_overdue_loans` + realtime + UI banner. Test scheduler/incident.
5. **S5 — Tích hợp M10 (chỉ chuẩn bị field):** đảm bảo field KPI-source ổn định (`returned_at`, `due_return_at`, `lifetime_loans`, đếm incident) — không code M10 ở đây.

> Phụ thuộc cứng: S2 cần M01 đã có `AntMed Hospital`/`AntMed Doctor`. M03 (`AntMed Warehouse`) optional cho `current_warehouse` — nếu chưa có, để trống, bổ sung sau.

---

## 9. ADRs

### ADR-M05-01: Bộ dụng cụ là DocType native, KHÔNG reuse ERPNext `Asset`
- **Status**: Proposed (chờ chốt ở slice BE)
- **Date**: 2026-06-17
- **Context**: Scaffold cũ (separate-app) gắn `AntMed Instrument Set.asset`→`Asset` và auto-create từ Asset (`ensure_instrument_set`). D1 = NATIVE-LITE: **không cài ERPNext** trên site `miyano`.
- **Decision**: `AntMed Instrument Set` tự là thực thể tài sản (`asset_value`, `max_loans`, `lifetime_loans`); bỏ Link→`Asset` và hook auto-create.
- **Consequences**: (+) độc lập ERPNext, schema gọn; (−) mất tính năng khấu hao/lý lịch tài sản của ERPNext Asset — chấp nhận, ngoài scope M05. (Tham chiếu DEC D1=B trong `../PLAN_AntMed_CRM.md`.)

### ADR-M05-02: Vòng đời chạy trên `AntMed Instrument Loan.workflow_state`; `Set.current_status` là gương denorm
- **Status**: Proposed
- **Context**: Scaffold có trạng thái ở **cả** Set (8 trị) và Loan (7 trị) → nguồn sự thật mơ hồ.
- **Decision**: SSoT vòng đời = `AntMed Instrument Loan.workflow_state` (Frappe Workflow). `AntMed Instrument Set.current_status` cập nhật **derive** qua module hook `sync_set_status` (không nhập tay) để tra cứu nhanh "bộ đang ở đâu" + giữ trạng thái dài hạn `Lost`/`Damaged`.
- **Consequences**: (+) một nguồn sự thật, gương phục vụ UI; (−) phải đảm bảo hook chạy mọi đường đổi state — cần test đồng bộ. Tham chiếu D2 (Frappe Workflow) trong `../SPEC_AntMed_CRM.md §8`.

> Kế thừa ADR-M01-01 (in-place), ADR-M01-02 (prefix `AntMed `), DEC-A (role VI), DEC D1/D2 (native-lite + Frappe Workflow) — không Supersede.

---

## 10. Acceptance / DoD (theo SPEC §6)

- **BE test** `crm/tests/test_antmed_instrument_loan.py` → `bench --site miyano run-tests --module crm.tests.test_antmed_instrument_loan` = **`Ran N tests ... OK`**, 0 fail. TC tối thiểu:
  1. 6 DocType tồn tại sau migrate (3 chính + 3 child) với field tối thiểu; naming sinh `AntMed-LN-…`/`-STR-…`/`-INC-…`.
  2. `list_instrument_sets`/`list_loans` trả `{data, total_count}`; **`len(data)==total_count`** khi không phân trang.
  3. **BR-05**: `book` cùng bộ trùng khoảng thời gian → `frappe.throw` (ValidationError).
  4. **BR-09**: `mark_ready` khi chưa có Sterilization Pass → throw; sau khi có Pass → chuyển **Sẵn sàng**, `Set.current_status=Ready`.
  5. Workflow: 6 transition hợp lệ chạy được; transition sai role bị chặn (smoke mỗi state).
  6. `sync_set_status` đồng bộ `Set.current_status` + `lifetime_loans` đúng sau handover.
  7. `report_incident` Missing/Damaged → `Set.current_status` set Lost/Damaged.
  8. Permission: user thiếu read → `get_loan` raise `PermissionError`.
- **No-regression**: `test_antmed_bootstrap` + `test_antmed_customer` (M01) + 4 test gốc CRM vẫn xanh.
- **FE vitest** `frontend/tests/unit/antmedInstrumentLoan.test.js`: 4 route tồn tại (lazy); page gọi đúng `antmed_crm.api.antmed.instrument_loan.*`; KHÔNG `antmed_crm.api`/axios; route CRM gốc còn.
- **Build**: `yarn build` xanh, chunk `Antmed*` không vỡ.
- **Pixel (sau USER reload)**: Playwright `http://miyano/crm/antmed/loans` → tab Đang giữ render, mở modal checklist bàn giao chụp ảnh + ký → state đổi; tab Xử lý sau dùng → tiệt khuẩn Pass → bộ Sẵn sàng; 0 console error, API 200.
- DoD: BE OK + vitest + build + (sau reload) pixel + no-regression. Chưa pixel ⇒ "contract verified", chưa "xong".

---

## Tham chiếu chéo
- Governing spec: `../SPEC_AntMed_CRM.md` (D1 native-lite, D2 Frappe Workflow, §5 code style, §6 DoD)
- Roadmap/wave + DAG: `../PLAN_AntMed_CRM.md` (M05 dòng 47, W3, phụ thuộc M01/M03, cấp M10)
- Mô tả nghiệp vụ: `../../antmed_crm/docs/AntMed_CRM_Modules.md §5` (vòng đời 7 trạng thái, checklist chụp ảnh, cảnh báo trùng/quá hạn)
- UI: `../../antmed_crm/docs/AntMed_CRM_UI_Design.md §3.3` (màn Cho mượn/Nhận trả, modal checklist) + sidebar "Bộ dụng cụ"
- Exemplar house style: `./m01_customer360.md`
- Scaffold tham chiếu (separate-app cũ, ADAPT `AM `→`AntMed `, bỏ ERPNext Asset): `docs/antmed_crm/antmed_crm/m05_instrument_loan/doctype/` (am_instrument_set, am_instrument_loan, am_sterilization_record, am_instrument_set_component, am_loan_checklist_item, am_loan_incident) + `hooks.py` (ensure_instrument_set — DROP) + `scheduler.py` (check_overdue_loans — KEEP)
- Module liên quan: M01 (Customer 360°), M03 (Kho/Warehouse), M10 (KPI)
- BR enforce map: `docs/antmed_crm/README.md` §12 (BR-05 book, BR-09 mark_ready)
