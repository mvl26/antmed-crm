# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M05 Slice S3 (BE) — Tiệt khuẩn + BR-09: AntMed Sterilization + sterilize/mark_ready — TDD viết TRƯỚC.

Cover m05_instrument_loan.md §2 (Sterilization) + §4 (BR-09) + §5:
  test_doctype           — AntMed Sterilization tồn tại; naming AntMed-STR; result reqd.
  test_sterilize         — sterilize → tạo bản ghi + loan 'Đang xử lý/tiệt khuẩn' + Set status.
  test_br09_block        — mark_ready khi CHƯA có kết quả Pass → throw 'BR-09'.
  test_mark_ready_pass   — sterilize(Pass) → mark_ready → loan 'Đã đóng' + Set 'Sẵn sàng'.

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_sterilization
"""

import re

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from antmed_crm.api.antmed import instrument_loan

STR_NAME_RE = re.compile(r"^AntMed-STR-\d{4}-\d+")


def _mk_hospital(code, name):
	if frappe.db.exists("AntMed Hospital", code):
		return frappe.get_doc("AntMed Hospital", code)
	return frappe.get_doc(
		{"doctype": "AntMed Hospital", "hospital_code": code, "hospital_name": name}
	).insert(ignore_permissions=True)


def _mk_set(set_code):
	if frappe.db.exists("AntMed Instrument Set", set_code):
		return frappe.get_doc("AntMed Instrument Set", set_code)
	return frappe.get_doc(
		{
			"doctype": "AntMed Instrument Set",
			"set_code": set_code,
			"components": [{"component_name": "Kẹp", "qty": 1}],
		}
	).insert(ignore_permissions=True)


class TestAntMedSterilization(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hosp = _mk_hospital("_T-STR-BV", "BV Tiệt Khuẩn").name

	def _returned_loan(self, suffix):
		"""Tạo loan đi hết book→handover→return (sẵn sàng để tiệt khuẩn) trên bộ riêng."""
		s = _mk_set(f"_T-STR-SET-{suffix}").name
		name = instrument_loan.book(
			instrument_set=s,
			hospital=self.hosp,
			booked_at=str(add_to_date(now_datetime(), hours=2)),
			due_return_at=str(add_to_date(now_datetime(), hours=8)),
		)["name"]
		instrument_loan.handover(name)
		instrument_loan.receive_return(name)
		return name, s

	def test_doctype(self):
		self.assertTrue(frappe.db.exists("DocType", "AntMed Sterilization"))
		meta = frappe.get_meta("AntMed Sterilization")
		self.assertEqual(meta.get_field("result").reqd, 1)

	def test_sterilize(self):
		loan, s = self._returned_loan("STZ")
		res = instrument_loan.sterilize(loan=loan, method="Hấp", result="Pass")
		self.assertRegex(res["sterilization"], STR_NAME_RE)
		self.assertEqual(
			frappe.db.get_value("AntMed Instrument Loan", loan, "status"), "Đang xử lý/tiệt khuẩn"
		)
		self.assertEqual(
			frappe.db.get_value("AntMed Instrument Set", s, "current_status"), "Đang xử lý/tiệt khuẩn"
		)

	def test_br09_block(self):
		loan, s = self._returned_loan("BR09")
		instrument_loan.sterilize(loan=loan, method="EO", result="Fail")  # Fail → KHÔNG đủ điều kiện
		with self.assertRaises(frappe.ValidationError) as cm:
			instrument_loan.mark_ready(loan)
		self.assertIn("BR-09", str(cm.exception))

	def test_mark_ready_pass(self):
		loan, s = self._returned_loan("RDY")
		instrument_loan.sterilize(loan=loan, method="Plasma", result="Pass")
		res = instrument_loan.mark_ready(loan)
		self.assertEqual(res["set_status"], "Sẵn sàng")
		self.assertEqual(frappe.db.get_value("AntMed Instrument Loan", loan, "status"), "Đã đóng")
		self.assertEqual(frappe.db.get_value("AntMed Instrument Set", s, "current_status"), "Sẵn sàng")
