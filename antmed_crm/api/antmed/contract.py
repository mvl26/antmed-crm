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

Pattern mượn từ antmed_crm/api/antmed/customer.py (đã verify live R2).
"""

import frappe
from frappe import _
from frappe.utils import add_months, get_datetime, getdate, nowdate

from antmed_crm.antmed import contract_hooks
from antmed_crm.api.antmed._filters import coerce_filters

CONTRACT_DOCTYPE = "AntMed Contract"
HOSPITAL_DOCTYPE = "AntMed Hospital"
QUOTA_ITEM_DOCTYPE = "AntMed Quota Item"
QUOTA_USAGE_LOG_DOCTYPE = "AntMed Quota Usage Log"

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
	return coerce_filters(filters, field_map={"workflow_state": "status"})


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
		result["hospital_name"] = frappe.db.get_value(HOSPITAL_DOCTYPE, doc.get("hospital"), "hospital_name")
	result["items"] = [{k: row.get(k) for k in QUOTA_ROW_FIELDS} for row in (doc.get("items") or [])]
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


# Ngưỡng cảnh báo used_pct (cao→thấp) + ngưỡng ngày sắp hết hạn (§4).
QUOTA_ALERT_BANDS = (100, 90, 70)
EXPIRY_ALERT_DAYS = 30


def _quota_threshold(used_pct: float) -> int | None:
	"""Band cảnh báo cao nhất đã chạm theo used_pct (100/90/70); None nếu <70."""
	for band in QUOTA_ALERT_BANDS:
		if used_pct >= band:
			return band
	return None


@frappe.whitelist(methods=["GET"])
def list_quota_alerts() -> dict:
	"""Cảnh báo điều hành (M02-2, §4/§5): quota chạm 70/90/100% + HĐ sắp hết hạn (≤30 ngày).

	Trả RAW {data, total_count}. Chỉ gồm HĐ user đọc được (get_list dưới DocPerm) → count==rows
	(noperm → rỗng, fail-closed). Mỗi alert có shape ổn định 10 key (Hyrum):
	  kind 'quota'|'expiry' · contract/contract_no/hospital/hospital_name ·
	  item/item_name/used_pct/threshold (quota) · days_to_expiry (expiry).
	Quota gộp batch theo parent IN scope (KHÔNG N+1).
	"""
	contracts = frappe.get_list(
		CONTRACT_DOCTYPE,
		fields=[
			"name",
			"contract_no",
			"hospital",
			"hospital.hospital_name as hospital_name",
			"valid_to",
		],
		limit_page_length=0,
		order_by=f"`tab{CONTRACT_DOCTYPE}`.modified desc",
	)
	by_name = {c["name"]: c for c in contracts}
	names = list(by_name)
	today = getdate(nowdate())
	alerts = []

	# Quota alerts — mỗi dòng item có used_pct ≥ 70.
	if names:
		for it in frappe.get_all(
			QUOTA_ITEM_DOCTYPE,
			filters={"parenttype": CONTRACT_DOCTYPE, "parentfield": "items", "parent": ("in", names)},
			fields=["parent", "item", "item_name", "quota_qty", "used_qty"],
		):
			quota = it.get("quota_qty") or 0
			if not quota:
				continue
			used_pct = round(100 * (it.get("used_qty") or 0) / quota, 2)
			band = _quota_threshold(used_pct)
			if band is None:
				continue
			c = by_name[it["parent"]]
			alerts.append(
				{
					"kind": "quota",
					"contract": c["name"],
					"contract_no": c.get("contract_no"),
					"hospital": c.get("hospital"),
					"hospital_name": c.get("hospital_name"),
					"item": it.get("item"),
					"item_name": it.get("item_name"),
					"used_pct": used_pct,
					"threshold": band,
					"days_to_expiry": None,
				}
			)

	# Expiry alerts — HĐ còn ≤ 30 ngày tới valid_to (gồm cả đã quá hạn, ngày âm).
	for c in contracts:
		if not c.get("valid_to"):
			continue
		days_to_expiry = (getdate(c["valid_to"]) - today).days
		if days_to_expiry <= EXPIRY_ALERT_DAYS:
			alerts.append(
				{
					"kind": "expiry",
					"contract": c["name"],
					"contract_no": c.get("contract_no"),
					"hospital": c.get("hospital"),
					"hospital_name": c.get("hospital_name"),
					"item": None,
					"item_name": None,
					"used_pct": None,
					"threshold": None,
					"days_to_expiry": days_to_expiry,
				}
			)

	# Nặng trước: quota (threshold desc) rồi expiry (gần hạn trước) — thứ tự hiển thị ổn định.
	alerts.sort(
		key=lambda a: (
			0 if a["kind"] == "quota" else 1,
			-(a["threshold"] or 0),
			a["days_to_expiry"] if a["days_to_expiry"] is not None else 9999,
		)
	)
	return {"data": alerts, "total_count": len(alerts)}


@frappe.whitelist(methods=["GET"])
def top_hospitals(limit: int = 10) -> dict:
	"""Xếp hạng BV theo doanh thu HĐ (widget "Top 10 Bệnh viện" — Dashboard CEO, mockup A1).

	Gộp theo hospital trên các HĐ user ĐỌC ĐƯỢC (frappe.get_list → tôn trọng DocPerm +
	User Permission/permission_query_conditions BR-13, KHÔNG raw SQL):
	  - revenue        = SUM(total_value) các HĐ của BV đó.
	  - quota_used_pct = 100*SUM(used_qty)/SUM(quota_qty) trên TẤT CẢ dòng quota của
	                     các HĐ thuộc BV (0.0 nếu BV chưa có quota / sum_quota==0).
	  - health_color   = _health_color(quota_used_pct, days_to_expiry=None) — rank-by-revenue
	                     KHÔNG xét hạn (ADR-M02-08) ⇒ chỉ ngưỡng quota: green ≤80 / orange
	                     >80–100 / red >100.
	  - hospital_name  = resolve qua dotted-fetch (hospital.hospital_name).
	Trả RAW {data, total_count}. data sort GIẢM theo revenue, cắt tối đa `limit` dòng.
	total_count = số BV phân biệt trong scope (KHÔNG cắt limit) → drill "xem tất cả" về sau.

	⚠️ Đây là endpoint XẾP-HẠNG-CẮT-TOP (KHÔNG phải list phân trang) ⇒ invariant count==rows
	   KHÔNG áp dụng (rows bị cắt theo limit có chủ đích). Quota gộp BATCH (1 get_all theo
	   parent IN names) — KHÔNG N+1 (mirror pattern get_contract_health).

	Fail-closed BR-13: user KHÔNG read-perm trên AntMed Contract → frappe.get_list raise
	PermissionError → trả {"data": [], "total_count": 0} (KHÔNG rò, KHÔNG leak).
	"""
	limit = max(1, int(limit))

	try:
		rows = frappe.get_list(
			CONTRACT_DOCTYPE,
			fields=["name", "hospital", "hospital.hospital_name as hospital_name", "total_value"],
			limit_page_length=0,
		)
	except frappe.PermissionError:
		return {"data": [], "total_count": 0}

	# Gộp revenue theo hospital + map HĐ→BV (bỏ HĐ thiếu hospital — không có BV để gộp).
	rev: dict = {}
	name_map: dict = {}
	contract_to_hospital: dict = {}
	for r in rows:
		h = r.get("hospital")
		if not h:
			continue
		rev[h] = rev.get(h, 0.0) + (r.get("total_value") or 0)
		if h not in name_map:
			name_map[h] = r.get("hospital_name")
		contract_to_hospital[r["name"]] = h

	# Gộp quota BATCH theo parent IN names (chỉ HĐ trong scope) — KHÔNG N+1.
	sum_q: dict = {}
	sum_u: dict = {}
	names = list(contract_to_hospital)
	if names:
		for it in frappe.get_all(
			QUOTA_ITEM_DOCTYPE,
			filters={"parenttype": CONTRACT_DOCTYPE, "parentfield": "items", "parent": ("in", names)},
			fields=["parent", "quota_qty", "used_qty"],
		):
			h = contract_to_hospital.get(it["parent"])
			if not h:
				continue
			sum_q[h] = sum_q.get(h, 0.0) + (it.get("quota_qty") or 0)
			sum_u[h] = sum_u.get(h, 0.0) + (it.get("used_qty") or 0)

	data = []
	for h, revenue in rev.items():
		q = sum_q.get(h, 0.0)
		used_pct = round(100 * sum_u.get(h, 0.0) / q, 2) if q else 0.0
		data.append(
			{
				"hospital": h,
				"hospital_name": name_map.get(h),
				"revenue": revenue,
				"quota_used_pct": used_pct,
				"health_color": _health_color(used_pct, None),
			}
		)

	total_count = len(data)  # số BV phân biệt trong scope (trước khi cắt limit).
	# Sort GIẢM revenue; tie-break theo hospital (asc) cho output deterministic (test ổn định).
	data.sort(key=lambda d: (-d["revenue"], d["hospital"]))
	data = data[:limit]
	return {"data": data, "total_count": total_count}


@frappe.whitelist(methods=["GET"])
def top_quota_items(limit: int = 5) -> dict:
	"""Xếp hạng VT trúng thầu theo % quota đã dùng (widget "Danh mục VT trúng thầu — top 5",
	chân màn /antmed/contract-health — mockup A2, M02-5).

	Gộp CROSS-CONTRACT theo item trên các HĐ user ĐỌC ĐƯỢC (frappe.get_list → tôn trọng
	DocPerm + permission_query_conditions BR-13, KHÔNG raw SQL):
	  - quota_qty    = SUM(quota_qty) trên TẤT CẢ dòng quota cùng item của các HĐ trong scope.
	  - used_qty     = SUM(used_qty)  trên các dòng đó.
	  - used_pct     = round(100*SUM(used_qty)/SUM(quota_qty), 1) nếu SUM(quota_qty)>0 ELSE 0.0
	                   (fail-safe — KHÔNG ZeroDivisionError).
	  - item_name    = tên đại diện (dòng quota đầu tiên gặp của item đó).
	  - health_color = _health_color(used_pct, days_to_expiry=None) — TÁI DÙNG helper chung
	                   (cùng nguồn ngưỡng với contract-health & top_hospitals, KHÔNG đẻ ngưỡng mới):
	                   green ≤80 / orange >80–100 / red >100.
	Trả RAW {data, total_count}. data sort GIẢM theo used_pct (tie-break ổn định theo item),
	cắt tối đa `limit` dòng. total_count = số item phân biệt trong scope (KHÔNG cắt limit).

	⚠️ Endpoint xếp-hạng-cắt-top (KHÔNG phân trang): rows bị cắt cố ý ⇒ invariant count==rows
	   của list_contracts KHÔNG áp dụng (total_count có thể > len(data)) — ADR-M02-09.
	   Quota gộp BATCH (1 get_all theo parent IN names) — KHÔNG N+1 (mirror top_hospitals).

	Fail-closed BR-13: user KHÔNG read-perm trên AntMed Contract → frappe.get_list raise
	PermissionError → trả {"data": [], "total_count": 0} (KHÔNG rò, KHÔNG leak).
	"""
	limit = max(1, int(limit))

	# HĐ trong scope (limit_page_length=0 = lấy ĐỦ mọi HĐ user thấy → không sót item).
	try:
		contracts = frappe.get_list(
			CONTRACT_DOCTYPE,
			fields=["name"],
			limit_page_length=0,
		)
	except frappe.PermissionError:
		return {"data": [], "total_count": 0}

	names = [c["name"] for c in contracts]
	if not names:
		return {"data": [], "total_count": 0}

	# Gộp quota CROSS-CONTRACT theo item (BATCH: 1 get_all theo parent IN names) — KHÔNG N+1.
	sum_q: dict = {}
	sum_u: dict = {}
	name_map: dict = {}
	for it in frappe.get_all(
		QUOTA_ITEM_DOCTYPE,
		filters={"parenttype": CONTRACT_DOCTYPE, "parentfield": "items", "parent": ("in", names)},
		fields=["item", "item_name", "quota_qty", "used_qty"],
	):
		key = it.get("item")
		if not key:
			continue  # dòng quota thiếu item → bỏ (không gộp vào nhóm None)
		sum_q[key] = sum_q.get(key, 0.0) + (it.get("quota_qty") or 0)
		sum_u[key] = sum_u.get(key, 0.0) + (it.get("used_qty") or 0)
		if key not in name_map and it.get("item_name"):
			name_map[key] = it.get("item_name")

	data = []
	for key in sum_q:
		q = sum_q[key]
		used = sum_u.get(key, 0.0)
		used_pct = round(100 * used / q, 1) if q else 0.0
		data.append(
			{
				"item": key,
				"item_name": name_map.get(key) or key,
				"quota_qty": q,
				"used_qty": used,
				"used_pct": used_pct,
				"health_color": _health_color(used_pct, None),
			}
		)

	total_count = len(data)  # số item phân biệt trong scope (TRƯỚC khi cắt limit).
	# Sort GIẢM used_pct; tie-break ổn định theo item (asc) cho output deterministic (test ổn định).
	data.sort(key=lambda d: (-d["used_pct"], d["item"]))
	data = data[:limit]
	return {"data": data, "total_count": total_count}


# DocType danh mục VTYT (giữ field `classification` — Select "Loại A/B/C/D"). Quota item.item (Data,
# = SKU) trỏ tới name của AntMed Item ⇒ batch-fetch classification 1 query (KHÔNG N+1).
ITEM_DOCTYPE = "AntMed Item"

# 4 lớp phân loại VTYT chuẩn (khớp EXACT options AntMed Item.classification). Thứ tự A→B→C→D CỐ ĐỊNH
# — widget "Cơ cấu doanh thu" (mockup A2 CEO) LUÔN render đủ 4 dòng (kể cả lớp revenue 0).
REVENUE_MIX_CLASSES = ("Loại A", "Loại B", "Loại C", "Loại D")
# Shape mỗi dòng (Hyrum — 4 key, FROZEN; đổi = breaking FE bind AntmedRevenueMixCard).
REVENUE_MIX_ROW_KEYS = ("classification", "label", "revenue", "pct")


@frappe.whitelist(methods=["GET"])
def revenue_mix() -> dict:
	"""Cơ cấu doanh thu theo nhóm phân loại VTYT (widget "Cơ cấu doanh thu" — Dashboard CEO, mockup A2).

	Gộp CROSS-CONTRACT theo classification của AntMed Item trên các HĐ user ĐỌC ĐƯỢC
	(frappe.get_list → tôn trọng DocPerm + permission_query_conditions BR-13, KHÔNG raw SQL):
	  - revenue (mỗi lớp) = SUM(used_qty × unit_price) trên TẤT CẢ dòng AntMed Quota Item có item
	                        thuộc classification đó (các HĐ trong scope).
	  - data                = ĐÚNG 4 phần tử CỐ ĐỊNH thứ tự Loại A→B→C→D (kể cả lớp revenue 0 → vẫn
	                          render đủ 4 dòng). Mỗi dòng {classification, label, revenue, pct}.
	  - total_revenue       = SUM 4 lớp A–D (để pct cộng ~100%). Item thiếu/ngoài A–D classification
	                          (gộp nhóm "Khác") KHÔNG vào 4 dòng & KHÔNG vào total_revenue.
	  - pct                 = round(100*revenue/total_revenue, 1) nếu total>0 ELSE 0.0 (fail-safe —
	                          KHÔNG ZeroDivisionError).

	⚠️ Endpoint widget (KHÔNG phân trang): data CỐ ĐỊNH 4 dòng ⇒ KHÔNG có total_count/limit.
	   Classification gộp BATCH: 1 get_all quota lines (theo parent IN names) + 1 get_all item→
	   classification (theo name IN distinct SKUs) — KHÔNG N+1.

	Fail-closed BR-13: user KHÔNG read-perm trên AntMed Contract → frappe.get_list raise
	PermissionError → trả {data: 4 dòng revenue=0/pct=0, total_revenue: 0} (KHÔNG raise, KHÔNG leak).
	"""
	# HĐ trong scope (limit_page_length=0 = lấy ĐỦ mọi HĐ user thấy → không sót dòng quota).
	try:
		contracts = frappe.get_list(
			CONTRACT_DOCTYPE,
			fields=["name"],
			limit_page_length=0,
		)
	except frappe.PermissionError:
		return _empty_revenue_mix()

	names = [c["name"] for c in contracts]
	if not names:
		return _empty_revenue_mix()

	# Dòng quota CROSS-CONTRACT (BATCH: 1 get_all theo parent IN names) — KHÔNG N+1.
	# Gộp doanh thu THEO SKU trước; classification map sau (1 query nữa) → tránh N+1.
	rev_by_sku: dict = {}
	for it in frappe.get_all(
		QUOTA_ITEM_DOCTYPE,
		filters={"parenttype": CONTRACT_DOCTYPE, "parentfield": "items", "parent": ("in", names)},
		fields=["item", "used_qty", "unit_price"],
	):
		sku = it.get("item")
		if not sku:
			continue  # dòng thiếu SKU → bỏ (không có item để tra classification)
		line_rev = (it.get("used_qty") or 0) * (it.get("unit_price") or 0)
		rev_by_sku[sku] = rev_by_sku.get(sku, 0.0) + line_rev

	# Tra classification cho TẤT CẢ SKU phân biệt (BATCH: 1 get_all theo name IN skus) — KHÔNG N+1.
	# ignore_permissions=True: classification là metadata tham chiếu (KHÔNG phải dữ liệu phạm vi
	# NV — BR-13 fail-closed đã chốt TRÊN AntMed Contract ở get_list trên). Tránh role thiếu read
	# AntMed Item làm rớt classification → revenue dồn nhầm vào "Khác" (ADR-M02-12 §Consequences).
	classification_by_sku: dict = {}
	skus = list(rev_by_sku)
	if skus:
		for row in frappe.get_all(
			ITEM_DOCTYPE,
			filters={"name": ("in", skus)},
			fields=["name", "classification"],
			ignore_permissions=True,
		):
			classification_by_sku[row["name"]] = row.get("classification")

	# Gộp doanh thu về 4 lớp chuẩn; SKU thiếu/ngoài A–D → nhóm "Khác" (KHÔNG vào 4 dòng & total).
	rev_by_class: dict = {c: 0.0 for c in REVENUE_MIX_CLASSES}
	for sku, revenue in rev_by_sku.items():
		cls = classification_by_sku.get(sku)
		if cls in rev_by_class:
			rev_by_class[cls] += revenue
		# else: nhóm "Khác" — bỏ qua (KHÔNG render, KHÔNG cộng total → pct 4 lớp cộng ~100%).

	total_revenue = sum(rev_by_class.values())
	data = [
		{
			"classification": cls,
			"label": cls,
			"revenue": rev_by_class[cls],
			"pct": round(100 * rev_by_class[cls] / total_revenue, 1) if total_revenue else 0.0,
		}
		for cls in REVENUE_MIX_CLASSES
	]
	return {"data": data, "total_revenue": total_revenue}


def _empty_revenue_mix() -> dict:
	"""Fail-closed / scope rỗng: 4 dòng A–D revenue=0/pct=0, total_revenue=0 (KHÔNG raise, KHÔNG leak)."""
	return {
		"data": [
			{"classification": cls, "label": cls, "revenue": 0.0, "pct": 0.0} for cls in REVENUE_MIX_CLASSES
		],
		"total_revenue": 0,
	}


# Shape RAW dict của widget "Doanh thu tháng" (KPI hàng 1 — Dashboard CEO, mockup A1, M02-8).
# Hyrum — 5 key FROZEN; đổi = breaking FE bind AntmedHome thẻ 'Doanh thu tháng'.
MONTHLY_REVENUE_KEYS = ("current", "previous", "delta_pct", "month_label", "currency")
MONTHLY_REVENUE_CURRENCY = "VND"


def _month_label(d) -> str:
	"""Nhãn tháng 'T<m>/<yyyy>' (vd T6/2026) — khớp regex 'T\\d{1,2}/\\d{4}' (acceptance M02-8)."""
	return f"T{d.month}/{d.year:04d}"


def _empty_monthly_revenue() -> dict:
	"""Fail-closed / scope rỗng: current=previous=0, delta_pct=None, month_label hợp lệ, currency.

	KHÔNG raise, KHÔNG leak (BR-13). month_label LUÔN là tháng hiện tại hợp lệ (FE bind dòng phụ).
	"""
	this_month = getdate(nowdate())
	return {
		"current": 0.0,
		"previous": 0.0,
		"delta_pct": None,
		"month_label": _month_label(this_month),
		"currency": MONTHLY_REVENUE_CURRENCY,
	}


@frappe.whitelist(methods=["GET"])
def monthly_revenue() -> dict:
	"""Doanh thu THÁNG (KPI lớn hàng 1 "Doanh thu tháng — ▲% vs tháng trước" — Dashboard CEO, mockup A1).

	Rollup từ AntMed Quota Usage Log (qty × ts) JOIN AntMed Quota Item (unit_price theo
	contract×item). KHÔNG DocType mới, KHÔNG module mới (M02-8).

	Trả RAW dict shape ổn định 5 key (Hyrum — MONTHLY_REVENUE_KEYS):
	  {
	    "current": float,            # SUM(qty × unit_price) MỌI log ts trong THÁNG HIỆN TẠI (month-to-date)
	    "previous": float,           # cùng công thức cho THÁNG LIỀN TRƯỚC (CẢ tháng)
	    "delta_pct": float | None,   # round(100*(cur-prev)/prev, 1) khi prev>0; None khi prev==0 (FE '—')
	    "month_label": "T<m>/<yyyy>",
	    "currency": "VND",
	  }

	unit_price tra từ AntMed Quota Item khớp (contract, item) — log có (contract, item) KHÔNG
	khớp dòng quota nào ⇒ unit_price=0 (bỏ qua doanh thu, KHÔNG vỡ).

	BATCH (KHÔNG N+1): 1 get_list HĐ trong scope + 1 get_all log (ts >= đầu tháng-trước) +
	1 get_all quota item (parent IN contracts) dựng map (contract,item)→unit_price ở Python.
	KHÔNG raw SQL.

	Fail-closed BR-13: user KHÔNG read-perm AntMed Contract/Quota → frappe.get_list raise
	PermissionError → trả _empty_monthly_revenue (zero, month_label hợp lệ, KHÔNG raise, KHÔNG leak).
	"""
	this_month = getdate(nowdate())
	this_start = this_month.replace(day=1)  # đầu tháng hiện tại (month-to-date theo nowdate)
	prev_start = add_months(this_start, -1)  # đầu tháng liền trước

	# HĐ trong scope (get_list tôn trọng DocPerm + permission_query_conditions BR-13).
	# Fail-closed: noperm → PermissionError → empty (KHÔNG raise, KHÔNG leak).
	try:
		contracts = frappe.get_list(CONTRACT_DOCTYPE, fields=["name"], limit_page_length=0)
	except frappe.PermissionError:
		return _empty_monthly_revenue()

	names = [c["name"] for c in contracts]
	if not names:
		return _empty_monthly_revenue()

	# Map (contract, item) → unit_price (BATCH: 1 get_all quota item theo parent IN names) — KHÔNG N+1.
	price_map: dict = {}
	for it in frappe.get_all(
		QUOTA_ITEM_DOCTYPE,
		filters={"parenttype": CONTRACT_DOCTYPE, "parentfield": "items", "parent": ("in", names)},
		fields=["parent", "item", "unit_price"],
	):
		price_map[(it.get("parent"), it.get("item"))] = it.get("unit_price") or 0

	# Log tiêu hao từ đầu THÁNG LIỀN TRƯỚC (1 get_all gộp cả 2 tháng) — chỉ HĐ trong scope.
	logs = frappe.get_all(
		QUOTA_USAGE_LOG_DOCTYPE,
		filters={"contract": ("in", names), "ts": (">=", f"{prev_start} 00:00:00")},
		fields=["contract", "item", "qty", "ts"],
		limit_page_length=0,
	)

	current = 0.0
	previous = 0.0
	for log in logs:
		ts = get_datetime(log.get("ts"))
		if not ts:
			continue
		# unit_price tra theo (contract, item); không khớp dòng quota nào → 0 (bỏ qua doanh thu).
		unit_price = price_map.get((log.get("contract"), log.get("item")), 0)
		line_rev = (log.get("qty") or 0) * unit_price
		ts_date = getdate(ts)
		if ts_date >= this_start:
			current += line_rev
		elif ts_date >= prev_start:  # đầu tháng trước ≤ ts < đầu tháng này = CẢ tháng trước
			previous += line_rev

	delta_pct = round(100 * (current - previous) / previous, 1) if previous > 0 else None
	return {
		"current": float(current),
		"previous": float(previous),
		"delta_pct": delta_pct,
		"month_label": _month_label(this_month),
		"currency": MONTHLY_REVENUE_CURRENCY,
	}


# ── M02 Slice M02-9 — endpoint MỚI revenue_by_group (widget "Doanh thu theo Nhóm vật tư" CEO, mockup A3) ──
# Số bucket tháng của widget stacked-bar (cửa sổ rolling 12 tháng, kết thúc ở tháng hiện tại).
REVENUE_BY_GROUP_MONTHS = 12
# 4 lớp phân loại VTYT chuẩn (khớp EXACT options AntMed Item.classification). Item thiếu/ngoài 4 lớp
# này → dồn nhóm fallback "Khác". Hằng export ổn định (FE/test bind shape).
REVENUE_BY_GROUP_CLASSES = ("Loại A", "Loại B", "Loại C", "Loại D")
REVENUE_BY_GROUP_OTHER = "Khác"
# 5 nhóm CỐ ĐỊNH thứ tự render A→B→C→D→Khác (widget LUÔN render đủ 5 dòng kể cả revenue=0).
REVENUE_BY_GROUP_ORDER = (*REVENUE_BY_GROUP_CLASSES, REVENUE_BY_GROUP_OTHER)
# Shape RAW dict (Hyrum — 4 key FROZEN; đổi = breaking FE bind AntmedRevenuePage stacked bar).
REVENUE_BY_GROUP_KEYS = ("months", "groups", "grand_total", "currency")
# Shape mỗi group (Hyrum — 4 key FROZEN).
GROUP_ROW_KEYS = ("classification", "label", "monthly", "total")
REVENUE_BY_GROUP_CURRENCY = "VND"


def _month_short_label(d) -> str:
	"""Nhãn tháng ngắn 'T<m>' (vd T6) — trục X widget stacked-bar (mirror contract_consumption_by_month)."""
	return f"T{d.month}"


def _empty_revenue_by_group() -> dict:
	"""Fail-closed / scope rỗng: 12 nhãn tháng hợp lệ + 5 group monthly toàn 0, grand_total 0.

	KHÔNG raise, KHÔNG leak (BR-13). months LUÔN đủ 12 nhãn 'T<m>' (rolling, kết ở tháng hiện tại);
	groups LUÔN đủ 5 dòng thứ tự A→B→C→D→Khác → FE bind ổn định kể cả khi không có quyền/dữ liệu.
	"""
	today = getdate(nowdate())
	months = [
		_month_short_label(add_months(today, offset)) for offset in range(-(REVENUE_BY_GROUP_MONTHS - 1), 1)
	]
	groups = [
		{
			"classification": cls,
			"label": cls,
			"monthly": [0.0] * REVENUE_BY_GROUP_MONTHS,
			"total": 0.0,
		}
		for cls in REVENUE_BY_GROUP_ORDER
	]
	return {
		"months": months,
		"groups": groups,
		"grand_total": 0,
		"currency": REVENUE_BY_GROUP_CURRENCY,
	}


@frappe.whitelist(methods=["GET"])
def revenue_by_group() -> dict:
	"""Doanh thu THẬT theo Nhóm phân loại VTYT × 12 tháng (widget stacked-bar — Dashboard CEO, mockup A3).

	revenue = SUM(qty × unit_price) gộp từ AntMed Quota Usage Log (qty × ts → bucket THÁNG) JOIN
	AntMed Quota Item (unit_price theo contract×item) gộp theo classification của AntMed Item.
	KHÔNG DocType mới, KHÔNG module mới (M02-9).

	Trả RAW dict shape ổn định (Hyrum — KHÔNG bọc { data, total_count }):
	  {
	    "months": ["T<m>", ...],                    # ĐÚNG 12 nhãn, thứ tự thời gian TĂNG dần,
	                                                 #   phần tử cuối = tháng hiện tại (rolling)
	    "groups": [
	      {
	        "classification": "Loại A"|...|"Khác",
	        "label": <== classification>,
	        "monthly": [<float>, ... 12 phần tử],    # monthly[i] = revenue bucket tháng i
	        "total": <float>,                        # SUM(monthly)
	      },
	      ... ĐÚNG 5 group thứ tự CỐ ĐỊNH A→B→C→D→Khác (kể cả revenue=0 vẫn render đủ)
	    ],
	    "grand_total": <float>,                       # SUM(total trên CẢ 5 group, kể cả "Khác")
	    "currency": "VND",
	  }

	classification: SKU (= log.item / quota.item) trỏ name AntMed Item; item thiếu/ngoài A–D
	classification → nhóm "Khác" (gom vào group thứ 5, KHÁC revenue_mix — ở đây "Khác" CÓ render &
	CÓ cộng grand_total). unit_price tra (contract, item) từ AntMed Quota Item — log không khớp dòng
	quota nào ⇒ unit_price=0 (bỏ qua doanh thu, KHÔNG vỡ). log có ts ngoài cửa sổ 12 tháng → bỏ.

	BATCH (KHÔNG N+1, KHÔNG raw SQL): 1 get_list HĐ trong scope + 1 get_all log (ts >= đầu cửa sổ) +
	1 get_all quota item (price_map) + 1 get_all AntMed Item (classification_by_sku) = ≤4 query.

	Fail-closed BR-13: user KHÔNG read-perm AntMed Contract → frappe.get_list raise PermissionError →
	trả _empty_revenue_by_group (months 12 nhãn, groups 5 dòng 0, KHÔNG raise, KHÔNG leak).
	"""
	today = getdate(nowdate())

	# HĐ trong scope (get_list tôn trọng DocPerm + permission_query_conditions BR-13).
	# Fail-closed: noperm → PermissionError → empty (KHÔNG raise, KHÔNG leak).
	try:
		contracts = frappe.get_list(CONTRACT_DOCTYPE, fields=["name"], limit_page_length=0)
	except frappe.PermissionError:
		return _empty_revenue_by_group()

	names = [c["name"] for c in contracts]
	if not names:
		return _empty_revenue_by_group()

	# Dựng 12 bucket tháng liên tục (cũ → mới), kết thúc ở tháng hiện tại (rolling). index theo 'YYYY-MM'.
	months: list[str] = []
	month_index: dict[str, int] = {}
	for i, offset in enumerate(range(-(REVENUE_BY_GROUP_MONTHS - 1), 1)):
		d = add_months(today, offset)
		months.append(_month_short_label(d))
		month_index[f"{d.year:04d}-{d.month:02d}"] = i

	# Map (contract, item) → unit_price (BATCH: 1 get_all quota item theo parent IN names) — KHÔNG N+1.
	# ignore_permissions=True: scope BR-13 ĐÃ chốt ở get_list(Contract) trên (parent IN names = HĐ user
	# đọc được). Bỏ permission re-check ở child query → tránh get_list lồng (N+1, ADR-M02-09 §query budget).
	price_map: dict = {}
	for it in frappe.get_all(
		QUOTA_ITEM_DOCTYPE,
		filters={"parenttype": CONTRACT_DOCTYPE, "parentfield": "items", "parent": ("in", names)},
		fields=["parent", "item", "unit_price"],
		ignore_permissions=True,
	):
		price_map[(it.get("parent"), it.get("item"))] = it.get("unit_price") or 0

	# Log tiêu hao từ đầu cửa sổ 12 tháng (1 get_all gộp) — chỉ HĐ trong scope.
	# ignore_permissions=True: contract IN names = HĐ user đọc được (scope BR-13 đã chốt ở get_list trên).
	window_start = add_months(today.replace(day=1), -(REVENUE_BY_GROUP_MONTHS - 1))
	logs = frappe.get_all(
		QUOTA_USAGE_LOG_DOCTYPE,
		filters={"contract": ("in", names), "ts": (">=", f"{window_start} 00:00:00")},
		fields=["contract", "item", "qty", "ts"],
		limit_page_length=0,
		ignore_permissions=True,
	)

	# Gộp doanh thu theo (sku, bucket-index) trước; classification map sau (1 query nữa) → tránh N+1.
	rev_by_sku_month: dict = {}
	skus: set = set()
	for log in logs:
		ts = get_datetime(log.get("ts"))
		if not ts:
			continue
		idx = month_index.get(f"{ts.year:04d}-{ts.month:02d}")
		if idx is None:
			continue  # ngoài cửa sổ 12 tháng → bỏ
		sku = log.get("item")
		if not sku:
			continue
		unit_price = price_map.get((log.get("contract"), sku), 0)
		line_rev = (log.get("qty") or 0) * unit_price
		if not line_rev:
			continue
		skus.add(sku)
		key = (sku, idx)
		rev_by_sku_month[key] = rev_by_sku_month.get(key, 0.0) + line_rev

	# Tra classification cho TẤT CẢ SKU phân biệt (BATCH: 1 get_all theo name IN skus) — KHÔNG N+1.
	# ignore_permissions=True: classification là metadata tham chiếu (BR-13 đã chốt TRÊN AntMed Contract
	# ở get_list trên). Tránh role thiếu read AntMed Item làm rớt classification → dồn nhầm "Khác".
	classification_by_sku: dict = {}
	if skus:
		for row in frappe.get_all(
			ITEM_DOCTYPE,
			filters={"name": ("in", list(skus))},
			fields=["name", "classification"],
			ignore_permissions=True,
		):
			classification_by_sku[row["name"]] = row.get("classification")

	# Gộp về 5 group × 12 bucket; SKU thiếu/ngoài A–D classification → nhóm "Khác" (CÓ render & total).
	monthly_by_group: dict = {cls: [0.0] * REVENUE_BY_GROUP_MONTHS for cls in REVENUE_BY_GROUP_ORDER}
	for (sku, idx), revenue in rev_by_sku_month.items():
		cls = classification_by_sku.get(sku)
		if cls not in monthly_by_group:
			cls = REVENUE_BY_GROUP_OTHER
		monthly_by_group[cls][idx] += revenue

	groups = []
	grand_total = 0.0
	for cls in REVENUE_BY_GROUP_ORDER:
		monthly = [float(v) for v in monthly_by_group[cls]]
		total = float(sum(monthly))
		grand_total += total
		groups.append({"classification": cls, "label": cls, "monthly": monthly, "total": total})

	return {
		"months": months,
		"groups": groups,
		"grand_total": float(grand_total),
		"currency": REVENUE_BY_GROUP_CURRENCY,
	}


# Số bucket tháng của widget "Tiêu hao HĐ theo tháng" (mockup A1, M02-6) — cửa sổ rolling 12 tháng.
CONSUMPTION_MONTHS = 12


@frappe.whitelist(methods=["GET"])
def contract_consumption_by_month(contract: str) -> dict:
	"""Tiêu hao HĐ theo tháng (widget bar chart 12 cột — mockup A1, render trên màn Chi tiết HĐ).

	SUM(qty) tiêu hao của 1 HĐ theo từng tháng, gộp từ AntMed Quota Usage Log (KHÔNG DocType
	mới, KHÔNG module mới). Cửa sổ = `CONSUMPTION_MONTHS` (12) bucket tháng gần nhất, ROLLING
	(kết thúc ở tháng hiện tại) — chốt theo BA (rolling 12 tháng, ADR-M02-06).

	Trả RAW dict shape ổn định (Hyrum — đổi = breaking FE bind AntmedConsumptionChartCard):
	  {
	    "data": [{"month": "YYYY-MM", "label": "T<m>", "qty": <float>}, ...]  # ĐÚNG 12 phần tử
	    "total_qty": <float>,   # tổng SUM(qty) toàn cửa sổ 12 tháng
	    "contract": <name>,
	  }
	  - 12 bucket tháng LIÊN TỤC (KHÔNG bỏ cột); tháng không có log → qty = 0.0.
	  - 2 log cùng tháng cùng HĐ → cột tháng đó = SUM(qty).
	  - Lọc theo contract → log của HĐ khác KHÔNG lọt.
	  - max(qty)==0 ⇒ FE tự render mọi cột 0% (BE chỉ trả số, KHÔNG tính chiều cao bar).

	BR-13 fail-closed: user KHÔNG read-perm trên HĐ → trả {"data": [], "total_qty": 0,
	"contract": <name>} (KHÔNG rò dữ liệu, KHÔNG leak stacktrace). Dùng frappe.has_permission
	+ frappe.get_all (tôn trọng DocPerm/permission_query_conditions) — KHÔNG raw SQL.
	"""
	# Fail-closed: không read được HĐ → rỗng (KHÔNG raise, KHÔNG leak), giữ contract để FE bind title.
	if not frappe.has_permission(CONTRACT_DOCTYPE, "read", doc=contract):
		return {"data": [], "total_qty": 0, "contract": contract}

	# Dựng 12 bucket tháng liên tục (cũ → mới), kết thúc ở tháng hiện tại (rolling).
	today = getdate(nowdate())
	buckets: list[dict] = []
	index: dict[str, dict] = {}
	for offset in range(-(CONSUMPTION_MONTHS - 1), 1):
		d = add_months(today, offset)
		key = f"{d.year:04d}-{d.month:02d}"
		bucket = {"month": key, "label": f"T{d.month}", "qty": 0.0}
		buckets.append(bucket)
		index[key] = bucket

	# Lấy log tiêu hao của ĐÚNG HĐ này trong cửa sổ (get_all dưới quyền — KHÔNG raw SQL).
	window_start = add_months(today.replace(day=1), -(CONSUMPTION_MONTHS - 1))
	logs = frappe.get_all(
		QUOTA_USAGE_LOG_DOCTYPE,
		filters={"contract": contract, "ts": (">=", f"{window_start} 00:00:00")},
		fields=["qty", "ts"],
		limit_page_length=0,
	)

	total_qty = 0.0
	for log in logs:
		ts = get_datetime(log.get("ts"))
		if not ts:
			continue
		key = f"{ts.year:04d}-{ts.month:02d}"
		bucket = index.get(key)
		if bucket is None:
			continue  # ngoài cửa sổ 12 tháng (log mới hơn "now" hiếm gặp) → bỏ
		qty = log.get("qty") or 0.0
		bucket["qty"] = round(bucket["qty"] + qty, 4)
		total_qty += qty

	return {"data": buckets, "total_qty": round(total_qty, 4), "contract": contract}
