# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""Controller cho DocType: AntMed 2FA Session (M14 — phiên xác thực 2 lớp, ephemeral, BR-12).

otp_hash = SHA256(OTP) — KHÔNG lưu plaintext. used=1 sau confirm (chống replay). Tạo/confirm
qua antmed_crm.api.antmed.audit.request_2fa/confirm_2fa.
"""

from frappe.model.document import Document


class AntMed2FASession(Document):
	pass
