# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M04 Slice S2 (BE) — Vòng đời giao phòng mổ: create/assign/start_transit/handover + dispatch_board.

Cover m04_or_delivery.md §3 (states) + §5 (lifecycle endpoints) + SLA:
  test_create_request        — tạo phiếu → status 'Nháp'.
  test_assign                — Nháp → 'Đã gán NV' + set assigned_employee.
  test_invalid_transition    — start_transit khi chưa 'Đã gán NV' → throw.
  test_full_lifecycle        — create→assign→start_transit→handover → 'Đã bàn giao', docstatus 1, sla_status set.
  test_sla_late              — handover sau giờ mổ (quá khứ) → sla_status 'Late'.
  test_dispatch_board        — gom phiếu theo cột trạng thái.
  test_handover_permission   — user không write → PermissionError.

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_delivery_flow
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from antmed_crm.api.antmed import delivery


def _mk_hospital(code, name):
	if frappe.db.exists("AntMed Hospital", code):
		return frappe.get_doc("AntMed Hospital", code)
	return frappe.get_doc({"doctype": "AntMed Hospital", "hospital_code": code, "hospital_name": name}).insert(
		ignore_permissions=True
	)


def _mk_item(code, name):
	if frappe.db.exists("AntMed Item", code):
		return frappe.get_doc("AntMed Item", code)
	return frappe.get_doc({"doctype": "AntMed Item", "item_code": code, "item_name": name}).insert(
		ignore_permissions=True
	)


class TestAntMedDeliveryFlow(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hosp = _mk_hospital("_T-DRF-BV", "BV Flow Giao").name
		cls.item = _mk_item("_T-DRF-VTYT", "VT flow giao").name

	def _create(self, surgery_dt):
		return delivery.create_request(
			hospital=self.hosp,
			surgery_datetime=surgery_dt,
			items=[{"item": self.item, "requested_qty": 2}],
		)["name"]

	def test_create_request(self):
		name = self._create(str(add_to_date(now_datetime(), hours=4)))
		self.assertEqual(frappe.db.get_value("AntMed Delivery", name, "status"), "Nháp")

	def test_assign(self):
		name = self._create(str(add_to_date(now_datetime(), hours=4)))
		res = delivery.assign(name, "Administrator")
		self.assertEqual(res["status"], "Đã gán NV")
		self.assertEqual(frappe.db.get_value("AntMed Delivery", name, "assigned_employee"), "Administrator")

	def test_invalid_transition(self):
		name = self._create(str(add_to_date(now_datetime(), hours=4)))
		with self.assertRaises(frappe.ValidationError):
			delivery.start_transit(name)  # chưa 'Đã gán NV'

	def test_full_lifecycle(self):
		name = self._create(str(add_to_date(now_datetime(), hours=4)))
		delivery.assign(name, "Administrator")
		delivery.start_transit(name)
		res = delivery.handover(name)
		self.assertEqual(res["status"], "Đã bàn giao")
		self.assertEqual(res["sla_status"], "OnTime")  # giao trước giờ mổ
		self.assertEqual(frappe.db.get_value("AntMed Delivery", name, "docstatus"), 1)
		self.assertIsNotNone(frappe.db.get_value("AntMed Delivery", name, "delivered_at"))

	def test_sla_late(self):
		name = self._create(str(add_to_date(now_datetime(), hours=-2)))  # giờ mổ đã qua
		delivery.assign(name, "Administrator")
		delivery.start_transit(name)
		res = delivery.handover(name)
		self.assertEqual(res["sla_status"], "Late")

	def test_dispatch_board(self):
		name = self._create(str(add_to_date(now_datetime(), hours=4)))
		delivery.assign(name, "Administrator")
		board = delivery.dispatch_board()
		self.assertIn("columns", board)
		cols = {c["status"]: c["items"] for c in board["columns"]}
		self.assertIn("Đã gán NV", cols)
		self.assertIn(name, {it["name"] for it in cols["Đã gán NV"]})

	def test_handover_permission(self):
		name = self._create(str(add_to_date(now_datetime(), hours=4)))
		delivery.assign(name, "Administrator")
		delivery.start_transit(name)
		email = "_t_drf_noperm@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc({"doctype": "User", "email": email, "first_name": "NoPermDRF", "send_welcome_email": 0}).insert(
				ignore_permissions=True
			)
		frappe.set_user(email)
		try:
			with self.assertRaises(frappe.PermissionError):
				delivery.handover(name)
		finally:
			frappe.set_user("Administrator")
