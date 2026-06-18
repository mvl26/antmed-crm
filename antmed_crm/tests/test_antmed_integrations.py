# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M13 Slice S1 (BE) — Tích hợp (framework): AntMed Integration Setting + Log.

⚠️ KHÔNG gọi API thật (stub). Secrets (Password) KHÔNG bao giờ trả ra FE (BR-INT-01).
Cover m13_integrations.md §2/§5:
  test_doctypes              — Setting issingle; Log tồn tại.
  test_get_settings_masked   — get_settings KHÔNG lộ token/api_key thật.
  test_log_and_list          — _log tạo bản ghi; list_integration_logs count==rows (KHÔNG payload).
  test_get_and_retry_log     — get_integration_log detail; retry_log đổi status Retrying.

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_integrations
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from antmed_crm.api.antmed import integrations


class TestAntMedIntegrations(FrappeTestCase):
	def test_doctypes(self):
		self.assertTrue(frappe.db.exists("DocType", "AntMed Integration Setting"))
		self.assertTrue(frappe.db.exists("DocType", "AntMed Integration Log"))
		self.assertEqual(frappe.get_meta("AntMed Integration Setting").issingle, 1)

	def test_get_settings_masked(self):
		secret = "ZALO-SECRET-TOKEN-XYZ"
		s = frappe.get_doc("AntMed Integration Setting")
		s.zalo_oa_id = "OA123"
		s.zalo_access_token = secret
		s.save(ignore_permissions=True)
		res = integrations.get_settings()
		self.assertNotIn(secret, frappe.as_json(res))
		self.assertTrue(res.get("zalo_configured"))
		self.assertEqual(res.get("zalo_oa_id"), "OA123")

	def test_log_and_list(self):
		integrations._log("zalo", "Outbound", "/send", "Success", request_payload="hi", response_payload="ok")
		res = integrations.list_integration_logs(page_length=0)
		self.assertEqual(set(res.keys()), {"data", "total_count"})
		self.assertEqual(len(res["data"]), res["total_count"])
		# list KHÔNG kèm payload nặng
		self.assertNotIn("request_payload", res["data"][0])

	def test_get_and_retry_log(self):
		name = integrations._log("sms", "Outbound", "/sms", "Failed", error_message="timeout")
		detail = integrations.get_integration_log(name)
		self.assertEqual(detail["name"], name)
		self.assertEqual(detail["status"], "Failed")
		res = integrations.retry_log(name)
		self.assertEqual(res["status"], "Retrying")
		self.assertEqual(frappe.db.get_value("AntMed Integration Log", name, "status"), "Retrying")
