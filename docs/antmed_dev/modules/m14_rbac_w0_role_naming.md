# M14 — RBAC nền W0: Đổi tên 3 Role AntMed sang tiếng Việt (DEC-A)

| Mục | Giá trị |
|---|---|
| Module folder | `antmed_crm/antmed/` (RBAC nền — áp tại M01 bootstrap, thuộc trục M14 Security/RBAC) |
| Phase triển khai | W0 — RBAC nền (chạy trước mọi feature có DocPerm) |
| Đề mục | W0-1: Đổi 3 Role sang nhãn tiếng Việt + migrate rename idempotent |
| Role chính (SAU đổi) | `NV kinh doanh`, `Thủ kho`, `Quản lý` |
| Site dev/test | `miyano` |
| Trạng thái docs | Stable (spec chốt cho W0-1) — **Self-Correction**: Supersede ADR-M01-02 |
| Cập nhật | 2026-06-17 |

> ⚠️ **Self-Correction**: Vòng R1 chốt tên Role tiếng Anh (`AntMed Sales Rep`/`AntMed Warehouse Keeper`/`AntMed Manager`) theo **ADR-M01-02**. DEC-A đảo quyết định đó: dùng **nhãn tiếng Việt** làm `name` Role. Doc này **Supersede ADR-M01-02** (xem §ADR-M14W0-01) và là **nguồn quyết định cuối** khi mâu thuẫn với spec EN cũ trong `m01_bootstrap.md` / `m01_naming_conventions.md` (2 file đó đã được light-touch cập nhật trỏ về đây).

---

## Overview

W0-1 là **RBAC nền** (foundation, không phải feature nghiệp vụ): đổi định danh 3 Role AntMed từ tiếng Anh sang **nhãn tiếng Việt** theo DEC-A, để khớp giao diện desk + ngữ cảnh người dùng AntMed (NV kinh doanh / Thủ kho / Quản lý đều là người Việt). Vì Role đã tồn tại thật trong DB site `miyano` (tạo ở R1 qua fixture), KHÔNG thể chỉ đổi fixture — phải **rename bản ghi Role hiện hữu** một cách **idempotent** rồi đồng bộ mọi nơi tham chiếu (fixture, hooks filter, DocPerm trong 2 doctype, test).

**Business value (W0-1)**: nhãn vai trò hiển thị đúng tiếng Việt trên Role list / User permission / Assignment; giảm nhầm lẫn cho người dùng cuối; chuẩn hoá định danh Role trước khi các module M0X sau gắn DocPerm/Role Profile (đổi sau sẽ phải sửa lan rộng).

> Phạm vi W0-1 **chỉ đổi tên** — KHÔNG đổi cấu trúc quyền (ma trận DocPerm giữ nguyên ý nghĩa, chỉ đổi chuỗi `role`).

---

## Scope — Boundaries (Always / Never)

### Always (W0-1 LUÔN làm)
- **Always** dùng đúng 3 `name` Role mới (tiếng Việt, có dấu): `NV kinh doanh`, `Thủ kho`, `Quản lý`.
- **Always** giữ `is_custom=1`, `desk_access=1`, `disabled=0` cho cả 3 Role (không đổi flag).
- **Always** đổi tên Role hiện hữu bằng **patch** `frappe.rename_doc('Role', old, new, force=True)` — chỉ gọi **khi `old` tồn tại VÀ `new` chưa tồn tại** (guard idempotent).
- **Always** cập nhật `antmed_crm/fixtures/role.json`: cả `name` **và** `role_name` = nhãn VI (để `bench migrate` re-import KHÔNG tái tạo Role EN).
- **Always** cập nhật filter `fixtures` trong `antmed_crm/hooks.py` sang 3 tên VI (không còn EN).
- **Always** cập nhật DocPerm `role` trong `antmed_crm/antmed/doctype/antmed_hospital/antmed_hospital.json` và `.../antmed_doctor/antmed_doctor.json` sang tên VI, **giữ nguyên ma trận quyền** (xem §DocPerm).
- **Always** cập nhật test (`test_antmed_bootstrap.py`, `test_antmed_customer.py`) sang tên VI.
- **Always** đặt patch ở **`[pre_model_sync]`** trong `antmed_crm/patches.txt` — chạy TRƯỚC khi doctype migrate, để khi Frappe sync DocType `AntMed Hospital`/`AntMed Doctor` (DocPerm đã trỏ role VI) thì Role VI ĐÃ tồn tại → KHÔNG lỗi "role không tồn tại".

### Never (W0-1 TUYỆT ĐỐI KHÔNG)
- **Never** để sót bất kỳ tên EN nào (`AntMed Sales Rep` / `AntMed Warehouse Keeper` / `AntMed Manager`) trong: `role.json`, `hooks.py`, 2 doctype JSON, test, doc. Grep phải = 0.
- **Never** dùng `frappe.delete_doc` rồi tạo lại Role (mất mọi User permission/role-assignment đang trỏ Role cũ). Phải `rename_doc` để Frappe tự cập nhật reference.
- **Never** gọi `rename_doc` vô điều kiện (chạy lần 2 sẽ lỗi vì `old` không còn) — phải có guard `exists(old) and not exists(new)`.
- **Never** đổi ma trận quyền (thêm/bớt read/write/create/delete) trong lần W0-1 này — chỉ đổi chuỗi `role`.
- **Never** git commit / push / merge / reset DB / drop site (HARD-STOP — thuộc user).
- **Never** đổi tên Role lõi Frappe (`System Manager` giữ nguyên trong DocPerm).

---

## Rename mapping (EN → VI)

| `name` cũ (EN, R1) | `name` mới (VI, DEC-A) | `role_name` mới | Vai trò |
|---|---|---|---|
| `AntMed Sales Rep` | **`NV kinh doanh`** | `NV kinh doanh` | Nhân viên kinh doanh |
| `AntMed Warehouse Keeper` | **`Thủ kho`** | `Thủ kho` | Thủ kho |
| `AntMed Manager` | **`Quản lý`** | `Quản lý` | Quản lý |

> Với DocType `Role`, `name` == `role_name` (Frappe đặt `name` theo `role_name`). Đổi tên = đổi cả hai. Fixture phải set cả `name` lẫn `role_name` = nhãn VI.

---

## DocTypes

**KHÔNG có DocType mới ở W0-1.** Chỉ thao tác trên:
- DocType lõi Frappe `Role` (rename 3 bản ghi).
- DocPerm con (child table `permissions`) trong 2 DocType nghiệp vụ đã có: `AntMed Hospital`, `AntMed Doctor` (đổi chuỗi `role`).

| Loại | Tên | Thao tác W0-1 |
|---|---|---|
| Frappe core (reuse) | `Role` | rename 3 bản ghi EN→VI (patch) + re-import fixture VI |
| AntMed (đã có) | `AntMed Hospital` | đổi DocPerm `role` EN→VI (sửa JSON) |
| AntMed (đã có) | `AntMed Doctor` | đổi DocPerm `role` EN→VI (sửa JSON) |

---

## Fixtures (RBAC — 3 Role nhãn VI)

`antmed_crm/fixtures/role.json` — cả `name` và `role_name` = nhãn VI:

```json
[
 { "doctype": "Role", "name": "NV kinh doanh", "role_name": "NV kinh doanh",
   "desk_access": 1, "disabled": 0, "is_custom": 1 },
 { "doctype": "Role", "name": "Thủ kho", "role_name": "Thủ kho",
   "desk_access": 1, "disabled": 0, "is_custom": 1 },
 { "doctype": "Role", "name": "Quản lý", "role_name": "Quản lý",
   "desk_access": 1, "disabled": 0, "is_custom": 1 }
]
```

Filter `fixtures` trong `antmed_crm/hooks.py` (chỉ đổi list tên — KHÔNG đụng key khác):

```python
fixtures = [
    {
        "doctype": "Role",
        "filters": {
            "name": ["in", ["NV kinh doanh", "Thủ kho", "Quản lý"]],
        },
    },
]
```

> **Vì sao patch + fixture VI cùng lúc**: fixture chỉ *upsert theo `name`*. Trên site `miyano` đang tồn tại Role `name='AntMed Sales Rep'`. Nếu CHỈ đổi fixture sang VI mà không rename, `bench migrate` sẽ **tạo MỚI** 3 Role VI và **để lại** 3 Role EN cũ → 6 Role, fail acceptance "không còn Role EN". Patch `rename_doc` (pre_model_sync) đổi tên bản ghi EN sẵn có thành VI TRƯỚC, sau đó fixture VI chỉ upsert trùng tên (no-op) → đúng 3 Role. Trên site mới (chưa có Role nào) thì patch no-op (guard `exists(old)` = False) và fixture tạo thẳng 3 Role VI. Cả hai đường đều hội tụ về **đúng 3 Role VI**.

---

## Patch — rename idempotent

| Thuộc tính | Giá trị |
|---|---|
| File | `antmed_crm/patches/v1_0/rename_antmed_roles_to_vi.py` |
| Khai trong | `antmed_crm/patches.txt`, mục **`[pre_model_sync]`** (cuối block) |
| Hàm | `def execute():` |
| Cơ chế | `frappe.rename_doc('Role', old, new, force=True)` cho từng cặp, có guard |
| Idempotent | Chạy lần 2: mọi `old` đã không còn → guard skip → KHÔNG lỗi, KHÔNG tạo trùng |

**Logic chốt (spec, BE hiện thực):**

```python
import frappe

RENAMES = [
    ("AntMed Sales Rep", "NV kinh doanh"),
    ("AntMed Warehouse Keeper", "Thủ kho"),
    ("AntMed Manager", "Quản lý"),
]

def execute():
    for old, new in RENAMES:
        if frappe.db.exists("Role", old) and not frappe.db.exists("Role", new):
            frappe.rename_doc("Role", old, new, force=True, ignore_permissions=True)
        # else: hoặc đã rename (idempotent), hoặc site mới chưa có old → fixture lo phần tạo
```

**Boundaries patch:**
- **Always** guard `exists(old) and not exists(new)` trước mỗi `rename_doc`.
- **Always** `force=True` (Role bị bảo vệ rename mặc định; force cho phép đổi tên Role custom).
- **Never** wrap trong try/except nuốt lỗi (lỗi thật phải nổi để biết migrate hỏng).
- **Edge-case** *(BE lưu ý)*: nếu cả `old` và `new` cùng tồn tại (vd ai đó tạo tay Role VI) → guard skip rename; fixture sẽ giữ Role VI, Role EN còn lại phải xử lý thủ công — đánh dấu *(Cần khảo sát nếu gặp)*; trên site `miyano` hiện chỉ có EN nên không rơi vào nhánh này.

---

## DocPerm — ma trận quyền (GIỮ NGUYÊN, chỉ đổi chuỗi `role`)

Áp cho **cả** `AntMed Hospital` và `AntMed Doctor` (2 doctype JSON). Ma trận giữ y như R2, chỉ đổi tên role:

| Role | read | write | create | delete | export/print/email/report/share |
|---|---|---|---|---|---|
| `System Manager` | ✅ | ✅ | ✅ | ✅ | ✅ (giữ nguyên, KHÔNG đổi) |
| `Quản lý` (was `AntMed Manager`) | ✅ | ✅ | ✅ | ✅ | ✅ |
| `NV kinh doanh` (was `AntMed Sales Rep`) | ✅ | ✅ | ✅ | ❌ **KHÔNG delete** | ✅ |

- `Quản lý`: **full** (read/write/create/delete) — như `AntMed Manager` cũ.
- `NV kinh doanh`: **read/write/create**, **KHÔNG delete** — như `AntMed Sales Rep` cũ (DocPerm hiện không có key `"delete"` cho role này → giữ nguyên, chỉ đổi `"role"` string).
- `Thủ kho` (`AntMed Warehouse Keeper`): **không gắn DocPerm** trên Hospital/Doctor (kho không quản lý khách hàng) — giữ nguyên trạng thái R2 (không có entry).

> **Wiring**: DocPerm nằm **trong child table `permissions` của chính 2 doctype JSON** (không phải fixture rời). `bench migrate` apply DocType → đồng bộ DocPerm. Vì patch rename chạy ở `pre_model_sync` (trước), khi `post_model_sync` apply DocType thì Role VI đã tồn tại → KHÔNG lỗi "role không tồn tại".

---

## API

**W0-1 KHÔNG thêm/sửa endpoint.** Endpoint hiện hữu (`antmed_crm.api.antmed.health.ping`, `antmed_crm.api.antmed.customer.*`) không nhúng chuỗi role → không chịu ảnh hưởng. Data-scope/`permission_query_conditions` chưa wiring cho 2 doctype này ở R2 (RBAC qua DocPerm). Invariant **count == rows** giữ nguyên hành vi R2 (không đổi).

---

## UI

**W0-1 KHÔNG đụng FE.** Đã verify: `grep -rn "get_roles\|AntMed Sales Rep\|AntMed Warehouse\|AntMed Manager" frontend/src/` = **0 hit** → không có FE role-string nào phải đổi. FE no-regression = `yarn vitest run` xanh (không thay đổi code FE).

> Nhãn Role hiển thị trên desk (Role list, User form, Assignment) sẽ tự đổi sang tiếng Việt sau rename — không cần sửa FE SPA.

---

## Business Rules

W0-1 là RBAC nền — **không thực thi BR nghiệp vụ mới**. Liên quan gián tiếp:

| BR | Liên hệ W0-1 |
|---|---|
| BR-13 data-scope (NV chỉ thấy BV được giao) | `[ROADMAP]` M14 — sẽ wiring `permission_query_conditions` dùng role `NV kinh doanh` (tên VI là input). W0-1 chốt tên để BR-13 sau trỏ đúng. |
| BR-11 / BR-12 (approved_by / 2FA) | `[ROADMAP]` M14 — Role profile gắn về sau dùng tên VI. |

> Quy ước message BR (round sau) không đổi: `frappe.throw(_("BR-XX: <thông điệp tiếng Việt>"))`.

---

## Integration

- `antmed_crm/hooks.py`: chỉ đổi list tên trong `fixtures` filter. KHÔNG đụng `permission_query_conditions` / `doc_events` / `after_migrate` / `before_tests` / `scheduler_events` gốc.
- `antmed_crm/patches.txt`: THÊM 1 dòng patch ở `[pre_model_sync]`. KHÔNG xoá/đổi thứ tự patch Frappe CRM gốc.
- No-regression bắt buộc: 4 test gốc Frappe CRM vẫn PASS (`test_org_hierarchy`, `test_crm_lead`, `test_crm_territory`, `test_crm_task`).

---

## Test harness (acceptance W0-1)

### BE
- `antmed_crm/tests/test_antmed_bootstrap.py` — đổi 3 hằng tên Role sang VI; assert:
  - `frappe.db.exists("Role", x)` truthy cho cả 3 tên VI (sau migrate).
  - ĐÚNG 3 Role AntMed VI (không thừa Role EN). `frappe.db.exists("Role", "<EN>")` trả `None`/falsy cho cả 3 tên EN.
  - (giữ) `ping()` shape + GET-only + module registered.
- `antmed_crm/tests/test_antmed_customer.py` — RBAC dương dùng role **`NV kinh doanh`** (thay `AntMed Sales Rep`): user gán `NV kinh doanh` đọc được BV + bác sỹ; `count == rows`.
- Lệnh chạy THẬT:
  ```
  bench --site miyano migrate          # re-import fixtures, apply DocType — KHÔNG tái tạo Role EN
  bench --site miyano migrate          # chạy lần 2: patch idempotent, KHÔNG lỗi, count Role VI == 3
  bench --site miyano run-tests --module antmed_crm.tests.test_antmed_bootstrap
  bench --site miyano run-tests --module antmed_crm.tests.test_antmed_customer
  ```

### Verify acceptance (count==rows / không rò rỉ)
- Sau migrate: `frappe.get_all("Role", filters={"name": ["in", ["NV kinh doanh","Thủ kho","Quản lý"]]})` → đúng **3 rows**.
- `frappe.db.exists("Role", "AntMed Sales Rep")` (và 2 tên EN khác) → `None`.
- `grep -rn "AntMed Sales Rep\|AntMed Warehouse Keeper\|AntMed Manager" antmed_crm/` → **0 hit** (trừ doc lịch sử/ADR mô tả mapping).

### FE
- `yarn vitest run` (trong `frontend/`) xanh — no FE change. Verified grep role-string = 0.

---

## Build sequence (cho BE — KHÔNG commit)

1. **BE**: sửa `antmed_crm/fixtures/role.json` → 3 Role VI (`name`+`role_name`+`is_custom=1`).
2. **BE**: sửa `antmed_crm/hooks.py` `fixtures` filter list → 3 tên VI.
3. **BE**: tạo `antmed_crm/patches/v1_0/rename_antmed_roles_to_vi.py` (logic §Patch) + thêm dòng vào `antmed_crm/patches.txt` `[pre_model_sync]`.
4. **BE**: sửa DocPerm `role` trong `antmed_hospital.json` + `antmed_doctor.json` (3 chỗ EN → VI mỗi file: `AntMed Manager`→`Quản lý`, `AntMed Sales Rep`→`NV kinh doanh`).
5. **BE**: sửa test `test_antmed_bootstrap.py` + `test_antmed_customer.py` sang tên VI.
6. **BE**: `bench --site miyano migrate` (2 lần) → verify đúng 3 Role VI, 0 Role EN.
7. **BE**: `run-tests` 2 module AntMed + 4 test gốc (no-regression).
8. **FE**: `yarn vitest run` (no change, chỉ xác nhận xanh).

---

## ADR

### ADR-M14W0-01: Đổi `name` Role AntMed sang nhãn tiếng Việt (DEC-A) — **Supersedes ADR-M01-02**
- **Status**: Accepted — **Supersedes ADR-M01-02** (R1 chọn tên EN)
- **Date**: 2026-06-17
- **Context**: ADR-M01-02 (R1) chốt `name` Role tiếng Anh không dấu (`AntMed Sales Rep`…) với lý do "ổn định cho FE `frappe.get_roles()`". Nhưng (a) FE đã verify **không** dùng bất kỳ role-string nào (`grep get_roles/role = 0` trong `frontend/src`), nên lý do "ổn định FE" không còn ràng buộc; (b) người dùng cuối AntMed (NV kinh doanh / Thủ kho / Quản lý) đều là người Việt, nhãn EN gây nhầm trên desk; (c) DEC-A (quyết định nghiệp vụ) yêu cầu nhãn tiếng Việt.
- **Decision**: `name` (== `role_name`) của 3 Role AntMed = nhãn tiếng Việt: `NV kinh doanh`, `Thủ kho`, `Quản lý`. Đổi tên bản ghi hiện hữu bằng patch `rename_doc` idempotent (pre_model_sync) + fixture VI + đồng bộ DocPerm/hooks/test.
- **Alternatives**:
  - *Giữ tên EN, chỉ đổi nhãn hiển thị* — Role không tách `name` khỏi `label`; muốn hiển thị VI phải đổi `name`. Loại.
  - *Đổi fixture sang VI mà KHÔNG patch rename* — sẽ để lại Role EN cũ (6 Role) trên site đã cài. Loại — fail acceptance.
  - *Delete Role EN + tạo Role VI* — mất mọi role-assignment/User permission trỏ Role cũ. Loại — phải `rename_doc` để Frappe tự cập nhật reference.
- **Consequences**:
  - (+) Nhãn vai trò tiếng Việt nhất quán toàn desk; định danh chốt trước khi M0X sau gắn Role Profile/DocPerm.
  - (+) Rename giữ nguyên mọi reference (User role, DocPerm) — không mất dữ liệu phân quyền.
  - (−) `name` Role có dấu tiếng Việt + khoảng trắng → khi truyền trong URL/query phải URL-encode (Frappe xử lý sẵn ở desk; nếu round sau cần check role ở FE thì so sánh chuỗi VI — ghi nhớ).
  - (−) Mọi tài liệu/test/JSON tham chiếu tên EN phải đồng bộ (đã liệt kê trong build sequence). Tên EN chỉ còn xuất hiện trong ADR mô tả mapping (lịch sử).
  - (−) App đã cài THẬT là app RIÊNG `antmed_crm` (fork Frappe CRM, theo tinh thần ADR-M01-01 — KHÔNG in-place trong app `crm`); nếu sau này đổi naming Role lần nữa cần đối chiếu lại → khi đó viết ADR mới.

### ADR-M14W0-02: Dùng patch `rename_doc` (idempotent) thay vì chỉ đổi fixture
- **Status**: Accepted
- **Date**: 2026-06-17
- **Context**: Role EN đã tồn tại thật trên site `miyano`. Fixture chỉ upsert theo `name` → đổi fixture không xoá Role cũ.
- **Decision**: Patch `[pre_model_sync]` gọi `frappe.rename_doc('Role', old, new, force=True)` với guard `exists(old) and not exists(new)` để idempotent; fixture VI đi kèm để site mới vẫn tạo được Role và để re-import không tái tạo EN.
- **Alternatives**: chỉ fixture (để lại Role EN — loại); patch `delete + insert` (mất reference — loại); `after_migrate` hook (chạy mỗi migrate, khó idempotent rõ ràng, lẫn với fixture — loại, patch là cơ chế chuẩn Frappe cho data-migration one-shot).
- **Consequences**: (+) chạy nhiều lần an toàn; (+) site cũ rename, site mới fixture-create, hội tụ cùng kết quả. (−) thêm 1 patch vào `patches.txt` (đặt `pre_model_sync` để Role tồn tại trước khi DocType apply DocPerm).

---

## Tham chiếu chéo
- **Kế tiếp W0-2** (cho 3 Role VI này **boot vào SPA** `/antmed/*` qua allow-check additive — DEC-B): `./m14_rbac_w0_antmed_boot.md`. W0-1 chốt *tên* Role; W0-2 chốt *đường boot* cho Role đó (độc lập, không Supersede W0-1).
- Spec bootstrap R1 (đã light-touch trỏ về doc này cho phần Role): `./m01_bootstrap.md`
- Convention naming (đã light-touch cập nhật bảng Role VI): `./m01_naming_conventions.md`
- Customer 360° R2 (DocPerm dùng tên VI): `./m01_customer360.md`
- Source thật: `antmed_crm/fixtures/role.json`, `antmed_crm/hooks.py`, `antmed_crm/patches.txt`, `antmed_crm/patches/v1_0/`, `antmed_crm/antmed/doctype/antmed_hospital/antmed_hospital.json`, `antmed_crm/antmed/doctype/antmed_doctor/antmed_doctor.json`, `antmed_crm/tests/test_antmed_bootstrap.py`, `antmed_crm/tests/test_antmed_customer.py`
