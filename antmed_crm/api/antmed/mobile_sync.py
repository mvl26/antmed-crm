# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M12 Slice S1 — Mobile/PWA: bootstrap + scan_lot + register_device.

Đường gọi: antmed_crm.api.antmed.mobile_sync.<fn> (xem m12_mobile.md §5).
@frappe.whitelist(), type-annotated, RAW dict. Đọc DƯỚI permission (BR-M12-3 / BR-13):
mỗi user chỉ thấy data trong phạm vi. Write offline (apply_outbox/pull_changes) ở M12-S2.
"""

import frappe
from frappe import _
from frappe.utils import now_datetime

DEVICE_DOCTYPE = "AntMed Mobile Device"
LOT_DOCTYPE = "AntMed Lot"


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
		frappe.db.set_value(DEVICE_DOCTYPE, device_id, values)
	else:
		frappe.get_doc({"doctype": DEVICE_DOCTYPE, "device_id": device_id, **values}).insert(ignore_permissions=True)
	return {"device_id": device_id, "registered": True}
