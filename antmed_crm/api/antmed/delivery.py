# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M04 Slice S1 — endpoint Giao phòng mổ (Delivery, read-only).

Đường gọi: antmed_crm.api.antmed.delivery.<fn> (xem m04_or_delivery.md §5).
@frappe.whitelist(methods=["GET"]), type-annotated, RAW dict. count==rows (BR-13).
Vòng đời (assign/start_transit/handover) + SLA + BR-01/06 để slice M04-S2/S3.
"""

import json

import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime

DELIVERY_DOCTYPE = "AntMed Delivery"
HOSPITAL_DOCTYPE = "AntMed Hospital"
DOCTOR_DOCTYPE = "AntMed Doctor"

# Thứ tự cột kanban điều phối (dispatch_board) + state machine vòng đời (m04 §3).
STATUS_ORDER = ["Nháp", "Đã phân loại", "Đã gán NV", "Đang giao", "Đã bàn giao", "Đã đóng", "Từ chối"]
_NEXT = {
	"Nháp": {"Đã phân loại", "Đã gán NV", "Từ chối"},
	"Đã phân loại": {"Đã gán NV", "Từ chối"},
	"Đã gán NV": {"Đang giao", "Từ chối"},
	"Đang giao": {"Đã bàn giao"},
	"Đã bàn giao": {"Đã đóng"},
}


def _assert_transition(current: str, target: str) -> None:
	if target not in _NEXT.get(current, set()):
		frappe.throw(_("Không thể chuyển trạng thái '{0}' → '{1}'.").format(current, target))


def _check_write(name: str) -> None:
	"""Gate quyền cho endpoint mutating (LL-BE-13 — KHÔNG tin FE ẩn nút)."""
	if not frappe.has_permission(DELIVERY_DOCTYPE, "write", doc=name):
		frappe.throw(_("Bạn không có quyền cập nhật phiếu giao này."), frappe.PermissionError)

DELIVERY_LIST_FIELDS = [
	"name",
	"hospital",
	"hospital.hospital_name as hospital_name",
	"doctor",
	"doctor.full_name as doctor_name",
	"surgery_datetime",
	"status",
	"sla_status",
	"assigned_employee",
	"assigned_employee.full_name as assigned_employee_name",
]
DELIVERY_LIST_ITEM_KEYS = (
	"name",
	"hospital",
	"hospital_name",
	"doctor",
	"doctor_name",
	"surgery_datetime",
	"status",
	"sla_status",
	"assigned_employee",
	"assigned_employee_name",
)
DELIVERY_DETAIL_FIELDS = (
	"name",
	"hospital",
	"doctor",
	"surgery_room",
	"surgery_datetime",
	"sla_minutes",
	"contract",
	"assigned_employee",
	"status",
	"delivered_at",
	"sla_status",
	"notes",
	"docstatus",
)
DELIVERY_ITEM_KEYS = ("item", "item_name", "lot", "uom", "requested_qty", "delivered_qty", "consumed_qty", "returned_qty")


def _coerce_filters(filters: dict | str | None) -> list:
	if not filters:
		return []
	if isinstance(filters, str):
		filters = frappe.parse_json(filters) or []
	if isinstance(filters, dict):
		return [[k, "=", v] for k, v in filters.items()]
	return list(filters)


@frappe.whitelist(methods=["GET"])
def list_deliveries(
	filters: dict | str | None = None,
	status: str | None = None,
	hospital: str | None = None,
	start: int = 0,
	page_length: int = 20,
) -> dict:
	"""Danh sách phiếu giao phòng mổ. Trả RAW {data, total_count} — count==rows khi page_length=0.

	Mỗi item gồm ĐÚNG 8 field: name, hospital, hospital_name, doctor, surgery_datetime,
	status, sla_status, assigned_employee. hospital_name resolve qua Link (dotted-fetch).
	"""
	conditions = _coerce_filters(filters)
	if status:
		conditions.append(["status", "=", status])
	if hospital:
		conditions.append(["hospital", "=", hospital])

	start = max(0, int(start))
	page_length = max(0, int(page_length))

	rows = frappe.get_list(
		DELIVERY_DOCTYPE,
		filters=conditions,
		fields=DELIVERY_LIST_FIELDS,
		limit_start=start,
		limit_page_length=page_length or 0,
		order_by=f"`tab{DELIVERY_DOCTYPE}`.surgery_datetime desc",
	)
	data = [{k: r.get(k) for k in DELIVERY_LIST_ITEM_KEYS} for r in rows]

	total_count = len(frappe.get_list(DELIVERY_DOCTYPE, filters=conditions, pluck="name", limit_page_length=0))
	return {"data": data, "total_count": total_count}


@frappe.whitelist(methods=["GET"])
def get_delivery(name: str) -> dict:
	"""Chi tiết phiếu giao + items[] + hospital_name/doctor_name. throw PermissionError nếu không read."""
	if not frappe.has_permission(DELIVERY_DOCTYPE, "read", doc=name):
		frappe.throw(_("Bạn không có quyền xem phiếu giao này."), frappe.PermissionError)

	doc = frappe.get_doc(DELIVERY_DOCTYPE, name).as_dict()
	result = {k: doc.get(k) for k in DELIVERY_DETAIL_FIELDS}
	# LL-BE-2 + LL-BE-5: enrich *_name, null-guard FK orphan.
	result["hospital_name"] = (
		frappe.db.get_value(HOSPITAL_DOCTYPE, doc.get("hospital"), "hospital_name") if doc.get("hospital") else None
	)
	result["doctor_name"] = (
		frappe.db.get_value(DOCTOR_DOCTYPE, doc.get("doctor"), "full_name") if doc.get("doctor") else None
	)
	result["assigned_employee_name"] = (
		frappe.db.get_value("User", doc.get("assigned_employee"), "full_name") if doc.get("assigned_employee") else None
	)
	result["items"] = [{k: row.get(k) for k in DELIVERY_ITEM_KEYS} for row in (doc.get("items") or [])]
	return result


@frappe.whitelist(methods=["POST"])
def create_request(
	hospital: str,
	surgery_datetime: str,
	items: str | list | None = None,
	doctor: str | None = None,
	surgery_room: str | None = None,
	contract: str | None = None,
	sla_minutes: int = 120,
) -> dict:
	"""NV tạo yêu cầu giao phòng mổ (status 'Nháp'). items = list dict (hoặc JSON-string)."""
	item_rows = json.loads(items) if isinstance(items, str) else (items or [])
	doc = frappe.get_doc(
		{
			"doctype": DELIVERY_DOCTYPE,
			"hospital": hospital,
			"doctor": doctor,
			"surgery_datetime": surgery_datetime,
			"surgery_room": surgery_room,
			"contract": contract,
			"sla_minutes": int(sla_minutes),
			"status": "Nháp",
			"items": item_rows,
		}
	)
	doc.insert()
	return {"name": doc.name, "status": doc.status}


@frappe.whitelist(methods=["POST"])
def assign(name: str, assigned_employee: str) -> dict:
	"""Gán NV phụ trách → 'Đã gán NV' (m04 §3). Gate quyền write."""
	_check_write(name)
	current = frappe.db.get_value(DELIVERY_DOCTYPE, name, "status")
	_assert_transition(current, "Đã gán NV")
	frappe.db.set_value(DELIVERY_DOCTYPE, name, {"assigned_employee": assigned_employee, "status": "Đã gán NV"})
	return {"name": name, "status": "Đã gán NV", "assigned_employee": assigned_employee}


@frappe.whitelist(methods=["POST"])
def start_transit(name: str) -> dict:
	"""NV bắt đầu giao → 'Đang giao'."""
	_check_write(name)
	current = frappe.db.get_value(DELIVERY_DOCTYPE, name, "status")
	_assert_transition(current, "Đang giao")
	frappe.db.set_value(DELIVERY_DOCTYPE, name, "status", "Đang giao")
	return {"name": name, "status": "Đang giao"}


@frappe.whitelist(methods=["POST"])
def handover(name: str) -> dict:
	"""Bàn giao tại phòng mổ → 'Đã bàn giao' (submit, docstatus 1) + tính SLA.

	sla_status = 'OnTime' nếu giao trước/đúng giờ phẫu thuật, ngược lại 'Late'.
	(Gate chữ ký/ảnh/GPS + trừ quota M02 để slice M04-S3.)
	"""
	_check_write(name)
	doc = frappe.get_doc(DELIVERY_DOCTYPE, name)
	_assert_transition(doc.status, "Đã bàn giao")
	now = now_datetime()
	doc.delivered_at = now
	doc.status = "Đã bàn giao"
	doc.sla_status = "OnTime" if now <= get_datetime(doc.surgery_datetime) else "Late"
	doc.submit()
	return {"name": name, "status": doc.status, "sla_status": doc.sla_status, "delivered_at": str(doc.delivered_at)}


@frappe.whitelist(methods=["GET"])
def dispatch_board(hospital: str | None = None) -> dict:
	"""Bảng điều phối (kanban): gom phiếu theo cột trạng thái. count==rows dưới DocPerm."""
	conditions = []
	if hospital:
		conditions.append(["hospital", "=", hospital])
	rows = frappe.get_list(
		DELIVERY_DOCTYPE,
		filters=conditions,
		fields=DELIVERY_LIST_FIELDS,
		limit_page_length=0,
		order_by=f"`tab{DELIVERY_DOCTYPE}`.surgery_datetime asc",
	)
	board: dict = {}
	for r in rows:
		board.setdefault(r.get("status"), []).append({k: r.get(k) for k in DELIVERY_LIST_ITEM_KEYS})
	return {"columns": [{"status": s, "items": board.get(s, [])} for s in STATUS_ORDER], "total": len(rows)}


@frappe.whitelist(methods=["GET"])
def list_assignable_employees() -> dict:
	"""NV có thể gán phụ trách phiếu giao (role 'NV kinh doanh' / 'Quản lý', user active).

	Trả {data: [{value: <user>, label: <full_name>}]} cho dropdown 'Gán NV' (S2).
	value = User.name gửi BE; label = full_name hiển thị (KHÔNG leak email ra UI).
	"""
	user_ids = frappe.get_all(
		"Has Role",
		filters={"role": ["in", ["NV kinh doanh", "Quản lý"]], "parenttype": "User"},
		pluck="parent",
		distinct=True,
	)
	if not user_ids:
		return {"data": []}
	users = frappe.get_all(
		"User",
		filters=[
			["name", "in", user_ids],
			["enabled", "=", 1],
			["name", "not in", ["Administrator", "Guest"]],
		],
		fields=["name as value", "full_name as label"],
		order_by="full_name asc",
	)
	return {"data": users}
