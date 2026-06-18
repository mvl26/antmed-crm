# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""Controller cho DocType: AntMed Stock Ledger (M03 — sổ cái tồn kho, append-only).

Single source of truth cho tồn: balance(kho×item×lot) = SUM(qty_change). Chỉ ghi qua
antmed_crm.antmed.stock (hệ thống), KHÔNG nhập tay. Xem stock.get_balance/post_stock_entry.
"""

from frappe.model.document import Document


class AntMedStockLedger(Document):
	pass
