# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""Controller cho DocType: AntMed Document Release Queue (M06 — hàng chờ phát hành chứng từ).

1 dòng / 1 phiếu giao (autoname field:delivery, unique). missing_chips (JSON) = VT còn
thiếu CO/CQ — màn "Hàng chờ" hiển thị chip. Tạo/cập nhật qua api documents.*.
"""

from frappe.model.document import Document


class AntMedDocumentReleaseQueue(Document):
	pass
