# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""CRM Bác sỹ — nhật ký cuộc gọi (log_call / list_call_logs) tái dùng CRM Call Log (TDD).

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_call_log
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from antmed_crm.api.antmed import doctor_care


def _ensure(doctype, key, val, values):
	return (
		frappe.db.get_value(doctype, {key: val}, "name")
		or frappe.get_doc({"doctype": doctype, key: val, **values}).insert(ignore_permissions=True).name
	)


class TestAntMedCallLog(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hosp = _ensure("AntMed Hospital", "hospital_code", "_T-CALL-BV", {"hospital_name": "BV Call"})
		cls.doctor = _ensure(
			"AntMed Doctor",
			"doctor_code",
			"_T-CALL-BS",
			{"full_name": "BS Call", "hospital": cls.hosp, "phone": "0900000001"},
		)
		cls.doctor_nophone = _ensure(
			"AntMed Doctor",
			"doctor_code",
			"_T-CALL-BS2",
			{"full_name": "BS NoPhone", "hospital": cls.hosp},
		)

	def test_log_call_creates_crm_call_log(self):
		res = doctor_care.log_call(doctor=self.doctor, outcome="Nghe máy", duration_sec=90)
		self.assertEqual(res["status"], "Completed")
		doc = frappe.get_doc("CRM Call Log", res["call_log"])
		self.assertEqual(doc.type, "Outgoing")
		self.assertEqual(doc.telephony_medium, "Manual")
		self.assertEqual(doc.reference_doctype, "AntMed Doctor")
		self.assertEqual(doc.reference_docname, self.doctor)
		self.assertEqual(doc.to, "0900000001")
		self.assertTrue(doc.id)
		self.assertEqual(int(doc.duration), 90)

	def test_outcome_maps_to_status(self):
		for outcome, status in {
			"Nghe máy": "Completed",
			"Không nghe": "No Answer",
			"Máy bận": "Busy",
			"Hộp thư": "No Answer",
		}.items():
			self.assertEqual(doctor_care.log_call(doctor=self.doctor, outcome=outcome)["status"], status)

	def test_note_creates_fcrm_note(self):
		res = doctor_care.log_call(doctor=self.doctor, outcome="Nghe máy", note="Phản hồi tốt")
		note_name = frappe.db.get_value("CRM Call Log", res["call_log"], "note")
		self.assertTrue(note_name)
		self.assertEqual(frappe.db.get_value("FCRM Note", note_name, "content"), "Phản hồi tốt")

	def test_missing_phone_throws(self):
		with self.assertRaises(frappe.ValidationError):
			doctor_care.log_call(doctor=self.doctor_nophone, outcome="Nghe máy")

	def test_invalid_outcome_throws(self):
		with self.assertRaises(frappe.ValidationError):
			doctor_care.log_call(doctor=self.doctor, outcome="XYZ")

	def test_list_call_logs_shape_and_sort(self):
		doctor_care.log_call(
			doctor=self.doctor, outcome="Nghe máy", note="N1", called_at="2026-01-01 08:00:00"
		)
		newer = doctor_care.log_call(doctor=self.doctor, outcome="Máy bận", called_at="2026-06-01 09:00:00")
		res = doctor_care.list_call_logs(doctor=self.doctor)
		self.assertGreaterEqual(res["total_count"], 2)
		row = res["data"][0]
		for k in ("name", "status", "outcome", "direction", "duration", "start_time", "caller_name"):
			self.assertIn(k, row)
		self.assertEqual(row["direction"], "Gọi đi")
		self.assertEqual(row["name"], newer["call_log"])  # newest start_time first

	def test_list_call_logs_visible_to_scoped_rep(self):
		# Admin logs a call for the doctor.
		res = doctor_care.log_call(doctor=self.doctor, outcome="Nghe máy", note="rep-visible")
		email = "_t-call-rep@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": "RepCall",
					"send_welcome_email": 0,
					"roles": [{"role": "NV kinh doanh"}],
				}
			).insert(ignore_permissions=True)
		else:
			u = frappe.get_doc("User", email)
			if "NV kinh doanh" not in [r.role for r in u.roles]:
				u.append("roles", {"role": "NV kinh doanh"})
				u.save(ignore_permissions=True)
		if not frappe.db.exists(
			"User Permission", {"user": email, "allow": "AntMed Hospital", "for_value": self.hosp}
		):
			frappe.get_doc(
				{
					"doctype": "User Permission",
					"user": email,
					"allow": "AntMed Hospital",
					"for_value": self.hosp,
				}
			).insert(ignore_permissions=True)
		frappe.set_user(email)
		try:
			out = doctor_care.list_call_logs(doctor=self.doctor)
			self.assertIn(res["call_log"], [r["name"] for r in out["data"]])
		finally:
			frappe.set_user("Administrator")

	def test_br13_fail_closed(self):
		email = "_t-call-noperm@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": "NoPermCall", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.set_user(email)
		try:
			with self.assertRaises(frappe.PermissionError):
				doctor_care.list_call_logs(doctor=self.doctor)
			with self.assertRaises(frappe.PermissionError):
				doctor_care.log_call(doctor=self.doctor, outcome="Nghe máy")
		finally:
			frappe.set_user("Administrator")
