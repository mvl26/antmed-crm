# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""H1 — Quản trị User & Role: gate admin + guard chống leo quyền/tự khoá.

Lệnh:  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_admin
"""

import json

import frappe
from frappe.tests.utils import FrappeTestCase

from antmed_crm.api.antmed import admin


def _ensure_user(email, first, roles):
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": first,
				"send_welcome_email": 0,
				"user_type": "System User",
				"roles": [{"role": r} for r in roles],
			}
		).insert(ignore_permissions=True)
	return email


class TestAntMedAdmin(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.ql = _ensure_user("_t_adm_ql@example.com", "AdmQL", ["Quản lý"])
		cls.nv = _ensure_user("_t_adm_nv@example.com", "AdmNV", ["NV kinh doanh"])
		cls.target = _ensure_user("_t_adm_target@example.com", "AdmTarget", ["NV kinh doanh"])

	def tearDown(self):
		frappe.set_user("Administrator")

	# ── Gate: non-admin bị chặn mọi endpoint ─────────────────────────────────
	def test_gate_blocks_non_admin(self):
		frappe.set_user(self.nv)
		for call in (
			lambda: admin.list_users(),
			lambda: admin.list_roles(),
			lambda: admin.role_permissions("NV kinh doanh"),
			lambda: admin.create_user("x@y.vn", "X", "Thủ kho"),
			lambda: admin.set_user_enabled(self.target, 0),
			lambda: admin.set_user_roles(self.target, json.dumps(["Thủ kho"])),
			lambda: admin.set_global_2fa(1),
		):
			with self.assertRaises(frappe.PermissionError):
				call()

	def test_admin_role_passes_gate(self):
		frappe.set_user(self.ql)
		res = admin.list_users()
		self.assertEqual(set(res.keys()), {"data", "total_count", "global_2fa"})

	# ── Read shapes ──────────────────────────────────────────────────────────
	def test_list_users_shape(self):
		res = admin.list_users(search="AdmTarget")
		row = next((r for r in res["data"] if r["name"] == self.target), None)
		self.assertIsNotNone(row)
		for k in ("full_name", "email", "roles", "data_scope", "two_factor", "enabled"):
			self.assertIn(k, row)
		self.assertIn("NV kinh doanh", row["roles"])

	def test_role_permissions_from_docperm(self):
		res = admin.role_permissions("NV kinh doanh")
		hosp = next((r for r in res["rows"] if r["doctype"] == "AntMed Hospital"), None)
		self.assertIsNotNone(hosp)
		self.assertTrue(hosp["read"])  # NV đọc được BV
		contract = next((r for r in res["rows"] if r["doctype"] == "AntMed Contract"), None)
		self.assertFalse(contract["create"])  # NV KHÔNG tạo được Hợp đồng

	# ── Writes + guards ──────────────────────────────────────────────────────
	def test_create_user(self):
		email = "_t_adm_new@example.com"
		if frappe.db.exists("User", email):
			frappe.delete_doc("User", email, force=True, ignore_permissions=True)
		res = admin.create_user(email, "Người Mới", "Thủ kho", password="Antmed@2026")
		self.assertEqual(res["name"], email)
		self.assertIn("Thủ kho", frappe.get_roles(email))
		# Mật khẩu < 8 ký tự → chặn.
		with self.assertRaises(frappe.ValidationError):
			admin.create_user("_t_adm_short@example.com", "Short Pwd", "Thủ kho", password="123")

	def test_set_roles_managed_only(self):
		admin.set_user_roles(self.target, json.dumps(["Thủ kho"]))
		roles = set(frappe.get_roles(self.target))
		self.assertIn("Thủ kho", roles)
		self.assertNotIn("NV kinh doanh", roles)  # đã gỡ

	def test_set_roles_escalation_blocked(self):
		with self.assertRaises(frappe.ValidationError):
			admin.set_user_roles(self.target, json.dumps(["System Manager"]))

	def test_guard_administrator(self):
		with self.assertRaises(frappe.ValidationError):
			admin.set_user_enabled("Administrator", 0)

	def test_guard_self_lock(self):
		frappe.set_user(self.ql)
		with self.assertRaises(frappe.ValidationError):
			admin.set_user_enabled(self.ql, 0)

	def test_set_enabled_toggle(self):
		admin.set_user_enabled(self.target, 0)
		self.assertEqual(frappe.db.get_value("User", self.target, "enabled"), 0)
		admin.set_user_enabled(self.target, 1)
		self.assertEqual(frappe.db.get_value("User", self.target, "enabled"), 1)
