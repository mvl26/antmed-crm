# M04 — Giao hàng & Bàn giao Phòng mổ (SLA) (Core Doc)

| Mục | Giá trị |
|---|---|
| Module folder | `antmed_crm/antmed/` (module Frappe **`AntMed`**, scrubbed = `antmed`) |
| DocType folder | `antmed_crm/antmed/doctype/antmed_delivery/`, `.../antmed_or_schedule/`, `.../antmed_sla_log/`, `.../antmed_delivery_item/` … (đề xuất) |
| Code path BE | `antmed_crm/antmed/doctype/<snake>/` + `antmed_crm/api/antmed/delivery.py` (đường gọi `antmed_crm.api.antmed.delivery.<fn>`) |
| FE pages | `frontend/src/pages/Antmed*` + route `/antmed/deliveries`, `/antmed/deliveries/:name`, `/antmed/dispatch` (kanban) |
| Wave (PLAN) | **W2 — Chuỗi vận hành lõi** (M04 → M06 → M09, tuần tự) |
| Role chính (VI) | `NV kinh doanh` (giao tại phòng mổ), `Quản lý` (điều phối/gán NV, duyệt ngoài thầu); `Thủ kho` (xuất kho cá nhân) — [PLANNED] thêm `Trưởng phòng KD` nếu tách vai điều phối khỏi `Quản lý` |
| Phụ thuộc | **M01** (Hospital/Doctor), **M02** (Contract/Quota — đối chiếu danh mục trúng thầu BR-01/BR-06), **M03** (Item/Lot/Warehouse/Stock Entry — FIFO/HSD BR-08) |
| Cấp dữ liệu cho | **M06** (chứng từ + HĐĐT theo phiếu giao), **M09** (đơn bán từ tiêu hao thực tế), **M10** (KPI SLA giao đúng giờ) |
| Trạng thái | **PLANNED — chưa code** |
| Cập nhật | 2026-06-17 |

> **Trạng thái: [PLANNED — chưa code]**
> Tài liệu này là **blueprint phát triển (DESIGN / đề xuất)** — schema/API/workflow dưới đây **chưa được implement**. Mọi DocType/field/endpoint là *đề xuất*, ground @ scaffold tham chiếu (`docs/antmed_crm/antmed_crm/m04_or_delivery/`, bản app-riêng cũ) + `AntMed_CRM_Modules.md §4` + `AntMed_CRM_UI_Design.md`. Đã **adapt**: prefix `AM `→`AntMed `, ERPNext-reuse (`Customer`/`Item`/`Batch`/`Delivery Note`)→**native-lite** (`AntMed Hospital`/`AntMed Item`/`AntMed Lot`/`AntMed Delivery`), bỏ giả định app riêng (`antmed_crm.api.*`→`antmed_crm.api.antmed.*`, module `M04 OR Delivery`→`AntMed`).

---

## 1. Overview

M04 là **trái tim vận hành đặc thù AntMed**: bệnh viện gọi vật tư cho một **kíp mổ sắp diễn ra** → NV kinh doanh phải giao **tận phòng mổ trước giờ ca mổ** (SLA giờ ca). Đây là module **CRM gốc KHÔNG có** (`AntMed_CRM_Modules.md` — bảng khoảng cách: "4. Giao phòng mổ với SLA giờ ca = Không sẵn → Xây mới").

Vai trò trong 14 module (theo DAG `PLAN §2`): M04 nằm **giữa chuỗi vận hành lõi** `M02(Contract) → M04(Delivery) → M06(Docs/HĐĐT) → M09(Orders/AR)`. Nó **tiêu thụ** master data (BV/bác sỹ từ M01, hợp đồng/quota từ M02, tồn lô/HSD từ M03) và **sinh ra** sự kiện gốc cho hạ nguồn: phiếu giao đã ký (→ M06 sinh chứng từ/HĐĐT), lượng **vật tư dùng thực tế** (→ M09 lập đơn bán đúng tiêu hao), và bản ghi **đúng/trễ SLA** (→ M10 KPI).

**Business value (theo `Modules.md §4`):**
- Đối chiếu **tự động** yêu cầu vật tư với hợp đồng trúng thầu (M02) → cảnh báo/chặn nếu vật tư **ngoài danh mục** (BR-01).
- Gán NV giao + **ưu tiên theo giờ ca mổ** (SLA) — điều phối nhiều lượt giao/ngày.
- Phiếu giao (DO) số: **ký số / ký tay trên app**, **chụp ảnh hiện trường**, **GPS** thời điểm bàn giao — bằng chứng pháp lý + audit.
- Ghi nhận **vật tư đã dùng vs trả lại** → cấp tiêu hao thực cho M09 (xuất hóa đơn đúng thực tế).

**User stories:**
- *NV kinh doanh (mobile)*: mở ca giao hôm nay → xác nhận yêu cầu → quét lấy hàng kho cá nhân (gợi ý lot FIFO) → tới BV (GPS check-in) → bác sỹ/điều dưỡng ký số + chụp ≥2 ảnh → chọn "Hoàn tất / một phần" → hệ thống sinh phiếu giao và phát SLA đúng/trễ.
- *Quản lý (điều phối)*: nhìn **bảng điều phối kanban** (Mới tiếp nhận → Đã gán NV → Đang giao → Đã bàn giao) với đồng hồ đếm ngược tới giờ mổ; kéo-thả gán NV; duyệt yêu cầu ngoài danh mục thầu.
- *Hệ thống*: với mỗi yêu cầu giao đã đối chiếu HĐ, ghi log mốc thời gian (tạo → gán → lên đường → bàn giao) để đo SLA và truy vết.

---

## 2. DocTypes (native-lite, [PLANNED])

> Field set = **đề xuất**, ground @ scaffold `m04_or_delivery/doctype/*` (đã adapt sang native-lite) + `Modules.md §4` + `UI_Design §3.2`. Trường nghiệp vụ mở rộng (bản đồ điều phối, route-optimize nhiều lượt) = backlog. **Adapt khoá:** scaffold dùng `Customer`/`AM Doctor`/`Employee`/`Item`/`Batch`/`Delivery Note` → ở đây đổi sang `AntMed Hospital`/`AntMed Doctor`/`User` (NV)/`AntMed Item`/`AntMed Lot`/`AntMed Delivery`.

| DocType (đề xuất) | Loại | Field chính (đề xuất — grounded) | Naming series / autoname |
|---|---|---|---|
| **`AntMed Delivery`** | txn (submittable, **có workflow**) | `naming_series`, `source` (Portal/Zalo/Email/Phone/Mobile App), `hospital` (Link `AntMed Hospital`, reqd), `doctor` (Link `AntMed Doctor`), `surgery_room` (Data), `surgery_datetime` (Datetime, reqd), `sla_minutes` (Int, default 120), `or_schedule` (Link `AntMed OR Schedule`), `contract` (Link `AntMed Contract`, read_only — derive khi đối chiếu BR-01), `out_of_contract_flag` (Check), `out_of_contract_approved_by` (Link `User`, read_only), `assigned_employee` (Link `User` — NV giao), `workflow_state` (Select, xem §3), `items` (Table `AntMed Delivery Item`), `delivered_at` (Datetime), `sla_status` (Select OnTime/Late, read_only), `gps_lat`/`gps_lng`/`gps_accuracy` (Float — GPS bàn giao), `signature_method` (Select Digital/Paper-Photo), `signed_at` (Datetime), `signed_by` (Data — BS/ĐD ký nhận), `photos` (Table `AntMed DO Photo`), `signatures` (Table `AntMed DO Signature`), `notes` (Long Text) | `naming_series:` **`AntMed-DR-.YYYY.-.#####`** ⚠️ trùng prefix reserve `AM-DR` ở M01 — dùng `AntMed-DR-` để khỏi đụng; `is_submittable: 1` |
| **`AntMed Delivery Item`** | child (của `AntMed Delivery`) | `item` (Link `AntMed Item`, reqd), `item_name` (Data, read_only fetch), `requested_qty` (Float, reqd), `delivered_qty` (Float), **`consumed_qty`** (Float — vật tư **dùng** thực tế → cấp cho M09), **`returned_qty`** (Float — trả về kho ký gửi/cá nhân), `uom` (Data), `lot` (Link `AntMed Lot` — lot xuất, gợi ý FIFO BR-08), `contract_item` (Link tới dòng quota M02), `notes` | `autoname: hash` (child, `istable: 1`) |
| **`AntMed OR Schedule`** | master/txn nhẹ | `hospital` (Link), `doctor` (Link `AntMed Doctor`), `surgery_room` (Data), `surgery_datetime` (Datetime, reqd), `surgery_type` (Data), `status` (Select Dự kiến/Đã xác nhận/Hủy) — *lịch ca mổ để treo Delivery + đếm ngược kanban* | `autoname: hash` hoặc series `AntMed-OR-.YYYY.-.#####` [cần khảo sát: BV cấp lịch hay AntMed tự nhập] |
| **`AntMed SLA Log`** | log (append-only) | `delivery` (Link `AntMed Delivery`), `event` (Select Created/Assigned/EnRoute/Delivered), `ts` (Datetime, default now), `lag_sec` (Int — lệch so với mốc trước/ngưỡng) | `autoname: hash`, `istable: 0` |
| **`AntMed DO Photo`** *(child, [PLANNED])* | child (của `AntMed Delivery`) | `file_url` (Attach Image), `taken_at` (Datetime), `caption` (Data), `gps_lat`/`gps_lng` (Float) | `autoname: hash` |
| **`AntMed DO Signature`** *(child, [PLANNED])* | child (của `AntMed Delivery`) | `signer_name` (Data, reqd), `signer_role` (Select Bác sỹ/Điều dưỡng/Khác), `signature_png` (Attach Image), `sign_method` (Select Touch/USB Token/Paper-Photo), `hash_sha256` (Data, read_only — hash chữ ký, gắn audit BR-10) | `autoname: hash` |

> **Quyết định adapt từ scaffold** (xem ADR-M04-01): scaffold tách `AM Delivery Request` (DR) + `AM DO Extras` (gắn vào `Delivery Note` của ERPNext). Native-lite **không có** `Delivery Note` → **hợp nhất** DR + DO-extras thành **một** DocType `AntMed Delivery` (DR + bàn giao trên cùng vòng đời/workflow); GPS/ký/ảnh thành field + child ngay trên `AntMed Delivery`. `AntMed DO Photo`/`AntMed DO Signature` giữ là child table như scaffold.

> **Naming**: scaffold dùng series `DR-.YYYY.-.#####`. M01 đã **reserve** prefix `AM-DR` (không cho M01 dùng) cho Delivery Request → ở đây chốt **`AntMed-DR-.YYYY.-.#####`** (prefix `AntMed `). [cần khảo sát: thống nhất 1 chuẩn prefix series toàn dự án — `AntMed-` hay `AM-`.]

---

## 3. Workflow

**CÓ workflow** (state machine) — đây là khác biệt lõi của M04. Dùng **Frappe Workflow gốc** (D2): định nghĩa trong fixture `antmed_crm/fixtures/workflow.json` + `docstatus`, state field = **`workflow_state`**. States/transitions **tiếng Việt** (key kỹ thuật giữ ở action; nhãn VI). Adapt từ scaffold `status` (`Draft\nTriaged\nAssigned\nInTransit\nDelivered\nClosed\nRejected`, ~7 trạng thái + submittable).

**Workflow `AntMed DR Workflow`** (đề xuất — ~6 state hữu dụng + 1 nhánh từ chối):

| # | State (workflow_state, VI) | docstatus | Vai trò được phép tới đây | Ý nghĩa |
|---|---|---|---|---|
| 1 | **Nháp** (Draft) | 0 | NV kinh doanh / Quản lý | Vừa tiếp nhận yêu cầu (call/Zalo/Email/app), chưa đối chiếu xong |
| 2 | **Đã phân loại** (Triaged) | 0 | Quản lý | Đã đối chiếu HĐ (BR-01); nếu ngoài thầu → cần duyệt |
| 3 | **Đã gán NV** (Assigned) | 0 | Quản lý | Gán `assigned_employee` + ưu tiên theo giờ mổ (SLA) |
| 4 | **Đang giao** (InTransit) | 0 | NV kinh doanh | NV lên đường (GPS check-in tại BV) |
| 5 | **Đã bàn giao** (Delivered) | **1** (submit) | NV kinh doanh | Ký số + ≥2 ảnh + GPS → **submit**; chốt `consumed/returned`, phát SLA, kích M06 |
| 6 | **Đã đóng** (Closed) | 1 | Quản lý / hệ thống | Đã sinh chứng từ + đơn (M06/M09) xong |
| — | **Từ chối** (Rejected) | 0/2 | Quản lý | Hủy yêu cầu (BV hủy ca, ngoài thầu không duyệt) |

**Transitions chính (đề xuất):**
- `Nháp → Đã phân loại` (Quản lý/NV; chạy đối chiếu BR-01).
- `Đã phân loại → Đã gán NV` (Quản lý; nếu `out_of_contract_flag` thì yêu cầu `out_of_contract_approved_by` trước).
- `Đã phân loại → Từ chối` (Quản lý).
- `Đã gán NV → Đang giao` (NV kinh doanh; ghi `AntMed SLA Log` event=EnRoute).
- `Đang giao → Đã bàn giao` (NV kinh doanh; **bắt buộc** chữ ký + ảnh + GPS — gate ở controller, xem BR §4; transition này = **submit**, docstatus 0→1).
- `Đã bàn giao → Đã đóng` (hệ thống/Quản lý sau khi M06 sinh chứng từ).

> Mỗi transition phát một bản ghi `AntMed SLA Log` (event/ts/lag_sec). State `Đã bàn giao` đặt `docstatus=1` để khoá sửa (chứng cứ bàn giao bất biến) → liên kết BR-07 (chặn xóa DO đã ký).

---

## 4. Business Rules

> Enforce theo **Frappe-standard**: rule trong **module hooks** (`antmed_crm/antmed/m04_delivery_hooks.py` hoặc controller `antmed_delivery.py`) wired qua `doc_events` trong `antmed_crm/hooks.py`; lỗi nghiệp vụ = `frappe.throw(_("BR-XX: …tiếng Việt"))`. Adapt vị trí enforce từ README (cột "Vị trí" — đổi `AM Delivery Request`/`Delivery Note`→`AntMed Delivery`, `api/delivery`→`antmed_crm.api.antmed.delivery`).

| BR | Mô tả | Nơi enforce (đề xuất, native-lite) |
|---|---|---|
| **BR-01** | **Đối chiếu danh mục trúng thầu**: mọi `AntMed Delivery Item.item` phải thuộc danh mục vật tư trúng thầu của hợp đồng còn hiệu lực của BV (M02). Ngoài danh mục → set `out_of_contract_flag=1` + cảnh báo; chặn chuyển `Đã gán NV` cho tới khi `out_of_contract_approved_by` (Quản lý duyệt). | `AntMed Delivery.validate` (controller) — đối chiếu `AntMed Contract`/`AntMed Quota Item` của M02. *(scaffold: `AM Delivery Request.validate`)* |
| **BR-06** | **Khoá quota chạm trần**: tổng SL đã giao + SL yêu cầu không vượt quota dòng hợp đồng (100% lock). Vượt → `frappe.throw`. | `AntMed Delivery.validate` (khi submit `Đã bàn giao`, đối chiếu lũy kế quota M02). *(scaffold: `Delivery Note.validate quota 100% lock`)* |
| **BR-08** | **Gợi ý/cảnh báo FIFO–HSD**: khi chọn `lot` cho item, hệ thống gợi ý lot theo FIFO/HSD gần nhất (M03); chọn lot không-FIFO hoặc cận/hết HSD → **cảnh báo** (warn, không chặn cứng). | `antmed_crm.api.antmed.delivery.fifo_suggest` + `AntMed Delivery.validate` (warn). *(scaffold: `api/delivery.fifo_suggest + check_fifo warn`)* |
| **BR-07** | **Chặn xóa DO đã ký/đã bàn giao**: `AntMed Delivery` ở trạng thái `Đã bàn giao`/`Đã đóng` (docstatus=1, có chữ ký) **không được xóa** — bằng chứng pháp lý. | `AntMed Delivery.on_trash` → `frappe.throw`. *(scaffold: `block_delete_signed_do trên Delivery Note.on_trash`)* |
| **BR-10** | **Audit hash-chain**: thao tác gán/submit/đóng + hash chữ ký (`AntMed DO Signature.hash_sha256`) ghi `AntMed Audit Log` (M14). | lazy-import `antmed_crm.api.antmed` M14 trong `doc_events` (`on_update`/`on_submit`). [PLANNED — phụ thuộc M14] |
| **BR-13** | **Data-scope**: NV kinh doanh chỉ thấy `AntMed Delivery` của BV được giao / của chính mình (`assigned_employee`). | `permission_query_conditions` cho `AntMed Delivery` (M14/W4). **[ROADMAP]** — W2 chỉ giữ invariant `count == rows`; data-scope hoãn (như ADR-M01-05). |

> **Invariant kỹ thuật bắt buộc** (gate, không phải BR nghiệp vụ): list endpoint giữ **count == rows** (`get_list(pluck=…, limit_page_length=0)` để khi W4 thêm `permission_query_conditions` không vỡ contract).

---

## 5. API

> File: `antmed_crm/api/antmed/delivery.py`. Mọi hàm `@frappe.whitelist(methods=["GET"|"POST"])`, **type-annotated** (`antmed_crm/hooks.py:require_type_annotated_api_methods`), trả **RAW dict/list** (KHÔNG `_ok/_err` envelope). Lỗi nghiệp vụ/permission = `frappe.throw(...)` in-handler. Đường gọi `antmed_crm.api.antmed.delivery.<fn>`.

| Endpoint (đề xuất) | Verb | Mô tả |
|---|---|---|
| `antmed_crm.api.antmed.delivery.list_deliveries` | GET | List phiếu giao (filter: `workflow_state`, `hospital`, `assigned_employee`, khoảng `surgery_datetime`, `sla_status`). Trả `{data, total_count}`; **count == rows** khi không phân trang. Field item: `name, hospital, hospital_name, doctor, surgery_datetime, sla_minutes, workflow_state, assigned_employee, sla_status, out_of_contract_flag`. |
| `antmed_crm.api.antmed.delivery.get_delivery` | GET | Chi tiết 1 phiếu giao + `items` (gồm `requested/delivered/consumed/returned_qty`, `lot`), `photos`, `signatures`, GPS, SLA. `frappe.throw(PermissionError)` nếu thiếu read-perm. |
| `antmed_crm.api.antmed.delivery.create_request` | POST | Tạo `AntMed Delivery` (Nháp) từ yêu cầu (source/hospital/doctor/surgery_datetime/items). Chạy BR-01 đối chiếu → trả về `out_of_contract` cảnh báo nếu có. |
| `antmed_crm.api.antmed.delivery.fifo_suggest` | GET | Với `hospital`/`assigned_employee`/`item` → gợi ý lot theo FIFO/HSD (M03 native), cảnh báo cận/hết HSD (BR-08). Trả list lot {`lot`, `qty_available`, `expiry`, `co_cq_status`}. |
| `antmed_crm.api.antmed.delivery.assign` | POST | Gán `assigned_employee` + chuyển `Đã gán NV` (gate BR-01: nếu ngoài thầu phải đã duyệt). Ghi `AntMed SLA Log` (Assigned). |
| `antmed_crm.api.antmed.delivery.start_transit` | POST | Chuyển `Đang giao` + GPS check-in. Ghi `AntMed SLA Log` (EnRoute). |
| `antmed_crm.api.antmed.delivery.handover` | POST | Bàn giao: nhận `signatures` (≥1), `photos` (≥2), `gps_*`, `consumed/returned_qty` từng item → **submit** (`Đã bàn giao`), tính `sla_status` (so `delivered_at` vs `surgery_datetime`), ghi `AntMed SLA Log` (Delivered). Gate bắt buộc chữ ký + ảnh + GPS. |
| `antmed_crm.api.antmed.delivery.dispatch_board` | GET | Dữ liệu kanban điều phối: nhóm theo `workflow_state` (Mới tiếp nhận/Đã gán NV/Đang giao/Đã bàn giao) + đồng hồ đếm ngược tới `surgery_datetime`. |

> Bất biến **count == rows** áp cho `list_deliveries` (và mọi list). `handover`/`assign`/`start_transit` là POST đổi trạng thái → kiểm `frappe.has_permission(..., "submit"/"write")` + tôn trọng transition workflow.

---

## 6. Integration

**Vào (M04 phụ thuộc — đọc/đối chiếu, lazy-import + truyền PK):**
- **M01**: `AntMed Delivery.hospital → AntMed Hospital`, `doctor → AntMed Doctor` (Link). FE resolve `hospital_name` để hiển thị.
- **M02**: BR-01/BR-06 đọc `AntMed Contract` + dòng `AntMed Quota Item` của BV để đối chiếu danh mục trúng thầu + lũy kế quota. Truyền **PK** (`contract`, `contract_item`), lazy-import module M02 trong hook, KHÔNG import vòng.
- **M03**: BR-08 đọc tồn lô/HSD (`AntMed Lot`, tồn theo bin native) để gợi ý FIFO; khi `Đã bàn giao` ghi giảm tồn kho cá nhân/ký gửi qua `AntMed Stock Entry` (truyền PK lot + qty consumed/returned).

**Ra (M04 cấp dữ liệu — qua `doc_events`):**
- **M06** (Chứng từ/HĐĐT): `AntMed Delivery.on_submit` (`Đã bàn giao`) → kích M06 sinh bộ chứng từ + đẩy job HĐĐT (lazy-import handler M06, truyền `delivery` PK). *(UI_Design §3.2 Bước 4: "đẩy job xuất HĐĐT — không cần thao tác".)*
- **M09** (Đơn/AR): `consumed_qty` từng item = **tiêu hao thực tế** → M09 lập đơn bán đúng thực tế (truyền PK delivery + dòng consumed). Gate: chỉ tạo đơn từ delivery đã `Đã bàn giao`.
- **M10** (KPI): `sla_status` (OnTime/Late) + `AntMed SLA Log` → KPI "giao đúng SLA".

**`doc_events` đề xuất (thêm vào `antmed_crm/hooks.py`, additive):**
```python
doc_events = {
  "AntMed Delivery": {
    "validate":  "antmed_crm.antmed.m04_delivery_hooks.validate_delivery",   # BR-01, BR-06, BR-08(warn)
    "on_submit": "antmed_crm.antmed.m04_delivery_hooks.on_handover",          # SLA, →M06, →M09, audit BR-10
    "on_trash":  "antmed_crm.antmed.m04_delivery_hooks.block_delete_signed",  # BR-07
  }
}
```

> **Compliance gate**: M06 chịu trách nhiệm gate CO/CQ/ĐKLH; M04 chỉ **cấp sự kiện** (delivery đã ký) + lot xuất để M06 gắn CO/CQ theo lô. M04 KHÔNG tự phát hành HĐĐT.

---

## 7. UI

> Vue 3 + frappe-ui SPA, gọi `antmed_crm.api.antmed.delivery.*`. Route mới **APPEND** vào `frontend/src/router.js` (lazy). KHÔNG đụng route CRM gốc. Nhãn 100% tiếng Việt qua `__()`. Mobile-first cho NV; desktop cho điều phối.

| Màn hình (UI_Design) | Route (đề xuất) | Page Vue | Role dùng |
|---|---|---|---|
| **Bảng điều phối ca giao** (kanban thời gian thực, 4 cột, đồng hồ đếm ngược) — §2.2 | `/antmed/dispatch` | `AntmedDispatchBoard.vue` | `Quản lý` |
| **Danh sách phiếu giao** (lọc state/BV/NV/SLA) | `/antmed/deliveries` | `AntmedDeliveries.vue` | `Quản lý`, `NV kinh doanh` |
| **Chi tiết phiếu giao** (items, GPS, ảnh, chữ ký, SLA) | `/antmed/deliveries/:name` | `AntmedDeliveryDetail.vue` | tất cả role M04 |
| **Wizard "Bắt đầu giao hàng phòng mổ"** (4 bước: Xác nhận yêu cầu → Quét lấy hàng FIFO → Bàn giao (GPS+ký+ảnh) → Sinh chứng từ) — §3.2 | `/antmed/deliveries/:name/handover` (hoặc modal Stepper) | `AntmedDeliveryHandover.vue` | `NV kinh doanh` (mobile) |

- **Kanban** (§2.2): thẻ hiển thị BV, bác sỹ, giờ mổ, NV, **đồng hồ đếm ngược** (xanh ≥1h, cam <1h, đỏ trễ — accent cam `#F97316` cho cảnh báo SLA). Kéo-thả thẻ → modal xác nhận gán NV + check tồn kho NV đang giữ.
- **Wizard mobile** (§3.2): Stepper 4 bước; cảnh báo đỏ nếu vật tư **ngoài danh mục HĐ** (BR-01); quét QR/barcode lấy lot (cảnh báo FIFO BR-08); **Signature pad** + bắt buộc **≥2 ảnh** + GPS auto check-in; lựa chọn "Hoàn tất / một phần — còn lại trả kho ký gửi" (→ `consumed`/`returned`).
- Component dùng: Stepper, Signature pad, Scanner overlay, Status pill (state workflow VI), DatePicker preset giờ ca, Table sticky. Mỗi resource có loading/error/empty; A11y AA; thao tác submit (bàn giao) có double-confirm + audit.
- **Cấm**: axios/tanstack/`frappe.client.*` trực tiếp; `crm.api.*` (namespace cũ — đúng là `antmed_crm.api.antmed.*`); sửa route/page/store CRM gốc.

---

## 8. Build slices (cho factory — mỗi slice 1 vòng)

> Tuân thứ tự phụ thuộc: M01/M02/M03 phải có DocType ổn trước. TDD failing-first; KHÔNG commit (HARD-STOP user).

1. **S1 — Schema + workflow nền**: tạo `AntMed Delivery` (+ child `AntMed Delivery Item`, `AntMed DO Photo`, `AntMed DO Signature`) + `AntMed SLA Log` + `AntMed OR Schedule`; fixture `workflow.json` (`AntMed DR Workflow` 6 state VI). `bench migrate` → verify DocType + workflow tồn tại + naming `AntMed-DR-…`. DocPerm cho 3 role VI.
2. **S2 — API list/detail + BR-01**: `list_deliveries` (count==rows) + `get_delivery` + `create_request` + `validate_delivery` (BR-01 đối chiếu danh mục thầu M02). Test BE failing-first.
3. **S3 — Vòng đời + SLA**: `assign`/`start_transit`/`handover` (chuyển state, gate chữ ký+ảnh+GPS, tính `sla_status`, ghi `AntMed SLA Log`); BR-07 (chặn xóa DO đã ký). Smoke từng transition.
4. **S4 — FIFO + quota**: `fifo_suggest` + BR-08 (warn) + BR-06 (khoá quota) — phụ thuộc M03/M02 sẵn sàng.
5. **S5 — FE list + detail + kanban điều phối**: `AntmedDeliveries.vue`, `AntmedDeliveryDetail.vue`, `AntmedDispatchBoard.vue` + 3 route. vitest + build.
6. **S6 — FE wizard bàn giao mobile** (Stepper 4 bước, Signature pad, scanner, GPS, ảnh).
7. **S7 — Integration ra hạ nguồn**: `doc_events on_submit` → M06 (chứng từ/HĐĐT) + M09 (đơn từ consumed) + audit BR-10 (khi M06/M09/M14 sẵn sàng).

---

## 9. ADRs

### ADR-M04-01: Hợp nhất `AntMed Delivery` (DR + bàn giao) thay vì tách DR + `Delivery Note`
- **Status**: Proposed (chốt khi BA-gate M04)
- **Date**: 2026-06-17
- **Context**: Scaffold app-cũ tách `AM Delivery Request` (yêu cầu, submittable) + gắn GPS/ký/ảnh vào `AM DO Extras` (autoname theo **`Delivery Note`** của ERPNext). Native-lite (D1=B) **không có** ERPNext `Delivery Note`. Vòng đời giao phòng mổ AntMed là một mạch liền: tiếp nhận → gán → đi giao → bàn giao ký số.
- **Decision**: Một DocType **`AntMed Delivery`** mang trọn vòng đời + workflow; GPS/ký/ảnh là field + child (`AntMed DO Photo`/`AntMed DO Signature`) ngay trên nó. State `Đã bàn giao` = submit (docstatus 1) khoá sửa.
- **Alternatives**: (a) giữ 2 DocType (DR + Delivery) như scaffold — loại: dư thừa khi không có `Delivery Note` gốc, thêm join. (b) tái dùng ERPNext `Delivery Note` — loại: vi phạm D1 native-lite.
- **Consequences**: (+) một vòng đời/một workflow, đơn giản truy vết SLA; (+) audit/chặn-xóa rõ ràng qua docstatus. (−) phải tự code chuyển tồn kho khi bàn giao (qua `AntMed Stock Entry` M03).

### ADR-M04-02: Workflow Frappe-native + state field `workflow_state` (VI)
- **Status**: Proposed
- **Date**: 2026-06-17
- **Context**: M04 cần state machine có gán role/điều kiện (DEC D2). Scaffold dùng field `status` (Select tĩnh, không gán role).
- **Decision**: Dùng **Frappe Workflow gốc** (fixture `workflow.json`) với `workflow_state`, 6 state VI + transition gán role VI + map `docstatus` (Delivered→1). KHÔNG dùng `workflowcore`.
- **Consequences**: (+) chuẩn Frappe, transition có quyền + log. (−) phải bảo trì fixture workflow; nhãn VI là định danh state (lưu ý i18n).

> Kế thừa **ADR-M01-01** (app RIÊNG `antmed_crm`; gốc: in-place; THỰC TẾ = app RIÊNG `antmed_crm`), **ADR-M01-02** (prefix `AntMed `), **DEC-2026-06-17-A** (role VI), **DEC-2026-06-17-B** (route AntMed riêng), **ADR-M01-05** (hoãn data-scope BR-13, giữ count==rows) — không Supersede.

---

## 10. Acceptance / DoD

Theo **SPEC §6**. Một slice M04 "xong" khi:

1. **BE run-tests**: `bench --site miyano run-tests --module antmed_crm.tests.test_antmed_delivery` → **`Ran N tests … OK`**, 0 fail. TC tối thiểu:
   - `AntMed Delivery` + child + `AntMed SLA Log`/`AntMed OR Schedule` tồn tại sau migrate, đủ field tối thiểu; naming sinh `AntMed-DR-…`.
   - Workflow `AntMed DR Workflow` load; transition hợp lệ `Nháp→…→Đã bàn giao` chạy; transition không-được-phép bị chặn.
   - BR-01: item ngoài danh mục thầu → set `out_of_contract_flag` + chặn `assign` khi chưa duyệt.
   - BR-06: vượt quota → `frappe.throw("BR-06: …")`. BR-07: xóa DO `Đã bàn giao` → `frappe.throw`.
   - `handover` thiếu chữ ký/ảnh/GPS → throw; đủ → submit + `sla_status` đúng (so giờ mổ).
   - `list_deliveries`: trả `{data,total_count}`, **`len(data)==total_count`** khi không phân trang.
   - Permission: user thiếu read-perm gọi `get_delivery` → `frappe.PermissionError`.
2. **FE**: `yarn vitest run` xanh (route `/antmed/dispatch|deliveries|...` tồn tại + lazy; gọi đúng `antmed_crm.api.antmed.delivery.*`; KHÔNG `antmed_crm.api`/axios/tanstack) + `yarn build` xanh (chunk `Antmed*` không vỡ).
3. **Pixel verify** (sau USER reload gunicorn): `http://miyano/crm/antmed/dispatch` render kanban thật + đồng hồ đếm ngược; mở 1 phiếu → wizard bàn giao (ký + ảnh + GPS); 0 console error; API 200.
4. **No-regression**: bootstrap M01 + 4 test gốc CRM (Lead/Task/Territory/org-hierarchy) vẫn xanh; route/doctype CRM gốc nguyên vẹn.

> Chưa pixel-verify ⇒ chỉ "contract verified", chưa "xong".

---

## Tham chiếu chéo
- Spec & Plan cấp dự án: `../SPEC_AntMed_CRM.md` (§6 DoD, §8 ADR), `../PLAN_AntMed_CRM.md` (§2 DAG, §3 Wave W2, D1/D2 locked).
- Mô tả nghiệp vụ: `../../antmed_crm/docs/AntMed_CRM_Modules.md` **§4 "Module Giao hàng & Bàn giao Phòng mổ"** (ground-truth feature).
- UI 7 vai trò: `../../antmed_crm/docs/AntMed_CRM_UI_Design.md` §2.2 (kanban điều phối), §3.2 (wizard giao 4 bước mobile).
- House style: `./m01_customer360.md`.
- Module liên quan (DAG): M01 (`AntMed Hospital`/`AntMed Doctor`), M02 (Contract/Quota — BR-01/06), M03 (Item/Lot/Stock Entry — BR-08), M06 (chứng từ/HĐĐT — `on_submit`), M09 (đơn từ `consumed_qty`), M10 (KPI SLA), M14 (audit BR-10, data-scope BR-13).
- Scaffold tham chiếu (app-cũ, đã adapt AM→AntMed + ERPNext→native-lite): `docs/antmed_crm/antmed_crm/m04_or_delivery/doctype/` (`am_delivery_request`, `am_delivery_request_item`, `am_do_extras`, `am_do_photo`, `am_do_signature`, `am_sla_log`).
- BR enforcement gốc (đã adapt vị trí): `docs/antmed_crm/README.md` §12 (BR-01/02/06/07/08/10/13).
