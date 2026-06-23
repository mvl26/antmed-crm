# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M07 Slice S2 (BE) — Quà tặng bác sỹ + BR-11 (anti-bribery): AntMed Doctor Gift.

Cover m07_doctor_care.md §2 (Doctor Gift) + §4 (BR-11) + §5 (create_gift/list_gifts):
  test_doctype          — AntMed Doctor Gift tồn tại, naming AM-GIFT.
  test_br11_requires_approver — create_gift thiếu approved_by → throw 'BR-11'.
  test_create_gift_ok   — có approved_by → tạo được.
  test_list_gifts       — list_gifts theo bác sỹ; count==rows.

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_doctor_gift
"""

import re

import frappe
from frappe.tests.utils import FrappeTestCase

from antmed_crm.api.antmed import doctor_care

GIFT_RE = re.compile(r"^AM-GIFT-\d{4}-\d+")


def _ensure(doctype, key, val, values):
	return (
		frappe.db.get_value(doctype, {key: val}, "name")
		or frappe.get_doc({"doctype": doctype, key: val, **values}).insert(ignore_permissions=True).name
	)


class TestAntMedDoctorGift(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hosp = _ensure("AntMed Hospital", "hospital_code", "_T-GIFT-BV", {"hospital_name": "BV Gift"})
		cls.doctor = _ensure(
			"AntMed Doctor", "doctor_code", "_T-GIFT-BS", {"full_name": "BS Quà", "hospital": cls.hosp}
		)
		cls.approver = _ensure(
			"User", "email", "_t_gift_mgr@example.com", {"first_name": "Mgr Gift", "send_welcome_email": 0}
		)

	def test_doctype(self):
		self.assertTrue(frappe.db.exists("DocType", "AntMed Doctor Gift"))

	def test_br11_requires_approver(self):
		with self.assertRaises(frappe.ValidationError) as cm:
			doctor_care.create_gift(doctor=self.doctor, item_or_text="Giỏ quà Tết", value_vnd=2000000)
		self.assertIn("BR-11", str(cm.exception))

	def test_create_gift_ok(self):
		res = doctor_care.create_gift(
			doctor=self.doctor,
			item_or_text="Sách chuyên môn",
			value_vnd=500000,
			approved_by=self.approver,
			purpose="Tri ân hội thảo",
		)
		self.assertRegex(res["gift"], GIFT_RE)
		self.assertEqual(frappe.db.get_value("AntMed Doctor Gift", res["gift"], "approved_by"), self.approver)

	def test_list_gifts(self):
		doctor_care.create_gift(
			doctor=self.doctor, item_or_text="Hoa", value_vnd=300000, approved_by=self.approver
		)
		res = doctor_care.list_gifts(doctor=self.doctor, page_length=0)
		self.assertEqual(set(res.keys()), {"data", "total_count"})
		self.assertEqual(len(res["data"]), res["total_count"])
		self.assertGreaterEqual(res["total_count"], 1)
