# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M14 Slice S1 — Audit hash-chain (BR-10): AntMed Audit Log.

write_log = server-side (KHÔNG whitelist) — gọi từ doc_events/handler nhạy cảm. Tính
prev_hash (hash bản ghi cuối) → hash_sha256 = SHA256(prev_hash + canonical_payload).
verify_chain walk lại toàn bộ phát hiện chuỗi gãy. Insert TRỰC TIẾP = vỡ chain → KHÔNG làm.
"""

import hashlib

import frappe
from frappe import _
from frappe.utils import now_datetime

AUDIT_DOCTYPE = "AntMed Audit Log"
# Field tham gia hash (thứ tự cố định) — write_log & verify_chain DÙNG CHUNG (Hyrum-safe).
_HASH_FIELDS = ("ref_doctype", "ref_name", "action", "actor", "ts", "before_json", "after_json")


def _payload_str(d: dict) -> str:
	"""Chuỗi canonical từ các field tham gia hash (str ổn định, ts giây)."""
	return "|".join(str(d.get(f) or "") for f in _HASH_FIELDS)


def _json(v) -> str:
	if v is None:
		return ""
	import json

	return json.dumps(v, sort_keys=True, ensure_ascii=False, default=str)


def write_log(ref_doctype: str, ref_name: str, action: str, before=None, after=None, actor: str | None = None) -> str:
	"""Ghi 1 dòng audit nối chuỗi hash. Trả name. (KHÔNG whitelist — server-side only.)"""
	ts = now_datetime().replace(microsecond=0)  # giây — tránh lệch hash khi round-trip Datetime
	row = {
		"ref_doctype": ref_doctype,
		"ref_name": ref_name,
		"action": action,
		"actor": actor or frappe.session.user,
		"ts": str(ts),
		"before_json": _json(before),
		"after_json": _json(after),
	}
	last = frappe.get_all(AUDIT_DOCTYPE, fields=["hash_sha256"], order_by="creation desc", limit_page_length=1)
	prev = (last[0]["hash_sha256"] if last else "") or ""
	row_hash = hashlib.sha256((prev + _payload_str(row)).encode()).hexdigest()
	doc = frappe.get_doc({"doctype": AUDIT_DOCTYPE, **row, "ts": ts, "prev_hash": prev, "hash_sha256": row_hash})
	doc.insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist(methods=["GET"])
def verify_chain() -> dict:
	"""Walk toàn bộ audit theo thứ tự ghi, recompute hash → phát hiện chuỗi gãy (BR-10).

	Trả {ok, broken_at, count}. Chỉ admin (DocPerm read trên Audit Log).
	"""
	if not frappe.has_permission(AUDIT_DOCTYPE, "read"):
		frappe.throw(_("Bạn không có quyền kiểm tra audit."), frappe.PermissionError)
	logs = frappe.get_all(
		AUDIT_DOCTYPE,
		fields=["name", "ref_doctype", "ref_name", "action", "actor", "ts", "before_json", "after_json", "hash_sha256"],
		order_by="creation asc",
	)
	prev = ""
	for log in logs:
		row = {**log, "ts": str(log.get("ts") or "")}
		expected = hashlib.sha256((prev + _payload_str(row)).encode()).hexdigest()
		if expected != log["hash_sha256"]:
			return {"ok": False, "broken_at": log["name"], "count": len(logs)}
		prev = log["hash_sha256"]
	return {"ok": True, "broken_at": None, "count": len(logs)}


@frappe.whitelist(methods=["GET"])
def list_logs(ref_doctype: str | None = None, action: str | None = None, start: int = 0, page_length: int = 20) -> dict:
	"""Danh sách audit log. Trả RAW {data, total_count} — count==rows dưới DocPerm."""
	conditions = []
	if ref_doctype:
		conditions.append(["ref_doctype", "=", ref_doctype])
	if action:
		conditions.append(["action", "=", action])
	start = max(0, int(start))
	page_length = max(0, int(page_length))
	fields = ["name", "ref_doctype", "ref_name", "action", "actor", "ts", "hash_sha256"]
	rows = frappe.get_list(AUDIT_DOCTYPE, filters=conditions, fields=fields, limit_start=start, limit_page_length=page_length or 0, order_by="creation desc")
	total_count = len(frappe.get_list(AUDIT_DOCTYPE, filters=conditions, pluck="name", limit_page_length=0))
	return {"data": rows, "total_count": total_count}
