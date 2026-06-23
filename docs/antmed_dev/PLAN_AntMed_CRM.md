# Plan: AntMed CRM — Hoàn thiện toàn bộ tính năng (Phase 2)

> **Trạng thái:** Phase 2 — Plan · *chờ human duyệt trước khi sang Tasks/Implement.*
> **Cặp với:** `SPEC_AntMed_CRM.md` (governing spec) · **Cập nhật:** 2026-06-17 · **Vị trí:** `docs/antmed_dev/` (tracked) · **Nguồn BA:** `docs/antmed_crm/docs/` (tham khảo)
> Engine thực thi: **AntMed factory loop** (pm→ba→[be‖fe]→qa→user), mỗi vòng = 1 vertical slice.

---

## 0. Trạng thái hiện tại (baseline)

- ✅ **M01 — Bootstrap** (namespace `antmed_crm/antmed/`, 3 Role, `antmed_crm.api.antmed.health.ping`) + **Customer 360° slice** (DocType `AntMed Hospital`/`AntMed Doctor`, API list/detail, 3 trang Vue). Test xanh (BE 11 OK, FE 136). **Uncommitted**, chờ USER reload + pixel verify.
- ⏳ Mở: role-name → tiếng Việt (DEC-A), tách route AntMed riêng (DEC-B), purge data rác `_SEC-H*`.

---

## ✅ DECISIONS LOCKED (user 2026-06-17)

- **D1 = (B) Native-lite** — KHÔNG cài ERPNext. Xây DocType AntMed-native: `AntMed Item`/VTYT, `AntMed Warehouse`, `AntMed Lot` (CO/CQ/HSD), `AntMed Stock Entry`, `AntMed Delivery`, `AntMed Instrument Set`. Tự code FIFO/HSD/tồn-bin ở mức cần dùng.
- **D2 = Frappe Workflow gốc** (default, user không override) — state machine qua fixtures `workflow.json` + `docstatus`. KHÔNG cặp vào `workflowcore`.
- **D3 = role tiếng Việt (DEC-A) + tách route AntMed riêng (DEC-B)** — áp ở W0.
- **Thứ tự = giữ nguyên W0→W4.** · **Cadence = ~8 vòng/mẻ** (chạy 8 vòng → dừng review).

---

## 1. Quyết định nền tảng cần chốt (chặn/định hình plan)

| ID | Quyết định | Lựa chọn | Khuyến nghị |
|---|---|---|---|
| **D1** | **Tầng kho/vật tư khi KHÔNG có ERPNext** | **(A)** cài ERPNext rồi reuse Item/Warehouse/Batch/Bin/Delivery Note · **(B)** xây **DocType AntMed-native nhẹ** (`AntMed Item`/VTYT, `AntMed Warehouse`, `AntMed Lot`, `AntMed Delivery`, `AntMed Instrument Set`) · **(C)** hybrid | **(B) native** — hợp triết lý fork nhẹ, toàn quyền lot CO/CQ + kho ký gửi + bộ mượn; tránh phụ thuộc ERPNext nặng vào CRM đã fork. Đánh đổi: tự code FIFO/HSD/tồn-bin. |
| **D2** | **Engine workflow/state-machine** (M04 giao phòng mổ, M05 bộ mượn 7 trạng thái, M02/M08) | Frappe **Workflow** gốc (fixtures `workflow.json` + `docstatus`) · reuse app `workflowcore` (đã cài) | **Frappe Workflow gốc** — chuẩn, không cặp AntMed vào app dự án khác; chỉ xét workflowcore nếu cần tính năng vượt Frappe. |
| **D3** | Role naming + truy cập SPA | đã chốt: role **tiếng Việt** (DEC-A) + **tách route AntMed riêng** (DEC-B) | áp ngay ở **Wave 0** (nền RBAC) |
| **D4** | Audit trail M14 | hash-chain SHA256 (theo domain doc BR-10) | nền tối thiểu sớm, bồi dần |

> ⚠️ **D1 phải chốt trước Wave 1** — nó định hình M02/M03/M04/M05/M06/M09. Plan dưới đây giả định **(B) native**; nếu bạn chọn (A)/(C) tôi sửa lại các wave kho/giao hàng.

---

## 2. Component inventory + Dependency DAG

| M | Module | Trạng thái CRM gốc | Phụ thuộc | Cấp dữ liệu cho | DocType chính (native) |
|---|---|---|---|---|---|
| M01 | Customer 360° (BV+Bác sỹ) | tùy biến | — | hầu hết | `AntMed Hospital`, `AntMed Doctor` ✅ |
| M14 | Security/RBAC/Audit/2FA | một phần | — (nền) | tất cả | Role(VI), `AntMed Audit Log`, data-scope BR-13 |
| M02 | Hợp đồng & Quota | một phần | M01 | M04, M09, M08 | `AntMed Contract`, `AntMed Quota Item` |
| M03 | Kho đa điểm + Lot/CO-CQ + Recall | xây mới | (Item native) | M04, M05, M06 | `AntMed Item`, `AntMed Warehouse`, `AntMed Lot`, `AntMed Stock Entry` |
| M04 | Giao phòng mổ + SLA giờ ca | **xây mới** | M01, M02, M03 | M06, M09, M10 | `AntMed Delivery` (workflow), `AntMed OR Schedule` |
| M05 | Bộ dụng cụ mượn + tiệt khuẩn | **xây mới hoàn toàn** | M01, M03(kho) | M10 | `AntMed Instrument Set` (workflow 7 trạng thái), `AntMed Sterilization` |
| M06 | Chứng từ CO/CQ + HĐĐT | xây mới + tích hợp | M02, M03, M04 | M09, M13 | `AntMed Document`, `AntMed E-Invoice` |
| M07 | CSKH Bác sỹ + GPS check-in | tùy biến | M01 | M10 | `AntMed Doctor Visit`, `AntMed Care Note` |
| M08 | Pipeline → Tender → Won | có (Lead/Deal gốc) | M01 | M02 | mở rộng `CRM Lead`/`CRM Deal` + `AntMed Tender` |
| M09 | Đơn hàng, Công nợ, AR | một phần | M02, M04 | M10, M11 | `AntMed Order`, `AntMed AR Entry` |
| M10 | KPI lai (bán+giao+mượn) | xây mới | M04, M05, M09 | M11 | `AntMed KPI`, `AntMed Commission` |
| M11 | Dashboard điều hành | có khung | M02,M04,M09,M10 | — | report + dashboard config |
| M12 | Mobile PWA offline-first | thường phải xây | M01,M04,M05 | — | (FE PWA layer) |
| M13 | Integrations (HĐĐT/Zalo/SMS/Bank/HIS) | một phần | M06, M09 | — | settings + connectors |

```
M14(RBAC/audit) ─┐
M01(Customer) ───┼─► M02(Contract) ─► M04(Delivery) ─► M06(Docs/HĐĐT) ─► M13(Integr)
                 │        │               │     │
M03(Inventory) ──┴────────┘               │     └─► M09(Orders/AR) ─► M10(KPI) ─► M11(Dashboard)
        └─► M05(Instrument Loan) ─────────┘
M01 ─► M07(Doctor Care)        M01 ─► M08(Pipeline) ─► M02
M12(Mobile) & M11 = cross-cutting / aggregate (sau cùng)
```

---

## 3. Implementation Waves (thứ tự theo phụ thuộc)

> Mỗi module = nhiều **vertical slice**; mỗi slice = 1 vòng factory (BA spec → BE+FE → QA → user). Ước lượng vòng là *tương đối*, không phải cam kết thời gian.

| Wave | Mục tiêu | Module/slice | Song song? | ~Vòng |
|---|---|---|---|---|
| **W0 — Đóng nền** | Hoàn tất M01 + nền RBAC/route | finish M01 slice (reload+pixel+commit) · role VI (DEC-A) · tách route AntMed (DEC-B) · audit log skeleton (M14-lite) | tuần tự | 3–4 |
| **W1 — Master data & catalog** | Dữ liệu gốc để vận hành | M01 full (child: khoa/người-quyết-định/preferences) · **M03 catalog-lite** (`AntMed Item`+`Lot`+CO/CQ) · **M02** (Contract+Quota) | M01-full ‖ M03 ‖ M02 (sau M01 core) | 8–11 |
| **W2 — Chuỗi vận hành lõi** | Giao hàng có chứng từ + công nợ | **M04** Giao phòng mổ (workflow+SLA) → **M06** Chứng từ/HĐĐT → **M09** Đơn/AR | tuần tự (chuỗi phụ thuộc) | 12–16 |
| **W3 — Đặc thù AntMed** | Khác biệt cạnh tranh | **M05** Bộ dụng cụ mượn + tiệt khuẩn (workflow 7 trạng thái) · **M07** CSKH bác sỹ | W3 ‖ với W2 (sau W1) | 8–11 |
| **W4 — Tăng trưởng & kiểm soát** | Phễu + chỉ số + tích hợp + siết bảo mật | **M08** Pipeline/Tender · **M10** KPI · **M11** Dashboard · **M13** Integrations · **M14 full** (2FA, data-scope BR-13, audit hash-chain hoàn chỉnh) · **M12** Mobile PWA | nhiều nhánh ‖ | 14–20 |

**Tổng ước lượng thô:** ~45–60 vòng factory (nhiều tuần). Chạy theo **mẻ nhỏ** (vd 2–4 vòng/mẻ), review giữa mẻ — đúng kỷ luật "nhỏ → review → mở rộng".

---

## 4. Parallel vs Sequential

- **Tuần tự bắt buộc:** W0 → W1 → (chuỗi M02→M04→M06→M09 trong W2).
- **Song song an toàn:** M01-full ‖ M02 ‖ M03 (W1); M05 ‖ M07 (W3) chạy song song với W2; trong W4 các nhánh M08/M10/M11/M13/M12 phần lớn độc lập.
- **Cross-cutting (bồi liên tục mỗi wave, không để cuối):** M14 RBAC + data-scope BR-13 + audit; i18n tiếng Việt; no-regression CRM gốc.

---

## 5. Risks & Mitigations

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| **Không có ERPNext** (D1) | 🔴 cao | Chốt D1 trước W1; khuyến nghị native-lite, chỉ xây phần dùng tới (FIFO/HSD/CO-CQ) |
| App riêng `apps/antmed_crm` fork từ Frappe CRM → khó merge upstream Frappe CRM | 🟠 vừa | Giữ AntMed **additive** (route/hook/doctype prefix riêng), không sửa core; ghi ADR mọi chỗ đụng core (vd `CRM_ALLOWED_ROLES`) |
| Reload gunicorn `--preload` (HARD-STOP, bench dùng chung) | 🟠 vừa | Gom thay đổi .py trước 1 lần reload; thêm **CI live-HTTP smoke** tách "run-tests xanh" vs "HTTP live" |
| Scope 14 module khổng lồ | 🟠 vừa | Vertical slice + factory; checkpoint mỗi wave; KHÔNG big-bang |
| Data-scope BR-13 hoãn (mọi NV thấy mọi BV) | 🟡 thấp | Giữ invariant `count==rows` ngay; bật `permission_query_conditions` ở W4/M14 không vỡ contract |
| Data test lẫn production (`_SEC-H*`) | 🟡 thấp | Purge ở W0; seed test có prefix + teardown bắt buộc |
| Workflow phức tạp (M04 SLA, M05 7-trạng-thái) | 🟠 vừa | Chốt D2 (Frappe Workflow); state machine qua fixtures `workflow.json` + smoke test mỗi transition |
| Compliance VTYT (CO/CQ/ĐKLH/HĐĐT) sai = pháp lý | 🟠 vừa | M06 có BA gate domain (6-câu-hỏi feasibility) + test compliance gate trước khi cho giao |

---

## 6. Verification Checkpoints

- **Mỗi slice:** DoD §6 SPEC — BE run-tests `Ran N OK` + FE vitest + build + (sau reload) pixel verify + no-regression.
- **Cuối mỗi Wave:** integration smoke chuỗi nghiệp vụ + persona UAT (factory Bước 6 user) + commit mẻ (sau USER duyệt).
- **Cuối mỗi Phase (roadmap):** demo end-to-end vòng đời (lead→giao→AR; mượn→tiệt khuẩn→trả).

---

## 7. Open Questions (cần human trước khi Implement)

1. **D1 — ERPNext:** chọn (A) cài ERPNext / (B) native-lite *(khuyến nghị)* / (C) hybrid? ← **chặn W1**.
2. **D2 — Workflow engine:** Frappe Workflow gốc *(khuyến nghị)* hay reuse `workflowcore`?
3. **Thứ tự ưu tiên:** đồng ý waves W0→W4 như trên, hay muốn kéo module nào lên sớm (vd M05 bộ mượn là điểm nhấn — lên W2)?
4. **Cadence factory:** mỗi mẻ mấy vòng trước khi dừng review? (đề xuất 2–4).
5. **Commit/credential:** khi nào commit + push GitHub? Cấp user/mật khẩu test để pixel-verify?
6. Xác nhận lại **role-name tiếng Việt** (đánh đổi: name VI thành định danh `frappe.get_roles()`).
