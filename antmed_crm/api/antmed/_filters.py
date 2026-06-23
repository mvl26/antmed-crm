# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""Util chung chuẩn hoá `filters` cho các list-endpoint AntMed.

NGUỒN DUY NHẤT — gom 8 bản copy-paste `_coerce_filters` (consolidate R2). Mỗi module
giữ wrapper mỏng `_coerce_filters` (giảm blast-radius call-site) gọi xuống đây.

Hai biến thể hành vi được BẢO TOÀN 100% (đã characterization-test, KHÔNG drift):
  - safe=False (mặc định — 6 bản chuẩn + contract): parse JSON-string bằng `frappe.parse_json`
    → JSON HỎNG sẽ RAISE (lan lên caller); fallback non-dict → `list(filters)`.
  - safe=True (tasks): parse bằng `json.loads` trong try/except → JSON HỎNG → `[]` (nuốt lỗi);
    fallback non-dict, non-list → `[]`.

field_map (contract — ADR-M02-04): remap key trong nhánh dict TRƯỚC khi tạo điều kiện
(vd {"workflow_state": "status"}). KHÔNG áp cho list passthrough (giống bản gốc).
"""

import json

import frappe


def coerce_filters(
	filters: dict | str | list | None,
	field_map: dict | None = None,
	*,
	safe: bool = False,
) -> list:
	"""Chuẩn hoá filters về list điều kiện. FE/GET truyền dict hoặc JSON-string.

	dict {field: value} → list [[field, "=", value]] để gộp được điều kiện search.
	"""
	if not filters:
		return []
	if isinstance(filters, str):
		if safe:
			try:
				filters = json.loads(filters)
			except Exception:
				return []
		else:
			filters = frappe.parse_json(filters) or []
	if isinstance(filters, dict):
		conditions = []
		for k, v in filters.items():
			field = field_map.get(k, k) if field_map else k
			conditions.append([field, "=", v])
		return conditions
	if safe:
		return filters if isinstance(filters, list) else []
	return list(filters)
