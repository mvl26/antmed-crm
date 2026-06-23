# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M03 Slice M03-S1 — endpoint Vật tư & Tồn kho (catalog VTYT, read-only).

Đường gọi: antmed_crm.api.antmed.inventory.<fn> (xem m03_inventory.md §5).
Mọi hàm @frappe.whitelist(methods=["GET"]), type-annotated, trả RAW dict (KHÔNG
envelope). count==rows (BR-13): total_count đếm DƯỚI permission user (get_list).
Pattern mượn từ antmed_crm/api/antmed/contract.py (đã verify).
"""

import json

import frappe
from frappe import _
from frappe.utils import add_days, date_diff, getdate, nowdate

from antmed_crm.api.antmed._filters import coerce_filters

ITEM_DOCTYPE = "AntMed Item"
WAREHOUSE_DOCTYPE = "AntMed Warehouse"
LOT_DOCTYPE = "AntMed Lot"
HOSPITAL_DOCTYPE = "AntMed Hospital"
LEDGER_DOCTYPE = "AntMed Stock Ledger"
STOCK_ENTRY_DOCTYPE = "AntMed Stock Entry"

# M03-3 (mockup D2 "Kho ký gửi tại Bệnh viện"): hằng dùng chung BE↔FE.
CONSIGNMENT_WAREHOUSE_TYPE = "Ký gửi BV"
NEAR_EXPIRY_DAYS = 90  # cùng ngưỡng cho KPI + chip/highlight cận date (nhất quán mockup '38 ngày').
# Hyrum: thứ tự/khoá cố định để FE bind ổn định (KHÔNG đảo/đổi).
CONSIGNMENT_ROW_KEYS = ("sku", "item_name", "lot", "expiry_date", "system_qty", "near_expiry")
# M03-5 (mockup D2 hàng KPI 3 thẻ "Bệnh viện có ký gửi · Tồn ký gửi · Cận date ≤90 ngày"): khoá KPI
# cố định cho consignment_stock — FE bind 5 key ổn định (Hyrum, KHÔNG đảo/đổi/thêm bớt). Test đối chiếu shape.
CONSIGNMENT_KPI_KEYS = {
	"hospitals_with_consignment",
	"near_expiry_lots",
	"total_value",
	"total_sku",
	"total_lots",
}

# M03-4 (mockup D1 sidebar "⚠ Cảnh báo HSD" + D2 KPI "Cận date ≤90 ngày"): rollup lot cận/quá date
# trên TOÀN bộ kho (Tổng + Cá nhân NV + Ký gửi BV). Cùng ngưỡng 90 ngày với near_expiry consignment.
# severity = phân tầng ngày tới hạn (days_to_expiry): expired (<0) / d30 (0..30) / d60 (31..60) / d90 (61..90).
EXPIRY_BAND_D30 = 30
EXPIRY_BAND_D60 = 60
EXPIRY_BAND_D90 = 90
# Hyrum: khoá cố định mỗi dòng cảnh báo HSD (FE bind ổn định — KHÔNG đảo/đổi/thêm bớt).
EXPIRY_ROW_KEYS = (
	"sku",
	"item_name",
	"lot",
	"warehouse",
	"warehouse_name",
	"warehouse_type",
	"expiry_date",
	"balance_qty",
	"days_to_expiry",
	"severity",
)
# Hyrum: khoá KPI cố định (FE bind 4 KPI card + total_lots — KHÔNG đảo/đổi).
EXPIRY_KPI_KEYS = ("expired", "d30", "d60", "d90", "total_lots")

STOCK_ENTRY_ITEM_DOCTYPE = "AntMed Stock Entry Item"
# Field phiếu kho cho list endpoint (Hyrum — đổi/đảo thứ tự = breaking FE binding).
# nv_employee_name resolve User.full_name qua Link bằng dotted-fetch (null-guard FK orphan).
STOCK_ENTRY_LIST_FIELDS = [
	"name",
	"entry_type",
	"from_warehouse",
	"to_warehouse",
	"posting_datetime",
	"docstatus",
	"nv_employee",
	"nv_employee.full_name as nv_employee_name",
]
# Key BE-cũ (giữ shape, KHÔNG đảo) + key M03-1 THÊM (nv_employee/nv_employee_name/total_value).
STOCK_ENTRY_LIST_ITEM_KEYS = (
	"name",
	"entry_type",
	"from_warehouse",
	"to_warehouse",
	"posting_datetime",
	"docstatus",
	"nv_employee",
	"nv_employee_name",
	"total_value",
)

# M03-8 (mockup C2 Wizard bước 3 — card "Vật tư đã chuẩn bị") — chi tiết 1 phiếu xuất (drill-down từ
# list "Phiếu xuất gần đây"). Hyrum: khoá cố định header + dòng (FE bind ổn định — KHÔNG đảo/đổi/thêm bớt).
# Header = 11 khoá scalar (KHÔNG gồm `items` — items là khoá top-level riêng, list dòng vật tư).
# Tách header/items để FE bind 2 vùng (card header + bảng) ổn định + test đối chiếu shape riêng.
STOCK_ENTRY_DETAIL_HEADER_KEYS = (
	"name",
	"entry_type",
	"posting_datetime",
	"from_warehouse",
	"to_warehouse",
	"nv_employee",
	"nv_employee_name",
	"hospital",
	"hospital_name",
	"expected_use_date",
	"total_value",
)
STOCK_ENTRY_DETAIL_ITEM_KEYS = (
	"item",
	"item_name",
	"lot",
	"lot_no",
	"expiry_date",
	"qty",
	"uom",
	"unit_price",
	"amount",
	"cocq_ok",
)

# Field lô trả về cho list endpoint (Hyrum). item_name resolve qua Link bằng dotted-fetch.
LOT_LIST_FIELDS = [
	"name",
	"lot_no",
	"item",
	"item.item_name as item_name",
	"supplier",
	"expiry_date",
	"recall_status",
]
LOT_LIST_ITEM_KEYS = ("name", "lot_no", "item", "item_name", "supplier", "expiry_date", "recall_status")
# Shape mỗi dòng lô trong get_item.lots.
LOT_ROW_FIELDS = ("lot_no", "expiry_date", "recall_status", "co_cert", "cq_cert")

# Field chi tiết lô (mockup D3 left-card "Thông tin lot") cho get_lot.
# Đọc thẳng từ doc.as_dict(); item_name/supplier_name resolve riêng (dotted-fetch null-guard FK orphan).
# 3 aggregate qty_in/qty_out/qty_remaining tính từ AntMed Stock Ledger (antmed.stock.get_lot_movement).
LOT_DETAIL_FIELDS = (
	"name",
	"lot_no",
	"item",
	"supplier",
	"mfg_date",
	"expiry_date",
	"co_cert",
	"cq_cert",
	"recall_status",
	"recall_reason",
)

# M03-7 (mockup D3 action "⚠ Khởi tạo Recall theo lot này") — tập trạng thái recall hợp lệ khi
# Thủ kho KHỞI TẠO recall (KHÔNG gồm 'Bình thường' — không recall ngược về bình thường ở đây).
# Khớp EXACT subset options DocType AntMed Lot.recall_status (VI có dấu). Hyrum: FE bind đồng bộ
# (utils/antmedUi.js::RECALL_INITIATE_STATUSES) — đổi tập này = breaking FE.
RECALL_STATUS_OPTIONS = ("Theo dõi", "Đã thu hồi")
# Trạng thái terminal one-way: lô đã 'Đã thu hồi' → KHÔNG cho recall lại (idempotent guard).
RECALL_STATUS_RECALLED = "Đã thu hồi"

# M03-6 (mockup D3 right-card "Cây truy vết") — dòng thời gian di chuyển 1 lô.
# Hyrum: khoá cố định mỗi event (FE bind ổn định — KHÔNG đảo/đổi/thêm bớt). direction in|out.
LOT_TRACE_EVENT_KEYS = (
	"posting_datetime",
	"entry_type",
	"direction",
	"warehouse",
	"warehouse_name",
	"warehouse_type",
	"qty",
	"voucher_no",
	"hospital",
	"nv_employee",
)

# Field warehouse trả về cho list endpoint (Hyrum contract với FE).
WAREHOUSE_LIST_FIELDS = ["name", "warehouse_name", "warehouse_type", "employee", "hospital", "disabled"]
WAREHOUSE_LIST_ITEM_KEYS = (
	"name",
	"warehouse_name",
	"warehouse_type",
	"employee",
	"hospital",
	"disabled",
)

# Field item trả về cho list endpoint (Hyrum — đổi = breaking FE binding).
ITEM_LIST_FIELDS = [
	"name",
	"item_code",
	"item_name",
	"classification",
	"requires_cocq",
	"shelf_life_months",
]
ITEM_LIST_ITEM_KEYS = (
	"name",
	"item_code",
	"item_name",
	"classification",
	"requires_cocq",
	"shelf_life_months",
)
# Field chi tiết trả về cho get_item.
ITEM_DETAIL_FIELDS = (
	"name",
	"item_code",
	"item_name",
	"manufacturer_code",
	"registration_no",
	"ma_dkluuhanh",
	"requires_cocq",
	"shelf_life_months",
	"classification",
	"uom",
	"default_unit_price",
	"is_consignment",
	"disabled",
)


def _coerce_filters(filters: dict | str | None) -> list:
	"""Chuẩn hoá filters về list điều kiện (dict hoặc JSON-string từ FE/GET)."""
	return coerce_filters(filters)


@frappe.whitelist(methods=["GET"])
def list_items(
	filters: dict | str | None = None,
	search: str | None = None,
	start: int = 0,
	page_length: int = 20,
) -> dict:
	"""Danh mục VTYT. Trả RAW {data, total_count} — count==rows khi page_length=0.

	- search: khớp item_code HOẶC item_name (LIKE) qua or_filters.
	- filters: dict|JSON-string (vd classification, requires_cocq, disabled).
	- total_count đếm DƯỚI permission user (get_list, pluck) → giữ invariant count==rows.
	- Mỗi item gồm ĐÚNG 6 field: name, item_code, item_name, classification,
	  requires_cocq, shelf_life_months.
	"""
	conditions = _coerce_filters(filters)
	or_filters = None
	if search:
		or_filters = [["item_code", "like", f"%{search}%"], ["item_name", "like", f"%{search}%"]]

	start = max(0, int(start))
	page_length = max(0, int(page_length))

	rows = frappe.get_list(
		ITEM_DOCTYPE,
		filters=conditions,
		or_filters=or_filters,
		fields=ITEM_LIST_FIELDS,
		limit_start=start,
		limit_page_length=page_length or 0,
		order_by="item_code asc",
	)
	data = [{k: r.get(k) for k in ITEM_LIST_ITEM_KEYS} for r in rows]

	total_count = len(
		frappe.get_list(
			ITEM_DOCTYPE, filters=conditions, or_filters=or_filters, pluck="name", limit_page_length=0
		)
	)
	return {"data": data, "total_count": total_count}


@frappe.whitelist(methods=["GET"])
def get_item(name: str) -> dict:
	"""Chi tiết 1 VTYT + lots[] (lô CO/CQ/HSD). throw PermissionError nếu không read được.

	M03-S1: `lots` trả [] (DocType AntMed Lot chưa land — bổ sung ở slice M03 kế). Shape
	`lots` giữ ổn định (Hyrum) để FE bind sẵn không vỡ khi lô đổ vào.
	"""
	if not frappe.has_permission(ITEM_DOCTYPE, "read", doc=name):
		frappe.throw(_("Bạn không có quyền xem vật tư này."), frappe.PermissionError)

	doc = frappe.get_doc(ITEM_DOCTYPE, name).as_dict()
	result = {k: doc.get(k) for k in ITEM_DETAIL_FIELDS}
	# Lô của vật tư (A2: AntMed Lot đã land) — HSD sớm nhất trước.
	lots = frappe.get_list(
		LOT_DOCTYPE,
		filters={"item": name},
		fields=list(LOT_ROW_FIELDS),
		order_by="expiry_date asc",
		limit_page_length=0,
	)
	result["lots"] = [{k: r.get(k) for k in LOT_ROW_FIELDS} for r in lots]
	return result


@frappe.whitelist(methods=["GET"])
def list_warehouses(
	warehouse_type: str | None = None,
	filters: dict | str | None = None,
	start: int = 0,
	page_length: int = 20,
) -> dict:
	"""Danh sách kho (3 cấp). Trả RAW {data, total_count} — count==rows khi page_length=0.

	- warehouse_type: lọc nhanh theo loại kho (Tổng/Cá nhân NV/Ký gửi BV).
	- total_count đếm DƯỚI permission user (get_list, pluck) → giữ invariant count==rows.
	- Mỗi item gồm ĐÚNG 6 field: name, warehouse_name, warehouse_type, employee, hospital, disabled.
	"""
	conditions = _coerce_filters(filters)
	if warehouse_type:
		conditions.append(["warehouse_type", "=", warehouse_type])

	start = max(0, int(start))
	page_length = max(0, int(page_length))

	rows = frappe.get_list(
		WAREHOUSE_DOCTYPE,
		filters=conditions,
		fields=WAREHOUSE_LIST_FIELDS,
		limit_start=start,
		limit_page_length=page_length or 0,
		order_by="warehouse_name asc",
	)
	data = [{k: r.get(k) for k in WAREHOUSE_LIST_ITEM_KEYS} for r in rows]

	total_count = len(
		frappe.get_list(WAREHOUSE_DOCTYPE, filters=conditions, pluck="name", limit_page_length=0)
	)
	return {"data": data, "total_count": total_count}


@frappe.whitelist(methods=["GET"])
def list_lots(
	item: str | None = None,
	filters: dict | str | None = None,
	search: str | None = None,
	start: int = 0,
	page_length: int = 20,
) -> dict:
	"""Danh sách lô VTYT. Trả RAW {data, total_count} — count==rows khi page_length=0.

	- item: lọc nhanh theo vật tư.
	- search: khớp lot_no (LIKE).
	- Mỗi item gồm ĐÚNG 7 field: name, lot_no, item, item_name, supplier, expiry_date,
	  recall_status. item_name resolve qua Link bằng dotted-fetch (null-guard FK orphan).
	"""
	conditions = _coerce_filters(filters)
	if item:
		conditions.append(["item", "=", item])
	if search:
		conditions.append(["lot_no", "like", f"%{search}%"])

	start = max(0, int(start))
	page_length = max(0, int(page_length))

	rows = frappe.get_list(
		LOT_DOCTYPE,
		filters=conditions,
		fields=LOT_LIST_FIELDS,
		limit_start=start,
		limit_page_length=page_length or 0,
		order_by=f"`tab{LOT_DOCTYPE}`.expiry_date asc",
	)
	data = [{k: r.get(k) for k in LOT_LIST_ITEM_KEYS} for r in rows]

	total_count = len(frappe.get_list(LOT_DOCTYPE, filters=conditions, pluck="name", limit_page_length=0))
	return {"data": data, "total_count": total_count}


@frappe.whitelist(methods=["GET"])
def get_lot(name: str) -> dict:
	"""Truy vết 1 lô (mockup D3 left-card "Thông tin lot"). Trả RAW dict (KHÔNG envelope).

	- name = docname (== lot_no, autoname field:lot_no). Lô không tồn tại →
	  frappe.DoesNotExistError (idiom get_doc, khớp get_item) để FE bắt not-found.
	- Fail-closed (BR-13): user không quyền đọc AntMed Lot → PermissionError (không rò data).
	- item_name + supplier_name resolve qua Link bằng dotted-fetch (null-guard FK orphan/None).
	- qty_in/qty_out/qty_remaining tính từ sổ tồn (AntMed Stock Ledger) bằng 1 query gộp
	  (antmed.stock.get_lot_movement, CASE WHEN — KHÔNG N+1); lô không ledger → 0/0/0.
	"""
	from antmed_crm.antmed import stock

	if not frappe.has_permission(LOT_DOCTYPE, "read", doc=name):
		frappe.throw(_("Bạn không có quyền xem lô này."), frappe.PermissionError)

	doc = frappe.get_doc(LOT_DOCTYPE, name).as_dict()
	result = {k: doc.get(k) for k in LOT_DETAIL_FIELDS}

	# item_name / supplier_name resolve qua Link (null-guard: FK trống/orphan → None, không lỗi).
	result["item_name"] = (
		frappe.db.get_value(ITEM_DOCTYPE, doc.get("item"), "item_name") if doc.get("item") else None
	)
	result["supplier_name"] = (
		frappe.db.get_value("AntMed Supplier", doc.get("supplier"), "supplier_name")
		if doc.get("supplier")
		else None
	)

	# 3 aggregate từ sổ tồn (toàn kho cho lô) — khớp invariant SL còn = SUM(qty_change).
	result.update(stock.get_lot_movement(name))

	# CO/CQ → resolve file_url của AntMed Certificate (mockup D3: link tải PDF). null-guard FK orphan.
	result["co_file_url"] = (
		frappe.db.get_value("AntMed Certificate", doc.get("co_cert"), "file_url")
		if doc.get("co_cert")
		else None
	)
	result["cq_file_url"] = (
		frappe.db.get_value("AntMed Certificate", doc.get("cq_cert"), "file_url")
		if doc.get("cq_cert")
		else None
	)
	# SL còn TÁCH theo loại kho (mockup D3 "SL còn = kho TT 80 + ký gửi BV 73") — 1 query GROUP BY.
	result["balance_by_warehouse_type"] = stock.get_lot_balance_by_warehouse_type(name)
	return result


@frappe.whitelist(methods=["GET"])
def lot_trace(name: str) -> dict:
	"""Cây truy vết 1 lô (mockup D3 right-card "Cây truy vết"). Trả RAW dict (KHÔNG envelope).

	Dòng thời gian di chuyển của lô từ AntMed Stock Ledger (nhập NCC → xuất NV → chuyển kho/ký gửi
	BV) — phục vụ recall/khiếu nại/audit. Shape (Hyrum — khoá cố định, FE bind ổn định):
	  {lot, item, item_name, events:[{posting_datetime, entry_type, direction, warehouse,
	   warehouse_name, warehouse_type, qty, voucher_no, hospital, nv_employee}]}

	- name = docname lô (== lot_no). Lô không tồn tại → frappe.DoesNotExistError (idiom get_doc,
	  khớp get_lot/get_item) để FE bắt nhánh not-found (dùng chung message hiện có).
	- events = list di chuyển theo posting_datetime ASC (antmed.stock.get_lot_trace: 1 query JOIN
	  Ledger × Stock Entry × Warehouse, KHÔNG N+1; SQL param-bind %s). Lô chưa có ledger → events:[].
	- direction = 'in' nếu qty_change>0 ngược lại 'out'; qty = ABS(qty_change).
	- Fail-closed (BR-13): user thiếu read-perm AntMed Stock Ledger/Stock Entry/Warehouse → events:[]
	  (KHÔNG rò data; KHÔNG throw 500). Vẫn trả lot/item/item_name (đã qua get_doc theo read-perm Lot).
	- item_name resolve qua Link bằng dotted-fetch (null-guard FK orphan/None).
	"""
	from antmed_crm.antmed import stock

	if not frappe.has_permission(LOT_DOCTYPE, "read", doc=name):
		frappe.throw(_("Bạn không có quyền xem lô này."), frappe.PermissionError)

	# Lô không tồn tại → DoesNotExistError (idiom get_doc, khớp get_lot) cho FE nhánh not-found.
	doc = frappe.get_doc(LOT_DOCTYPE, name)
	item = doc.get("item")
	item_name = frappe.db.get_value(ITEM_DOCTYPE, item, "item_name") if item else None

	# Fail-closed (BR-13): thiếu read-perm 3 doctype nguồn của dòng thời gian → events rỗng (KHÔNG rò).
	if (
		not frappe.has_permission(LEDGER_DOCTYPE, "read")
		or not frappe.has_permission(STOCK_ENTRY_DOCTYPE, "read")
		or not frappe.has_permission(WAREHOUSE_DOCTYPE, "read")
	):
		return {"lot": doc.name, "item": item, "item_name": item_name, "events": []}

	try:
		events = stock.get_lot_trace(name)
	except frappe.PermissionError:
		events = []

	return {"lot": doc.name, "item": item, "item_name": item_name, "events": events}


@frappe.whitelist(methods=["POST"])
def initiate_recall(lot: str, reason: str, status: str = RECALL_STATUS_RECALLED) -> dict:
	"""Khởi tạo recall cho 1 lô (mockup D3 action "⚠ Khởi tạo Recall theo lot này").

	Thủ kho lật AntMed Lot.recall_status sang 'Theo dõi' (theo dõi) HOẶC 'Đã thu hồi' (thu hồi
	hẳn) + ghi recall_reason + add_comment dòng thời gian (audit). Trả RAW dict (KHÔNG envelope):
	  {name, recall_status, recall_reason}.

	- status PHẢI ∈ RECALL_STATUS_OPTIONS ('Theo dõi' | 'Đã thu hồi'); ngoài tập → ValidationError.
	  Mặc định 'Đã thu hồi' (mockup D3: mức mặc định khi bấm nút recall).
	- reason BẮT BUỘC (Long Text); rỗng / chỉ khoảng trắng → ValidationError (KHÔNG mutate).
	- one-way: lô đã 'Đã thu hồi' → gọi lại = ValidationError (idempotent guard, không double-recall).
	- Fail-closed (BR-13): user KHÔNG write-perm AntMed Lot → PermissionError (KHÔNG mutate, không rò).
	- Lô không tồn tại → frappe.DoesNotExistError (idiom get_doc, khớp get_lot) cho FE nhánh not-found.
	- Audit: add_comment('Comment', 'Khởi tạo recall: <status> — <reason>') gắn doc lô bởi user hiện tại.
	- KHÔNG raw SQL: mutate qua doc thật (get_doc / save / add_comment) → chạy doc_events nếu có.
	  KHÔNG ignore_permissions (DocPerm áp tự nhiên + đã guard write-perm fail-closed ở trên).
	"""
	# Fail-closed (BR-13): chốt write-perm TRƯỚC khi đọc/mutate (đúng thứ tự — không rò khi thiếu quyền).
	if not frappe.has_permission(LOT_DOCTYPE, "write", doc=lot):
		frappe.throw(_("Bạn không có quyền khởi tạo recall cho lô này."), frappe.PermissionError)

	# Validate status ∈ tập cho phép (ngoài tập → ValidationError, KHÔNG mutate).
	if status not in RECALL_STATUS_OPTIONS:
		frappe.throw(
			_("Mức recall không hợp lệ: {0}. Chỉ chấp nhận 'Theo dõi' hoặc 'Đã thu hồi'.").format(status)
		)

	# reason bắt buộc, không chỉ khoảng trắng (validate BE — song song validate FE).
	clean_reason = (reason or "").strip()
	if not clean_reason:
		frappe.throw(_("Vui lòng nhập lý do recall."))

	# Lô không tồn tại → DoesNotExistError (idiom get_doc, khớp get_lot).
	doc = frappe.get_doc(LOT_DOCTYPE, lot)

	# one-way idempotent guard: lô đã thu hồi hẳn → KHÔNG cho recall lại (tránh double-recall).
	if doc.recall_status == RECALL_STATUS_RECALLED:
		frappe.throw(_("Lô này đã được thu hồi — không thể khởi tạo recall lại."))

	# Mutate qua doc thật + save (chạy doc_events/audit-version; KHÔNG raw SQL, KHÔNG ignore_permissions).
	doc.recall_status = status
	doc.recall_reason = clean_reason
	doc.save()
	# Audit dòng thời gian: ghi rõ mức recall + lý do + user hiện tại (add_comment gắn doc lô).
	doc.add_comment("Comment", _("Khởi tạo recall: {0} — {1}").format(status, clean_reason))

	# 'Đã thu hồi' → tự sinh AntMed Recall Notification + thông báo BV/NV ảnh hưởng (idempotent).
	# 'Theo dõi' (chưa thu hồi hẳn) KHÔNG phát thông báo thu hồi.
	recall_notification = None
	affected_hospitals = 0
	if status == RECALL_STATUS_RECALLED:
		rn = _create_recall_notification(lot, clean_reason)
		recall_notification = rn["name"]
		affected_hospitals = rn["affected_count"]

	return {
		"name": doc.name,
		"recall_status": doc.recall_status,
		"recall_reason": doc.recall_reason,
		"recall_notification": recall_notification,
		"affected_hospitals": affected_hospitals,
	}


@frappe.whitelist(methods=["POST"])
def create_stock_entry(
	entry_type: str,
	items: str | list | None = None,
	from_warehouse: str | None = None,
	to_warehouse: str | None = None,
	nv_employee: str | None = None,
	hospital: str | None = None,
	reason: str | None = None,
) -> dict:
	"""Tạo + submit 1 phiếu kho (nhập/xuất/chuyển). Submit → ghi sổ tồn + tồn-không-âm.

	`items` = list dict (hoặc JSON-string từ FE): [{item, lot?, qty, uom?, unit_price?}].
	DocPerm áp tự nhiên (insert/submit theo quyền user). Trả {name, entry_type, docstatus}.
	"""
	item_rows = json.loads(items) if isinstance(items, str) else (items or [])
	doc = frappe.get_doc(
		{
			"doctype": STOCK_ENTRY_DOCTYPE,
			"entry_type": entry_type,
			"from_warehouse": from_warehouse,
			"to_warehouse": to_warehouse,
			"nv_employee": nv_employee,
			"hospital": hospital,
			"reason": reason,
			"items": item_rows,
		}
	)
	doc.insert()
	doc.submit()
	return {"name": doc.name, "entry_type": doc.entry_type, "docstatus": doc.docstatus}


# M03-S3 (mockup C2 Wizard "Xuất cho NV" — quét QR + FIFO + chip CO/CQ): khoá cố định 1 dòng quét
# (Hyrum — FE bind ổn định, KHÔNG đảo/đổi/thêm bớt). reason ∈ {ok, not_found, no_perm}.
SCAN_LOT_KEYS = (
	"found",
	"reason",
	"item",
	"item_name",
	"lot",
	"lot_no",
	"expiry_date",
	"uom",
	"unit_price",
	"requires_cocq",
	"has_co",
	"has_cq",
	"cocq_ok",
	"recall_status",
	"available_qty",
	"days_to_expiry",
	"is_fifo_priority",
	"suggested_lot",
)


def _empty_scan(reason: str) -> dict:
	"""Shape quét rỗng ổn định (found=False) — FE bind cùng khoá kể cả not-found/no-perm."""
	row = {k: None for k in SCAN_LOT_KEYS}
	row["found"] = False
	row["reason"] = reason
	return row


@frappe.whitelist(methods=["GET"])
def fifo_suggest(item: str, warehouse: str, qty: float = 1) -> dict:
	"""BR-08 — gợi ý lô xuất theo HSD sớm nhất (FIFO) đủ `qty`. Trả RAW dict (KHÔNG envelope).

	Shape (Hyrum): {item, warehouse, requested_qty, fulfillable, shortage,
	  lots:[{lot, lot_no, expiry_date, available_qty, take_qty}]}.
	- lots = lô còn tồn của (item×kho) xếp HSD sớm nhất trước (stock.get_fifo_lots); take_qty phân bổ
	  tham lam từ lô cận date nhất đến khi đủ qty. fulfillable = tổng tồn ≥ qty; shortage = thiếu (≥0).
	- BR-13 fail-closed: thiếu read-perm AntMed Stock Ledger/Lot → lots:[] (KHÔNG rò, KHÔNG 500).
	"""
	from antmed_crm.antmed import stock

	want = float(qty or 0)
	base = {
		"item": item,
		"warehouse": warehouse,
		"requested_qty": want,
		"fulfillable": False,
		"shortage": want,
		"lots": [],
	}
	if not frappe.has_permission(LEDGER_DOCTYPE, "read") or not frappe.has_permission(LOT_DOCTYPE, "read"):
		return base

	lots = stock.get_fifo_lots(item, warehouse)
	remaining = want
	out = []
	for lot in lots:
		avail = lot["available_qty"]
		take = min(avail, remaining) if remaining > 0 else 0.0
		remaining = max(0.0, remaining - take)
		out.append(
			{
				"lot": lot["lot"],
				"lot_no": lot["lot_no"],
				"expiry_date": lot["expiry_date"],
				"available_qty": avail,
				"take_qty": take,
			}
		)
	base["lots"] = out
	base["shortage"] = remaining
	base["fulfillable"] = remaining <= 0 and bool(out)
	return base


@frappe.whitelist(methods=["GET"])
def check_fifo(item: str, warehouse: str, lot: str) -> dict:
	"""BR-08 — lô đã chọn có đúng ưu tiên FIFO (HSD sớm nhất) không. Trả RAW dict (KHÔNG envelope).

	Shape (Hyrum): {is_priority, chosen_lot, chosen_expiry, suggested_lot, suggested_expiry}.
	- suggested_lot = lô còn tồn có HSD sớm nhất của (item×kho). is_priority=True khi lô chọn CHÍNH là
	  lô đó HOẶC HSD lô chọn ≤ HSD lô gợi ý (xuất lô cận date hơn vẫn hợp FIFO). Không có lô tồn →
	  is_priority=True (không cảnh báo vô nghĩa). FE warn khi is_priority=False.
	- BR-13 fail-closed: thiếu read-perm → is_priority=True (không chặn/không rò), suggested None.
	"""
	from frappe.utils import getdate

	from antmed_crm.antmed import stock

	base = {
		"is_priority": True,
		"chosen_lot": lot,
		"chosen_expiry": None,
		"suggested_lot": None,
		"suggested_expiry": None,
	}
	if not frappe.has_permission(LEDGER_DOCTYPE, "read") or not frappe.has_permission(LOT_DOCTYPE, "read"):
		return base

	lots = stock.get_fifo_lots(item, warehouse)
	if not lots:
		return base
	suggested = lots[0]
	base["suggested_lot"] = suggested["lot"]
	base["suggested_expiry"] = suggested["expiry_date"]
	chosen = next((l for l in lots if l["lot"] == lot), None)
	base["chosen_expiry"] = chosen["expiry_date"] if chosen else None
	# Ưu tiên nếu là chính lô gợi ý, hoặc lô chọn có HSD ≤ lô gợi ý (cận date hơn — vẫn FIFO-hợp lệ).
	if lot == suggested["lot"]:
		base["is_priority"] = True
	elif base["chosen_expiry"] and suggested["expiry_date"]:
		base["is_priority"] = getdate(base["chosen_expiry"]) <= getdate(suggested["expiry_date"])
	else:
		base["is_priority"] = False
	return base


@frappe.whitelist(methods=["GET"])
def scan_lot(code: str, warehouse: str | None = None) -> dict:
	"""Quét QR/Barcode 1 lô/VTYT (mockup C2 Wizard "Xuất cho NV" — camera). Trả RAW dict (KHÔNG envelope).

	`code` = chuỗi quét (lot_no == AntMed Lot.name, HOẶC item_code == AntMed Item.name). Giải mã:
	  - Là lô → dùng lô đó. - Là VTYT → gợi ý lô FIFO (HSD sớm nhất còn tồn ở `warehouse`).
	  - Không khớp → found=False reason='not_found'.
	Shape ổn định SCAN_LOT_KEYS (Hyrum) — FE bind 1 dòng bảng "Vật tư đã quét" + chip CO/CQ + alert.
	- cocq_ok (BR-03): vật tư requires_cocq mà lô thiếu co_cert/cq_cert → 0 (FE chặn 'Xuất' — mockup
	  'thiếu CQ — không thể xuất'). has_co/has_cq = lô có CO/CQ chưa.
	- available_qty = tồn lô tại `warehouse` (None nếu không truyền kho); is_fifo_priority = check_fifo.
	- days_to_expiry = (HSD − hôm nay).days (âm = quá hạn). recall_status từ AntMed Lot.
	- BR-13 fail-closed: thiếu read-perm AntMed Lot → found=False reason='no_perm' (KHÔNG rò, KHÔNG 500).
	"""
	from antmed_crm.antmed import stock

	if not frappe.has_permission(LOT_DOCTYPE, "read"):
		return _empty_scan("no_perm")

	code = (code or "").strip()
	if not code:
		return _empty_scan("not_found")

	# Giải mã: ưu tiên lô (== lot_no/name); rồi VTYT (== item_code/name) → gợi ý lô FIFO.
	lot_name = None
	item = None
	if frappe.db.exists(LOT_DOCTYPE, code):
		lot_name = code
		item = frappe.db.get_value(LOT_DOCTYPE, code, "item")
	elif frappe.db.exists(ITEM_DOCTYPE, code):
		item = code
		if warehouse:
			fifo = stock.get_fifo_lots(item, warehouse)
			if fifo:
				lot_name = fifo[0]["lot"]
	if not lot_name:
		# VTYT khớp nhưng không có lô tồn (hoặc không truyền kho) → vẫn báo not_found dòng quét.
		return _empty_scan("not_found")

	lot_doc = frappe.get_doc(LOT_DOCTYPE, lot_name)
	item = item or lot_doc.get("item")
	item_doc = frappe.get_doc(ITEM_DOCTYPE, item) if item and frappe.db.exists(ITEM_DOCTYPE, item) else None

	requires_cocq = int(item_doc.get("requires_cocq") or 0) if item_doc else 0
	has_co = bool(lot_doc.get("co_cert"))
	has_cq = bool(lot_doc.get("cq_cert"))
	cocq_ok = stock.compute_cocq_ok(requires_cocq, lot_doc.get("co_cert"), lot_doc.get("cq_cert"))

	expiry = lot_doc.get("expiry_date")
	days_to_expiry = date_diff(expiry, nowdate()) if expiry else None

	available_qty = stock.get_balance(warehouse, item, lot_name) if (warehouse and item) else None
	is_fifo_priority = None
	if warehouse and item:
		is_fifo_priority = check_fifo(item, warehouse, lot_name)["is_priority"]

	return {
		"found": True,
		"reason": "ok",
		"item": item,
		"item_name": item_doc.get("item_name") if item_doc else None,
		"lot": lot_name,
		"lot_no": lot_doc.get("lot_no"),
		"expiry_date": expiry,
		"uom": (item_doc.get("uom") if item_doc else None),
		"unit_price": (item_doc.get("default_unit_price") if item_doc else None),
		"requires_cocq": requires_cocq,
		"has_co": has_co,
		"has_cq": has_cq,
		"cocq_ok": bool(cocq_ok),
		"recall_status": lot_doc.get("recall_status"),
		"available_qty": available_qty,
		"days_to_expiry": days_to_expiry,
		"is_fifo_priority": is_fifo_priority,
		"suggested_lot": None if is_fifo_priority is None else (lot_name if is_fifo_priority else None),
	}


@frappe.whitelist(methods=["GET"])
def get_stock(warehouse: str, item: str, lot: str | None = None) -> dict:
	"""Tồn hiện tại của (kho × item × lot). Trả {warehouse, item, lot, balance_qty}."""
	from antmed_crm.antmed import stock

	return {
		"warehouse": warehouse,
		"item": item,
		"lot": lot,
		"balance_qty": stock.get_balance(warehouse, item, lot),
	}


@frappe.whitelist(methods=["GET"])
def list_stock_entries(
	entry_type: str | None = None,
	filters: dict | str | None = None,
	start: int = 0,
	page_length: int = 20,
) -> dict:
	"""Danh sách phiếu kho (widget "Phiếu xuất gần đây"). Trả RAW {data, total_count} — count==rows dưới DocPerm.

	Mỗi item: name, entry_type, from_warehouse, to_warehouse, posting_datetime, docstatus,
	  nv_employee, nv_employee_name (User.full_name dotted-fetch), total_value (SUM child.amount).
	- entry_type: lọc nhanh theo loại phiếu (vd 'Xuất cho NV' cho widget Thủ kho).
	- total_value gộp batch: 1 query get_all child theo parent IN [phiếu trang hiện tại] (KHÔNG N+1).
	  amount = qty*unit_price (controller tính ở validate). Thiếu dòng/amount → total_value None.
	- total_count đếm DƯỚI permission user (get_list, pluck) → giữ invariant count==rows (BR-13);
	  user noperm → rows rỗng + total_count 0 (fail-closed, không rò rỉ ngoài scope).
	"""
	conditions = _coerce_filters(filters)
	if entry_type:
		conditions.append(["entry_type", "=", entry_type])

	start = max(0, int(start))
	page_length = max(0, int(page_length))

	# Fail-closed (BR-13): user không có ANY read-perm trên AntMed Stock Entry → get_list
	# raise PermissionError. Trả shape rỗng ổn định (KHÔNG rò rỉ, count==rows==0) thay vì 403.
	try:
		rows = frappe.get_list(
			STOCK_ENTRY_DOCTYPE,
			filters=conditions,
			fields=STOCK_ENTRY_LIST_FIELDS,
			limit_start=start,
			limit_page_length=page_length or 0,
			# Qualify bảng: dotted-fetch nv_employee.full_name JOIN tabUser → `posting_datetime`
			# không ambiguous (chỉ AntMed Stock Entry có cột này), nhưng nêu rõ bảng cho an toàn.
			order_by=f"`tab{STOCK_ENTRY_DOCTYPE}`.posting_datetime desc",
		)
	except frappe.PermissionError:
		return {"data": [], "total_count": 0}

	# total_value gộp batch — 1 query child theo parent IN scope trang hiện tại (KHÔNG N+1).
	names = [r["name"] for r in rows]
	totals: dict = {}
	if names:
		for line in frappe.get_all(
			STOCK_ENTRY_ITEM_DOCTYPE,
			filters={"parenttype": STOCK_ENTRY_DOCTYPE, "parentfield": "items", "parent": ("in", names)},
			fields=["parent", "amount"],
		):
			totals[line["parent"]] = totals.get(line["parent"], 0.0) + (line.get("amount") or 0.0)

	data = []
	for r in rows:
		row = {k: r.get(k) for k in STOCK_ENTRY_LIST_ITEM_KEYS if k != "total_value"}
		# Key total_value LUÔN tồn tại (Hyrum); None khi phiếu không có dòng nào (giữ shape ổn định).
		row["total_value"] = totals.get(r["name"])
		data.append(row)

	total_count = len(
		frappe.get_list(STOCK_ENTRY_DOCTYPE, filters=conditions, pluck="name", limit_page_length=0)
	)
	return {"data": data, "total_count": total_count}


def _empty_consignment(hospital: str | None, hospitals: list) -> dict:
	"""Shape rỗng ổn định (BR-13 fail-closed) — KHÔNG rò data, kpis ĐỦ 5 key đều 0, rows [].

	kpis giữ NGUYÊN 5 key (CONSIGNMENT_KPI_KEYS) để FE bind 5 thẻ KPI không KeyError khi noperm.
	"""
	return {
		"hospital": hospital,
		"hospitals": hospitals,
		"kpis": {
			"hospitals_with_consignment": 0,
			"near_expiry_lots": 0,
			"total_value": 0,
			"total_sku": 0,
			"total_lots": 0,
		},
		"rows": [],
	}


@frappe.whitelist(methods=["GET"])
def consignment_stock(hospital: str | None = None) -> dict:
	"""Tồn kho ký gửi tại 1 BV (mockup D2, Thủ kho). Trả RAW dict (KHÔNG envelope).

	Shape (Hyrum — khoá cố định, FE bind ổn định):
	  {hospital, hospitals:[{name,hospital_name}],
	   kpis:{hospitals_with_consignment, near_expiry_lots, total_value, total_sku, total_lots},
	   rows:[{sku, item_name, lot, expiry_date, system_qty, near_expiry}]}

	- `hospitals` = danh sách BV có kho ký gửi (warehouse_type='Ký gửi BV', distinct hospital).
	- hospital None → lấy BV đầu tiên (mockup default 'BV Bạch Mai').
	- rows: tồn ký gửi của BV chọn, SL hệ thống = SUM(qty_change) theo (kho ký gửi × item × lot),
	  chỉ dòng >0 (antmed.stock.get_consignment_balances — 1 query gộp GROUP BY, KHÔNG N+1).
	  item_name (AntMed Item) + expiry_date (AntMed Lot) resolve qua dotted-fetch null-guard FK orphan.
	- near_expiry = expiry_date ≤ add_days(nowdate, 90) (cùng ngưỡng KPI + chip/highlight).
	- KPI (5 key — hàng KPI 3 thẻ mockup D2, tính trên TOÀN bộ kho ký gửi all_balances):
	  - hospitals_with_consignment = distinct BV có ≥1 dòng tồn ký gửi >0 (toàn kho ký gửi).
	  - near_expiry_lots = số dòng (hospital,lot) tồn>0 trong kho ký gửi có expiry ≤90 ngày.
	  - total_value = SUM(system_qty × AntMed Item.default_unit_price) trên TOÀN bộ tồn ký gửi.
	    Giá lấy từ AntMed Item.default_unit_price (đơn giá VTYT) — KHÔNG đơn giá hợp đồng: tồn ký gửi
	    là tồn VẬT LÝ, không gắn với 1 HĐ cụ thể. Giá bulk-fetch 1 query theo distinct item (KHÔNG
	    get_value trong loop → N+1); item thiếu/None giá → đóng góp 0.
	  - total_sku = số item distinct có tồn>0 toàn kho ký gửi.
	  - total_lots = số dòng (item,lot) tồn>0 toàn kho ký gửi (== len(all_balances), cùng cách đếm
	    near_expiry_lots theo (hospital,lot) đã HAVING SUM>0).
	- BR-13 fail-closed: user không read-perm AntMed Stock Ledger/Warehouse → shape rỗng ổn định
	  (rows:[], kpis 5 key đều 0) thay vì rò data/500.
	"""
	from antmed_crm.antmed import stock

	# Fail-closed (BR-13): thiếu read-perm 2 doctype nguồn → shape rỗng ổn định (KHÔNG rò, KHÔNG 500).
	if not frappe.has_permission(LEDGER_DOCTYPE, "read") or not frappe.has_permission(
		WAREHOUSE_DOCTYPE, "read"
	):
		return _empty_consignment(hospital, [])

	# Danh sách BV có kho ký gửi (distinct hospital từ kho 'Ký gửi BV'), dưới permission user.
	try:
		wh_rows = frappe.get_list(
			WAREHOUSE_DOCTYPE,
			filters={"warehouse_type": CONSIGNMENT_WAREHOUSE_TYPE, "hospital": ["is", "set"]},
			fields=["hospital"],
			limit_page_length=0,
		)
	except frappe.PermissionError:
		return _empty_consignment(hospital, [])

	# distinct + dotted-fetch hospital_name (null-guard FK orphan). Sắp theo hospital_name (ổn định).
	hospital_names = []
	seen = set()
	for r in wh_rows:
		h = r.get("hospital")
		if h and h not in seen:
			seen.add(h)
			hospital_names.append(h)
	name_map = {}
	if hospital_names:
		for hr in frappe.get_all(
			HOSPITAL_DOCTYPE, filters={"name": ["in", hospital_names]}, fields=["name", "hospital_name"]
		):
			name_map[hr["name"]] = hr.get("hospital_name")
	hospitals = sorted(
		({"name": h, "hospital_name": name_map.get(h)} for h in hospital_names),
		key=lambda x: (x["hospital_name"] or x["name"] or ""),
	)

	# hospital None / không truyền → BV đầu tiên (mockup default). Không có kho ký gửi → shape rỗng.
	if not hospitals:
		return _empty_consignment(hospital, [])
	if not hospital:
		hospital = hospitals[0]["name"]

	# Tồn ký gửi của BV chọn — 1 query gộp GROUP BY (KHÔNG N+1).
	try:
		balances = stock.get_consignment_balances(hospital)
	except frappe.PermissionError:
		return _empty_consignment(hospital, hospitals)

	# Bulk-fetch item_name + lot expiry_date theo tập item/lot (KHÔNG get_value trong loop → N+1).
	item_ids = list({b["item"] for b in balances if b.get("item")})
	lot_ids = list({b["lot"] for b in balances if b.get("lot")})
	item_name_map = {}
	if item_ids:
		for ir in frappe.get_all(
			ITEM_DOCTYPE, filters={"name": ["in", item_ids]}, fields=["name", "item_name"]
		):
			item_name_map[ir["name"]] = ir.get("item_name")
	lot_exp_map = {}
	if lot_ids:
		for lr in frappe.get_all(
			LOT_DOCTYPE, filters={"name": ["in", lot_ids]}, fields=["name", "expiry_date"]
		):
			lot_exp_map[lr["name"]] = lr.get("expiry_date")

	threshold = getdate(add_days(nowdate(), NEAR_EXPIRY_DAYS))
	rows = []
	for b in balances:
		expiry = lot_exp_map.get(b.get("lot"))
		near = bool(expiry) and getdate(expiry) <= threshold
		rows.append(
			{
				"sku": b.get("item"),
				"item_name": item_name_map.get(b.get("item")),
				"lot": b.get("lot"),
				"expiry_date": expiry,
				"system_qty": b.get("system_qty"),
				"near_expiry": near,
			}
		)
	# Sắp HSD sớm nhất trước (cận date lên trên) — ổn định cho FE; None xuống cuối.
	rows.sort(key=lambda r: (r["expiry_date"] is None, r["expiry_date"] or ""))

	# KPI toàn kho ký gửi (1 query gộp GROUP BY (hospital,item,lot) HAVING SUM>0): distinct BV có tồn +
	# số lô cận date + total_value/total_sku/total_lots toàn bộ.
	all_balances = stock.get_all_consignment_balances()
	hospitals_with_consignment = len({b["hospital"] for b in all_balances if b.get("hospital")})
	near_lot_ids = list({b["lot"] for b in all_balances if b.get("lot")})
	near_exp_map = {}
	if near_lot_ids:
		for lr in frappe.get_all(
			LOT_DOCTYPE, filters={"name": ["in", near_lot_ids]}, fields=["name", "expiry_date"]
		):
			near_exp_map[lr["name"]] = lr.get("expiry_date")
	# Đếm theo (hospital, lot) — 1 lô tồn ở nhiều BV tính riêng (mockup: lô cận date toàn kho ký gửi).
	near_expiry_lots = 0
	for b in all_balances:
		exp = near_exp_map.get(b.get("lot"))
		if exp and getdate(exp) <= threshold:
			near_expiry_lots += 1

	# total_sku = số item distinct có tồn>0 toàn kho ký gửi; total_lots = số dòng (item,lot) tồn>0
	# (all_balances đã HAVING SUM>0 ⇒ = len(all_balances)).
	all_item_ids = {b["item"] for b in all_balances if b.get("item")}
	total_sku = len(all_item_ids)
	total_lots = len(all_balances)
	# total_value = SUM(system_qty × default_unit_price). Giá bulk-fetch 1 query theo distinct item
	# (KHÔNG get_value trong loop → N+1). Item thiếu/None giá → đóng góp 0 (price_map.get(...) or 0).
	price_map = {}
	if all_item_ids:
		for pr in frappe.get_all(
			ITEM_DOCTYPE, filters={"name": ["in", list(all_item_ids)]}, fields=["name", "default_unit_price"]
		):
			price_map[pr["name"]] = pr.get("default_unit_price")
	total_value = 0.0
	for b in all_balances:
		total_value += (b.get("system_qty") or 0) * (price_map.get(b.get("item")) or 0)

	return {
		"hospital": hospital,
		"hospitals": hospitals,
		"kpis": {
			"hospitals_with_consignment": hospitals_with_consignment,
			"near_expiry_lots": near_expiry_lots,
			"total_value": total_value,
			"total_sku": total_sku,
			"total_lots": total_lots,
		},
		"rows": rows,
	}


def _empty_expiry_alerts() -> dict:
	"""Shape rỗng ổn định (BR-13 fail-closed) — KHÔNG rò data, mọi KPI 0, rows []."""
	return {
		"kpis": {"expired": 0, "d30": 0, "d60": 0, "d90": 0, "total_lots": 0},
		"rows": [],
	}


def _expiry_severity(days_to_expiry: int) -> str:
	"""Phân tầng severity theo số ngày tới hạn (BE quyết — FE chỉ map chip/nhãn).

	days < 0           → 'expired'  (đã quá hạn)
	0 ≤ days ≤ 30      → 'd30'      (≤30 ngày)
	31 ≤ days ≤ 60     → 'd60'      (≤60 ngày)
	61 ≤ days ≤ 90     → 'd90'      (≤90 ngày)
	"""
	if days_to_expiry < 0:
		return "expired"
	if days_to_expiry <= EXPIRY_BAND_D30:
		return "d30"
	if days_to_expiry <= EXPIRY_BAND_D60:
		return "d60"
	return "d90"


@frappe.whitelist(methods=["GET"])
def expiry_alerts() -> dict:
	"""Cảnh báo HSD (mockup D1 sidebar "⚠ Cảnh báo HSD", Thủ kho). Trả RAW dict (KHÔNG envelope).

	Rollup lot CẬN/QUÁ date trên TOÀN bộ kho (Tổng + Cá nhân NV + Ký gửi BV) từ AntMed Stock
	Ledger JOIN AntMed Lot. Shape (Hyrum — khoá cố định, FE bind ổn định):
	  {kpis:{expired, d30, d60, d90, total_lots},
	   rows:[{sku, item_name, lot, warehouse, warehouse_name, warehouse_type,
	          expiry_date, balance_qty, days_to_expiry, severity}]}

	- rows: chỉ gồm lô có SUM(balance_qty)>0 VÀ (expiry_date ≤ add_days(nowdate, 90) HOẶC đã quá
	  hạn) — antmed.stock.get_expiring_balances(90): 1 query JOIN (Stock Ledger × Lot × Warehouse,
	  GROUP BY kho×item×lot, HAVING SUM>0, WHERE expiry ≤ ngưỡng) → KHÔNG N+1. Lô >90 ngày hoặc
	  không HSD đã bị lọc thẳng trong SQL → KHÔNG lọt.
	- days_to_expiry = date_diff(expiry_date, nowdate) (số nguyên; âm = đã quá hạn).
	- severity ∈ {expired (<0), d30 (0..30), d60 (31..60), d90 (61..90)}.
	- Sắp days_to_expiry tăng dần (quá hạn lên đầu) — BE sort sẵn, FE KHÔNG sort lại.
	- KPI: expired/d30/d60/d90 = đếm số dòng (lot-warehouse) theo từng tầng; total_lots = tổng dòng.
	- item_name (AntMed Item) + warehouse_name/warehouse_type gom sẵn trong JOIN rollup (KHÔNG N+1).
	- BR-13 fail-closed: user thiếu read-perm AntMed Stock Ledger/Lot/Warehouse → shape rỗng ổn
	  định ({rows:[], kpis tất cả 0}) thay vì rò data/raise.
	"""
	from antmed_crm.antmed import stock

	# Fail-closed (BR-13): thiếu read-perm 3 doctype nguồn → shape rỗng ổn định (KHÔNG rò, KHÔNG 500).
	if (
		not frappe.has_permission(LEDGER_DOCTYPE, "read")
		or not frappe.has_permission(LOT_DOCTYPE, "read")
		or not frappe.has_permission(WAREHOUSE_DOCTYPE, "read")
	):
		return _empty_expiry_alerts()

	# Rollup lô cận/quá date toàn kho — 1 query JOIN gộp GROUP BY (HAVING SUM>0, expiry ≤ 90 ngày).
	# item_name/warehouse_name/warehouse_type gom sẵn trong JOIN → KHÔNG N+1 ở đây.
	try:
		balances = stock.get_expiring_balances(EXPIRY_BAND_D90)
	except frappe.PermissionError:
		return _empty_expiry_alerts()

	ref = nowdate()
	kpis = {"expired": 0, "d30": 0, "d60": 0, "d90": 0, "total_lots": 0}
	rows = []
	for b in balances:
		expiry = b.get("expiry_date")
		# get_expiring_balances đã lọc expiry IS NOT NULL ≤ ngưỡng; null-guard phòng thủ.
		if not expiry:
			continue
		days_to_expiry = date_diff(expiry, ref)  # (expiry − hôm nay).days; âm = đã quá hạn
		severity = _expiry_severity(days_to_expiry)
		kpis[severity] += 1
		kpis["total_lots"] += 1
		rows.append(
			{
				"sku": b.get("item"),
				"item_name": b.get("item_name"),
				"lot": b.get("lot"),
				"warehouse": b.get("warehouse"),
				"warehouse_name": b.get("warehouse_name"),
				"warehouse_type": b.get("warehouse_type"),
				"expiry_date": expiry,
				"balance_qty": b.get("balance_qty"),
				"days_to_expiry": days_to_expiry,
				"severity": severity,
			}
		)
	# Sắp days_to_expiry tăng dần (quá hạn — âm — lên đầu). Ổn định cho FE; FE KHÔNG sort lại.
	rows.sort(key=lambda r: r["days_to_expiry"])

	return {"kpis": kpis, "rows": rows}


def _empty_stock_entry_detail(name: str) -> dict:
	"""Shape rỗng ổn định (BR-13 fail-closed) — KHÔNG rò header thật, items rỗng, total_value None.

	Trả ĐỦ STOCK_ENTRY_DETAIL_HEADER_KEYS (Hyrum: FE bind ổn định kể cả nhánh fail-closed) nhưng
	mọi giá trị header = None (KHÔNG lộ BV/NV/ngày dùng thật của phiếu user không có quyền xem).
	"""
	header = {k: None for k in STOCK_ENTRY_DETAIL_HEADER_KEYS}
	header["name"] = name
	header["items"] = []
	return header


@frappe.whitelist(methods=["GET"])
def get_stock_entry(name: str) -> dict:
	"""Chi tiết 1 phiếu xuất (mockup C2 Wizard bước 3 — card "Vật tư đã chuẩn bị"). Trả RAW dict (KHÔNG envelope).

	Drill-down từ list "Phiếu xuất gần đây" → render header phiếu + bảng dòng vật tư đã chuẩn bị.
	Shape (Hyrum — khoá cố định, FE bind ổn định):
	  {name, entry_type, posting_datetime, from_warehouse, to_warehouse, nv_employee,
	   nv_employee_name, hospital, hospital_name, expected_use_date, total_value,
	   items:[{item, item_name, lot, lot_no, expiry_date, qty, uom, unit_price, amount, cocq_ok}]}

	- name = docname phiếu (naming series AM-SE). Phiếu không tồn tại → frappe.DoesNotExistError
	  (idiom get_doc, khớp get_lot/get_item) → FE bắt nhánh empty-state 'Không tìm thấy phiếu'.
	- total_value = SUM(item.amount); phiếu 0 dòng → items==[] & total_value None (giữ shape ổn định).
	- item_name (AntMed Item) + lot_no/expiry_date (AntMed Lot) resolve THEO BATCH: ĐÚNG 1 get_all
	  AntMed Lot theo lot IN [...] + 1 get_all AntMed Item theo item IN [...] (KHÔNG N+1 theo số dòng).
	- nv_employee_name (User.full_name) + hospital_name (AntMed Hospital.hospital_name) resolve qua
	  dotted-fetch null-guard (FK orphan/None → None). KHÔNG lộ mã/email thô (FE hiển thị *_name).
	- cocq_ok pass-through nguyên trạng từ child (Check 0/1 → bool); FE map chip CO/CQ.
	- BR-13 fail-closed: user KHÔNG read-perm AntMed Stock Entry → KHÔNG rò header thật, trả shape
	  rỗng ổn định (_empty_stock_entry_detail) — KHÔNG raise 500, KHÔNG lộ BV/NV/ngày dùng.
	- KHÔNG raw SQL: đọc qua get_doc + get_all (DocPerm áp tự nhiên). KHÔNG aggregate/sort phía FE.
	"""
	# Fail-closed (BR-13): chốt read-perm TRƯỚC khi đọc/mutate. Thiếu quyền → shape rỗng ổn định
	# (KHÔNG rò header thật, KHÔNG raise 500). Chốt theo doc cụ thể (data-scope NV chỉ BV được giao).
	if not frappe.has_permission(STOCK_ENTRY_DOCTYPE, "read", doc=name):
		return _empty_stock_entry_detail(name)

	# Phiếu không tồn tại → DoesNotExistError (idiom get_doc, khớp get_lot) cho FE nhánh not-found.
	doc = frappe.get_doc(STOCK_ENTRY_DOCTYPE, name)

	# Header *_name resolve qua dotted-fetch (null-guard FK orphan/None) — KHÔNG lộ mã/email thô.
	nv_employee = doc.get("nv_employee")
	nv_employee_name = frappe.db.get_value("User", nv_employee, "full_name") if nv_employee else None
	hospital = doc.get("hospital")
	hospital_name = frappe.db.get_value(HOSPITAL_DOCTYPE, hospital, "hospital_name") if hospital else None

	# Dòng vật tư: đọc thẳng từ child table (doc.items). Resolve item_name + lot_no/expiry_date THEO
	# BATCH — gom mã item/lot rồi 1 get_all/loại (KHÔNG N+1 theo số dòng).
	child_rows = doc.get("items") or []
	item_codes = {r.item for r in child_rows if r.get("item")}
	lot_codes = {r.lot for r in child_rows if r.get("lot")}

	# Gom item_name + uom (fallback ĐVT khi dòng phiếu không set uom) — 1 get_all (KHÔNG N+1).
	item_map: dict = {}
	if item_codes:
		for it in frappe.get_all(
			ITEM_DOCTYPE, filters={"name": ("in", list(item_codes))}, fields=["name", "item_name", "uom"]
		):
			item_map[it["name"]] = it

	lot_map: dict = {}
	if lot_codes:
		for lt in frappe.get_all(
			LOT_DOCTYPE,
			filters={"name": ("in", list(lot_codes))},
			fields=["name", "lot_no", "expiry_date"],
		):
			lot_map[lt["name"]] = lt

	items = []
	total = 0.0
	has_amount = False
	for r in child_rows:
		amount = r.get("amount")
		if amount is not None:
			total += amount or 0.0
			has_amount = True
		lot_doc = lot_map.get(r.get("lot")) or {}
		item_doc = item_map.get(r.get("item")) or {}
		# ĐVT: ưu tiên uom dòng phiếu; trống → fallback uom mặc định AntMed Item (mockup C2 cột ĐVT).
		uom = r.get("uom") or item_doc.get("uom")
		items.append(
			{
				"item": r.get("item"),
				"item_name": item_doc.get("item_name"),
				"lot": r.get("lot"),
				"lot_no": lot_doc.get("lot_no"),
				"expiry_date": lot_doc.get("expiry_date"),
				"qty": r.get("qty"),
				"uom": uom,
				"unit_price": r.get("unit_price"),
				"amount": amount,
				# Check 0/1 → bool tường minh (FE map chip CO/CQ true/false/None).
				"cocq_ok": bool(r.get("cocq_ok")),
			}
		)

	# Phiếu 0 dòng (hoặc không dòng nào có amount) → total_value None (giữ shape ổn định, KHÔNG 0 giả).
	total_value = total if has_amount else None

	return {
		"name": doc.name,
		"entry_type": doc.get("entry_type"),
		"posting_datetime": doc.get("posting_datetime"),
		"from_warehouse": doc.get("from_warehouse"),
		"to_warehouse": doc.get("to_warehouse"),
		"nv_employee": nv_employee,
		"nv_employee_name": nv_employee_name,
		"hospital": hospital,
		"hospital_name": hospital_name,
		"expected_use_date": doc.get("expected_use_date"),
		"total_value": total_value,
		"items": items,
	}


# ── M03 (mockup sidebar "📊 Kiểm kê") — phiếu Kiểm kê tồn 1 kho (AntMed Stock Count) ──
# snapshot tồn → nhập SL thực đếm → submit ghi điều chỉnh sổ tồn (variance). Constants Hyrum (FE bind).
STOCK_COUNT_DOCTYPE = "AntMed Stock Count"
STOCK_COUNT_ITEM_DOCTYPE = "AntMed Stock Count Item"

SNAPSHOT_ROW_KEYS = ("item", "item_name", "lot", "lot_no", "expiry_date", "system_qty")
STOCK_COUNT_LIST_FIELDS = [
	"name",
	"warehouse",
	"count_datetime",
	"docstatus",
	"total_variance_qty",
	"counted_by",
	"counted_by.full_name as counted_by_name",
]
STOCK_COUNT_LIST_ITEM_KEYS = (
	"name",
	"warehouse",
	"count_datetime",
	"docstatus",
	"total_variance_qty",
	"counted_by",
	"counted_by_name",
)
STOCK_COUNT_DETAIL_HEADER_KEYS = (
	"name",
	"warehouse",
	"warehouse_name",
	"count_datetime",
	"counted_by",
	"counted_by_name",
	"total_variance_qty",
	"note",
	"docstatus",
)
STOCK_COUNT_DETAIL_ITEM_KEYS = (
	"item",
	"item_name",
	"lot",
	"lot_no",
	"expiry_date",
	"system_qty",
	"counted_qty",
	"variance",
)


@frappe.whitelist(methods=["GET"])
def stock_count_snapshot(warehouse: str) -> dict:
	"""Snapshot tồn 1 kho cho phiếu Kiểm kê (mockup '📊 Kiểm kê'). Trả RAW dict (KHÔNG envelope).

	Shape: {warehouse, rows:[{item, item_name, lot, lot_no, expiry_date, system_qty}]}.
	- rows = mọi (item × lot) còn tồn >0 ở kho (stock.get_warehouse_balances — 1 query gộp, KHÔNG N+1).
	- BR-13 fail-closed: thiếu read-perm AntMed Stock Ledger/Warehouse → rows:[] (KHÔNG rò, KHÔNG 500).
	"""
	from antmed_crm.antmed import stock

	if not frappe.has_permission(LEDGER_DOCTYPE, "read") or not frappe.has_permission(
		WAREHOUSE_DOCTYPE, "read"
	):
		return {"warehouse": warehouse, "rows": []}
	return {"warehouse": warehouse, "rows": stock.get_warehouse_balances(warehouse)}


@frappe.whitelist(methods=["POST"])
def create_stock_count(warehouse: str, items: str | list | None = None, note: str | None = None) -> dict:
	"""Tạo + submit phiếu Kiểm kê → ghi điều chỉnh sổ tồn (variance) đưa tồn về SL thực đếm.

	`items` = list dict (hoặc JSON-string từ FE): [{item, lot?, counted_qty}]. system_qty/variance do
	controller TỰ TÍNH (authoritative tại submit). DocPerm áp tự nhiên. Trả {name, docstatus,
	total_variance_qty}.
	"""
	item_rows = json.loads(items) if isinstance(items, str) else (items or [])
	doc = frappe.get_doc(
		{"doctype": STOCK_COUNT_DOCTYPE, "warehouse": warehouse, "note": note, "items": item_rows}
	)
	doc.insert()
	doc.submit()
	return {"name": doc.name, "docstatus": doc.docstatus, "total_variance_qty": doc.total_variance_qty}


@frappe.whitelist(methods=["GET"])
def list_stock_counts(
	warehouse: str | None = None,
	filters: dict | str | None = None,
	start: int = 0,
	page_length: int = 20,
) -> dict:
	"""Danh sách phiếu Kiểm kê (lịch sử). Trả RAW {data, total_count} — count==rows dưới DocPerm.

	Mỗi item: name, warehouse, count_datetime, docstatus, total_variance_qty, counted_by,
	  counted_by_name (User.full_name dotted-fetch). filter warehouse lọc nhanh theo kho.
	- BR-13 fail-closed: user noperm AntMed Stock Count → {data:[], total_count:0} (KHÔNG rò).
	"""
	conditions = _coerce_filters(filters)
	if warehouse:
		conditions.append(["warehouse", "=", warehouse])

	start = max(0, int(start))
	page_length = max(0, int(page_length))

	try:
		rows = frappe.get_list(
			STOCK_COUNT_DOCTYPE,
			filters=conditions,
			fields=STOCK_COUNT_LIST_FIELDS,
			limit_start=start,
			limit_page_length=page_length or 0,
			order_by=f"`tab{STOCK_COUNT_DOCTYPE}`.count_datetime desc",
		)
	except frappe.PermissionError:
		return {"data": [], "total_count": 0}

	data = [{k: r.get(k) for k in STOCK_COUNT_LIST_ITEM_KEYS} for r in rows]
	total_count = len(
		frappe.get_list(STOCK_COUNT_DOCTYPE, filters=conditions, pluck="name", limit_page_length=0)
	)
	return {"data": data, "total_count": total_count}


def _empty_stock_count_detail(name: str) -> dict:
	"""Shape rỗng ổn định (BR-13 fail-closed) — KHÔNG rò header thật, items rỗng."""
	header = {k: None for k in STOCK_COUNT_DETAIL_HEADER_KEYS}
	header["name"] = name
	header["items"] = []
	return header


@frappe.whitelist(methods=["GET"])
def get_stock_count(name: str) -> dict:
	"""Chi tiết 1 phiếu Kiểm kê (drill-down từ list). Trả RAW dict (KHÔNG envelope).

	Shape (Hyrum): header STOCK_COUNT_DETAIL_HEADER_KEYS + items[STOCK_COUNT_DETAIL_ITEM_KEYS].
	- item_name (AntMed Item) + lot_no/expiry_date (AntMed Lot) resolve BATCH (KHÔNG N+1).
	- warehouse_name + counted_by_name dotted-fetch null-guard. Phiếu không tồn tại → DoesNotExistError.
	- BR-13 fail-closed: user noperm → shape rỗng ổn định (KHÔNG rò header, KHÔNG 500).
	"""
	if not frappe.has_permission(STOCK_COUNT_DOCTYPE, "read", doc=name):
		return _empty_stock_count_detail(name)

	doc = frappe.get_doc(STOCK_COUNT_DOCTYPE, name)

	warehouse = doc.get("warehouse")
	warehouse_name = (
		frappe.db.get_value(WAREHOUSE_DOCTYPE, warehouse, "warehouse_name") if warehouse else None
	)
	counted_by = doc.get("counted_by")
	counted_by_name = frappe.db.get_value("User", counted_by, "full_name") if counted_by else None

	child_rows = doc.get("items") or []
	item_codes = {r.item for r in child_rows if r.get("item")}
	lot_codes = {r.lot for r in child_rows if r.get("lot")}
	item_map: dict = {}
	if item_codes:
		for it in frappe.get_all(
			ITEM_DOCTYPE, filters={"name": ("in", list(item_codes))}, fields=["name", "item_name"]
		):
			item_map[it["name"]] = it
	lot_map: dict = {}
	if lot_codes:
		for lt in frappe.get_all(
			LOT_DOCTYPE, filters={"name": ("in", list(lot_codes))}, fields=["name", "lot_no", "expiry_date"]
		):
			lot_map[lt["name"]] = lt

	items = []
	for r in child_rows:
		lot_doc = lot_map.get(r.get("lot")) or {}
		item_doc = item_map.get(r.get("item")) or {}
		items.append(
			{
				"item": r.get("item"),
				"item_name": item_doc.get("item_name"),
				"lot": r.get("lot"),
				"lot_no": lot_doc.get("lot_no"),
				"expiry_date": lot_doc.get("expiry_date"),
				"system_qty": r.get("system_qty"),
				"counted_qty": r.get("counted_qty"),
				"variance": r.get("variance"),
			}
		)

	return {
		"name": doc.name,
		"warehouse": warehouse,
		"warehouse_name": warehouse_name,
		"count_datetime": doc.get("count_datetime"),
		"counted_by": counted_by,
		"counted_by_name": counted_by_name,
		"total_variance_qty": doc.get("total_variance_qty"),
		"note": doc.get("note"),
		"docstatus": doc.docstatus,
		"items": items,
	}


# ── M03 (mockup sidebar "⚠ Cảnh báo HSD") — scheduler hằng ngày notify lô cận/quá HSD ──
# KHÔNG @frappe.whitelist (chỉ scheduler/test gọi — tránh endpoint spam Notification). Wire ở
# hooks.py::scheduler_events.daily. Idempotent theo ngày (1 thông báo/user/ngày, dedup theo subject).
def notify_expiry_alerts(within_days: int = 90) -> dict:
	"""Quét lô cận/quá HSD ≤ within_days (toàn kho) → tạo Notification Log cho Thủ kho/Quản lý.

	Trả {expired, d30, d60, d90, total_lots, notified}. Không có lô cận date → notified=0 (không spam).
	Recipient = user enabled mang role 'Thủ kho'/'Quản lý' (trừ Administrator/Guest). Idempotent theo
	ngày: subject gắn ngày hôm nay → đã có Notification Log cùng subject cho user thì bỏ qua.
	"""
	from antmed_crm.antmed import stock

	balances = stock.get_expiring_balances(int(within_days))
	summary = {"expired": 0, "d30": 0, "d60": 0, "d90": 0, "total_lots": 0}
	ref = nowdate()
	for b in balances:
		expiry = b.get("expiry_date")
		if not expiry:
			continue
		summary[_expiry_severity(date_diff(expiry, ref))] += 1
		summary["total_lots"] += 1
	if not summary["total_lots"]:
		return {**summary, "notified": 0}

	user_ids = frappe.get_all(
		"Has Role",
		filters={"role": ["in", ["Thủ kho", "Quản lý"]], "parenttype": "User"},
		pluck="parent",
		distinct=True,
	)
	users = (
		frappe.get_all(
			"User",
			filters=[
				["name", "in", user_ids],
				["enabled", "=", 1],
				["name", "not in", ["Administrator", "Guest"]],
			],
			pluck="name",
		)
		if user_ids
		else []
	)
	subject = _("Cảnh báo HSD {0}: {1} lô cận/quá hạn ({2} đã quá hạn)").format(
		ref, summary["total_lots"], summary["expired"]
	)
	content = _(
		"Tồn kho có {0} lô cần xử lý HSD: {1} đã quá hạn, {2} ≤30 ngày, {3} ≤60 ngày, {4} ≤90 ngày. "
		"Mở '⚠ Cảnh báo HSD' để xem chi tiết."
	).format(summary["total_lots"], summary["expired"], summary["d30"], summary["d60"], summary["d90"])
	notified = 0
	for user in users:
		if frappe.db.exists("Notification Log", {"for_user": user, "subject": subject}):
			continue
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"for_user": user,
				"type": "Alert",
				"subject": subject,
				"email_content": content,
			}
		).insert(ignore_permissions=True)
		notified += 1
	return {**summary, "notified": notified}


# ── M03 D3 (cây phả hệ truy vết lot) — lô → giao phòng mổ (M04) → hóa đơn (E-Invoice) ──
# Nối lô tới ca mổ/bác sỹ/BV/SL dùng qua AntMed Delivery Item.lot (KHÔNG qua ledger — handover
# chưa chắc ghi ledger). Hyrum: khoá cố định mỗi nhánh giao (FE bind ổn định).
DELIVERY_DOCTYPE = "AntMed Delivery"
DELIVERY_ITEM_DOCTYPE = "AntMed Delivery Item"
EINVOICE_DOCTYPE = "AntMed E-Invoice"
DOCTOR_DOCTYPE = "AntMed Doctor"
GENEALOGY_DELIVERY_KEYS = (
	"delivery",
	"status",
	"hospital",
	"hospital_name",
	"doctor",
	"doctor_name",
	"surgery_datetime",
	"surgery_room",
	"used_qty",
	"einvoice",
	"einvoice_status",
	"einvoice_pdf",
)


@frappe.whitelist(methods=["GET"])
def lot_genealogy(lot: str) -> dict:
	"""Cây phả hệ tiêu thụ 1 lô tại ca mổ (mockup D3): lô → AntMed Delivery (BV/bác sỹ/ca mổ/SL dùng)
	→ Hóa đơn (AntMed E-Invoice). Trả RAW dict (KHÔNG envelope).

	Shape (Hyrum): {lot, item, item_name, deliveries:[{delivery, status, hospital, hospital_name,
	  doctor, doctor_name, surgery_datetime, surgery_room, used_qty, einvoice, einvoice_status,
	  einvoice_pdf}]}.
	- deliveries = các phiếu giao có dòng (Delivery Item) gắn LÔ này; used_qty = consumed||delivered||
	  requested của lô trong phiếu. Sort surgery_datetime tăng (ca sớm trước; None cuối).
	- Parent Delivery đọc DƯỚI quyền (frappe.get_list áp User Permission hospital → BR-13 fail-closed:
	  phiếu ngoài tuyến NV KHÔNG lọt). einvoice = AntMed E-Invoice.delivery == phiếu (1 hóa đơn/phiếu).
	- Fail-closed: thiếu read-perm AntMed Lot → PermissionError; thiếu read-perm AntMed Delivery →
	  deliveries:[] (KHÔNG rò). Lô không có phiếu giao nào → deliveries:[].
	"""
	if not frappe.has_permission(LOT_DOCTYPE, "read", doc=lot):
		frappe.throw(_("Bạn không có quyền xem lô này."), frappe.PermissionError)

	item = frappe.db.get_value(LOT_DOCTYPE, lot, "item")
	item_name = frappe.db.get_value(ITEM_DOCTYPE, item, "item_name") if item else None
	base = {"lot": lot, "item": item, "item_name": item_name, "deliveries": []}

	if not frappe.has_permission(DELIVERY_DOCTYPE, "read"):
		return base

	# Dòng giao gắn lô (child get_all — lọc parent dưới quyền ở bước sau, fail-closed).
	child = frappe.get_all(
		DELIVERY_ITEM_DOCTYPE,
		filters={"lot": lot, "parenttype": DELIVERY_DOCTYPE},
		fields=["parent", "consumed_qty", "delivered_qty", "requested_qty"],
	)
	if not child:
		return base
	parent_names = list({c["parent"] for c in child if c.get("parent")})

	# used_qty của lô theo từng phiếu (consumed → delivered → requested).
	used_by_del: dict = {}
	for c in child:
		q = float(c.get("consumed_qty") or c.get("delivered_qty") or c.get("requested_qty") or 0)
		used_by_del[c["parent"]] = used_by_del.get(c["parent"], 0.0) + q

	# Parent phiếu giao DƯỚI quyền (User Permission hospital → NV ngoài tuyến KHÔNG thấy).
	try:
		dels = frappe.get_list(
			DELIVERY_DOCTYPE,
			filters={"name": ["in", parent_names]},
			fields=["name", "status", "hospital", "doctor", "surgery_datetime", "surgery_room"],
			limit_page_length=0,
		)
	except frappe.PermissionError:
		return base
	if not dels:
		return base

	# Batch resolve hospital_name + doctor_name (KHÔNG N+1).
	hosp_ids = list({d["hospital"] for d in dels if d.get("hospital")})
	doc_ids = list({d["doctor"] for d in dels if d.get("doctor")})
	hosp_map = (
		{
			r["name"]: r.get("hospital_name")
			for r in frappe.get_all(HOSPITAL_DOCTYPE, {"name": ["in", hosp_ids]}, ["name", "hospital_name"])
		}
		if hosp_ids
		else {}
	)
	doc_map = (
		{
			r["name"]: r.get("full_name")
			for r in frappe.get_all(DOCTOR_DOCTYPE, {"name": ["in", doc_ids]}, ["name", "full_name"])
		}
		if doc_ids
		else {}
	)

	# E-Invoice theo phiếu (batch; 1 hóa đơn/phiếu — lấy đầu).
	del_names = [d["name"] for d in dels]
	einv_map: dict = {}
	for e in frappe.get_all(
		EINVOICE_DOCTYPE, {"delivery": ["in", del_names]}, ["name", "delivery", "status", "pdf_file"]
	):
		einv_map.setdefault(e["delivery"], e)

	deliveries = []
	for d in dels:
		einv = einv_map.get(d["name"]) or {}
		deliveries.append(
			{
				"delivery": d["name"],
				"status": d.get("status"),
				"hospital": d.get("hospital"),
				"hospital_name": hosp_map.get(d.get("hospital")),
				"doctor": d.get("doctor"),
				"doctor_name": doc_map.get(d.get("doctor")),
				"surgery_datetime": d.get("surgery_datetime"),
				"surgery_room": d.get("surgery_room"),
				"used_qty": used_by_del.get(d["name"]),
				"einvoice": einv.get("name"),
				"einvoice_status": einv.get("status"),
				"einvoice_pdf": einv.get("pdf_file"),
			}
		)
	deliveries.sort(key=lambda x: (x["surgery_datetime"] is None, str(x["surgery_datetime"] or "")))
	base["deliveries"] = deliveries
	return base


# ── M03 D3 (lưu vết truy vết lô — audit/recall) — AntMed Lot Trace Request ──
LTR_DOCTYPE = "AntMed Lot Trace Request"
LTR_LIST_FIELDS = [
	"name",
	"lot",
	"lot_no",
	"requested_by",
	"requested_by.full_name as requested_by_name",
	"generated_at",
	"affected_hospitals",
]
LTR_LIST_ITEM_KEYS = (
	"name",
	"lot",
	"lot_no",
	"requested_by",
	"requested_by_name",
	"generated_at",
	"affected_hospitals",
)


@frappe.whitelist(methods=["POST"])
def save_lot_trace(lot: str, note: str | None = None) -> dict:
	"""Lưu 1 bản truy vết lô (snapshot get_lot + lot_trace + lot_genealogy) cho audit/recall.

	Trả {name, generated_at, affected_hospitals}. affected_hospitals = số BV distinct trong phả hệ.
	graph_json = JSON snapshot (lot_info + events + deliveries) — đóng băng tại thời điểm truy vết.
	Fail-closed: thiếu read-perm AntMed Lot → PermissionError.
	"""
	if not frappe.has_permission(LOT_DOCTYPE, "read", doc=lot):
		frappe.throw(_("Bạn không có quyền xem lô này."), frappe.PermissionError)

	info = get_lot(lot)
	trace = lot_trace(lot)
	gen = lot_genealogy(lot)
	affected = len({d["hospital"] for d in gen.get("deliveries", []) if d.get("hospital")})
	snapshot = {
		"lot_info": info,
		"events": trace.get("events", []),
		"deliveries": gen.get("deliveries", []),
		"generated_at": str(frappe.utils.now_datetime()),
	}
	doc = frappe.get_doc(
		{
			"doctype": LTR_DOCTYPE,
			"lot": lot,
			"lot_no": info.get("lot_no"),
			"requested_by": frappe.session.user,
			"generated_at": frappe.utils.now_datetime(),
			"affected_hospitals": affected,
			"note": note,
			"graph_json": frappe.as_json(snapshot),
		}
	)
	doc.insert()
	return {"name": doc.name, "generated_at": str(doc.generated_at), "affected_hospitals": affected}


@frappe.whitelist(methods=["GET"])
def list_lot_traces(
	lot: str | None = None,
	filters: dict | str | None = None,
	start: int = 0,
	page_length: int = 20,
) -> dict:
	"""Danh sách bản truy vết đã lưu. Trả RAW {data, total_count} — count==rows dưới DocPerm.

	Mỗi item: name, lot, lot_no, requested_by, requested_by_name (User.full_name), generated_at,
	affected_hospitals. filter lot lọc nhanh theo lô. Fail-closed: noperm → {data:[], total_count:0}.
	"""
	conditions = _coerce_filters(filters)
	if lot:
		conditions.append(["lot", "=", lot])

	start = max(0, int(start))
	page_length = max(0, int(page_length))

	try:
		rows = frappe.get_list(
			LTR_DOCTYPE,
			filters=conditions,
			fields=LTR_LIST_FIELDS,
			limit_start=start,
			limit_page_length=page_length or 0,
			order_by=f"`tab{LTR_DOCTYPE}`.generated_at desc",
		)
	except frappe.PermissionError:
		return {"data": [], "total_count": 0}

	data = [{k: r.get(k) for k in LTR_LIST_ITEM_KEYS} for r in rows]
	total_count = len(frappe.get_list(LTR_DOCTYPE, filters=conditions, pluck="name", limit_page_length=0))
	return {"data": data, "total_count": total_count}


@frappe.whitelist(methods=["GET"])
def get_lot_trace_request(name: str) -> dict:
	"""Chi tiết 1 bản truy vết đã lưu (header + graph parse). Trả RAW dict (KHÔNG envelope).

	graph = parse graph_json (lot_info + events + deliveries snapshot). Phiếu không tồn tại →
	DoesNotExistError. Fail-closed: noperm → PermissionError.
	"""
	if not frappe.has_permission(LTR_DOCTYPE, "read", doc=name):
		frappe.throw(_("Bạn không có quyền xem bản truy vết này."), frappe.PermissionError)
	doc = frappe.get_doc(LTR_DOCTYPE, name)
	graph = frappe.parse_json(doc.graph_json) if doc.graph_json else {}
	return {
		"name": doc.name,
		"lot": doc.lot,
		"lot_no": doc.lot_no,
		"requested_by": doc.requested_by,
		"requested_by_name": (
			frappe.db.get_value("User", doc.requested_by, "full_name") if doc.requested_by else None
		),
		"generated_at": doc.generated_at,
		"affected_hospitals": doc.affected_hospitals,
		"note": doc.note,
		"graph": graph,
	}


# ── M03 D3 (recall → tự sinh thông báo thu hồi + BV ảnh hưởng) — AntMed Recall Notification ──
RN_DOCTYPE = "AntMed Recall Notification"
RN_LIST_FIELDS = [
	"name",
	"lot",
	"lot_no",
	"item",
	"status",
	"initiated_at",
	"affected_count",
	"notified_count",
]
RN_LIST_ITEM_KEYS = (
	"name",
	"lot",
	"lot_no",
	"item",
	"status",
	"initiated_at",
	"affected_count",
	"notified_count",
)
RN_AFFECTED_KEYS = ("hospital", "hospital_name", "qty_consignment", "qty_delivered")


def _recall_affected_hospitals(lot: str) -> list[dict]:
	"""BV ảnh hưởng bởi recall 1 lô = BV còn ký gửi lô + BV đã được giao/dùng lô (gộp).

	Trả list dict {hospital, hospital_name, qty_consignment, qty_delivered}. Đọc raw (recall là hành
	động admin — phải thấy MỌI BV ảnh hưởng, không giới hạn data-scope người bấm).
	"""
	from antmed_crm.antmed import stock

	by_hosp: dict = {}
	# 1) Còn ký gửi tại BV (lô vẫn nằm vật lý ở kho ký gửi).
	for c in stock.get_lot_consignment_by_hospital(lot):
		h = c["hospital"]
		by_hosp.setdefault(h, {"qty_consignment": 0.0, "qty_delivered": 0.0})
		by_hosp[h]["qty_consignment"] += c["qty"]
	# 2) Đã giao/dùng ở ca mổ (Delivery Item.lot → Delivery.hospital).
	child = frappe.get_all(
		DELIVERY_ITEM_DOCTYPE,
		filters={"lot": lot, "parenttype": DELIVERY_DOCTYPE},
		fields=["parent", "consumed_qty", "delivered_qty", "requested_qty"],
	)
	if child:
		parents = list({c["parent"] for c in child if c.get("parent")})
		del_hosp = {
			d["name"]: d.get("hospital")
			for d in frappe.get_all(DELIVERY_DOCTYPE, {"name": ["in", parents]}, ["name", "hospital"])
		}
		for c in child:
			h = del_hosp.get(c["parent"])
			if not h:
				continue
			q = float(c.get("consumed_qty") or c.get("delivered_qty") or c.get("requested_qty") or 0)
			by_hosp.setdefault(h, {"qty_consignment": 0.0, "qty_delivered": 0.0})
			by_hosp[h]["qty_delivered"] += q

	name_map = {}
	if by_hosp:
		for r in frappe.get_all(
			HOSPITAL_DOCTYPE, {"name": ["in", list(by_hosp.keys())]}, ["name", "hospital_name"]
		):
			name_map[r["name"]] = r.get("hospital_name")
	return [
		{
			"hospital": h,
			"hospital_name": name_map.get(h),
			"qty_consignment": v["qty_consignment"],
			"qty_delivered": v["qty_delivered"],
		}
		for h, v in sorted(by_hosp.items())
	]


def _notify_recall(lot_label: str, item: str | None, affected: list) -> int:
	"""Tạo Notification Log cảnh báo thu hồi cho Quản lý/Thủ kho + NV phụ trách BV ảnh hưởng.

	Recipient = user enabled mang role Quản lý/Thủ kho ∪ user có User Permission (allow=AntMed Hospital)
	tới BV ảnh hưởng (NV phụ trách tuyến). Trả số người đã báo.
	"""
	hosp_names = [a["hospital"] for a in affected]
	recipients = set(
		frappe.get_all(
			"Has Role",
			{"role": ["in", ["Quản lý", "Thủ kho"]], "parenttype": "User"},
			pluck="parent",
			distinct=True,
		)
	)
	if hosp_names:
		for u in frappe.get_all(
			"User Permission",
			{"allow": HOSPITAL_DOCTYPE, "for_value": ["in", hosp_names]},
			pluck="user",
			distinct=True,
		):
			recipients.add(u)
	recipients.discard("Administrator")
	recipients.discard("Guest")
	if not recipients:
		return 0
	recipients = set(frappe.get_all("User", {"name": ["in", list(recipients)], "enabled": 1}, pluck="name"))

	subject = _("Thu hồi lô {0}: {1} BV ảnh hưởng").format(lot_label, len(affected))
	content = _(
		"Lô {0} ({1}) đã bị thu hồi. {2} bệnh viện đang giữ/đã dùng lô — kiểm tra & xử lý ngay."
	).format(lot_label, item or "", len(affected))
	notified = 0
	for u in recipients:
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"for_user": u,
				"type": "Alert",
				"subject": subject,
				"email_content": content,
			}
		).insert(ignore_permissions=True)
		notified += 1
	return notified


def _create_recall_notification(lot: str, reason: str) -> dict:
	"""Tạo AntMed Recall Notification cho lô (idempotent theo bản đang mở) + thông báo. Trả {name, affected_count}."""
	existing = frappe.db.get_value(RN_DOCTYPE, {"lot": lot, "status": ["!=", "Đóng"]}, "name")
	if existing:
		return {
			"name": existing,
			"affected_count": frappe.db.get_value(RN_DOCTYPE, existing, "affected_count") or 0,
		}

	lot_no = frappe.db.get_value(LOT_DOCTYPE, lot, "lot_no")
	item = frappe.db.get_value(LOT_DOCTYPE, lot, "item")
	affected = _recall_affected_hospitals(lot)
	notified = _notify_recall(lot_no or lot, item, affected)
	doc = frappe.get_doc(
		{
			"doctype": RN_DOCTYPE,
			"lot": lot,
			"lot_no": lot_no,
			"item": item,
			"reason": reason,
			"status": "Đã phát",
			"initiated_by": frappe.session.user,
			"initiated_at": frappe.utils.now_datetime(),
			"affected_count": len(affected),
			"notified_count": notified,
			"hospitals": [{k: a[k] for k in RN_AFFECTED_KEYS} for a in affected],
		}
	)
	doc.insert(ignore_permissions=True)
	return {"name": doc.name, "affected_count": len(affected)}


@frappe.whitelist(methods=["GET"])
def list_recall_notifications(
	lot: str | None = None,
	filters: dict | str | None = None,
	start: int = 0,
	page_length: int = 20,
) -> dict:
	"""Danh sách thông báo thu hồi. Trả RAW {data, total_count} — count==rows dưới DocPerm.

	Mỗi item: name, lot, lot_no, item, status, initiated_at, affected_count, notified_count.
	Fail-closed: noperm → {data:[], total_count:0}.
	"""
	conditions = _coerce_filters(filters)
	if lot:
		conditions.append(["lot", "=", lot])
	start = max(0, int(start))
	page_length = max(0, int(page_length))
	try:
		rows = frappe.get_list(
			RN_DOCTYPE,
			filters=conditions,
			fields=RN_LIST_FIELDS,
			limit_start=start,
			limit_page_length=page_length or 0,
			order_by=f"`tab{RN_DOCTYPE}`.initiated_at desc",
		)
	except frappe.PermissionError:
		return {"data": [], "total_count": 0}
	data = [{k: r.get(k) for k in RN_LIST_ITEM_KEYS} for r in rows]
	total_count = len(frappe.get_list(RN_DOCTYPE, filters=conditions, pluck="name", limit_page_length=0))
	return {"data": data, "total_count": total_count}


@frappe.whitelist(methods=["GET"])
def get_recall_notification(name: str) -> dict:
	"""Chi tiết 1 thông báo thu hồi (header + BV ảnh hưởng). Trả RAW dict (KHÔNG envelope).

	Phiếu không tồn tại → DoesNotExistError. Fail-closed: noperm → PermissionError.
	"""
	if not frappe.has_permission(RN_DOCTYPE, "read", doc=name):
		frappe.throw(_("Bạn không có quyền xem thông báo thu hồi này."), frappe.PermissionError)
	doc = frappe.get_doc(RN_DOCTYPE, name)
	return {
		"name": doc.name,
		"lot": doc.lot,
		"lot_no": doc.lot_no,
		"item": doc.item,
		"status": doc.status,
		"reason": doc.reason,
		"initiated_by": doc.initiated_by,
		"initiated_at": doc.initiated_at,
		"affected_count": doc.affected_count,
		"notified_count": doc.notified_count,
		"hospitals": [{k: h.get(k) for k in RN_AFFECTED_KEYS} for h in (doc.get("hospitals") or [])],
	}


# ── M03 D3 (export PDF bản truy vết lô) ──
def _esc(value) -> str:
	"""Escape HTML tối thiểu cho nội dung render PDF (chống vỡ markup)."""
	return frappe.utils.escape_html(str(value)) if value is not None else ""


def _render_lot_trace_html(doc, graph: dict) -> str:
	"""Dựng HTML 1 trang cho PDF truy vết: thông tin lô + dòng thời gian + phả hệ ca mổ."""
	info = (graph.get("lot_info") or {}) if isinstance(graph, dict) else {}
	events = graph.get("events") or []
	deliveries = graph.get("deliveries") or []

	info_rows = "".join(
		f"<tr><td class='k'>{_esc(k)}</td><td>{_esc(v)}</td></tr>"
		for k, v in (
			("SKU", info.get("item_name") or info.get("item")),
			("NCC", info.get("supplier_name") or info.get("supplier")),
			("NSX", info.get("mfg_date")),
			("HSD", info.get("expiry_date")),
			("SL nhập", info.get("qty_in")),
			("SL đã xuất", info.get("qty_out")),
			("SL còn", info.get("qty_remaining")),
			("Trạng thái thu hồi", info.get("recall_status")),
		)
	)
	ev_rows = (
		"".join(
			f"<tr><td>{_esc(e.get('posting_datetime'))}</td><td>{_esc(e.get('entry_type'))}</td>"
			f"<td>{_esc(e.get('direction'))}</td><td>{_esc(e.get('warehouse_name') or e.get('warehouse'))}</td>"
			f"<td>{_esc(e.get('qty'))}</td></tr>"
			for e in events
		)
		or "<tr><td colspan='5'>Không có dòng thời gian</td></tr>"
	)
	del_rows = (
		"".join(
			f"<tr><td>{_esc(d.get('hospital_name') or d.get('hospital'))}</td><td>{_esc(d.get('doctor_name') or d.get('doctor'))}</td>"
			f"<td>{_esc(d.get('surgery_datetime'))}</td><td>{_esc(d.get('used_qty'))}</td><td>{_esc(d.get('einvoice') or '—')}</td></tr>"
			for d in deliveries
		)
		or "<tr><td colspan='5'>Chưa có ca mổ dùng lô này</td></tr>"
	)

	return f"""<html><head><meta charset='utf-8'><style>
	body{{font-family:Arial,sans-serif;font-size:12px;color:#1a1a1a;padding:18px}}
	h1{{font-size:18px;margin:0 0 2px}} h2{{font-size:13px;margin:16px 0 6px;border-bottom:1px solid #ccc;padding-bottom:3px}}
	.sub{{color:#666;font-size:11px;margin-bottom:8px}}
	table{{width:100%;border-collapse:collapse;margin-bottom:6px}}
	th,td{{border:1px solid #ddd;padding:5px 7px;text-align:left}} th{{background:#f3f4f6}}
	td.k{{width:160px;color:#555;background:#fafafa}}
	</style></head><body>
	<h1>Truy vết lô {_esc(doc.lot_no or doc.lot)}</h1>
	<div class='sub'>Mã bản: {_esc(doc.name)} · Người truy vết: {_esc(doc.requested_by)} · Lúc: {_esc(doc.generated_at)} · BV ảnh hưởng: {_esc(doc.affected_hospitals)}</div>
	<h2>Thông tin lô</h2><table>{info_rows}</table>
	<h2>Dòng thời gian (nhập/xuất/chuyển)</h2>
	<table><tr><th>Thời điểm</th><th>Loại</th><th>Chiều</th><th>Kho</th><th>SL</th></tr>{ev_rows}</table>
	<h2>Sử dụng tại ca mổ</h2>
	<table><tr><th>Bệnh viện</th><th>Bác sỹ</th><th>Ca mổ</th><th>SL dùng</th><th>Hóa đơn</th></tr>{del_rows}</table>
	</body></html>"""


@frappe.whitelist(methods=["POST"])
def export_lot_trace_pdf(name: str) -> dict:
	"""Sinh PDF cho 1 bản truy vết đã lưu (AntMed Lot Trace Request) → đính kèm + trả file_url.

	Render graph_json (thông tin lô + dòng thời gian + phả hệ ca mổ) → PDF (wkhtmltopdf) → File private
	đính vào exported_pdf. Fail-closed: noperm → PermissionError; phiếu không tồn tại → DoesNotExistError.
	"""
	if not frappe.has_permission(LTR_DOCTYPE, "read", doc=name):
		frappe.throw(_("Bạn không có quyền xuất bản truy vết này."), frappe.PermissionError)

	from frappe.utils.pdf import get_pdf

	doc = frappe.get_doc(LTR_DOCTYPE, name)
	graph = frappe.parse_json(doc.graph_json) if doc.graph_json else {}
	pdf_bytes = get_pdf(_render_lot_trace_html(doc, graph))
	file_name = f"truy-vet-{doc.lot_no or doc.lot}-{doc.name}.pdf"
	file_doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": file_name,
			"attached_to_doctype": LTR_DOCTYPE,
			"attached_to_name": doc.name,
			"attached_to_field": "exported_pdf",
			"content": pdf_bytes,
			"is_private": 1,
		}
	).insert(ignore_permissions=True)
	frappe.db.set_value(LTR_DOCTYPE, doc.name, "exported_pdf", file_doc.file_url)
	return {"name": doc.name, "exported_pdf": file_doc.file_url, "file_name": file_name}
