# AntMed CRM — namespace in-place (module `AntMed`)

> Bootstrap nền AntMed **bên trong app `crm`** (KHÔNG app riêng `antmed_crm`).
> SSoT spec: `docs/antmed_crm/docs/` (`m01_bootstrap.md`, `m01_naming_conventions.md`).
> Round R1 (M01) chỉ đặt nền — namespace + RBAC + smoke endpoint + harness. Chưa có DocType nghiệp vụ.

## Sơ đồ thư mục nền

```
crm/
├── modules.txt                 # khai module "AntMed" (cạnh FCRM, Lead Syncing)
├── hooks.py                    # CHỈ thêm key `fixtures` (3 Role) — KHÔNG đụng key gốc
├── antmed/                     # module Frappe "AntMed" (code nghiệp vụ round sau)
│   ├── __init__.py
│   └── README.md               # (file này) convention FE↔BE
├── api/antmed/                 # package endpoint — đường gọi antmed_crm.api.antmed.<module>.<fn>
│   ├── __init__.py
│   └── health.py               # ping() — smoke GET, RAW dict
├── fixtures/role.json          # 3 Role AntMed (Frappe import_fixtures CHỈ đọc crm/fixtures/)
└── tests/test_antmed_bootstrap.py   # harness R1 (BE)

frontend/src/
├── router.js                   # CHỈ thêm route /antmed (lazy) — KHÔNG đụng route gốc
└── pages/AntmedHome.vue        # placeholder gọi antmed_crm.api.antmed.health.ping
```

## 1. Namespace Python (BE)

| Loại | Quy ước | Ví dụ |
|---|---|---|
| Module Frappe | `AntMed` (khai `crm/modules.txt`) | `AntMed` |
| Thư mục code module | `crm/antmed/` | `crm/antmed/__init__.py` |
| Package API | `crm/api/antmed/` (có `__init__.py`) | `crm/api/antmed/health.py` |
| Đường gọi endpoint | `antmed_crm.api.antmed.<module>.<fn>` | `antmed_crm.api.antmed.health.ping` |

**Cấm**: `crm.api.*` (namespace cũ — app cài là `antmed_crm`), `assetcore.*`, app khác (ADR-M01-01).

## 2. DocType prefix (round sau)

| Trường hợp | Prefix | Ví dụ |
|---|---|---|
| DocType nghiệp vụ AntMed | **`AntMed `** | `AntMed Hospital Profile`, `AntMed Contract` |
| ERPNext/Frappe reuse | KHÔNG prefix | `Delivery Note`, `Customer`, `Item`, `Warehouse`, `Role` |

> ADR-M01-02: bản in-place dùng `AntMed ` (KHÔNG `AM `). Map domain doc: `AM Xxx` (skill) ↔ `AntMed Xxx` (in-place).

## 3. Role naming (RBAC)

| `name` Role (định danh, tiếng Anh) | Vai trò (VN) |
|---|---|
| `AntMed Sales Rep` | NV kinh doanh |
| `AntMed Warehouse Keeper` | Thủ kho |
| `AntMed Manager` | Quản lý |

Role rỗng quyền ở R1 (DocPerm/Role Profile gắn ở round có DocType).

## 4. API contract (Frappe-standard)

- `@frappe.whitelist(methods=[...])` **tường minh verb** (KHÔNG bare). GET đọc, POST ghi.
- Trả **RAW dict/list** — KHÔNG envelope `_ok`/`_err`, KHÔNG `MSG.*`.
- Lỗi nghiệp vụ = `frappe.throw(_("BR-XX: <thông điệp tiếng Việt>"))` (Frappe → exception JSON / HTTP 417).
- Hàm whitelist **type-annotate** (param + return) — `crm/hooks.py: require_type_annotated_api_methods = True`.
- Optional param: default `str = ""` (KHÔNG `None`); list/dict → param `*_json` + `json.loads(raw or "[]")`.
- **2 loại 403**: dispatcher-403 (guest gọi endpoint không `allow_guest`) vs in-handler permission-403 (`frappe.throw(..., frappe.PermissionError)`).
- **count == rows** (round có list endpoint): đếm DƯỚI `permission_query_conditions` (data-scope BR-13).

## 5. Frontend (Vue 3 + frappe-ui SPA)

| Loại | Prefix / quy ước | Ví dụ |
|---|---|---|
| Route path | `/antmed` → `/antmed/<feature>` | `/antmed` |
| Route name | PascalCase tiền tố `Antmed` | `AntmedHome` |
| Page component | `frontend/src/pages/Antmed<Feature>.vue` | `AntmedHome.vue` |
| Store (round sau) | `stores/antmed<Feature>.js` → `useAntmed<Feature>Store` | `antmedHospitals.js` |
| Resource call | `createResource({ url: 'antmed_crm.api.antmed.<module>.<fn>' })` | `antmed_crm.api.antmed.health.ping` |

**Cấm**: sửa/xoá route/page/store Frappe CRM gốc (Leads/Deals/Contacts/Tasks…). Chỉ THÊM prefix `Antmed`.

## 6. Fixtures & hooks

- Fixture file: **`crm/fixtures/<doctype_snake>.json`** — Frappe `import_fixtures` chỉ load từ `apps/crm/crm/fixtures/` (KHÔNG đọc `crm/fcrm/fixtures/` hay `crm/antmed/fixtures/`).
- `crm/hooks.py`: CHỈ **THÊM** key `fixtures = [...]`. KHÔNG đụng `permission_query_conditions` / `doc_events` / `after_migrate` / `before_tests` / `scheduler_events` gốc (no-regression).

## 7. Test

- BE: `crm/tests/test_<module>.py` (hoặc `crm/api/antmed/test_<module>.py`).
- Lệnh: `bench --site miyano run-tests --module crm.tests.test_antmed_bootstrap`.
- Mỗi feature: ≥1 test mới, 0 fail + chạy lại 4 test gốc no-regression (`test_org_hierarchy`, `test_crm_lead`, `test_crm_territory`, `test_crm_task`).
