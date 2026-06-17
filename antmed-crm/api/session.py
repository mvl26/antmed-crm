import frappe
from frappe import _

from crm.api.antmed.rbac import ANTMED_ALLOWED_ROLES

# GIỮ NGUYÊN — DEC-B invariant: KHÔNG narrow/đổi value (Gate-2 acceptance).
# AntMed roles KHÔNG được thêm vào hằng này (đó là đổi semantics CRM gốc).
CRM_ALLOWED_ROLES = ["System Manager", "Sales Manager", "Sales User"]


def get_session_role_flags():
	roles = set(frappe.get_roles())

	# [W0-2 ADDITIVE — DEC-B] không throw nếu user là CRM HOẶC AntMed.
	# `allowed` là biến CỤC BỘ (union) — KHÔNG mutate hằng CRM_ALLOWED_ROLES.
	allowed = set(CRM_ALLOWED_ROLES) | set(ANTMED_ALLOWED_ROLES)
	if not roles.intersection(allowed):
		frappe.throw(_("You are not permitted to access CRM resources."), frappe.PermissionError)

	# Cờ CRM giữ NGUYÊN ngữ nghĩa: AntMed-thuần → mọi cờ CRM False
	# (KHÔNG nhét AntMed user vào crmUsers — xem Risk-1 Core Doc).
	return {
		"is_system_manager": "System Manager" in roles,
		"is_sales_manager": "Sales Manager" in roles and "System Manager" not in roles,
		"is_sales_user": "Sales User" in roles
		and "Sales Manager" not in roles
		and "System Manager" not in roles,
	}


@frappe.whitelist()
def get_users():
	session_roles = get_session_role_flags()

	users = frappe.qb.get_query(
		"User",
		fields=[
			"name",
			"email",
			"enabled",
			"user_image",
			"first_name",
			"last_name",
			"full_name",
			"user_type",
			"language",
		],
		order_by="full_name asc",
		distinct=True,
		filters={"enabled": 1},
	).run(as_dict=1)

	crm_users = []
	system_language = frappe.db.get_single_value("System Settings", "language")

	for user in users:
		if frappe.session.user == user.name:
			user.session_user = True

		user.roles = frappe.get_roles(user.name)

		user.role = ""

		if "System Manager" in user.roles:
			user.role = "System Manager"
		elif "Sales Manager" in user.roles:
			user.role = "Sales Manager"
		elif "Sales User" in user.roles:
			user.role = "Sales User"
		elif "Guest" in user.roles:
			user.role = "Guest"

		if frappe.session.user == user.name:
			user.session_user = True

		user.is_telephony_agent = frappe.db.exists("CRM Telephony Agent", {"user": user.name})
		user.language = user.language or system_language

		if user.role in ("System Manager", "Sales Manager", "Sales User"):
			crm_users.append(user)

	if not session_roles["is_system_manager"]:
		users = crm_users

	return users, crm_users


@frappe.whitelist()
def get_organizations():
	get_session_role_flags()

	organizations = frappe.qb.get_query(
		"CRM Organization",
		fields=["*"],
		order_by="name asc",
		distinct=True,
	).run(as_dict=1)

	return organizations
