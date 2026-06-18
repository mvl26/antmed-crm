# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""Controller cho DocType: AntMed Delivery (M04 — giao hàng & bàn giao phòng mổ).

M04-S1: schema + read. `status` = Select (vòng đời điều phối Nháp→…→Đã đóng); transition
role-gated + SLA + gate chữ ký/ảnh/GPS + BR-01/06 (M02) để slice M04-S2/S3. naming
AntMed-DR-.YYYY.-.##### (KHÔNG AM-DR — reserve). Item_name fetch từ AntMed Item ở before_save.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class AntMedDelivery(Document):
	def before_save(self):
		"""Điền item_name từ AntMed Item nếu thiếu (LL-BE-2 — FE hiện tên, không mã)."""
		for line in self.items:
			if line.item and not line.item_name:
				line.item_name = frappe.db.get_value("AntMed Item", line.item, "item_name")

	def on_trash(self):
		"""BR-07: KHÔNG cho xóa phiếu giao đã bàn giao/ký nhận (chứng cứ pháp lý)."""
		if self.status in ("Đã bàn giao", "Đã đóng"):
			frappe.throw(_("BR-07: Không được xóa phiếu giao đã bàn giao/ký. Phải hủy kèm lý do."))
