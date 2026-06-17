# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""W0-1 (DEC-A / ADR-M14W0-01): rename 3 Role AntMed EN -> nhãn tiếng Việt.

Chạy ở [pre_model_sync] để Role VI tồn tại TRƯỚC khi DocType (AntMed Hospital/Doctor)
apply DocPerm trỏ role VI -> không lỗi "role không tồn tại".

Idempotent: chỉ rename khi `old` tồn tại VÀ `new` chưa tồn tại. Chạy lần 2 = no-op.
Site mới (chưa có Role nào) = no-op, fixture role.json sẽ tạo thẳng 3 Role VI.
"""

import frappe

RENAMES = [
	("AntMed Sales Rep", "NV kinh doanh"),
	("AntMed Warehouse Keeper", "Thủ kho"),
	("AntMed Manager", "Quản lý"),
]


def execute():
	for old, new in RENAMES:
		if frappe.db.exists("Role", old) and not frappe.db.exists("Role", new):
			# force=True: Role bị Frappe bảo vệ rename mặc định; force cho phép đổi tên Role custom.
			frappe.rename_doc("Role", old, new, force=True)
