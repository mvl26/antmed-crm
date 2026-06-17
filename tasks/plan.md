# Implementation Plan: AntMed CRM Frontend Prototype (bám mockup)

Spec: `docs/SPEC.md` · Mockup: `docs/antmed_crm/docs/AntMed_CRM_Full_Mockups.html`
Branch: `feat/antmed-mockup-prototype` · Mode: `/build auto` (1 lần duyệt → chạy hết).

## Overview
Dựng prototype trực quan 24 màn/8 vai trò khớp mockup, dữ liệu mẫu tĩnh, phục vụ tại `/crm`
(Home → A1). Vue 3 + frappe-ui + Tailwind. Test theo idiom dự án (pure-logic + content-assert).

## Architecture Decisions
- **Prototype, không backend** (Q1): dữ liệu mẫu tĩnh ở `src/data/antmedMock.js`.
- **AntMed = Home `/crm`** (Q2): route `/` render A1; CRM routes giữ nguyên reachable.
- **Layout chọn theo `route.meta.antmedShell`** (mở rộng `isAntmedPath`, tương thích `/antmed/*`).
- **UI kit tái dùng** `components/Antmed/ui/*` để 24 màn nhất quán & DRY.
- **Nav role-aware**: `src/data/antmedNav.js` đa-vai-trò (single source) + role switcher.
- **Không xoá** page real-data/CRM hiện có (no-regression).

## Task List

### Phase 1 — Foundation

- [x] **T0 — Sửa test baseline brittle (prep).** `antmedCustomer.test.js:93` khớp nhầm comment "createListResource" trong `antmed.js`. Đổi assert sang khớp **lệnh gọi** (`/createListResource\s*\(/`) thay vì chuỗi bất kỳ. *AC:* suite xanh 100%. *Files:* `tests/unit/antmedCustomer.test.js`. *Scope:* XS. *Deps:* None.

- [ ] **T1 — UI kit + token.** Tạo `components/Antmed/ui/`: AmPill, AmCard, AmKpiCard, AmBar, AmLifecycle, AmTimeline, AmFunnel, AmHeatCell, AmSteps, AmKanbanColumn, AmKanbanCard, AmPhoneFrame, AmTablet, AmRoleBand, AmScanBox, AmAlertBox + helper `antmedUi.js` (PILL_THEME map). *AC:* mỗi component file tồn tại + export; PILL_THEME phủ ok/warn/danger/info/neutral. *Verify:* test content-assert + helper unit test; `vite build` sạch. *Files:* ~16 `.vue` + `utils/antmedUi.js` + `tests/unit/antmedUi.test.js`. *Scope:* L. *Deps:* T0.

- [ ] **T2 — Dữ liệu mẫu.** `src/data/antmedMock.js`: export theo màn (ceoDashboard, contracts, revenue, dispatch, team, approvals, repToday, doctor, warehouseExport, consignment, lotTrace, docsPending, coCq, reconciliation, receivables, commission, portal, users, audit, instruments). *AC:* invariant test (mảng không rỗng, field bắt buộc). *Files:* `data/antmedMock.js` + `tests/unit/antmedMock.test.js`. *Scope:* M. *Deps:* None.

- [ ] **T3 — Shell role-aware + layout.** Mở rộng `antmedNav.js` thành nav theo vai trò (`ANTMED_ROLES`, `navForRole`) + role switcher trong AntmedLayout (topbar variant portal). Cập nhật `App.vue` chọn layout theo `route.meta.antmedShell` (giữ `isAntmedPath`). *AC:* `navForRole(role)` trả nav đúng; `isNavActive` vẫn đúng; App.vue dùng meta. *Files:* `data/antmedNav.js`, `components/Antmed/AntmedLayout.vue`, `App.vue` + cập nhật `tests/unit/antmedShell.test.js`. *Scope:* M. *Deps:* T1.

- [ ] **T4 — Routing 24 màn + Home→A1.** Thêm route mọi màn (meta `antmedShell:true`, `role`) trong `router.js`; route Home `/` render A1; `beforeEach` không redirect Home→Leads khi đã login. *AC:* bảng route có đủ 24 name/path + meta; Home có component. *Files:* `router.js` + cập nhật `tests/unit/antmedRouterGuard.test.js` (+ test route table). *Scope:* M. *Deps:* T3.

> **Checkpoint Foundation:** `yarn test:run` xanh · `vite build` sạch · `/crm` mở ra shell A1.

### Phase 2 — Màn theo vai trò (mỗi task: 1 commit, test content-assert, build khi đủ điều kiện)

- [ ] **T5 — CEO (A1, A2, A3).** Dashboard điều hành, Sức khỏe HĐ, Báo cáo DT. *Deps:* T4. *Scope:* M.
- [ ] **T6 — Trưởng KD (B1, B2, B3).** Kanban điều phối, Quản lý đội ngũ, Hộp duyệt. *Deps:* T4. *Scope:* M.
- [ ] **T7 — NV mobile I (C1, C2, C3).** Trang chủ, Wizard 4 bước, Checklist bộ DC (trong AmPhoneFrame/AmTablet). *Deps:* T4. *Scope:* M.
- [ ] **T8 — NV mobile II (C4, C5).** CRM Bác sỹ, Offline mode. *Deps:* T4. *Scope:* S.
- [ ] **T9 — Thủ kho (D1, D2, D3).** Xuất QR, Kho ký gửi, Truy vết lot. *Deps:* T4. *Scope:* M.
- [ ] **T10 — Chứng từ (E1, E2, E3).** Hàng chờ, Kho CO/CQ, Đối soát ký nhận. *Deps:* T4. *Scope:* M.
- [ ] **T11 — Kế toán (F1, F2).** Công nợ theo BV, Hoa hồng NV. *Deps:* T4. *Scope:* S.
- [ ] **T12 — Portal BV (G1, G2).** Trang chủ + gọi VT, Lịch sử & chứng từ (topbar trắng). *Deps:* T4. *Scope:* S.
- [ ] **T13 — Admin (H1, H2).** User & Role, Audit log. *Deps:* T4. *Scope:* S.
- [ ] **T14 — Bộ dụng cụ (I1).** Vòng đời 47 bộ. *Deps:* T4. *Scope:* S.

**AC chung mỗi màn:** render trong AntmedLayout đúng vai trò; có đủ các section bắt buộc ở §3 SPEC; dùng UI kit + dữ liệu mẫu; text VI qua `__()`; status pill kèm chữ. **Verify mỗi task:** test mới (content-assert section + route reachable) xanh · `yarn test:run` xanh · `vite build` sạch · commit.

> **Checkpoint Complete:** build sạch · Playwright duyệt trực quan A1/B1/C2/D3/F1/I1 · tất cả 24 route mở được.

## Risks and Mitigations
| Risk | Impact | Mitigation |
|---|---|---|
| Thay landing Home ảnh hưởng user CRM hiện hữu | Med | Giữ CRM routes reachable; reversible qua git revert; test guard giữ xanh |
| `vite build` chậm làm mỗi task lâu | Low | Build bắt buộc sau Foundation & cuối; per-task khi khả thi |
| Test content-assert "đỗ giả" (chỉ khớp chuỗi) | Med | Assert nhiều dấu hiệu cấu trúc + route reachable, không chỉ 1 từ |
| Prototype lệch quy ước "không bịa số" | Low | Người dùng đã chấp thuận (Q1); khoanh dữ liệu mẫu trong 1 module |

## Open Questions
- Không còn (Q1–Q3 đã chốt). Nếu phát sinh quyết định ngoài spec → dừng & hỏi (theo /build auto).
