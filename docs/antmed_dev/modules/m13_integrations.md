# M13 — Tích hợp & API (Core Doc)

| Mục | Giá trị |
|---|---|
| Module folder | `crm/antmed/` (module Frappe **`AntMed`**, scrubbed = `antmed`) |
| DocType folder | `crm/antmed/doctype/antmed_integration_setting/`, `crm/antmed/doctype/antmed_integration_log/` |
| Code path BE | `crm/api/antmed/integrations.py` (đường gọi `antmed_crm.api.antmed.integrations.<fn>`) + connector helpers trong `crm/antmed/integrations/` (zalo, sms, bank, muasamcong, accounting, his) + module hooks `crm/antmed/integrations/hooks.py` (scheduler/retry) |
| FE pages | `frontend/src/pages/AntmedIntegrationSetting.vue`, `frontend/src/pages/AntmedIntegrationLog.vue` + route `/antmed/admin/integrations`, `/antmed/admin/integration-logs` |
| Wave (PLAN) | **W4 — Tăng trưởng & kiểm soát** |
| Role chính (VI) | `Quản lý` (admin tích hợp). Đề xuất role chuyên trách `Quản trị hệ thống` *(VI — [PLANNED], thay cho `AM System Admin` scaffold)* |
| Phụ thuộc (M..) | **M06** (Chứng từ/HĐĐT — dùng chung connector HĐĐT + provider Viettel/MISA/VNPT), **M09** (Đơn/AR — đối soát thu ngân hàng, đặt vật tư từ portal) |
| Cấp dữ liệu cho (M..) | — (module rìa: connector + log + setting; phục vụ vận hành, không cấp master/txn cho module nghiệp vụ khác) |
| Trạng thái | **[PLANNED — chưa code]** |
| Cập nhật | 2026-06-17 |

> **Trạng thái: [PLANNED — chưa code]**
>
> Toàn bộ DocType / API / connector dưới đây là **DESIGN (đề xuất)** — chưa hiện diện trong `crm/antmed/`. Scaffold tham chiếu (`docs/antmed_crm/antmed_crm/m13_integrations/`) là bản app-riêng cũ (`AM …`, module `M13 Integrations`, dùng ERPNext `Sales Invoice`) → **ADAPT** sang in-place: `AM `→`AntMed `, `M13 Integrations`→`AntMed`, ERPNext-reuse→native-lite. **Phần lớn connector thực = `[ROADMAP]`/stub** (cần DPA + sandbox credential — xem HANDOVER §"dev cần TỰ làm tiếp"); M13 chốt **khung** (Setting tập trung + Log + dispatcher + retry) chứ không gọi API thật ở slice đầu.

---

## 1. Overview

M13 là **lớp tích hợp ngoài (integration edge)** của AntMed CRM: tập trung **cấu hình kết nối** (Single `AntMed Integration Setting`) + **nhật ký giao dịch tích hợp** (`AntMed Integration Log`) + bộ **connector** ra/vào hệ thống thứ ba. Đây là module *rìa* — không sở hữu nghiệp vụ lõi, mà **bọc** các đường tích hợp cho M06 (HĐĐT) và M09 (đặt vật tư, đối soát thu).

Theo `AntMed_CRM_Modules.md §13` (ground-truth nghiệp vụ):
- **Hóa đơn điện tử, kế toán, ngân hàng** (đối soát thu).
- **Zalo OA / Email / SMS gateway** để bệnh viện đặt vật tư.
- **Tích hợp đấu thầu** (muasamcong.mpi.gov.vn) theo dõi gói thầu mới.
- **API mở** cho phòng mổ / kho mổ của bệnh viện đối chiếu kho ký gửi.

Vị trí trong 14 module: M13 nằm cuối DAG (W4), **phụ thuộc M06 + M09** và **không cấp dữ liệu** cho module khác. Nó là nơi quy tụ secret/endpoint (1 Single duy nhất) và là điểm quan sát mọi cuộc gọi out/in (1 log chuẩn hoá) — phục vụ vận hành + thanh kiểm tra.

**Business value:** một nơi duy nhất bật/tắt + nhập credential cho từng kênh; mọi lần gửi HĐĐT/Zalo/SMS/đối soát đều có log (status + payload + retry) để truy vết khi lỗi; bệnh viện đặt vật tư qua Zalo/portal vào thẳng pipeline đơn (M09); kế toán đối soát thu tự động.

**Connector trong phạm vi (đánh dấu rõ trạng thái):**

| Connector | Hướng | Liên quan | Trạng thái đề xuất |
|---|---|---|---|
| HĐĐT (Viettel / MISA / VNPT) | Outbound | **M06** (dùng chung — provider + dispatcher) | `[ROADMAP]` thực; khung stub W4 |
| Kế toán (MISA / Fast / Bravo) | Outbound | M09 | `[ROADMAP]` — [cần khảo sát] API từng phần mềm |
| Zalo OA | In/Out + Webhook | M07/M09 (BV đặt vật tư) | stub + webhook skeleton |
| SMS gateway (VietGuys/eSMS/Stringee) | Outbound | thông báo | stub |
| Email | Outbound | dùng `frappe.sendmail` gốc | reuse Frappe |
| Bank (BIDV/VCB/MB…) | Inbound (đối soát thu) | **M09** AR | `[ROADMAP]` — [cần khảo sát] |
| muasamcong crawler | Inbound (poll) | M08 Tender | stub (crawler thật cần parse endpoint) |
| HIS adapter (per-BV) | In/Out | M03 kho ký gửi | `[ROADMAP]` — [cần khảo sát] (cần API spec từng BV — HANDOVER) |
| API mở đối chiếu kho ký gửi | Inbound (BV gọi) | M03 | `[ROADMAP]` |

### User stories
- *Quản trị hệ thống* mở **Settings tích hợp**, bật connector Zalo + nhập token, lưu → connector sẵn sàng (không lộ secret ra FE).
- *Quản trị hệ thống* mở **Nhật ký tích hợp**, lọc theo connector + trạng thái `Thất bại`, xem payload request/response để chẩn đoán lần gửi HĐĐT lỗi, bấm **gửi lại**.
- *Bác sỹ/điều dưỡng BV* nhắn "đặt vật tư …" qua **Zalo OA** → webhook nhận → tạo phơi đặt hàng nháp (M09) + ghi 1 `AntMed Integration Log` (Inbound). *(connector thực = [ROADMAP])*

---

## 2. DocTypes (native-lite, [PLANNED])

> Field ĐỀ XUẤT, ground @ scaffold `am_integration_setting.json` / `am_integration_log.json` (đã ADAPT `AM `→`AntMed `, bỏ module `M13 Integrations` → `AntMed`, bỏ role `AM System Admin` → role VI [PLANNED]) + `AntMed_CRM_Modules.md §13` + HANDOVER §"Cấu hình integration". **KHÔNG ERPNext** (`Sales Invoice` trong scaffold dispatcher → tham chiếu `AntMed Order`/`AntMed E-Invoice` của M09/M06).

| DocType | Loại | Field chính (ĐỀ XUẤT) | Naming |
|---|---|---|---|
| `AntMed Integration Setting` | **Single** (config tập trung) | (Zalo) `zalo_oa_id`, `zalo_access_token`*, `zalo_secret`* · (SMS) `sms_provider` Select, `sms_endpoint`, `sms_api_key`*, `sms_brand_name` · (Map) `map_provider` Select, `map_api_key`* · (muasamcong) `muasamcong_enabled` Check, `muasamcong_endpoint` · (Bank) `bank_provider` Select, `bank_api_key`* · (Signing) `signing_lib_path`, `signing_certificate_path` | Single (issingle=1) |
| `AntMed Integration Log` | **log / txn** | `integration_name` (Data, list-view), `direction` Select `Outbound\|Inbound\|Webhook`, `endpoint`, `status` Select `Success\|Failed\|Retrying\|DeadLetter`, `retry_count` Int, `request_payload` Long Text, `response_payload` Long Text, `error_message` Long Text, `ts` Datetime (default now) | `autoname: "hash"` (Random — như scaffold) |

\* `fieldtype = Password` (mã hoá tại nghỉ, đọc qua `get_password()`; **KHÔNG** trả ra FE — xem §6 gate compliance).

> **Tách bạch với M06 (quan trọng — tránh trùng lặp):** Provider HĐĐT (`AntMed E-Invoice Provider` Single — endpoints/tax-code/default provider) + bản ghi đồng bộ HĐĐT (`AntMed E-Invoice Sync` / `AntMed E-Invoice`) thuộc **M06**. M13 **không** định nghĩa lại; M13 chỉ thêm `signing_*` + các kênh phi-HĐĐT vào `AntMed Integration Setting` và cung cấp **dispatcher + retry-worker** chạy trên DocType của M06. *(Ranh giới M06↔M13 = [cần khảo sát] khi M06 land — ghi ADR Supersede nếu cần gộp Single.)*

> **VI options** (đề xuất đổi nhãn hiển thị, giữ key kỹ thuật cho `status`/`direction` nếu connector code đối chiếu chuỗi): nhãn `Outbound→Gửi đi`, `Inbound→Nhận về`, `Webhook→Webhook`; `Success→Thành công`, `Failed→Thất bại`, `Retrying→Đang thử lại`, `DeadLetter→Hỏng (dead-letter)`. [cần khảo sát] — nếu connector so khớp chuỗi options thì **giữ key EN trong DocType, dịch ở FE** (an toàn i18n, theo SPEC §5).

---

## 3. Workflow

**Không có workflow / state machine.** `AntMed Integration Setting` là config Single (không submit). `AntMed Integration Log` là bản ghi log thuần (không `docstatus`, không chuyển trạng thái có ràng buộc) — `status` chỉ là **nhãn vòng đời kỹ thuật** của một lần gọi (Thành công/Thất bại/Đang thử lại/Dead-letter) do connector/worker tự set, KHÔNG phải Frappe Workflow. Vòng đời HĐĐT (phát hành→ký→CQT) là workflow/trạng thái thuộc **M06**.

---

## 4. Business Rules

> M13 **không** thực thi BR nghiệp vụ VTYT lõi (quota/lot/CO-CQ). Các quy tắc dưới đây là **ràng buộc kỹ thuật/bảo mật của lớp tích hợp**, enforce trong **module hooks** (`crm/antmed/integrations/hooks.py`) hoặc controller `validate`/helper connector. Đánh số nội bộ BR-INT-xx để khỏi đụng BR-01..15.

| BR | Mô tả | Trạng thái | Nơi enforce |
|---|---|---|---|
| BR-10 (audit) | Mọi cuộc gọi tích hợp out/in ghi 1 `AntMed Integration Log` (actor/endpoint/payload/status/ts) — phục vụ thanh kiểm tra | **[PLANNED]** | helper `_log()` gọi trong từng connector trước/sau request |
| BR-12 (2FA — liên quan) | Thao tác nhạy cảm "phát hành HĐĐT" cần 2FA (theo Modules §14) | enforce ở **M06/M14**; M13 chỉ thực thi gửi sau khi M06 cho phép | gate ở dispatcher: nếu chưa qua cổng M06 → `frappe.throw` |
| BR-INT-01 | Secret (token/api_key) **không bao giờ** trả ra FE/log | **[PLANNED]** | API trả Setting **mask** field Password; `_log()` redact payload chứa token |
| BR-INT-02 | Connector tắt (`*_enabled=0` / thiếu credential) → từ chối gọi, ghi log `Failed` với lý do rõ tiếng Việt | **[PLANNED]** | đầu mỗi connector: `frappe.throw(_("BR-INT-02: Kênh … chưa bật/chưa cấu hình"))` |
| BR-INT-03 | Retry có giới hạn (`retry_count < N`, đề xuất N=5) rồi chuyển `DeadLetter`; idempotency để không gửi trùng | **[PLANNED]** | scheduler worker `flush_*_queue` (lazy-import) |
| BR-INT-04 | Webhook vào (Zalo/bank) **verify chữ ký/HMAC** trước khi xử lý; chống replay (idempotency key) | **[PLANNED]** ([cần khảo sát] HMAC từng provider) | handler `webhook()` `allow_guest=True` + verify bằng `*_secret` |
| BR-INT-05 | Quyền cấu hình tích hợp: chỉ role admin (`Quản lý` / `Quản trị hệ thống`) read+write Setting; log read-only với role thường | **[PLANNED]** | DocPerm trên 2 DocType + `frappe.has_permission` trong API |

---

## 5. API

> File: `crm/api/antmed/integrations.py`. Mọi hàm `@frappe.whitelist(methods=[...])`, **type-annotated** (`crm/hooks.py:28`), trả **RAW dict/list** (KHÔNG `_ok/_err` envelope). Lỗi nghiệp vụ/bảo mật = `frappe.throw(_("BR-INT-xx: …tiếng Việt"))`. Webhook vào dùng `allow_guest=True` + verify chữ ký (KHÔNG dựa session).

| Endpoint (`antmed_crm.api.antmed.integrations.*`) | Verb | Mô tả |
|---|---|---|
| `get_settings` | GET | Trả `AntMed Integration Setting` **đã mask** mọi field Password (chỉ `bool` "đã cấu hình" + non-secret) — BR-INT-01. Chỉ role admin. |
| `update_settings` | POST | Cập nhật Setting (ghi credential qua `set_password`); chỉ role admin; ghi audit. |
| `test_connection` | POST | `connector: str` → ping kênh (dry-run / sandbox), trả `{ok, message}`; ghi 1 log. |
| `list_integration_logs` | GET | `filters/start/page_length/integration_name/status` → **RAW dict** `{ "data": [...], "total_count": int }`. **Giữ invariant `count == rows`** (`get_list(pluck/limit_page_length=0)`); item: `name, integration_name, direction, endpoint, status, retry_count, ts`. Payload **không** trả ở list (chỉ ở detail). |
| `get_integration_log` | GET | `name: str` → detail 1 log (kèm `request_payload`/`response_payload` đã **redact** secret); `frappe.throw(PermissionError)` nếu thiếu read-perm. |
| `retry_log` | POST | `name: str` → đẩy lại 1 log `Failed`/`DeadLetter` qua connector tương ứng (idempotent); BR-INT-03. |
| `zalo_webhook` | POST `allow_guest=True` | Nhận webhook Zalo OA; verify HMAC (BR-INT-04); nếu là "đặt vật tư" → tạo phơi đơn nháp M09; luôn ghi log Inbound. *(connector thực = [ROADMAP])* |
| `bank_webhook` | POST `allow_guest=True` | Nhận biến động số dư/đối soát thu → khớp `AntMed AR Entry` (M09); verify chữ ký. *(= [ROADMAP])* |

> **Connector helpers (KHÔNG whitelist — gọi nội bộ):** `integrations/zalo.py::send_message`, `integrations/sms.py::send`, `integrations/bank.py::reconcile`, `integrations/muasamcong.py::crawl_today`, `integrations/accounting.py::push_invoice`, `integrations/dispatcher.py::dispatch` (HĐĐT, dùng DocType M06), `integrations/workers.py::flush_*_queue` (scheduler). Tất cả gọi `_log()`.

---

## 6. Integration

**doc_events vào/ra (theo DAG — `crm/antmed/integrations/hooks.py`, lazy-import + truyền PK, KHÔNG truyền doc nặng):**
- `AntMed E-Invoice` / `AntMed E-Invoice Sync` (M06) `on_submit`/`after_insert` → enqueue `dispatcher.dispatch(einvoice_name)` (gửi HĐĐT). *Lazy-import connector trong handler; chỉ truyền `name`.*
- `AntMed Order` (M09) `on_submit` → (tuỳ chọn) `sms.send`/`zalo.send_message` thông báo BV. `[ROADMAP]`.
- `AntMed AR Entry` (M09) ← `bank_webhook` cập nhật đối soát thu (chiều vào).

**Scheduler (hooks `scheduler_events`):**
- `flush_einvoice_queue` (cron, ví dụ mỗi 15') — retry các bản ghi HĐĐT `Failed` (`retry_count < 5`) — BR-INT-03.
- `flush_zalo_queue` / `flush_sms_queue` — backlog gửi đi (stub đầu).
- `muasamcong.crawl_today` (daily) — poll gói thầu mới → tạo lead/tender (M08). Chỉ chạy khi `muasamcong_enabled`.

**Gate compliance / bảo mật (đặc thù M13):**
- **BR-INT-01 mask secret**: API ra FE không lộ token/api_key (chỉ cờ "đã cấu hình"). `_log()` redact payload chứa secret trước khi lưu.
- **Gate HĐĐT (BR-12)**: dispatcher chỉ gửi sau khi M06 xác nhận đã qua 2FA/cổng phát hành — M13 không tự ý phát hành.
- **Webhook**: verify HMAC/chữ ký (BR-INT-04) trước khi tạo dữ liệu nghiệp vụ; idempotency chống replay.

> **Nguyên tắc additive:** M13 chỉ THÊM doc_events/scheduler/route prefix AntMed vào `crm/hooks.py`; KHÔNG sửa key gốc CRM. Connector dùng `requests` với `timeout` rõ; ở `developer_mode` trả **mock** (như scaffold `zalo_oa.py`) để test không gọi mạng thật.

---

## 7. UI

> Vue 3 + frappe-ui SPA. Màn hình M13 thuộc persona **System Admin / Quản trị** (`AntMed_CRM_UI_Design.md §8.1`: sidebar "Tích hợp (HĐĐT, kế toán, Zalo, đấu thầu)") và bảng so khớp §9 dòng *"13. Tích hợp → Settings tích hợp → Admin"*. Route APPEND vào `frontend/src/router.js` (lazy), nhóm `/antmed/admin/*`.

| Route | name | component | Role | Mô tả |
|---|---|---|---|---|
| `/antmed/admin/integrations` | `AntmedIntegrationSetting` | `pages/AntmedIntegrationSetting.vue` | `Quản lý`/`Quản trị hệ thống` | Form Settings: section Zalo / SMS / Map / muasamcong / Bank / Signing; field secret hiển thị **••• đã cấu hình** + nút "Đổi"; nút "Kiểm tra kết nối" mỗi kênh. Gọi `get_settings`/`update_settings`/`test_connection`. |
| `/antmed/admin/integration-logs` | `AntmedIntegrationLogs` | `pages/AntmedIntegrationLog.vue` | `Quản lý`/`Quản trị hệ thống` | Bảng log: lọc connector + trạng thái + ngày; cột `integration_name/direction/status/retry_count/ts`; click → drawer detail (payload đã redact) + nút "Gửi lại". Gọi `list_integration_logs`/`get_integration_log`/`retry_log`. |

- **Always** lazy import; nhãn 100% tiếng Việt qua `__()`; loading/error/empty cho mỗi resource; **không** render secret thô.
- **Never** gọi `crm.api.*` (đúng: `antmed_crm.api.antmed.integrations.*`); **Never** axios trực tiếp; **Never** đụng route/sidebar CRM gốc.

---

## 8. Build slices (cho factory — mỗi slice 1 vòng)

> Chuỗi vertical-slice, TDD failing-first. M13 ở **W4** → land **sau** M06 + M09 (phụ thuộc) hoặc song song với phần connector stub.

1. **Slice 13.1 — Setting + Log skeleton** *(nền)*: 2 DocType (`AntMed Integration Setting` Single + `AntMed Integration Log`) + DocPerm role VI; helper `_log()`; API `get_settings`(mask)/`update_settings`/`list_integration_logs`(count==rows)/`get_integration_log`; FE 2 trang admin. KHÔNG gọi mạng thật.
2. **Slice 13.2 — Dispatcher HĐĐT + retry** (sau M06): `dispatcher.dispatch` + `flush_einvoice_queue` (scheduler) chạy trên DocType M06; mock ở `developer_mode`; `retry_log` API + nút FE.
3. **Slice 13.3 — Zalo OA in/out + webhook** (sau M09): `zalo.send_message` + `zalo_webhook` (HMAC + parse "đặt vật tư" → phơi đơn M09 nháp). `[ROADMAP]` phần gọi API thật.
4. **Slice 13.4 — SMS + Bank đối soát** (sau M09): `sms.send`; `bank_webhook` khớp `AntMed AR Entry`. `[ROADMAP]`.
5. **Slice 13.5 — muasamcong crawler** (sau M08): `crawl_today` daily → tender/lead. `[ROADMAP]` (parse endpoint thật).
6. **Slice 13.6 — HIS adapter + API mở đối chiếu kho ký gửi** (sau M03): khung adapter per-BV. `[ROADMAP]` — [cần khảo sát] API spec từng BV (HANDOVER).

---

## 9. ADRs

**Chưa có ADR riêng cho M13** (sẽ ghi khi land W4). Kế thừa + tham chiếu:
- **ADR-M01-01** (in-place app `crm`) + **ADR-M01-02** (prefix `AntMed `) — áp dụng: connector/Setting/Log đều prefix `AntMed `, path `antmed_crm.api.antmed.integrations.*`.
- **DEC-2026-06-17-A** (role tiếng Việt) — role admin tích hợp = `Quản lý` (mở rộng `Quản trị hệ thống` [PLANNED]).
- **D1 native-lite** — dispatcher/worker thao tác trên DocType **native M06/M09** (`AntMed E-Invoice`, `AntMed Order`, `AntMed AR Entry`), KHÔNG dùng ERPNext `Sales Invoice` (scaffold cũ tham chiếu `Sales Invoice` → ADAPT bỏ).

**Quyết định module-level đề xuất (chốt khi land):**
- **ADR-M13-01 [đề xuất]** — *Ranh giới Setting HĐĐT M06 ↔ M13*: HĐĐT provider Single thuộc M06; M13 chỉ thêm kênh phi-HĐĐT + dispatcher/worker. **Context/Decision/Consequences** = [cần khảo sát khi M06 land] (có thể gộp 1 Single nếu trùng lặp lớn).

---

## 10. Acceptance / DoD

Theo SPEC §6 — một slice "xong" khi:
1. **BE**: `bench --site miyano run-tests --module crm.tests.test_antmed_integrations` → **`Ran N OK`**, 0 fail. TC tối thiểu (slice 13.1): 2 DocType tồn tại sau migrate + field tối thiểu; `get_settings` **không** trả secret thô (BR-INT-01); `list_integration_logs` trả `{data,total_count}` với **`len(data)==total_count`** khi không phân trang (count==rows); thiếu read-perm → `frappe.PermissionError`; `_log()` ghi đúng `status/direction`.
2. **FE**: `yarn vitest run` xanh — 2 route admin tồn tại (path/name/lazy), gọi đúng `antmed_crm.api.antmed.integrations.*`, KHÔNG `antmed_crm.api`/axios/tanstack, không render secret thô.
3. **Build**: `yarn build` xanh, chunk `Antmed*` không vỡ.
4. **Pixel** (sau USER reload): `http://miyano/crm/antmed/admin/integrations` render form + mask secret; `/antmed/admin/integration-logs` render bảng + filter + drawer detail; 0 console error; API 200.
5. **No-regression**: route/test Frappe CRM gốc + module AntMed đã land còn xanh; connector ở `developer_mode` trả mock (không gọi mạng trong test).

---

## Tham chiếu chéo

- **Spec/Plan cấp dự án**: `../SPEC_AntMed_CRM.md` (Tech Stack, §5 conventions, §6 DoD, ADR/DEC), `../PLAN_AntMed_CRM.md` (component inventory M13 — W4, phụ thuộc M06/M09; DAG).
- **Nghiệp vụ**: `../../antmed_crm/docs/AntMed_CRM_Modules.md §13` (4 nhóm tích hợp) + §14 (audit/2FA cho phát hành HĐĐT).
- **UI**: `../../antmed_crm/docs/AntMed_CRM_UI_Design.md §8` (System Admin — sidebar Tích hợp) + §9 (so khớp module 13 → Settings tích hợp → Admin).
- **House style**: `./m01_customer360.md` (cấu trúc Core Doc, ADR block, DoD, count==rows).
- **Scaffold tham chiếu (ADAPT, KHÔNG copy)**: `docs/antmed_crm/antmed_crm/m13_integrations/` — `doctype/am_integration_setting/am_integration_setting.json`, `doctype/am_integration_log/am_integration_log.json`, `zalo_oa.py`, `sms_gateway.py`, `bank_reconciliation.py`, `muasamcong_crawler.py`, `einvoice_dispatcher.py`, `accounting_misa.py`, `workers.py`.
- **HANDOVER**: `docs/antmed_crm/HANDOVER.md` §"Bước 6 Cấu hình integration" + §"Phần dev cần TỰ làm tiếp" (Integration thực Viettel/MISA/VNPT, HIS adapter per-BV, migration Zalo cũ → đều `[ROADMAP]`).
- **Module liên quan (khi land)**: M06 (Chứng từ/HĐĐT — provider + sync), M09 (Đơn/AR — đặt vật tư + đối soát thu), M08 (Tender — muasamcong), M03 (kho ký gửi — API mở/HIS), M14 (RBAC/2FA/audit cho gate phát hành).
