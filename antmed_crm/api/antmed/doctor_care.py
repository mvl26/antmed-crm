# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M07 Slice S1 — endpoint CSKH bác sỹ (Doctor Visit + Care Note).

Đường gọi: antmed_crm.api.antmed.doctor_care.<fn> (xem m07_doctor_care.md §5).
@frappe.whitelist(), type-annotated, RAW dict. count==rows (BR-13). BR-11 (quà tặng) ở slice sau.
"""

import frappe
from frappe import _
from frappe.utils import getdate, now_datetime, nowdate

VISIT_DOCTYPE = "AntMed Doctor Visit"
NOTE_DOCTYPE = "AntMed Care Note"
DOCTOR_DOCTYPE = "AntMed Doctor"
GIFT_DOCTYPE = "AntMed Doctor Gift"
SURVEY_DOCTYPE = "AntMed Satisfaction Survey"
CALL_PLAN_DOCTYPE = "AntMed Call Plan"

CALL_LOG_DOCTYPE = "CRM Call Log"
CALL_OUTCOME_TO_STATUS = {
	"Nghe máy": "Completed",
	"Không nghe": "No Answer",
	"Máy bận": "Busy",
	"Hộp thư": "No Answer",
}
CALL_STATUS_TO_OUTCOME = {"Completed": "Nghe máy", "No Answer": "Không nghe", "Busy": "Máy bận"}
CALL_LOG_LIST_FIELDS = [
	"name", "id", "type", "status", "duration", "start_time",
	"caller", "caller.full_name as caller_name", "note", "note.content as note_text",
]

GIFT_LIST_FIELDS = ["name", "doctor", "gift_date", "item_or_text", "value_vnd", "approved_by"]
GIFT_LIST_ITEM_KEYS = ("name", "doctor", "gift_date", "item_or_text", "value_vnd", "approved_by")

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


@frappe.whitelist(methods=["POST"])
def create_gift(
	doctor: str,
	item_or_text: str,
	value_vnd: float | None = None,
	purpose: str | None = None,
	approved_by: str | None = None,
) -> dict:
	"""Ghi nhận quà tặng bác sỹ. BR-11 (approved_by bắt buộc) enforce ở controller validate."""
	if not frappe.has_permission(GIFT_DOCTYPE, "create"):
		frappe.throw(_("Bạn không có quyền ghi quà tặng."), frappe.PermissionError)
	doc = frappe.get_doc(
		{
			"doctype": GIFT_DOCTYPE,
			"doctor": doctor,
			"item_or_text": item_or_text,
			"value_vnd": value_vnd,
			"purpose": purpose,
			"approved_by": approved_by,
			"gift_date": now_datetime().date(),
		}
	)
	doc.insert(ignore_permissions=True)  # validate BR-11 vẫn chạy
	return {"gift": doc.name, "approved_by": approved_by}


@frappe.whitelist(methods=["GET"])
def list_gifts(doctor: str | None = None, start: int = 0, page_length: int = 20) -> dict:
	"""Danh sách quà tặng (review compliance). count==rows dưới DocPerm."""
	conditions = []
	if doctor:
		conditions.append(["doctor", "=", doctor])
	start = max(0, int(start))
	page_length = max(0, int(page_length))
	rows = frappe.get_list(
		GIFT_DOCTYPE,
		filters=conditions,
		fields=GIFT_LIST_FIELDS,
		limit_start=start,
		limit_page_length=page_length or 0,
		order_by="gift_date desc",
	)
	data = [{k: r.get(k) for k in GIFT_LIST_ITEM_KEYS} for r in rows]
	total_count = len(frappe.get_list(GIFT_DOCTYPE, filters=conditions, pluck="name", limit_page_length=0))
	return {"data": data, "total_count": total_count}


@frappe.whitelist(methods=["POST"])
def submit_survey(doctor: str, score_1_5: int, comments: str | None = None, delivery: str | None = None, instrument_loan: str | None = None) -> dict:
	"""Ghi khảo sát hài lòng bác sỹ (điểm 1-5)."""
	if not frappe.has_permission(SURVEY_DOCTYPE, "create"):
		frappe.throw(_("Bạn không có quyền ghi khảo sát."), frappe.PermissionError)
	doc = frappe.get_doc(
		{
			"doctype": SURVEY_DOCTYPE,
			"doctor": doctor,
			"score_1_5": int(score_1_5),
			"comments": comments,
			"delivery": delivery,
			"instrument_loan": instrument_loan,
			"responded_at": now_datetime(),
		}
	)
	doc.insert(ignore_permissions=True)
	return {"survey": doc.name, "doctor": doctor}


def send_call_plan_today() -> dict:
	"""Scheduler (daily): Call Plan tới hạn thăm (next_visit <= hôm nay) → realtime nhắc NV.

	Trả {count, due:[{name, doctor, sales_rep}]}.
	"""
	due = frappe.get_all(
		CALL_PLAN_DOCTYPE,
		filters={"next_visit": ["<=", nowdate()]},
		fields=["name", "doctor", "sales_rep"],
		limit_page_length=0,
	)
	for p in due:
		try:
			frappe.publish_realtime("antmed_call_plan_due", {"call_plan": p["name"], "doctor": p["doctor"]}, user=p.get("sales_rep"))
		except Exception:
			frappe.log_error(frappe.get_traceback(), "M07 send_call_plan_today")
	return {"count": len(due), "due": due}


@frappe.whitelist(methods=["POST"])
def log_call(
	doctor: str,
	outcome: str,
	duration_sec: int | str | None = None,
	note: str | None = None,
	to_number: str | None = None,
	called_at: str | None = None,
) -> dict:
	"""Ghi 1 cuộc gọi thủ công (tel:) vào CRM Call Log, link Dynamic → AntMed Doctor.

	BR-13: gate trên quyền đọc AntMed Doctor (User Permission allow=AntMed Hospital scope
	doctor qua hospital). CRM Call Log tạo ignore_permissions sau khi đã gate (tránh phải
	cấu hình DocPerm CRM Call Log cho role 'NV kinh doanh').
	"""
	if not frappe.has_permission(DOCTOR_DOCTYPE, "read", doc=doctor):
		frappe.throw(_("Bạn không có quyền với bác sỹ này."), frappe.PermissionError)

	status = CALL_OUTCOME_TO_STATUS.get(outcome)
	if not status:
		frappe.throw(_("Kết quả cuộc gọi không hợp lệ."))

	to = (to_number or frappe.db.get_value(DOCTOR_DOCTYPE, doctor, "phone") or "").strip()
	if not to:
		frappe.throw(_("Bác sỹ chưa có số điện thoại."))

	from_no = frappe.db.get_value("User", frappe.session.user, "mobile_no") or frappe.session.user

	try:
		duration = int(duration_sec) if duration_sec not in (None, "") else 0
	except (TypeError, ValueError):
		duration = 0

	call = frappe.get_doc(
		{
			"doctype": CALL_LOG_DOCTYPE,
			"type": "Outgoing",
			"telephony_medium": "Manual",
			"status": status,
			"from": from_no,
			"to": to,
			"caller": frappe.session.user,
			"duration": max(0, duration),
			"start_time": called_at or now_datetime(),
			"reference_doctype": DOCTOR_DOCTYPE,
			"reference_docname": doctor,
		}
	)

	if note:
		fcrm_note = frappe.get_doc(
			{
				"doctype": "FCRM Note",
				"title": _("Ghi chú cuộc gọi"),
				"content": note,
				"reference_doctype": DOCTOR_DOCTYPE,
				"reference_docname": doctor,
			}
		).insert(ignore_permissions=True)
		call.note = fcrm_note.name

	call.insert(ignore_permissions=True)
	return {"call_log": call.name, "status": status}


@frappe.whitelist(methods=["GET"])
def list_call_logs(doctor: str, start: int = 0, page_length: int = 20) -> dict:
	"""Nhật ký cuộc gọi của 1 bác sỹ (CRM Call Log reference = AntMed Doctor). BR-13 gate read."""
	if not frappe.has_permission(DOCTOR_DOCTYPE, "read", doc=doctor):
		frappe.throw(_("Bạn không có quyền với bác sỹ này."), frappe.PermissionError)

	conditions = {"reference_doctype": DOCTOR_DOCTYPE, "reference_docname": doctor}
	start = max(0, int(start))
	page_length = max(0, int(page_length))

	rows = frappe.get_all(
		CALL_LOG_DOCTYPE,
		filters=conditions,
		fields=CALL_LOG_LIST_FIELDS,
		order_by="start_time desc",
		limit_start=start,
		limit_page_length=page_length or 0,
	)
	for r in rows:
		r["outcome"] = CALL_STATUS_TO_OUTCOME.get(r.get("status"), r.get("status"))
		r["direction"] = "Gọi đi" if r.get("type") == "Outgoing" else "Gọi đến"

	return {"data": rows, "total_count": frappe.db.count(CALL_LOG_DOCTYPE, conditions)}


def notify_doctor_birthdays(within_days: int = 7) -> dict:
	"""Scheduler (daily): bác sỹ có sinh nhật trong `within_days` ngày tới (bỏ qua năm) → nhắc.

	Trả {count, upcoming:[{doctor, full_name, days_to_birthday}]}.
	"""
	today = getdate(nowdate())
	upcoming = []
	for d in frappe.get_all(DOCTOR_DOCTYPE, filters=[["birthday", "is", "set"]], fields=["name", "full_name", "birthday"], limit_page_length=0):
		bd = getdate(d["birthday"])
		try:
			this_year = bd.replace(year=today.year)
		except ValueError:  # 29/02
			continue
		if this_year < today:
			this_year = this_year.replace(year=today.year + 1)
		days = (this_year - today).days
		if 0 <= days <= int(within_days):
			upcoming.append({"doctor": d["name"], "full_name": d["full_name"], "days_to_birthday": days})
	return {"count": len(upcoming), "upcoming": upcoming}
