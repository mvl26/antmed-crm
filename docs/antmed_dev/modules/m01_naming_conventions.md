# AntMed — Convention naming FE ↔ BE (R1 in-place)

| Mục | Giá trị |
|---|---|
| Phạm vi | Namespace in-place AntMed bên trong app `crm` |
| Nguồn | Acceptance R1 (M01 Bootstrap) + `crm/hooks.py`, `crm/modules.txt` (verify @ source) |
| Đích mirror | `crm/antmed/README.md` (BE copy nội dung này, 1 trang) |
| Cập nhật | 2026-06-17 |

> Tài liệu này là **hợp đồng đặt tên** để R2 (M1 Khách hàng/Bệnh viện) và các round sau theo nhất quán, KHÔNG phải bịa lại mỗi round.

---

## 1. Namespace Python (BE)

| Loại | Quy ước | Ví dụ R1 |
|---|---|---|
| Module Frappe | `AntMed` (khai trong `crm/modules.txt`) | `AntMed` |
| Thư mục code module | `crm/antmed/` | `crm/antmed/__init__.py` |
| Package API | `crm/api/antmed/` (có `__init__.py`) | `crm/api/antmed/health.py` |
| Đường gọi endpoint | `crm.api.antmed.<module>.<fn>` | `crm.api.antmed.health.ping` |
| File api theo module nghiệp vụ (round sau) | `crm/api/antmed/<module>.py` | `crm/api/antmed/hospitals.py` |

**Cấm**: `antmed_crm.api.*`, `assetcore.*`, app riêng `antmed_crm`. (ADR-M01-01)

---

## 2. DocType prefix

| Trường hợp | Prefix | Ví dụ |
|---|---|---|
| DocType nghiệp vụ AntMed (round sau) | **`AntMed `** | `AntMed Hospital Profile`, `AntMed Contract` |
| DocType ERPNext/Frappe reuse | KHÔNG prefix | `Delivery Note`, `Customer`, `Item`, `Warehouse`, `Role` |

> ADR-M01-02: bản in-place dùng `AntMed ` (KHÔNG `AM `) cho **DocType nghiệp vụ**. Map sang tài liệu domain skill: `AM Xxx` (skill) ↔ `AntMed Xxx` (bản in-place). Khi tách app sẽ viết ADR Supersede.
>
> ⚠️ Phần **Role** của ADR-M01-02 (tên Role tiếng Anh) đã bị **Supersede** bởi ADR-M14W0-01 (Role → nhãn tiếng Việt). Prefix `AntMed ` vẫn áp cho **DocType**, KHÔNG còn áp cho **Role name**.

---

## 3. Role naming (RBAC) — ⚠️ ĐÃ ĐỔI sang tiếng Việt (DEC-A, Supersede)

> 🔴 **DEC-A (2026-06-17)**: `name` Role đổi sang **nhãn tiếng Việt**. Bảng EN dưới là **lịch sử R1** (ADR-M01-02, đã Supersede bởi ADR-M14W0-01). Spec rename idempotent: `./m14_rbac_w0_role_naming.md`.

| `name` Role HIỆN HÀNH (VI, DEC-A) | `name` cũ R1 (EN, lịch sử) | Vai trò |
|---|---|---|
| `NV kinh doanh` | `AntMed Sales Rep` | Nhân viên kinh doanh |
| `Thủ kho` | `AntMed Warehouse Keeper` | Thủ kho |
| `Quản lý` | `AntMed Manager` | Quản lý |

- Tên Role = **nhãn tiếng Việt** (`name` == `role_name`), `is_custom=1`, `desk_access=1`.
- FE đã verify KHÔNG dùng role-string (`grep get_roles/role = 0` trong `frontend/src`) → đổi tên an toàn cho FE.
- DocPerm: `Quản lý` full; `NV kinh doanh` read/write/create (KHÔNG delete); `Thủ kho` không gắn trên Hospital/Doctor (xem `./m14_rbac_w0_role_naming.md` §DocPerm).

---

## 4. API contract (Frappe-standard)

- Endpoint = `@frappe.whitelist(methods=[...])` **tường minh verb** (KHÔNG bare whitelist). GET cho đọc, POST cho ghi.
- Trả **RAW dict/list** — KHÔNG envelope `_ok`/`_err`, KHÔNG registry `MSG.*`.
- Lỗi nghiệp vụ = in-handler `frappe.throw(_("BR-XX: <thông điệp tiếng Việt>"))` (Frappe trả exception JSON).
- Hàm whitelist phải **type-annotate** (param + return) — `crm/hooks.py:28 require_type_annotated_api_methods = True`.
- **2 loại 403** phân biệt rõ khi đặc tả:
  - **dispatcher-403**: guest/không session cookie gọi endpoint không `allow_guest`.
  - **in-handler permission-403**: `frappe.throw(..., frappe.PermissionError)` khi thiếu role/data-scope.
- **count == rows** (round có list endpoint): số bản ghi list trả ra phải khớp khi drill theo `permission_query_conditions` (data-scope BR-13).

---

## 5. Frontend (Vue 3 + frappe-ui SPA)

| Loại | Prefix / quy ước | Ví dụ R1 |
|---|---|---|
| Route path | `/antmed` (gốc) → `/antmed/<feature>` | `/antmed` |
| Route name | PascalCase tiền tố `Antmed` | `AntmedHome` |
| Page component | `frontend/src/pages/Antmed<Feature>.vue` | `AntmedHome.vue` |
| Store (round sau) | `frontend/src/stores/antmed<Feature>.js` → `useAntmed<Feature>Store` | `antmedHospitals.js` |
| Resource call | `createResource({ url: 'crm.api.antmed.<module>.<fn>' })` | `crm.api.antmed.health.ping` |

**Cấm**: sửa/xoá route/page/store Frappe CRM gốc (Leads/Deals/Contacts/Tasks…). Chỉ THÊM route/page mới prefix `Antmed`.

---

## 6. Fixtures & hooks

- Fixture file: **`crm/fixtures/<doctype_snake>.json`** (verify @ source — Frappe `import_fixtures` chỉ load từ `apps/crm/crm/fixtures/`; `crm/fcrm/fixtures/` hay `crm/antmed/fixtures/` KHÔNG được `bench migrate` đọc).
- `crm/hooks.py`: chỉ **THÊM** key `fixtures = [...]` (trước R1 chưa có). KHÔNG đụng `permission_query_conditions` / `doc_events` / `after_migrate` / `before_tests` / `scheduler_events` gốc.

---

## 7. Test

- BE test: `crm/api/antmed/test_<module>.py` hoặc `crm/antmed/tests/test_<module>.py`.
- Lệnh: `bench --site miyano run-tests --module crm.api.antmed.test_<module>`.
- Mỗi feature mới: ≥1 test mới, 0 fail, + chạy lại 4 test gốc (no-regression).

---

## Tham chiếu chéo
- Spec bootstrap đầy đủ: `./m01_bootstrap.md`
- Domain 14 module: `../../antmed_crm/docs/AntMed_CRM_Modules.md`
