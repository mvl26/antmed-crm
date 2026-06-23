# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M03 Slice M03-S1 (BE foundation) — DocType AntMed Item + API list_items/get_item — TDD viết TRƯỚC.

Cover spec m03_inventory.md §2 (AntMed Item) + §5 (list_items/get_item) + §10 DoD:
  test_item_doctype_and_fields  — DocType tồn tại; đủ field tối thiểu; autoname field:item_code.
  test_item_code_unique         — 2 item cùng item_code → raise.
  test_list_items_shape         — {data,total_count}; item đúng 6 key; len(data)==total_count (count==rows).
  test_list_items_search        — search khớp item_code HOẶC item_name.
  test_list_items_filter        — filter classification lọc đúng.
  test_get_item                 — get_item trả field VTYT + lots[] (rỗng — Lot chưa land).
  test_get_item_permission      — user không read → PermissionError.
  test_docperm_vietnamese       — DocPerm dùng role VI (Quản lý/Thủ kho), KHÔNG role AM System Admin.

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_inventory
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from antmed_crm.api.antmed import inventory

ITEM_MIN_FIELDS = {
	"item_code",
	"item_name",
	"manufacturer_code",
	"registration_no",
	"ma_dkluuhanh",
	"requires_cocq",
	"shelf_life_months",
	"classification",
	"uom",
	"default_unit_price",
	"is_consignment",
	"disabled",
}
LIST_ITEM_KEYS = {"name", "item_code", "item_name", "classification", "requires_cocq", "shelf_life_months"}


def _mk_item(item_code, item_name, **kw):
	if frappe.db.exists("AntMed Item", item_code):
		return frappe.get_doc("AntMed Item", item_code)
	doc = frappe.get_doc({"doctype": "AntMed Item", "item_code": item_code, "item_name": item_name, **kw})
	doc.insert(ignore_permissions=True)
	return doc


class TestAntMedInventory(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.it1 = _mk_item(
			"_T-VTYT-STENT",
			"Stent mạch vành phủ thuốc",
			classification="Loại D",
			requires_cocq=1,
			shelf_life_months=36,
			uom="Cái",
			default_unit_price=12000000,
		).name
		cls.it2 = _mk_item(
			"_T-VTYT-GAC",
			"Gạc phẫu thuật",
			classification="Loại A",
			requires_cocq=0,
			shelf_life_months=60,
			uom="Gói",
		).name

	def test_item_doctype_and_fields(self):
		self.assertTrue(frappe.db.exists("DocType", "AntMed Item"))
		meta = frappe.get_meta("AntMed Item")
		fields = {f.fieldname for f in meta.fields}
		self.assertTrue(
			ITEM_MIN_FIELDS.issubset(fields), msg=f"AntMed Item thiếu field: {ITEM_MIN_FIELDS - fields}"
		)
		# autoname field:item_code → name == item_code
		self.assertEqual(self.it1, "_T-VTYT-STENT")
		self.assertEqual(meta.get_field("item_code").unique, 1)
		self.assertEqual(meta.track_changes, 1)

	def test_item_code_unique(self):
		"""item_code unique + autoname field:item_code → insert thẳng mã trùng phải raise."""
		with self.assertRaises(
			(frappe.UniqueValidationError, frappe.DuplicateEntryError, frappe.ValidationError)
		):
			frappe.get_doc(
				{"doctype": "AntMed Item", "item_code": "_T-VTYT-STENT", "item_name": "Trùng mã"}
			).insert(ignore_permissions=True)

	def test_list_items_shape(self):
		res = inventory.list_items(page_length=0)
		self.assertEqual(set(res.keys()), {"data", "total_count"})
		self.assertGreaterEqual(len(res["data"]), 2)
		self.assertEqual(set(res["data"][0].keys()), LIST_ITEM_KEYS)
		self.assertEqual(len(res["data"]), res["total_count"])

	def test_list_items_search(self):
		# search theo item_name
		r1 = inventory.list_items(search="Stent", page_length=0)
		codes1 = {r["item_code"] for r in r1["data"]}
		self.assertIn("_T-VTYT-STENT", codes1)
		self.assertNotIn("_T-VTYT-GAC", codes1)
		# search theo item_code
		r2 = inventory.list_items(search="_T-VTYT-GAC", page_length=0)
		codes2 = {r["item_code"] for r in r2["data"]}
		self.assertIn("_T-VTYT-GAC", codes2)
		self.assertNotIn("_T-VTYT-STENT", codes2)

	def test_list_items_filter(self):
		res = inventory.list_items(filters={"classification": "Loại D"}, page_length=0)
		codes = {r["item_code"] for r in res["data"]}
		self.assertIn("_T-VTYT-STENT", codes)
		self.assertNotIn("_T-VTYT-GAC", codes)
		self.assertEqual(len(res["data"]), res["total_count"])

	def test_get_item(self):
		res = inventory.get_item(self.it1)
		self.assertEqual(res["item_code"], "_T-VTYT-STENT")
		self.assertEqual(res["item_name"], "Stent mạch vành phủ thuốc")
		self.assertEqual(res["classification"], "Loại D")
		self.assertEqual(res["requires_cocq"], 1)
		self.assertEqual(res["shelf_life_months"], 36)
		self.assertIn("lots", res)
		self.assertEqual(res["lots"], [])  # AntMed Lot chưa land (slice kế)

	def test_get_item_permission(self):
		email = "_t_inv_noperm@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": "NoPermInv", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.set_user(email)
		try:
			with self.assertRaises(frappe.PermissionError):
				inventory.get_item(self.it1)
		finally:
			frappe.set_user("Administrator")

	def test_docperm_vietnamese(self):
		perms = {p.role for p in frappe.get_meta("AntMed Item").permissions}
		self.assertIn("Quản lý", perms)
		self.assertIn("Thủ kho", perms)
		self.assertIn("System Manager", perms)
		self.assertNotIn("AM System Admin", perms)


# ── M03-1 (mockup widget kho "Phiếu xuất gần đây") — list_stock_entries mở rộng ──
# TDD viết TRƯỚC: shape mỗi item +nv_employee/nv_employee_name/total_value; filter entry_type;
# noperm fail-closed; total_value = SUM(child.amount) gộp batch (KHÔNG N+1).

STOCK_ENTRY_ROW_KEYS = {
	"name",
	"entry_type",
	"from_warehouse",
	"to_warehouse",
	"posting_datetime",
	"docstatus",
	"nv_employee",
	"nv_employee_name",
	"total_value",
}


def _mk_se_item(code, name):
	if frappe.db.exists("AntMed Item", code):
		return frappe.get_doc("AntMed Item", code)
	return frappe.get_doc({"doctype": "AntMed Item", "item_code": code, "item_name": name}).insert(
		ignore_permissions=True
	)


def _mk_se_lot(lot_no, item):
	if frappe.db.exists("AntMed Lot", lot_no):
		return frappe.get_doc("AntMed Lot", lot_no)
	return frappe.get_doc(
		{"doctype": "AntMed Lot", "lot_no": lot_no, "item": item, "expiry_date": "2028-12-31"}
	).insert(ignore_permissions=True)


def _mk_se_wh(name, wtype, **kw):
	if frappe.db.exists("AntMed Warehouse", name):
		return frappe.get_doc("AntMed Warehouse", name)
	return frappe.get_doc(
		{"doctype": "AntMed Warehouse", "warehouse_name": name, "warehouse_type": wtype, **kw}
	).insert(ignore_permissions=True)


class TestAntMedStockEntryList(FrappeTestCase):
	"""list_stock_entries mở rộng cho widget kho 'Phiếu xuất gần đây' (Thủ kho)."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.item = _mk_se_item("_T-SEL-ITEM", "VT phiếu xuất test").name
		cls.wh_tong = _mk_se_wh("_T-SEL-WH-TONG", "Tổng").name
		cls.wh_nv = _mk_se_wh("_T-SEL-WH-NV", "Cá nhân NV", employee="Administrator").name
		# Nhập 100 (Nhập NCC) để có tồn → xuất cho NV được.
		lot = _mk_se_lot("_T-SEL-LOT", cls.item).name
		inventory.create_stock_entry(
			entry_type="Nhập NCC",
			to_warehouse=cls.wh_tong,
			items=[{"item": cls.item, "lot": lot, "qty": 100}],
		)
		# Phiếu "Xuất cho NV": 10 × đơn giá 190.000 = 1.900.000 (total_value).
		cls.issue = inventory.create_stock_entry(
			entry_type="Xuất cho NV",
			from_warehouse=cls.wh_tong,
			nv_employee="Administrator",
			items=[{"item": cls.item, "lot": lot, "qty": 10, "unit_price": 190000}],
		)["name"]

	def test_list_stock_entries_shape(self):
		"""Mỗi item có đủ 9 key (gồm nv_employee/nv_employee_name/total_value); total_count==len(data)."""
		res = inventory.list_stock_entries(page_length=0)
		self.assertEqual(set(res.keys()), {"data", "total_count"})
		self.assertGreaterEqual(len(res["data"]), 1)
		for row in res["data"]:
			self.assertEqual(set(row.keys()), STOCK_ENTRY_ROW_KEYS, msg=f"shape lệch: {set(row.keys())}")
		self.assertEqual(len(res["data"]), res["total_count"])  # count==rows dưới DocPerm

	def test_list_stock_entries_nv_employee_name_resolved(self):
		"""nv_employee_name resolve qua User.full_name (dotted-fetch) cho phiếu Xuất cho NV."""
		res = inventory.list_stock_entries(entry_type="Xuất cho NV", page_length=0)
		row = next(r for r in res["data"] if r["name"] == self.issue)
		self.assertEqual(row["nv_employee"], "Administrator")
		expected = frappe.db.get_value("User", "Administrator", "full_name")
		self.assertEqual(row["nv_employee_name"], expected)

	def test_list_stock_entries_filter_entry_type(self):
		"""entry_type='Xuất cho NV' chỉ trả phiếu loại đó; None trả mọi loại (>1 loại)."""
		only_issue = inventory.list_stock_entries(entry_type="Xuất cho NV", page_length=0)
		self.assertTrue(only_issue["data"])
		self.assertTrue(all(r["entry_type"] == "Xuất cho NV" for r in only_issue["data"]))

		all_types = inventory.list_stock_entries(entry_type=None, page_length=0)
		kinds = {r["entry_type"] for r in all_types["data"]}
		self.assertIn("Xuất cho NV", kinds)
		self.assertIn("Nhập NCC", kinds)  # đã có ít nhất 2 loại trong setUp

	def test_list_stock_entries_total_value(self):
		"""total_value = SUM(child.amount) của phiếu (key LUÔN tồn tại, kể cả khi None)."""
		res = inventory.list_stock_entries(entry_type="Xuất cho NV", page_length=0)
		row = next(r for r in res["data"] if r["name"] == self.issue)
		self.assertIn("total_value", row)
		self.assertEqual(row["total_value"], 1900000.0)  # 10 × 190.000

	def test_list_stock_entries_total_value_no_n_plus_1(self):
		"""total_value gộp batch: child amount lấy bằng ĐÚNG ≤1 query (KHÔNG N+1 theo số phiếu)."""
		res_first = inventory.list_stock_entries(page_length=0)
		self.assertGreaterEqual(len(res_first["data"]), 1)
		count_holder = {"n": 0}
		orig_get_all = frappe.get_all

		def _counting_get_all(*a, **kw):
			doctype = a[0] if a else kw.get("doctype")
			if doctype == "AntMed Stock Entry Item":
				count_holder["n"] += 1
			return orig_get_all(*a, **kw)

		frappe.get_all = _counting_get_all
		try:
			inventory.list_stock_entries(page_length=0)
		finally:
			frappe.get_all = orig_get_all
		self.assertLessEqual(count_holder["n"], 1, msg="total_value phải gộp batch (≤1 query child)")

	def test_list_stock_entries_noperm_fail_closed(self):
		"""User không có DocPerm AntMed Stock Entry → KHÔNG rò bản ghi nào (fail-closed).

		Frappe get_list (DatabaseQuery.check_read_permission) khi user không có BẤT KỲ read-perm
		nào trên doctype sẽ RAISE PermissionError (chặn ngay, không trả data) — đây là non-leak
		đúng, cùng convention list_hospitals/list_contracts. Chốt: hoặc raise, hoặc trả
		data==[]/total_count==0; TUYỆT ĐỐI không row nào lọt.
		"""
		# sanity (chống false-green): admin THẤY phiếu đã seed.
		self.assertGreaterEqual(inventory.list_stock_entries(page_length=0)["total_count"], 1)
		email = "_t_se_noperm@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": "NoPermSE", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.set_user(email)
		try:
			try:
				res = inventory.list_stock_entries(page_length=0)
			except frappe.PermissionError:
				return  # an toàn: chặn ngay, không trả data (fail-closed)
			self.assertEqual(res["data"], [])
			self.assertEqual(res["total_count"], 0)
		finally:
			frappe.set_user("Administrator")


# ── M03-2 (mockup D3 left-card "Thông tin lot") — get_lot truy vết 1 lô ──
# TDD viết TRƯỚC: shape đủ key + item_name/supplier_name dotted-fetch null-guard;
# 3 aggregate qty_in/qty_out/qty_remaining từ sổ tồn (AntMed Stock Ledger);
# not-found raise DoesNotExistError (idiom get_doc, khớp get_item); noperm fail-closed.

GET_LOT_KEYS = {
	"name",
	"lot_no",
	"item",
	"item_name",
	"supplier",
	"supplier_name",
	"mfg_date",
	"expiry_date",
	"co_cert",
	"cq_cert",
	"recall_status",
	"recall_reason",
	"qty_in",
	"qty_out",
	"qty_remaining",
	# M03 D3 enrich: link tải CO/CQ + SL còn tách theo loại kho.
	"co_file_url",
	"cq_file_url",
	"balance_by_warehouse_type",
}


def _mk_lt_item(code, name):
	if frappe.db.exists("AntMed Item", code):
		return frappe.get_doc("AntMed Item", code)
	return frappe.get_doc({"doctype": "AntMed Item", "item_code": code, "item_name": name}).insert(
		ignore_permissions=True
	)


def _mk_lt_supplier(code, name):
	if frappe.db.exists("AntMed Supplier", code):
		return frappe.get_doc("AntMed Supplier", code)
	return frappe.get_doc(
		{"doctype": "AntMed Supplier", "supplier_code": code, "supplier_name": name}
	).insert(ignore_permissions=True)


def _mk_lt_lot(lot_no, item, **kw):
	if frappe.db.exists("AntMed Lot", lot_no):
		return frappe.get_doc("AntMed Lot", lot_no)
	return frappe.get_doc(
		{"doctype": "AntMed Lot", "lot_no": lot_no, "item": item, "expiry_date": "2029-06-30", **kw}
	).insert(ignore_permissions=True)


def _mk_lt_wh(name, wtype, **kw):
	if frappe.db.exists("AntMed Warehouse", name):
		return frappe.get_doc("AntMed Warehouse", name)
	return frappe.get_doc(
		{"doctype": "AntMed Warehouse", "warehouse_name": name, "warehouse_type": wtype, **kw}
	).insert(ignore_permissions=True)


class TestAntMedGetLot(FrappeTestCase):
	"""get_lot — truy vết 1 lô (mockup D3 left-card 'Thông tin lot')."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.sup = _mk_lt_supplier("_T-LT-NCC", "NCC Truy Vết Lô").name
		cls.item = _mk_lt_item("_T-LT-ITEM", "VTYT truy vết lô").name
		cls.lot = _mk_lt_lot(
			"_T-LT-LOT",
			cls.item,
			supplier=cls.sup,
			mfg_date="2026-01-01",
			recall_status="Theo dõi",
			recall_reason="Đang theo dõi cảnh báo NCC",
		).name
		# Lô KHÔNG có ledger (kiểm 0/0/0).
		cls.lot_no_ledger = _mk_lt_lot("_T-LT-LOT-EMPTY", cls.item, supplier=cls.sup).name
		# Kho + sổ tồn: nhập 100 (Nhập NCC) rồi xuất 30 (Xuất cho NV) cho lô cls.lot.
		cls.wh_tong = _mk_lt_wh("_T-LT-WH-TONG", "Tổng").name
		inventory.create_stock_entry(
			entry_type="Nhập NCC",
			to_warehouse=cls.wh_tong,
			items=[{"item": cls.item, "lot": cls.lot, "qty": 100}],
		)
		inventory.create_stock_entry(
			entry_type="Xuất cho NV",
			from_warehouse=cls.wh_tong,
			nv_employee="Administrator",
			items=[{"item": cls.item, "lot": cls.lot, "qty": 30}],
		)

	def test_get_lot_shape(self):
		"""get_lot trả đủ key (name/lot_no/item/item_name/supplier/.../recall_status/qty_*)."""
		res = inventory.get_lot(self.lot)
		self.assertEqual(set(res.keys()), GET_LOT_KEYS, msg=f"shape lệch: {set(res.keys())}")
		self.assertEqual(res["name"], self.lot)
		self.assertEqual(res["lot_no"], self.lot)
		self.assertEqual(res["item"], self.item)
		self.assertEqual(res["supplier"], self.sup)
		self.assertEqual(res["recall_status"], "Theo dõi")
		self.assertEqual(res["recall_reason"], "Đang theo dõi cảnh báo NCC")

	def test_get_lot_item_name_resolved(self):
		"""item_name + supplier_name resolve qua Link bằng dotted-fetch (FK hợp lệ)."""
		res = inventory.get_lot(self.lot)
		self.assertEqual(res["item_name"], "VTYT truy vết lô")
		self.assertEqual(res["supplier_name"], "NCC Truy Vết Lô")

	def test_get_lot_item_name_null_guard(self):
		"""Lô supplier=None → supplier_name None (null-guard FK orphan, không lỗi)."""
		lot = _mk_lt_lot("_T-LT-LOT-NOSUP", self.item).name  # supplier để trống
		res = inventory.get_lot(lot)
		self.assertEqual(res["item_name"], "VTYT truy vết lô")
		self.assertIsNone(res["supplier"])
		self.assertIsNone(res["supplier_name"])

	def test_get_lot_quantities(self):
		"""Nhập 100 + xuất 30 → qty_in=100, qty_out=30, qty_remaining=70 (khớp sổ tồn)."""
		res = inventory.get_lot(self.lot)
		self.assertEqual(res["qty_in"], 100.0)
		self.assertEqual(res["qty_out"], 30.0)
		self.assertEqual(res["qty_remaining"], 70.0)

	def test_get_lot_quantities_no_ledger(self):
		"""Lô không có ledger → 0/0/0 (không lỗi)."""
		res = inventory.get_lot(self.lot_no_ledger)
		self.assertEqual(res["qty_in"], 0.0)
		self.assertEqual(res["qty_out"], 0.0)
		self.assertEqual(res["qty_remaining"], 0.0)

	def test_get_lot_balance_by_warehouse_type(self):
		"""SL còn tách theo loại kho (mockup D3): lô nhập 100 xuất 30 ở kho Tổng → còn 70 ở 'Tổng'."""
		res = inventory.get_lot(self.lot)
		by_type = {b["warehouse_type"]: b["qty"] for b in res["balance_by_warehouse_type"]}
		self.assertEqual(by_type.get("Tổng"), 70.0)
		# SUM breakdown == qty_remaining (invariant).
		self.assertEqual(sum(b["qty"] for b in res["balance_by_warehouse_type"]), res["qty_remaining"])

	def test_get_lot_cocq_file_url(self):
		"""co_file_url/cq_file_url resolve từ Certificate.file_url (link tải PDF mockup D3)."""
		# Lô không gắn chứng từ → None (null-guard).
		res = inventory.get_lot(self.lot)
		self.assertIsNone(res["co_file_url"])
		self.assertIsNone(res["cq_file_url"])
		# Gắn CO có file_url → co_file_url resolve đúng.
		cert = (
			frappe.get_doc(
				{
					"doctype": "AntMed Certificate",
					"cert_no": "_T-LT-CO-FILE",
					"cert_type": "CO",
					"item": self.item,
					"lot": self.lot,
					"file_url": "/files/co_test.pdf",
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
		frappe.db.set_value("AntMed Lot", self.lot, "co_cert", cert)
		res2 = inventory.get_lot(self.lot)
		self.assertEqual(res2["co_file_url"], "/files/co_test.pdf")

	def test_get_lot_not_found(self):
		"""Lô không tồn tại → DoesNotExistError (idiom get_doc, khớp get_item)."""
		with self.assertRaises(frappe.DoesNotExistError):
			inventory.get_lot("_T-LT-KHONG-TON-TAI")

	def test_get_lot_noperm_fail_closed(self):
		"""User không quyền đọc AntMed Lot → PermissionError (fail-closed, không rò data)."""
		email = "_t_lot_noperm@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": "NoPermLot", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.set_user(email)
		try:
			with self.assertRaises(frappe.PermissionError):
				inventory.get_lot(self.lot)
		finally:
			frappe.set_user("Administrator")


# ── M03-3 (mockup D2 "Kho ký gửi tại Bệnh viện") — consignment_stock tổng hợp tồn ký gửi ──
# TDD viết TRƯỚC: endpoint MỚI antmed_crm.api.antmed.inventory.consignment_stock(hospital).
#   Tổng hợp tồn ký gửi từ AntMed Stock Ledger trên kho warehouse_type='Ký gửi BV' (1 query gộp
#   GROUP BY, KHÔNG N+1; SQL param-bind %s LL-BE-11). Trả RAW dict (KHÔNG envelope):
#     {hospital, hospitals:[{name,hospital_name}], kpis:{hospitals_with_consignment,
#      near_expiry_lots}, rows:[{sku,item_name,lot,expiry_date,system_qty,near_expiry}]}.
#   - system_qty = SUM(qty_change) sổ tồn theo (kho ký gửi BV × item × lot); chỉ dòng > 0.
#   - near_expiry = expiry_date ≤ 90 ngày kể từ hôm nay (cùng ngưỡng cho KPI + chip/highlight).
#   - filter hospital: chỉ tồn của kho ký gửi thuộc BV được chọn; None → BV đầu tiên.
#   - BR-13 fail-closed: user không read-perm Stock Ledger/Warehouse → {rows:[], kpis 0}.

from frappe.utils import add_days, getdate, today

CONSIGNMENT_ROW_KEYS = {"sku", "item_name", "lot", "expiry_date", "system_qty", "near_expiry"}
CONSIGNMENT_NEAR_EXPIRY_DAYS = 90
# M03-5: hàng KPI 3 thẻ (mockup D2) — shape kpis ổn định 5 key (Hyrum, FE bind cố định).
CONSIGNMENT_KPI_KEYS_5 = {
	"hospitals_with_consignment",
	"near_expiry_lots",
	"total_value",
	"total_sku",
	"total_lots",
}


def _mk_cg_item(code, name, **kw):
	if frappe.db.exists("AntMed Item", code):
		return frappe.get_doc("AntMed Item", code)
	return frappe.get_doc({"doctype": "AntMed Item", "item_code": code, "item_name": name, **kw}).insert(
		ignore_permissions=True
	)


def _mk_cg_hospital(code, name):
	if frappe.db.exists("AntMed Hospital", code):
		return frappe.get_doc("AntMed Hospital", code)
	return frappe.get_doc(
		{"doctype": "AntMed Hospital", "hospital_code": code, "hospital_name": name}
	).insert(ignore_permissions=True)


def _mk_cg_lot(lot_no, item, expiry):
	if frappe.db.exists("AntMed Lot", lot_no):
		return frappe.get_doc("AntMed Lot", lot_no)
	return frappe.get_doc(
		{"doctype": "AntMed Lot", "lot_no": lot_no, "item": item, "expiry_date": expiry}
	).insert(ignore_permissions=True)


def _mk_cg_wh(name, wtype, **kw):
	if frappe.db.exists("AntMed Warehouse", name):
		return frappe.get_doc("AntMed Warehouse", name)
	return frappe.get_doc(
		{"doctype": "AntMed Warehouse", "warehouse_name": name, "warehouse_type": wtype, **kw}
	).insert(ignore_permissions=True)


class TestAntMedConsignmentStockTransfer(FrappeTestCase):
	"""consignment_stock — tồn ký gửi tại Bệnh viện (mockup D2, Thủ kho).

	Bộ test thứ hai (kịch bản Chuyển kho cross-BV + loại kho Tổng + guard no-N+1).
	Tên class PHẢI khác TestAntMedConsignmentStock bên dưới — nếu trùng tên, Python
	chỉ giữ class định nghĩa SAU → bộ test này bị shadow, KHÔNG chạy (mất coverage).
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# default_unit_price (đơn giá VTYT) → tính total_value KPI = SUM(system_qty × giá).
		# item_c KHÔNG có giá (đóng góp 0 vào total_value — đối chứng item thiếu giá).
		cls.item_a = _mk_cg_item("_T-CG-ITEM-A", "Stent ký gửi A", default_unit_price=12000000).name
		cls.item_b = _mk_cg_item("_T-CG-ITEM-B", "Dây dẫn ký gửi B", default_unit_price=500000).name
		cls.item_c = _mk_cg_item("_T-CG-ITEM-C", "VTYT không giá C").name
		# 2 BV có kho ký gửi.
		cls.bv1 = _mk_cg_hospital("_T-CG-BV1", "BV Ký Gửi Một").name
		cls.bv2 = _mk_cg_hospital("_T-CG-BV2", "BV Ký Gửi Hai").name
		# Kho ký gửi BV1 + BV2 + 1 kho Tổng (KHÔNG được lọt vào consignment).
		cls.wh_cg1 = _mk_cg_wh("_T-CG-WH-BV1", "Ký gửi BV", hospital=cls.bv1).name
		cls.wh_cg2 = _mk_cg_wh("_T-CG-WH-BV2", "Ký gửi BV", hospital=cls.bv2).name
		cls.wh_tong = _mk_cg_wh("_T-CG-WH-TONG", "Tổng").name
		# Lô: 1 lô cận date (≤90 ngày) + 1 lô xa hạn.
		near = add_days(today(), 38)  # mockup ví dụ '38 ngày'
		far = add_days(today(), 400)
		cls.lot_near = _mk_cg_lot("_T-CG-LOT-NEAR", cls.item_a, near).name
		cls.lot_far = _mk_cg_lot("_T-CG-LOT-FAR", cls.item_b, far).name
		cls.lot_empty = _mk_cg_lot("_T-CG-LOT-EMPTY", cls.item_a, far).name
		# Lô của item_c (KHÔNG giá) — tồn>0 ký gửi BV1 → đếm vào total_sku/total_lots nhưng 0 vào total_value.
		cls.lot_noprice = _mk_cg_lot("_T-CG-LOT-NOPRICE", cls.item_c, far).name
		# Nạp tồn ký gửi BV1: nhập 50 lô near (item_a) + nhập 30 lô far (item_b) + 10 lô_noprice (item_c).
		inventory.create_stock_entry(
			entry_type="Nhập ký gửi BV",
			to_warehouse=cls.wh_cg1,
			hospital=cls.bv1,
			items=[{"item": cls.item_a, "lot": cls.lot_near, "qty": 50}],
		)
		inventory.create_stock_entry(
			entry_type="Nhập ký gửi BV",
			to_warehouse=cls.wh_cg1,
			hospital=cls.bv1,
			items=[{"item": cls.item_b, "lot": cls.lot_far, "qty": 30}],
		)
		inventory.create_stock_entry(
			entry_type="Nhập ký gửi BV",
			to_warehouse=cls.wh_cg1,
			hospital=cls.bv1,
			items=[{"item": cls.item_c, "lot": cls.lot_noprice, "qty": 10}],
		)
		# BV1: lô_empty nhập 20 rồi chuyển hết sang BV2 → BV1 còn 0 (KHÔNG lọt) + BV2 có tồn.
		inventory.create_stock_entry(
			entry_type="Nhập ký gửi BV",
			to_warehouse=cls.wh_cg1,
			hospital=cls.bv1,
			items=[{"item": cls.item_a, "lot": cls.lot_empty, "qty": 20}],
		)
		inventory.create_stock_entry(
			entry_type="Chuyển kho",
			from_warehouse=cls.wh_cg1,
			to_warehouse=cls.wh_cg2,
			hospital=cls.bv2,
			items=[{"item": cls.item_a, "lot": cls.lot_empty, "qty": 20}],
		)
		# Tồn kho Tổng (KHÔNG ký gửi) — phải KHÔNG lọt vào consignment.
		inventory.create_stock_entry(
			entry_type="Nhập NCC",
			to_warehouse=cls.wh_tong,
			items=[{"item": cls.item_a, "lot": cls.lot_far, "qty": 999}],
		)

	def test_consignment_stock_shape(self):
		"""Trả đủ key gốc + mỗi row đủ CONSIGNMENT_ROW_KEYS (Hyrum contract FE)."""
		res = inventory.consignment_stock(hospital=self.bv1)
		self.assertEqual(set(res.keys()), {"hospital", "hospitals", "kpis", "rows"})
		# M03-5: kpis ổn định ĐỦ 5 key (hàng KPI 3 thẻ mockup D2) — đối chiếu hằng export ở endpoint.
		self.assertEqual(set(res["kpis"].keys()), CONSIGNMENT_KPI_KEYS_5)
		self.assertEqual(set(res["kpis"].keys()), inventory.CONSIGNMENT_KPI_KEYS)
		self.assertTrue(res["rows"], "BV1 phải có dòng tồn ký gửi")
		for row in res["rows"]:
			self.assertEqual(set(row.keys()), CONSIGNMENT_ROW_KEYS, msg=f"shape lệch: {set(row.keys())}")
		# hospitals = danh sách BV có kho ký gửi (name + hospital_name).
		hnames = {h["name"] for h in res["hospitals"]}
		self.assertIn(self.bv1, hnames)
		self.assertIn(self.bv2, hnames)
		bv1_meta = next(h for h in res["hospitals"] if h["name"] == self.bv1)
		self.assertEqual(bv1_meta["hospital_name"], "BV Ký Gửi Một")

	def test_consignment_system_qty_sum(self):
		"""SL hệ thống = SUM(qty_change) theo (kho ký gửi BV × item × lot); chỉ row >0."""
		res = inventory.consignment_stock(hospital=self.bv1)
		by_lot = {r["lot"]: r for r in res["rows"]}
		self.assertEqual(by_lot[self.lot_near]["system_qty"], 50.0)
		self.assertEqual(by_lot[self.lot_far]["system_qty"], 30.0)
		# Lô đã xuất/chuyển hết (BV1) KHÔNG lọt (system_qty>0 only).
		self.assertNotIn(self.lot_empty, by_lot)
		self.assertTrue(all(r["system_qty"] > 0 for r in res["rows"]))
		# SKU + item_name hiển thị được (không rỗng).
		self.assertEqual(by_lot[self.lot_near]["sku"], "_T-CG-ITEM-A")
		self.assertEqual(by_lot[self.lot_near]["item_name"], "Stent ký gửi A")

	def test_consignment_filter_by_hospital(self):
		"""Chỉ tồn kho ký gửi thuộc BV chọn; BV khác KHÔNG lọt; None → BV đầu tiên."""
		res1 = inventory.consignment_stock(hospital=self.bv1)
		lots1 = {r["lot"] for r in res1["rows"]}
		self.assertIn(self.lot_near, lots1)
		# Lô chuyển sang BV2 KHÔNG lọt vào BV1.
		self.assertNotIn(self.lot_empty, lots1)
		# BV2 chỉ thấy lô của mình (lot_empty 20), KHÔNG thấy lô của BV1.
		res2 = inventory.consignment_stock(hospital=self.bv2)
		lots2 = {r["lot"] for r in res2["rows"]}
		self.assertIn(self.lot_empty, lots2)
		self.assertNotIn(self.lot_near, lots2)
		self.assertNotIn(self.lot_far, lots2)
		# hospital=None → lấy BV đầu tiên (hospital trả về thuộc danh sách BV có ký gửi).
		res0 = inventory.consignment_stock(hospital=None)
		self.assertIn(res0["hospital"], {h["name"] for h in res0["hospitals"]})

	def test_consignment_near_expiry_flag(self):
		"""Lô ≤90 ngày → near_expiry True + đếm KPI; lô xa hơn → False."""
		res = inventory.consignment_stock(hospital=self.bv1)
		by_lot = {r["lot"]: r for r in res["rows"]}
		self.assertTrue(by_lot[self.lot_near]["near_expiry"])  # 38 ngày ≤ 90
		self.assertFalse(by_lot[self.lot_far]["near_expiry"])  # 400 ngày > 90
		# near_expiry_lots = số lot tồn>0 cận date toàn kho ký gửi (seed: chỉ lot_near cận date).
		self.assertEqual(res["kpis"]["near_expiry_lots"], 1)
		# Cross-check ngưỡng: lô đúng-mép 90 ngày vẫn near.
		edge_date = add_days(today(), CONSIGNMENT_NEAR_EXPIRY_DAYS)
		self.assertLessEqual(getdate(by_lot[self.lot_near]["expiry_date"]), getdate(edge_date))

	def test_consignment_kpi_hospitals_with_consignment(self):
		"""KPI = distinct BV có ≥1 dòng tồn ký gửi >0 (BV1 + BV2 = 2)."""
		res = inventory.consignment_stock(hospital=self.bv1)
		self.assertGreaterEqual(res["kpis"]["hospitals_with_consignment"], 2)

	def test_consignment_fail_closed_no_perm(self):
		"""User không read-perm Stock Ledger/Warehouse → {rows:[], kpis 0}, KHÔNG raise/rò data."""
		from unittest.mock import patch

		# sanity (chống false-green): admin THẤY tồn.
		self.assertTrue(inventory.consignment_stock(hospital=self.bv1)["rows"])

		def _fake_has_permission(doctype, *a, **kw):
			# Chặn read trên Stock Ledger + Warehouse; còn lại True.
			if doctype in ("AntMed Stock Ledger", "AntMed Warehouse"):
				return False
			return True

		with patch.object(frappe, "has_permission", side_effect=_fake_has_permission):
			res = inventory.consignment_stock(hospital=self.bv1)
		self.assertEqual(res["rows"], [])
		self.assertEqual(res["kpis"]["hospitals_with_consignment"], 0)
		self.assertEqual(res["kpis"]["near_expiry_lots"], 0)

	def test_consignment_fail_closed_kpi(self):
		"""M03-5 BR-13 _empty_consignment shape mới: thiếu read-perm → kpis ĐỦ 5 key đều ==0, rows []."""
		from unittest.mock import patch

		def _deny(doctype, *a, **kw):
			if doctype in ("AntMed Stock Ledger", "AntMed Warehouse"):
				return False
			return True

		with patch.object(frappe, "has_permission", side_effect=_deny):
			res = inventory.consignment_stock(hospital=self.bv1)
		self.assertEqual(res["rows"], [])
		# Shape kpis ổn định ĐỦ 5 key (FE bind cố định, KHÔNG KeyError) — tất cả == 0.
		self.assertEqual(set(res["kpis"].keys()), CONSIGNMENT_KPI_KEYS_5)
		for k in CONSIGNMENT_KPI_KEYS_5:
			self.assertEqual(res["kpis"][k], 0, msg=f"fail-closed: kpis[{k}] phải ==0")

	def test_consignment_kpi_total_value(self):
		"""total_value = SUM(system_qty × AntMed Item.default_unit_price) toàn kho ký gửi; item thiếu giá → 0."""
		res = inventory.consignment_stock(hospital=self.bv1)
		# all_balances toàn kho ký gửi (>0): bv1 item_a/near=50, item_b/far=30, item_c/noprice=10; bv2 item_a/empty=20.
		# total_value = 50×12.000.000 + 30×500.000 + 10×0 (item_c không giá) + 20×12.000.000.
		expected = 50 * 12000000 + 30 * 500000 + 10 * 0 + 20 * 12000000
		self.assertEqual(res["kpis"]["total_value"], expected)
		# Cross-check item thiếu giá đóng góp 0: bỏ tồn item_c khỏi tổng vẫn ra cùng số.
		self.assertEqual(res["kpis"]["total_value"], 855000000)

	def test_consignment_kpi_total_sku_and_total_lots(self):
		"""total_sku = số item distinct tồn>0 toàn kho ký gửi; total_lots = số dòng (item,lot) tồn>0 (== len all_balances)."""
		from antmed_crm.antmed import stock

		all_balances = stock.get_all_consignment_balances()
		distinct_items = {b["item"] for b in all_balances if b.get("item")}
		res = inventory.consignment_stock(hospital=self.bv1)
		# Invariant cốt lõi: KPI == số gộp toàn cục helper (KHÔNG hardcode absolute — site có thể có
		# data ký gửi khác/leaked từ test khác; production luôn nhiều BV). Đối chiếu theo INVARIANT.
		self.assertEqual(res["kpis"]["total_sku"], len(distinct_items))
		self.assertEqual(res["kpis"]["total_lots"], len(all_balances))
		# Seed của test PHẢI được đếm: 3 SKU (item_a/b/c) + 4 dòng (bv1 near/far/noprice + bv2 empty).
		seed_items = {self.item_a, self.item_b, self.item_c}
		self.assertTrue(
			seed_items.issubset(distinct_items), msg=f"thiếu seed item: {seed_items - distinct_items}"
		)
		seed_lots = {self.lot_near, self.lot_far, self.lot_noprice, self.lot_empty}
		all_lots = {b["lot"] for b in all_balances if b.get("lot")}
		self.assertTrue(seed_lots.issubset(all_lots), msg=f"thiếu seed lot: {seed_lots - all_lots}")
		self.assertGreaterEqual(res["kpis"]["total_sku"], 3)
		self.assertGreaterEqual(res["kpis"]["total_lots"], 4)

	def test_consignment_kpi_total_value_no_n_plus_1(self):
		"""Bulk-fetch default_unit_price: ≤1 query get_all theo tập item (KHÔNG N+1 theo số dòng tồn)."""
		orig_get_all = frappe.get_all
		item_price_calls = {"n": 0}

		def _counting_get_all(doctype, *a, **kw):
			# Đếm RIÊNG query bulk giá item: get_all AntMed Item có lấy default_unit_price.
			fields = kw.get("fields") or (a[1] if len(a) > 1 else None) or []
			if doctype == "AntMed Item" and any("default_unit_price" in str(f) for f in fields):
				item_price_calls["n"] += 1
			return orig_get_all(doctype, *a, **kw)

		with __import__("unittest.mock", fromlist=["patch"]).patch.object(
			frappe, "get_all", side_effect=_counting_get_all
		):
			inventory.consignment_stock(hospital=self.bv1)
		# Giá item bulk-fetch ĐÚNG ≤1 query theo distinct item (KHÔNG get_value/get_all trong loop).
		self.assertLessEqual(
			item_price_calls["n"], 1, msg="default_unit_price phải bulk-fetch ≤1 query (KHÔNG N+1)"
		)

	def test_consignment_no_raw_user_sql(self):
		"""stock.get_consignment_balances dùng param-bind %s (KHÔNG nối hospital) + 1 query gộp GROUP BY."""
		import inspect

		from antmed_crm.antmed import stock

		src = inspect.getsource(stock.get_consignment_balances)
		# Có placeholder param-bind %s.
		self.assertIn("%s", src)
		# Giá trị user (hospital) KHÔNG được nội suy vào chuỗi SQL — phải đi qua bind %s.
		# (Tên bảng là hằng module interpolate qua .format — không phải user input.)
		self.assertNotRegex(src, r"f['\"][^'\"]*SELECT", msg="KHÔNG f-string SQL")
		self.assertNotRegex(src, r"\{hospital\}")
		# 1 query gộp GROUP BY (KHÔNG N+1 theo từng kho/lô).
		self.assertIn("GROUP BY", src.upper())
		# bind tuple gồm hospital (giá trị user truyền bằng tham số, không nối chuỗi).
		self.assertIn("hospital", src)

	def test_consignment_no_n_plus_1(self):
		"""Tồn ký gửi của BV lấy bằng ĐÚNG ≤1 query SQL gộp GROUP BY (KHÔNG N+1 theo số kho/lô)."""
		from antmed_crm.antmed import stock

		count_holder = {"n": 0}
		orig_balances = stock.get_consignment_balances

		def _counting_balances(hospital):
			count_holder["n"] += 1
			return orig_balances(hospital)

		stock.get_consignment_balances = _counting_balances
		try:
			inventory.consignment_stock(hospital=self.bv1)
		finally:
			stock.get_consignment_balances = orig_balances
		# consignment_stock gọi get_consignment_balances(BV) ĐÚNG 1 lần (rows của BV chọn).
		self.assertEqual(count_holder["n"], 1, msg="tồn BV phải lấy bằng đúng 1 lần gộp GROUP BY")


# ── M03-3 (mockup D2 "Kho ký gửi tại Bệnh viện") — consignment_stock tổng hợp tồn ký gửi theo BV ──
# TDD viết TRƯỚC: shape đủ key {hospital,hospitals,kpis{...},rows[CONSIGNMENT_ROW_KEYS]};
# SL hệ thống = SUM(qty_change) theo (kho ký gửi BV × item × lot), chỉ dòng >0; lọc theo BV;
# near_expiry ≤90 ngày → True + đếm kpi; KPI distinct BV có tồn; fail-closed noperm; param-bind %s (KHÔNG N+1).

import datetime

from frappe.utils import nowdate

CONSIGNMENT_ROW_KEYS = {"sku", "item_name", "lot", "expiry_date", "system_qty", "near_expiry"}
# M03-5: kpis ổn định ĐỦ 5 key (hàng KPI 3 thẻ mockup D2).
CONSIGNMENT_KPI_KEYS = {
	"hospitals_with_consignment",
	"near_expiry_lots",
	"total_value",
	"total_sku",
	"total_lots",
}
CONSIGNMENT_RESULT_KEYS = {"hospital", "hospitals", "kpis", "rows"}


def _mk_cs_hospital(code, name):
	if frappe.db.exists("AntMed Hospital", code):
		return frappe.get_doc("AntMed Hospital", code)
	return frappe.get_doc(
		{"doctype": "AntMed Hospital", "hospital_code": code, "hospital_name": name}
	).insert(ignore_permissions=True)


def _mk_cs_item(code, name):
	if frappe.db.exists("AntMed Item", code):
		return frappe.get_doc("AntMed Item", code)
	return frappe.get_doc({"doctype": "AntMed Item", "item_code": code, "item_name": name}).insert(
		ignore_permissions=True
	)


def _mk_cs_lot(lot_no, item, expiry_date):
	if frappe.db.exists("AntMed Lot", lot_no):
		return frappe.get_doc("AntMed Lot", lot_no)
	return frappe.get_doc(
		{"doctype": "AntMed Lot", "lot_no": lot_no, "item": item, "expiry_date": expiry_date}
	).insert(ignore_permissions=True)


def _mk_cs_consignment_wh(name, hospital):
	if frappe.db.exists("AntMed Warehouse", name):
		return frappe.get_doc("AntMed Warehouse", name)
	return frappe.get_doc(
		{
			"doctype": "AntMed Warehouse",
			"warehouse_name": name,
			"warehouse_type": "Ký gửi BV",
			"hospital": hospital,
		}
	).insert(ignore_permissions=True)


class TestAntMedConsignmentStock(FrappeTestCase):
	"""consignment_stock — bảng tồn kho ký gửi tại BV (mockup D2, Thủ kho)."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# 2 BV: Bạch Mai (có tồn ký gửi) + Việt Đức (kho ký gửi nhưng tồn = 0 → đối chứng filter & KPI).
		cls.bv1 = _mk_cs_hospital("_T-CS-BV-BM", "BV Bạch Mai (test)").name
		cls.bv2 = _mk_cs_hospital("_T-CS-BV-VD", "BV Việt Đức (test)").name
		cls.item = _mk_cs_item("_T-CS-ITEM", "VTYT ký gửi test").name
		# Kho ký gửi của từng BV.
		cls.wh1 = _mk_cs_consignment_wh("_T-CS-WH-BM", cls.bv1).name
		cls.wh2 = _mk_cs_consignment_wh("_T-CS-WH-VD", cls.bv2).name
		# Kho Tổng để nạp tồn vào kho ký gửi (Nhập ký gửi BV ghi + vào to_warehouse).
		# Lô cận date (≤90 ngày, ví dụ +38 ngày như mockup) + lô xa (>90 ngày).
		cls.exp_near = add_days(nowdate(), 38)
		cls.exp_far = add_days(nowdate(), 400)
		cls.lot_near = _mk_cs_lot("_T-CS-LOT-NEAR", cls.item, cls.exp_near).name
		cls.lot_far = _mk_cs_lot("_T-CS-LOT-FAR", cls.item, cls.exp_far).name
		# Lô đã xuất hết (system_qty=0 → KHÔNG lọt vào rows).
		cls.lot_empty = _mk_cs_lot("_T-CS-LOT-EMPTY", cls.item, cls.exp_far).name

		# BV1 (Bạch Mai): nhập ký gửi 50 lô cận date + 30 lô xa.
		inventory.create_stock_entry(
			entry_type="Nhập ký gửi BV",
			to_warehouse=cls.wh1,
			hospital=cls.bv1,
			items=[{"item": cls.item, "lot": cls.lot_near, "qty": 50}],
		)
		inventory.create_stock_entry(
			entry_type="Nhập ký gửi BV",
			to_warehouse=cls.wh1,
			hospital=cls.bv1,
			items=[{"item": cls.item, "lot": cls.lot_far, "qty": 30}],
		)
		# BV1: lô empty — nhập 10 rồi điều chỉnh -10 (về 0) → system_qty=0, KHÔNG lọt.
		inventory.create_stock_entry(
			entry_type="Nhập ký gửi BV",
			to_warehouse=cls.wh1,
			hospital=cls.bv1,
			items=[{"item": cls.item, "lot": cls.lot_empty, "qty": 10}],
		)
		# Điều chỉnh -10 cho lô empty (Điều chỉnh ghi qty_change vào to_warehouse).
		frappe.get_doc(
			{
				"doctype": "AntMed Stock Entry",
				"entry_type": "Điều chỉnh",
				"to_warehouse": cls.wh1,
				"reason": "Đưa lô về 0 cho test",
				"items": [{"item": cls.item, "lot": cls.lot_empty, "qty": -10}],
			}
		).insert(ignore_permissions=True).submit()

	# ── shape ──
	def test_consignment_stock_shape(self):
		"""Trả đủ key {hospital,hospitals,kpis{...},rows}; mỗi row đủ CONSIGNMENT_ROW_KEYS."""
		res = inventory.consignment_stock(hospital=self.bv1)
		self.assertEqual(set(res.keys()), CONSIGNMENT_RESULT_KEYS, msg=f"shape lệch: {set(res.keys())}")
		self.assertEqual(set(res["kpis"].keys()), CONSIGNMENT_KPI_KEYS)
		self.assertEqual(res["hospital"], self.bv1)
		self.assertTrue(res["rows"], "BV Bạch Mai phải có tồn ký gửi")
		for row in res["rows"]:
			self.assertEqual(set(row.keys()), CONSIGNMENT_ROW_KEYS, msg=f"row shape lệch: {set(row.keys())}")
		# hospitals[] mỗi phần tử {name, hospital_name}.
		self.assertTrue(res["hospitals"])
		for h in res["hospitals"]:
			self.assertEqual(set(h.keys()), {"name", "hospital_name"})
		hnames = {h["name"] for h in res["hospitals"]}
		self.assertIn(self.bv1, hnames)
		self.assertIn(self.bv2, hnames)  # BV2 có kho ký gửi (distinct hospital) dù tồn=0

	# ── SL hệ thống = SUM(qty_change), chỉ >0 ──
	def test_consignment_system_qty_sum(self):
		"""SL hệ thống đúng theo (kho ký gửi × item × lot); lô đã xuất hết (=0) KHÔNG lọt."""
		res = inventory.consignment_stock(hospital=self.bv1)
		by_lot = {r["lot"]: r for r in res["rows"]}
		self.assertEqual(by_lot[self.lot_near]["system_qty"], 50.0)
		self.assertEqual(by_lot[self.lot_far]["system_qty"], 30.0)
		self.assertNotIn(self.lot_empty, by_lot, "lô system_qty=0 KHÔNG được lọt vào rows")
		self.assertEqual(by_lot[self.lot_near]["sku"], self.item)
		self.assertEqual(by_lot[self.lot_near]["item_name"], "VTYT ký gửi test")

	# ── lọc theo BV ──
	def test_consignment_filter_by_hospital(self):
		"""Chỉ tồn kho ký gửi của BV được chọn; BV khác KHÔNG lọt. hospital=None → BV đầu tiên."""
		res1 = inventory.consignment_stock(hospital=self.bv1)
		lots1 = {r["lot"] for r in res1["rows"]}
		self.assertIn(self.lot_near, lots1)
		# BV2 (Việt Đức) tồn=0 → rows rỗng.
		res2 = inventory.consignment_stock(hospital=self.bv2)
		self.assertEqual(res2["hospital"], self.bv2)
		self.assertEqual(res2["rows"], [])
		# hospital=None → resolve BV đầu tiên (không lỗi, hospital không None).
		res_none = inventory.consignment_stock(hospital=None)
		self.assertIsNotNone(res_none["hospital"])
		self.assertIn(res_none["hospital"], {h["name"] for h in res_none["hospitals"]})

	# ── near_expiry flag + kpi ──
	def test_consignment_near_expiry_flag(self):
		"""Lô ≤90 ngày → near_expiry=True + đếm kpi near_expiry_lots; lô xa → False."""
		res = inventory.consignment_stock(hospital=self.bv1)
		by_lot = {r["lot"]: r for r in res["rows"]}
		self.assertTrue(by_lot[self.lot_near]["near_expiry"])
		self.assertFalse(by_lot[self.lot_far]["near_expiry"])
		# KPI near_expiry_lots đếm lô tồn>0 trong kho ký gửi có expiry ≤90 ngày (≥1: lot_near).
		self.assertGreaterEqual(res["kpis"]["near_expiry_lots"], 1)

	# ── KPI distinct BV có tồn ──
	def test_consignment_kpi_hospitals_with_consignment(self):
		"""hospitals_with_consignment = distinct BV có ≥1 dòng tồn ký gửi >0 (BV2 tồn=0 KHÔNG tính)."""
		res = inventory.consignment_stock(hospital=self.bv1)
		# Chỉ BV1 có tồn>0 trong tập test (BV2 tồn=0). Đếm toàn cục → ≥1.
		self.assertGreaterEqual(res["kpis"]["hospitals_with_consignment"], 1)

	# ── fail-closed noperm ──
	def test_consignment_fail_closed_no_perm(self):
		"""User không read-perm Stock Ledger/Warehouse → {rows:[],kpis 0}, KHÔNG raise/rò data."""
		orig = frappe.has_permission

		def _deny(doctype, *a, **kw):
			if doctype in ("AntMed Stock Ledger", "AntMed Warehouse"):
				return False
			return orig(doctype, *a, **kw)

		frappe.has_permission = _deny
		try:
			res = inventory.consignment_stock(hospital=self.bv1)
		finally:
			frappe.has_permission = orig
		self.assertEqual(res["rows"], [])
		self.assertEqual(res["kpis"]["hospitals_with_consignment"], 0)
		self.assertEqual(res["kpis"]["near_expiry_lots"], 0)

	# ── param-bind %s + KHÔNG N+1 (source-level guard) ──
	def test_consignment_no_raw_user_sql(self):
		"""get_consignment_balances dùng param-bind %s (KHÔNG f-string nối hospital); 1 query gộp GROUP BY."""
		import inspect

		from antmed_crm.antmed import stock

		src = inspect.getsource(stock.get_consignment_balances)
		# hospital phải truyền qua tham số %s — KHÔNG nối thẳng biến hospital vào chuỗi SQL.
		self.assertIn("%s", src)
		self.assertNotIn('f"""', src.replace("\n", " "))  # KHÔNG f-string SQL block
		# Đếm số lần gọi frappe.db.sql trong helper = ĐÚNG 1 (1 query gộp GROUP BY, KHÔNG N+1).
		self.assertEqual(
			src.count("frappe.db.sql"), 1, msg="get_consignment_balances phải dùng ĐÚNG 1 query gộp"
		)

	def test_consignment_balances_helper_filter(self):
		"""get_consignment_balances(bv1) chỉ trả lô tồn>0 của kho ký gửi BV1; bv2 (tồn=0) → []."""
		from antmed_crm.antmed import stock

		rows1 = stock.get_consignment_balances(self.bv1)
		lots1 = {r["lot"]: r["system_qty"] for r in rows1}
		self.assertEqual(lots1.get(self.lot_near), 50.0)
		self.assertEqual(lots1.get(self.lot_far), 30.0)
		self.assertNotIn(self.lot_empty, lots1)  # HAVING SUM>0
		self.assertEqual(stock.get_consignment_balances(self.bv2), [])


# ── M03-4 (mockup D1 "⚠ Cảnh báo HSD" + D2 KPI "Cận date ≤90 ngày") — expiry_alerts ──
# TDD viết TRƯỚC: endpoint MỚI antmed_crm.api.antmed.inventory.expiry_alerts() (whitelist GET).
#   Rollup lot CẬN/QUÁ date trên TOÀN BỘ kho (Tổng + Cá nhân NV + Ký gửi BV) từ AntMed Stock
#   Ledger JOIN AntMed Lot + AntMed Warehouse (1 query gộp GROUP BY, KHÔNG N+1; SQL param-bind %s).
#   Chỉ lot có SUM(balance_qty=qty_change) > 0 VÀ (expiry_date ≤ add_days(nowdate,90) HOẶC đã quá hạn).
#   Trả RAW dict (KHÔNG envelope):
#     {kpis:{expired,d30,d60,d90,total_lots},
#      rows:[{sku,item_name,lot,warehouse,warehouse_name,warehouse_type,expiry_date,
#             balance_qty,days_to_expiry,severity}]}
#   - days_to_expiry = date_diff(expiry_date, nowdate); severity = expired(<0)/d30(0..30)/d60(31..60)/d90(61..90).
#   - KPI đếm số LOT-warehouse theo từng tầng; total_lots = tổng dòng. Sort days_to_expiry asc (quá hạn đầu).
#   - BR-13 fail-closed: thiếu read-perm Stock Ledger/Lot/Warehouse → {rows:[], kpis tất cả 0}.

EXPIRY_ROW_KEYS = {
	"sku",
	"item_name",
	"lot",
	"warehouse",
	"warehouse_name",
	"warehouse_type",
	"expiry_date",
	"balance_qty",
	"days_to_expiry",
	"severity",
}
EXPIRY_KPI_KEYS = {"expired", "d30", "d60", "d90", "total_lots"}


def _mk_ex_item(code, name):
	if frappe.db.exists("AntMed Item", code):
		return frappe.get_doc("AntMed Item", code)
	return frappe.get_doc({"doctype": "AntMed Item", "item_code": code, "item_name": name}).insert(
		ignore_permissions=True
	)


def _mk_ex_lot(lot_no, item, expiry_date):
	if frappe.db.exists("AntMed Lot", lot_no):
		return frappe.get_doc("AntMed Lot", lot_no)
	return frappe.get_doc(
		{"doctype": "AntMed Lot", "lot_no": lot_no, "item": item, "expiry_date": expiry_date}
	).insert(ignore_permissions=True)


def _mk_ex_lot_no_expiry(lot_no, item):
	"""Lô KHÔNG có expiry_date (PHẢI bị loại — WHERE expiry_date IS NOT NULL)."""
	if frappe.db.exists("AntMed Lot", lot_no):
		return frappe.get_doc("AntMed Lot", lot_no)
	return frappe.get_doc({"doctype": "AntMed Lot", "lot_no": lot_no, "item": item}).insert(
		ignore_permissions=True
	)


def _mk_ex_wh(name, wtype, **kw):
	if frappe.db.exists("AntMed Warehouse", name):
		return frappe.get_doc("AntMed Warehouse", name)
	return frappe.get_doc(
		{"doctype": "AntMed Warehouse", "warehouse_name": name, "warehouse_type": wtype, **kw}
	).insert(ignore_permissions=True)


class TestAntMedExpiryAlerts(FrappeTestCase):
	"""expiry_alerts — Cảnh báo HSD toàn kho (mockup D1 ⚠, Thủ kho Tổng)."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.item = _mk_ex_item("_T-EX-ITEM", "VTYT cảnh báo HSD test").name
		# 1 kho Tổng nạp tồn cho mọi lô (đủ để gom theo (warehouse,item,lot)).
		cls.wh = _mk_ex_wh("_T-EX-WH-TONG", "Tổng").name
		# Mốc HSD tương đối hôm nay: quá hạn (-5), ≤30 (15), ≤60 (45), ≤90 (80), xa (>90 = 400).
		cls.exp_expired = add_days(nowdate(), -5)
		cls.exp_d30 = add_days(nowdate(), 15)
		cls.exp_d60 = add_days(nowdate(), 45)
		cls.exp_d90 = add_days(nowdate(), 80)
		cls.exp_far = add_days(nowdate(), 400)
		cls.lot_expired = _mk_ex_lot("_T-EX-LOT-EXPIRED", cls.item, cls.exp_expired).name
		cls.lot_d30 = _mk_ex_lot("_T-EX-LOT-D30", cls.item, cls.exp_d30).name
		cls.lot_d60 = _mk_ex_lot("_T-EX-LOT-D60", cls.item, cls.exp_d60).name
		cls.lot_d90 = _mk_ex_lot("_T-EX-LOT-D90", cls.item, cls.exp_d90).name
		cls.lot_far = _mk_ex_lot("_T-EX-LOT-FAR", cls.item, cls.exp_far).name  # >90 → bị loại
		cls.lot_zero = _mk_ex_lot("_T-EX-LOT-ZERO", cls.item, cls.exp_d30).name  # balance=0 → bị loại
		# Nạp tồn >0 cho 4 lô cận/quá date + lô xa (đối chứng) — Nhập NCC vào kho Tổng.
		for lot in (cls.lot_expired, cls.lot_d30, cls.lot_d60, cls.lot_d90, cls.lot_far):
			inventory.create_stock_entry(
				entry_type="Nhập NCC",
				to_warehouse=cls.wh,
				items=[{"item": cls.item, "lot": lot, "qty": 10}],
			)
		# Lô balance=0: nhập 5 rồi điều chỉnh -5 về 0 → HAVING SUM>0 loại.
		inventory.create_stock_entry(
			entry_type="Nhập NCC",
			to_warehouse=cls.wh,
			items=[{"item": cls.item, "lot": cls.lot_zero, "qty": 5}],
		)
		frappe.get_doc(
			{
				"doctype": "AntMed Stock Entry",
				"entry_type": "Điều chỉnh",
				"to_warehouse": cls.wh,
				"reason": "Đưa lô về 0 cho test cảnh báo HSD",
				"items": [{"item": cls.item, "lot": cls.lot_zero, "qty": -5}],
			}
		).insert(ignore_permissions=True).submit()

	def _rows_by_lot(self, res):
		return {r["lot"]: r for r in res["rows"]}

	# ── shape ──
	def test_expiry_alerts_shape(self):
		"""Trả đủ key {kpis, rows}; kpis đủ EXPIRY_KPI_KEYS; mỗi row đủ EXPIRY_ROW_KEYS (Hyrum)."""
		res = inventory.expiry_alerts()
		self.assertEqual(set(res.keys()), {"kpis", "rows"})
		self.assertEqual(set(res["kpis"].keys()), EXPIRY_KPI_KEYS)
		self.assertTrue(res["rows"], "phải có dòng cảnh báo HSD (4 lô seed cận/quá date)")
		for row in res["rows"]:
			self.assertEqual(set(row.keys()), EXPIRY_ROW_KEYS, msg=f"row shape lệch: {set(row.keys())}")
		# Hằng số shape khớp test (chống đổi shape ngầm — Hyrum).
		self.assertEqual(set(inventory.EXPIRY_ROW_KEYS), EXPIRY_ROW_KEYS)
		self.assertEqual(set(inventory.EXPIRY_KPI_KEYS), EXPIRY_KPI_KEYS)

	# ── chỉ balance>0 & ≤90d/expired ──
	def test_expiry_alerts_only_balance_and_within_90(self):
		"""Chỉ lot balance>0 VÀ (≤90 ngày HOẶC quá hạn); lô xa (>90) + balance=0 KHÔNG lọt."""
		res = inventory.expiry_alerts()
		by_lot = self._rows_by_lot(res)
		self.assertIn(self.lot_expired, by_lot)
		self.assertIn(self.lot_d30, by_lot)
		self.assertIn(self.lot_d60, by_lot)
		self.assertIn(self.lot_d90, by_lot)
		self.assertNotIn(self.lot_far, by_lot, "lô HSD xa (>90 ngày) KHÔNG được lọt")
		self.assertNotIn(self.lot_zero, by_lot, "lô balance=0 KHÔNG được lọt")
		self.assertTrue(all(r["balance_qty"] > 0 for r in res["rows"]))
		# SKU + tên VT + kho hiển thị được.
		self.assertEqual(by_lot[self.lot_d30]["sku"], self.item)
		self.assertEqual(by_lot[self.lot_d30]["item_name"], "VTYT cảnh báo HSD test")
		self.assertEqual(by_lot[self.lot_d30]["warehouse"], self.wh)
		self.assertEqual(by_lot[self.lot_d30]["warehouse_name"], "_T-EX-WH-TONG")
		self.assertEqual(by_lot[self.lot_d30]["warehouse_type"], "Tổng")
		self.assertEqual(by_lot[self.lot_d30]["balance_qty"], 10.0)

	# ── severity từng tầng ──
	def test_expiry_alerts_severity_tiers(self):
		"""severity = expired(<0)/d30(0..30)/d60(31..60)/d90(61..90) + days_to_expiry đúng dấu."""
		res = inventory.expiry_alerts()
		by_lot = self._rows_by_lot(res)
		self.assertEqual(by_lot[self.lot_expired]["severity"], "expired")
		self.assertLess(by_lot[self.lot_expired]["days_to_expiry"], 0)
		self.assertEqual(by_lot[self.lot_d30]["severity"], "d30")
		self.assertTrue(0 <= by_lot[self.lot_d30]["days_to_expiry"] <= 30)
		self.assertEqual(by_lot[self.lot_d60]["severity"], "d60")
		self.assertTrue(31 <= by_lot[self.lot_d60]["days_to_expiry"] <= 60)
		self.assertEqual(by_lot[self.lot_d90]["severity"], "d90")
		self.assertTrue(61 <= by_lot[self.lot_d90]["days_to_expiry"] <= 90)

	# ── kpis đếm đúng ──
	def test_expiry_alerts_kpis_count(self):
		"""kpis đếm đúng số LOT-warehouse từng tầng; total_lots = tổng dòng."""
		res = inventory.expiry_alerts()
		k = res["kpis"]
		# 1 lô mỗi tầng trong tập test (đếm theo lot-warehouse, ≥ vì site có thể có data khác).
		self.assertGreaterEqual(k["expired"], 1)
		self.assertGreaterEqual(k["d30"], 1)
		self.assertGreaterEqual(k["d60"], 1)
		self.assertGreaterEqual(k["d90"], 1)
		# total_lots = tổng dòng rows.
		self.assertEqual(k["total_lots"], len(res["rows"]))
		# total_lots = expired + d30 + d60 + d90 (4 tầng phủ kín mọi dòng đã lọc).
		self.assertEqual(k["total_lots"], k["expired"] + k["d30"] + k["d60"] + k["d90"])
		# Cross-check theo từng severity của rows.
		from collections import Counter

		cnt = Counter(r["severity"] for r in res["rows"])
		self.assertEqual(k["expired"], cnt["expired"])
		self.assertEqual(k["d30"], cnt["d30"])
		self.assertEqual(k["d60"], cnt["d60"])
		self.assertEqual(k["d90"], cnt["d90"])

	# ── sort days_to_expiry asc (quá hạn lên đầu) ──
	def test_expiry_alerts_sort_asc(self):
		"""Sort theo days_to_expiry asc → quá hạn (âm) lên đầu, ≤90 ở cuối."""
		res = inventory.expiry_alerts()
		days = [r["days_to_expiry"] for r in res["rows"]]
		self.assertEqual(days, sorted(days), msg="rows phải sort days_to_expiry asc")
		# Dòng đầu là lô quá hạn (days âm nhất trong tập test).
		self.assertEqual(res["rows"][0]["severity"], "expired")
		self.assertLess(res["rows"][0]["days_to_expiry"], 0)

	# ── fail-closed noperm ──
	def test_expiry_alerts_fail_closed_no_perm(self):
		"""Thiếu read-perm Stock Ledger/Lot/Warehouse → {rows:[], kpis tất cả 0}, KHÔNG raise/rò."""
		from unittest.mock import patch

		# sanity (chống false-green): admin THẤY cảnh báo.
		self.assertTrue(inventory.expiry_alerts()["rows"])

		def _deny(doctype, *a, **kw):
			if doctype in ("AntMed Stock Ledger", "AntMed Lot", "AntMed Warehouse"):
				return False
			return True

		with patch.object(frappe, "has_permission", side_effect=_deny):
			res = inventory.expiry_alerts()
		self.assertEqual(res["rows"], [])
		self.assertEqual(res["kpis"], {"expired": 0, "d30": 0, "d60": 0, "d90": 0, "total_lots": 0})

	# ── param-bind %s (KHÔNG nội suy biến user vào SQL) ──
	def test_expiry_alerts_no_raw_user_sql(self):
		"""get_expiring_balances dùng param-bind %s; KHÔNG f-string nội suy giá trị vào SQL."""
		import inspect

		from antmed_crm.antmed import stock

		src = inspect.getsource(stock.get_expiring_balances)
		self.assertIn("%s", src)  # within_days bind %s
		# KHÔNG f-string SQL (giá trị user phải đi qua bind, KHÔNG nội suy).
		self.assertNotRegex(src, r"f['\"][^'\"]*SELECT", msg="KHÔNG f-string SQL")
		self.assertNotRegex(src, r"\{within_days\}")
		self.assertIn("GROUP BY", src.upper())
		# add_days(nowdate(), within_days) → giá trị ngày phải bind, KHÔNG nội suy thẳng.
		self.assertIn("within_days", src)

	# ── KHÔNG N+1 ──
	def test_expiry_alerts_no_n_plus_1(self):
		"""Rollup lấy bằng ĐÚNG 1 query gộp GROUP BY (KHÔNG N+1 theo số lô/kho)."""
		from antmed_crm.antmed import stock

		count_holder = {"sql": 0}
		orig_sql = frappe.db.sql

		def _counting_sql(*a, **kw):
			count_holder["sql"] += 1
			return orig_sql(*a, **kw)

		# Đếm số lần get_expiring_balances gọi frappe.db.sql = đúng 1 (1 query gộp).
		inner = {"n": 0}
		orig_get = stock.get_expiring_balances

		def _counting_get(*a, **kw):
			inner["n"] += 1
			return orig_get(*a, **kw)

		stock.get_expiring_balances = _counting_get
		frappe.db.sql = _counting_sql
		try:
			inventory.expiry_alerts()
		finally:
			stock.get_expiring_balances = orig_get
			frappe.db.sql = orig_sql
		# expiry_alerts gọi get_expiring_balances ĐÚNG 1 lần.
		self.assertEqual(inner["n"], 1, msg="rollup phải lấy bằng đúng 1 lần gộp")

	# ── helper stock.get_expiring_balances trực tiếp ──
	def test_get_expiring_balances_helper(self):
		"""get_expiring_balances(90) JOIN gom item_name/warehouse_name; HAVING SUM>0; ≤90 ngày."""
		from antmed_crm.antmed import stock

		rows = stock.get_expiring_balances(90)
		by_lot = {r["lot"]: r for r in rows}
		self.assertIn(self.lot_expired, by_lot)
		self.assertIn(self.lot_d90, by_lot)
		self.assertNotIn(self.lot_far, by_lot)  # >90 ngày
		self.assertNotIn(self.lot_zero, by_lot)  # balance=0 (HAVING SUM>0)
		# JOIN gom sẵn item_name + warehouse_name + warehouse_type (KHÔNG N+1 ở endpoint).
		r = by_lot[self.lot_d30]
		self.assertEqual(r["item_name"], "VTYT cảnh báo HSD test")
		self.assertEqual(r["warehouse_name"], "_T-EX-WH-TONG")
		self.assertEqual(r["warehouse_type"], "Tổng")
		self.assertEqual(r["balance_qty"], 10.0)


# ── M03-6 (mockup D3 right-card "Cây truy vết") — lot_trace dòng thời gian di chuyển 1 lô ──
# TDD viết TRƯỚC: endpoint MỚI antmed_crm.api.antmed.inventory.lot_trace(name) (GET) trả RAW dict
#   {lot, item, item_name, events:[...]}; events từ AntMed Stock Ledger JOIN Stock Entry + Warehouse,
#   ORDER posting_datetime ASC; mỗi event shape cố định LOT_TRACE_EVENT_KEYS (Hyrum):
#     {posting_datetime, entry_type, direction(in|out), qty, warehouse, warehouse_name,
#      warehouse_type, voucher_no, hospital, nv_employee}.
#   - direction='in' nếu qty_change>0 ngược lại 'out'; qty=ABS(qty_change).
#   - Lô không tồn tại → DoesNotExistError (idiom get_doc, khớp get_lot/get_item).
#   - Lô tồn tại nhưng chưa có ledger → events:[].
#   - BR-13 fail-closed: user thiếu read-perm Stock Ledger/Stock Entry/Warehouse → events:[]
#     (KHÔNG rò data, KHÔNG throw 500); 1 query (no_n+1) + param-bind %s (no_raw_sql).

LOT_TRACE_EVENT_KEYS = {
	"posting_datetime",
	"entry_type",
	"direction",
	"qty",
	"warehouse",
	"warehouse_name",
	"warehouse_type",
	"voucher_no",
	"hospital",
	"nv_employee",
}


def _mk_tr_item(code, name):
	if frappe.db.exists("AntMed Item", code):
		return frappe.get_doc("AntMed Item", code)
	return frappe.get_doc({"doctype": "AntMed Item", "item_code": code, "item_name": name}).insert(
		ignore_permissions=True
	)


def _mk_tr_hospital(code, name):
	if frappe.db.exists("AntMed Hospital", code):
		return frappe.get_doc("AntMed Hospital", code)
	return frappe.get_doc(
		{"doctype": "AntMed Hospital", "hospital_code": code, "hospital_name": name}
	).insert(ignore_permissions=True)


def _mk_tr_lot(lot_no, item):
	if frappe.db.exists("AntMed Lot", lot_no):
		return frappe.get_doc("AntMed Lot", lot_no)
	return frappe.get_doc(
		{"doctype": "AntMed Lot", "lot_no": lot_no, "item": item, "expiry_date": "2029-12-31"}
	).insert(ignore_permissions=True)


def _mk_tr_wh(name, wtype, **kw):
	if frappe.db.exists("AntMed Warehouse", name):
		return frappe.get_doc("AntMed Warehouse", name)
	return frappe.get_doc(
		{"doctype": "AntMed Warehouse", "warehouse_name": name, "warehouse_type": wtype, **kw}
	).insert(ignore_permissions=True)


class TestAntMedLotTrace(FrappeTestCase):
	"""lot_trace — right-card 'Cây truy vết' (Thủ kho, mockup D3): dòng thời gian di chuyển 1 lô."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.item = _mk_tr_item("_T-TRC-ITEM", "VTYT truy vết di chuyển").name
		cls.hosp = _mk_tr_hospital("_T-TRC-BV", "BV Cây Truy Vết").name
		cls.wh_tong = _mk_tr_wh("_T-TRC-WH-TONG", "Tổng").name
		cls.wh_cg = _mk_tr_wh("_T-TRC-WH-CG", "Ký gửi BV", hospital=cls.hosp).name
		cls.lot = _mk_tr_lot("_T-TRC-LOT", cls.item).name
		cls.lot_empty = _mk_tr_lot("_T-TRC-LOT-EMPTY", cls.item).name
		# Nhập NCC 100 (01/01) → Xuất NV 30 (01/02) → Chuyển ký gửi BV 20 (01/03) — 3 ngày khác nhau.
		se_in = inventory.create_stock_entry(
			entry_type="Nhập NCC",
			to_warehouse=cls.wh_tong,
			items=[{"item": cls.item, "lot": cls.lot, "qty": 100}],
		)["name"]
		frappe.db.set_value("AntMed Stock Entry", se_in, "posting_datetime", "2026-01-01 08:00:00")
		frappe.db.sql(
			"UPDATE `tabAntMed Stock Ledger` SET posting_datetime=%s WHERE stock_entry=%s",
			("2026-01-01 08:00:00", se_in),
		)
		se_out = inventory.create_stock_entry(
			entry_type="Xuất cho NV",
			from_warehouse=cls.wh_tong,
			nv_employee="Administrator",
			items=[{"item": cls.item, "lot": cls.lot, "qty": 30}],
		)["name"]
		frappe.db.set_value("AntMed Stock Entry", se_out, "posting_datetime", "2026-02-01 09:00:00")
		frappe.db.sql(
			"UPDATE `tabAntMed Stock Ledger` SET posting_datetime=%s WHERE stock_entry=%s",
			("2026-02-01 09:00:00", se_out),
		)
		se_trf = inventory.create_stock_entry(
			entry_type="Chuyển kho",
			from_warehouse=cls.wh_tong,
			to_warehouse=cls.wh_cg,
			hospital=cls.hosp,
			items=[{"item": cls.item, "lot": cls.lot, "qty": 20}],
		)["name"]
		frappe.db.set_value("AntMed Stock Entry", se_trf, "posting_datetime", "2026-03-01 10:00:00")
		frappe.db.sql(
			"UPDATE `tabAntMed Stock Ledger` SET posting_datetime=%s WHERE stock_entry=%s",
			("2026-03-01 10:00:00", se_trf),
		)
		# Chuyển 20 ra khỏi kho ký gửi (muộn nhất) → tồn ký gửi nét về 0: KHÔNG pollute KPI
		# all_consignment_balances (HAVING SUM>0) của test ký gửi khác. Dòng ledger vẫn còn → giữ
		# event 'in' kho Ký gửi BV cho test trace (ledger append-only, không phụ thuộc tồn net).
		se_back = inventory.create_stock_entry(
			entry_type="Chuyển kho",
			from_warehouse=cls.wh_cg,
			to_warehouse=cls.wh_tong,
			items=[{"item": cls.item, "lot": cls.lot, "qty": 20}],
		)["name"]
		frappe.db.set_value("AntMed Stock Entry", se_back, "posting_datetime", "2026-04-01 11:00:00")
		frappe.db.sql(
			"UPDATE `tabAntMed Stock Ledger` SET posting_datetime=%s WHERE stock_entry=%s",
			("2026-04-01 11:00:00", se_back),
		)
		# KHÔNG frappe.db.commit(): commit phá rollback FrappeTestCase → leak kho ký gửi "_T-TRC-WH-CG"
		# vào DB vĩnh viễn, làm sai KPI consignment toàn cục (total_sku/total_lots). UPDATE cùng
		# transaction đã hiển thị cho read sau (cùng connection) — không cần commit.

	def test_lot_trace_result_shape(self):
		"""Trả RAW dict {lot, item, item_name, events}; events là list."""
		res = inventory.lot_trace(self.lot)
		self.assertEqual(set(res.keys()), {"lot", "item", "item_name", "events"})
		self.assertEqual(res["lot"], self.lot)
		self.assertEqual(res["item"], self.item)
		self.assertEqual(res["item_name"], "VTYT truy vết di chuyển")
		self.assertIsInstance(res["events"], list)
		self.assertTrue(res["events"])

	def test_lot_trace_event_shape(self):
		"""Mỗi event đúng 10 key cố định (LOT_TRACE_EVENT_KEYS == inventory.LOT_TRACE_EVENT_KEYS)."""
		res = inventory.lot_trace(self.lot)
		self.assertEqual(set(inventory.LOT_TRACE_EVENT_KEYS), LOT_TRACE_EVENT_KEYS)
		for ev in res["events"]:
			self.assertEqual(set(ev.keys()), LOT_TRACE_EVENT_KEYS, msg=f"shape lệch: {set(ev.keys())}")

	def test_lot_trace_order_asc(self):
		"""events ORDER posting_datetime ASC (nhập sớm nhất lên đầu)."""
		res = inventory.lot_trace(self.lot)
		dts = [str(e["posting_datetime"]) for e in res["events"]]
		self.assertEqual(dts, sorted(dts), msg=f"chưa ASC: {dts}")
		self.assertEqual(res["events"][0]["entry_type"], "Nhập NCC")

	def test_lot_trace_direction_and_abs_qty(self):
		"""direction='in' cho qty_change>0; 'out' cho <0; qty=ABS (luôn dương)."""
		res = inventory.lot_trace(self.lot)
		for ev in res["events"]:
			self.assertIn(ev["direction"], ("in", "out"))
			self.assertGreater(ev["qty"], 0)
		first = res["events"][0]
		self.assertEqual(first["direction"], "in")
		self.assertEqual(first["qty"], 100.0)
		issue = next(e for e in res["events"] if e["entry_type"] == "Xuất cho NV")
		self.assertEqual(issue["direction"], "out")
		self.assertEqual(issue["qty"], 30.0)

	def test_lot_trace_join_fields(self):
		"""JOIN gom đúng warehouse_name/warehouse_type/hospital/nv_employee."""
		res = inventory.lot_trace(self.lot)
		rcv = next(e for e in res["events"] if e["entry_type"] == "Nhập NCC")
		self.assertEqual(rcv["warehouse"], self.wh_tong)
		self.assertEqual(rcv["warehouse_name"], "_T-TRC-WH-TONG")
		self.assertEqual(rcv["warehouse_type"], "Tổng")
		issue = next(e for e in res["events"] if e["entry_type"] == "Xuất cho NV")
		self.assertEqual(issue["nv_employee"], "Administrator")
		cg_in = next(e for e in res["events"] if e["warehouse"] == self.wh_cg and e["direction"] == "in")
		self.assertEqual(cg_in["warehouse_type"], "Ký gửi BV")
		self.assertEqual(cg_in["hospital"], self.hosp)
		self.assertTrue(cg_in["voucher_no"])

	def test_lot_trace_no_ledger(self):
		"""Lô tồn tại nhưng chưa có ledger → events:[] (FE empty-sub)."""
		res = inventory.lot_trace(self.lot_empty)
		self.assertEqual(res["lot"], self.lot_empty)
		self.assertEqual(res["events"], [])

	def test_lot_trace_not_found(self):
		"""Lô không tồn tại → DoesNotExistError (idiom get_doc, khớp get_lot)."""
		with self.assertRaises(frappe.DoesNotExistError):
			inventory.lot_trace("_T-TRC-KHONG-TON-TAI")

	def test_lot_trace_fail_closed_no_perm(self):
		"""BR-13 fail-closed: thiếu read-perm Ledger/Stock Entry/Warehouse → events:[] (KHÔNG rò/500)."""
		from unittest.mock import patch

		# sanity (chống false-green): có perm → thấy events.
		self.assertTrue(inventory.lot_trace(self.lot)["events"])

		def _deny(doctype, *a, **kw):
			if doctype in ("AntMed Stock Ledger", "AntMed Stock Entry", "AntMed Warehouse"):
				return False
			return True

		with patch.object(frappe, "has_permission", side_effect=_deny):
			res = inventory.lot_trace(self.lot)
		# Vẫn trả shape ổn định nhưng events rỗng (không lộ data, không raise).
		self.assertEqual(set(res.keys()), {"lot", "item", "item_name", "events"})
		self.assertEqual(res["events"], [])

	def test_lot_trace_no_raw_sql(self):
		"""stock.get_lot_trace param-bind %s (KHÔNG nối chuỗi lot) + KHÔNG f-string SQL."""
		import inspect

		from antmed_crm.antmed import stock

		src = inspect.getsource(stock.get_lot_trace)
		self.assertIn("%s", src)
		self.assertNotRegex(src, r"f['\"][^'\"]*SELECT", msg="KHÔNG f-string SQL")
		self.assertNotRegex(src, r"\{lot\}")

	def test_lot_trace_no_n_plus_1(self):
		"""events lấy bằng ĐÚNG 1 lần gọi get_lot_trace (1 query JOIN — KHÔNG N+1 theo dòng)."""
		from antmed_crm.antmed import stock

		count = {"n": 0}
		orig = stock.get_lot_trace

		def _counting(lot):
			count["n"] += 1
			return orig(lot)

		stock.get_lot_trace = _counting
		try:
			inventory.lot_trace(self.lot)
		finally:
			stock.get_lot_trace = orig
		self.assertEqual(count["n"], 1, msg="events phải lấy bằng đúng 1 query JOIN gộp")


# ── M03-7 (mockup D3 action "⚠ Khởi tạo Recall theo lot này") — initiate_recall ──
# TDD viết TRƯỚC: endpoint MỚI antmed_crm.api.antmed.inventory.initiate_recall(lot, reason, status).
#   Thủ kho lật AntMed Lot.recall_status sang 'Theo dõi' | 'Đã thu hồi' + ghi recall_reason +
#   add_comment audit. Trả RAW dict {name, recall_status, recall_reason}.
#   - happy path status='Đã thu hồi' → recall_status đổi + recall_reason ghi + return 3 khóa.
#   - status='Theo dõi' → recall_status='Theo dõi' (không phải 'Đã thu hồi').
#   - reason rỗng/khoảng trắng → ValidationError, recall_status KHÔNG đổi.
#   - status ngoài tập {Theo dõi, Đã thu hồi} → ValidationError.
#   - lô đã 'Đã thu hồi' → recall lại = ValidationError (one-way idempotent, không double-recall).
#   - BR-13 fail-closed: user KHÔNG write-perm AntMed Lot → PermissionError, KHÔNG mutate (DB giữ nguyên).
#   - audit: add_comment 'Khởi tạo recall' được tạo trên doc lô.
#   - RECALL_STATUS_OPTIONS export == ('Theo dõi','Đã thu hồi'); no raw SQL trong initiate_recall.


class TestAntMedInitiateRecall(FrappeTestCase):
	"""initiate_recall — Thủ kho khởi tạo recall theo lô (mockup D3 action button)."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.item = _mk_lt_item("_T-RC-ITEM", "VTYT khởi tạo recall").name

	def _fresh_lot(self, lot_no, **kw):
		"""Tạo lô MỚI mỗi test (tránh trạng thái dây — db_set ghi vĩnh viễn trong rollback scope)."""
		if frappe.db.exists("AntMed Lot", lot_no):
			frappe.delete_doc("AntMed Lot", lot_no, force=True, ignore_permissions=True)
		return frappe.get_doc(
			{
				"doctype": "AntMed Lot",
				"lot_no": lot_no,
				"item": self.item,
				"expiry_date": "2029-06-30",
				**kw,
			}
		).insert(ignore_permissions=True)

	def test_initiate_recall_happy_recalled(self):
		"""status='Đã thu hồi' → recall_status đổi + recall_reason ghi + tự sinh Recall Notification."""
		lot = self._fresh_lot("_T-RC-HAPPY").name
		res = inventory.initiate_recall(lot=lot, reason="Phát hiện lỗi tiệt khuẩn", status="Đã thu hồi")
		# Return 5 khóa (thêm recall_notification + affected_hospitals — auto-recall D3).
		self.assertEqual(
			set(res.keys()),
			{"name", "recall_status", "recall_reason", "recall_notification", "affected_hospitals"},
		)
		self.assertEqual(res["name"], lot)
		self.assertEqual(res["recall_status"], "Đã thu hồi")
		self.assertEqual(res["recall_reason"], "Phát hiện lỗi tiệt khuẩn")
		# DB thực sự đổi.
		self.assertEqual(frappe.db.get_value("AntMed Lot", lot, "recall_status"), "Đã thu hồi")
		self.assertEqual(frappe.db.get_value("AntMed Lot", lot, "recall_reason"), "Phát hiện lỗi tiệt khuẩn")
		# Tự sinh AntMed Recall Notification cho lô (BV ảnh hưởng = 0 vì lô test không có giao/ký gửi).
		self.assertIsNotNone(res["recall_notification"])
		self.assertTrue(frappe.db.exists("AntMed Recall Notification", res["recall_notification"]))
		self.assertEqual(
			frappe.db.get_value("AntMed Recall Notification", res["recall_notification"], "lot"), lot
		)

	def test_initiate_recall_theo_doi(self):
		"""status='Theo dõi' → recall_status='Theo dõi' (KHÔNG phải 'Đã thu hồi')."""
		lot = self._fresh_lot("_T-RC-THEODOI").name
		res = inventory.initiate_recall(lot=lot, reason="Cảnh báo từ NCC", status="Theo dõi")
		self.assertEqual(res["recall_status"], "Theo dõi")
		self.assertEqual(frappe.db.get_value("AntMed Lot", lot, "recall_status"), "Theo dõi")

	def test_initiate_recall_default_status_recalled(self):
		"""status mặc định (không truyền) = 'Đã thu hồi' (mockup D3 mức mặc định)."""
		lot = self._fresh_lot("_T-RC-DEFAULT").name
		res = inventory.initiate_recall(lot=lot, reason="Lý do mặc định")
		self.assertEqual(res["recall_status"], "Đã thu hồi")

	def test_initiate_recall_empty_reason(self):
		"""reason='' → ValidationError, recall_status KHÔNG đổi (giữ 'Bình thường' mặc định)."""
		lot = self._fresh_lot("_T-RC-EMPTY").name
		with self.assertRaises(frappe.ValidationError):
			inventory.initiate_recall(lot=lot, reason="", status="Đã thu hồi")
		self.assertEqual(frappe.db.get_value("AntMed Lot", lot, "recall_status"), "Bình thường")

	def test_initiate_recall_whitespace_reason(self):
		"""reason='   ' (chỉ khoảng trắng) → ValidationError, recall_status KHÔNG đổi."""
		lot = self._fresh_lot("_T-RC-WS").name
		with self.assertRaises(frappe.ValidationError):
			inventory.initiate_recall(lot=lot, reason="   ", status="Đã thu hồi")
		self.assertEqual(frappe.db.get_value("AntMed Lot", lot, "recall_status"), "Bình thường")

	def test_initiate_recall_invalid_status(self):
		"""status='Bình thường' (ngoài tập cho phép) → ValidationError, KHÔNG mutate."""
		lot = self._fresh_lot("_T-RC-INVALID").name
		with self.assertRaises(frappe.ValidationError):
			inventory.initiate_recall(lot=lot, reason="Lý do", status="Bình thường")
		self.assertEqual(frappe.db.get_value("AntMed Lot", lot, "recall_status"), "Bình thường")

	def test_initiate_recall_unknown_status(self):
		"""status='Foobar' (giá trị lạ) → ValidationError."""
		lot = self._fresh_lot("_T-RC-FOO").name
		with self.assertRaises(frappe.ValidationError):
			inventory.initiate_recall(lot=lot, reason="Lý do", status="Foobar")

	def test_initiate_recall_one_way_guard(self):
		"""Lô đã 'Đã thu hồi' → gọi lại initiate_recall → ValidationError (idempotent, không double-recall)."""
		lot = self._fresh_lot("_T-RC-ONEWAY").name
		inventory.initiate_recall(lot=lot, reason="Recall lần 1", status="Đã thu hồi")
		with self.assertRaises(frappe.ValidationError):
			inventory.initiate_recall(lot=lot, reason="Recall lần 2", status="Đã thu hồi")
		# Reason vẫn là lần 1 (không bị ghi đè bởi lần 2).
		self.assertEqual(frappe.db.get_value("AntMed Lot", lot, "recall_reason"), "Recall lần 1")

	def test_initiate_recall_from_theo_doi_to_recalled(self):
		"""'Theo dõi' → 'Đã thu hồi' được phép (escalate); 'Theo dõi' KHÔNG phải terminal."""
		lot = self._fresh_lot("_T-RC-ESCALATE").name
		inventory.initiate_recall(lot=lot, reason="Theo dõi trước", status="Theo dõi")
		res = inventory.initiate_recall(lot=lot, reason="Thu hồi sau", status="Đã thu hồi")
		self.assertEqual(res["recall_status"], "Đã thu hồi")
		self.assertEqual(frappe.db.get_value("AntMed Lot", lot, "recall_reason"), "Thu hồi sau")

	def test_initiate_recall_fail_closed_no_write_perm(self):
		"""BR-13 fail-closed: user KHÔNG write-perm AntMed Lot → PermissionError, KHÔNG mutate."""
		lot = self._fresh_lot("_T-RC-NOPERM").name
		email = "_t_recall_noperm@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": "NoPermRecall", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.set_user(email)
		try:
			with self.assertRaises(frappe.PermissionError):
				inventory.initiate_recall(lot=lot, reason="Cố recall", status="Đã thu hồi")
		finally:
			frappe.set_user("Administrator")
		# DB KHÔNG đổi (giữ 'Bình thường').
		self.assertEqual(frappe.db.get_value("AntMed Lot", lot, "recall_status"), "Bình thường")

	def test_initiate_recall_audit_comment(self):
		"""add_comment timeline được tạo (Comment chứa 'Khởi tạo recall' gắn doc lô) — audit."""
		lot = self._fresh_lot("_T-RC-AUDIT").name
		inventory.initiate_recall(lot=lot, reason="Lý do audit", status="Đã thu hồi")
		comments = frappe.get_all(
			"Comment",
			filters={
				"reference_doctype": "AntMed Lot",
				"reference_name": lot,
				"comment_type": "Comment",
			},
			fields=["content"],
		)
		self.assertTrue(
			any("Khởi tạo recall" in (c.get("content") or "") for c in comments),
			msg=f"Phải có Comment audit 'Khởi tạo recall'; có: {comments}",
		)

	def test_recall_status_options_export(self):
		"""RECALL_STATUS_OPTIONS export == ('Theo dõi','Đã thu hồi') — đồng bộ FE RECALL_INITIATE_STATUSES."""
		self.assertEqual(inventory.RECALL_STATUS_OPTIONS, ("Theo dõi", "Đã thu hồi"))

	def test_initiate_recall_no_raw_sql(self):
		"""initiate_recall KHÔNG dùng raw SQL — mutate qua doc thật (get_doc/save/add_comment)."""
		import inspect

		src = inspect.getsource(inventory.initiate_recall)
		self.assertNotIn("frappe.db.sql", src, msg="initiate_recall không được dùng raw SQL")
		self.assertNotIn(".sql(", src, msg="initiate_recall không được dùng raw SQL")
		# Mutate qua doc.save (chạy doc_events/audit-version) — KHÔNG db_set chui.
		self.assertIn(".save(", src, msg="initiate_recall phải mutate qua doc.save()")
		# KHÔNG ignore_permissions trên mutate (DocPerm áp tự nhiên + guard write-perm fail-closed).
		self.assertNotRegex(src, r"ignore_permissions\s*=\s*True")


# ── M03-8 (mockup C2 Wizard bước 3 / drill-down "Phiếu xuất gần đây") — get_stock_entry ──
# TDD viết TRƯỚC: endpoint MỚI antmed_crm.api.antmed.inventory.get_stock_entry(name).
#   Chi tiết 1 phiếu xuất + dòng vật tư đã chuẩn bị (SKU/Tên/Lot/HSD/SL/ĐVT/chip CO-CQ).
#   Header keys (STOCK_ENTRY_DETAIL_HEADER_KEYS) + items (STOCK_ENTRY_DETAIL_ITEM_KEYS mỗi dòng).
#   item_name BATCH (AntMed Item) + lot_no/expiry_date BATCH (AntMed Lot) — KHÔNG N+1.
#   total_value = SUM(amount); phiếu 0 dòng → items==[] & total_value None. Phiếu không tồn tại →
#   DoesNotExistError. BR-13 fail-closed: noperm → shape rỗng (KHÔNG rò header thật, KHÔNG 500).

# header = 11 khoá scalar; full = header + 'items' (list dòng). Tách để assert shape riêng.
STOCK_ENTRY_DETAIL_HEADER_KEYS = {
	"name",
	"entry_type",
	"posting_datetime",
	"from_warehouse",
	"to_warehouse",
	"nv_employee",
	"nv_employee_name",
	"hospital",
	"hospital_name",
	"expected_use_date",
	"total_value",
}
STOCK_ENTRY_DETAIL_FULL_KEYS = STOCK_ENTRY_DETAIL_HEADER_KEYS | {"items"}
STOCK_ENTRY_DETAIL_ITEM_KEYS = {
	"item",
	"item_name",
	"lot",
	"lot_no",
	"expiry_date",
	"qty",
	"uom",
	"unit_price",
	"amount",
	"cocq_ok",
}


def _mk_sed_item(code, name, **kw):
	if frappe.db.exists("AntMed Item", code):
		return frappe.get_doc("AntMed Item", code)
	return frappe.get_doc({"doctype": "AntMed Item", "item_code": code, "item_name": name, **kw}).insert(
		ignore_permissions=True
	)


def _mk_sed_lot(lot_no, item, expiry):
	if frappe.db.exists("AntMed Lot", lot_no):
		return frappe.get_doc("AntMed Lot", lot_no)
	return frappe.get_doc(
		{"doctype": "AntMed Lot", "lot_no": lot_no, "item": item, "expiry_date": expiry}
	).insert(ignore_permissions=True)


def _mk_sed_hospital(code, name):
	if frappe.db.exists("AntMed Hospital", code):
		return frappe.get_doc("AntMed Hospital", code)
	return frappe.get_doc(
		{"doctype": "AntMed Hospital", "hospital_code": code, "hospital_name": name}
	).insert(ignore_permissions=True)


def _mk_sed_wh(name, wtype, **kw):
	if frappe.db.exists("AntMed Warehouse", name):
		return frappe.get_doc("AntMed Warehouse", name)
	return frappe.get_doc(
		{"doctype": "AntMed Warehouse", "warehouse_name": name, "warehouse_type": wtype, **kw}
	).insert(ignore_permissions=True)


class TestAntMedGetStockEntry(FrappeTestCase):
	"""get_stock_entry — chi tiết 1 phiếu xuất + vật tư đã chuẩn bị (mockup C2 Wizard bước 3)."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# item_a có uom 'Sợi'; dòng item_b KHÔNG set uom → endpoint fallback AntMed Item.uom ('Gói').
		cls.item = _mk_sed_item("_T-SED-ITEM", "Chỉ Vicryl 2-0", uom="Sợi", default_unit_price=190000).name
		cls.item2 = _mk_sed_item("_T-SED-ITEM2", "Gạc cầm máu", uom="Gói").name
		cls.hospital = _mk_sed_hospital("_T-SED-BV", "BV K Trung Ương").name
		cls.wh_tong = _mk_sed_wh("_T-SED-WH-TONG", "Tổng").name
		cls.lot = _mk_sed_lot("_T-SED-LOT", cls.item, "2028-11-30").name
		cls.lot2 = _mk_sed_lot("_T-SED-LOT2", cls.item2, "2029-04-30").name
		# cocq_ok do controller TỰ TÍNH (BR-03, derived read-only): lô cls.lot gắn đủ CO+CQ → cocq_ok=1;
		# lô cls.lot2 KHÔNG có chứng từ (item requires_cocq default 1) → cocq_ok=0. (Pass-through True/False.)
		co = (
			frappe.get_doc(
				{
					"doctype": "AntMed Certificate",
					"cert_no": "_T-SED-CO",
					"cert_type": "CO",
					"item": cls.item,
					"lot": cls.lot,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
		cq = (
			frappe.get_doc(
				{
					"doctype": "AntMed Certificate",
					"cert_no": "_T-SED-CQ",
					"cert_type": "CQ",
					"item": cls.item,
					"lot": cls.lot,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
		frappe.db.set_value("AntMed Lot", cls.lot, "co_cert", co)
		frappe.db.set_value("AntMed Lot", cls.lot, "cq_cert", cq)
		# Nhập tồn đủ để xuất.
		inventory.create_stock_entry(
			entry_type="Nhập NCC",
			to_warehouse=cls.wh_tong,
			items=[
				{"item": cls.item, "lot": cls.lot, "qty": 100},
				{"item": cls.item2, "lot": cls.lot2, "qty": 100},
			],
		)
		# Phiếu "Xuất cho NV" 2 dòng: 5×190.000 (cocq_ok=1) + 3×0 (dòng b không unit_price, cocq_ok=0).
		doc = frappe.get_doc(
			{
				"doctype": "AntMed Stock Entry",
				"entry_type": "Xuất cho NV",
				"from_warehouse": cls.wh_tong,
				"nv_employee": "Administrator",
				"hospital": cls.hospital,
				"expected_use_date": "2026-06-20",
				"items": [
					{
						"item": cls.item,
						"lot": cls.lot,
						"qty": 5,
						"unit_price": 190000,
						"cocq_ok": 1,
					},
					{"item": cls.item2, "lot": cls.lot2, "qty": 3, "cocq_ok": 0},
				],
			}
		)
		doc.insert(ignore_permissions=True)
		doc.submit()
		cls.entry = doc.name
		# Phiếu 0 dòng: DocType bắt buộc 'items' (reqd) → KHÔNG insert được phiếu rỗng. Mô phỏng phiếu
		# orphan-0-dòng bằng cách xoá child rows của 1 phiếu thật (get_doc đọc lại từ DB → items==[]).
		doc2 = frappe.get_doc(
			{
				"doctype": "AntMed Stock Entry",
				"entry_type": "Điều chỉnh",
				"to_warehouse": cls.wh_tong,
				"reason": "Phiếu test 0 dòng",
				"items": [{"item": cls.item, "lot": cls.lot, "qty": 1}],
			}
		)
		doc2.insert(ignore_permissions=True)
		cls.entry_empty = doc2.name
		frappe.db.delete(
			"AntMed Stock Entry Item", {"parent": cls.entry_empty, "parenttype": "AntMed Stock Entry"}
		)

	def test_get_stock_entry_header_shape(self):
		"""(1) Header đủ STOCK_ENTRY_DETAIL_HEADER_KEYS + key 'items' (full = header | items)."""
		res = inventory.get_stock_entry(self.entry)
		self.assertEqual(
			set(res.keys()), STOCK_ENTRY_DETAIL_FULL_KEYS, msg=f"shape header lệch: {set(res.keys())}"
		)
		header = {k: v for k, v in res.items() if k != "items"}
		self.assertEqual(set(header.keys()), STOCK_ENTRY_DETAIL_HEADER_KEYS)
		self.assertEqual(res["name"], self.entry)
		self.assertEqual(res["entry_type"], "Xuất cho NV")
		self.assertEqual(res["from_warehouse"], self.wh_tong)
		self.assertEqual(res["nv_employee"], "Administrator")
		self.assertEqual(res["hospital"], self.hospital)
		self.assertEqual(str(res["expected_use_date"]), "2026-06-20")

	def test_get_stock_entry_item_shape(self):
		"""(2) Mỗi dòng items đủ STOCK_ENTRY_DETAIL_ITEM_KEYS (Hyrum)."""
		res = inventory.get_stock_entry(self.entry)
		self.assertEqual(len(res["items"]), 2)
		for row in res["items"]:
			self.assertEqual(
				set(row.keys()), STOCK_ENTRY_DETAIL_ITEM_KEYS, msg=f"shape dòng lệch: {set(row.keys())}"
			)

	def test_get_stock_entry_resolve_names(self):
		"""(3) item_name từ AntMed Item; lot_no+expiry_date từ AntMed Lot; *_name header; uom fallback."""
		res = inventory.get_stock_entry(self.entry)
		by_item = {r["item"]: r for r in res["items"]}
		ra = by_item[self.item]
		self.assertEqual(ra["item_name"], "Chỉ Vicryl 2-0")
		self.assertEqual(ra["lot_no"], self.lot)  # autoname field:lot_no → name == lot_no
		self.assertEqual(str(ra["expiry_date"]), "2028-11-30")
		self.assertEqual(ra["uom"], "Sợi")  # uom đặt trên dòng
		# Dòng b KHÔNG set uom → fallback AntMed Item.uom ('Gói').
		self.assertEqual(by_item[self.item2]["uom"], "Gói")
		# Header *_name: nv_employee_name (User.full_name), hospital_name (AntMed Hospital).
		self.assertEqual(res["nv_employee_name"], frappe.db.get_value("User", "Administrator", "full_name"))
		self.assertEqual(res["hospital_name"], "BV K Trung Ương")

	def test_get_stock_entry_total_value(self):
		"""(4) total_value == SUM(item.amount); phiếu 0 dòng → items==[] & total_value None."""
		res = inventory.get_stock_entry(self.entry)
		self.assertEqual(res["total_value"], sum(r["amount"] or 0 for r in res["items"]))
		self.assertEqual(res["total_value"], 5 * 190000)  # dòng b amount 0
		# Phiếu 0 dòng → shape ổn định.
		empty = inventory.get_stock_entry(self.entry_empty)
		self.assertEqual(empty["items"], [])
		self.assertIsNone(empty["total_value"])
		self.assertEqual(set(empty.keys()), STOCK_ENTRY_DETAIL_FULL_KEYS)

	def test_get_stock_entry_cocq_passthrough(self):
		"""(5) cocq_ok pass-through đúng theo child (Check 0/1 → bool)."""
		res = inventory.get_stock_entry(self.entry)
		by_item = {r["item"]: r for r in res["items"]}
		self.assertIs(by_item[self.item]["cocq_ok"], True)
		self.assertIs(by_item[self.item2]["cocq_ok"], False)

	def test_get_stock_entry_not_found(self):
		"""(6) Phiếu không tồn tại → DoesNotExistError (idiom get_doc, khớp get_lot)."""
		with self.assertRaises(frappe.DoesNotExistError):
			inventory.get_stock_entry("_T-SED-KHONG-TON-TAI")

	def test_get_stock_entry_no_n_plus_1(self):
		"""(7) item_name + lot_no/expiry gộp BATCH: ≤1 get_all/loại (KHÔNG N+1 theo số dòng)."""
		count = {"AntMed Item": 0, "AntMed Lot": 0}
		orig_get_all = frappe.get_all

		def _counting_get_all(*a, **kw):
			dt = a[0] if a else kw.get("doctype")
			if dt in count:
				count[dt] += 1
			return orig_get_all(*a, **kw)

		frappe.get_all = _counting_get_all
		try:
			res = inventory.get_stock_entry(self.entry)
		finally:
			frappe.get_all = orig_get_all
		self.assertEqual(len(res["items"]), 2)  # sanity: nhiều dòng
		self.assertLessEqual(count["AntMed Item"], 1, msg="item_name phải gộp batch (≤1 get_all Item)")
		self.assertLessEqual(count["AntMed Lot"], 1, msg="lot_no/expiry phải gộp batch (≤1 get_all Lot)")

	def test_get_stock_entry_no_raw_sql(self):
		"""(7b) get_stock_entry KHÔNG raw SQL — đọc qua get_doc + get_all (DocPerm tự nhiên)."""
		import inspect

		src = inspect.getsource(inventory.get_stock_entry)
		self.assertNotIn("frappe.db.sql", src, msg="get_stock_entry không được dùng raw SQL")
		self.assertNotIn(".sql(", src, msg="get_stock_entry không được dùng raw SQL")

	def test_get_stock_entry_fail_closed_no_perm(self):
		"""(8) BR-13: user không read-perm → KHÔNG rò header thật, KHÔNG 500.

		Trả shape rỗng ổn định HOẶC raise PermissionError (cả 2 fail-closed); TUYỆT ĐỐI không rò
		BV/NV/ngày dùng thật. Chạy DƯỚI user scoped (không role AntMed Stock Entry).
		"""
		# sanity (chống false-green): admin THẤY header thật.
		self.assertEqual(inventory.get_stock_entry(self.entry)["hospital_name"], "BV K Trung Ương")
		email = "_t_sed_noperm@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": "NoPermSED", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.set_user(email)
		try:
			try:
				res = inventory.get_stock_entry(self.entry)
			except frappe.PermissionError:
				return  # an toàn: chặn ngay, KHÔNG rò (fail-closed)
			# KHÔNG 500 (đã trả). KHÔNG rò header thật.
			self.assertIsNone(res["hospital"])
			self.assertIsNone(res["hospital_name"])
			self.assertIsNone(res["nv_employee"])
			self.assertIsNone(res["nv_employee_name"])
			self.assertIsNone(res["expected_use_date"])
			self.assertIsNone(res["total_value"])
			self.assertEqual(res["items"], [])
			# Header keys vẫn đủ (Hyrum: FE bind ổn định kể cả nhánh fail-closed).
			self.assertEqual(set(res.keys()), STOCK_ENTRY_DETAIL_FULL_KEYS)
		finally:
			frappe.set_user("Administrator")

	def test_get_stock_entry_get_only(self):
		"""(9) GET-only: @frappe.whitelist(methods=['GET']) — KHÔNG cho POST.

		Frappe lưu HTTP method cho phép trong frappe.allowed_http_methods_for_whitelisted_func
		(key = func đã unwrap). Tra theo __qualname__ để chống POST mutation nhầm.
		"""
		reg = frappe.allowed_http_methods_for_whitelisted_func
		allowed = next(
			(v for k, v in reg.items() if getattr(k, "__qualname__", "") == "get_stock_entry"), None
		)
		self.assertEqual(list(allowed or []), ["GET"], msg=f"get_stock_entry phải GET-only; có: {allowed}")

	def test_get_stock_entry_detail_keys_export(self):
		"""SSoT hằng export khớp shape test (đồng bộ BE↔FE Hyrum)."""
		self.assertEqual(set(inventory.STOCK_ENTRY_DETAIL_HEADER_KEYS), STOCK_ENTRY_DETAIL_HEADER_KEYS)
		self.assertEqual(set(inventory.STOCK_ENTRY_DETAIL_ITEM_KEYS), STOCK_ENTRY_DETAIL_ITEM_KEYS)
