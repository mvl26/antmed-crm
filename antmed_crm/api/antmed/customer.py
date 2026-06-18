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


def _coerce_filters(filters: dict | str | None) -> list:
	"""Chuẩn hoá filters về list điều kiện. FE/GET truyền dict hoặc JSON-string."""
	if not filters:
		return []
	if isinstance(filters, str):
		filters = frappe.parse_json(filters) or []
	if isinstance(filters, dict):
		# dict {field: value} → list [[field, "=", value]] để gộp được điều kiện search.
		return [[k, "=", v] for k, v in filters.items()]
	return list(filters)


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
