# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M14 Slice S1 (BE) — Audit hash-chain (BR-10): AntMed Audit Log + audit.write_log/verify_chain.

Cover m14_security_audit.md §BR-10:
  test_doctype          — AntMed Audit Log tồn tại; hash_sha256 read_only.
  test_write_log_chains — write_log nối prev_hash → hash_sha256 (SHA256 chain).
  test_verify_chain_ok  — chuỗi hợp lệ → ok True.
  test_verify_chain_tamper — sửa 1 bản ghi (không cập nhật hash) → ok False + broken_at.

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_audit
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from antmed_crm.api.antmed import audit


class TestAntMedAudit(FrappeTestCase):
	def test_doctype(self):
		self.assertTrue(frappe.db.exists("DocType", "AntMed Audit Log"))
		self.assertEqual(frappe.get_meta("AntMed Audit Log").get_field("hash_sha256").read_only, 1)

	def test_write_log_chains(self):
		a = audit.write_log("AntMed Item", "_T-AUD-1", "Insert", after={"item_code": "_T-AUD-1"})
		b = audit.write_log("AntMed Item", "_T-AUD-1", "Update", before={"x": 1}, after={"x": 2})
		ha = frappe.db.get_value("AntMed Audit Log", a, "hash_sha256")
		pb = frappe.db.get_value("AntMed Audit Log", b, "prev_hash")
		self.assertTrue(ha)
		self.assertEqual(pb, ha)  # b.prev_hash == a.hash_sha256 (xích nối)

	def test_verify_chain_ok(self):
		audit.write_log("AntMed Item", "_T-AUD-OK", "Insert", after={"v": 1})
		audit.write_log("AntMed Item", "_T-AUD-OK", "Submit", after={"v": 2})
		res = audit.verify_chain()
		self.assertTrue(res["ok"])
		self.assertIsNone(res["broken_at"])
		self.assertGreaterEqual(res["count"], 2)

	def test_verify_chain_tamper(self):
		name = audit.write_log("AntMed Item", "_T-AUD-TMP", "Insert", after={"v": 1})
		audit.write_log("AntMed Item", "_T-AUD-TMP", "Update", after={"v": 99})
		# Giả lập sửa lén nội dung (KHÔNG cập nhật hash) → chuỗi gãy.
		frappe.db.set_value("AntMed Audit Log", name, "after_json", '{"v": 1000}')
		res = audit.verify_chain()
		self.assertFalse(res["ok"])
		self.assertEqual(res["broken_at"], name)
