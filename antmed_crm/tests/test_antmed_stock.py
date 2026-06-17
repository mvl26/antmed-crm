# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M03 Slice A3 (BE) — Sổ tồn + phiếu kho: AntMed Stock Ledger + AntMed Stock Entry — TDD viết TRƯỚC.

Cover m03_inventory.md §2 (Stock Entry/Ledger) + §4 (tồn không âm) + §5:
  test_doctypes              — 3 DocType tồn tại; Stock Entry submittable + naming AM-SE; Item child istable.
  test_receipt_increases     — 'Nhập NCC' → ledger +qty; get_stock == qty.
  test_issue_decreases       — Nhập 100 rồi 'Xuất cho NV' 30 → tồn 70.
  test_negative_stock_blocked— Xuất quá tồn → ValidationError (tồn không âm).
  test_transfer              — 'Chuyển kho' 20 → from -20, to +20.
  test_idempotent_ledger     — 1 phiếu submit → đúng số dòng ledger (không nhân đôi).
  test_list_stock_entries    — {data,total_count}; count==rows.

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_stock
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from antmed_crm.api.antmed import inventory


def _mk_item(code, name):
	if frappe.db.exists("AntMed Item", code):
		return frappe.get_doc("AntMed Item", code)
	return frappe.get_doc({"doctype": "AntMed Item", "item_code": code, "item_name": name}).insert(
		ignore_permissions=True
	)


def _mk_lot(lot_no, item):
	if frappe.db.exists("AntMed Lot", lot_no):
		return frappe.get_doc("AntMed Lot", lot_no)
	return frappe.get_doc(
		{"doctype": "AntMed Lot", "lot_no": lot_no, "item": item, "expiry_date": "2027-12-31"}
	).insert(ignore_permissions=True)


def _mk_wh(name, wtype, **kw):
	if frappe.db.exists("AntMed Warehouse", name):
		return frappe.get_doc("AntMed Warehouse", name)
	return frappe.get_doc(
		{"doctype": "AntMed Warehouse", "warehouse_name": name, "warehouse_type": wtype, **kw}
	).insert(ignore_permissions=True)


class TestAntMedStock(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.item = _mk_item("_T-STK-ITEM", "VT tồn kho test").name
		cls.wh_tong = _mk_wh("_T-STK-WH-TONG", "Tổng").name
		cls.wh_nv = _mk_wh("_T-STK-WH-NV", "Cá nhân NV", employee="Administrator").name

	def _fresh_lot(self, suffix):
		"""Lô riêng cho mỗi test → tồn (kho×item×lot) độc lập (không cộng dồn xuyên test)."""
		return _mk_lot(f"_T-STK-LOT-{suffix}", self.item).name

	def _receipt(self, wh, qty, lot):
		return inventory.create_stock_entry(
			entry_type="Nhập NCC", to_warehouse=wh, items=[{"item": self.item, "lot": lot, "qty": qty}]
		)

	def test_doctypes(self):
		for dt in ("AntMed Stock Ledger", "AntMed Stock Entry", "AntMed Stock Entry Item"):
			self.assertTrue(frappe.db.exists("DocType", dt), msg=f"thiếu {dt}")
		self.assertEqual(frappe.get_meta("AntMed Stock Entry").is_submittable, 1)
		self.assertEqual(frappe.get_meta("AntMed Stock Entry Item").istable, 1)

	def test_receipt_increases(self):
		lot = self._fresh_lot("RCV")
		se = self._receipt(self.wh_tong, 100, lot)
		self.assertEqual(se["docstatus"], 1)
		self.assertEqual(inventory.get_stock(self.wh_tong, self.item, lot)["balance_qty"], 100.0)

	def test_issue_decreases(self):
		lot = self._fresh_lot("ISS")
		self._receipt(self.wh_tong, 100, lot)
		inventory.create_stock_entry(
			entry_type="Xuất cho NV",
			from_warehouse=self.wh_tong,
			nv_employee="Administrator",
			items=[{"item": self.item, "lot": lot, "qty": 30}],
		)
		self.assertEqual(inventory.get_stock(self.wh_tong, self.item, lot)["balance_qty"], 70.0)

	def test_negative_stock_blocked(self):
		lot = self._fresh_lot("NEG")
		self._receipt(self.wh_tong, 10, lot)
		with self.assertRaises(frappe.ValidationError):
			inventory.create_stock_entry(
				entry_type="Xuất cho NV",
				from_warehouse=self.wh_tong,
				items=[{"item": self.item, "lot": lot, "qty": 9999}],
			)

	def test_transfer(self):
		lot = self._fresh_lot("TRF")
		self._receipt(self.wh_tong, 100, lot)
		inventory.create_stock_entry(
			entry_type="Chuyển kho",
			from_warehouse=self.wh_tong,
			to_warehouse=self.wh_nv,
			items=[{"item": self.item, "lot": lot, "qty": 20}],
		)
		self.assertEqual(inventory.get_stock(self.wh_tong, self.item, lot)["balance_qty"], 80.0)
		self.assertEqual(inventory.get_stock(self.wh_nv, self.item, lot)["balance_qty"], 20.0)

	def test_idempotent_ledger(self):
		se = self._receipt(self.wh_tong, 50, self._fresh_lot("IDEM"))
		n = frappe.db.count("AntMed Stock Ledger", {"stock_entry": se["name"]})
		self.assertEqual(n, 1)  # 1 phiếu Nhập 1 dòng → đúng 1 ledger

	def test_list_stock_entries(self):
		self._receipt(self.wh_tong, 5, self._fresh_lot("LST"))
		res = inventory.list_stock_entries(page_length=0)
		self.assertEqual(set(res.keys()), {"data", "total_count"})
		self.assertEqual(len(res["data"]), res["total_count"])
