# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""Controller cho DocType: AntMed Warehouse (M03 — kho 3 cấp, ADR-M03-02).

3 cấp qua field `warehouse_type` (KHÔNG tách 3 DocType): Tổng / Cá nhân NV / Ký gửi BV.
Ràng buộc native (m03 §4): kho 'Cá nhân NV' ⇒ bắt buộc employee; 'Ký gửi BV' ⇒ bắt buộc hospital.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class AntMedWarehouse(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		disabled: DF.Check
		employee: DF.Link | None
		hospital: DF.Link | None
		parent_warehouse: DF.Link | None
		warehouse_name: DF.Data
		warehouse_type: DF.Literal["Tổng", "Cá nhân NV", "Ký gửi BV"]
	# end: auto-generated types

	def validate(self):
		"""Ràng buộc kho 3 cấp (m03 §4 — BR native)."""
		if self.warehouse_type == "Cá nhân NV" and not self.employee:
			frappe.throw(_("Kho 'Cá nhân NV' phải gắn nhân viên (employee)."))
		if self.warehouse_type == "Ký gửi BV" and not self.hospital:
			frappe.throw(_("Kho 'Ký gửi BV' phải gắn bệnh viện (hospital)."))
