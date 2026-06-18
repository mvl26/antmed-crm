# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""Controller cho DocType: AntMed Sterilization (M05 — bản ghi tiệt khuẩn bộ dụng cụ).

result Pass/Fail là điều kiện BR-09: chỉ mark_ready (về 'Sẵn sàng') khi có ≥1 Pass cho lượt.
"""

from frappe.model.document import Document


class AntMedSterilization(Document):
	pass
