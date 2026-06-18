# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""Controller cho DocType: AntMed Material Request (M09 — Portal BV "Gọi vật tư cho ca mổ").

BV gửi yêu cầu vật tư → NV tiếp nhận → tạo phiếu giao (AntMed Delivery). status = vòng đời
Portal (Mới→NV đã nhận→Đã tạo phiếu giao / Từ chối). in_quota/needs_approval set ở api.
"""

from frappe.model.document import Document


class AntMedMaterialRequest(Document):
	pass
