# M12 — Mobile App cho NV Kinh doanh (PWA) (Core Doc)

| Mục | Giá trị |
|---|---|
| Module folder | `antmed_crm/antmed/` (server-side phụ trợ) + **FE layer** `apps/antmed_crm/frontend/src` (PWA) |
| Code path BE | `antmed_crm/antmed/doctype/antmed_mobile_*/` + endpoint `antmed_crm/api/antmed/mobile_sync.py` (đường gọi `antmed_crm.api.antmed.mobile_sync.<fn>`) |
| Code path FE | `frontend/src/pages/AntmedMobile*.vue` · `frontend/src/data/mobileSync.js` · `frontend/src/sw.js` (service worker) · `frontend/src/utils/outbox.js` (IndexedDB) · route `/antmed/m/*` |
| Wave (PLAN) | **W4 — Tăng trưởng & kiểm soát** (cross-cutting / aggregate, làm sau cùng) |
| Role chính (VI) | `NV kinh doanh` (giao diện chính ngoài hiện trường) · `Quản lý` (chỉ giám sát sync log) |
| Phụ thuộc (M..) | **M01** (KH/Bác sỹ), **M04** (Giao phòng mổ / DO), **M05** (Bộ dụng cụ mượn) |
| Cấp dữ liệu cho (M..) | — (M12 là tầng FE tiêu thụ + ghi xuyên qua API của M01/M04/M05; không sinh dữ liệu master mới) |
| Trạng thái | **[PLANNED — chưa code]** (FE PWA layer; DocType server-side tùy chọn nếu cần outbox/sync-log phía server) |
| Cập nhật | 2026-06-17 |

> **Trạng thái: [PLANNED — chưa code]**
>
> M12 là **tầng giao diện (FE PWA)** dựng TRÊN các slice nghiệp vụ đã có (M01/M04/M05). Nó **không phải** một app riêng và **không** đẻ ra domain mới — nó gói lại các luồng "ngoài hiện trường" thành trải nghiệm offline-first. Mọi schema/API/workflow dưới đây là **DESIGN (đề xuất)**, chưa code. M12 chỉ khởi động khi M01/M04/M05 đã land (xem §6 Integration & §8 Build slices).

---

## 1. Overview

M12 là **giao diện chính của NV kinh doanh** — theo `AntMed_CRM_Modules.md §12`, app điện thoại là *giao diện chính* của đội kinh doanh vì họ làm việc ngoài hiện trường (bệnh viện / phòng mổ). Theo `AntMed_CRM_UI_Design.md §3` ("màn hình quan trọng nhất"), bối cảnh là **đôi khi mất sóng → offline-first** (phòng mổ hay chặn sóng).

Phạm vi nghiệp vụ M12 (ground @ Modules §12):
- **Lấy hàng từ kho cá nhân** (quét QR/barcode) → luồng dữ liệu của **M03/M04**.
- **Giao cho phòng mổ** (ký số trên màn cảm ứng, chụp ảnh, GPS check-in) → **M04** Delivery/DO.
- **Mượn/trả bộ dụng cụ + checklist bàn giao** (chụp ảnh từng bước) → **M05** Instrument Loan.
- **Tra cứu hợp đồng/giá trúng thầu tại chỗ** khi bác sỹ hỏi → đọc M01/M02 (read-only).
- **Offline-first**: ghi nhận khi mất mạng, **sync khi có mạng** (outbox + delta pull).
- **Đẩy thông báo** (push): yêu cầu mới, bộ mượn quá hạn, công nợ chạm ngưỡng.

**Quyết định kiến trúc Phase 1 (chốt theo brief):** PWA offline-first = **service worker + IndexedDB outbox** TRÊN SPA Vue 3 / frappe-ui hiện có. **KHÔNG React Native ở Phase 1** (xem ADR-M12-01). Sync delta qua endpoint `antmed_crm.api.antmed.mobile_sync.*` (đề xuất).

**Business value:** NV kinh doanh thao tác liền mạch tại phòng mổ kể cả khi mất sóng; thao tác xếp hàng cục bộ và tự đồng bộ — giảm rủi ro mất dữ liệu giao hàng / checklist bộ mượn ngay tại chỗ chặn sóng.

**User stories:**
- *Là NV kinh doanh*, tại phòng mổ mất sóng, tôi muốn **ký số bàn giao DO + chụp ảnh** và app **lưu cục bộ**, để khi ra khỏi phòng mổ có sóng nó **tự đồng bộ** lên server mà tôi không phải làm lại.
- *Là NV kinh doanh*, tôi muốn **quét QR lot** để tự tick vật tư lấy từ kho cá nhân (kèm HSD + trạng thái CO/CQ), để không nhập tay sai lot.
- *Là NV kinh doanh*, tôi muốn **checklist bàn giao bộ dụng cụ** (tick từng món + ảnh + chữ ký bác sỹ) hoạt động offline, để hoàn tất mượn/trả ngay tại chỗ.
- *Là Quản lý*, tôi muốn xem **nhật ký đồng bộ** (ai sync, hướng nào, có xung đột không) để chẩn đoán khi NV báo "mất dữ liệu".

> ⚠️ M12 **không** định nghĩa lại workflow giao phòng mổ (M04) hay vòng đời bộ mượn 7 trạng thái (M05). Nó **gọi lại** API/workflow của các module đó qua lớp sync. Nếu một thao tác offline tạo/sửa DO hay phiếu mượn, server vẫn chạy **đúng** controller + `doc_events` của M04/M05 (business rule là SSoT ở đó).

---

## 2. DocTypes (native-lite, [PLANNED])

> M12 là **FE layer** → phần lớn không cần DocType mới. Chỉ thêm DocType server-side khi cần **trạng thái phía server** cho: (a) idempotency của outbox khi push, (b) nhật ký đồng bộ để chẩn đoán, (c) đăng ký thiết bị cho push notification. Ground @ reference scaffold `docs/antmed_crm/antmed_crm/m12_mobile/doctype/` (3 DocType: `am_mobile_device`, `am_mobile_offline_queue`, `am_mobile_sync_log`) → **ADAPT** `AM `→`AntMed `, module `M12 Mobile`→`AntMed`, role `AM System Admin`→VI roles, native-lite.

| DocType (ĐỀ XUẤT) | Loại | Field chính (ĐỀ XUẤT — grounded scaffold + Modules §12) | Naming |
|---|---|---|---|
| `AntMed Mobile Device` | master/log | `device_id` (Data, reqd, unique), `user` (Link User), `push_token` (Data — token push, scaffold gọi `fcm_token` [UNVERIFIED nhà cung cấp push, xem §6]), `platform` (Data), `app_version` (Data), `last_seen` (Datetime) | `autoname: field:device_id` (naming_rule = By fieldname) |
| `AntMed Mobile Offline Queue` | txn/log (server-side mirror của outbox khi push) | `idempotency_key` (Data, reqd, **unique** — chống xử lý trùng), `user` (Link User), `operation` (Data — vd `create_delivery`/`sign_do`/`loan_checklist`), `payload_json` (Long Text), `status` (Select `Pending`\n`Processed`\n`Failed`, default `Pending`), `ts_received` (Datetime, default now), `ts_processed` (Datetime), `error_log` (Long Text — thêm so với scaffold để chẩn đoán) | `autoname: field:idempotency_key` |
| `AntMed Mobile Sync Log` | log | `user` (Link User), `direction` (Select `Pull`\n`Push`), `doctype_synced` (Data), `record_count` (Int), `ts` (Datetime), `status` (Select `OK`\n`Conflict`\n`Failed`, default `OK`), `error_log` (Long Text) | `autoname: hash` (naming_rule = Random) |

**Ghi chú thiết kế:**
- 3 DocType trên là **tùy chọn (server-side)**. Nếu Phase-1 chọn outbox **thuần FE** (IndexedDB) + push qua API nghiệp vụ sẵn có, có thể **bỏ** `AntMed Mobile Offline Queue` (idempotency xử lý bằng key trong endpoint `apply_outbox`). Khuyến nghị tối thiểu giữ **`AntMed Mobile Sync Log`** (chẩn đoán) + **`AntMed Mobile Device`** (push). `[cần khảo sát]` mức độ cần server-side queue.
- **KHÔNG** submittable (`is_submittable = 0`), **KHÔNG** workflow — đây là master/log kỹ thuật, không phải chứng từ nghiệp vụ. `track_changes = 1` (audit nhẹ).
- `payload_json` chỉ là **bản sao tạm** của thao tác; bản ghi nghiệp vụ thật (DO/phiếu mượn) vẫn nằm ở DocType của M04/M05. M12 **không** là nguồn sự thật cho nghiệp vụ.

---

## 3. Workflow

**Không có workflow nghiệp vụ riêng cho M12.** M12 không có state machine của riêng nó — nó **tái sử dụng** workflow của các module nguồn:
- Giao phòng mổ / DO: workflow của **M04** (Frappe-native, `docstatus` + `workflow_state` tiếng Việt).
- Mượn/trả bộ dụng cụ: workflow vòng đời bộ mượn của **M05**.

Các field `status` trên `AntMed Mobile Offline Queue` (`Pending/Processed/Failed`) và `AntMed Mobile Sync Log` (`OK/Conflict/Failed`) chỉ là **trạng thái kỹ thuật của hàng đợi/log đồng bộ** (chuyển đổi bằng code khi xử lý outbox), **không phải** Frappe Workflow và **không** dùng `docstatus`.

---

## 4. Business Rules

M12 **không thêm BR nghiệp vụ "cứng" mới** — mọi BR thực sự (BR-01 đối chiếu danh mục trúng thầu, BR-06 quota, FIFO/HSD, CO/CQ gate…) được **enforce phía server** trong controller + `doc_events` của M04/M05/M02 khi outbox được áp. M12 chỉ đặt **invariant kỹ thuật** của tầng đồng bộ:

| Mã | Mô tả | Nơi enforce |
|---|---|---|
| BR-M12-1 (kỹ thuật) | **Idempotency**: cùng một `idempotency_key` push nhiều lần (do retry khi chập chờn sóng) chỉ tạo/áp **đúng một** bản ghi nghiệp vụ. | endpoint `antmed_crm.api.antmed.mobile_sync.apply_outbox` (check `idempotency_key` unique trên `AntMed Mobile Offline Queue` hoặc tra cờ đã xử lý trước khi gọi API M04/M05) |
| BR-M12-2 (kỹ thuật) | **Server là trọng tài BR**: khi áp outbox, mọi `frappe.throw(_("BR-XX: …"))` của M04/M05 vẫn chạy. Nếu fail → ghi `status=Failed` + `error_log`, **trả lỗi về FE** để hiển thị, KHÔNG nuốt lỗi. | `apply_outbox` (lazy-import controller M04/M05) |
| BR-M12-3 (kỹ thuật) | **Data-scope kế thừa BR-13**: pull delta chỉ trả các bản ghi user **được phép đọc** (qua `frappe.get_list` + permission engine / `permission_query_conditions` của M04/M05). Giữ invariant **count == rows**. | endpoint `pull_changes` (dùng `get_list(..., limit_page_length=0)`) |
| BR-M12-4 (kỹ thuật) | **Xung đột (conflict)**: nếu bản ghi server đã đổi sau timestamp client mang theo → đánh dấu `Conflict` trong sync log, **không ghi đè mù**; trả về cho FE xử lý (last-write-wins có cảnh báo, hoặc để Quản lý quyết). | `apply_outbox` / `pull_changes` |

> M12 **không** tự kiểm BR-01/BR-06/FIFO/HSD/CO-CQ — đó là trách nhiệm của M02/M03/M04/M05. Đây là nguyên tắc "server là SSoT cho nghiệp vụ" để tránh nhân đôi luật ở FE (dễ lệch).

---

## 5. API

> File ĐỀ XUẤT: `antmed_crm/api/antmed/mobile_sync.py`, đường gọi `antmed_crm.api.antmed.mobile_sync.<fn>`. Mọi hàm `@frappe.whitelist(...)`, **type-annotated** (vì `antmed_crm/hooks.py` bật `require_type_annotated_api_methods`), trả **RAW dict/list** (KHÔNG `_ok/_err`/envelope). Lỗi nghiệp vụ = để `frappe.throw` của module nguồn nổi lên (Frappe trả exception JSON).

| Endpoint (ĐỀ XUẤT) | Verb | Mô tả |
|---|---|---|
| `antmed_crm.api.antmed.mobile_sync.bootstrap` | GET | Tải gói khởi tạo offline cho user hiện tại: tuyến BV/bác sỹ (M01), ca giao hôm nay (M04), bộ đang giữ (M05), tồn kho cá nhân (M03). Trả RAW dict gộp các list để FE nạp vào IndexedDB. **Mỗi list giữ count == rows** (`get_list(pluck=…, limit_page_length=0)`). |
| `antmed_crm.api.antmed.mobile_sync.pull_changes` | GET | **Sync delta** từ server về client: tham số `since` (datetime client mang theo) + danh sách doctype quan tâm. Trả `{ "data": {<doctype>: [..rows..]}, "server_ts": <now>, "deleted": [...] }`. Lọc theo permission của user (BR-M12-3). |
| `antmed_crm.api.antmed.mobile_sync.apply_outbox` | POST | **Push** danh sách thao tác offline đã xếp hàng. Body = `operations: list[dict]` mỗi op có `idempotency_key`, `operation`, `payload`. Với mỗi op: check idempotency (BR-M12-1) → lazy-import + gọi đúng API/controller M04/M05 → ghi `AntMed Mobile Sync Log`. Trả RAW `{ "results": [{"idempotency_key","status","name"?,"error"?}], "applied": int, "failed": int }`. |
| `antmed_crm.api.antmed.mobile_sync.register_device` | POST | Đăng ký/cập nhật `AntMed Mobile Device` (device_id, push_token, platform, app_version) cho user — phục vụ push notification. Trả RAW `{ "device_id": ... }`. |
| `antmed_crm.api.antmed.mobile_sync.scan_lot` | GET | Tra cứu 1 lot theo mã QR/barcode quét được (param `code`): trả `lot`, `item`, `hsd`/expiry, `co_cq_status`, tồn khả dụng trong kho cá nhân của user. Đọc dữ liệu M03 (read-only). Trả RAW dict (hoặc throw `frappe.DoesNotExistError` nếu mã không khớp). |

**Quy ước:**
- **Invariant count == rows**: `bootstrap` và `pull_changes` trả list KHÔNG được lệch số đếm; dùng `limit_page_length=0` và để permission engine lọc — `len(rows)` chính là tổng khớp filter (không cắt trang giữa chừng).
- `apply_outbox` là điểm **ghi** duy nhất; nó **không** chứa logic nghiệp vụ — chỉ điều phối tới M04/M05 và quản idempotency/log. Lỗi BR của module nguồn được phản ánh nguyên văn vào `results[].error`.
- Hai loại 403 như chuẩn dự án: dispatcher-403 (guest gọi → chặn vì không `allow_guest`) và in-handler permission-403 (`frappe.PermissionError` khi `has_permission` fail trên doc cụ thể).

---

## 6. Integration

**DAG phụ thuộc (PLAN):** M12 ← M01, M04, M05. M12 **cấp dữ liệu cho**: — (không có). M12 là **consumer/edge layer**.

- **Hướng VÀO (M12 đọc/gọi):**
  - **M01**: đọc `AntMed Hospital`/`AntMed Doctor` cho màn "Khách hàng" (UI §3.4) — read-only.
  - **M04**: `apply_outbox` gọi API/controller giao phòng mổ (tạo/ký DO, đính ảnh, GPS) — **lazy-import** module M04, **truyền PK** (name của DO/yêu cầu), KHÔNG import vòng.
  - **M05**: `apply_outbox` gọi API/controller mượn/trả bộ dụng cụ + checklist — lazy-import, truyền PK phiếu mượn.
  - **M03**: `scan_lot` đọc lot/HSD/CO-CQ/tồn kho cá nhân — read-only.
- **Hướng RA (`doc_events` từ M12):** M12 **không** đăng ký `doc_events` nghiệp vụ mới vào `antmed_crm/hooks.py`. Việc ghi `AntMed Mobile Sync Log` xảy ra **bên trong** `apply_outbox` (gọi tường minh), không qua hook chéo module → tránh phình `hooks.py`.
- **Lazy-import + truyền PK:** trong `apply_outbox`, import controller M04/M05 **trong thân hàm** (không ở top-level) và chỉ truyền **khóa chính** (doc name) + payload tối thiểu; để controller đó tự `get_doc` và chạy `doc_events`. Đây là cách giữ M12 không phụ thuộc cứng vào nội tại M04/M05.
- **Compliance gate:** M12 **không** tự gate CO/CQ/ĐKLH/HĐĐT. `scan_lot` chỉ **hiển thị** trạng thái CO/CQ (cảnh báo cho NV); việc **chặn** (gate) khi lot thiếu chứng từ là trách nhiệm controller M03/M04 lúc `apply_outbox` áp thao tác. M12 chỉ surface cảnh báo sớm để NV không quét nhầm.
- **Push notification:** `AntMed Mobile Device.push_token` + provider push. `[UNVERIFIED]` nhà cung cấp push (scaffold dùng `fcm_token` ám chỉ Firebase Cloud Messaging; dự án có sẵn kênh Zalo/SMS — `[cần khảo sát]` chọn FCM hay Web Push API hay đẩy qua Zalo). Quyết định để [PLANNED] trong slice push (S4).

---

## 7. UI

> Vue 3 + frappe-ui SPA, **mobile-first** cho `NV kinh doanh` (UI_Design §0: mobile-first cho NV KD). Route mới APPEND vào `frontend/src/router.js` (lazy). Page đặt tên `AntmedMobile<Feature>.vue`. Gọi đúng `antmed_crm.api.antmed.mobile_sync.*` / `antmed_crm.api.antmed.<module>.*`. PWA: service worker + manifest + IndexedDB outbox.

### Routes (THÊM mới — lazy import; prefix `/antmed/m/` cho lớp mobile)

| path | name | component | mô tả (nguồn UI_Design §3) |
|---|---|---|---|
| `/antmed/m` | `AntmedMobileHome` | `pages/AntmedMobileHome.vue` | Home: ca giao hôm nay, bộ đang giữ, tồn kho cá nhân, doanh số tháng, chuông thông báo (§3.1) |
| `/antmed/m/deliver/:name` | `AntmedMobileDeliver` | `pages/AntmedMobileDeliver.vue` | Luồng "Bắt đầu giao hàng phòng mổ" 4 bước: xác nhận → quét lấy hàng → ký số/ảnh/GPS → sinh chứng từ (§3.2). Dùng M04. |
| `/antmed/m/loans` | `AntmedMobileLoans` | `pages/AntmedMobileLoans.vue` | Bộ dụng cụ — Đang giữ / Lịch hẹn / Xử lý sau dùng + modal Checklist bàn giao (§3.3). Dùng M05. |
| `/antmed/m/customers` | `AntmedMobileCustomers` | `pages/AntmedMobileCustomers.vue` | CRM bác sỹ theo tuyến + profile + FAB "Ghi chú ghé thăm" (§3.4). Đọc M01. |
| `/antmed/m/sync` | `AntmedMobileSync` | `pages/AntmedMobileSync.vue` | Trạng thái offline: banner "Chế độ ngoại tuyến — N thao tác chờ đồng bộ", danh sách outbox, nút sync, toast kết quả (§3.5). |

**Thành phần PWA (FE):**
- `frontend/src/sw.js` — service worker: cache app shell (precache) + chiến lược network-first cho API GET có fallback cache; đăng ký qua `vite-plugin-pwa` hoặc `workbox` `[cần khảo sát chọn lib]`.
- `frontend/src/utils/outbox.js` — wrapper IndexedDB: enqueue thao tác (kèm `idempotency_key` sinh client), liệt kê, đánh dấu đã sync, retry.
- `frontend/src/data/mobileSync.js` — store domain dùng `createResource`/`createListResource` gọi `antmed_crm.api.antmed.mobile_sync.*`; điều phối pull→merge IndexedDB và flush outbox khi `navigator.onLine`.
- `manifest.webmanifest` — tên app, icon, `display: standalone`, theme color (để "Add to Home Screen").

**Boundaries UI:**
- **Always** lazy import các page mới; **Always** `__()` cho nhãn VN; loading/error/empty + **banner offline** rõ ràng cho mỗi resource.
- **Always** dùng frappe-ui resource (không axios trực tiếp); thao tác ghi khi offline → enqueue outbox, KHÔNG gọi API ngay.
- **Never** sửa route/layout/sidebar/page CRM gốc; **Never** gọi `crm.api.*` (đúng là `antmed_crm.api.antmed.*`); **Never** nhân đôi luật nghiệp vụ M04/M05 ở FE (chỉ gọi server).

---

## 8. Build slices (cho factory — mỗi slice một vòng, TDD)

> Tiền đề: M01 đã land (slice Customer 360°). **M04 và M05 phải land trước** các slice ghi của M12. Trước đó M12 chỉ làm được phần read-only/khung PWA.

1. **S1 — Khung PWA + bootstrap (read-only):** thêm `manifest.webmanifest` + `sw.js` (precache app shell) + route `/antmed/m` + `AntmedMobileHome.vue`. BE: `antmed_crm/api/antmed/mobile_sync.py::bootstrap` (RAW dict, count==rows). Test: route tồn tại, gọi đúng endpoint, build PWA xanh, SW đăng ký.
2. **S2 — Outbox engine + sync log:** `utils/outbox.js` (IndexedDB), `data/mobileSync.js`, page `/antmed/m/sync`. BE: DocType `AntMed Mobile Sync Log` (+ tùy chọn `AntMed Mobile Offline Queue`) + `pull_changes` + `apply_outbox` (khung idempotency, chưa nối M04/M05 — op test giả). Test: idempotency (push trùng key → 1 lần), count==rows cho `pull_changes`.
3. **S3 — Giao phòng mổ offline (nối M04):** page `/antmed/m/deliver/:name` 4 bước (quét QR `scan_lot`, ký số canvas, chụp ảnh, GPS). `apply_outbox` lazy-import controller M04. Test: thao tác offline → outbox → áp → DO tạo đúng + BR M04 vẫn enforce; lỗi BR phản ánh vào results.
4. **S4 — Bộ mượn offline (nối M05) + push:** page `/antmed/m/loans` + modal checklist; `apply_outbox` nối M05; `register_device` + `AntMed Mobile Device`; push provider (`[PLANNED]`). Test: checklist offline → sync; đăng ký thiết bị.
5. **S5 — Khách hàng (M01 read-only) + hoàn thiện conflict UX:** page `/antmed/m/customers` + FAB ghi chú; xử lý `Conflict` trong sync log + UX cảnh báo. Test: pull/merge, conflict surface.

---

## 9. ADRs

### ADR-M12-01: Phase-1 dùng **PWA (service worker + IndexedDB)** trên SPA Vue/frappe-ui, KHÔNG React Native
- **Status**: Accepted (chốt theo brief M12)
- **Date**: 2026-06-17
- **Context**: NV kinh doanh cần app mobile offline-first. Dự án đã có sẵn SPA Vue 3 + frappe-ui trong app riêng `apps/antmed_crm/frontend`. Làm React Native là một codebase + pipeline build/release thứ hai, lệch hẳn kiến trúc app-riêng đã chốt (ADR-M01-01; gốc: in-place — THỰC TẾ = app RIÊNG `antmed_crm`).
- **Decision**: Phase 1 = **PWA** trên SPA hiện có (precache app shell + IndexedDB outbox + sync delta). Native app (React Native) để **backlog Phase 2+** nếu nghiệp vụ camera/BLE/độ ổn định đòi hỏi.
- **Consequences**: (+) Một codebase, tái dùng route/store/resource đã có; ship nhanh; "Add to Home Screen". (−) Phụ thuộc khả năng PWA của trình duyệt thiết bị; push notification phức tạp hơn native (`[cần khảo sát]` provider). (−) Camera/QR qua Web API có thể kém ổn định hơn native — chấp nhận ở Phase 1.

### ADR-M12-02: **Server là trọng tài nghiệp vụ**; M12 không nhân đôi BR ở FE
- **Status**: Accepted
- **Date**: 2026-06-17
- **Context**: Thao tác offline rồi sync dễ cám dỗ việc copy luật (BR-01/quota/FIFO/HSD) xuống FE để "validate sớm". Điều này tạo hai nguồn sự thật, dễ lệch.
- **Decision**: M12 chỉ **xếp hàng** thao tác và **áp** chúng qua controller/`doc_events` của M04/M05 phía server (BR-M12-2). FE chỉ surface **cảnh báo mềm** (vd CO/CQ trong `scan_lot`), không chặn cứng.
- **Consequences**: (+) Một nguồn sự thật BR; offline không bao giờ "qua mặt" luật. (−) NV có thể xếp hàng thao tác mà server sẽ từ chối khi sync → cần UX hiển thị `Failed`/`Conflict` rõ ràng (slice S2/S5).

> Kế thừa: **ADR-M01-01** (gốc: in-place; THỰC TẾ = app RIÊNG `antmed_crm`) và **ADR-M01-02** (prefix `AntMed `) áp dụng nguyên vẹn cho M12. **DEC-A** (role VI) và **DEC-B** (route/app AntMed riêng cho boot) liên quan: page `/antmed/m/*` phải qua được gate boot của user AntMed thuần (`NV kinh doanh`).

---

## 10. Acceptance / DoD

> Theo SPEC §6. "Xong" một slice = BE test xanh + FE vitest xanh + build xanh + (sau USER reload) pixel verify + no-regression.

**BE (Frappe test runner — TDD failing-first):**
- File ĐỀ XUẤT: `antmed_crm/tests/test_antmed_mobile_sync.py`. Lệnh: `bench --site miyano run-tests --module antmed_crm.tests.test_antmed_mobile_sync` → **`Ran N tests … OK`**, 0 fail.
- TC tối thiểu: (1) `bootstrap()` trả RAW dict các list, **count == rows**; (2) `pull_changes(since=...)` trả delta đúng + lọc theo permission (count==rows, BR-M12-3); (3) `apply_outbox` **idempotency** — push trùng `idempotency_key` chỉ áp 1 lần (BR-M12-1); (4) `apply_outbox` áp op M04/M05 → bản ghi nghiệp vụ tạo đúng + **BR của module nguồn vẫn enforce** (lỗi BR phản ánh vào `results[].error`, status `Failed`); (5) `scan_lot(code)` trả lot/HSD/CO-CQ đúng, mã sai → `DoesNotExistError`; (6) (nếu có DocType) `AntMed Mobile Sync Log`/`Device` tồn tại sau migrate + naming đúng.
- **No-regression**: `test_antmed_bootstrap` + `test_antmed_customer` + 4 test gốc CRM (Lead/Task/Organization/Territory) vẫn xanh; KHÔNG đụng route/test gốc.

**FE (vitest + build):**
- File ĐỀ XUẤT: `frontend/tests/unit/antmedMobile.test.js`. Assertion: route `/antmed/m*` tồn tại (path/name/lazy); page gọi đúng `antmed_crm.api.antmed.mobile_sync.*`; outbox enqueue/flush logic unit-test; KHÔNG `antmed_crm.api`/axios/tanstack.
- `yarn build` xanh, SFC compile sạch, **service worker + manifest emit** không vỡ chunk cũ; route CRM gốc còn nguyên.

**Pixel / e2e (Playwright MCP, site `miyano` cổng 80, sau USER reload):**
- `/antmed/m` render Home thật (0 console error, API 200); mô phỏng offline (DevTools) → thao tác ký/checklist lưu outbox + banner "Chế độ ngoại tuyến"; bật mạng lại → tự sync + toast kết quả.

> ⚠️ Reload: thêm DocType + API → cần `bench --site miyano migrate` + **USER reload BE** (HARD-STOP). PWA: kiểm tra cache-busting service worker để client lấy bản mới.

---

## Tham chiếu chéo
- Spec & nguyên tắc: `../SPEC_AntMed_CRM.md` (§6 Testing, §7 Boundaries, §8 ADR đã chốt)
- Kế hoạch & DAG/Wave: `../PLAN_AntMed_CRM.md` (dòng M12: Mobile PWA offline-first, W4, phụ thuộc M01/M04/M05)
- Nghiệp vụ: `../../antmed_crm/docs/AntMed_CRM_Modules.md` §12 (Module Mobile App cho NV Kinh doanh)
- UI: `../../antmed_crm/docs/AntMed_CRM_UI_Design.md` §3 (Mobile App NV KD — màn hình quan trọng nhất; §3.1–3.5)
- House style + namespace/role/naming: `./m01_customer360.md`
- Module liên quan (sẽ land trước): M04 Giao phòng mổ/DO, M05 Bộ dụng cụ mượn, M03 Kho/Lot, M01 Customer 360° `[các Core Doc M03/M04/M05 — PLANNED, chưa viết]`
- Reference scaffold (OLD separate-app, chỉ tham khảo field-level — ADAPT `AM `→`AntMed `): `docs/antmed_crm/antmed_crm/m12_mobile/doctype/` (`am_mobile_device`, `am_mobile_offline_queue`, `am_mobile_sync_log`)
