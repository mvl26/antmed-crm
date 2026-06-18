# M14 — RBAC nền W0-2: Cho user role AntMed thuần boot vào SPA (DEC-B, allow-check ADDITIVE)

| Mục | Giá trị |
|---|---|
| Module folder | `crm/antmed/` (RBAC nền — thuộc trục M14 Security/RBAC, giao điểm M01 SPA boot) |
| Phase triển khai | W0 — RBAC nền (chạy trước mọi feature có route AntMed riêng) |
| Đề mục | W0-2: user role AntMed thuần (`NV kinh doanh`) boot được SPA `/antmed/*` qua allow-check **additive** — KHÔNG narrow `CRM_ALLOWED_ROLES` |
| Quyết định gốc | **DEC-B** — tách route/guard AntMed riêng (KHÔNG sửa ngữ nghĩa CRM gốc) |
| Role chính | `NV kinh doanh`, `Thủ kho`, `Quản lý` (3 Role VI — xem `./m14_rbac_w0_role_naming.md`) |
| Site dev/test | `miyano` |
| Trạng thái docs | Stable (spec chốt cho W0-2 — đủ để BE/FE code) |
| Cập nhật | 2026-06-17 |

> 🔗 **Tiền đề**: W0-1 (`./m14_rbac_w0_role_naming.md`) đã chốt **tên 3 Role VI** (`NV kinh doanh` / `Thủ kho` / `Quản lý`) + migrate xong trên `miyano`. W0-2 KHÔNG đụng tên Role, chỉ thêm **đường boot** cho các Role đó vào SPA.

> 🟡 **Open thread nguồn (STATE)**: "DEC-B — NEXT SLICE W0: Tách route/shell AntMed riêng (boot block). AntMed pages mount TRONG Frappe CRM SPA shell → user CHỈ có Role `NV kinh doanh` bị `CRM_ALLOWED_ROLES` chặn → redirect `/crm/not-permitted`." W0-2 đóng đúng open thread này.

---

## Overview

### Vấn đề (root cause — verify từ code thật)

AntMed SPA pages (`/antmed`, `/antmed/hospitals`, …) mount **bên trong Frappe CRM SPA shell** (route `/crm`, build base `/crm`). User AntMed thuần chỉ có Role `NV kinh doanh` (không có `Sales User`/`Sales Manager`/`System Manager`) bị chặn ở **3 tầng**:

| Tầng | File:line (verify) | Hành vi hiện tại với user AntMed thuần |
|---|---|---|
| **Gate-1 HTML serve** | `crm/www/crm.py:17` → `crm/api/__init__.py:54` `check_app_permission()` | `check_app_permission()` trả `False` (line 71–73 chỉ chấp nhận `System Manager`/`Sales User`/`Sales Manager`) → `get_context()` `frappe.throw(PermissionError)` → **KHÔNG nhận được SPA HTML** (Frappe trả trang lỗi, không phải app). |
| **Gate-2 session API** | `crm/api/session.py:10–11` `get_session_role_flags()` | `roles.intersection(CRM_ALLOWED_ROLES)` rỗng → `frappe.throw("not permitted", PermissionError)`. Mọi endpoint gọi helper này (`get_users`, `get_organizations`) ném 403. |
| **Gate-3 router guard** | `frontend/src/router.js:166` `!isCrmUser()` | `isCrmUser()` (`stores/users.js:80`) tra `users.data.crmUsers` — danh sách build ở `get_users()` (`session.py:70`) **chỉ append** user có `user.role ∈ {System Manager, Sales Manager, Sales User}`. User AntMed thuần có `user.role = ""` (không khớp nhánh nào, `session.py:53–62`) → KHÔNG nằm trong `crmUsers` → `isCrmUser()` falsy → guard redirect `Not Permitted` cho **MỌI** route, kể cả `/antmed/*`. |

→ NV KD AntMed thuần **KHÔNG boot được app**.

### Giải pháp (DEC-B — allow-check ADDITIVE, KHÔNG narrow CRM gốc)

Mở **OR-thêm nhánh AntMed** ở cả 3 tầng, single-source danh sách Role AntMed ở BE, FE đọc qua boot flag:

1. **BE single source**: hằng `ANTMED_ALLOWED_ROLES = ["NV kinh doanh", "Thủ kho", "Quản lý"]` + helper `is_antmed_user()` / allow-check additive `is_crm_or_antmed_user()` — **1 nơi định nghĩa** (`crm/api/antmed/rbac.py`).
2. **Gate-1**: `check_app_permission()` OR-thêm: pass nếu có 1 trong CRM roles **HOẶC** 1 trong AntMed roles.
3. **Gate-2**: `get_session_role_flags()` OR-thêm nhánh AntMed (không throw nếu là AntMed user); `CRM_ALLOWED_ROLES` **literal giữ nguyên** = `[System Manager, Sales Manager, Sales User]`.
4. **Gate-3**: router guard tách nhánh — route `/antmed/*` cho phép boot nếu user là **CRM HOẶC AntMed**; route CRM gốc (`/leads`…) **GIỮ NGUYÊN** logic `isCrmUser()` (AntMed-thuần vẫn bị chặn route CRM gốc → no-regression).
5. **Boot flag**: `get_boot()` (`crm/www/crm.py`) thêm `antmed_roles` + cờ `is_antmed_user` → FE đọc `window.antmed_roles` / helper store, **KHÔNG hardcode** danh sách Role lần 2 ở FE.

**Business value (W0-2)**: NV kinh doanh AntMed thuần đăng nhập là vào thẳng SPA AntMed mà KHÔNG cần cấp thêm Role CRM gốc (`Sales User`) — đúng nguyên tắc least-privilege; đồng thời CRM-pure user (Sales User) KHÔNG bị ảnh hưởng (no-regression toàn diện).

---

## Scope — Boundaries (Always / Never)

### Always (W0-2 LUÔN làm)
- **Always** định nghĩa danh sách Role AntMed **1 nơi duy nhất** ở BE: hằng `ANTMED_ALLOWED_ROLES` trong `crm/api/antmed/rbac.py`. Mọi tầng (Gate-1/2/3, boot) **import từ đây**, KHÔNG lặp literal.
- **Always** allow-check là **ADDITIVE / OR**: trả `True` nếu user có MỘT trong `{System Manager, Sales Manager, Sales User}` **HOẶC** MỘT trong `{NV kinh doanh, Thủ kho, Quản lý}`.
- **Always** giữ literal `CRM_ALLOWED_ROLES = ["System Manager", "Sales Manager", "Sales User"]` **NGUYÊN VẸN** (không thêm/bớt/đổi value) trong `crm/api/session.py:4`.
- **Always** chỉ **EXTEND** (thêm nhánh OR) ở 3 core file `crm/api/__init__.py`, `crm/api/session.py`, `frontend/src/router.js` — KHÔNG đổi ngữ nghĩa nhánh CRM gốc.
- **Always** để route **CRM gốc** (`/leads`, `/deals`, `/contacts`…) GIỮ guard `isCrmUser()` — AntMed-thuần vẫn redirect `Not Permitted` khi vào route CRM gốc (no-regression CRM gốc).
- **Always** cho route **`/antmed/*`** pass với cả CRM user **và** AntMed user (CRM user vào `/antmed/*` cũng pass).
- **Always** expose danh sách Role AntMed + cờ qua **boot** (`get_boot()` trong `crm/www/crm.py`) → FE đọc `window.antmed_roles` (KHÔNG hardcode lần 2).
- **Always** ghi **ADR** nêu *vì sao buộc đụng core* (gate ở HTML/session layer — không có hook extension-point khác) + cam kết CHỈ extend.

### Never (W0-2 TUYỆT ĐỐI KHÔNG)
- **Never** thu hẹp / đổi giá trị `CRM_ALLOWED_ROLES` (acceptance Gate-2 yêu cầu literal giữ nguyên). KHÔNG thêm Role AntMed VÀO `CRM_ALLOWED_ROLES` (đó là narrow/đổi semantics CRM gốc, sai DEC-B).
- **Never** đổi ngữ nghĩa nhánh CRM gốc ở `check_app_permission()` / `get_session_role_flags()` / `isCrmUser()` (chỉ OR-thêm, không sửa AND/return cũ).
- **Never** cho phép user AntMed-thuần vào route **CRM gốc** (`/leads`…) — phải vẫn redirect `Not Permitted` (no-regression CRM gốc, Gate-3 yêu cầu rõ).
- **Never** hardcode danh sách Role AntMed lần 2 ở FE (router.js / store) — phải đọc từ boot (`window.antmed_roles`). Nếu boot chưa có (fallback) → ghi rõ fallback, KHÔNG copy literal rời.
- **Never** sửa `crm/api/session.py::get_users()` để nhét AntMed user vào `crmUsers` array (sẽ rò AntMed user vào mọi dropdown CRM gốc: AssignTo, Assignment, Dashboard… — xem §Risk). `crmUsers` GIỮ nguyên ngữ nghĩa "CRM-pure users".
- **Never** git commit / push / merge / reset DB / drop site (HARD-STOP — thuộc user).
- **Never** đổi build base SPA (`createWebHistory('/crm')`) hay tách app FE riêng ở W0-2 (DEC-B = tách **route/guard**, KHÔNG tách app — pages AntMed vẫn mount trong shell `/crm`, chỉ mở guard cho prefix `/antmed`).

---

## DocTypes

**KHÔNG có DocType mới ở W0-2.** Chỉ thao tác trên Role lõi Frappe `Role` (đọc roles, không tạo/sửa) + code RBAC. (3 Role VI đã tạo ở W0-1.)

---

## BE — Single source RBAC AntMed

### File mới: `crm/api/antmed/rbac.py`

| Thành phần | Chữ ký | Trả về (RAW) | Vai trò |
|---|---|---|---|
| Hằng | `ANTMED_ALLOWED_ROLES: list[str]` | `["NV kinh doanh", "Thủ kho", "Quản lý"]` | **Single source** — mọi tầng import |
| Helper | `is_antmed_user(user: str \| None = None) -> bool` | `True` nếu `frappe.get_roles(user)` giao `ANTMED_ALLOWED_ROLES` khác rỗng | check role AntMed |
| Helper | `is_crm_or_antmed_user(user: str \| None = None) -> bool` | `True` nếu là CRM user (giao `CRM_ALLOWED_ROLES`) **HOẶC** AntMed user | allow-check additive dùng chung |

> **Vì sao đặt ở `crm/api/antmed/rbac.py`** (không nhét vào `session.py`): `session.py` là **core CRM gốc** — đặt hằng AntMed ở đó làm "ô nhiễm" file gốc + khó grep. `rbac.py` trong package `crm/api/antmed/` cô lập code AntMed dưới prefix, dễ tách app sau (theo ADR-M01-01). `session.py` chỉ **import** `ANTMED_ALLOWED_ROLES` từ package AntMed (one-line, không lặp literal).

**Logic chốt (spec — BE hiện thực, KHÔNG bịa thêm):**

```python
# crm/api/antmed/rbac.py
import frappe

# SINGLE SOURCE — 3 Role AntMed VI (đồng bộ tên với W0-1 / role.json).
ANTMED_ALLOWED_ROLES = ["NV kinh doanh", "Thủ kho", "Quản lý"]


def is_antmed_user(user: str | None = None) -> bool:
    """True nếu user có ≥1 Role AntMed (NV kinh doanh / Thủ kho / Quản lý)."""
    roles = set(frappe.get_roles(user))
    return bool(roles.intersection(ANTMED_ALLOWED_ROLES))


def is_crm_or_antmed_user(user: str | None = None) -> bool:
    """Allow-check ADDITIVE: CRM-pure user HOẶC AntMed user."""
    from crm.api.session import CRM_ALLOWED_ROLES  # lazy-import: tránh circular
    roles = set(frappe.get_roles(user))
    return bool(
        roles.intersection(CRM_ALLOWED_ROLES)
        or roles.intersection(ANTMED_ALLOWED_ROLES)
    )
```

> ⚠️ **Lazy-import bắt buộc**: `is_crm_or_antmed_user` import `CRM_ALLOWED_ROLES` từ `crm.api.session` **trong thân hàm** (không top-level) để tránh circular import khi `session.py` cũng import từ package AntMed. (Pattern B cross-module — xem skill `antmed-doc`.)

---

## Core files — điểm wiring (CHỈ extend, OR-thêm nhánh)

### Gate-1 — `crm/api/__init__.py::check_app_permission()`

**Hiện tại** (line 71–75): trả `True` chỉ khi có role CRM. **Đổi** (OR-thêm nhánh AntMed, giữ nguyên check module + nhánh CRM):

```python
# crm/api/__init__.py — check_app_permission()
# ... giữ nguyên đoạn allowed_modules + 'FCRM' check (line 58–69) ...
roles = frappe.get_roles()
if any(role in ["System Manager", "Sales User", "Sales Manager"] for role in roles):
    return True
# [W0-2 ADDITIVE] OR-thêm nhánh AntMed — KHÔNG sửa nhánh CRM trên
from antmed_crm.api.antmed.rbac import is_antmed_user
if is_antmed_user():
    return True
return False
```

> ⚠️ *(Cần khảo sát khi BE wiring)*: dòng `if "FCRM" not in allowed_modules: return False` (line 68–69) — module `FCRM` được cấp qua Role Profile/Module Profile. **Phải xác nhận** 3 Role AntMed VI có map tới module cho phép `FCRM` (hoặc user AntMed có module `FCRM` trong `get_modules_from_all_apps_for_user()`) **trước** khi đến nhánh role-check; nếu không, Gate-1 vẫn `False` ở line 69 trước khi tới nhánh AntMed. Nếu user AntMed thuần KHÔNG có `FCRM` → cần (a) gán module `FCRM` cho Role AntMed, HOẶC (b) nới điều kiện module thành `FCRM` **HOẶC** `AntMed`. **BE đo trên site `miyano`**: `frappe.config.get_modules_from_all_apps_for_user(<user AntMed>)` — nếu thiếu `FCRM`/`AntMed` thì xử theo (b) (OR-thêm `"AntMed"` vào điều kiện module, vẫn additive). Đánh dấu *(Cần khảo sát baseline module-of-user)*.

### Gate-2 — `crm/api/session.py::get_session_role_flags()`

**Hiện tại** (line 10–11): throw nếu không giao `CRM_ALLOWED_ROLES`. **Đổi** (OR-thêm AntMed vào điều kiện không-throw; `CRM_ALLOWED_ROLES` literal GIỮ NGUYÊN):

```python
# crm/api/session.py
from antmed_crm.api.antmed.rbac import ANTMED_ALLOWED_ROLES  # top-level OK: rbac.py không import ngược ở top-level

CRM_ALLOWED_ROLES = ["System Manager", "Sales Manager", "Sales User"]  # GIỮ NGUYÊN — không đổi

def get_session_role_flags():
    roles = set(frappe.get_roles())
    # [W0-2 ADDITIVE] không throw nếu user là CRM HOẶC AntMed
    allowed = set(CRM_ALLOWED_ROLES) | set(ANTMED_ALLOWED_ROLES)
    if not roles.intersection(allowed):
        frappe.throw(_("You are not permitted to access CRM resources."), frappe.PermissionError)
    return {
        "is_system_manager": "System Manager" in roles,
        "is_sales_manager": "Sales Manager" in roles and "System Manager" not in roles,
        "is_sales_user": "Sales User" in roles
            and "Sales Manager" not in roles
            and "System Manager" not in roles,
        # (tuỳ chọn) "is_antmed_user": bool(roles.intersection(ANTMED_ALLOWED_ROLES)),
    }
```

> ✅ **Invariant Gate-2**: `CRM_ALLOWED_ROLES` literal **không bị thu hẹp/đổi** (vẫn `[System Manager, Sales Manager, Sales User]`) — `allowed` là **biến cục bộ** union, KHÔNG mutate hằng module. `get_users()` / `get_organizations()` không phải sửa thêm (chúng gọi `get_session_role_flags()` đã nới). `crmUsers` array vẫn chỉ chứa CRM-pure users (KHÔNG nhét AntMed — xem Never).

> ⚠️ **Phân biệt 2 loại 403** (DONE-gate spec-contract):
> - **dispatcher-403** (guest / no session cookie): xảy ra TRƯỚC khi vào handler — `@frappe.whitelist()` (không `allow_guest`) tự chặn Guest. KHÔNG đổi ở W0-2.
> - **in-handler permission-403**: `get_session_role_flags()` `frappe.throw(PermissionError)` khi user có session nhưng **thiếu cả CRM lẫn AntMed role**. Sau W0-2, user AntMed thuần KHÔNG còn rơi vào nhánh này (đã nới allow-check). User KHÔNG-role-nào (cả CRM lẫn AntMed) VẪN bị throw (đúng).

### Gate-3 — `frontend/src/router.js` (guard `beforeEach`)

**Hiện tại** (line 166): `if (isLoggedIn && to.name !== 'Not Permitted' && !isCrmUser()) next({ name: 'Not Permitted' })` — chặn MỌI route khi không phải CRM user. **Đổi** (tách nhánh theo prefix route):

```js
// frontend/src/router.js — trong beforeEach, thay block line 166
const isAntmedRoute = to.path.startsWith('/antmed')
const allowAntmed = isAntmedUser()  // đọc window.antmed_roles (xem §Boot/FE helper)

if (isLoggedIn && to.name !== 'Not Permitted') {
  if (isAntmedRoute) {
    // route AntMed: cho phép CRM user HOẶC AntMed user
    if (!isCrmUser() && !allowAntmed) {
      return next({ name: 'Not Permitted' })
    }
  } else {
    // route CRM gốc: GIỮ NGUYÊN — chỉ CRM user (AntMed-thuần bị chặn → no-regression)
    if (!isCrmUser()) {
      return next({ name: 'Not Permitted' })
    }
  }
}
// ... phần còn lại của guard (Home/default-view/login redirect…) giữ nguyên ...
```

> ✅ **Gate-3 invariant**:
> - `/antmed/*` + user `NV kinh doanh` → pass (không redirect). ✅
> - `/antmed/*` + CRM user (Sales User) → pass (nhánh `isCrmUser()` truthy). ✅
> - `/leads` (CRM gốc) + user AntMed-thuần → `isCrmUser()` falsy, KHÔNG phải route AntMed → redirect `Not Permitted`. ✅ (no-regression CRM gốc)
> - `/leads` + CRM user → `isCrmUser()` truthy → pass. ✅ (no-regression)
> - ⚠️ **Lưu ý ordering**: nhánh `Home` (line 168, redirect default-view) hiện chạy SAU check `isCrmUser()`. Với user AntMed thuần, route `Home` (`/`) sẽ KHÔNG có `defaultView` CRM → cần quyết landing: **W0-2 chốt** — user AntMed thuần vào `/` (Home) thì redirect tới `/antmed` (landing AntMed). BE/FE wiring: trong nhánh `to.name === 'Home'`, nếu `!isCrmUser() && allowAntmed` → `next({ name: 'AntmedHome' })` TRƯỚC khi vào logic `getDefaultView()` CRM (logic CRM gốc giữ cho CRM user). *(Cần khảo sát: CRM user có cũng muốn landing AntMed không — mặc định KHÔNG, CRM user giữ landing CRM.)*

### Boot — `crm/www/crm.py::get_boot()` (+ FE helper)

**Đổi** `get_boot()` thêm 2 key (single source → FE):

```python
# crm/www/crm.py — trong get_boot() dict, THÊM:
from antmed_crm.api.antmed.rbac import ANTMED_ALLOWED_ROLES, is_antmed_user
# ...
"antmed_roles": ANTMED_ALLOWED_ROLES,
"is_antmed_user": is_antmed_user(),
```

→ `crm.html:204` inject `window["antmed_roles"]` + `window["is_antmed_user"]`. FE thêm helper (đề xuất đặt cạnh `usersStore` hoặc util mới `frontend/src/utils/antmed.js`):

```js
// FE — đọc từ boot, KHÔNG hardcode literal Role lần 2
export function isAntmedUser() {
  return Boolean(window.is_antmed_user)
}
export const antmedRoles = window.antmed_roles || []
```

> **Vì sao bootflag `is_antmed_user` (đã tính sẵn ở BE) thay vì FE tự so role**: FE SPA gốc KHÔNG có sẵn danh sách role của user trong store (chỉ có `crmUsers`). Tính sẵn ở BE = single-source thật (FE không cần biết tên 3 Role, chỉ đọc cờ boolean) → đổi tên Role sau (vd thêm Role AntMed thứ 4) KHÔNG phải sửa FE. `window.antmed_roles` expose thêm để FE cần liệt kê (vd settings) thì có, vẫn từ 1 nguồn.

---

## API

**W0-2 KHÔNG thêm endpoint whitelist nghiệp vụ mới.** `rbac.py` chứa helper **nội bộ** (không `@frappe.whitelist` — chỉ gọi server-side bởi gate/boot). Endpoint hiện hữu giữ shape RAW dict/list, không envelope (`antmed_crm.api.antmed.health.ping`, `antmed_crm.api.antmed.customer.*`). Không đụng quy ước Frappe-standard API (RAW, in-handler `frappe.throw` cho lỗi nghiệp vụ).

> **Invariant count == rows**: W0-2 KHÔNG đổi `permission_query_conditions` (chưa wiring cho Hospital/Doctor ở R2 — RBAC qua DocPerm). Số rows list endpoint không đổi hành vi. BR-13 data-scope vẫn `[ROADMAP]` M14.

---

## UI / UX flow (theo vai trò)

| Vai trò | Đăng nhập → landing | Route được phép | Route bị chặn |
|---|---|---|---|
| `NV kinh doanh` (AntMed thuần) | `/` → redirect `/antmed` (AntmedHome) | `/antmed/*` (Home AntMed, Hospitals, Detail…) | `/leads`, `/deals`, `/contacts`… (CRM gốc) → `Not Permitted` |
| `Sales User` (CRM thuần) | `/` → default CRM view (Leads…) | `/leads…` (CRM gốc) **VÀ** `/antmed/*` | (không có) |
| `System Manager` | như CRM | tất cả | (không có) |
| User KHÔNG role nào (cả CRM lẫn AntMed) | bị `Not Permitted` (Gate-2 throw + Gate-3 redirect) | — | tất cả |

**Flow boot user `NV kinh doanh` (sau W0-2):**
1. Login → request `/crm` → `crm.www.crm.get_context()` → `check_app_permission()` **True** (nhánh AntMed) → nhận SPA HTML + boot (`window.is_antmed_user = true`, `window.antmed_roles`).
2. SPA mount → `get_users()` (qua `get_session_role_flags()`) **KHÔNG throw** (nhánh AntMed) → store load.
3. Router guard: vào `/` → redirect `/antmed`; vào `/antmed/*` → pass; lỡ gõ `/leads` → `Not Permitted`.
4. Render `/antmed` (AntmedHome) → các page Customer 360° (R2) hoạt động bình thường.

---

## Business Rules

W0-2 là **RBAC nền (boot gate)** — KHÔNG thực thi BR nghiệp vụ mới. Liên hệ:

| BR | Liên hệ W0-2 |
|---|---|
| BR-13 data-scope (NV chỉ thấy BV được giao) | `[ROADMAP]` M14 — `permission_query_conditions` sẽ dùng role `NV kinh doanh` (đã có tên VI từ W0-1, allow-boot từ W0-2). W0-2 mở **cửa boot**, BR-13 sau mới scope data. Hai việc độc lập. |
| BR-12 (2FA) / BR-11 (approved_by) | `[ROADMAP]` M14 — không đụng ở W0-2. |
| BR-10 (audit hash-chain) | `[ROADMAP]` M14 — không đụng. |

> Quy ước message BR round sau: in-handler `frappe.throw(_("BR-XX: <thông điệp tiếng Việt>"))`. W0-2 gate dùng message generic Frappe gốc (`"You are not permitted…"`) — KHÔNG phải lỗi nghiệp vụ BR.

---

## Risk / Self-Correction notes

- **Risk-1 (rò AntMed user vào dropdown CRM)**: KHÔNG nhét AntMed user vào `crmUsers` (`get_users()`). `crmUsers` được ~15 component CRM gốc dùng làm danh sách user gán việc (AssignTo, AssignmentModal, Dashboard, Hierarchy, CommentBox…). Nếu nhét AntMed user vào → họ xuất hiện sai trong assignment CRM gốc → **regression**. → W0-2 chỉ nới **gate boot**, KHÔNG đổi `crmUsers` semantics. Acceptance Gate-3 "CRM gốc no-regression" bao trùm điểm này.
- **Risk-2 (FCRM module gate)**: Gate-1 `check_app_permission()` còn 1 điều kiện module `FCRM` (line 68) TRƯỚC role-check. Phải verify user AntMed thuần có module cho phép (xem *(Cần khảo sát)* ở §Gate-1). Đây là điểm có thể làm Gate-1 vẫn fail dù đã thêm nhánh role — **BE đo trước, không giả định**.
- **Risk-3 (FE hardcode)**: cấm copy literal 3 Role vào FE. Cờ boot `is_antmed_user` là nguồn. Nếu vì lý do nào đó cần fallback (boot thiếu) → ghi rõ fallback `window.is_antmed_user ?? false` (an toàn = chặn), KHÔNG copy tên Role.

---

## Test harness (acceptance W0-2)

### BE — module test mới `crm/tests/test_antmed_rbac_boot.py`

> Acceptance gốc: `bench --site miyano run-tests crm.tests.test_antmed_rbac_boot` → `Ran N OK 0 fail`.

| Test ID | Mục tiêu | Assert |
|---|---|---|
| `test_antmed_role_list_single_source` | `ANTMED_ALLOWED_ROLES` đúng 3 tên VI | `== ["NV kinh doanh", "Thủ kho", "Quản lý"]` |
| `test_crm_allowed_roles_unchanged` | Gate-2 invariant: literal CRM giữ nguyên | `CRM_ALLOWED_ROLES == ["System Manager", "Sales Manager", "Sales User"]` |
| `test_gate1_antmed_user_gets_context` | Gate-1: user chỉ `NV kinh doanh` → `check_app_permission()` True (KHÔNG PermissionError) | `set_user(antmed_user); assertTrue(check_app_permission())` |
| `test_gate1_crm_user_still_true` | Gate-1 no-regression | user `Sales User` → `check_app_permission()` True |
| `test_gate2_antmed_user_no_throw` | Gate-2: user `NV kinh doanh` → `get_session_role_flags()` KHÔNG throw | gọi không raise; trả dict flags |
| `test_gate2_norole_user_still_throws` | Gate-2: user không CRM-không-AntMed → VẪN throw | `assertRaises(frappe.PermissionError)` |
| `test_is_antmed_user_helper` | helper additive đúng | `is_antmed_user(antmed_u)` True; `is_antmed_user(crm_u)` False; `is_crm_or_antmed_user` True cả hai |
| `test_boot_exposes_antmed_flag` | boot có key | `get_boot()` chứa `antmed_roles` + `is_antmed_user` |

> **Test fixtures**: tạo user tạm gán đúng Role (vd `_antmed_boot@example.com` gán `NV kinh doanh`; `_crm_boot@example.com` gán `Sales User`; `_norole_boot@example.com` không role nghiệp vụ). Dùng `frappe.set_user(...)` rồi restore `Administrator` trong `tearDown`. (Đếm `N` = số test, acceptance chỉ cần `OK 0 fail`.)

### FE — `frontend/src/router.js` guard + vitest

- Thêm test guard mới (vitest) cover Gate-3: mock `window.is_antmed_user` + `isCrmUser`:
  - AntMed user + `/antmed/hospitals` → KHÔNG redirect.
  - AntMed user + `/leads` → redirect `Not Permitted`.
  - CRM user + `/antmed/hospitals` → KHÔNG redirect.
  - CRM user + `/leads` → KHÔNG redirect (no-regression).
- Acceptance: `yarn vitest run` **≥ baseline (138+ gồm test guard mới)** xanh; `yarn build` xanh.

> ⚠️ Baseline hiện ghi nhận trong STATE = **136/136** (sau R2). Acceptance đề mục ghi "138+ gồm test guard mới" → thêm ≥2 test guard mới nâng baseline lên ≥138. *(Cần khảo sát baseline chính xác khi FE chạy — nếu R2 đã 136, +2 guard = 138; nếu lệch, lấy số thật làm baseline, miễn ≥ trước + có test guard mới.)*

### No-regression (BẮT BUỘC xanh)
- BE: `test_antmed_bootstrap` + `test_antmed_customer` còn xanh.
- BE: bootstrap CRM gốc (`test_org_hierarchy`, `test_crm_lead`, `test_crm_task`) còn xanh.
- FE: `yarn vitest run` ≥ baseline; `yarn build` xanh.

### Lệnh chạy THẬT (dev — KHÔNG commit)
```
bench --site miyano migrate                                   # nếu boot/role đụng — re-sync
bench --site miyano run-tests --module crm.tests.test_antmed_rbac_boot
bench --site miyano run-tests --module crm.tests.test_antmed_bootstrap
bench --site miyano run-tests --module crm.tests.test_antmed_customer
cd frontend && yarn vitest run && yarn build
```

---

## Build sequence (cho BE/FE — KHÔNG commit)

1. **BE**: tạo `crm/api/antmed/rbac.py` (`ANTMED_ALLOWED_ROLES` + `is_antmed_user` + `is_crm_or_antmed_user`, lazy-import `CRM_ALLOWED_ROLES`).
2. **BE**: `crm/api/__init__.py::check_app_permission()` — OR-thêm nhánh `is_antmed_user()`; verify điều kiện module `FCRM` (Risk-2) trên `miyano` trước, xử theo (a)/(b) nếu thiếu.
3. **BE**: `crm/api/session.py` — top-level import `ANTMED_ALLOWED_ROLES`; nới `get_session_role_flags()` bằng `allowed` cục bộ (union); GIỮ literal `CRM_ALLOWED_ROLES`.
4. **BE**: `crm/www/crm.py::get_boot()` — thêm `antmed_roles` + `is_antmed_user`.
5. **BE**: viết `crm/tests/test_antmed_rbac_boot.py` (8 test trên).
6. **FE**: helper `isAntmedUser()` đọc `window.is_antmed_user` (`utils/antmed.js` hoặc cạnh store).
7. **FE**: `frontend/src/router.js` — tách nhánh `isAntmedRoute` (allow CRM HOẶC AntMed) vs CRM gốc (giữ `isCrmUser()`); Home landing → `/antmed` cho AntMed-thuần.
8. **FE**: thêm vitest guard (4 case trên).
9. **BE**: `migrate` (nếu cần) + `run-tests` 3 module + no-regression CRM gốc.
10. **FE**: `yarn vitest run` (≥138) + `yarn build`.

---

## ADR

### ADR-M14W0-03: Allow-check ADDITIVE (OR-thêm nhánh AntMed) thay vì narrow `CRM_ALLOWED_ROLES`
- **Status**: Accepted
- **Date**: 2026-06-17
- **Context**: User AntMed thuần (`NV kinh doanh`) bị 3 gate CRM gốc chặn boot (Gate-1 `check_app_permission`, Gate-2 `get_session_role_flags`, Gate-3 router `isCrmUser`). Cần cho họ boot `/antmed/*` mà KHÔNG phá CRM gốc. DEC-B (user chốt) = tách route/guard AntMed riêng, KHÔNG sửa ngữ nghĩa CRM gốc.
- **Decision**: Thêm **nhánh OR** ở mỗi gate (pass nếu CRM role **HOẶC** AntMed role). `CRM_ALLOWED_ROLES` literal **giữ nguyên**. Danh sách Role AntMed single-source ở `crm/api/antmed/rbac.py::ANTMED_ALLOWED_ROLES`; FE đọc cờ boot `window.is_antmed_user`.
- **Alternatives**:
  - *Thêm 3 Role AntMed VÀO `CRM_ALLOWED_ROLES`* — đổi value hằng CRM gốc → AntMed user lọt vào ngữ cảnh CRM-pure (vd `crmUsers`, flags `is_sales_user`), narrow/đổi semantics CRM gốc. **Loại** (vi phạm acceptance "literal không đổi" + DEC-B).
  - *Tách app FE AntMed riêng (build base `/antmed`, www context riêng)* — đúng tinh thần "tách app" nhưng nặng (router/build/auth/boot riêng), không cần ở W0-2; pages AntMed đang mount tốt trong shell `/crm`. **Hoãn** (`[ROADMAP]` nếu sau cần cô lập hoàn toàn).
  - *Cấp thêm `Sales User` cho mọi NV KD AntMed* — vi phạm least-privilege + làm AntMed user thành CRM user (thấy /leads). **Loại**.
- **Consequences**:
  - (+) NV KD AntMed boot được SPA mà không cần Role CRM; CRM-pure user không đổi hành vi (no-regression).
  - (+) Single-source ở BE → đổi danh sách Role AntMed 1 nơi; FE đọc cờ, không drift.
  - (−) **Buộc đụng 3 core file** (`crm/api/__init__.py`, `crm/api/session.py`, `frontend/src/router.js`) — đây là tầng gate HTML/session/router, KHÔNG có extension-point/hook nào khác để chèn (Frappe www `get_context` gọi thẳng `check_app_permission`; session helper gọi thẳng; FE guard là 1 `beforeEach` tập trung). **Cam kết**: chỉ EXTEND (OR-thêm nhánh), KHÔNG sửa return/AND nhánh CRM gốc. Diff core tối thiểu, có ADR ghi lý do buộc đụng.
  - (−) Thêm 1 dependency core→AntMed: `session.py` import `antmed_crm.api.antmed.rbac`. Rủi ro circular xử bằng lazy-import trong `is_crm_or_antmed_user` (import `CRM_ALLOWED_ROLES` ngược). `session.py` import `ANTMED_ALLOWED_ROLES` top-level an toàn (rbac.py không import session ở top-level).

### ADR-M14W0-04: Bootflag `is_antmed_user` (tính sẵn ở BE) làm nguồn cho FE guard — KHÔNG hardcode role ở FE
- **Status**: Accepted
- **Date**: 2026-06-17
- **Context**: FE router guard cần biết user có phải AntMed user để mở route `/antmed/*`. FE SPA gốc KHÔNG có sẵn role list của user trong store (chỉ `crmUsers` data-derived). Acceptance yêu cầu "định nghĩa Role AntMed 1 nơi (BE); FE đọc qua boot/cờ, KHÔNG hardcode lần 2".
- **Decision**: BE tính sẵn `is_antmed_user()` + expose `antmed_roles` qua `get_boot()` → `crm.html` inject `window.is_antmed_user` / `window.antmed_roles`. FE helper `isAntmedUser()` chỉ đọc cờ boolean (không biết tên Role).
- **Alternatives**:
  - *FE fetch role qua endpoint riêng* — thêm round-trip + endpoint mới, thừa (boot đã có sẵn cơ chế inject `window[key]`). **Loại**.
  - *FE hardcode 3 tên Role để so* — drift khi đổi Role; vi phạm single-source. **Loại** (acceptance cấm).
- **Consequences**: (+) Single-source thật: thêm/đổi Role AntMed chỉ sửa `ANTMED_ALLOWED_ROLES`, FE không đụng. (+) FE không lộ business role names. (−) Cờ tính tại thời điểm boot (server-render) — nếu role user đổi giữa phiên phải reload (chấp nhận được: role-change hiếm, cần reload session toàn cục).

---

## Tham chiếu chéo
- Tiền đề tên Role VI (W0-1): `./m14_rbac_w0_role_naming.md`
- Bootstrap nền R1 (namespace `crm/antmed/`, `health.ping`): `./m01_bootstrap.md`
- Convention naming FE↔BE: `./m01_naming_conventions.md`
- Customer 360° R2 (pages `/antmed/*` được mở boot): `./m01_customer360.md`
- Source thật (gate points): `crm/www/crm.py`, `crm/api/__init__.py`, `crm/api/session.py`, `frontend/src/router.js`, `frontend/src/stores/users.js`, `frontend/src/stores/session.js`, `crm/www/crm.html`
- Source mới (W0-2): `crm/api/antmed/rbac.py`, `crm/tests/test_antmed_rbac_boot.py`, FE helper `frontend/src/utils/antmed.js` (hoặc cạnh store)
