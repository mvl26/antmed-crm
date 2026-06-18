# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""AntMed — Ghi chú (FCRM Note) + Dòng thời gian hoạt động gắn lên bản ghi AntMed.

Port FCRM Note dùng cho AntMed: ghi chú/công việc đính theo bản ghi (Hợp đồng/Bệnh viện/
Phiếu giao…) qua reference_doctype/reference_docname → 1 timeline thống nhất cho UI (AmTimeline).
Đường gọi: antmed_crm.api.antmed.notes.<fn>. GET đọc DƯỚI permission (BR-13); add_note = POST.
"""

import re

import frappe
from frappe import _

NOTE_DOCTYPE = "FCRM Note"
TASK_DOCTYPE = "CRM Task"
NOTE_FIELDS = ["name", "title", "content", "owner", "creation", "modified"]
TASK_FIELDS = ["name", "title", "status", "priority", "due_date", "assigned_to", "creation"]
OPEN_TASK_STATUSES = ("Todo", "In Progress")


def _ref(reference_doctype: str, reference_docname: str) -> list:
	return [
		["reference_doctype", "=", reference_doctype],
		["reference_docname", "=", reference_docname],
	]


def _strip_html(html: str | None) -> str:
	if not html:
		return ""
	return re.sub(r"<[^>]+>", "", html).strip()


@frappe.whitelist(methods=["GET"])
def list_notes(reference_doctype: str, reference_docname: str) -> dict:
	"""Ghi chú gắn 1 bản ghi AntMed. RAW {data, total_count} — count==rows dưới permission (BR-13)."""
	rows = frappe.get_list(
		NOTE_DOCTYPE,
		filters=_ref(reference_doctype, reference_docname),
		fields=NOTE_FIELDS,
		order_by="creation desc",
		limit_page_length=0,
	)
	cache: dict = {}
	for r in rows:
		u = r.get("owner")
		if u and u not in cache:
			cache[u] = frappe.db.get_value("User", u, "full_name")
		r["owner_name"] = cache.get(u) if u else None
	return {"data": rows, "total_count": len(rows)}


@frappe.whitelist(methods=["POST"])
def add_note(
	reference_doctype: str, reference_docname: str, content: str, title: str | None = None
) -> dict:
	"""Thêm ghi chú vào bản ghi AntMed. content bắt buộc (không rỗng). Trả {name, title, content}."""
	if not (content and content.strip()):
		frappe.throw(_("Nội dung ghi chú không được để trống."))
	# FCRM Note.title BẮT BUỘC → suy từ content khi không truyền title (tránh MandatoryError).
	title = (title or "").strip() or _strip_html(content)[:60] or "Ghi chú"
	doc = frappe.get_doc(
		{
			"doctype": NOTE_DOCTYPE,
			"title": title,
			"content": content,
			"reference_doctype": reference_doctype,
			"reference_docname": reference_docname,
		}
	).insert()
	return {"name": doc.name, "title": doc.title, "content": doc.content}


@frappe.whitelist(methods=["GET"])
def activity(reference_doctype: str, reference_docname: str) -> dict:
	"""Dòng thời gian hoạt động (Ghi chú + Công việc) của 1 bản ghi AntMed.

	RAW { events:[{type,name,time,text,sub,highlight}], note_count, task_count } — sort mới→cũ.
	Dùng cho AmTimeline (events:[{time,text,sub,highlight}]). Đọc DƯỚI permission (BR-13).
	"""
	conditions = _ref(reference_doctype, reference_docname)
	notes = frappe.get_list(
		NOTE_DOCTYPE, filters=conditions, fields=NOTE_FIELDS, order_by="creation desc", limit_page_length=0
	)
	tasks = frappe.get_list(
		TASK_DOCTYPE, filters=conditions, fields=TASK_FIELDS, order_by="creation desc", limit_page_length=0
	)

	cache: dict = {}

	def who(u):
		if not u:
			return None
		if u not in cache:
			cache[u] = frappe.db.get_value("User", u, "full_name")
		return cache[u] or u

	events = []
	for n in notes:
		text = n.get("title") or _strip_html(n.get("content"))[:80] or "Ghi chú"
		events.append(
			{
				"type": "note",
				"name": n["name"],
				"ts": str(n.get("creation") or ""),
				"time": str(n.get("creation") or "")[:16],
				"text": text,
				"sub": f"Ghi chú · {who(n.get('owner'))}",
			}
		)
	for t in tasks:
		sub = f"Công việc · {t.get('status') or ''}"
		if t.get("assigned_to"):
			sub += f" · {who(t.get('assigned_to'))}"
		events.append(
			{
				"type": "task",
				"name": t["name"],
				"ts": str(t.get("creation") or ""),
				"time": str(t.get("creation") or "")[:16],
				"text": t.get("title") or "Công việc",
				"sub": sub,
				"highlight": t.get("status") in OPEN_TASK_STATUSES,
			}
		)

	events.sort(key=lambda e: e["ts"], reverse=True)
	for e in events:
		e.pop("ts", None)

	return {"events": events, "note_count": len(notes), "task_count": len(tasks)}
