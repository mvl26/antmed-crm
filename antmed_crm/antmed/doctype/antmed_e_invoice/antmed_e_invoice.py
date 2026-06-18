# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""Controller cho DocType: AntMed E-Invoice (M06 — hóa đơn điện tử).

BR-04: HĐĐT bất biến sau khi submit (đã phát hành) → on_update_after_submit chặn sửa.
⚠️ Phát hành thật (provider Viettel/MISA/VNPT) = M13/ROADMAP; hiện stub dev-mode.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class AntMedEInvoice(Document):
	def on_update_after_submit(self):
		frappe.throw(_("BR-04: Hóa đơn điện tử đã phát hành không được chỉnh sửa."))
