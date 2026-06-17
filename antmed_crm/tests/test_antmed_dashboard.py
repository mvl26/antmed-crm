# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M11 Dashboard — FE Slice 2 — harness test cho overview() (TDD viết TRƯỚC implement).

Cover acceptance Slice 2 (Dashboard A1 — KPI nền đếm M01 đã land):
  test_overview_shape            — overview() trả dict đúng 2 key {hospital_count, doctor_count} kiểu int.
  test_overview_counts_match     — sau khi seed K AntMed Hospital + L AntMed Doctor → count khớp K/L.
  test_overview_counts_under_permission — user KHÔNG có read AntMed Hospital → hospital_count==0 (không leak).
  test_overview_is_get_only      — endpoint whitelist methods=['GET'] (không cho POST/PUT…).

Nguyên tắc count == rows (BR-13): đếm bằng len(get_list(pluck="name", limit_page_length=0)) —
get_list tôn trọng DocPerm + (khi M14 bật) permission_query_conditions, KHÔNG dùng frappe.db.count.

Lệnh chạy:
  bench --site miyano run-tests --module crm.tests.test_antmed_dashboard
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from antmed_crm.api.antmed import dashboard


def _mk_hospital(code, name, **kw):
	doc = frappe.get_doc(
		{"doctype": "AntMed Hospital", "hospital_code": code, "hospital_name": name, **kw}
	)
	doc.insert(ignore_permissions=True)
	return doc


def _mk_doctor(doctor_code, full_name, hospital, **kw):
	doc = frappe.get_doc(
		{
			"doctype": "AntMed Doctor",
			"doctor_code": doctor_code,
			"full_name": full_name,
			"hospital": hospital,
			**kw,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


class TestAntMedDashboard(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# Seed sạch: đếm baseline TRƯỚC khi seed để test count khớp delta (DB có thể đã có rác).
		cls.hosp_before = len(
			frappe.get_list("AntMed Hospital", pluck="name", limit_page_length=0)
		)
		cls.doc_before = len(frappe.get_list("AntMed Doctor", pluck="name", limit_page_length=0))
		# K=2 bệnh viện, L=3 bác sỹ.
		cls.h1 = _mk_hospital("_T-DASH-H1", "BV Dashboard 1", contract_status="Đã ký")
		cls.h2 = _mk_hospital("_T-DASH-H2", "BV Dashboard 2", contract_status="Tiềm năng")
		cls.d1 = _mk_doctor("_T-DASH-D1", "BS Dashboard 1", cls.h1.name, specialty="Ngoại")
		cls.d2 = _mk_doctor("_T-DASH-D2", "BS Dashboard 2", cls.h1.name, specialty="Tim mạch")
		cls.d3 = _mk_doctor("_T-DASH-D3", "BS Dashboard 3", cls.h2.name, specialty="Da liễu")

	# --- (a) shape: dict đúng 2 key kiểu int ---------------------------------
	def test_overview_shape(self):
		"""overview() trả RAW dict đúng 2 key hospital_count + doctor_count, cả 2 kiểu int."""
		res = dashboard.overview()
		self.assertIsInstance(res, dict)
		self.assertEqual(set(res.keys()), {"hospital_count", "doctor_count"})
		self.assertIsInstance(res["hospital_count"], int)
		self.assertIsInstance(res["doctor_count"], int)
		# KHÔNG envelope _ok/_err / data bọc — RAW dict thuần.
		self.assertNotIn("data", res)
		self.assertNotIn("_ok", res)

	# --- (b) count khớp K/L sau seed -----------------------------------------
	def test_overview_counts_match(self):
		"""Sau seed K=2 BV + L=3 bác sỹ → count tăng đúng delta so với baseline."""
		res = dashboard.overview()
		self.assertEqual(res["hospital_count"], self.hosp_before + 2)
		self.assertEqual(res["doctor_count"], self.doc_before + 3)
		# count == rows (BR-13): khớp đúng số get_list trả dưới quyền Administrator.
		self.assertEqual(
			res["hospital_count"],
			len(frappe.get_list("AntMed Hospital", pluck="name", limit_page_length=0)),
		)
		self.assertEqual(
			res["doctor_count"],
			len(frappe.get_list("AntMed Doctor", pluck="name", limit_page_length=0)),
		)

	# --- (c) count đếm DƯỚI permission — user thiếu read → 0 (không leak) -----
	def test_overview_counts_under_permission(self):
		"""User KHÔNG có read AntMed Hospital → hospital_count==0 (đếm dưới permission, không leak)."""
		email = "_t_dash_noperm@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": "DashNoPerm",
					"send_welcome_email": 0,
				}
			).insert(ignore_permissions=True)
		# sanity chống false-green: admin THẤY ít nhất số đã seed.
		self.assertGreaterEqual(dashboard.overview()["hospital_count"], 2)
		frappe.set_user(email)
		try:
			# get_list khi user không có read-perm sẽ raise PermissionError HOẶC trả rỗng;
			# cả 2 đều là non-leak. overview() đếm qua get_list nên KHÔNG được trả số > 0
			# cho user mù-quyền. Nếu get_list raise → overview raise (đường an toàn,
			# dispatcher chặn); nếu trả rỗng → count phải == 0.
			try:
				res = dashboard.overview()
			except frappe.PermissionError:
				return  # an toàn: chặn ngay, không rò bất kỳ con số nào
			self.assertEqual(res["hospital_count"], 0, msg=f"LEAK hospital_count: {res}")
			self.assertEqual(res["doctor_count"], 0, msg=f"LEAK doctor_count: {res}")
		finally:
			frappe.set_user("Administrator")

	# --- (d) GET-only whitelist ----------------------------------------------
	def test_overview_is_get_only(self):
		"""overview() được whitelist CHỈ cho GET (allowed methods chứa GET, KHÔNG POST/PUT).

		Frappe v15 lưu method-restriction trong dict frappe.allowed_http_methods_for_whitelisted_func
		(key = function object), KHÔNG phải thuộc tính trên hàm. Hàm whitelisted nằm trong
		frappe.whitelisted (verify endpoint callable qua dispatcher, không guest).
		"""
		self.assertIn(
			dashboard.overview,
			frappe.whitelisted,
			msg="overview() chưa được @frappe.whitelist()",
		)
		allowed = frappe.allowed_http_methods_for_whitelisted_func.get(dashboard.overview)
		self.assertEqual(
			allowed,
			["GET"],
			msg="overview() phải khai @frappe.whitelist(methods=['GET']) — chỉ cho GET",
		)
