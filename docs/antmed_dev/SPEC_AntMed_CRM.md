# Spec: AntMed CRM (in-place trên Frappe CRM)

> **Trạng thái:** Phase 1 — Specify · *chờ human duyệt trước khi sang Plan/Tasks/Implement.*
> **Cập nhật:** 2026-06-17 · **Vị trí:** `docs/antmed_dev/` (tài liệu phát triển — tracked) · **Nguồn BA tham khảo:** `docs/antmed_crm/docs/` (read-only) · **Loại:** governing spec cấp dự án.
> Spec này **gộp & chốt** các quyết định rải rác (ADR-M01-*, lựa chọn của user 2026-06-17). Khi quyết định đổi → **sửa spec trước**, rồi mới code.

---

## 1. Objective (Mục tiêu)

Xây **CRM cho Công ty TNHH AntMed** — phân phối vật tư y tế (VTYT) và **cho mượn bộ dụng cụ phẫu thuật** cho bệnh viện — bằng cách **fork & mở rộng Frappe CRM (`apps/crm` v1.73.2) tại chỗ**, KHÔNG tạo app `antmed_crm` riêng.

- **Người dùng:** NV kinh doanh (mobile-first, làm tại phòng mổ), Thủ kho, NV chứng từ, Kế toán/AR, Trưởng phòng KD, CEO/BGĐ, và bác sỹ/điều dưỡng (portal). 7 persona — xem `AntMed_CRM_UI_Design.md`.
- **Phạm vi nghiệp vụ:** 14 module M01–M14 (`AntMed_CRM_Modules.md`). Khác biệt lõi vs CRM thường: **M04 giao phòng mổ (SLA giờ ca)**, **M05 vòng đời bộ dụng cụ mượn + tiệt khuẩn**, **M03 kho ký gửi BV + truy vết lot CO/CQ**, **M06 chứng từ pháp lý + HĐĐT**.
- **Thành công (project-level):** đội kinh doanh chạy trọn vòng *lead → thầu → hợp đồng → đơn → giao phòng mổ → công nợ* và *mượn bộ dụng cụ → tiệt khuẩn → trả*, trên một SPA Vue tiếng Việt, có audit + phân quyền; **không phá vỡ** Frappe CRM gốc (Leads/Deals/Contacts vẫn chạy).

### User stories (lát cắt hiện tại — M01 Customer 360°)
- *NV kinh doanh* mở danh sách **Bệnh viện**, tìm/lọc theo hạng, mở hồ sơ 360° (thông tin + danh sách bác sỹ).
- Từ hồ sơ BV, mở **profile Bác sỹ** (chuyên khoa, liên hệ, Zalo, ghi chú) và quay ngược lại BV.

---

## 2. Tech Stack

| Lớp | Công nghệ |
|---|---|
| Backend | Frappe Framework **v15**, Frappe CRM app `crm` **v1.73.2**, Python 3.10+ |
| DB / cache | MariaDB · Redis 7 |
| Frontend | **Vue 3 + frappe-ui** SPA (`createResource`/`createListResource`/`useDocument`), Vue Router, TailwindCSS, Vite |
| Bench/site | bench `/home/miyano/frappe-bench` · site **`miyano`** (KHÔNG `antmed.local`) |
| Phục vụ | **nginx :80** (serve `/assets` + proxy) → **gunicorn `--preload` :8000** (supervisor) → socketio :9000 |
| Tầng kho/vật tư | **AntMed-native** (D1=B, 2026-06-17): KHÔNG ERPNext — `AntMed Item`/`Lot`/`Warehouse`/`Stock Entry`/`Delivery`/`Instrument Set` |
| Workflow | **Frappe Workflow gốc** (D2): fixtures `workflow.json` + `docstatus` (KHÔNG `workflowcore`) |

---

## 3. Commands

```bash
# Backend test (TDD — chạy theo module)
bench --site miyano run-tests --module crm.tests.test_antmed_customer
bench --site miyano run-tests --module crm.tests.test_antmed_bootstrap

# Frontend test + build  (chạy trong apps/crm/frontend)
cd /home/miyano/frappe-bench/apps/crm/frontend && yarn vitest run
cd /home/miyano/frappe-bench/apps/crm/frontend && yarn build      # hoặc: bench build --app crm

# Migrate (sau khi thêm/sửa DocType / fixtures)
bench --site miyano migrate

# Reload web workers (gunicorn --preload nắm snapshot cũ — BẮT BUỘC sau khi đổi .py/hooks)
sudo supervisorctl restart frappe-bench-web: && bench --site miyano clear-cache
# ^ HARD-STOP USER: bench dùng chung (assetcore/normcore…) — Claude KHÔNG tự chạy.

# Pixel verify: http://miyano/crm/antmed  (cổng 80 qua nginx, cần đăng nhập) — KHÔNG :8000/:8080
```

---

## 4. Project Structure (in-place trong `apps/crm`)

```
crm/                                 # Python package (Frappe CRM gốc + AntMed)
  modules.txt                        # + dòng "AntMed"
  hooks.py                           # CHỈ THÊM key (fixtures, doc_events AntMed…); KHÔNG sửa key gốc
  fixtures/<doctype_snake>.json      # role.json … (Frappe chỉ đọc apps/crm/crm/fixtures/)
  antmed/                            # code module AntMed
    doctype/<snake>/<snake>.{json,py}   # AntMed Hospital, AntMed Doctor, …
    README.md                        # mirror naming convention
  api/antmed/<module>.py             # whitelist endpoint → crm.api.antmed.<module>.<fn>
  tests/test_antmed_<module>.py      # BE test (vị trí thực tế đang dùng)
frontend/src/
  pages/Antmed<Feature>.vue          # AntmedHospitalList / AntmedHospitalDetail / AntmedDoctorDetail …
  data/antmed.js                     # createResource factory cho crm.api.antmed.*
  stores/antmed<Feature>.js          # (round sau)
  router.js                          # CHỈ THÊM route /antmed/* ; KHÔNG đụng route gốc
frontend/tests/unit/antmed*.test.js  # FE vitest
docs/antmed_dev/                     # SSoT DEV DOCS (tracked): SPEC/PLAN/README + modules/m0X_*.md
docs/antmed_crm/docs/                # BA SOURCE (read-only, gitignored): AntMed_CRM_*.md + *.docx/*.html
```

---

## 5. Code Style & Conventions (hợp đồng — `m01_naming_conventions.md`)

**Backend (Frappe-standard, KHÔNG 3-tier):**
```python
# crm/api/antmed/customer.py
import frappe
from frappe import _

@frappe.whitelist(methods=["GET"])                       # verb tường minh, KHÔNG bare
def get_hospital(name: str) -> dict:                      # BẮT BUỘC type-annotate (hooks.py:28)
    if not frappe.has_permission("AntMed Hospital", "read", doc=name):
        frappe.throw(_("BR-13: Không có quyền xem bệnh viện này"), frappe.PermissionError)
    doc = frappe.get_doc("AntMed Hospital", name)         # 404 DoesNotExistError nếu ∄
    return {                                              # trả RAW dict — KHÔNG _ok/_err envelope
        "name": doc.name, "hospital_name": doc.hospital_name, "rank": doc.rank,
        "doctors": frappe.get_all("AntMed Doctor", filters={"hospital": name},
                                  fields=["name", "full_name", "specialty", "phone"]),
    }
```
- Endpoint path: `crm.api.antmed.<module>.<fn>`. **Cấm** `antmed_crm.api.*`, `assetcore.*`, app riêng.
- DocType prefix **`AntMed `** (KHÔNG `AM `). ERPNext reuse KHÔNG prefix.
- Lỗi nghiệp vụ = `frappe.throw(_("BR-XX: …tiếng Việt"))`. Phân biệt **dispatcher-403** (guest) vs **in-handler PermissionError-403**.
- List endpoint giữ bất biến **count == rows** (đếm qua `get_list(pluck=…, limit_page_length=0)` để R3 thêm `permission_query_conditions` không vỡ).

**Frontend (Vue 3 + frappe-ui):**
```js
// frontend/src/data/antmed.js — list trả dict {data,total_count} ⇒ dùng createResource, đọc r.data.data
export const listHospitals = createResource({ url: 'crm.api.antmed.customer.list_hospitals', auto: false })
```
- Route `/antmed/*`, route name `Antmed*`, component `frontend/src/pages/Antmed<Feature>.vue`.
- Nhãn 100% tiếng Việt qua `__()`; **giữ key kỹ thuật** (vd status `ok`) khi chỉ đổi nhãn hiển thị. Design token frappe-ui (KHÔNG hex thô). A11y: aria-live, role=alert, dl/dt/dd, focus-ring.
- **Cấm**: axios/tanstack-query/`frappe.client.*` trực tiếp; sửa/xoá route-page-store CRM gốc.

---

## 6. Testing Strategy

| Lớp | Framework | Vị trí | Mức kỳ vọng |
|---|---|---|---|
| BE unit/controller/BR | Frappe test runner | `crm/tests/test_antmed_<module>.py` | TDD failing-first; mỗi feature ≥1 test; **0 fail**; assert shape (Hyrum) |
| BE no-regression | như trên | test gốc CRM | bootstrap + Lead + Task + Organization vẫn OK |
| FE unit | vitest | `frontend/tests/unit/antmed*.test.js` | route/lazy/props, gọi đúng `crm.api.antmed.*`, gate cấm-import |
| FE build | vite | — | `yarn build` xanh, SFC compile sạch |
| Pixel / e2e | Playwright MCP | site `miyano` cổng 80 (login) | render thật: list/detail hiển thị, 0 console error, API 200 |

- **Definition of Done một lát cắt:** BE test xanh + FE vitest xanh + build xanh + (sau USER reload) **pixel render verify** + no-regression. Chưa pixel-verify ⇒ chưa "xong", chỉ "contract verified".

---

## 7. Boundaries

**Always (luôn):**
- Spec/Core-Doc **trước** code (BA gate). Mỗi lát cắt một đề mục, TDD, sửa root cause.
- Verify @source trước khi tin; chạy test THẬT (`Ran N OK`) trước khi tuyên bố xong.
- Chỉ THÊM vào CRM gốc (route/hook/doctype mới prefix AntMed); giữ no-regression.

**Ask first (hỏi trước):**
- Reload/restart gunicorn (HARD-STOP USER — bench dùng chung), `bench migrate` trên site thật, đổi schema DocType đã có data, thêm dependency, sửa file gốc CRM (`crm/api/session.py`, router guard…), commit/push.

**Never (không bao giờ):**
- Tạo app `antmed_crm` riêng / dùng `antmed_crm.api.*` (đã chốt in-place).
- `git commit`/push/reset DB/drop site/deploy prod khi chưa có lệnh USER.
- Sửa/xoá doctype/route/test của Frappe CRM gốc; xoá test đang fail để "qua bài".
- Commit secrets; copy nguyên app scaffold `docs/antmed_crm/antmed_crm` (chỉ tham khảo).

---

## 8. Architecture Decisions (đã chốt)

| ID | Quyết định | Ghi chú |
|---|---|---|
| ADR-M01-01 | **In-place** trong app `crm`, KHÔNG app riêng | user 2026-06-17 |
| ADR-M01-02 | DocType/Role prefix **`AntMed `** (không `AM `) | map domain doc `AM Xxx` ↔ `AntMed Xxx` |
| ADR-M01-04 | DocType **mới** `AntMed Hospital`/`AntMed Doctor`, KHÔNG extend `CRM Organization`/`Contact` | thiếu field y tế |
| ADR-M01-05 | **Hoãn** data-scope BR-13 (R2 RBAC theo DocPerm) | invariant count==rows vẫn enforce |
| DEC-2026-06-17-A | **Role name → TIẾNG VIỆT**: `NV kinh doanh`/`Thủ kho`/`Quản lý` | ⚠️ ghi đè §3 convention doc (đang EN). Cân nhắc FE role-check theo name VI; *open*. |
| DEC-2026-06-17-B | **Tách route/app AntMed riêng** cho truy cập SPA (layout+guard riêng), KHÔNG sửa `CRM_ALLOWED_ROLES` | user 2026-06-17 — giải bài user AntMed thuần bị 403 boot |

---

## 9. Success Criteria (cụ thể, kiểm chứng được)

**Lát cắt M01 Customer 360° (đang làm):**
1. `bench --site miyano run-tests --module crm.tests.test_antmed_customer` → `Ran N OK`, 0 fail. ✅ (đã đạt: 11 OK)
2. `yarn vitest run` xanh (≥136) + `yarn build` xanh. ✅
3. Sau USER reload: `http://miyano/crm/antmed/hospitals` render list BV thật, search/lọc hạng đúng, click → detail 360° + danh sách bác sỹ, click bác sỹ → profile + link ngược BV; 0 console error; ping/API 200. ⏳ *chờ reload + pixel verify*
4. No-regression: route/test Frappe CRM gốc còn nguyên. ✅
5. Role name hiển thị **tiếng Việt** (DEC-A); user AntMed thuần boot được SPA (DEC-B). ⏳

**Project-level (đo theo roadmap):** mỗi module M0X đóng khi đạt DoD §6 + acceptance trong Core Doc module tương ứng.

---

## 10. Roadmap (phân pha — `AntMed_CRM_Modules.md`)

- **Phase 1 — Lõi vận hành:** M01 (✅ slice Customer 360°), M02 Hợp đồng/Quota, M03 Kho/Lot, M04 Giao phòng mổ, M06 Chứng từ/HĐĐT, M12 Mobile.
- **Phase 2 — Đặc thù AntMed:** M05 Bộ dụng cụ mượn + tiệt khuẩn, M07 CSKH bác sỹ, M11 Dashboard.
- **Phase 3 — Tăng trưởng & kiểm soát:** M08 Pipeline/thầu, M09 Đơn/AR, M10 KPI, M13 Integrations, M14 Security/Audit.

Cơ chế thực thi: **AntMed factory loop** (pm→ba→[be‖fe]→qa→user), mỗi vòng đóng 1 đề mục theo spec này.

---

## 11. Open Questions (cần human)

1. **Scope spec:** xác nhận spec này ở mức *cấp dự án + M1 chi tiết* là đúng ý? (hay muốn spec sâu cho từng module ngay bây giờ?)
2. **Role naming (DEC-A):** name Role tiếng Việt sẽ là định danh `frappe.get_roles()` — FE check theo chuỗi VI. OK, hay muốn **key EN ổn định + lớp dịch** (an toàn hơn cho i18n)? (đang chốt VI theo lựa chọn của bạn — xác nhận lại).
3. **Tách route AntMed (DEC-B):** mức tách tới đâu — chỉ layout+guard riêng trong cùng SPA, hay tách hẳn entry/portal? (ảnh hưởng công sức).
4. **Môi trường pixel-verify:** ai cung cấp credential test (Administrator / user mẫu) để Playwright đăng nhập verify?
5. **Commit:** working tree R1+R2 hiện chưa commit (HARD-STOP). Khi nào bạn muốn commit + có push GitHub không?
