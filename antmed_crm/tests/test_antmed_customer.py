# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M01 R2 Customer 360° — harness test (TDD viết TRƯỚC implement).

Cover acceptance R2 (Bệnh viện + Bác sỹ):
  test_create_hospital_and_doctor   — tạo AntMed Hospital + 2 AntMed Doctor link tới nó,
                                       assert exist sau insert + autoname đúng (BV=mã, BS=AM-DOC-).
  test_hospital_code_unique         — hospital_code unique (2 BV cùng code → lỗi).
  test_doctype_min_fields           — meta 2 DocType có đủ field tối thiểu (verify @source M1 dòng 13-14).
  test_list_hospitals_shape         — list_hospitals() trả {data,total_count}; item đúng 5 field;
                                       total_count == len(data) khi không phân trang (BR-13 count==rows).
  test_list_hospitals_search        — list_hospitals(search=...) lọc đúng theo hospital_name.
  test_get_hospital_360             — get_hospital(name) trả field BV + doctors[] đúng số lượng (2)
                                       + đúng full_name/specialty.
  test_list_doctors_filter_by_hospital — list_doctors(hospital=X) chỉ trả bác sỹ thuộc X.
  test_get_doctor_resolves_hospital_name — get_doctor resolve hospital_name qua Link.
  test_permission_guard             — user không có read → get_hospital/get_doctor raise PermissionError.

Lệnh chạy:
  bench --site miyano run-tests --module antmed_crm.tests.test_antmed_customer
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from antmed_crm.api.antmed import customer

# Field tối thiểu theo spec m01_customer360.md §DocTypes (ground @ Modules.md §1 dòng 13-14).
HOSPITAL_MIN_FIELDS = {
	"hospital_code",
	"hospital_name",
	"rank",
	"tax_code",
	"address",
	"contract_status",
}
DOCTOR_MIN_FIELDS = {
	"doctor_code",
	"full_name",
	"hospital",
	"specialty",
	"birthday",
	"phone",
	"email",
	"zalo",
	"notes",
}

# Item-shape chốt với FE (Hyrum — đổi = breaking binding createResource).
HOSPITAL_LIST_ITEM_FIELDS = {"name", "hospital_name", "rank", "contract_status", "tax_code"}


def _mk_hospital(code, name, **kw):
	doc = frappe.get_doc(
		{
			"doctype": "AntMed Hospital",
			"hospital_code": code,
			"hospital_name": name,
			**kw,
		}
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


class TestAntMedCustomer(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# BV mẫu + 2 bác sỹ thuộc BV đó (mặt 360).
		cls.hosp = _mk_hospital(
			"_T-HOSP-360",
			"BV Test Customer360",
			rank="Đặc biệt",
			tax_code="0123456789",
			address="01 Test St",
			contract_status="Đã ký",
		)
		cls.doc1 = _mk_doctor(
			"_T-BS-001",
			"Nguyễn Văn Test A",
			cls.hosp.name,
			specialty="Ngoại tổng quát",
			phone="0900000001",
		)
		cls.doc2 = _mk_doctor(
			"_T-BS-002",
			"Trần Thị Test B",
			cls.hosp.name,
			specialty="Tim mạch",
			phone="0900000002",
		)
		# BV thứ 2 + 1 bác sỹ — để chứng minh filter theo hospital không rò.
		cls.hosp2 = _mk_hospital("_T-HOSP-OTHER", "BV Khác Test", contract_status="Tiềm năng")
		cls.doc_other = _mk_doctor("_T-BS-OTHER", "Lê Văn Khác", cls.hosp2.name, specialty="Da liễu")

	# --- DocType existence + autoname ---------------------------------------
	def test_create_hospital_and_doctor(self):
		"""2 DocType tồn tại; BV autoname = hospital_code; bác sỹ autoname series AM-DOC-."""
		self.assertTrue(frappe.db.exists("DocType", "AntMed Hospital"))
		self.assertTrue(frappe.db.exists("DocType", "AntMed Doctor"))
		# BV: name == hospital_code (autoname field:hospital_code)
		self.assertEqual(self.hosp.name, "_T-HOSP-360")
		self.assertTrue(frappe.db.exists("AntMed Hospital", "_T-HOSP-360"))
		# Bác sỹ: name sinh theo series AM-DOC-…, KHÔNG AM-DR
		self.assertTrue(self.doc1.name.startswith("AM-DOC-"), msg=f"doctor name={self.doc1.name!r}")
		self.assertFalse(self.doc1.name.startswith("AM-DR"))
		self.assertTrue(frappe.db.exists("AntMed Doctor", self.doc1.name))

	def test_hospital_code_unique(self):
		"""hospital_code unique — tạo BV thứ 2 cùng code → ném lỗi."""
		with self.assertRaises((frappe.UniqueValidationError, frappe.DuplicateEntryError, frappe.ValidationError)):
			_mk_hospital("_T-HOSP-360", "Trùng mã")

	def test_doctype_min_fields(self):
		"""Meta 2 DocType có đủ field tối thiểu (verify @source M1 dòng 13-14)."""
		hosp_fields = {f.fieldname for f in frappe.get_meta("AntMed Hospital").fields}
		self.assertTrue(
			HOSPITAL_MIN_FIELDS.issubset(hosp_fields),
			msg=f"AntMed Hospital thiếu field: {HOSPITAL_MIN_FIELDS - hosp_fields}",
		)
		doc_fields = {f.fieldname for f in frappe.get_meta("AntMed Doctor").fields}
		self.assertTrue(
			DOCTOR_MIN_FIELDS.issubset(doc_fields),
			msg=f"AntMed Doctor thiếu field: {DOCTOR_MIN_FIELDS - doc_fields}",
		)

	# --- list_hospitals -----------------------------------------------------
	def test_list_hospitals_shape(self):
		"""Trả dict {data:list, total_count:int}; item đúng 5 field; count==rows khi không phân trang."""
		res = customer.list_hospitals(page_length=0)
		self.assertIsInstance(res, dict)
		self.assertEqual(set(res.keys()), {"data", "total_count"})
		self.assertIsInstance(res["data"], list)
		self.assertIsInstance(res["total_count"], int)
		self.assertGreaterEqual(len(res["data"]), 2)  # ít nhất 2 BV test
		# Item shape chốt (Hyrum)
		item = res["data"][0]
		self.assertEqual(set(item.keys()), HOSPITAL_LIST_ITEM_FIELDS)
		# BR-13 count == rows khi không phân trang
		self.assertEqual(len(res["data"]), res["total_count"])

	def test_list_hospitals_search(self):
		"""search lọc đúng theo hospital_name (LIKE)."""
		res = customer.list_hospitals(search="Customer360", page_length=0)
		names = [r["name"] for r in res["data"]]
		self.assertIn("_T-HOSP-360", names)
		self.assertNotIn("_T-HOSP-OTHER", names)
		self.assertEqual(len(res["data"]), res["total_count"])

	# --- get_hospital (mặt 360) ---------------------------------------------
	def test_get_hospital_360(self):
		"""Trả field BV + doctors[] đúng số (2) + đúng full_name/specialty/phone."""
		res = customer.get_hospital("_T-HOSP-360")
		self.assertEqual(res["name"], "_T-HOSP-360")
		self.assertEqual(res["hospital_name"], "BV Test Customer360")
		self.assertEqual(res["rank"], "Đặc biệt")
		self.assertEqual(res["contract_status"], "Đã ký")
		self.assertIn("doctors", res)
		self.assertEqual(len(res["doctors"]), 2)
		child_keys = set(res["doctors"][0].keys())
		self.assertEqual(child_keys, {"name", "full_name", "specialty", "phone"})
		full_names = {d["full_name"] for d in res["doctors"]}
		self.assertEqual(full_names, {"Nguyễn Văn Test A", "Trần Thị Test B"})
		specialties = {d["specialty"] for d in res["doctors"]}
		self.assertEqual(specialties, {"Ngoại tổng quát", "Tim mạch"})

	# --- list_doctors -------------------------------------------------------
	def test_list_doctors_filter_by_hospital(self):
		"""list_doctors(hospital=X) chỉ trả bác sỹ thuộc X; count==rows."""
		res = customer.list_doctors(hospital="_T-HOSP-360", page_length=0)
		self.assertEqual(set(res.keys()), {"data", "total_count"})
		names = {r["name"] for r in res["data"]}
		self.assertEqual(names, {self.doc1.name, self.doc2.name})
		self.assertNotIn(self.doc_other.name, names)
		self.assertEqual(len(res["data"]), res["total_count"])

	def test_get_doctor_resolves_hospital_name(self):
		"""get_doctor trả profile + hospital_name resolve đúng qua Link (link ngược về BV)."""
		res = customer.get_doctor(self.doc1.name)
		self.assertEqual(res["name"], self.doc1.name)
		self.assertEqual(res["full_name"], "Nguyễn Văn Test A")
		self.assertEqual(res["hospital"], "_T-HOSP-360")
		self.assertEqual(res["hospital_name"], "BV Test Customer360")
		self.assertEqual(res["specialty"], "Ngoại tổng quát")

	# --- permission guard ---------------------------------------------------
	def test_permission_guard(self):
		"""User không có read-perm → get_hospital/get_doctor raise frappe.PermissionError."""
		# Tạo user thường không gán role AntMed (chỉ có quyền mặc định, KHÔNG read 2 DocType này).
		email = "_t_antmed_noperm@example.com"
		if not frappe.db.exists("User", email):
			u = frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": "NoPerm",
					"send_welcome_email": 0,
				}
			)
			u.insert(ignore_permissions=True)
		frappe.set_user(email)
		try:
			with self.assertRaises(frappe.PermissionError):
				customer.get_hospital("_T-HOSP-360")
			with self.assertRaises(frappe.PermissionError):
				customer.get_doctor(self.doc1.name)
		finally:
			frappe.set_user("Administrator")

	# --- data-confidentiality: list endpoints must NOT leak to no-read user ----
	def test_list_endpoints_no_leak_for_noperm_user(self):
		"""User KHÔNG có read-perm → list_hospitals/list_doctors KHÔNG rò bản ghi nào.

		Frappe get_list (DatabaseQuery.check_read_permission) khi user không có BẤT KỲ read-perm
		nào trên doctype sẽ RAISE PermissionError (an toàn — chặn ngay, không trả data). Đây là
		hành vi non-leak đúng. Test chốt: hoặc raise PermissionError, hoặc (nếu Frappe đổi) trả
		rỗng — TUYỆT ĐỐI không có row nào lọt ra.
		"""
		email = "_t_antmed_noperm@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": "NoPerm", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		# sanity: admin DOES see the seeded rows (chống false-green: nếu DB rỗng test vô nghĩa)
		self.assertGreaterEqual(customer.list_hospitals(page_length=0)["total_count"], 2)
		frappe.set_user(email)
		try:
			for fn, kw in [(customer.list_hospitals, {}), (customer.list_doctors, {})]:
				try:
					res = fn(page_length=0)
				except frappe.PermissionError:
					continue  # an toàn: chặn ngay, không trả data
				# nếu KHÔNG raise thì BẮT BUỘC rỗng (không row nào lọt)
				self.assertEqual(res["total_count"], 0, msg=f"LEAK qua {fn.__name__}: {res}")
				self.assertEqual(len(res["data"]), 0, msg=f"LEAK rows qua {fn.__name__}: {res}")
				self.assertEqual(len(res["data"]), res["total_count"])
		finally:
			frappe.set_user("Administrator")

	def test_sales_rep_can_read_hospital_and_doctor(self):
		"""RBAC dương: user gán role 'NV kinh doanh' (DEC-A, was 'AntMed Sales Rep') ĐỌC được
		BV + bác sỹ (DocPerm read=1), chứng minh role thực sự mở quyền (không chỉ chặn no-perm)."""
		role = "NV kinh doanh"
		email = "_t_antmed_salesrep@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": "SalesRep",
					"send_welcome_email": 0,
					"roles": [{"role": role}],
				}
			).insert(ignore_permissions=True)
		else:
			u = frappe.get_doc("User", email)
			if role not in [r.role for r in u.roles]:
				u.add_roles(role)
		frappe.set_user(email)
		try:
			rh = customer.list_hospitals(page_length=0)
			self.assertGreaterEqual(
				rh["total_count"], 2, msg="NV kinh doanh KHÔNG đọc được BV — RBAC sai"
			)
			# get_hospital + get_doctor không được raise PermissionError với NV kinh doanh
			gh = customer.get_hospital("_T-HOSP-360")
			self.assertEqual(gh["name"], "_T-HOSP-360")
			gd = customer.get_doctor(self.doc1.name)
			self.assertEqual(gd["name"], self.doc1.name)
		finally:
			frappe.set_user("Administrator")

	def test_docperm_roles_are_vietnamese(self):
		"""DocPerm gắn đúng (DEC-A): meta 2 DocType có role VI với ma trận quyền đúng.

		'Quản lý' = full (write+create+delete); 'NV kinh doanh' = read/write/create KHÔNG delete.
		KHÔNG còn role EN nào trong permissions của 2 DocType.
		"""
		legacy_en = {"AntMed Manager", "AntMed Sales Rep", "AntMed Warehouse Keeper"}
		for dt in ("AntMed Hospital", "AntMed Doctor"):
			perms = {p.role: p for p in frappe.get_meta(dt).permissions}
			# không sót role EN
			self.assertEqual(
				legacy_en & set(perms),
				set(),
				msg=f"{dt}: còn DocPerm role EN: {legacy_en & set(perms)}",
			)
			# Quản lý: full
			self.assertIn("Quản lý", perms, msg=f"{dt}: thiếu DocPerm 'Quản lý'")
			ql = perms["Quản lý"]
			self.assertTrue(ql.read and ql.write and ql.create and ql.delete,
				msg=f"{dt}: 'Quản lý' phải full quyền (read/write/create/delete)")
			# NV kinh doanh: read/write/create, KHÔNG delete
			self.assertIn("NV kinh doanh", perms, msg=f"{dt}: thiếu DocPerm 'NV kinh doanh'")
			nv = perms["NV kinh doanh"]
			self.assertTrue(nv.read and nv.write and nv.create,
				msg=f"{dt}: 'NV kinh doanh' phải có read/write/create")
			self.assertFalse(nv.delete,
				msg=f"{dt}: 'NV kinh doanh' KHÔNG được có quyền delete (BR DocPerm)")
