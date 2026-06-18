# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""Controller cho DocType: AntMed Stock Count (M03 — Kiểm kê tồn 1 kho).

Mockup '📊 Kiểm kê': chọn kho → snapshot SL hệ thống → nhập SL thực đếm → chênh lệch (variance).
Submit → ghi AntMed Stock Ledger dòng điều chỉnh (variance) để đưa tồn về SL thực đếm. Logic ghi sổ
ở antmed_crm.antmed.stock.post_stock_count (idempotent theo voucher). on_cancel đảo điều chỉnh.
"""

import frappe
from frappe.model.document import Document


class AntMedStockCount(Document):
	def validate(self):
		"""Tính variance mỗi dòng = SL thực đếm − SL hệ thống (authoritative tại thời điểm validate)."""
		from antmed_crm.antmed import stock

		# SL hệ thống authoritative (chống snapshot cũ): 1 query gộp tồn kho → map (item,lot)→tồn.
		balances = {
			(b["item"], b["lot"]): b["system_qty"] for b in stock.get_warehouse_balances(self.warehouse)
		}
		total = 0.0
		for line in self.items:
			line.system_qty = balances.get((line.item, line.lot), 0.0)
			line.variance = float(line.counted_qty or 0) - float(line.system_qty or 0)
			total += line.variance
		self.total_variance_qty = total
		if not self.counted_by:
			self.counted_by = frappe.session.user

	def on_submit(self):
		from antmed_crm.antmed import stock

		stock.post_stock_count(self)

	def on_cancel(self):
		from antmed_crm.antmed import stock

		stock.reverse_stock_count(self)
