# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""Controller cho DocType: AntMed Doctor Gift (M07 — quà tặng bác sỹ, compliance).

BR-11 (anti-bribery): mọi quà tặng PHẢI có người duyệt (approved_by) — enforce ở validate
→ chạy cho cả Desk lẫn api (không bypass).
"""

import frappe
from frappe import _
from frappe.model.document import Document


class AntMedDoctorGift(Document):
	def validate(self):
		if not self.approved_by:
			frappe.throw(_("BR-11: Quà tặng bác sỹ phải có người duyệt (approved_by) — chống hối lộ."))
