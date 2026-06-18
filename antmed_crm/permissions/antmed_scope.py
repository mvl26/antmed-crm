# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M14-S3a — Data-scope BR-13 (owner-based) cho AntMed doctype qua permission_query_conditions.

An toàn + well-defined: NV chỉ thấy bản ghi MÌNH phụ trách (field owner). Admin/Quản lý bypass
(thấy hết) như org_hierarchy. Fail-closed: NV không khớp → KHÔNG thấy gì.

⚠️ Đây là 'BR-13 lite' theo owner. Scope hospital-territory đầy đủ (NV thấy mọi bản ghi của BV
trong tuyến) cần model NV↔BV — CHƯA tồn tại, là quyết định thiết kế (chờ BA/khách hàng).
"""

import frappe

# DocType → field chứa NV phụ trách (owner). Mở rộng dần khi field rõ ràng.
_OWNER_FIELD = {
	"AntMed Delivery": "assigned_employee",
}
# Role thấy TẤT CẢ (không bị scope) — như Quản lý/admin trong org_hierarchy.
_BYPASS_ROLES = {"System Manager", "Quản lý"}
ASSIGNMENT_DOCTYPE = "AntMed Employee Hospital"


def _assigned_hospitals(user: str) -> list:
	"""BV trong tuyến của NV (model NV↔BV — AntMed Employee Hospital)."""
	return frappe.get_all(ASSIGNMENT_DOCTYPE, filters={"employee": user}, pluck="hospital") or []


def _bypass(user: str) -> bool:
	return user == "Administrator" or bool(_BYPASS_ROLES & set(frappe.get_roles(user)))


def _scope_condition(doctype: str, hospital_field: str, user: str | None = None) -> str:
	"""BR-13: NV thấy bản ghi của BV trong tuyến HOẶC bản ghi mình phụ trách. Admin/QL bypass.

	Fail-closed: NV chưa gán tuyến → chỉ thấy bản ghi owner mình (không lộ BV ngoài tuyến).
	"""
	user = user or frappe.session.user
	if _bypass(user):
		return ""
	owner_field = _OWNER_FIELD.get(doctype)
	own = f"`tab{doctype}`.`{owner_field}` = {frappe.db.escape(user)}" if owner_field else "1=0"
	hospitals = _assigned_hospitals(user)
	if not hospitals:
		return own
	in_list = ", ".join(frappe.db.escape(h) for h in hospitals)
	return f"(`tab{doctype}`.`{hospital_field}` in ({in_list}) or {own})"


def delivery_scope(user=None):
	"""permission_query_conditions cho AntMed Delivery (BR-13 territory NV↔BV + owner)."""
	return _scope_condition("AntMed Delivery", "hospital", user)
