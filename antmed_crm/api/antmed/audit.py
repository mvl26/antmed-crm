# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M14 Slice S1 — Audit hash-chain (BR-10): AntMed Audit Log.

write_log = server-side (KHÔNG whitelist) — gọi từ doc_events/handler nhạy cảm. Tính
prev_hash (hash bản ghi cuối) → hash_sha256 = SHA256(prev_hash + canonical_payload).
verify_chain walk lại toàn bộ phát hiện chuỗi gãy. Insert TRỰC TIẾP = vỡ chain → KHÔNG làm.
"""

import hashlib
import secrets

import frappe
from frappe import _
from frappe.utils import add_to_date, get_datetime, now_datetime

AUDIT_DOCTYPE = "AntMed Audit Log"
SESSION_2FA_DOCTYPE = "AntMed 2FA Session"
OTP_TTL_MIN = 5
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


def write_log(
	ref_doctype: str, ref_name: str, action: str, before=None, after=None, actor: str | None = None
) -> str:
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
	last = frappe.get_all(
		AUDIT_DOCTYPE, fields=["hash_sha256"], order_by="creation desc", limit_page_length=1
	)
	prev = (last[0]["hash_sha256"] if last else "") or ""
	row_hash = hashlib.sha256((prev + _payload_str(row)).encode()).hexdigest()
	doc = frappe.get_doc(
		{"doctype": AUDIT_DOCTYPE, **row, "ts": ts, "prev_hash": prev, "hash_sha256": row_hash}
	)
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
		fields=[
			"name",
			"ref_doctype",
			"ref_name",
			"action",
			"actor",
			"ts",
			"before_json",
			"after_json",
			"hash_sha256",
		],
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
def list_logs(
	ref_doctype: str | None = None, action: str | None = None, start: int = 0, page_length: int = 20
) -> dict:
	"""Danh sách audit log. Trả RAW {data, total_count} — count==rows dưới DocPerm."""
	conditions = []
	if ref_doctype:
		conditions.append(["ref_doctype", "=", ref_doctype])
	if action:
		conditions.append(["action", "=", action])
	start = max(0, int(start))
	page_length = max(0, int(page_length))
	fields = ["name", "ref_doctype", "ref_name", "action", "actor", "ts", "hash_sha256"]
	rows = frappe.get_list(
		AUDIT_DOCTYPE,
		filters=conditions,
		fields=fields,
		limit_start=start,
		limit_page_length=page_length or 0,
		order_by="creation desc",
	)
	total_count = len(frappe.get_list(AUDIT_DOCTYPE, filters=conditions, pluck="name", limit_page_length=0))
	return {"data": rows, "total_count": total_count}


# ── M14-S2: 2FA (BR-12) — cơ chế additive (CHƯA wire vào handler nhạy cảm) ────
def _hash_otp(otp: str) -> str:
	return hashlib.sha256(str(otp).encode()).hexdigest()


@frappe.whitelist(methods=["POST"])
def request_2fa(action_label: str) -> dict:
	"""Tạo phiên 2FA cho 1 thao tác nhạy cảm: sinh OTP, lưu HASH, gửi qua kênh (M13/ROADMAP).

	⚠️ OTP KHÔNG bao giờ trả ra response (BR-12). Trả {session, expires_at}.
	"""
	otp = f"{secrets.randbelow(1000000):06d}"
	expires = add_to_date(now_datetime(), minutes=OTP_TTL_MIN)
	s = frappe.get_doc(
		{
			"doctype": SESSION_2FA_DOCTYPE,
			"user": frappe.session.user,
			"action_label": action_label,
			"otp_hash": _hash_otp(otp),
			"expires_at": expires,
			"used": 0,
		}
	)
	s.insert(ignore_permissions=True)
	# STUB: gửi OTP qua SMS/Zalo (integrations._log + connector thật = M13/ROADMAP).
	return {"session": s.name, "expires_at": str(expires)}


@frappe.whitelist(methods=["POST"])
def confirm_2fa(session: str, otp: str) -> dict:
	"""Xác nhận OTP cho phiên 2FA → used=1. Sai/hết hạn/đã dùng → throw BR-12."""
	s = frappe.get_doc(SESSION_2FA_DOCTYPE, session)
	if s.user != frappe.session.user:
		frappe.throw(_("Phiên 2FA không thuộc về bạn."), frappe.PermissionError)
	if s.used:
		frappe.throw(_("BR-12: OTP đã được sử dụng."))
	if get_datetime(s.expires_at) < now_datetime():
		frappe.throw(_("BR-12: OTP đã hết hạn, vui lòng yêu cầu lại."))
	if s.otp_hash != _hash_otp(otp):
		frappe.throw(_("BR-12: Mã OTP không đúng."))
	frappe.db.set_value(SESSION_2FA_DOCTYPE, session, "used", 1)
	return {"ok": True, "session": session}


def _enforce_2fa(action_label: str) -> None:
	"""Gate thao tác nhạy cảm (BR-12): cần 1 phiên 2FA đã confirm trong TTL. Else throw.

	Gọi ở ĐẦU handler nhạy cảm (hủy DO đã ký / phát hành HĐĐT / xóa chứng từ). CHƯA wire
	tự động — chờ sign-off để gắn vào từng handler (đổi hành vi flow cũ).
	"""
	cutoff = add_to_date(now_datetime(), minutes=-OTP_TTL_MIN)
	if not frappe.db.exists(
		SESSION_2FA_DOCTYPE,
		{"user": frappe.session.user, "action_label": action_label, "used": 1, "modified": [">", cutoff]},
	):
		frappe.throw(_("BR-12: Thao tác '{0}' cần xác thực 2 lớp (OTP).").format(action_label))
