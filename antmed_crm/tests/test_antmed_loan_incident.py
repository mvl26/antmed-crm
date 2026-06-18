# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M05 Slice S4 (BE) — Sự cố bộ mượn + nhắc quá hạn: AntMed Loan Incident + report_incident + scheduler.

Cover m05_instrument_loan.md §2 (Loan Incident) + §4 + scheduler check_overdue_loans:
  test_doctype             — AntMed Loan Incident tồn tại, naming AntMed-INC.
  test_report_missing      — báo Missing → incident + loan 'Sự cố' + Set 'Mất'.
  test_report_damaged      — báo Damaged → Set 'Hỏng'.
  test_check_overdue_loans — lượt quá hạn (due_return_at < now, đang ở BV) → vào danh sách quá hạn.

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_loan_incident
"""

import re

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from antmed_crm.api.antmed import instrument_loan

INC_NAME_RE = re.compile(r"^AntMed-INC-\d{4}-\d+")


def _mk_hospital(code, name):
	return frappe.db.get_value("AntMed Hospital", code, "name") or frappe.get_doc(
		{"doctype": "AntMed Hospital", "hospital_code": code, "hospital_name": name}
	).insert(ignore_permissions=True).name


def _mk_set(set_code):
	return frappe.db.get_value("AntMed Instrument Set", set_code, "name") or frappe.get_doc(
		{"doctype": "AntMed Instrument Set", "set_code": set_code, "components": [{"component_name": "Kẹp", "qty": 1}]}
	).insert(ignore_permissions=True).name


class TestAntMedLoanIncident(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hosp = _mk_hospital("_T-INC-BV", "BV Sự Cố")

	def _active_loan(self, suffix):
		s = _mk_set(f"_T-INC-SET-{suffix}")
		loan = instrument_loan.book(
			instrument_set=s,
			hospital=self.hosp,
			booked_at=str(add_to_date(now_datetime(), hours=2)),
			due_return_at=str(add_to_date(now_datetime(), hours=8)),
		)["name"]
		instrument_loan.handover(loan)
		return loan, s

	def test_doctype(self):
		self.assertTrue(frappe.db.exists("DocType", "AntMed Loan Incident"))

	def test_report_missing(self):
		loan, s = self._active_loan("MISS")
		res = instrument_loan.report_incident(loan=loan, incident_type="Missing", value_estimated=45000000)
		self.assertRegex(res["incident"], INC_NAME_RE)
		self.assertEqual(frappe.db.get_value("AntMed Instrument Loan", loan, "status"), "Sự cố")
		self.assertEqual(frappe.db.get_value("AntMed Instrument Set", s, "current_status"), "Mất")

	def test_report_damaged(self):
		loan, s = self._active_loan("DMG")
		instrument_loan.report_incident(loan=loan, incident_type="Damaged")
		self.assertEqual(frappe.db.get_value("AntMed Instrument Set", s, "current_status"), "Hỏng")

	def test_check_overdue_loans(self):
		loan, s = self._active_loan("OVD")
		# đẩy due_return_at về quá khứ → quá hạn
		frappe.db.set_value("AntMed Instrument Loan", loan, "due_return_at", add_to_date(now_datetime(), hours=-2))
		res = instrument_loan.check_overdue_loans()
		self.assertIn("overdue", res)
		self.assertIn(loan, res["overdue"])
