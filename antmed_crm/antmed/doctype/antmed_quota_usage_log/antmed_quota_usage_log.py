# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""Controller cho DocType: AntMed Quota Usage Log (M02 Slice M02-3).

Log tiêu hao quota — single source of truth cho `used_qty`/`remaining_pct` của
AntMed Quota Item (derive, KHÔNG nhập tay — LL-BE-15). Mỗi lần M04 giao 1 vật tư
trong HĐ → 1 dòng log + recompute (xem antmed_crm.antmed.contract_hooks.consume_quota).
Đây là đường đối chiếu DR giữa M02 ↔ M04 (m02_contract_quota.md §2/§6).
"""

from frappe.model.document import Document


class AntMedQuotaUsageLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		contract: DF.Link
		do_ref: DF.Data | None
		item: DF.Data
		qty: DF.Float
		snapshot_pct: DF.Percent
		ts: DF.Datetime
	# end: auto-generated types

	pass
