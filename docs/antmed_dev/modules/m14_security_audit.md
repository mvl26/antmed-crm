# M14 — Phân quyền, Bảo mật & Audit (Core Doc)

| Mục | Giá trị |
|---|---|
| Module folder | `crm/antmed/` (module Frappe **`AntMed`**) — trục cross-cutting nền (Security/RBAC/Audit) |
| DocType folder | `crm/antmed/doctype/antmed_audit_log/`, `.../antmed_data_scope/`, `.../antmed_2fa_session/` *(PLANNED — W4)* |
| Code path | `crm/api/antmed/rbac.py` (đã có, W0-2) · `crm/api/antmed/audit.py` *(PLANNED)* · module hooks `crm/antmed/<module>_hooks.py` qua `doc_events` |
| API package | `crm/api/antmed/audit.py` → đường gọi `crm.api.antmed.audit.<fn>` (W4) |
| FE pages | `frontend/src/pages/AntmedAuditLog.vue`, `AntmedUserRole.vue` *(PLANNED — W4)* + route `/antmed/admin/audit`, `/antmed/admin/users` |
| Wave (PLAN) | **W0 (done)** RBAC nền + audit-lite · **W4 (full)** 2FA + data-scope BR-13 + audit hash-chain hoàn chỉnh |
| Role chính (VI) | `Quản lý` (admin/audit), `NV kinh doanh`, `Thủ kho`; mở rộng `[PLANNED]` `CEO`/`Kế toán`/`Chứng từ`/`System Admin` |
| Phụ thuộc (M..) | — (nền, không phụ thuộc module nghiệp vụ) |
| Cấp dữ liệu cho (M..) | **tất cả** M01–M13 (RBAC/role + data-scope + audit/2FA gate dùng chung) |
| Trạng thái | **PARTIAL** — W0 đã land (3 Role VI + boot allow-check + audit-lite skeleton); M14-full = **[PLANNED]** W4 |
| Cập nhật | 2026-06-17 |

> **Trạng thái: [PARTIAL — W0 done]** — phần W0 (Role VI + boot allow-check) đã hiện thực & verify trên site `miyano`; **audit hash-chain / 2FA / data-scope BR-13 = [PLANNED — chưa code], spec ở đây là DESIGN (đề xuất) cho W4.**

> 🔗 **2 slice doc W0 (đã/đang hiện thực — KHÔNG rewrite ở đây, chỉ tham chiếu):**
> - W0-1 — đổi 3 Role AntMed sang nhãn tiếng Việt (DEC-A): `./m14_rbac_w0_role_naming.md`
> - W0-2 — cho user role AntMed thuần boot vào SPA `/antmed/*` (DEC-B, allow-check additive): `./m14_rbac_w0_antmed_boot.md`
>
> Core Doc này là **umbrella M14**: gói gọn W0 (đã có) + đặc tả M14-full (W4). Verify @source W0: `crm/fixtures/role.json` (3 Role VI), `crm/api/antmed/rbac.py` (`ANTMED_ALLOWED_ROLES`, `is_antmed_user`, `is_crm_or_antmed_user`).

---

## 1. Overview

M14 là **trục cross-cutting nền** trong 14 module: không phải feature nghiệp vụ độc lập mà là tầng **phân quyền (RBAC) + phân quyền theo dữ liệu (data-scope) + audit trail + 2FA** mà mọi module M01–M13 "treo" vào. Theo `AntMed_CRM_Modules.md §14`:

- **RBAC theo vai trò**: CEO, Trưởng kinh doanh, NV kinh doanh, Thủ kho, Kế toán, Chứng từ, Khách hàng (read-only portal). *(D1 hiện chốt 3 Role VI lõi — `NV kinh doanh`/`Thủ kho`/`Quản lý`; các vai trò còn lại `[PLANNED]`.)*
- **Phân quyền theo dữ liệu (BR-13)**: NV chỉ thấy bệnh viện được giao.
- **Log audit (BR-10)** mọi thao tác trên vật tư, bộ dụng cụ, chứng từ — phục vụ thanh kiểm tra ngành y tế.
- **2FA (BR-12)** cho thao tác xuất kho, phát hành hóa đơn, xóa chứng từ.

**Business value**: (W0) NV kinh doanh AntMed thuần đăng nhập là vào thẳng SPA AntMed mà không cần cấp Role CRM gốc (least-privilege). (W4) thanh tra y tế có thể trích xuất nhật ký bất biến (hash-chain) chứng minh không bị sửa hậu kỳ; thao tác nguy hiểm (xuất kho/phát hành HĐĐT/xóa chứng từ) bắt buộc xác thực 2 lớp; NV chỉ thấy đúng phần dữ liệu BV được phân công.

**User story:**
- *Là Quản lý*, tôi mở màn "Audit log", lọc theo actor / đối tượng (lot, phiếu giao, hóa đơn, bộ dụng cụ) / hành động / thời gian, xem diff trước-sau, và export phục vụ thanh tra — biết chắc bản ghi không bị sửa nhờ chuỗi hash.
- *Là NV kinh doanh*, khi mở danh sách bệnh viện tôi chỉ thấy BV được giao cho tôi (không rò rỉ BV của NV khác).
- *Là Thủ kho*, khi xác nhận xuất kho một phiếu, hệ thống bắt tôi nhập OTP 2FA trước khi ghi sổ; thao tác này được audit-log đầy đủ.

> ⚠️ **Scope-note W0 vs W4**: W0 (đã land) **chỉ** gồm (a) 3 Role VI + (b) boot allow-check (`rbac.py`) + (c) audit-lite *skeleton* (đặt chỗ, **chưa** hash-chain đầy đủ, chưa wiring `doc_events` toàn bộ). Toàn bộ DocType/API/workflow ở §2–§6 dưới đây thuộc **W4 = [PLANNED]**, trình bày dạng DESIGN (đề xuất), KHÔNG phải code đã có.

---

## 2. DocTypes (native-lite, [PLANNED] — trừ Role)

> Field set **đề xuất**, ground @ reference scaffold `m14_security_audit/doctype/` (bản app-tách cũ, prefix `AM ` → đổi `AntMed `) + `AntMed_CRM_Modules.md §14` + README BR-10/12/13. Native-lite: **không** dùng ERPNext; mọi DocType mới là `AntMed *` trong module `AntMed`.

| DocType | Loại | Field chính (ĐỀ XUẤT — grounded scaffold + Modules) | naming | Trạng thái |
|---|---|---|---|---|
| `Role` (Frappe core, reuse) | master core | 3 bản ghi VI: `NV kinh doanh`, `Thủ kho`, `Quản lý` (`name`==`role_name`, `is_custom=1`, `desk_access=1`) | — | ✅ **W0 done** (xem `./m14_rbac_w0_role_naming.md`) |
| `AntMed Audit Log` | log (append-only) | `ref_doctype`(Data), `ref_name`(Data), `action`(Select `Insert\nUpdate\nDelete\nSubmit\nCancel`), `actor`(Data), `ip_address`(Data), `user_agent`(Data), `before_json`(Long Text), `after_json`(Long Text), `diff_json`(Long Text), `prev_hash`(Data), `hash_sha256`(Data, read_only), `ts`(Datetime, default `now`) | `autoname: hash` (Random) | **[PLANNED — W4]** (BR-10) |
| `AntMed Data Scope` | master (cấu hình) | `role`(Link→Role, reqd), `scope_type`(Select `Region\nRoute\nHospital`), `scope_value`(Data), `user`(Link→User) | `autoname: hash` (Random) | **[PLANNED — W4]** (BR-13) |
| `AntMed 2FA Session` | txn (ephemeral) | `user`(Link→User, reqd), `action_label`(Data, reqd — vd `xuất kho`/`phát hành HĐĐT`/`xóa chứng từ`), `otp_hash`(Data), `expires_at`(Datetime), `used`(Check) | `autoname: hash` (Random) | **[PLANNED — W4]** (BR-12) |
| `AntMed Role Profile Seed` | master (seed cấu hình) | `role_profile`(Data, reqd, unique), `permissions_json`(Long Text) | `autoname: field:role_profile` | **[PLANNED — W4 / cần khảo sát]** (xem ADR-M14-04) |

**Adaptation notes (scaffold `AM ` → `AntMed `):**
- `AM Audit Log` → **`AntMed Audit Log`**. Giữ nguyên field-set scaffold; `module` đổi từ `M14 Security Audit` → **`AntMed`**; DocPerm role `AM System Admin` → đổi sang **`Quản lý`** (+ `System Manager`). `track_changes` để `0` cho chính bảng audit (audit log không cần tự-track).
- `AM Data Scope` → **`AntMed Data Scope`**. `scope_value` cho `scope_type=Hospital` chứa `name` của `AntMed Hospital` (Link-style by Data, hoặc cân nhắc đổi sang Link→`AntMed Hospital` — *cần khảo sát mô hình "NV phụ trách BV"*, xem §4 BR-13).
- `AM 2FA Session` → **`AntMed 2FA Session`**. `otp_hash` lưu **hash** OTP (KHÔNG plaintext); TTL qua `expires_at`; `used=1` sau khi confirm (chống replay).
- `AM Role Profile Seed` → **`AntMed Role Profile Seed`**. *[cần khảo sát]*: ở D1 có thể KHÔNG cần DocType seed riêng — Frappe đã có `Role Profile` core; cân nhắc dùng **fixture `role_profile.json`** thay vì DocType seed (xem ADR-M14-04).

> **Append-only Audit Log**: `AntMed Audit Log` không cho `write`/`delete` qua UI (chỉ tạo bằng server-side `audit.write_log`). Tính bất biến đến từ **hash-chain** (`prev_hash` → `hash_sha256`), không từ permission đơn thuần.

---

## 3. Workflow

**Không có workflow / state machine** cho các DocType M14. `AntMed Audit Log` là log append-only (không submit, không docstatus). `AntMed 2FA Session` chỉ có cờ `used` (Check) — vòng đời tuyến tính `tạo → confirm/used → hết hạn`, **không** là Frappe Workflow.

> M14 **cung cấp gate** cho workflow của module khác (2FA chặn transition nguy hiểm, audit ghi mọi transition) chứ bản thân không có state machine. Các transition nghiệp vụ (DO submit, phát hành HĐĐT, xóa chứng từ) định nghĩa ở M04/M06 — M14 chỉ hook vào.

---

## 4. Business Rules

| BR | Mô tả | Nơi enforce (ĐỀ XUẤT) | Trạng thái |
|---|---|---|---|
| **BR-10** | Audit hash-chain SHA256: mọi thao tác trên vật tư/bộ dụng cụ/chứng từ ghi 1 bản ghi `AntMed Audit Log` nối chuỗi hash (`hash = sha256(prev_hash + payload)`) → bất biến, phát hiện chèn/sửa | `audit.write_log()` gọi từ **module hooks `doc_events`** (`on_update`/`on_submit`/`on_cancel`/`on_trash`) của các doctype trọng yếu; verify bằng `audit.verify_chain()` | **[PLANNED — W4]** (W0 mới có skeleton) |
| **BR-12** | 2FA cho thao tác nguy hiểm: **xuất kho** (M03/M04 Stock Entry/Delivery), **phát hành hóa đơn** (M06 HĐĐT), **xóa chứng từ** (M06 on_trash) | `audit.require_2fa_and_log()` gọi đầu handler/`validate` thao tác; chưa confirm OTP hợp lệ trong TTL → `frappe.throw(_("BR-12: Thao tác cần xác thực 2 lớp (2FA)…"))` | **[PLANNED — W4]** |
| **BR-13** | Data-scope: NV chỉ thấy bệnh viện được giao (và dữ liệu treo theo BV: hợp đồng/giao/lot…) | `permission_query_conditions` cho **5 doctype** (đề xuất: `AntMed Hospital`, `AntMed Doctor`, `AntMed Contract`, `AntMed Delivery`, `AntMed Stock Entry` — *danh sách cuối cần chốt W4*), dựa trên `AntMed Data Scope` (role/user → hospital) | **[PLANNED — W4]** (hoãn từ R2 — ADR-M01-05; bật ở W4 mà KHÔNG vỡ invariant `count==rows`) |

**Nguyên tắc enforce (Frappe-standard):**
- Business rule đặt trong **module hooks** (vd `crm/antmed/audit_hooks.py`) wired qua `doc_events` trong `crm/hooks.py` (chỉ **THÊM** nhánh, không sửa nhánh CRM gốc). Lazy-import + truyền PK (Pattern B cross-module).
- Lỗi nghiệp vụ = `frappe.throw(_("BR-XX: …tiếng Việt"))`. Vd: `frappe.throw(_("BR-12: Thao tác xuất kho cần xác thực 2FA. Vui lòng nhập mã OTP."))`.
- BR-13 enforce ở **query layer** (`permission_query_conditions`) — KHÔNG ở handler — để mọi `get_list`/list endpoint tự lọc; **invariant `count == rows`** vẫn phải đúng sau khi bật scope (count đếm sau khi áp scope = số rows trả ra).

> Quan hệ "NV ↔ BV được giao" (input cho BR-13) **chưa tồn tại field** ở D1 → **[cần khảo sát]** mô hình phân công: (a) child table `assigned_reps` trên `AntMed Hospital`, hoặc (b) bảng `AntMed Data Scope` (role/user → hospital). Scaffold nghiêng (b). Chốt ở W4 (viết ADR Supersede ADR-M01-05).

---

## 5. API

> File **[PLANNED — W4]**: `crm/api/antmed/audit.py`. Mọi hàm `@frappe.whitelist(methods=[...])`, **type-annotated** (`crm/hooks.py: require_type_annotated_api_methods = True`), trả **RAW dict/list** (KHÔNG `_ok/_err`/envelope). Lỗi nghiệp vụ/permission = `frappe.throw(...)` in-handler.

| Endpoint (`crm.api.antmed.audit.*`) | Verb | Mô tả (ĐỀ XUẤT) |
|---|---|---|
| `audit.write_log` | (server-side, **không** whitelist — gọi từ `doc_events`/handler) | Ghi 1 bản ghi `AntMed Audit Log`: tính `prev_hash` = `hash_sha256` của log gần nhất, `hash_sha256 = sha256(prev_hash + canonical_payload)`. Idempotent theo `(ref_doctype, ref_name, action, ts)`. **BR-10**. |
| `audit.verify_chain` | (server-side / `bench execute`) | Duyệt toàn bộ log theo thứ tự `ts`, tái tính hash từng bước; trả `{ "ok": bool, "broken_at": str\|None, "count": int }`. Phát hiện điểm gãy chuỗi. **BR-10**. |
| `audit.list_logs` | GET | List audit cho màn admin: `filters`(dict\|str), `start`, `page_length`, fields `ref_doctype/ref_name/action/actor/ip_address/ts/hash_sha256`. Trả `{ "data": [...], "total_count": int }` — **invariant `count == rows`** khi không phân trang. |
| `audit.get_log` | GET | Chi tiết 1 bản ghi (kèm `before_json/after_json/diff_json`); `frappe.has_permission` → `PermissionError` nếu không đọc được. |
| `audit.request_2fa` | POST | Tạo `AntMed 2FA Session` cho `(user, action_label)`: sinh OTP, lưu `otp_hash` + `expires_at` (TTL ngắn), gửi OTP qua kênh (Email/SMS/Zalo — M13). Trả `{ "session": name, "expires_at": ... }`. **BR-12**. |
| `audit.confirm_2fa` | POST | Xác nhận OTP cho session: so `otp_hash`, check chưa `used` & chưa hết hạn → set `used=1`; trả `{ "ok": true }`. Sai/hết hạn → `frappe.throw(_("BR-12: Mã OTP không hợp lệ hoặc đã hết hạn."))`. |
| `audit.require_2fa_and_log` | (server-side helper) | Gate dùng trong handler thao tác nguy hiểm: kiểm tra có 2FA session `used` hợp lệ trong TTL cho action; nếu chưa → throw BR-12; nếu có → `write_log` rồi cho qua. |

> **Lưu ý namespace**: scaffold cũ ghi `antmed_crm.m14_security_audit.audit.*` / `antmed_crm.api.*` — **SAI** ở build in-place. Đúng = **`crm.api.antmed.audit.*`**.
>
> **W0 hiện có** (verify @source `crm/api/antmed/rbac.py`): helper **nội bộ** (không whitelist) `is_antmed_user`, `is_crm_or_antmed_user`, hằng `ANTMED_ALLOWED_ROLES`. Không phải endpoint nghiệp vụ — phục vụ boot gate (xem `./m14_rbac_w0_antmed_boot.md`).

---

## 6. Integration

**Hướng phụ thuộc (DAG)**: M14 là **nền** — không phụ thuộc module nghiệp vụ; **cấp dịch vụ** (RBAC/audit/2FA/scope) cho tất cả M01–M13. Wiring là **một chiều vào** M14 (các module gọi gate của M14), tránh circular.

- **doc_events vào M14 (audit, BR-10)** — `crm/hooks.py` `doc_events` THÊM nhánh cho các doctype trọng yếu (vật tư/bộ dụng cụ/chứng từ), trỏ `crm.antmed.audit_hooks.<fn>`:
  ```python
  # ĐỀ XUẤT (W4) — chỉ THÊM, không sửa nhánh CRM gốc
  doc_events = {
      "AntMed Stock Entry":  {"on_submit": "crm.antmed.audit_hooks.log_stock_entry", "on_cancel": "..."},
      "AntMed Delivery":     {"on_submit": "crm.antmed.audit_hooks.log_delivery", "on_trash": "..."},
      "AntMed Lot":          {"on_update": "crm.antmed.audit_hooks.log_lot"},
      "AntMed Instrument Set": {"on_update": "crm.antmed.audit_hooks.log_instrument"},
      # chứng từ CO/CQ/HĐĐT (M06): "AntMed Document": {...}
  }
  ```
  Mỗi hook **lazy-import** `from crm.api.antmed import audit` rồi `audit.write_log(doc.doctype, doc.name, action, before, after)` — truyền **PK + payload**, không truyền object nặng.
- **2FA gate (BR-12)** — handler thao tác nguy hiểm ở M03/M04/M06 gọi `audit.require_2fa_and_log(action_label=...)` **đầu** hàm (trước khi mutate). M14 cung cấp helper; module gọi.
- **Data-scope (BR-13)** — `permission_query_conditions` map trong `crm/hooks.py` (THÊM key cho doctype AntMed scoped) → hàm trong `crm.antmed.data_scope.get_<doctype>_query_conditions(user)` đọc `AntMed Data Scope`. Là **gate compliance** cho mọi list của các module gắn scope.
- **RBAC boot (W0, đã có)** — `crm/api/__init__.py::check_app_permission`, `crm/api/session.py::get_session_role_flags`, `crm/www/crm.py::get_boot`, `frontend/src/router.js` đều OR-thêm nhánh AntMed qua `crm.api.antmed.rbac` (single-source). Chi tiết: `./m14_rbac_w0_antmed_boot.md`.

> **Gate compliance ngoài**: audit phục vụ thanh kiểm tra ngành y tế (export theo yêu cầu thanh tra) — gắn với compliance chứng từ M06 (CO/CQ/ĐKLH/HĐĐT). M14 không tự sinh chứng từ, chỉ ghi vết & chặn 2FA khi phát hành.

---

## 7. UI

> Vue 3 + frappe-ui SPA. Route mới APPEND vào `frontend/src/router.js` (lazy), gọi `crm.api.antmed.audit.*`. Vai trò dùng: **`Quản lý`** (admin/audit), `[PLANNED]` CEO/System Admin. Ground @ `AntMed_CRM_UI_Design.md §8` (System Admin / Quản trị) + §9 dòng 14.

| Route (THÊM mới — lazy) | Page (`pages/Antmed*.vue`) | Màn hình (UI_Design) | Role dùng |
|---|---|---|---|
| `/antmed/admin/audit` | `AntmedAuditLog.vue` | **§8.2 "Audit log"** — bảng lọc: actor, đối tượng (lot/phiếu giao/hóa đơn/bộ dụng cụ), hành động, IP, thời gian, **diff trước-sau**; nút **Export** theo yêu cầu thanh tra | `Quản lý`, `[PLANNED]` CEO |
| `/antmed/admin/users` | `AntmedUserRole.vue` | **§9 dòng 14 "User & Role"** — gán user ↔ Role VI ↔ data-scope (BV được giao) | `Quản lý`, `[PLANNED]` System Admin |
| *(không có route mới)* | component 2FA modal | OTP modal bật khi thao tác nguy hiểm (xuất kho/phát hành HĐĐT/xóa chứng từ) — gọi `request_2fa`/`confirm_2fa` | tất cả thao tác viên |

- **Audit log page**: dùng `createResource({ url: 'crm.api.antmed.audit.list_logs', ... })` (shape bọc `{data,total_count}` như M01); click 1 dòng → `get_log` hiển thị `diff_json` (Audit timeline component, UI_Design §10.x). Export = nút gọi endpoint export (hoặc Frappe report export).
- **Nút thao tác nguy hiểm**: theo UI_Design §A11y "mọi nút thao tác nguy hiểm có double-confirm + audit" → 2FA modal là lớp confirm cho 3 action BR-12.
- **Boundaries UI**: lazy import; `__()` cho nhãn VN; **Never** gọi `antmed_crm.api.*` (đúng = `crm.api.antmed.*`); **Never** sửa route/sidebar CRM gốc.

---

## 8. Build slices (cho factory — mỗi slice 1 vòng)

**W0 (đã land — tham chiếu, KHÔNG làm lại):**
- ✅ **S0-1** Role VI + rename idempotent (`./m14_rbac_w0_role_naming.md`).
- ✅ **S0-2** Boot allow-check additive `rbac.py` + 3 gate + boot flag (`./m14_rbac_w0_antmed_boot.md`).
- 🟡 **S0-3 (audit-lite skeleton)** — đặt chỗ; **chưa** hash-chain đầy đủ. *(W4 hoàn thiện.)*

**W4 (M14-full — [PLANNED], thứ tự đề xuất):**
1. **S1 — Audit hash-chain (BR-10)**: DocType `AntMed Audit Log` (append-only) + `crm/api/antmed/audit.py::write_log/verify_chain` + test chuỗi hash (insert N log → `verify_chain().ok == True`; sửa 1 bản ghi → phát hiện `broken_at`).
2. **S2 — Audit wiring**: `crm/antmed/audit_hooks.py` + THÊM `doc_events` cho doctype trọng yếu (lazy-import); `list_logs`/`get_log` + page `AntmedAuditLog.vue` (route `/antmed/admin/audit`).
3. **S3 — 2FA (BR-12)**: DocType `AntMed 2FA Session` + `request_2fa`/`confirm_2fa`/`require_2fa_and_log`; gate vào 3 thao tác nguy hiểm (xuất kho/phát hành HĐĐT/xóa chứng từ) ở M03/M04/M06; 2FA modal FE.
4. **S4 — Data-scope (BR-13)**: DocType `AntMed Data Scope` + `permission_query_conditions` cho ≤5 doctype + page `AntmedUserRole.vue`; **giữ invariant `count==rows`**; viết ADR Supersede ADR-M01-05. *(Cần chốt mô hình NV↔BV trước.)*
5. **S5 — Role profile / vai trò mở rộng**: bổ sung Role VI còn thiếu (CEO/Kế toán/Chứng từ/System Admin) + Role Profile (fixture, xem ADR-M14-04).

> Mỗi slice vertical (BE DocType+API+test → FE page nếu có), TDD failing-first, no-regression. KHÔNG commit (HARD-STOP user).

---

## 9. ADRs

### ADR-M14-01: Audit trail = DocType native `AntMed Audit Log` + hash-chain SHA256 (BR-10)
- **Status**: Proposed (W4)
- **Date**: 2026-06-17
- **Context**: thanh kiểm tra ngành y tế yêu cầu nhật ký **bất biến** chứng minh không sửa hậu kỳ. Frappe có `track_changes`/Version core nhưng **không** chống sửa (admin có thể xóa Version) và không có chuỗi hash. Scaffold cũ đề xuất `AM Audit Log` với `prev_hash`/`hash_sha256`.
- **Decision**: DocType native `AntMed Audit Log` append-only; `write_log` nối chuỗi `hash_sha256 = sha256(prev_hash + canonical_payload)`; `verify_chain` phát hiện gãy. Ghi qua `doc_events` (lazy-import).
- **Consequences**: (+) bất biến kiểm chứng được, export thanh tra. (−) chi phí ghi mỗi thao tác trọng yếu (chấp nhận — chỉ doctype trọng yếu, không log mọi read). (−) cần chuẩn hóa `canonical_payload` (sắp xếp key) để hash ổn định — *cần chốt khi code S1*.

### ADR-M14-02: Data-scope BR-13 bằng `permission_query_conditions` (bật W4) — **kế thừa/Supersede ADR-M01-05**
- **Status**: Proposed (W4) — sẽ **Supersedes ADR-M01-05** khi bật
- **Date**: 2026-06-17
- **Context**: R2 hoãn data-scope (ADR-M01-05) vì chưa có mô hình "NV phụ trách BV"; vẫn giữ invariant `count==rows` để không vỡ contract khi bật sau.
- **Decision**: W4 thêm `AntMed Data Scope` + `permission_query_conditions` (THÊM key vào `crm/hooks.py`, không sửa nhánh CRM gốc `CRM Lead`/`CRM Deal` hiện có) cho ≤5 doctype AntMed; lọc ở query layer; `count` đếm sau scope == rows trả ra.
- **Consequences**: (+) least-privilege thật, không rò rỉ BV. (−) buộc chốt mô hình NV↔BV (cần khảo sát). (−) phải bổ sung test data-scope (count==rows theo từng NV).

### ADR-M14-03: Allow-check ADDITIVE cho boot + bootflag (DEC-B) — đã quyết ở W0
- **Status**: Accepted (W0 — land rồi)
- **Tham chiếu**: ADR-M14W0-03 + ADR-M14W0-04 trong `./m14_rbac_w0_antmed_boot.md` (OR-thêm nhánh AntMed ở 3 gate, single-source `ANTMED_ALLOWED_ROLES`, FE đọc `window.is_antmed_user`). Core Doc này KHÔNG lặp lại nội dung — chỉ ghi nhận đã quyết.

### ADR-M14-04: Role Profile bằng fixture core thay vì DocType `AntMed Role Profile Seed`
- **Status**: Proposed (W4) — *cần khảo sát*
- **Context**: scaffold cũ đề xuất DocType `AM Role Profile Seed` (`role_profile` + `permissions_json`). Frappe core đã có DocType `Role Profile`.
- **Decision (đề xuất)**: dùng **fixture `role_profile.json`** (như `role.json` W0) thay vì DocType seed riêng — đơn giản, idempotent, không phình schema. Chỉ tạo DocType seed nếu cần cấu hình động ngoài Role Profile core.
- **Consequences**: (+) gọn, nhất quán cơ chế fixture đã dùng cho Role. (−) nếu nghiệp vụ cần seed permissions tùy biến ngoài Role Profile core → xét lại. **Chốt khi code S5.**

> DEC-A (Role VI) đã quyết ở W0 — xem ADR-M14W0-01 (`./m14_rbac_w0_role_naming.md`, Supersedes ADR-M01-02). DEC-B (tách route/guard) — ADR-M14W0-03.

---

## 10. Acceptance / DoD

Theo SPEC §6 — một lát cắt "xong" = BE test xanh THẬT + FE vitest + build + (sau USER reload) pixel-verify + no-regression.

**W0 (đã đạt — tham chiếu 2 slice doc):**
- BE: `bench --site miyano run-tests --module crm.tests.test_antmed_bootstrap` (3 Role VI tồn tại, 0 Role EN) + `crm.tests.test_antmed_rbac_boot` (allow-check additive) → `Ran N OK`, 0 fail.
- No-regression: `test_antmed_customer` + test gốc CRM (`test_org_hierarchy`, `test_crm_lead`, `test_crm_task`) xanh.
- FE: `yarn vitest run` ≥ baseline (≥138 gồm guard) + `yarn build` xanh.

**W4 (M14-full — DoD đề xuất, [PLANNED]):**
1. **BR-10**: `bench --site miyano run-tests --module crm.tests.test_antmed_audit` → `Ran N OK`. TC: write_log nối chuỗi đúng (`prev_hash` của log sau == `hash_sha256` của log trước); `verify_chain().ok == True` với N log; sửa/chèn 1 bản ghi → `ok == False` + `broken_at` đúng; `bench --site miyano execute crm.api.antmed.audit.verify_chain` chạy được.
2. **BR-12**: test `request_2fa` → `confirm_2fa` (đúng OTP, trong TTL) → `used=1`; OTP sai/hết hạn/replay (`used=1`) → `frappe.throw` BR-12; thao tác nguy hiểm thiếu 2FA hợp lệ → bị chặn.
3. **BR-13**: test 2 NV khác BV phụ trách → mỗi NV `list_*` chỉ thấy BV được giao; **`len(data) == total_count`** theo từng NV (count==rows sau scope); user không scope → không rò rỉ.
4. **FE**: vitest cho `AntmedAuditLog`/`AntmedUserRole` (route/lazy, gọi đúng `crm.api.antmed.audit.*`, KHÔNG `antmed_crm.api`/axios) + `yarn build` xanh.
5. **No-regression**: toàn bộ test W0 + test gốc CRM còn xanh; `permission_query_conditions` CRM gốc (`CRM Lead`/`CRM Deal`) KHÔNG đổi.
6. **Pixel (sau USER reload)**: `/antmed/admin/audit` render bảng lọc + diff; 2FA modal hiện đúng khi thao tác nguy hiểm; 0 console error.

---

## Tham chiếu chéo
- Sources: `../SPEC_AntMed_CRM.md` (§6 Testing/DoD), `../PLAN_AntMed_CRM.md` (M14 wave W0/W4, D4 audit hash-chain), `../../antmed_crm/docs/AntMed_CRM_Modules.md` (§14 Phân quyền/Bảo mật/Audit), `../../antmed_crm/docs/AntMed_CRM_UI_Design.md` (§8 System Admin, §8.2 Audit log, §9 dòng 14).
- **2 slice doc W0 (đã/đang hiện thực — nguồn quyết định, KHÔNG rewrite ở Core Doc này):** `./m14_rbac_w0_role_naming.md` (DEC-A, 3 Role VI, ADR-M14W0-01/02), `./m14_rbac_w0_antmed_boot.md` (DEC-B, allow-check additive, ADR-M14W0-03/04).
- Module liên quan: `./m01_customer360.md` (BR-13 hoãn — ADR-M01-05, invariant count==rows), `./m01_bootstrap.md` (namespace `crm/antmed/`, 3 Role).
- Reference scaffold (app-tách cũ, adapt `AM `→`AntMed `, ERPNext→native-lite, namespace `antmed_crm.*`→`crm.api.antmed.*`): `docs/antmed_crm/antmed_crm/m14_security_audit/doctype/` (`am_audit_log`, `am_data_scope`, `am_2fa_session`, `am_role_profile_seed`).
- README BR map: `docs/antmed_crm/README.md` (BR-10 hash chain, BR-12 2FA, BR-13 permission_query_conditions 5 doctype).
- Source thật W0 (verify): `crm/fixtures/role.json`, `crm/api/antmed/rbac.py`, `crm/api/__init__.py`, `crm/api/session.py`, `crm/www/crm.py`, `frontend/src/router.js`.
