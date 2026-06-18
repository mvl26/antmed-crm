# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""Controller cho DocType: AntMed Hospital (M01 R2 Customer 360°).

Master data hồ sơ bệnh viện (pháp nhân). KHÔNG submittable, KHÔNG workflow —
`contract_status` là nhãn Select tĩnh ở R2 (chưa derive từ HĐ thật — xem ADR-M01-05).
"""

from frappe.model.document import Document


class AntMedHospital(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		address: DF.SmallText | None
		contract_status: DF.Literal["Đã ký", "Tiềm năng", "Hết hạn"]
		hospital_code: DF.Data
		hospital_name: DF.Data
		rank: DF.Literal["", "Đặc biệt", "I", "II", "III", "Khác"]
		tax_code: DF.Data | None
	# end: auto-generated types

	pass
