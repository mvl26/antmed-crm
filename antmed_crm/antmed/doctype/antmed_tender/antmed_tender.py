# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""Controller cho DocType: AntMed Tender (M08 — gói thầu / pipeline phát triển khách hàng).

status = giai đoạn pipeline (Tiếp cận→…→Trúng/Trượt). BR-M08-02 (Trúng cần decision_no)
enforce ở api pipeline.set_tender_result. Khi Trúng → tạo HĐ (BR-M08-05, slice sau).
"""

from frappe.model.document import Document


class AntMedTender(Document):
	pass
