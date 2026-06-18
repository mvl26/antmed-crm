# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M07 Slice S1 (BE) — CSKH bác sỹ: AntMed Doctor Visit + Care Note + check_in/save_care_note.

Cover m07_doctor_care.md §2 (Visit/Care Note) + §5 (list/get/check_in/save_care_note):
  test_doctypes            — Doctor Visit submittable + naming AM-VISIT; Care Note naming AM-NOTE.
  test_check_in            — check_in → visit 'Đã check-in' + checked_in_at + GPS.
  test_save_care_note      — tạo Care Note gắn bác sỹ/visit.
  test_list_and_get_visit  — list_visits {data,total_count} count==rows; get_visit + notes; permission.
  test_list_care_notes     — list_care_notes theo bác sỹ.

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_doctor_visit
"""

import re

import frappe
from frappe.tests.utils import FrappeTestCase

from antmed_crm.api.antmed import doctor_care

VISIT_RE = re.compile(r"^AM-VISIT-\d{4}-\d+")


def _ensure(doctype, key, val, values):
	return frappe.db.get_value(doctype, {key: val}, "name") or frappe.get_doc({"doctype": doctype, key: val, **values}).insert(ignore_permissions=True).name


class TestAntMedDoctorVisit(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hosp = _ensure("AntMed Hospital", "hospital_code", "_T-VIS-BV", {"hospital_name": "BV Visit"})
		cls.doctor = _ensure("AntMed Doctor", "doctor_code", "_T-VIS-BS", {"full_name": "BS Thăm Khám", "hospital": cls.hosp})

	def test_doctypes(self):
		self.assertTrue(frappe.db.exists("DocType", "AntMed Doctor Visit"))
		self.assertTrue(frappe.db.exists("DocType", "AntMed Care Note"))
		self.assertEqual(frappe.get_meta("AntMed Doctor Visit").is_submittable, 1)

	def test_check_in(self):
		res = doctor_care.check_in(doctor=self.doctor, hospital=self.hosp, gps_lat="10.77", gps_lng="106.7", topic="Giới thiệu stent mới")
		self.assertRegex(res["visit"], VISIT_RE)
		self.assertEqual(res["status"], "Đã check-in")
		self.assertIsNotNone(frappe.db.get_value("AntMed Doctor Visit", res["visit"], "checked_in_at"))
		self.assertAlmostEqual(float(frappe.db.get_value("AntMed Doctor Visit", res["visit"], "gps_lat")), 10.77, places=2)

	def test_save_care_note(self):
		v = doctor_care.check_in(doctor=self.doctor, hospital=self.hosp)["visit"]
		res = doctor_care.save_care_note(doctor=self.doctor, content="BS quan tâm sản phẩm A", visit=v, category="Chăm sóc")
		self.assertTrue(frappe.db.exists("AntMed Care Note", res["note"]))
		self.assertEqual(frappe.db.get_value("AntMed Care Note", res["note"], "doctor"), self.doctor)

	def test_list_and_get_visit(self):
		v = doctor_care.check_in(doctor=self.doctor, hospital=self.hosp)["visit"]
		res = doctor_care.list_visits(page_length=0)
		self.assertEqual(set(res.keys()), {"data", "total_count"})
		self.assertEqual(len(res["data"]), res["total_count"])
		detail = doctor_care.get_visit(v)
		self.assertEqual(detail["name"], v)
		self.assertIn("care_notes", detail)
		email = "_t_vis_noperm@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc({"doctype": "User", "email": email, "first_name": "NoPermVis", "send_welcome_email": 0}).insert(ignore_permissions=True)
		frappe.set_user(email)
		try:
			with self.assertRaises(frappe.PermissionError):
				doctor_care.get_visit(v)
		finally:
			frappe.set_user("Administrator")

	def test_list_care_notes(self):
		v = doctor_care.check_in(doctor=self.doctor, hospital=self.hosp)["visit"]
		doctor_care.save_care_note(doctor=self.doctor, content="Note 1", visit=v)
		res = doctor_care.list_care_notes(doctor=self.doctor, page_length=0)
		self.assertEqual(len(res["data"]), res["total_count"])
		self.assertGreaterEqual(res["total_count"], 1)
