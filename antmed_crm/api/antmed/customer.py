# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M01 R2 Customer 360° — endpoint Bệnh viện + Bác sỹ.

Đường gọi: antmed_crm.api.antmed.customer.<fn>  (xem m01_customer360.md §API).
Mọi hàm @frappe.whitelist(methods=["GET"]), type-annotated (require_type_annotated_api_methods),
trả RAW dict (KHÔNG envelope _ok/_err). Lỗi permission = frappe.throw(..., frappe.PermissionError).

Invariant BR-13 (count == rows): khi không phân trang, len(data) == total_count.
total_count đếm DƯỚI permission của user (frappe.get_list tôn trọng DocPerm) — KHÔNG dùng
frappe.db.count (bỏ qua permission). R2 chưa wiring permission_query_conditions (ADR-M01-05),
nhưng cách đếm này giữ contract count==rows khi M14/R3 thêm data-scope.
"""

import frappe
from frappe import _

from antmed_crm.api.antmed._filters import coerce_filters

HOSPITAL_DOCTYPE = "AntMed Hospital"
DOCTOR_DOCTYPE = "AntMed Doctor"
STOCK_ENTRY_DOCTYPE = "AntMed Stock Entry"
CONTRACT_DOCTYPE = "AntMed Contract"
QUOTA_ITEM_DOCTYPE = "AntMed Quota Item"

# M07-1 Portal "Thông báo gần đây" — số dòng tối đa + shape item ổn định (Hyrum).
PORTAL_NOTIF_LIMIT = 10
PORTAL_NOTIF_KEYS = ("kind", "ts", "title", "ref")

# Field item trả về cho list endpoint (hợp đồng với FE — Hyrum: đổi = breaking binding).
HOSPITAL_LIST_FIELDS = ["name", "hospital_name", "rank", "contract_status", "tax_code"]
DOCTOR_LIST_FIELDS = ["name", "full_name", "specialty", "hospital", "phone"]
# Field bác sỹ con trong "mặt 360" của bệnh viện (đúng acceptance get_hospital).
HOSPITAL_DOCTOR_FIELDS = ["name", "full_name", "specialty", "phone"]

# Select options khớp doctype AntMed Hospital (cho form tạo bệnh viện).
HOSPITAL_RANK_OPTIONS = ("Đặc biệt", "I", "II", "III", "Khác")
HOSPITAL_CONTRACT_STATUS_OPTIONS = ("Đã ký", "Tiềm năng", "Hết hạn")


@frappe.whitelist(methods=["POST"])
def create_hospital(
	hospital_name: str,
	hospital_code: str,
	rank: str | None = None,
	contract_status: str | None = None,
	tax_code: str | None = None,
	address: str | None = None,
) -> dict:
	"""Tạo bệnh viện (AntMed Hospital). hospital_code + hospital_name bắt buộc; còn lại optional.

	Gate quyền create theo DocPerm (System Manager / Quản lý / NV kinh doanh).
	"""
	if not frappe.has_permission(HOSPITAL_DOCTYPE, "create"):
		frappe.throw(_("Bạn không có quyền tạo bệnh viện."), frappe.PermissionError)
	if not (hospital_name or "").strip():
		frappe.throw(_("Tên bệnh viện bắt buộc."))
	if not (hospital_code or "").strip():
		frappe.throw(_("Mã bệnh viện bắt buộc."))
	doc = frappe.get_doc(
		{
			"doctype": HOSPITAL_DOCTYPE,
			"hospital_code": hospital_code.strip(),
			"hospital_name": hospital_name.strip(),
			"rank": rank or None,
			"contract_status": contract_status or None,
			"tax_code": tax_code,
			"address": address,
		}
	)
	doc.insert()
	return {"name": doc.name, "hospital_name": doc.hospital_name}


def _coerce_filters(filters: dict | str | None) -> list:
	"""Chuẩn hoá filters về list điều kiện. FE/GET truyền dict hoặc JSON-string."""
	return coerce_filters(filters)


@frappe.whitelist(methods=["GET"])
def list_hospitals(
	filters: dict | str | None = None,
	start: int = 0,
	page_length: int = 20,
	search: str | None = None,
) -> dict:
	"""List bệnh viện. Trả RAW dict {data: list[dict], total_count: int}.

	- search: lọc theo hospital_name (LIKE %search%).
	- page_length=0 → không phân trang (lấy hết khớp filter); khi đó len(data)==total_count.
	- total_count đếm DƯỚI permission user (get_list) → giữ invariant count==rows kể cả khi
	  R3 thêm permission_query_conditions.
	"""
	conditions = _coerce_filters(filters)
	if search:
		conditions.append(["hospital_name", "like", f"%{search}%"])

	start = max(0, int(start))
	page_length = max(0, int(page_length))

	data = frappe.get_list(
		HOSPITAL_DOCTYPE,
		filters=conditions,
		fields=HOSPITAL_LIST_FIELDS,
		limit_start=start,
		limit_page_length=page_length or 0,  # 0 = không giới hạn
		order_by="modified desc",
	)
	# total_count = tổng khớp filter, đếm dưới permission (pluck name, không limit).
	total_count = len(
		frappe.get_list(
			HOSPITAL_DOCTYPE,
			filters=conditions,
			pluck="name",
			limit_page_length=0,
		)
	)
	return {"data": data, "total_count": total_count}


@frappe.whitelist(methods=["GET"])
def get_hospital(name: str) -> dict:
	"""Mặt 360 của bệnh viện: field BV + danh sách bác sỹ thuộc BV (children).

	throw PermissionError nếu user không read được hồ sơ này.
	"""
	if not frappe.has_permission(HOSPITAL_DOCTYPE, "read", doc=name):
		frappe.throw(_("Bạn không có quyền xem hồ sơ bệnh viện này."), frappe.PermissionError)

	doc = frappe.get_doc(HOSPITAL_DOCTYPE, name).as_dict()
	result = {
		"name": doc.get("name"),
		"hospital_code": doc.get("hospital_code"),
		"hospital_name": doc.get("hospital_name"),
		"rank": doc.get("rank"),
		"tax_code": doc.get("tax_code"),
		"address": doc.get("address"),
		"contract_status": doc.get("contract_status"),
	}
	result["doctors"] = frappe.get_list(
		DOCTOR_DOCTYPE,
		filters={"hospital": name},
		fields=HOSPITAL_DOCTOR_FIELDS,
		order_by="full_name asc",
		limit_page_length=0,
	)
	return result


@frappe.whitelist(methods=["GET"])
def list_doctors(
	filters: dict | str | None = None,
	hospital: str | None = None,
	start: int = 0,
	page_length: int = 20,
) -> dict:
	"""List bác sỹ. Trả RAW dict {data, total_count}. hospital = lọc nhanh theo 1 BV."""
	conditions = _coerce_filters(filters)
	if hospital:
		conditions.append(["hospital", "=", hospital])

	start = max(0, int(start))
	page_length = max(0, int(page_length))

	data = frappe.get_list(
		DOCTOR_DOCTYPE,
		filters=conditions,
		fields=DOCTOR_LIST_FIELDS,
		limit_start=start,
		limit_page_length=page_length or 0,
		order_by="modified desc",
	)
	total_count = len(
		frappe.get_list(
			DOCTOR_DOCTYPE,
			filters=conditions,
			pluck="name",
			limit_page_length=0,
		)
	)
	return {"data": data, "total_count": total_count}


@frappe.whitelist(methods=["GET"])
def get_doctor(name: str) -> dict:
	"""Profile bác sỹ + hospital_name resolve qua Link (link ngược về BV).

	throw PermissionError nếu user không read được.
	"""
	if not frappe.has_permission(DOCTOR_DOCTYPE, "read", doc=name):
		frappe.throw(_("Bạn không có quyền xem hồ sơ bác sỹ này."), frappe.PermissionError)

	doc = frappe.get_doc(DOCTOR_DOCTYPE, name).as_dict()
	result = {
		"name": doc.get("name"),
		"doctor_code": doc.get("doctor_code"),
		"full_name": doc.get("full_name"),
		"hospital": doc.get("hospital"),
		"hospital_name": None,
		"specialty": doc.get("specialty"),
		"birthday": doc.get("birthday"),
		"phone": doc.get("phone"),
		"email": doc.get("email"),
		"zalo": doc.get("zalo"),
		"notes": doc.get("notes"),
	}
	# LL-BE-2 + LL-BE-5: enrich *_name, null-guard FK orphan.
	if doc.get("hospital"):
		result["hospital_name"] = frappe.db.get_value(
			HOSPITAL_DOCTYPE, doc.get("hospital"), "hospital_name"
		)
	return result


# ---------------------------------------------------------------------------
# M07-1 — Portal Bệnh viện "📰 Thông báo gần đây" (rollup REAL events).
# ---------------------------------------------------------------------------
def _empty_portal_notifications(hospital: str) -> dict:
	"""Shape fail-closed / rỗng: data == [] nhưng vẫn đủ key + hospital_name resolve được."""
	return {
		"data": [],
		"hospital": hospital,
		"hospital_name": frappe.db.get_value(HOSPITAL_DOCTYPE, hospital, "hospital_name"),
	}


@frappe.whitelist(methods=["GET"])
def portal_notifications(hospital: str) -> dict:
	"""Timeline "Thông báo gần đây" cho Portal Bệnh viện (mockup G1).

	Trả RAW dict {data: list[dict], hospital, hospital_name}. Mỗi item shape ỔN ĐỊNH
	(Hyrum — PORTAL_NOTIF_KEYS): kind ('delivery'|'quota') · ts (datetime) · title (str VI)
	· ref (str|None: số phiếu / mã item).

	Nguồn THẬT:
	  - delivery = AntMed Stock Entry entry_type='Xuất cho NV' AND hospital=<bv>
	    (get_list dưới DocPerm; PermissionError → []  — fail-closed, KHÔNG raise 500).
	  - quota    = quota item của HĐ thuộc BV có used_pct ở band cảnh báo (>=70%,
	    tái dùng _quota_threshold của contract.py). Batch get_all theo parent IN scope
	    (KHÔNG N+1).

	Merge 2 nguồn → sort ts giảm dần → cắt top PORTAL_NOTIF_LIMIT.

	Data-scoping: chỉ dùng get_list/get_all (tôn trọng DocPerm) — portal user chỉ thấy
	BV mình (filter hospital truyền vào + DocPerm trên Stock Entry/Contract). KHÔNG raw SQL.
	"""
	# Tái dùng ngưỡng cảnh báo quota (lazy import — tránh circular import lúc bench start).
	from antmed_crm.api.antmed.contract import _quota_threshold

	events: list[dict] = []

	# --- delivery events (Stock Entry 'Xuất cho NV' của BV) ---------------
	try:
		deliveries = frappe.get_list(
			STOCK_ENTRY_DOCTYPE,
			filters={"entry_type": "Xuất cho NV", "hospital": hospital},
			fields=["name", "naming_series", "posting_datetime"],
			order_by="posting_datetime desc",
			limit_page_length=PORTAL_NOTIF_LIMIT,
		)
	except frappe.PermissionError:
		return _empty_portal_notifications(hospital)
	for se in deliveries:
		events.append(
			{
				"kind": "delivery",
				"ts": se.get("posting_datetime"),
				"title": _("Phiếu giao {0} đã xuất cho NV").format(se.get("name")),
				"ref": se.get("name"),
			}
		)

	# --- quota events (quota item HĐ của BV chạm band cảnh báo >=70%) -----
	try:
		contracts = frappe.get_list(
			CONTRACT_DOCTYPE,
			filters={"hospital": hospital},
			fields=["name", "modified"],
			limit_page_length=0,
		)
	except frappe.PermissionError:
		contracts = []
	contract_mtime = {c["name"]: c.get("modified") for c in contracts}
	names = list(contract_mtime)
	if names:
		# 1 get_all duy nhất theo parent IN scope (KHÔNG N+1).
		for it in frappe.get_all(
			QUOTA_ITEM_DOCTYPE,
			filters={
				"parenttype": CONTRACT_DOCTYPE,
				"parentfield": "items",
				"parent": ("in", names),
			},
			fields=["parent", "item", "item_name", "quota_qty", "used_qty"],
		):
			quota = it.get("quota_qty") or 0
			if not quota:
				continue
			used_pct = round(100 * (it.get("used_qty") or 0) / quota, 2)
			if _quota_threshold(used_pct) is None:
				continue
			events.append(
				{
					"kind": "quota",
					"ts": contract_mtime.get(it["parent"]),
					"title": _("Quota {0} còn {1}%").format(
						it.get("item_name"), round(100 - used_pct)
					),
					"ref": it.get("item"),
				}
			)

	# Merge → sort ts giảm dần (None xuống cuối) → cắt top LIMIT.
	events.sort(key=lambda e: (e["ts"] is not None, e["ts"]), reverse=True)
	return {
		"data": events[:PORTAL_NOTIF_LIMIT],
		"hospital": hospital,
		"hospital_name": frappe.db.get_value(HOSPITAL_DOCTYPE, hospital, "hospital_name"),
	}


# ---------------------------------------------------------------------------
# M07-2 — Portal Bệnh viện "📋 Danh mục vật tư trúng thầu" (mockup G1, id=bv).
# ---------------------------------------------------------------------------
# Ngưỡng chip quota theo % CÒN LẠI (remaining_pct) — BR data-scope portal BV.
# FE đọc thẳng quota_chip (KHÔNG tự tính lại ngưỡng).
TENDER_CHIP_WARN_PCT = 10  # >0 và ≤10% → 'warn' (sắp hết)


def _tender_quota_chip(remaining_pct: float) -> str:
	"""Phân tầng chip quota theo % CÒN LẠI: ok (>10) / warn (>0 và ≤10) / danger (≤0 = hết)."""
	if remaining_pct <= 0:
		return "danger"
	if remaining_pct <= TENDER_CHIP_WARN_PCT:
		return "warn"
	return "ok"


@frappe.whitelist(methods=["GET"])
def tender_catalog(hospital: str) -> dict:
	"""Danh mục vật tư trúng thầu của 1 BV (card Portal BV, mockup G1 "Form gọi vật tư").

	Trả RAW dict ỔN ĐỊNH (Hyrum):
	  { hospital, hospital_name, contract, items:[{ item, item_name, uom,
	    remaining_qty, quota_qty, used_qty, remaining_pct, quota_chip }] }.

	- items = TẤT CẢ AntMed Quota Item của HĐ status ∈ ACTIVE_CONTRACT_STATUSES
	  ('Hiệu lực','Sắp hết hạn' — SSoT contract_hooks) của BV; gộp nhiều HĐ active nếu có.
	  HĐ Nháp/Hết hạn/Đã huỷ KHÔNG tính. Batch get_all theo parent IN scope (KHÔNG N+1).
	- GỘP THEO SKU (item) cross-contract: trùng SKU ở nhiều HĐ active → 1 dòng, cộng
	  quota_qty/used_qty rồi tính LẠI remaining_pct/quota_chip trên tổng (KHÔNG nhân đôi).
	- remaining_qty = quota_qty - used_qty; remaining_pct = round(100*remaining_qty/quota_qty, 1)
	  (quota_qty==0 → 0.0, KHÔNG ZeroDivision). quota_chip phân tầng THẬT từ remaining_pct
	  (FE chỉ map chip → theme/nhãn, KHÔNG tính lại ngưỡng).
	- KHÔNG có HĐ active → { contract: None, items: [] } (KHÔNG throw); hospital_name resolve.
	- KHÔNG trả unit_price (data-scope portal BV — BR; chống lộ giá đơn vị).
	- READ-only: chỉ get_list/get_all (tôn trọng DocPerm) — KHÔNG raw SQL, KHÔNG mutation.

	Data-scoping: portal user chỉ thấy BV mình (filter hospital + DocPerm trên Contract).
	BR-13 fail-closed: user thiếu read-perm Contract → contract=None, items=[] (KHÔNG raise 500).
	"""
	from antmed_crm.antmed.contract_hooks import ACTIVE_CONTRACT_STATUSES

	hospital_name = frappe.db.get_value(HOSPITAL_DOCTYPE, hospital, "hospital_name")

	# HĐ active của BV (đọc DƯỚI DocPerm). Fail-closed: noperm → rỗng.
	try:
		contracts = frappe.get_list(
			CONTRACT_DOCTYPE,
			filters={
				"hospital": hospital,
				"status": ("in", ACTIVE_CONTRACT_STATUSES),
			},
			fields=["name"],
			order_by="modified desc",
			limit_page_length=0,
		)
	except frappe.PermissionError:
		contracts = []

	names = [c["name"] for c in contracts]
	if not names:
		return {
			"hospital": hospital,
			"hospital_name": hospital_name,
			"contract": None,
			"items": [],
		}

	# 1 get_all duy nhất theo parent IN scope (KHÔNG N+1).
	rows = frappe.get_all(
		QUOTA_ITEM_DOCTYPE,
		filters={
			"parenttype": CONTRACT_DOCTYPE,
			"parentfield": "items",
			"parent": ("in", names),
		},
		fields=["item", "item_name", "uom", "quota_qty", "used_qty"],
	)

	# GỘP THEO SKU cross-contract (trùng item ở nhiều HĐ active → cộng quota/used). Giữ
	# thứ tự gặp đầu tiên (order_by modified desc trên HĐ + thứ tự child) cho output ổn định.
	agg: dict = {}
	order: list = []
	for r in rows:
		sku = r.get("item")
		if sku not in agg:
			order.append(sku)
			agg[sku] = {
				"item": sku,
				"item_name": r.get("item_name"),
				"uom": r.get("uom"),
				"quota_qty": 0.0,
				"used_qty": 0.0,
			}
		agg[sku]["quota_qty"] += r.get("quota_qty") or 0
		agg[sku]["used_qty"] += r.get("used_qty") or 0

	items = []
	for sku in order:
		a = agg[sku]
		quota = a["quota_qty"]
		used = a["used_qty"]
		remaining_qty = quota - used
		# remaining_pct THẬT từ TỔNG quota/used (null-guard quota==0 → 0.0, KHÔNG ZeroDivision).
		remaining_pct = round(100 * remaining_qty / quota, 1) if quota else 0.0
		items.append(
			{
				"item": a["item"],
				"item_name": a["item_name"],
				"uom": a["uom"],
				"remaining_qty": remaining_qty,
				"quota_qty": quota,
				"used_qty": used,
				"remaining_pct": remaining_pct,
				"quota_chip": _tender_quota_chip(remaining_pct),
			}
		)

	return {
		"hospital": hospital,
		"hospital_name": hospital_name,
		# contract = HĐ active đầu tiên (mới nhất theo modified) — nhãn tham chiếu trên card.
		"contract": names[0],
		"items": items,
	}


# ── M09 — Portal BV "Gọi vật tư cho ca mổ" (mockup G1) ──────────────────────────
MATERIAL_REQUEST_DOCTYPE = "AntMed Material Request"
ITEM_DOCTYPE = "AntMed Item"
DELIVERY_DOCTYPE = "AntMed Delivery"
DOCUMENT_DOCTYPE = "AntMed Document"
PORTAL_HISTORY_STATES = ("Đã gán NV", "Đang giao", "Đã bàn giao", "Đã đóng")
MR_LIST_FIELDS = ["name", "hospital", "doctor", "status", "urgency", "surgery_datetime", "needs_approval", "creation"]
MR_LIST_ITEM_KEYS = ("name", "hospital", "doctor", "status", "urgency", "surgery_datetime", "needs_approval", "creation")
MR_DETAIL_FIELDS = ("name", "hospital", "doctor", "status", "urgency", "surgery_datetime", "surgery_room", "assigned_employee", "needs_approval", "delivery_ref", "notes", "docstatus")
MR_ITEM_KEYS = ("item", "item_name", "requested_qty", "in_quota", "note")


def _assert_hospital_access(hospital: str) -> None:
	"""Chống IDOR cross-hospital (BR-13): nếu user bị giới hạn BV (User Permission), `hospital`
	PHẢI thuộc tập cho phép. User không bị giới hạn (admin/NV phủ toàn bộ) → cho qua.
	"""
	perms = frappe.defaults.get_user_permissions() or {}
	allowed = [p.get("doc") for p in perms.get(HOSPITAL_DOCTYPE, []) if p.get("doc")]
	if allowed and hospital not in allowed:
		frappe.throw(_("Bạn không có quyền thao tác cho bệnh viện này."), frappe.PermissionError)


@frappe.whitelist(methods=["POST"])
def create_material_request(
	hospital: str,
	items,
	doctor: str | None = None,
	surgery_datetime: str | None = None,
	surgery_room: str | None = None,
	urgency: str = "Bình thường",
	notes: str | None = None,
) -> dict:
	"""BV gửi yêu cầu vật tư cho ca mổ (mockup G1). Mỗi dòng đánh dấu in_quota (BR-01: trong
	danh mục trúng thầu). Item ngoài thầu → needs_approval=1 (NV duyệt). Trả {name, status, needs_approval}.
	"""
	if not frappe.has_permission(MATERIAL_REQUEST_DOCTYPE, "create"):
		frappe.throw(_("Bạn không có quyền gửi yêu cầu vật tư."), frappe.PermissionError)
	# Chống IDOR: chỉ cho gửi yêu cầu cho BV trong phạm vi của user (User Permission, BR-13).
	_assert_hospital_access(hospital)
	if doctor and frappe.db.get_value(DOCTOR_DOCTYPE, doctor, "hospital") not in (None, hospital):
		frappe.throw(_("Bác sỹ không thuộc bệnh viện này."))
	rows = frappe.parse_json(items) if isinstance(items, str) else (items or [])
	if not rows:
		frappe.throw(_("Yêu cầu phải có ít nhất 1 vật tư."))

	from antmed_crm.antmed import contract_hooks

	needs_approval = False
	mr_items = []
	for r in rows:
		item = r.get("item")
		in_quota = bool(contract_hooks.find_active_contract_with_item(hospital, item))
		if not in_quota:
			needs_approval = True
		mr_items.append(
			{
				"item": item,
				"item_name": frappe.db.get_value(ITEM_DOCTYPE, item, "item_name"),
				"requested_qty": r.get("requested_qty") or 0,
				"in_quota": 1 if in_quota else 0,
				"note": r.get("note"),
			}
		)
	doc = frappe.get_doc(
		{
			"doctype": MATERIAL_REQUEST_DOCTYPE,
			"hospital": hospital,
			"doctor": doctor,
			"surgery_datetime": surgery_datetime,
			"surgery_room": surgery_room,
			"urgency": urgency,
			"status": "Mới",
			"needs_approval": 1 if needs_approval else 0,
			"notes": notes,
			"items": mr_items,
		}
	)
	doc.insert(ignore_permissions=True)
	doc.submit()
	return {"name": doc.name, "status": doc.status, "needs_approval": bool(needs_approval)}


@frappe.whitelist(methods=["GET"])
def list_material_requests(hospital: str | None = None, status: str | None = None, start: int = 0, page_length: int = 20) -> dict:
	"""Danh sách yêu cầu vật tư của BV (Portal). Trả RAW {data, total_count} — count==rows dưới DocPerm."""
	conditions = []
	if hospital:
		conditions.append(["hospital", "=", hospital])
	if status:
		conditions.append(["status", "=", status])
	start = max(0, int(start))
	page_length = max(0, int(page_length))
	rows = frappe.get_list(
		MATERIAL_REQUEST_DOCTYPE,
		filters=conditions,
		fields=MR_LIST_FIELDS,
		limit_start=start,
		limit_page_length=page_length or 0,
		order_by=f"`tab{MATERIAL_REQUEST_DOCTYPE}`.creation desc",
	)
	data = [{k: r.get(k) for k in MR_LIST_ITEM_KEYS} for r in rows]
	total_count = len(frappe.get_list(MATERIAL_REQUEST_DOCTYPE, filters=conditions, pluck="name", limit_page_length=0))
	return {"data": data, "total_count": total_count}


@frappe.whitelist(methods=["GET"])
def get_material_request(name: str) -> dict:
	"""Chi tiết 1 yêu cầu vật tư + items[]. throw PermissionError nếu không read."""
	if not frappe.has_permission(MATERIAL_REQUEST_DOCTYPE, "read", doc=name):
		frappe.throw(_("Bạn không có quyền xem yêu cầu này."), frappe.PermissionError)
	doc = frappe.get_doc(MATERIAL_REQUEST_DOCTYPE, name).as_dict()
	result = {k: doc.get(k) for k in MR_DETAIL_FIELDS}
	result["hospital_name"] = frappe.db.get_value(HOSPITAL_DOCTYPE, doc.get("hospital"), "hospital_name") if doc.get("hospital") else None
	result["doctor_name"] = frappe.db.get_value(DOCTOR_DOCTYPE, doc.get("doctor"), "full_name") if doc.get("doctor") else None
	result["items"] = [{k: row.get(k) for k in MR_ITEM_KEYS} for row in (doc.get("items") or [])]
	return result


@frappe.whitelist(methods=["POST"])
def receive_material_request(name: str) -> dict:
	"""NV tiếp nhận yêu cầu vật tư → 'NV đã nhận' + gán mình. Gate write."""
	if not frappe.has_permission(MATERIAL_REQUEST_DOCTYPE, "write", doc=name):
		frappe.throw(_("Bạn không có quyền tiếp nhận yêu cầu này."), frappe.PermissionError)
	frappe.db.set_value(MATERIAL_REQUEST_DOCTYPE, name, {"status": "NV đã nhận", "assigned_employee": frappe.session.user})
	return {"name": name, "status": "NV đã nhận"}


@frappe.whitelist(methods=["POST"])
def convert_to_delivery(name: str) -> dict:
	"""NV tạo phiếu giao (AntMed Delivery) từ yêu cầu Portal → 'Đã tạo phiếu giao' + delivery_ref.

	Idempotent: đã có delivery_ref → trả lại phiếu cũ (KHÔNG tạo trùng). Nối M09 Portal → M04.
	"""
	if not frappe.has_permission(MATERIAL_REQUEST_DOCTYPE, "write", doc=name):
		frappe.throw(_("Bạn không có quyền xử lý yêu cầu này."), frappe.PermissionError)
	mr = frappe.get_doc(MATERIAL_REQUEST_DOCTYPE, name)
	if mr.delivery_ref:
		return {"name": name, "delivery": mr.delivery_ref, "status": mr.status}
	dlv = frappe.get_doc(
		{
			"doctype": DELIVERY_DOCTYPE,
			"hospital": mr.hospital,
			"doctor": mr.doctor,
			# surgery_datetime bắt buộc trên phiếu giao — default 'now' nếu yêu cầu chưa nêu giờ mổ.
			"surgery_datetime": mr.surgery_datetime or frappe.utils.now_datetime(),
			"surgery_room": mr.surgery_room,
			# NV chuyển yêu cầu = người được gán → phiếu vào thẳng 'Đã gán NV'.
			"status": "Đã gán NV",
			"assigned_employee": mr.assigned_employee or frappe.session.user,
			"items": [{"item": it.item, "item_name": it.item_name, "requested_qty": it.requested_qty} for it in mr.items],
		}
	)
	dlv.insert(ignore_permissions=True)
	frappe.db.set_value(MATERIAL_REQUEST_DOCTYPE, name, {"status": "Đã tạo phiếu giao", "delivery_ref": dlv.name})
	return {"name": name, "delivery": dlv.name, "status": "Đã tạo phiếu giao"}


@frappe.whitelist(methods=["GET"])
def portal_history(hospital: str, start: int = 0, page_length: int = 20) -> dict:
	"""Lịch sử giao & chứng từ của BV (mockup G2). Trả RAW {data, total_count} — count==rows.

	Mỗi dòng: delivery, doctor_name, date, status, sku_count, has_documents (có bundle M06),
	payment_status (placeholder 'Chờ TT' — AR thật ở M-finance). Đọc dưới DocPerm.
	"""
	conditions = [["hospital", "=", hospital], ["status", "in", list(PORTAL_HISTORY_STATES)]]
	start = max(0, int(start))
	page_length = max(0, int(page_length))
	deliveries = frappe.get_list(
		DELIVERY_DOCTYPE,
		filters=conditions,
		fields=["name", "doctor", "surgery_datetime", "delivered_at", "status"],
		limit_start=start,
		limit_page_length=page_length or 0,
		order_by=f"`tab{DELIVERY_DOCTYPE}`.surgery_datetime desc",
	)
	names = [d["name"] for d in deliveries]
	sku_by_parent: dict = {}
	doc_parents: set = set()
	if names:
		for it in frappe.get_all("AntMed Delivery Item", filters={"parent": ["in", names]}, fields=["parent"], limit_page_length=0):
			sku_by_parent[it["parent"]] = sku_by_parent.get(it["parent"], 0) + 1
		for d in frappe.get_all(DOCUMENT_DOCTYPE, filters={"delivery": ["in", names]}, fields=["delivery"], limit_page_length=0):
			doc_parents.add(d["delivery"])
	data = [
		{
			"delivery": d["name"],
			"doctor": d.get("doctor"),
			"doctor_name": frappe.db.get_value(DOCTOR_DOCTYPE, d.get("doctor"), "full_name") if d.get("doctor") else None,
			"date": str(d.get("delivered_at") or d.get("surgery_datetime") or ""),
			"status": d.get("status"),
			"sku_count": sku_by_parent.get(d["name"], 0),
			"has_documents": d["name"] in doc_parents,
			"payment_status": "Chờ TT",
		}
		for d in deliveries
	]
	total_count = len(frappe.get_list(DELIVERY_DOCTYPE, filters=conditions, pluck="name", limit_page_length=0))
	return {"data": data, "total_count": total_count}
