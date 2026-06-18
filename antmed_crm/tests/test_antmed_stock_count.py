# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M03 (mockup '📊 Kiểm kê') — AntMed Stock Count: snapshot + variance + điều chỉnh tồn — TDD viết TRƯỚC.

Cover m03_inventory.md §2/§4 (Kiểm kê tồn 1 kho):
  test_doctypes            — AntMed Stock Count submittable + child istable + naming AM-SC.
  test_snapshot            — stock_count_snapshot trả tồn (item×lot) >0 của kho.
  test_count_up/down/zero  — counted>system → tồn tăng; counted<system → giảm; ==→ không ledger.
  test_authoritative       — system_qty controller tự tính (bỏ qua giá trị FE gửi).
  test_cancel_reverses     — on_cancel đảo điều chỉnh → tồn về cũ.
  test_list/get            — list_stock_counts count==rows; get_stock_count shape + variance.

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_stock_count
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from antmed_crm.api.antmed import inventory

SNAPSHOT_ROW_KEYS = {"item", "item_name", "lot", "lot_no", "expiry_date", "system_qty"}
DETAIL_HEADER_KEYS = {
	"name",
	"warehouse",
	"warehouse_name",
	"count_datetime",
	"counted_by",
	"counted_by_name",
	"total_variance_qty",
	"note",
	"docstatus",
}
DETAIL_ITEM_KEYS = {"item", "item_name", "lot", "lot_no", "expiry_date", "system_qty", "counted_qty", "variance"}


def _mk_item(code, name):
	if frappe.db.exists("AntMed Item", code):
		return frappe.get_doc("AntMed Item", code)
	return frappe.get_doc({"doctype": "AntMed Item", "item_code": code, "item_name": name}).insert(
		ignore_permissions=True
	)


def _mk_lot(lot_no, item, expiry="2028-12-31"):
	if frappe.db.exists("AntMed Lot", lot_no):
		return frappe.get_doc("AntMed Lot", lot_no)
	return frappe.get_doc(
		{"doctype": "AntMed Lot", "lot_no": lot_no, "item": item, "expiry_date": expiry}
	).insert(ignore_permissions=True)


def _mk_wh(name, wtype="Tổng", **kw):
	if frappe.db.exists("AntMed Warehouse", name):
		return frappe.get_doc("AntMed Warehouse", name)
	return frappe.get_doc(
		{"doctype": "AntMed Warehouse", "warehouse_name": name, "warehouse_type": wtype, **kw}
	).insert(ignore_permissions=True)


class TestAntMedStockCount(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.item = _mk_item("_T-SC-ITEM", "VT kiểm kê").name
		cls.wh = _mk_wh("_T-SC-WH").name

	def _fresh(self, suffix, qty):
		"""Lô riêng + nạp tồn `qty` → mỗi test tồn độc lập (không cộng dồn)."""
		lot = _mk_lot(f"_T-SC-LOT-{suffix}", self.item).name
		inventory.create_stock_entry(
			entry_type="Nhập NCC", to_warehouse=self.wh, items=[{"item": self.item, "lot": lot, "qty": qty}]
		)
		return lot

	def test_doctypes(self):
		self.assertTrue(frappe.db.exists("DocType", "AntMed Stock Count"))
		self.assertTrue(frappe.db.exists("DocType", "AntMed Stock Count Item"))
		self.assertEqual(frappe.get_meta("AntMed Stock Count").is_submittable, 1)
		self.assertEqual(frappe.get_meta("AntMed Stock Count Item").istable, 1)
		series = frappe.get_meta("AntMed Stock Count").get_field("naming_series").options
		self.assertIn("AM-SC-", series)

	def test_docperm_vietnamese(self):
		perms = {p.role for p in frappe.get_meta("AntMed Stock Count").permissions}
		self.assertIn("Thủ kho", perms)
		self.assertIn("Quản lý", perms)
		self.assertNotIn("AM System Admin", perms)

	def test_snapshot(self):
		lot = self._fresh("SNAP", 40)
		res = inventory.stock_count_snapshot(self.wh)
		self.assertEqual(res["warehouse"], self.wh)
		by_lot = {r["lot"]: r for r in res["rows"]}
		self.assertIn(lot, by_lot)
		self.assertEqual(by_lot[lot]["system_qty"], 40.0)
		self.assertEqual(set(by_lot[lot].keys()), SNAPSHOT_ROW_KEYS)
		self.assertEqual(by_lot[lot]["item_name"], "VT kiểm kê")

	def test_count_up_adjusts_stock(self):
		"""counted 110 > system 100 → variance +10 → tồn về 110."""
		lot = self._fresh("UP", 100)
		res = inventory.create_stock_count(self.wh, items=[{"item": self.item, "lot": lot, "counted_qty": 110}])
		self.assertEqual(res["docstatus"], 1)
		self.assertEqual(res["total_variance_qty"], 10.0)
		self.assertEqual(inventory.get_stock(self.wh, self.item, lot)["balance_qty"], 110.0)

	def test_count_down_adjusts_stock(self):
		"""counted 70 < system 100 → variance -30 → tồn về 70."""
		lot = self._fresh("DOWN", 100)
		res = inventory.create_stock_count(self.wh, items=[{"item": self.item, "lot": lot, "counted_qty": 70}])
		self.assertEqual(res["total_variance_qty"], -30.0)
		self.assertEqual(inventory.get_stock(self.wh, self.item, lot)["balance_qty"], 70.0)

	def test_count_zero_variance_no_ledger(self):
		"""counted == system → variance 0 → KHÔNG ghi dòng điều chỉnh."""
		lot = self._fresh("ZERO", 50)
		res = inventory.create_stock_count(self.wh, items=[{"item": self.item, "lot": lot, "counted_qty": 50}])
		self.assertEqual(res["total_variance_qty"], 0.0)
		n = frappe.db.count(
			"AntMed Stock Ledger", {"voucher_type": "AntMed Stock Count", "voucher_no": res["name"]}
		)
		self.assertEqual(n, 0)
		self.assertEqual(inventory.get_stock(self.wh, self.item, lot)["balance_qty"], 50.0)

	def test_system_qty_authoritative(self):
		"""system_qty controller TỰ TÍNH từ sổ tồn — bỏ qua giá trị FE gửi (chống snapshot cũ)."""
		lot = self._fresh("AUTH", 100)
		# FE gửi system_qty=999 (cũ/sai) — controller phải dùng tồn thật 100 → variance = 80-100 = -20.
		res = inventory.create_stock_count(
			self.wh, items=[{"item": self.item, "lot": lot, "system_qty": 999, "counted_qty": 80}]
		)
		self.assertEqual(res["total_variance_qty"], -20.0)
		self.assertEqual(inventory.get_stock(self.wh, self.item, lot)["balance_qty"], 80.0)

	def test_cancel_reverses(self):
		"""on_cancel đảo điều chỉnh → tồn về 100."""
		lot = self._fresh("CANCEL", 100)
		res = inventory.create_stock_count(self.wh, items=[{"item": self.item, "lot": lot, "counted_qty": 130}])
		self.assertEqual(inventory.get_stock(self.wh, self.item, lot)["balance_qty"], 130.0)
		frappe.get_doc("AntMed Stock Count", res["name"]).cancel()
		self.assertEqual(inventory.get_stock(self.wh, self.item, lot)["balance_qty"], 100.0)

	def test_idempotent_post(self):
		"""1 phiếu submit → đúng 1 dòng ledger điều chỉnh (không nhân đôi)."""
		lot = self._fresh("IDEM", 100)
		res = inventory.create_stock_count(self.wh, items=[{"item": self.item, "lot": lot, "counted_qty": 95}])
		n = frappe.db.count(
			"AntMed Stock Ledger", {"voucher_type": "AntMed Stock Count", "voucher_no": res["name"]}
		)
		self.assertEqual(n, 1)

	def test_list_stock_counts(self):
		lot = self._fresh("LST", 10)
		inventory.create_stock_count(self.wh, items=[{"item": self.item, "lot": lot, "counted_qty": 12}])
		res = inventory.list_stock_counts(warehouse=self.wh, page_length=0)
		self.assertEqual(set(res.keys()), {"data", "total_count"})
		self.assertEqual(len(res["data"]), res["total_count"])
		self.assertTrue(res["data"])
		row = res["data"][0]
		self.assertEqual(
			set(row.keys()),
			{"name", "warehouse", "count_datetime", "docstatus", "total_variance_qty", "counted_by", "counted_by_name"},
		)

	def test_get_stock_count(self):
		lot = self._fresh("GET", 100)
		created = inventory.create_stock_count(
			self.wh, items=[{"item": self.item, "lot": lot, "counted_qty": 88}], note="Kiểm kê quý"
		)
		res = inventory.get_stock_count(created["name"])
		self.assertEqual(set(res.keys()), DETAIL_HEADER_KEYS | {"items"})
		self.assertEqual(res["warehouse"], self.wh)
		self.assertEqual(res["note"], "Kiểm kê quý")
		self.assertEqual(res["total_variance_qty"], -12.0)
		self.assertEqual(len(res["items"]), 1)
		line = res["items"][0]
		self.assertEqual(set(line.keys()), DETAIL_ITEM_KEYS)
		self.assertEqual(line["system_qty"], 100.0)
		self.assertEqual(line["counted_qty"], 88.0)
		self.assertEqual(line["variance"], -12.0)
		self.assertEqual(line["item_name"], "VT kiểm kê")

	def test_get_stock_count_not_found(self):
		with self.assertRaises(frappe.DoesNotExistError):
			inventory.get_stock_count("_T-SC-KHONG-TON-TAI")
