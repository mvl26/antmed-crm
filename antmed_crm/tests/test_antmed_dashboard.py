# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M11 Dashboard — endpoint tổng quan + KPI quota/cảnh báo (TDD viết TRƯỚC implement).

Cover Slice 2 (overview — KPI nền đếm M01) + Slice M11-3 (quota_summary — gộp quota/cảnh báo từ M02):

  overview() (Slice 2):
    test_overview_shape            — dict đúng 2 key {hospital_count, doctor_count} kiểu int.
    test_overview_counts_match     — sau seed K BV + L bác sỹ → count khớp K/L.
    test_overview_counts_under_permission — user KHÔNG read AntMed Hospital → 0 (không leak).
    test_overview_is_get_only      — whitelist methods=['GET'].

  quota_summary() (Slice M11-3 — thay 2 placeholder 'Quota đã dùng' + 'Cảnh báo điều hành'):
    test_quota_summary_shape       — dict đúng 3 key {avg_quota_used_pct float, contracts_over_90_count int, alerts list}.
    test_quota_summary_is_get_only — whitelist methods chứa GET, KHÔNG POST/PUT.
    test_avg_quota_used_pct        — seed 25% + 90% + 50% → avg ≈ 55.0 (khớp mean get_contract_health).
    test_avg_empty_no_div_zero     — scope rỗng → avg == 0.0 (không raise, không NaN).
    test_contracts_over_90_count   — seed 90/95/110% + 50% → count == 3 (>=90 inclusive).
    test_alerts_only_red_orange    — alert chỉ chứa HĐ health_color đỏ/cam; HĐ xanh KHÔNG xuất hiện.
    test_alerts_capped_and_severity— >6 HĐ cảnh báo → len==6, danger trước warn; mỗi item đủ 4 key.
    test_no_leak_for_noperm_user   — user không read AntMed Contract → avg==0.0, count==0, alerts==[] (fail-closed).

Nguyên tắc count == rows (BR-13): mọi tổng hợp lấy từ contract.get_contract_health (get_list
permission-respecting) — KHÔNG frappe.db.count / raw SQL. User mù quyền → mọi giá trị 0/rỗng.

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_dashboard
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from antmed_crm.api.antmed import dashboard

QUOTA_SUMMARY_KEYS = {"avg_quota_used_pct", "contracts_over_90_count", "alerts"}
ALERT_ITEM_KEYS = {"type", "severity", "contract", "label"}

# M08 Slice 1: thứ tự + nhãn VI funnel pipeline gói thầu (mockup A1 widget "Pipeline gói thầu").
TENDER_STAGE_ORDER = ["lead", "survey", "quote", "bid", "won"]
TENDER_STAGE_LABELS = ["Lead", "Khảo sát", "Báo giá", "Dự thầu", "Trúng"]
TENDER_STAGE_ITEM_KEYS = {"key", "label", "count"}
TENDER_PIPELINE_KEYS = {"stages", "total"}


def _ensure_lost_reason():
	"""Đảm bảo có 1 CRM Lost Reason để seed Lead status type Lost (Junk/Unqualified).

	CRM Lead.validate_lost_reason() bắt buộc lost_reason khi status thuộc type Lost —
	seed test phải cấp lost_reason hợp lệ (KHÔNG đổi luồng prod).
	"""
	reason = "_T-TP-Lost-Reason"
	if not frappe.db.exists("CRM Lost Reason", reason):
		frappe.get_doc({"doctype": "CRM Lost Reason", "lost_reason": reason}).insert(
			ignore_permissions=True
		)
	return reason


def _mk_lead(first_name, status, **kw):
	"""Seed 1 CRM Lead với status cho trước (status reqd, Link → CRM Lead Status).

	Status type Lost (Junk/Unqualified) cần lost_reason — tự cấp nếu caller chưa truyền.
	"""
	if (
		"lost_reason" not in kw
		and frappe.get_cached_value("CRM Lead Status", status, "type") == "Lost"
	):
		kw["lost_reason"] = _ensure_lost_reason()
	doc = frappe.get_doc(
		{"doctype": "CRM Lead", "first_name": first_name, "status": status, **kw}
	)
	doc.insert(ignore_permissions=True)
	return doc


def _mk_deal(status, **kw):
	"""Seed 1 CRM Deal với status cho trước (status reqd, Link → CRM Deal Status)."""
	doc = frappe.get_doc({"doctype": "CRM Deal", "status": status, **kw})
	doc.insert(ignore_permissions=True)
	return doc


def _mk_hospital(code, name, **kw):
	if frappe.db.exists("AntMed Hospital", code):
		return frappe.get_doc("AntMed Hospital", code)
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


def _item(code, quota, used):
	"""Dòng quota con — used/quota → used_pct dùng để kiểm avg/count/alert."""
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


class TestAntMedDashboard(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# Seed sạch: baseline TRƯỚC khi seed (DB có thể đã có rác từ suite khác).
		cls.hosp_before = len(frappe.get_list("AntMed Hospital", pluck="name", limit_page_length=0))
		cls.doc_before = len(frappe.get_list("AntMed Doctor", pluck="name", limit_page_length=0))
		# K=2 bệnh viện, L=3 bác sỹ (Slice 2 overview).
		cls.h1 = _mk_hospital("_T-DASH-H1", "BV Dashboard 1", contract_status="Đã ký")
		cls.h2 = _mk_hospital("_T-DASH-H2", "BV Dashboard 2", contract_status="Tiềm năng")
		cls.d1 = _mk_doctor("_T-DASH-D1", "BS Dashboard 1", cls.h1.name, specialty="Ngoại")
		cls.d2 = _mk_doctor("_T-DASH-D2", "BS Dashboard 2", cls.h1.name, specialty="Tim mạch")
		cls.d3 = _mk_doctor("_T-DASH-D3", "BS Dashboard 3", cls.h2.name, specialty="Da liễu")

	# === Slice 2: overview() ==================================================
	def test_overview_shape(self):
		"""overview() trả RAW dict đúng 2 key hospital_count + doctor_count, cả 2 kiểu int."""
		res = dashboard.overview()
		self.assertIsInstance(res, dict)
		self.assertEqual(set(res.keys()), {"hospital_count", "doctor_count"})
		self.assertIsInstance(res["hospital_count"], int)
		self.assertIsInstance(res["doctor_count"], int)
		self.assertNotIn("data", res)
		self.assertNotIn("_ok", res)

	def test_overview_counts_match(self):
		"""count == rows (BR-13): overview() count == số get_list trả dưới quyền user, đúng cùng lúc.

		Assert INVARIANT (count==rows) + seeded HĐ/BS đã visible — KHÔNG dùng delta literal so với
		baseline setUpClass (mong manh khi test khác trong class seed HĐ committed; xem R-9).
		"""
		res = dashboard.overview()
		hosp_rows = frappe.get_list("AntMed Hospital", pluck="name", limit_page_length=0)
		doc_rows = frappe.get_list("AntMed Doctor", pluck="name", limit_page_length=0)
		# count khớp rows tại cùng thời điểm (invariant cốt lõi, leak-proof).
		self.assertEqual(res["hospital_count"], len(hosp_rows))
		self.assertEqual(res["doctor_count"], len(doc_rows))
		# 2 BV + 3 BS đã seed phải nằm trong tập đếm (chống false-green count rỗng).
		self.assertIn(self.h1.name, hosp_rows)
		self.assertIn(self.h2.name, hosp_rows)
		for d in (self.d1, self.d2, self.d3):
			self.assertIn(d.name, doc_rows)

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
		self.assertGreaterEqual(dashboard.overview()["hospital_count"], 2)
		frappe.set_user(email)
		try:
			try:
				res = dashboard.overview()
			except frappe.PermissionError:
				return
			self.assertEqual(res["hospital_count"], 0, msg=f"LEAK hospital_count: {res}")
			self.assertEqual(res["doctor_count"], 0, msg=f"LEAK doctor_count: {res}")
		finally:
			frappe.set_user("Administrator")

	def test_overview_is_get_only(self):
		"""overview() được whitelist CHỈ cho GET (allowed methods == ['GET'])."""
		self.assertIn(dashboard.overview, frappe.whitelisted, msg="overview() chưa @frappe.whitelist()")
		allowed = frappe.allowed_http_methods_for_whitelisted_func.get(dashboard.overview)
		self.assertEqual(allowed, ["GET"], msg="overview() phải @frappe.whitelist(methods=['GET'])")

	# === Slice M11-3: quota_summary() =========================================
	def test_quota_summary_shape(self):
		"""quota_summary() trả RAW dict ĐÚNG 3 key, đúng kiểu — không thừa/thiếu key."""
		res = dashboard.quota_summary()
		self.assertIsInstance(res, dict)
		self.assertEqual(set(res.keys()), QUOTA_SUMMARY_KEYS)
		self.assertIsInstance(res["avg_quota_used_pct"], float)
		self.assertIsInstance(res["contracts_over_90_count"], int)
		self.assertIsInstance(res["alerts"], list)
		# RAW dict — KHÔNG envelope bọc.
		self.assertNotIn("data", res)
		self.assertNotIn("_ok", res)

	def test_quota_summary_is_get_only(self):
		"""quota_summary() whitelist methods chứa GET, KHÔNG cho POST/PUT (chặn ở dispatcher)."""
		self.assertIn(
			dashboard.quota_summary, frappe.whitelisted, msg="quota_summary() chưa @frappe.whitelist()"
		)
		allowed = frappe.allowed_http_methods_for_whitelisted_func.get(dashboard.quota_summary)
		self.assertEqual(
			allowed, ["GET"], msg="quota_summary() phải @frappe.whitelist(methods=['GET'])"
		)

	def test_avg_quota_used_pct(self):
		"""Seed HĐ 25% + 90% + 50% (đặt riêng BV để đếm gọn) → avg khớp mean get_contract_health.

		So với chính mean(quota_used_pct) của contract.get_contract_health (cùng SSoT) trên toàn
		scope admin — tránh phụ thuộc rác DB; chỉ assert avg == mean được tính lại từ data nguồn.
		"""
		from antmed_crm.api.antmed import contract

		hosp = _mk_hospital("_T-DASH-AVG", "BV Quota Avg").name
		far = add_days(nowdate(), 400)
		_mk_contract("_T-DASH-Q25", hosp, [_item("DAVG-25", 100, 25)], far)  # 25%
		_mk_contract("_T-DASH-Q90", hosp, [_item("DAVG-90", 100, 90)], far)  # 90%
		_mk_contract("_T-DASH-Q50", hosp, [_item("DAVG-50", 100, 50)], far)  # 50%

		health = contract.get_contract_health(page_length=0)["data"]
		pcts = [r["quota_used_pct"] for r in health]
		expected = round(sum(pcts) / len(pcts), 2) if pcts else 0.0

		res = dashboard.quota_summary()
		self.assertEqual(res["avg_quota_used_pct"], expected)
		# Sanity: 3 HĐ vừa seed có trong data với đúng pct (chống false-green seed sai).
		# name = naming series (AM-HD-...), KHÁC contract_no → tra theo contract_no.
		by = {r["contract_no"]: r["quota_used_pct"] for r in health}
		self.assertEqual(by["_T-DASH-Q25"], 25.0)
		self.assertEqual(by["_T-DASH-Q90"], 90.0)
		self.assertEqual(by["_T-DASH-Q50"], 50.0)

	def test_avg_empty_no_div_zero(self):
		"""Scope rỗng (user mù quyền) → avg_quota_used_pct == 0.0 (không raise, không NaN)."""
		email = "_t_dash_q_noperm@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": "QNoPerm",
					"send_welcome_email": 0,
				}
			).insert(ignore_permissions=True)
		frappe.set_user(email)
		try:
			try:
				res = dashboard.quota_summary()
			except frappe.PermissionError:
				return
			self.assertEqual(res["avg_quota_used_pct"], 0.0)
			# Không NaN: == chính nó (NaN != NaN).
			self.assertEqual(res["avg_quota_used_pct"], res["avg_quota_used_pct"])
		finally:
			frappe.set_user("Administrator")

	def test_contracts_over_90_count(self):
		"""Seed 90/95/110% + 50% (BV riêng) → đúng 3 HĐ có quota_used_pct >= 90 (inclusive)."""
		hosp = _mk_hospital("_T-DASH-OVER", "BV Over90").name
		far = add_days(nowdate(), 400)
		_mk_contract("_T-DASH-O90", hosp, [_item("DOV-90", 100, 90)], far)  # 90% (>=90 → đếm)
		_mk_contract("_T-DASH-O95", hosp, [_item("DOV-95", 100, 95)], far)  # 95%
		_mk_contract("_T-DASH-O110", hosp, [_item("DOV-110", 100, 110)], far)  # 110%
		_mk_contract("_T-DASH-O50", hosp, [_item("DOV-50", 100, 50)], far)  # 50% (KHÔNG đếm)

		from antmed_crm.api.antmed import contract

		health = contract.get_contract_health(page_length=0)["data"]
		expected = sum(1 for r in health if (r["quota_used_pct"] or 0) >= 90)

		res = dashboard.quota_summary()
		self.assertEqual(res["contracts_over_90_count"], expected)
		self.assertGreaterEqual(res["contracts_over_90_count"], 3)

	def test_alerts_only_red_orange(self):
		"""alert chỉ chứa HĐ health_color đỏ/cam; HĐ xanh (50%, hạn xa) KHÔNG xuất hiện."""
		hosp = _mk_hospital("_T-DASH-ALERT", "BV Alert").name
		far = add_days(nowdate(), 400)
		green = _mk_contract("_T-DASH-AL-GREEN", hosp, [_item("DAL-GR", 100, 50)], far).name  # xanh
		red_cap = _mk_contract("_T-DASH-AL-CAP", hosp, [_item("DAL-CAP", 100, 110)], far).name  # đỏ over

		from antmed_crm.api.antmed import contract

		health = {r["name"]: r["health_color"] for r in contract.get_contract_health(page_length=0)["data"]}
		self.assertEqual(health[green], "green")  # sanity seed
		self.assertEqual(health[red_cap], "red")

		alerts = dashboard.quota_summary()["alerts"]
		alert_contracts = {a["contract"] for a in alerts}
		# HĐ xanh KHÔNG được lọt vào alerts.
		self.assertNotIn(green, alert_contracts)
		# Mọi alert phải thuộc HĐ đỏ/cam (đối chiếu health_color SSoT).
		for a in alerts:
			self.assertIn(
				health.get(a["contract"]),
				("red", "orange"),
				msg=f"alert {a} không thuộc HĐ đỏ/cam",
			)

	def test_alerts_capped_and_severity(self):
		"""> 6 HĐ cảnh báo → len(alerts)==6, danger đứng trước warn; mỗi item đủ 4 key đúng giá trị."""
		hosp = _mk_hospital("_T-DASH-CAP", "BV Cap").name
		far = add_days(nowdate(), 400)
		soon = add_days(nowdate(), 5)
		# 5 HĐ đỏ (over-cap / near-expiry) + 3 HĐ cam (80<pct<=100) → >6 cảnh báo.
		for i in range(5):
			_mk_contract(f"_T-DASH-CAP-RED{i}", hosp, [_item(f"DCAP-R{i}", 100, 110)], far)  # đỏ over
		_mk_contract("_T-DASH-CAP-EXP", hosp, [_item("DCAP-E", 100, 10)], soon)  # đỏ near-expiry
		for i in range(3):
			_mk_contract(f"_T-DASH-CAP-ORG{i}", hosp, [_item(f"DCAP-O{i}", 100, 95)], far)  # cam 95%

		alerts = dashboard.quota_summary()["alerts"]
		self.assertEqual(len(alerts), 6, msg=f"phải cắt tối đa 6, got {len(alerts)}")

		# Mỗi item shape ổn định 4 key + giá trị hợp lệ (Hyrum).
		for a in alerts:
			self.assertEqual(set(a.keys()), ALERT_ITEM_KEYS, msg=f"alert thừa/thiếu key: {a}")
			self.assertIn(a["type"], ("expiry", "quota", "over_cap"))
			self.assertIn(a["severity"], ("danger", "warn"))
			self.assertIsInstance(a["contract"], str)
			self.assertIsInstance(a["label"], str)
			self.assertTrue(a["label"])

		# danger đứng TRƯỚC warn (không xen kẽ).
		severities = [a["severity"] for a in alerts]
		first_warn = next((i for i, s in enumerate(severities) if s == "warn"), len(severities))
		self.assertTrue(
			all(s == "danger" for s in severities[:first_warn]),
			msg=f"danger phải đứng trước warn: {severities}",
		)
		self.assertTrue(
			all(s == "warn" for s in severities[first_warn:]),
			msg=f"sau warn đầu tiên không được có danger: {severities}",
		)

	def test_no_leak_for_noperm_user(self):
		"""User không read AntMed Contract → avg==0.0, count==0, alerts==[] (fail-closed)."""
		email = "_t_dash_leak@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": "LeakCheck",
					"send_welcome_email": 0,
				}
			).insert(ignore_permissions=True)
		frappe.set_user(email)
		try:
			try:
				res = dashboard.quota_summary()
			except frappe.PermissionError:
				return  # fail-closed: chặn ngay, không lộ con số nào
			self.assertEqual(res["avg_quota_used_pct"], 0.0, msg=f"LEAK avg: {res}")
			self.assertEqual(res["contracts_over_90_count"], 0, msg=f"LEAK count: {res}")
			self.assertEqual(res["alerts"], [], msg=f"LEAK alerts: {res}")
		finally:
			frappe.set_user("Administrator")


# ════════════════════════════════════════════════════════════════════════════
# M08 Slice 1 — tender_pipeline() : funnel "Pipeline gói thầu" (A1 CEO Hàng 3)
#   5 tầng đếm SỐ THẬT từ CRM Lead status + CRM Deal status:
#     lead   = CRM Lead   status in (New, Contacted, Nurture)
#     survey = CRM Lead   status = Qualified
#     quote  = CRM Deal   status in (Qualification, Demo/Making, Proposal/Quotation)
#     bid    = CRM Deal   status in (Negotiation, Ready to Close)
#     won    = CRM Deal   status = Won
#   Loại trừ Converted/Unqualified/Junk (Lead) + Lost (Deal) — chỉ pipeline đang chạy + trúng.
# ════════════════════════════════════════════════════════════════════════════
class TestAntMedTenderPipeline(FrappeTestCase):
	def test_tender_pipeline_shape(self):
		"""tender_pipeline() trả RAW dict {stages(list 5), total}; mỗi stage 3 key đúng thứ tự + nhãn VI."""
		res = dashboard.tender_pipeline()
		self.assertIsInstance(res, dict)
		self.assertEqual(set(res.keys()), TENDER_PIPELINE_KEYS)
		self.assertIsInstance(res["stages"], list)
		self.assertEqual(len(res["stages"]), 5, msg="funnel phải đúng 5 tầng")
		self.assertIsInstance(res["total"], int)
		# RAW dict — KHÔNG envelope bọc.
		self.assertNotIn("data", res)
		self.assertNotIn("_ok", res)

		# Thứ tự key + nhãn VI khớp mockup A1 (Hyrum: FE phụ thuộc order + label).
		self.assertEqual([s["key"] for s in res["stages"]], TENDER_STAGE_ORDER)
		self.assertEqual([s["label"] for s in res["stages"]], TENDER_STAGE_LABELS)
		for s in res["stages"]:
			self.assertEqual(set(s.keys()), TENDER_STAGE_ITEM_KEYS, msg=f"stage thừa/thiếu key: {s}")
			self.assertIsInstance(s["count"], int)
			self.assertGreaterEqual(s["count"], 0)

	def test_tender_pipeline_status_mapping(self):
		"""Seed Lead (New, Qualified, Junk) + Deal (Proposal/Quotation, Negotiation, Won, Lost):
		count tầng lead/survey/quote/bid/won khớp delta đúng; Junk/Lost KHÔNG đếm; total == SUM 5.

		Đo theo DELTA (sau − trước) để miễn nhiễm rác DB từ suite khác (R-9 idiom của class trên).
		"""
		before = {s["key"]: s["count"] for s in dashboard.tender_pipeline()["stages"]}

		# status Junk/Lost (type=Lost) cần lost_reason (Link CRM Lost Reason) — seed 1 reason.
		reason = "_T-TP-Reason"
		if not frappe.db.exists("CRM Lost Reason", reason):
			frappe.get_doc({"doctype": "CRM Lost Reason", "lost_reason": reason}).insert(
				ignore_permissions=True
			)

		_mk_lead("_T-TP-New", "New")  # → lead
		_mk_lead("_T-TP-Qualified", "Qualified")  # → survey
		_mk_lead("_T-TP-Junk", "Junk", lost_reason=reason)  # → KHÔNG đếm (loại)
		_mk_deal("Proposal/Quotation")  # → quote
		_mk_deal("Negotiation")  # → bid
		_mk_deal("Won")  # → won
		_mk_deal("Lost", lost_reason=reason)  # → KHÔNG đếm (loại)

		res = dashboard.tender_pipeline()
		after = {s["key"]: s["count"] for s in res["stages"]}
		delta = {k: after[k] - before[k] for k in TENDER_STAGE_ORDER}

		self.assertEqual(delta["lead"], 1, msg=f"lead delta sai: {delta}")
		self.assertEqual(delta["survey"], 1, msg=f"survey delta sai: {delta}")
		self.assertEqual(delta["quote"], 1, msg=f"quote delta sai: {delta}")
		self.assertEqual(delta["bid"], 1, msg=f"bid delta sai: {delta}")
		self.assertEqual(delta["won"], 1, msg=f"won delta sai: {delta}")
		# Junk (Lead) + Lost (Deal) KHÔNG được làm tăng tầng nào → tổng delta đúng 5 (không 7).
		self.assertEqual(sum(delta.values()), 5, msg=f"Junk/Lost bị đếm nhầm: {delta}")
		# total == tổng 5 count (invariant cốt lõi, mọi lúc).
		self.assertEqual(res["total"], sum(s["count"] for s in res["stages"]))

	def test_tender_pipeline_fail_soft_no_perm(self):
		"""User KHÔNG read-perm CRM Lead/Deal → mọi tầng count=0, total=0, KHÔNG raise (mirror overview)."""
		email = "_t_tp_noperm@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": "TPNoPerm",
					"send_welcome_email": 0,
				}
			).insert(ignore_permissions=True)
		frappe.set_user(email)
		try:
			# KHÔNG được raise (fail-soft) — bắt PermissionError = FAIL contract (phải nuốt về 0).
			res = dashboard.tender_pipeline()
			self.assertEqual(res["total"], 0, msg=f"LEAK total: {res}")
			for s in res["stages"]:
				self.assertEqual(s["count"], 0, msg=f"LEAK stage {s['key']}: {res}")
		finally:
			frappe.set_user("Administrator")

	def test_tender_pipeline_no_raw_sql_no_n_plus_1(self):
		"""Source dùng get_list/db.count (KHÔNG SQL string-format) + ≤ 5 count-query (1/tầng, no N+1)."""
		import inspect

		src = inspect.getsource(dashboard.tender_pipeline) + inspect.getsource(
			dashboard._count_status_under_permission
		)
		# KHÔNG raw SQL string-format (chống SQL injection): không frappe.db.sql / f-string SELECT.
		self.assertNotIn("frappe.db.sql", src, msg="KHÔNG raw SQL — dùng get_list/db.count")
		self.assertNotIn("SELECT", src.upper())

		# Đếm số get_list thực: ≤ 5 (1 count-query / tầng). Loop per-row = N+1 → vỡ ngưỡng này.
		calls = {"n": 0}
		orig_get_list = frappe.get_list

		def _spy(*a, **kw):
			calls["n"] += 1
			return orig_get_list(*a, **kw)

		frappe.get_list = _spy
		try:
			dashboard.tender_pipeline()
		finally:
			frappe.get_list = orig_get_list
		self.assertLessEqual(calls["n"], 5, msg=f"N+1: {calls['n']} get_list (phải ≤5, 1/tầng)")
		self.assertGreaterEqual(calls["n"], 1, msg="phải gọi get_list (count dưới permission)")

	def test_tender_pipeline_is_get_only(self):
		"""tender_pipeline() whitelist CHỈ GET (allowed == ['GET'])."""
		self.assertIn(
			dashboard.tender_pipeline, frappe.whitelisted, msg="tender_pipeline() chưa @frappe.whitelist()"
		)
		allowed = frappe.allowed_http_methods_for_whitelisted_func.get(dashboard.tender_pipeline)
		self.assertEqual(allowed, ["GET"], msg="tender_pipeline() phải @frappe.whitelist(methods=['GET'])")
