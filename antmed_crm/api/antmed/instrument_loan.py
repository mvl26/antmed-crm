# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M05 Slice S1 — endpoint Bộ dụng cụ (Instrument Set, read-only).

Đường gọi: antmed_crm.api.antmed.instrument_loan.<fn> (xem m05_instrument_loan.md §5).
@frappe.whitelist(methods=["GET"]), type-annotated, RAW dict. count==rows (BR-13).
Vòng đời mượn 7-state (book/handover/receive_return/sterilize/mark_ready) để slice M05-S2/S3.
"""

import frappe
from frappe import _
from frappe.utils import date_diff, get_datetime, get_first_day, now_datetime

from antmed_crm.api.antmed._filters import coerce_filters

SET_DOCTYPE = "AntMed Instrument Set"
LOAN_DOCTYPE = "AntMed Instrument Loan"
STERILIZATION_DOCTYPE = "AntMed Sterilization"
SET_COMPONENT_DOCTYPE = "AntMed Instrument Set Component"

# Trạng thái Set theo nhóm KPI (mockup I1: Tổng / Đang lưu hành / Tại kho SS / Quá hạn-thất lạc).
CIRCULATION_STATES = (
	"Đã đặt",
	"Đang giao",
	"Đang sử dụng tại BV",
	"Đã trả về NV KD",
	"Đang xử lý/tiệt khuẩn",
)
READY_STATE = "Sẵn sàng"
ISSUE_STATES = ("Mất", "Hỏng")
# Lượt mượn còn "mở" (giữ chỗ bộ) — dùng tìm lượt active của mỗi bộ cho board.
OPEN_LOAN_STATES = (
	"Đã đặt",
	"Đang giao",
	"Đang sử dụng tại BV",
	"Đã trả về NV KD",
	"Đang xử lý/tiệt khuẩn",
)
# Lượt mượn quá hạn (đã quá due_return_at mà chưa quay về kho an toàn).
OVERDUE_STATES = ("Đang sử dụng tại BV", "Đã trả về NV KD")

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
	return coerce_filters(filters)


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
	# Sinh handover_checklist từ components của bộ (FE C3 hiển thị checklist nhận/bàn giao).
	for comp in frappe.get_all(
		SET_COMPONENT_DOCTYPE,
		filters={"parent": instrument_set, "parenttype": SET_DOCTYPE},
		fields=["component_name", "qty"],
		order_by="idx asc",
	):
		doc.append("handover_checklist", {"component_name": comp.component_name, "expected": comp.qty})
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
	result["handover_checklist"] = _checklist_rows(doc.get("handover_checklist"))
	result["return_checklist"] = _checklist_rows(doc.get("return_checklist"))

	# Enrich cho FE C3 — tên đọc được (LL-FE *_name) + ngữ cảnh bộ + cờ quá hạn.
	sinfo = (
		frappe.db.get_value(SET_DOCTYPE, doc.get("instrument_set"), ["set_code", "surgery_type"], as_dict=True)
		if doc.get("instrument_set")
		else None
	) or {}
	result["set_code"] = sinfo.get("set_code")
	result["surgery_type"] = sinfo.get("surgery_type")
	result["hospital_name"] = (
		frappe.db.get_value("AntMed Hospital", doc.get("hospital"), "hospital_name") if doc.get("hospital") else None
	)
	result["doctor_name"] = (
		frappe.db.get_value("AntMed Doctor", doc.get("doctor"), "full_name") if doc.get("doctor") else None
	)
	result["employee_name"] = (
		frappe.db.get_value("User", doc.get("employee"), "full_name") if doc.get("employee") else None
	)
	result["is_overdue"] = _is_overdue(doc.get("due_return_at"), doc.get("status"))
	return result


def _checklist_rows(rows: list | None) -> list:
	"""Chuẩn hoá 1 checklist con (handover/return) cho FE — đủ field render C3."""
	return [
		{
			"component_name": c.get("component_name"),
			"expected": c.get("expected"),
			"condition": c.get("condition"),
			"signed_by": c.get("signed_by"),
			"photo": c.get("photo"),
		}
		for c in (rows or [])
	]


def _is_overdue(due_return_at, status) -> bool:
	"""Quá hạn = đã qua due_return_at mà lượt còn ở BV / chưa khép vòng tiệt khuẩn."""
	if not due_return_at or status not in OVERDUE_STATES:
		return False
	return get_datetime(due_return_at) < now_datetime()


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


# ── I1 board — vòng đời 47 bộ (KPI + grid card + tần suất) ──────────────────


def _name_map(doctype: str, name_field: str, ids) -> dict:
	ids = list({i for i in ids if i})
	if not ids:
		return {}
	rows = frappe.get_all(doctype, filters={"name": ["in", ids]}, fields=["name", name_field])
	return {r["name"]: r.get(name_field) for r in rows}


def _user_name_map(ids) -> dict:
	ids = list({i for i in ids if i})
	if not ids:
		return {}
	rows = frappe.get_all("User", filters={"name": ["in", ids]}, fields=["name", "full_name"])
	return {r["name"]: r.full_name for r in rows}


@frappe.whitelist(methods=["GET"])
def board(current_status: str | None = None, search: str | None = None) -> dict:
	"""I1 — bảng vòng đời bộ dụng cụ: {kpis, sets[], frequency[]}.

	kpis tính trên TOÀN fleet (không phụ thuộc filter); sets[] theo filter/search (get_list →
	tôn trọng DocPerm). Mỗi card enrich item_count + BV/BS/NV của lượt active + ETA + cờ quá hạn.
	Batch query — KHÔNG N+1.
	"""
	conditions = []
	if current_status:
		conditions.append(["current_status", "=", current_status])
	if search:
		conditions.append(["set_code", "like", f"%{search}%"])

	sets = frappe.get_list(
		SET_DOCTYPE,
		filters=conditions,
		fields=["name", "set_code", "surgery_type", "current_status", "current_holder", "lifetime_loans"],
		order_by="set_code asc",
		limit_page_length=0,
	)
	set_names = [s.name for s in sets]

	comp_counts = {}
	if set_names:
		for r in frappe.get_all(
			SET_COMPONENT_DOCTYPE,
			filters={"parent": ["in", set_names], "parenttype": SET_DOCTYPE},
			fields=["parent", "count(name) as c"],
			group_by="parent",
		):
			comp_counts[r.parent] = r.c

	active = {}
	if set_names:
		for ln in frappe.get_all(
			LOAN_DOCTYPE,
			filters={"instrument_set": ["in", set_names], "status": ["in", OPEN_LOAN_STATES]},
			fields=["name", "instrument_set", "hospital", "doctor", "employee", "status", "booked_at", "due_return_at"],
			order_by="booked_at desc",
			limit_page_length=0,
		):
			active.setdefault(ln.instrument_set, ln)

	hosp_name = _name_map("AntMed Hospital", "hospital_name", [l.hospital for l in active.values()])
	doc_name = _name_map("AntMed Doctor", "full_name", [l.doctor for l in active.values()])
	emp_name = _user_name_map([l.employee for l in active.values()] + [s.current_holder for s in sets])

	rows = []
	for s in sets:
		ln = active.get(s.name)
		holder = (ln.employee if ln else None) or s.current_holder
		eta = ln.due_return_at if ln else None
		rows.append(
			{
				"name": s.name,
				"set_code": s.set_code,
				"surgery_type": s.surgery_type,
				"current_status": s.current_status,
				"item_count": comp_counts.get(s.name, 0),
				"lifetime_loans": s.lifetime_loans,
				"hospital": ln.hospital if ln else None,
				"hospital_name": hosp_name.get(ln.hospital) if ln else None,
				"doctor": ln.doctor if ln else None,
				"doctor_name": doc_name.get(ln.doctor) if ln else None,
				"holder": holder,
				"holder_name": emp_name.get(holder),
				"active_loan": ln.name if ln else None,
				"eta": str(eta) if eta else None,
				"is_overdue": _is_overdue(eta, ln.status) if ln else False,
			}
		)

	return {"kpis": _board_kpis(), "sets": rows, "frequency": _frequency_report()}


def _board_kpis() -> dict:
	"""KPI toàn fleet (mockup I1): tổng / đang lưu hành / tại kho sẵn sàng / quá hạn-thất lạc."""
	all_sets = frappe.get_all(SET_DOCTYPE, fields=["name", "current_status"], limit_page_length=0)
	total = len(all_sets)
	in_circ = sum(1 for s in all_sets if s.current_status in CIRCULATION_STATES)
	ready = sum(1 for s in all_sets if s.current_status == READY_STATE)
	lost = sum(1 for s in all_sets if s.current_status in ISSUE_STATES)
	overdue = sum(
		1
		for ln in frappe.get_all(
			LOAN_DOCTYPE, filters={"status": ["in", OVERDUE_STATES]}, fields=["due_return_at", "status"], limit_page_length=0
		)
		if _is_overdue(ln.due_return_at, ln.status)
	)
	return {"total": total, "in_circulation": in_circ, "ready": ready, "issue": lost + overdue}


def _frequency_report() -> list:
	"""Tần suất theo loại bộ (gợi ý mua thêm): số bộ / lượt mượn tháng / avg vòng quay (ngày)."""
	sets = frappe.get_all(SET_DOCTYPE, fields=["name", "surgery_type"], limit_page_length=0)
	set_type = {}
	agg = {}
	for s in sets:
		t = s.surgery_type or "—"
		set_type[s.name] = t
		agg.setdefault(t, {"set_count": 0, "loans_month": 0, "cycles": []})
		agg[t]["set_count"] += 1

	first = get_first_day(now_datetime())
	for ln in frappe.get_all(
		LOAN_DOCTYPE,
		filters={"booked_at": [">=", first]},
		fields=["instrument_set", "loaned_at", "returned_at"],
		limit_page_length=0,
	):
		t = set_type.get(ln.instrument_set)
		if not t:
			continue
		agg[t]["loans_month"] += 1
		if ln.loaned_at and ln.returned_at:
			agg[t]["cycles"].append(date_diff(ln.returned_at, ln.loaned_at))

	out = []
	for t, v in agg.items():
		avg_cycle = round(sum(v["cycles"]) / len(v["cycles"]), 1) if v["cycles"] else None
		ratio = (v["loans_month"] / v["set_count"]) if v["set_count"] else 0
		if ratio >= 6:
			suggestion, theme = "+2 bộ", "danger"
		elif ratio >= 4:
			suggestion, theme = "+1 bộ", "warn"
		else:
			suggestion, theme = "Đủ", "ok"
		out.append(
			{
				"surgery_type": t,
				"set_count": v["set_count"],
				"loans_month": v["loans_month"],
				"avg_cycle_days": avg_cycle,
				"suggestion": suggestion,
				"theme": theme,
			}
		)
	out.sort(key=lambda x: -x["loans_month"])
	return out


@frappe.whitelist(methods=["POST"])
def save_checklist(loan: str, kind: str = "handover", items_json: str | None = None) -> dict:
	"""C3 — lưu tình trạng từng món (condition/signed_by) cho checklist nhận/trả.

	kind ∈ {handover, return}. Chỉ sửa khi lượt chưa chốt bàn giao (docstatus 0).
	"""
	_check_loan_write(loan)
	doc = frappe.get_doc(LOAN_DOCTYPE, loan)
	if doc.docstatus != 0:
		frappe.throw(_("Chỉ cập nhật checklist khi lượt mượn chưa chốt bàn giao."))
	field = "handover_checklist" if kind == "handover" else "return_checklist"
	items = frappe.parse_json(items_json) if items_json else []
	by_name = {it.get("component_name"): it for it in items if it.get("component_name")}
	for row in doc.get(field) or []:
		it = by_name.get(row.component_name)
		if not it:
			continue
		if it.get("condition"):
			row.condition = it["condition"]
		if it.get("signed_by") is not None:
			row.signed_by = it["signed_by"]
	doc.save()
	return {"name": loan, "kind": kind, "rows": len(doc.get(field) or [])}


# ── M05-S4: Sự cố + nhắc quá hạn ────────────────────────────────────────────
INCIDENT_DOCTYPE = "AntMed Loan Incident"
# Map loại sự cố → trạng thái bộ.
_INCIDENT_SET_STATUS = {"Missing": "Mất", "Damaged": "Hỏng"}


@frappe.whitelist(methods=["POST"])
def report_incident(
	loan: str,
	incident_type: str,
	value_estimated: float | None = None,
	description: str | None = None,
	charged_to_hospital: int = 0,
) -> dict:
	"""Báo sự cố bộ mượn (Missing/Damaged/Late) → tạo AntMed Loan Incident + loan 'Sự cố'.

	Missing → Set 'Mất'; Damaged → Set 'Hỏng' (Late giữ trạng thái). Gate quyền write.
	"""
	_check_loan_write(loan)
	loan_doc = frappe.get_doc(LOAN_DOCTYPE, loan)
	inc = frappe.get_doc(
		{
			"doctype": INCIDENT_DOCTYPE,
			"loan": loan,
			"instrument_set": loan_doc.instrument_set,
			"incident_type": incident_type,
			"value_estimated": value_estimated,
			"description": description,
			"charged_to_hospital": int(charged_to_hospital or 0),
		}
	)
	inc.insert(ignore_permissions=True)
	frappe.db.set_value(LOAN_DOCTYPE, loan, "status", "Sự cố", update_modified=False)
	set_status = _INCIDENT_SET_STATUS.get(incident_type)
	if set_status:
		frappe.db.set_value(SET_DOCTYPE, loan_doc.instrument_set, "current_status", set_status, update_modified=False)
	return {"incident": inc.name, "loan_status": "Sự cố", "set_status": set_status}


def check_overdue_loans() -> dict:
	"""Scheduler (daily): lượt mượn quá hạn (due_return_at < now, còn ở BV/chưa xử lý) → realtime alert.

	Wire ở root hooks.py::scheduler_events.daily. Trả {count, overdue:[names]} (testable).
	"""
	now = now_datetime()
	overdue = frappe.get_all(
		LOAN_DOCTYPE,
		filters={"status": ["in", OVERDUE_STATES], "due_return_at": ["<", now]},
		fields=["name", "instrument_set", "hospital"],
		limit_page_length=0,
	)
	for o in overdue:
		try:
			frappe.publish_realtime("antmed_loan_overdue", {"loan": o["name"], "instrument_set": o["instrument_set"]})
		except Exception:
			frappe.log_error(frappe.get_traceback(), "M05 check_overdue_loans publish_realtime")
	return {"count": len(overdue), "overdue": [o["name"] for o in overdue]}
