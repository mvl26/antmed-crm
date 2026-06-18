# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""Controller cho DocType: AntMed Lot (M03 — lô VTYT: CO/CQ/HSD/ĐKLH, truy vết & recall).

expiry_date (HSD) reqd — nền FIFO theo HSD (BR-08, slice A4) + cảnh báo cận date. recall_status
mặc định 'Bình thường', đổi qua AntMed Recall Notification (slice A6), KHÔNG workflow độc lập.
"""

from frappe.model.document import Document


class AntMedLot(Document):
	pass
