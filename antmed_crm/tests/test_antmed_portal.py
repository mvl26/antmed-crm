# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M09 Slice S2 (BE) — Portal flow: NV nhận yêu cầu → tạo phiếu giao + Lịch sử (mockup G1/G2).

  test_receive          — receive_material_request → 'NV đã nhận' + assigned_employee.
  test_convert_delivery — convert_to_delivery → tạo AntMed Delivery (items khớp) + MR 'Đã tạo
                          phiếu giao' + delivery_ref.
  test_portal_history   — portal_history(hospital) liệt kê phiếu giao của BV (G2), count==rows.

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_portal
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from antmed_crm.api.antmed import customer


def _ensure(doctype, key, val, values):
	return frappe.db.get_value(doctype, {key: val}, "name") or frappe.get_doc({"doctype": doctype, key: val, **values}).insert(ignore_permissions=True).name


class TestAntMedPortal(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hosp = _ensure("AntMed Hospital", "hospital_code", "_T-PORTAL-BV", {"hospital_name": "BV Portal Flow"})
		cls.doctor = _ensure("AntMed Doctor", "doctor_code", "_T-PORTAL-BS", {"full_name": "BS Portal", "hospital": cls.hosp})
		cls.item = _ensure("AntMed Item", "item_code", "VTYT-PORTAL", {"item_name": "VT Portal"})

	def _mk_request(self):
		return customer.create_material_request(
			hospital=self.hosp,
			items=[{"item": self.item, "requested_qty": 4}],
			doctor=self.doctor,
			surgery_datetime=str(add_to_date(now_datetime(), hours=5)),
			surgery_room="PM4",
		)["name"]

	def test_receive(self):
		mr = self._mk_request()
		res = customer.receive_material_request(mr)
		self.assertEqual(res["status"], "NV đã nhận")
		self.assertEqual(frappe.db.get_value("AntMed Material Request", mr, "assigned_employee"), "Administrator")

	def test_convert_delivery(self):
		mr = self._mk_request()
		customer.receive_material_request(mr)
		res = customer.convert_to_delivery(mr)
		dlv = res["delivery"]
		self.assertTrue(frappe.db.exists("AntMed Delivery", dlv))
		self.assertEqual(frappe.db.get_value("AntMed Material Request", mr, "status"), "Đã tạo phiếu giao")
		self.assertEqual(frappe.db.get_value("AntMed Material Request", mr, "delivery_ref"), dlv)
		# items chuyển sang phiếu giao
		dlv_items = frappe.get_all("AntMed Delivery Item", filters={"parent": dlv}, fields=["item", "requested_qty"])
		self.assertEqual(dlv_items[0]["item"], self.item)
		self.assertEqual(dlv_items[0]["requested_qty"], 4)

	def test_portal_history(self):
		mr = self._mk_request()
		customer.receive_material_request(mr)
		customer.convert_to_delivery(mr)
		res = customer.portal_history(hospital=self.hosp, page_length=0)
		self.assertEqual(set(res.keys()), {"data", "total_count"})
		self.assertEqual(len(res["data"]), res["total_count"])
		self.assertGreaterEqual(res["total_count"], 1)
		row = res["data"][0]
		for k in ("delivery", "doctor_name", "sku_count", "has_documents", "payment_status"):
			self.assertIn(k, row)
