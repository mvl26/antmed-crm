# M09 — Đơn hàng, Công nợ & Doanh thu (AR) (Core Doc)

| Mục | Giá trị |
|---|---|
| Module folder | `antmed_crm/antmed/` (module Frappe **`AntMed`**, scrubbed = `antmed`) — DocType M09 đặt tại `antmed_crm/antmed/doctype/antmed_order/`, `antmed_crm/antmed/doctype/antmed_ar_entry/`, … |
| Code path BE | `antmed_crm/antmed/doctype/<snake>/` + endpoint `antmed_crm/api/antmed/orders_ar.py` (đường gọi `antmed_crm.api.antmed.orders_ar.<fn>`) |
| Module hooks (BR) | `doc_events` wiring trong `antmed_crm/hooks.py` → `antmed_crm/antmed/<module hooks>.py` (vd `antmed_crm.antmed.orders_ar_hooks.*`) |
| FE pages | `frontend/src/pages/Antmed*` + route `/antmed/orders`, `/antmed/ar`, `/antmed/ar/:hospital` |
| Wave (PLAN) | **W2 — Chuỗi vận hành lõi** (sau M04 → M06 → **M09**) |
| Role chính (VI) | `Kế toán` **[PLANNED — chưa có trong fixture]**, `Quản lý` (override BR-14) · phụ: `NV kinh doanh` (xem AR theo tuyến), `System Manager` |
| Phụ thuộc | **M02** (Hợp đồng/Quota — đơn giá, hạn TT), **M04** (Giao phòng mổ — DO tiêu hao thực) |
| Cấp dữ liệu cho | **M10** (KPI doanh thu/hoa hồng), **M11** (Dashboard công nợ/AR aging) |
| Trạng thái | **PLANNED — chưa code** cho S1–S5 (DocType `AntMed Order`/AR). **Slice M09-1 (widget Hoa hồng NV flat-rate, §7bis) = READY TO BUILD** — KHÔNG DocType, endpoint `antmed_crm.api.antmed.finance.commission_summary` |
| Cập nhật | 2026-06-18 |

> **Trạng thái: [PLANNED — chưa code]**
> Toàn bộ schema/API/workflow/BR dưới đây là **DESIGN (đề xuất)** — *spec-before-code*, factory sẽ build từ tài liệu này. Chưa có DocType `AntMed Order`/`AntMed AR Entry` nào tồn tại trên site `miyano`. Mọi đề xuất được ground từ: PLAN component-inventory (dòng M09), `AntMed_CRM_Modules.md §9`, reference scaffold `m09_orders_ar/` (bản app-riêng cũ — đã **adapt** `AM `→`AntMed `, ERPNext-reuse→native-lite), `AntMed_CRM_UI_Design.md §6` (màn Kế toán), và `m01_customer360.md` (house style + hợp đồng API Frappe-standard).

---

## 1. Overview

M09 là **mắt xích cuối của chuỗi vận hành lõi** (W2: M04 Giao phòng mổ → M06 Chứng từ/HĐĐT → **M09 Đơn/AR**). Nó biến **vật tư đã tiêu hao thực tế** tại phòng mổ (ghi nhận ở M04 DO — "vật tư đã dùng vs vật tư trả lại") thành **đơn bán** → **công nợ phải thu (AR)** có tuổi nợ, rồi cấp số liệu doanh thu cho M10 (KPI/hoa hồng) và M11 (Dashboard điều hành).

Theo `AntMed_CRM_Modules.md §9` (mô tả nghiệp vụ ground-truth):
- **Đơn bán từ phiếu giao thực tế tiêu hao** (Module 4) — không xuất theo SL yêu cầu mà theo SL đã dùng.
- **Hóa đơn ↔ Công nợ**: tuổi nợ, hạn thanh toán theo HĐ, **nhắc thu tự động**.
- **Đối soát thu chi** với kế toán; **xuất file** cho phần mềm kế toán (MISA/Fast/Bravo).
- **KPI doanh thu** theo bác sỹ / bệnh viện / NV kinh doanh / nhóm vật tư (cấp cho M10).

Điểm đặc thù AntMed vs CRM bán hàng thuần: (a) đơn **derive từ DO tiêu hao** (M04), không nhập tay; (b) **BR-14 chặn đơn mới khi công nợ BV vượt ngưỡng**; (c) **AR aging 4 khoảng** 0–30 / 31–60 / 61–90 / >90 (UI heatmap); (d) **không dùng ERPNext** — AR ledger là DocType native `AntMed AR Entry` (D1 native-lite).

### User stories
- *Kế toán* mở **Bảng công nợ**, xem BV theo tuổi nợ (4 khoảng heatmap), bấm **"Gửi nhắc"** / **"Ghi nhận thu"** / **"Tạo biên bản đối chiếu"** (UI §6.2).
- *Kế toán* cuối kỳ bấm **"Xuất kế toán"** → sinh file MISA/Fast/Bravo cho khoảng ngày đã chọn, log lại lần xuất.
- *NV kinh doanh / Quản lý* khi tạo/duyệt đơn cho 1 BV bị **chặn** (BR-14) nếu công nợ BV đó vượt ngưỡng; chỉ `Quản lý` được override.

### 6 câu hỏi domain — feasibility check (BA Bước 2)

| # | Câu hỏi | Trả lời cho M09 |
|---|---|---|
| 1 | **CRM stage?** | Giai đoạn **sau giao hàng** — đơn bán + công nợ + doanh thu. Đầu vào là DO đã bàn giao (M04). |
| 2 | **Ràng buộc hợp đồng/quota?** | **CÓ (gián tiếp)**: đơn giá lấy theo HĐ trúng thầu (M02); BR-14 chặn đơn theo **công nợ** (khác BR-06 chặn theo quota của M02/M04). M09 KHÔNG re-check quota (đã làm ở M04). |
| 3 | **Actor là bệnh viện hay bác sỹ?** | **Bệnh viện** (pháp nhân) cho AR/công nợ + xuất hóa đơn; **bác sỹ/NV** chỉ là chiều phân tích doanh thu (cấp M10). |
| 4 | **Nghĩa vụ chứng từ / HĐĐT?** | HĐĐT **thuộc M06** — M09 KHÔNG phát hành HĐĐT. M09 chỉ tham chiếu hóa đơn/chứng từ M06 để dựng AR (link `e_invoice`/`document`), và xuất **file kế toán** (MISA/Fast/Bravo) ≠ HĐĐT. |
| 5 | **Truy vết lot / thu hồi?** | Không trực tiếp. Lot-trace ở M03/M06; M09 chỉ giữ link tới DO/Order để truy ngược nếu cần. |
| 6 | **Hậu quả nếu data sai?** | **Cao** — sai công nợ/doanh thu ảnh hưởng tiền + kế toán + KPI lương. ⇒ AR ledger phải **bất biến sau submit** (docstatus), audit (M14 hash-chain) mọi thao tác ghi thu, và `count == rows` cho list để KHÔNG rò rỉ/thiếu AR. |

---

## 2. DocTypes (native-lite, [PLANNED])

> **Adapt từ scaffold** `m09_orders_ar/doctype/` (app-riêng cũ): `AM `→`AntMed `; `Customer`→`AntMed Hospital`; `Sales Invoice`/`Sales Order`/`Payment Entry`→**native** `AntMed Order`/`AntMed AR Entry`/`AntMed Payment`; module `M09 Orders AR`→`AntMed`; role `AM System Admin`/`AM CEO`→`Kế toán`/`Quản lý`. Field-set = **tối thiểu** theo acceptance; field mở rộng = backlog.

| DocType | Loại | Field chính (ĐỀ XUẤT — ground scaffold + Modules §9) | Naming series / autoname | Submittable |
|---|---|---|---|---|
| **`AntMed Order`** | txn (lõi) | `naming_series`, `hospital` (Link `AntMed Hospital`, reqd), `contract` (Link `AntMed Contract`, M02), `delivery` (Link `AntMed Delivery`, M04 — nguồn tiêu hao), `order_date`, `due_date` (hạn TT theo HĐ), `items` (child `AntMed Order Item`), `total_amount` (Currency, sum line), `status` (Select), `sales_rep` (Link User/NV — chiều KPI) | `AntMed Order` series **`AM-SO-.YYYY.-.#####`** | **1** (docstatus: Draft→Submitted) |
| **`AntMed Order Item`** | child | `item` (Link `AntMed Item`, M03), `lot` (Link `AntMed Lot`), `qty` (SL **đã tiêu hao** từ DO), `rate` (đơn giá HĐ trúng thầu — M02), `amount` (= qty×rate), `item_group` (nhóm VT — chiều KPI M10) | (child) | — |
| **`AntMed AR Entry`** | txn / ledger | `naming_series`, `hospital` (Link `AntMed Hospital`), `order` (Link `AntMed Order`), `e_invoice` (Link `AntMed E-Invoice`, M06 — tùy chọn), `posting_date`, `due_date`, `entry_type` (Select: `Ghi nợ`/`Ghi có`), `debit`, `credit`, `outstanding_amount` (Currency), `status` (Select) | `AM-AR-.YYYY.-.#####` | **1** (ledger bất biến sau submit) |
| **`AntMed Payment`** | txn | `naming_series`, `hospital`, `payment_date`, `amount` (Currency), `mode` (Select: `Chuyển khoản`/`Tiền mặt`), `against_ar` (child `AntMed Payment Allocation`: `ar_entry`+`allocated`), `bank_txn_id` (đối soát) | `AM-PAY-.YYYY.-.#####` | **1** |
| **`AntMed Payment Reminder`** | log/txn | `naming_series` **`PR-.YYYY.-.#####`**, `ar_entry` (Link `AntMed AR Entry` — **adapt** từ `sales_invoice`), `hospital`, `due_date`, `days_overdue` (Int), `channel` (Select `Email`/`Zalo`/`SMS`), `sent_at`, `escalation_level` (Int), `status` (Select `Scheduled`/`Sent`/`Escalated`/`Resolved`) | `PR-.YYYY.-.#####` | **1** (scaffold: `is_submittable=1`) |
| **`AntMed Debt Threshold Block`** | master/config | `hospital` (Link `AntMed Hospital`, **unique** — autoname `field:hospital`, **adapt** từ `Customer`), `threshold_vnd` (Currency), `current_ar_vnd` (Currency), `blocked_at` (Datetime), `unblock_reason` (Long Text), `unblocked_by` (Link User) | `field:hospital` | 0 |
| **`AntMed Bank Reconciliation Match`** | log | `bank_txn_id` (Data, reqd), `payment` (Link `AntMed Payment` — **adapt** từ `Payment Entry`), `matched_at` (Datetime), `match_score` (Percent) | `Random` (hash) | 0 |
| **`AntMed Accounting Export Log`** | log | `naming_series` **`EXP-.YYYY.-.#####`**, `target` (Select `MISA`/`Fast`/`Bravo`, reqd), `date_from`, `date_to`, `file_xml` (Attach), `status` (Select `Pending`/`Success`/`Failed`) | `EXP-.YYYY.-.#####` | 0 |

> **Ghi chú adapt quan trọng (native-lite, D1):**
> - Scaffold gốc reuse ERPNext `Sales Invoice`/`Sales Order`/`Payment Entry`/`Customer` — **bỏ hết**. M09 tự dựng AR ledger native: `AntMed AR Entry` (ghi nợ khi đơn submit, ghi có khi thu) + `AntMed Payment`. Tuổi nợ tính từ `due_date` + `outstanding_amount` bằng code (KHÔNG kế thừa accounting ERPNext).
> - `AntMed Debt Threshold Block` giữ làm **master cấu hình ngưỡng/BV** (1 BV ↔ 1 ngưỡng, autoname `field:hospital`) **kiêm** nhật ký lần khóa/mở. Phương án thay thế *(cần khảo sát)*: chuyển `threshold_vnd` thành field trên `AntMed Hospital` (giống scaffold hooks đọc `debt_threshold` trên `AM Hospital Profile`) → đơn giản hơn nhưng mất nhật ký khóa/mở. **Đề xuất giữ DocType riêng**.
> - `[UNVERIFIED]` ranh giới `AntMed Order` vs `AntMed AR Entry`: có thể gộp (đơn = chứng từ công nợ) hay tách (đơn → nhiều AR theo đợt thanh toán). Đề xuất **tách** (ledger riêng) để hỗ trợ thu nhiều đợt + biên bản đối chiếu; chốt lại ở slice S2.
> - `item_group`/`sales_rep` là **chiều phân tích cho M10** (doanh thu theo nhóm VT/NV/BV/bác sỹ) — `[cần khảo sát]` mô hình nhóm VT (Link `AntMed Item Group`?) khi M03 chốt danh mục.

---

## 3. Workflow

M09 dùng **docstatus** (Frappe-native submit) cho các txn, và **một Workflow nhẹ** cho vòng đời đơn — đề xuất qua fixtures `antmed_crm/fixtures/workflow.json` (D2 Frappe-native, KHÔNG `workflowcore`). State field = `status` (hoặc `workflow_state`), giá trị **tiếng Việt**.

### `AntMed Order` — vòng đời đơn (đề xuất)

| State (VI) | docstatus | Mô tả | Transition → | Role được phép |
|---|---|---|---|---|
| `Nháp` | 0 | Đơn vừa dựng từ DO tiêu hao, chưa chốt | → `Chờ duyệt` | `NV kinh doanh`, `Kế toán` |
| `Chờ duyệt` | 0 | Chờ kiểm tra công nợ (BR-14) + đơn giá HĐ | → `Đã chốt` / → `Bị chặn` | `Kế toán`, `Quản lý` |
| `Bị chặn` | 0 | BR-14: công nợ BV vượt ngưỡng → không cho submit | → `Đã chốt` (chỉ khi `Quản lý` override/mở khóa) | `Quản lý` |
| `Đã chốt` | 1 | Submit → sinh `AntMed AR Entry` (ghi nợ) | → `Đã hủy` | `Kế toán`, `Quản lý` |
| `Đã hủy` | 2 | Cancel (đảo AR) | — | `Quản lý` |

> `AntMed AR Entry`/`AntMed Payment`/`AntMed Payment Reminder` dùng **docstatus** đơn thuần (Draft/Submitted/Cancelled) — KHÔNG cần workflow đa trạng thái. `AntMed Payment Reminder.status` (`Scheduled`/`Sent`/`Escalated`/`Resolved`) là **nhãn tiến trình do scheduler/handler set**, không phải workflow có transition do người dùng bấm.
> `AntMed Debt Threshold Block` / `Bank Reconciliation Match` / `Accounting Export Log` = **không có workflow** (master/log).

---

## 4. Business Rules

| BR | Mô tả | Nơi enforce (ĐỀ XUẤT) | Trạng thái |
|---|---|---|---|
| **BR-14** | **Chặn đơn khi công nợ BV vượt ngưỡng.** Khi submit/validate `AntMed Order`: tính tổng `outstanding_amount` các `AntMed AR Entry` (docstatus=1) của BV; nếu ≥ `threshold_vnd` (từ `AntMed Debt Threshold Block` của BV) → `frappe.throw`. Chỉ `Quản lý` được vượt. | `doc_events`: `AntMed Order` → `validate` → `antmed_crm.antmed.orders_ar_hooks.check_debt_threshold_block` | **[PLANNED]** — scaffold có `check_debt_threshold_block` (đọc `AM Hospital Profile.debt_threshold`, override `AM CEO`); **adapt**: native AR sum thay `Sales Invoice`, role override `Quản lý` thay `AM CEO`. |
| BR-13 | **Data-scope**: NV chỉ thấy AR/đơn của BV được giao. | `permission_query_conditions` cho `AntMed Order`/`AntMed AR Entry` (wiring ở M14/W4) — giữ invariant `count == rows` ngay từ M09. | **[ROADMAP — M14]** (ADR-M01-05) |
| BR-10 | **Audit hash-chain** mọi thao tác ghi thu / mở khóa công nợ / xuất kế toán. | M14 `audit.write_log` gọi từ handler `record_payment`, `unblock_hospital`, `export_accounting`. | **[ROADMAP — M14]** |
| BR-12 | **2FA** cho thao tác nhạy cảm (mở khóa công nợ BR-14, ghi nhận thu lớn). | M14 `audit.require_2fa_and_log` (gate trước override). | **[ROADMAP — M14]** |

> **Invariant kỹ thuật (gate, không phải BR nghiệp vụ):** mọi list endpoint AR/đơn giữ **`count == rows`** (đếm qua `get_list(pluck=…, limit_page_length=0)`), để khi M14 bật `permission_query_conditions` không vỡ contract.
> Mã lỗi nghiệp vụ tiếng Việt, vd: `frappe.throw(_("BR-14: BV {0} có công nợ {1:,.0f} vượt ngưỡng {2:,.0f}.").format(...))`.

---

## 5. API

> File: `antmed_crm/api/antmed/orders_ar.py`. Mọi hàm `@frappe.whitelist(methods=["GET"|"POST"])`, **type-annotated** (`antmed_crm/hooks.py:28 require_type_annotated_api_methods = True`), trả **RAW dict/list** (KHÔNG `_ok/_err`/envelope). Lỗi nghiệp vụ = `frappe.throw(_("BR-XX: …"))`. List giữ **count == rows**.

| Endpoint (`antmed_crm.api.antmed.orders_ar.<fn>`) | Verb | Mô tả |
|---|---|---|
| `list_orders` | GET | List đơn `{data, total_count}`; filter `hospital`/`status`/khoảng ngày. **count == rows** khi không phân trang. |
| `get_order` | GET | Chi tiết 1 đơn + child items + link DO/HĐ/AR. `frappe.has_permission(... , doc=name)` → throw `PermissionError`. |
| `create_order_from_delivery` | POST | **Dựng đơn từ DO tiêu hao** (M04): nhận `delivery`, copy line theo SL đã dùng, set đơn giá HĐ (M02). Chạy BR-14 ở validate. |
| `submit_order` | POST | Submit đơn (docstatus 0→1) → sinh `AntMed AR Entry` ghi nợ. BR-14 chặn nếu vượt ngưỡng. |
| `get_ar_aging` | GET | **AR aging theo BV**: trả list BV + 4 cột `b_0_30`/`b_31_60`/`b_61_90`/`b_90_plus` + `total_outstanding`. Nguồn cho UI heatmap §6.2 + Dashboard M11. **count == rows** = số BV có công nợ. |
| `get_ar_ledger` | GET | Sổ chi tiết AR 1 BV: timeline hóa đơn/đơn ↔ thu ↔ còn lại (UI "Click BV → chi tiết"). |
| `record_payment` | POST | Ghi nhận thu: tạo `AntMed Payment` + phân bổ vào `AntMed AR Entry`, cập nhật `outstanding_amount`. Audit (M14). |
| `send_reminder` | POST | Gửi nhắc thu thủ công cho 1 BV/AR → tạo `AntMed Payment Reminder` (kênh Email/Zalo/SMS). |
| `unblock_hospital` | POST | `Quản lý` mở khóa BR-14 cho BV: ghi `unblock_reason`/`unblocked_by` vào `AntMed Debt Threshold Block`. 2FA (M14). |
| `export_accounting` | POST | Xuất file kế toán MISA/Fast/Bravo cho khoảng ngày → sinh file + ghi `AntMed Accounting Export Log` (`target`, `date_from/to`, `file_xml`, `status`). |

> **Scheduler (không phải whitelist):** `antmed_crm.antmed.orders_ar_scheduler.send_payment_reminders` — chạy **daily** (khai trong `scheduler_events` của `antmed_crm/hooks.py`). **Adapt** từ scaffold `scheduler.py`: quét `AntMed AR Entry` (thay `Sales Invoice`) có `outstanding_amount>0` và `DATEDIFF(today, due_date) IN (0,7,30)`; chống trùng theo `(ar_entry, days_overdue)`; set `escalation_level` 1/2/3. **[UNVERIFIED]** tích hợp kênh gửi thật (Email/Zalo/SMS) = M13.

---

## 6. Integration (doc_events vào/ra theo DAG)

**Vào M09 (upstream):**
- **M04 `AntMed Delivery` (DO) → M09 đơn**: khi DO bàn giao hoàn tất (ghi nhận tiêu hao thực), `doc_events` `AntMed Delivery.on_submit` → lazy-import handler M09 dựng/gợi ý `AntMed Order` (truyền **PK** `delivery.name`, KHÔNG truyền object). Có thể bán tự động (NV bấm `create_order_from_delivery`) thay vì auto cứng — `[cần khảo sát]` mức tự động.
- **M02 `AntMed Contract`/`AntMed Quota Item`**: đọc đơn giá trúng thầu + hạn TT khi dựng line đơn (lazy `frappe.db.get_value` theo PK BV/HĐ). M09 **không** sửa M02.
- **M06 `AntMed E-Invoice`/`AntMed Document`**: AR entry link tới hóa đơn đã phát hành (M06) để timeline công nợ đầy đủ; M09 chỉ **đọc** (không phát hành HĐĐT).

**Trong M09 (doc_events nội bộ):**
- `AntMed Order.validate` → `check_debt_threshold_block` (BR-14).
- `AntMed Order.on_submit` → sinh `AntMed AR Entry` (ghi nợ) + cập nhật `current_ar_vnd` trên `AntMed Debt Threshold Block`.
- `AntMed Payment.on_submit` → ghi có vào AR entry, giảm `outstanding_amount`, cập nhật `current_ar_vnd`.

**Ra khỏi M09 (downstream):**
- **→ M10 (KPI/hoa hồng)**: doanh thu theo `sales_rep`/`hospital`/`item_group`/bác sỹ — M10 đọc từ `AntMed Order`/`AntMed AR Entry` (PK, không event nặng).
- **→ M11 (Dashboard)**: `get_ar_aging` cấp số liệu công nợ 4 khoảng cho widget "Cảnh báo điều hành" (UI §1.2) + Dashboard Kế toán.
- **→ M13 (Integrations)**: kênh gửi nhắc thu (Email/Zalo/SMS), đối soát ngân hàng (`AntMed Bank Reconciliation Match`), xuất file kế toán — connector thật thuộc M13.

> Nguyên tắc: handler cross-module **lazy-import** + **truyền PK** (string `name`), tránh import vòng giữa module; gate compliance (CO/CQ/HĐĐT) đã enforce ở M04/M06 trước khi tới M09 — M09 không re-gate compliance.

---

## 7. UI

> Vue 3 + frappe-ui SPA. Gọi đúng `antmed_crm.api.antmed.orders_ar.*` qua `createResource`/`createListResource`. Route mới **APPEND** vào `frontend/src/router.js` (lazy). KHÔNG đụng route CRM gốc. Nhãn 100% tiếng Việt qua `__()`; tiền VND `1.234.567 ₫`, số `tabular-nums`. Persona chính = **Kế toán** (desktop-first — UI §6).

### Routes (THÊM mới — lazy)

| path | name | component | mô tả | Role dùng |
|---|---|---|---|---|
| `/antmed/orders` | `AntmedOrders` | `pages/AntmedOrders.vue` | List đơn bán (filter BV/trạng thái/kỳ) | Kế toán, Quản lý, NV KD |
| `/antmed/orders/:name` | `AntmedOrderDetail` | `pages/AntmedOrderDetail.vue` | Chi tiết đơn + line tiêu hao + link DO/HĐ/AR | Kế toán, Quản lý |
| `/antmed/ar` | `AntmedAR` | `pages/AntmedAR.vue` | **Bảng công nợ** — BV × tuổi nợ 0–30/31–60/61–90/>90 (heatmap đỏ dần); cột hành động "Gửi nhắc"/"Tạo biên bản đối chiếu"/"Ghi nhận thu" | Kế toán |
| `/antmed/ar/:hospital` | `AntmedARDetail` | `pages/AntmedARDetail.vue` | Chi tiết 1 BV: timeline hóa đơn → thanh toán → còn lại + file biên bản đối chiếu | Kế toán |
| `/antmed/ar/export` | `AntmedAccountingExport` | `pages/AntmedAccountingExport.vue` | Xuất kế toán MISA/Fast/Bravo theo kỳ + lịch sử export | Kế toán |

> Ground @ `AntMed_CRM_UI_Design.md §6` (Kế toán): sidebar *Hóa đơn / Công nợ phải thu / Đối soát ngân hàng / Hoa hồng NV / Xuất kế toán (MISA/Fast)*; §6.2 bảng công nợ tuổi nợ 4 khoảng heatmap + 3 nút hành động + click BV → chi tiết; §9 hàng "9. Đơn hàng & Công nợ → Bảng công nợ, Hóa đơn → Kế toán, CEO". Hoa hồng NV (§6.3) = bản ĐẦY ĐỦ (tier × nhóm VT × NV, khóa kỳ) thuộc **M10**; **M09-1 dưới đây** chỉ là **widget tổng quan flat-rate** mở persona Kế toán (xem §7bis).

---

## 7bis. Slice M09-1 — Widget "Hoa hồng NV" (mockup F2, persona Kế toán) — [READY TO BUILD]

> ⚠️ **Self-Correction / Ground-truth path (đọc TRƯỚC khi build).** Repo này là **app riêng `antmed_crm`** (KHÔNG in-place `crm`). Các path `crm/antmed/…` và `crm.api.antmed.*` trong §1–§10 (viết theo template system-prompt mặc định) **KHÔNG đúng repo này** — phần §7bis dưới đây dùng đường thật đã verify trong code: BE = `antmed_crm/api/antmed/<module>.py`, URL resource = `antmed_crm.api.antmed.<module>.<fn>`, test = `antmed_crm/tests/test_antmed_<module>.py`, FE data layer = `frontend/src/data/antmed.js`. Khi build slice khác của M09, áp cùng quy ước này.

### 7bis.1 Scope (Boundaries)

Mục tiêu vòng 26: mở **persona Kế toán** bằng màn MỚI `/antmed/finance/commission` (mockup F2 "Hoa hồng Nhân viên" — header card pair), wire **endpoint MỚI** `finance.commission_summary`. Widget gồm **2 thẻ header**: trái = "Tổng hoa hồng kỳ" (số tiền), phải = "Quy tắc kỳ <period_label>" (list quy tắc flat-rate).

- **Always:**
  - Hoa hồng kỳ = `round(SUM(deal_value × FLAT_RATE))` trên **CRM Deal** có `status` thuộc **type 'Won'** & `closed_date` trong **tháng hiện tại** (`[get_first_day .. get_last_day]` của `nowdate()`).
  - Đọc deal qua `frappe.get_list(... limit_page_length=0)` (tôn trọng DocPerm + `permission_query_conditions` BR-13) — gộp ở Python. KHÔNG raw SQL / KHÔNG f-string injection.
  - Endpoint trả **RAW dict** (KHÔNG envelope `_ok/_err`, KHÔNG `MSG.*`). FE đọc `r.data.<key>` (KHÔNG `r.data.data`).
  - Fail-closed BR-13: thiếu read-perm CRM Deal → `get_list` raise `PermissionError` → trả `_empty_commission()` (mọi số = 0, `rules` GIỮ NGUYÊN), KHÔNG 500.
  - FLAT_RATE + danh sách `rules` = **hằng số module** (constant trong `finance.py`) — KHÔNG đọc DocType.
- **Never:**
  - KHÔNG tạo DocType mới (`AntMed Commission`/`AntMed Commission Rule` = **[ROADMAP — M10]**, KHÔNG build ở slice này).
  - KHÔNG tạo module mới (đặt trong M09 / file `finance.py`).
  - KHÔNG per-category bonus engine, KHÔNG tier table (đó là M10 `compute_commission` BR-M10-04).
  - KHÔNG đổi stub cũ `/finance/commission` thành … (xem 7bis.5 — giữ NGUYÊN, no-regression).
  - KHÔNG hardcode số liệu mock trong UI production; KHÔNG hardcode JSX `rules` trong template (render từ data thật).

### 7bis.2 DocTypes

**KHÔNG có DocType mới.** Nguồn dữ liệu = **`CRM Deal`** (đọc, không sửa) — fields `deal_value` (Currency), `status` (Link → `CRM Deal Status`), `closed_date` (Date), `deal_owner` (Link → User). Phân loại Won qua **`CRM Deal Status`** (field `type` Select, giá trị `Won` — đã verify `crm_deal_status.json`).

> `flat_rate_pct` + `rules` là tham số **flat-rate phẳng** đặt cứng trong code (KHÔNG `AntMed Commission Rule`). Khi M10 build engine tier đầy đủ → endpoint này có thể đọc `AntMed Commission Rule` active; tới lúc đó là **[ROADMAP — M10]**, đánh dấu nợ kỹ thuật.

### 7bis.3 API — `antmed_crm/api/antmed/finance.py` (FILE MỚI)

| Endpoint (`antmed_crm.api.antmed.finance.<fn>`) | Verb | Mô tả |
|---|---|---|
| `commission_summary(period: str \| None = None) -> dict` | GET | Tổng hoa hồng + quy tắc kỳ (flat-rate) cho widget F2. `period` tùy chọn (mặc định = tháng hiện tại; reserved cho chọn kỳ — slice này chỉ cần default đúng). Type-annotated (require_type_annotated_api_methods). |

**Shape RAW dict trả về** (key ổn định — Hyrum; FE đọc `r.data.<key>`, KHÔNG `.data.data`):

```python
{
  "total_commission": float,   # round(SUM(deal_value × FLAT_RATE)) deal Won closed_date trong kỳ. Kỳ rỗng → 0 (KHÔNG None)
  "total_revenue":    float,   # SUM(deal_value) deal Won closed_date trong kỳ. Kỳ rỗng → 0
  "rep_count":        int,     # số deal_owner PHÂN BIỆT có ≥1 deal Won trong kỳ. Kỳ rỗng → 0
  "group_count":      int,     # = len(rules) (số nhóm vật tư trong quy tắc kỳ — flat-rate hiện 1 nhóm)
  "period_label":     str,     # "T<m>/<yyyy>" (vd "T6/2026") — KHỚP regex 'T\d{1,2}/\d{4}'
  "flat_rate_pct":    float,   # = FLAT_RATE × 100 (vd 0.05 → 5.0) — % hiển thị
  "currency":         "VND",
  "rules": [                   # list mô tả quy tắc kỳ (render thẻ phải) — KHÔNG hardcode trong template FE
    {"label": str, "rate_pct": float},   # vd {"label": "Hoa hồng phẳng (toàn nhóm vật tư)", "rate_pct": 5.0}
  ],
}
```

**Hằng số module (đặt đầu `finance.py`):**

```python
COMMISSION_FLAT_RATE = 0.05   # 5% — flat-rate phẳng (cần khảo sát baseline thực tế với Kế toán)  [UNVERIFIED]
COMMISSION_CURRENCY = "VND"
# rules: SSoT cho thẻ "Quy tắc kỳ" — group_count = len(COMMISSION_RULES). Label tiếng Việt.
COMMISSION_RULES = [
    {"label": "Hoa hồng phẳng (toàn nhóm vật tư)", "rate_pct": COMMISSION_FLAT_RATE * 100},
]
COMMISSION_SUMMARY_KEYS = ("total_commission", "total_revenue", "rep_count", "group_count",
                           "period_label", "flat_rate_pct", "currency", "rules")
```

> ⚠️ `COMMISSION_FLAT_RATE = 5%` là **[UNVERIFIED — cần khảo sát baseline]** với Kế toán AntMed (chưa có chứng từ chốt %). Build dùng 5% làm placeholder hợp lý; ghi nợ khảo sát. KHÔNG để engine suy ra % từ nguồn khác.

**Thuật toán `commission_summary` (mirror `contract.monthly_revenue` + `sales_team.team_roster`):**

1. `this_month = getdate(nowdate())`; `month_start = str(get_first_day(nowdate()))`; `month_end = str(get_last_day(nowdate()))`. `period_label = f"T{this_month.month}/{this_month.year:04d}"`.
2. `try: deals = frappe.get_list("CRM Deal", fields=["deal_owner","deal_value","status","closed_date"], limit_page_length=0)` — **fail-closed**: `except frappe.PermissionError: return _empty_commission()`.
3. `won_statuses = _statuses_of_type(["Won"])` — tái dùng helper (đã có trong `sales_team.py`; M09 finance gọi `frappe.get_all("CRM Deal Status", filters={"type": ["in", ["Won"]]}, pluck="name", limit_page_length=0)` **inline** để KHÔNG cross-import API module). Phân loại trên doctype cấu hình → KHÔNG bị data-scope.
4. Lặp deals: nếu `status in won_statuses` **và** `closed and month_start <= str(closed_date) <= month_end` → cộng `deal_value or 0` vào `total_revenue`; thêm `deal_owner` (nếu truthy) vào `set` reps.
5. `total_revenue = round(total_revenue)` (hoặc giữ float); `total_commission = round(total_revenue * COMMISSION_FLAT_RATE)`; `rep_count = len(reps)`; `group_count = len(COMMISSION_RULES)`.
6. Trả dict theo shape trên (`rules = COMMISSION_RULES`, `flat_rate_pct = COMMISSION_FLAT_RATE * 100`, `currency = COMMISSION_CURRENCY`).

**`_empty_commission()`** (kỳ rỗng / fail-closed): `total_commission=0`, `total_revenue=0`, `rep_count=0`, `group_count=len(COMMISSION_RULES)`, `period_label` = tháng hiện tại hợp lệ, `flat_rate_pct=COMMISSION_FLAT_RATE*100`, `currency`, `rules=COMMISSION_RULES`. **KHÔNG None, KHÔNG raise.**

> **403 phân biệt:** dispatcher-403 (guest/no session) do Frappe trả trước handler; **in-handler** thiếu read-perm CRM Deal KHÔNG raise 403 mà **fail-closed → `_empty_commission()`** (BR-13, mọi số 0). Endpoint là read-only GET, KHÔNG có in-handler permission-throw riêng.
>
> **Invariant count==rows:** không có list endpoint ở slice này (chỉ summary). `rep_count`/`total_revenue` tính DƯỚI `permission_query_conditions` (get_list) → khi M14 bật data-scope, NV chỉ thấy deal của BV được giao ⇒ số tự thu hẹp đúng, KHÔNG rò.

### 7bis.4 Business Rules

| BR | Áp dụng M09-1 | Nơi enforce |
|---|---|---|
| **BR-13** (data-scope, fail-closed) | `get_list("CRM Deal")` raise `PermissionError` → `_empty_commission()` (zero, rules giữ nguyên), KHÔNG 500. Khi data-scope bật, `total_*`/`rep_count` chỉ tính trên deal user đọc được. | `commission_summary` try/except `frappe.PermissionError`. |
| BR-10 (audit) | KHÔNG áp — endpoint read-only, không ghi/đổi tiền. | — |
| BR-12 (2FA) | KHÔNG áp — không thao tác nhạy cảm. | — |

> Không có `frappe.throw` nghiệp vụ ở slice này (read-only summary). Lỗi nghiệp vụ tương lai (vd khóa kỳ M10) = `frappe.throw(_("BR-M10-03: …"))`.

### 7bis.5 UI / Route / Nav

**Route (`frontend/src/router.js`):** THÊM route real-data MỚI, GIỮ stub cũ (no-regression).

| path | name | meta | component | mô tả |
|---|---|---|---|---|
| `/antmed/finance/commission` | `AntmedCommissionPage` (đề xuất — name DUY NHẤT) | `{ antmedShell: true, role: 'finance' }` | `() => import('@/pages/AntmedCommission.vue')` (page MỚI, lazy) | Màn real-data widget F2 — render trong **AntmedLayout** (isAntmedPath `/antmed/*` + `meta.antmedShell`), sidebar **Kế toán** (role='finance'). |

- **Stub cũ `/finance/commission`** (name `AntmedCommission`, component `antmedStub`, dòng router.js:259) **GIỮ NGUYÊN** — KHÔNG đổi path/component → no-regression PROTO test còn xanh. (Nếu name mới trùng `AntmedCommission` thì đổi name stub cũ → `AntmedCommissionMock` như tiền lệ M10-2 `AntmedDispatch`→`AntmedDispatchMock`; ưu tiên đặt name page mới **khác** để KHỎI đụng stub.)
- **Nav (`frontend/src/data/antmedNav.js`):** mục `fin-commission` (label "Hoa hồng NV") đổi `to: '/finance/commission'` → **`to: '/antmed/finance/commission'`** và `enabled: false` → **`enabled: true`** (mở persona Kế toán). KHÔNG đổi `fin-invoices`/`fin-receivables` (vẫn `enabled: false`, trỏ `/finance/receivables`).

**Data layer (`frontend/src/data/antmed.js`):** THÊM `getCommissionSummary({ auto, onError })` = `createResource({ url: 'antmed_crm.api.antmed.finance.commission_summary', method: 'GET', auto, onError })` — mirror `getMonthlyRevenue`/`getDispatchBoard`. FE đọc `r.data.total_commission` … (RAW dict, **KHÔNG** `r.data.data`).

**Page `frontend/src/pages/AntmedCommission.vue` (MỚI):**
- Breadcrumb "Trang chủ › Hoa hồng NV"; tiêu đề "Hoa hồng Nhân viên" (khớp mockup F2).
- **Header card pair** (2 thẻ):
  - **Thẻ trái "Tổng hoa hồng kỳ"**: value = `formatVnMoney(total_commission) + ' ₫'` (tái dùng `utils/antmedUi.js::formatVnMoney`; `total_commission=0` → **'0 ₫'** số THẬT, KHÔNG 'Sắp có'/'Chưa có'). Dòng phụ = `'<rep_count> NV · <group_count> nhóm vật tư'` (khớp nhãn mockup F2). Có thể dùng `AntmedKpiCard` (props `label`/`value`/`sub`) hoặc card riêng.
  - **Thẻ phải "Quy tắc kỳ <period_label>"**: tiêu đề chèn `period_label` thật; body = `v-for` qua `rules` → mỗi dòng `'<label> · <rate_pct>%'`. **KHÔNG hardcode JSX** danh sách trong template — render từ `data.rules`.
- **Tri-branch (bắt buộc):** `loading` → empty 'Đang tải…' · `error` → empty 'Lỗi tải hoa hồng' · `v-else` (có data) → 2 thẻ. KHÔNG hardcode mock số liệu trong UI production. KHÔNG `sort/reduce/aggregate` ở FE (BE đã gộp).

> Ground @ `AntMed_CRM_UI_Design.md §6.3` (Hoa hồng NV, persona Kế toán). Slice này chỉ dựng **header card pair** (tổng quan flat-rate); bảng chi tiết NV × nhóm VT × tier + nút "Khóa kỳ" = **[ROADMAP — M10]**.

### 7bis.6 ADR

#### ADR-M09-03: Commission widget M09-1 = flat-rate **hằng số trong code**, KHÔNG DocType, KHÔNG engine tier (M10)
- **Status**: Accepted (vòng 26)
- **Date**: 2026-06-18
- **Context**: Mockup F2 cần mở persona Kế toán nhanh với 2 thẻ tổng quan hoa hồng kỳ. Engine hoa hồng đầy đủ (tier × nhóm VT × NV, khóa kỳ, đẩy lương) đã đặc tả ở M10 (`AntMed Commission`/`AntMed Commission Rule`/BR-M10-04) nhưng CHƯA build (M10 = Wave 4). Yêu cầu vòng 26: KHÔNG new DocType, KHÔNG new module, KHÔNG per-category bonus engine.
- **Decision**: Đặt endpoint `finance.commission_summary` trong M09 (file `finance.py` mới), tính `total_commission = round(SUM(deal_value × FLAT_RATE))` trên CRM Deal Won kỳ hiện tại; `FLAT_RATE` + `rules` là **hằng số module**. Thẻ "Quy tắc kỳ" render từ `rules` (data thật, KHÔNG hardcode template).
- **Alternatives**: (a) Build ngay `AntMed Commission Rule` + engine tier — loại: vượt scope vòng 26, đụng Wave 4, rủi ro migration. (b) Đặt trong M10 module mới — loại: yêu cầu KHÔNG new module. (c) Đọc % từ Settings DocType — loại: vẫn là DocType phụ, chưa cần.
- **Consequences**: (+) mở persona Kế toán + thẻ F2 ngay, không nợ DB; render `rules` từ data → khi nâng M10 chỉ đổi nguồn `rules`/`flat_rate` mà KHÔNG đổi contract FE. (−) `FLAT_RATE=5%` là placeholder `[UNVERIFIED]`; hoa hồng theo nhóm VT thật chỉ đến khi M10 engine tier xong (nợ kỹ thuật ghi rõ). (−) endpoint nằm ở M09 `finance.py` dù nghiệp vụ hoa hồng "thuần" thuộc M10 — chấp nhận vì widget mở persona Kế toán (§6.3) và M09 là module Kế toán.

#### ADR-M09-04: BE finance API ở **`antmed_crm/api/antmed/finance.py`** (app riêng), KHÔNG `crm.api.antmed`
- **Status**: Accepted (vòng 26) — **Self-Correction** so với §1–§10 (viết theo template `crm.*`).
- **Date**: 2026-06-18
- **Context**: §1/§5/§10 ghi path `crm/antmed/…` + `crm.api.antmed.orders_ar.*` (template system-prompt mặc định: in-place app `crm`). Nhưng repo thực = app riêng `antmed_crm` (verify: `antmed_crm/api/antmed/{contract,sales_team,…}.py`, URL resource `antmed_crm.api.antmed.*` trong `frontend/src/data/antmed.js`, test `antmed_crm/tests/test_antmed_*`).
- **Decision**: File mới = `antmed_crm/api/antmed/finance.py`; URL whitelist = `antmed_crm.api.antmed.finance.commission_summary`; test = `antmed_crm/tests/test_antmed_finance.py`. Áp cùng quy ước cho mọi slice M09 khác (orders/AR khi build thật → `antmed_crm/api/antmed/orders_ar.py`).
- **Alternatives**: theo nguyên văn `crm.api.antmed.orders_ar` — loại: sai app, FE resource sẽ 404.
- **Consequences**: (+) endpoint callable đúng repo; (−) §1–§10 cũ còn chữ `crm.*` (giữ — light-touch, KHÔNG rewrite; §7bis + 2 ADR này là nguồn chốt cho slice). Backlog: khi build orders/AR thật, normalize path §1/§5/§10 sang `antmed_crm.*`.

### 7bis.7 Acceptance / DoD (slice M09-1)

1. **BE run-tests xanh**: `bench --site miyano run-tests --module antmed_crm.tests.test_antmed_finance` → `Ran N tests … OK`. TC tối thiểu:
   - Shape: trả đủ 8 key (`COMMISSION_SUMMARY_KEYS`); `currency=='VND'`; `period_label` khớp `T\d{1,2}/\d{4}`; `rules` là list `{label, rate_pct}`; `group_count == len(rules)`.
   - `total_commission == round(total_revenue × FLAT_RATE)`; `total_revenue == SUM(deal_value)` deal Won `closed_date` trong [đầu..cuối tháng]; deal Won tháng KHÁC / status KHÁC Won KHÔNG cộng.
   - `rep_count` = số `deal_owner` phân biệt có Won trong kỳ (deal_owner rỗng KHÔNG đếm).
   - Kỳ rỗng → `total_commission=0`/`total_revenue=0`/`rep_count=0` (KHÔNG None, KHÔNG raise); `rules`/`group_count` giữ nguyên.
   - **Fail-closed BR-13**: monkeypatch `frappe.get_list` raise `PermissionError` → trả `_empty_commission()` (mọi số 0, rules giữ), KHÔNG 500.
   - KHÔNG raw SQL (grep `frappe.db.sql` vắng trong `finance.py`); chỉ `get_list`/`get_all`.
   - (Khuyến nghị) chạy giá trị dưới NV scoped để xác nhận data-scope thu hẹp đúng (mirror test M02-8).
2. **FE vitest xanh** (`cd frontend && yarn vitest run`): route `AntmedCommissionPage` `/antmed/finance/commission` tồn tại (meta.antmedShell+role='finance', lazy); stub cũ `/finance/commission` còn nguyên; `getCommissionSummary` url `antmed_crm.api.antmed.finance.commission_summary` method GET; page đọc `r.data.total_commission`… (KHÔNG `.data.data`); thẻ trái render `formatVnMoney+' ₫'` (0→'0 ₫') + dòng phụ `'<n> NV · <m> nhóm vật tư'`; thẻ phải v-for `rules`; tri-branch loading/error/data; KHÔNG mock số liệu/KHÔNG sort/reduce. nav `fin-commission` enabled+to `/antmed/finance/commission`.
3. **FE build xanh**: `yarn build` emit chunk `AntmedCommission` chứa 'Hoa hồng', 'Tổng hoa hồng kỳ', 'Quy tắc kỳ', 'Lỗi tải hoa hồng', 'Đang tải…'.
4. **Pixel/LIVE** (sau USER reload): `http://miyano/crm/antmed/finance/commission` mở trong AntmedLayout, sidebar Kế toán, 2 thẻ render data thật, 0 console error, API 200 (KHÔNG còn trỏ antmedStub).
5. **No-regression**: test bootstrap + Customer 360° + 4 test gốc CRM + suite sales_team/contract còn xanh; route/stub CRM gốc nguyên vẹn.

---

## 8. Build slices (vertical — mỗi slice 1 vòng factory)

| Slice | Mục tiêu | BE | FE | Gate |
|---|---|---|---|---|
| **M09-1 — Widget Hoa hồng NV** (vòng 26, **§7bis**, mockup F2) | Mở persona Kế toán: 2 thẻ header "Tổng hoa hồng kỳ" + "Quy tắc kỳ" flat-rate. KHÔNG DocType/module/tier engine | `finance.py` MỚI: `commission_summary` (RAW dict 8 key) + `_empty_commission` + hằng `COMMISSION_FLAT_RATE`/`COMMISSION_RULES`/`COMMISSION_SUMMARY_KEYS` | route `/antmed/finance/commission` (`AntmedCommission.vue` MỚI) + `getCommissionSummary` + nav `fin-commission` enabled | `test_antmed_finance` Ran N OK (shape/Won-kỳ/rep_count/empty/fail-closed/no-SQL) + vitest + build; stub cũ giữ nguyên |
| **S1 — Đơn từ DO** | Dựng `AntMed Order`(+item) từ DO tiêu hao, list/detail | DocType `AntMed Order`/`AntMed Order Item`; `list_orders`/`get_order`/`create_order_from_delivery`; DocPerm | `AntmedOrders.vue` + `AntmedOrderDetail.vue` (list+detail) | BE test (count==rows, dựng đơn từ DO) + FE vitest + build |
| **S2 — AR ledger + aging** | `AntMed AR Entry` ledger + submit đơn sinh AR + aging 4 khoảng | DocType `AntMed AR Entry`; `submit_order` (on_submit→AR); `get_ar_aging`/`get_ar_ledger` | `AntmedAR.vue` (heatmap 4 khoảng) + `AntmedARDetail.vue` | test aging math + count==rows + pixel heatmap |
| **S3 — BR-14 chặn đơn** | Chặn đơn theo công nợ + override Quản lý | `AntMed Debt Threshold Block`; hook `check_debt_threshold_block` (validate); `unblock_hospital` | nút/khóa trạng thái `Bị chặn` + dialog mở khóa (Quản lý) | test BR-14 throw + override + role gate |
| **S4 — Thu tiền + nhắc thu** | Ghi nhận thu + nhắc thu (thủ công + scheduler) | `AntMed Payment`(+allocation), `AntMed Payment Reminder`; `record_payment`/`send_reminder` + scheduler `send_payment_reminders` (daily) | nút "Ghi nhận thu"/"Gửi nhắc" trên Bảng công nợ | test phân bổ thu + scheduler chống-trùng |
| **S5 — Xuất kế toán + đối soát NH** | Export MISA/Fast/Bravo + bank match | `AntMed Accounting Export Log`, `AntMed Bank Reconciliation Match`; `export_accounting` | `AntmedAccountingExport.vue` + lịch sử export | test export sinh file + log status |

> Thứ tự bắt buộc S1→S2→S3 (đơn→AR→chặn theo AR); S4/S5 nối sau. Mỗi slice giữ **no-regression** (test bootstrap + Customer 360° + 4 test gốc CRM còn xanh).

---

## 9. ADRs

> Quyết định cấp dự án **ADR-M01-01** (gốc: in-place; THỰC TẾ = app RIÊNG `antmed_crm`), **ADR-M01-02** (prefix `AntMed `), **ADR-M01-05** (hoãn data-scope BR-13), **DEC-A** (role VI), **DEC-B** (tách route AntMed), **D1** (native-lite, KHÔNG ERPNext), **D2** (Frappe Workflow gốc) đều áp cho M09 — kế thừa, không lặp lại.

### ADR-M09-01: AR ledger **native** (`AntMed AR Entry`/`AntMed Payment`), KHÔNG reuse ERPNext Sales Invoice/Payment Entry
- **Status**: Proposed (chốt ở S2)
- **Context**: Scaffold app-riêng cũ dựng M09 trên ERPNext `Sales Invoice`/`Sales Order`/`Payment Entry`/`Customer` (hooks + scheduler query `tabSales Invoice`). Nhưng D1 đã chốt **native-lite, KHÔNG cài ERPNext** trên site `miyano`.
- **Decision**: Tự dựng AR ledger native: `AntMed Order`(+item) → submit sinh `AntMed AR Entry` (ghi nợ) → `AntMed Payment` ghi có; tuổi nợ + outstanding tính bằng code từ `due_date`/`posting_date`.
- **Consequences**: (+) toàn quyền tuổi nợ 4 khoảng + biên bản đối chiếu + xuất MISA/Fast/Bravo theo schema riêng; không phụ thuộc accounting ERPNext nặng. (−) phải tự code phân bổ thu, đảo bút toán khi cancel, và đảm bảo ledger bất biến sau submit (docstatus).

### ADR-M09-02: Ngưỡng công nợ là DocType riêng `AntMed Debt Threshold Block` (không nhồi field vào `AntMed Hospital`)
- **Status**: Proposed
- **Context**: Scaffold đọc `debt_threshold` trên `AM Hospital Profile`. Cần vừa cấu hình ngưỡng/BV vừa lưu nhật ký khóa/mở (`blocked_at`/`unblock_reason`/`unblocked_by`) phục vụ audit BR-14.
- **Decision**: Giữ DocType riêng (autoname `field:hospital`, 1 BV ↔ 1 bản ghi) làm config **kiêm** nhật ký.
- **Alternatives**: field `debt_threshold` trên `AntMed Hospital` — đơn giản hơn nhưng mất nhật ký khóa/mở. *(cần khảo sát — chốt ở S3)*.
- **Consequences**: (+) audit khóa/mở rõ ràng; (−) thêm 1 DocType + đồng bộ `current_ar_vnd` mỗi lần AR thay đổi.

---

## 10. Acceptance / DoD (theo SPEC §6)

Một slice M09 "xong" khi đạt **toàn bộ**:

1. **BE run-tests xanh thật**: `bench --site miyano run-tests --module antmed_crm.tests.test_antmed_orders_ar` → **`Ran N tests … OK`**, 0 fail. TC tối thiểu theo slice:
   - DocType tồn tại sau migrate + đủ field tối thiểu (`frappe.get_meta`); naming series `AM-SO-`/`AM-AR-`/`AM-PAY-`/`PR-`/`EXP-` sinh đúng.
   - `create_order_from_delivery` copy đúng SL **tiêu hao** từ DO (M04) + đơn giá HĐ (M02).
   - `get_ar_aging` chia đúng 4 khoảng 0–30/31–60/61–90/>90; tổng khớp; **`len(data) == total_count`** (count==rows).
   - **BR-14**: submit đơn cho BV vượt ngưỡng → `frappe.throw` chứa `BR-14`; `Quản lý` override được; role khác KHÔNG.
   - `record_payment` giảm đúng `outstanding_amount`; scheduler `send_payment_reminders` chống trùng `(ar_entry, days_overdue)`.
2. **FE vitest xanh** (`yarn vitest run`): route mới tồn tại (path/name/lazy); page gọi đúng `antmed_crm.api.antmed.orders_ar.*`; KHÔNG `crm.api.*`/axios/tanstack; route CRM gốc còn nguyên.
3. **FE build xanh**: `yarn build` emit chunk `Antmed*` không vỡ.
4. **Pixel verify** (sau USER reload gunicorn): `http://miyano/crm/antmed/ar` render Bảng công nợ thật, heatmap 4 khoảng đúng màu, nút "Gửi nhắc"/"Ghi nhận thu" hoạt động, click BV → chi tiết; 0 console error; API 200.
5. **No-regression**: `test_antmed_bootstrap` + `test_antmed_customer` + 4 test gốc CRM (`test_org_hierarchy`, `test_crm_lead`, `test_crm_task`, `test_crm_territory`) vẫn xanh; route/doctype Frappe CRM gốc nguyên vẹn.

> Chưa pixel-verify ⇒ chưa "xong", chỉ "contract verified" (SPEC §6).

---

## Tham chiếu chéo

- **SSoT governing**: `../SPEC_AntMed_CRM.md` (D1 native-lite, D2 Frappe Workflow, Frappe-standard BE, count==rows, DoD §6), `../PLAN_AntMed_CRM.md` (M09 row §2: `AntMed Order`/`AntMed AR Entry`; W2 chuỗi M04→M06→M09; DAG).
- **Nghiệp vụ ground-truth**: `../../antmed_crm/docs/AntMed_CRM_Modules.md §9` (đơn từ DO tiêu hao, công nợ/tuổi nợ, nhắc thu, xuất MISA/Fast/Bravo, KPI doanh thu).
- **UI**: `../../antmed_crm/docs/AntMed_CRM_UI_Design.md §6` (persona Kế toán — Công nợ 4 khoảng heatmap, 3 nút hành động, xuất kế toán) + §1.2 (widget công nợ Dashboard CEO) + §9 (map module↔màn hình).
- **House style + hợp đồng API Frappe-standard**: `./m01_customer360.md` (RAW dict, PermissionError, count==rows, DocPerm role VI), `./m14_rbac_w0_role_naming.md` (role VI `NV kinh doanh`/`Thủ kho`/`Quản lý`; `Kế toán` = **[PLANNED]** cần thêm).
- **Scaffold tham chiếu (app-riêng cũ — đã adapt)**: `docs/antmed_crm/antmed_crm/m09_orders_ar/` — `hooks.py` (`check_debt_threshold_block` BR-14), `scheduler.py` (`send_payment_reminders` daily), doctype `am_debt_threshold_block`/`am_payment_reminder`/`am_bank_reconciliation_match`/`am_accounting_export_log` (⚠️ JSON gốc còn `AM `/ERPNext/`AM System Admin` — phải đổi `AntMed `/native/role VI khi build).
- **Module docs liên quan**: M02 (Hợp đồng/Quota — đơn giá/hạn TT), M04 (Giao phòng mổ — DO tiêu hao), M06 (Chứng từ/HĐĐT — hóa đơn link AR), M10 (KPI doanh thu/hoa hồng), M11 (Dashboard công nợ), M14 (RBAC/data-scope BR-13/2FA BR-12/audit BR-10).
