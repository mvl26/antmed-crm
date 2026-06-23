# M06 — Chứng từ & Hồ sơ Pháp lý + HĐĐT (Core Doc)

| Mục | Giá trị |
|---|---|
| Module folder | `antmed_crm/antmed/` (module Frappe **`AntMed`**, scrubbed = `antmed`) |
| DocType folder | `antmed_crm/antmed/doctype/antmed_document/`, `antmed_crm/antmed/doctype/antmed_e_invoice/`, … |
| Code path BE | `antmed_crm/antmed/doctype/<snake>/` + module hooks `doc_events` + `antmed_crm/api/antmed/documents.py` (đường gọi `antmed_crm.api.antmed.documents.<fn>`) |
| Wave (PLAN) | **W2 — Chuỗi vận hành lõi** (M04 → **M06** → M09, tuần tự bắt buộc) |
| Role chính (VI) | `NV chứng từ` *(VI role mới — [PLANNED], xem §4/ADR-M06-03)*, `Kế toán` *([PLANNED])*, `Quản lý`; phụ: `NV kinh doanh` (xem trạng thái bộ chứng từ đơn của mình) |
| Phụ thuộc | **M02** (Contract — pháp nhân/HĐ), **M03** (Lot CO/CQ/ĐKLH), **M04** (Delivery — nguồn sinh bộ chứng từ) |
| Cấp dữ liệu cho | **M09** (Đơn/AR — HĐĐT đã phát hành làm gốc công nợ), **M13** (Integrations — connector Viettel/MISA/VNPT) |
| FE pages | `frontend/src/pages/Antmed*` + route `/antmed/documents`, `/antmed/documents/queue`, `/antmed/documents/cocq`, `/antmed/einvoices` |
| Site dev | `miyano` |
| Trạng thái | **[PLANNED — chưa code]** |
| Cập nhật | 2026-06-17 |

> **Trạng thái: [PLANNED — chưa code]**
> Toàn bộ schema/API/workflow dưới đây là **DESIGN (đề xuất)**, ground @ scaffold cũ (separate-app) đã ADAPT `AM `→`AntMed `, ERPNext-reuse→native-lite, + `AntMed_CRM_Modules.md §6` + `UI_Design §5`. **Chưa có dòng code nào** trong `antmed_crm/antmed/` cho M06. Mọi tham chiếu code = đề xuất sẽ build.

> 🔗 **Tiền đề (đã land R1/R2, dùng lại — KHÔNG dựng lại)**: module `AntMed` trong `antmed_crm/modules.txt`; package `antmed_crm/api/antmed/`; 3 Role fixture (`NV kinh doanh`/`Thủ kho`/`Quản lý`); route `/antmed` + layout SPA. M06 **mở rộng** namespace này.

---

## 1. Overview

M06 là khâu **"đóng bộ chứng từ pháp lý + phát hành hóa đơn điện tử"** trong chuỗi vận hành lõi W2. Sau khi M04 giao phòng mổ hoàn tất một `AntMed Delivery`, M06 **gom tự động** đủ bộ giấy tờ bệnh viện yêu cầu cho lần giao đó rồi phát hành HĐĐT — trước khi M09 ghi công nợ.

Theo `AntMed_CRM_Modules.md §6` (ground-truth nghiệp vụ):
- **Sinh tự động bộ chứng từ theo phiếu giao**: Hóa đơn VAT, Phiếu xuất kho (PXK), Phiếu giao hàng, **CO**, **CQ**, Phiếu kiểm nghiệm, Giấy phép NK, Số đăng ký lưu hành (ĐKLH).
- **Kho mẫu CO/CQ theo lô vật tư** — gắn **tự động theo lot xuất** (lot do M03 quản, mỗi `AntMed Lot` đã có CO/CQ/HSD).
- **Tích hợp HĐĐT** Viettel/MISA/VNPT → phát hành & gửi mail/Zalo bệnh viện.
- **Trạng thái chứng từ**: chờ phát hành / đã gửi / bệnh viện đã ký nhận / đã thanh toán.
- **Lưu trữ điện tử có hiệu lực kiểm toán**: hash, dấu thời gian, log truy cập.

**Vai trò trong 14 module**: M06 là **BA gate domain** — compliance VTYT (CO/CQ/ĐKLH/HĐĐT) sai = rủi ro pháp lý (PLAN §rủi-ro dòng 104). Đây là điểm chốt "không đủ chứng từ → không được phát hành / không ghi nhận công nợ".

**Business value**: NV chứng từ không phải gom giấy tờ thủ công cho từng phiếu giao; hệ thống tự đối chiếu lot↔CO/CQ và chặn phát hành thiếu giấy; HĐĐT phát hành 1-chạm + gửi BV; mọi truy cập/sửa có hash + timestamp phục vụ audit/recall.

**User stories:**
- *NV chứng từ* mở **Hàng chờ phát hành**, thấy các phiếu giao đã hoàn tất nhưng **thiếu chứng từ** (chip đỏ "thiếu CQ lot X"), kéo-thả file hoặc gắn từ kho CO/CQ theo lot, rồi bấm **Phát hành HĐĐT** → ký số → gửi BV.
- *NV chứng từ* mở **Đối soát ký nhận**: BV đã ký / chờ ký / phản hồi sai sót; hệ thống nhắc qua mail/Zalo sau N ngày chưa ký.
- *Kế toán* thấy HĐĐT đã phát hành (mã CQT) làm gốc cho công nợ M09.

---

## 2. DocTypes (native-lite, [PLANNED])

> Field set = **đề xuất tối thiểu** đủ acceptance W2, ground @ scaffold cũ `m06_documents/doctype/*` (đã ADAPT) + `Modules §6` + `UI_Design §5`. **ADAPT chính**: scaffold cũ Link tới ERPNext `Delivery Note`/`Sales Invoice`/`AM Lot Info`/`AM Medical Supply Info` → **native-lite**: Link tới `AntMed Delivery` (M04), `AntMed Lot` (M03), `AntMed Item` (M03). Prefix `AM `→`AntMed `.

| DocType (đề xuất) | Loại | Field chính (ĐỀ XUẤT — grounded) | Naming series |
|---|---|---|---|
| **`AntMed Document`** (Bundle) | txn | `delivery` (Link→`AntMed Delivery`, reqd), `hospital` (Link→`AntMed Hospital`, fetch từ delivery), `status` (Select workflow — xem §3), `invoice_vat` (Attach), `stock_issue` (Attach PXK), `delivery_slip` (Attach), `co` (Attach), `cq` (Attach), `inspection` (Attach Phiếu KN), `import_license` (Attach Giấy phép NK), `registration_no` (Attach/Data ĐKLH), `bundle_pdf` (Attach — bundle tổng), `e_invoice` (Link→`AntMed E-Invoice`), `missing_items` (Long Text JSON — chip thiếu), `hash_sha256` (Data — hash bộ chứng từ), child `lines` (Link `AntMed Document Line`) | `AM-DOC-BUNDLE-.YYYY.-.#####` *(KHÔNG `AM-DR`, KHÔNG `AM-DOC-` — reserve M01 Doctor)* |
| **`AntMed Document Line`** | child | `item` (Link→`AntMed Item`), `lot` (Link→`AntMed Lot`), `qty` (Float), `co_attached` (Check), `cq_attached` (Check), `requires_cocq` (Check — fetch từ `AntMed Item`) | — (child) |
| **`AntMed E-Invoice`** | txn (submittable) | `delivery` / `document_bundle` (Link), `provider` (Select `Viettel`/`MISA`/`VNPT`, reqd), `status` (Select `Pending`/`Đã ký`/`Đã phát hành`/`CQT chấp nhận`/`Lỗi` — xem §3), `ma_cqt` (Data — mã cơ quan thuế), `sign_certificate_used` (Data), `signed_at` (Datetime), `xml_file` (Attach), `pdf_file` (Attach), `sent_to_email` (Data), `sent_to_zalo` (Data), `ack_at` (Datetime — BV ký nhận), `retry_count` (Int), `last_error` (Long Text) | `AM-HD-.YYYY.-.#####` (HĐ) |
| **`AntMed Document Release Queue`** | txn/log | `delivery` (Link→`AntMed Delivery`, reqd, unique), `document_bundle` (Link), `status` (Select `Chờ phát hành`/`Thiếu chứng từ`/`Sẵn sàng`/`Đã phát hành`/`Đã gửi BV`/`BV đã ký`), `missing_chips` (Long Text JSON), `assigned_to` (Link→User), `ts` (Datetime) | `field:delivery` *(1 hàng chờ / 1 phiếu giao)* |
| **`AntMed Handover Confirmation`** | txn (submittable) | `delivery` (Link→`AntMed Delivery`, reqd), `document_bundle` (Link), `hospital_contact` (Data — người nhận BV, reqd), `signed_at` (Datetime), `signature_file` (Attach — ảnh chữ ký), `hash_sha256` (Data) | `AM-HC-.YYYY.-.#####` |
| **`AntMed E-Invoice Provider`** | master (Single) | `default_provider` (Select), 3 section Viettel/MISA/VNPT × (`endpoint` Data, `api_key` Password, `taxcode` Data), `default_certificate_path` (Data), `cqt_endpoint` (Data) | Single (Settings) |

> **Ghi chú native-lite (ADAPT từ scaffold cũ):**
> - Scaffold cũ `AM Document Bundle.delivery_note` (Link `Delivery Note` ERPNext) → đề xuất `AntMed Document.delivery` (Link `AntMed Delivery` của M04). [cần khảo sát] tên field PK chính xác của M04 khi M04 land — đề xuất `delivery`.
> - Scaffold cũ `enforce_cocq_attached` đọc `Delivery Note Item.batch_no` + `AM Lot Info.co_cert/cq_cert` + `AM Medical Supply Info.requires_cocq` → native-lite đọc child `AntMed Delivery` line (lot) + `AntMed Lot.co/cq` + `AntMed Item.requires_cocq`. [cần khảo sát] tên field CO/CQ trên `AntMed Lot` (M03) — đề xuất `co_cert`/`cq_cert` hoặc `co`/`cq`.
> - `AntMed Document` **không submittable** (là bundle gom file, đời sống theo `status`/workflow). `AntMed E-Invoice` + `AntMed Handover Confirmation` **submittable** (cần immutability BR-04 / chữ ký — `docstatus`).
> - **Reserve naming**: KHÔNG dùng `AM-DR` (M04 Delivery), KHÔNG dùng `AM-DOC-.YYYY.` đơn thuần (đã cấp cho `AntMed Doctor` M01). M06 dùng `AM-DOC-BUNDLE-`, `AM-HD-`, `AM-HC-`.

---

## 3. Workflow

M06 có **2 state machine** (Frappe-native Workflow, fixtures `antmed_crm/fixtures/workflow.json`, states/transitions tiếng Việt). Trạng thái = field `status` (đề xuất; có thể đổi `workflow_state` khi BE chốt).

### 3.1 Workflow `AntMed Document` (vòng đời bộ chứng từ — `Modules §6` 4 trạng thái + gate thiếu)

| State (VI) | docstatus | Mô tả | Vai trò hành động |
|---|---|---|---|
| `Chờ phát hành` | 0 | Bundle vừa sinh từ Delivery, đang gom file | NV chứng từ |
| `Thiếu chứng từ` | 0 | Chưa đủ CO/CQ/giấy bắt buộc (chip đỏ) — **chặn phát hành** | NV chứng từ |
| `Đã phát hành` | 1 (HĐĐT submit) | HĐĐT đã ký + phát hành, gửi BV | NV chứng từ |
| `Đã gửi BV` | 1 | Đã gửi mail/Zalo cho BV | tự động / NV chứng từ |
| `BV đã ký nhận` | 1 | Có Handover Confirmation đã ký | NV chứng từ |
| `Đã thanh toán` | 1 | M09 cập nhật khi AR khớp thanh toán | (đến từ M09) |

**Transitions (đề xuất):** `Chờ phát hành` → `Thiếu chứng từ` (auto khi đối chiếu thiếu) / `Đã phát hành` (chỉ khi đủ — gate BR-03) → `Đã gửi BV` → `BV đã ký nhận` → `Đã thanh toán`.

### 3.2 Workflow `AntMed E-Invoice` (vòng đời HĐĐT — ADAPT scaffold `status`)

| State (VI) | docstatus | Mô tả |
|---|---|---|
| `Chờ ký` (`Pending`) | 0 | Tạo bản nháp HĐĐT |
| `Đã ký` (`Signed`) | 0/1 | Ký số bằng certificate |
| `Đã phát hành` (`Submitted`) | 1 | Đẩy lên provider → **immutable (BR-04)** |
| `CQT chấp nhận` (`AcceptedByCQT`) | 1 | Có `ma_cqt` |
| `Lỗi` (`Failed`) | 0 | `last_error`, `retry_count++` |

> **`AntMed Handover Confirmation`** không có workflow nhiều bước — chỉ Draft → Submit (đóng băng chữ ký + hash). Đối soát ký nhận hiển thị 3 nhãn "Chờ ký / Đã ký / Phản hồi sai sót" derive từ trạng thái HĐĐT + tồn tại Handover (UI_Design §5.4) — [cần khảo sát] có cần thêm state `Phản hồi sai sót` riêng không.

---

## 4. Business Rules

| BR | Mô tả | Nơi enforce (đề xuất) |
|---|---|---|
| **BR-03** | **Không phát hành thiếu CO/CQ**: mọi lot của item `requires_cocq=1` phải có CO **và** CQ đính kèm trước khi phát hành bộ chứng từ / HĐĐT. Thiếu → `frappe.throw(_("BR-03: Phải gắn CO/CQ trước khi phát hành: {chips}"))`. | module hooks `doc_events`: `AntMed Document` (hoặc `AntMed E-Invoice`) `before_submit`/`validate` — `antmed_crm/antmed/m06/doc_events.py::enforce_cocq_attached` (ADAPT từ scaffold `enforce_cocq_attached`). |
| **BR-04** | **HĐĐT immutable sau phát hành**: sau khi `AntMed E-Invoice` submit (đã đẩy provider/có `ma_cqt`), **cấm sửa/hủy** nội dung (số HĐ, tiền, lot). Chỉ điều chỉnh qua HĐĐT điều chỉnh/thay thế mới. | `AntMed E-Invoice` submittable (`docstatus=1` khóa field) + controller `on_update_after_submit`/`on_cancel` → `frappe.throw(_("BR-04: HĐĐT đã phát hành không thể sửa/hủy"))`. |
| **BR-07** | **Không xóa phiếu giao đã ký**: chặn xóa `AntMed Delivery` khi đã có Handover Confirmation/bộ chứng từ đã phát hành. | doc_events `AntMed Delivery.on_trash` (do M04 owner; M06 cung cấp check "có bundle đã phát hành"). Liên-module — xem §6. |
| **BR-10** | **Audit hash chain**: mỗi lần upload/sửa file chứng từ, phát hành HĐĐT, ghi nhận ký nhận → ghi log có `hash_sha256` (lưu trữ có hiệu lực kiểm toán — `Modules §6` "hash, dấu thời gian, log truy cập"). | lazy-import `antmed_crm.api.antmed.audit.write_log` (M14) từ doc_events M06. `hash_sha256` trên `AntMed Document`/`AntMed Handover Confirmation`. |

> **BA gate domain (6 câu hỏi feasibility — PLAN dòng 104):** M06 chạm CRM stage *giao hàng/chứng từ*; **có** nghĩa vụ chứng từ + HĐĐT (trọng tâm); **có** truy vết lot (CO/CQ theo lot từ M03); hậu quả data sai = **cao** (pháp lý) → BR-03/BR-04/BR-10 là **gate cứng**, phải có test compliance trước khi cho phát hành.

> **`NV chứng từ` (VI role)**: scaffold cũ dùng `AM Document Officer` ("E1 phát hành chứng từ + HĐĐT", README dòng 107). Theo DEC-A (role tiếng Việt) → đề xuất role mới **`NV chứng từ`** [PLANNED] (mở rộng bộ 3 role hiện có). `Kế toán` [PLANNED] cho khâu thanh toán/M09.

---

## 5. API

> File đề xuất: `antmed_crm/api/antmed/documents.py`. Mọi hàm `@frappe.whitelist(methods=["GET"|"POST"])`, **type-annotated** (`antmed_crm/hooks.py:28 require_type_annotated_api_methods=True`), trả **RAW dict/list** (KHÔNG `_ok`/`_err`/envelope). Lỗi nghiệp vụ = `frappe.throw(_("BR-XX: …"))`. List giữ bất biến **count == rows** (`get_list(pluck=…, limit_page_length=0)`).

| Endpoint (đề xuất) | Verb | Mô tả |
|---|---|---|
| `antmed_crm.api.antmed.documents.list_release_queue` | GET | Hàng chờ phát hành: phiếu giao đã xong nhưng chưa đủ bộ chứng từ. Trả `{data, total_count}`; mỗi item: `delivery`, `hospital`, `sales_rep`, `missing_chips` (list), `status`, `date`. **Invariant count==rows**. Filter theo BV/NV/trạng thái (UI_Design §5.1 top bar). |
| `antmed_crm.api.antmed.documents.get_bundle` | GET | Chi tiết 1 bộ chứng từ theo `delivery` hoặc `name`: các file đính kèm + `lines` (lot/CO/CQ status) + `missing_items` + trạng thái HĐĐT. `frappe.has_permission` → `PermissionError`. |
| `antmed_crm.api.antmed.documents.refresh_release_status` | POST | Đối chiếu lại lot↔CO/CQ của 1 Delivery, cập nhật `missing_chips` + `status` (`Thiếu chứng từ`/`Sẵn sàng`). (ADAPT scaffold `refresh_release_status`.) |
| `antmed_crm.api.antmed.documents.attach_cocq` | POST | Gắn file CO/CQ cho 1 lot (kéo-thả hoặc từ kho CO/CQ theo lot). Ghi hash + audit log (BR-10). |
| `antmed_crm.api.antmed.documents.list_cocq_store` | GET | Kho CO/CQ theo cây NCC → Nhãn hàng → Lot (UI_Design §5.3): mỗi file `pdf`, `hash`, `uploaded_at`, số phiếu giao đã gắn. **count==rows**. |
| `antmed_crm.api.antmed.documents.issue_einvoice` | POST | Phát hành HĐĐT cho 1 bundle: gate **BR-03** (đủ CO/CQ), tạo `AntMed E-Invoice`, enqueue job ký+đẩy provider (M13), trả trạng thái. |
| `antmed_crm.api.antmed.documents.list_einvoices` | GET | Danh sách HĐĐT: `provider`, `status`, `ma_cqt`, `signed_at`, `sent_to_email`, `ack_at`. **count==rows**. |
| `antmed_crm.api.antmed.documents.list_handover_review` | GET | Đối soát ký nhận (UI_Design §5.4): phiếu đã gửi BV + trạng thái `Chờ ký`/`Đã ký`/`Phản hồi sai sót`. **count==rows**. |
| `antmed_crm.api.antmed.documents.confirm_handover` | POST | Ghi nhận BV ký nhận: tạo/submit `AntMed Handover Confirmation` (chữ ký + hash + `signed_at`), chuyển bundle → `BV đã ký nhận`. |

> **Phân biệt 403**: dispatcher-403 (guest) cho tất cả; in-handler `PermissionError` cho `get_bundle`/`confirm_handover`/`issue_einvoice`. Với `list_*`, Frappe permission engine + (về sau) `permission_query_conditions` BR-13 tự lọc — không tồn tại = list rỗng, KHÔNG 403.

---

## 6. Integration (doc_events theo DAG: M03/M04 → **M06** → M09/M13)

> Quy ước liên-module: **lazy-import + truyền PK** (không import nặng ở top-level; truyền `name`/PK qua hàm). Mỗi module sở hữu doc_events trên DocType của mình.

**Vào M06 (M06 lắng nghe / được gọi):**
- **M04 → M06**: khi `AntMed Delivery` submit (hoàn tất giao) → doc_events (M04 owner gọi sang M06) `enqueue_document_release(delivery_name)` → tạo `AntMed Document Release Queue` (`status=Chờ phát hành`) + gọi `refresh_release_status` (ADAPT scaffold `enqueue_document_release`). Truyền **PK `delivery`**.
- **M03 ← M06 (read)**: đối chiếu CO/CQ đọc `AntMed Lot` (CO/CQ/HSD) + `AntMed Item.requires_cocq`. Gắn CO/CQ **tự động theo lot xuất**.
- **M02 ← M06 (read)**: pháp nhân BV / thông tin HĐ để xuất HĐ VAT (MST từ `AntMed Hospital` M01 qua HĐ M02).

**Ra khỏi M06 (M06 cấp dữ liệu):**
- **M06 → M09**: HĐĐT đã phát hành (`AntMed E-Invoice`, `ma_cqt`) là **gốc công nợ AR**. M09 đọc HĐĐT để tạo đơn/AR (BR-14 ở M09). Trạng thái `Đã thanh toán` quay ngược về bundle do M09 cập nhật.
- **M06 → M13**: `issue_einvoice` enqueue job tới **connector HĐĐT** (Viettel/MISA/VNPT) — ADAPT scaffold `frappe.enqueue("antmed_crm.m13_integrations.einvoice_dispatcher.dispatch")` → native `antmed_crm.api.antmed.integrations.einvoice.dispatch` [PLANNED M13]. Cấu hình từ `AntMed E-Invoice Provider` (Single). Auto-fallback provider (README dòng 127).
- **M06 → M14 (audit)**: mọi upload/phát hành/ký nhận → `write_log` hash-chain (BR-10).

**Compliance gate (cốt lõi):** BR-03 chặn `issue_einvoice`/submit bundle khi thiếu CO/CQ → đảm bảo "không giao/không phát hành thiếu giấy". Đây là gate domain M06.

> doc_events thực tế wiring trong **`antmed_crm/hooks.py`** (chỉ THÊM key `doc_events`, KHÔNG sửa key gốc) trỏ tới module hooks M06; business rules nằm trong module hooks, KHÔNG nhồi controller chung.

---

## 7. UI

> Vue 3 + frappe-ui SPA. Persona chính = **NV chứng từ / Pháp lý** (UI_Design §5, desktop-first). Route `/antmed/*` APPEND vào `frontend/src/router.js` (lazy). Nhãn 100% tiếng Việt qua `__()`. KHÔNG đụng route CRM gốc. Gọi đúng `antmed_crm.api.antmed.documents.*` (KHÔNG `crm.api.*`, KHÔNG axios).

### Routes (THÊM mới — lazy import)

| path | name | component | Mô tả |
|---|---|---|---|
| `/antmed/documents/queue` | `AntmedDocumentQueue` | `pages/AntmedDocumentQueue.vue` | **Hàng chờ phát hành** (§5.2) — bảng phiếu giao thiếu chứng từ + drawer kéo-thả CO/CQ + nút phát hành HĐĐT |
| `/antmed/documents/cocq` | `AntmedCoCqStore` | `pages/AntmedCoCqStore.vue` | **Kho CO/CQ** (§5.3) — tree NCC→Nhãn hàng→Lot, mỗi file PDF/hash/ngày/số phiếu đã gắn |
| `/antmed/einvoices` | `AntmedEInvoices` | `pages/AntmedEInvoices.vue` | Danh sách **Hóa đơn điện tử** — provider/trạng thái/mã CQT |
| `/antmed/documents/handover` | `AntmedHandoverReview` | `pages/AntmedHandoverReview.vue` | **Đối soát ký nhận** (§5.4) — Chờ ký/Đã ký/Phản hồi sai sót + nhắc mail/Zalo |
| `/antmed/documents/:name` | `AntmedDocumentDetail` | `pages/AntmedDocumentDetail.vue` | Chi tiết 1 bộ chứng từ |

**Sidebar persona NV chứng từ (§5.1):** Hàng chờ phát hành · Kho CO/CQ · Hóa đơn điện tử · Hồ sơ lưu hành · Lưu trữ · Đối soát ký nhận. **Top bar:** lọc theo BV / theo NV / theo trạng thái.

**Điểm UI chốt (ground UI_Design):**
- Cột **"Thiếu"**: chip đỏ "thiếu CQ", "thiếu CO lot X" (từ `missing_chips`); cột **"Tình trạng CO/CQ"** tick xanh nếu đã đính, cảnh báo đỏ **buộc đính trước khi xuất** (§5.2, dòng 186).
- Drawer phải: xem phiếu giao + kéo-thả file CO/CQ vào ô tương ứng **hoặc** gắn từ kho có sẵn theo lot.
- Nút **"Phát hành hóa đơn điện tử"** → modal preview → ký số → kết quả gửi Mail/Zalo BV.
- Định danh vật tư mọi nơi: `Mã VT | Tên | Lot | HSD | CO/CQ status` (UI_Design §nguyên-tắc dòng 12).
- FE đọc shape `{data, total_count}` bằng `createResource` (đọc `r.data.data`) — như M01 (list trả dict bọc, KHÔNG list thuần).

---

## 8. Build slices (vertical, cho factory — mỗi slice 1 vòng)

> Thứ tự tôn trọng phụ thuộc: cần M03 (Lot CO/CQ) + M04 (Delivery) đã land trước (W2 tuần tự). TDD failing-first; KHÔNG commit.

1. **S1 — Schema bundle + queue (read path):** tạo `AntMed Document`, `AntMed Document Line`, `AntMed Document Release Queue` + DocPerm role. doc_events M04→M06 `enqueue_document_release`. API `list_release_queue` + `get_bundle` + `refresh_release_status`. Test: queue sinh khi Delivery submit; count==rows; missing_chips đúng. FE: `/antmed/documents/queue` list + drawer (read-only).
2. **S2 — Gắn CO/CQ + gate BR-03:** API `attach_cocq` + `list_cocq_store` (kho CO/CQ theo lot, ADAPT đọc `AntMed Lot`). doc_events `enforce_cocq_attached` (BR-03). Test: thiếu CO/CQ → throw BR-03; đủ → status `Sẵn sàng`. FE: kéo-thả + tick CO/CQ + chặn xuất khi đỏ.
3. **S3 — HĐĐT (E-Invoice) + BR-04:** `AntMed E-Invoice` (submittable) + `AntMed E-Invoice Provider` (Single). API `issue_einvoice` + `list_einvoices`. Workflow HĐĐT (§3.2). BR-04 immutable sau submit. enqueue stub job M13 (chưa cần connector thật). Test: phát hành khi đủ giấy; sửa sau submit → throw BR-04. FE: `/antmed/einvoices` + modal preview.
4. **S4 — Ký nhận + audit hash:** `AntMed Handover Confirmation` (submittable) + API `confirm_handover` + `list_handover_review`. BR-10 hash-chain (lazy-import M14 audit; nếu M14 chưa land → ghi `hash_sha256` cục bộ + [PLANNED] wiring audit). Test: ký nhận → bundle `BV đã ký nhận` + hash set. FE: `/antmed/documents/handover` + nhắc N ngày.

---

## 9. ADRs

### ADR-M06-01: Bundle gom file = DocType `AntMed Document` (KHÔNG submittable), HĐĐT/Ký nhận tách riêng (submittable)
- **Status**: Proposed
- **Context**: Bộ chứng từ có nhiều file (HĐ VAT/PXK/CO/CQ/KN/GPNK/ĐKLH) đời sống theo trạng thái (chờ/đã gửi/đã ký/đã thanh toán), trong khi HĐĐT cần **immutability sau phát hành** (BR-04) và ký nhận cần **đóng băng chữ ký + hash**.
- **Decision**: `AntMed Document` = bundle theo `status`/workflow, **không submittable** (file còn bổ sung). `AntMed E-Invoice` + `AntMed Handover Confirmation` = **submittable** (`docstatus=1` khóa) để thực thi BR-04 + hash.
- **Consequences**: (+) tách rõ "gom file linh hoạt" vs "đối tượng pháp lý đóng băng"; (−) phải đồng bộ `status` bundle ↔ trạng thái HĐĐT (transition §3).

### ADR-M06-02: Native-lite thay ERPNext (Delivery Note/Sales Invoice/Batch) — tuân DEC D1=B
- **Status**: Accepted (kế thừa D1)
- **Context**: Scaffold cũ Link `Delivery Note`/`Sales Invoice` + đọc `AM Lot Info`/`AM Medical Supply Info`/`Delivery Note Item.batch_no` (giả định ERPNext + separate-app).
- **Decision**: Thay bằng `AntMed Delivery` (M04), `AntMed Lot`/`AntMed Item` (M03). KHÔNG cài ERPNext. Tự đọc lot↔CO/CQ native.
- **Consequences**: (+) đồng nhất stack fork-nhẹ, toàn quyền CO/CQ theo lot; (−) phụ thuộc tên field chính xác của M03/M04 khi land ([cần khảo sát] `delivery` PK, `AntMed Lot.co/cq`, `AntMed Item.requires_cocq`).

### ADR-M06-03: Thêm role tiếng Việt `NV chứng từ` (+ `Kế toán`) — tuân DEC-A
- **Status**: Proposed
- **Context**: Scaffold cũ `AM Document Officer`/`AM Accountant`. DEC-A chốt role name tiếng Việt.
- **Decision**: Thêm role fixture **`NV chứng từ`** (E1 phát hành chứng từ + HĐĐT) và **`Kế toán`** [PLANNED] vào `antmed_crm/fixtures/role.json`; gắn DocPerm 5 DocType M06.
- **Consequences**: (+) khớp persona UI_Design §5/§6; (−) mở rộng bộ 3 role hiện có → cập nhật `m14_rbac_w0_role_naming.md`.

> Kế thừa **ADR-M01-01** (app RIÊNG `antmed_crm`; gốc: in-place; THỰC TẾ = app RIÊNG `antmed_crm`), **ADR-M01-02** (prefix `AntMed `), **DEC-A** (role VI), **DEC-B** (route AntMed riêng) — không Supersede.

---

## 10. Acceptance / DoD (theo SPEC §6)

**BE (TDD — xanh THẬT):** file `antmed_crm/tests/test_antmed_documents.py`; lệnh `bench --site miyano run-tests --module antmed_crm.tests.test_antmed_documents` → **`Ran N tests … OK`**, 0 fail. TC tối thiểu:
1. 5 DocType M06 tồn tại sau migrate + field tối thiểu (`frappe.get_meta`); naming `AM-DOC-BUNDLE-`/`AM-HD-`/`AM-HC-` (KHÔNG `AM-DR`, KHÔNG đụng `AM-DOC-` của Doctor).
2. Delivery submit → sinh `AntMed Document Release Queue` (`status=Chờ phát hành`).
3. `list_release_queue()` trả `{data, total_count}`; **`len(data)==total_count`** khi không phân trang (count==rows).
4. **BR-03**: phát hành khi thiếu CO/CQ lot `requires_cocq` → `frappe.throw` chứa `"BR-03"`; đủ → `Sẵn sàng`/phát hành OK.
5. **BR-04**: `AntMed E-Invoice` submit rồi sửa nội dung → `frappe.throw` chứa `"BR-04"`.
6. `confirm_handover` → bundle `BV đã ký nhận` + `hash_sha256` set; **BR-10** audit log ghi (hoặc hash cục bộ nếu M14 chưa land).
7. Permission: user thiếu read gọi `get_bundle` → `frappe.PermissionError`.
- **No-regression**: `test_antmed_bootstrap` (6) + `test_antmed_customer` + 4 test gốc CRM (Lead/Task/Organization/Territory) vẫn xanh.

**FE (vitest — xanh):** `frontend/tests/unit/antmedDocuments.test.js` — route mới tồn tại (path/name/lazy); page gọi đúng `antmed_crm.api.antmed.documents.*`; KHÔNG `antmed_crm.api`/axios/tanstack; route CRM gốc còn. `yarn vitest run` xanh + `yarn build` emit chunk Antmed* không vỡ.

**Pixel / e2e (sau USER reload):** Playwright trên `http://miyano/crm/antmed/documents/queue` (cổng 80, login): list phiếu thiếu chứng từ render, chip đỏ đúng, drawer kéo-thả, modal phát hành HĐĐT; 0 console error; API 200.

> **DoD một lát cắt** = BE test xanh + FE vitest xanh + build xanh + (sau USER reload) pixel verify + no-regression. Chưa pixel-verify ⇒ "contract verified", chưa "xong".

---

## Tham chiếu chéo
- Spec cấp dự án: `../SPEC_AntMed_CRM.md` (D1 native-lite, D2 workflow, §5 code style, §6 testing).
- Plan/Wave/DAG: `../PLAN_AntMed_CRM.md` (M06 W2, phụ thuộc M02/M03/M04, cấp M09/M13, rủi ro compliance dòng 104).
- Nghiệp vụ: `../../antmed_crm/docs/AntMed_CRM_Modules.md §6` (bộ chứng từ, kho CO/CQ theo lot, HĐĐT, 4 trạng thái, lưu trữ hash).
- UI: `../../antmed_crm/docs/AntMed_CRM_UI_Design.md §5` (persona NV chứng từ: Hàng chờ phát hành / Kho CO/CQ / Đối soát ký nhận) + §nguyên-tắc (định danh VT, mobile/desktop).
- House style: `./m01_customer360.md` (metadata table, ADR, acceptance/DoD, count==rows).
- Role naming: `./m14_rbac_w0_role_naming.md` (DEC-A — thêm `NV chứng từ`/`Kế toán`).
- Scaffold tham chiếu (separate-app cũ — chỉ đọc field, ĐÃ ADAPT, KHÔNG copy): `docs/antmed_crm/antmed_crm/m06_documents/doctype/` (`am_document_bundle`, `am_e_invoice_sync`, `am_e_invoice_provider`, `am_document_release_queue`, `am_handover_confirmation`) + `m06_documents/hooks.py` (`enqueue_document_release`/`enforce_cocq_attached`/`enqueue_einvoice`).
- Module liên quan: M03 (Lot CO/CQ), M04 (Delivery — nguồn), M09 (AR), M13 (connector HĐĐT), M14 (audit hash BR-10).
