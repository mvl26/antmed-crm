# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""Controller cho DocType: AntMed Contract (M02 Slice M02-1 — read-only).

Master HĐ/gói thầu trúng giữa AntMed và bệnh viện (Link → AntMed Hospital), kèm
danh mục SKU + quota (child AntMed Quota Item). naming_series AM-HD-.YYYY.-.#####
(KHÔNG TC-/AM-DR-/AM-DOC-). is_submittable=1 (hậu quả data sai cao — câu hỏi #6).

M02-1: `status` là Select read-only display (KHÔNG Workflow — ADR-M02-04). Transition
/role/workflow_state thật để Slice M02-2. Slice này KHÔNG enforce BR-01/02/06.
"""

from frappe.model.document import Document


class AntMedContract(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from antmed_crm.antmed.doctype.antmed_quota_item.antmed_quota_item import AntMedQuotaItem

		contract_no: DF.Data
		hospital: DF.Link
		items: DF.Table[AntMedQuotaItem]
		naming_series: DF.Literal["AM-HD-.YYYY.-.#####"]
		signed_date: DF.Date
		status: DF.Literal["", "Nháp", "Hiệu lực", "Sắp hết hạn", "Hết hạn", "Đã huỷ"]
		total_value: DF.Currency
		valid_from: DF.Date | None
		valid_to: DF.Date | None
	# end: auto-generated types

	pass
