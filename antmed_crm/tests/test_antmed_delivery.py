# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M04 Slice S1 (BE) — Giao phòng mổ: AntMed Delivery + Delivery Item + read API — TDD viết TRƯỚC.

Cover m04_or_delivery.md §2 (Delivery/Item) + §5 (list_deliveries/get_delivery) + §10:
  test_doctypes_and_naming  — DocType tồn tại; Delivery submittable + naming AntMed-DR; Item child istable.
  test_create_delivery      — tạo phiếu giao → name khớp ^AntMed-DR-YYYY-\\d+; status mặc định 'Nháp'.
  test_list_deliveries_shape— {data,total_count}; item đúng key; count==rows.
  test_list_filter          — lọc theo hospital + status.
  test_get_delivery         — detail + items[] + hospital_name/doctor_name resolve; PermissionError nếu không read.
  test_docperm_vietnamese   — role VI (Quản lý/NV kinh doanh/Thủ kho), KHÔNG AM System Admin.

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_delivery
"""

import re

import frappe
from frappe.tests.utils import FrappeTestCase

from antmed_crm.api.antmed import delivery

DR_NAME_RE = re.compile(r"^AntMed-DR-\d{4}-\d+")
DELIVERY_MIN_FIELDS = {
	"hospital",
	"doctor",
	"surgery_room",
	"surgery_datetime",
	"sla_minutes",
	"contract",
	"assigned_employee",
	"status",
	"delivered_at",
	"sla_status",
	"items",
}
DELIVERY_ITEM_FIELDS = {"item", "item_name", "requested_qty", "delivered_qty", "consumed_qty", "returned_qty", "lot"}
# Shape list_deliveries — đã mở rộng (factory): + doctor_name + assigned_employee_name (enrich cho FE điều phối).
LIST_KEYS = {
	"name",
	"hospital",
	"hospital_name",
	"doctor",
	"doctor_name",
	"surgery_datetime",
	"status",
	"sla_status",
	"assigned_employee",
	"assigned_employee_name",
}


def _mk_hospital(code, name):
	if frappe.db.exists("AntMed Hospital", code):
		return frappe.get_doc("AntMed Hospital", code)
	return frappe.get_doc({"doctype": "AntMed Hospital", "hospital_code": code, "hospital_name": name}).insert(
		ignore_permissions=True
	)


def _mk_doctor(code, name, hospital):
	if frappe.db.exists("AntMed Doctor", {"doctor_code": code}):
		return frappe.get_doc("AntMed Doctor", {"doctor_code": code})
	return frappe.get_doc(
		{"doctype": "AntMed Doctor", "doctor_code": code, "full_name": name, "hospital": hospital}
	).insert(ignore_permissions=True)


def _mk_item(code, name):
	if frappe.db.exists("AntMed Item", code):
		return frappe.get_doc("AntMed Item", code)
	return frappe.get_doc({"doctype": "AntMed Item", "item_code": code, "item_name": name}).insert(
		ignore_permissions=True
	)


def _mk_delivery(hospital, doctor, items, **kw):
	doc = frappe.get_doc(
		{
			"doctype": "AntMed Delivery",
			"hospital": hospital,
			"doctor": doctor,
			"surgery_room": kw.pop("surgery_room", "Phòng mổ 1"),
			"surgery_datetime": kw.pop("surgery_datetime", "2026-07-01 08:00:00"),
			"items": items,
			**kw,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


class TestAntMedDelivery(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hosp = _mk_hospital("_T-DR-BV", "BV Giao Phòng Mổ").name
		cls.hosp2 = _mk_hospital("_T-DR-BV2", "BV Khác DR").name
		cls.doctor = _mk_doctor("_T-DR-BS", "BS Giao Phòng Mổ", cls.hosp).name
		cls.item = _mk_item("_T-DR-VTYT", "Stent giao test").name
		cls.dr1 = _mk_delivery(
			cls.hosp,
			cls.doctor,
			items=[{"item": cls.item, "item_name": "Stent giao test", "requested_qty": 2, "uom": "Cái"}],
			status="Đã gán NV",
		).name
		cls.dr2 = _mk_delivery(cls.hosp2, None, items=[{"item": cls.item, "requested_qty": 1}], status="Nháp").name

	def test_doctypes_and_naming(self):
		self.assertTrue(frappe.db.exists("DocType", "AntMed Delivery"))
		self.assertTrue(frappe.db.exists("DocType", "AntMed Delivery Item"))
		self.assertEqual(frappe.get_meta("AntMed Delivery").is_submittable, 1)
		self.assertEqual(frappe.get_meta("AntMed Delivery Item").istable, 1)
		dfields = {f.fieldname for f in frappe.get_meta("AntMed Delivery").fields}
		self.assertTrue(DELIVERY_MIN_FIELDS.issubset(dfields), msg=f"thiếu: {DELIVERY_MIN_FIELDS - dfields}")
		ifields = {f.fieldname for f in frappe.get_meta("AntMed Delivery Item").fields}
		self.assertTrue(DELIVERY_ITEM_FIELDS.issubset(ifields), msg=f"thiếu: {DELIVERY_ITEM_FIELDS - ifields}")

	def test_create_delivery(self):
		self.assertRegex(self.dr1, DR_NAME_RE)
		self.assertEqual(frappe.db.get_value("AntMed Delivery", self.dr2, "status"), "Nháp")

	def test_list_deliveries_shape(self):
		res = delivery.list_deliveries(page_length=0)
		self.assertEqual(set(res.keys()), {"data", "total_count"})
		self.assertGreaterEqual(len(res["data"]), 2)
		self.assertEqual(set(res["data"][0].keys()), LIST_KEYS)
		self.assertEqual(len(res["data"]), res["total_count"])

	def test_list_filter(self):
		res = delivery.list_deliveries(filters={"hospital": self.hosp}, page_length=0)
		names = {r["name"] for r in res["data"]}
		self.assertIn(self.dr1, names)
		self.assertNotIn(self.dr2, names)
		row = next(r for r in res["data"] if r["name"] == self.dr1)
		self.assertEqual(row["hospital_name"], "BV Giao Phòng Mổ")
		res2 = delivery.list_deliveries(status="Nháp", page_length=0)
		self.assertIn(self.dr2, {r["name"] for r in res2["data"]})
		self.assertNotIn(self.dr1, {r["name"] for r in res2["data"]})

	def test_get_delivery(self):
		res = delivery.get_delivery(self.dr1)
		self.assertEqual(res["name"], self.dr1)
		self.assertEqual(res["hospital_name"], "BV Giao Phòng Mổ")
		self.assertEqual(res["doctor_name"], "BS Giao Phòng Mổ")
		self.assertEqual(len(res["items"]), 1)
		self.assertEqual(res["items"][0]["item"], self.item)
		# permission guard
		email = "_t_dr_noperm@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc({"doctype": "User", "email": email, "first_name": "NoPermDR", "send_welcome_email": 0}).insert(
				ignore_permissions=True
			)
		frappe.set_user(email)
		try:
			with self.assertRaises(frappe.PermissionError):
				delivery.get_delivery(self.dr1)
		finally:
			frappe.set_user("Administrator")

	def test_docperm_vietnamese(self):
		perms = {p.role for p in frappe.get_meta("AntMed Delivery").permissions}
		self.assertIn("Quản lý", perms)
		self.assertIn("NV kinh doanh", perms)
		self.assertIn("Thủ kho", perms)
		self.assertNotIn("AM System Admin", perms)
