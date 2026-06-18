# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M02 Slice M02-3 — Quota enforce + usage log — harness test (TDD viết TRƯỚC).

Cover acceptance M02-3 (spec m02_contract_quota.md §4/§5/§8 slice 3):
  test_usage_log_doctype                — DocType `AntMed Quota Usage Log` tồn tại + đủ field tối thiểu.
  test_assert_item_in_contract_found    — item thuộc HĐ hiệu lực → trả contract name (BR-01).
  test_assert_item_in_contract_blocks    — item ngoài HĐ + user thường → throw "BR-02".
  test_assert_item_in_contract_override  — user `Quản lý` ghi đè BR-02 → trả None (không throw).
  test_assert_item_in_contract_hospital_scope — item của BV khác KHÔNG khớp BV đang xét.
  test_draft_contract_not_active        — HĐ `Nháp` (docstatus 0) KHÔNG được đối chiếu (throw BR-02).
  test_assert_quota_available_ok        — còn quota → không throw (BR-06 happy).
  test_assert_quota_available_blocks_at_cap — vượt trần + lock_at_100 → throw "BR-06".
  test_assert_quota_available_unlocked  — lock_at_100=0 → cho qua dù vượt trần (chỉ cảnh báo).
  test_consume_quota_and_recompute      — consume → ghi log + derive used_qty/remaining_pct (invariant).
  test_consume_quota_idempotent         — cùng do_ref → KHÔNG ghi log trùng (LL-BE-7).
  test_check_item_in_contract_found     — endpoint trả {in_contract,contract,unit_price,remaining_qty}.
  test_check_item_in_contract_not_found — item ngoài HĐ → in_contract False, các field None (KHÔNG throw).

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_quota
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from antmed_crm.antmed import contract_hooks
from antmed_crm.api.antmed import contract

USAGE_LOG_MIN_FIELDS = {"contract", "item", "do_ref", "qty", "snapshot_pct", "ts"}


def _mk_hospital(code, name):
	if frappe.db.exists("AntMed Hospital", code):
		return frappe.get_doc("AntMed Hospital", code)
	doc = frappe.get_doc({"doctype": "AntMed Hospital", "hospital_code": code, "hospital_name": name})
	doc.insert(ignore_permissions=True)
	return doc


def _quota_row(item, qty, lock=1, price=1000000):
	return {
		"item": item,
		"item_name": f"VT {item}",
		"uom": "Cái",
		"unit_price": price,
		"quota_qty": qty,
		"used_qty": 0,
		"remaining_pct": 100.0,
		"lock_at_100": lock,
	}


def _mk_active_contract(contract_no, hospital, items):
	"""HĐ hiệu lực = status 'Hiệu lực' + submit (docstatus 1)."""
	doc = frappe.get_doc(
		{
			"doctype": "AntMed Contract",
			"contract_no": contract_no,
			"hospital": hospital,
			"signed_date": "2026-01-05",
			"valid_from": "2026-01-05",
			"valid_to": "2026-12-31",
			"status": "Hiệu lực",
			"total_value": 1000000000,
			"items": items,
		}
	)
	doc.insert(ignore_permissions=True)
	doc.submit()
	return doc


def _mk_draft_contract(contract_no, hospital, items):
	doc = frappe.get_doc(
		{
			"doctype": "AntMed Contract",
			"contract_no": contract_no,
			"hospital": hospital,
			"signed_date": "2026-01-05",
			"status": "Nháp",
			"items": items,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


def _ensure_user(email, role=None):
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0}
		).insert(ignore_permissions=True)
	if role:
		user = frappe.get_doc("User", email)
		if role not in {r.role for r in user.roles}:
			user.add_roles(role)
	return email


class TestAntMedQuota(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hosp1 = _mk_hospital("_T-HOSP-Q1", "BV Quota 1").name
		cls.hosp2 = _mk_hospital("_T-HOSP-Q2", "BV Quota 2").name
		# HĐ hiệu lực của hosp1 với 4 item: Q1 (lock, q100), Q2 (unlock, q50),
		# CONSUME (lock, q100) cho test consume, RECOMP (lock, q100) cho test recompute.
		cls.ctA = _mk_active_contract(
			"_T-CTQ-A",
			cls.hosp1,
			items=[
				_quota_row("VTYT-Q1", 100, lock=1, price=5000000),
				_quota_row("VTYT-Q2", 50, lock=0, price=2000000),
				_quota_row("VTYT-CONSUME", 100, lock=1),
				_quota_row("VTYT-RECOMP", 100, lock=1),
			],
		).name
		# HĐ hiệu lực của hosp2 chứa item riêng → chứng minh hospital-scope.
		cls.ctB = _mk_active_contract(
			"_T-CTQ-B", cls.hosp2, items=[_quota_row("VTYT-ONLY2", 80, lock=1)]
		).name
		# HĐ nháp (docstatus 0) của hosp1 → KHÔNG được đối chiếu.
		cls.ctDraft = _mk_draft_contract(
			"_T-CTQ-DRAFT", cls.hosp1, items=[_quota_row("VTYT-DRAFT", 100, lock=1)]
		).name
		cls.plain_user = _ensure_user("_t_quota_plain@example.com")
		cls.manager_user = _ensure_user("_t_quota_manager@example.com", role="Quản lý")

	# --- DocType ------------------------------------------------------------
	def test_usage_log_doctype(self):
		self.assertTrue(frappe.db.exists("DocType", "AntMed Quota Usage Log"))
		fields = {f.fieldname for f in frappe.get_meta("AntMed Quota Usage Log").fields}
		self.assertTrue(
			USAGE_LOG_MIN_FIELDS.issubset(fields),
			msg=f"AntMed Quota Usage Log thiếu field: {USAGE_LOG_MIN_FIELDS - fields}",
		)
		# contract là Link → AntMed Contract
		c_field = frappe.get_meta("AntMed Quota Usage Log").get_field("contract")
		self.assertEqual(c_field.fieldtype, "Link")
		self.assertEqual(c_field.options, "AntMed Contract")

	# --- BR-01 / BR-02 : đối chiếu danh mục --------------------------------
	def test_assert_item_in_contract_found(self):
		self.assertEqual(contract_hooks.assert_item_in_contract(self.hosp1, "VTYT-Q1"), self.ctA)

	def test_assert_item_in_contract_blocks(self):
		"""User thường: item ngoài HĐ → throw BR-02 (KHÔNG chạy bằng Administrator: có mọi role)."""
		frappe.set_user(self.plain_user)
		try:
			with self.assertRaises(frappe.ValidationError) as cm:
				contract_hooks.assert_item_in_contract(self.hosp1, "VTYT-KHONG-CO")
			self.assertIn("BR-02", str(cm.exception))
		finally:
			frappe.set_user("Administrator")

	def test_assert_item_in_contract_override(self):
		"""Role Quản lý ghi đè BR-02 → trả None (cho qua, không throw)."""
		frappe.set_user(self.manager_user)
		try:
			self.assertIsNone(contract_hooks.assert_item_in_contract(self.hosp1, "VTYT-KHONG-CO"))
		finally:
			frappe.set_user("Administrator")

	def test_assert_item_in_contract_hospital_scope(self):
		"""Item chỉ thuộc HĐ của hosp2 → với hosp1 coi như ngoài HĐ (data không rò chéo BV)."""
		frappe.set_user(self.plain_user)
		try:
			with self.assertRaises(frappe.ValidationError):
				contract_hooks.assert_item_in_contract(self.hosp1, "VTYT-ONLY2")
		finally:
			frappe.set_user("Administrator")
		# nhưng đúng BV (hosp2) thì tìm thấy
		self.assertEqual(contract_hooks.assert_item_in_contract(self.hosp2, "VTYT-ONLY2"), self.ctB)

	def test_draft_contract_not_active(self):
		"""HĐ Nháp (docstatus 0) KHÔNG được đối chiếu → item của HĐ nháp coi như ngoài HĐ."""
		frappe.set_user(self.plain_user)
		try:
			with self.assertRaises(frappe.ValidationError):
				contract_hooks.assert_item_in_contract(self.hosp1, "VTYT-DRAFT")
		finally:
			frappe.set_user("Administrator")

	# --- BR-06 : quota chạm trần -------------------------------------------
	def test_assert_quota_available_ok(self):
		# còn 100, xin 50 → không throw
		contract_hooks.assert_quota_available(self.ctA, "VTYT-Q1", 50)

	def test_assert_quota_available_blocks_at_cap(self):
		with self.assertRaises(frappe.ValidationError) as cm:
			contract_hooks.assert_quota_available(self.ctA, "VTYT-Q1", 101)  # > trần 100, lock=1
		self.assertIn("BR-06", str(cm.exception))

	def test_assert_quota_available_unlocked(self):
		# lock_at_100=0 → cho qua dù vượt trần (chỉ cảnh báo, không chặn)
		contract_hooks.assert_quota_available(self.ctA, "VTYT-Q2", 999)

	# --- usage log + recompute ---------------------------------------------
	def test_consume_quota_and_recompute(self):
		"""consume → ghi log + derive used_qty == SUM(log), remaining_pct = (1-used/quota)*100."""
		contract_hooks.consume_quota(self.ctA, "VTYT-RECOMP", 20, do_ref="R-1")
		contract_hooks.consume_quota(self.ctA, "VTYT-RECOMP", 15, do_ref="R-2")
		total = frappe.db.sql(
			"""SELECT COALESCE(SUM(qty),0) FROM `tabAntMed Quota Usage Log`
			   WHERE contract=%s AND item=%s""",
			(self.ctA, "VTYT-RECOMP"),
		)[0][0]
		row = frappe.db.get_value(
			"AntMed Quota Item",
			{"parent": self.ctA, "item": "VTYT-RECOMP"},
			["used_qty", "remaining_pct", "quota_qty"],
			as_dict=True,
		)
		self.assertEqual(float(row.used_qty), float(total))  # invariant: used == tổng log
		self.assertGreaterEqual(float(total), 35.0)
		self.assertAlmostEqual(
			float(row.remaining_pct), round((1 - float(total) / float(row.quota_qty)) * 100, 2), places=2
		)

	def test_consume_quota_idempotent(self):
		"""Cùng (contract,item,do_ref) gọi 2 lần → chỉ 1 dòng log (LL-BE-7)."""
		contract_hooks.consume_quota(self.ctA, "VTYT-CONSUME", 30, do_ref="DO-IDEM")
		contract_hooks.consume_quota(self.ctA, "VTYT-CONSUME", 30, do_ref="DO-IDEM")
		count = frappe.db.count(
			"AntMed Quota Usage Log",
			{"contract": self.ctA, "item": "VTYT-CONSUME", "do_ref": "DO-IDEM"},
		)
		self.assertEqual(count, 1)

	# --- endpoint check_item_in_contract -----------------------------------
	def test_check_item_in_contract_found(self):
		res = contract.check_item_in_contract(self.hosp1, "VTYT-Q1")
		self.assertEqual(set(res.keys()), {"in_contract", "contract", "unit_price", "remaining_qty"})
		self.assertTrue(res["in_contract"])
		self.assertEqual(res["contract"], self.ctA)
		self.assertEqual(res["unit_price"], 5000000)
		self.assertIsNotNone(res["remaining_qty"])

	def test_check_item_in_contract_not_found(self):
		res = contract.check_item_in_contract(self.hosp1, "VTYT-KHONG-CO")
		self.assertEqual(
			res, {"in_contract": False, "contract": None, "unit_price": None, "remaining_qty": None}
		)
