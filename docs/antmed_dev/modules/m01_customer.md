# M01 — Quản lý Khách hàng (Customer 360°) (Core Doc — UMBRELLA)

| Mục | Giá trị |
|---|---|
| Module folder | `crm/antmed/` (module Frappe **`AntMed`**, scrubbed = `antmed`) |
| Code path | `crm/antmed/doctype/<snake>/` + `crm/api/antmed/customer.py` (đường gọi `antmed_crm.api.antmed.customer.<fn>`) |
| Wave (PLAN) | **W0** (slice Customer 360° — DONE) + **W1** (M01-full: child khoa/người ra quyết định/preferences + lịch sử tương tác) |
| Role chính (VI) | `NV kinh doanh`, `Quản lý` (+ `Thủ kho` không quản KH) — DEC-A, xem `./m14_rbac_w0_role_naming.md` |
| Phụ thuộc (M..) | — (module nền, không phụ thuộc module nghiệp vụ nào) |
| Cấp dữ liệu cho (M..) | **hầu hết module**: M02 (HĐ-quota theo BV), M04 (giao phòng mổ theo BV/bác sỹ), M05, M06, M07, M08, M09, M10 |
| Trạng thái | **BUILT (slice Customer 360°)** + phần M01-full **[PLANNED — chưa code]** |
| Cập nhật | 2026-06-17 |

> **Trạng thái: [BUILT — slice] cho Customer 360° (BV + Bác sỹ)** · **[PLANNED — chưa code] cho M01-full (child tables + lịch sử tương tác)**

> 🔗 **Doc này là UMBRELLA M01** — KHÔNG viết lại nội dung 3 slice doc đã land. Phần "đã hiện thực" chỉ **tóm tắt + link**; phần mới spec ở doc này là **M01-full (W1)**. Mọi field-level / API-level của slice → đọc thẳng `./m01_customer360.md`.

---

## 1. Overview

M01 là **mặt 360° của khách hàng** trong 14 module AntMed CRM: quản lý bệnh viện trúng thầu lẫn tiềm năng + cây quan hệ nội bộ (bác sỹ, khoa/phòng, người ra quyết định) + lịch sử tương tác hợp nhất. Đây là **module nền** — không phụ thuộc module nghiệp vụ nào, nhưng cấp dữ liệu master cho hầu hết module còn lại (HĐ-quota M02 treo vào BV; giao phòng mổ M04 treo vào BV/bác sỹ; CSKH M07 treo vào bác sỹ; pipeline M08 phân vai KH theo `contract_status`).

Theo `../../antmed_crm/docs/AntMed_CRM_Modules.md §1` (ground-truth nghiệp vụ), M01 có 5 cụm chức năng:
1. **Hồ sơ bệnh viện** — mã, hạng, khoa/phòng mổ, địa chỉ, MST, trạng thái hợp đồng. → *Slice đã code (BV core) + M01-full bổ sung child khoa/phòng.*
2. **Hồ sơ bác sỹ (đơn vị chăm sóc cốt lõi)** — chuyên khoa, ca mổ thường gặp, vật tư ưa dùng, sở thích bộ dụng cụ, lịch mổ, sinh nhật, ghi chú. → *Slice đã code (bác sỹ core) + M01-full bổ sung Doctor Preference (vật tư ưa dùng).*
3. **Sơ đồ tổ chức ra quyết định** — trưởng khoa, dược, vật tư, kế toán, đấu thầu — ai duyệt gì. → *M01-full (child Decision Maker).*
4. **Phân vai khách hàng** — in-contract / prospect / churn (phục vụ pipeline M08). → *Slice đã có nhãn tĩnh `contract_status`; phân vai đầy đủ = M08.*
5. **Lịch sử tương tác hợp nhất** — cuộc gọi, ghé thăm, đơn giao, phản hồi, khiếu nại — timeline theo bác sỹ và theo bệnh viện. → *M01-full (DocType log `AntMed Interaction`).*

**User story (M01-full):**
- *Là NV kinh doanh*, tôi muốn xem **cây khoa/phòng mổ** của một bệnh viện và **ai duyệt vật tư/đấu thầu/thanh toán** ở đó, để biết tiếp cận đúng người.
- *Là NV kinh doanh*, tôi muốn ghi nhanh **một lần ghé thăm/cuộc gọi** với bác sỹ và xem lại **timeline tương tác** theo bác sỹ + theo bệnh viện, để không bỏ sót cam kết.
- *Là Quản lý*, tôi muốn biết **vật tư ưa dùng** của từng bác sỹ để chuẩn bị hàng/bộ dụng cụ trước ca mổ.

### Đã hiện thực (slice Customer 360° — DONE) — chỉ LINK, không lặp lại
| Slice doc | Nội dung | Trạng thái |
|---|---|---|
| `./m01_bootstrap.md` | Foundation R1: namespace `crm/antmed/` + package `crm/api/antmed/` + 3 Role fixture + `health.ping` + harness test. ADR-M01-01/02/03. | BUILT |
| `./m01_naming_conventions.md` | Convention naming FE↔BE (prefix `AntMed `/`antmed`/`Antmed*`, mapping `AM ↔ AntMed `, đường gọi `antmed_crm.api.antmed.*`). | BUILT |
| `./m01_customer360.md` | **Slice nghiệp vụ R2**: DocType `AntMed Hospital` (autoname `field:hospital_code`) + `AntMed Doctor` (series `AM-DOC-.YYYY.-.####`), 4 endpoint `list_hospitals/get_hospital/list_doctors/get_doctor`, 3 trang Vue. ADR-M01-04/05. Test BE 11 OK, FE ≥136. | BUILT (chờ pixel verify) |
| `./m14_rbac_w0_antmed_boot.md` · `./m14_rbac_w0_role_naming.md` | Gate boot route `/antmed/*` cho role AntMed thuần + đổi tên 3 Role sang tiếng Việt (DEC-A). | BUILT |

> Đã code @ source: `AntMed Hospital`, `AntMed Doctor`, API `antmed_crm.api.antmed.customer.{list_hospitals,get_hospital,list_doctors,get_doctor}`, 3 trang Vue (`AntmedHospitals`, `AntmedHospitalDetail`, `AntmedDoctorDetail`).

---

## 2. DocTypes (native-lite, [PLANNED])

> Phần dưới chỉ là **M01-full (W1) — DESIGN, chưa code**. DocType `AntMed Hospital` / `AntMed Doctor` core **ĐÃ CODE** → schema field-level xem `./m01_customer360.md §DocTypes`. Ground @ scaffold `m01_customer/doctype/{am_hospital_department,am_decision_maker,am_doctor_preference}` (adapt `AM `→`AntMed `, ERPNext-reuse→native-lite) + `Modules §1`.

| DocType | Loại | Field chính (ĐỀ XUẤT) | Naming |
|---|---|---|---|
| `AntMed Hospital` ✅ | master (đã code) | `hospital_code` (unique), `hospital_name`, `rank` (Đặc biệt/I/II/III/Khác), `tax_code`, `address`, `contract_status` (Đã ký/Tiềm năng/Hết hạn) + **[PLANNED]** child `departments`, `decision_makers` | `field:hospital_code` |
| `AntMed Doctor` ✅ | master (đã code) | `doctor_code` (unique), `full_name`, `hospital` (Link→Hospital), `specialty`, `birthday`, `phone`/`email`/`zalo`, `notes` + **[PLANNED]** child `preferred_supplies` | series `AM-DOC-.YYYY.-.####` |
| `AntMed Hospital Department` | **child (istable=1)** của `AntMed Hospital` | `department_name` (reqd), `head_doctor`, `surgery_room_count` (Int — số phòng mổ), `contact_phone` | child (hash) |
| `AntMed Decision Maker` | **child (istable=1)** của `AntMed Hospital` | `role` (Select: Trưởng khoa/Dược/Vật tư/Kế toán/Đấu thầu/Khác — reqd), `person_name` (reqd), `contact`, `approves_for` (phụ trách phê duyệt) | child (hash) |
| `AntMed Doctor Preference` | **child (istable=1)** của `AntMed Doctor` | `item` (Link→**`AntMed Item`** ⚠️ native-lite, KHÔNG `Item` ERPNext), `preferred_lot` (Data), `notes` | child (hash) |
| `AntMed Interaction` | **log (txn, không submit)** | `interaction_type` (Select: Cuộc gọi/Ghé thăm/Đơn giao/Phản hồi/Khiếu nại), `interaction_date` (Datetime), `hospital` (Link→Hospital), `doctor` (Link→Doctor), `subject`, `details` (Small Text), `owner_rep` (Link→User/NV), `source_ref` (Dynamic Link — trỏ DO/đơn giao M04 khi auto-log) | series `AM-INT-.YYYY.-.#####` |

**Ghi chú native-lite & adapt từ scaffold:**
- Scaffold dùng `module: "M01 Customer"`, prefix `AM `, role `AM System Admin`, và `AM Doctor.hospital → Link "Customer"` (ERPNext) → **adapt**: module = `AntMed`, prefix = `AntMed `, role = `Quản lý`/`NV kinh doanh`, `hospital → Link "AntMed Hospital"` (đã chốt ở slice).
- `AntMed Doctor Preference.item`: scaffold trỏ `Item` (ERPNext) → **đổi sang `AntMed Item`** (DocType native-lite của M03). Vì M03 chưa land ở W1 cùng lúc → field này có thể tạm để **Data** (mã vật tư free-text) rồi nâng cấp thành `Link "AntMed Item"` khi M03 catalog-lite sẵn sàng — ghi nhận là **[cần khảo sát thứ tự W1]** (M01-full ‖ M03 song song theo PLAN W1).
- `AntMed Interaction` **KHÔNG có trong scaffold** (scaffold M01 chỉ có 5 doctype: hospital_profile/doctor/department/decision_maker/doctor_preference) → đề xuất **mới**, ground @ `Modules §1` cụm 5 ("lịch sử tương tác hợp nhất: timeline theo bác sỹ và theo bệnh viện"). Là DocType log độc lập (KHÔNG child) để timeline query được 2 chiều (theo `hospital` HOẶC `doctor`) và để M04/M07 auto-append. **[UNVERIFIED]** field set chính xác — cần PM chốt enum `interaction_type` + có cần `attachments`/ảnh hiện trường không.
- 3 child table (Department/Decision Maker/Doctor Preference) là **istable=1** → KHÔNG có endpoint/route riêng; CRUD qua document cha (`AntMed Hospital`/`AntMed Doctor`).

---

## 3. Workflow

**Không có workflow / state machine ở M01** (cả slice lẫn M01-full).
- `contract_status` (BV) = Select **tĩnh** (nhãn dữ liệu), KHÔNG phải `workflow_state`. Vòng đời hợp đồng thật = M02 (khi M02 land, `contract_status` nên **derive** từ HĐ thật, không nhập tay → khi đó viết ADR Supersede).
- `AntMed Interaction`, child tables: master/log data, KHÔNG `docstatus`, KHÔNG submit.

---

## 4. Business Rules

M01 là master data → **không thực thi BR nghiệp vụ "cứng"** (quota/chứng từ/lot). Chỉ đăng ký không gian + invariant kỹ thuật.

| BR | Mô tả | Trạng thái M01 | Nơi enforce (tương lai) |
|---|---|---|---|
| BR-13 | Data-scope: NV chỉ thấy BV được giao (và bác sỹ/tương tác thuộc BV đó) | **[ROADMAP]** (hoãn — ADR-M01-05) | `permission_query_conditions` cho `AntMed Hospital`/`AntMed Doctor`/`AntMed Interaction` (M14), cần field "NV phụ trách BV" trước |
| BR-01 | Đối chiếu danh mục trúng thầu | [ROADMAP] | controller M02/M04 |
| BR-06 | Khoá quota chạm trần | [ROADMAP] | controller quota M02 |
| BR-10 | Audit hash-chain | [ROADMAP] | M14 |
| — (invariant) | **count == rows** cho mọi list endpoint (kể cả list tương tác M01-full) | **BẮT BUỘC** | `crm/api/antmed/customer.py` (`get_list(limit_page_length=0)` + `db.count` khớp) |

**M01-full — quy tắc nhẹ (enforce ở controller validate / module hooks `doc_events`):**
- **BR-M01F-01 (validate)**: `AntMed Interaction` phải có **ít nhất một** trong `hospital` hoặc `doctor` (không cho log "trôi nổi"). Enforce ở `AntMed Interaction.validate()` → `frappe.throw(_("BR-M01F-01: Tương tác phải gắn với bệnh viện hoặc bác sỹ."))`.
- **BR-M01F-02 (auto-derive)**: nếu set `doctor` mà bỏ trống `hospital` → tự điền `hospital` = `doctor.hospital` (controller `validate`, lazy). Giữ timeline 2 chiều nhất quán.
- Message lỗi nghiệp vụ luôn tiếng Việt, format `frappe.throw(_("BR-XX: …"))`. KHÔNG dùng envelope `_ok/_err`.

---

## 5. API

> File: `crm/api/antmed/customer.py`. Mọi hàm `@frappe.whitelist(methods=[...])`, **type-annotated** (do `crm/hooks.py` bật `require_type_annotated_api_methods = True`), trả **RAW dict/list** (KHÔNG envelope). List endpoint giữ invariant **count == rows** (`get_list(pluck/limit_page_length=0)` + `db.count` khớp).

### Đã code (slice) — chỉ liệt kê, chi tiết xem `./m01_customer360.md §API`
| Endpoint | Verb | Mô tả |
|---|---|---|
| `antmed_crm.api.antmed.customer.list_hospitals` | GET | List BV `{data, total_count}`, search theo `hospital_name`, count==rows |
| `antmed_crm.api.antmed.customer.get_hospital` | GET | Detail 360° BV + `doctors[]`; throw `PermissionError` nếu thiếu read |
| `antmed_crm.api.antmed.customer.list_doctors` | GET | List bác sỹ (lọc theo `hospital`), count==rows |
| `antmed_crm.api.antmed.customer.get_doctor` | GET | Profile bác sỹ + `hospital_name` resolve qua Link |

### M01-full (ĐỀ XUẤT — [PLANNED]) — thêm vào cùng file `customer.py`
| Endpoint | Verb | Signature (ĐỀ XUẤT) | Mô tả |
|---|---|---|---|
| `antmed_crm.api.antmed.customer.get_hospital_departments` | GET | `(hospital: str) -> list[dict]` | Trả list child khoa/phòng của 1 BV (đọc child table `departments`). *(Hoặc gộp vào `get_hospital` mở rộng — xem note.)* |
| `antmed_crm.api.antmed.customer.get_hospital_decision_makers` | GET | `(hospital: str) -> list[dict]` | Trả list người ra quyết định của BV. |
| `antmed_crm.api.antmed.customer.list_interactions` | GET | `(hospital: str \| None = None, doctor: str \| None = None, start: int = 0, page_length: int = 20) -> dict` | Timeline tương tác lọc theo `hospital` HOẶC `doctor`; trả `{data, total_count}`; **count==rows** khi không phân trang. |
| `antmed_crm.api.antmed.customer.log_interaction` | POST | `(interaction_type: str, hospital: str \| None = None, doctor: str \| None = None, subject: str \| None = None, details: str \| None = None) -> dict` | Ghi nhanh 1 tương tác (insert `AntMed Interaction`); chạy BR-M01F-01/02; trả doc vừa tạo. |

> **Note (chốt để không gold-plate)**: child khoa/phòng + người ra quyết định có thể **mở rộng `get_hospital`** trả thêm key `departments` / `decision_makers` thay vì 2 endpoint riêng (giảm round-trip cho trang detail). 2 endpoint riêng chỉ cần nếu FE lazy-load tab. **[cần khảo sát]** FE quyết định — mặc định khuyến nghị **gộp vào `get_hospital`**.
> **2 loại 403** giữ như slice: dispatcher-403 (guest) cho mọi endpoint; in-handler `PermissionError` cho các `get_*` khi `has_permission` fail. `log_interaction` (POST) thêm check `has_permission("AntMed Interaction", "create")`.

---

## 6. Integration

**Dependency DAG**: M01 là gốc — `M01 ─► M02/M04/M07/M08…`. Vì M01 cấp master cho hầu hết module → 2 DocType core phải **ổn định tên + khoá** (lý do đã reserve series `AM-DR` cho M04, chốt `AM-DOC-` cho bác sỹ — xem `./m01_customer360.md`).

**doc_events (M01-full, wire qua `crm/hooks.py` + module hooks):**
- **Vào M01 (auto-log tương tác)** — module sau bắn event, M01 nhận: khi M04 `AntMed Delivery` submit / M07 `AntMed Doctor Visit` lưu → **lazy-import** một helper M01 (`crm.antmed.interaction.append_interaction`) **truyền PK** (`hospital`, `doctor`, `source_ref`) để append `AntMed Interaction` (type=`Đơn giao`/`Ghé thăm`). Hướng phụ thuộc đúng DAG: M04/M07 (downstream) gọi vào M01 (upstream master) bằng PK, KHÔNG import ngược.
- **Ra khỏi M01**: M01 KHÔNG bắn event sang module khác (là gốc). Slice hiện tại **KHÔNG** thêm `doc_events` mới (xem `./m01_customer360.md §Integration`); M01-full chỉ thêm `validate` cho `AntMed Interaction` (trong module hooks, KHÔNG đụng key `doc_events` core CRM).
- **Gate compliance**: M01 không có gate compliance (không sinh CO/CQ/ĐKLH/HĐĐT — đó là M06).
- **No-regression**: giữ `permission_query_conditions`/`doc_events`/`after_migrate`/`before_tests` của CRM gốc NGUYÊN VẸN; chỉ THÊM. Chạy lại bootstrap (6) + customer (11) + 4 test gốc CRM phải xanh.

---

## 7. UI

> Vue 3 + frappe-ui SPA. Route APPEND vào `frontend/src/router.js` (lazy). Đường gọi `antmed_crm.api.antmed.customer.*` (KHÔNG `crm.api.*`). Ground @ `../../antmed_crm/docs/AntMed_CRM_UI_Design.md` (§1 "Khách hàng": Danh sách BV + Profile bác sỹ; §3.4 mobile Profile bác sỹ có tab Lịch sử ca mổ / Vật tư ưa dùng / Ghi chú).

### Đã code (slice) — xem `./m01_customer360.md §UI`
| Route | Page | Role |
|---|---|---|
| `/antmed/hospitals` | `AntmedHospitals.vue` | NV kinh doanh, Quản lý |
| `/antmed/hospitals/:name` | `AntmedHospitalDetail.vue` | nt |
| `/antmed/doctors/:name` | `AntmedDoctorDetail.vue` | nt |

### M01-full (ĐỀ XUẤT — [PLANNED]) — mở rộng page đã có, KHÔNG thêm route mới (trừ tab)
- **`AntmedHospitalDetail.vue`** (mở rộng): thêm **tab/section "Khoa & Phòng mổ"** (bảng từ `departments`) + **tab "Người ra quyết định"** (bảng `decision_makers`: vai trò · họ tên · liên hệ · phụ trách phê duyệt) + **tab "Lịch sử tương tác"** (timeline gọi `list_interactions(hospital=name)`). Nguồn: `get_hospital` mở rộng hoặc 2 endpoint con.
- **`AntmedDoctorDetail.vue`** (mở rộng): thêm **tab "Vật tư ưa dùng"** (bảng `preferred_supplies`) + **tab "Lịch sử tương tác"** (`list_interactions(doctor=name)`) — khớp UI mobile §3.4 (tab Vật tư ưa dùng / Ghi chú).
- **Modal "Ghi nhanh tương tác"** (component, không route): form chọn type/subject/details → gọi `log_interaction` (POST) → refresh timeline. Dùng `createResource` (frappe-ui), KHÔNG axios.
- Boundaries: lazy import; `__()` cho nhãn VN; loading/error/empty cho mỗi resource; KHÔNG đụng route/sidebar CRM gốc.

---

## 8. Build slices (cho factory — mỗi slice 1 vòng, TDD failing-first, KHÔNG commit)

> Slice 0 (Customer 360° core) **ĐÃ DONE** — xem `./m01_customer360.md §Build sequence`. Dưới đây là M01-full (W1), chia nhỏ độc lập để chạy được song song M03/M02.

1. **Slice M01F-A — Child khoa/phòng + người ra quyết định**: thêm 2 child DocType `AntMed Hospital Department` + `AntMed Decision Maker` + 2 Table field vào `AntMed Hospital`; migrate; mở rộng `get_hospital` (hoặc 2 endpoint con); test BE field-meta + count==rows; FE thêm 2 tab vào `AntmedHospitalDetail.vue` + vitest.
2. **Slice M01F-B — Vật tư ưa dùng bác sỹ**: thêm child `AntMed Doctor Preference` (field `item` Data tạm hoặc Link `AntMed Item` nếu M03 đã land) + Table field vào `AntMed Doctor`; test; FE tab "Vật tư ưa dùng" trong `AntmedDoctorDetail.vue`.
3. **Slice M01F-C — Lịch sử tương tác**: tạo DocType log `AntMed Interaction` (series `AM-INT-`) + controller `validate` (BR-M01F-01/02); endpoint `list_interactions` (count==rows) + `log_interaction` (POST); test BE (validate + count==rows + permission); FE tab timeline + modal ghi nhanh + vitest.
4. **Slice M01F-D (tích hợp, sau M04/M07)** — wire auto-log: M04/M07 lazy-import `append_interaction(hospital, doctor, source_ref, type)`; test integration append đúng PK. *(Phụ thuộc M04/M07 → chạy ở wave sau, không phải W1.)*

---

## 9. ADRs

Kế thừa ADR slice (không Supersede):
- **ADR-M01-01** (bootstrap in-place trong app `crm`, không đẻ app `antmed_crm`) — `./m01_bootstrap.md`.
- **ADR-M01-02** (prefix `AntMed `, KHÔNG `AM `) — đã bị **DEC-A** (`./m14_rbac_w0_role_naming.md`) Supersede phần *Role naming* (sang tiếng Việt); prefix DocType vẫn `AntMed `.
- **ADR-M01-04** (DocType mới `AntMed Hospital`/`AntMed Doctor`, KHÔNG extend `CRM Organization`/`Contact`) — `./m01_customer360.md`.
- **ADR-M01-05** (hoãn data-scope BR-13, RBAC = DocPerm theo Role) — `./m01_customer360.md`.

### ADR-M01-06: `AntMed Interaction` là DocType log độc lập (KHÔNG child của BV/Doctor)
- **Status**: Proposed (chờ PM chốt — M01-full chưa code)
- **Date**: 2026-06-17
- **Context**: `Modules §1` cụm 5 yêu cầu "timeline tương tác hợp nhất **theo bác sỹ và theo bệnh viện**". Scaffold M01 KHÔNG có doctype này. Nếu làm child table của `AntMed Hospital` thì không query được theo bác sỹ (và ngược lại); nếu làm 2 child trùng lặp thì rò rỉ/khó hợp nhất.
- **Decision**: Tạo **1 DocType log độc lập** `AntMed Interaction` với 2 Link `hospital` + `doctor` (ít nhất 1, BR-M01F-01). Timeline = `list_interactions(filters by hospital OR doctor)`. Cho phép M04/M07 auto-append qua helper truyền PK.
- **Alternatives**: child table trên `AntMed Hospital` — loại (không query theo bác sỹ); dùng `Comment`/`Activity` Frappe gốc — loại (không có enum nghiệp vụ VTYT, khó data-scope BR-13 + audit về sau).
- **Consequences**: (+) timeline 2 chiều, mở rộng được cho audit/recall; (+) M04/M07 append không phụ thuộc ngược. (−) phải tự định nghĩa DocPerm + (về sau) `permission_query_conditions`. (−) enum `interaction_type` **[UNVERIFIED]** — cần PM chốt + xem có cần đính ảnh hiện trường.

### ADR-M01-07: `AntMed Doctor Preference.item` dùng `AntMed Item` (native-lite), KHÔNG `Item` ERPNext
- **Status**: Proposed
- **Date**: 2026-06-17
- **Context**: Scaffold `am_doctor_preference.item` = `Link "Item"` (ERPNext). DEC D1 native-lite cấm reuse ERPNext.
- **Decision**: Đổi sang `Link "AntMed Item"` (DocType M03). Nếu M03 chưa land khi build Slice M01F-B → tạm để **Data** (mã VTYT free-text) rồi nâng cấp bằng patch khi M03 sẵn sàng.
- **Consequences**: (+) tuân thủ native-lite, không phụ thuộc ERPNext. (−) phụ thuộc thứ tự build M01-full ↔ M03 — **[cần khảo sát]** (PLAN W1 cho phép M01-full ‖ M03).

---

## 10. Acceptance / DoD

Theo SPEC §6. Một lát cắt M01-full "xong" = **BE test xanh + FE vitest xanh + build xanh + (sau USER reload) pixel verify + no-regression**.

**BE (run-tests THẬT — `Ran N tests … OK`, 0 fail):**
- `bench --site miyano run-tests --module crm.tests.test_antmed_customer` → bổ sung TC M01-full:
  - 3 child DocType tồn tại sau migrate + đủ field tối thiểu (`frappe.get_meta`).
  - `AntMed Interaction` tồn tại + naming `AM-INT-…`; `validate` chặn khi thiếu cả `hospital` lẫn `doctor` (BR-M01F-01 → throw); auto-derive `hospital` từ `doctor` (BR-M01F-02).
  - `list_interactions(hospital=…)` / `(doctor=…)` trả `{data,total_count}`, **`len(data)==total_count`** khi không phân trang (count==rows).
  - `log_interaction` (POST) insert đúng + chạy BR; permission thiếu `create` → `PermissionError`.
  - `get_hospital` (mở rộng) trả `departments` + `decision_makers` đúng số dòng child.
- **No-regression**: `crm.tests.test_antmed_bootstrap` (6) + 4 test gốc CRM (`test_org_hierarchy`, `test_crm_lead`, `test_crm_task`, `test_crm_territory`) vẫn OK.

**FE:**
- `cd /home/miyano/frappe-bench/apps/crm/frontend && yarn vitest run` xanh (≥ baseline 136, thêm test M01-full): tab mới render; gọi đúng `antmed_crm.api.antmed.customer.{list_interactions,log_interaction}`; KHÔNG `antmed_crm.api`/axios.
- `yarn build` xanh; chunk `Antmed*` không vỡ; route CRM gốc còn nguyên.

**Pixel (sau USER reload `bench restart`):** `http://miyano/crm/antmed/hospitals/<bv>` render tab Khoa/Phòng + Người ra quyết định + Timeline; doctor detail render tab Vật tư ưa dùng + Timeline; modal ghi nhanh tương tác lưu thật, refresh timeline; 0 console error, API 200. Chưa pixel-verify ⇒ chỉ "contract verified".

---

## Tham chiếu chéo
- **Slice đã hiện thực (đọc trước cho field/API-level)**: `./m01_bootstrap.md`, `./m01_customer360.md`, `./m01_naming_conventions.md`, `./m14_rbac_w0_role_naming.md`, `./m14_rbac_w0_antmed_boot.md`.
- **Spec/Plan/Modules/UI**: `../SPEC_AntMed_CRM.md` (§6 Testing/DoD), `../PLAN_AntMed_CRM.md` (W0/W1, DAG, M01 ‖ M02 ‖ M03), `../../antmed_crm/docs/AntMed_CRM_Modules.md §1` (ground-truth 5 cụm), `../../antmed_crm/docs/AntMed_CRM_UI_Design.md` (§1 Khách hàng, §3.4 Profile bác sỹ).
- **Scaffold tham chiếu (adapt `AM `→`AntMed `, ERPNext→native-lite)**: `docs/antmed_crm/antmed_crm/m01_customer/doctype/{am_hospital_department,am_decision_maker,am_doctor_preference,am_doctor,am_hospital_profile}/*.json`.
- **Module liên quan (downstream)**: M02 (Contract/Quota Link→Hospital), M03 (`AntMed Item` cho Doctor Preference), M04 (auto-log Delivery), M07 (auto-log Doctor Visit), M08 (phân vai KH), M14 (data-scope BR-13).
