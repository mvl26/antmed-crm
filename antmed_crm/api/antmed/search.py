# Copyright (c) 2026, AntMed and Contributors
# For license information, please see license.txt
"""Quick-search command palette (header) — tìm nhanh đa-doctype.

global_search(query, limit) gộp Bệnh viện + Hợp đồng + Bộ dụng cụ + Giao phòng mổ cho
command palette FE. Tái dùng list_* (đã có search + frappe.get_list dưới quyền user)
→ KẾ THỪA permission + data-scope BR-13, KHÔNG nhân đôi logic phân quyền.
"""

import frappe

from antmed_crm.api.antmed.contract import list_contracts
from antmed_crm.api.antmed.customer import list_hospitals
from antmed_crm.api.antmed.delivery import list_deliveries
from antmed_crm.api.antmed.instrument_loan import list_instrument_sets


@frappe.whitelist(methods=["GET"])
def global_search(query: str | int | None = None, limit: str | int = 5) -> dict:
	"""Trả RAW dict 4 nhóm: hospitals / contracts / instrument_sets / deliveries.

	- query rỗng/whitespace → cả 4 nhóm rỗng (tránh quét toàn bảng).
	- limit clamp 1..20; giá trị không parse được → mặc định 5.
	- Mỗi nhóm tối đa `limit` bản ghi, theo quyền đọc của user hiện tại.
	"""
	query = (str(query) if query is not None else "").strip()
	if not query:
		return {"hospitals": [], "contracts": [], "instrument_sets": [], "deliveries": []}

	try:
		limit = int(limit)
	except (TypeError, ValueError):
		limit = 5
	limit = max(1, min(limit, 20))

	return {
		"hospitals": list_hospitals(search=query, page_length=limit).get("data", []),
		"contracts": list_contracts(search=query, page_length=limit).get("data", []),
		"instrument_sets": list_instrument_sets(search=query, page_length=limit).get("data", []),
		"deliveries": list_deliveries(search=query, page_length=limit).get("data", []),
	}
