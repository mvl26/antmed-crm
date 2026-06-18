# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M13 Slice S1 — Tích hợp (framework: Setting + Log + dispatcher skeleton).

⚠️ STUB: KHÔNG gọi API thật (Zalo/SMS/bank/HĐĐT) — connector thật = ROADMAP (cần DPA +
sandbox creds). Secrets (Password) KHÔNG bao giờ trả ra FE/log (BR-INT-01) — get_settings
chỉ trả 'configured' bool. Mọi gọi tích hợp ghi 1 AntMed Integration Log (BR-10/BR-INT).
"""

import frappe
from frappe import _

SETTING_DOCTYPE = "AntMed Integration Setting"
LOG_DOCTYPE = "AntMed Integration Log"
# (prov, secret_field, extra non-secret field)
_PROVIDERS = (("zalo", "zalo_access_token", "zalo_oa_id"), ("sms", "sms_api_key", "sms_provider"), ("bank", "bank_api_key", "bank_provider"))

LOG_LIST_FIELDS = ["name", "integration_name", "direction", "endpoint", "status", "retry_count", "ts"]


def _log(integration_name, direction, endpoint, status, request_payload=None, response_payload=None, error_message=None, retry_count=0):
	"""Ghi 1 dòng nhật ký tích hợp (server-side). Trả name. (KHÔNG whitelist.)"""
	doc = frappe.get_doc(
		{
			"doctype": LOG_DOCTYPE,
			"integration_name": integration_name,
			"direction": direction,
			"endpoint": endpoint,
			"status": status,
			"request_payload": request_payload,
			"response_payload": response_payload,
			"error_message": error_message,
			"retry_count": int(retry_count or 0),
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist(methods=["GET"])
def get_settings() -> dict:
	"""Cấu hình tích hợp — CHỈ trả 'configured' bool + field không nhạy cảm. KHÔNG secrets (BR-INT-01)."""
	if not frappe.has_permission(SETTING_DOCTYPE, "read"):
		frappe.throw(_("Bạn không có quyền xem cấu hình tích hợp."), frappe.PermissionError)
	s = frappe.get_doc(SETTING_DOCTYPE)
	out = {"zalo_oa_id": s.zalo_oa_id, "sms_provider": s.sms_provider, "sms_brand_name": s.sms_brand_name, "bank_provider": s.bank_provider}
	for prov, secret_field, _extra in _PROVIDERS:
		out[f"{prov}_configured"] = bool(s.get_password(secret_field, raise_exception=False))
	out["map_configured"] = bool(s.get_password("map_api_key", raise_exception=False))
	return out


@frappe.whitelist(methods=["GET"])
def list_integration_logs(status: str | None = None, integration_name: str | None = None, start: int = 0, page_length: int = 20) -> dict:
	"""Nhật ký tích hợp (KHÔNG kèm payload nặng). Trả RAW {data, total_count} count==rows."""
	conditions = []
	if status:
		conditions.append(["status", "=", status])
	if integration_name:
		conditions.append(["integration_name", "=", integration_name])
	start = max(0, int(start))
	page_length = max(0, int(page_length))
	rows = frappe.get_list(LOG_DOCTYPE, filters=conditions, fields=LOG_LIST_FIELDS, limit_start=start, limit_page_length=page_length or 0, order_by="creation desc")
	total_count = len(frappe.get_list(LOG_DOCTYPE, filters=conditions, pluck="name", limit_page_length=0))
	return {"data": rows, "total_count": total_count}


@frappe.whitelist(methods=["GET"])
def get_integration_log(name: str) -> dict:
	"""Chi tiết 1 nhật ký (request/response). throw PermissionError nếu không read."""
	if not frappe.has_permission(LOG_DOCTYPE, "read", doc=name):
		frappe.throw(_("Bạn không có quyền xem nhật ký này."), frappe.PermissionError)
	doc = frappe.get_doc(LOG_DOCTYPE, name).as_dict()
	keys = ("name", "integration_name", "direction", "endpoint", "status", "retry_count", "ts", "error_message", "request_payload", "response_payload")
	return {k: doc.get(k) for k in keys}


@frappe.whitelist(methods=["POST"])
def retry_log(name: str) -> dict:
	"""Đặt lại nhật ký Failed/DeadLetter để thử lại (stub — dispatcher thật ở ROADMAP). BR-INT-03."""
	if not frappe.has_permission(LOG_DOCTYPE, "write", doc=name):
		frappe.throw(_("Bạn không có quyền thử lại."), frappe.PermissionError)
	rc = (frappe.db.get_value(LOG_DOCTYPE, name, "retry_count") or 0) + 1
	frappe.db.set_value(LOG_DOCTYPE, name, {"status": "Retrying", "retry_count": rc})
	return {"name": name, "status": "Retrying", "retry_count": rc}
