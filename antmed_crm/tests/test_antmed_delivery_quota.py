# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M04 Slice S3 (BE) — Trừ quota (BR-06) + chữ ký/GPS + BR-07 khi bàn giao phòng mổ.

Cover m04_or_delivery.md §4 (BR-06/BR-07) + §3 (handover capture):
  test_handover_consumes_quota — bàn giao → trừ quota HĐ (M02 consume_quota), used_qty tăng.
  test_br06_block_over_cap     — quota chạm trần + lock → bàn giao throw 'BR-06' (không submit).
  test_handover_captures_gps   — gps_lat/lng + signed_by lưu trên phiếu giao.
  test_br07_block_delete_signed— phiếu đã bàn giao (docstatus 1) → xóa raise.

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_delivery_quota
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from antmed_crm.api.antmed import delivery


def _ensure(doctype, key, val, values):
	name = frappe.db.get_value(doctype, {key: val}, "name")
	return name or frappe.get_doc({"doctype": doctype, key: val, **values}).insert(ignore_permissions=True).name


def _mk_contract(contract_no, hospital, item, quota_qty, used_qty, lock=1):
	rem = round((1 - used_qty / quota_qty) * 100, 2) if quota_qty else 0
	doc = frappe.get_doc(
		{
			"doctype": "AntMed Contract",
			"contract_no": contract_no,
			"hospital": hospital,
			"signed_date": "2026-01-05",
			"status": "Hiệu lực",
			"valid_to": "2026-12-31",
			"items": [{"item": item, "item_name": item, "uom": "Cái", "unit_price": 1000000, "quota_qty": quota_qty, "used_qty": used_qty, "remaining_pct": rem, "lock_at_100": lock}],
		}
	)
	doc.insert(ignore_permissions=True)
	doc.submit()
	return doc.name


def _used_qty(contract, item):
	return frappe.db.get_value("AntMed Quota Item", {"parent": contract, "item": item}, "used_qty")


class TestAntMedDeliveryQuota(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hosp = _ensure("AntMed Hospital", "hospital_code", "_T-DRQ-BV", {"hospital_name": "BV Quota Giao"})
		cls.item = _ensure("AntMed Item", "item_code", "VTYT-DRQ", {"item_name": "Stent quota giao"})

	def _delivery(self, contract, qty):
		dlv = frappe.get_doc(
			{"doctype": "AntMed Delivery", "hospital": self.hosp, "contract": contract, "surgery_datetime": str(add_to_date(now_datetime(), hours=4)), "items": [{"item": self.item, "requested_qty": qty}]}
		).insert(ignore_permissions=True).name
		delivery.assign(dlv, "Administrator")
		delivery.start_transit(dlv)
		return dlv

	def test_handover_consumes_quota(self):
		c = _mk_contract("_T-DRQ-C1", self.hosp, self.item, quota_qty=100, used_qty=0)
		dlv = self._delivery(c, 10)
		delivery.handover(dlv)
		self.assertEqual(float(_used_qty(c, self.item)), 10.0)

	def test_br06_block_over_cap(self):
		c = _mk_contract("_T-DRQ-C2", self.hosp, self.item, quota_qty=100, used_qty=95, lock=1)
		dlv = self._delivery(c, 10)  # 10 > còn lại 5
		with self.assertRaises(frappe.ValidationError) as cm:
			delivery.handover(dlv)
		self.assertIn("BR-06", str(cm.exception))
		self.assertEqual(frappe.db.get_value("AntMed Delivery", dlv, "docstatus"), 0)  # KHÔNG submit

	def test_handover_captures_gps(self):
		c = _mk_contract("_T-DRQ-C3", self.hosp, self.item, quota_qty=100, used_qty=0)
		dlv = self._delivery(c, 2)
		delivery.handover(dlv, gps_lat="10.776", gps_lng="106.700", signed_by="BS Nguyễn", signature_method="Touch")
		self.assertEqual(frappe.db.get_value("AntMed Delivery", dlv, "signed_by"), "BS Nguyễn")
		self.assertAlmostEqual(float(frappe.db.get_value("AntMed Delivery", dlv, "gps_lat")), 10.776, places=3)

	def test_br07_block_delete_signed(self):
		c = _mk_contract("_T-DRQ-C4", self.hosp, self.item, quota_qty=100, used_qty=0)
		dlv = self._delivery(c, 1)
		delivery.handover(dlv)
		with self.assertRaises(Exception):
			frappe.delete_doc("AntMed Delivery", dlv, force=False)
