# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""Controller cho DocType: AntMed Document (M06 — bundle chứng từ 1 phiếu giao).

Gom CO/CQ/HĐ GTGT theo phiếu giao; `missing_items` (JSON) = VT requires_cocq còn thiếu
CO/CQ (BR-03 chuẩn bị). status điều khiển qua api documents.* (read-only display).
"""

from frappe.model.document import Document


class AntMedDocument(Document):
	pass
