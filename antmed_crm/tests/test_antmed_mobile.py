# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M12 Slice S1 (BE) — Mobile/PWA: AntMed Mobile Device/Sync Log + bootstrap/scan_lot/register_device.

Cover m12_mobile.md §2/§5:
  test_doctypes        — Mobile Device (autoname device_id) + Mobile Sync Log tồn tại.
  test_bootstrap       — bootstrap() trả bundle offline (server_ts + các collection list).
  test_scan_lot        — scan_lot(lô) → chi tiết; lô lạ → raise.
  test_register_device — upsert thiết bị (push token).

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_mobile
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from antmed_crm.api.antmed import mobile_sync


def _ensure(doctype, key, val, values):
	return (
		frappe.db.get_value(doctype, {key: val}, "name")
		or frappe.get_doc({"doctype": doctype, key: val, **values}).insert(ignore_permissions=True).name
	)


class TestAntMedMobile(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.item = _ensure("AntMed Item", "item_code", "_T-MOB-VTYT", {"item_name": "VT mobile"})
		cls.lot = _ensure(
			"AntMed Lot", "lot_no", "_T-MOB-LOT", {"item": cls.item, "expiry_date": "2027-12-31"}
		)

	def test_doctypes(self):
		self.assertTrue(frappe.db.exists("DocType", "AntMed Mobile Device"))
		self.assertTrue(frappe.db.exists("DocType", "AntMed Mobile Sync Log"))

	def test_bootstrap(self):
		res = mobile_sync.bootstrap()
		self.assertIn("server_ts", res)
		for k in ("doctors", "deliveries", "loans"):
			self.assertIn(k, res)
			self.assertIsInstance(res[k], list)

	def test_scan_lot(self):
		res = mobile_sync.scan_lot(self.lot)
		self.assertEqual(res["lot"], self.lot)
		self.assertEqual(res["item"], self.item)
		self.assertEqual(res["item_name"], "VT mobile")
		with self.assertRaises(frappe.DoesNotExistError):
			mobile_sync.scan_lot("_T-MOB-KHONGCO")

	def test_register_device(self):
		res = mobile_sync.register_device(
			device_id="DEV-TEST-1", push_token="tok-123", platform="android", app_version="1.0.0"
		)
		self.assertEqual(res["device_id"], "DEV-TEST-1")
		self.assertTrue(frappe.db.exists("AntMed Mobile Device", "DEV-TEST-1"))
		# upsert: gọi lại đổi token → vẫn 1 bản ghi
		mobile_sync.register_device(
			device_id="DEV-TEST-1", push_token="tok-456", platform="android", app_version="1.0.1"
		)
		self.assertEqual(frappe.db.count("AntMed Mobile Device", {"device_id": "DEV-TEST-1"}), 1)
		self.assertEqual(frappe.db.get_value("AntMed Mobile Device", "DEV-TEST-1", "push_token"), "tok-456")

	def test_register_device_idor_blocked(self):
		"""IDOR: user khác KHÔNG được chiếm/ghi đè thiết bị đã đăng ký bởi người khác (device takeover)."""
		ua = _ensure(
			"User", "email", "_t_mob_a@example.com", {"first_name": "Mob A", "send_welcome_email": 0}
		)
		ub = _ensure(
			"User", "email", "_t_mob_b@example.com", {"first_name": "Mob B", "send_welcome_email": 0}
		)
		frappe.set_user(ua)
		try:
			mobile_sync.register_device(device_id="DEV-IDOR", push_token="A-token")
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("AntMed Mobile Device", "DEV-IDOR", "user"), ua)
		# user B cố chiếm thiết bị của A → PermissionError, token của A KHÔNG đổi
		frappe.set_user(ub)
		try:
			with self.assertRaises(frappe.PermissionError):
				mobile_sync.register_device(device_id="DEV-IDOR", push_token="B-token")
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("AntMed Mobile Device", "DEV-IDOR", "user"), ua)
		self.assertEqual(frappe.db.get_value("AntMed Mobile Device", "DEV-IDOR", "push_token"), "A-token")
