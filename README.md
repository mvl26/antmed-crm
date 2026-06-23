<div align="center" markdown="1">

<img src=".github/logo.svg" height="80" alt="AntMed CRM Logo">

<h1>AntMed CRM</h1>

**Quản lý phân phối thiết bị & vật tư y tế (VTYT) và cho mượn bộ dụng cụ phẫu thuật cho bệnh viện**

[![License: AGPL v3](https://img.shields.io/badge/License-AGPLv3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Frappe v15](https://img.shields.io/badge/Frappe-v15-0d9488.svg)](https://github.com/frappe/frappe)

</div>

## Giới thiệu

**AntMed CRM** là phần mềm CRM chuyên ngành cho doanh nghiệp phân phối **thiết bị & vật tư y tế (VTYT)**:
quản lý trọn vòng đời từ tiếp cận bệnh viện/bác sỹ → gói thầu/hợp đồng → kho ký gửi & truy vết lô →
giao phòng mổ → mượn-trả bộ dụng cụ & tiệt khuẩn → chứng từ pháp lý (CO/CQ/ĐKLH/hóa đơn điện tử) →
công nợ và KPI.

Sản phẩm được phát triển trên nền **Frappe Framework v15** (Python backend + giao diện **Vue 3 /
frappe-ui** dạng SPA) theo hướng **native-lite** (không phụ thuộc ERPNext), kế thừa nền tảng
[Frappe CRM](https://github.com/frappe/crm) cho lead/deal và bổ sung toàn bộ nghiệp vụ đặc thù ngành VTYT.
Site phát triển: `miyano`.

## Tính năng chính (14 module)

| Module                                    | Nghiệp vụ                                                                                                 |
| :---------------------------------------- | :---------------------------------------------------------------------------------------------------------- |
| **M01 — Khách hàng 360**         | Bệnh viện, khoa/phòng, bác sỹ; hồ sơ 360, lịch sử tương tác                                     |
| **M02 — Hợp đồng & Gói thầu** | Hợp đồng, gói thầu, quota theo mặt hàng, theo dõi thực hiện                                       |
| **M03 — Kho & Lô**                | Kho đa cấp + ký gửi BV, lô/CO/CQ, FIFO theo HSD, kiểm kê,**thu hồi (recall) & truy vết lô** |
| **M04 — Giao phòng mổ**          | Phiếu giao (DO), điều phối ca mổ, SLA, ghi nhận tiêu hao theo lô                                    |
| **M05 — Bộ dụng cụ mượn**     | Vòng đời mượn–trả, checklist,**tiệt khuẩn**                                                  |
| **M06 — Chứng từ**               | CO/CQ, ĐKLH, giấy phép nhập khẩu,**hóa đơn điện tử**                                       |
| **M07 — CSKH bác sỹ**            | Kế hoạch thăm khám, ghi chú chăm sóc, quà tặng                                                     |
| **M08 — Pipeline**                 | Lead → thầu → cơ hội (CRM Deal), bảng Kanban kéo–thả                                               |
| **M09 — Đơn hàng & Công nợ**  | Đơn hàng, công nợ AR, chặn đơn theo hạn mức                                                       |
| **M10 — Nhân sự & KPI**          | Đội kinh doanh, chỉ tiêu, KPI                                                                           |
| **M11 — Dashboard**                | Bảng điều khiển & báo cáo điều hành                                                                |
| **M12 — Mobile / PWA**             | Trải nghiệm di động, đồng bộ offline                                                                 |
| **M13 — Tích hợp**               | Zalo/SMS thông báo, nhà cung cấp hóa đơn điện tử                                                  |
| **M14 — RBAC & Audit**             | Phân quyền, 2FA, nhật ký kiểm toán hash-chain                                                         |

### Vai trò nghiệp vụ

Ba vai trò chính: **NV kinh doanh** · **Thủ kho** · **Quản lý** — phân quyền và data-scoping
(NV chỉ thấy bệnh viện được giao) qua RBAC native của Frappe.

## Công nghệ

- [Frappe Framework](https://github.com/frappe/frappe) **v15** — full-stack web framework (Python).
- [Frappe UI](https://github.com/frappe/frappe-ui) — thư viện UI dựa trên **Vue 3** cho giao diện SPA hiện đại.
- **MariaDB** — cơ sở dữ liệu.
- **Redis** — cache & hàng đợi tác vụ (queue).
- **Native-lite:** không cài ERPNext; toàn bộ doctype nghiệp vụ là `AntMed *` thuần.

## Cấu trúc dự án

```text
antmed_crm/                      # Repo (app antmed_crm)
├── antmed_crm/                  # Python app package (app_name = antmed_crm)
│   ├── api/antmed/              # Endpoint whitelisted: antmed_crm.api.antmed.<module>.<fn>
│   │                            #   customer · contract · inventory · delivery · instrument_loan
│   │                            #   documents · doctor_care · pipeline · finance · dashboard
│   │                            #   sales_team · mobile_sync · integrations · rbac · audit ...
│   ├── antmed/doctype/          # Module "AntMed" — 49 DocType (AntMed Hospital / Lot /
│   │                            #   Stock Entry / Delivery / Contract / Instrument Loan /
│   │                            #   Document / E-Invoice / Audit Log ...)
│   ├── fixtures/                # workflow · role · naming_series · custom_field
│   ├── hooks.py                 # định danh app · doc_events · scheduler_events
│   ├── permissions/  overrides/  patches/  integrations/  tests/
│   └── modules.txt              # AntMed · FCRM · Lead Syncing
├── frontend/                    # SPA Vue 3 + frappe-ui (phục vụ tại base /crm)
│   └── src/                     # pages/ (38 trang Antmed*.vue) · components/ · data/antmed.js
│                                #   · router.js · stores/ · utils/
├── docs/antmed_dev/             # Spec phát triển module M01–M14
├── docker/   .github/           # Triển khai & CI/CD (image ghcr.io/mvl26/antmed_crm)
├── .claude/                     # Quy tắc & skill cho phiên phát triển
└── pyproject.toml   package.json
```

> **Quy ước:** app = `antmed_crm` (snake_case); module nghiệp vụ = `antmed` (DocType prefix `AntMed `);
> callpath API = `antmed_crm.api.antmed.<module>.<fn>`.

## Bắt đầu (Development)

1. [Cài đặt Bench](https://docs.frappe.io/framework/user/en/installation).
2. Trong thư mục `frappe-bench`, chạy `bench start` và giữ tiến trình.
3. Mở terminal mới, vào `frappe-bench` và chạy:
   ```sh
   # Lấy app
   bench get-app antmed_crm        # hoặc: bench get-app https://github.com/mvl26/antmed_crm.git

   # Cài app vào site (thay <site> bằng site của bạn, vd: miyano)
   bench --site <site> install-app antmed_crm

   bench browse <site> --user Administrator
   ```
4. Truy cập ứng dụng tại `<site>:8000/crm`.

**Phát triển Frontend**

```sh
cd frappe-bench/apps/antmed_crm/frontend
yarn install
yarn dev
```

Vite dev server chạy tại `http://sitename.localhost:8080`. Toàn bộ mã frontend nằm trong
`frappe-bench/apps/antmed_crm/frontend`.

## Triển khai bằng Docker

Image container được CI build và đẩy lên GitHub Container Registry:

```
ghcr.io/mvl26/antmed_crm:stable
```

Image đa kiến trúc (`linux/amd64`, `linux/arm64`) dựng từ
[frappe_docker](https://github.com/frappe/frappe_docker) (layered Containerfile). Xem thư mục
`docker/` và workflow `.github/workflows/builds.yml` để biết chi tiết.
