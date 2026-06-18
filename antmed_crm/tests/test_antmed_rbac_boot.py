# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M14 RBAC nền W0-2 — boot gate test (TDD viết TRƯỚC implement).

Core Doc: docs/antmed_crm/docs/m14_rbac_w0_antmed_boot.md (DEC-B, ADR-M14W0-03/04).

Cover acceptance W0-2 (allow-check ADDITIVE, KHÔNG narrow CRM_ALLOWED_ROLES):
  Gate-1 (HTML serve)  — check_app_permission() True cho AntMed-thuần + Sales User (no-regression),
                         False cho outsider.
  Gate-2 (session API) — get_session_role_flags() KHÔNG throw cho AntMed-thuần; VẪN throw outsider.
                         CRM_ALLOWED_ROLES literal KHÔNG đổi (bằng chứng DEC-B).
  Boot                 — get_boot() phơi is_antmed_user + antmed_roles.
  Helper               — is_antmed_user / is_crm_or_antmed_user additive đúng.

Lệnh chạy:
  bench --site miyano run-tests --module antmed_crm.tests.test_antmed_rbac_boot
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from antmed_crm.api import check_app_permission
from antmed_crm.api.antmed.rbac import (
	ANTMED_ALLOWED_ROLES,
	is_antmed_user,
	is_crm_or_antmed_user,
)
from antmed_crm.api.session import CRM_ALLOWED_ROLES, get_session_role_flags
from antmed_crm.www.crm import get_boot

# User fixtures (tạo trong setUp, xoá trong tearDown).
ANTMED_USER = "_antmed_boot@example.com"  # chỉ Role 'NV kinh doanh'
CRM_USER = "_crm_boot@example.com"  # chỉ Role 'Sales User'
OUTSIDER_USER = "_outsider_boot@example.com"  # không CRM-role, không AntMed-role


def _ensure_user(email: str, role: str | None):
	"""Tạo user enabled với đúng 1 Role nghiệp vụ (hoặc không role nào nếu role=None)."""
	if frappe.db.exists("User", email):
		frappe.delete_doc("User", email, force=1, ignore_permissions=True)
	doc = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": email.split("@")[0],
			"send_welcome_email": 0,
			"enabled": 1,
		}
	)
	doc.insert(ignore_permissions=True)
	if role:
		doc.add_roles(role)
	return doc


class TestAntMedRbacBoot(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		_ensure_user(ANTMED_USER, "NV kinh doanh")
		_ensure_user(CRM_USER, "Sales User")
		_ensure_user(OUTSIDER_USER, None)
		frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")
		for email in (ANTMED_USER, CRM_USER, OUTSIDER_USER):
			if frappe.db.exists("User", email):
				frappe.delete_doc("User", email, force=1, ignore_permissions=True)
		frappe.db.commit()
		super().tearDownClass()

	def tearDown(self):
		# Mọi test set_user phải khôi phục Administrator để không rò context.
		frappe.set_user("Administrator")

	# --- Single source / invariant ------------------------------------------
	def test_antmed_role_list_single_source(self):
		"""ANTMED_ALLOWED_ROLES = đúng 3 tên VI (single source)."""
		self.assertEqual(
			list(ANTMED_ALLOWED_ROLES),
			["NV kinh doanh", "Thủ kho", "Quản lý"],
		)

	def test_crm_allowed_roles_constant_unchanged(self):
		"""DEC-B invariant: CRM_ALLOWED_ROLES literal KHÔNG bị narrow/đổi value."""
		self.assertEqual(
			CRM_ALLOWED_ROLES,
			["System Manager", "Sales Manager", "Sales User"],
		)

	# --- Helper additive ----------------------------------------------------
	def test_has_antmed_access_true_for_nv_kinh_doanh(self):
		"""user chỉ Role 'NV kinh doanh' → is_antmed_user() True."""
		self.assertTrue(is_antmed_user(ANTMED_USER))

	def test_is_antmed_user_false_for_crm_user(self):
		"""Sales User KHÔNG phải AntMed user."""
		self.assertFalse(is_antmed_user(CRM_USER))

	def test_is_crm_or_antmed_user_additive(self):
		"""allow-check additive: True cho cả AntMed-thuần lẫn CRM user, False outsider."""
		self.assertTrue(is_crm_or_antmed_user(ANTMED_USER))
		self.assertTrue(is_crm_or_antmed_user(CRM_USER))
		self.assertFalse(is_crm_or_antmed_user(OUTSIDER_USER))

	# --- Gate-1: check_app_permission --------------------------------------
	def test_check_app_permission_true_for_antmed_only_user(self):
		"""Gate-1: user AntMed-thuần → check_app_permission() True (KHÔNG PermissionError)."""
		frappe.set_user(ANTMED_USER)
		self.assertTrue(check_app_permission())

	def test_check_app_permission_still_true_for_sales_user(self):
		"""Gate-1 no-regression: Sales User → vẫn True."""
		frappe.set_user(CRM_USER)
		self.assertTrue(check_app_permission())

	def test_check_app_permission_false_for_outsider(self):
		"""Gate-1: user không CRM-role không AntMed-role → False (gate vẫn chặn)."""
		frappe.set_user(OUTSIDER_USER)
		self.assertFalse(check_app_permission())

	# --- Gate-2: get_session_role_flags ------------------------------------
	def test_session_flags_no_throw_for_antmed_user(self):
		"""Gate-2: user AntMed-thuần KHÔNG raise PermissionError; trả dict flags CRM=False."""
		frappe.set_user(ANTMED_USER)
		flags = get_session_role_flags()
		self.assertIsInstance(flags, dict)
		# AntMed-thuần không phải CRM role nào → mọi cờ CRM False (giữ semantics CRM).
		self.assertFalse(flags["is_system_manager"])
		self.assertFalse(flags["is_sales_manager"])
		self.assertFalse(flags["is_sales_user"])

	def test_session_flags_still_throw_for_outsider(self):
		"""Gate-2: user không CRM-không-AntMed → VẪN raise (giữ chặn)."""
		frappe.set_user(OUTSIDER_USER)
		with self.assertRaises(frappe.PermissionError):
			get_session_role_flags()

	def test_session_flags_intact_for_crm_user(self):
		"""Gate-2 no-regression: Sales User → cờ is_sales_user True, không throw."""
		frappe.set_user(CRM_USER)
		flags = get_session_role_flags()
		self.assertTrue(flags["is_sales_user"])
		self.assertFalse(flags["is_system_manager"])
		self.assertFalse(flags["is_sales_manager"])

	# --- Boot ---------------------------------------------------------------
	def test_boot_exposes_is_antmed_user_flag(self):
		"""Boot: get_boot() phơi is_antmed_user True cho AntMed user, False outsider; + antmed_roles."""
		frappe.set_user(ANTMED_USER)
		boot = get_boot()
		self.assertIn("is_antmed_user", boot)
		self.assertIn("antmed_roles", boot)
		self.assertTrue(boot["is_antmed_user"])
		self.assertEqual(list(boot["antmed_roles"]), list(ANTMED_ALLOWED_ROLES))

		frappe.set_user(OUTSIDER_USER)
		boot_out = get_boot()
		self.assertFalse(boot_out["is_antmed_user"])
