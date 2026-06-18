# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M07 Slice S1 — endpoint CSKH bác sỹ (Doctor Visit + Care Note).

Đường gọi: antmed_crm.api.antmed.doctor_care.<fn> (xem m07_doctor_care.md §5).
@frappe.whitelist(), type-annotated, RAW dict. count==rows (BR-13). BR-11 (quà tặng) ở slice sau.
"""

import frappe
from frappe import _
from frappe.utils import now_datetime

VISIT_DOCTYPE = "AntMed Doctor Visit"
NOTE_DOCTYPE = "AntMed Care Note"
DOCTOR_DOCTYPE = "AntMed Doctor"

VISIT_LIST_FIELDS = ["name", "doctor", "doctor.full_name as doctor_name", "hospital", "sales_rep", "status", "checked_in_at"]
VISIT_LIST_ITEM_KEYS = ("name", "doctor", "doctor_name", "hospital", "sales_rep", "status", "checked_in_at")
VISIT_DETAIL_FIELDS = ("name", "doctor", "hospital", "sales_rep", "status", "checked_in_at", "gps_lat", "gps_lng", "topic", "competitors_pitching", "commitments", "docstatus")
NOTE_LIST_FIELDS = ["name", "doctor", "visit", "note_date", "category", "content", "sales_rep"]
NOTE_LIST_ITEM_KEYS = ("name", "doctor", "visit", "note_date", "category", "content", "sales_rep")


def _coerce_filters(filters: dict | str | None) -> list:
	if not filters:
		return []
	if isinstance(filters, str):
		filters = frappe.parse_json(filters) or []
	if isinstance(filters, dict):
		return [[k, "=", v] for k, v in filters.items()]
	return list(filters)


@frappe.whitelist(methods=["POST"])
def check_in(
	doctor: str,
	hospital: str | None = None,
	gps_lat: str | None = None,
	gps_lng: str | None = None,
	topic: str | None = None,
) -> dict:
	"""NV check-in gặp bác sỹ → tạo Doctor Visit 'Đã check-in' + GPS + thời điểm."""
	if not frappe.has_permission(VISIT_DOCTYPE, "create"):
		frappe.throw(_("Bạn không có quyền tạo lượt thăm."), frappe.PermissionError)
	doc = frappe.get_doc(
		{
			"doctype": VISIT_DOCTYPE,
			"doctor": doctor,
			"hospital": hospital,
			"sales_rep": frappe.session.user,
			"topic": topic,
			"status": "Đã check-in",
			"checked_in_at": now_datetime(),
		}
	)
	if gps_lat is not None and str(gps_lat) != "":
		doc.gps_lat = float(gps_lat)
	if gps_lng is not None and str(gps_lng) != "":
		doc.gps_lng = float(gps_lng)
	doc.insert(ignore_permissions=True)
	return {"visit": doc.name, "status": doc.status}


@frappe.whitelist(methods=["POST"])
def save_care_note(doctor: str, content: str, visit: str | None = None, category: str | None = None) -> dict:
	"""Ghi 1 ghi chú chăm sóc bác sỹ (gắn lượt thăm nếu có)."""
	if not frappe.has_permission(NOTE_DOCTYPE, "create"):
		frappe.throw(_("Bạn không có quyền ghi chú chăm sóc."), frappe.PermissionError)
	note = frappe.get_doc(
		{
			"doctype": NOTE_DOCTYPE,
			"doctor": doctor,
			"visit": visit,
			"category": category,
			"content": content,
			"sales_rep": frappe.session.user,
			"note_date": now_datetime().date(),
		}
	)
	note.insert(ignore_permissions=True)
	return {"note": note.name, "doctor": doctor}


@frappe.whitelist(methods=["GET"])
def list_visits(
	filters: dict | str | None = None,
	doctor: str | None = None,
	sales_rep: str | None = None,
	start: int = 0,
	page_length: int = 20,
) -> dict:
	"""Danh sách lượt thăm bác sỹ. Trả RAW {data, total_count} — count==rows dưới DocPerm."""
	conditions = _coerce_filters(filters)
	if doctor:
		conditions.append(["doctor", "=", doctor])
	if sales_rep:
		conditions.append(["sales_rep", "=", sales_rep])
	start = max(0, int(start))
	page_length = max(0, int(page_length))
	rows = frappe.get_list(
		VISIT_DOCTYPE,
		filters=conditions,
		fields=VISIT_LIST_FIELDS,
		limit_start=start,
		limit_page_length=page_length or 0,
		order_by=f"`tab{VISIT_DOCTYPE}`.checked_in_at desc",
	)
	data = [{k: r.get(k) for k in VISIT_LIST_ITEM_KEYS} for r in rows]
	total_count = len(frappe.get_list(VISIT_DOCTYPE, filters=conditions, pluck="name", limit_page_length=0))
	return {"data": data, "total_count": total_count}


@frappe.whitelist(methods=["GET"])
def get_visit(name: str) -> dict:
	"""Chi tiết lượt thăm + care_notes[]. throw PermissionError nếu không read."""
	if not frappe.has_permission(VISIT_DOCTYPE, "read", doc=name):
		frappe.throw(_("Bạn không có quyền xem lượt thăm này."), frappe.PermissionError)
	doc = frappe.get_doc(VISIT_DOCTYPE, name).as_dict()
	result = {k: doc.get(k) for k in VISIT_DETAIL_FIELDS}
	result["doctor_name"] = frappe.db.get_value(DOCTOR_DOCTYPE, doc.get("doctor"), "full_name") if doc.get("doctor") else None
	result["care_notes"] = frappe.get_all(
		NOTE_DOCTYPE, filters={"visit": name}, fields=["name", "category", "content", "note_date"], order_by="creation desc"
	)
	return result


@frappe.whitelist(methods=["GET"])
def list_care_notes(doctor: str | None = None, start: int = 0, page_length: int = 20) -> dict:
	"""Dòng thời gian ghi chú chăm sóc (lọc theo bác sỹ). count==rows dưới DocPerm."""
	conditions = []
	if doctor:
		conditions.append(["doctor", "=", doctor])
	start = max(0, int(start))
	page_length = max(0, int(page_length))
	rows = frappe.get_list(
		NOTE_DOCTYPE,
		filters=conditions,
		fields=NOTE_LIST_FIELDS,
		limit_start=start,
		limit_page_length=page_length or 0,
		order_by="creation desc",
	)
	data = [{k: r.get(k) for k in NOTE_LIST_ITEM_KEYS} for r in rows]
	total_count = len(frappe.get_list(NOTE_DOCTYPE, filters=conditions, pluck="name", limit_page_length=0))
	return {"data": data, "total_count": total_count}
