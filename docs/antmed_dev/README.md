# AntMed CRM — Tài liệu phát triển (dev docs, tracked)

Thư mục này chứa **tài liệu phát triển** do team sinh ra khi build AntMed CRM (fork **in-place** trên app `crm`). **Git theo dõi** — sửa/review/commit ở đây.

> ⛔ **Phân biệt với `docs/antmed_crm/`**: đó là **repo scaffold tham khảo + tài liệu NGUỒN BA gốc** (`AntMed_CRM_Modules.md`, `AntMed_CRM_UI_Design.md`, `BA_AntMed_CRM.docx`, mockups). Là **git repo riêng + bị gitignore** (`.gitignore:23`) ⇒ KHÔNG version-control cùng app `crm`. Chỉ **đọc tham khảo**; KHÔNG viết dev-doc vào đó.

## Quy ước nền (chốt 2026-06-17 — xem SPEC §5, §8)
- **In-place** trong app `crm`: BE ở `crm/antmed/` + `crm/api/antmed/` → endpoint `antmed_crm.api.antmed.<module>.<fn>`. FE ở `frontend/src` (page `Antmed<Feature>.vue`, route `/antmed/*`). Site = `miyano`.
- DocType/Role prefix **`AntMed `** (KHÔNG `AM `). **Native-lite** (D1): KHÔNG ERPNext — tự xây `AntMed Item/Lot/Warehouse/Stock Entry/Delivery/Instrument Set…`. Workflow = **Frappe-native** (D2). Role **tiếng Việt** (DEC-A).
- Mọi BE = Frappe-standard (KHÔNG 3-tier): whitelist trả raw dict; lỗi nghiệp vụ `frappe.throw(_("BR-XX: …"))`; business rule ở module hooks qua `doc_events`.

## Cấu trúc
```
docs/antmed_dev/                 (TRACKED)
├── README.md                    # file này — index + quy ước
├── SPEC_AntMed_CRM.md           # governing spec cấp dự án (6 vùng lõi + ADR + boundaries + DoD)
├── PLAN_AntMed_CRM.md           # kế hoạch 14 module (dependency DAG + 5 wave W0→W4 + risk)
└── modules/                     # Core Doc / spec từng module (BA viết TRƯỚC khi code)
docs/antmed_crm/docs/            (gitignored, read-only) — nguồn BA gốc: AntMed_CRM_Modules.md, UI_Design.md, *.docx, mockups
```

## Bộ tài liệu module (14 module — anatomy chuẩn: Overview · DocTypes · Workflow · BR · API · Integration · UI · Build slices · ADR · Acceptance)

| Module | Core Doc | Wave | Trạng thái |
|---|---|---|---|
| **M01** Khách hàng (Customer 360°) | [`modules/m01_customer.md`](modules/m01_customer.md) (umbrella) · [`m01_customer360.md`](modules/m01_customer360.md) · [`m01_bootstrap.md`](modules/m01_bootstrap.md) · [`m01_naming_conventions.md`](modules/m01_naming_conventions.md) | W0–W1 | ✅ slice Customer 360° (BUILT) · M01-full [PLANNED] |
| **M02** Hợp đồng & Quota | [`modules/m02_contract_quota.md`](modules/m02_contract_quota.md) | W1 | [PLANNED] |
| **M03** Vật tư & Kho đa điểm (native-lite) | [`modules/m03_inventory.md`](modules/m03_inventory.md) | W1 | [PLANNED] |
| **M04** Giao phòng mổ + SLA | [`modules/m04_or_delivery.md`](modules/m04_or_delivery.md) | W2 | [PLANNED] |
| **M05** Cho mượn bộ dụng cụ + tiệt khuẩn | [`modules/m05_instrument_loan.md`](modules/m05_instrument_loan.md) | W3 | [PLANNED] |
| **M06** Chứng từ CO/CQ/ĐKLH + HĐĐT | [`modules/m06_documents.md`](modules/m06_documents.md) | W2 | [PLANNED] |
| **M07** CSKH Bác sỹ | [`modules/m07_doctor_care.md`](modules/m07_doctor_care.md) | W3 | [PLANNED] |
| **M08** Sales Pipeline / Tender | [`modules/m08_pipeline.md`](modules/m08_pipeline.md) | W4 | [PLANNED] (extend CRM Lead/Deal gốc) |
| **M09** Đơn hàng, Công nợ & AR | [`modules/m09_orders_ar.md`](modules/m09_orders_ar.md) | W2 | [PLANNED] |
| **M10** Nhân sự KD & KPI | [`modules/m10_hr_kpi.md`](modules/m10_hr_kpi.md) | W4 | [PLANNED] |
| **M11** Báo cáo & Dashboard (API-only) | [`modules/m11_dashboard.md`](modules/m11_dashboard.md) | W4 | [PLANNED] (KHÔNG doctype) |
| **M12** Mobile PWA | [`modules/m12_mobile.md`](modules/m12_mobile.md) | W4 | [PLANNED] (FE PWA layer) |
| **M13** Tích hợp & API | [`modules/m13_integrations.md`](modules/m13_integrations.md) | W4 | [PLANNED] (nhiều phần [ROADMAP]) |
| **M14** Phân quyền, Bảo mật & Audit | [`modules/m14_security_audit.md`](modules/m14_security_audit.md) (umbrella) · [`m14_rbac_w0_role_naming.md`](modules/m14_rbac_w0_role_naming.md) · [`m14_rbac_w0_antmed_boot.md`](modules/m14_rbac_w0_antmed_boot.md) | W0 + W4 | 🟡 W0 role-VI + boot (PARTIAL) · M14-full [PLANNED] |

## Nguyên tắc làm việc
- Tài liệu nguồn (đầu vào, read-only) = `docs/antmed_crm/docs/`; tài liệu phát triển (đầu ra) = **thư mục này**.
- Mỗi Core Doc module mới → đặt trong `modules/`. Đặt tên `m0X_<tên>.md`.
- **Spec-before-code**: BA chốt Core Doc module → BE/FE mới build (factory loop). `[PLANNED]` = thiết kế đề xuất, chưa có code; đánh dấu `[UNVERIFIED]`/`[cần khảo sát]` cho điểm chưa chốt.
- Engine thực thi: AntMed factory loop (pm→ba→[be‖fe]→qa→user), mỗi vòng = 1 vertical slice theo SPEC + Core Doc module.
