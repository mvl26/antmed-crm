# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""AntMed — Công việc (Task) trên doctype CRM Task (port từ FCRM dùng cho AntMed CRM).

Đường gọi: antmed_crm.api.antmed.tasks.<fn>. @frappe.whitelist(methods=["GET"]), type-annotated,
RAW dict. count==rows (BR-13 fail-closed: đọc DƯỚI permission → NV chỉ thấy task trong phạm vi).
Task gắn được vào bản ghi AntMed (Hợp đồng/Bệnh viện/Phiếu giao…) qua reference_doctype/_docname.
"""

import json

import frappe

TASK_DOCTYPE = "CRM Task"
TASK_FIELDS = [
	"name",
	"title",
	"status",
	"priority",
	"start_date",
	"due_date",
	"assigned_to",
	"reference_doctype",
	"reference_docname",
]
# Trạng thái "đang mở" (chưa đóng) — phục vụ KPI + lọc nhanh ở UI.
OPEN_STATUSES = ("Backlog", "Todo", "In Progress")


def _coerce_filters(filters: dict | str | None) -> list:
	if not filters:
		return []
	if isinstance(filters, str):
		try:
			filters = json.loads(filters)
		except Exception:
			return []
	if isinstance(filters, dict):
		return [[k, "=", v] for k, v in filters.items()]
	return filters if isinstance(filters, list) else []


@frappe.whitelist(methods=["GET"])
def list_tasks(
	filters: dict | str | None = None,
	status: str | None = None,
	reference_doctype: str | None = None,
	reference_docname: str | None = None,
	start: int = 0,
	page_length: int = 50,
) -> dict:
	"""Danh sách công việc AntMed. Trả RAW {data, total_count, open_count} — count==rows khi page_length=0.

	Mỗi item gồm TASK_FIELDS + assigned_to_name (resolve qua User, KHÔNG lộ email) + is_open.
	Lọc tùy chọn: status; hoặc gắn theo bản ghi AntMed (reference_doctype + reference_docname).
	"""
	conditions = _coerce_filters(filters)
	if status:
		conditions.append(["status", "=", status])
	if reference_doctype:
		conditions.append(["reference_doctype", "=", reference_doctype])
	if reference_docname:
		conditions.append(["reference_docname", "=", reference_docname])

	start = max(0, int(start))
	page_length = max(0, int(page_length))

	rows = frappe.get_list(
		TASK_DOCTYPE,
		filters=conditions,
		fields=TASK_FIELDS,
		limit_start=start,
		limit_page_length=page_length or 0,
		order_by="due_date asc, modified desc",
	)

	cache: dict = {}
	open_count = 0
	for r in rows:
		emp = r.get("assigned_to")
		if emp and emp not in cache:
			cache[emp] = frappe.db.get_value("User", emp, "full_name")
		r["assigned_to_name"] = cache.get(emp) if emp else None
		r["is_open"] = r.get("status") in OPEN_STATUSES
		if r["is_open"]:
			open_count += 1

	total_count = len(frappe.get_list(TASK_DOCTYPE, filters=conditions, pluck="name", limit_page_length=0))
	return {"data": rows, "total_count": total_count, "open_count": open_count}
