# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M07 Slice S3 (BE) — Khảo sát + Call Plan + scheduler: AntMed Satisfaction Survey/Call Plan.

Cover m07_doctor_care.md §2/§5 + scheduler (send_call_plan_today/notify_doctor_birthdays):
  test_doctypes            — Satisfaction Survey + Call Plan tồn tại.
  test_submit_survey       — tạo khảo sát hài lòng (score 1-5).
  test_call_plan_today     — plan next_visit=hôm nay → vào danh sách nhắc.
  test_doctor_birthdays    — bác sỹ sinh nhật trong 7 ngày → vào danh sách nhắc.

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_doctor_care2
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from antmed_crm.api.antmed import doctor_care


def _ensure(doctype, key, val, values):
	return (
		frappe.db.get_value(doctype, {key: val}, "name")
		or frappe.get_doc({"doctype": doctype, key: val, **values}).insert(ignore_permissions=True).name
	)


class TestAntMedDoctorCare2(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hosp = _ensure("AntMed Hospital", "hospital_code", "_T-CARE2-BV", {"hospital_name": "BV Care2"})
		cls.doctor = _ensure(
			"AntMed Doctor", "doctor_code", "_T-CARE2-BS", {"full_name": "BS Care2", "hospital": cls.hosp}
		)

	def test_doctypes(self):
		self.assertTrue(frappe.db.exists("DocType", "AntMed Satisfaction Survey"))
		self.assertTrue(frappe.db.exists("DocType", "AntMed Call Plan"))

	def test_submit_survey(self):
		res = doctor_care.submit_survey(doctor=self.doctor, score_1_5=5, comments="Rất hài lòng")
		self.assertTrue(frappe.db.exists("AntMed Satisfaction Survey", res["survey"]))
		self.assertEqual(frappe.db.get_value("AntMed Satisfaction Survey", res["survey"], "score_1_5"), 5)

	def test_call_plan_today(self):
		frappe.get_doc(
			{
				"doctype": "AntMed Call Plan",
				"doctor": self.doctor,
				"sales_rep": "Administrator",
				"next_visit": nowdate(),
			}
		).insert(ignore_permissions=True)
		res = doctor_care.send_call_plan_today()
		self.assertIn("due", res)
		self.assertIn(self.doctor, {d["doctor"] for d in res["due"]})

	def test_doctor_birthdays(self):
		# bác sỹ có sinh nhật cách hôm nay 2 ngày (bỏ qua năm)
		bday = add_days(nowdate(), 2)
		bs = _ensure(
			"AntMed Doctor",
			"doctor_code",
			"_T-CARE2-BDAY",
			{
				"full_name": "BS Sinh Nhật",
				"hospital": self.hosp,
				"birthday": f"1980-{bday[5:7]}-{bday[8:10]}",
			},
		)
		res = doctor_care.notify_doctor_birthdays(within_days=7)
		self.assertIn("upcoming", res)
		self.assertIn(bs, {d["doctor"] for d in res["upcoming"]})
