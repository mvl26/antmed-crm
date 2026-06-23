# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M02 Slice M02-2 (BE) — endpoint list_quota_alerts (cảnh báo điều hành) — TDD viết TRƯỚC.

Cover spec m02_contract_quota.md §4 (Quota alert 70/90/100%) + §5 (list_quota_alerts):
  test_alert_shape_and_count_eq_rows — {data,total_count}; mỗi alert đúng 10 key; total_count==len(data).
  test_quota_threshold_bands         — used_pct ≥70/90/100 → threshold đúng band (70/90/100).
  test_below_70_no_quota_alert       — used_pct <70 → KHÔNG sinh quota alert.
  test_expiry_alert                  — HĐ còn ≤30 ngày → alert kind 'expiry' + days_to_expiry đúng.
  test_no_leak_for_noperm_user       — user không read → total_count 0 + data rỗng (fail-closed).

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_quota_alerts
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from antmed_crm.api.antmed import contract

ALERT_KEYS = {
	"kind",
	"contract",
	"contract_no",
	"hospital",
	"hospital_name",
	"item",
	"item_name",
	"used_pct",
	"threshold",
	"days_to_expiry",
}


def _mk_hospital(code, name):
	if frappe.db.exists("AntMed Hospital", code):
		return frappe.get_doc("AntMed Hospital", code)
	doc = frappe.get_doc({"doctype": "AntMed Hospital", "hospital_code": code, "hospital_name": name})
	doc.insert(ignore_permissions=True)
	return doc


def _item(code, quota, used):
	pct = round((1 - used / quota) * 100, 2) if quota else 0
	return {
		"item": code,
		"item_name": f"VT {code}",
		"uom": "Cái",
		"unit_price": 1000000,
		"quota_qty": quota,
		"used_qty": used,
		"remaining_pct": pct,
		"lock_at_100": 1,
	}


def _mk_contract(contract_no, hospital, items, valid_to):
	doc = frappe.get_doc(
		{
			"doctype": "AntMed Contract",
			"contract_no": contract_no,
			"hospital": hospital,
			"signed_date": "2026-01-05",
			"valid_from": "2026-01-05",
			"valid_to": valid_to,
			"status": "Hiệu lực",
			"total_value": 1000000000,
			"items": items,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


class TestAntMedQuotaAlerts(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hosp = _mk_hospital("_T-HOSP-QA", "BV Alerts").name
		far = add_days(nowdate(), 400)  # không kích expiry alert
		cls.ct70 = _mk_contract("_T-QA-70", cls.hosp, [_item("VTYT-70", 100, 70)], far).name  # 70%
		cls.ct90 = _mk_contract("_T-QA-90", cls.hosp, [_item("VTYT-90", 100, 95)], far).name  # 95% → band 90
		cls.ct100 = _mk_contract("_T-QA-100", cls.hosp, [_item("VTYT-100", 100, 100)], far).name  # 100%
		cls.ct_below = _mk_contract(
			"_T-QA-LOW", cls.hosp, [_item("VTYT-LOW", 100, 50)], far
		).name  # 50% → no alert
		cls.ct_exp = _mk_contract(
			"_T-QA-EXP", cls.hosp, [_item("VTYT-EXP", 100, 0)], add_days(nowdate(), 10)
		).name  # 0% nhưng còn 10 ngày → expiry alert

	def _alerts(self):
		return contract.list_quota_alerts()["data"]

	def _find(self, data, contract_name, kind):
		return next((a for a in data if a["contract"] == contract_name and a["kind"] == kind), None)

	def test_alert_shape_and_count_eq_rows(self):
		res = contract.list_quota_alerts()
		self.assertEqual(set(res.keys()), {"data", "total_count"})
		self.assertGreaterEqual(len(res["data"]), 4)  # 70/90/100 quota + 1 expiry
		self.assertEqual(set(res["data"][0].keys()), ALERT_KEYS)
		self.assertEqual(len(res["data"]), res["total_count"])

	def test_quota_threshold_bands(self):
		data = self._alerts()
		self.assertEqual(self._find(data, self.ct70, "quota")["threshold"], 70)
		self.assertEqual(self._find(data, self.ct90, "quota")["threshold"], 90)
		a100 = self._find(data, self.ct100, "quota")
		self.assertEqual(a100["threshold"], 100)
		self.assertEqual(a100["used_pct"], 100.0)
		self.assertEqual(a100["item"], "VTYT-100")

	def test_below_70_no_quota_alert(self):
		self.assertIsNone(self._find(self._alerts(), self.ct_below, "quota"))

	def test_expiry_alert(self):
		data = self._alerts()
		exp = self._find(data, self.ct_exp, "expiry")
		self.assertIsNotNone(exp)
		self.assertEqual(exp["days_to_expiry"], 10)
		# 0% dùng → KHÔNG có quota alert cho HĐ này
		self.assertIsNone(self._find(data, self.ct_exp, "quota"))

	def test_no_leak_for_noperm_user(self):
		email = "_t_qa_noperm@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": "NoPermQA", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		self.assertGreaterEqual(contract.list_quota_alerts()["total_count"], 4)
		frappe.set_user(email)
		try:
			try:
				res = contract.list_quota_alerts()
			except frappe.PermissionError:
				return
			self.assertEqual(res["total_count"], 0, msg=f"LEAK: {res}")
			self.assertEqual(len(res["data"]), 0, msg=f"LEAK rows: {res}")
		finally:
			frappe.set_user("Administrator")
