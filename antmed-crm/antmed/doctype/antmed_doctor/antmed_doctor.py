# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""Controller cho DocType: AntMed Doctor (M01 R2 Customer 360°).

Master data hồ sơ bác sỹ (cá nhân chăm sóc), Link → AntMed Hospital (gốc 360).
naming_series AM-DOC-.YYYY.-.#### (KHÔNG AM-DR — reserve M04). KHÔNG submittable.
"""

from frappe.model.document import Document


class AntMedDoctor(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		birthday: DF.Date | None
		doctor_code: DF.Data | None
		email: DF.Data | None
		full_name: DF.Data
		hospital: DF.Link | None
		naming_series: DF.Literal["AM-DOC-.YYYY.-.####"]
		notes: DF.SmallText | None
		phone: DF.Data | None
		specialty: DF.Data | None
		zalo: DF.Data | None
	# end: auto-generated types

	pass
