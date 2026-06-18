# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M12 Slice S1 — Mobile/PWA: bootstrap + scan_lot + register_device.

Đường gọi: antmed_crm.api.antmed.mobile_sync.<fn> (xem m12_mobile.md §5).
@frappe.whitelist(), type-annotated, RAW dict. Đọc DƯỚI permission (BR-M12-3 / BR-13):
mỗi user chỉ thấy data trong phạm vi. Write offline (apply_outbox/pull_changes) ở M12-S2.
"""

import json

import frappe
from frappe import _
from frappe.utils import now_datetime

DEVICE_DOCTYPE = "AntMed Mobile Device"
LOT_DOCTYPE = "AntMed Lot"
SYNC_LOG_DOCTYPE = "AntMed Mobile Sync Log"

# Allowlist op offline → endpoint thật (KHÔNG dispatch tùy ý — chống abuse). BR-M12-2.
_OUTBOX_OPS = {
	"save_care_note": "antmed_crm.api.antmed.doctor_care.save_care_note",
	"check_in": "antmed_crm.api.antmed.doctor_care.check_in",
	"submit_survey": "antmed_crm.api.antmed.doctor_care.submit_survey",
	"register_device": "antmed_crm.api.antmed.mobile_sync.register_device",
}


@frappe.whitelist(methods=["GET"])
def bootstrap() -> dict:
	"""Gói khởi tạo offline cho NV: bác sỹ + phiếu giao + lượt mượn (đọc dưới permission user).

	Trả {server_ts, doctors[], deliveries[], loans[]}. Mỗi collection lọc theo DocPerm/scope.
	"""
	doctors = frappe.get_list("AntMed Doctor", fields=["name", "full_name", "hospital", "specialty"], limit_page_length=0)
	deliveries = frappe.get_list(
		"AntMed Delivery",
		fields=["name", "hospital", "status", "surgery_datetime"],
		filters=[["status", "not in", ["Đã đóng", "Từ chối"]]],
		limit_page_length=200,
		order_by="surgery_datetime asc",
	)
	loans = frappe.get_list(
		"AntMed Instrument Loan",
		fields=["name", "instrument_set", "hospital", "status", "due_return_at"],
		filters=[["status", "in", ["Đã đặt", "Đang giao", "Đang sử dụng tại BV"]]],
		limit_page_length=200,
	)
	return {"server_ts": str(now_datetime()), "doctors": doctors, "deliveries": deliveries, "loans": loans}


@frappe.whitelist(methods=["GET"])
def scan_lot(code: str) -> dict:
	"""Quét QR/barcode lô → tra cứu nhanh (lô/VTYT/HSD/CO-CQ). throw DoesNotExistError nếu không có."""
	lot = frappe.db.get_value(LOT_DOCTYPE, code, ["name", "item", "expiry_date", "recall_status", "co_cert", "cq_cert"], as_dict=True)
	if not lot:
		frappe.throw(_("Không tìm thấy lô {0}.").format(code), frappe.DoesNotExistError)
	item_name = frappe.db.get_value("AntMed Item", lot.item, "item_name") if lot.item else None
	cocq_ok = bool(lot.co_cert and lot.cq_cert)
	return {
		"lot": lot.name,
		"item": lot.item,
		"item_name": item_name,
		"expiry_date": lot.expiry_date,
		"recall_status": lot.recall_status,
		"cocq_ok": cocq_ok,
	}


@frappe.whitelist(methods=["POST"])
def register_device(device_id: str, push_token: str | None = None, platform: str | None = None, app_version: str | None = None) -> dict:
	"""Đăng ký/cập nhật thiết bị di động (push). Upsert theo device_id."""
	values = {"user": frappe.session.user, "push_token": push_token, "platform": platform, "app_version": app_version, "last_seen": now_datetime()}
	if frappe.db.exists(DEVICE_DOCTYPE, device_id):
		# Chống IDOR / device-takeover: chỉ chủ sở hữu mới được cập nhật thiết bị (push token).
		owner = frappe.db.get_value(DEVICE_DOCTYPE, device_id, "user")
		if owner and owner != frappe.session.user:
			frappe.throw(_("Thiết bị này đã được đăng ký bởi người dùng khác."), frappe.PermissionError)
		frappe.db.set_value(DEVICE_DOCTYPE, device_id, values)
	else:
		frappe.get_doc({"doctype": DEVICE_DOCTYPE, "device_id": device_id, **values}).insert(ignore_permissions=True)
	return {"device_id": device_id, "registered": True}


def _outbox_done(key: str | None) -> bool:
	"""Đã áp thành công op này (idempotency theo idempotency_key) chưa? BR-M12-1."""
	return bool(key) and bool(frappe.db.exists(SYNC_LOG_DOCTYPE, {"doctype_synced": key, "direction": "Push", "status": "OK"}))


def _log_sync(key: str | None, status: str, error: str | None = None) -> None:
	frappe.get_doc(
		{"doctype": SYNC_LOG_DOCTYPE, "user": frappe.session.user, "direction": "Push", "doctype_synced": key, "record_count": 1, "status": status, "error_log": error}
	).insert(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def apply_outbox(operations) -> dict:
	"""Replay hàng đợi offline của mobile. Mỗi op {idempotency_key, operation, payload}.

	- Allowlist (_OUTBOX_OPS) — KHÔNG dispatch endpoint tùy ý.
	- Idempotent theo idempotency_key (BR-M12-1): đã OK → 'Skipped', không áp lại.
	- Server BR vẫn chạy (BR-M12-2): lỗi nghiệp vụ → 'Failed' + message BR-XX (không nuốt);
	  lỗi hệ thống → log_error + message hằng (không leak traceback).
	Trả {results:[{idempotency_key, status, ...}], applied, failed}.
	"""
	ops = json.loads(operations) if isinstance(operations, str) else (operations or [])
	results = []
	applied = 0
	failed = 0
	for op in ops:
		op = op or {}
		key = op.get("idempotency_key")
		name = op.get("operation")
		payload = op.get("payload") or {}
		if _outbox_done(key):
			results.append({"idempotency_key": key, "status": "Skipped"})
			continue
		if name not in _OUTBOX_OPS:
			results.append({"idempotency_key": key, "status": "Rejected", "error": "operation không hợp lệ"})
			failed += 1
			continue
		try:
			fn = frappe.get_attr(_OUTBOX_OPS[name])
			res = fn(**payload)
			_log_sync(key, "OK")
			applied += 1
			results.append({"idempotency_key": key, "status": "OK", "result": res})
		except frappe.ValidationError as e:  # lỗi nghiệp vụ BR-XX — message dành cho người dùng
			_log_sync(key, "Failed", str(e))
			failed += 1
			results.append({"idempotency_key": key, "status": "Failed", "error": str(e)})
		except Exception:
			frappe.log_error(frappe.get_traceback(), "M12 apply_outbox")
			_log_sync(key, "Failed", "Lỗi hệ thống")
			failed += 1
			results.append({"idempotency_key": key, "status": "Failed", "error": "Lỗi hệ thống"})
	return {"results": results, "applied": applied, "failed": failed}
