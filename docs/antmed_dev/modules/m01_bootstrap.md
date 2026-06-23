# M01 — Bootstrap nền AntMed (app riêng `antmed_crm`)

| Mục | Giá trị |
|---|---|
| Module folder | `antmed_crm/antmed/` (module Frappe tên **`AntMed`**, khai trong `antmed_crm/modules.txt`) |
| API package | `antmed_crm/api/antmed/` (package, có `__init__.py`) |
| Phase triển khai | 0 — Foundation (KHÔNG phải feature M1 nghiệp vụ) |
| Role chính | `NV kinh doanh`, `Thủ kho`, `Quản lý` (⚠️ đổi tiếng Việt theo DEC-A — xem `./m14_rbac_w0_role_naming.md`; R1 gốc dùng EN, đã Supersede) |
| Site dev | `miyano` |
| Trạng thái docs | Stable (spec chốt cho R1) |
| Cập nhật | 2026-06-17 |

> 🔴 **Self-Correction (DEC-A, 2026-06-17)**: Tên 3 Role đã đổi sang **tiếng Việt** (`NV kinh doanh` / `Thủ kho` / `Quản lý`) — **ADR-M01-02 (tên EN) đã bị Supersede** bởi ADR-M14W0-01. Mọi mục nhắc tên Role EN bên dưới (§Scope, §Fixtures, §ADR-M01-02) là **ngữ cảnh lịch sử R1**; nguồn quyết định cuối về Role naming = `./m14_rbac_w0_role_naming.md`.

> ⚠️ **ADR-M01-01 (xem §ADR)**: AntMed là **app RIÊNG `antmed_crm`** (fork từ Frappe CRM, cài như app riêng trên site — KHÔNG tách thành 2 app). Code AntMed sống trong module `antmed_crm/antmed/` + endpoint package `antmed_crm/api/antmed/` → đường gọi `antmed_crm.api.antmed.<module>.<fn>`. App DUY NHẤT cài là `antmed_crm`; KHÔNG dùng namespace cũ `crm.api.*`. Doctype prefix `AntMed ` (xem ADR-M01-02). R1 chỉ đặt nền namespace + RBAC + harness, chưa tạo doctype nghiệp vụ.

---

## Overview

M01 là **foundation round (R1)**: dựng nền để các round M0X tiếp theo (M1 Khách hàng/Bệnh viện, M2 Hợp đồng-quota, …) có chỗ "đậu" mà KHÔNG phá Frappe CRM gốc. Phạm vi R1 thuần kỹ thuật:

1. **Namespace** `antmed_crm/antmed/` (Python module `AntMed`) + `antmed_crm/api/antmed/` (package endpoint).
2. **3 Role fixture RBAC** load qua `bench migrate`, reproduce được (export fixture + khai trong `hooks.py`).
3. **1 endpoint smoke** `antmed_crm.api.antmed.health.ping()` chứng minh đường BE callable (RAW dict).
4. **Convention naming FE↔BE** (1 trang) đủ để R2 (M1) theo.
5. **Harness test xanh** (≥1 test mới, 0 fail) + **FE smoke** route `/antmed` → `AntmedHome.vue` gọi `health.ping`.
6. **No-regression**: 4 test gốc Frappe CRM vẫn PASS; `hooks.py` mở rộng AN TOÀN.

**Business value (R1)**: giảm rủi ro merge — AntMed là app riêng fork từ Frappe CRM, tái dùng toàn bộ hạ tầng (auth, desk, frontend SPA, build), cô lập code AntMed dưới prefix `antmed`/`Antmed`/`AntMed ` để dễ grep, dễ bảo trì.

---

## Scope — Boundaries (Always / Never)

### Always (R1 LUÔN làm)
- **Always** tạo thư mục Python `antmed_crm/antmed/` có `__init__.py` (rỗng hợp lệ) + khai module **`AntMed`** trong `antmed_crm/modules.txt` (thêm dòng mới, GIỮ `FCRM` và `Lead Syncing`).
- **Always** tạo package `antmed_crm/api/antmed/__init__.py` + file `antmed_crm/api/antmed/health.py` chứa `ping()`.
- **Always** tạo đúng **3 Role**: `AntMed Sales Rep`, `AntMed Warehouse Keeper`, `AntMed Manager` (tên tiếng Anh, KHÔNG dấu — để FE/RBAC ổn định; nhãn tiếng Việt ghi trong doc).
- **Always** export 3 Role ra fixture **`antmed_crm/fixtures/role.json`** (path Frappe `import_fixtures` thực sự load) + khai `fixtures` list trong `hooks.py`.
- **Always** giữ `permission_query_conditions`, `doc_events`, `after_migrate`, `before_tests`, `scheduler_events` của Frappe CRM gốc NGUYÊN VẸN — chỉ THÊM key `fixtures` (hiện chưa có).
- **Always** type-annotate hàm `ping()` (return type hint) — vì `hooks.py:28 require_type_annotated_api_methods = True`.
- **Always** dùng `methods=["GET"]` tường minh cho `ping()` (KHÔNG bare `@frappe.whitelist()`).

### Never (R1 TUYỆT ĐỐI KHÔNG)
- **Never** tách thành 2 app (app DUY NHẤT cài là app riêng `antmed_crm`), **Never** dùng namespace cũ `crm.api.*` hay `assetcore.*`.
- **Never** tạo bất kỳ DocType nghiệp vụ nào (Hợp đồng/Quota/DR/Loan/Chứng từ…) — đó là round sau.
- **Never** xoá/sửa/đụng `permission_query_conditions`, `doc_events`, `override_doctype_class`, `after_migrate`, `before_tests` sẵn có.
- **Never** đụng route/page/store Frappe CRM gốc (`frontend/src/router.js` chỉ THÊM 1 route mới; KHÔNG sửa route cũ).
- **Never** git commit / push / merge / reset DB / drop site (HARD-STOP — thuộc user).
- **Never** wrap response bằng envelope `_ok`/`_err` hay registry `MSG.*` — `ping()` trả RAW dict thuần.
- **Never** gán DocPerm nghiệp vụ cho 3 Role ở R1 (chỉ tạo Role rỗng quyền; permission gắn ở round có doctype).

---

## DocTypes

**KHÔNG có DocType nghiệp vụ mới ở R1.** Chỉ tạo bản ghi của DocType lõi Frappe **`Role`** (3 bản ghi) qua fixture — không phải DocType mới.

| Loại | Tên | Ghi chú |
|---|---|---|
| Frappe core DocType (reuse) | `Role` | Tạo 3 bản ghi fixture (xem §Fixtures) |

---

## Fixtures (RBAC — 3 Role)

> 🔴 **OUTDATED (R1 lịch sử)** — DEC-A/W0-1 đã đổi `name` Role sang tiếng Việt và đổi cơ chế (patch `rename_doc` + fixture VI). Khi BE code fixture/hooks **dùng `./m14_rbac_w0_role_naming.md` §Fixtures làm chuẩn**, KHÔNG copy bảng/JSON EN bên dưới.

3 Role (R1 gốc dùng **tên định danh tiếng Anh**; **đã Supersede** → xem banner đầu file & `./m14_rbac_w0_role_naming.md`), nhãn vai trò tiếng Việt:

| `name` (Role) | Vai trò (VN) | `desk_access` | Ghi chú R1 |
|---|---|---|---|
| `AntMed Sales Rep` | NV kinh doanh | 1 | Role rỗng quyền nghiệp vụ ở R1 |
| `AntMed Warehouse Keeper` | Thủ kho | 1 | nt |
| `AntMed Manager` | Quản lý | 1 | nt |

**Acceptance kiểm chứng**: sau `bench --site miyano migrate`, cả 3 thỏa
`frappe.db.exists("Role", "<tên>") == True`.

### Định dạng fixture (chuẩn Frappe Role)
Export ra `role.json` (mảng object), mỗi Role tối thiểu:
```json
{
  "doctype": "Role",
  "name": "AntMed Sales Rep",
  "role_name": "AntMed Sales Rep",
  "desk_access": 1,
  "disabled": 0
}
```
> *(Cần khảo sát)*: các flag phụ (`restrict_to_domain`, `home_page`, `two_factor_auth`) để mặc định ở R1; 2FA (BR-12) gắn ở round M14, KHÔNG bật cứng tại R1.

### Khai trong `hooks.py` (AN TOÀN — chỉ THÊM key)
`antmed_crm/hooks.py` hiện **CHƯA có** biến `fixtures` (đã verify @ source). BE THÊM mới — KHÔNG đụng key khác:
```python
# Fixtures
# --------
fixtures = [
    {
        "doctype": "Role",
        "filters": {
            "name": [
                "in",
                ["AntMed Sales Rep", "AntMed Warehouse Keeper", "AntMed Manager"],
            ]
        },
    },
]
```
> **Boundaries — Ask-first**: nếu sau này export thêm fixture khác (Workflow/Custom Field) thì APPEND entry vào list này, KHÔNG biến nó thành mảng string trống/null.

> **Vị trí file fixture** *(đã verify @ source — BE chốt)*: PHẢI là `antmed_crm/fixtures/role.json`. Frappe `import_fixtures(app)` chỉ đọc từ `frappe.get_app_path(app, "fixtures")` = `apps/antmed_crm/antmed_crm/fixtures/` (xác minh qua `frappe.utils.fixtures.import_fixtures`). File đặt ở `antmed_crm/fcrm/fixtures/` HOẶC `antmed_crm/antmed/fixtures/` sẽ **KHÔNG** được `bench migrate` load (đã thử nghiệm: fixture ở `antmed_crm/fcrm/fixtures/role.json` → 3 Role KHÔNG được tạo). Spec cũ nói `antmed_crm/fcrm/fixtures/` là **SAI** — đã sửa.

---

## API

### Endpoint smoke — `antmed_crm.api.antmed.health.ping`

| Thuộc tính | Giá trị |
|---|---|
| Đường dẫn gọi | `antmed_crm.api.antmed.health.ping` |
| File | `antmed_crm/api/antmed/health.py` |
| Decorator | `@frappe.whitelist(methods=["GET"])` (KHÔNG bare) |
| Verb | GET |
| Auth | Yêu cầu session (KHÔNG `allow_guest`) → guest = dispatcher-403 |
| Trả về | **RAW dict thuần** (không envelope) |

**Shape trả về (cố định)**:
```json
{ "app": "antmed", "status": "ok", "version": "<antmed_crm.__version__>" }
```
- `version` lấy động từ `antmed_crm.__version__` (hiện `1.73.2` @ `antmed_crm/__init__.py:1`) — KHÔNG hard-code chuỗi.
- Hàm phải có return type hint, ví dụ `def ping() -> dict:` (do `hooks.py:28 require_type_annotated_api_methods = True`).

**Spec-contract (Frappe-standard — DONE-gate)**:
- Trả RAW dict/list (KHÔNG `_ok`/`_err`, KHÔNG `MSG.*`).
- Lỗi nghiệp vụ (round sau) = in-handler `frappe.throw(_("BR-XX: <thông điệp VN>"))` → Frappe trả exception JSON. R1 `ping()` không có nhánh lỗi nghiệp vụ.
- **2 loại 403** phân biệt khi đặc tả: **dispatcher-403** (guest/không session cookie gọi endpoint không `allow_guest`) vs **in-handler permission-403** (`frappe.throw(..., frappe.PermissionError)` khi thiếu role/data-scope). R1 `ping()` chỉ phụ thuộc dispatcher-403 (cần đăng nhập); chưa kiểm tra role.

> **[ROADMAP]** Endpoint nghiệp vụ thật (list/detail) ở round sau phải giữ invariant **count == rows** khi drill theo `permission_query_conditions` (data-scope BR-13). R1 chưa có list endpoint nên invariant này chưa áp dụng.

---

## UI

### Route + Page placeholder (FE smoke)

| Thuộc tính | Giá trị |
|---|---|
| Route path | `/antmed` |
| Route name | `AntmedHome` |
| Component | `frontend/src/pages/AntmedHome.vue` (lazy `() => import(...)`) |
| Hành vi | Gọi `createResource({ url: 'antmed_crm.api.antmed.health.ping' })`, hiển thị `status` |

**Boundaries UI (R1)**:
- **Always** THÊM 1 object route mới vào mảng `routes` trong `frontend/src/router.js` (lazy import, KHÔNG eager).
- **Never** sửa/xoá route, alias, `handleMobileView`, hay page Frappe CRM gốc (Leads/Deals/Contacts…).
- `AntmedHome.vue` là placeholder: render trạng thái `health.ping` (loading / `status: ok` / lỗi). KHÔNG cần layout sidebar đầy đủ ở R1.
- `vue-tsc` / `npm run build` (hoặc lint) phải KHÔNG vỡ.

> Màn hình nghiệp vụ theo 7 vai trò (`AntMed_CRM_UI_Design.md`) là round sau — R1 chỉ chứng minh đường FE→BE callable.

---

## Business Rules

**R1 chưa thực thi BR nghiệp vụ nào** (chưa có doctype/workflow). Doc này chỉ **đăng ký không gian BR** để round sau wiring vào `doc_events`/controller:

| BR (định hướng round sau) | Điểm wiring dự kiến | Trạng thái R1 |
|---|---|---|
| BR-01 đối chiếu danh mục trúng thầu | controller M02/M04 | `[ROADMAP]` |
| BR-02 chặn item ngoài HĐ | `doc_events` Delivery Note (M04) | `[ROADMAP]` |
| BR-06 khoá quota chạm trần | controller quota (M02/M04) | `[ROADMAP]` |
| BR-10 audit hash-chain | module M14 | `[ROADMAP]` |
| BR-12 2FA xuất kho/HĐ | module M14 | `[ROADMAP]` |
| BR-13 data-scope NV chỉ thấy BV được giao | `permission_query_conditions` (M14) | `[ROADMAP]` |

> Quy ước message BR (round sau): `frappe.throw(_("BR-XX: <thông điệp tiếng Việt>"))` in-handler.

---

## Integration

- **R1 KHÔNG thêm `doc_events`/`permission_query_conditions` mới.** Chỉ thêm key `fixtures` vào `hooks.py`.
- No-regression bắt buộc: 4 test gốc PASS sau khi thêm `fixtures`:
  - `antmed_crm.permissions.test_org_hierarchy`
  - `antmed_crm.fcrm.doctype.crm_lead.test_crm_lead`
  - `antmed_crm.fcrm.doctype.crm_territory.test_crm_territory`
  - `antmed_crm.fcrm.doctype.crm_task.test_crm_task`
- `before_tests = "antmed_crm.tests.before_tests"` (`hooks.py:209`) GIỮ NGUYÊN — test AntMed mới chạy chung harness.

---

## Test harness (acceptance)

### BE test mới (≥1 test, 0 fail)
- File *(BE chốt)*: `antmed_crm/tests/test_antmed_bootstrap.py` (chạy chung harness `before_tests`).
- TC (6 test, đều PASS):
  1. `test_three_roles_exist` — `frappe.db.exists("Role", x)` truthy cho cả 3 Role (sau migrate).
  2. `test_exactly_three_antmed_roles` — ĐÚNG 3 Role prefix `AntMed ` (không thừa/thiếu).
  3. `test_health_ping_shape` — `ping()` trả dict đúng 3 key `{app:"antmed", status:"ok", version}`.
  4. `test_health_ping_version_is_dynamic` — `version == antmed_crm.__version__` (str, động).
  5. `test_health_ping_is_get_only` — whitelisted, `allowed_http_methods == ["GET"]` (KHÔNG bare).
  6. `test_module_registered` — `"AntMed" in frappe.get_module_list("antmed_crm")` + `import antmed_crm.antmed` OK.
- Lệnh chạy THẬT (output OK):
  ```
  bench --site miyano run-tests --module antmed_crm.tests.test_antmed_bootstrap
  ```

### FE smoke
- `vue-tsc --noEmit` hoặc `npm run build` (hoặc `yarn build`) trong `frontend/` không vỡ.
- Route `/antmed` render `AntmedHome.vue`, resource `health.ping` trả `status: ok`.

---

## Build sequence (cho BE/FE — KHÔNG commit)

> Thứ tự để dev theo; BA chỉ chốt spec, dev thực thi.

1. **BE**: tạo `antmed_crm/antmed/__init__.py`; thêm dòng `AntMed` vào `antmed_crm/modules.txt` (lưu ý file hiện KHÔNG có newline cuối — phải xuống dòng trước khi thêm).
2. **BE**: tạo `antmed_crm/api/antmed/__init__.py` + `antmed_crm/api/antmed/health.py::ping()` (GET, type hint, RAW dict).
3. **BE**: tạo `antmed_crm/fixtures/role.json` (3 Role — path Frappe thực sự import) + thêm `fixtures = [...]` vào `antmed_crm/hooks.py` (chỉ THÊM key).
4. **BE**: `bench --site miyano migrate` → verify 3 `frappe.db.exists("Role", …)`.
5. **BE**: viết `test_health.py`; chạy `bench --site miyano run-tests --module …` (xanh) + chạy lại 4 test gốc (no-regression).
6. **FE**: tạo `frontend/src/pages/AntmedHome.vue` + thêm route `/antmed` vào `router.js`; `vue-tsc`/`build` pass.
7. **BE/Doc**: tạo `antmed_crm/antmed/README.md` (convention FE↔BE — xem `m01_naming_conventions.md`).

---

## ADR

### ADR-M01-01: Bootstrap app RIÊNG `antmed_crm` (chủ trương gốc: in-place; THỰC TẾ = app RIÊNG `antmed_crm`, không tách thành 2 app)
- **Status**: Accepted (Revised 2026-06-17 — đảo giả định tên app; xem §Consequences)
- **Date**: 2026-06-17
- **Context**: AntMed CRM **fork từ Frappe CRM** nhưng cài như **app RIÊNG** trên site (`miyano`) tên là **`antmed_crm`** (`sites/apps.txt` = `frappe, antmed_crm, …`). *(chủ trương gốc: in-place; THỰC TẾ = app RIÊNG `antmed_crm`.)* Yêu cầu: tái dùng auth/desk/SPA/build và giảm rủi ro merge với CRM gốc, KHÔNG tách thành 2 app.
- **Decision**: Đặt code AntMed trong app `antmed_crm` dưới module `antmed_crm/antmed/` (Python module Frappe `AntMed`) + package endpoint `antmed_crm/api/antmed/` → đường gọi whitelist `antmed_crm.api.antmed.<module>.<fn>`. App DUY NHẤT cài là `antmed_crm`; KHÔNG dùng namespace cũ `crm.api.*`.
- **Alternatives**:
  - *Tách thành 2 app (AntMed riêng + CRM riêng)* — loại: chi phí cài thêm app, đồng bộ build FE riêng, rủi ro chia đôi site.
  - *Nhét thẳng vào module `FCRM`* — loại: trộn code, khó grep/khó tách, dễ đụng test gốc.
- **Consequences**:
  - (+) Tái dùng toàn bộ hạ tầng app fork; chỉ thêm 1 module + 1 api package; dễ grep theo prefix `antmed`/`Antmed`/`AntMed `.
  - (−) Prefix doctype round sau là `AntMed ` (KHÔNG `AM `) để khớp role naming — **lệch** với domain doc skill (prefix `AM `). Khác biệt này ghi nhận tại ADR-M01-02.

### ADR-M01-02: Role/DocType naming dùng tiền tố `AntMed ` (không `AM `)
- **Status**: Accepted
- **Date**: 2026-06-17
- **Context**: Acceptance R1 chốt cứng 3 tên Role: `AntMed Sales Rep` / `AntMed Warehouse Keeper` / `AntMed Manager`. Skill domain dùng prefix ngắn `AM ` (vd `AM Sales Rep`). Hai prefix không khớp.
- **Decision**: R1 (và namespace `antmed_crm/antmed/`) dùng tiền tố **`AntMed `** cho Role; doctype nghiệp vụ round sau cũng dùng `AntMed ` để nhất quán với namespace `antmed_crm/antmed/` + FE prefix `Antmed*`.
- **Alternatives**: dùng `AM ` theo skill — loại vì acceptance R1 đã chốt tên `AntMed …`, đổi sẽ fail gate.
- **Consequences**: Tài liệu domain skill (prefix `AM `) là *tham chiếu định hướng*, KHÔNG phải tên thật của app `antmed_crm`. Khi nào quyết định đổi sang `AM ` → ADR mới Supersede ADR-M01-02. Mapping `AM ↔ AntMed ` phải nêu trong doc convention.

### ADR-M01-03: `fixtures` thay vì tạo Role trong `after_install`/patch
- **Status**: Accepted
- **Date**: 2026-06-17
- **Context**: 3 Role cần reproduce được trên mọi site qua `bench migrate`, không chỉ chạy 1 lần khi install.
- **Decision**: Export Role ra `role.json` + khai `fixtures` trong `hooks.py` (Frappe sync fixture mỗi `migrate`).
- **Alternatives**: tạo Role trong `after_install` hook (chỉ chạy 1 lần, không reproduce trên site đã cài) — loại; viết patch idempotent — loại vì fixture là cách chuẩn Frappe cho master data.
- **Consequences**: Mọi `bench migrate` đảm bảo 3 Role tồn tại; thêm/sửa Role chỉ cần sửa `role.json`. `hooks.py` thêm 1 key `fixtures` (trước đó chưa có) — an toàn no-regression.

---

## Tham chiếu chéo
- Convention naming FE↔BE: `./m01_naming_conventions.md` (và bản app `antmed_crm/antmed/README.md`)
- Mô tả nghiệp vụ 14 module: `../../antmed_crm/docs/AntMed_CRM_Modules.md`
- UI 7 vai trò: `../../antmed_crm/docs/AntMed_CRM_UI_Design.md`
- Source thật: `antmed_crm/hooks.py`, `antmed_crm/modules.txt`, `antmed_crm/__init__.py`, `antmed_crm/api/__init__.py`, `frontend/src/router.js`
