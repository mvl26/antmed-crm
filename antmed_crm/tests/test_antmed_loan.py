# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M05 Slice S2 (BE) — Vòng đời mượn bộ dụng cụ: AntMed Instrument Loan + book/handover/return.

Cover m05_instrument_loan.md §2 (Loan) + §3 (7-state) + §4 (BR-05) + §5:
  test_doctypes_and_naming  — Loan tồn tại, submittable, naming AntMed-LN; Checklist Item istable.
  test_book                 — book → loan 'Đã đặt' + Set.current_status 'Đã đặt'.
  test_br05_overlap         — book trùng lịch cùng bộ → throw 'BR-05'.
  test_handover             — handover → 'Đang sử dụng tại BV' + Set status + lifetime_loans+1 + docstatus 1.
  test_receive_return       — return → 'Đã trả về NV KD' + returned_at + Set status.
  test_list_and_get_loan    — list_loans {data,total_count} count==rows; get_loan detail + permission.

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_loan
"""

import re

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from antmed_crm.api.antmed import instrument_loan

LN_NAME_RE = re.compile(r"^AntMed-LN-\d{4}-\d+")


def _mk_hospital(code, name):
	if frappe.db.exists("AntMed Hospital", code):
		return frappe.get_doc("AntMed Hospital", code)
	return frappe.get_doc({"doctype": "AntMed Hospital", "hospital_code": code, "hospital_name": name}).insert(
		ignore_permissions=True
	)


def _mk_set(set_code):
	if frappe.db.exists("AntMed Instrument Set", set_code):
		return frappe.get_doc("AntMed Instrument Set", set_code)
	return frappe.get_doc(
		{"doctype": "AntMed Instrument Set", "set_code": set_code, "surgery_type": "Tim mạch", "components": [{"component_name": "Kẹp", "qty": 1}]}
	).insert(ignore_permissions=True)


class TestAntMedLoan(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hosp = _mk_hospital("_T-LN-BV", "BV Mượn Bộ").name

	def _fresh_set(self, suffix):
		return _mk_set(f"_T-LN-SET-{suffix}").name

	def _book(self, set_name, hours_from=2, hours_to=8):
		return instrument_loan.book(
			instrument_set=set_name,
			hospital=self.hosp,
			booked_at=str(add_to_date(now_datetime(), hours=hours_from)),
			due_return_at=str(add_to_date(now_datetime(), hours=hours_to)),
		)["name"]

	def test_doctypes_and_naming(self):
		self.assertTrue(frappe.db.exists("DocType", "AntMed Instrument Loan"))
		self.assertTrue(frappe.db.exists("DocType", "AntMed Loan Checklist Item"))
		self.assertEqual(frappe.get_meta("AntMed Instrument Loan").is_submittable, 1)
		self.assertEqual(frappe.get_meta("AntMed Loan Checklist Item").istable, 1)
		name = self._book(self._fresh_set("NAME"))
		self.assertRegex(name, LN_NAME_RE)

	def test_book(self):
		s = self._fresh_set("BOOK")
		name = self._book(s)
		self.assertEqual(frappe.db.get_value("AntMed Instrument Loan", name, "status"), "Đã đặt")
		self.assertEqual(frappe.db.get_value("AntMed Instrument Set", s, "current_status"), "Đã đặt")

	def test_br05_overlap(self):
		s = self._fresh_set("OVERLAP")
		self._book(s, 2, 8)
		with self.assertRaises(frappe.ValidationError) as cm:
			self._book(s, 4, 10)  # trùng khoảng [2,8]
		self.assertIn("BR-05", str(cm.exception))

	def test_handover(self):
		s = self._fresh_set("HO")
		name = self._book(s)
		res = instrument_loan.handover(name)
		self.assertEqual(res["status"], "Đang sử dụng tại BV")
		self.assertEqual(frappe.db.get_value("AntMed Instrument Set", s, "current_status"), "Đang sử dụng tại BV")
		self.assertEqual(frappe.db.get_value("AntMed Instrument Set", s, "lifetime_loans"), 1)
		self.assertEqual(frappe.db.get_value("AntMed Instrument Loan", name, "docstatus"), 1)
		self.assertIsNotNone(frappe.db.get_value("AntMed Instrument Loan", name, "loaned_at"))

	def test_receive_return(self):
		s = self._fresh_set("RET")
		name = self._book(s)
		instrument_loan.handover(name)
		res = instrument_loan.receive_return(name)
		self.assertEqual(res["status"], "Đã trả về NV KD")
		self.assertIsNotNone(frappe.db.get_value("AntMed Instrument Loan", name, "returned_at"))
		self.assertEqual(frappe.db.get_value("AntMed Instrument Set", s, "current_status"), "Đã trả về NV KD")

	def test_list_and_get_loan(self):
		s = self._fresh_set("LIST")
		name = self._book(s)
		res = instrument_loan.list_loans(page_length=0)
		self.assertEqual(set(res.keys()), {"data", "total_count"})
		self.assertEqual(len(res["data"]), res["total_count"])
		detail = instrument_loan.get_loan(name)
		self.assertEqual(detail["name"], name)
		self.assertEqual(detail["instrument_set"], s)
		# permission guard
		email = "_t_ln_noperm@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc({"doctype": "User", "email": email, "first_name": "NoPermLN", "send_welcome_email": 0}).insert(
				ignore_permissions=True
			)
		frappe.set_user(email)
		try:
			with self.assertRaises(frappe.PermissionError):
				instrument_loan.get_loan(name)
		finally:
			frappe.set_user("Administrator")


class TestAntMedInstrumentBoard(FrappeTestCase):
	"""M05 I1/C3 — board() (KPI+grid+tần suất) + save_checklist() (C3)."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hosp = _mk_hospital("_T-BD-BV", "BV Board").name

	def test_board_shape(self):
		b = instrument_loan.board()
		self.assertEqual(set(b.keys()), {"kpis", "sets", "frequency"})
		self.assertEqual(set(b["kpis"].keys()), {"total", "in_circulation", "ready", "issue"})
		self.assertIsInstance(b["sets"], list)
		self.assertIsInstance(b["frequency"], list)
		# KPI 'total' = toàn fleet (admin context).
		self.assertEqual(b["kpis"]["total"], len(frappe.get_all("AntMed Instrument Set", pluck="name")))

	def test_board_card_enrichment(self):
		s = _mk_set("_T-BD-SET").name
		b = instrument_loan.board(search="_T-BD-SET")
		row = next((r for r in b["sets"] if r["name"] == s), None)
		self.assertIsNotNone(row)
		for k in ("set_code", "surgery_type", "current_status", "item_count", "is_overdue", "hospital_name"):
			self.assertIn(k, row)
		self.assertEqual(row["item_count"], 1)  # _mk_set thêm đúng 1 component "Kẹp"

	def test_save_checklist_persist_then_lock(self):
		import json

		s = _mk_set("_T-BD-CL").name
		loan = instrument_loan.book(
			instrument_set=s,
			hospital=self.hosp,
			booked_at=str(add_to_date(now_datetime(), hours=2)),
			due_return_at=str(add_to_date(now_datetime(), hours=8)),
		)["name"]
		# book() sinh handover_checklist từ components → có "Kẹp".
		res = instrument_loan.save_checklist(
			loan, kind="handover", items_json=json.dumps([{"component_name": "Kẹp", "condition": "Damaged"}])
		)
		self.assertEqual(res["name"], loan)
		detail = instrument_loan.get_loan(loan)
		row = next((c for c in detail["handover_checklist"] if c["component_name"] == "Kẹp"), None)
		self.assertIsNotNone(row)
		self.assertEqual(row["condition"], "Damaged")
		# Sau handover (submit) → khoá, save_checklist throw.
		instrument_loan.handover(loan)
		with self.assertRaises(frappe.ValidationError):
			instrument_loan.save_checklist(
				loan, kind="handover", items_json=json.dumps([{"component_name": "Kẹp", "condition": "OK"}])
			)
