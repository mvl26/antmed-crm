# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M06 Slice S1 (BE) — Chứng từ (bundle + hàng chờ phát hành): AntMed Document/Line/Release Queue.

Cover m06_documents.md §2 (Document/Line/Queue) + §5 (list_release_queue/get_bundle/refresh)
+ §4 (BR-03 chuẩn bị — đánh dấu thiếu CO/CQ; chặn cứng phát hành ở M06-S3):
  test_doctypes              — 3 DocType tồn tại; Document Line istable.
  test_create_bundle_missing — item requires_cocq + lô THIẾU CO/CQ → status 'Thiếu chứng từ' + missing.
  test_create_bundle_ok      — item KHÔNG requires_cocq → 'Chờ phát hành'.
  test_list_release_queue    — {data,total_count} count==rows.
  test_get_bundle            — detail + lines; co_attached/cq_attached đúng.
  test_refresh_status        — gắn CO/CQ cho lô rồi refresh → 'Chờ phát hành'.

M06-1 (BE) — Màn "Hàng chờ phát hành chứng từ" (KPI rollup + worklist mở rộng):
  test_release_queue_summary_shape   — summary() trả ĐỦ 3 key, shape ổn định kể cả 0 bản ghi.
  test_release_queue_summary_counts  — đếm theo NỘI DUNG missing_chips (CO/CQ) + ready_to_release.
  test_release_queue_summary_robust  — missing_chips JSON hỏng/None/'' → [] KHÔNG throw, KHÔNG đếm.
  test_release_queue_summary_perm    — user KHÔNG read-perm → {0,0,0} (fail-closed BR-13).
  test_list_release_queue_perm       — rows chỉ bản ghi user được phép; count==len(rows).
  test_list_release_queue_extended   — mỗi dòng có hospital_name/assigned_employee/ts; key cũ còn (backward-compat).

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_document
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from antmed_crm.api.antmed import documents


def _ensure(doctype, key, val, values):
	name = frappe.db.get_value(doctype, {key: val}, "name")
	if name:
		return name
	return frappe.get_doc({"doctype": doctype, key: val, **values}).insert(ignore_permissions=True).name


class TestAntMedDocument(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hosp = _ensure("AntMed Hospital", "hospital_code", "_T-DOC-BV", {"hospital_name": "BV Chứng Từ"})
		cls.item_cocq = _ensure(
			"AntMed Item", "item_code", "_T-DOC-STENT", {"item_name": "Stent cần CO/CQ", "requires_cocq": 1}
		)
		cls.item_free = _ensure(
			"AntMed Item", "item_code", "_T-DOC-GAC", {"item_name": "Gạc không CO/CQ", "requires_cocq": 0}
		)
		cls.lot_nocert = _ensure(
			"AntMed Lot", "lot_no", "_T-DOC-LOT-NOCERT", {"item": cls.item_cocq, "expiry_date": "2027-12-31"}
		)

	def _mk_delivery(self, items):
		return (
			frappe.get_doc(
				{
					"doctype": "AntMed Delivery",
					"hospital": self.hosp,
					"surgery_datetime": "2026-08-01 08:00:00",
					"items": items,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def test_doctypes(self):
		for dt in ("AntMed Document", "AntMed Document Line", "AntMed Document Release Queue"):
			self.assertTrue(frappe.db.exists("DocType", dt), msg=f"thiếu {dt}")
		self.assertEqual(frappe.get_meta("AntMed Document Line").istable, 1)

	def test_create_bundle_missing(self):
		dlv = self._mk_delivery([{"item": self.item_cocq, "lot": self.lot_nocert, "requested_qty": 2}])
		res = documents.create_bundle(dlv)
		self.assertEqual(res["status"], "Thiếu chứng từ")
		self.assertIn(self.item_cocq, res["missing"])

	def test_create_bundle_ok(self):
		dlv = self._mk_delivery([{"item": self.item_free, "requested_qty": 5}])
		res = documents.create_bundle(dlv)
		self.assertEqual(res["status"], "Chờ phát hành")
		self.assertEqual(res["missing"], [])

	def test_list_release_queue(self):
		dlv = self._mk_delivery([{"item": self.item_free, "requested_qty": 1}])
		documents.create_bundle(dlv)
		res = documents.list_release_queue(page_length=0)
		self.assertEqual(set(res.keys()), {"data", "total_count"})
		self.assertEqual(len(res["data"]), res["total_count"])

	def test_get_bundle(self):
		dlv = self._mk_delivery([{"item": self.item_cocq, "lot": self.lot_nocert, "requested_qty": 2}])
		b = documents.create_bundle(dlv)["bundle"]
		detail = documents.get_bundle(b)
		self.assertEqual(detail["name"], b)
		self.assertEqual(len(detail["lines"]), 1)
		self.assertEqual(detail["lines"][0]["requires_cocq"], 1)
		self.assertEqual(detail["lines"][0]["co_attached"], 0)

	def test_refresh_status(self):
		dlv = self._mk_delivery([{"item": self.item_cocq, "lot": self.lot_nocert, "requested_qty": 2}])
		b = documents.create_bundle(dlv)["bundle"]
		self.assertEqual(frappe.db.get_value("AntMed Document", b, "status"), "Thiếu chứng từ")
		# gắn CO + CQ cho lô rồi refresh
		cert_co = (
			frappe.get_doc({"doctype": "AntMed Certificate", "cert_no": "CO-DOC-1", "cert_type": "CO"})
			.insert(ignore_permissions=True)
			.name
		)
		cert_cq = (
			frappe.get_doc({"doctype": "AntMed Certificate", "cert_no": "CQ-DOC-1", "cert_type": "CQ"})
			.insert(ignore_permissions=True)
			.name
		)
		frappe.db.set_value("AntMed Lot", self.lot_nocert, {"co_cert": cert_co, "cq_cert": cert_cq})
		res = documents.refresh_release_status(dlv)
		self.assertEqual(res["status"], "Chờ phát hành")

	# ---------------- M06-1: KPI rollup release_queue_summary() ----------------

	def _seed_queue(self, suffix, status, missing_chips, assigned_employee=None):
		"""Seed 1 phiếu giao + 1 hàng chờ phát hành với missing_chips/status cụ thể.

		missing_chips truyền raw (đã là chuỗi JSON / None / chuỗi rỗng / list) để test robustness.
		"""
		dlv_doc = {
			"doctype": "AntMed Delivery",
			"hospital": self.hosp,
			"surgery_datetime": "2026-08-01 08:00:00",
			"items": [{"item": self.item_free, "requested_qty": 1}],
		}
		if assigned_employee:
			dlv_doc["assigned_employee"] = assigned_employee
		dlv = frappe.get_doc(dlv_doc).insert(ignore_permissions=True).name
		import json as _json

		if isinstance(missing_chips, list | dict):
			chips_val = _json.dumps(missing_chips, ensure_ascii=False)
		else:
			chips_val = missing_chips  # None / '' / JSON hỏng giữ nguyên
		frappe.get_doc(
			{
				"doctype": "AntMed Document Release Queue",
				"delivery": dlv,
				"status": status,
				"missing_chips": chips_val,
			}
		).insert(ignore_permissions=True)
		return dlv

	def test_release_queue_summary_shape(self):
		res = documents.release_queue_summary()
		self.assertEqual(set(res.keys()), {"missing_co", "missing_cq", "ready_to_release"})
		for k in ("missing_co", "missing_cq", "ready_to_release"):
			self.assertIsInstance(res[k], int)

	def test_release_queue_summary_counts(self):
		base = documents.release_queue_summary()
		# (a) Chờ phát hành nhưng thiếu CO  (b) Thiếu chứng từ thiếu CQ  (c) Chờ phát hành đủ (rỗng)
		self._seed_queue("A", "Chờ phát hành", ["CO lot Lx"])
		self._seed_queue("B", "Thiếu chứng từ", ["CQ lot Ly"])
		self._seed_queue("C", "Chờ phát hành", [])
		res = documents.release_queue_summary()
		self.assertEqual(res["missing_co"] - base["missing_co"], 1)
		self.assertEqual(res["missing_cq"] - base["missing_cq"], 1)
		self.assertEqual(res["ready_to_release"] - base["ready_to_release"], 1)

	def test_release_queue_summary_robust(self):
		base = documents.release_queue_summary()
		# missing_chips None / chuỗi rỗng / JSON hỏng → parse [] KHÔNG throw, KHÔNG đếm CO/CQ.
		self._seed_queue("R1", "Chờ phát hành", None)
		self._seed_queue("R2", "Chờ phát hành", "")
		self._seed_queue("R3", "Thiếu chứng từ", "{not-json[")
		res = documents.release_queue_summary()  # KHÔNG raise
		self.assertEqual(res["missing_co"], base["missing_co"])
		self.assertEqual(res["missing_cq"], base["missing_cq"])
		# 2 dòng "Chờ phát hành" có chips rỗng (None/'') tính là ready_to_release.
		self.assertEqual(res["ready_to_release"] - base["ready_to_release"], 2)

	def test_release_queue_summary_perm(self):
		self._seed_queue("P", "Chờ phát hành", ["CO lot Lz"])
		email = "_t_doc_noperm@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": "NoPermDoc", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.set_user(email)
		try:
			res = documents.release_queue_summary()
			self.assertEqual(res, {"missing_co": 0, "missing_cq": 0, "ready_to_release": 0})
		finally:
			frappe.set_user("Administrator")

	def test_list_release_queue_perm(self):
		self._seed_queue("LP", "Chờ phát hành", ["CO lot LP"])
		email = "_t_doc_noperm_list@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": "NoPermList", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.set_user(email)
		try:
			res = documents.list_release_queue(page_length=0)
			self.assertEqual(len(res["data"]), res["total_count"])  # count==rows dưới quyền hạn chế
		finally:
			frappe.set_user("Administrator")

	def test_list_release_queue_extended(self):
		emp = "_t_doc_nv@example.com"
		if not frappe.db.exists("User", emp):
			frappe.get_doc(
				{"doctype": "User", "email": emp, "first_name": "NV Giao", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		self._seed_queue("EXT", "Chờ phát hành", ["CO lot LEXT"], assigned_employee=emp)
		res = documents.list_release_queue(page_length=0)
		row = next(r for r in res["data"] if r.get("assigned_employee") == emp)
		# Cột E1 resolve đúng theo delivery (KHÔNG None do thiếu join).
		self.assertEqual(row["hospital_name"], "BV Chứng Từ")
		self.assertEqual(row["assigned_employee"], emp)
		self.assertIsNotNone(row["ts"])
		# Backward-compat: key cũ vẫn còn.
		for k in ("name", "delivery", "document_bundle", "status", "missing_chips", "assigned_to"):
			self.assertIn(k, row)


class TestBuildLinesNPlusOne(FrappeTestCase):
	"""Characterization _build_lines (M06) — KHÓA hành vi + chống N+1.

	`_build_lines` được 4 caller dùng (create_bundle/refresh_release_status/assess_cocq/summary).
	Test này CHỐT 100% output (thứ tự dòng + co/cq/requires + missing) cho delivery NHIỀU item,
	và đo số query 'AntMed Item'/'AntMed Lot' là HẰNG SỐ (≤2) bất kể số dòng N (1 vs nhiều).
	Chạy XANH trên code CŨ (khoá hành vi) → refactor batch-then-map → vẫn XANH (output-identical),
	chỉ khác query-count giảm 2N→2.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hosp = _ensure("AntMed Hospital", "hospital_code", "_T-NP1-BV", {"hospital_name": "BV N+1"})
		cls.item_cocq = _ensure(
			"AntMed Item", "item_code", "_T-NP1-STENT", {"item_name": "Stent N+1", "requires_cocq": 1}
		)
		cls.item_free = _ensure(
			"AntMed Item", "item_code", "_T-NP1-GAC", {"item_name": "Gạc N+1", "requires_cocq": 0}
		)
		# Lô đủ CO+CQ (full).
		cls.cert_co = (
			frappe.get_doc({"doctype": "AntMed Certificate", "cert_no": "_T-NP1-CO", "cert_type": "CO"})
			.insert(ignore_permissions=True)
			.name
		)
		cls.cert_cq = (
			frappe.get_doc({"doctype": "AntMed Certificate", "cert_no": "_T-NP1-CQ", "cert_type": "CQ"})
			.insert(ignore_permissions=True)
			.name
		)
		cls.lot_full = _ensure(
			"AntMed Lot",
			"lot_no",
			"_T-NP1-LOT-FULL",
			{
				"item": cls.item_cocq,
				"expiry_date": "2027-12-31",
				"co_cert": cls.cert_co,
				"cq_cert": cls.cert_cq,
			},
		)
		# Lô CHỈ có CO (thiếu CQ).
		cls.lot_co_only = _ensure(
			"AntMed Lot",
			"lot_no",
			"_T-NP1-LOT-COONLY",
			{"item": cls.item_cocq, "expiry_date": "2027-12-31", "co_cert": cls.cert_co},
		)
		# Lô KHÔNG cert (cho item free — requires=0 nên không vào missing).
		cls.lot_free = _ensure(
			"AntMed Lot", "lot_no", "_T-NP1-LOT-FREE", {"item": cls.item_free, "expiry_date": "2027-12-31"}
		)

	def _mk_delivery(self, items):
		return (
			frappe.get_doc(
				{
					"doctype": "AntMed Delivery",
					"hospital": self.hosp,
					"surgery_datetime": "2026-08-01 08:00:00",
					"items": items,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def _multi_items(self):
		"""4 dòng đủ branch: full / co-only / requires-no-lot / free-no-cert."""
		return [
			{"item": self.item_cocq, "lot": self.lot_full, "requested_qty": 2},
			{"item": self.item_cocq, "lot": self.lot_co_only, "requested_qty": 3},
			{"item": self.item_cocq, "requested_qty": 1},  # requires + KHÔNG lot → thiếu CO/CQ
			{"item": self.item_free, "lot": self.lot_free, "requested_qty": 5},  # không requires
		]

	def test_build_lines_output_identical(self):
		"""Khoá 100%: thứ tự dòng + co/cq/requires từng dòng + missing list."""
		dlv = self._mk_delivery(self._multi_items())
		lines, missing = documents._build_lines(dlv)
		self.assertEqual(len(lines), 4)
		# Dòng 0: full → requires=1, co=1, cq=1
		self.assertEqual(lines[0]["item"], self.item_cocq)
		self.assertEqual(lines[0]["lot"], self.lot_full)
		self.assertEqual(lines[0]["qty"], 2)
		self.assertEqual(
			(lines[0]["requires_cocq"], lines[0]["co_attached"], lines[0]["cq_attached"]), (1, 1, 1)
		)
		# Dòng 1: co-only → requires=1, co=1, cq=0
		self.assertEqual(lines[1]["lot"], self.lot_co_only)
		self.assertEqual(
			(lines[1]["requires_cocq"], lines[1]["co_attached"], lines[1]["cq_attached"]), (1, 1, 0)
		)
		# Dòng 2: requires + KHÔNG lot → requires=1, co=0, cq=0
		self.assertIn(lines[2]["lot"], (None, ""))
		self.assertEqual(
			(lines[2]["requires_cocq"], lines[2]["co_attached"], lines[2]["cq_attached"]), (1, 0, 0)
		)
		# Dòng 3: free → requires=0, co=0, cq=0 (lô không cert)
		self.assertEqual(lines[3]["item"], self.item_free)
		self.assertEqual(
			(lines[3]["requires_cocq"], lines[3]["co_attached"], lines[3]["cq_attached"]), (0, 0, 0)
		)
		# missing = item requires mà thiếu CO hoặc CQ → dòng 1 (thiếu CQ) + dòng 2 (thiếu cả 2), KHÔNG dòng 0/3.
		self.assertEqual(missing, [self.item_cocq, self.item_cocq])

	def test_build_lines_all_ok(self):
		"""Tất cả dòng đủ CO/CQ hoặc không-requires → missing rỗng."""
		dlv = self._mk_delivery(
			[
				{"item": self.item_cocq, "lot": self.lot_full, "requested_qty": 1},
				{"item": self.item_free, "lot": self.lot_free, "requested_qty": 2},
			]
		)
		lines, missing = documents._build_lines(dlv)
		self.assertEqual(missing, [])
		self.assertEqual(len(lines), 2)

	def _count_lookups(self, delivery_name):
		"""Đếm số lần đọc 'AntMed Item' + 'AntMed Lot' khi dựng lines (qua get_value & get_all).

		N+1 cũ: get_value gọi 1 lần / item + 1 lần / lot → ~2N. Sau refactor: get_all gom = ≤2.
		Đếm CẢ get_value lẫn get_all để không phụ thuộc cách hiện thực — chỉ quan tâm tổng số
		round-trip đọc 2 doctype này KHÔNG tăng theo số dòng.
		"""
		from unittest.mock import patch

		orig_get_value = frappe.db.get_value
		orig_get_all = frappe.get_all
		count = {"n": 0}

		def _is_target(args, kwargs):
			dt = kwargs.get("doctype")
			if dt is None and args:
				dt = args[0]
			return dt in ("AntMed Item", "AntMed Lot")

		def _gv(*args, **kwargs):
			if _is_target(args, kwargs):
				count["n"] += 1
			return orig_get_value(*args, **kwargs)

		def _ga(*args, **kwargs):
			if _is_target(args, kwargs):
				count["n"] += 1
			return orig_get_all(*args, **kwargs)

		with (
			patch.object(frappe.db, "get_value", side_effect=_gv),
			patch.object(frappe, "get_all", side_effect=_ga),
		):
			documents._build_lines(delivery_name)
		return count["n"]

	def test_build_lines_query_count_constant(self):
		"""Đo N+1: số đọc AntMed Item/Lot KHÔNG tăng theo số dòng (N=1 vs N=4) và ≤2."""
		dlv1 = self._mk_delivery([{"item": self.item_cocq, "lot": self.lot_full, "requested_qty": 1}])
		dlv4 = self._mk_delivery(self._multi_items())
		c1 = self._count_lookups(dlv1)
		c4 = self._count_lookups(dlv4)
		# Hằng số: 4 dòng KHÔNG tốn nhiều round-trip hơn 1 dòng.
		self.assertEqual(c1, c4, msg=f"query count phải hằng số bất kể N: N=1→{c1}, N=4→{c4} (N+1 chưa fix?)")
		# Tối đa 2 (1 query AntMed Item + 1 query AntMed Lot).
		self.assertLessEqual(c4, 2, msg=f"đọc AntMed Item/Lot phải ≤2 batch, đang {c4} (N+1?)")
