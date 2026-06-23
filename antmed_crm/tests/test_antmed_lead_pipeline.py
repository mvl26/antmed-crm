# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M08 Slice S3 (BE) — Lead pipeline: get_lead + convert_lead_to_tender + lead_funnel.

Hoàn thiện trang /antmed/leads theo mockup (funnel Lead→Khảo sát→Báo giá→Dự thầu→Trúng) +
nối CRM Lead → AntMed Tender (qualify thành gói thầu):
  test_get_lead          — chi tiết lead (kế thừa CRM Lead) + tender link.
  test_convert_to_tender — lead → AntMed Tender (source_lead), idempotent.
  test_lead_funnel       — {stages:[lead, khảo sát, báo giá, dự thầu, trúng]} có count.

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_lead_pipeline
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from antmed_crm.api.antmed import pipeline


class TestAntMedLeadPipeline(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.lead = (
			frappe.get_doc(
				{
					"doctype": "CRM Lead",
					"first_name": "BV Tiềm Năng Test",
					"organization": "BV Tiềm Năng Test",
					"status": "New",
					"lead_owner": "Administrator",
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def test_get_lead(self):
		res = pipeline.get_lead(self.lead)
		self.assertEqual(res["name"], self.lead)
		self.assertIn("status", res)
		self.assertIn("tender", res)  # link tới gói thầu (None nếu chưa convert)

	def test_convert_to_tender(self):
		res = pipeline.convert_lead_to_tender(self.lead, estimated_value=3000000000)
		self.assertEqual(res["lead"], self.lead)
		self.assertTrue(res["created"])
		tender = res["tender"]
		self.assertTrue(frappe.db.exists("AntMed Tender", tender))
		self.assertEqual(frappe.db.get_value("AntMed Tender", tender, "source_lead"), self.lead)
		# idempotent: convert lần 2 → KHÔNG tạo tender mới
		res2 = pipeline.convert_lead_to_tender(self.lead)
		self.assertEqual(res2["tender"], tender)
		self.assertFalse(res2["created"])

	def test_lead_funnel(self):
		res = pipeline.lead_funnel()
		self.assertIn("stages", res)
		keys = [s["key"] for s in res["stages"]]
		self.assertEqual(keys, ["lead", "khao_sat", "bao_gia", "du_thau", "trung"])
		for s in res["stages"]:
			self.assertIn("count", s)
			self.assertGreaterEqual(s["count"], 0)
