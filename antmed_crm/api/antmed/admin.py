# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""H1 — Quản trị User & Role (admin RBAC).

Đường gọi: antmed_crm.api.antmed.admin.<fn>. MỌI endpoint gate _assert_admin()
(System Manager / Quản lý) — đây là bề mặt nhạy cảm (liệt kê + sửa quyền user).
Guard chống leo quyền: KHÔNG đụng Administrator, KHÔNG tự khoá mình, CHỈ quản các role
trong MANAGED_ROLES (không gán/gỡ System Manager qua màn này).
"""

import frappe
from frappe import _
from frappe.utils import validate_email_address

# Role admin được phép dùng màn H1.
ADMIN_ROLES = ("System Manager", "Quản lý")

# Role màn H1 được quyền gán/gỡ (KHÔNG gồm System Manager — chống leo quyền qua UI).
MANAGED_ROLES = ("Quản lý", "NV kinh doanh", "Thủ kho", "Sales Manager", "Sales User")

# Theme pill cho từng role (FE map; để đây làm single-source nhãn↔theme).
ROLE_THEME = {
	"Quản lý": "orange",
	"Sales Manager": "orange",
	"NV kinh doanh": "blue",
	"Sales User": "blue",
	"Thủ kho": "gray",
}

# DocType AntMed hiển thị trong ma trận quyền (nhãn nghiệp vụ VI).
PERMISSION_MODULES = [
	("AntMed Hospital", "Bệnh viện / Khách hàng"),
	("AntMed Contract", "Hợp đồng & Quota"),
	("AntMed Item", "Vật tư"),
	("AntMed Warehouse", "Kho"),
	("AntMed Stock Entry", "Phiếu xuất kho"),
	("AntMed Delivery", "Phiếu giao phòng mổ"),
	("AntMed Instrument Set", "Bộ dụng cụ"),
	("AntMed Instrument Loan", "Lượt mượn bộ"),
	("AntMed Certificate", "Chứng từ CO/CQ"),
]


def _assert_admin() -> None:
	roles = set(frappe.get_roles())
	if not roles.intersection(ADMIN_ROLES):
		frappe.throw(
			_("Chỉ Quản trị (System Manager / Quản lý) được truy cập màn này."), frappe.PermissionError
		)


def _guard_target(user: str) -> None:
	"""Chống thao tác lên tài khoản hệ thống / chính mình (tránh tự khoá)."""
	if user in ("Administrator", "Guest"):
		frappe.throw(_("Không được thao tác trên tài khoản hệ thống."))
	if user == frappe.session.user:
		frappe.throw(_("Không thể tự thay đổi quyền/khoá tài khoản của chính mình."))
	if not frappe.db.exists("User", user):
		frappe.throw(_("Không tìm thấy người dùng {0}.").format(user))


def _data_scope(user: str) -> str:
	"""Phạm vi DL = các Bệnh viện user bị giới hạn (User Permission); rỗng → Toàn bộ."""
	rows = frappe.get_all(
		"User Permission",
		filters={"user": user, "allow": "AntMed Hospital"},
		fields=["for_value"],
		limit=5,
	)
	if not rows:
		return _("Toàn bộ")
	names = frappe.get_all(
		"AntMed Hospital", filters={"name": ["in", [r.for_value for r in rows]]}, fields=["hospital_name"]
	)
	return " · ".join([n.hospital_name for n in names if n.hospital_name]) or _("Toàn bộ")


@frappe.whitelist(methods=["GET"])
def list_users(search: str | None = None, start: int = 0, page_length: int = 50) -> dict:
	"""Danh sách System User + role quản lý + phạm vi DL + 2FA(global) + enabled. Admin-gated."""
	_assert_admin()
	conditions = {"user_type": "System User", "name": ["not in", ["Administrator", "Guest"]]}
	if search:
		conditions["full_name"] = ["like", f"%{search}%"]

	start = max(0, int(start))
	page_length = max(0, int(page_length))
	users = frappe.get_all(
		"User",
		filters=conditions,
		fields=["name", "full_name", "enabled"],
		order_by="full_name asc",
		limit_start=start,
		limit_page_length=page_length or 0,
	)
	global_2fa = bool(frappe.db.get_single_value("System Settings", "enable_two_factor_auth"))

	data = []
	for u in users:
		all_roles = set(frappe.get_roles(u.name))
		managed = [r for r in MANAGED_ROLES if r in all_roles]
		data.append(
			{
				"name": u.name,
				"full_name": u.full_name or u.name,
				"email": u.name,
				"roles": managed,
				"is_admin": "System Manager" in all_roles,
				"data_scope": _data_scope(u.name),
				"two_factor": global_2fa,
				"enabled": bool(u.enabled),
			}
		)
	total_count = frappe.db.count("User", conditions)
	return {"data": data, "total_count": total_count, "global_2fa": global_2fa}


@frappe.whitelist(methods=["GET"])
def list_roles() -> dict:
	"""Role gán được qua màn H1 (kèm theme pill)."""
	_assert_admin()
	return {
		"roles": [{"name": r, "theme": ROLE_THEME.get(r, "gray")} for r in MANAGED_ROLES],
	}


@frappe.whitelist(methods=["GET"])
def role_permissions(role: str) -> dict:
	"""Ma trận quyền (Module × Đọc/Tạo/Sửa/Xóa) cho 1 role, đọc từ DocPerm. Admin-gated."""
	_assert_admin()
	if role not in MANAGED_ROLES:
		frappe.throw(_("Vai trò không hợp lệ."))
	rows = []
	for doctype, label in PERMISSION_MODULES:
		perm = (
			frappe.db.get_value(
				"DocPerm",
				{"parent": doctype, "role": role, "permlevel": 0},
				["read", "create", "write", "delete"],
				as_dict=True,
			)
			or {}
		)
		rows.append(
			{
				"module": label,
				"doctype": doctype,
				"read": bool(perm.get("read")),
				"create": bool(perm.get("create")),
				"write": bool(perm.get("write")),
				"delete": bool(perm.get("delete")),
			}
		)
	return {"role": role, "rows": rows}


@frappe.whitelist(methods=["POST"])
def create_user(email: str, full_name: str, role: str, password: str | None = None) -> dict:
	"""Tạo System User mới + gán 1 role + ĐẶT mật khẩu đăng nhập. Admin-gated.

	password (bắt buộc, ≥8 ký tự): admin đặt trực tiếp để user đăng nhập ngay
	(send_welcome_email=0). Mật khẩu phải đạt password policy của site nếu có.
	"""
	_assert_admin()
	email = (email or "").strip().lower()
	validate_email_address(email, throw=True)
	if role not in MANAGED_ROLES:
		frappe.throw(_("Vai trò không hợp lệ."))
	if frappe.db.exists("User", email):
		frappe.throw(_("Email {0} đã tồn tại.").format(email))
	password = (password or "").strip()
	if len(password) < 8:
		frappe.throw(_("Mật khẩu phải có tối thiểu 8 ký tự."))
	parts = (full_name or "").strip().split(" ", 1)
	doc = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": parts[0] or email,
			"last_name": parts[1] if len(parts) > 1 else "",
			"user_type": "System User",
			"send_welcome_email": 0,
			"new_password": password,
			"roles": [{"role": role}],
		}
	)
	doc.insert()
	return {"name": doc.name, "full_name": doc.full_name, "role": role}


@frappe.whitelist(methods=["POST"])
def set_user_enabled(user: str, enabled: int) -> dict:
	"""Khoá/mở tài khoản (enabled 0/1). Admin-gated + guard self/Administrator."""
	_assert_admin()
	_guard_target(user)
	enabled = 1 if int(enabled) else 0
	doc = frappe.get_doc("User", user)
	doc.enabled = enabled
	doc.save()
	return {"name": user, "enabled": bool(enabled)}


@frappe.whitelist(methods=["POST"])
def set_user_roles(user: str, roles_json: str | None = None) -> dict:
	"""Đặt lại tập role QUẢN LÝ của user (chỉ trong MANAGED_ROLES). Admin-gated.

	roles_json = list role mong muốn. Role ngoài MANAGED_ROLES (vd System Manager) GIỮ NGUYÊN.
	"""
	_assert_admin()
	_guard_target(user)
	desired = set(frappe.parse_json(roles_json) if roles_json else [])
	invalid = desired - set(MANAGED_ROLES)
	if invalid:
		frappe.throw(_("Không được gán role ngoài phạm vi quản lý: {0}").format(", ".join(sorted(invalid))))

	doc = frappe.get_doc("User", user)
	current_managed = {r.role for r in doc.get("roles") if r.role in MANAGED_ROLES}
	to_add = desired - current_managed
	to_remove = current_managed - desired
	if to_add:
		doc.add_roles(*to_add)
	if to_remove:
		doc.remove_roles(*to_remove)
	return {"name": user, "roles": sorted(desired)}


@frappe.whitelist(methods=["POST"])
def set_global_2fa(enabled: int) -> dict:
	"""Bật/tắt 2FA TOÀN HỆ THỐNG (System Settings). Admin-gated.

	Lưu ý: Frappe không hỗ trợ 2FA bật/tắt từng-user — đây là công tắc hệ thống.
	"""
	_assert_admin()
	enabled = 1 if int(enabled) else 0
	frappe.db.set_single_value("System Settings", "enable_two_factor_auth", enabled)
	return {"enabled": bool(enabled)}
