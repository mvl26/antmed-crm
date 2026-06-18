# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""Hồ sơ người dùng hiện tại (Frappe User) — màn Trang cá nhân AntMed.

`me()` trả hồ sơ của CHÍNH user đang đăng nhập (không gate role — ai cũng xem được
hồ sơ của mình; Guest bị chặn). Dùng cho topbar avatar + trang /antmed/profile.
"""

import frappe
from frappe import _


@frappe.whitelist(methods=["GET"])
def me() -> dict:
	"""Hồ sơ user phiên hiện tại: tên, email, role, phạm vi DL, 2FA, lần đăng nhập cuối."""
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Chưa đăng nhập."), frappe.PermissionError)

	u = (
		frappe.db.get_value(
			"User",
			user,
			["full_name", "email", "enabled", "user_image", "last_login", "time_zone"],
			as_dict=True,
		)
		or {}
	)
	roles = [r for r in frappe.get_roles(user) if r not in ("All", "Guest", "Desk User")]

	# Tái dùng helper data-scope của màn admin (không gate — chỉ đọc User Permission).
	from antmed_crm.api.antmed.admin import MANAGED_ROLES, _data_scope

	return {
		"name": user,
		"full_name": u.get("full_name") or user,
		"email": u.get("email") or user,
		"enabled": bool(u.get("enabled")),
		"user_image": u.get("user_image"),
		"last_login": str(u.get("last_login")) if u.get("last_login") else None,
		"time_zone": u.get("time_zone"),
		"roles": roles,
		"managed_roles": [r for r in roles if r in MANAGED_ROLES],
		"is_admin": "System Manager" in roles,
		"data_scope": _data_scope(user),
		"two_factor": bool(frappe.db.get_single_value("System Settings", "enable_two_factor_auth")),
	}
