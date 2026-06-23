# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M03 Slice A1 (BE) — DocType AntMed Warehouse (kho 3 cấp) + API list_warehouses — TDD viết TRƯỚC.

Cover m03_inventory.md §2 (AntMed Warehouse) + §4 (ràng buộc kho 3 cấp, BR native) + §5:
  test_warehouse_doctype_and_fields — DocType tồn tại; field tối thiểu; autoname field:warehouse_name.
  test_3tier_personal_requires_employee — type 'Cá nhân NV' thiếu employee → raise; có → ok.
  test_3tier_consignment_requires_hospital — type 'Ký gửi BV' thiếu hospital → raise; có → ok.
  test_3tier_central_ok — type 'Tổng' không cần employee/hospital → ok.
  test_list_warehouses_shape — {data,total_count}; item đúng 6 key; count==rows.
  test_list_warehouses_filter_type — lọc theo warehouse_type.
  test_docperm_vietnamese — DocPerm role VI (Quản lý/Thủ kho), KHÔNG AM System Admin.

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_warehouse
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from antmed_crm.api.antmed import inventory

WH_MIN_FIELDS = {"warehouse_name", "warehouse_type", "employee", "hospital", "parent_warehouse", "disabled"}
WH_LIST_KEYS = {"name", "warehouse_name", "warehouse_type", "employee", "hospital", "disabled"}


def _mk_hospital(code, name):
	if frappe.db.exists("AntMed Hospital", code):
		return frappe.get_doc("AntMed Hospital", code)
	doc = frappe.get_doc({"doctype": "AntMed Hospital", "hospital_code": code, "hospital_name": name})
	doc.insert(ignore_permissions=True)
	return doc


def _mk_warehouse(warehouse_name, warehouse_type, **kw):
	doc = frappe.get_doc(
		{
			"doctype": "AntMed Warehouse",
			"warehouse_name": warehouse_name,
			"warehouse_type": warehouse_type,
			**kw,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


class TestAntMedWarehouse(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hosp = _mk_hospital("_T-HOSP-WH", "BV Warehouse").name
		cls.wh_central = _mk_warehouse("_T-WH-TONG", "Tổng").name
		cls.wh_consign = _mk_warehouse("_T-WH-KYGUI", "Ký gửi BV", hospital=cls.hosp).name

	def test_warehouse_doctype_and_fields(self):
		self.assertTrue(frappe.db.exists("DocType", "AntMed Warehouse"))
		meta = frappe.get_meta("AntMed Warehouse")
		fields = {f.fieldname for f in meta.fields}
		self.assertTrue(WH_MIN_FIELDS.issubset(fields), msg=f"thiếu field: {WH_MIN_FIELDS - fields}")
		self.assertEqual(self.wh_central, "_T-WH-TONG")  # autoname field:warehouse_name

	def test_3tier_personal_requires_employee(self):
		with self.assertRaises(frappe.ValidationError):
			_mk_warehouse("_T-WH-CANHAN-BAD", "Cá nhân NV")  # thiếu employee
		ok = _mk_warehouse("_T-WH-CANHAN-OK", "Cá nhân NV", employee="Administrator")
		self.assertEqual(ok.warehouse_type, "Cá nhân NV")

	def test_3tier_consignment_requires_hospital(self):
		with self.assertRaises(frappe.ValidationError):
			_mk_warehouse("_T-WH-KYGUI-BAD", "Ký gửi BV")  # thiếu hospital

	def test_3tier_central_ok(self):
		w = _mk_warehouse("_T-WH-TONG-2", "Tổng")  # không cần employee/hospital
		self.assertEqual(w.warehouse_type, "Tổng")

	def test_list_warehouses_shape(self):
		res = inventory.list_warehouses(page_length=0)
		self.assertEqual(set(res.keys()), {"data", "total_count"})
		self.assertGreaterEqual(len(res["data"]), 2)
		self.assertEqual(set(res["data"][0].keys()), WH_LIST_KEYS)
		self.assertEqual(len(res["data"]), res["total_count"])

	def test_list_warehouses_filter_type(self):
		res = inventory.list_warehouses(warehouse_type="Ký gửi BV", page_length=0)
		names = {r["name"] for r in res["data"]}
		self.assertIn(self.wh_consign, names)
		self.assertNotIn(self.wh_central, names)
		self.assertEqual(len(res["data"]), res["total_count"])

	def test_docperm_vietnamese(self):
		perms = {p.role for p in frappe.get_meta("AntMed Warehouse").permissions}
		self.assertIn("Quản lý", perms)
		self.assertIn("Thủ kho", perms)
		self.assertNotIn("AM System Admin", perms)
