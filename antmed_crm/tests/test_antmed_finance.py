# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M09-1 "Hoa hồng Nhân viên" (Kế toán) — endpoint finance.commission_summary (TDD viết TRƯỚC).

Màn /antmed/finance/commission (mockup F2): 2 card header — "Tổng hoa hồng kỳ" + "Quy tắc kỳ".
Tổng hoa hồng kỳ = SUM(deal_value × FLAT_RATE) trên CRM Deal status type 'Won' & closed_date
trong THÁNG HIỆN TẠI [get_first_day .. get_last_day]. KHÔNG new DocType, KHÔNG new module,
KHÔNG per-category bonus engine — chỉ rollup/đếm doctype CRM Deal có sẵn.

commission_summary() trả RAW dict (KHÔNG envelope, KHÔNG bọc { data, total_count }):
  { total_commission, total_revenue, rep_count, group_count, period_label,
    flat_rate_pct, currency, rules }

Cover (acceptance Test-case TDD M09-1):
  (a) shape       — đủ COMMISSION_SUMMARY_KEYS; currency=='VND'; period_label khớp regex T<m>/<yyyy>.
  (b) formula     — total_revenue==SUM(deal_value Won kỳ); total_commission==round(rev*FLAT_RATE,0);
                    Deal Lost / Won closed THÁNG TRƯỚC KHÔNG được tính.
  (c) rep_count   — số deal_owner phân biệt có Won trong kỳ.
  (d) empty       — 0 deal Won kỳ → total_commission==0, total_revenue==0, rep_count==0,
                    rules KHÔNG rỗng (==len(COMMISSION_RULES)).
  (e) fail-closed — monkeypatch frappe.get_list raise PermissionError → _empty_commission shape
                    (số=0, rules giữ nguyên), KHÔNG raise (BR-13).
  (f) get-only    — @frappe.whitelist(methods=['GET']).
  (g) no_raw_sql  — 'frappe.db.sql' KHÔNG xuất hiện trong finance.py source.
  (h) data-scope  — chạy dưới NV scoped (User Permission AntMed Hospital) chỉ thấy deal trong phạm vi.

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_finance
"""

import re

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_months, get_first_day, nowdate

from antmed_crm.api.antmed import finance

COMMISSION_SUMMARY_KEYS = {
	"total_commission",
	"total_revenue",
	"rep_count",
	"group_count",
	"period_label",
	"flat_rate_pct",
	"currency",
	"rules",
}

PERIOD_LABEL_RE = re.compile(r"^T\d{1,2}/\d{4}$")


def _ensure_lost_reason():
	reason = "_T-FIN-Lost-Reason"
	if not frappe.db.exists("CRM Lost Reason", reason):
		frappe.get_doc({"doctype": "CRM Lost Reason", "lost_reason": reason}).insert(ignore_permissions=True)
	return reason


def _won_status() -> str:
	rows = frappe.get_all("CRM Deal Status", filters={"type": "Won"}, pluck="name", limit_page_length=1)
	return rows[0] if rows else "Won"


def _lost_status() -> str:
	rows = frappe.get_all("CRM Deal Status", filters={"type": "Lost"}, pluck="name", limit_page_length=1)
	return rows[0] if rows else "Lost"


def _open_status() -> str:
	rows = frappe.get_all(
		"CRM Deal Status", filters={"type": ["in", ["Open", "Ongoing"]]}, pluck="name", limit_page_length=1
	)
	return rows[0] if rows else "Qualification"


def _mk_user(email: str, first_name: str, roles: list[str] | None = None):
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": first_name, "send_welcome_email": 0}
		).insert(ignore_permissions=True)
	if roles:
		user = frappe.get_doc("User", email)
		have = [r.role for r in user.roles]
		add = [r for r in roles if r not in have and frappe.db.exists("Role", r)]
		if add:
			user.add_roles(*add)
	return email


def _assign_deal_to(deal_name: str, user: str):
	"""Tạo ToDo allocated_to=user cho 1 CRM Deal — Sales User scope thấy deal qua ToDo (BR-13).

	Cho phép 1 user 'Sales User' (ngoài hierarchy) thấy deal của owner KHÁC → cô lập value-assert
	khỏi deal cross-run mà Administrator thấy hết (mirror permission_query_conditions: own ∪ ToDo).
	"""
	if frappe.db.exists(
		"ToDo", {"reference_type": "CRM Deal", "reference_name": deal_name, "allocated_to": user, "status": "Open"}
	):
		return
	frappe.get_doc(
		{
			"doctype": "ToDo",
			"reference_type": "CRM Deal",
			"reference_name": deal_name,
			"allocated_to": user,
			"status": "Open",
			"description": f"[test] assign {deal_name} to {user}",
		}
	).insert(ignore_permissions=True)


def _mk_deal(owner: str, status: str, value: float, force_closed_date: str = "", **kw):
	"""Seed 1 CRM Deal. force_closed_date: set closed_date SAU insert (bypass controller override).

	Lý do: CRM Deal.validate ép closed_date=nowdate() khi status đổi sang type Won. Để seed deal Won
	ĐÃ closed THÁNG TRƯỚC, phải set_value sau insert — đây là dàn dựng dữ liệu test, KHÔNG đổi prod.
	"""
	doc = frappe.get_doc(
		{
			"doctype": "CRM Deal",
			"status": status,
			"deal_owner": owner,
			"deal_value": value,
			**kw,
		}
	)
	doc.insert(ignore_permissions=True)
	if force_closed_date:
		frappe.db.set_value("CRM Deal", doc.name, "closed_date", force_closed_date)
		doc.reload()
	return doc


class TestAntMedCommissionSummary(FrappeTestCase):
	"""Value-assert dưới SCOPED Sales User (chỉ thấy deal seed qua ToDo) — cô lập khỏi deal cross-run.

	Administrator thấy MỌI deal toàn site → revenue/rep_count phình (cross-contaminate). Chạy
	commission_summary() dưới user 'Sales User' ngoài hierarchy: permission_query_conditions giới
	hạn own ∪ ToDo-assigned. Ta assign CHÍNH XÁC deal seed cho user này → endpoint chỉ thấy seed.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.won = _won_status()
		cls.lost = _lost_status()
		cls.open_st = _open_status()
		cls.last_month_closed = get_first_day(add_months(nowdate(), -1))

		cls.u1 = _mk_user("_t_fin_rep1@example.com", "FinRepOne")
		cls.u2 = _mk_user("_t_fin_rep2@example.com", "FinRepTwo")
		# Scoped reader = Sales User ngoài hierarchy (read CRM Deal qua own ∪ ToDo). KHÔNG Sales Manager
		# (sẽ thấy hết). Chạy mọi value-assert dưới user này.
		cls.scoped = _mk_user("_t_fin_scoped_reader@example.com", "FinScopedReader", roles=["Sales User"])

		# Dọn deal cũ của 2 owner test (setUpClass commit → tránh tích luỹ qua các lần chạy lại).
		for owner in (cls.u1, cls.u2):
			for nm in frappe.get_all("CRM Deal", filters={"deal_owner": owner}, pluck="name"):
				frappe.delete_doc("CRM Deal", nm, force=True, ignore_permissions=True)

		# u1: 2 deal Won tháng này (200tr + 100tr) → controller tự set closed_date=nowdate().
		d1 = _mk_deal(cls.u1, cls.won, 200_000_000)
		d2 = _mk_deal(cls.u1, cls.won, 100_000_000)
		# u1: 1 Won THÁNG TRƯỚC (ép closed_date) — KHÔNG được tính vào kỳ.
		d3 = _mk_deal(cls.u1, cls.won, 999_000_000, force_closed_date=cls.last_month_closed)
		# u1: 1 Open (KHÔNG phải Won) — KHÔNG được tính.
		d4 = _mk_deal(cls.u1, cls.open_st, 50_000_000)

		# u2: 1 deal Won tháng này (60tr) + 1 Lost (KHÔNG được tính).
		d5 = _mk_deal(cls.u2, cls.won, 60_000_000)
		d6 = _mk_deal(cls.u2, cls.lost, 10_000_000, lost_reason=_ensure_lost_reason())

		# Assign TẤT CẢ deal seed cho scoped reader (Won-kỳ + nhiễu) → endpoint chỉ thấy đúng seed này.
		for d in (d1, d2, d3, d4, d5, d6):
			_assign_deal_to(d.name, cls.scoped)
		frappe.db.commit()

	def setUp(self):
		# Mọi test trong class chạy dưới scoped Sales User (cô lập scope).
		frappe.set_user(self.scoped)

	def tearDown(self):
		frappe.set_user("Administrator")

	# (a) shape ----------------------------------------------------------------
	def test_shape(self):
		res = finance.commission_summary()
		self.assertIsInstance(res, dict)
		self.assertEqual(set(res.keys()), COMMISSION_SUMMARY_KEYS, msg=f"key thừa/thiếu: {res.keys()}")
		self.assertEqual(res["currency"], "VND")
		self.assertRegex(res["period_label"], PERIOD_LABEL_RE)
		# RAW dict — KHÔNG envelope bọc.
		self.assertNotIn("data", res)
		self.assertNotIn("_ok", res)
		# rules là list dict {label, rate_pct}.
		self.assertIsInstance(res["rules"], list)
		self.assertTrue(res["rules"], "rules phải KHÔNG rỗng (mô tả quy tắc kỳ)")
		for r in res["rules"]:
			self.assertEqual(set(r.keys()), {"label", "rate_pct"}, msg=f"rule shape sai: {r}")

	# (b) formula --------------------------------------------------------------
	def test_commission_formula(self):
		res = finance.commission_summary()
		# total_revenue = SUM(deal_value Won kỳ) = u1 (200+100) + u2 (60) = 360tr.
		# (Won tháng trước 999tr, Open 50tr, Lost 10tr ĐỀU bị loại.)
		self.assertEqual(res["total_revenue"], 360_000_000)
		# total_commission = round(360tr × FLAT_RATE, 0).
		expected = round(360_000_000 * finance.FLAT_RATE, 0)
		self.assertEqual(res["total_commission"], expected)
		# flat_rate_pct = FLAT_RATE × 100 (vd 5.0 cho 5%).
		self.assertEqual(res["flat_rate_pct"], round(finance.FLAT_RATE * 100, 2))

	def test_lost_and_prev_month_excluded(self):
		"""Deal Lost + Won closed THÁNG TRƯỚC + Open KHÔNG được tính (đã gộp ở formula)."""
		res = finance.commission_summary()
		# Nếu cộng nhầm Won tháng trước (999tr) → revenue sẽ > 1 tỷ. Phải == 360tr.
		self.assertLess(res["total_revenue"], 1_000_000_000)
		self.assertEqual(res["total_revenue"], 360_000_000)

	# (c) rep_count distinct ---------------------------------------------------
	def test_rep_count_distinct(self):
		res = finance.commission_summary()
		# 3 deal Won trong kỳ của 2 deal_owner khác nhau (u1×2, u2×1) → rep_count == 2.
		self.assertEqual(res["rep_count"], 2)

	def test_group_count_equals_rules_len(self):
		res = finance.commission_summary()
		self.assertEqual(res["group_count"], len(finance.COMMISSION_RULES))
		self.assertEqual(res["group_count"], len(res["rules"]))

	# (f) get-only -------------------------------------------------------------
	def test_get_only(self):
		self.assertIn(
			finance.commission_summary, frappe.whitelisted, msg="commission_summary() chưa @frappe.whitelist()"
		)
		allowed = frappe.allowed_http_methods_for_whitelisted_func.get(finance.commission_summary)
		self.assertEqual(allowed, ["GET"], msg="commission_summary() phải @frappe.whitelist(methods=['GET'])")

	# (g) no raw sql / no f-string injection -----------------------------------
	def test_no_raw_sql(self):
		import inspect

		src = inspect.getsource(finance)
		self.assertNotIn("frappe.db.sql", src, msg="KHÔNG raw SQL — dùng get_list/get_all")
		self.assertNotIn("SELECT", src.upper(), msg="KHÔNG raw SELECT string")

	# (h) data-scope BR-13 — Sales User scoped chỉ thấy deal trong phạm vi ------
	def test_data_scope(self):
		"""Sales User scoped (permission_query_conditions: own ∪ ToDo) — commission_summary tôn trọng
		get_list, KHÔNG bypass scope, KHÔNG raise.

		self.scoped (Sales User ngoài hierarchy) CHỈ thấy deal seed (đã assign ToDo) → endpoint thấy
		ĐÚNG phạm vi: total_revenue == 360tr (Won kỳ trong scope), rep_count == 2 (u1+u2), KHÔNG
		phình theo deal cross-run mà Administrator thấy hết → chứng minh data-scope BR-13 hoạt động.
		Quan hệ formula nhất quán dưới scope (KHÔNG bịa).
		"""
		# setUp đã set_user(self.scoped) → đang chạy dưới đúng scope cần kiểm.
		res = finance.commission_summary()  # KHÔNG được raise
		self.assertEqual(set(res.keys()), COMMISSION_SUMMARY_KEYS)
		# Scope chỉ thấy seed → con số tuyệt đối ỔN ĐỊNH (cô lập khỏi cross-run).
		self.assertEqual(res["total_revenue"], 360_000_000, msg="data-scope vỡ: thấy deal ngoài phạm vi")
		self.assertEqual(res["rep_count"], 2)
		# Quan hệ formula vẫn đúng dưới scope (không bịa).
		self.assertEqual(res["total_commission"], round(res["total_revenue"] * finance.FLAT_RATE, 0))


class TestAntMedCommissionEmptyAndFailClosed(FrappeTestCase):
	"""Empty period + fail-closed BR-13 — cô lập (KHÔNG seed Won của owner riêng để empty thật)."""

	# (d) empty period ---------------------------------------------------------
	def test_empty_period_fail_closed_user(self):
		"""User KHÔNG read-perm CRM Deal → get_list raise PermissionError → empty shape (số=0).

		Đây cũng phục vụ acceptance 'empty period' (số=0) qua đường fail-closed sạch (không phụ
		thuộc deal toàn site). rules KHÔNG rỗng (giữ nguyên COMMISSION_RULES).
		"""
		email = "_t_fin_noperm@example.com"
		_mk_user(email, "FinNoPerm")
		frappe.set_user(email)
		try:
			res = finance.commission_summary()  # KHÔNG được raise
			self.assertEqual(res["total_commission"], 0)
			self.assertEqual(res["total_revenue"], 0)
			self.assertEqual(res["rep_count"], 0)
			# rules giữ nguyên — KHÔNG rỗng.
			self.assertEqual(len(res["rules"]), len(finance.COMMISSION_RULES))
			self.assertTrue(res["rules"])
			# group_count vẫn == len(rules) (mô tả quy tắc kỳ độc lập với deal).
			self.assertEqual(res["group_count"], len(finance.COMMISSION_RULES))
		finally:
			frappe.set_user("Administrator")

	# (e) fail-closed monkeypatch get_list -------------------------------------
	def test_fail_closed_monkeypatch(self):
		orig = frappe.get_list

		def _raise(*a, **k):
			if a and a[0] == finance.DEAL_DOCTYPE:
				raise frappe.PermissionError("no perm")
			return orig(*a, **k)

		frappe.get_list = _raise
		try:
			res = finance.commission_summary()  # KHÔNG được raise
			self.assertEqual(res["total_commission"], 0, msg=f"LEAK: {res}")
			self.assertEqual(res["total_revenue"], 0)
			self.assertEqual(res["rep_count"], 0)
			self.assertEqual(set(res.keys()), COMMISSION_SUMMARY_KEYS)
			# rules giữ nguyên (KHÔNG rỗng) — fail-closed = số về 0 NHƯNG mô tả quy tắc vẫn render.
			self.assertEqual(len(res["rules"]), len(finance.COMMISSION_RULES))
		finally:
			frappe.get_list = orig
