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


# ── M03-6 (mockup D3 right-card "Cây truy vết") — stock.get_lot_trace helper trực tiếp ──
# TDD viết TRƯỚC: 1 query JOIN (Stock Ledger × Stock Entry × Warehouse) ORDER posting_datetime ASC;
# direction='in' khi qty_change>0 ngược lại 'out'; qty=ABS(qty_change); JOIN gom đúng
# entry_type/warehouse_name/warehouse_type/hospital/nv_employee (KHÔNG N+1, param-bind %s LL-BE-11).

LOT_TRACE_EVENT_KEYS_HELPER = {
	"posting_datetime",
	"entry_type",
	"direction",
	"qty",
	"warehouse",
	"warehouse_name",
	"warehouse_type",
	"voucher_no",
	"hospital",
	"nv_employee",
}


class TestAntMedGetLotTraceHelper(FrappeTestCase):
	"""stock.get_lot_trace — dòng thời gian di chuyển 1 lô (nhập NCC → xuất NV → chuyển/ký gửi)."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.item = _mk_item("_T-STKLT-ITEM", "VT truy vết di chuyển").name
		cls.hosp = (
			frappe.get_doc(
				{"doctype": "AntMed Hospital", "hospital_code": "_T-STKLT-BV", "hospital_name": "BV Truy Vết"}
			).insert(ignore_permissions=True)
			if not frappe.db.exists("AntMed Hospital", "_T-STKLT-BV")
			else frappe.get_doc("AntMed Hospital", "_T-STKLT-BV")
		).name
		cls.wh_tong = _mk_wh("_T-STKLT-WH-TONG", "Tổng").name
		cls.wh_cg = _mk_wh("_T-STKLT-WH-CG", "Ký gửi BV", hospital=cls.hosp).name
		cls.lot = _mk_lot("_T-STKLT-LOT", cls.item).name
		# Nhập NCC 100 vào kho Tổng (ngày sớm nhất) → xuất NV 30 (giữa) → chuyển ký gửi BV 20 (muộn nhất).
		cls.se_in = inventory.create_stock_entry(
			entry_type="Nhập NCC",
			to_warehouse=cls.wh_tong,
			items=[{"item": cls.item, "lot": cls.lot, "qty": 100}],
		)["name"]
		frappe.db.set_value("AntMed Stock Entry", cls.se_in, "posting_datetime", "2026-01-01 08:00:00")
		frappe.db.set_value(
			"AntMed Stock Ledger", {"stock_entry": cls.se_in}, "posting_datetime", "2026-01-01 08:00:00"
		)
		cls.se_out = inventory.create_stock_entry(
			entry_type="Xuất cho NV",
			from_warehouse=cls.wh_tong,
			nv_employee="Administrator",
			items=[{"item": cls.item, "lot": cls.lot, "qty": 30}],
		)["name"]
		frappe.db.set_value("AntMed Stock Entry", cls.se_out, "posting_datetime", "2026-02-01 09:00:00")
		frappe.db.set_value(
			"AntMed Stock Ledger", {"stock_entry": cls.se_out}, "posting_datetime", "2026-02-01 09:00:00"
		)
		cls.se_trf = inventory.create_stock_entry(
			entry_type="Chuyển kho",
			from_warehouse=cls.wh_tong,
			to_warehouse=cls.wh_cg,
			hospital=cls.hosp,
			items=[{"item": cls.item, "lot": cls.lot, "qty": 20}],
		)["name"]
		frappe.db.set_value("AntMed Stock Entry", cls.se_trf, "posting_datetime", "2026-03-01 10:00:00")
		frappe.db.sql(
			"UPDATE `tabAntMed Stock Ledger` SET posting_datetime=%s WHERE stock_entry=%s",
			("2026-03-01 10:00:00", cls.se_trf),
		)
		# Chuyển 20 ra khỏi kho ký gửi → tồn ký gửi nét 0: KHÔNG pollute KPI all_consignment_balances
		# (HAVING SUM>0) của test ký gửi cùng suite. Ledger append-only → giữ event 'in' kho ký gửi.
		cls.se_back = inventory.create_stock_entry(
			entry_type="Chuyển kho",
			from_warehouse=cls.wh_cg,
			to_warehouse=cls.wh_tong,
			items=[{"item": cls.item, "lot": cls.lot, "qty": 20}],
		)["name"]
		frappe.db.set_value("AntMed Stock Entry", cls.se_back, "posting_datetime", "2026-04-01 11:00:00")
		frappe.db.sql(
			"UPDATE `tabAntMed Stock Ledger` SET posting_datetime=%s WHERE stock_entry=%s",
			("2026-04-01 11:00:00", cls.se_back),
		)
		# KHÔNG frappe.db.commit(): commit phá rollback FrappeTestCase → leak kho ký gửi test vào DB
		# vĩnh viễn, làm sai KPI consignment toàn cục. UPDATE cùng transaction đã hiển thị cho read sau
		# (cùng connection) — không cần commit. (Back-transfer ở trên giữ net tồn ký gửi = 0 phòng thủ.)

	def test_helper_shape(self):
		"""Mỗi event đúng 10 key cố định (LOT_TRACE_EVENT_KEYS)."""
		from antmed_crm.antmed import stock

		events = stock.get_lot_trace(self.lot)
		self.assertTrue(events)
		for ev in events:
			self.assertEqual(set(ev.keys()), LOT_TRACE_EVENT_KEYS_HELPER, msg=f"shape lệch: {set(ev.keys())}")

	def test_helper_order_asc(self):
		"""ORDER posting_datetime ASC (nhập 01/01 → xuất 01/02 → chuyển 01/03)."""
		from antmed_crm.antmed import stock

		events = stock.get_lot_trace(self.lot)
		dts = [str(e["posting_datetime"]) for e in events]
		self.assertEqual(dts, sorted(dts), msg=f"chưa ASC: {dts}")

	def test_helper_direction_and_abs_qty(self):
		"""direction='in' cho qty_change>0; 'out' cho <0; qty = ABS(qty_change) (luôn dương)."""
		from antmed_crm.antmed import stock

		events = stock.get_lot_trace(self.lot)
		for ev in events:
			self.assertIn(ev["direction"], ("in", "out"))
			self.assertGreater(ev["qty"], 0, msg=f"qty phải dương tuyệt đối: {ev}")
		# Nhập NCC (kho Tổng, sớm nhất) → in, qty 100.
		first = events[0]
		self.assertEqual(first["direction"], "in")
		self.assertEqual(first["qty"], 100.0)
		self.assertEqual(first["entry_type"], "Nhập NCC")
		# Xuất cho NV → out, qty 30.
		issue = next(e for e in events if e["entry_type"] == "Xuất cho NV")
		self.assertEqual(issue["direction"], "out")
		self.assertEqual(issue["qty"], 30.0)

	def test_helper_join_fields(self):
		"""JOIN gom đúng entry_type/warehouse_name/warehouse_type/hospital/nv_employee."""
		from antmed_crm.antmed import stock

		events = stock.get_lot_trace(self.lot)
		# Nhập NCC → kho Tổng.
		rcv = next(e for e in events if e["entry_type"] == "Nhập NCC")
		self.assertEqual(rcv["warehouse"], self.wh_tong)
		self.assertEqual(rcv["warehouse_name"], "_T-STKLT-WH-TONG")
		self.assertEqual(rcv["warehouse_type"], "Tổng")
		# Xuất cho NV → nv_employee resolve.
		issue = next(e for e in events if e["entry_type"] == "Xuất cho NV")
		self.assertEqual(issue["nv_employee"], "Administrator")
		# Chuyển kho ký gửi BV → có dòng vào kho Ký gửi BV (warehouse_type) + hospital.
		cg_in = next(e for e in events if e["warehouse"] == self.wh_cg and e["direction"] == "in")
		self.assertEqual(cg_in["warehouse_type"], "Ký gửi BV")
		self.assertEqual(cg_in["hospital"], self.hosp)

	def test_helper_no_ledger(self):
		"""Lô không có ledger → [] (không lỗi)."""
		from antmed_crm.antmed import stock

		empty_lot = _mk_lot("_T-STKLT-LOT-EMPTY", self.item).name
		self.assertEqual(stock.get_lot_trace(empty_lot), [])

	def test_helper_param_bind_and_single_query(self):
		"""param-bind %s cho lot (KHÔNG nối chuỗi user) + 1 query JOIN (KHÔNG N+1)."""
		import inspect

		from antmed_crm.antmed import stock

		src = inspect.getsource(stock.get_lot_trace)
		self.assertIn("%s", src)
		# Giá trị user (lot) KHÔNG nội suy vào chuỗi SQL — đi qua bind %s. Tên bảng là hằng .format.
		self.assertNotRegex(src, r"f['\"][^'\"]*SELECT", msg="KHÔNG f-string SQL")
		self.assertNotRegex(src, r"\{lot\}")
		# 1 query JOIN gộp (INNER JOIN Stock Entry + Warehouse) — KHÔNG N+1.
		self.assertIn("JOIN", src.upper())
