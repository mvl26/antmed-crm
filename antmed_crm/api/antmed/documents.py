# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M06 Slice S1 — endpoint Chứng từ (bundle + hàng chờ phát hành).

Đường gọi: antmed_crm.api.antmed.documents.<fn> (xem m06_documents.md §5).
@frappe.whitelist(), type-annotated, RAW dict. count==rows (BR-13). BR-03 (gate CO/CQ):
slice này ĐÁNH DẤU thiếu CO/CQ (missing_items/chips); chặn CỨNG phát hành ở M06-S3 (HĐĐT).
"""

import json

import frappe
from frappe import _

DOCUMENT_DOCTYPE = "AntMed Document"
QUEUE_DOCTYPE = "AntMed Document Release Queue"
DELIVERY_DOCTYPE = "AntMed Delivery"
CERTIFICATE_DOCTYPE = "AntMed Certificate"
LOT_DOCTYPE = "AntMed Lot"
EINVOICE_DOCTYPE = "AntMed E-Invoice"
PROVIDER_DOCTYPE = "AntMed E-Invoice Provider"
HANDOVER_DOCTYPE = "AntMed Handover Confirmation"

# Trạng thái bundle đã phát hành → vào màn đối soát ký nhận.
HANDOVER_REVIEW_STATUSES = ("Đã phát hành", "Đã gửi BV", "BV đã ký nhận")
HANDOVER_LIST_FIELDS = ["name", "delivery", "hospital", "hospital.hospital_name as hospital_name", "status"]
HANDOVER_LIST_ITEM_KEYS = ("name", "delivery", "hospital", "hospital_name", "status")

EINVOICE_LIST_FIELDS = ["name", "delivery", "provider", "status", "ma_cqt", "signed_at"]
EINVOICE_LIST_ITEM_KEYS = ("name", "delivery", "provider", "status", "ma_cqt", "signed_at")

CERT_LIST_FIELDS = ["name", "cert_no", "cert_type", "item", "lot", "issued_date", "expires_at"]
CERT_LIST_ITEM_KEYS = ("name", "cert_no", "cert_type", "item", "lot", "issued_date", "expires_at")

QUEUE_LIST_FIELDS = ["name", "delivery", "document_bundle", "status", "missing_chips", "assigned_to", "ts"]
# Key cũ (backward-compat) — KHÔNG đổi/xoá. Key MỚI (ts/hospital_name/assigned_employee) chỉ THÊM.
QUEUE_LIST_ITEM_KEYS = ("name", "delivery", "document_bundle", "status", "missing_chips", "assigned_to")
QUEUE_LIST_EXTRA_KEYS = ("ts", "hospital_name", "assigned_employee", "assigned_employee_name")
READY_STATUS = "Chờ phát hành"
DOC_DETAIL_FIELDS = ("name", "delivery", "hospital", "status", "missing_items", "hash_sha256")
LINE_KEYS = ("item", "lot", "qty", "requires_cocq", "co_attached", "cq_attached")


def _parse_chips(raw) -> list:
	"""Parse missing_chips JSON null-guard. Chuỗi rỗng / None / JSON hỏng → [] (KHÔNG throw).

	Dùng CHUNG cho summary count + list output để 2 nguồn nhất quán (Hyrum-safe).
	Chỉ trả list; giá trị không phải list (vd dict/số) → [] để count không lệch.
	"""
	if not raw:
		return []
	if isinstance(raw, list):
		return raw
	try:
		parsed = json.loads(raw)
	except (ValueError, TypeError):
		return []
	return parsed if isinstance(parsed, list) else []


def _chip_text(chips: list) -> str:
	"""Gộp các chip thành 1 chuỗi để dò 'CO'/'CQ' (chip dạng 'CO lot L-9930')."""
	return " ".join(str(c) for c in chips)


def _build_lines(delivery_name: str) -> tuple[list, list]:
	"""Dựng dòng chứng từ từ phiếu giao + đánh dấu CO/CQ. Trả (lines, missing_item_codes).

	requires_cocq lấy từ AntMed Item; co/cq attached = lô có co_cert/cq_cert (AntMed Lot).
	KHÔNG N+1: bulk-fetch distinct item/lot (≤2 query) → map ở Python (giống list_release_queue).
	Output-identical với loop get_value cũ: item/lot absent trong map → default 0 (= get_value None→0).
	"""
	dlv = frappe.get_doc(DELIVERY_DOCTYPE, delivery_name)

	# BULK 1: item distinct → requires_cocq (1 query, rỗng-safe — KHÔNG query `in []`).
	item_codes = list({it.item for it in dlv.items if it.item})
	requires_map: dict = {}
	if item_codes:
		for r in frappe.get_all(
			"AntMed Item",
			filters=[["name", "in", item_codes]],
			fields=["name", "requires_cocq"],
			limit_page_length=0,
		):
			requires_map[r["name"]] = int(r.get("requires_cocq") or 0)

	# BULK 2: lot distinct → (co_cert, cq_cert) (1 query, rỗng-safe).
	lot_codes = list({it.lot for it in dlv.items if it.lot})
	cert_map: dict = {}
	if lot_codes:
		for r in frappe.get_all(
			"AntMed Lot",
			filters=[["name", "in", lot_codes]],
			fields=["name", "co_cert", "cq_cert"],
			limit_page_length=0,
		):
			cert_map[r["name"]] = (r.get("co_cert"), r.get("cq_cert"))

	lines, missing = [], []
	for it in dlv.items:
		requires = requires_map.get(it.item, 0) if it.item else 0
		co = cq = 0
		if it.lot:
			cert = cert_map.get(it.lot) or (None, None)
			co = 1 if cert[0] else 0
			cq = 1 if cert[1] else 0
		lines.append(
			{
				"item": it.item,
				"lot": it.lot,
				"qty": it.requested_qty,
				"requires_cocq": requires,
				"co_attached": co,
				"cq_attached": cq,
			}
		)
		if requires and not (co and cq):
			missing.append(it.item)
	return lines, missing


def _status_for(missing: list) -> str:
	return "Thiếu chứng từ" if missing else "Chờ phát hành"


@frappe.whitelist(methods=["POST"])
def create_bundle(delivery: str) -> dict:
	"""Tạo bundle chứng từ + dòng + hàng chờ từ 1 phiếu giao (idempotent theo delivery)."""
	if not frappe.has_permission(DOCUMENT_DOCTYPE, "create"):
		frappe.throw(_("Bạn không có quyền tạo bundle chứng từ."), frappe.PermissionError)
	existing = frappe.db.get_value(DOCUMENT_DOCTYPE, {"delivery": delivery}, "name")
	if existing:
		return refresh_release_status(delivery)

	lines, missing = _build_lines(delivery)
	status = _status_for(missing)
	hospital = frappe.db.get_value(DELIVERY_DOCTYPE, delivery, "hospital")
	bundle = frappe.get_doc(
		{
			"doctype": DOCUMENT_DOCTYPE,
			"delivery": delivery,
			"hospital": hospital,
			"status": status,
			"missing_items": json.dumps(missing, ensure_ascii=False),
			"lines": lines,
		}
	)
	bundle.insert(ignore_permissions=True)
	if not frappe.db.exists(QUEUE_DOCTYPE, delivery):
		frappe.get_doc(
			{
				"doctype": QUEUE_DOCTYPE,
				"delivery": delivery,
				"document_bundle": bundle.name,
				"status": status,
				"missing_chips": json.dumps(missing, ensure_ascii=False),
			}
		).insert(ignore_permissions=True)
	return {"bundle": bundle.name, "status": status, "missing": missing}


@frappe.whitelist(methods=["POST"])
def refresh_release_status(delivery: str) -> dict:
	"""Tính lại CO/CQ thiếu cho bundle của phiếu giao + cập nhật bundle/queue status."""
	bundle_name = frappe.db.get_value(DOCUMENT_DOCTYPE, {"delivery": delivery}, "name")
	if not bundle_name:
		frappe.throw(_("Chưa có bundle chứng từ cho phiếu giao {0}.").format(delivery))
	lines, missing = _build_lines(delivery)
	status = _status_for(missing)
	bundle = frappe.get_doc(DOCUMENT_DOCTYPE, bundle_name)
	bundle.set("lines", lines)
	bundle.status = status
	bundle.missing_items = json.dumps(missing, ensure_ascii=False)
	bundle.save(ignore_permissions=True)
	if frappe.db.exists(QUEUE_DOCTYPE, delivery):
		frappe.db.set_value(
			QUEUE_DOCTYPE,
			delivery,
			{"status": status, "missing_chips": json.dumps(missing, ensure_ascii=False)},
		)
	return {"bundle": bundle_name, "status": status, "missing": missing}


@frappe.whitelist(methods=["GET"])
def list_release_queue(status: str | None = None, start: int = 0, page_length: int = 20) -> dict:
	"""Hàng chờ phát hành chứng từ (worklist E1). Trả RAW {data, total_count} — count==rows dưới DocPerm.

	Mỗi dòng = key cũ (backward-compat: name/delivery/document_bundle/status/missing_chips/assigned_to)
	+ key THÊM cho cột E1: ts, hospital_name, assigned_employee (NV) — resolve qua delivery.
	KHÔNG N+1: bulk-fetch delivery distinct (1 query) + hospital distinct (1 query) → map ở Python.
	"""
	conditions = []
	if status:
		conditions.append(["status", "=", status])
	start = max(0, int(start))
	page_length = max(0, int(page_length))
	# Fail-closed BR-13: user KHÔNG read-perm AntMed Document Release Queue → rỗng (count==rows==0), KHÔNG throw.
	try:
		rows = frappe.get_list(
			QUEUE_DOCTYPE,
			filters=conditions,
			fields=QUEUE_LIST_FIELDS,
			limit_start=start,
			limit_page_length=page_length or 0,
			order_by="modified desc",
		)
	except frappe.PermissionError:
		return {"data": [], "total_count": 0}

	# BULK 1: phiếu giao distinct → hospital + assigned_employee (KHÔNG get_value trong loop).
	delivery_names = list({r.get("delivery") for r in rows if r.get("delivery")})
	dlv_map: dict = {}
	hospital_names: set = set()
	employee_users: set = set()
	if delivery_names:
		for d in frappe.get_all(
			DELIVERY_DOCTYPE,
			filters=[["name", "in", delivery_names]],
			fields=["name", "hospital", "assigned_employee"],
			limit_page_length=0,
			ignore_permissions=True,
		):
			dlv_map[d["name"]] = d
			if d.get("hospital"):
				hospital_names.add(d["hospital"])
			if d.get("assigned_employee"):
				employee_users.add(d["assigned_employee"])

	# BULK 2: bệnh viện distinct → hospital_name (1 query map).
	hosp_name_map: dict = {}
	if hospital_names:
		for h in frappe.get_all(
			"AntMed Hospital",
			filters=[["name", "in", list(hospital_names)]],
			fields=["name", "hospital_name"],
			limit_page_length=0,
			ignore_permissions=True,
		):
			hosp_name_map[h["name"]] = h.get("hospital_name")

	# BULK 3: NV (User) distinct → full_name (KHÔNG leak email thô ra UI — GATE-2). 1 query map.
	emp_name_map: dict = {}
	if employee_users:
		for u in frappe.get_all(
			"User",
			filters=[["name", "in", list(employee_users)]],
			fields=["name", "full_name"],
			limit_page_length=0,
			ignore_permissions=True,
		):
			emp_name_map[u["name"]] = u.get("full_name")

	data = []
	for r in rows:
		row = {k: r.get(k) for k in QUEUE_LIST_ITEM_KEYS}
		dlv = dlv_map.get(r.get("delivery")) or {}
		row["ts"] = r.get("ts")
		row["assigned_employee"] = dlv.get("assigned_employee")
		# Tên NV đọc được (full_name) — FE hiển thị tên này, KHÔNG email/ID (assigned_employee giữ raw cho backward-compat).
		row["assigned_employee_name"] = emp_name_map.get(dlv.get("assigned_employee"))
		row["hospital_name"] = hosp_name_map.get(dlv.get("hospital")) or dlv.get("hospital")
		data.append(row)

	total_count = len(frappe.get_list(QUEUE_DOCTYPE, filters=conditions, pluck="name", limit_page_length=0))
	return {"data": data, "total_count": total_count}


@frappe.whitelist(methods=["GET"])
def release_queue_summary() -> dict:
	"""KPI rollup màn 'Hàng chờ phát hành chứng từ' (E1). Trả RAW dict khoá CỐ ĐỊNH (Hyrum-safe):

	    {missing_co, missing_cq, ready_to_release}

	- missing_co       = số hàng chờ có 'CO' trong missing_chips.
	- missing_cq       = số hàng chờ có 'CQ' trong missing_chips.
	- ready_to_release = số hàng chờ status='Chờ phát hành' AND missing_chips rỗng (đủ CO+CQ).

	Đếm dưới DocPerm (BR-13) — count khớp số dòng list_release_queue user được phép thấy.
	Fail-closed: user KHÔNG read-perm AntMed Document Release Queue → {0,0,0} (KHÔNG throw/leak/500).
	KHÔNG N+1 / KHÔNG raw SQL: 1 get_list lấy {status, missing_chips} rồi gộp ở Python.
	"""
	empty = {"missing_co": 0, "missing_cq": 0, "ready_to_release": 0}
	if not frappe.has_permission(QUEUE_DOCTYPE, "read"):
		return empty
	try:
		rows = frappe.get_list(
			QUEUE_DOCTYPE,
			fields=["status", "missing_chips"],
			limit_page_length=0,
		)
	except frappe.PermissionError:
		return empty

	missing_co = missing_cq = ready = 0
	for r in rows:
		chips = _parse_chips(r.get("missing_chips"))
		text = _chip_text(chips)
		if "CO" in text:
			missing_co += 1
		if "CQ" in text:
			missing_cq += 1
		if r.get("status") == READY_STATUS and not chips:
			ready += 1
	return {"missing_co": missing_co, "missing_cq": missing_cq, "ready_to_release": ready}


@frappe.whitelist(methods=["GET"])
def get_bundle(name: str) -> dict:
	"""Chi tiết bundle + lines[]. throw PermissionError nếu không read."""
	if not frappe.has_permission(DOCUMENT_DOCTYPE, "read", doc=name):
		frappe.throw(_("Bạn không có quyền xem bundle chứng từ này."), frappe.PermissionError)
	doc = frappe.get_doc(DOCUMENT_DOCTYPE, name).as_dict()
	result = {k: doc.get(k) for k in DOC_DETAIL_FIELDS}
	result["lines"] = [{k: ln.get(k) for k in LINE_KEYS} for ln in (doc.get("lines") or [])]
	return result


@frappe.whitelist(methods=["POST"])
def attach_cocq(
	lot: str, cert_type: str, cert_no: str, item: str | None = None, file_url: str | None = None
) -> dict:
	"""Gắn 1 chứng từ CO hoặc CQ vào lô (tạo AntMed Certificate + set lô.co_cert/cq_cert).

	(hash_sha256 file + audit BR-10 wire ở M14.)
	"""
	if cert_type not in ("CO", "CQ"):
		frappe.throw(_("cert_type phải là 'CO' hoặc 'CQ'."))
	if not frappe.has_permission(CERTIFICATE_DOCTYPE, "create"):
		frappe.throw(_("Bạn không có quyền gắn chứng từ."), frappe.PermissionError)
	cert = frappe.get_doc(
		{
			"doctype": CERTIFICATE_DOCTYPE,
			"cert_no": cert_no,
			"cert_type": cert_type,
			"lot": lot,
			"item": item,
			"file_url": file_url,
		}
	)
	cert.insert(ignore_permissions=True)
	field = "co_cert" if cert_type == "CO" else "cq_cert"
	frappe.db.set_value(LOT_DOCTYPE, lot, field, cert.name)
	return {"certificate": cert.name, "lot": lot, "cert_type": cert_type}


@frappe.whitelist(methods=["GET"])
def list_cocq_store(
	cert_type: str | None = None, search: str | None = None, start: int = 0, page_length: int = 20
) -> dict:
	"""Kho CO/CQ (danh sách chứng từ). Trả RAW {data, total_count} — count==rows dưới DocPerm."""
	conditions = []
	if cert_type:
		conditions.append(["cert_type", "=", cert_type])
	if search:
		conditions.append(["cert_no", "like", f"%{search}%"])
	start = max(0, int(start))
	page_length = max(0, int(page_length))
	rows = frappe.get_list(
		CERTIFICATE_DOCTYPE,
		filters=conditions,
		fields=CERT_LIST_FIELDS,
		limit_start=start,
		limit_page_length=page_length or 0,
		order_by="modified desc",
	)
	data = [{k: r.get(k) for k in CERT_LIST_ITEM_KEYS} for r in rows]
	total_count = len(
		frappe.get_list(CERTIFICATE_DOCTYPE, filters=conditions, pluck="name", limit_page_length=0)
	)
	return {"data": data, "total_count": total_count}


def assert_cocq_complete(delivery: str) -> None:
	"""BR-03 (chặn cứng): throw nếu còn VT requires_cocq thiếu CO/CQ. Gọi trước phát hành (M06-S3)."""
	_lines, missing = _build_lines(delivery)
	if missing:
		frappe.throw(_("BR-03: Còn vật tư thiếu CO/CQ, không thể phát hành: {0}.").format(", ".join(missing)))


@frappe.whitelist(methods=["GET"])
def check_release(delivery: str) -> dict:
	"""Kiểm tra điều kiện phát hành (BR-03, KHÔNG throw): {can_release, missing, status}."""
	_lines, missing = _build_lines(delivery)
	return {"can_release": not missing, "missing": missing, "status": _status_for(missing)}


@frappe.whitelist(methods=["POST"])
def issue_einvoice(delivery: str) -> dict:
	"""Phát hành HĐĐT cho 1 phiếu giao (STUB dev-mode — KHÔNG gọi provider thật).

	Gate BR-03 (assert_cocq_complete) TRƯỚC khi phát hành. Idempotent: 1 HĐĐT/phiếu giao.
	Stub: tạo + submit (BR-04 immutable) với mã CQT giả 'STUB-CQT-…'. Provider thật = M13/ROADMAP.
	"""
	if not frappe.has_permission(EINVOICE_DOCTYPE, "create"):
		frappe.throw(_("Bạn không có quyền phát hành hóa đơn điện tử."), frappe.PermissionError)
	existing = frappe.db.get_value(EINVOICE_DOCTYPE, {"delivery": delivery}, "name")
	if existing:
		return {
			"einvoice": existing,
			"status": frappe.db.get_value(EINVOICE_DOCTYPE, existing, "status"),
			"stub": True,
		}

	assert_cocq_complete(delivery)  # BR-03 hard gate

	from frappe.utils import now_datetime

	bundle = frappe.db.get_value(DOCUMENT_DOCTYPE, {"delivery": delivery}, "name")
	provider = frappe.db.get_single_value(PROVIDER_DOCTYPE, "default_provider") or "Viettel"
	ev = frappe.get_doc(
		{
			"doctype": EINVOICE_DOCTYPE,
			"delivery": delivery,
			"document_bundle": bundle,
			"provider": provider,
			"status": "Chờ ký",
		}
	)
	ev.insert(ignore_permissions=True)
	# STUB ký + phát hành (dev-mode): KHÔNG network thật, mã CQT giả.
	ev.status = "Đã phát hành"
	ev.ma_cqt = f"STUB-CQT-{ev.name}"
	ev.signed_at = now_datetime()
	ev.submit()  # BR-04: bất biến sau submit
	if bundle:
		frappe.db.set_value(DOCUMENT_DOCTYPE, bundle, "status", "Đã phát hành")
		if frappe.db.exists(QUEUE_DOCTYPE, delivery):
			frappe.db.set_value(QUEUE_DOCTYPE, delivery, "status", "Đã phát hành")
	return {"einvoice": ev.name, "status": ev.status, "ma_cqt": ev.ma_cqt, "stub": True}


@frappe.whitelist(methods=["GET"])
def list_einvoices(status: str | None = None, start: int = 0, page_length: int = 20) -> dict:
	"""Danh sách HĐĐT. Trả RAW {data, total_count} — count==rows dưới DocPerm."""
	conditions = []
	if status:
		conditions.append(["status", "=", status])
	start = max(0, int(start))
	page_length = max(0, int(page_length))
	rows = frappe.get_list(
		EINVOICE_DOCTYPE,
		filters=conditions,
		fields=EINVOICE_LIST_FIELDS,
		limit_start=start,
		limit_page_length=page_length or 0,
		order_by="modified desc",
	)
	data = [{k: r.get(k) for k in EINVOICE_LIST_ITEM_KEYS} for r in rows]
	total_count = len(
		frappe.get_list(EINVOICE_DOCTYPE, filters=conditions, pluck="name", limit_page_length=0)
	)
	return {"data": data, "total_count": total_count}


@frappe.whitelist(methods=["GET"])
def get_provider_settings() -> dict:
	"""Cấu hình HĐĐT — CHỈ trả 'configured' bool/endpoint, TUYỆT ĐỐI KHÔNG trả api_key (BR-INT-01)."""
	if not frappe.has_permission(PROVIDER_DOCTYPE, "read"):
		frappe.throw(_("Bạn không có quyền xem cấu hình HĐĐT."), frappe.PermissionError)
	s = frappe.get_doc(PROVIDER_DOCTYPE)
	out = {"default_provider": s.default_provider}
	for prov in ("viettel", "misa", "vnpt"):
		out[f"{prov}_endpoint"] = s.get(f"{prov}_endpoint")
		# CHỈ bool — api_key (Password) KHÔNG bao giờ đưa vào response (BR-INT-01).
		out[f"{prov}_configured"] = bool(s.get_password(f"{prov}_api_key", raise_exception=False))
	return out


@frappe.whitelist(methods=["POST"])
def confirm_handover(
	delivery: str, hospital_contact: str | None = None, signature_file: str | None = None
) -> dict:
	"""BV ký nhận chứng từ → tạo + submit AntMed Handover Confirmation (hash chống sửa), bundle 'BV đã ký nhận'.

	Idempotent: 1 xác nhận / phiếu giao. (Audit hash-chain đầy đủ ở M14.)
	"""
	if not frappe.has_permission(HANDOVER_DOCTYPE, "create"):
		frappe.throw(_("Bạn không có quyền xác nhận ký nhận."), frappe.PermissionError)
	existing = frappe.db.get_value(HANDOVER_DOCTYPE, {"delivery": delivery}, "name")
	if existing:
		return {
			"handover": existing,
			"status": "BV đã ký nhận",
			"hash": frappe.db.get_value(HANDOVER_DOCTYPE, existing, "hash_sha256"),
		}

	import hashlib

	from frappe.utils import now_datetime

	bundle = frappe.db.get_value(DOCUMENT_DOCTYPE, {"delivery": delivery}, "name")
	signed_at = now_datetime()
	hc = frappe.get_doc(
		{
			"doctype": HANDOVER_DOCTYPE,
			"delivery": delivery,
			"document_bundle": bundle,
			"hospital_contact": hospital_contact,
			"signature_file": signature_file,
			"signed_at": signed_at,
		}
	)
	hc.hash_sha256 = hashlib.sha256(f"{delivery}|{hospital_contact}|{signed_at}".encode()).hexdigest()
	hc.insert(ignore_permissions=True)
	hc.submit()
	if bundle:
		frappe.db.set_value(DOCUMENT_DOCTYPE, bundle, "status", "BV đã ký nhận")
		if frappe.db.exists(QUEUE_DOCTYPE, delivery):
			frappe.db.set_value(QUEUE_DOCTYPE, delivery, "status", "BV đã ký nhận")
	return {"handover": hc.name, "status": "BV đã ký nhận", "hash": hc.hash_sha256}


@frappe.whitelist(methods=["GET"])
def list_handover_review(start: int = 0, page_length: int = 20) -> dict:
	"""Màn đối soát ký nhận: bundle đã phát hành/đã gửi/đã ký. Trả RAW {data, total_count} count==rows."""
	start = max(0, int(start))
	page_length = max(0, int(page_length))
	conditions = [["status", "in", list(HANDOVER_REVIEW_STATUSES)]]
	rows = frappe.get_list(
		DOCUMENT_DOCTYPE,
		filters=conditions,
		fields=HANDOVER_LIST_FIELDS,
		limit_start=start,
		limit_page_length=page_length or 0,
		order_by=f"`tab{DOCUMENT_DOCTYPE}`.modified desc",
	)
	data = [{k: r.get(k) for k in HANDOVER_LIST_ITEM_KEYS} for r in rows]
	total_count = len(
		frappe.get_list(DOCUMENT_DOCTYPE, filters=conditions, pluck="name", limit_page_length=0)
	)
	return {"data": data, "total_count": total_count}
