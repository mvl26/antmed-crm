# M07 — CSKH Bác sỹ (Doctor Relationship) (Core Doc)

| Mục | Giá trị |
|---|---|
| Module folder | `antmed_crm/antmed/` (module Frappe **`AntMed`**, scrubbed = `antmed`) — DocType tại `antmed_crm/antmed/doctype/<snake>/` |
| Code path BE | `antmed_crm/antmed/doctype/antmed_doctor_visit/` … + endpoint `antmed_crm/api/antmed/doctor_care.py` (đường gọi `antmed_crm.api.antmed.doctor_care.<fn>`) |
| Module hooks | business rule (BR-11) wiring qua `doc_events` trong `antmed_crm/hooks.py` → `antmed_crm/antmed/doctype/antmed_doctor_gift/antmed_doctor_gift.py:validate` |
| Scheduler | nhắc lịch ghé thăm + nhắc sinh nhật trong `antmed_crm/antmed/doctor_care_scheduler.py` (wire `scheduler_events` ở `hooks.py`) |
| FE pages | `frontend/src/pages/AntmedDoctorCare*.vue` (tab trong profile bác sỹ M01) + route `/antmed/doctors/:name` (mở rộng) · `/antmed/visits` |
| Wave (PLAN) | **W3 — Đặc thù AntMed** (chạy song song W2, sau W1) |
| Role chính (VI) | `NV kinh doanh` (ghé thăm/ghi chú/quà), `Quản lý` (duyệt quà — compliance BR-11) — xem `./m14_rbac_w0_role_naming.md`. `[PLANNED]` role `CSKH` nếu tách đội chăm sóc (xem ADR-M07-03). |
| Phụ thuộc | **M01** (`AntMed Doctor`, `AntMed Hospital`) |
| Cấp dữ liệu cho | **M10** (KPI — điểm hài lòng, tần suất ghé thăm, doanh thu mang về theo bác sỹ) |
| Site dev | `miyano` |
| Trạng thái | **PLANNED — chưa code** |
| Cập nhật | 2026-06-17 |

> **Trạng thái: [PLANNED — chưa code]**
> Toàn bộ schema/API/workflow dưới đây là **DESIGN (đề xuất)**, ground @ scaffold `m07_doctor_care` (bản app-riêng cũ — đã ADAPT `AM `→`AntMed `, ERPNext-reuse→native-lite) + `AntMed_CRM_Modules.md §7` + `AntMed_CRM_UI_Design.md §3.4`. **Chưa có code** trong `antmed_crm/antmed/` cho module này. Bất cứ điểm nào không truy được nguồn → đánh dấu `[UNVERIFIED]` / `[cần khảo sát]`.

---

## 1. Overview

M07 — CSKH Bác sỹ là module **đặc thù cạnh tranh** của AntMed: khác CRM thường ở chỗ **khách hàng cuối là cá nhân bác sỹ** (người quyết định dùng VTYT / mượn bộ dụng cụ), không chỉ pháp nhân bệnh viện. Module "treo" lên xương sống M01 (`AntMed Doctor` Link→`AntMed Hospital`) và bồi thêm các thực thể quan-hệ-khách-hàng: lịch ghé thăm, ghi chú cuộc gặp, quà tặng/tài trợ (có gate compliance), khảo sát hài lòng sau ca mổ, nhắc sinh nhật.

Theo `AntMed_CRM_Modules.md §7` (ground-truth nghiệp vụ):
- **Lịch ghé thăm định kỳ** (call plan), **check-in GPS** khi đến.
- **Ghi chú cuộc gặp**: chủ đề, vật tư đang quan tâm, đối thủ đang chào, cam kết tiếp theo (kèm ảnh / ghi âm).
- **Quà tặng, mẫu dùng thử, tài trợ hội nghị** — lưu vết để tuân thủ chính sách compliance (**BR-11**: cần `approved_by`).
- **Khảo sát hài lòng sau ca mổ** — đánh giá vật tư, dịch vụ giao, bộ dụng cụ mượn.
- **Sinh nhật, kỷ niệm** — nhắc tự động cho NV phụ trách.

**Business value:** NV kinh doanh duy trì quan hệ bác sỹ một cách có hệ thống (không phụ thuộc trí nhớ cá nhân), lãnh đạo nhìn được tần suất chăm sóc + tín hiệu cạnh tranh (đối thủ đang chào ai), và công ty **chứng minh tuân thủ anti-bribery** (mọi quà tặng có người duyệt + ghi vết). Dữ liệu M07 nuôi KPI M10 (điểm hài lòng, coverage ghé thăm).

### User stories
- *NV kinh doanh (mobile, tại phòng mổ)* mở profile bác sỹ → bấm **"+ Ghi chú ghé thăm"**, hệ thống **check-in GPS** tự động, nhập chủ đề + đối thủ đang chào + cam kết tiếp theo, đính ảnh/ghi âm.
- *NV kinh doanh* tạo phiếu **quà tặng** cho bác sỹ (mẫu thử/hội nghị); hệ thống **chặn lưu nếu chưa có người duyệt** (BR-11) → *Quản lý* duyệt.
- *Hệ thống* gửi nhắc **sinh nhật bác sỹ trước 7 ngày** cho NV phụ trách; nhắc **lịch ghé thăm đến hạn** hôm nay.
- *NV kinh doanh* gửi **khảo sát hài lòng** sau ca mổ (gắn với phiếu giao M04 / bộ mượn M05) và nhập điểm 1–5 khi bác sỹ phản hồi.

### 6 câu hỏi domain — feasibility check (BA Bước 2)
| # | Câu hỏi | Trả lời cho M07 |
|---|---|---|
| 1 | **CRM stage?** | Giai đoạn **quan hệ khách hàng / chăm sóc** (sau khi có hồ sơ bác sỹ M01). Không phải lead-gen (đó là M08). |
| 2 | **Ràng buộc hợp đồng/quota?** | **KHÔNG** trực tiếp. M07 không khoá quota; chỉ liên kết tham chiếu khi khảo sát gắn vào phiếu giao/bộ mượn. |
| 3 | **Actor là bệnh viện hay bác sỹ?** | **Bác sỹ (cá nhân)** là trung tâm; bệnh viện là ngữ cảnh (nơi ghé thăm). Mọi txn Link→`AntMed Doctor`. |
| 4 | **Nghĩa vụ chứng từ / HĐĐT?** | **KHÔNG** sinh CO/CQ/ĐKLH/HĐĐT. Quà tặng có **nghĩa vụ compliance nội bộ** (BR-11) chứ không phải chứng từ pháp lý ngành. |
| 5 | **Truy vết lot / thu hồi?** | **KHÔNG**. Khảo sát chỉ *tham chiếu* phiếu giao/bộ mượn (Link), không quản lot. |
| 6 | **Hậu quả nếu data sai?** | **Compliance**: quà tặng không người duyệt = rủi ro pháp lý/anti-bribery → BR-11 là gate cứng. GPS sai = thấp (tín hiệu, không tài chính). |

---

## 2. DocTypes (native-lite, [PLANNED])

> Field set **đề xuất**, ground @ scaffold `m07_doctor_care/doctype/*` + `Modules §7` + `UI_Design §3.4`. **ADAPT** từ scaffold cũ: `AM Doctor`→`AntMed Doctor`; `Employee`/`Customer`/`Delivery Note`/`AM Instrument Loan` (ERPNext-reuse hoặc tên cũ) → **native-lite** (`User`/`AntMed Hospital`/`AntMed Delivery`/`AntMed Instrument Set` loan của M05). Naming series đổi prefix `AntMed`/`AM-` theo chuẩn dự án.

| DocType | Loại | Field chính ĐỀ XUẤT (grounded) | Naming |
|---|---|---|---|
| **`AntMed Doctor Visit`** | txn (submittable) | `doctor` (Link `AntMed Doctor`, reqd), `sales_rep` (Link `User`), `hospital` (Link `AntMed Hospital`), `checked_in_at` (Datetime), `gps_lat`/`gps_lng` (Float), `topic` (Data), `competitors_pitching` (Long Text — đối thủ đang chào), `commitments` (Long Text — cam kết tiếp theo), `photos` (Long Text/JSON urls), `voice_note_file` (Attach), `status` (Select, xem §3) | `naming_series` **`AM-VISIT-.YYYY.-.#####`** |
| **`AntMed Care Note`** | txn / log | `doctor` (Link `AntMed Doctor`, reqd), `sales_rep` (Link `User`), `visit` (Link `AntMed Doctor Visit`, optional — ghi chú thuộc 1 lần ghé thăm), `note_date` (Date, default today), `category` (Select: `Vật tư quan tâm`/`Đối thủ`/`Cam kết`/`Khác`), `content` (Long Text, reqd) | `naming_series` **`AM-NOTE-.YYYY.-.#####`** |
| **`AntMed Call Plan`** `[PLANNED]` | master/plan | `sales_rep` (Link `User`, reqd), `doctor` (Link `AntMed Doctor`, reqd), `frequency` (Select: `Hàng tuần`/`Hai tuần`/`Hàng tháng`, default `Hàng tháng`), `next_visit` (Date), `last_visit` (Date) | `autoname` `hash` (Random) |
| **`AntMed Doctor Gift`** `[PLANNED]` | txn (compliance) | `doctor` (Link `AntMed Doctor`, reqd), `item_or_text` (Data — quà/mẫu thử, reqd), `value_vnd` (Currency), `gift_date` (Date, default today), `purpose` (Select: `Mẫu thử`/`Lễ tết`/`Hội nghị`/`Khác`), **`approved_by`** (Link `User` — BR-11), `compliance_note` (Long Text) | `naming_series` **`AM-GIFT-.YYYY.-.#####`** |
| **`AntMed Satisfaction Survey`** `[PLANNED]` | txn / log | `doctor` (Link `AntMed Doctor`), `delivery` (Link **`AntMed Delivery`** — native-lite thay `Delivery Note`), `instrument_loan` (Link **`AntMed Instrument Set` loan** của M05 — native-lite thay `AM Instrument Loan`), `score_1_5` (Int), `comments` (Long Text), `sent_at` (Datetime), `responded_at` (Datetime) | `autoname` `hash` (Random) |

**Ghi chú ADAPT quan trọng (scaffold cũ → native-lite):**
- Scaffold `am_doctor_visit` dùng `is_submittable: 1` + `status` Select `Planned/CheckedIn/Completed/Reviewed`. **Đề xuất giữ submittable** cho Visit (để có `docstatus` neo audit + workflow nhẹ — xem §3), nhưng **đổi nhãn status sang tiếng Việt**.
- Scaffold dùng `Employee` (Link) cho NV. Site `miyano` (app `antmed_crm`, không ERPNext) **không có `Employee`** → ADAPT sang **`User`** (`sales_rep`). `[cần khảo sát]`: nếu sau này có DocType nhân sự AntMed-native thì đổi Link.
- Scaffold `hospital` Link→`Customer`; ADAPT → **`AntMed Hospital`** (M01).
- Scaffold survey Link→`Delivery Note` + `AM Instrument Loan`; ADAPT → **`AntMed Delivery`** (M04) + loan-record của **M05** (`[cần khảo sát]` tên DocType loan chính xác — M05 chưa chốt; tạm để optional Link, gắn khi M05 land).
- `AntMed Care Note` **không có trong scaffold** nhưng có trong PLAN component-inventory (`AntMed Doctor Visit`, `AntMed Care Note`). Đề xuất tách Note khỏi Visit để ghi chú có thể tồn tại độc lập (gọi điện, không ghé). `[UNVERIFIED]`: ranh giới Visit↔Note có thể gộp — chốt ở build slice S2.
- Scaffold `photos` = Long Text chứa JSON urls. Đề xuất **giữ nguyên** (native-lite, tránh child table ảnh ở vòng đầu); có thể nâng cấp thành child `AntMed Visit Photo` ở backlog.

> Boundaries — Ask-first: có cần child table `Vật tư ưa dùng` / `Lịch sử ca mổ` ngay trong profile bác sỹ (UI §3.4 tab) hay derive từ M03/M04? → đề xuất **derive** (query), KHÔNG thêm child ở M07. Xác nhận PM.

---

## 3. Workflow

M07 có **một state machine nhẹ trên `AntMed Doctor Visit`** (vòng đời ghé thăm) + **gate duyệt trên `AntMed Doctor Gift`** (không phải workflow đầy đủ, là validate BR-11 — xem §4). Các DocType còn lại (Care Note, Call Plan, Survey) **không có workflow**.

### Workflow `AntMed Doctor Visit` (Frappe-native — fixtures `antmed_crm/fixtures/workflow.json`)

State field đề xuất: **`status`** (Select; giữ field scaffold) — hoặc `workflow_state` chuẩn Frappe Workflow. `[cần khảo sát]` BE chốt 1 trong 2; nếu dùng Frappe Workflow engine thì field = `workflow_state`.

| State (VI) | docstatus | Ý nghĩa | Vào bởi |
|---|---|---|---|
| `Lên kế hoạch` | 0 (Draft) | Visit được lên lịch (từ Call Plan), chưa đến | NV kinh doanh |
| `Đã check-in` | 0 | NV đã đến BV, GPS check-in (`checked_in_at`, `gps_lat/lng` set) | NV kinh doanh |
| `Hoàn thành` | 1 (Submitted) | Đã ghi chú đầy đủ, submit (neo audit) | NV kinh doanh |
| `Đã review` | 1 | Quản lý đã xem/đánh giá | Quản lý |

| Transition | Từ → Đến | Role | Điều kiện |
|---|---|---|---|
| Check-in | `Lên kế hoạch` → `Đã check-in` | NV kinh doanh | set `checked_in_at` + GPS |
| Hoàn thành | `Đã check-in` → `Hoàn thành` | NV kinh doanh | `topic` không rỗng; submit (docstatus 0→1) |
| Review | `Hoàn thành` → `Đã review` | Quản lý | — |

> Native Frappe Workflow: định nghĩa trong `antmed_crm/fixtures/workflow.json` (state + transition + role tiếng Việt), `docstatus` map theo bảng. **KHÔNG** dùng `workflowcore`.
> `[cần khảo sát]`: có thể đơn giản hoá bỏ `Lên kế hoạch` nếu Visit luôn tạo tại thời điểm check-in (mobile). Chốt ở slice S1.

**`AntMed Doctor Gift`**: KHÔNG workflow. Gate duyệt = controller `validate` (BR-11). Scaffold `is_submittable: 0` → giữ non-submittable; trạng thái "đã duyệt" = `approved_by` có giá trị.

**`AntMed Care Note` / `AntMed Call Plan` / `AntMed Satisfaction Survey`**: Không có workflow.

---

## 4. Business Rules

| BR | Mô tả | Nơi enforce |
|---|---|---|
| **BR-11** | **Quà tặng/tài trợ cần người duyệt** (compliance anti-bribery): không được lưu/hoàn tất `AntMed Doctor Gift` nếu `approved_by` rỗng. Ground @ README `BR-11 → AM Doctor Gift.validate (approved_by)`. | Controller `antmed_crm/antmed/doctype/antmed_doctor_gift/antmed_doctor_gift.py::validate` → `frappe.throw(_("BR-11: Quà tặng/tài trợ phải có người duyệt (compliance)."))`. Wire bằng class method (đi theo DocType), KHÔNG cần `doc_events` riêng. |
| BR-11b `[đề xuất]` | Ngưỡng giá trị: nếu `value_vnd` ≥ ngưỡng (vd 500.000đ) thì `approved_by` **bắt buộc là `Quản lý`** (không tự duyệt). `[cần khảo sát]` ngưỡng + chính sách công ty. | cùng `validate` — `[UNVERIFIED]` ngưỡng chưa có nguồn, để PLANNED. |
| BR-13 | Data-scope: NV chỉ thấy bác sỹ/visit của tuyến được giao. | `[ROADMAP]` — `permission_query_conditions` cho `AntMed Doctor Visit`/`AntMed Doctor Gift`/… (M14). Cần mô hình "NV phụ trách bác sỹ/BV" (xem M01 ADR-M01-05). Invariant `count == rows` vẫn enforce ngay từ M07. |
| BR-10 | Audit hash-chain cho hành vi nhạy cảm (duyệt quà). | `[ROADMAP]` M14 — khi M14 land, ghi audit log cho sự kiện duyệt `AntMed Doctor Gift`. |

> Ngoài BR-11, M07 **không** có BR nghiệp vụ "cứng" nào khác (không quota/lot/chứng từ). GPS/sinh nhật/khảo sát là tính năng, không phải ràng buộc chặn lưu.

---

## 5. API

> File: `antmed_crm/api/antmed/doctor_care.py`. Mọi hàm `@frappe.whitelist(methods=["GET"|"POST"])`, **type-annotated** (`antmed_crm/hooks.py:28 require_type_annotated_api_methods=True`), trả **RAW dict/list** (KHÔNG `_ok/_err`/envelope). Lỗi nghiệp vụ = `frappe.throw(_("BR-XX: …"))`; permission = `frappe.throw(..., frappe.PermissionError)`. List endpoint giữ **count == rows** (`get_list(limit_page_length=0)` để đếm, không bị cắt phân trang).

| Endpoint (`antmed_crm.api.antmed.doctor_care.<fn>`) | Verb | Mô tả |
|---|---|---|
| `list_visits` | GET | List ghé thăm (filter theo `doctor`/`sales_rep`/`hospital`/`status`/khoảng ngày). Trả `{ "data": [...], "total_count": int }`; **count == rows** khi không phân trang. Field item: `name`, `doctor`, `hospital`, `checked_in_at`, `topic`, `status`. |
| `get_visit` | GET | Chi tiết 1 visit + ghi chú liên quan. `frappe.has_permission(..., doc=name)` → `PermissionError` nếu fail. |
| `check_in` | POST | Tạo/cập nhật Visit với GPS: nhận `doctor`, `hospital`, `gps_lat`, `gps_lng` → set `checked_in_at=now()`, status `Đã check-in`. Trả RAW doc. |
| `save_care_note` | POST | Tạo `AntMed Care Note` (nhận `doctor`, `visit?`, `category`, `content`). Trả RAW doc. |
| `list_care_notes` | GET | Timeline ghi chú theo bác sỹ. `{data,total_count}`, count==rows. |
| `create_gift` | POST | Tạo `AntMed Doctor Gift`. **Sẽ throw BR-11** nếu thiếu `approved_by` (lỗi đến từ controller `validate`, không re-implement ở API). |
| `list_gifts` | GET | List quà tặng theo bác sỹ (compliance review). count==rows. |
| `submit_survey` | POST | Tạo/cập nhật `AntMed Satisfaction Survey` (nhận `doctor`, `delivery?`, `instrument_loan?`, `score_1_5`, `comments`). |
| `doctor_care_summary` | GET | Mặt 360 chăm sóc cho 1 bác sỹ: số visit gần đây, ghi chú mới nhất, quà đã tặng, điểm hài lòng TB, ngày sinh nhật, lịch ghé thăm kế tiếp. Phục vụ tab UI §3.4 + cấp số liệu M10. |

> `[UNVERIFIED]`: scaffold cũ **không có** file API (`api/<module>.py`) — toàn bộ endpoint trên là **đề xuất mới** theo chuẩn dự án (Frappe-standard, RAW). BE chốt signature lúc code.

---

## 6. Integration

**Phụ thuộc vào (M01):**
- `AntMed Doctor Visit.doctor` / `AntMed Care Note.doctor` / `AntMed Doctor Gift.doctor` / `AntMed Satisfaction Survey.doctor` → Link **`AntMed Doctor`** (M01).
- `.hospital` → Link **`AntMed Hospital`** (M01). Lazy-import + truyền PK (name) khi cross-module call; KHÔNG import controller chéo.

**Tham chiếu (không bắt buộc, gắn khi module kia land):**
- `AntMed Satisfaction Survey.delivery` → **`AntMed Delivery`** (M04 giao phòng mổ) — khảo sát sau ca mổ.
- `AntMed Satisfaction Survey.instrument_loan` → loan-record **M05** (bộ dụng cụ mượn). `[cần khảo sát]` tên DocType M05.

**Cấp dữ liệu cho (M10 KPI):**
- M10 query coverage ghé thăm (số visit/bác sỹ/kỳ), điểm hài lòng TB (`score_1_5`), tín hiệu cạnh tranh (`competitors_pitching`). Qua endpoint `doctor_care_summary` hoặc `get_list` trực tiếp — KHÔNG đẩy ngược doc_events vào M10.

**doc_events / hooks:**
- `AntMed Doctor Gift` → `validate` (BR-11) là **class method** trên controller (không cần khai `doc_events`).
- **Scheduler** (`scheduler_events` trong `antmed_crm/hooks.py`), ground @ scaffold `scheduler.py`:
  - **Daily** `send_call_plan_today`: tìm `AntMed Call Plan` có `next_visit == today` → `frappe.publish_realtime("call_plan_due", …, user=<sales_rep>)`.
  - **Daily** `notify_doctor_birthdays`: bác sỹ có sinh nhật sau **7 ngày** → nhắc NV phụ trách. ADAPT scaffold: scaffold tra NV qua `AM Employee Route` (chưa có ở app `antmed_crm`) → **`[cần khảo sát]`** lấy NV phụ trách từ đâu (Call Plan.sales_rep, hay field "NV phụ trách" trên `AntMed Doctor`). Đề xuất: dùng `AntMed Call Plan.sales_rep` (đã có Link doctor↔sales_rep); fallback bỏ qua nếu không có.
- **Gate compliance BR-11**: chặn tại controller, không phải doc_events chéo.

---

## 7. UI

> Vue 3 + frappe-ui SPA. Gọi `antmed_crm.api.antmed.doctor_care.*` qua `createResource`/`createListResource`. Route APPEND vào `frontend/src/router.js` (lazy). KHÔNG đụng route CRM gốc. Nhãn 100% tiếng Việt qua `__()`. Mobile-first (NV làm tại phòng mổ).

Ground @ `UI_Design.md §3.4` ("Khách hàng — CRM bác sỹ") + §3.2 (GPS auto check-in):
- **Profile bác sỹ** (mở rộng trang M01 `/antmed/doctors/:name`): thêm các **tab** — *Lịch sử ca mổ* / *Vật tư ưa dùng* (derive M03/M04) / *Ghi chú* (Care Note) / *Quà tặng đã gửi* (Doctor Gift) / *Khảo sát hài lòng* (Survey).
- **FAB "+ Ghi chú ghé thăm"**: form ngắn — chủ đề, đối thủ đang chào, cam kết tiếp theo, ảnh/ghi âm. Bấm → `check_in` (GPS auto từ trình duyệt) + `save_care_note`.
- **Banner offline** (§3.5): thao tác lưu local, có sóng tự sync (PWA M12 hỗ trợ).

| Route (APPEND) | name | component | mô tả | Role |
|---|---|---|---|---|
| `/antmed/doctors/:name` (mở rộng) | `AntmedDoctorDetail` | `pages/AntmedDoctorDetail.vue` (+ tab CSKH) | profile + tab ghi chú/quà/khảo sát | NV kinh doanh, Quản lý |
| `/antmed/visits` | `AntmedDoctorVisits` | `pages/AntmedDoctorVisits.vue` | list ghé thăm + GPS timeline | NV kinh doanh, Quản lý |
| `/antmed/visits/:name` | `AntmedDoctorVisitDetail` | `pages/AntmedDoctorVisitDetail.vue` | chi tiết visit | NV kinh doanh, Quản lý |
| `/antmed/gifts` | `AntmedDoctorGifts` | `pages/AntmedDoctorGifts.vue` | quà tặng + trạng thái duyệt (compliance) | NV kinh doanh, Quản lý |

> `[UNVERIFIED]`: UI_Design không đặc tả màn riêng cho Call Plan; đề xuất hiển thị "lịch ghé thăm kế tiếp" trong tab profile + danh sách "đến hạn hôm nay" trên home NV (notify realtime). Chốt ở slice S2.

---

## 8. Build slices

> Chia vertical slice cho factory (mỗi slice 1 vòng, TDD failing-first). Thứ tự đi từ lõi quan hệ → compliance → tự động hoá.

- **S1 — Ghé thăm + GPS check-in (lõi):** DocType `AntMed Doctor Visit` (+ workflow nhẹ §3) + `AntMed Care Note`; API `list_visits`/`get_visit`/`check_in`/`save_care_note`/`list_care_notes`; FE tab Ghi chú + FAB + `/antmed/visits`. BE test count==rows + check_in set GPS/status.
- **S2 — Quà tặng + compliance (BR-11):** DocType `AntMed Doctor Gift`; controller `validate` BR-11 (throw nếu thiếu `approved_by`); API `create_gift`/`list_gifts`; FE tab Quà tặng + nút duyệt (Quản lý). BE test: tạo gift thiếu approver → raise; có approver → OK.
- **S3 — Khảo sát hài lòng:** DocType `AntMed Satisfaction Survey`; API `submit_survey`; FE tab Khảo sát (gắn Link delivery/loan optional). Cấp `score_1_5` cho M10.
- **S4 — Call Plan + nhắc tự động:** DocType `AntMed Call Plan`; scheduler `send_call_plan_today` + `notify_doctor_birthdays` (wire `scheduler_events`); FE "đến hạn hôm nay". Test scheduler bằng `execute` (không cần reload).
- **S5 — `doctor_care_summary` + tab profile hợp nhất:** endpoint tổng hợp 360 chăm sóc; FE ráp các tab vào `AntmedDoctorDetail`.

> Mỗi slice: BE test xanh (`Ran N OK`) + FE vitest + `yarn build` + (sau USER reload) pixel verify. KHÔNG commit (HARD-STOP user).

---

## 9. ADRs

### ADR-M07-01: `AntMed Doctor Visit` submittable + workflow nhẹ (giữ docstatus)
- **Status**: Proposed
- **Context**: Scaffold cũ đặt Visit `is_submittable: 1` với status `Planned/CheckedIn/Completed/Reviewed`. Visit là bằng chứng chăm sóc (audit, KPI) → cần neo trạng thái không sửa được sau hoàn thành.
- **Decision**: Giữ Visit **submittable**, dùng **Frappe-native Workflow** (fixtures `workflow.json`) với state tiếng Việt + `docstatus` (D2). KHÔNG `workflowcore`.
- **Consequences**: (+) audit/KPI chắc; (−) thêm bước submit trên mobile — chấp nhận, có thể auto-submit khi "Hoàn thành". `[cần khảo sát]` bỏ state `Lên kế hoạch` nếu Visit luôn sinh lúc check-in.

### ADR-M07-02: Native-lite Link thay ERPNext/Employee (ADAPT scaffold)
- **Status**: Accepted (kế thừa D1 + ADR-M01-04)
- **Context**: Scaffold cũ Link→`Employee`/`Customer`/`Delivery Note`/`AM Instrument Loan`. Site `miyano` (app `antmed_crm`) **không có ERPNext/Employee**.
- **Decision**: `Employee`→**`User`** (`sales_rep`); `Customer`→**`AntMed Hospital`**; `Delivery Note`→**`AntMed Delivery`** (M04); loan→DocType M05 (gắn khi land). Tuân D1 native-lite, ADR-M01-02 prefix `AntMed `.
- **Consequences**: (+) không phụ thuộc ERPNext; (−) `[cần khảo sát]` mô hình nhân sự — nếu sau có DocType NV AntMed-native thì migrate Link.

### ADR-M07-03: BR-11 enforce ở controller `validate`, không workflow
- **Status**: Proposed
- **Context**: Quà tặng cần `approved_by` (anti-bribery) nhưng vòng đời đơn giản (1 lần duyệt), không cần state machine.
- **Decision**: BR-11 = `frappe.throw` trong `AntMed Doctor Gift.validate` khi `approved_by` rỗng. Gift **non-submittable**. Audit duyệt = `[ROADMAP]` BR-10/M14.
- **Consequences**: (+) đơn giản, fail-fast; (−) "đã duyệt" suy ra từ field, không có lịch sử transition — đủ ở vòng đầu.

> Tham chiếu: DEC-A (role VI), ADR-M01-04/05 (DocType mới + hoãn data-scope) áp dụng kế thừa.

---

## 10. Acceptance / DoD

Theo SPEC §6 (DoD một lát cắt = BE test + FE vitest + build + pixel + no-regression):

**BE (TDD — `Ran N OK`, 0 fail):** file `antmed_crm/tests/test_antmed_doctor_care.py`, lệnh `bench --site miyano run-tests --module antmed_crm.tests.test_antmed_doctor_care`. TC tối thiểu:
1. DocTypes tồn tại sau migrate + field tối thiểu (`frappe.get_meta`): `AntMed Doctor Visit`, `AntMed Care Note`, (S2+) `AntMed Doctor Gift`, `AntMed Satisfaction Survey`, `AntMed Call Plan`.
2. `AntMed Doctor Visit` Link `doctor`→`AntMed Doctor` resolve; naming sinh `AM-VISIT-…`.
3. `check_in()` set `checked_in_at` + GPS + status `Đã check-in`.
4. `list_visits()` trả `{data,total_count}`; **`len(data)==total_count`** khi không phân trang (count==rows).
5. **BR-11**: tạo `AntMed Doctor Gift` thiếu `approved_by` → `frappe.ValidationError` (message chứa `BR-11`); có `approved_by` → lưu OK.
6. `submit_survey()` lưu `score_1_5`; `get_visit` permission fail → `PermissionError`.
7. Scheduler `notify_doctor_birthdays`/`send_call_plan_today` chạy không lỗi (gọi qua `execute`, mock realtime).
- **No-regression**: `test_antmed_bootstrap` (6) + `test_antmed_customer` + 4 test gốc CRM vẫn xanh.

**FE (vitest xanh + build xanh):** `frontend/tests/unit/antmedDoctorCare.test.js` — route mới tồn tại (path/name/lazy); page gọi đúng `antmed_crm.api.antmed.doctor_care.*`; KHÔNG `antmed_crm.api`/axios/tanstack; route CRM gốc còn nguyên. `yarn build` emit chunk Antmed* không vỡ.

**Pixel (sau USER reload):** Playwright smoke `/antmed/visits` → check-in (GPS mock) → ghi chú; tab Quà tặng chặn lưu khi chưa duyệt; 0 console error; API 200.

---

## Tham chiếu chéo
- Spec & plan cấp dự án: `../SPEC_AntMed_CRM.md` (D1 native-lite, D2 workflow, §6 DoD), `../PLAN_AntMed_CRM.md` (W3, dòng M07 component-inventory: `AntMed Doctor Visit`/`AntMed Care Note`).
- Nghiệp vụ: `../../antmed_crm/docs/AntMed_CRM_Modules.md §7` (CSKH Bác sỹ — call plan/GPS/ghi chú/quà compliance/khảo sát/sinh nhật).
- UI: `../../antmed_crm/docs/AntMed_CRM_UI_Design.md §3.4` (CRM bác sỹ + tab), §3.2 (GPS auto check-in), §3.5 (offline).
- House style + phụ thuộc M01: `./m01_customer360.md` (`AntMed Doctor`/`AntMed Hospital`, ADR-M01-04/05, count==rows).
- Scaffold tham chiếu (app-riêng cũ, ĐÃ ADAPT): `docs/antmed_crm/antmed_crm/m07_doctor_care/doctype/{am_doctor_visit,am_doctor_gift,am_call_plan,am_satisfaction_survey}/*.json` + `scheduler.py`.
- BR list: `docs/antmed_crm/README.md` (BR-11 → `AM Doctor Gift.validate (approved_by)`; BR-10/12/13).
- Module liên quan: M04 (`AntMed Delivery` — khảo sát sau ca), M05 (bộ mượn — khảo sát), M10 (KPI — tiêu thụ data M07), M14 (data-scope BR-13 + audit BR-10).
