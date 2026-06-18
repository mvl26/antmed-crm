# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""Controller cho DocType: AntMed Employee Hospital (M14 — gán tuyến NV↔BV cho data-scope BR-13).

1 dòng = 1 NV phụ trách 1 BV. permission_query_conditions (antmed_scope) đọc bảng này để NV
chỉ thấy bản ghi của BV trong tuyến mình.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class AntMedEmployeeHospital(Document):
	def validate(self):
		# Chống gán trùng (cùng NV + cùng BV) → tránh nhiễu IN-list scope.
		dup = frappe.db.exists(
			"AntMed Employee Hospital",
			{"employee": self.employee, "hospital": self.hospital, "name": ["!=", self.name or ""]},
		)
		if dup:
			frappe.throw(_("NV {0} đã được gán BV {1}.").format(self.employee, self.hospital))
