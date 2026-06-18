# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""Controller cho DocType: AntMed Certificate (M03 — chứng từ CO/CQ/ĐKLH của lô VTYT).

hash_sha256 (BR-10) tính từ file CO/CQ — wiring đầy đủ ở M14 (audit). Slice A2 chỉ tạo
schema + read; gate chặn cứng CO/CQ trước xuất/giao thực thi ở M06 (phát hành).
"""

from frappe.model.document import Document


class AntMedCertificate(Document):
	pass
