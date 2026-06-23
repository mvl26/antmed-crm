# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M06 Slice S2 (BE) — Gắn CO/CQ + kiểm tra điều kiện phát hành (BR-03): attach_cocq/list_cocq_store/check_release.

Cover m06_documents.md §5 (attach_cocq/list_cocq_store) + §4 (BR-03):
  test_attach_co_cq         — attach_cocq 'CO' → lô.co_cert set; 'CQ' → lô.cq_cert set.
  test_list_cocq_store      — {data,total_count} count==rows + filter cert_type.
  test_check_release        — delivery thiếu CO/CQ → can_release False; gắn đủ → True.
  test_attach_permission    — user không create cert → PermissionError.

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_cocq
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from antmed_crm.api.antmed import documents


def _ensure(doctype, key, val, values):
	name = frappe.db.get_value(doctype, {key: val}, "name")
	return (
		name or frappe.get_doc({"doctype": doctype, key: val, **values}).insert(ignore_permissions=True).name
	)


class TestAntMedCoCq(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hosp = _ensure("AntMed Hospital", "hospital_code", "_T-COCQ-BV", {"hospital_name": "BV CoCq"})
		cls.item = _ensure(
			"AntMed Item", "item_code", "_T-COCQ-STENT", {"item_name": "Stent CoCq", "requires_cocq": 1}
		)

	def _fresh_lot(self, suffix):
		return (
			frappe.get_doc(
				{
					"doctype": "AntMed Lot",
					"lot_no": f"_T-COCQ-LOT-{suffix}",
					"item": self.item,
					"expiry_date": "2027-12-31",
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def _mk_delivery(self, lot):
		return (
			frappe.get_doc(
				{
					"doctype": "AntMed Delivery",
					"hospital": self.hosp,
					"surgery_datetime": "2026-08-01 08:00:00",
					"items": [{"item": self.item, "lot": lot, "requested_qty": 1}],
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def test_attach_co_cq(self):
		lot = self._fresh_lot("ATT")
		documents.attach_cocq(lot=lot, cert_type="CO", cert_no="CO-ATT-1")
		documents.attach_cocq(lot=lot, cert_type="CQ", cert_no="CQ-ATT-1")
		self.assertIsNotNone(frappe.db.get_value("AntMed Lot", lot, "co_cert"))
		self.assertIsNotNone(frappe.db.get_value("AntMed Lot", lot, "cq_cert"))

	def test_list_cocq_store(self):
		lot = self._fresh_lot("STORE")
		documents.attach_cocq(lot=lot, cert_type="CO", cert_no="CO-STORE-1")
		res = documents.list_cocq_store(page_length=0)
		self.assertEqual(set(res.keys()), {"data", "total_count"})
		self.assertEqual(len(res["data"]), res["total_count"])
		res_co = documents.list_cocq_store(cert_type="CO", page_length=0)
		self.assertTrue(all(r["cert_type"] == "CO" for r in res_co["data"]))

	def test_check_release(self):
		lot = self._fresh_lot("REL")
		dlv = self._mk_delivery(lot)
		before = documents.check_release(dlv)
		self.assertFalse(before["can_release"])
		self.assertIn(self.item, before["missing"])
		documents.attach_cocq(lot=lot, cert_type="CO", cert_no="CO-REL-1")
		documents.attach_cocq(lot=lot, cert_type="CQ", cert_no="CQ-REL-1")
		after = documents.check_release(dlv)
		self.assertTrue(after["can_release"])
		self.assertEqual(after["missing"], [])

	def test_attach_permission(self):
		lot = self._fresh_lot("PERM")
		email = "_t_cocq_noperm@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": "NoPermCoCq", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.set_user(email)
		try:
			with self.assertRaises(frappe.PermissionError):
				documents.attach_cocq(lot=lot, cert_type="CO", cert_no="CO-PERM-1")
		finally:
			frappe.set_user("Administrator")
