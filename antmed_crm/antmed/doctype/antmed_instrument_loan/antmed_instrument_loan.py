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
		# Overlap [booked_at, due_return_at] với lượt active khác cùng bộ. get_all → param-bind
		# (LL-BE-11), KHÔNG raw f-string SQL (tránh sql-format-injection rule).
		overlap = frappe.get_all(
			"AntMed Instrument Loan",
			filters={
				"instrument_set": self.instrument_set,
				"name": ["!=", self.name or "__new__"],
				"docstatus": ["<", 2],
				"status": ["in", list(ACTIVE_LOAN_STATUSES)],
				"booked_at": ["<", self.due_return_at],
				"due_return_at": [">", self.booked_at],
			},
			limit_page_length=1,
		)
		if overlap:
			frappe.throw(_("BR-05: Bộ dụng cụ đã có lịch mượn trùng khoảng thời gian này."))
