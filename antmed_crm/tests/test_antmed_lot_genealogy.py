# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M03 D3 (cây phả hệ truy vết lot) — inventory.lot_genealogy: lô → giao phòng mổ → hóa đơn — TDD.

Cover: lô gắn ở Delivery Item → trả deliveries[] có hospital_name/doctor_name/surgery/used_qty +
e-invoice; lô không có phiếu → []; lô không tồn tại perm → PermissionError; sort theo ca mổ.

Lệnh:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_lot_genealogy
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from antmed_crm.api.antmed import inventory

GENEALOGY_DELIVERY_KEYS = {
	"delivery",
	"status",
	"hospital",
	"hospital_name",
	"doctor",
	"doctor_name",
	"surgery_datetime",
	"surgery_room",
	"used_qty",
	"einvoice",
	"einvoice_status",
	"einvoice_pdf",
}


def _mk(dt, name, doc):
	if frappe.db.exists(dt, name):
		return frappe.get_doc(dt, name)
	return frappe.get_doc({"doctype": dt, **doc}).insert(ignore_permissions=True)


class TestLotGenealogy(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.item = _mk(
			"AntMed Item", "_T-GEN-ITEM", {"item_code": "_T-GEN-ITEM", "item_name": "Chỉ Vicryl GEN"}
		).name
		cls.lot = _mk(
			"AntMed Lot",
			"_T-GEN-LOT",
			{"lot_no": "_T-GEN-LOT", "item": cls.item, "expiry_date": "2028-12-31"},
		).name
		cls.lot_empty = _mk(
			"AntMed Lot",
			"_T-GEN-LOT-EMPTY",
			{"lot_no": "_T-GEN-LOT-EMPTY", "item": cls.item, "expiry_date": "2028-12-31"},
		).name
		cls.hosp = _mk(
			"AntMed Hospital", "_T-GEN-BV", {"hospital_code": "_T-GEN-BV", "hospital_name": "BV Việt Đức GEN"}
		).name
		cls.doctor = _mk(
			"AntMed Doctor",
			"_T-GEN-BS",
			{"doctor_code": "_T-GEN-BS", "full_name": "BS. Hùng GEN", "hospital": cls.hosp},
		).name

		# 2 phiếu giao dùng lô (ca sớm + ca muộn) → kiểm sort + used_qty.
		cls.del1 = (
			frappe.get_doc(
				{
					"doctype": "AntMed Delivery",
					"hospital": cls.hosp,
					"doctor": cls.doctor,
					"surgery_datetime": "2026-05-03 14:30:00",
					"surgery_room": "P.Mổ 1",
					"status": "Nháp",
					"items": [{"item": cls.item, "lot": cls.lot, "requested_qty": 30, "consumed_qty": 30}],
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
		cls.del2 = (
			frappe.get_doc(
				{
					"doctype": "AntMed Delivery",
					"hospital": cls.hosp,
					"doctor": cls.doctor,
					"surgery_datetime": "2026-05-05 09:00:00",
					"status": "Nháp",
					"items": [{"item": cls.item, "lot": cls.lot, "requested_qty": 40, "delivered_qty": 40}],
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
		# E-Invoice gắn phiếu 1.
		cls.einv = (
			frappe.get_doc(
				{
					"doctype": "AntMed E-Invoice",
					"delivery": cls.del1,
					"status": "Đã phát hành",
					"pdf_file": "/files/hd1.pdf",
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def test_genealogy_shape(self):
		res = inventory.lot_genealogy(self.lot)
		self.assertEqual(set(res.keys()), {"lot", "item", "item_name", "deliveries"})
		self.assertEqual(res["lot"], self.lot)
		self.assertEqual(res["item"], self.item)
		self.assertEqual(res["item_name"], "Chỉ Vicryl GEN")
		self.assertEqual(len(res["deliveries"]), 2)
		for d in res["deliveries"]:
			self.assertEqual(set(d.keys()), GENEALOGY_DELIVERY_KEYS, msg=f"shape lệch: {set(d.keys())}")

	def test_genealogy_resolves_and_used_qty(self):
		res = inventory.lot_genealogy(self.lot)
		by_del = {d["delivery"]: d for d in res["deliveries"]}
		d1 = by_del[self.del1]
		self.assertEqual(d1["hospital_name"], "BV Việt Đức GEN")
		self.assertEqual(d1["doctor_name"], "BS. Hùng GEN")
		self.assertEqual(str(d1["surgery_datetime"]), "2026-05-03 14:30:00")
		self.assertEqual(d1["used_qty"], 30.0)  # consumed_qty
		self.assertEqual(d1["einvoice"], self.einv)
		self.assertEqual(d1["einvoice_status"], "Đã phát hành")
		self.assertEqual(d1["einvoice_pdf"], "/files/hd1.pdf")
		# Phiếu 2: dùng delivered_qty (không có consumed) = 40; chưa có hóa đơn.
		d2 = by_del[self.del2]
		self.assertEqual(d2["used_qty"], 40.0)
		self.assertIsNone(d2["einvoice"])

	def test_genealogy_sorted_by_surgery(self):
		"""Ca sớm (03/05 14:30) trước ca muộn (05/05 09:00)."""
		res = inventory.lot_genealogy(self.lot)
		self.assertEqual(res["deliveries"][0]["delivery"], self.del1)
		self.assertEqual(res["deliveries"][1]["delivery"], self.del2)

	def test_genealogy_lot_without_delivery(self):
		res = inventory.lot_genealogy(self.lot_empty)
		self.assertEqual(res["deliveries"], [])
		self.assertEqual(res["item"], self.item)

	def test_genealogy_fail_closed_no_delivery_perm(self):
		"""Thiếu read-perm AntMed Delivery → deliveries:[] (KHÔNG rò)."""
		from unittest.mock import patch

		def _deny(doctype, *a, **kw):
			return doctype != "AntMed Delivery"

		with patch.object(frappe, "has_permission", side_effect=_deny):
			res = inventory.lot_genealogy(self.lot)
		self.assertEqual(res["deliveries"], [])


class TestLotTraceRequest(FrappeTestCase):
	"""save_lot_trace / list_lot_traces / get_lot_trace_request — lưu vết audit/recall."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.item = _mk(
			"AntMed Item", "_T-LTR-ITEM", {"item_code": "_T-LTR-ITEM", "item_name": "VT lưu vết"}
		).name
		cls.lot = _mk(
			"AntMed Lot",
			"_T-LTR-LOT",
			{"lot_no": "_T-LTR-LOT", "item": cls.item, "expiry_date": "2028-12-31"},
		).name
		cls.hosp = _mk(
			"AntMed Hospital", "_T-LTR-BV", {"hospital_code": "_T-LTR-BV", "hospital_name": "BV Lưu Vết"}
		).name
		cls.dlv = (
			frappe.get_doc(
				{
					"doctype": "AntMed Delivery",
					"hospital": cls.hosp,
					"surgery_datetime": "2026-05-03 14:30:00",
					"status": "Nháp",
					"items": [{"item": cls.item, "lot": cls.lot, "requested_qty": 10, "consumed_qty": 10}],
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def test_doctype_exists(self):
		self.assertTrue(frappe.db.exists("DocType", "AntMed Lot Trace Request"))
		series = frappe.get_meta("AntMed Lot Trace Request").get_field("naming_series").options
		self.assertIn("AM-LTR-", series)

	def test_save_lot_trace(self):
		res = inventory.save_lot_trace(self.lot, note="Truy vết recall test")
		self.assertTrue(res["name"])
		self.assertEqual(res["affected_hospitals"], 1)  # 1 BV trong phả hệ
		# Bản ghi lưu graph_json snapshot.
		doc = frappe.get_doc("AntMed Lot Trace Request", res["name"])
		self.assertEqual(doc.lot, self.lot)
		self.assertEqual(doc.lot_no, self.lot)
		self.assertEqual(doc.requested_by, "Administrator")
		graph = frappe.parse_json(doc.graph_json)
		self.assertIn("lot_info", graph)
		self.assertIn("deliveries", graph)
		self.assertEqual(len(graph["deliveries"]), 1)

	def test_list_and_get_lot_trace(self):
		saved = inventory.save_lot_trace(self.lot)["name"]
		lst = inventory.list_lot_traces(lot=self.lot, page_length=0)
		self.assertEqual(set(lst.keys()), {"data", "total_count"})
		self.assertEqual(len(lst["data"]), lst["total_count"])
		self.assertIn(saved, {r["name"] for r in lst["data"]})
		row = next(r for r in lst["data"] if r["name"] == saved)
		self.assertEqual(set(row.keys()), set(inventory.LTR_LIST_ITEM_KEYS))
		# get detail → graph parse có deliveries.
		detail = inventory.get_lot_trace_request(saved)
		self.assertEqual(detail["lot"], self.lot)
		self.assertEqual(detail["affected_hospitals"], 1)
		self.assertIn("deliveries", detail["graph"])
		self.assertEqual(len(detail["graph"]["deliveries"]), 1)

	def test_get_not_found(self):
		with self.assertRaises(frappe.DoesNotExistError):
			inventory.get_lot_trace_request("_T-LTR-KHONG-TON-TAI")

	def test_export_pdf(self):
		"""export_lot_trace_pdf → sinh PDF + đính kèm exported_pdf."""
		saved = inventory.save_lot_trace(self.lot)["name"]
		res = inventory.export_lot_trace_pdf(saved)
		self.assertTrue(res["exported_pdf"])
		self.assertTrue(res["exported_pdf"].endswith(".pdf"))
		self.assertEqual(
			frappe.db.get_value("AntMed Lot Trace Request", saved, "exported_pdf"), res["exported_pdf"]
		)
		self.assertTrue(
			frappe.db.exists(
				"File", {"attached_to_doctype": "AntMed Lot Trace Request", "attached_to_name": saved}
			),
			"phải tạo File PDF đính kèm",
		)
