# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M02 Slice M02-2 (BE) — endpoint get_contract_health (màn "Sức khỏe Hợp đồng") — TDD viết TRƯỚC.

Cover spec m02_contract_quota.md §5 (get_contract_health) + §7 (ngưỡng màu):
  test_shape_and_count_eq_rows  — {data,total_count}; item đúng 10 key; len(data)==total_count (BR-13).
  test_quota_used_pct_aggregate — quota_used_pct = 100*SUM(used)/SUM(quota) trên CÁC dòng item.
  test_days_to_expiry           — days_to_expiry = (valid_to - today).days; None nếu thiếu valid_to.
  test_color_green/orange/red_cap/red_expiry — cờ màu: xanh ≤80% / cam 80–100% / đỏ >100% hoặc ≤30 ngày.
  test_no_leak_for_noperm_user  — user không read → total_count 0 + data rỗng (count==rows, fail-closed).

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_contract_health
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from antmed_crm.api.antmed import contract

HEALTH_ITEM_KEYS = {
	"name",
	"contract_no",
	"hospital",
	"hospital_name",
	"valid_to",
	"total_value",
	"status",
	"quota_used_pct",
	"days_to_expiry",
	"health_color",
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


def _mk_contract(contract_no, hospital, items, valid_to, status="Hiệu lực"):
	doc = frappe.get_doc(
		{
			"doctype": "AntMed Contract",
			"contract_no": contract_no,
			"hospital": hospital,
			"signed_date": "2026-01-05",
			"valid_from": "2026-01-05",
			"valid_to": valid_to,
			"status": status,
			"total_value": 1000000000,
			"items": items,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


class TestAntMedContractHealth(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hosp = _mk_hospital("_T-HOSP-CH", "BV Health").name
		far = add_days(nowdate(), 400)  # > 30 ngày → không kích đỏ vì hết hạn
		soon = add_days(nowdate(), 10)  # ≤ 30 ngày → đỏ near-expiry
		cls.green = _mk_contract("_T-CH-GREEN", cls.hosp, [_item("VTYT-GR", 100, 50)], far).name  # 50%
		cls.orange = _mk_contract("_T-CH-ORANGE", cls.hosp, [_item("VTYT-OR", 100, 90)], far).name  # 90%
		cls.red_cap = _mk_contract("_T-CH-REDCAP", cls.hosp, [_item("VTYT-RC", 100, 110)], far).name  # 110%
		cls.red_exp = _mk_contract(
			"_T-CH-REDEXP", cls.hosp, [_item("VTYT-RE", 100, 10)], soon
		).name  # 10% nhưng sắp hết hạn
		cls.agg = _mk_contract(
			"_T-CH-AGG", cls.hosp, [_item("VTYT-A1", 100, 30), _item("VTYT-A2", 100, 20)], far
		).name  # (30+20)/(100+100)=25%

	def _find(self, data, name):
		return next((r for r in data if r["name"] == name), None)

	def test_shape_and_count_eq_rows(self):
		res = contract.get_contract_health(page_length=0)
		self.assertIsInstance(res, dict)
		self.assertEqual(set(res.keys()), {"data", "total_count"})
		self.assertGreaterEqual(len(res["data"]), 5)
		self.assertEqual(set(res["data"][0].keys()), HEALTH_ITEM_KEYS)
		self.assertEqual(len(res["data"]), res["total_count"])  # BR-13 count==rows

	def test_quota_used_pct_aggregate(self):
		row = self._find(contract.get_contract_health(page_length=0)["data"], self.agg)
		self.assertIsNotNone(row)
		self.assertEqual(row["quota_used_pct"], 25.0)

	def test_days_to_expiry(self):
		row = self._find(contract.get_contract_health(page_length=0)["data"], self.red_exp)
		self.assertEqual(row["days_to_expiry"], 10)

	def test_color_green(self):
		row = self._find(contract.get_contract_health(page_length=0)["data"], self.green)
		self.assertEqual(row["health_color"], "green")

	def test_color_orange(self):
		row = self._find(contract.get_contract_health(page_length=0)["data"], self.orange)
		self.assertEqual(row["health_color"], "orange")

	def test_color_red_over_cap(self):
		row = self._find(contract.get_contract_health(page_length=0)["data"], self.red_cap)
		self.assertEqual(row["health_color"], "red")

	def test_color_red_near_expiry(self):
		"""Quota mới 10% (xanh theo quota) nhưng còn ≤30 ngày → đỏ (overlay hết hạn)."""
		row = self._find(contract.get_contract_health(page_length=0)["data"], self.red_exp)
		self.assertEqual(row["health_color"], "red")

	def test_no_leak_for_noperm_user(self):
		email = "_t_ch_noperm@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": "NoPermCH", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		self.assertGreaterEqual(contract.get_contract_health(page_length=0)["total_count"], 5)
		frappe.set_user(email)
		try:
			try:
				res = contract.get_contract_health(page_length=0)
			except frappe.PermissionError:
				return
			self.assertEqual(res["total_count"], 0, msg=f"LEAK: {res}")
			self.assertEqual(len(res["data"]), 0, msg=f"LEAK rows: {res}")
		finally:
			frappe.set_user("Administrator")
