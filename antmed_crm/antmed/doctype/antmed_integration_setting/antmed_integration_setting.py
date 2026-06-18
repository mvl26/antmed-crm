# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""Controller cho Single DocType: AntMed Integration Setting (cấu hình tích hợp — secrets).

api_key/token = Password (mã hóa). KHÔNG bao giờ trả ra FE (BR-INT-01) — chỉ qua get_password
ở server. get_settings (api) chỉ trả 'configured' bool + field không nhạy cảm.
"""

from frappe.model.document import Document


class AntMedIntegrationSetting(Document):
	pass
