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

ITEM_DOCTYPE = "AntMed Item"
WAREHOUSE_DOCTYPE = "AntMed Warehouse"
LOT_DOCTYPE = "AntMed Lot"
STOCK_ENTRY_DOCTYPE = "AntMed Stock Entry"

STOCK_ENTRY_LIST_FIELDS = [
	"name",
	"entry_type",
	"from_warehouse",
	"to_warehouse",
	"posting_datetime",
	"docstatus",
]
STOCK_ENTRY_LIST_ITEM_KEYS = (
	"name",
	"entry_type",
	"from_warehouse",
	"to_warehouse",
	"posting_datetime",
	"docstatus",
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
	if not filters:
		return []
	if isinstance(filters, str):
		filters = frappe.parse_json(filters) or []
	if isinstance(filters, dict):
		return [[k, "=", v] for k, v in filters.items()]
	return list(filters)


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

	total_count = len(frappe.get_list(WAREHOUSE_DOCTYPE, filters=conditions, pluck="name", limit_page_length=0))
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
	"""Danh sách phiếu kho. Trả RAW {data, total_count} — count==rows dưới DocPerm."""
	conditions = _coerce_filters(filters)
	if entry_type:
		conditions.append(["entry_type", "=", entry_type])

	start = max(0, int(start))
	page_length = max(0, int(page_length))

	rows = frappe.get_list(
		STOCK_ENTRY_DOCTYPE,
		filters=conditions,
		fields=STOCK_ENTRY_LIST_FIELDS,
		limit_start=start,
		limit_page_length=page_length or 0,
		order_by="posting_datetime desc",
	)
	data = [{k: r.get(k) for k in STOCK_ENTRY_LIST_ITEM_KEYS} for r in rows]

	total_count = len(frappe.get_list(STOCK_ENTRY_DOCTYPE, filters=conditions, pluck="name", limit_page_length=0))
	return {"data": data, "total_count": total_count}
