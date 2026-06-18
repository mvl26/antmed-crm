# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""Controller cho DocType: AntMed Audit Log (M14 — sổ kiểm toán bất biến, hash-chain BR-10).

Append-only: chỉ ghi qua antmed_crm.api.antmed.audit.write_log (tính prev_hash→hash_sha256).
Không role nào được sửa/xóa (DocPerm chỉ read) — giữ tính bất biến của chuỗi.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class AntMedAuditLog(Document):
	def on_update_after_submit(self):
		frappe.throw(_("BR-10: Audit log bất biến, không được sửa."))
