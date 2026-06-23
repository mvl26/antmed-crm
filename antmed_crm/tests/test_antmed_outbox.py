# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M12 Slice S2 (BE) — Offline write-replay: mobile_sync.apply_outbox (allowlist + idempotency).

Cover m12_mobile.md §5 (apply_outbox) + BR-M12-1/2:
  test_apply_ok          — op hợp lệ (save_care_note) → applied, bản ghi tạo.
  test_idempotent        — cùng idempotency_key 2 lần → áp DUY NHẤT 1 lần (BR-M12-1).
  test_reject_unknown_op — op ngoài allowlist → Rejected (KHÔNG dispatch tùy ý).

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_outbox
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from antmed_crm.api.antmed import mobile_sync


def _ensure(doctype, key, val, values):
	return (
		frappe.db.get_value(doctype, {key: val}, "name")
		or frappe.get_doc({"doctype": doctype, key: val, **values}).insert(ignore_permissions=True).name
	)


class TestAntMedOutbox(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hosp = _ensure("AntMed Hospital", "hospital_code", "_T-OBX-BV", {"hospital_name": "BV Outbox"})
		cls.doctor = _ensure(
			"AntMed Doctor", "doctor_code", "_T-OBX-BS", {"full_name": "BS Outbox", "hospital": cls.hosp}
		)

	def test_apply_ok(self):
		res = mobile_sync.apply_outbox(
			[
				{
					"idempotency_key": "OBX-1",
					"operation": "save_care_note",
					"payload": {"doctor": self.doctor, "content": "Ghi chú offline"},
				}
			]
		)
		self.assertEqual(res["applied"], 1)
		self.assertEqual(res["results"][0]["status"], "OK")
		self.assertGreaterEqual(frappe.db.count("AntMed Care Note", {"doctor": self.doctor}), 1)

	def test_idempotent(self):
		op = {
			"idempotency_key": "OBX-IDEM",
			"operation": "save_care_note",
			"payload": {"doctor": self.doctor, "content": "x"},
		}
		mobile_sync.apply_outbox([op])
		before = frappe.db.count("AntMed Care Note", {"doctor": self.doctor})
		res2 = mobile_sync.apply_outbox([op])  # cùng key
		after = frappe.db.count("AntMed Care Note", {"doctor": self.doctor})
		self.assertEqual(after, before)  # KHÔNG tạo thêm
		self.assertEqual(res2["results"][0]["status"], "Skipped")

	def test_reject_unknown_op(self):
		res = mobile_sync.apply_outbox(
			[{"idempotency_key": "OBX-BAD", "operation": "frappe.delete_doc", "payload": {}}]
		)
		self.assertEqual(res["results"][0]["status"], "Rejected")
		self.assertEqual(res["applied"], 0)
