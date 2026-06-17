# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M02 Slice M02-1 — endpoint Hợp đồng & Quota (read-only).

Đường gọi: antmed_crm.api.antmed.contract.<fn>  (xem m02_contract_quota.md §1bis.3).
Mọi hàm @frappe.whitelist(methods=["GET"]), type-annotated, trả RAW dict (KHÔNG
envelope _ok/_err). Lỗi permission = frappe.throw(..., frappe.PermissionError).

Invariant BR-13 (count == rows): khi không phân trang, len(data) == total_count.
total_count đếm DƯỚI permission của user (frappe.get_list tôn trọng DocPerm) — KHÔNG
dùng frappe.db.count (bỏ qua permission). Giữ contract count==rows khi M14/R3 thêm
permission_query_conditions data-scope.

Pattern mượn từ crm/api/antmed/customer.py (đã verify live R2).
"""

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from antmed_crm.antmed import contract_hooks

CONTRACT_DOCTYPE = "AntMed Contract"
HOSPITAL_DOCTYPE = "AntMed Hospital"
QUOTA_ITEM_DOCTYPE = "AntMed Quota Item"

# Field item trả về cho list endpoint (Hyrum contract với FE AntmedContracts.vue:
# đổi = breaking binding). hospital_name resolve qua dotted-fetch trong get_list.
CONTRACT_LIST_FIELDS = [
	"name",
	"contract_no",
	"hospital",
	"hospital.hospital_name as hospital_name",
	"valid_to",
	"total_value",
	"status",
]
# Key item shape chốt (7 key) — dùng để chuẩn hoá output đảm bảo KHÔNG thừa/thiếu.
CONTRACT_LIST_ITEM_KEYS = (
	"name",
	"contract_no",
	"hospital",
	"hospital_name",
	"valid_to",
	"total_value",
	"status",
)
# Shape mỗi dòng quota trong get_contract.
QUOTA_ROW_FIELDS = [
	"item",
	"item_name",
	"uom",
	"unit_price",
	"quota_qty",
	"used_qty",
	"remaining_pct",
	"lock_at_100",
]


def _coerce_filters(filters: dict | str | None) -> list:
	"""Chuẩn hoá filters về list điều kiện. FE/GET truyền dict hoặc JSON-string.

	M02-1: acceptance gọi 'workflow_state/status' — field thật ở slice này là `status`.
	Nếu caller truyền key `workflow_state` → map về `status` (ADR-M02-04).
	"""
	if not filters:
		return []
	if isinstance(filters, str):
		filters = frappe.parse_json(filters) or []
	if isinstance(filters, dict):
		conditions = []
		for k, v in filters.items():
			field = "status" if k == "workflow_state" else k
			conditions.append([field, "=", v])
		return conditions
	return list(filters)


@frappe.whitelist(methods=["GET"])
def list_contracts(
	filters: dict | str | None = None,
	start: int = 0,
	page_length: int = 20,
	search: str | None = None,
) -> dict:
	"""List hợp đồng. Trả RAW dict {data: list[dict], total_count: int}.

	- search: lọc theo contract_no (LIKE %search%).
	- filters: dict|JSON-string, hỗ trợ key `hospital` + `status` (alias `workflow_state`).
	- page_length=0 → không phân trang (lấy hết khớp filter); khi đó len(data)==total_count.
	- total_count đếm DƯỚI permission user (get_list, pluck name) → giữ invariant count==rows.
	- Mỗi item gồm ĐÚNG 7 field: name, contract_no, hospital, hospital_name, valid_to,
	  total_value, status. hospital_name resolve qua Link bằng dotted-fetch (1 query,
	  null-guard FK orphan: LEFT JOIN → None khi hospital blank/orphan).
	"""
	conditions = _coerce_filters(filters)
	if search:
		conditions.append(["contract_no", "like", f"%{search}%"])

	start = max(0, int(start))
	page_length = max(0, int(page_length))

	rows = frappe.get_list(
		CONTRACT_DOCTYPE,
		filters=conditions,
		fields=CONTRACT_LIST_FIELDS,
		limit_start=start,
		limit_page_length=page_length or 0,  # 0 = không giới hạn
		# Qualify table: dotted-fetch hospital_name JOIN → `modified` ambiguous nếu không
		# nêu rõ bảng HĐ (tabAntMed Hospital cũng có cột modified).
		order_by=f"`tab{CONTRACT_DOCTYPE}`.modified desc",
	)
	# Chuẩn hoá ĐÚNG 7 key (chống thừa/thiếu — Hyrum); null-guard hospital_name.
	data = [{k: r.get(k) for k in CONTRACT_LIST_ITEM_KEYS} for r in rows]

	# total_count = tổng khớp filter, đếm dưới permission (pluck name, không limit).
	total_count = len(
		frappe.get_list(
			CONTRACT_DOCTYPE,
			filters=conditions,
			pluck="name",
			limit_page_length=0,
		)
	)
	return {"data": data, "total_count": total_count}


@frappe.whitelist(methods=["GET"])
def get_contract(name: str) -> dict:
	"""Chi tiết HĐ: field HĐ + hospital_name (resolve qua Link) + items[] (quota).

	throw PermissionError nếu user không read được hợp đồng này.
	"""
	if not frappe.has_permission(CONTRACT_DOCTYPE, "read", doc=name):
		frappe.throw(_("Bạn không có quyền xem hợp đồng này."), frappe.PermissionError)

	doc = frappe.get_doc(CONTRACT_DOCTYPE, name).as_dict()
	result = {
		"name": doc.get("name"),
		"contract_no": doc.get("contract_no"),
		"hospital": doc.get("hospital"),
		"hospital_name": None,
		"signed_date": doc.get("signed_date"),
		"valid_from": doc.get("valid_from"),
		"valid_to": doc.get("valid_to"),
		"total_value": doc.get("total_value"),
		"status": doc.get("status"),
		"docstatus": doc.get("docstatus"),
	}
	# LL-BE-2 + LL-BE-5: enrich *_name, null-guard FK orphan.
	if doc.get("hospital"):
		result["hospital_name"] = frappe.db.get_value(
			HOSPITAL_DOCTYPE, doc.get("hospital"), "hospital_name"
		)
	result["items"] = [
		{k: row.get(k) for k in QUOTA_ROW_FIELDS} for row in (doc.get("items") or [])
	]
	return result


@frappe.whitelist(methods=["GET"])
def check_item_in_contract(hospital: str, item: str) -> dict:
	"""BR-01 lookup (read-only, KHÔNG throw): vật tư X có trong HĐ hiệu lực của BV Y không + quota còn lại.

	Cho M04/mobile tra TRƯỚC khi giao (khác `contract_hooks.assert_item_in_contract` — bản này
	không chặn, chỉ trả dữ liệu). Trả RAW dict 4 key ổn định (Hyrum):
	  { "in_contract": bool, "contract": str|None, "unit_price": float|None, "remaining_qty": float|None }
	"""
	contract_name = contract_hooks.find_active_contract_with_item(hospital, item)
	if not contract_name:
		return {"in_contract": False, "contract": None, "unit_price": None, "remaining_qty": None}
	row = frappe.db.get_value(
		QUOTA_ITEM_DOCTYPE,
		{"parent": contract_name, "item": item},
		["unit_price", "quota_qty", "used_qty"],
		as_dict=True,
	)
	if not row:
		return {"in_contract": True, "contract": contract_name, "unit_price": None, "remaining_qty": None}
	remaining_qty = (row.quota_qty or 0) - (row.used_qty or 0)
	return {
		"in_contract": True,
		"contract": contract_name,
		"unit_price": row.unit_price,
		"remaining_qty": remaining_qty,
	}


def _health_color(used_pct: float, days_to_expiry: int | None) -> str:
	"""Cờ màu sức khoẻ HĐ (§7): xanh ≤80% / cam 80–100% / đỏ >100% HOẶC còn ≤30 ngày tới hạn."""
	color = "green"
	if used_pct > 80:
		color = "orange"
	if used_pct > 100:
		color = "red"
	if days_to_expiry is not None and days_to_expiry <= 30:
		color = "red"
	return color


@frappe.whitelist(methods=["GET"])
def get_contract_health(start: int = 0, page_length: int = 20) -> dict:
	"""Dữ liệu màn "Sức khoẻ Hợp đồng" (M02-2): mỗi HĐ kèm quota tổng đã dùng + hạn + cờ màu.

	Mỗi item gồm field HĐ (như list_contracts) + 3 field dẫn xuất:
	  - quota_used_pct = 100*SUM(used_qty)/SUM(quota_qty) trên các dòng quota (0 nếu chưa có quota).
	  - days_to_expiry = (valid_to - hôm nay).days (None nếu thiếu valid_to).
	  - health_color   = xanh/cam/đỏ theo §7 (xem _health_color).
	Trả RAW {data, total_count}. total_count đếm DƯỚI permission user (get_list) → giữ invariant
	count==rows (BR-13). Quota gộp batch (1 query get_all theo parent IN scope) — KHÔNG N+1.
	"""
	start = max(0, int(start))
	page_length = max(0, int(page_length))

	rows = frappe.get_list(
		CONTRACT_DOCTYPE,
		fields=CONTRACT_LIST_FIELDS,
		limit_start=start,
		limit_page_length=page_length or 0,
		order_by=f"`tab{CONTRACT_DOCTYPE}`.modified desc",
	)

	# Gộp quota của các HĐ trong scope (chỉ item của HĐ user thấy — names lấy từ get_list permission).
	agg: dict = {}
	names = [r["name"] for r in rows]
	if names:
		for it in frappe.get_all(
			QUOTA_ITEM_DOCTYPE,
			filters={"parenttype": CONTRACT_DOCTYPE, "parentfield": "items", "parent": ("in", names)},
			fields=["parent", "quota_qty", "used_qty"],
		):
			sum_q, sum_u = agg.get(it["parent"], (0.0, 0.0))
			agg[it["parent"]] = (sum_q + (it.get("quota_qty") or 0), sum_u + (it.get("used_qty") or 0))

	today = getdate(nowdate())
	data = []
	for r in rows:
		sum_quota, sum_used = agg.get(r["name"], (0.0, 0.0))
		used_pct = round(100 * sum_used / sum_quota, 2) if sum_quota else 0.0
		days_to_expiry = (getdate(r.get("valid_to")) - today).days if r.get("valid_to") else None
		data.append(
			{
				"name": r.get("name"),
				"contract_no": r.get("contract_no"),
				"hospital": r.get("hospital"),
				"hospital_name": r.get("hospital_name"),
				"valid_to": r.get("valid_to"),
				"total_value": r.get("total_value"),
				"status": r.get("status"),
				"quota_used_pct": used_pct,
				"days_to_expiry": days_to_expiry,
				"health_color": _health_color(used_pct, days_to_expiry),
			}
		)

	total_count = len(frappe.get_list(CONTRACT_DOCTYPE, pluck="name", limit_page_length=0))
	return {"data": data, "total_count": total_count}
