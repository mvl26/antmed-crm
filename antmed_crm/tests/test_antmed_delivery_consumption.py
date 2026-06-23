# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M04→M03 wiring — bàn giao phòng mổ sinh AntMed Stock Entry 'Giao phòng mổ' trừ kho NV — TDD.

Cover: handover → ghi sổ tồn tiêu hao theo lô (kho cá nhân NV); FK delivery; guarded (NV không kho
→ bỏ qua, bàn giao vẫn OK); idempotent (1 phiếu/bàn giao).

Lệnh:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_delivery_consumption
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from antmed_crm.api.antmed import delivery, inventory

STOCK_ENTRY = "AntMed Stock Entry"


def _mk(dt, name, doc):
	if frappe.db.exists(dt, name):
		return frappe.get_doc(dt, name)
	return frappe.get_doc({"doctype": dt, **doc}).insert(ignore_permissions=True)


def _user(email):
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0}
		).insert(ignore_permissions=True)
	return email


def _delivery(hospital, nv, item, lot, qty, status="Đang giao", doctor=None):
	return (
		frappe.get_doc(
			{
				"doctype": "AntMed Delivery",
				"hospital": hospital,
				"doctor": doctor,
				"surgery_datetime": f"{add_days(nowdate(), 1)} 14:30:00",
				"status": status,
				"assigned_employee": nv,
				"items": [{"item": item, "lot": lot, "requested_qty": qty, "consumed_qty": qty}],
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


class TestDeliveryConsumption(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.item = _mk(
			"AntMed Item",
			"_T-GPM-ITEM",
			{"item_code": "_T-GPM-ITEM", "item_name": "VT giao phòng mổ", "requires_cocq": 0},
		).name
		cls.hosp = _mk(
			"AntMed Hospital",
			"_T-GPM-BV",
			{"hospital_code": "_T-GPM-BV", "hospital_name": "BV Giao Phòng Mổ"},
		).name
		cls.nv = _user("_t_gpm_nv@example.com")
		cls.nv_wh = _mk(
			"AntMed Warehouse",
			"_T-GPM-WH-NV",
			{"warehouse_name": "_T-GPM-WH-NV", "warehouse_type": "Cá nhân NV", "employee": cls.nv},
		).name

	def _fresh_lot(self, suffix, qty):
		"""Lô riêng + nạp tồn `qty` vào kho NV → mỗi test tồn độc lập (handover submit không rollback sạch)."""
		lot = _mk(
			"AntMed Lot",
			f"_T-GPM-LOT-{suffix}",
			{"lot_no": f"_T-GPM-LOT-{suffix}", "item": self.item, "expiry_date": add_days(nowdate(), 300)},
		).name
		inventory.create_stock_entry(
			entry_type="Nhập NCC",
			to_warehouse=self.nv_wh,
			items=[{"item": self.item, "lot": lot, "qty": qty}],
		)
		return lot

	def test_handover_posts_consumption_stock_entry(self):
		"""Bàn giao 20 → sinh phiếu 'Giao phòng mổ' (FK delivery) trừ kho NV 50→30."""
		lot = self._fresh_lot("POST", 50)
		dlv = _delivery(self.hosp, self.nv, self.item, lot, 20)
		delivery.handover(dlv)
		# Phiếu kho 'Giao phòng mổ' link delivery, đã submit.
		se = frappe.db.get_value(
			STOCK_ENTRY, {"delivery": dlv, "entry_type": "Giao phòng mổ"}, ["name", "docstatus"], as_dict=True
		)
		self.assertIsNotNone(se, "phải sinh AntMed Stock Entry 'Giao phòng mổ'")
		self.assertEqual(se["docstatus"], 1)
		# Kho NV giảm 20 (lô riêng → không bị test khác trừ).
		self.assertEqual(inventory.get_stock(self.nv_wh, self.item, lot)["balance_qty"], 30.0)

	def test_handover_idempotent_one_entry(self):
		"""1 lần bàn giao → đúng 1 phiếu 'Giao phòng mổ' (không nhân đôi)."""
		lot = self._fresh_lot("IDEM", 50)
		dlv = _delivery(self.hosp, self.nv, self.item, lot, 5)
		delivery.handover(dlv)
		n = frappe.db.count(STOCK_ENTRY, {"delivery": dlv, "entry_type": "Giao phòng mổ"})
		self.assertEqual(n, 1)

	def test_handover_guarded_no_nv_warehouse(self):
		"""NV KHÔNG có kho cá nhân → bàn giao vẫn THÀNH CÔNG, KHÔNG sinh phiếu kho (best-effort skip)."""
		lot = self._fresh_lot("GUARD", 50)
		nv2 = _user("_t_gpm_nv2@example.com")  # KHÔNG tạo kho cá nhân
		dlv = _delivery(self.hosp, nv2, self.item, lot, 10)
		res = delivery.handover(dlv)
		self.assertEqual(res["status"], "Đã bàn giao")  # bàn giao OK
		n = frappe.db.count(STOCK_ENTRY, {"delivery": dlv})
		self.assertEqual(n, 0)  # không ghi sổ (NV chưa có kho)

	def test_consumption_appears_in_genealogy(self):
		"""Phả hệ lô thấy phiếu giao vừa bàn giao (lô → ca mổ)."""
		lot = self._fresh_lot("GEN", 50)
		dlv = _delivery(self.hosp, self.nv, self.item, lot, 3)
		delivery.handover(dlv)
		gen = inventory.lot_genealogy(lot)
		self.assertIn(dlv, {d["delivery"] for d in gen["deliveries"]})
