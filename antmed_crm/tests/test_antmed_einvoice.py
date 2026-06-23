# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M06 Slice S3 (BE) — Hóa đơn điện tử (STUB): AntMed E-Invoice + Provider + issue_einvoice.

⚠️ STUB dev-mode: KHÔNG gọi API provider thật, KHÔNG phát hành HĐĐT LIVE. Provider secrets
(api_key Password) KHÔNG bao giờ trả ra FE (BR-INT-01). Cover m06_documents.md §5 + §4:
  test_doctypes              — E-Invoice submittable + naming AM-EINV; Provider issingle.
  test_issue_blocked_by_br03 — issue khi thiếu CO/CQ → throw 'BR-03'.
  test_issue_stub_ok         — đủ CO/CQ → issue → E-Invoice 'Đã phát hành', ma_cqt set, docstatus 1, stub.
  test_issue_idempotent      — issue 2 lần / 1 phiếu → cùng 1 hóa đơn.
  test_list_einvoices        — {data,total_count} count==rows.
  test_provider_settings_masked — get_provider_settings KHÔNG lộ api_key thật.

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_einvoice
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from antmed_crm.api.antmed import documents


def _ensure(doctype, key, val, values):
	name = frappe.db.get_value(doctype, {key: val}, "name")
	return (
		name or frappe.get_doc({"doctype": doctype, key: val, **values}).insert(ignore_permissions=True).name
	)


class TestAntMedEInvoice(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hosp = _ensure("AntMed Hospital", "hospital_code", "_T-EINV-BV", {"hospital_name": "BV EInvoice"})
		cls.item = _ensure(
			"AntMed Item", "item_code", "_T-EINV-STENT", {"item_name": "Stent EInvoice", "requires_cocq": 1}
		)

	def _delivery_with_certs(self, suffix, attach=True):
		lot = (
			frappe.get_doc(
				{
					"doctype": "AntMed Lot",
					"lot_no": f"_T-EINV-LOT-{suffix}",
					"item": self.item,
					"expiry_date": "2027-12-31",
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
		dlv = (
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
		if attach:
			documents.attach_cocq(lot=lot, cert_type="CO", cert_no=f"CO-EINV-{suffix}")
			documents.attach_cocq(lot=lot, cert_type="CQ", cert_no=f"CQ-EINV-{suffix}")
		return dlv

	def test_doctypes(self):
		self.assertTrue(frappe.db.exists("DocType", "AntMed E-Invoice"))
		self.assertTrue(frappe.db.exists("DocType", "AntMed E-Invoice Provider"))
		self.assertEqual(frappe.get_meta("AntMed E-Invoice").is_submittable, 1)
		self.assertEqual(frappe.get_meta("AntMed E-Invoice Provider").issingle, 1)

	def test_issue_blocked_by_br03(self):
		dlv = self._delivery_with_certs("BR03", attach=False)  # thiếu CO/CQ
		with self.assertRaises(frappe.ValidationError) as cm:
			documents.issue_einvoice(dlv)
		self.assertIn("BR-03", str(cm.exception))

	def test_issue_stub_ok(self):
		dlv = self._delivery_with_certs("OK")
		res = documents.issue_einvoice(dlv)
		self.assertTrue(res.get("stub"))
		ev = res["einvoice"]
		self.assertTrue(ev.startswith("AM-EINV-"))
		self.assertEqual(frappe.db.get_value("AntMed E-Invoice", ev, "status"), "Đã phát hành")
		self.assertIsNotNone(frappe.db.get_value("AntMed E-Invoice", ev, "ma_cqt"))
		self.assertEqual(frappe.db.get_value("AntMed E-Invoice", ev, "docstatus"), 1)  # BR-04 immutable

	def test_issue_idempotent(self):
		dlv = self._delivery_with_certs("IDEM")
		a = documents.issue_einvoice(dlv)["einvoice"]
		b = documents.issue_einvoice(dlv)["einvoice"]
		self.assertEqual(a, b)

	def test_list_einvoices(self):
		dlv = self._delivery_with_certs("LIST")
		documents.issue_einvoice(dlv)
		res = documents.list_einvoices(page_length=0)
		self.assertEqual(set(res.keys()), {"data", "total_count"})
		self.assertEqual(len(res["data"]), res["total_count"])

	def test_provider_settings_masked(self):
		secret = "SUPER-SECRET-KEY-123"
		s = frappe.get_doc("AntMed E-Invoice Provider")
		s.default_provider = "Viettel"
		s.viettel_api_key = secret
		s.save(ignore_permissions=True)
		res = documents.get_provider_settings()
		# KHÔNG được lộ api_key thật ở bất kỳ giá trị nào
		self.assertNotIn(secret, frappe.as_json(res))
		self.assertTrue(res.get("viettel_configured"))
		self.assertEqual(res.get("default_provider"), "Viettel")
