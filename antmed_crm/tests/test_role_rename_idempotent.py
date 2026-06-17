# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""W0-1 (DEC-A / ADR-M14W0-01) — patch rename Role EN→VI phải IDEMPOTENT.

Acceptance:
  - Gọi patch.execute() nhiều lần liên tiếp → KHÔNG raise.
  - Sau khi chạy: đúng 3 Role VI tồn tại ['NV kinh doanh','Thủ kho','Quản lý'].
  - KHÔNG còn Role EN ['AntMed Sales Rep','AntMed Warehouse Keeper','AntMed Manager'].
  - KHÔNG tạo Role trùng (count Role VI == 3).

Lệnh chạy:
  bench --site miyano run-tests --module antmed_crm.tests.test_role_rename_idempotent
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from antmed_crm.patches.v1_0 import rename_antmed_roles_to_vi as patch

ROLES_VI = ["NV kinh doanh", "Thủ kho", "Quản lý"]
ROLES_EN = ["AntMed Sales Rep", "AntMed Warehouse Keeper", "AntMed Manager"]


class TestRoleRenameIdempotent(FrappeTestCase):
	def test_execute_is_idempotent(self):
		"""Chạy execute() 2 lần liên tiếp → không lỗi, không Role trùng, không Role EN.

		Tại thời điểm test, migrate đã rename EN→VI (Role VI tồn tại, EN đã hết). Gọi lại
		execute() phải no-op qua guard `exists(old) and not exists(new)` → không raise.
		"""
		# tiền điều kiện: state đã hội tụ về VI sau migrate
		for r in ROLES_VI:
			self.assertTrue(frappe.db.exists("Role", r), msg=f"Role VI thiếu trước test: {r!r}")

		# chạy 2 lần — KHÔNG được raise
		patch.execute()
		patch.execute()

		# đúng 3 Role VI, không trùng
		rows = frappe.get_all("Role", filters={"name": ["in", ROLES_VI]}, pluck="name")
		self.assertEqual(
			sorted(rows), sorted(ROLES_VI),
			msg=f"Sau execute() x2 phải đúng 3 Role VI, thực tế: {sorted(rows)}",
		)
		# không còn Role EN
		for r in ROLES_EN:
			self.assertIsNone(
				frappe.db.exists("Role", r),
				msg=f"Role EN vẫn còn sau execute() idempotent: {r!r}",
			)

	def test_rename_map_is_complete(self):
		"""Map rename đúng 3 cặp EN→VI (chống sót/đổi sai mapping)."""
		self.assertEqual(
			patch.RENAMES,
			[
				("AntMed Sales Rep", "NV kinh doanh"),
				("AntMed Warehouse Keeper", "Thủ kho"),
				("AntMed Manager", "Quản lý"),
			],
		)
