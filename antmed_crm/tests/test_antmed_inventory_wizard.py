# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M03-S3 (mockup C2 Wizard "Xuất cho NV") — FIFO + CO/CQ flag + scan_lot — TDD viết TRƯỚC.

Cover m03_inventory.md §4 (BR-08 FIFO warn, BR-03 cocq_ok) + §5 (fifo_suggest/check_fifo/scan_lot):
  TestCocqFlag           — controller set cocq_ok mỗi dòng (requires_cocq + cert lô).
  TestFifoLots           — stock.get_fifo_lots HSD sớm nhất trước; chỉ lô tồn>0.
  TestFifoSuggest        — fifo_suggest phân bổ take_qty + fulfillable/shortage.
  TestCheckFifo          — is_priority True cho lô cận date nhất; False cho lô muộn hơn.
  TestScanLot            — quét lô (cocq chip + available_qty + days_to_expiry); not_found; fail-closed.
  TestWarehouseBalances  — stock.get_warehouse_balances snapshot kho (cho Kiểm kê).

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_inventory_wizard
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from antmed_crm.antmed import stock
from antmed_crm.api.antmed import inventory

SCAN_LOT_KEYS = {
	"found",
	"reason",
	"item",
	"item_name",
	"lot",
	"lot_no",
	"expiry_date",
	"uom",
	"unit_price",
	"requires_cocq",
	"has_co",
	"has_cq",
	"cocq_ok",
	"recall_status",
	"available_qty",
	"days_to_expiry",
	"is_fifo_priority",
	"suggested_lot",
}


def _mk_item(code, name, **kw):
	if frappe.db.exists("AntMed Item", code):
		return frappe.get_doc("AntMed Item", code)
	return frappe.get_doc(
		{"doctype": "AntMed Item", "item_code": code, "item_name": name, **kw}
	).insert(ignore_permissions=True)


def _mk_lot(lot_no, item, expiry, **kw):
	if frappe.db.exists("AntMed Lot", lot_no):
		return frappe.get_doc("AntMed Lot", lot_no)
	return frappe.get_doc(
		{"doctype": "AntMed Lot", "lot_no": lot_no, "item": item, "expiry_date": expiry, **kw}
	).insert(ignore_permissions=True)


def _mk_cert(cert_no, cert_type, item=None, lot=None):
	if frappe.db.exists("AntMed Certificate", cert_no):
		return frappe.get_doc("AntMed Certificate", cert_no)
	return frappe.get_doc(
		{"doctype": "AntMed Certificate", "cert_no": cert_no, "cert_type": cert_type, "item": item, "lot": lot}
	).insert(ignore_permissions=True)


def _mk_wh(name, wtype, **kw):
	if frappe.db.exists("AntMed Warehouse", name):
		return frappe.get_doc("AntMed Warehouse", name)
	return frappe.get_doc(
		{"doctype": "AntMed Warehouse", "warehouse_name": name, "warehouse_type": wtype, **kw}
	).insert(ignore_permissions=True)


class TestCocqFlag(FrappeTestCase):
	"""BR-03 — controller set cocq_ok mỗi dòng phiếu (M03 gắn cờ; M06 chặn cứng)."""

	def test_compute_cocq_ok_pure(self):
		# Không yêu cầu CO/CQ → luôn 1.
		self.assertEqual(stock.compute_cocq_ok(0, None, None), 1)
		# Yêu cầu + đủ 2 chứng từ → 1.
		self.assertEqual(stock.compute_cocq_ok(1, "CERT-CO", "CERT-CQ"), 1)
		# Yêu cầu + thiếu 1 → 0.
		self.assertEqual(stock.compute_cocq_ok(1, "CERT-CO", None), 0)
		self.assertEqual(stock.compute_cocq_ok(1, None, "CERT-CQ"), 0)
		self.assertEqual(stock.compute_cocq_ok(1, None, None), 0)

	def test_cocq_ok_set_on_lines(self):
		"""Phiếu nhập: lô có đủ CO/CQ → cocq_ok=1; lô thiếu → cocq_ok=0; item không yêu cầu → 1."""
		it_req = _mk_item("_T-CQ-REQ", "VT cần CO/CQ", requires_cocq=1).name
		it_free = _mk_item("_T-CQ-FREE", "VT không cần CO/CQ", requires_cocq=0).name
		lot_ok = _mk_lot("_T-CQ-LOT-OK", it_req, "2028-01-31").name
		lot_bad = _mk_lot("_T-CQ-LOT-BAD", it_req, "2028-01-31").name
		lot_free = _mk_lot("_T-CQ-LOT-FREE", it_free, "2028-01-31").name
		co = _mk_cert("_T-CQ-CO", "CO", item=it_req, lot=lot_ok).name
		cq = _mk_cert("_T-CQ-CQ", "CQ", item=it_req, lot=lot_ok).name
		frappe.db.set_value("AntMed Lot", lot_ok, "co_cert", co)
		frappe.db.set_value("AntMed Lot", lot_ok, "cq_cert", cq)
		wh = _mk_wh("_T-CQ-WH", "Tổng").name
		doc = frappe.get_doc(
			{
				"doctype": "AntMed Stock Entry",
				"entry_type": "Nhập NCC",
				"to_warehouse": wh,
				"items": [
					{"item": it_req, "lot": lot_ok, "qty": 5},
					{"item": it_req, "lot": lot_bad, "qty": 5},
					{"item": it_free, "lot": lot_free, "qty": 5},
				],
			}
		)
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.items[0].cocq_ok, 1)  # đủ CO+CQ
		self.assertEqual(doc.items[1].cocq_ok, 0)  # thiếu chứng từ
		self.assertEqual(doc.items[2].cocq_ok, 1)  # item không yêu cầu


class TestFifoLots(FrappeTestCase):
	"""stock.get_fifo_lots — lô còn tồn xếp HSD sớm nhất trước (BR-08)."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.item = _mk_item("_T-FIFO-ITEM", "VT FIFO").name
		cls.wh = _mk_wh("_T-FIFO-WH", "Tổng").name
		# 3 lô khác HSD: muộn(2029) / sớm(2027) / giữa(2028). Nạp tồn cả 3 + 1 lô đã xuất hết.
		cls.lot_late = _mk_lot("_T-FIFO-LATE", cls.item, "2029-12-31").name
		cls.lot_early = _mk_lot("_T-FIFO-EARLY", cls.item, "2027-01-31").name
		cls.lot_mid = _mk_lot("_T-FIFO-MID", cls.item, "2028-06-30").name
		# HSD tương lai nhưng SỚM NHẤT (trước lot_early) → vẫn chứng minh "lô tồn 0 bị loại dù FIFO-first".
		# (KHÔNG dùng HSD quá khứ: lô hết hạn nay bị chặn xuất — gate an toàn HSD.)
		cls.lot_zero = _mk_lot("_T-FIFO-ZERO", cls.item, add_days(nowdate(), 30)).name
		for lot, qty in ((cls.lot_late, 10), (cls.lot_early, 20), (cls.lot_mid, 15)):
			inventory.create_stock_entry(
				entry_type="Nhập NCC", to_warehouse=cls.wh, items=[{"item": cls.item, "lot": lot, "qty": qty}]
			)
		# lot_zero: nhập 5 rồi xuất hết → tồn 0 (KHÔNG lọt FIFO).
		inventory.create_stock_entry(
			entry_type="Nhập NCC", to_warehouse=cls.wh, items=[{"item": cls.item, "lot": cls.lot_zero, "qty": 5}]
		)
		inventory.create_stock_entry(
			entry_type="Xuất cho NV", from_warehouse=cls.wh, nv_employee="Administrator",
			items=[{"item": cls.item, "lot": cls.lot_zero, "qty": 5}],
		)

	def test_fifo_order_earliest_first(self):
		lots = stock.get_fifo_lots(self.item, self.wh)
		order = [l["lot"] for l in lots]
		# Sớm → giữa → muộn; lô tồn 0 KHÔNG lọt.
		self.assertEqual(order, [self.lot_early, self.lot_mid, self.lot_late])
		self.assertNotIn(self.lot_zero, order)
		self.assertEqual(lots[0]["available_qty"], 20.0)

	def test_fifo_empty_when_no_stock(self):
		self.assertEqual(stock.get_fifo_lots(self.item, "_KHONG-CO-KHO"), [])
		self.assertEqual(stock.get_fifo_lots("", self.wh), [])


class TestFifoSuggest(FrappeTestCase):
	"""inventory.fifo_suggest — phân bổ take_qty + fulfillable/shortage."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.item = _mk_item("_T-FSUG-ITEM", "VT fifo suggest").name
		cls.wh = _mk_wh("_T-FSUG-WH", "Tổng").name
		cls.lot_a = _mk_lot("_T-FSUG-A", cls.item, "2027-01-31").name  # sớm, 8
		cls.lot_b = _mk_lot("_T-FSUG-B", cls.item, "2028-01-31").name  # muộn, 10
		inventory.create_stock_entry(
			entry_type="Nhập NCC", to_warehouse=cls.wh, items=[{"item": cls.item, "lot": cls.lot_a, "qty": 8}]
		)
		inventory.create_stock_entry(
			entry_type="Nhập NCC", to_warehouse=cls.wh, items=[{"item": cls.item, "lot": cls.lot_b, "qty": 10}]
		)

	def test_allocate_across_lots(self):
		"""Cần 12 → lấy 8 lô sớm + 4 lô muộn; fulfillable=True; shortage=0."""
		res = inventory.fifo_suggest(self.item, self.wh, qty=12)
		self.assertTrue(res["fulfillable"])
		self.assertEqual(res["shortage"], 0)
		by_lot = {l["lot"]: l for l in res["lots"]}
		self.assertEqual(by_lot[self.lot_a]["take_qty"], 8.0)
		self.assertEqual(by_lot[self.lot_b]["take_qty"], 4.0)

	def test_shortage_when_not_enough(self):
		"""Cần 100 > tồn 18 → fulfillable=False; shortage=82."""
		res = inventory.fifo_suggest(self.item, self.wh, qty=100)
		self.assertFalse(res["fulfillable"])
		self.assertEqual(res["shortage"], 82.0)


class TestCheckFifo(FrappeTestCase):
	"""inventory.check_fifo — lô chọn có ưu tiên FIFO không (warn nếu False)."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.item = _mk_item("_T-CFIFO-ITEM", "VT check fifo").name
		cls.wh = _mk_wh("_T-CFIFO-WH", "Tổng").name
		cls.lot_early = _mk_lot("_T-CFIFO-EARLY", cls.item, "2027-01-31").name
		cls.lot_late = _mk_lot("_T-CFIFO-LATE", cls.item, "2029-01-31").name
		for lot in (cls.lot_early, cls.lot_late):
			inventory.create_stock_entry(
				entry_type="Nhập NCC", to_warehouse=cls.wh, items=[{"item": cls.item, "lot": lot, "qty": 10}]
			)

	def test_priority_true_for_earliest(self):
		res = inventory.check_fifo(self.item, self.wh, self.lot_early)
		self.assertTrue(res["is_priority"])
		self.assertEqual(res["suggested_lot"], self.lot_early)

	def test_priority_false_for_later(self):
		res = inventory.check_fifo(self.item, self.wh, self.lot_late)
		self.assertFalse(res["is_priority"])
		self.assertEqual(res["suggested_lot"], self.lot_early)


class TestScanLot(FrappeTestCase):
	"""inventory.scan_lot — quét QR lô (chip CO/CQ + tồn + HSD); not_found; fail-closed."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.item = _mk_item("_T-SCAN-ITEM", "VT quét QR", requires_cocq=1, uom="Cái", default_unit_price=250000).name
		cls.wh = _mk_wh("_T-SCAN-WH", "Tổng").name
		cls.exp = add_days(nowdate(), 200)
		cls.lot = _mk_lot("_T-SCAN-LOT", cls.item, cls.exp).name  # thiếu CO/CQ → cocq_ok False
		inventory.create_stock_entry(
			entry_type="Nhập NCC", to_warehouse=cls.wh, items=[{"item": cls.item, "lot": cls.lot, "qty": 7}]
		)

	def test_scan_found_shape(self):
		res = inventory.scan_lot(self.lot, warehouse=self.wh)
		self.assertEqual(set(res.keys()), SCAN_LOT_KEYS, msg=f"shape lệch: {set(res.keys())}")
		self.assertTrue(res["found"])
		self.assertEqual(res["reason"], "ok")
		self.assertEqual(res["item"], self.item)
		self.assertEqual(res["item_name"], "VT quét QR")
		self.assertEqual(res["lot"], self.lot)
		self.assertEqual(res["uom"], "Cái")
		self.assertEqual(res["unit_price"], 250000)
		self.assertEqual(res["available_qty"], 7.0)

	def test_scan_cocq_missing_blocks(self):
		"""Lô thiếu CO/CQ + item requires_cocq → cocq_ok False (FE chặn 'Xuất')."""
		res = inventory.scan_lot(self.lot, warehouse=self.wh)
		self.assertEqual(res["requires_cocq"], 1)
		self.assertFalse(res["has_co"])
		self.assertFalse(res["has_cq"])
		self.assertFalse(res["cocq_ok"])

	def test_scan_cocq_ok_when_certs_present(self):
		lot2 = _mk_lot("_T-SCAN-LOT-OK", self.item, self.exp).name
		co = _mk_cert("_T-SCAN-CO", "CO", item=self.item, lot=lot2).name
		cq = _mk_cert("_T-SCAN-CQ", "CQ", item=self.item, lot=lot2).name
		frappe.db.set_value("AntMed Lot", lot2, "co_cert", co)
		frappe.db.set_value("AntMed Lot", lot2, "cq_cert", cq)
		res = inventory.scan_lot(lot2, warehouse=self.wh)
		self.assertTrue(res["has_co"])
		self.assertTrue(res["has_cq"])
		self.assertTrue(res["cocq_ok"])

	def test_scan_not_found(self):
		res = inventory.scan_lot("_KHONG-TON-TAI-MA", warehouse=self.wh)
		self.assertFalse(res["found"])
		self.assertEqual(res["reason"], "not_found")
		# Shape vẫn ổn định (FE bind không KeyError).
		self.assertEqual(set(res.keys()), SCAN_LOT_KEYS)

	def test_scan_by_item_code_suggests_fifo_lot(self):
		"""Quét item_code (không phải lô) → gợi ý lô FIFO trong kho."""
		res = inventory.scan_lot(self.item, warehouse=self.wh)
		self.assertTrue(res["found"])
		self.assertEqual(res["lot"], self.lot)  # lô duy nhất còn tồn

	def test_scan_fail_closed_no_perm(self):
		"""User thiếu read-perm AntMed Lot → found=False reason='no_perm' (không rò)."""
		from unittest.mock import patch

		def _deny(doctype, *a, **kw):
			return doctype != "AntMed Lot"

		with patch.object(frappe, "has_permission", side_effect=_deny):
			res = inventory.scan_lot(self.lot, warehouse=self.wh)
		self.assertFalse(res["found"])
		self.assertEqual(res["reason"], "no_perm")


class TestWarehouseBalances(FrappeTestCase):
	"""stock.get_warehouse_balances — snapshot tồn 1 kho (cho '📊 Kiểm kê')."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.item = _mk_item("_T-WB-ITEM", "VT snapshot kho").name
		cls.wh = _mk_wh("_T-WB-WH", "Tổng").name
		cls.lot1 = _mk_lot("_T-WB-LOT1", cls.item, "2028-01-31").name
		cls.lot2 = _mk_lot("_T-WB-LOT2", cls.item, "2029-01-31").name
		inventory.create_stock_entry(
			entry_type="Nhập NCC", to_warehouse=cls.wh, items=[{"item": cls.item, "lot": cls.lot1, "qty": 40}]
		)
		inventory.create_stock_entry(
			entry_type="Nhập NCC", to_warehouse=cls.wh, items=[{"item": cls.item, "lot": cls.lot2, "qty": 25}]
		)

	def test_snapshot_rows(self):
		rows = stock.get_warehouse_balances(self.wh)
		by_lot = {r["lot"]: r for r in rows}
		self.assertIn(self.lot1, by_lot)
		self.assertIn(self.lot2, by_lot)
		self.assertEqual(by_lot[self.lot1]["system_qty"], 40.0)
		self.assertEqual(by_lot[self.lot2]["system_qty"], 25.0)
		self.assertEqual(by_lot[self.lot1]["item_name"], "VT snapshot kho")
		self.assertEqual(set(rows[0].keys()), {"item", "item_name", "lot", "lot_no", "expiry_date", "system_qty"})

	def test_snapshot_empty_warehouse(self):
		self.assertEqual(stock.get_warehouse_balances(""), [])


class TestExpiryScheduler(FrappeTestCase):
	"""inventory.notify_expiry_alerts — scheduler hằng ngày notify Thủ kho lô cận/quá HSD."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.item = _mk_item("_T-EXP-ITEM", "VT cận HSD").name
		cls.wh = _mk_wh("_T-EXP-WH", "Tổng").name
		# Lô cận date 10 ngày + tồn>0 → lọt cảnh báo (band d30).
		cls.lot = _mk_lot("_T-EXP-LOT", cls.item, add_days(nowdate(), 10)).name
		inventory.create_stock_entry(
			entry_type="Nhập NCC", to_warehouse=cls.wh, items=[{"item": cls.item, "lot": cls.lot, "qty": 5}]
		)
		# User Thủ kho nhận thông báo.
		cls.user = "_t_exp_thukho@example.com"
		if not frappe.db.exists("User", cls.user):
			u = frappe.get_doc(
				{"doctype": "User", "email": cls.user, "first_name": "Thủ kho HSD", "send_welcome_email": 0}
			)
			u.insert(ignore_permissions=True)
			u.add_roles("Thủ kho")

	def test_summary_counts_near_expiry(self):
		res = inventory.notify_expiry_alerts(90)
		# Lô seed cận date 10 ngày → band d30, lọt vào tổng (≥1; site có thể có lô khác).
		self.assertGreaterEqual(res["d30"], 1)
		self.assertGreaterEqual(res["total_lots"], 1)

	def test_notifies_thukho_user(self):
		# Dọn Notification Log cùng-ngày của user (idempotency subject theo ngày dùng chung giữa test) →
		# đảm bảo lần gọi này TẠO mới cho user (notified đếm user này ≥1).
		frappe.db.delete("Notification Log", {"for_user": self.user})
		res = inventory.notify_expiry_alerts(90)
		self.assertGreaterEqual(res["notified"], 1)
		self.assertTrue(
			frappe.db.exists("Notification Log", {"for_user": self.user}),
			msg="Thủ kho phải nhận Notification Log cảnh báo HSD",
		)

	def test_idempotent_same_day(self):
		"""Gọi lại trong ngày → notified=0 (đã có thông báo cùng subject/user)."""
		inventory.notify_expiry_alerts(90)
		again = inventory.notify_expiry_alerts(90)
		self.assertEqual(again["notified"], 0)


class TestRecallBlockOnIssue(FrappeTestCase):
	"""An toàn recall — KHÔNG cho xuất/đặt ký gửi lô 'Đã thu hồi' (cho phép Chuyển kho gom cách ly)."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.item = _mk_item("_T-RCL-ITEM", "VT recall block", requires_cocq=0).name
		cls.wh = _mk_wh("_T-RCL-WH", "Tổng").name
		cls.wh_nv = _mk_wh("_T-RCL-WH-NV", "Cá nhân NV", employee="Administrator").name

	def _stocked_lot(self, suffix, recall_status="Bình thường", qty=50):
		lot = _mk_lot(f"_T-RCL-LOT-{suffix}", self.item, "2028-12-31").name
		inventory.create_stock_entry(
			entry_type="Nhập NCC", to_warehouse=self.wh, items=[{"item": self.item, "lot": lot, "qty": qty}]
		)
		frappe.db.set_value("AntMed Lot", lot, "recall_status", recall_status)
		return lot

	def test_recalled_lot_blocks_issue(self):
		lot = self._stocked_lot("ISSUE", recall_status="Đã thu hồi")
		with self.assertRaises(frappe.ValidationError) as ctx:
			inventory.create_stock_entry(
				entry_type="Xuất cho NV", from_warehouse=self.wh, nv_employee="Administrator",
				items=[{"item": self.item, "lot": lot, "qty": 5}],
			)
		self.assertIn("thu hồi", str(ctx.exception))

	def test_watched_lot_allows_issue(self):
		"""Lô 'Theo dõi' (chưa thu hồi hẳn) vẫn xuất được (chỉ chặn 'Đã thu hồi')."""
		lot = self._stocked_lot("WATCH", recall_status="Theo dõi")
		res = inventory.create_stock_entry(
			entry_type="Xuất cho NV", from_warehouse=self.wh, nv_employee="Administrator",
			items=[{"item": self.item, "lot": lot, "qty": 5}],
		)
		self.assertEqual(res["docstatus"], 1)

	def test_recalled_lot_allows_transfer(self):
		"""Chuyển kho lô recall (gom về kho cách ly) KHÔNG bị chặn."""
		lot = self._stocked_lot("TRF", recall_status="Đã thu hồi")
		res = inventory.create_stock_entry(
			entry_type="Chuyển kho", from_warehouse=self.wh, to_warehouse=self.wh_nv,
			items=[{"item": self.item, "lot": lot, "qty": 5}],
		)
		self.assertEqual(res["docstatus"], 1)

	def test_recalled_lot_blocks_consignment(self):
		"""Đặt ký gửi BV lô recall cũng bị chặn (đưa hàng tới BV để dùng)."""
		lot = _mk_lot("_T-RCL-LOT-CG", self.item, "2028-12-31").name
		frappe.db.set_value("AntMed Lot", lot, "recall_status", "Đã thu hồi")
		with self.assertRaises(frappe.ValidationError):
			inventory.create_stock_entry(
				entry_type="Nhập ký gửi BV", to_warehouse=self.wh,
				items=[{"item": self.item, "lot": lot, "qty": 5}],
			)


class TestExpiredBlockOnIssue(FrappeTestCase):
	"""An toàn HSD — KHÔNG cho xuất/đặt ký gửi lô đã hết hạn (cho phép Chuyển kho gom thanh lý)."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.item = _mk_item("_T-EXPB-ITEM", "VT expired block", requires_cocq=0).name
		cls.wh = _mk_wh("_T-EXPB-WH", "Tổng").name
		cls.wh_nv = _mk_wh("_T-EXPB-WH-NV", "Cá nhân NV", employee="Administrator").name
		# Lô đã hết hạn (HSD hôm qua) + tồn 50 (Nhập NCC KHÔNG bị chặn).
		cls.lot_expired = _mk_lot("_T-EXPB-LOT-EXP", cls.item, add_days(nowdate(), -1)).name
		inventory.create_stock_entry(
			entry_type="Nhập NCC", to_warehouse=cls.wh, items=[{"item": cls.item, "lot": cls.lot_expired, "qty": 50}]
		)
		# Lô còn hạn để đối chứng.
		cls.lot_ok = _mk_lot("_T-EXPB-LOT-OK", cls.item, add_days(nowdate(), 200)).name
		inventory.create_stock_entry(
			entry_type="Nhập NCC", to_warehouse=cls.wh, items=[{"item": cls.item, "lot": cls.lot_ok, "qty": 50}]
		)

	def test_expired_lot_blocks_issue(self):
		with self.assertRaises(frappe.ValidationError) as ctx:
			inventory.create_stock_entry(
				entry_type="Xuất cho NV", from_warehouse=self.wh, nv_employee="Administrator",
				items=[{"item": self.item, "lot": self.lot_expired, "qty": 5}],
			)
		self.assertIn("hết hạn", str(ctx.exception))

	def test_valid_lot_allows_issue(self):
		res = inventory.create_stock_entry(
			entry_type="Xuất cho NV", from_warehouse=self.wh, nv_employee="Administrator",
			items=[{"item": self.item, "lot": self.lot_ok, "qty": 5}],
		)
		self.assertEqual(res["docstatus"], 1)

	def test_expired_lot_allows_transfer(self):
		"""Chuyển kho lô hết hạn (gom thanh lý) KHÔNG bị chặn."""
		res = inventory.create_stock_entry(
			entry_type="Chuyển kho", from_warehouse=self.wh, to_warehouse=self.wh_nv,
			items=[{"item": self.item, "lot": self.lot_expired, "qty": 5}],
		)
		self.assertEqual(res["docstatus"], 1)
