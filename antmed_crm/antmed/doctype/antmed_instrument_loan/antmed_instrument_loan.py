# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""Controller cho DocType: AntMed Instrument Loan (M05 — lượt mượn bộ dụng cụ).

BR-05 (chống đặt trùng lịch) enforce ở validate → chạy cho cả Desk lẫn api. Vòng đời
7-state qua `status` (read-only display); transition + sync Set + BR-09 tiệt khuẩn ở api
(antmed_crm.api.antmed.instrument_loan). SQL param-bind %s (LL-BE-11).
"""

import frappe
from frappe import _
from frappe.model.document import Document

# State mượn còn "giữ chỗ" bộ → xét trùng lịch (BR-05).
ACTIVE_LOAN_STATUSES = ("Đã đặt", "Đang giao", "Đang sử dụng tại BV")


class AntMedInstrumentLoan(Document):
	def validate(self):
		self._assert_no_overlap()

	def _assert_no_overlap(self):
		"""BR-05: cùng 1 bộ KHÔNG được có 2 lượt mượn active trùng khoảng [booked_at, due_return_at]."""
		if not (self.instrument_set and self.booked_at and self.due_return_at):
			return
		placeholders = ", ".join(["%s"] * len(ACTIVE_LOAN_STATUSES))
		rows = frappe.db.sql(
			f"""SELECT name FROM `tabAntMed Instrument Loan`
				WHERE instrument_set = %s AND name != %s AND docstatus < 2
				  AND status IN ({placeholders})
				  AND booked_at < %s AND due_return_at > %s
				LIMIT 1""",
			(self.instrument_set, self.name or "__new__", *ACTIVE_LOAN_STATUSES, self.due_return_at, self.booked_at),
		)
		if rows:
			frappe.throw(_("BR-05: Bộ dụng cụ đã có lịch mượn trùng khoảng thời gian này."))
