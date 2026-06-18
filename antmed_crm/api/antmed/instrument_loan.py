# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M05 Slice S1 — endpoint Bộ dụng cụ (Instrument Set, read-only).

Đường gọi: antmed_crm.api.antmed.instrument_loan.<fn> (xem m05_instrument_loan.md §5).
@frappe.whitelist(methods=["GET"]), type-annotated, RAW dict. count==rows (BR-13).
Vòng đời mượn 7-state (book/handover/receive_return/sterilize/mark_ready) để slice M05-S2/S3.
"""

import frappe
from frappe import _

SET_DOCTYPE = "AntMed Instrument Set"

SET_LIST_FIELDS = ["name", "set_code", "surgery_type", "current_status", "current_holder", "lifetime_loans"]
SET_LIST_ITEM_KEYS = ("name", "set_code", "surgery_type", "current_status", "current_holder", "lifetime_loans")
SET_DETAIL_FIELDS = (
	"name",
	"set_code",
	"surgery_type",
	"current_status",
	"asset_value",
	"max_loans",
	"lifetime_loans",
	"supplier",
	"current_holder",
	"current_warehouse",
)
COMPONENT_KEYS = ("component_name", "qty", "criticality", "reference_photo")


def _coerce_filters(filters: dict | str | None) -> list:
	if not filters:
		return []
	if isinstance(filters, str):
		filters = frappe.parse_json(filters) or []
	if isinstance(filters, dict):
		return [[k, "=", v] for k, v in filters.items()]
	return list(filters)


@frappe.whitelist(methods=["GET"])
def list_instrument_sets(
	filters: dict | str | None = None,
	current_status: str | None = None,
	search: str | None = None,
	start: int = 0,
	page_length: int = 20,
) -> dict:
	"""Danh mục bộ dụng cụ. Trả RAW {data, total_count} — count==rows khi page_length=0.

	- current_status: lọc nhanh theo trạng thái (Sẵn sàng/Đang sử dụng tại BV/…).
	- search: khớp set_code (LIKE). Mỗi item gồm ĐÚNG 6 field.
	"""
	conditions = _coerce_filters(filters)
	if current_status:
		conditions.append(["current_status", "=", current_status])
	if search:
		conditions.append(["set_code", "like", f"%{search}%"])

	start = max(0, int(start))
	page_length = max(0, int(page_length))

	rows = frappe.get_list(
		SET_DOCTYPE,
		filters=conditions,
		fields=SET_LIST_FIELDS,
		limit_start=start,
		limit_page_length=page_length or 0,
		order_by="set_code asc",
	)
	data = [{k: r.get(k) for k in SET_LIST_ITEM_KEYS} for r in rows]

	total_count = len(frappe.get_list(SET_DOCTYPE, filters=conditions, pluck="name", limit_page_length=0))
	return {"data": data, "total_count": total_count}


@frappe.whitelist(methods=["GET"])
def get_instrument_set(name: str) -> dict:
	"""Chi tiết bộ + components[] + loans[] (lượt mượn gần đây — [] cho tới M05-S2).

	throw PermissionError nếu không read được.
	"""
	if not frappe.has_permission(SET_DOCTYPE, "read", doc=name):
		frappe.throw(_("Bạn không có quyền xem bộ dụng cụ này."), frappe.PermissionError)

	doc = frappe.get_doc(SET_DOCTYPE, name).as_dict()
	result = {k: doc.get(k) for k in SET_DETAIL_FIELDS}
	result["components"] = [{k: c.get(k) for k in COMPONENT_KEYS} for c in (doc.get("components") or [])]
	result["loans"] = []  # AntMed Instrument Loan — slice M05-S2
	return result
