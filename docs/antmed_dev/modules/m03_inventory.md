# M03 — Vật tư & Tồn kho Đa điểm (native-lite) (Core Doc)

| Mục | Giá trị |
|---|---|
| Module folder | `crm/antmed/` (module Frappe **`AntMed`**, scrubbed = `antmed`) |
| DocType folder | `crm/antmed/doctype/antmed_item/`, `.../antmed_warehouse/`, `.../antmed_lot/`, `.../antmed_stock_entry/` … |
| Code path | `crm/antmed/doctype/<snake>/` + module hooks `crm/antmed/hooks_m03.py` (doc_events) + scheduler `crm/antmed/scheduler_m03.py` |
| API package | `crm/api/antmed/inventory.py` (đường gọi `crm.api.antmed.inventory.<fn>`) |
| Wave (PLAN) | **W1 — Master data & catalog** (M03 catalog-lite chạy ‖ M01-full ‖ M02) |
| Role chính (VI) | `Thủ kho` (chính), `NV kinh doanh` (kho cá nhân + đối chiếu ký gửi), `Quản lý` |
| Phụ thuộc (M..) | — (Item native — không phụ thuộc module nào; tham chiếu mềm `AntMed Hospital` từ M01 cho kho ký gửi) |
| Cấp dữ liệu cho (M..) | **M04** (giao phòng mổ: tồn/FIFO/lot), **M05** (bộ dụng cụ mượn: xuất/nhập kho), **M06** (chứng từ CO/CQ/ĐKLH gate) |
| Trạng thái | **[PLANNED — chưa code]** (DESIGN; đề xuất schema/API/workflow) |
| Cập nhật | 2026-06-17 |

> **Trạng thái: [PLANNED — chưa code]**
> Toàn bộ DocType / API / workflow / BR dưới đây là **ĐỀ XUẤT thiết kế** (spec-before-code), ground từ PLAN component-inventory dòng M03, `AntMed_CRM_Modules.md §3`, scaffold cũ `m03_inventory/` (app riêng — ĐÃ adapt `AM `→`AntMed `, ERPNext-reuse→native-lite), `AntMed_CRM_UI_Design.md §4 (Thủ kho)`, và BR-03/08/13/15. **Chưa có dòng code nào trên site `miyano`.** Mọi mục không truy được nguồn → đánh `[UNVERIFIED]` / `[cần khảo sát]`.

---

## 1. Overview

M03 là **xương sống vật tư** của AntMed CRM: nơi định nghĩa danh mục VTYT, lô (lot) gắn CO/CQ/HSD/ĐKLH, và **tồn kho 3 cấp** — điểm khác biệt cốt lõi so với CRM thường (tồn không phải một kho duy nhất). Theo `AntMed_CRM_Modules.md §3`:

- **Danh mục vật tư:** mã nội bộ, mã NSX, mã đăng ký lưu hành (ĐKLH), lot/serial, hạn dùng, CO/CQ gắn theo lô.
- **Kho phân cấp 3 cấp:** Kho Tổng công ty → Kho Cá nhân NV kinh doanh (đang mang theo) → Kho Ký gửi tại từng bệnh viện.
- **Phiếu xuất nội bộ:** NV lấy hàng từ kho Tổng — số lượng, lý do, ngày dự kiến dùng.
- **Kho ký gửi tại BV:** tồn theo lô, HSD, **đối chiếu định kỳ** với điều dưỡng kho mổ, cảnh báo cận date.
- **Truy vết lot:** NCC → ca mổ → bác sỹ — phục vụ thu hồi (recall) và hậu kiểm.
- **Kiểm kê di động** bằng quét QR/barcode (FE M12 dùng API M03).

**Vai trò trong 14 module:** M03 đứng ở Wave 1 (master data), **cấp dữ liệu** cho chuỗi vận hành W2/W3: M04 (giao phòng mổ cần tồn + FIFO theo HSD), M05 (bộ dụng cụ mượn xuất/nhập kho), M06 (gate chứng từ CO/CQ/ĐKLH trước khi cho phát hành). Vì native-lite (D1), M03 **tự xây** `AntMed Item`/`Warehouse`/`Lot`/`Stock Entry` thay cho ERPNext Item/Warehouse/Batch/Bin/Delivery Note.

**Business value:** Thủ kho và NV kinh doanh nhìn được tồn theo lô + HSD ở đúng cấp kho; hệ thống tự gợi ý FIFO theo HSD (BR-08), chặn xuất hàng thiếu CO/CQ (BR-03 chuẩn bị cho M06), nhắc đối chiếu kho ký gửi (BR-15), và truy vết được mọi lô khi recall.

### User stories
- *Thủ kho* nhập lô mới từ NCC (gắn CO/CQ, HSD, ĐKLH) → xuất cho NV kinh doanh (phiếu xuất nội bộ, FIFO cảnh báo nếu lô không ưu tiên).
- *NV kinh doanh* xem **kho cá nhân** đang giữ (SKU, lô, HSD), cập nhật đối chiếu **kho ký gửi BV** khi điều dưỡng kho mổ đếm thực tế.
- *Thủ kho/Quản lý* tra cứu **truy vết lot** (NCC → NV → BV → ca mổ → bác sỹ) khi có recall, và **phát thông báo thu hồi** tới các BV bị ảnh hưởng.

### 6 câu hỏi domain — feasibility check (BA Bước 2)

| # | Câu hỏi | Trả lời cho M03 |
|---|---|---|
| 1 | **CRM stage?** | **Vận hành kho** (master VTYT + giao dịch tồn). Không chạm pipeline/hợp đồng trực tiếp; chỉ cấp tồn/lot cho M04/M05. |
| 2 | **Ràng buộc hợp đồng/quota?** | Gián tiếp: M02 đối chiếu SKU trúng thầu dựa trên `AntMed Item`; M03 chỉ cung cấp danh mục — không enforce quota (đó là M02/M04). |
| 3 | **Actor là BV hay bác sỹ?** | **Cấp kho** là actor chính: Tổng / Cá nhân NV / Ký gửi BV. BV xuất hiện ở kho ký gửi (Link→`AntMed Hospital`); bác sỹ chỉ xuất hiện ở truy vết lot (qua M04/M05). |
| 4 | **Nghĩa vụ chứng từ / HĐĐT?** | **CÓ (gate)**: lô phải gắn CO/CQ/ĐKLH (BR-03 chuẩn bị). M03 lưu chứng từ ở cấp lô; phát hành HĐĐT là M06. |
| 5 | **Truy vết lot / thu hồi?** | **CÓ — trọng tâm**: truy vết NCC→NV→BV→ca mổ→bác sỹ + `AntMed Recall Notification`. Dữ liệu ca mổ/bác sỹ đến từ M04/M05 (lazy-import). |
| 6 | **Hậu quả nếu data sai?** | **Cao**: sai tồn/HSD → giao hàng hết hạn vào phòng mổ (rủi ro pháp lý + bệnh nhân). FIFO theo HSD (BR-08) và HSD cảnh báo là bắt buộc. Data-scope BR-13 (NV chỉ thấy kho cá nhân/BV của mình) = `[PLANNED]` W4/M14. |

---

## 2. DocTypes (native-lite, [PLANNED])

> Tất cả module = **`AntMed`**, prefix DocType = **`AntMed `**. Adapt từ scaffold cũ: `AM Medical Supply Info`→gộp vào `AntMed Item`; `Item`(ERPNext)→`AntMed Item`; `Batch`→`AntMed Lot`; `Warehouse`→`AntMed Warehouse`; `AM Lot Info`→gộp vào `AntMed Lot`; `AM Certificate`→`AntMed Certificate`; `Supplier`(ERPNext)→`AntMed Supplier` (master nhẹ). Field set = **tối thiểu khả dụng**, mở rộng = backlog. Role trong DocPerm dùng tên VI (DEC-A); scaffold cũ dùng `AM System Admin` → map sang `Quản lý`/`Thủ kho`.

| DocType (đề xuất) | Loại | Field chính ĐỀ XUẤT (ground scaffold + Modules §3) | Naming series / autoname | submittable |
|---|---|---|---|---|
| **`AntMed Item`** (VTYT) | master | `item_code`(unique), `item_name`, `manufacturer_code`(mã NSX), `registration_no`(số ĐKLH), `ma_dkluuhanh`(mã ĐK lưu hành), `requires_cocq`(Check, default 1), `shelf_life_months`(Int), `classification`(Select `Loại A/B/C/D`), `uom`, `default_unit_price`(Currency), `is_consignment`(Check), `disabled`(Check) | `field:item_code` (khoá tự nhiên) | — |
| **`AntMed Supplier`** (NCC) | master | `supplier_code`(unique), `supplier_name`, `tax_code`, `phone`, `address`, `disabled` | `field:supplier_code` | — |
| **`AntMed Warehouse`** (kho 3 cấp) | master | `warehouse_name`, **`warehouse_type`**(Select `Tổng`\n`Cá nhân NV`\n`Ký gửi BV`), `employee`(Link→User/HR — bắt buộc khi type=`Cá nhân NV`), `hospital`(Link→`AntMed Hospital` — bắt buộc khi type=`Ký gửi BV`), `parent_warehouse`(Link self, cây phân cấp), `disabled` | `field:warehouse_name` hoặc series `AM-WH-.####` `[cần khảo sát]` | — |
| **`AntMed Lot`** (lô CO/CQ/HSD/ĐKLH) | master/txn | `lot_no`(unique), `item`(Link→`AntMed Item`, reqd), `supplier`(Link→`AntMed Supplier`), `mfg_date`(Date), `expiry_date`(Date, reqd — HSD), `co_cert`(Link→`AntMed Certificate`), `cq_cert`(Link→`AntMed Certificate`), `recall_status`(Select `Bình thường`\n`Theo dõi`\n`Đã thu hồi`, default `Bình thường`), `recall_reason`(Long Text) | `field:lot_no` | — |
| **`AntMed Certificate`** (CO/CQ/Phiếu KN/GP NK) | master | `cert_no`(reqd), `cert_type`(Select `CO`\n`CQ`\n`Phiếu KN`\n`GP NK`, reqd), `item`(Link), `lot`(Link→`AntMed Lot`), `issued_date`(Date), `expires_at`(Date), `file_url`(Attach), `hash_sha256`(Data, read_only — BR-10) | series `AM-CERT-.YYYY.-.#####` | — |
| **`AntMed Stock Entry`** (phiếu nhập/xuất/chuyển) | txn | `naming_series`, `entry_type`(Select `Nhập NCC`\n`Xuất cho NV`\n`Chuyển kho`\n`Nhập ký gửi BV`\n`Điều chỉnh`), `posting_datetime`, `from_warehouse`(Link), `to_warehouse`(Link), `nv_employee`(Link — khi xuất cho NV), `hospital`(Link — khi nhập ký gửi BV), `reason`(Small Text), `expected_use_date`(Date — phiếu xuất nội bộ), `items`(Table→`AntMed Stock Entry Item`) | series `AM-SE-.YYYY.-.#####` | **1** (docstatus) |
| `AntMed Stock Entry Item` | child | `item`(Link, reqd), `lot`(Link→`AntMed Lot`), `qty`(Float, reqd), `uom`, `unit_price`(Currency), `amount`(Currency, read_only), `cocq_ok`(Check, read_only — tick xanh nếu lô có CO/CQ) | — (istable) | — |
| **`AntMed Stock Ledger`** (sổ tồn — bin theo kho×item×lot) | log | `warehouse`(Link), `item`(Link), `lot`(Link), `qty_change`(Float), `balance_qty`(Float), `stock_entry`(Link), `posting_datetime`, `voucher_type`, `voucher_no` | `hash` (auto) | — |
| **`AntMed Consignment Reconciliation`** (đối chiếu kho ký gửi — BR-15) | txn | `naming_series`, `hospital`(Link→`AntMed Hospital`, reqd), `warehouse`(Link→`AntMed Warehouse` type Ký gửi BV, reqd), `snapshot_at`(Datetime), `status`(Select `Nháp`\n`Đang đối chiếu`\n`Có chênh lệch`\n`Đã ký`\n`Đóng`), `total_variance_qty`(Float, ro), `total_variance_value`(Currency, ro), `signed_by_nv`, `signed_by_dd`(ký điều dưỡng kho mổ), `items`(Table) | series `AM-CR-.YYYY.-.#####` | **1** |
| `AntMed Consignment Reconciliation Item` | child | `lot`(Link), `expected_qty`(Float, ro — SL hệ thống), `counted_qty`(Float — SL thực đếm), `variance`(Float, ro), `reason`(Long Text), `photo`(Attach Image) | — (istable) | — |
| **`AntMed Recall Notification`** (thông báo thu hồi) | txn | `naming_series`, `lot`(Link→`AntMed Lot`, reqd), `affected_hospitals`(Long Text — JSON list, hoặc child `[cần khảo sát]`), `channel`(Select `Email`\n`Zalo`\n`SMS`\n`Cả 3`), `sent_at`(Datetime), `status`(Select `Nháp`\n`Đã duyệt`\n`Đã phát`\n`Đóng`) | series `AM-RN-.YYYY.-.#####` | **1** |
| **`AntMed Lot Trace Request`** (yêu cầu truy vết lot) | txn/log | `naming_series`, `lot_no`(Data, reqd), `requester`(Data, default user), `graph_json`(Long Text — cây NCC→NV→BV→ca→BS), `generated_at`(Datetime), `exported_pdf`(Attach) | series `AM-LTR-.YYYY.-.#####` | — |

> **Adapt-note (native-lite):**
> - Scaffold cũ `AM Medical Supply Info` (1-1 với `Item` ERPNext) → **không cần** vì `AntMed Item` đã tự chứa `registration_no`/`ma_dkluuhanh`/`requires_cocq`/`shelf_life_months`/`classification`. Bỏ hook `ensure_supply_info`.
> - Scaffold cũ `AM Lot Info` (1-1 với `Batch`) → **gộp** field `supplier`/`co_cert`/`cq_cert`/`recall_status`/`recall_reason` vào `AntMed Lot`. Bỏ hook `ensure_lot_info`.
> - ERPNext `Bin` (tồn theo kho×item) → thay bằng **`AntMed Stock Ledger`** (log từng biến động) + truy vấn tổng tồn theo `warehouse,item,lot`. Tồn-bin tự code ở mức cần dùng (D1).
> - `warehouse_type` là **field native** trên `AntMed Warehouse` (scaffold cũ là Custom Field `warehouse_type_am` trên ERPNext Warehouse) → native-lite không cần custom field.
> - **[UNVERIFIED]** Có cần `AntMed UOM` master riêng hay để `uom` là Data/Select tĩnh? Đề xuất: Data/Select tĩnh ở W1, master hoá sau nếu cần — `[cần khảo sát]`.

---

## 3. Workflow

M03 có **2 nhóm trạng thái**: (a) DocType giao dịch dùng **`docstatus`** (Draft→Submitted→Cancelled) cho `AntMed Stock Entry`; (b) **state machine có ràng buộc** cho `AntMed Consignment Reconciliation` và `AntMed Recall Notification` → đề xuất dùng **Frappe-native Workflow** (D2: fixtures `crm/fixtures/workflow.json`, field `status` làm `workflow_state`, states/transitions tiếng Việt).

### 3.1 `AntMed Stock Entry` — chỉ docstatus (không workflow riêng)
- `Nháp (docstatus=0)` → **Submit** → `Đã ghi sổ (docstatus=1)` (sinh dòng `AntMed Stock Ledger`, cập nhật tồn) → **Cancel** → `Đã huỷ (docstatus=2)` (đảo dòng ledger). FIFO/CO-CQ enforce ở `validate`/`on_submit` (xem §4).

### 3.2 `AntMed Consignment Reconciliation` — Workflow (đề xuất)

| State (`status`) | docstatus | Role được chuyển tiếp | Transition |
|---|---|---|---|
| `Nháp` | 0 | `Thủ kho` | tạo phiếu (snapshot tồn hệ thống) |
| `Đang đối chiếu` | 0 | `NV kinh doanh` | NV cập nhật `counted_qty` từ điều dưỡng kho mổ |
| `Có chênh lệch` | 0 | (auto khi tổng variance ≠ 0) | hệ thống tính `variance`, gắn nhãn |
| `Đã ký` | 1 | `Thủ kho` / `Quản lý` (submit) | ký NV + ký ĐD kho mổ → submit (BR-15 đóng chu kỳ) |
| `Đóng` | 1 | `Quản lý` | đóng đối chiếu sau xử lý chênh |

### 3.3 `AntMed Recall Notification` — Workflow (đề xuất)

| State (`status`) | docstatus | Role | Transition |
|---|---|---|---|
| `Nháp` | 0 | `Thủ kho` | chọn lô bị thu hồi, tính BV ảnh hưởng |
| `Đã duyệt` | 0 | `Quản lý` | duyệt nội dung + kênh |
| `Đã phát` | 1 | `Quản lý` (submit) | broadcast Email/Zalo/SMS (M13) + set `AntMed Lot.recall_status = Đã thu hồi` |
| `Đóng` | 1 | `Quản lý` | đóng sau khi xử lý xong |

> **Các DocType còn lại** (`AntMed Item`/`Supplier`/`Warehouse`/`Lot`/`Certificate`/`Stock Ledger`/`Lot Trace Request`) = **không có workflow** (master data / log). `AntMed Lot.recall_status` là Select nhãn (đổi qua Recall Notification, không phải workflow độc lập).

---

## 4. Business Rules

> Enforce trong **module hooks** `crm/antmed/hooks_m03.py` qua `doc_events` (wire ở `crm/hooks.py` — chỉ THÊM key), hoặc trong controller `validate`/`on_submit`. Lỗi nghiệp vụ = `frappe.throw(_("BR-XX: …tiếng Việt"))`.

| BR | Mô tả | Nơi enforce (đề xuất) | Trạng thái |
|---|---|---|---|
| **BR-08** | **FIFO theo HSD**: khi xuất kho (Stock Entry type `Xuất cho NV`/`Chuyển kho`) gợi ý lô có `expiry_date` sớm nhất còn tồn; nếu chọn lô không ưu tiên → **cảnh báo** (warn, không chặn cứng). Endpoint `fifo_suggest` + `check_fifo`. | `AntMed Stock Entry.validate` (warn) + `crm.api.antmed.inventory.fifo_suggest` | **[PLANNED]** — ground BR-08 README + UI_Design §4 dòng 128 |
| **BR-03** (chuẩn bị) | **Gate CO/CQ**: lô VTYT có `requires_cocq=1` phải gắn `co_cert`+`cq_cert` còn hiệu lực trước khi xuất/giao. M03 set `cocq_ok` trên dòng Stock Entry; **chặn cứng** thực thi ở M06 (phát hành). | `AntMed Stock Entry.validate` (set `cocq_ok`, warn nếu thiếu) | **[PLANNED]** — BR-03 enforce đầy đủ ở M06 Sales Invoice |
| **BR-15** | **Nhắc đối chiếu kho ký gửi định kỳ** (hằng tuần): scheduler quét kho `warehouse_type=Ký gửi BV` chưa đối chiếu trong 7 ngày → tạo task/notification cho NV phụ trách BV. | `crm/antmed/scheduler_m03.py::weekly_consignment_reminder` (hooks `scheduler_events`) | **[PLANNED]** — ground BR-15 README dòng 217 + scaffold scheduler |
| **BR-13** | **Data-scope**: NV chỉ thấy kho cá nhân của mình + kho ký gửi BV mình phụ trách. | `permission_query_conditions` cho `AntMed Warehouse`/`AntMed Stock Entry`/`AntMed Consignment Reconciliation` | **[PLANNED — hoãn W4/M14]** (giữ invariant count==rows ngay) |
| **BR-10** | **Audit hash-chain**: `AntMed Certificate.hash_sha256` (SHA256 file CO/CQ) + ghi `AntMed Audit Log` khi recall/đối chiếu submit. | `AntMed Certificate.validate` + lazy-import `crm.api.antmed.audit.write_log` | **[PLANNED]** — nền M14 |
| **BR (native)** | **Cận date 30/60/90 ngày**: scheduler quét lô có `expiry_date` rơi vào 30/60/90 ngày tới → `publish_realtime`/notification. | `scheduler_m03.py::check_near_expiry_90_60_30` | **[PLANNED]** — ground Modules §3 + UI_Design §4.3 |
| **BR (native)** | **Tồn không âm**: Stock Entry xuất quá tồn lô khả dụng → `frappe.throw` (chặn cứng). | `AntMed Stock Entry.on_submit` (kiểm `AntMed Stock Ledger` balance) | **[PLANNED]** |
| **BR (native)** | **Ràng buộc kho 3 cấp**: `warehouse_type=Cá nhân NV` ⇒ bắt buộc `employee`; `Ký gửi BV` ⇒ bắt buộc `hospital`. | `AntMed Warehouse.validate` | **[PLANNED]** — ground scaffold hook `validate_warehouse_type` |

> **Lưu ý invariant kỹ thuật (gate, không phải BR nghiệp vụ):** mọi list endpoint giữ **count == rows** (`get_list(..., limit_page_length=0)` để R4 thêm `permission_query_conditions` BR-13 không vỡ contract).

---

## 5. API

> File: `crm/api/antmed/inventory.py`. Mọi hàm `@frappe.whitelist(methods=["GET"|"POST"])`, **type-annotated** (`crm/hooks.py` `require_type_annotated_api_methods=True`), trả **RAW dict/list** (KHÔNG `_ok`/`_err`/envelope). Lỗi = `frappe.throw(_("BR-XX: …"))`. List endpoint giữ **count == rows**.

| Endpoint (`crm.api.antmed.inventory.<fn>`) | Verb | Mô tả |
|---|---|---|
| `list_items(filters, search, start, page_length)` | GET | Danh mục VTYT (`item_code`, `item_name`, `classification`, `requires_cocq`, `shelf_life_months`). count==rows. |
| `get_item(name)` | GET | Chi tiết 1 VTYT + danh sách lô (`AntMed Lot`) + tồn tổng. `has_permission` → `PermissionError`. |
| `list_warehouses(warehouse_type, filters)` | GET | Kho theo cấp (Tổng/Cá nhân NV/Ký gửi BV). count==rows. |
| `get_stock(warehouse, item, lot)` | GET | Tồn theo kho×item×lot (đọc `AntMed Stock Ledger` balance). RAW dict/list. |
| `list_stock_by_warehouse(warehouse, near_expiry_days)` | GET | Bảng tồn 1 kho: Mã/Tên/Lot/HSD/SL; lọc cận date 30/60/90. count==rows. |
| `fifo_suggest(item, warehouse, qty)` | GET | **BR-08**: trả danh sách lô gợi ý theo HSD sớm nhất đủ `qty`. |
| `check_fifo(item, warehouse, lot)` | GET | **BR-08**: trả `{is_priority: bool, suggested_lot}` để FE cảnh báo nếu lô không ưu tiên. |
| `create_stock_entry(entry_type, from_warehouse, to_warehouse, items, ...)` | POST | Tạo + (tuỳ) submit phiếu nhập/xuất/chuyển. Enforce tồn không âm + set `cocq_ok`. |
| `list_stock_entries(filters, entry_type)` | GET | Danh sách phiếu kho. count==rows. |
| `start_consignment_reconciliation(hospital, warehouse)` | POST | **BR-15**: snapshot tồn hệ thống → tạo `AntMed Consignment Reconciliation` (Nháp). |
| `submit_reconciliation(name, counted_items, signed_by_nv, signed_by_dd)` | POST | Cập nhật SL thực đếm, tính variance, submit (Đã ký). |
| `list_consignment_pending()` | GET | Kho ký gửi quá hạn đối chiếu (>7 ngày) — feed FE Thủ kho. count==rows. |
| `trace_lot(lot_no)` | GET | **Truy vết**: cây NCC→Stock Entry→NV→BV→ca mổ(M04)→bác sỹ(M04/M05). Lazy-import M04/M05, truyền PK. Trả `graph_json`. |
| `create_recall(lot, channel)` | POST | Tạo `AntMed Recall Notification`, tính BV ảnh hưởng từ truy vết. |
| `broadcast_recall(name)` | POST | Submit + phát Email/Zalo/SMS (lazy-import M13), set `Lot.recall_status=Đã thu hồi`. |
| `near_expiry_report(days)` | GET | Báo cáo lô cận date toàn hệ thống (30/60/90). count==rows. |

> **Shape list (ví dụ)** `{ "data": [...], "total_count": N }`, `len(data) == total_count` khi không phân trang. **POST mutate** trả RAW dict bản ghi vừa tạo/sửa (vd `{"name": "AM-SE-2026-00001", "docstatus": 1}`).

---

## 6. Integration

> Theo DAG (PLAN §2): M03 **không phụ thuộc** module nào (Item native), **cấp dữ liệu** cho M04/M05/M06. Quy ước: **lazy-import** module phụ thuộc trong hàm (tránh circular), **truyền PK** (name), không import controller chéo ở top-level.

**Doc_events VÀO `crm/hooks.py` (chỉ THÊM key — đề xuất):**
```python
# crm/hooks.py  (THÊM, không sửa key gốc)
doc_events = {
  "AntMed Warehouse":   {"validate": "crm.antmed.hooks_m03.validate_warehouse_type"},
  "AntMed Stock Entry": {"validate": "crm.antmed.hooks_m03.validate_stock_entry",   # tồn âm + FIFO warn + cocq_ok
                         "on_submit": "crm.antmed.hooks_m03.post_stock_ledger"},     # ghi AntMed Stock Ledger
  "AntMed Certificate": {"validate": "crm.antmed.hooks_m03.hash_certificate_file"},  # BR-10
  "AntMed Consignment Reconciliation": {"on_submit": "crm.antmed.hooks_m03.close_reconciliation"},
  "AntMed Recall Notification":        {"on_submit": "crm.antmed.hooks_m03.apply_recall"},
}
scheduler_events = {
  "daily":  ["crm.antmed.scheduler_m03.check_near_expiry_90_60_30"],
  "weekly": ["crm.antmed.scheduler_m03.weekly_consignment_reminder"],  # BR-15
}
```

**Ra (M03 cấp dữ liệu):**
- **→ M04 (giao phòng mổ):** M04 gọi `inventory.fifo_suggest` / `get_stock` (tồn kho cá nhân NV), khi giao xong sinh `AntMed Stock Entry` type `Nhập ký gửi BV` hoặc trừ kho cá nhân. M04 cung cấp ca-mổ/bác sỹ cho `trace_lot` (M03 lazy-import).
- **→ M05 (bộ dụng cụ mượn):** xuất/nhập kho khi mượn/trả qua `AntMed Stock Entry`.
- **→ M06 (chứng từ/HĐĐT):** **gate compliance** — M06 đọc `Lot.co_cert/cq_cert/registration_no` + dòng `cocq_ok` để chặn phát hành nếu thiếu (BR-03 enforce cứng tại M06).
- **→ M13 (integrations):** `broadcast_recall` lazy-import connector Email/Zalo/SMS.

**Vào (M03 nhận):**
- **← M01:** `AntMed Warehouse.hospital` Link→`AntMed Hospital` (kho ký gửi); `AntMed Consignment Reconciliation.hospital` Link→`AntMed Hospital`.
- **← M02 (mềm):** M02 đối chiếu SKU trúng thầu dựa trên `AntMed Item` (M02 đọc M03, không ngược lại).

---

## 7. UI

> Vue 3 + frappe-ui SPA. Route `/antmed/*` (APPEND vào `frontend/src/router.js`, lazy import). Page `Antmed<Feature>.vue`. Gọi đúng `crm.api.antmed.inventory.*` (KHÔNG `antmed_crm.api.*`, KHÔNG axios). Nguồn: `AntMed_CRM_UI_Design.md §4 (Thủ kho Tổng)` + định danh vật tư chuẩn `Mã VT | Tên | Lot | HSD | CO/CQ status` (§ nguyên tắc dòng 12).

| Màn hình (UI_Design) | Route | Page Vue | Role | Mô tả |
|---|---|---|---|---|
| Danh mục VTYT | `/antmed/items` | `AntmedItemList.vue` | Thủ kho, Quản lý | List + chi tiết VTYT (lô, tồn, CO/CQ). |
| Nhập kho | `/antmed/stock-entries/new?type=Nhập NCC` | `AntmedStockEntryForm.vue` | Thủ kho | Tạo phiếu nhập từ NCC (gắn lô, CO/CQ, HSD, ĐKLH). |
| Xuất kho cho NV (§4.2) | `/antmed/stock-entries/new?type=Xuất cho NV` | `AntmedStockEntryForm.vue` | Thủ kho | Chọn NV → quét lô → bảng Mã/Tên/Lot/HSD/SL/Đơn giá/Tổng; cột CO/CQ tick xanh, đỏ chặn; FIFO cảnh báo. |
| Kho ký gửi tại BV (§4.3) | `/antmed/consignment` | `AntmedConsignmentList.vue` | Thủ kho, NV kinh doanh | Chọn BV → bảng tồn ký gửi (SL hệ thống / SL thực tế / chênh) + nút "Yêu cầu đối chiếu" + lọc cận date 30/60/90. |
| Đối chiếu (form) | `/antmed/consignment/:name` | `AntmedReconciliationDetail.vue` | NV kinh doanh, Thủ kho | Cập nhật `counted_qty`, ảnh chứng minh, ký NV + ký ĐD → submit. |
| Lô & HSD | `/antmed/lots` | `AntmedLotList.vue` | Thủ kho | Lô theo item, HSD, CO/CQ, recall_status; cảnh báo cận date. |
| Truy vết lot (§4.4) | `/antmed/lot-trace` | `AntmedLotTrace.vue` | Thủ kho, Quản lý | Ô tra cứu Lot → graph dọc NCC→NV→BV→ca→BS; export PDF. |
| Cảnh báo / Recall | `/antmed/recalls` | `AntmedRecallList.vue` | Thủ kho, Quản lý | Tạo + duyệt + phát thông báo thu hồi. |
| Kho cá nhân NV (mobile) | `/antmed/my-stock` | `AntmedMyStock.vue` | NV kinh doanh | Tồn kho cá nhân (SKU, lô, HSD) — feed M12 mobile, quét QR. |

> A11y + nhãn 100% tiếng Việt qua `__()`; loading/error/empty mỗi resource; design token frappe-ui (KHÔNG hex thô). Route CRM gốc giữ NGUYÊN.

---

## 8. Build slices (cho factory — mỗi slice 1 vòng)

> Vertical slice; TDD failing-first; KHÔNG commit (HARD-STOP user). Theo PLAN: M03 ở W1, có thể chạy ‖ M01-full / M02.

1. **M03-S1 — Catalog-lite (master VTYT + lô + CO/CQ):** DocType `AntMed Item`, `AntMed Supplier`, `AntMed Lot`, `AntMed Certificate` + DocPerm (Thủ kho/Quản lý) + API `list_items`/`get_item`/list lô + BR `requires_cocq` set `cocq_ok`. FE `AntmedItemList` + `AntmedLotList`. Migrate + test count==rows.
2. **M03-S2 — Kho 3 cấp + sổ tồn:** `AntMed Warehouse` (validate 3 cấp), `AntMed Stock Ledger`, `AntMed Stock Entry` + child (docstatus, ghi ledger, tồn không âm). API `create_stock_entry`/`get_stock`/`list_stock_by_warehouse`. FE `AntmedStockEntryForm`. Test nhập/xuất/tồn.
3. **M03-S3 — FIFO theo HSD (BR-08) + cận date:** `fifo_suggest`/`check_fifo` + warn ở `validate`; scheduler `check_near_expiry_90_60_30`. FE cảnh báo lô không ưu tiên + lọc cận date. Test FIFO ordering.
4. **M03-S4 — Kho ký gửi + đối chiếu (BR-15):** `AntMed Consignment Reconciliation` (+child) + workflow + scheduler `weekly_consignment_reminder`. API start/submit/list_pending. FE `AntmedConsignmentList` + `AntmedReconciliationDetail`. Test variance + reminder.
5. **M03-S5 — Truy vết lot + recall:** `AntMed Lot Trace Request` + `trace_lot` (lazy-import M04/M05) + `AntMed Recall Notification` + workflow + `broadcast_recall` (lazy M13). FE `AntmedLotTrace` (graph) + `AntmedRecallList`. Test trace graph + recall set recall_status.

---

## 9. ADRs

### ADR-M03-01: Native-lite — tự xây Item/Warehouse/Lot/Stock Entry (KHÔNG ERPNext)
- **Status**: Accepted (kế thừa DEC D1=B, PLAN §"DECISIONS LOCKED")
- **Context**: Site `miyano` không cài ERPNext; scaffold cũ (`m03_inventory`) reuse ERPNext `Item`/`Batch`/`Warehouse`/`Bin`/`Supplier`/`Delivery Note`. Theo D1=(B), AntMed fork nhẹ Frappe CRM, không kéo ERPNext nặng.
- **Decision**: Xây DocType AntMed-native `AntMed Item`/`Supplier`/`Warehouse`/`Lot`/`Certificate`/`Stock Entry`(+child)/`Stock Ledger`; tồn-bin = log `AntMed Stock Ledger` + truy vấn balance; FIFO/HSD/CO-CQ tự code ở mức cần dùng.
- **Consequences**: (+) Toàn quyền lot CO/CQ/ĐKLH + kho ký gửi + truy vết; không phụ thuộc ERPNext. (−) Phải tự code FIFO/tồn-bin/đối chiếu (đánh đổi đã chấp nhận trong PLAN §5 Risks).

### ADR-M03-02: Kho 3 cấp qua field `warehouse_type` (không tách 3 DocType)
- **Status**: Accepted
- **Context**: Modules §3 yêu cầu Tổng→Cá nhân NV→Ký gửi BV. Scaffold cũ dùng Custom Field `warehouse_type_am` trên ERPNext Warehouse.
- **Decision**: Một DocType `AntMed Warehouse` + field native `warehouse_type` (Select) + `employee`/`hospital`/`parent_warehouse`; validate ràng buộc theo type.
- **Consequences**: (+) Schema gọn, truy vấn tồn đồng nhất. (−) Logic phân quyền/data-scope theo type phức tạp hơn (giải ở BR-13 W4).

### ADR-M03-03: Workflow Frappe-native cho Đối chiếu & Recall (không workflowcore)
- **Status**: Accepted (kế thừa DEC D2)
- **Context**: `AntMed Consignment Reconciliation` + `AntMed Recall Notification` cần state machine có vai trò; `AntMed Stock Entry` chỉ cần docstatus.
- **Decision**: Frappe-native Workflow (fixtures `workflow.json`, field `status`, states/transitions tiếng Việt) cho 2 DocType đối chiếu/recall; `AntMed Stock Entry` chỉ docstatus.
- **Consequences**: (+) Chuẩn Frappe, không cặp app khác. (−) Phải bảo trì fixtures workflow + smoke test mỗi transition.

> Kế thừa: **ADR-M01-01** (in-place), **ADR-M01-02** (prefix `AntMed `), **DEC-A** (role VI), **ADR-M01-05** (hoãn data-scope BR-13, giữ count==rows) — áp dụng nguyên cho M03.

---

## 10. Acceptance / DoD

> Theo SPEC §6. Một slice "xong" = BE test xanh + FE vitest + build + (sau USER reload) pixel verify + no-regression.

**BE (TDD — `Ran N OK`):** `bench --site miyano run-tests --module crm.tests.test_antmed_inventory`
- DocType tồn tại sau migrate + đủ field tối thiểu (`AntMed Item`/`Warehouse`/`Lot`/`Certificate`/`Stock Entry`/`Stock Ledger`).
- `item_code`/`lot_no`/`warehouse_name` unique; naming series sinh đúng (`AM-SE-`/`AM-CR-`/`AM-RN-`/`AM-LTR-`/`AM-CERT-`).
- `AntMed Warehouse.validate`: type `Cá nhân NV` thiếu `employee` → throw; `Ký gửi BV` thiếu `hospital` → throw.
- Stock Entry submit ghi `AntMed Stock Ledger` đúng dấu; xuất quá tồn → throw (tồn không âm).
- **BR-08 FIFO**: `fifo_suggest` trả lô HSD sớm nhất trước; `check_fifo` báo `is_priority=False` khi chọn lô muộn hơn.
- **BR-03**: lô `requires_cocq=1` thiếu CO/CQ → `cocq_ok=0` (warn).
- **BR-15**: `weekly_consignment_reminder` chọn đúng kho ký gửi quá 7 ngày.
- `trace_lot` trả graph NCC→NV→BV→ca→BS (lazy-import M04/M05 không lỗi khi M04/M05 chưa land → degrade gracefully).
- **count == rows** cho mọi list endpoint (không phân trang).
- **No-regression**: `test_antmed_bootstrap` + `test_antmed_customer` + 4 test gốc CRM vẫn OK.

**FE (vitest + build):** `cd frontend && yarn vitest run` xanh + `yarn build` xanh.
- Route `/antmed/items`, `/antmed/stock-entries`, `/antmed/consignment`, `/antmed/lots`, `/antmed/lot-trace`, `/antmed/recalls`, `/antmed/my-stock` tồn tại (lazy); gọi đúng `crm.api.antmed.inventory.*`; KHÔNG `antmed_crm.api`/axios; route CRM gốc còn nguyên.

**Pixel (Playwright, sau USER reload):** `http://miyano/crm/antmed/items` render thật; xuất kho FIFO cảnh báo hiển thị; truy vết lot vẽ graph; 0 console error; API 200.

---

## Tham chiếu chéo
- Governing spec: `../SPEC_AntMed_CRM.md` (D1 native-lite §2, Frappe-standard BE §5, DoD §6)
- Plan & DAG: `../PLAN_AntMed_CRM.md` (component-inventory M03 §2, Wave W1 §3, Risks §5)
- Nghiệp vụ ground-truth: `../../antmed_crm/docs/AntMed_CRM_Modules.md §3 — Quản lý Vật tư & Tồn kho Đa điểm` (dòng 27–36)
- UI: `../../antmed_crm/docs/AntMed_CRM_UI_Design.md §4 — Thủ kho Tổng` (Xuất kho NV / Kho ký gửi BV / Truy vết lot) + nguyên tắc định danh vật tư (dòng 12)
- Scaffold tham chiếu (app cũ — đã adapt AM→AntMed, ERPNext→native-lite): `docs/antmed_crm/antmed_crm/m03_inventory/doctype/` (`am_medical_supply_info`, `am_lot_info`, `am_certificate`, `am_consignment_reconciliation`(+item), `am_recall_notification`, `am_lot_trace_request`), `.../m03_inventory/hooks.py`, `.../scheduler.py`
- Module liên quan: `./m01_customer360.md` (AntMed Hospital cho kho ký gửi); M02 (SKU trúng thầu), M04 (giao phòng mổ — FIFO/trace), M05 (bộ mượn — xuất/nhập kho), M06 (gate CO/CQ), M14 (BR-13 data-scope, BR-10 audit) — **[PLANNED]**
- BR map (README): `docs/antmed_crm/README.md` (BR-08 FIFO, BR-03 CO/CQ gate, BR-15 đối chiếu ký gửi, BR-13 data-scope, BR-10 hash chain)
