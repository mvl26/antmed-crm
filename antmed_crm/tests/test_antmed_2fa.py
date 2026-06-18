# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M14 Slice S2 (BE) — 2FA (BR-12): AntMed 2FA Session + request_2fa/confirm_2fa/_enforce_2fa.

⚠️ Cơ chế additive — CHƯA wire vào handler nhạy cảm (đổi hành vi flow cũ → cần sign-off riêng).
OTP KHÔNG bao giờ trả ra response (gửi qua SMS/Zalo — M13/ROADMAP). Cover m14 §BR-12:
  test_doctype             — AntMed 2FA Session tồn tại; otp KHÔNG lộ ở request_2fa.
  test_confirm_ok          — confirm đúng OTP → used=1; _enforce_2fa qua.
  test_confirm_wrong_otp   — OTP sai → throw BR-12.
  test_enforce_without_session — chưa confirm → _enforce_2fa throw BR-12.

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_2fa
"""

import hashlib

import frappe
from frappe.tests.utils import FrappeTestCase

from antmed_crm.api.antmed import audit


class TestAntMed2FA(FrappeTestCase):
	def test_doctype(self):
		self.assertTrue(frappe.db.exists("DocType", "AntMed 2FA Session"))
		res = audit.request_2fa("test-action")
		self.assertIn("session", res)
		self.assertNotIn("otp", res)  # OTP KHÔNG lộ ra response (BR-INT-01-like)
		self.assertEqual(frappe.db.get_value("AntMed 2FA Session", res["session"], "used"), 0)

	def test_confirm_ok(self):
		s = audit.request_2fa("xuat-kho")["session"]
		frappe.db.set_value("AntMed 2FA Session", s, "otp_hash", hashlib.sha256(b"123456").hexdigest())
		res = audit.confirm_2fa(s, "123456")
		self.assertTrue(res["ok"])
		self.assertEqual(frappe.db.get_value("AntMed 2FA Session", s, "used"), 1)
		# sau confirm → _enforce_2fa qua cho cùng action
		audit._enforce_2fa("xuat-kho")  # không raise

	def test_confirm_wrong_otp(self):
		s = audit.request_2fa("phat-hanh-hddt")["session"]
		frappe.db.set_value("AntMed 2FA Session", s, "otp_hash", hashlib.sha256(b"000000").hexdigest())
		with self.assertRaises(frappe.ValidationError) as cm:
			audit.confirm_2fa(s, "999999")
		self.assertIn("BR-12", str(cm.exception))

	def test_enforce_without_session(self):
		with self.assertRaises(frappe.ValidationError) as cm:
			audit._enforce_2fa("hanh-dong-chua-2fa-bao-gio")
		self.assertIn("BR-12", str(cm.exception))
