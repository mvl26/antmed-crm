# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M08 Slice S2 (BE) — Forecast + BR-M08-05 (Trúng → tạo HĐ nháp): pipeline.forecast/set_tender_result.

Cover m08_pipeline.md §5 (forecast) + §4 (BR-M08-05):
  test_forecast_shape     — forecast() trả {total_weighted, by_stage[]}; số hợp lệ.
  test_win_creates_contract — set_tender_result('Trúng') → tạo HĐ nháp + tender.won_contract.
  test_win_idempotent     — gọi 2 lần → KHÔNG tạo HĐ thứ 2 (won_contract giữ nguyên).

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_pipeline_forecast
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from antmed_crm.api.antmed import pipeline


def _ensure(doctype, key, val, values):
	return frappe.db.get_value(doctype, {key: val}, "name") or frappe.get_doc({"doctype": doctype, key: val, **values}).insert(ignore_permissions=True).name


class TestAntMedPipelineForecast(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hosp = _ensure("AntMed Hospital", "hospital_code", "_T-FC-BV", {"hospital_name": "BV Forecast"})

	def test_forecast_shape(self):
		t = pipeline.create_tender(tender_no="_T-FC-001", tender_name="Gói FC", hospital=self.hosp, estimated_value=1000000000)["name"]
		frappe.db.set_value("AntMed Tender", t, "win_probability_pct", 60)
		res = pipeline.forecast()
		self.assertEqual(set(res.keys()), {"total_weighted", "by_stage"})
		self.assertIsInstance(res["by_stage"], list)
		self.assertGreaterEqual(res["total_weighted"], 0)

	def test_win_creates_contract(self):
		t = pipeline.create_tender(tender_no="_T-FC-WIN", tender_name="Gói thắng", hospital=self.hosp, estimated_value=2000000000)["name"]
		pipeline.set_tender_result(t, result="Trúng", decision_no="QĐ-FC-1")
		won = frappe.db.get_value("AntMed Tender", t, "won_contract")
		self.assertIsNotNone(won)
		self.assertTrue(frappe.db.exists("AntMed Contract", won))
		self.assertEqual(frappe.db.get_value("AntMed Contract", won, "hospital"), self.hosp)

	def test_win_idempotent(self):
		t = pipeline.create_tender(tender_no="_T-FC-IDEM", tender_name="Gói idem", hospital=self.hosp, estimated_value=500000000)["name"]
		pipeline.set_tender_result(t, result="Trúng", decision_no="QĐ-FC-2")
		won1 = frappe.db.get_value("AntMed Tender", t, "won_contract")
		pipeline.set_tender_result(t, result="Trúng", decision_no="QĐ-FC-2")
		won2 = frappe.db.get_value("AntMed Tender", t, "won_contract")
		self.assertEqual(won1, won2)
