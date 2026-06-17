# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M02 Slice M02-1 — Contract master + Quota Item (read-only) — harness test (TDD viết TRƯỚC).

Cover acceptance M02-1 (spec FROZEN m02_contract_quota.md §1bis):
  test_doctype_exists_and_submittable — 2 DocType tồn tại; AntMed Contract.is_submittable==1,
                                        AntMed Quota Item.istable==1.
  test_naming_series_am_hd           — tạo HĐ → name match ^AM-HD-\\d{4}-\\d+ (KHÔNG TC-/AM-DR-).
  test_doctype_min_fields            — meta 2 DocType có đủ field tối thiểu (verify §1bis.1/.2).
  test_contract_no_unique            — 2 HĐ cùng contract_no → raise.
  test_list_contracts_shape          — list_contracts() trả {data,total_count}; item đúng 7 field;
                                        len(data)==total_count khi page_length=0 (BR-13 count==rows).
  test_list_contracts_filter_search  — filter hospital + search contract_no lọc đúng.
  test_get_contract_resolves         — get_contract trả items[] + hospital_name resolve qua Link
                                        + đơn giá/quota đúng.
  test_submit_contract_docstatus     — submit HĐ hợp lệ → docstatus==1.
  test_permission_guard              — user không read → get_contract raise PermissionError.
  test_docperm_nv_read_only          — DocPerm VI: Quản lý full; NV kinh doanh read-only
                                        (KHÔNG write/create/delete); Thủ kho read; KHÔNG role EN.

Lệnh chạy:
  bench --site miyano run-tests --module crm.tests.test_antmed_contract
"""

import re

import frappe
from frappe.tests.utils import FrappeTestCase

from crm.api.antmed import contract

# Field tối thiểu theo spec §1bis.1 / §1bis.2.
CONTRACT_MIN_FIELDS = {
	"naming_series",
	"contract_no",
	"hospital",
	"status",
	"signed_date",
	"valid_from",
	"valid_to",
	"total_value",
	"items",
}
QUOTA_ITEM_MIN_FIELDS = {
	"item",
	"item_name",
	"uom",
	"unit_price",
	"quota_qty",
	"used_qty",
	"remaining_pct",
	"lock_at_100",
}

# Item-shape chốt với FE (Hyrum — đổi = breaking binding createResource).
CONTRACT_LIST_ITEM_FIELDS = {
	"name",
	"contract_no",
	"hospital",
	"hospital_name",
	"valid_to",
	"total_value",
	"status",
}
# Shape mỗi dòng quota trong get_contract.
QUOTA_ROW_FIELDS = {
	"item",
	"item_name",
	"uom",
	"unit_price",
	"quota_qty",
	"used_qty",
	"remaining_pct",
	"lock_at_100",
}

NAME_RE = re.compile(r"^AM-HD-\d{4}-\d+")


def _mk_hospital(code, name, **kw):
	if frappe.db.exists("AntMed Hospital", code):
		return frappe.get_doc("AntMed Hospital", code)
	doc = frappe.get_doc(
		{"doctype": "AntMed Hospital", "hospital_code": code, "hospital_name": name, **kw}
	)
	doc.insert(ignore_permissions=True)
	return doc


def _mk_contract(contract_no, hospital, items=None, **kw):
	doc = frappe.get_doc(
		{
			"doctype": "AntMed Contract",
			"contract_no": contract_no,
			"hospital": hospital,
			"signed_date": kw.pop("signed_date", "2026-01-05"),
			"items": items or [],
			**kw,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


class TestAntMedContract(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hosp = _mk_hospital(
			"_T-HOSP-CT",
			"BV Test Contract",
			rank="Đặc biệt",
			contract_status="Đã ký",
		)
		cls.hosp2 = _mk_hospital("_T-HOSP-CT2", "BV Khác Contract", contract_status="Tiềm năng")
		# HĐ 1 (thuộc hosp) có 1 dòng quota để verify get_contract.
		cls.ct1 = _mk_contract(
			"_T-CT-001",
			cls.hosp.name,
			items=[
				{
					"item": "VTYT-001",
					"item_name": "Stent mạch vành",
					"uom": "Cái",
					"unit_price": 12000000,
					"quota_qty": 100,
					"used_qty": 0,
					"remaining_pct": 100.0,
					"lock_at_100": 1,
				}
			],
			status="Hiệu lực",
			valid_from="2026-01-05",
			valid_to="2026-12-31",
			total_value=1500000000,
		)
		# HĐ 2 (thuộc hosp2) — để chứng minh filter hospital không rò.
		cls.ct2 = _mk_contract(
			"_T-CT-002",
			cls.hosp2.name,
			status="Nháp",
			valid_to="2026-06-30",
			total_value=500000000,
		)

	# --- DocType existence + submittable ------------------------------------
	def test_doctype_exists_and_submittable(self):
		self.assertTrue(frappe.db.exists("DocType", "AntMed Contract"))
		self.assertTrue(frappe.db.exists("DocType", "AntMed Quota Item"))
		self.assertEqual(frappe.get_meta("AntMed Contract").is_submittable, 1)
		self.assertEqual(frappe.get_meta("AntMed Quota Item").istable, 1)
		# track_changes bật (acceptance)
		self.assertEqual(frappe.get_meta("AntMed Contract").track_changes, 1)

	def test_naming_series_am_hd(self):
		"""name sinh theo series AM-HD-YYYY-##### (KHÔNG TC-/AM-DR-/AM-DOC-)."""
		self.assertRegex(self.ct1.name, NAME_RE)
		self.assertFalse(self.ct1.name.startswith("TC-"))
		self.assertFalse(self.ct1.name.startswith("AM-DR"))
		self.assertFalse(self.ct1.name.startswith("AM-DOC"))

	def test_doctype_min_fields(self):
		ct_fields = {f.fieldname for f in frappe.get_meta("AntMed Contract").fields}
		self.assertTrue(
			CONTRACT_MIN_FIELDS.issubset(ct_fields),
			msg=f"AntMed Contract thiếu field: {CONTRACT_MIN_FIELDS - ct_fields}",
		)
		qi_fields = {f.fieldname for f in frappe.get_meta("AntMed Quota Item").fields}
		self.assertTrue(
			QUOTA_ITEM_MIN_FIELDS.issubset(qi_fields),
			msg=f"AntMed Quota Item thiếu field: {QUOTA_ITEM_MIN_FIELDS - qi_fields}",
		)
		# hospital là Link → AntMed Hospital
		hosp_field = frappe.get_meta("AntMed Contract").get_field("hospital")
		self.assertEqual(hosp_field.fieldtype, "Link")
		self.assertEqual(hosp_field.options, "AntMed Hospital")
		# items là Table → AntMed Quota Item
		items_field = frappe.get_meta("AntMed Contract").get_field("items")
		self.assertEqual(items_field.fieldtype, "Table")
		self.assertEqual(items_field.options, "AntMed Quota Item")
		# used_qty / remaining_pct read_only
		qmeta = frappe.get_meta("AntMed Quota Item")
		self.assertEqual(qmeta.get_field("used_qty").read_only, 1)
		self.assertEqual(qmeta.get_field("remaining_pct").read_only, 1)

	def test_contract_no_unique(self):
		"""contract_no unique — tạo HĐ thứ 2 cùng contract_no → raise."""
		with self.assertRaises(
			(frappe.UniqueValidationError, frappe.DuplicateEntryError, frappe.ValidationError)
		):
			_mk_contract("_T-CT-001", self.hosp.name)

	# --- list_contracts -----------------------------------------------------
	def test_list_contracts_shape(self):
		res = contract.list_contracts(page_length=0)
		self.assertIsInstance(res, dict)
		self.assertEqual(set(res.keys()), {"data", "total_count"})
		self.assertIsInstance(res["data"], list)
		self.assertIsInstance(res["total_count"], int)
		self.assertGreaterEqual(len(res["data"]), 2)
		item = res["data"][0]
		self.assertEqual(set(item.keys()), CONTRACT_LIST_ITEM_FIELDS)
		# BR-13 count == rows khi không phân trang
		self.assertEqual(len(res["data"]), res["total_count"])

	def test_list_contracts_filter_search(self):
		# filter hospital
		res = contract.list_contracts(filters={"hospital": self.hosp.name}, page_length=0)
		names = {r["name"] for r in res["data"]}
		self.assertIn(self.ct1.name, names)
		self.assertNotIn(self.ct2.name, names)
		self.assertEqual(len(res["data"]), res["total_count"])
		# hospital_name resolve qua Link trong list (dotted-fetch)
		row = next(r for r in res["data"] if r["name"] == self.ct1.name)
		self.assertEqual(row["hospital_name"], "BV Test Contract")
		# search contract_no
		res2 = contract.list_contracts(search="_T-CT-001", page_length=0)
		names2 = {r["name"] for r in res2["data"]}
		self.assertIn(self.ct1.name, names2)
		self.assertNotIn(self.ct2.name, names2)
		self.assertEqual(len(res2["data"]), res2["total_count"])

	def test_list_contracts_filter_status(self):
		"""Acceptance gọi 'workflow_state/status' — M02-1 field là status; key workflow_state map về status."""
		res = contract.list_contracts(filters={"workflow_state": "Hiệu lực"}, page_length=0)
		names = {r["name"] for r in res["data"]}
		self.assertIn(self.ct1.name, names)
		self.assertNotIn(self.ct2.name, names)

	# --- get_contract -------------------------------------------------------
	def test_get_contract_resolves(self):
		res = contract.get_contract(self.ct1.name)
		self.assertEqual(res["name"], self.ct1.name)
		self.assertEqual(res["contract_no"], "_T-CT-001")
		self.assertEqual(res["hospital"], self.hosp.name)
		self.assertEqual(res["hospital_name"], "BV Test Contract")
		self.assertEqual(res["status"], "Hiệu lực")
		self.assertEqual(res["total_value"], 1500000000)
		self.assertIn("items", res)
		self.assertEqual(len(res["items"]), 1)
		row = res["items"][0]
		self.assertEqual(set(row.keys()), QUOTA_ROW_FIELDS)
		self.assertEqual(row["item"], "VTYT-001")
		self.assertEqual(row["item_name"], "Stent mạch vành")
		self.assertEqual(row["unit_price"], 12000000)
		self.assertEqual(row["quota_qty"], 100)
		self.assertEqual(row["lock_at_100"], 1)

	def test_submit_contract_docstatus(self):
		"""Submit 1 HĐ hợp lệ → docstatus==1 (verify submittable hoạt động; KHÔNG enforce BR)."""
		ct = _mk_contract(
			"_T-CT-SUBMIT",
			self.hosp.name,
			status="Hiệu lực",
			valid_to="2026-12-31",
			total_value=100000000,
		)
		ct.submit()
		self.assertEqual(ct.docstatus, 1)

	# --- permission guard ---------------------------------------------------
	def test_permission_guard(self):
		"""User không read-perm → get_contract raise frappe.PermissionError."""
		email = "_t_antmed_ct_noperm@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": "NoPermCT",
					"send_welcome_email": 0,
				}
			).insert(ignore_permissions=True)
		frappe.set_user(email)
		try:
			with self.assertRaises(frappe.PermissionError):
				contract.get_contract(self.ct1.name)
		finally:
			frappe.set_user("Administrator")

	def test_list_contracts_no_leak_for_noperm_user(self):
		"""User KHÔNG read-perm → list_contracts KHÔNG rò bản ghi (raise hoặc rỗng)."""
		email = "_t_antmed_ct_noperm@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": "NoPermCT", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		self.assertGreaterEqual(contract.list_contracts(page_length=0)["total_count"], 2)
		frappe.set_user(email)
		try:
			try:
				res = contract.list_contracts(page_length=0)
			except frappe.PermissionError:
				return  # an toàn: chặn ngay
			self.assertEqual(res["total_count"], 0, msg=f"LEAK: {res}")
			self.assertEqual(len(res["data"]), 0, msg=f"LEAK rows: {res}")
		finally:
			frappe.set_user("Administrator")

	# --- DocPerm VI ---------------------------------------------------------
	def test_docperm_nv_read_only(self):
		"""DocPerm VI: Quản lý full; NV kinh doanh read-only (KHÔNG write/create/delete);
		Thủ kho read; System Manager full; KHÔNG role EN."""
		legacy_en = {"AntMed Manager", "AntMed Sales Rep", "AntMed Warehouse Keeper", "AM System Admin"}
		perms = {p.role: p for p in frappe.get_meta("AntMed Contract").permissions}
		self.assertEqual(
			legacy_en & set(perms), set(), msg=f"Còn DocPerm role EN/legacy: {legacy_en & set(perms)}"
		)
		# System Manager + Quản lý full
		for role in ("System Manager", "Quản lý"):
			self.assertIn(role, perms, msg=f"thiếu DocPerm '{role}'")
			p = perms[role]
			self.assertTrue(
				p.read and p.write and p.create and p.delete and p.submit and p.cancel,
				msg=f"'{role}' phải full (read/write/create/delete/submit/cancel)",
			)
		# NV kinh doanh: read-only — KHÔNG write/create/delete
		self.assertIn("NV kinh doanh", perms)
		nv = perms["NV kinh doanh"]
		self.assertTrue(nv.read, msg="NV kinh doanh phải read")
		self.assertFalse(nv.write, msg="NV kinh doanh KHÔNG được write (BR DocPerm M02)")
		self.assertFalse(nv.create, msg="NV kinh doanh KHÔNG được create")
		self.assertFalse(nv.delete, msg="NV kinh doanh KHÔNG được delete")
		# Thủ kho: read-only
		self.assertIn("Thủ kho", perms)
		tk = perms["Thủ kho"]
		self.assertTrue(tk.read, msg="Thủ kho phải read")
		self.assertFalse(tk.write, msg="Thủ kho KHÔNG được write")
