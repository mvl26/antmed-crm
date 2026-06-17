# M09 — Đơn hàng, Công nợ & Doanh thu (AR) (Core Doc)

| Mục | Giá trị |
|---|---|
| Module folder | `crm/antmed/` (module Frappe **`AntMed`**, scrubbed = `antmed`) — DocType M09 đặt tại `crm/antmed/doctype/antmed_order/`, `crm/antmed/doctype/antmed_ar_entry/`, … |
| Code path BE | `crm/antmed/doctype/<snake>/` + endpoint `crm/api/antmed/orders_ar.py` (đường gọi `crm.api.antmed.orders_ar.<fn>`) |
| Module hooks (BR) | `doc_events` wiring trong `crm/hooks.py` → `crm/antmed/<module hooks>.py` (vd `crm.antmed.orders_ar_hooks.*`) |
| FE pages | `frontend/src/pages/Antmed*` + route `/antmed/orders`, `/antmed/ar`, `/antmed/ar/:hospital` |
| Wave (PLAN) | **W2 — Chuỗi vận hành lõi** (sau M04 → M06 → **M09**) |
| Role chính (VI) | `Kế toán` **[PLANNED — chưa có trong fixture]**, `Quản lý` (override BR-14) · phụ: `NV kinh doanh` (xem AR theo tuyến), `System Manager` |
| Phụ thuộc | **M02** (Hợp đồng/Quota — đơn giá, hạn TT), **M04** (Giao phòng mổ — DO tiêu hao thực) |
| Cấp dữ liệu cho | **M10** (KPI doanh thu/hoa hồng), **M11** (Dashboard công nợ/AR aging) |
| Trạng thái | **PLANNED — chưa code** (chưa có DocType/API/test trên site `miyano`) |
| Cập nhật | 2026-06-17 |

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

M09 dùng **docstatus** (Frappe-native submit) cho các txn, và **một Workflow nhẹ** cho vòng đời đơn — đề xuất qua fixtures `crm/fixtures/workflow.json` (D2 Frappe-native, KHÔNG `workflowcore`). State field = `status` (hoặc `workflow_state`), giá trị **tiếng Việt**.

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
| **BR-14** | **Chặn đơn khi công nợ BV vượt ngưỡng.** Khi submit/validate `AntMed Order`: tính tổng `outstanding_amount` các `AntMed AR Entry` (docstatus=1) của BV; nếu ≥ `threshold_vnd` (từ `AntMed Debt Threshold Block` của BV) → `frappe.throw`. Chỉ `Quản lý` được vượt. | `doc_events`: `AntMed Order` → `validate` → `crm.antmed.orders_ar_hooks.check_debt_threshold_block` | **[PLANNED]** — scaffold có `check_debt_threshold_block` (đọc `AM Hospital Profile.debt_threshold`, override `AM CEO`); **adapt**: native AR sum thay `Sales Invoice`, role override `Quản lý` thay `AM CEO`. |
| BR-13 | **Data-scope**: NV chỉ thấy AR/đơn của BV được giao. | `permission_query_conditions` cho `AntMed Order`/`AntMed AR Entry` (wiring ở M14/W4) — giữ invariant `count == rows` ngay từ M09. | **[ROADMAP — M14]** (ADR-M01-05) |
| BR-10 | **Audit hash-chain** mọi thao tác ghi thu / mở khóa công nợ / xuất kế toán. | M14 `audit.write_log` gọi từ handler `record_payment`, `unblock_hospital`, `export_accounting`. | **[ROADMAP — M14]** |
| BR-12 | **2FA** cho thao tác nhạy cảm (mở khóa công nợ BR-14, ghi nhận thu lớn). | M14 `audit.require_2fa_and_log` (gate trước override). | **[ROADMAP — M14]** |

> **Invariant kỹ thuật (gate, không phải BR nghiệp vụ):** mọi list endpoint AR/đơn giữ **`count == rows`** (đếm qua `get_list(pluck=…, limit_page_length=0)`), để khi M14 bật `permission_query_conditions` không vỡ contract.
> Mã lỗi nghiệp vụ tiếng Việt, vd: `frappe.throw(_("BR-14: BV {0} có công nợ {1:,.0f} vượt ngưỡng {2:,.0f}.").format(...))`.

---

## 5. API

> File: `crm/api/antmed/orders_ar.py`. Mọi hàm `@frappe.whitelist(methods=["GET"|"POST"])`, **type-annotated** (`crm/hooks.py:28 require_type_annotated_api_methods = True`), trả **RAW dict/list** (KHÔNG `_ok/_err`/envelope). Lỗi nghiệp vụ = `frappe.throw(_("BR-XX: …"))`. List giữ **count == rows**.

| Endpoint (`crm.api.antmed.orders_ar.<fn>`) | Verb | Mô tả |
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

> **Scheduler (không phải whitelist):** `crm.antmed.orders_ar_scheduler.send_payment_reminders` — chạy **daily** (khai trong `scheduler_events` của `crm/hooks.py`). **Adapt** từ scaffold `scheduler.py`: quét `AntMed AR Entry` (thay `Sales Invoice`) có `outstanding_amount>0` và `DATEDIFF(today, due_date) IN (0,7,30)`; chống trùng theo `(ar_entry, days_overdue)`; set `escalation_level` 1/2/3. **[UNVERIFIED]** tích hợp kênh gửi thật (Email/Zalo/SMS) = M13.

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

> Vue 3 + frappe-ui SPA. Gọi đúng `crm.api.antmed.orders_ar.*` qua `createResource`/`createListResource`. Route mới **APPEND** vào `frontend/src/router.js` (lazy). KHÔNG đụng route CRM gốc. Nhãn 100% tiếng Việt qua `__()`; tiền VND `1.234.567 ₫`, số `tabular-nums`. Persona chính = **Kế toán** (desktop-first — UI §6).

### Routes (THÊM mới — lazy)

| path | name | component | mô tả | Role dùng |
|---|---|---|---|---|
| `/antmed/orders` | `AntmedOrders` | `pages/AntmedOrders.vue` | List đơn bán (filter BV/trạng thái/kỳ) | Kế toán, Quản lý, NV KD |
| `/antmed/orders/:name` | `AntmedOrderDetail` | `pages/AntmedOrderDetail.vue` | Chi tiết đơn + line tiêu hao + link DO/HĐ/AR | Kế toán, Quản lý |
| `/antmed/ar` | `AntmedAR` | `pages/AntmedAR.vue` | **Bảng công nợ** — BV × tuổi nợ 0–30/31–60/61–90/>90 (heatmap đỏ dần); cột hành động "Gửi nhắc"/"Tạo biên bản đối chiếu"/"Ghi nhận thu" | Kế toán |
| `/antmed/ar/:hospital` | `AntmedARDetail` | `pages/AntmedARDetail.vue` | Chi tiết 1 BV: timeline hóa đơn → thanh toán → còn lại + file biên bản đối chiếu | Kế toán |
| `/antmed/ar/export` | `AntmedAccountingExport` | `pages/AntmedAccountingExport.vue` | Xuất kế toán MISA/Fast/Bravo theo kỳ + lịch sử export | Kế toán |

> Ground @ `AntMed_CRM_UI_Design.md §6` (Kế toán): sidebar *Hóa đơn / Công nợ phải thu / Đối soát ngân hàng / Hoa hồng NV / Xuất kế toán (MISA/Fast)*; §6.2 bảng công nợ tuổi nợ 4 khoảng heatmap + 3 nút hành động + click BV → chi tiết; §9 hàng "9. Đơn hàng & Công nợ → Bảng công nợ, Hóa đơn → Kế toán, CEO". Hoa hồng NV (§6.3) = **M10**, không thuộc M09.

---

## 8. Build slices (vertical — mỗi slice 1 vòng factory)

| Slice | Mục tiêu | BE | FE | Gate |
|---|---|---|---|---|
| **S1 — Đơn từ DO** | Dựng `AntMed Order`(+item) từ DO tiêu hao, list/detail | DocType `AntMed Order`/`AntMed Order Item`; `list_orders`/`get_order`/`create_order_from_delivery`; DocPerm | `AntmedOrders.vue` + `AntmedOrderDetail.vue` (list+detail) | BE test (count==rows, dựng đơn từ DO) + FE vitest + build |
| **S2 — AR ledger + aging** | `AntMed AR Entry` ledger + submit đơn sinh AR + aging 4 khoảng | DocType `AntMed AR Entry`; `submit_order` (on_submit→AR); `get_ar_aging`/`get_ar_ledger` | `AntmedAR.vue` (heatmap 4 khoảng) + `AntmedARDetail.vue` | test aging math + count==rows + pixel heatmap |
| **S3 — BR-14 chặn đơn** | Chặn đơn theo công nợ + override Quản lý | `AntMed Debt Threshold Block`; hook `check_debt_threshold_block` (validate); `unblock_hospital` | nút/khóa trạng thái `Bị chặn` + dialog mở khóa (Quản lý) | test BR-14 throw + override + role gate |
| **S4 — Thu tiền + nhắc thu** | Ghi nhận thu + nhắc thu (thủ công + scheduler) | `AntMed Payment`(+allocation), `AntMed Payment Reminder`; `record_payment`/`send_reminder` + scheduler `send_payment_reminders` (daily) | nút "Ghi nhận thu"/"Gửi nhắc" trên Bảng công nợ | test phân bổ thu + scheduler chống-trùng |
| **S5 — Xuất kế toán + đối soát NH** | Export MISA/Fast/Bravo + bank match | `AntMed Accounting Export Log`, `AntMed Bank Reconciliation Match`; `export_accounting` | `AntmedAccountingExport.vue` + lịch sử export | test export sinh file + log status |

> Thứ tự bắt buộc S1→S2→S3 (đơn→AR→chặn theo AR); S4/S5 nối sau. Mỗi slice giữ **no-regression** (test bootstrap + Customer 360° + 4 test gốc CRM còn xanh).

---

## 9. ADRs

> Quyết định cấp dự án **ADR-M01-01** (in-place app `crm`), **ADR-M01-02** (prefix `AntMed `), **ADR-M01-05** (hoãn data-scope BR-13), **DEC-A** (role VI), **DEC-B** (tách route AntMed), **D1** (native-lite, KHÔNG ERPNext), **D2** (Frappe Workflow gốc) đều áp cho M09 — kế thừa, không lặp lại.

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

1. **BE run-tests xanh thật**: `bench --site miyano run-tests --module crm.tests.test_antmed_orders_ar` → **`Ran N tests … OK`**, 0 fail. TC tối thiểu theo slice:
   - DocType tồn tại sau migrate + đủ field tối thiểu (`frappe.get_meta`); naming series `AM-SO-`/`AM-AR-`/`AM-PAY-`/`PR-`/`EXP-` sinh đúng.
   - `create_order_from_delivery` copy đúng SL **tiêu hao** từ DO (M04) + đơn giá HĐ (M02).
   - `get_ar_aging` chia đúng 4 khoảng 0–30/31–60/61–90/>90; tổng khớp; **`len(data) == total_count`** (count==rows).
   - **BR-14**: submit đơn cho BV vượt ngưỡng → `frappe.throw` chứa `BR-14`; `Quản lý` override được; role khác KHÔNG.
   - `record_payment` giảm đúng `outstanding_amount`; scheduler `send_payment_reminders` chống trùng `(ar_entry, days_overdue)`.
2. **FE vitest xanh** (`yarn vitest run`): route mới tồn tại (path/name/lazy); page gọi đúng `crm.api.antmed.orders_ar.*`; KHÔNG `antmed_crm.api.*`/axios/tanstack; route CRM gốc còn nguyên.
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
