# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M06 Slice S4 (BE) — Ký nhận BV: AntMed Handover Confirmation + confirm_handover/list_handover_review.

Cover m06_documents.md §2 (Handover Confirmation) + §5:
  test_doctype             — tồn tại, submittable, naming AM-HC; hash_sha256 read_only.
  test_confirm_handover    — confirm → bản ghi submit, bundle 'BV đã ký nhận', hash set.
  test_confirm_idempotent  — 2 lần / 1 phiếu → cùng 1 bản ghi.
  test_list_handover_review— {data,total_count} count==rows.
  test_permission          — user không create → PermissionError.

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_handover
"""

import re

import frappe
from frappe.tests.utils import FrappeTestCase

from antmed_crm.api.antmed import documents

HC_NAME_RE = re.compile(r"^AM-HC-\d{4}-\d+")


def _ensure(doctype, key, val, values):
	name = frappe.db.get_value(doctype, {key: val}, "name")
	return (
		name or frappe.get_doc({"doctype": doctype, key: val, **values}).insert(ignore_permissions=True).name
	)


class TestAntMedHandover(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hosp = _ensure("AntMed Hospital", "hospital_code", "_T-HC-BV", {"hospital_name": "BV Ký Nhận"})
		cls.item = _ensure(
			"AntMed Item", "item_code", "_T-HC-GAC", {"item_name": "Gạc ký nhận", "requires_cocq": 0}
		)

	def _delivery_bundle(self, suffix):
		dlv = (
			frappe.get_doc(
				{
					"doctype": "AntMed Delivery",
					"hospital": self.hosp,
					"surgery_datetime": "2026-08-01 08:00:00",
					"items": [{"item": self.item, "requested_qty": 1}],
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
		documents.create_bundle(dlv)
		return dlv

	def test_doctype(self):
		self.assertTrue(frappe.db.exists("DocType", "AntMed Handover Confirmation"))
		meta = frappe.get_meta("AntMed Handover Confirmation")
		self.assertEqual(meta.is_submittable, 1)
		self.assertEqual(meta.get_field("hash_sha256").read_only, 1)

	def test_confirm_handover(self):
		dlv = self._delivery_bundle("OK")
		res = documents.confirm_handover(delivery=dlv, hospital_contact="ĐD Nguyễn Thị A")
		self.assertRegex(res["handover"], HC_NAME_RE)
		self.assertIsNotNone(res["hash"])
		self.assertEqual(frappe.db.get_value("AntMed Handover Confirmation", res["handover"], "docstatus"), 1)
		bundle = frappe.db.get_value("AntMed Document", {"delivery": dlv}, "name")
		self.assertEqual(frappe.db.get_value("AntMed Document", bundle, "status"), "BV đã ký nhận")

	def test_confirm_idempotent(self):
		dlv = self._delivery_bundle("IDEM")
		a = documents.confirm_handover(delivery=dlv, hospital_contact="A")["handover"]
		b = documents.confirm_handover(delivery=dlv, hospital_contact="A")["handover"]
		self.assertEqual(a, b)

	def test_list_handover_review(self):
		dlv = self._delivery_bundle("LIST")
		documents.confirm_handover(delivery=dlv, hospital_contact="A")
		res = documents.list_handover_review(page_length=0)
		self.assertEqual(set(res.keys()), {"data", "total_count"})
		self.assertEqual(len(res["data"]), res["total_count"])

	def test_permission(self):
		dlv = self._delivery_bundle("PERM")
		email = "_t_hc_noperm@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": "NoPermHC", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.set_user(email)
		try:
			with self.assertRaises(frappe.PermissionError):
				documents.confirm_handover(delivery=dlv, hospital_contact="A")
		finally:
			frappe.set_user("Administrator")
