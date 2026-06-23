# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M03 D3 — Recall tự sinh AntMed Recall Notification + BV ảnh hưởng + thông báo — TDD.

Cover: initiate_recall('Đã thu hồi') → tạo Recall Notification; BV ảnh hưởng = ký gửi ∪ đã giao;
Notification Log cho Thủ kho; idempotent; list/get.

Lệnh:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_recall
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from antmed_crm.api.antmed import inventory

RN = "AntMed Recall Notification"


def _mk(dt, name, doc):
	if frappe.db.exists(dt, name):
		return frappe.get_doc(dt, name)
	return frappe.get_doc({"doctype": dt, **doc}).insert(ignore_permissions=True)


class TestRecallNotification(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.item = _mk(
			"AntMed Item",
			"_T-RCN-ITEM",
			{"item_code": "_T-RCN-ITEM", "item_name": "VT recall notif", "requires_cocq": 0},
		).name
		# BV1 giữ ký gửi; BV2 đã được giao.
		cls.bv1 = _mk(
			"AntMed Hospital",
			"_T-RCN-BV1",
			{"hospital_code": "_T-RCN-BV1", "hospital_name": "BV Ký Gửi Recall"},
		).name
		cls.bv2 = _mk(
			"AntMed Hospital",
			"_T-RCN-BV2",
			{"hospital_code": "_T-RCN-BV2", "hospital_name": "BV Giao Recall"},
		).name
		cls.cg_wh = _mk(
			"AntMed Warehouse",
			"_T-RCN-CG",
			{"warehouse_name": "_T-RCN-CG", "warehouse_type": "Ký gửi BV", "hospital": cls.bv1},
		).name
		# Thủ kho nhận thông báo.
		cls.thukho = "_t_rcn_thukho@example.com"
		if not frappe.db.exists("User", cls.thukho):
			u = frappe.get_doc(
				{
					"doctype": "User",
					"email": cls.thukho,
					"first_name": "Thủ kho Recall",
					"send_welcome_email": 0,
				}
			)
			u.insert(ignore_permissions=True)
			u.add_roles("Thủ kho")

	def _fresh_lot(self, suffix):
		"""Lô mới (Bình thường, còn hạn) + ký gửi BV1 20 + giao BV2 10 → 2 BV ảnh hưởng."""
		lot = _mk(
			"AntMed Lot",
			f"_T-RCN-LOT-{suffix}",
			{"lot_no": f"_T-RCN-LOT-{suffix}", "item": self.item, "expiry_date": add_days(nowdate(), 300)},
		).name
		inventory.create_stock_entry(
			entry_type="Nhập ký gửi BV",
			to_warehouse=self.cg_wh,
			hospital=self.bv1,
			items=[{"item": self.item, "lot": lot, "qty": 20}],
		)
		frappe.get_doc(
			{
				"doctype": "AntMed Delivery",
				"hospital": self.bv2,
				"surgery_datetime": f"{add_days(nowdate(), 1)} 09:00:00",
				"status": "Nháp",
				"items": [{"item": self.item, "lot": lot, "requested_qty": 10, "consumed_qty": 10}],
			}
		).insert(ignore_permissions=True)
		return lot

	def test_doctypes(self):
		self.assertTrue(frappe.db.exists("DocType", "AntMed Recall Notification"))
		self.assertTrue(frappe.db.exists("DocType", "AntMed Recall Affected Hospital"))
		self.assertIn("AM-RN-", frappe.get_meta(RN).get_field("naming_series").options)

	def test_recall_creates_notification_with_affected(self):
		lot = self._fresh_lot("AFF")
		res = inventory.initiate_recall(lot=lot, reason="Lỗi tiệt khuẩn", status="Đã thu hồi")
		self.assertIsNotNone(res["recall_notification"])
		self.assertEqual(res["affected_hospitals"], 2)  # BV1 ký gửi + BV2 giao
		# Chi tiết: BV ảnh hưởng đúng SL ký gửi/đã giao.
		detail = inventory.get_recall_notification(res["recall_notification"])
		by_h = {h["hospital"]: h for h in detail["hospitals"]}
		self.assertEqual(by_h[self.bv1]["qty_consignment"], 20.0)
		self.assertEqual(by_h[self.bv1]["qty_delivered"], 0.0)
		self.assertEqual(by_h[self.bv2]["qty_delivered"], 10.0)
		self.assertEqual(detail["status"], "Đã phát")
		self.assertEqual(detail["item"], self.item)

	def test_recall_notifies_thukho(self):
		frappe.db.delete("Notification Log", {"for_user": self.thukho})
		lot = self._fresh_lot("NOTIF")
		res = inventory.initiate_recall(lot=lot, reason="Cảnh báo NCC", status="Đã thu hồi")
		self.assertGreaterEqual(res["affected_hospitals"], 1)
		self.assertTrue(
			frappe.db.exists("Notification Log", {"for_user": self.thukho}),
			"Thủ kho phải nhận thông báo thu hồi",
		)

	def test_watch_does_not_create_notification(self):
		"""'Theo dõi' (chưa thu hồi hẳn) → KHÔNG sinh Recall Notification."""
		lot = self._fresh_lot("WATCH")
		res = inventory.initiate_recall(lot=lot, reason="Theo dõi NCC", status="Theo dõi")
		self.assertIsNone(res["recall_notification"])
		self.assertEqual(res["affected_hospitals"], 0)
		self.assertFalse(frappe.db.exists(RN, {"lot": lot}))

	def test_create_recall_notification_idempotent(self):
		"""_create_recall_notification gọi 2 lần (bản đang mở) → cùng 1 name."""
		lot = self._fresh_lot("IDEM")
		a = inventory._create_recall_notification(lot, "lần 1")["name"]
		b = inventory._create_recall_notification(lot, "lần 2")["name"]
		self.assertEqual(a, b)

	def test_list_recall_notifications(self):
		lot = self._fresh_lot("LST")
		inventory.initiate_recall(lot=lot, reason="x", status="Đã thu hồi")
		res = inventory.list_recall_notifications(lot=lot, page_length=0)
		self.assertEqual(set(res.keys()), {"data", "total_count"})
		self.assertEqual(len(res["data"]), res["total_count"])
		self.assertTrue(res["data"])
		self.assertEqual(set(res["data"][0].keys()), set(inventory.RN_LIST_ITEM_KEYS))
