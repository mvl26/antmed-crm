# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M02 Slice M02-3 — Quota enforce + usage log (pure functions, KHÔNG whitelist).

Logic ràng buộc HĐ/quota của M02 (BR-01/02/06 + derive used_qty). Gọi từ M04
(giao phòng mổ) qua lazy-import, truyền **PK string** (KHÔNG doc object) → giữ
DAG 1 chiều M02→M04 (m02_contract_quota.md §6). Wiring doc_events sang
`AntMed Delivery` thực hiện khi M04 land; slice này chỉ cần hàm sẵn sàng + test BR.

API nội bộ:
- find_active_contract_with_item(hospital, item) -> str | None   tra HĐ hiệu lực chứa item
- assert_item_in_contract(hospital, item)        -> str | None   BR-01/02 (throw nếu ngoài HĐ, trừ Quản lý)
- assert_quota_available(contract, item, qty)    -> None         BR-06 (throw nếu chạm trần khi lock_at_100)
- consume_quota(contract, item, qty, do_ref)     -> str          ghi 1 dòng log + recompute (idempotent theo do_ref)
- recompute_quota_usage(contract, item)          -> None         derive used_qty/remaining_pct từ tổng log
"""

import frappe
from frappe import _

CONTRACT_DOCTYPE = "AntMed Contract"
QUOTA_ITEM_DOCTYPE = "AntMed Quota Item"
USAGE_LOG_DOCTYPE = "AntMed Quota Usage Log"

# State HĐ còn đối chiếu được (docstatus 1). §3: `Hiệu lực` + `Sắp hết hạn` vẫn enforce;
# `Hết hạn` KHÔNG còn đối chiếu (M04 chặn). `Nháp`/`Chờ duyệt` = docstatus 0 → không tính.
ACTIVE_CONTRACT_STATUSES = ("Hiệu lực", "Sắp hết hạn")
# Role được ghi đè BR-02 (giao item ngoài HĐ) — §4 BR-02: chỉ `Quản lý`.
OVERRIDE_ROLE = "Quản lý"


def find_active_contract_with_item(hospital: str, item: str) -> str | None:
	"""Trả `name` HĐ hiệu lực (docstatus 1, status active) của BV `hospital` có chứa `item`, hoặc None.

	Pure lookup qua SQL (bỏ qua DocPerm — gọi server-side từ M04). Param-bind `%s` cho mọi
	giá trị user (LL-BE-11); số placeholder cho ACTIVE_CONTRACT_STATUSES là hằng nội bộ
	(KHÔNG user input) nên f-string an toàn.
	"""
	if not hospital or not item:
		return None
	placeholders = ", ".join(["%s"] * len(ACTIVE_CONTRACT_STATUSES))
	rows = frappe.db.sql(
		f"""SELECT c.name
			FROM `tab{CONTRACT_DOCTYPE}` c
			INNER JOIN `tab{QUOTA_ITEM_DOCTYPE}` qi
				ON qi.parent = c.name AND qi.parenttype = %s
			WHERE c.hospital = %s AND qi.item = %s
			  AND c.docstatus = 1 AND c.status IN ({placeholders})
			ORDER BY c.valid_to DESC
			LIMIT 1""",
		(CONTRACT_DOCTYPE, hospital, item, *ACTIVE_CONTRACT_STATUSES),
		as_dict=True,
	)
	return rows[0]["name"] if rows else None


def _can_override_contract() -> bool:
	"""User có Role `Quản lý` được ghi đè BR-02 (Administrator có mọi role → cũng qua)."""
	return OVERRIDE_ROLE in frappe.get_roles()


def assert_item_in_contract(hospital: str, item: str) -> str | None:
	"""BR-01/02: vật tư phải thuộc 1 HĐ hiệu lực của đúng BV. Trả `contract name`.

	Ngoài danh mục → `frappe.throw('BR-02: ...')`, trừ khi user có Role `Quản lý`
	(ghi đè → trả None, cho qua). Gọi từ `AntMed Delivery.validate` (M04) mỗi dòng giao.
	"""
	contract = find_active_contract_with_item(hospital, item)
	if contract:
		return contract
	if _can_override_contract():
		return None
	frappe.throw(
		_("BR-02: Vật tư {0} không thuộc danh mục trúng thầu hiệu lực của bệnh viện {1}.").format(
			item, hospital
		)
	)


def assert_quota_available(contract: str, item: str, qty: float) -> None:
	"""BR-06: chặn giao vượt trần quota khi `lock_at_100`.

	No-op khi item không có dòng quota trong HĐ (membership do BR-01 lo) hoặc `lock_at_100=0`
	(chỉ cảnh báo, không chặn). Null-guard FK orphan (LL-BE-5).
	"""
	row = frappe.db.get_value(
		QUOTA_ITEM_DOCTYPE,
		{"parent": contract, "item": item},
		["quota_qty", "used_qty", "lock_at_100"],
		as_dict=True,
	)
	if not row:
		return
	if not row.lock_at_100:
		return
	remaining = (row.quota_qty or 0) - (row.used_qty or 0)
	if float(qty or 0) > remaining:
		frappe.throw(
			_("BR-06: Quota vật tư {0} đã chạm trần (còn {1}/{2}). Cần phụ lục mới.").format(
				item, remaining, row.quota_qty or 0
			)
		)


def recompute_quota_usage(contract: str, item: str) -> None:
	"""Derive `used_qty` + `remaining_pct` của dòng quota từ tổng AntMed Quota Usage Log (LL-BE-15).

	Ghi thẳng qua `db.set_value` (parent submittable/docstatus 1 → KHÔNG `doc.save()`).
	"""
	row = frappe.db.get_value(
		QUOTA_ITEM_DOCTYPE,
		{"parent": contract, "item": item},
		["name", "quota_qty"],
		as_dict=True,
	)
	if not row:
		return
	total_used = (
		frappe.db.sql(
			f"""SELECT COALESCE(SUM(qty), 0) FROM `tab{USAGE_LOG_DOCTYPE}`
				WHERE contract = %s AND item = %s""",
			(contract, item),
		)[0][0]
		or 0
	)
	total_used = float(total_used)
	quota = float(row.quota_qty or 0)
	remaining_pct = round((1 - total_used / quota) * 100, 2) if quota else 0
	frappe.db.set_value(
		QUOTA_ITEM_DOCTYPE,
		row.name,
		{"used_qty": total_used, "remaining_pct": remaining_pct},
		update_modified=False,
	)


def consume_quota(contract: str, item: str, qty: float, do_ref: str | None = None) -> str:
	"""Ghi 1 dòng AntMed Quota Usage Log + recompute. Idempotent theo (contract,item,do_ref) (LL-BE-7).

	Gọi từ `AntMed Delivery.on_submit` (M04). Trả `name` của log (mới hoặc đã tồn tại).
	"""
	if do_ref:
		existing = frappe.db.exists(USAGE_LOG_DOCTYPE, {"contract": contract, "item": item, "do_ref": do_ref})
		if existing:
			return existing
	log = frappe.get_doc(
		{
			"doctype": USAGE_LOG_DOCTYPE,
			"contract": contract,
			"item": item,
			"do_ref": do_ref,
			"qty": float(qty or 0),
		}
	)
	log.insert(ignore_permissions=True)
	recompute_quota_usage(contract, item)
	# Snapshot % còn lại SAU khi tiêu hao lên dòng log (audit trail).
	pct = frappe.db.get_value(QUOTA_ITEM_DOCTYPE, {"parent": contract, "item": item}, "remaining_pct")
	if pct is not None:
		frappe.db.set_value(USAGE_LOG_DOCTYPE, log.name, "snapshot_pct", pct, update_modified=False)
	return log.name
