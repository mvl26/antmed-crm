# SPEC — AntMed CRM Frontend Prototype (bám mockup)

> Nguồn yêu cầu: `docs/antmed_crm/docs/AntMed_CRM_Full_Mockups.html` (24 màn / 8 vai trò).
> Spec này **chép lại thiết kế từ mockup** + 3 quyết định người dùng (2026-06-17). KHÔNG bịa thêm yêu cầu.

## 0. Quyết định nền (người dùng chốt)

| # | Quyết định | Hệ quả |
|---|---|---|
| Q1 | **Prototype trực quan — bám mockup 100%** | Dựng đủ 24 màn giống mockup, dùng **dữ liệu mẫu tĩnh** (đúng số liệu trong mockup). Đây là prototype demo, KHÔNG wire backend. Ngoại lệ quy ước "không bịa số" được người dùng cho phép vì đây là prototype. |
| Q2 | **AntMed là trang chủ `/crm`** | Vào `localhost/crm` (route Home `/`) hiển thị ngay Dashboard điều hành AntMed (A1). Route CRM gốc (`/leads`, `/deals`…) GIỮ NGUYÊN reachable (no-regression). |
| Q3 | **Lập kế hoạch + build tự động cả 24 màn** | `/build auto`: 1 lần phê duyệt plan → chạy hết, mỗi task có test + commit riêng. |

## 1. Phạm vi

- **In scope**: 24 màn prototype (A1–I1), trong app `frontend/` (Vue 3 + frappe-ui + Tailwind), phục vụ tại `/crm`.
- **Out of scope**: backend AntMed (`antmed_crm.api.antmed.*`), wiring dữ liệu thật, business rule, RBAC thực thi. Prototype dùng dữ liệu mẫu.
- **Không phá**: route + page CRM gốc và các page AntMed real-data hiện có (`AntmedHospitalList/Detail`, `AntmedDoctorDetail`, `AntmedContracts`) vẫn còn (reachable), không xoá.

## 2. Kiến trúc prototype

### 2.1 UI kit (components/Antmed/ui/)
Bộ component trình bày tái dùng, khớp visual mockup (palette teal brand, pill, card, table):
`AmPill` (ok/warn/danger/info/neutral), `AmCard`, `AmKpiCard` (mở rộng AntmedKpiCard), `AmBar` (warn/danger), `AmLifecycle` (7 trạng thái: SS·Đặt·Giao·SD·Trả·Xử lý·SS lại), `AmTimeline`, `AmFunnel`, `AmHeatCell`, `AmSteps` (wizard), `AmKanbanColumn`/`AmKanbanCard`, `AmPhoneFrame` (khung mobile cho màn C/G), `AmTablet`, `AmRoleBand`, `AmScanBox`, `AmSignaturePad` (placeholder), `AmAlertBox` (info/warn/danger).
- Token màu mockup ánh xạ qua Tailwind (`teal-*`, `amber-*`, `red-*`, `green-*`, `slate/ink-gray-*`) + 1 file CSS scoped cho biến brand nếu cần.

### 2.2 Shell + điều hướng (role-aware)
- **Topbar**: logo `⚕ AntMed CRM`, ô tìm kiếm, chip kỳ/vai trò, chuông, avatar. Variant portal (nền trắng) cho vai trò G.
- **Sidebar**: đổi theo vai trò đang xem (mỗi vai trò có nav riêng theo mockup).
- **Role switcher**: cho phép duyệt qua 8 vai trò trong prototype (single-source data `antmedNav`).
- Active-state qua `isNavActive` (giữ helper hiện có, mở rộng).

### 2.3 Routing & layout
- `/` (Home) → màn A1 (CEO Dashboard) trong AntmedLayout (Q2).
- Mỗi màn 1 route; gom theo vai trò (prefix `/ceo`, `/sales`, `/rep`, `/warehouse`, `/docs`, `/finance`, `/portal`, `/admin`, `/instruments`).
- `App.vue` chọn AntmedLayout theo `route.meta.antmedShell === true` (mở rộng `isAntmedPath` cũ — giữ tương thích route `/antmed/*`).
- `router.beforeEach`: Home khi đã đăng nhập KHÔNG redirect sang Leads nữa (Q2) — render A1. CRM routes giữ logic cũ.
- Dữ liệu mẫu: module tĩnh `src/data/antmedMock.js` (1 nguồn, có invariant test shape).

## 3. Danh mục 24 màn (acceptance theo mockup)

| Mã | Màn | Yếu tố bắt buộc (theo mockup) |
|---|---|---|
| A1 | CEO · Dashboard điều hành | 4 KPI (DT tháng/Quota/SLA/Bộ DC) + heatmap-map placeholder + Top 10 BV + Funnel pipeline + Cảnh báo |
| A2 | CEO · Sức khỏe hợp đồng | Bộ lọc + bảng HĐ (quota bar, status pill) + 2 card tiêu hao/Top SKU |
| A3 | CEO · Báo cáo doanh thu | 3 KPI + 2 chart placeholder + heatmap NV×BV + legend |
| B1 | TKD · Kanban điều phối | 4 cột (Mới/Đã gán/Đang giao/Bàn giao) thẻ urgent/warn/ok + legend |
| B2 | TKD · Quản lý đội ngũ | Bảng KPI NV + 2 card hồ sơ NV (timeline GPS, bộ DC) |
| B3 | TKD · Hộp duyệt yêu cầu | List inbox + drawer chi tiết YC + alert ngưỡng + nút duyệt/từ chối |
| C1 | NV · Trang chủ (mobile) | Phone frame, 3 stat, danh sách ca hôm nay (accent/ok/danger), tabbar |
| C2 | NV · Wizard giao 4 bước | Steps (done/current), bảng VT, GPS alert, ký số, nút điều hướng |
| C3 | NV · Checklist bộ dụng cụ | Checklist 42 món, ảnh, ký, lifecycle bộ |
| C4 | NV · CRM Bác sỹ (mobile) | Hồ sơ BS, nút gọi/zalo/checkin, tab ghi chú/lịch sử, FAB + |
| C5 | NV · Offline mode | Banner offline, danh sách thao tác chờ sync (pill warn) |
| D1 | Kho · Xuất cho NV (QR) | Form NV/mục đích, bảng VT đã quét + CO/CQ pill, scanbox, phiếu gần đây |
| D2 | Kho · Kho ký gửi BV | 3 KPI + bảng đối chiếu (chênh lệch, cận date) |
| D3 | Kho · Truy vết lot | Form mã lot, bảng thông tin lot, cây truy vết (tree), nút recall |
| E1 | Chứng từ · Hàng chờ phát hành | List thiếu CO/CQ + drawer + dropzone đính file |
| E2 | Chứng từ · Kho CO/CQ | Cây thư mục NCC + bảng file (hash, đã gắn) |
| E3 | Chứng từ · Đối soát ký nhận | 4 KPI + bảng SLA ký nhận |
| F1 | Kế toán · Công nợ theo BV | 4 KPI aging + bảng aging heatmap theo BV |
| F2 | Kế toán · Hoa hồng NV | 2 card tổng/quy tắc + bảng hoa hồng chi tiết |
| G1 | Portal · Trang chủ + gọi VT | Topbar trắng, 3 action card, form gọi VT (danh mục thầu), timeline thông báo |
| G2 | Portal · Lịch sử & chứng từ | Bảng lịch sử phiếu + chứng từ + trạng thái TT |
| H1 | Admin · User & Role | Bảng user (role/2FA/scope) + drawer ma trận quyền |
| H2 | Admin · Audit log | Bộ lọc + bảng audit (actor/IP/action/diff) |
| I1 | Bộ dụng cụ · Vòng đời 47 bộ | 4 KPI + grid card bộ (lifecycle) + bảng tần suất |

## 4. Ràng buộc kỹ thuật & DoD

- Vue 3 `<script setup>`, frappe-ui, Tailwind (token dự án). i18n qua `__()` cho text VI.
- A11y: `aria-label`/`aria-current` cho nav, status pill kèm chữ (không chỉ màu).
- **Test idiom dự án**: pure-logic + content-assert đọc source (KHÔNG `@vue/test-utils`). Mỗi task có test (RED→GREEN) cho: nav/route config, data-fixture invariants, và content-assert các section bắt buộc của màn.
- DoD mỗi task: test mới xanh · toàn bộ suite xanh (`yarn test:run`) · `vite build` compile sạch (tối thiểu sau nền + cuối) · 1 commit mô tả rõ.
- Verify cuối: build sạch + duyệt trực quan bằng Playwright trên các màn chính.
