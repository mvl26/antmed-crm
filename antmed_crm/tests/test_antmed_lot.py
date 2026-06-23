# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M03 Slice A2 (BE) — Catalog CO/CQ: AntMed Supplier + AntMed Lot + AntMed Certificate — TDD viết TRƯỚC.

Cover m03_inventory.md §2 (Supplier/Lot/Certificate) + §5 (list_lots) + get_item.lots wiring:
  test_doctypes_and_fields    — 3 DocType tồn tại + field tối thiểu + autoname tự nhiên.
  test_lot_unique_and_expiry  — lot_no unique; expiry_date reqd.
  test_lot_recall_default     — recall_status default 'Bình thường'.
  test_list_lots_shape        — {data,total_count}; item đúng key; count==rows.
  test_list_lots_filter_item  — lọc theo item.
  test_get_item_lots_wired    — get_item(item) trả lots[] thực (đã wire từ AntMed Lot).
  test_docperm_vietnamese     — role VI, KHÔNG AM System Admin.

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_lot
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from antmed_crm.api.antmed import inventory

SUPPLIER_FIELDS = {"supplier_code", "supplier_name", "tax_code", "disabled"}
CERT_FIELDS = {"cert_no", "cert_type", "item", "lot", "issued_date", "expires_at", "hash_sha256"}
LOT_FIELDS = {"lot_no", "item", "supplier", "mfg_date", "expiry_date", "co_cert", "cq_cert", "recall_status"}
LOT_LIST_KEYS = {"name", "lot_no", "item", "item_name", "supplier", "expiry_date", "recall_status"}


def _mk_item(item_code, item_name, **kw):
	if frappe.db.exists("AntMed Item", item_code):
		return frappe.get_doc("AntMed Item", item_code)
	return frappe.get_doc(
		{"doctype": "AntMed Item", "item_code": item_code, "item_name": item_name, **kw}
	).insert(ignore_permissions=True)


def _mk_supplier(code, name):
	if frappe.db.exists("AntMed Supplier", code):
		return frappe.get_doc("AntMed Supplier", code)
	return frappe.get_doc(
		{"doctype": "AntMed Supplier", "supplier_code": code, "supplier_name": name}
	).insert(ignore_permissions=True)


def _mk_lot(lot_no, item, **kw):
	return frappe.get_doc(
		{
			"doctype": "AntMed Lot",
			"lot_no": lot_no,
			"item": item,
			"expiry_date": kw.pop("expiry_date", "2027-12-31"),
			**kw,
		}
	).insert(ignore_permissions=True)


class TestAntMedLot(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.item = _mk_item("_T-LOTITEM-STENT", "Stent test lot", classification="Loại D").name
		cls.item2 = _mk_item("_T-LOTITEM-GAC", "Gạc test lot").name
		cls.sup = _mk_supplier("_T-SUP-ABBOTT", "Abbott VN").name
		cls.lot1 = _mk_lot("_T-LOT-001", cls.item, supplier=cls.sup, expiry_date="2027-06-30").name
		cls.lot2 = _mk_lot("_T-LOT-002", cls.item2, expiry_date="2027-09-30").name

	def test_doctypes_and_fields(self):
		for dt in ("AntMed Supplier", "AntMed Lot", "AntMed Certificate"):
			self.assertTrue(frappe.db.exists("DocType", dt), msg=f"thiếu DocType {dt}")
		self.assertTrue(
			SUPPLIER_FIELDS.issubset({f.fieldname for f in frappe.get_meta("AntMed Supplier").fields})
		)
		self.assertTrue(
			CERT_FIELDS.issubset({f.fieldname for f in frappe.get_meta("AntMed Certificate").fields})
		)
		self.assertTrue(LOT_FIELDS.issubset({f.fieldname for f in frappe.get_meta("AntMed Lot").fields}))
		self.assertEqual(self.lot1, "_T-LOT-001")  # autoname field:lot_no

	def test_lot_unique_and_expiry(self):
		with self.assertRaises(
			(frappe.UniqueValidationError, frappe.DuplicateEntryError, frappe.ValidationError)
		):
			frappe.get_doc(
				{
					"doctype": "AntMed Lot",
					"lot_no": "_T-LOT-001",
					"item": self.item,
					"expiry_date": "2028-01-01",
				}
			).insert(ignore_permissions=True)
		# expiry_date reqd
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({"doctype": "AntMed Lot", "lot_no": "_T-LOT-NOEXP", "item": self.item}).insert(
				ignore_permissions=True
			)

	def test_lot_recall_default(self):
		self.assertEqual(frappe.db.get_value("AntMed Lot", self.lot1, "recall_status"), "Bình thường")

	def test_list_lots_shape(self):
		res = inventory.list_lots(page_length=0)
		self.assertEqual(set(res.keys()), {"data", "total_count"})
		self.assertGreaterEqual(len(res["data"]), 2)
		self.assertEqual(set(res["data"][0].keys()), LOT_LIST_KEYS)
		self.assertEqual(len(res["data"]), res["total_count"])

	def test_list_lots_filter_item(self):
		res = inventory.list_lots(item=self.item, page_length=0)
		names = {r["name"] for r in res["data"]}
		self.assertIn(self.lot1, names)
		self.assertNotIn(self.lot2, names)
		self.assertEqual(len(res["data"]), res["total_count"])
		# item_name resolve qua Link (dotted-fetch)
		row = next(r for r in res["data"] if r["name"] == self.lot1)
		self.assertEqual(row["item_name"], "Stent test lot")

	def test_get_item_lots_wired(self):
		res = inventory.get_item(self.item)
		self.assertIn("lots", res)
		lot_nos = {l["lot_no"] for l in res["lots"]}
		self.assertIn("_T-LOT-001", lot_nos)

	def test_docperm_vietnamese(self):
		perms = {p.role for p in frappe.get_meta("AntMed Lot").permissions}
		self.assertIn("Quản lý", perms)
		self.assertIn("Thủ kho", perms)
		self.assertNotIn("AM System Admin", perms)
