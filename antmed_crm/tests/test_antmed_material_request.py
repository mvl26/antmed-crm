# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M09 Slice S1 (BE) — Portal BV "Gọi vật tư": AntMed Material Request + customer.create/list/get.

Cover mockup G1 (Form gọi vật tư) — BV gửi yêu cầu vật tư cho ca mổ, đánh dấu in-quota
(BR-01: trong danh mục trúng thầu) vs ngoài thầu (cần duyệt):
  test_doctypes          — Material Request submittable (YC) + Material Request Item child.
  test_create_in_out_quota — item trong HĐ → in_quota=1; ngoài HĐ → 0 + needs_approval.
  test_list_and_get      — list_material_requests count==rows; get_material_request + items.

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_material_request
"""

import re

import frappe
from frappe.tests.utils import FrappeTestCase

from antmed_crm.api.antmed import customer

YC_RE = re.compile(r"^YC-\d{4}-\d+")


def _ensure(doctype, key, val, values):
	return (
		frappe.db.get_value(doctype, {key: val}, "name")
		or frappe.get_doc({"doctype": doctype, key: val, **values}).insert(ignore_permissions=True).name
	)


class TestAntMedMaterialRequest(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hosp = _ensure(
			"AntMed Hospital", "hospital_code", "_T-MR-BV", {"hospital_name": "BV Material Req"}
		)
		cls.doctor = _ensure(
			"AntMed Doctor", "doctor_code", "_T-MR-BS", {"full_name": "BS Gọi VT", "hospital": cls.hosp}
		)
		cls.item_in = _ensure("AntMed Item", "item_code", "VTYT-MR-IN", {"item_name": "Chỉ Vicryl MR"})
		cls.item_out = _ensure("AntMed Item", "item_code", "VTYT-MR-OUT", {"item_name": "VT ngoài thầu MR"})
		# HĐ hiệu lực có item_in trong quota → find_active_contract_with_item khớp.
		if not frappe.db.exists("AntMed Contract", {"contract_no": "_T-MR-CT"}):
			c = frappe.get_doc(
				{
					"doctype": "AntMed Contract",
					"contract_no": "_T-MR-CT",
					"hospital": cls.hosp,
					"signed_date": "2026-01-05",
					"status": "Hiệu lực",
					"valid_to": "2026-12-31",
					"items": [
						{
							"item": cls.item_in,
							"item_name": "Chỉ Vicryl MR",
							"uom": "Cái",
							"unit_price": 100000,
							"quota_qty": 100,
							"used_qty": 0,
							"remaining_pct": 100,
							"lock_at_100": 1,
						}
					],
				}
			)
			c.insert(ignore_permissions=True)
			c.submit()

	def test_doctypes(self):
		self.assertTrue(frappe.db.exists("DocType", "AntMed Material Request"))
		self.assertTrue(frappe.db.exists("DocType", "AntMed Material Request Item"))
		self.assertEqual(frappe.get_meta("AntMed Material Request").is_submittable, 1)

	def test_create_in_out_quota(self):
		res = customer.create_material_request(
			hospital=self.hosp,
			items=[{"item": self.item_in, "requested_qty": 5}, {"item": self.item_out, "requested_qty": 2}],
			doctor=self.doctor,
			surgery_room="PM4",
			urgency="Khẩn",
		)
		self.assertRegex(res["name"], YC_RE)
		self.assertEqual(res["status"], "Mới")
		self.assertTrue(res["needs_approval"])  # có item ngoài thầu
		mr = frappe.get_doc("AntMed Material Request", res["name"])
		by_item = {r.item: r.in_quota for r in mr.items}
		self.assertEqual(by_item[self.item_in], 1)
		self.assertEqual(by_item[self.item_out], 0)

	def test_idor_cross_hospital_blocked(self):
		"""IDOR: user bị giới hạn BV (User Permission) KHÔNG được gửi yêu cầu cho BV khác."""
		other = _ensure("AntMed Hospital", "hospital_code", "_T-MR-OTHER", {"hospital_name": "BV Khác MR"})
		email = "_t_mr_portal@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": "Portal MR",
					"send_welcome_email": 0,
					"roles": [{"role": "NV kinh doanh"}],
				}
			).insert(ignore_permissions=True)
		if not frappe.db.exists(
			"User Permission", {"user": email, "allow": "AntMed Hospital", "for_value": other}
		):
			frappe.get_doc(
				{"doctype": "User Permission", "user": email, "allow": "AntMed Hospital", "for_value": other}
			).insert(ignore_permissions=True)
		frappe.set_user(email)
		try:
			# user chỉ được phép BV 'other' → gửi cho self.hosp phải bị chặn
			with self.assertRaises(frappe.PermissionError):
				customer.create_material_request(
					hospital=self.hosp, items=[{"item": self.item_in, "requested_qty": 1}]
				)
		finally:
			frappe.set_user("Administrator")

	def test_list_and_get(self):
		name = customer.create_material_request(
			hospital=self.hosp, items=[{"item": self.item_in, "requested_qty": 3}]
		)["name"]
		res = customer.list_material_requests(hospital=self.hosp, page_length=0)
		self.assertEqual(set(res.keys()), {"data", "total_count"})
		self.assertEqual(len(res["data"]), res["total_count"])
		detail = customer.get_material_request(name)
		self.assertEqual(detail["name"], name)
		self.assertGreaterEqual(len(detail["items"]), 1)
