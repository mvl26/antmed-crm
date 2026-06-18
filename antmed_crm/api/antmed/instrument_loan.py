# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M05 Slice S1 — endpoint Bộ dụng cụ (Instrument Set, read-only).

Đường gọi: antmed_crm.api.antmed.instrument_loan.<fn> (xem m05_instrument_loan.md §5).
@frappe.whitelist(methods=["GET"]), type-annotated, RAW dict. count==rows (BR-13).
Vòng đời mượn 7-state (book/handover/receive_return/sterilize/mark_ready) để slice M05-S2/S3.
"""

import frappe
from frappe import _
from frappe.utils import now_datetime

SET_DOCTYPE = "AntMed Instrument Set"
LOAN_DOCTYPE = "AntMed Instrument Loan"
STERILIZATION_DOCTYPE = "AntMed Sterilization"

LOAN_LIST_FIELDS = ["name", "instrument_set", "hospital", "status", "employee", "booked_at", "due_return_at"]
LOAN_LIST_ITEM_KEYS = ("name", "instrument_set", "hospital", "status", "employee", "booked_at", "due_return_at")
LOAN_DETAIL_FIELDS = (
	"name",
	"instrument_set",
	"hospital",
	"doctor",
	"employee",
	"surgery_case",
	"status",
	"booked_at",
	"loaned_at",
	"due_return_at",
	"returned_at",
	"docstatus",
)


def _check_loan_write(name: str) -> None:
	if not frappe.has_permission(LOAN_DOCTYPE, "write", doc=name):
		frappe.throw(_("Bạn không có quyền cập nhật lượt mượn này."), frappe.PermissionError)

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
	# Lượt mượn gần đây của bộ (M05-S2 — AntMed Instrument Loan đã land).
	result["loans"] = frappe.get_list(
		LOAN_DOCTYPE,
		filters={"instrument_set": name},
		fields=["name", "hospital", "status", "booked_at", "due_return_at", "returned_at"],
		order_by="creation desc",
		limit_page_length=10,
	)
	return result


@frappe.whitelist(methods=["POST"])
def book(
	instrument_set: str,
	hospital: str,
	booked_at: str,
	due_return_at: str,
	doctor: str | None = None,
	employee: str | None = None,
	surgery_case: str | None = None,
) -> dict:
	"""Đặt mượn bộ → loan 'Đã đặt' (BR-05 chống trùng lịch ở controller validate). Sync Set."""
	doc = frappe.get_doc(
		{
			"doctype": LOAN_DOCTYPE,
			"instrument_set": instrument_set,
			"hospital": hospital,
			"doctor": doctor,
			"employee": employee,
			"surgery_case": surgery_case,
			"booked_at": booked_at,
			"due_return_at": due_return_at,
			"status": "Đã đặt",
		}
	)
	doc.insert()
	frappe.db.set_value(SET_DOCTYPE, instrument_set, "current_status", "Đã đặt", update_modified=False)
	return {"name": doc.name, "status": doc.status}


@frappe.whitelist(methods=["POST"])
def handover(loan: str) -> dict:
	"""Bàn giao bộ tại BV → 'Đang sử dụng tại BV' (submit). Sync Set + tăng lifetime_loans."""
	_check_loan_write(loan)
	doc = frappe.get_doc(LOAN_DOCTYPE, loan)
	if doc.status not in ("Đã đặt", "Đang giao"):
		frappe.throw(_("Chỉ bàn giao được lượt 'Đã đặt'/'Đang giao' (hiện: {0}).").format(doc.status))
	doc.status = "Đang sử dụng tại BV"
	doc.loaned_at = now_datetime()
	doc.submit()
	current = frappe.db.get_value(SET_DOCTYPE, doc.instrument_set, "lifetime_loans") or 0
	frappe.db.set_value(
		SET_DOCTYPE,
		doc.instrument_set,
		{"current_status": "Đang sử dụng tại BV", "lifetime_loans": current + 1},
		update_modified=False,
	)
	return {"name": loan, "status": doc.status, "loaned_at": str(doc.loaned_at)}


@frappe.whitelist(methods=["POST"])
def receive_return(loan: str) -> dict:
	"""NV nhận bộ về → 'Đã trả về NV KD'. Sync Set. (Tiệt khuẩn BR-09 ở M05-S3.)"""
	_check_loan_write(loan)
	doc = frappe.get_doc(LOAN_DOCTYPE, loan)
	if doc.status != "Đang sử dụng tại BV":
		frappe.throw(_("Chỉ nhận về lượt đang 'Đang sử dụng tại BV' (hiện: {0}).").format(doc.status))
	now = now_datetime()
	frappe.db.set_value(LOAN_DOCTYPE, loan, {"status": "Đã trả về NV KD", "returned_at": now}, update_modified=False)
	frappe.db.set_value(SET_DOCTYPE, doc.instrument_set, "current_status", "Đã trả về NV KD", update_modified=False)
	return {"name": loan, "status": "Đã trả về NV KD", "returned_at": str(now)}


@frappe.whitelist(methods=["GET"])
def list_loans(
	filters: dict | str | None = None,
	status: str | None = None,
	employee: str | None = None,
	start: int = 0,
	page_length: int = 20,
) -> dict:
	"""Danh sách lượt mượn. Trả RAW {data, total_count} — count==rows dưới DocPerm."""
	conditions = _coerce_filters(filters)
	if status:
		conditions.append(["status", "=", status])
	if employee:
		conditions.append(["employee", "=", employee])

	start = max(0, int(start))
	page_length = max(0, int(page_length))

	rows = frappe.get_list(
		LOAN_DOCTYPE,
		filters=conditions,
		fields=LOAN_LIST_FIELDS,
		limit_start=start,
		limit_page_length=page_length or 0,
		order_by=f"`tab{LOAN_DOCTYPE}`.booked_at desc",
	)
	data = [{k: r.get(k) for k in LOAN_LIST_ITEM_KEYS} for r in rows]

	total_count = len(frappe.get_list(LOAN_DOCTYPE, filters=conditions, pluck="name", limit_page_length=0))
	return {"data": data, "total_count": total_count}


@frappe.whitelist(methods=["GET"])
def get_loan(name: str) -> dict:
	"""Chi tiết lượt mượn + 2 checklist. throw PermissionError nếu không read."""
	if not frappe.has_permission(LOAN_DOCTYPE, "read", doc=name):
		frappe.throw(_("Bạn không có quyền xem lượt mượn này."), frappe.PermissionError)
	doc = frappe.get_doc(LOAN_DOCTYPE, name).as_dict()
	result = {k: doc.get(k) for k in LOAN_DETAIL_FIELDS}
	result["handover_checklist"] = [
		{"component_name": c.get("component_name"), "expected": c.get("expected"), "condition": c.get("condition")}
		for c in (doc.get("handover_checklist") or [])
	]
	result["return_checklist"] = [
		{"component_name": c.get("component_name"), "expected": c.get("expected"), "condition": c.get("condition")}
		for c in (doc.get("return_checklist") or [])
	]
	return result


@frappe.whitelist(methods=["POST"])
def sterilize(
	loan: str,
	method: str | None = None,
	result: str = "Pass",
	operator: str | None = None,
	started_at: str | None = None,
	ended_at: str | None = None,
) -> dict:
	"""Ghi 1 bản ghi tiệt khuẩn cho lượt đã trả → loan 'Đang xử lý/tiệt khuẩn'. Sync Set."""
	_check_loan_write(loan)
	loan_doc = frappe.get_doc(LOAN_DOCTYPE, loan)
	if loan_doc.status not in ("Đã trả về NV KD", "Đang xử lý/tiệt khuẩn"):
		frappe.throw(_("Chỉ tiệt khuẩn lượt đã 'Đã trả về NV KD' (hiện: {0}).").format(loan_doc.status))
	str_doc = frappe.get_doc(
		{
			"doctype": STERILIZATION_DOCTYPE,
			"loan": loan,
			"instrument_set": loan_doc.instrument_set,
			"method": method,
			"result": result,
			"operator": operator,
			"started_at": started_at,
			"ended_at": ended_at,
		}
	)
	str_doc.insert(ignore_permissions=True)
	frappe.db.set_value(LOAN_DOCTYPE, loan, "status", "Đang xử lý/tiệt khuẩn", update_modified=False)
	frappe.db.set_value(
		SET_DOCTYPE, loan_doc.instrument_set, "current_status", "Đang xử lý/tiệt khuẩn", update_modified=False
	)
	return {"sterilization": str_doc.name, "result": result, "status": "Đang xử lý/tiệt khuẩn"}


@frappe.whitelist(methods=["POST"])
def mark_ready(loan: str) -> dict:
	"""BR-09: chỉ cho bộ về 'Sẵn sàng' khi lượt có ≥1 tiệt khuẩn result=Pass. Đóng lượt."""
	_check_loan_write(loan)
	loan_doc = frappe.get_doc(LOAN_DOCTYPE, loan)
	if loan_doc.status != "Đang xử lý/tiệt khuẩn":
		frappe.throw(_("Chỉ hoàn tất lượt đang 'Đang xử lý/tiệt khuẩn' (hiện: {0}).").format(loan_doc.status))
	if not frappe.db.exists(STERILIZATION_DOCTYPE, {"loan": loan, "result": "Pass"}):
		frappe.throw(_("BR-09: Bộ phải có kết quả tiệt khuẩn Pass trước khi sẵn sàng cho mượn lại."))
	frappe.db.set_value(LOAN_DOCTYPE, loan, "status", "Đã đóng", update_modified=False)
	frappe.db.set_value(SET_DOCTYPE, loan_doc.instrument_set, "current_status", "Sẵn sàng", update_modified=False)
	return {"name": loan, "status": "Đã đóng", "set_status": "Sẵn sàng"}
