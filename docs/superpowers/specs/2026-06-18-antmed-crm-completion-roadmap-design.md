# AntMed CRM — Lộ trình hoàn thiện (Gap Analysis + Roadmap)

- **Ngày:** 2026-06-18
- **Trạng thái:** Design đã duyệt (chờ user review spec)
- **Phạm vi:** Đối chiếu BA (`docs/BA/AntMed_CRM_Modules.md`, 14 module) ↔ codebase hiện tại; xác định gap; lộ trình hoàn thiện theo ưu tiên. Mỗi gap là 1 **sub-project riêng** (spec → plan → build).

---

## 1. Bối cảnh & mục tiêu

AntMed CRM = fork Frappe CRM, tùy biến cho nghiệp vụ vật tư y tế + cho mượn bộ dụng cụ phẫu thuật của Công ty AntMed (đội KD kiêm nhiệm: bán + thủ kho di động + giao phòng mổ + bộ dụng cụ mượn + chứng từ + CSKH bác sỹ + phát triển KH).

Codebase đã **rất trưởng thành**: 21 module BE (`antmed_crm/api/antmed/*.py`), 47 doctype AntMed-native (`antmed_crm/antmed/doctype/`), 39 màn FE (`frontend/src/pages/Antmed*.vue`), 48 file test BE. UI CRM gốc đã gỡ hoàn toàn (chỉ còn UI AntMed tại `/antmed/*`).

**Mục tiêu spec:** chốt 5 gap còn lại + thứ tự + tiêu chí Done, để build từng module trọn vẹn (Phase 1–3 của BA về cơ bản đã phủ; đây là phần "hoàn thiện").

## 2. Hiện trạng độ phủ 14 module (đã verify bằng code)

| Module BA | Trạng thái | Bằng chứng |
|---|---|---|
| M01 Khách hàng 360° | ✅ Đủ | `customer.py` (14 wl) + Hospital/Doctor doctype + FE HospitalList/Detail, DoctorDetail (+Activity panel) |
| M02 Hợp đồng/Quota | ✅ Đủ | `contract.py` (12 wl) + Contract/Quota doctype + FE Contracts/Detail/Health |
| M03 Tồn kho đa điểm/ký gửi/lot/recall | ✅ Đủ *(phiên song song)* | `inventory.py` (29 wl)/`stock.py` + stock_*/lot/recall doctype + FE Issue/Receipt/Count/LotTrace/LotList/Consignment/ExpiryAlerts |
| M04 Giao phòng mổ/SLA | ✅ Đủ | `delivery.py` (9 wl) + Delivery doctype + FE Deliveries/Detail/Dispatch (B1) |
| M05 Bộ dụng cụ mượn/tiệt khuẩn | ✅ Đủ | `instrument_loan.py` (13 wl) + InstrumentSet/Loan/Sterilization + FE Sets/Detail/Checklist |
| M06 Chứng từ/CO-CQ/HĐĐT | ✅ Đủ (lõi) | `documents.py` (14 wl) + Document/Certificate/EInvoice + FE ReleaseQueue |
| M07 CSKH bác sỹ | ⚠️ **GAP (FE)** | BE `doctor_care.py` (11 wl: call_plan/visit/gift/survey) **đủ** — **KHÔNG có màn FE** (chỉ DoctorDetail) |
| M08 Pipeline | ✅ Đủ *(phiên song song)* | `pipeline.py` (19 wl) + Lead/Deal/Tender + FE Leads/DealPipeline/DealDetail/TenderDetail |
| M09 Đơn hàng/Công nợ/Doanh thu | ⚠️ **GAP (lõi)** | `finance.py` chỉ `commission_summary` — **thiếu** đơn-từ-phiếu-giao, công nợ/tuổi nợ, nhắc thu, xuất kế toán |
| M10 HR/KPI | ✅ Đủ | `sales_team.py` (roster/KPI/commission) + FE Team/RepProfile |
| M11 Dashboard | ⚠️ **GAP (một phần)** | `dashboard.py`: overview(CEO)+quota+tender — **thiếu** dashboard Kho/Bộ dụng cụ/SLA giao/Báo cáo tuân thủ |
| M12 Mobile offline-first | ⚠️ **GAP** | `mobile_sync.py`: bootstrap/scan/register/apply_outbox (một phần) — **thiếu** PWA/service-worker offline đầy đủ + push |
| M13 Tích hợp | ⚠️ **GAP (connector thật)** | `integrations.py`: khung log+retry — **thiếu** connector HĐĐT (Viettel/MISA/VNPT), Zalo/SMS, đấu thầu |
| M14 RBAC/Bảo mật/Audit/2FA | ✅ Đủ | `rbac.py`/`audit.py` + 2FA/AuditLog doctype |

→ **9 module vững · 5 gap cần hoàn thiện: M07, M09, M11, M12, M13.**

## 3. Năm gap — chi tiết & tiêu chí Done

### Gap 1 — M07 CSKH Bác sỹ (FE-only) · Effort S–M
- **BA cần:** lịch ghé thăm (call plan) + check-in GPS; ghi chú cuộc gặp (chủ đề/đối thủ/cam kết); quà tặng & tài trợ (compliance log); khảo sát hài lòng sau ca mổ; nhắc sinh nhật/kỷ niệm.
- **Đã có:** BE `doctor_care.py` 11 endpoint + doctype Call Plan/Doctor Visit/Doctor Gift/Care Note/Satisfaction Survey. **FE chưa có màn.**
- **Việc:** FE `AntmedDoctorCare.vue` (lịch ghé thăm + nút check-in GPS) + tích hợp timeline gặp/quà/khảo sát vào **DoctorDetail** (tái dùng `AntmedActivityPanel`/`AmTimeline`). Resource `data/antmed.js` (GET, đúng method). Route `/antmed/doctor-care` + nav (mục CSKH). KHÔNG cần BE mới (verify trước; bổ sung endpoint nhỏ nếu thiếu).
- **Done:** màn render data thật; check-in tạo Doctor Visit (GPS); timeline gặp/quà/khảo sát trên DoctorDetail; vitest + build xanh; verify live.

### Gap 2 — M11 Dashboards còn thiếu · Effort M
- **BA cần:** Dashboard Kho (tồn theo lô/cận date/ký gửi); Dashboard Bộ dụng cụ (tần suất/vòng quay/sự cố); Dashboard SLA giao phòng mổ; Báo cáo tuân thủ (chứng từ thiếu/CO-CQ chưa gắn/HĐ sắp hết hạn).
- **Đã có:** `dashboard.py` overview(CEO)+quota+tender; data nền M03/M04/M05/M06 đầy đủ.
- **Việc:** BE ~4 endpoint GỘP (read-only, dưới permission BR-13): `warehouse_dashboard`, `instrument_dashboard`, `sla_dashboard`, `compliance_report`. FE thẻ/màn dùng UI kit (AmKpiCard/AmBar) + route + nav. KHÔNG doctype mới.
- **Done:** 4 dashboard render số liệu thật khớp nguồn; test BE (assert số ≥ side-effect thật) + FE; live verify.

### Gap 3 — M09 Đơn hàng / Công nợ / Doanh thu · Effort L (lõi tài chính)
- **BA cần:** đơn bán từ phiếu giao thực tế tiêu hao (M04); Hóa đơn ↔ Công nợ (tuổi nợ, hạn theo HĐ, nhắc thu tự động); đối soát + xuất file kế toán (MISA/Fast/Bravo); KPI doanh thu theo bác sỹ/BV/NV/nhóm vật tư.
- **Đã có:** `finance.py` commission_summary; E-Invoice doctype (M06); Delivery consumption (đã wire ledger).
- **Việc:** BE — doctype/luồng **Đơn bán** (sinh từ Delivery consumed_qty) + **Công nợ/AR** (aging buckets, hạn theo HĐ) + scheduler **nhắc thu**; endpoint xuất CSV kế toán; KPI doanh thu đa chiều. FE — màn Đơn hàng, Công nợ (tuổi nợ), KPI doanh thu. **Phụ thuộc** M06 (HĐĐT) + M04 (tiêu hao). TDD nặng (BR công nợ/đối soát).
- **Done:** đơn sinh đúng từ phiếu giao; AR aging chính xác; nhắc thu chạy scheduler; export khớp; test BE side-effect thật + FE; live e2e.

### Gap 4 — M13 Tích hợp (connector thật) · Effort L · **chặn ngoài**
- **BA cần:** connector HĐĐT (Viettel/MISA/VNPT) phát hành & gửi mail; Zalo OA/SMS gateway (BV đặt vật tư inbound); theo dõi đấu thầu muasamcong.mpi.gov.vn; API mở đối chiếu kho ký gửi.
- **Đã có:** `integrations.py` khung (settings/log/retry) + Integration Setting/Log doctype; E-Invoice Provider doctype.
- **Việc:** adapter từng connector (idempotent, log qua khung sẵn, retry); webhook inbound (Zalo/SMS → tạo Material Request/Delivery); scraper/API đấu thầu. **Chặn:** cần **credential/tài khoản vendor** → làm khi user cấp; trước đó chỉ dựng adapter + sandbox/mock + test.
- **Done:** mỗi connector phát/nhận thật trong sandbox; log + retry hoạt động; gate 2FA cho phát hành HĐĐT (M14).

### Gap 5 — M12 Mobile offline-first · Effort L · cross-cutting
- **BA cần:** PWA giao diện chính NV KD; lấy hàng (quét QR)/giao (ký số)/mượn-trả ngoài hiện trường; tra cứu HĐ/giá tại chỗ; chụp ảnh gắn đơn/checklist; **offline-first** (ghi khi mất sóng, sync khi có); push (yêu cầu mới/quá hạn/công nợ).
- **Đã có:** `mobile_sync.py` (bootstrap/scan_lot/register_device/apply_outbox) + Mobile Device/Sync Log doctype; QrScanner.vue (M03).
- **Việc:** PWA manifest + service-worker (cache shell + offline read); **outbox đầy đủ** cho mọi field-op (xuất/giao/mượn); push FCM; layout mobile (phone-frame). Làm **SAU** khi các màn field-ops ổn (bọc toàn app).
- **Done:** cài PWA; thao tác offline → outbox → sync khi online (không double-post, idempotent); push tới được thiết bị; e2e mobile.

## 4. Thứ tự ưu tiên & lý do

**M07 → M11 → M09 → M13 → M12** (đã user duyệt 2026-06-18).

1. **M07** — quick win, BE sẵn, chỉ thiếu FE; giá trị CSKH cao; rủi ro thấp.
2. **M11** — tận dụng data M03/M04/M05/M06 đã có; tăng giám sát điều hành; effort vừa.
3. **M09** — lõi tài chính, giá trị cao nhất nhưng lớn + phụ thuộc M06/M04 (cần data tiêu hao/HĐĐT ổn trước).
4. **M13** — **chặn bởi credential vendor** → dựng adapter trước, kích hoạt khi có tài khoản.
5. **M12** — cross-cutting (bọc mọi màn) → làm cuối khi field-ops đã hoàn chỉnh.

## 5. Phối hợp phiên song song (BẮT BUỘC)

Phiên BE/FE song song đang hoàn thiện **M03 (kho/wizard/QR), M08 (Lead/Deal/Tender), lot-trace, recall, PDF**. Roadmap này **KHÔNG đụng** các module đó. Khi build gap chạm file dùng chung (`router.js`, `antmedNav.js`, `data/antmed.js`), **append tối thiểu** + báo phối hợp; tránh sửa file WIP uncommitted của họ. Commit tách BE/FE, loại file phiên khác.

## 6. Chuẩn xuyên suốt (invariant cho mọi gap)

- **FE↔BE:** mọi `createResource` gọi `antmed_crm.api.antmed.*` phải khai `method:'GET'` (mutation `'POST'`); endpoint GET-only — POST mặc định → 403. (guard `antmedResourceMethod.test.js`)
- **i18n:** `__('...{0}...', [args])` — KHÔNG `__('{0}')` 1-arg (crash translation, trang trắng). (guard `antmedI18nFormat.test.js`)
- **Shell:** mọi màn dưới `/antmed/*` render trong `AntmedLayout`; icon dùng thư viện `@/components/Icons/*` (KHÔNG emoji tự chế).
- **Đọc dict RAW:** `board.data.*` trực tiếp (KHÔNG `.data.data`); fallback param đã-định-nghĩa (tránh `undefined`→chuỗi "undefined").
- **Permission:** đọc dưới `frappe.get_list` (BR-13 fail-closed) — NV chỉ thấy phạm vi.
- **TDD + data thật:** test assert side-effect THẬT (R-9 fixture tự dọn `_T-` prefix); UI test dùng data BV/VTYT VN thật (R-1); cuối mỗi kỳ dọn artifact (R-12).
- **DoD:** vitest + `yarn build` xanh; BE `bench run-tests` module xanh; live verify (server-side hoặc Playwright) trước khi tuyên bố Done.

## 7. Bước kế tiếp

Mỗi gap = 1 sub-project: **spec riêng → writing-plans → build từng slice**. Bắt đầu **Gap 1 (M07 CSKH)**: brainstorm chi tiết màn CSKH → spec → plan → implement. Các gap sau lặp lại quy trình.
