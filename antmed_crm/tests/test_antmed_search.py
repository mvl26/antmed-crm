# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""Quick-search command palette — endpoint search.global_search (TDD viết TRƯỚC).

global_search(query, limit) trả RAW dict {"hospitals": [...], "contracts": [...], "instrument_sets": [...], "deliveries": [...]}.
Tái dùng list_hospitals/list_contracts/list_instrument_sets/list_deliveries → kế thừa permission + data-scope (BR-13).

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_search
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from antmed_crm.api.antmed import delivery
from antmed_crm.api.antmed import search

PREFIX = "_QS"  # tiền tố seed riêng test này (dễ dọn, không đụng data khác)


def _mk_hospital(code, name):
	if frappe.db.exists("AntMed Hospital", code):
		return frappe.get_doc("AntMed Hospital", code)
	doc = frappe.get_doc({"doctype": "AntMed Hospital", "hospital_code": code, "hospital_name": name})
	doc.insert(ignore_permissions=True)
	return doc


def _mk_contract(contract_no, hospital):
	if frappe.db.exists("AntMed Contract", {"contract_no": contract_no}):
		return frappe.get_doc("AntMed Contract", {"contract_no": contract_no})
	doc = frappe.get_doc(
		{
			"doctype": "AntMed Contract",
			"contract_no": contract_no,
			"hospital": hospital,
			"signed_date": "2026-01-05",
			"valid_from": "2026-01-05",
			"valid_to": "2026-12-31",
			"status": "Hiệu lực",
			"total_value": 1000000000,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


def _mk_item(code, name):
	if frappe.db.exists("AntMed Item", code):
		return frappe.get_doc("AntMed Item", code)
	return frappe.get_doc({"doctype": "AntMed Item", "item_code": code, "item_name": name}).insert(
		ignore_permissions=True
	)


def _mk_instrument_set(set_code):
	if frappe.db.exists("AntMed Instrument Set", set_code):
		return frappe.get_doc("AntMed Instrument Set", set_code)
	return frappe.get_doc(
		{
			"doctype": "AntMed Instrument Set",
			"set_code": set_code,
			"components": [{"component_name": "Kẹp", "qty": 1}],
		}
	).insert(ignore_permissions=True)


class TestGlobalSearch(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hosp = _mk_hospital(f"{PREFIX}-CR", f"{PREFIX} Benh vien Cho Ray")
		cls.contract = _mk_contract(f"{PREFIX}-HD-001", cls.hosp.name)
		cls.iset = _mk_instrument_set(f"{PREFIX}-SET-1")
		cls.item = _mk_item(f"{PREFIX}-VTYT", f"{PREFIX} VT giao")
		cls.delivery_name = delivery.create_request(
			hospital=cls.hosp.name,
			surgery_datetime=str(add_to_date(now_datetime(), hours=4)),
			items=[{"item": cls.item.name, "requested_qty": 1}],
		)["name"]

	def test_empty_query_returns_empty_groups(self):
		empty = {"hospitals": [], "contracts": [], "instrument_sets": [], "deliveries": []}
		self.assertEqual(search.global_search(query=""), empty)
		self.assertEqual(search.global_search(query="   "), empty)

	def test_shape_has_all_groups(self):
		res = search.global_search(query=PREFIX)
		for key in ("hospitals", "contracts", "instrument_sets", "deliveries"):
			self.assertIn(key, res)
			self.assertIsInstance(res[key], list)

	def test_matches_hospital_by_name(self):
		res = search.global_search(query="Cho Ray")
		names = [h["name"] for h in res["hospitals"]]
		self.assertIn(self.hosp.name, names)

	def test_matches_contract_by_no(self):
		res = search.global_search(query=f"{PREFIX}-HD")
		nos = [c["contract_no"] for c in res["contracts"]]
		self.assertIn(f"{PREFIX}-HD-001", nos)

	def test_matches_instrument_set_by_code(self):
		res = search.global_search(query=f"{PREFIX}-SET")
		codes = [s["set_code"] for s in res["instrument_sets"]]
		self.assertIn(f"{PREFIX}-SET-1", codes)

	def test_matches_delivery_by_name(self):
		res = search.global_search(query=self.delivery_name)
		names = [d["name"] for d in res["deliveries"]]
		self.assertIn(self.delivery_name, names)

	def test_limit_is_honored(self):
		res = search.global_search(query=PREFIX, limit=1)
		self.assertLessEqual(len(res["hospitals"]), 1)
		self.assertLessEqual(len(res["contracts"]), 1)
		self.assertLessEqual(len(res["instrument_sets"]), 1)
		self.assertLessEqual(len(res["deliveries"]), 1)

	def test_limit_clamped_when_invalid(self):
		# limit không hợp lệ → fallback an toàn (5), KHÔNG raise
		res = search.global_search(query=PREFIX, limit="abc")
		self.assertIsInstance(res["hospitals"], list)
		self.assertIsInstance(res["contracts"], list)
		self.assertIsInstance(res["instrument_sets"], list)
		self.assertIsInstance(res["deliveries"], list)
		self.assertLessEqual(len(res["hospitals"]), 5)
		self.assertLessEqual(len(res["contracts"]), 5)
		self.assertLessEqual(len(res["instrument_sets"]), 5)
		self.assertLessEqual(len(res["deliveries"]), 5)
