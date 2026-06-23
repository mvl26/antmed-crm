# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M05 Slice S1 (BE) — Bộ dụng cụ: AntMed Instrument Set + Component + read API — TDD viết TRƯỚC.

Cover m05_instrument_loan.md §2 (Instrument Set/Component) + §5 (list/get):
  test_doctypes_and_fields   — DocType tồn tại; Component istable; Set autoname field:set_code.
  test_set_code_unique       — set_code unique.
  test_defaults              — current_status mặc định 'Sẵn sàng'; lifetime_loans 0.
  test_list_shape            — {data,total_count}; item đúng key; count==rows.
  test_list_filter_status    — lọc theo current_status.
  test_get_set               — detail + components[]; PermissionError nếu không read.
  test_docperm_vietnamese    — role VI, KHÔNG AM System Admin.

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_instrument
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from antmed_crm.api.antmed import instrument_loan

SET_MIN_FIELDS = {
	"set_code",
	"surgery_type",
	"asset_value",
	"max_loans",
	"lifetime_loans",
	"current_status",
	"current_holder",
	"current_warehouse",
	"components",
}
COMP_FIELDS = {"component_name", "qty", "criticality"}
LIST_KEYS = {"name", "set_code", "surgery_type", "current_status", "current_holder", "lifetime_loans"}


def _mk_set(set_code, **kw):
	comps = kw.pop("components", [{"component_name": "Kẹp phẫu thuật", "qty": 2, "criticality": "Critical"}])
	doc = frappe.get_doc(
		{"doctype": "AntMed Instrument Set", "set_code": set_code, "components": comps, **kw}
	)
	doc.insert(ignore_permissions=True)
	return doc


class TestAntMedInstrumentSet(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.s1 = _mk_set("_T-SET-TIM", surgery_type="Tim mạch", asset_value=45000000).name
		cls.s2 = _mk_set("_T-SET-CTCH", surgery_type="Chấn thương", current_status="Đang sử dụng tại BV").name

	def test_doctypes_and_fields(self):
		self.assertTrue(frappe.db.exists("DocType", "AntMed Instrument Set"))
		self.assertTrue(frappe.db.exists("DocType", "AntMed Instrument Set Component"))
		self.assertEqual(frappe.get_meta("AntMed Instrument Set Component").istable, 1)
		sfields = {f.fieldname for f in frappe.get_meta("AntMed Instrument Set").fields}
		self.assertTrue(SET_MIN_FIELDS.issubset(sfields), msg=f"thiếu: {SET_MIN_FIELDS - sfields}")
		cfields = {f.fieldname for f in frappe.get_meta("AntMed Instrument Set Component").fields}
		self.assertTrue(COMP_FIELDS.issubset(cfields), msg=f"thiếu: {COMP_FIELDS - cfields}")
		self.assertEqual(self.s1, "_T-SET-TIM")  # autoname field:set_code

	def test_set_code_unique(self):
		with self.assertRaises(
			(frappe.UniqueValidationError, frappe.DuplicateEntryError, frappe.ValidationError)
		):
			frappe.get_doc({"doctype": "AntMed Instrument Set", "set_code": "_T-SET-TIM"}).insert(
				ignore_permissions=True
			)

	def test_defaults(self):
		self.assertEqual(frappe.db.get_value("AntMed Instrument Set", self.s1, "current_status"), "Sẵn sàng")
		self.assertEqual(frappe.db.get_value("AntMed Instrument Set", self.s1, "lifetime_loans"), 0)

	def test_list_shape(self):
		res = instrument_loan.list_instrument_sets(page_length=0)
		self.assertEqual(set(res.keys()), {"data", "total_count"})
		self.assertGreaterEqual(len(res["data"]), 2)
		self.assertEqual(set(res["data"][0].keys()), LIST_KEYS)
		self.assertEqual(len(res["data"]), res["total_count"])

	def test_list_filter_status(self):
		res = instrument_loan.list_instrument_sets(current_status="Đang sử dụng tại BV", page_length=0)
		names = {r["name"] for r in res["data"]}
		self.assertIn(self.s2, names)
		self.assertNotIn(self.s1, names)

	def test_get_set(self):
		res = instrument_loan.get_instrument_set(self.s1)
		self.assertEqual(res["set_code"], "_T-SET-TIM")
		self.assertEqual(res["surgery_type"], "Tim mạch")
		self.assertGreaterEqual(len(res["components"]), 1)
		self.assertIn("loans", res)
		email = "_t_set_noperm@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": "NoPermSet", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.set_user(email)
		try:
			with self.assertRaises(frappe.PermissionError):
				instrument_loan.get_instrument_set(self.s1)
		finally:
			frappe.set_user("Administrator")

	def test_docperm_vietnamese(self):
		perms = {p.role for p in frappe.get_meta("AntMed Instrument Set").permissions}
		self.assertIn("Quản lý", perms)
		self.assertIn("Thủ kho", perms)
		self.assertNotIn("AM System Admin", perms)
