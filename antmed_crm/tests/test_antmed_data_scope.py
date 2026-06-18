# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M14 Slice S3a (BE) — Data-scope BR-13 (owner-based): permission_query_conditions trên AntMed Delivery.

Phạm vi an toàn: NV chỉ thấy phiếu giao MÌNH phụ trách (assigned_employee). Admin/Quản lý thấy hết
(bypass). Hospital-territory đầy đủ chờ model NV↔BV (chưa có — design pending). Cover BR-13:
  test_admin_sees_all   — Administrator KHÔNG bị scope.
  test_nv_scoped_to_own — NV chỉ thấy phiếu assigned_employee == mình (fail-closed phiếu của NV khác).

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_data_scope
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime


def _ensure(doctype, key, val, values):
	return frappe.db.get_value(doctype, {key: val}, "name") or frappe.get_doc({"doctype": doctype, key: val, **values}).insert(ignore_permissions=True).name


def _mk_nv(email):
	if not frappe.db.exists("User", email):
		frappe.get_doc({"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0}).insert(ignore_permissions=True)
	u = frappe.get_doc("User", email)
	if "NV kinh doanh" not in [r.role for r in u.roles]:
		u.add_roles("NV kinh doanh")
	return email


class TestAntMedDataScope(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hosp = _ensure("AntMed Hospital", "hospital_code", "_T-SCOPE-BV", {"hospital_name": "BV Scope"})
		cls.a = _mk_nv("_t_scope_a@example.com")
		cls.b = _mk_nv("_t_scope_b@example.com")
		cls.da = cls._mk_delivery(cls.a)
		cls.db_ = cls._mk_delivery(cls.b)

	@classmethod
	def _mk_delivery(cls, assigned):
		return frappe.get_doc(
			{"doctype": "AntMed Delivery", "hospital": cls.hosp, "surgery_datetime": str(add_to_date(now_datetime(), hours=5)), "assigned_employee": assigned, "status": "Đã gán NV"}
		).insert(ignore_permissions=True).name

	def test_admin_sees_all(self):
		names = {d["name"] for d in frappe.get_list("AntMed Delivery", filters={"name": ["in", [self.da, self.db_]]}, limit_page_length=0)}
		self.assertEqual(names, {self.da, self.db_})

	def test_nv_scoped_to_own(self):
		# A chưa gán tuyến BV nào → fail-closed về owner-based (chỉ phiếu mình phụ trách).
		frappe.set_user(self.a)
		try:
			names = {d["name"] for d in frappe.get_list("AntMed Delivery", limit_page_length=0)}
		finally:
			frappe.set_user("Administrator")
		self.assertIn(self.da, names)
		self.assertNotIn(self.db_, names)  # fail-closed: KHÔNG thấy phiếu của NV khác

	def test_territory_scope(self):
		# C được gán BV-Z → thấy MỌI phiếu tới Z (kể cả phiếu NV khác phụ trách). BR-13 territory.
		c = _mk_nv("_t_scope_c@example.com")
		hz = _ensure("AntMed Hospital", "hospital_code", "_T-SCOPE-BVZ", {"hospital_name": "BV Scope Z"})
		if not frappe.db.exists("AntMed Employee Hospital", {"employee": c, "hospital": hz}):
			frappe.get_doc({"doctype": "AntMed Employee Hospital", "employee": c, "hospital": hz}).insert(ignore_permissions=True)
		dz = frappe.get_doc(
			{"doctype": "AntMed Delivery", "hospital": hz, "surgery_datetime": str(add_to_date(now_datetime(), hours=6)), "assigned_employee": self.b, "status": "Đã gán NV"}
		).insert(ignore_permissions=True).name
		frappe.set_user(c)
		try:
			names = {d["name"] for d in frappe.get_list("AntMed Delivery", limit_page_length=0)}
		finally:
			frappe.set_user("Administrator")
		self.assertIn(dz, names)  # thấy phiếu tới BV trong tuyến dù assigned cho người khác
		self.assertNotIn(self.da, names)  # phiếu BV ngoài tuyến + không phụ trách → KHÔNG thấy
