# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""Controller cho DocType con: AntMed Quota Item (M02 Slice M02-1).

Child table (istable) của AntMed Contract — 1 dòng = 1 SKU trúng thầu + quota.
M02-1: `item` = Data (M03 chưa land — ADR-M02-02). `used_qty`/`remaining_pct`
read-only nhưng CHƯA có cơ chế derive (usage log thuộc Slice M02-2+) → KHÔNG
recompute ở slice này.
"""

from frappe.model.document import Document


class AntMedQuotaItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		item: DF.Data
		item_name: DF.Data | None
		lock_at_100: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		quota_qty: DF.Float
		remaining_pct: DF.Percent
		unit_price: DF.Currency
		uom: DF.Data | None
		used_qty: DF.Float
	# end: auto-generated types

	pass
