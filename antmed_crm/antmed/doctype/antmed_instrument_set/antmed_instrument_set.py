# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""Controller cho DocType: AntMed Instrument Set (M05 — bộ dụng cụ phẫu thuật mượn).

native-lite (KHÔNG ERPNext Asset). current_status = denorm mirror vòng đời mượn (đổi qua
AntMed Instrument Loan ở slice M05-S2, read-only). lifetime_loans tăng khi handover.
"""

from frappe.model.document import Document


class AntMedInstrumentSet(Document):
	pass
