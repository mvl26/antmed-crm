# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M08 Slice S1 (BE) — Gói thầu: AntMed Tender + create/get/list/set_result.

Cover m08_pipeline.md §2 (Tender) + §4 (BR-M08-01/02) + §5:
  test_doctype             — AntMed Tender submittable; naming AM-TND.
  test_create_tender       — create → status 'Tiếp cận'.
  test_tender_no_unique     — BR-M08-01: trùng tender_no → raise.
  test_set_result_requires_decision — BR-M08-02: 'Trúng' thiếu decision_no → throw; có → 'Trúng'.
  test_list_and_get        — list_tenders count==rows; get_tender + hospital_name + permission.

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_tender
"""

import re

import frappe
from frappe.tests.utils import FrappeTestCase

from antmed_crm.api.antmed import pipeline

TND_RE = re.compile(r"^AM-TND-\d{4}-\d+")


def _ensure(doctype, key, val, values):
	return (
		frappe.db.get_value(doctype, {key: val}, "name")
		or frappe.get_doc({"doctype": doctype, key: val, **values}).insert(ignore_permissions=True).name
	)


class TestAntMedTender(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hosp = _ensure("AntMed Hospital", "hospital_code", "_T-TND-BV", {"hospital_name": "BV Thầu"})

	def test_doctype(self):
		self.assertTrue(frappe.db.exists("DocType", "AntMed Tender"))
		self.assertEqual(frappe.get_meta("AntMed Tender").is_submittable, 1)

	def test_create_tender(self):
		res = pipeline.create_tender(
			tender_no="_T-TND-001",
			tender_name="Gói thầu VTYT 2026",
			hospital=self.hosp,
			estimated_value=5000000000,
		)
		self.assertRegex(res["name"], TND_RE)
		self.assertEqual(frappe.db.get_value("AntMed Tender", res["name"], "status"), "Tiếp cận")

	def test_tender_no_unique(self):
		pipeline.create_tender(tender_no="_T-TND-DUP", tender_name="A", hospital=self.hosp)
		with self.assertRaises(
			(frappe.UniqueValidationError, frappe.DuplicateEntryError, frappe.ValidationError)
		):
			pipeline.create_tender(tender_no="_T-TND-DUP", tender_name="B", hospital=self.hosp)

	def test_set_result_requires_decision(self):
		t = pipeline.create_tender(tender_no="_T-TND-RES", tender_name="C", hospital=self.hosp)["name"]
		with self.assertRaises(frappe.ValidationError) as cm:
			pipeline.set_tender_result(t, result="Trúng")  # thiếu decision_no
		self.assertIn("BR-M08-02", str(cm.exception))
		pipeline.set_tender_result(t, result="Trúng", decision_no="QĐ-123/2026")
		self.assertEqual(frappe.db.get_value("AntMed Tender", t, "status"), "Trúng")

	def test_list_and_get(self):
		t = pipeline.create_tender(tender_no="_T-TND-LIST", tender_name="D", hospital=self.hosp)["name"]
		res = pipeline.list_tenders(page_length=0)
		self.assertEqual(set(res.keys()), {"data", "total_count"})
		self.assertEqual(len(res["data"]), res["total_count"])
		detail = pipeline.get_tender(t)
		self.assertEqual(detail["name"], t)
		self.assertEqual(detail["hospital_name"], "BV Thầu")
		email = "_t_tnd_noperm@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": "NoPermTnd", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.set_user(email)
		try:
			with self.assertRaises(frappe.PermissionError):
				pipeline.get_tender(t)
		finally:
			frappe.set_user("Administrator")
