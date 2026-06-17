# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""Controller cho DocType: AntMed Stock Entry (M03 — phiếu nhập/xuất/chuyển kho).

Submit → ghi AntMed Stock Ledger (sổ tồn) + enforce tồn-không-âm (m03 §4). Logic sổ tồn
sống ở antmed_crm.antmed.stock (idempotent theo stock_entry). on_cancel đảo ledger.
"""

import frappe
from frappe import _
from frappe.model.document import Document

# Loại phiếu cần kho nguồn / kho đích.
_NEEDS_TO = {"Nhập NCC", "Nhập ký gửi BV"}
_NEEDS_FROM = {"Xuất cho NV"}
_NEEDS_BOTH = {"Chuyển kho"}


class AntMedStockEntry(Document):
	def validate(self):
		"""Bắt buộc kho phù hợp theo loại phiếu (m03 §2/§4)."""
		et = self.entry_type
		if et in _NEEDS_TO and not self.to_warehouse:
			frappe.throw(_("Phiếu '{0}' phải có kho đến (to_warehouse).").format(et))
		if et in _NEEDS_FROM and not self.from_warehouse:
			frappe.throw(_("Phiếu '{0}' phải có kho nguồn (from_warehouse).").format(et))
		if et in _NEEDS_BOTH and not (self.from_warehouse and self.to_warehouse):
			frappe.throw(_("Phiếu 'Chuyển kho' phải có cả kho nguồn và kho đến."))
		for line in self.items:
			line.amount = (line.qty or 0) * (line.unit_price or 0)

	def on_submit(self):
		from antmed_crm.antmed import stock

		stock.post_stock_entry(self)

	def on_cancel(self):
		from antmed_crm.antmed import stock

		stock.reverse_stock_entry(self)
