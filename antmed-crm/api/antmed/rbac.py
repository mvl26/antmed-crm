# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M14 RBAC nền W0-2 — single source danh sách Role AntMed + allow-check additive.

Core Doc: docs/antmed_crm/docs/m14_rbac_w0_antmed_boot.md (DEC-B, ADR-M14W0-03/04).

SINGLE SOURCE: ANTMED_ALLOWED_ROLES định nghĩa ĐÚNG 1 nơi ở đây. Mọi tầng
(Gate-1 check_app_permission, Gate-2 get_session_role_flags, boot get_boot)
import từ module này — KHÔNG lặp literal tên Role nơi khác (BE), FE đọc qua
cờ boot window.is_antmed_user / window.antmed_roles (KHÔNG hardcode lần 2).

Allow-check ADDITIVE (OR): True nếu user có ≥1 CRM role HOẶC ≥1 AntMed role —
KHÔNG narrow/đổi CRM_ALLOWED_ROLES (giữ ngữ nghĩa CRM gốc nguyên vẹn).

Các helper ở đây là NỘI BỘ (server-side, gọi bởi gate/boot) — KHÔNG @frappe.whitelist().
"""

import frappe

# SINGLE SOURCE — 3 Role AntMed VI (đồng bộ tên với W0-1 / role fixture).
ANTMED_ALLOWED_ROLES: list[str] = ["NV kinh doanh", "Thủ kho", "Quản lý"]


def is_antmed_user(user: str | None = None) -> bool:
	"""True nếu user có ≥1 Role AntMed (NV kinh doanh / Thủ kho / Quản lý).

	user=None → user phiên hiện tại (frappe.get_roles tự lấy session user).
	"""
	roles = set(frappe.get_roles(user))
	return bool(roles.intersection(ANTMED_ALLOWED_ROLES))


def is_crm_or_antmed_user(user: str | None = None) -> bool:
	"""Allow-check ADDITIVE: CRM-pure user HOẶC AntMed user.

	Lazy-import CRM_ALLOWED_ROLES trong thân hàm để tránh circular import
	(session.py import ANTMED_ALLOWED_ROLES từ module này ở top-level).
	"""
	from crm.api.session import CRM_ALLOWED_ROLES

	roles = set(frappe.get_roles(user))
	return bool(
		roles.intersection(CRM_ALLOWED_ROLES) or roles.intersection(ANTMED_ALLOWED_ROLES)
	)
