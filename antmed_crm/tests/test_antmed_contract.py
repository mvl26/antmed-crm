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
  bench --site miyano run-tests --module antmed_crm.tests.test_antmed_contract
"""

import re

import frappe
from frappe.tests.utils import FrappeTestCase

from antmed_crm.api.antmed import contract

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
	doc = frappe.get_doc({"doctype": "AntMed Hospital", "hospital_code": code, "hospital_name": name, **kw})
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


# Shape item top_hospitals (Hyrum — 5 key, FROZEN §1quater item shape; đổi = breaking FE bind).
TOP_HOSPITAL_ITEM_KEYS = {
	"hospital",
	"hospital_name",
	"revenue",
	"quota_used_pct",
	"health_color",
}


def _quota_row(item, quota, used):
	"""1 dòng quota tối thiểu cho seed top_hospitals."""
	return {
		"item": item,
		"item_name": f"VT {item}",
		"uom": "Cái",
		"unit_price": 1000000,
		"quota_qty": quota,
		"used_qty": used,
		"remaining_pct": round((1 - used / quota) * 100, 2) if quota else 0,
		"lock_at_100": 1,
	}


class TestAntMedTopHospitals(FrappeTestCase):
	"""M02 Slice M02-4 — endpoint MỚI top_hospitals (widget "Top 10 Bệnh viện" CEO).

	Spec FROZEN m02_contract_quota.md §1quater.1/.5. health_color = _health_color(pct, None)
	(ADR-M02-08) ⇒ ngưỡng quota: green ≤80 / orange >80–100 / red >100 (rank-by-revenue,
	KHÔNG xét hạn). data sort GIẢM theo revenue, cắt ≤ limit; total_count = số BV phân biệt
	trong scope (KHÔNG cắt). BR-13: chỉ BV/HĐ user đọc được (frappe.get_list, KHÔNG raw SQL).

	Lệnh chạy:
	  bench --site miyano run-tests --module antmed_crm.tests.test_antmed_contract
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# 3 BV doanh thu khác nhau (rev: A=3 tỷ > B=2 tỷ > C=1 tỷ) để verify sort giảm.
		# A: 2 HĐ (gộp revenue + gộp quota across HĐ) — quota tổng 100 dùng 50 → 50% → green.
		cls.hA = _mk_hospital("_T-TH-A", "BV Top A")
		_mk_contract(
			"_T-TH-A1",
			cls.hA.name,
			items=[_quota_row("VTA1", 40, 30)],
			status="Hiệu lực",
			valid_to="2027-12-31",
			total_value=2000000000,
		)
		_mk_contract(
			"_T-TH-A2",
			cls.hA.name,
			items=[_quota_row("VTA2", 60, 20)],
			status="Hiệu lực",
			valid_to="2027-12-31",
			total_value=1000000000,
		)
		# B: 1 HĐ — quota 100 dùng 95 → 95% → orange (>80, ≤100).
		cls.hB = _mk_hospital("_T-TH-B", "BV Top B")
		_mk_contract(
			"_T-TH-B1",
			cls.hB.name,
			items=[_quota_row("VTB1", 100, 95)],
			status="Hiệu lực",
			valid_to="2027-12-31",
			total_value=2000000000,
		)
		# C: 1 HĐ — quota 100 dùng 120 → 120% → red (>100, over-cap).
		cls.hC = _mk_hospital("_T-TH-C", "BV Top C")
		_mk_contract(
			"_T-TH-C1",
			cls.hC.name,
			items=[_quota_row("VTC1", 100, 120)],
			status="Hiệu lực",
			valid_to="2027-12-31",
			total_value=1000000000,
		)
		# D: HĐ KHÔNG quota → quota_used_pct == 0.0 & green.
		cls.hD = _mk_hospital("_T-TH-D", "BV Top D")
		_mk_contract(
			"_T-TH-D1",
			cls.hD.name,
			status="Hiệu lực",
			valid_to="2027-12-31",
			total_value=500000000,
		)

	def _by_hospital(self, data):
		return {r["hospital"]: r for r in data}

	# --- shape ---------------------------------------------------------------
	def test_top_hospitals_shape(self):
		res = contract.top_hospitals()
		self.assertIsInstance(res, dict)
		self.assertEqual(set(res.keys()), {"data", "total_count"})
		self.assertIsInstance(res["data"], list)
		self.assertIsInstance(res["total_count"], int)
		self.assertGreaterEqual(len(res["data"]), 4)
		for row in res["data"]:
			self.assertEqual(set(row.keys()), TOP_HOSPITAL_ITEM_KEYS)
		self.assertGreaterEqual(res["total_count"], 4)

	# --- sort giảm revenue ---------------------------------------------------
	def test_top_hospitals_sort_desc_revenue(self):
		res = contract.top_hospitals()
		revenues = [r["revenue"] for r in res["data"]]
		self.assertEqual(revenues, sorted(revenues, reverse=True), msg=f"chưa sort giảm: {revenues}")
		idx = {r["hospital"]: i for i, r in enumerate(res["data"])}
		self.assertLess(idx[self.hA.name], idx[self.hB.name])
		self.assertLess(idx[self.hB.name], idx[self.hC.name])

	# --- limit cắt đúng ------------------------------------------------------
	def test_top_hospitals_limit(self):
		for i in range(12):
			h = _mk_hospital(f"_T-THL-{i:02d}", f"BV Limit {i}")
			_mk_contract(
				f"_T-THL-CT-{i:02d}",
				h.name,
				status="Hiệu lực",
				valid_to="2027-12-31",
				total_value=100000000 * (i + 1),
			)
		res = contract.top_hospitals()
		self.assertEqual(len(res["data"]), 10, msg="limit mặc định phải cắt đúng 10 dòng")
		self.assertGreaterEqual(res["total_count"], 11)
		res3 = contract.top_hospitals(limit=3)
		self.assertEqual(len(res3["data"]), 3)
		self.assertEqual(res3["total_count"], res["total_count"], msg="total_count KHÔNG đổi theo limit")
		revs = [r["revenue"] for r in res3["data"]]
		self.assertEqual(revs, sorted(revs, reverse=True))

	# --- gộp revenue + quota theo từng BV -----------------------------------
	def test_top_hospitals_aggregate_by_bv(self):
		res = contract.top_hospitals(limit=50)
		by = self._by_hospital(res["data"])
		self.assertIn(self.hA.name, by)
		self.assertEqual(by[self.hA.name]["revenue"], 3000000000)
		self.assertEqual(by[self.hA.name]["hospital_name"], "BV Top A")
		# quota gộp across HĐ: quota = 40+60 = 100; used = 30+20 = 50 → 50.0%.
		self.assertEqual(by[self.hA.name]["quota_used_pct"], 50.0)

	# --- health_color theo ngưỡng (ADR-M02-08: _health_color(pct, None)) -----
	def test_top_hospitals_health_color(self):
		res = contract.top_hospitals(limit=50)
		by = self._by_hospital(res["data"])
		# A: 50% ≤80 → green
		self.assertEqual(by[self.hA.name]["quota_used_pct"], 50.0)
		self.assertEqual(by[self.hA.name]["health_color"], "green")
		# B: 95% (>80, ≤100) → orange
		self.assertEqual(by[self.hB.name]["quota_used_pct"], 95.0)
		self.assertEqual(by[self.hB.name]["health_color"], "orange")
		# C: 120% (>100) → red
		self.assertEqual(by[self.hC.name]["quota_used_pct"], 120.0)
		self.assertEqual(by[self.hC.name]["health_color"], "red")
		# D: không quota → 0.0% & green
		self.assertEqual(by[self.hD.name]["quota_used_pct"], 0.0)
		self.assertEqual(by[self.hD.name]["health_color"], "green")

	# --- empty / fail-closed (noperm) ---------------------------------------
	def test_top_hospitals_empty(self):
		"""User KHÔNG read-perm → {"data": [], "total_count": 0} (fail-closed, get_list)."""
		email = "_t_th_noperm@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": "NoPermTH", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		self.assertGreaterEqual(contract.top_hospitals()["total_count"], 4)
		frappe.set_user(email)
		try:
			res = contract.top_hospitals()
			self.assertEqual(res, {"data": [], "total_count": 0}, msg=f"LEAK/không fail-closed: {res}")
		finally:
			frappe.set_user("Administrator")

	# --- data-scope BR-13 (User Permission trên AntMed Hospital) -------------
	def test_top_hospitals_respects_permission(self):
		"""User có read (NV kinh doanh) NHƯNG bị User Permission giới hạn 1 BV → chỉ thấy BV đó."""
		role = "NV kinh doanh"
		email = "_t_th_scoped@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": "ScopedTH",
					"send_welcome_email": 0,
					"roles": [{"role": role}],
				}
			).insert(ignore_permissions=True)
		else:
			u = frappe.get_doc("User", email)
			if role not in [r.role for r in u.roles]:
				u.add_roles(role)
		if not frappe.db.exists(
			"User Permission", {"user": email, "allow": "AntMed Hospital", "for_value": self.hA.name}
		):
			frappe.get_doc(
				{
					"doctype": "User Permission",
					"user": email,
					"allow": "AntMed Hospital",
					"for_value": self.hA.name,
				}
			).insert(ignore_permissions=True)
		frappe.set_user(email)
		try:
			res = contract.top_hospitals(limit=50)
			names = {r["hospital"] for r in res["data"]}
			self.assertEqual(names, {self.hA.name}, msg=f"data-scope vỡ: thấy BV ngoài quyền {names}")
			self.assertEqual(res["total_count"], 1, msg=f"total_count phải = 1 BV trong scope: {res}")
			self.assertEqual(res["data"][0]["revenue"], 3000000000)
		finally:
			frappe.set_user("Administrator")
			frappe.db.delete(
				"User Permission",
				{"user": email, "allow": "AntMed Hospital", "for_value": self.hA.name},
			)


# Shape item top_quota_items (Hyrum — 6 key, FROZEN §1quinquies item shape; đổi = breaking FE bind).
TOP_QUOTA_ITEM_KEYS = {
	"item",
	"item_name",
	"quota_qty",
	"used_qty",
	"used_pct",
	"health_color",
}


class TestAntMedTopQuotaItems(FrappeTestCase):
	"""M02 Slice M02-5 — endpoint MỚI top_quota_items (widget "Danh mục VT trúng thầu — top 5" CEO).

	Spec FROZEN m02_contract_quota.md §1quinquies. used_pct gộp CROSS-CONTRACT theo item:
	used_pct = round(100*SUM(used_qty)/SUM(quota_qty), 1) (0.0 fail-safe khi SUM(quota)==0).
	health_color = _health_color(used_pct, None) — TÁI DÙNG (cùng map contract-health & top_hospitals):
	green ≤80 / orange >80–100 / red >100. data sort GIẢM theo used_pct, cắt ≤ limit;
	total_count = số item phân biệt trong scope (KHÔNG cắt). BR-13: chỉ HĐ user đọc được
	(frappe.get_list, KHÔNG raw SQL) → noperm → data==[] / total_count==0 (fail-closed).

	Lệnh chạy:
	  bench --site miyano run-tests --module antmed_crm.tests.test_antmed_contract
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# BV để treo HĐ seed (mỗi item-band 1 HĐ riêng để verify ngưỡng màu + sort).
		cls.hq = _mk_hospital("_T-TQI-HOSP", "BV Top Quota Items")
		# Item RED ≥ ngưỡng đỏ (>100): quota 100, used 130 → 130.0% → red.
		_mk_contract(
			"_T-TQI-CT-R",
			cls.hq.name,
			items=[_quota_row("VT-RED", 100, 130)],
			status="Hiệu lực",
			valid_to="2027-12-31",
			total_value=10,
		)
		# Item ORANGE (>80, ≤100): quota 100, used 90 → 90.0% → orange.
		_mk_contract(
			"_T-TQI-CT-O",
			cls.hq.name,
			items=[_quota_row("VT-ORANGE", 100, 90)],
			status="Hiệu lực",
			valid_to="2027-12-31",
			total_value=10,
		)
		# Item GREEN (≤80): quota 100, used 40 → 40.0% → green.
		_mk_contract(
			"_T-TQI-CT-G",
			cls.hq.name,
			items=[_quota_row("VT-GREEN", 100, 40)],
			status="Hiệu lực",
			valid_to="2027-12-31",
			total_value=10,
		)
		# Item CROSS: VT-CROSS xuất hiện ở 2 HĐ khác nhau → gộp 1 dòng.
		#   HĐ1: quota 100, used 10 ; HĐ2: quota 300, used 90 → sum 100/400 = 25.0%.
		_mk_contract(
			"_T-TQI-CT-X1",
			cls.hq.name,
			items=[_quota_row("VT-CROSS", 100, 10)],
			status="Hiệu lực",
			valid_to="2027-12-31",
			total_value=10,
		)
		_mk_contract(
			"_T-TQI-CT-X2",
			cls.hq.name,
			items=[_quota_row("VT-CROSS", 300, 90)],
			status="Hiệu lực",
			valid_to="2027-12-31",
			total_value=10,
		)
		# Item ZERO-QUOTA: quota 0 → used_pct == 0.0 (fail-safe, KHÔNG ZeroDivisionError).
		_mk_contract(
			"_T-TQI-CT-Z",
			cls.hq.name,
			items=[_quota_row("VT-ZERO", 0, 0)],
			status="Hiệu lực",
			valid_to="2027-12-31",
			total_value=10,
		)

	def _by_item(self, data):
		return {r["item"]: r for r in data}

	# --- shape ---------------------------------------------------------------
	def test_top_quota_items_shape(self):
		res = contract.top_quota_items()
		self.assertIsInstance(res, dict)
		self.assertEqual(set(res.keys()), {"data", "total_count"})
		self.assertIsInstance(res["data"], list)
		self.assertIsInstance(res["total_count"], int)
		self.assertGreaterEqual(len(res["data"]), 1)
		for row in res["data"]:
			self.assertEqual(set(row.keys()), TOP_QUOTA_ITEM_KEYS)
			self.assertIsInstance(row["quota_qty"], (int, float))
			self.assertIsInstance(row["used_qty"], (int, float))
			self.assertIsInstance(row["used_pct"], (int, float))
			self.assertIn(row["health_color"], ("green", "orange", "red"))

	# --- sort GIẢM theo used_pct --------------------------------------------
	def test_top_quota_items_sort_desc_pct(self):
		data = contract.top_quota_items(limit=200)["data"]
		pcts = [r["used_pct"] for r in data]
		self.assertEqual(pcts, sorted(pcts, reverse=True), msg=f"chưa sort giảm used_pct: {pcts}")
		# Đầu danh sách phải >= dòng kế (cụ thể row[0] >= row[1] khi có ≥2 dòng).
		if len(data) >= 2:
			self.assertGreaterEqual(data[0]["used_pct"], data[1]["used_pct"])

	# --- limit cắt đúng ------------------------------------------------------
	def test_top_quota_items_limit(self):
		res2 = contract.top_quota_items(limit=2)
		self.assertLessEqual(len(res2["data"]), 2)
		# default limit=5
		res = contract.top_quota_items()
		self.assertLessEqual(len(res["data"]), 5)
		# total_count KHÔNG đổi theo limit (số item phân biệt trong scope)
		self.assertEqual(res2["total_count"], res["total_count"])
		# limit ≤ 0 → tối thiểu 1 (không lỗi, không rỗng khi có data)
		self.assertGreaterEqual(len(contract.top_quota_items(limit=0)["data"]), 1)

	# --- gộp CROSS-CONTRACT theo item ---------------------------------------
	def test_top_quota_items_aggregate_cross_contract(self):
		"""Cùng 1 item ở 2 HĐ khác nhau → gộp 1 dòng: quota=100+300=400, used=10+90=100 → 25.0%."""
		by = self._by_item(contract.top_quota_items(limit=200)["data"])
		self.assertIn("VT-CROSS", by)
		row = by["VT-CROSS"]
		self.assertEqual(row["quota_qty"], 400)
		self.assertEqual(row["used_qty"], 100)
		self.assertEqual(row["used_pct"], 25.0)

	# --- zero-quota fail-safe ------------------------------------------------
	def test_top_quota_items_zero_quota_safe(self):
		"""Item sum_quota==0 → used_pct == 0.0, KHÔNG ZeroDivisionError."""
		by = self._by_item(contract.top_quota_items(limit=200)["data"])
		self.assertIn("VT-ZERO", by)
		self.assertEqual(by["VT-ZERO"]["quota_qty"], 0)
		self.assertEqual(by["VT-ZERO"]["used_pct"], 0.0)
		self.assertEqual(by["VT-ZERO"]["health_color"], "green")

	# --- health_color theo ngưỡng (ADR-M02-08: _health_color(pct, None)) -----
	def test_top_quota_items_health_color(self):
		by = self._by_item(contract.top_quota_items(limit=200)["data"])
		# RED: 130% (>100) → red (used_pct cao >= ngưỡng đỏ khớp _health_color)
		self.assertEqual(by["VT-RED"]["used_pct"], 130.0)
		self.assertEqual(by["VT-RED"]["health_color"], "red")
		self.assertEqual(by["VT-RED"]["health_color"], contract._health_color(130.0, None))
		# ORANGE: 90% (>80, ≤100) → orange
		self.assertEqual(by["VT-ORANGE"]["health_color"], "orange")
		self.assertEqual(by["VT-ORANGE"]["health_color"], contract._health_color(90.0, None))
		# GREEN: 40% (≤80) → green
		self.assertEqual(by["VT-GREEN"]["health_color"], "green")
		self.assertEqual(by["VT-GREEN"]["health_color"], contract._health_color(40.0, None))

	# --- empty / fail-closed (noperm) — BR-13 KHÔNG rò --------------------
	def test_top_quota_items_empty_fail_closed(self):
		"""User KHÔNG read-perm → {"data": [], "total_count": 0} (fail-closed, get_list)."""
		email = "_t_tqi_noperm@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": "NoPermTQI", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		self.assertGreaterEqual(contract.top_quota_items()["total_count"], 1)
		frappe.set_user(email)
		try:
			try:
				res = contract.top_quota_items()
			except frappe.PermissionError:
				return  # an toàn: chặn ngay tại get_list (0 read-perm) — không rò dữ liệu
			self.assertEqual(res["data"], [], msg=f"LEAK rows: {res}")
			self.assertEqual(res["total_count"], 0, msg=f"LEAK: {res}")
		finally:
			frappe.set_user("Administrator")

	# --- KHÔNG raw SQL (tôn trọng BR-13) ------------------------------------
	def test_top_quota_items_no_raw_sql(self):
		import inspect

		src = inspect.getsource(contract.top_quota_items)
		self.assertNotIn("frappe.db.sql", src, msg="top_quota_items KHÔNG được dùng raw SQL (bỏ qua BR-13)")
		self.assertIn("get_list", src, msg="top_quota_items phải dùng frappe.get_list (tôn trọng permission)")

	# --- regression cleanup: chỉ còn 1 def top_hospitals --------------------
	def test_no_duplicate_top_hospitals_def(self):
		"""Sau cleanup (M02-5): module CHỈ còn 1 def top_hospitals + resolve qua frappe.get_attr.
		Đếm số lần xuất hiện 'def top_hospitals(' trong source module = đúng 1 (KHÔNG dead def trùng).
		Đồng thời top_hospitals + top_quota_items đều resolve callable."""
		import inspect

		mod_src = inspect.getsource(contract)
		self.assertEqual(
			mod_src.count("def top_hospitals("),
			1,
			msg="contract.py phải CHỈ còn 1 def top_hospitals (đã gỡ def trùng vòng 10)",
		)
		# Cả 2 endpoint resolve đúng qua frappe.get_attr (path FE gọi).
		fn_th = frappe.get_attr("antmed_crm.api.antmed.contract.top_hospitals")
		fn_tqi = frappe.get_attr("antmed_crm.api.antmed.contract.top_quota_items")
		self.assertTrue(callable(fn_th))
		self.assertTrue(callable(fn_tqi))


# Shape mỗi bucket tháng (Hyrum — 3 key, FROZEN item shape; đổi = breaking FE bind bar chart).
CONSUMPTION_BUCKET_KEYS = {"month", "label", "qty"}

QUOTA_USAGE_DOCTYPE = "AntMed Quota Usage Log"


def _mk_usage_log(contract_name, qty, ts):
	"""Seed 1 dòng AntMed Quota Usage Log với `ts` cụ thể.

	`ts` là Datetime read-only (default now) → insert rồi ép giá trị qua frappe.db.set_value
	(test-only) để xếp đúng bucket tháng. `item` reqd → dùng SKU placeholder.
	"""
	doc = frappe.get_doc(
		{
			"doctype": QUOTA_USAGE_DOCTYPE,
			"contract": contract_name,
			"item": "VTYT-CONS",
			"qty": qty,
		}
	)
	doc.insert(ignore_permissions=True)
	frappe.db.set_value(QUOTA_USAGE_DOCTYPE, doc.name, "ts", ts, update_modified=False)
	return doc


class TestAntMedContractConsumptionByMonth(FrappeTestCase):
	"""M02 Slice M02-6 — endpoint MỚI contract_consumption_by_month (widget "Tiêu hao HĐ
	theo tháng" CEO, mockup A1, dưới bảng quota màn Chi tiết HĐ).

	Cửa sổ: rolling 12 tháng tính TỚI tháng hiện tại (BA chốt — ADR cửa sổ trong endpoint).
	Trả RAW {data, total_qty, contract}; data = ĐÚNG 12 bucket tháng tăng dần, mỗi bucket
	{month:'YYYY-MM', label:'T<m>', qty:<float>}; tháng trống qty=0.0 (KHÔNG bỏ cột).
	BR-13 fail-closed: user KHÔNG read-perm trên HĐ → {data:[], total_qty:0, contract:<name>}
	(KHÔNG rò, KHÔNG leak). frappe.get_all/get_doc — KHÔNG raw SQL.

	Lệnh chạy:
	  bench --site miyano run-tests --module antmed_crm.tests.test_antmed_contract
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hosp = _mk_hospital("_T-CONS-HOSP", "BV Tiêu Hao")
		# HĐ chính để gắn log tiêu hao.
		cls.ct = _mk_contract(
			"_T-CONS-CT",
			cls.hosp.name,
			status="Hiệu lực",
			valid_from="2025-01-01",
			valid_to="2027-12-31",
			total_value=1000000000,
		)
		# HĐ KHÁC — log của nó KHÔNG được lọt vào kết quả của cls.ct.
		cls.ct_other = _mk_contract(
			"_T-CONS-CT-OTHER",
			cls.hosp.name,
			status="Hiệu lực",
			valid_from="2025-01-01",
			valid_to="2027-12-31",
			total_value=500000000,
		)
		# Mốc tháng (theo cửa sổ rolling 12 tháng tính tới tháng hiện tại).
		from frappe.utils import add_months, getdate, nowdate

		today = getdate(nowdate())
		# Tháng hiện tại (M0), 1 tháng trước (M1), 2 tháng trước (M2) — 3 bucket có log.
		cls.m0 = today.strftime("%Y-%m")
		cls.m1 = add_months(today, -1).strftime("%Y-%m")
		cls.m2 = add_months(today, -2).strftime("%Y-%m")
		# Datetime đại diện đầu mỗi tháng (an toàn trong bucket — KHÔNG dùng ngày 28..31).
		cls.ts_m0 = cls.m0 + "-05 10:00:00"
		cls.ts_m1 = cls.m1 + "-05 10:00:00"
		cls.ts_m2 = cls.m2 + "-05 10:00:00"

		# cls.ct: tháng M0 có 2 log (4+6=10) → verify SUM; tháng M1 = 5; tháng M2 = 3.
		_mk_usage_log(cls.ct.name, 4, cls.ts_m0)
		_mk_usage_log(cls.ct.name, 6, cls.ts_m0)
		_mk_usage_log(cls.ct.name, 5, cls.ts_m1)
		_mk_usage_log(cls.ct.name, 3, cls.ts_m2)
		# HĐ khác có log cùng tháng M0 — phải bị loại khỏi kết quả cls.ct.
		_mk_usage_log(cls.ct_other.name, 99, cls.ts_m0)

	def _by_month(self, data):
		return {b["month"]: b for b in data}

	# --- shape: data là list 12 bucket, mỗi bucket có month/label/qty + total_qty + contract ---
	def test_consumption_shape(self):
		res = contract.contract_consumption_by_month(self.ct.name)
		self.assertIsInstance(res, dict)
		self.assertEqual(set(res.keys()), {"data", "total_qty", "contract"})
		self.assertIsInstance(res["data"], list)
		self.assertEqual(len(res["data"]), 12)
		for b in res["data"]:
			self.assertEqual(set(b.keys()), CONSUMPTION_BUCKET_KEYS)
			self.assertRegex(b["month"], r"^\d{4}-\d{2}$")
			self.assertRegex(b["label"], r"^T\d{1,2}$")
			self.assertIsInstance(b["qty"], float)
		self.assertIsInstance(res["total_qty"], float)
		self.assertEqual(res["contract"], self.ct.name)
		# data sort TĂNG dần theo tháng (deterministic cho FE bar chart trục X).
		months = [b["month"] for b in res["data"]]
		self.assertEqual(months, sorted(months))

	# --- 12 bucket zero-fill: 3 tháng có log → 9 tháng còn lại qty=0.0 (KHÔNG bỏ cột) -----
	def test_consumption_12_buckets_zero_fill(self):
		res = contract.contract_consumption_by_month(self.ct.name)
		self.assertEqual(len(res["data"]), 12)
		by = self._by_month(res["data"])
		# 3 tháng có log phải nằm trong cửa sổ 12 tháng.
		for m in (self.m0, self.m1, self.m2):
			self.assertIn(m, by, msg=f"tháng {m} phải có trong cửa sổ 12 tháng")
		# Đếm số bucket qty==0.0 = 12 - 3 = 9.
		zero_buckets = [b for b in res["data"] if b["qty"] == 0.0]
		self.assertEqual(len(zero_buckets), 9, msg="9 tháng trống phải qty=0.0 (KHÔNG bỏ cột)")

	# --- SUM(qty) cùng tháng cùng HĐ + total_qty toàn cửa sổ ----------------------------
	def test_consumption_sum_qty(self):
		res = contract.contract_consumption_by_month(self.ct.name)
		by = self._by_month(res["data"])
		# M0: 4+6 = 10.0 (gộp 2 log cùng tháng cùng HĐ).
		self.assertEqual(by[self.m0]["qty"], 10.0)
		self.assertEqual(by[self.m1]["qty"], 5.0)
		self.assertEqual(by[self.m2]["qty"], 3.0)
		# total_qty = tổng toàn cửa sổ = 10+5+3 = 18.0 (KHÔNG gồm HĐ khác).
		self.assertEqual(res["total_qty"], 18.0)

	# --- fail-closed BR-13: user KHÔNG read-perm HĐ → rỗng, KHÔNG raise leak ------------
	def test_consumption_fail_closed_no_perm(self):
		email = "_t_cons_noperm@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": "NoPermCons", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.set_user(email)
		try:
			res = contract.contract_consumption_by_month(self.ct.name)
			self.assertEqual(
				res,
				{"data": [], "total_qty": 0, "contract": self.ct.name},
				msg=f"LEAK/không fail-closed: {res}",
			)
		finally:
			frappe.set_user("Administrator")

	# --- log của HĐ khác KHÔNG lọt vào kết quả (filter contract đúng) -------------------
	def test_consumption_other_contract_excluded(self):
		res = contract.contract_consumption_by_month(self.ct.name)
		by = self._by_month(res["data"])
		# M0 của cls.ct = 10.0 (KHÔNG cộng 99 của HĐ khác).
		self.assertEqual(by[self.m0]["qty"], 10.0)
		self.assertEqual(res["total_qty"], 18.0)
		# Ngược lại: query HĐ khác trả đúng 99 ở M0 (chứng minh filter tách bạch 2 chiều).
		res_other = contract.contract_consumption_by_month(self.ct_other.name)
		by_other = self._by_month(res_other["data"])
		self.assertEqual(by_other[self.m0]["qty"], 99.0)
		self.assertEqual(res_other["total_qty"], 99.0)

	# --- KHÔNG raw SQL (tôn trọng BR-13 permission) ------------------------------------
	def test_consumption_no_raw_sql(self):
		import inspect

		src = inspect.getsource(contract.contract_consumption_by_month)
		self.assertNotIn(
			"frappe.db.sql", src, msg="contract_consumption_by_month KHÔNG được dùng raw SQL (bỏ qua BR-13)"
		)
		self.assertIn("get_all", src, msg="endpoint phải dùng frappe.get_all (tôn trọng permission)")
		# Endpoint resolve đúng path FE gọi.
		fn = frappe.get_attr("antmed_crm.api.antmed.contract.contract_consumption_by_month")
		self.assertTrue(callable(fn))

	# --- fail-closed dùng has_permission (BR-13) ----------------------------------------
	def test_consumption_uses_has_permission(self):
		import inspect

		src = inspect.getsource(contract.contract_consumption_by_month)
		self.assertIn(
			"has_permission", src, msg="endpoint phải dùng frappe.has_permission (fail-closed BR-13)"
		)


# Shape mỗi dòng cơ cấu doanh thu (Hyrum — 4 key, FROZEN §1sext.shape; đổi = breaking FE bind card).
REVENUE_MIX_ROW_KEYS = {"classification", "label", "revenue", "pct"}
# Thứ tự cố định A→B→C→D (load-bearing — FE bind theo index, mockup A2). KHÔNG đổi/đảo.
REVENUE_MIX_ORDER = ["Loại A", "Loại B", "Loại C", "Loại D"]
ITEM_DOCTYPE = "AntMed Item"


def _mk_item(item_code, classification=None):
	"""Seed 1 AntMed Item (autoname=field:item_code ⇒ name == item_code) với classification tuỳ chọn.

	Quota item.item (Data, = SKU) trỏ tới name AntMed Item ⇒ revenue_mix batch-tra classification.
	classification=None → item KHÔNG thuộc 4 lớp chuẩn (nhóm 'Khác', loại khỏi 4 dòng + total).
	`classification` là Select chỉ nhận "", Loại A/B/C/D ⇒ KHÔNG seed được giá trị ngoài options;
	case "ngoài A–D" hiện thực bằng SKU KHÔNG có AntMed Item (resolve None → 'Khác').
	"""
	if frappe.db.exists(ITEM_DOCTYPE, item_code):
		return frappe.get_doc(ITEM_DOCTYPE, item_code)
	payload = {
		"doctype": ITEM_DOCTYPE,
		"item_code": item_code,
		"item_name": f"VT {item_code}",
	}
	if classification:
		payload["classification"] = classification
	doc = frappe.get_doc(payload)
	doc.insert(ignore_permissions=True)
	return doc


def _rev_row(item, used_qty, unit_price):
	"""1 dòng quota để verify revenue = used_qty × unit_price (quota_qty KHÔNG ảnh hưởng revenue_mix)."""
	return {
		"item": item,
		"item_name": f"VT {item}",
		"uom": "Cái",
		"unit_price": unit_price,
		"quota_qty": max(used_qty, 1),
		"used_qty": used_qty,
		"remaining_pct": 0.0,
		"lock_at_100": 0,
	}


class TestAntMedRevenueMix(FrappeTestCase):
	"""M02 Slice M02-7 — endpoint MỚI revenue_mix (widget "Cơ cấu doanh thu" — Dashboard CEO, mockup A2).

	revenue (mỗi lớp) = SUM(used_qty × unit_price) cross-contract gộp theo classification của AntMed
	Item. data ĐÚNG 4 phần tử CỐ ĐỊNH thứ tự Loại A→B→C→D (kể cả lớp revenue=0 vẫn render).
	item thiếu classification / SKU không có AntMed Item → nhóm 'Khác' (KHÔNG render & KHÔNG cộng
	total). total_revenue = SUM 4 lớp A–D; pct = round(100*rev/total, 1) (total==0 ⇒ pct=0.0, KHÔNG
	ZeroDivisionError). BR-13 fail-closed: user KHÔNG read-perm AntMed Contract → {data 4 dòng 0,
	total_revenue 0} (KHÔNG raise, KHÔNG leak). data-scope: revenue HĐ ngoài scope NV KHÔNG cộng vào.

	Lệnh chạy:
	  bench --site miyano run-tests --module antmed_crm.tests.test_antmed_contract
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hosp = _mk_hospital("_T-RM-HOSP", "BV Revenue Mix")
		_mk_item("RM-A1", "Loại A")
		_mk_item("RM-A2", "Loại A")
		_mk_item("RM-B1", "Loại B")
		_mk_item("RM-C1", "Loại C")
		_mk_item("RM-NOCLS", None)  # item KHÔNG phân loại → 'Khác'
		# SKU 'RM-GHOST' KHÔNG tạo AntMed Item → resolve None → 'Khác' (data bẩn / SKU ngoài danh mục).
		# HĐ1: Loại A (RM-A1 10×2tr=20tr) + Loại B (RM-B1 5×4tr=20tr).
		_mk_contract(
			"_T-RM-CT1",
			cls.hosp.name,
			items=[_rev_row("RM-A1", 10, 2_000_000), _rev_row("RM-B1", 5, 4_000_000)],
			status="Hiệu lực",
			valid_to="2027-12-31",
			total_value=10,
		)
		# HĐ2: Loại A (RM-A2 4×5tr=20tr → A gộp cross-HĐ = 40tr) + Loại C (RM-C1 1×30tr=30tr).
		_mk_contract(
			"_T-RM-CT2",
			cls.hosp.name,
			items=[_rev_row("RM-A2", 4, 5_000_000), _rev_row("RM-C1", 1, 30_000_000)],
			status="Hiệu lực",
			valid_to="2027-12-31",
			total_value=10,
		)
		# Kỳ vọng 4 lớp: A=40tr, B=20tr, C=30tr, D=0 → total=90tr.
		cls.exp_a, cls.exp_b, cls.exp_c, cls.exp_d = 40_000_000.0, 20_000_000.0, 30_000_000.0, 0.0
		cls.exp_total = 90_000_000.0

	def _by_cls(self, data):
		return {r["classification"]: r for r in data}

	# (a) data luôn ĐÚNG 4 phần tử thứ tự Loại A→B→C→D + label==classification + 4 key ---------
	def test_revenue_mix_shape_4_rows_fixed_order(self):
		res = contract.revenue_mix()
		self.assertIsInstance(res, dict)
		self.assertEqual(set(res.keys()), {"data", "total_revenue"})
		self.assertIsInstance(res["data"], list)
		self.assertEqual(len(res["data"]), 4, msg=f"phải ĐÚNG 4 dòng A–D: {res['data']}")
		self.assertEqual([r["classification"] for r in res["data"]], REVENUE_MIX_ORDER)
		self.assertIsInstance(res["total_revenue"], (int, float))
		for row in res["data"]:
			self.assertEqual(set(row.keys()), REVENUE_MIX_ROW_KEYS)
			self.assertEqual(row["label"], row["classification"])
			self.assertIsInstance(row["revenue"], (int, float))
			self.assertIsInstance(row["pct"], (int, float))

	def test_revenue_mix_empty_helper_4_rows(self):
		"""Fail-closed shape: 4 dòng rev=0/pct=0, total_revenue=0 (DB-rỗng / noperm path)."""
		res = contract._empty_revenue_mix()
		self.assertEqual([r["classification"] for r in res["data"]], REVENUE_MIX_ORDER)
		self.assertTrue(all(r["revenue"] == 0.0 and r["pct"] == 0.0 for r in res["data"]))
		self.assertEqual(res["total_revenue"], 0)

	# (b) revenue = SUM(used_qty*unit_price) đúng cho 1 lớp nhiều dòng/nhiều HĐ ---------------
	def test_revenue_mix_aggregate_cross_contract(self):
		by = self._by_cls(contract.revenue_mix()["data"])
		self.assertEqual(by["Loại A"]["revenue"], self.exp_a)  # 20tr + 20tr (2 HĐ) = 40tr
		self.assertEqual(by["Loại B"]["revenue"], self.exp_b)
		self.assertEqual(by["Loại C"]["revenue"], self.exp_c)

	# (c) item thuộc Loại B → cộng đúng lớp B, KHÔNG lọt lớp khác; lớp 0 vẫn render ----------
	def test_revenue_mix_band_isolation_and_zero_row(self):
		by = self._by_cls(contract.revenue_mix()["data"])
		self.assertEqual(by["Loại B"]["revenue"], 20_000_000.0)
		# Loại D không item nào → revenue 0 nhưng VẪN render dòng (4 dòng cố định).
		self.assertIn("Loại D", by)
		self.assertEqual(by["Loại D"]["revenue"], self.exp_d)
		self.assertEqual(by["Loại D"]["pct"], 0.0)

	# (d) item classification None / SKU không tồn tại → 'Khác' KHÔNG vào 4 dòng & total --------
	def test_revenue_mix_unclassified_to_other(self):
		base = contract.revenue_mix()
		base_total = base["total_revenue"]
		base_a = self._by_cls(base["data"])["Loại A"]["revenue"]
		# Thêm HĐ: item KHÔNG phân loại (RM-NOCLS) + SKU không có AntMed Item (RM-GHOST).
		_mk_contract(
			"_T-RM-CT-OTHER",
			self.hosp.name,
			items=[_rev_row("RM-NOCLS", 100, 9_000_000), _rev_row("RM-GHOST", 50, 7_000_000)],
			status="Hiệu lực",
			valid_to="2027-12-31",
			total_value=10,
		)
		after = contract.revenue_mix()
		self.assertEqual(after["total_revenue"], base_total)  # 'Khác' KHÔNG cộng total
		self.assertEqual(self._by_cls(after["data"])["Loại A"]["revenue"], base_a)  # lớp A không đổi
		self.assertEqual(len(after["data"]), 4)  # KHÔNG mọc dòng 'Khác'
		self.assertEqual([r["classification"] for r in after["data"]], REVENUE_MIX_ORDER)
		self.assertNotIn("Khác", self._by_cls(after["data"]))

	# (e) total_revenue==0 ⇒ mọi pct=0.0 (no ZeroDivision) — scope NV rỗng -------------------
	def test_revenue_mix_total_zero_safe(self):
		role = "NV kinh doanh"
		email = "_t_rm_emptyscope@example.com"
		empty_hosp = _mk_hospital("_T-RM-EMPTY", "BV Rỗng Revenue")
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": "EmptyScopeRM",
					"send_welcome_email": 0,
					"roles": [{"role": role}],
				}
			).insert(ignore_permissions=True)
		else:
			u = frappe.get_doc("User", email)
			if role not in [r.role for r in u.roles]:
				u.add_roles(role)
		if not frappe.db.exists(
			"User Permission", {"user": email, "allow": "AntMed Hospital", "for_value": empty_hosp.name}
		):
			frappe.get_doc(
				{
					"doctype": "User Permission",
					"user": email,
					"allow": "AntMed Hospital",
					"for_value": empty_hosp.name,
				}
			).insert(ignore_permissions=True)
		frappe.set_user(email)
		try:
			res = contract.revenue_mix()
			self.assertEqual(len(res["data"]), 4)
			self.assertEqual([r["classification"] for r in res["data"]], REVENUE_MIX_ORDER)
			self.assertEqual(res["total_revenue"], 0.0)
			for row in res["data"]:
				self.assertEqual(row["revenue"], 0.0)
				self.assertEqual(row["pct"], 0.0)  # KHÔNG ZeroDivisionError
		finally:
			frappe.set_user("Administrator")
			frappe.db.delete(
				"User Permission",
				{"user": email, "allow": "AntMed Hospital", "for_value": empty_hosp.name},
			)

	# (f) pct = round(100*rev/total,1) & SUM(pct 4 lớp) ~ 100 khi total>0 -------------------
	def test_revenue_mix_pct_formula_sum_about_100(self):
		res = contract.revenue_mix()
		self.assertEqual(res["total_revenue"], self.exp_total)
		by = self._by_cls(res["data"])
		for c, rev in (
			("Loại A", self.exp_a),
			("Loại B", self.exp_b),
			("Loại C", self.exp_c),
			("Loại D", self.exp_d),
		):
			self.assertEqual(by[c]["pct"], round(100 * rev / self.exp_total, 1))
		# A=44.4 · B=22.2 · C=33.3 · D=0.0 → Σ ≈ 100 (±làm tròn).
		self.assertEqual(by["Loại A"]["pct"], 44.4)
		self.assertEqual(by["Loại C"]["pct"], 33.3)
		self.assertAlmostEqual(sum(r["pct"] for r in res["data"]), 100.0, delta=0.5)

	# (g) fail-closed BR-13: user KHÔNG read-perm Contract → 4 dòng 0, KHÔNG raise -----------
	def test_revenue_mix_fail_closed(self):
		email = "_t_rm_noperm@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": "NoPermRM", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		self.assertGreater(contract.revenue_mix()["total_revenue"], 0)  # admin sanity
		frappe.set_user(email)
		try:
			try:
				res = contract.revenue_mix()
			except frappe.PermissionError:
				return  # an toàn: chặn ngay get_list — không rò
			self.assertEqual(len(res["data"]), 4, msg=f"fail-closed phải GIỮ 4 dòng: {res}")
			self.assertEqual([r["classification"] for r in res["data"]], REVENUE_MIX_ORDER)
			self.assertTrue(
				all(r["revenue"] == 0.0 and r["pct"] == 0.0 for r in res["data"]),
				msg=f"LEAK revenue: {res}",
			)
			self.assertEqual(res["total_revenue"], 0, msg=f"LEAK total: {res}")
		finally:
			frappe.set_user("Administrator")

	# data-scope BR-13: revenue từ HĐ ngoài scope NV KHÔNG cộng vào ---------------------------
	def test_revenue_mix_respects_data_scope(self):
		role = "NV kinh doanh"
		email = "_t_rm_scoped@example.com"
		scoped_hosp = _mk_hospital("_T-RM-SCOPED", "BV Scoped RM")
		_mk_item("RM-SCOPED-A", "Loại A")
		_mk_contract(
			"_T-RM-CT-SCOPED",
			scoped_hosp.name,
			items=[_rev_row("RM-SCOPED-A", 2, 1_000_000)],  # Loại A = 2tr
			status="Hiệu lực",
			valid_to="2027-12-31",
			total_value=10,
		)
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": "ScopedRM",
					"send_welcome_email": 0,
					"roles": [{"role": role}],
				}
			).insert(ignore_permissions=True)
		else:
			u = frappe.get_doc("User", email)
			if role not in [r.role for r in u.roles]:
				u.add_roles(role)
		if not frappe.db.exists(
			"User Permission", {"user": email, "allow": "AntMed Hospital", "for_value": scoped_hosp.name}
		):
			frappe.get_doc(
				{
					"doctype": "User Permission",
					"user": email,
					"allow": "AntMed Hospital",
					"for_value": scoped_hosp.name,
				}
			).insert(ignore_permissions=True)
		frappe.set_user(email)
		try:
			res = contract.revenue_mix()
			by = self._by_cls(res["data"])
			# Chỉ thấy HĐ BV scoped: Loại A = 2tr, các lớp khác = 0, total = 2tr.
			self.assertEqual(by["Loại A"]["revenue"], 2_000_000.0)
			self.assertEqual(by["Loại B"]["revenue"], 0.0)
			self.assertEqual(by["Loại C"]["revenue"], 0.0)
			self.assertEqual(by["Loại D"]["revenue"], 0.0)
			self.assertEqual(res["total_revenue"], 2_000_000.0)
		finally:
			frappe.set_user("Administrator")
			frappe.db.delete(
				"User Permission",
				{"user": email, "allow": "AntMed Hospital", "for_value": scoped_hosp.name},
			)

	# (h) no_raw_sql (grep frappe.db.sql vắng trong revenue_mix) -----------------------------
	def test_revenue_mix_no_raw_sql(self):
		import inspect

		src = inspect.getsource(contract.revenue_mix)
		self.assertNotIn("frappe.db.sql", src, msg="revenue_mix KHÔNG được dùng raw SQL (bỏ qua BR-13)")
		self.assertIn("get_list", src, msg="revenue_mix phải dùng frappe.get_list (tôn trọng perm)")
		fn = frappe.get_attr("antmed_crm.api.antmed.contract.revenue_mix")
		self.assertTrue(callable(fn))

	# (i) no_n+1 (mock get_all đếm ≤2 lần: quota lines + item classifications) ----------------
	def test_revenue_mix_no_n_plus_1(self):
		import unittest.mock as mock

		real_get_all = frappe.get_all
		calls = {"n": 0}

		def counting_get_all(*args, **kwargs):
			calls["n"] += 1
			return real_get_all(*args, **kwargs)

		with mock.patch.object(frappe, "get_all", side_effect=counting_get_all):
			contract.revenue_mix()
		self.assertLessEqual(
			calls["n"], 2, msg=f"N+1: get_all gọi {calls['n']} lần (phải ≤2: quota lines + item class)"
		)

	# hằng REVENUE_MIX_CLASSES export ổn định (FE bind shape) --------------------------------
	def test_revenue_mix_classes_constant(self):
		self.assertEqual(list(contract.REVENUE_MIX_CLASSES), REVENUE_MIX_ORDER)


# ── M02 Slice M02-8 — endpoint MỚI monthly_revenue (KPI "Doanh thu tháng" CEO, mockup A1 hàng 1) ──
# Shape RAW dict (Hyrum — 5 key FROZEN; đổi = breaking FE bind thẻ KPI + dòng phụ MoM).
MONTHLY_REVENUE_KEYS = {"current", "previous", "delta_pct", "month_label", "currency"}
MONTH_LABEL_RE = re.compile(r"^T\d{1,2}/\d{4}$")
CONTRACT_DOCTYPE = "AntMed Contract"


def _mk_rev_log(contract_name, item, qty, ts):
	"""Seed 1 AntMed Quota Usage Log với (contract, item, qty, ts) cụ thể cho monthly_revenue.

	`ts` ép qua frappe.db.set_value SAU insert (xếp đúng bucket THÁNG-HIỆN-TẠI / THÁNG-TRƯỚC).
	Khác _mk_usage_log (hardcode item='VTYT-CONS'): cần control item để map (contract,item)→unit_price.
	"""
	doc = frappe.get_doc(
		{"doctype": QUOTA_USAGE_DOCTYPE, "contract": contract_name, "item": item, "qty": qty}
	)
	doc.insert(ignore_permissions=True)
	frappe.db.set_value(QUOTA_USAGE_DOCTYPE, doc.name, "ts", ts, update_modified=False)
	return doc


class TestAntMedMonthlyRevenue(FrappeTestCase):
	"""M02 Slice M02-8 — endpoint MỚI monthly_revenue (KPI "Doanh thu tháng" Dashboard CEO).

	RAW dict { current, previous, delta_pct, month_label:'T<m>/<yyyy>', currency:'VND' }.
	current  = SUM(qty × unit_price) MỌI log AntMed Quota Usage Log ts trong THÁNG HIỆN TẠI
	           (month-to-date theo nowdate()); unit_price tra (contract,item) từ AntMed Quota Item.
	previous = cùng công thức cho cả THÁNG LIỀN TRƯỚC.
	delta_pct = round(100*(current-previous)/previous, 1) khi previous>0; None khi previous==0.
	BR-13 fail-closed: noperm AntMed Contract → frappe.get_list raise PermissionError →
	  _empty_monthly_revenue (zero, KHÔNG raise, KHÔNG leak). scope rỗng → current=previous=0.
	BATCH KHÔNG N+1: 1 get_all log + 1 get_all quota item. log (contract,item) không khớp dòng
	  quota nào → unit_price=0 (bỏ qua doanh thu, KHÔNG vỡ). KHÔNG raw SQL. GET-only.

	Lệnh chạy:
	  bench --site miyano run-tests --module antmed_crm.tests.test_antmed_contract
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# DEDUP cross-run: FrappeTestCase commit ở setUpClass ⇒ log seed của lần chạy TRƯỚC còn lại
		# (tích luỹ → current/previous sai). Xoá MỌI usage log của HĐ test MR trước khi re-seed.
		for ct_name in (
			"_T-MR-CT",
			"_T-MR-CT-NOPREV",
			"_T-MR-CT-SCOPED",
		):
			frappe.db.delete(QUOTA_USAGE_DOCTYPE, {"contract": ct_name})
		cls.hosp = _mk_hospital("_T-MR-HOSP", "BV Monthly Revenue")
		# HĐ chính: 2 item có unit_price khác nhau để verify SUM(qty × unit_price).
		#   MR-IT-A đơn giá 2.000.000 ; MR-IT-B đơn giá 5.000.000.
		cls.ct = _mk_contract(
			"_T-MR-CT",
			cls.hosp.name,
			items=[
				_quota_row("MR-IT-A", 1000, 0),
				_quota_row("MR-IT-B", 1000, 0),
			],
			status="Hiệu lực",
			valid_from="2025-01-01",
			valid_to="2027-12-31",
			total_value=10,
		)
		# Ép unit_price chuẩn (helper _quota_row mặc định 1.000.000) qua child row.
		ct = frappe.get_doc(contract.CONTRACT_DOCTYPE, cls.ct.name)
		for row in ct.items:
			row.unit_price = 2_000_000 if row.item == "MR-IT-A" else 5_000_000
		ct.save(ignore_permissions=True)

		from frappe.utils import add_months, getdate, nowdate

		today = getdate(nowdate())
		prev = add_months(today, -1)
		cls.cur_label = f"T{today.month}/{today.year}"
		# Datetime đầu mỗi tháng (an toàn trong bucket — KHÔNG dùng 28..31, tránh lệch khi nowdate cuối tháng).
		cls.ts_cur = f"{today.year:04d}-{today.month:02d}-05 10:00:00"
		cls.ts_prev = f"{prev.year:04d}-{prev.month:02d}-05 10:00:00"

		# THÁNG HIỆN TẠI: A 10×2tr=20tr + B 20×5tr=100tr → current = 120tr.
		_mk_rev_log(cls.ct.name, "MR-IT-A", 10, cls.ts_cur)
		_mk_rev_log(cls.ct.name, "MR-IT-B", 20, cls.ts_cur)
		# THÁNG TRƯỚC: A 50×2tr=100tr (2 log 30+20) → previous = 100tr (cả tháng).
		_mk_rev_log(cls.ct.name, "MR-IT-A", 30, cls.ts_prev)
		_mk_rev_log(cls.ct.name, "MR-IT-A", 20, cls.ts_prev)
		# Log có item KHÔNG nằm trong Quota Item của HĐ → unit_price=0 → KHÔNG cộng doanh thu.
		_mk_rev_log(cls.ct.name, "MR-IT-GHOST", 999, cls.ts_cur)

		cls.exp_current = 120_000_000.0  # 20tr + 100tr (ghost bỏ qua)
		cls.exp_previous = 100_000_000.0

		# NV scoped CHỈ thấy _T-MR-HOSP → monthly_revenue() chỉ gộp cls.ct (cô lập assertion giá trị
		# khỏi HĐ test khác / lần chạy trước mà Administrator thấy hết). Test giá trị set_user(NV) này.
		cls.scoped_email = "_t_mr_isolated@example.com"
		_ensure_scoped_user(cls.scoped_email, "NV kinh doanh", "AntMed Hospital", cls.hosp.name)

	# (1) shape — dict đúng keys + currency=='VND' + month_label khớp regex ---------------------
	def test_monthly_revenue_shape(self):
		res = contract.monthly_revenue()
		self.assertIsInstance(res, dict)
		self.assertEqual(set(res.keys()), MONTHLY_REVENUE_KEYS)
		self.assertEqual(set(res.keys()), set(contract.MONTHLY_REVENUE_KEYS))
		self.assertEqual(res["currency"], "VND")
		self.assertRegex(res["month_label"], MONTH_LABEL_RE)
		self.assertEqual(res["month_label"], self.cur_label)
		self.assertIsInstance(res["current"], (int, float))
		self.assertIsInstance(res["previous"], (int, float))

	def _scoped(self):
		"""monthly_revenue() dưới NV scoped (chỉ thấy _T-MR-HOSP) → cô lập gộp về cls.ct."""
		frappe.set_user(self.scoped_email)
		try:
			return contract.monthly_revenue()
		finally:
			frappe.set_user("Administrator")

	# (2) current = SUM(qty×unit_price) chỉ log THÁNG HIỆN TẠI -----------------------------------
	def test_monthly_revenue_current_this_month_only(self):
		res = self._scoped()
		self.assertEqual(res["current"], self.exp_current)
		# current KHÔNG gồm doanh thu tháng trước (100tr).
		self.assertNotEqual(res["current"], self.exp_current + self.exp_previous)

	# (3) previous = cả tháng trước (gộp 2 log) ------------------------------------------------
	def test_monthly_revenue_previous_full_prev_month(self):
		res = self._scoped()
		self.assertEqual(res["previous"], self.exp_previous)  # 30+20 = 50 × 2tr = 100tr

	# (4) delta_pct = round(100*(cur-prev)/prev,1) khi prev>0 (cur=120,prev=100 → 20.0) --------
	def test_monthly_revenue_delta_pct_formula(self):
		res = self._scoped()
		self.assertEqual(res["delta_pct"], 20.0)
		self.assertEqual(
			res["delta_pct"],
			round(100 * (res["current"] - res["previous"]) / res["previous"], 1),
		)

	# (5) delta_pct == None khi previous == 0 (chỉ seed log tháng này) -------------------------
	def test_monthly_revenue_delta_none_when_prev_zero(self):
		hosp = _mk_hospital("_T-MR-HOSP-NOPREV", "BV MR NoPrev")
		ct = _mk_contract(
			"_T-MR-CT-NOPREV",
			hosp.name,
			items=[_quota_row("MR-NP-A", 1000, 0)],
			status="Hiệu lực",
			valid_to="2027-12-31",
			total_value=10,
		)
		frappe.db.delete(QUOTA_USAGE_DOCTYPE, {"contract": ct.name})  # dedup cross-run
		_mk_rev_log(ct.name, "MR-NP-A", 5, self.ts_cur)  # chỉ tháng này
		role = "NV kinh doanh"
		email = "_t_mr_noprev@example.com"
		_ensure_scoped_user(email, role, "AntMed Hospital", hosp.name)
		frappe.set_user(email)
		try:
			res = contract.monthly_revenue()
			self.assertGreater(res["current"], 0)
			self.assertEqual(res["previous"], 0)
			self.assertIsNone(res["delta_pct"])
		finally:
			frappe.set_user("Administrator")
			frappe.db.delete(
				"User Permission",
				{"user": email, "allow": "AntMed Hospital", "for_value": hosp.name},
			)

	# (6) scope rỗng (0 contract / 0 log) → current=previous=0, delta_pct=None -----------------
	def test_monthly_revenue_empty_scope(self):
		hosp = _mk_hospital("_T-MR-HOSP-EMPTY", "BV MR Empty")
		role = "NV kinh doanh"
		email = "_t_mr_empty@example.com"
		_ensure_scoped_user(email, role, "AntMed Hospital", hosp.name)
		frappe.set_user(email)
		try:
			res = contract.monthly_revenue()
			self.assertEqual(res["current"], 0)
			self.assertEqual(res["previous"], 0)
			self.assertIsNone(res["delta_pct"])
			self.assertRegex(res["month_label"], MONTH_LABEL_RE)
			self.assertEqual(res["currency"], "VND")
		finally:
			frappe.set_user("Administrator")
			frappe.db.delete(
				"User Permission",
				{"user": email, "allow": "AntMed Hospital", "for_value": hosp.name},
			)

	# (7) BR-13 fail-closed — frappe.get_list raise PermissionError → _empty (zero, KHÔNG raise) -
	def test_monthly_revenue_fail_closed(self):
		import unittest.mock as mock

		def raise_perm(*args, **kwargs):
			raise frappe.PermissionError("no read AntMed Contract")

		with mock.patch.object(frappe, "get_list", side_effect=raise_perm):
			res = contract.monthly_revenue()
		self.assertEqual(res["current"], 0)
		self.assertEqual(res["previous"], 0)
		self.assertIsNone(res["delta_pct"])
		self.assertRegex(res["month_label"], MONTH_LABEL_RE)
		self.assertEqual(res["currency"], "VND")
		# Khớp helper fail-closed dùng chung (shape ổn định; month_label sinh từ nowdate).
		self.assertEqual(res, contract._empty_monthly_revenue())

	# (8) unit_price KHÔNG khớp (item ngoài Quota Item của HĐ) → KHÔNG cộng doanh thu ----------
	def test_monthly_revenue_unmatched_item_ignored(self):
		# setUpClass đã seed MR-IT-GHOST 999 qty tháng này; nếu cộng nhầm current sẽ ≠ 120tr.
		# Dưới NV scoped (chỉ thấy _T-MR-HOSP) → cô lập về cls.ct (GHOST không khớp quota → 0).
		res = self._scoped()
		self.assertEqual(res["current"], self.exp_current, msg="log item ngoài quota KHÔNG được cộng")
		# Sanity: 999 × bất kỳ unit_price quota nào (2tr/5tr) đều ≫ chênh lệch → khác hẳn nếu vỡ.
		self.assertNotEqual(res["current"], self.exp_current + 999 * 2_000_000)

	# (9) GET-only — @frappe.whitelist(methods=['GET']) (POST → 403) ---------------------------
	def test_monthly_revenue_get_only(self):
		fn = frappe.get_attr("antmed_crm.api.antmed.contract.monthly_revenue")
		self.assertTrue(callable(fn))
		# frappe lưu allowed HTTP methods ở dict module-level (KHÔNG attr trên fn).
		allowed = frappe.allowed_http_methods_for_whitelisted_func.get(fn)
		self.assertIsNotNone(allowed, msg="monthly_revenue phải @frappe.whitelist(methods=[...])")
		self.assertIn("GET", allowed)
		self.assertNotIn("POST", allowed)
		# Source-level guard: decorator phải nêu rõ methods=["GET"].
		import inspect

		src = inspect.getsource(contract.monthly_revenue)
		self.assertIn('methods=["GET"]', src)

	# (10) KHÔNG raw SQL + BATCH (≤2 get_all: log + quota item) -------------------------------
	def test_monthly_revenue_no_raw_sql_and_batch(self):
		import inspect
		import unittest.mock as mock

		src = inspect.getsource(contract.monthly_revenue)
		self.assertNotIn("frappe.db.sql", src, msg="monthly_revenue KHÔNG được dùng raw SQL (bỏ qua BR-13)")
		self.assertIn("get_list", src, msg="phải dùng frappe.get_list (fail-closed + scope BR-13)")

		real_get_all = frappe.get_all
		calls = {"n": 0}

		def counting(*args, **kwargs):
			calls["n"] += 1
			return real_get_all(*args, **kwargs)

		with mock.patch.object(frappe, "get_all", side_effect=counting):
			contract.monthly_revenue()
		self.assertLessEqual(
			calls["n"], 2, msg=f"N+1: get_all gọi {calls['n']} lần (phải ≤2: log + quota item)"
		)

	# (11) data-scope BR-13: doanh thu HĐ ngoài scope NV KHÔNG cộng vào ------------------------
	def test_monthly_revenue_respects_data_scope(self):
		# NV chỉ thấy BV scoped riêng → chỉ doanh thu HĐ của BV đó (KHÔNG cộng cls.ct của _T-MR-HOSP).
		hosp = _mk_hospital("_T-MR-HOSP-SCOPED", "BV MR Scoped")
		ct = _mk_contract(
			"_T-MR-CT-SCOPED",
			hosp.name,
			items=[_quota_row("MR-SC-A", 1000, 0)],
			status="Hiệu lực",
			valid_to="2027-12-31",
			total_value=10,
		)
		c = frappe.get_doc(contract.CONTRACT_DOCTYPE, ct.name)
		c.items[0].unit_price = 1_000_000
		c.save(ignore_permissions=True)
		frappe.db.delete(QUOTA_USAGE_DOCTYPE, {"contract": ct.name})  # dedup cross-run
		_mk_rev_log(ct.name, "MR-SC-A", 7, self.ts_cur)  # 7 × 1tr = 7tr tháng này
		role = "NV kinh doanh"
		email = "_t_mr_scoped@example.com"
		_ensure_scoped_user(email, role, "AntMed Hospital", hosp.name)
		frappe.set_user(email)
		try:
			res = contract.monthly_revenue()
			# Chỉ thấy HĐ BV scoped: current = 7tr (KHÔNG gồm 120tr của _T-MR-HOSP ngoài scope).
			self.assertEqual(res["current"], 7_000_000.0)
			self.assertEqual(res["previous"], 0)
			self.assertIsNone(res["delta_pct"])
		finally:
			frappe.set_user("Administrator")
			frappe.db.delete(
				"User Permission",
				{"user": email, "allow": "AntMed Hospital", "for_value": hosp.name},
			)


def _ensure_scoped_user(email, role, allow, for_value):
	"""Tạo/đảm bảo User có role + User Permission giới hạn 1 giá trị (data-scope BR-13 test helper)."""
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@")[0],
				"send_welcome_email": 0,
				"roles": [{"role": role}],
			}
		).insert(ignore_permissions=True)
	else:
		u = frappe.get_doc("User", email)
		if role not in [r.role for r in u.roles]:
			u.add_roles(role)
	if not frappe.db.exists("User Permission", {"user": email, "allow": allow, "for_value": for_value}):
		frappe.get_doc(
			{"doctype": "User Permission", "user": email, "allow": allow, "for_value": for_value}
		).insert(ignore_permissions=True)


# ── M02 Slice M02-9 — endpoint MỚI revenue_by_group (widget "Doanh thu theo Nhóm vật tư" CEO) ──
# Shape RAW dict ổn định (Hyrum — 4 key FROZEN; đổi = breaking FE bind stacked-bar 12 tháng × 5 nhóm).
REVENUE_BY_GROUP_KEYS = {"months", "groups", "grand_total", "currency"}
GROUP_ROW_KEYS = {"classification", "label", "monthly", "total"}
# Thứ tự cố định A→B→C→D→Khác (load-bearing — FE bind theo index; 5 dòng LUÔN render kể cả 0).
REVENUE_BY_GROUP_ORDER = ["Loại A", "Loại B", "Loại C", "Loại D", "Khác"]
# Trục X = nhãn tháng ngắn 'T<m>' (BE quyết định format — mirror contract_consumption_by_month).
MONTH_SHORT_RE = re.compile(r"^T\d{1,2}$")


class TestAntMedRevenueByGroup(FrappeTestCase):
	"""M02 Slice M02-9 — endpoint MỚI revenue_by_group (widget "Doanh thu theo Nhóm vật tư" CEO, mockup A3).

	Stacked-bar 12 tháng trượt × 4 nhóm phân loại VTYT (Loại A/B/C/D) + nhóm fallback 'Khác'.
	revenue = SUM(qty × unit_price) từ AntMed Quota Usage Log (qty × ts → bucket tháng) JOIN
	AntMed Quota Item (unit_price theo contract×item) gộp theo classification của AntMed Item.

	RAW dict { months:[12 str 'T<m>' thứ tự thời gian tăng], groups:[{classification,label,
	monthly:[12 number],total}], grand_total, currency:'VND' }. groups LUÔN đủ 5 dòng thứ tự cố
	định A→B→C→D→Khác (kể cả revenue=0). item thiếu/ngoài A–D classification → dồn 'Khác'.
	BR-13 fail-closed: noperm AntMed Contract → frappe.get_list raise PermissionError →
	_empty_revenue_by_group (months 12 nhãn, 5 group monthly toàn 0, grand_total 0, KHÔNG raise).
	BATCH KHÔNG N+1: 1 get_list HĐ + 1 get_all log + 1 get_all quota item + 1 get_all item.
	KHÔNG raw SQL. GET-only.

	Lệnh chạy:
	  bench --site miyano run-tests --module antmed_crm.tests.test_antmed_contract
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# DEDUP cross-run: FrappeTestCase commit ở setUpClass ⇒ log seed lần TRƯỚC còn lại (tích luỹ).
		for ct_name in ("_T-RBG-CT", "_T-RBG-CT-SCOPED"):
			frappe.db.delete(QUOTA_USAGE_DOCTYPE, {"contract": ct_name})
		cls.hosp = _mk_hospital("_T-RBG-HOSP", "BV Revenue By Group")
		# Item phân loại: A/B/C + 1 item KHÔNG phân loại (→ 'Khác'). SKU ghost (no AntMed Item) → 'Khác'.
		_mk_item("RBG-A1", "Loại A")
		_mk_item("RBG-B1", "Loại B")
		_mk_item("RBG-C1", "Loại C")
		_mk_item("RBG-NOCLS", None)
		# HĐ chính với 5 dòng quota (đơn giá khác nhau để verify qty × unit_price).
		cls.ct = _mk_contract(
			"_T-RBG-CT",
			cls.hosp.name,
			items=[
				_rev_row("RBG-A1", 0, 2_000_000),
				_rev_row("RBG-B1", 0, 4_000_000),
				_rev_row("RBG-C1", 0, 3_000_000),
				_rev_row("RBG-NOCLS", 0, 1_000_000),
				_rev_row("RBG-GHOST", 0, 5_000_000),
			],
			status="Hiệu lực",
			valid_from="2024-01-01",
			valid_to="2027-12-31",
			total_value=10,
		)

		from frappe.utils import add_months, getdate, nowdate

		today = getdate(nowdate())
		cls.today = today
		cls.cur_label = f"T{today.month}"
		# 3 mốc tháng trong cửa sổ: hiện tại (M0), 1 tháng trước (M1), 5 tháng trước (M5).
		cls.m0 = today
		cls.m1 = add_months(today, -1)
		cls.m5 = add_months(today, -5)
		cls.ts_m0 = f"{cls.m0.year:04d}-{cls.m0.month:02d}-05 10:00:00"
		cls.ts_m1 = f"{cls.m1.year:04d}-{cls.m1.month:02d}-05 10:00:00"
		cls.ts_m5 = f"{cls.m5.year:04d}-{cls.m5.month:02d}-05 10:00:00"
		# Datetime NGOÀI cửa sổ (13 tháng trước) → KHÔNG được cộng vào bất kỳ bucket nào.
		cls.m_out = add_months(today, -13)
		cls.ts_out = f"{cls.m_out.year:04d}-{cls.m_out.month:02d}-05 10:00:00"

		# Seed log:
		#   M0: A 10×2tr=20tr ; B 5×4tr=20tr ; NOCLS 3×1tr=3tr (→ Khác) ; GHOST 2×5tr=10tr (→ Khác)
		#   M1: A 4×2tr=8tr
		#   M5: C 6×3tr=18tr
		#   OUT: A 1000×2tr (ngoài cửa sổ — bỏ qua)
		_mk_rev_log(cls.ct.name, "RBG-A1", 10, cls.ts_m0)
		_mk_rev_log(cls.ct.name, "RBG-B1", 5, cls.ts_m0)
		_mk_rev_log(cls.ct.name, "RBG-NOCLS", 3, cls.ts_m0)
		_mk_rev_log(cls.ct.name, "RBG-GHOST", 2, cls.ts_m0)
		_mk_rev_log(cls.ct.name, "RBG-A1", 4, cls.ts_m1)
		_mk_rev_log(cls.ct.name, "RBG-C1", 6, cls.ts_m5)
		_mk_rev_log(cls.ct.name, "RBG-A1", 1000, cls.ts_out)

		# NV scoped chỉ thấy _T-RBG-HOSP → cô lập assertion giá trị khỏi HĐ test khác Admin thấy hết.
		cls.scoped_email = "_t_rbg_isolated@example.com"
		_ensure_scoped_user(cls.scoped_email, "NV kinh doanh", "AntMed Hospital", cls.hosp.name)

	def _scoped(self):
		"""revenue_by_group() dưới NV scoped (chỉ thấy _T-RBG-HOSP) → cô lập gộp về cls.ct."""
		frappe.set_user(self.scoped_email)
		try:
			return contract.revenue_by_group()
		finally:
			frappe.set_user("Administrator")

	def _by_cls(self, groups):
		return {g["classification"]: g for g in groups}

	def _idx_of_month(self, months, d):
		"""Index bucket của mốc tháng d trong months (nhãn 'T<m>'). Cửa sổ 12 tháng KHÔNG trùng 'T<m>'."""
		return months.index(f"T{d.month}")

	# (1) shape — 4 key + currency=='VND' + mỗi group đúng 4 key -------------------------------
	def test_shape(self):
		res = contract.revenue_by_group()
		self.assertIsInstance(res, dict)
		self.assertEqual(set(res.keys()), REVENUE_BY_GROUP_KEYS)
		self.assertEqual(set(res.keys()), set(contract.REVENUE_BY_GROUP_KEYS))
		self.assertEqual(res["currency"], "VND")
		self.assertIsInstance(res["months"], list)
		self.assertIsInstance(res["groups"], list)
		self.assertIsInstance(res["grand_total"], (int, float))
		for g in res["groups"]:
			self.assertEqual(set(g.keys()), GROUP_ROW_KEYS)
			self.assertEqual(set(g.keys()), set(contract.GROUP_ROW_KEYS))
			self.assertEqual(g["label"], g["classification"])
			self.assertIsInstance(g["monthly"], list)
			self.assertEqual(len(g["monthly"]), 12)
			self.assertIsInstance(g["total"], (int, float))

	# (2) months window — len==12, tăng dần, phần tử cuối = tháng hiện tại ----------------------
	def test_months_window(self):
		res = contract.revenue_by_group()
		months = res["months"]
		self.assertEqual(len(months), 12)
		for m in months:
			self.assertRegex(m, MONTH_SHORT_RE)
		# Phần tử cuối = tháng hiện tại (nhãn 'T<m>').
		self.assertEqual(months[-1], self.cur_label)
		# Khớp helper format BE (đồng nhất nguồn nhãn).
		self.assertEqual(months[-1], contract._month_short_label(self.today))
		# Thứ tự thời gian tăng dần: tái dựng cửa sổ 12 mốc từ nowdate, lùi 11 tháng → so khớp.
		from frappe.utils import add_months

		expect = [contract._month_short_label(add_months(self.today, off)) for off in range(-11, 1)]
		self.assertEqual(months, expect)

	# (3) bucket theo ts — log tháng X rơi đúng index; revenue = qty × unit_price (price_map) ---
	def test_bucket_by_ts(self):
		res = self._scoped()
		months = res["months"]
		by = self._by_cls(res["groups"])
		i0 = self._idx_of_month(months, self.m0)
		i1 = self._idx_of_month(months, self.m1)
		i5 = self._idx_of_month(months, self.m5)
		# Loại A: M0 = 10×2tr = 20tr ; M1 = 4×2tr = 8tr ; các bucket khác = 0.
		self.assertEqual(by["Loại A"]["monthly"][i0], 20_000_000.0)
		self.assertEqual(by["Loại A"]["monthly"][i1], 8_000_000.0)
		# Loại B: M0 = 5×4tr = 20tr.
		self.assertEqual(by["Loại B"]["monthly"][i0], 20_000_000.0)
		# Loại C: M5 = 6×3tr = 18tr (KHÔNG ở M0).
		self.assertEqual(by["Loại C"]["monthly"][i5], 18_000_000.0)
		self.assertEqual(by["Loại C"]["monthly"][i0], 0.0)
		# Bucket ngoài 3 mốc (vd ngay trước M0) = 0 cho Loại A.
		i_mid = self._idx_of_month(months, add_months_local(self.today, -3))
		self.assertEqual(by["Loại A"]["monthly"][i_mid], 0.0)

	# (4) log NGOÀI cửa sổ 12 tháng KHÔNG cộng vào bất kỳ bucket nào ----------------------------
	def test_out_of_window_ignored(self):
		res = self._scoped()
		by = self._by_cls(res["groups"])
		# Nếu log OUT (1000×2tr=2 tỷ) bị cộng nhầm → Loại A total ≫ 28tr.
		self.assertEqual(by["Loại A"]["total"], 28_000_000.0, msg="log ngoài cửa sổ KHÔNG được cộng")

	# (5) classification gộp đúng + item thiếu/ngoài A–D → 'Khác' ------------------------------
	def test_classification_group(self):
		res = self._scoped()
		by = self._by_cls(res["groups"])
		months = res["months"]
		i0 = self._idx_of_month(months, self.m0)
		# NOCLS (item KHÔNG phân loại) 3×1tr=3tr + GHOST (SKU no AntMed Item) 2×5tr=10tr → Khác = 13tr ở M0.
		self.assertEqual(by["Khác"]["monthly"][i0], 13_000_000.0)
		self.assertEqual(by["Khác"]["total"], 13_000_000.0)
		# Item Loại A → group 'Loại A' (KHÔNG lọt 'Khác').
		self.assertEqual(by["Loại A"]["total"], 28_000_000.0)

	# (6) 5 group LUÔN đủ thứ tự cố định A→B→C→D→Khác kể cả revenue=0 --------------------------
	def test_fixed_5_groups_order(self):
		res = contract.revenue_by_group()
		self.assertEqual([g["classification"] for g in res["groups"]], REVENUE_BY_GROUP_ORDER)
		self.assertEqual(len(res["groups"]), 5)
		# Loại D không có log nào (cả Admin lẫn scoped) → vẫn render dòng monthly toàn 0.
		d = self._by_cls(self._scoped()["groups"])["Loại D"]
		self.assertEqual(d["monthly"], [0.0] * 12)
		self.assertEqual(d["total"], 0.0)

	# (7) total = SUM(monthly) ; grand_total = SUM(group.total over 5 groups) -------------------
	def test_totals(self):
		res = self._scoped()
		for g in res["groups"]:
			self.assertEqual(
				g["total"], sum(g["monthly"]), msg=f"total≠SUM(monthly) cho {g['classification']}"
			)
		self.assertEqual(res["grand_total"], sum(g["total"] for g in res["groups"]))
		# Tổng kỳ vọng (scoped): A=28tr + B=20tr + C=18tr + D=0 + Khác=13tr = 79tr.
		self.assertEqual(res["grand_total"], 79_000_000.0)

	# (8) empty-scope — _empty_revenue_by_group() đúng shape (months 12, 5 group 0, grand 0) ----
	def test_empty_scope(self):
		res = contract._empty_revenue_by_group()
		self.assertEqual(set(res.keys()), REVENUE_BY_GROUP_KEYS)
		self.assertEqual(len(res["months"]), 12)
		for m in res["months"]:
			self.assertRegex(m, MONTH_SHORT_RE)
		self.assertEqual([g["classification"] for g in res["groups"]], REVENUE_BY_GROUP_ORDER)
		for g in res["groups"]:
			self.assertEqual(set(g.keys()), GROUP_ROW_KEYS)
			self.assertEqual(g["monthly"], [0.0] * 12)
			self.assertEqual(g["total"], 0.0)
		self.assertEqual(res["grand_total"], 0)
		self.assertEqual(res["currency"], "VND")

	# (8b) scope rỗng thực (NV thấy BV không có HĐ) → _empty shape -----------------------------
	def test_empty_scope_live(self):
		hosp = _mk_hospital("_T-RBG-HOSP-EMPTY", "BV RBG Empty")
		email = "_t_rbg_empty@example.com"
		_ensure_scoped_user(email, "NV kinh doanh", "AntMed Hospital", hosp.name)
		frappe.set_user(email)
		try:
			res = contract.revenue_by_group()
			self.assertEqual(len(res["months"]), 12)
			self.assertEqual([g["classification"] for g in res["groups"]], REVENUE_BY_GROUP_ORDER)
			self.assertTrue(all(g["monthly"] == [0.0] * 12 for g in res["groups"]))
			self.assertEqual(res["grand_total"], 0)
			self.assertEqual(res["currency"], "VND")
		finally:
			frappe.set_user("Administrator")
			frappe.db.delete(
				"User Permission", {"user": email, "allow": "AntMed Hospital", "for_value": hosp.name}
			)

	# (9) fail-closed — frappe.get_list raise PermissionError → _empty (KHÔNG raise, KHÔNG leak) -
	def test_fail_closed(self):
		import unittest.mock as mock

		def raise_perm(*args, **kwargs):
			raise frappe.PermissionError("no read AntMed Contract")

		with mock.patch.object(frappe, "get_list", side_effect=raise_perm):
			res = contract.revenue_by_group()
		self.assertEqual(len(res["months"]), 12)
		self.assertEqual([g["classification"] for g in res["groups"]], REVENUE_BY_GROUP_ORDER)
		self.assertTrue(all(g["monthly"] == [0.0] * 12 for g in res["groups"]))
		self.assertEqual(res["grand_total"], 0)
		self.assertEqual(res, contract._empty_revenue_by_group())

	# (10) data-scope BR-13 — NV scoped chỉ thấy revenue HĐ tuyến mình, KHÔNG thấy HĐ Admin -----
	def test_data_scope(self):
		hosp = _mk_hospital("_T-RBG-HOSP-SCOPED", "BV RBG Scoped")
		_mk_item("RBG-SC-A", "Loại A")
		ct = _mk_contract(
			"_T-RBG-CT-SCOPED",
			hosp.name,
			items=[_rev_row("RBG-SC-A", 0, 1_000_000)],
			status="Hiệu lực",
			valid_to="2027-12-31",
			total_value=10,
		)
		frappe.db.delete(QUOTA_USAGE_DOCTYPE, {"contract": ct.name})
		_mk_rev_log(ct.name, "RBG-SC-A", 7, self.ts_m0)  # 7×1tr = 7tr tháng này
		email = "_t_rbg_scoped@example.com"
		_ensure_scoped_user(email, "NV kinh doanh", "AntMed Hospital", hosp.name)
		frappe.set_user(email)
		try:
			res = contract.revenue_by_group()
			by = self._by_cls(res["groups"])
			i0 = self._idx_of_month(res["months"], self.m0)
			# Chỉ thấy HĐ BV scoped: Loại A M0 = 7tr (KHÔNG gồm 20tr của _T-RBG-HOSP ngoài scope).
			self.assertEqual(by["Loại A"]["monthly"][i0], 7_000_000.0)
			self.assertEqual(by["Loại A"]["total"], 7_000_000.0)
			self.assertEqual(res["grand_total"], 7_000_000.0)
		finally:
			frappe.set_user("Administrator")
			frappe.db.delete(
				"User Permission", {"user": email, "allow": "AntMed Hospital", "for_value": hosp.name}
			)

	# (11) GET-only — @frappe.whitelist(methods=['GET']) (POST → 403) --------------------------
	def test_get_only(self):
		fn = frappe.get_attr("antmed_crm.api.antmed.contract.revenue_by_group")
		self.assertTrue(callable(fn))
		allowed = frappe.allowed_http_methods_for_whitelisted_func.get(fn)
		self.assertIsNotNone(allowed, msg="revenue_by_group phải @frappe.whitelist(methods=[...])")
		self.assertIn("GET", allowed)
		self.assertNotIn("POST", allowed)
		import inspect

		src = inspect.getsource(contract.revenue_by_group)
		self.assertIn('methods=["GET"]', src)

	# (12) KHÔNG raw SQL + BATCH ≤4 query (get_list HĐ + get_all log/quota/item) — KHÔNG N+1 ----
	def test_no_raw_sql_batch(self):
		"""KHÔNG raw SQL + BATCH ≤4 query (1 get_list HĐ + 3 get_all: log + quota item + AntMed Item).

		Đo TÁCH BIỆT từng hàm trong patch context riêng — patch ĐỒNG THỜI cả get_list & get_all sẽ
		double-count do frappe.get_list nội bộ delegate sang get_all (đệ quy qua mock). get_all chỉ
		gồm 3 batch của ENDPOINT (item-class get_all skip khi không SKU nào sinh doanh thu → ≤3).
		get_list của endpoint = 1 (phần dư là Frappe nội bộ resolve permission) → bound nhẹ qua source.
		Chạy dưới NV scoped (data tất định) để 3 batch đều fire.
		"""
		import inspect
		import unittest.mock as mock

		src = inspect.getsource(contract.revenue_by_group)
		self.assertNotIn("frappe.db.sql", src, msg="revenue_by_group KHÔNG được dùng raw SQL (bỏ qua BR-13)")
		self.assertIn("get_list", src, msg="phải dùng frappe.get_list (fail-closed + scope BR-13)")
		# Endpoint phát ĐÚNG 1 get_list (HĐ scope) + 3 get_all (log/quota/item) ở source — KHÔNG N+1.
		self.assertEqual(src.count("frappe.get_list("), 1, msg="endpoint chỉ 1 get_list HĐ (scope)")
		self.assertEqual(src.count("frappe.get_all("), 3, msg="endpoint chỉ 3 get_all (log/quota/item)")

		# get_all batch của endpoint ≤3 (đo riêng — KHÔNG patch chung get_list để khỏi đệ quy nội bộ).
		# Đo dưới Administrator: frappe.get_list (Admin) KHÔNG spawn get_all nội bộ resolve permission
		# (non-Admin spawn thêm 1 → 4). Số get_all ở đây = batch THẬT của endpoint (log + quota + item,
		# item-class skip nếu không SKU nào sinh doanh thu → ≤3) → bound N+1 ổn định, KHÔNG phụ thuộc data.
		real_get_all = frappe.get_all
		n_all = {"n": 0}

		def counting_all(*args, **kwargs):
			n_all["n"] += 1
			return real_get_all(*args, **kwargs)

		with mock.patch.object(frappe, "get_all", side_effect=counting_all):
			contract.revenue_by_group()
		self.assertLessEqual(
			n_all["n"], 3, msg=f"N+1: get_all gọi {n_all['n']} lần (phải ≤3: log + quota item + AntMed Item)"
		)

	# (13) hằng REVENUE_BY_GROUP_CLASSES + order export ổn định (FE bind shape) ----------------
	def test_classes_constant(self):
		self.assertEqual(list(contract.REVENUE_BY_GROUP_CLASSES), ["Loại A", "Loại B", "Loại C", "Loại D"])


def add_months_local(d, n):
	"""Wrapper add_months (test helper — tránh import lặp trong từng test)."""
	from frappe.utils import add_months

	return add_months(d, n)
