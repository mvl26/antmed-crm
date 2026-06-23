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
		with self.assertRaises(
			(frappe.UniqueValidationError, frappe.DuplicateEntryError, frappe.ValidationError)
		):
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
			for fn, _kw in [(customer.list_hospitals, {}), (customer.list_doctors, {})]:
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
			self.assertGreaterEqual(rh["total_count"], 2, msg="NV kinh doanh KHÔNG đọc được BV — RBAC sai")
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
			self.assertTrue(
				ql.read and ql.write and ql.create and ql.delete,
				msg=f"{dt}: 'Quản lý' phải full quyền (read/write/create/delete)",
			)
			# NV kinh doanh: read/write/create, KHÔNG delete
			self.assertIn("NV kinh doanh", perms, msg=f"{dt}: thiếu DocPerm 'NV kinh doanh'")
			nv = perms["NV kinh doanh"]
			self.assertTrue(
				nv.read and nv.write and nv.create, msg=f"{dt}: 'NV kinh doanh' phải có read/write/create"
			)
			self.assertFalse(nv.delete, msg=f"{dt}: 'NV kinh doanh' KHÔNG được có quyền delete (BR DocPerm)")


# ---------------------------------------------------------------------------
# M07-1 — Portal Bệnh viện "Thông báo gần đây" (TDD viết TRƯỚC implement).
#
# Endpoint MỚI: customer.portal_notifications(hospital) @whitelist(methods=['GET'])
# RAW dict {data, hospital, hospital_name}; mỗi item shape ỔN ĐỊNH (Hyrum) >=4 key:
#   kind ('delivery'|'quota') · ts (datetime iso) · title (str VI) · ref (str|None).
# - delivery = AntMed Stock Entry entry_type='Xuất cho NV' AND hospital=<bv>
#              (get_list dưới DocPerm, fail-closed PermissionError → []).
# - quota    = quota item của HĐ thuộc BV có used_pct ở band cảnh báo (>=70%),
#              batch get_all theo parent IN scope (KHÔNG N+1).
# - merge → sort ts desc → cắt top LIMIT.
#
# Lệnh: bench --site miyano run-tests --module antmed_crm.tests.test_antmed_customer
# ---------------------------------------------------------------------------
import inspect


def _mk_warehouse(name, wtype="Tổng"):
	if frappe.db.exists("AntMed Warehouse", name):
		return frappe.get_doc("AntMed Warehouse", name)
	return frappe.get_doc(
		{"doctype": "AntMed Warehouse", "warehouse_name": name, "warehouse_type": wtype}
	).insert(ignore_permissions=True)


def _mk_item(code, name):
	if frappe.db.exists("AntMed Item", code):
		return frappe.get_doc("AntMed Item", code)
	return frappe.get_doc({"doctype": "AntMed Item", "item_code": code, "item_name": name}).insert(
		ignore_permissions=True
	)


def _mk_lot(lot_no, item):
	if frappe.db.exists("AntMed Lot", lot_no):
		return frappe.get_doc("AntMed Lot", lot_no)
	return frappe.get_doc(
		{"doctype": "AntMed Lot", "lot_no": lot_no, "item": item, "expiry_date": "2030-12-31"}
	).insert(ignore_permissions=True)


def _receipt(wh, item, lot, qty):
	"""Nhập NCC để có tồn (cho phép Xuất cho NV submit không âm)."""
	doc = frappe.get_doc(
		{
			"doctype": "AntMed Stock Entry",
			"entry_type": "Nhập NCC",
			"to_warehouse": wh,
			"items": [{"item": item, "lot": lot, "qty": qty}],
		}
	)
	doc.insert(ignore_permissions=True)
	doc.submit()
	return doc


def _issue_to_nv(wh, item, lot, qty, hospital, posting_dt=None):
	"""Phiếu 'Xuất cho NV' submit cho 1 bệnh viện (delivery event nguồn)."""
	doc = frappe.get_doc(
		{
			"doctype": "AntMed Stock Entry",
			"entry_type": "Xuất cho NV",
			"from_warehouse": wh,
			"hospital": hospital,
			"items": [{"item": item, "lot": lot, "qty": qty}],
		}
	)
	doc.insert(ignore_permissions=True)
	doc.submit()
	if posting_dt:
		frappe.db.set_value(
			"AntMed Stock Entry", doc.name, "posting_datetime", posting_dt, update_modified=False
		)
	return doc


def _mk_contract(no, hospital, quota_rows):
	"""HĐ + child quota items. quota_rows = list of dict(item,item_name,quota_qty,used_qty)."""
	doc = frappe.get_doc(
		{
			"doctype": "AntMed Contract",
			"contract_no": no,
			"hospital": hospital,
			"status": "Hiệu lực",
			"signed_date": "2026-01-01",
			"items": quota_rows,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


class TestPortalNotifications(FrappeTestCase):
	"""M07-1 — customer.portal_notifications(hospital)."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# 2 bệnh viện cô lập.
		cls.bv_a = _mk_hospital("_T-PNOTIF-A", "BV Portal A").name
		cls.bv_b = _mk_hospital("_T-PNOTIF-B", "BV Portal B").name
		# Kho / item / lô + tồn đủ để xuất.
		cls.wh = _mk_warehouse("_T-PNOTIF-WH").name
		cls.item = _mk_item("_T-PNOTIF-IT", "Vật tư Portal").name
		cls.lot = _mk_lot("_T-PNOTIF-LOT", cls.item).name
		_receipt(cls.wh, cls.item, cls.lot, 1000)
		# Delivery: 2 phiếu Xuất cho NV cho BV_A (mốc khác nhau) + 1 cho BV_B.
		cls.se_a1 = _issue_to_nv(cls.wh, cls.item, cls.lot, 5, cls.bv_a, "2026-06-10 08:00:00").name
		cls.se_a2 = _issue_to_nv(cls.wh, cls.item, cls.lot, 7, cls.bv_a, "2026-06-15 09:30:00").name
		cls.se_b1 = _issue_to_nv(cls.wh, cls.item, cls.lot, 3, cls.bv_b, "2026-06-14 10:00:00").name
		# Quota: HĐ của BV_A có 1 item used_pct>=70 (80/100=80%) + 1 item <70 (10/100=10%).
		cls.contract_a = _mk_contract(
			"_T-PNOTIF-HD-A",
			cls.bv_a,
			[
				{
					"item": cls.item,
					"item_name": "Quota Cảnh báo 80%",
					"quota_qty": 100,
					"used_qty": 80,
				},
				{
					"item": cls.item,
					"item_name": "Quota An toàn 10%",
					"quota_qty": 100,
					"used_qty": 10,
				},
			],
		).name

	# --- shape (Hyrum lock) -------------------------------------------------
	def test_shape_top_level(self):
		"""Trả dict đủ key {data, hospital, hospital_name}; data là list."""
		from antmed_crm.api.antmed import customer as cust

		res = cust.portal_notifications(self.bv_a)
		self.assertIsInstance(res, dict)
		self.assertEqual(set(res.keys()), {"data", "hospital", "hospital_name"})
		self.assertEqual(res["hospital"], self.bv_a)
		self.assertEqual(res["hospital_name"], "BV Portal A")
		self.assertIsInstance(res["data"], list)

	def test_item_shape_min_4_keys(self):
		"""Mỗi item có >=4 key {kind, ts, title, ref} (Hyrum)."""
		from antmed_crm.api.antmed import customer as cust

		res = cust.portal_notifications(self.bv_a)
		self.assertGreater(len(res["data"]), 0)
		for it in res["data"]:
			self.assertTrue({"kind", "ts", "title", "ref"}.issubset(set(it.keys())))
			self.assertIn(it["kind"], ("delivery", "quota"))
			self.assertIsInstance(it["title"], str)

	# --- delivery -----------------------------------------------------------
	def test_delivery_only_for_this_hospital(self):
		"""BV_A chỉ chứa 2 delivery của BV_A; KHÔNG lẫn BV_B; title chứa naming_series; ts=posting_datetime."""
		from antmed_crm.api.antmed import customer as cust

		res = cust.portal_notifications(self.bv_a)
		deliveries = [it for it in res["data"] if it["kind"] == "delivery"]
		refs = {it["ref"] for it in deliveries}
		self.assertEqual(refs, {self.se_a1, self.se_a2})
		self.assertNotIn(self.se_b1, refs)
		# title dạng 'Phiếu giao <name> đã xuất cho NV'
		for it in deliveries:
			self.assertIn(it["ref"], it["title"])
			self.assertIn("đã xuất cho NV", it["title"])
		# ts == posting_datetime của phiếu (iso)
		ts_map = {it["ref"]: str(it["ts"]) for it in deliveries}
		self.assertIn("2026-06-10 08:00:00", ts_map[self.se_a1])
		self.assertIn("2026-06-15 09:30:00", ts_map[self.se_a2])

	# --- quota --------------------------------------------------------------
	def test_quota_only_band_items(self):
		"""Đúng 1 quota event (used_pct>=70); item <70 KHÔNG xuất hiện; title 'Quota <name> còn <100-pct>%'."""
		from antmed_crm.api.antmed import customer as cust

		res = cust.portal_notifications(self.bv_a)
		quotas = [it for it in res["data"] if it["kind"] == "quota"]
		self.assertEqual(len(quotas), 1, msg=f"quota events={quotas}")
		q = quotas[0]
		# 80% used → còn 20%
		self.assertIn("Quota Cảnh báo 80%", q["title"])
		self.assertIn("còn 20%", q["title"])
		# item <70 (10%) không có
		titles = " | ".join(it["title"] for it in quotas)
		self.assertNotIn("An toàn 10%", titles)

	# --- sort + limit -------------------------------------------------------
	def test_sort_desc_and_limit(self):
		"""Merge delivery+quota sắp ts giảm dần; số dòng <= LIMIT."""
		from antmed_crm.api.antmed import customer as cust

		res = cust.portal_notifications(self.bv_a)
		data = res["data"]
		self.assertLessEqual(len(data), cust.PORTAL_NOTIF_LIMIT)
		ts_list = [str(it["ts"]) for it in data if it["ts"] is not None]
		self.assertEqual(ts_list, sorted(ts_list, reverse=True), msg=f"chưa sort desc: {ts_list}")

	# --- empty --------------------------------------------------------------
	def test_empty_when_no_events(self):
		"""BV không có stock entry & không có quota cảnh báo → data == [] (không lỗi)."""
		from antmed_crm.api.antmed import customer as cust

		empty_bv = _mk_hospital("_T-PNOTIF-EMPTY", "BV Trống Portal").name
		res = cust.portal_notifications(empty_bv)
		self.assertEqual(res["data"], [])
		self.assertEqual(res["hospital"], empty_bv)
		self.assertEqual(res["hospital_name"], "BV Trống Portal")

	# --- fail-closed --------------------------------------------------------
	def test_fail_closed_on_permission_error(self):
		"""monkeypatch frappe.get_list raise PermissionError → trả _empty (data==[]) KHÔNG raise 500."""
		from antmed_crm.api.antmed import customer as cust

		orig = frappe.get_list

		def _boom(*a, **kw):
			raise frappe.PermissionError("denied")

		frappe.get_list = _boom
		try:
			res = cust.portal_notifications(self.bv_a)
		finally:
			frappe.get_list = orig
		self.assertEqual(res["data"], [])
		self.assertEqual(set(res.keys()), {"data", "hospital", "hospital_name"})

	# --- GET-only -----------------------------------------------------------
	def test_get_only_whitelist(self):
		"""@whitelist(methods=['GET']) — chỉ GET, POST bị từ chối."""
		from antmed_crm.api.antmed import customer as cust

		# Frappe lưu ràng buộc HTTP method ở map này (không phải thuộc tính trên hàm).
		allowed = frappe.allowed_http_methods_for_whitelisted_func.get(cust.portal_notifications)
		self.assertIsNotNone(allowed, msg="endpoint không khai báo methods whitelist")
		self.assertIn("GET", allowed)
		self.assertNotIn("POST", allowed)
		# Phải nằm trong tập whitelisted (callable từ FE).
		self.assertIn(cust.portal_notifications, frappe.whitelisted)

	# --- no raw SQL ---------------------------------------------------------
	def test_no_raw_sql_in_source(self):
		"""Hàm KHÔNG dùng frappe.db.sql (inspect source)."""
		from antmed_crm.api.antmed import customer as cust

		src = inspect.getsource(cust.portal_notifications)
		self.assertNotIn("frappe.db.sql", src)
		self.assertNotIn(".sql(", src)

	# --- no N+1 (quota batch) ----------------------------------------------
	def test_quota_no_n_plus_1(self):
		"""Quota dùng 1 get_all theo parent IN names (spy count) dù nhiều HĐ.

		Dùng BV RIÊNG (_T-PNOTIF-NN) với 2 HĐ — tránh polluting BV_A cho test khác
		(FrappeTestCase commit giữa các test → record seed sẽ lưu lại)."""
		from antmed_crm.api.antmed import customer as cust

		bv_nn = _mk_hospital("_T-PNOTIF-NN", "BV Portal NplusOne").name
		for no, used in (("_T-PNOTIF-NN-HD1", 80), ("_T-PNOTIF-NN-HD2", 90)):
			if not frappe.db.exists("AntMed Contract", {"contract_no": no}):
				_mk_contract(
					no,
					bv_nn,
					[{"item": self.item, "item_name": f"Quota {no}", "quota_qty": 100, "used_qty": used}],
				)
		orig_get_all = frappe.get_all
		calls = {"quota": 0}

		def _spy(doctype, *a, **kw):
			if doctype == "AntMed Quota Item":
				calls["quota"] += 1
			return orig_get_all(doctype, *a, **kw)

		frappe.get_all = _spy
		try:
			res = cust.portal_notifications(bv_nn)
		finally:
			frappe.get_all = orig_get_all
		self.assertEqual(calls["quota"], 1, msg=f"quota phải 1 get_all (batch), thực tế={calls['quota']}")
		# vẫn merge đúng (2 quota cảnh báo: 80% + 90% — từ 2 HĐ khác nhau)
		quotas = [it for it in res["data"] if it["kind"] == "quota"]
		self.assertEqual(len(quotas), 2, msg=f"quotas={quotas}")


# ---------------------------------------------------------------------------
# M07-2 — Portal BV widget "Danh mục vật tư trúng thầu" (TDD viết TRƯỚC implement).
#
# Endpoint MỚI: customer.tender_catalog(hospital) @whitelist(methods=['GET'])
# RAW dict ổn định:
#   { hospital, hospital_name, contract, items:[{ item, item_name, uom,
#     remaining_qty, quota_qty, used_qty, remaining_pct, quota_chip }] }
# - items = TẤT CẢ AntMed Quota Item của HĐ status ∈ {Hiệu lực, Sắp hết hạn} của BV
#   (gộp nhiều HĐ active; LOẠI Nháp/Hết hạn/Đã huỷ).
# - remaining_qty = quota_qty - used_qty; remaining_pct = 100*remaining_qty/quota_qty
#   (quota_qty==0 → remaining_pct = 0.0, KHÔNG ZeroDivision).
# - quota_chip phân tầng THẬT theo remaining_pct: 'ok' (>10) / 'warn' (>0 và ≤10) /
#   'danger' (≤0 = hết quota).
# - KHÔNG có HĐ active → { contract: None, items: [] } (KHÔNG throw); hospital_name resolve.
# - KHÔNG trả unit_price (data-scope portal BV — BR).
#
# Lệnh: bench --site miyano run-tests --module antmed_crm.tests.test_antmed_customer
# ---------------------------------------------------------------------------
def _mk_contract_status(no, hospital, status, quota_rows):
	"""HĐ + child quota items với status tuỳ chọn (Nháp/Hiệu lực/Sắp hết hạn/Hết hạn/Đã huỷ)."""
	doc = frappe.get_doc(
		{
			"doctype": "AntMed Contract",
			"contract_no": no,
			"hospital": hospital,
			"status": status,
			"signed_date": "2026-01-01",
			"items": quota_rows,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


TENDER_ITEM_KEYS = {
	"item",
	"item_name",
	"uom",
	"remaining_qty",
	"quota_qty",
	"used_qty",
	"remaining_pct",
	"quota_chip",
}


class TestTenderCatalog(FrappeTestCase):
	"""M07-2 — customer.tender_catalog(hospital).

	remaining_pct LÀ TÍNH LẠI (100*remaining_qty/quota_qty), KHÔNG đọc field stored.
	Gộp THEO SKU (item) cross-contract: cộng quota_qty/used_qty rồi tính lại pct/chip.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.bv = _mk_hospital("_T-TCAT-A", "BV Tender Catalog A").name
		# 3 SKU PHÂN BIỆT (thực tế: SKU=item code, item_name=tên SKU đó) — remaining_pct THẬT 50/8/0:
		#   50% còn → used 50/100  (ok)   ·  8% còn → used 92/100 (warn)  ·  0% còn → 100/100 (danger).
		cls.contract = _mk_contract_status(
			"_T-TCAT-HD-ACTIVE",
			cls.bv,
			"Hiệu lực",
			[
				{
					"item": "_T-TCAT-OK",
					"item_name": "VT Còn nhiều",
					"uom": "Cái",
					"quota_qty": 100,
					"used_qty": 50,
					"unit_price": 12000,
				},
				{
					"item": "_T-TCAT-WARN",
					"item_name": "VT Sắp hết",
					"uom": "Hộp",
					"quota_qty": 100,
					"used_qty": 92,
					"unit_price": 5000,
				},
				{
					"item": "_T-TCAT-DANGER",
					"item_name": "VT Hết quota",
					"uom": "Cái",
					"quota_qty": 100,
					"used_qty": 100,
					"unit_price": 3000,
				},
			],
		).name

	def test_tender_catalog_top_level_shape(self):
		"""Trả dict ĐÚNG 4 key {hospital, hospital_name, contract, items}; items là list."""
		from antmed_crm.api.antmed import customer as cust

		res = cust.tender_catalog(self.bv)
		self.assertIsInstance(res, dict)
		self.assertEqual(set(res.keys()), {"hospital", "hospital_name", "contract", "items"})
		self.assertEqual(res["hospital"], self.bv)
		self.assertEqual(res["hospital_name"], "BV Tender Catalog A")
		self.assertIsInstance(res["items"], list)

	def test_tender_catalog_returns_active_contract_items(self):
		"""HĐ 'Hiệu lực' 3 quota item (remaining_pct 50/8/0) → 3 item, chip ok/warn/danger,
		remaining_qty = quota_qty-used_qty đúng."""
		from antmed_crm.api.antmed import customer as cust

		res = cust.tender_catalog(self.bv)
		self.assertEqual(res["hospital"], self.bv)
		self.assertEqual(res["hospital_name"], "BV Tender Catalog A")
		# contract = docname (autoname series AM-HD-…), KHÔNG phải contract_no.
		self.assertEqual(res["contract"], self.contract)
		items = res["items"]
		self.assertEqual(len(items), 3, msg=f"items={items}")
		by_sku = {it["item"]: it for it in items}
		ok = by_sku["_T-TCAT-OK"]
		warn = by_sku["_T-TCAT-WARN"]
		danger = by_sku["_T-TCAT-DANGER"]
		# remaining_qty = quota - used
		self.assertEqual(ok["remaining_qty"], 50)
		self.assertEqual(warn["remaining_qty"], 8)
		self.assertEqual(danger["remaining_qty"], 0)
		# remaining_pct TÍNH LẠI THẬT
		self.assertEqual(ok["remaining_pct"], 50.0)
		self.assertEqual(warn["remaining_pct"], 8.0)
		self.assertEqual(danger["remaining_pct"], 0.0)
		# phân tầng chip THẬT theo ngưỡng >10 / 0<·≤10 / ≤0
		self.assertEqual(ok["quota_chip"], "ok")
		self.assertEqual(warn["quota_chip"], "warn")
		self.assertEqual(danger["quota_chip"], "danger")
		# ánh xạ đúng thứ tự acceptance ['ok','warn','danger']
		chips = [by_sku[s]["quota_chip"] for s in ("_T-TCAT-OK", "_T-TCAT-WARN", "_T-TCAT-DANGER")]
		self.assertEqual(chips, ["ok", "warn", "danger"])
		# uom + item_name pass-through
		self.assertEqual(ok["uom"], "Cái")
		self.assertEqual(warn["uom"], "Hộp")
		self.assertEqual(ok["item_name"], "VT Còn nhiều")

	def test_tender_catalog_chip_boundaries(self):
		"""Biên chip CHÍNH XÁC: remaining_pct=10 → 'warn' (≤10), =10.01→'ok', =0→'danger'."""
		from antmed_crm.api.antmed import customer as cust

		bv_b = _mk_hospital("_T-TCAT-BND", "BV Tender Biên").name
		_mk_contract_status(
			"_T-TCAT-HD-BND",
			bv_b,
			"Hiệu lực",
			[
				# 10% còn (used 90/100) → biên trên warn (≤10).
				{
					"item": "_T-TCAT-B10",
					"item_name": "Biên 10",
					"uom": "Cái",
					"quota_qty": 100,
					"used_qty": 90,
				},
				# >10% (used 89/100 = 11%) → ok.
				{
					"item": "_T-TCAT-B11",
					"item_name": "Biên 11",
					"uom": "Cái",
					"quota_qty": 100,
					"used_qty": 89,
				},
			],
		)
		res = cust.tender_catalog(bv_b)
		by_sku = {it["item"]: it for it in res["items"]}
		self.assertEqual(by_sku["_T-TCAT-B10"]["quota_chip"], "warn")
		self.assertEqual(by_sku["_T-TCAT-B11"]["quota_chip"], "ok")

	def test_tender_catalog_omits_unit_price(self):
		"""Mỗi item dict ĐÚNG 8 key, KHÔNG chứa key unit_price (data-scope portal BV)."""
		from antmed_crm.api.antmed import customer as cust

		res = cust.tender_catalog(self.bv)
		self.assertGreater(len(res["items"]), 0)
		for it in res["items"]:
			self.assertNotIn("unit_price", it, msg=f"LỘ unit_price: {it}")
			self.assertEqual(set(it.keys()), TENDER_ITEM_KEYS, msg=f"shape sai: {it}")

	def test_tender_catalog_excludes_inactive_contracts(self):
		"""HĐ Hết hạn/Nháp/Đã huỷ KHÔNG xuất hiện; chỉ Hiệu lực/Sắp hết hạn."""
		from antmed_crm.api.antmed import customer as cust

		bv2 = _mk_hospital("_T-TCAT-MIX", "BV Tender Mix").name
		# HĐ active 'Sắp hết hạn' (PHẢI xuất hiện).
		_mk_contract_status(
			"_T-TCAT-HD-SOON",
			bv2,
			"Sắp hết hạn",
			[
				{
					"item": "_T-TCAT-SOON",
					"item_name": "VT Active Soon",
					"uom": "Cái",
					"quota_qty": 100,
					"used_qty": 10,
				}
			],
		)
		# HĐ inactive — KHÔNG được xuất hiện.
		_mk_contract_status(
			"_T-TCAT-HD-EXP",
			bv2,
			"Hết hạn",
			[
				{
					"item": "_T-TCAT-EXP",
					"item_name": "VT Expired",
					"uom": "Cái",
					"quota_qty": 100,
					"used_qty": 10,
				}
			],
		)
		_mk_contract_status(
			"_T-TCAT-HD-DRAFT",
			bv2,
			"Nháp",
			[
				{
					"item": "_T-TCAT-DRAFT",
					"item_name": "VT Draft",
					"uom": "Cái",
					"quota_qty": 100,
					"used_qty": 10,
				}
			],
		)
		_mk_contract_status(
			"_T-TCAT-HD-CANCEL",
			bv2,
			"Đã huỷ",
			[
				{
					"item": "_T-TCAT-CANCEL",
					"item_name": "VT Cancelled",
					"uom": "Cái",
					"quota_qty": 100,
					"used_qty": 10,
				}
			],
		)
		res = cust.tender_catalog(bv2)
		item_codes = {it["item"] for it in res["items"]}
		self.assertIn("_T-TCAT-SOON", item_codes)
		self.assertNotIn("_T-TCAT-EXP", item_codes)
		self.assertNotIn("_T-TCAT-DRAFT", item_codes)
		self.assertNotIn("_T-TCAT-CANCEL", item_codes)

	def test_tender_catalog_no_active_contract_returns_empty(self):
		"""BV không có HĐ active → {contract: None, items: []} (KHÔNG throw); hospital_name resolve đúng."""
		from antmed_crm.api.antmed import customer as cust

		bv_empty = _mk_hospital("_T-TCAT-EMPTY", "BV Tender Trống").name
		# Chỉ 1 HĐ Nháp (không active).
		_mk_contract_status(
			"_T-TCAT-HD-NONE",
			bv_empty,
			"Nháp",
			[
				{
					"item": "_T-TCAT-NONE",
					"item_name": "VT Nháp",
					"uom": "Cái",
					"quota_qty": 100,
					"used_qty": 10,
				}
			],
		)
		res = cust.tender_catalog(bv_empty)
		self.assertIsNone(res["contract"])
		self.assertEqual(res["items"], [])
		self.assertEqual(res["hospital"], bv_empty)
		self.assertEqual(res["hospital_name"], "BV Tender Trống")

	def test_tender_catalog_unknown_hospital_returns_empty(self):
		"""hospital không tồn tại → {contract:None, items:[], hospital_name:None} (KHÔNG throw)."""
		from antmed_crm.api.antmed import customer as cust

		res = cust.tender_catalog("_T-TCAT-DOES-NOT-EXIST")
		self.assertEqual(set(res.keys()), {"hospital", "hospital_name", "contract", "items"})
		self.assertIsNone(res["contract"])
		self.assertEqual(res["items"], [])

	def test_tender_catalog_merges_same_sku_across_contracts(self):
		"""2 HĐ active CÙNG SKU → gộp 1 dòng: quota_qty/used_qty cộng, remaining_pct tính lại."""
		from antmed_crm.api.antmed import customer as cust

		bv_mg = _mk_hospital("_T-TCAT-MG", "BV Tender Merge").name
		_mk_contract_status(
			"_T-TCAT-HD-MG1",
			bv_mg,
			"Hiệu lực",
			[
				{
					"item": "_T-TCAT-MGSKU",
					"item_name": "VT Gộp",
					"uom": "Cái",
					"quota_qty": 100,
					"used_qty": 40,
				}
			],
		)
		_mk_contract_status(
			"_T-TCAT-HD-MG2",
			bv_mg,
			"Sắp hết hạn",
			[
				{
					"item": "_T-TCAT-MGSKU",
					"item_name": "VT Gộp",
					"uom": "Cái",
					"quota_qty": 100,
					"used_qty": 56,
				}
			],
		)
		res = cust.tender_catalog(bv_mg)
		self.assertEqual(len(res["items"]), 1, msg=f"phải gộp 1 dòng: {res['items']}")
		it = res["items"][0]
		self.assertEqual(it["item"], "_T-TCAT-MGSKU")
		self.assertEqual(it["quota_qty"], 200)  # 100 + 100
		self.assertEqual(it["used_qty"], 96)  # 40 + 56
		self.assertEqual(it["remaining_qty"], 104)  # 200 - 96
		self.assertEqual(it["remaining_pct"], 52.0)  # 104/200
		self.assertEqual(it["quota_chip"], "ok")

	def test_tender_catalog_merges_distinct_sku_multiple_contracts(self):
		"""Nhiều HĐ active SKU KHÁC nhau → tất cả SKU xuất hiện (gộp items toàn HĐ active)."""
		from antmed_crm.api.antmed import customer as cust

		bv_multi = _mk_hospital("_T-TCAT-MULTI", "BV Tender Multi").name
		c1 = _mk_contract_status(
			"_T-TCAT-HD-M1",
			bv_multi,
			"Hiệu lực",
			[{"item": "_T-TCAT-M1", "item_name": "VT HĐ1", "uom": "Cái", "quota_qty": 100, "used_qty": 20}],
		).name
		c2 = _mk_contract_status(
			"_T-TCAT-HD-M2",
			bv_multi,
			"Sắp hết hạn",
			[{"item": "_T-TCAT-M2", "item_name": "VT HĐ2", "uom": "Hộp", "quota_qty": 100, "used_qty": 30}],
		).name
		res = cust.tender_catalog(bv_multi)
		codes = {it["item"] for it in res["items"]}
		self.assertEqual(codes, {"_T-TCAT-M1", "_T-TCAT-M2"}, msg=f"gộp sai: {codes}")
		# contract = 1 trong các HĐ active (docname, KHÔNG None khi có ≥1 active).
		self.assertIn(res["contract"], {c1, c2})

	def test_tender_catalog_get_only_whitelist(self):
		"""@whitelist(methods=['GET']) — chỉ GET, POST bị từ chối; callable từ FE."""
		from antmed_crm.api.antmed import customer as cust

		allowed = frappe.allowed_http_methods_for_whitelisted_func.get(cust.tender_catalog)
		self.assertIsNotNone(allowed, msg="endpoint không khai báo methods whitelist")
		self.assertIn("GET", allowed)
		self.assertNotIn("POST", allowed)
		self.assertIn(cust.tender_catalog, frappe.whitelisted)

	def test_tender_catalog_no_raw_sql(self):
		"""Hàm KHÔNG dùng frappe.db.sql (inspect source)."""
		from antmed_crm.api.antmed import customer as cust

		src = inspect.getsource(cust.tender_catalog)
		self.assertNotIn("frappe.db.sql", src)
		self.assertNotIn(".sql(", src)

	def test_tender_catalog_quota_no_n_plus_1(self):
		"""Quota dùng 1 get_all theo parent IN names dù nhiều HĐ active (spy count)."""
		from antmed_crm.api.antmed import customer as cust

		bv_nn = _mk_hospital("_T-TCAT-NN", "BV Tender NplusOne").name
		for no, code in (("_T-TCAT-NN-1", "_T-TCAT-NN-S1"), ("_T-TCAT-NN-2", "_T-TCAT-NN-S2")):
			_mk_contract_status(
				no,
				bv_nn,
				"Hiệu lực",
				[{"item": code, "item_name": code, "uom": "Cái", "quota_qty": 100, "used_qty": 20}],
			)
		orig_get_all = frappe.get_all
		calls = {"quota": 0}

		def _spy(doctype, *a, **kw):
			if doctype == "AntMed Quota Item":
				calls["quota"] += 1
			return orig_get_all(doctype, *a, **kw)

		frappe.get_all = _spy
		try:
			res = cust.tender_catalog(bv_nn)
		finally:
			frappe.get_all = orig_get_all
		self.assertEqual(calls["quota"], 1, msg=f"quota phải 1 get_all (batch), thực tế={calls['quota']}")
		self.assertEqual(len(res["items"]), 2, msg=f"items={res['items']}")

	def test_tender_catalog_zero_quota_no_zero_division(self):
		"""quota_qty == 0 → remaining_pct 0.0, chip danger (KHÔNG ZeroDivision)."""
		from antmed_crm.api.antmed import customer as cust

		bv_zero = _mk_hospital("_T-TCAT-ZERO", "BV Tender Zero").name
		_mk_contract_status(
			"_T-TCAT-HD-ZERO",
			bv_zero,
			"Hiệu lực",
			[
				{
					"item": "_T-TCAT-ZSKU",
					"item_name": "VT Zero Quota",
					"uom": "Cái",
					"quota_qty": 0,
					"used_qty": 0,
				}
			],
		)
		res = cust.tender_catalog(bv_zero)
		self.assertEqual(len(res["items"]), 1)
		it = res["items"][0]
		self.assertEqual(it["remaining_pct"], 0.0)
		self.assertEqual(it["quota_chip"], "danger")
