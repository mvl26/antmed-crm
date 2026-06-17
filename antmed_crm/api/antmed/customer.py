# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M01 R2 Customer 360° — endpoint Bệnh viện + Bác sỹ.

Đường gọi: crm.api.antmed.customer.<fn>  (xem m01_customer360.md §API).
Mọi hàm @frappe.whitelist(methods=["GET"]), type-annotated (require_type_annotated_api_methods),
trả RAW dict (KHÔNG envelope _ok/_err). Lỗi permission = frappe.throw(..., frappe.PermissionError).

Invariant BR-13 (count == rows): khi không phân trang, len(data) == total_count.
total_count đếm DƯỚI permission của user (frappe.get_list tôn trọng DocPerm) — KHÔNG dùng
frappe.db.count (bỏ qua permission). R2 chưa wiring permission_query_conditions (ADR-M01-05),
nhưng cách đếm này giữ contract count==rows khi M14/R3 thêm data-scope.
"""

import frappe
from frappe import _

HOSPITAL_DOCTYPE = "AntMed Hospital"
DOCTOR_DOCTYPE = "AntMed Doctor"

# Field item trả về cho list endpoint (hợp đồng với FE — Hyrum: đổi = breaking binding).
HOSPITAL_LIST_FIELDS = ["name", "hospital_name", "rank", "contract_status", "tax_code"]
DOCTOR_LIST_FIELDS = ["name", "full_name", "specialty", "hospital", "phone"]
# Field bác sỹ con trong "mặt 360" của bệnh viện (đúng acceptance get_hospital).
HOSPITAL_DOCTOR_FIELDS = ["name", "full_name", "specialty", "phone"]


def _coerce_filters(filters: dict | str | None) -> list:
	"""Chuẩn hoá filters về list điều kiện. FE/GET truyền dict hoặc JSON-string."""
	if not filters:
		return []
	if isinstance(filters, str):
		filters = frappe.parse_json(filters) or []
	if isinstance(filters, dict):
		# dict {field: value} → list [[field, "=", value]] để gộp được điều kiện search.
		return [[k, "=", v] for k, v in filters.items()]
	return list(filters)


@frappe.whitelist(methods=["GET"])
def list_hospitals(
	filters: dict | str | None = None,
	start: int = 0,
	page_length: int = 20,
	search: str | None = None,
) -> dict:
	"""List bệnh viện. Trả RAW dict {data: list[dict], total_count: int}.

	- search: lọc theo hospital_name (LIKE %search%).
	- page_length=0 → không phân trang (lấy hết khớp filter); khi đó len(data)==total_count.
	- total_count đếm DƯỚI permission user (get_list) → giữ invariant count==rows kể cả khi
	  R3 thêm permission_query_conditions.
	"""
	conditions = _coerce_filters(filters)
	if search:
		conditions.append(["hospital_name", "like", f"%{search}%"])

	start = max(0, int(start))
	page_length = max(0, int(page_length))

	data = frappe.get_list(
		HOSPITAL_DOCTYPE,
		filters=conditions,
		fields=HOSPITAL_LIST_FIELDS,
		limit_start=start,
		limit_page_length=page_length or 0,  # 0 = không giới hạn
		order_by="modified desc",
	)
	# total_count = tổng khớp filter, đếm dưới permission (pluck name, không limit).
	total_count = len(
		frappe.get_list(
			HOSPITAL_DOCTYPE,
			filters=conditions,
			pluck="name",
			limit_page_length=0,
		)
	)
	return {"data": data, "total_count": total_count}


@frappe.whitelist(methods=["GET"])
def get_hospital(name: str) -> dict:
	"""Mặt 360 của bệnh viện: field BV + danh sách bác sỹ thuộc BV (children).

	throw PermissionError nếu user không read được hồ sơ này.
	"""
	if not frappe.has_permission(HOSPITAL_DOCTYPE, "read", doc=name):
		frappe.throw(_("Bạn không có quyền xem hồ sơ bệnh viện này."), frappe.PermissionError)

	doc = frappe.get_doc(HOSPITAL_DOCTYPE, name).as_dict()
	result = {
		"name": doc.get("name"),
		"hospital_code": doc.get("hospital_code"),
		"hospital_name": doc.get("hospital_name"),
		"rank": doc.get("rank"),
		"tax_code": doc.get("tax_code"),
		"address": doc.get("address"),
		"contract_status": doc.get("contract_status"),
	}
	result["doctors"] = frappe.get_list(
		DOCTOR_DOCTYPE,
		filters={"hospital": name},
		fields=HOSPITAL_DOCTOR_FIELDS,
		order_by="full_name asc",
		limit_page_length=0,
	)
	return result


@frappe.whitelist(methods=["GET"])
def list_doctors(
	filters: dict | str | None = None,
	hospital: str | None = None,
	start: int = 0,
	page_length: int = 20,
) -> dict:
	"""List bác sỹ. Trả RAW dict {data, total_count}. hospital = lọc nhanh theo 1 BV."""
	conditions = _coerce_filters(filters)
	if hospital:
		conditions.append(["hospital", "=", hospital])

	start = max(0, int(start))
	page_length = max(0, int(page_length))

	data = frappe.get_list(
		DOCTOR_DOCTYPE,
		filters=conditions,
		fields=DOCTOR_LIST_FIELDS,
		limit_start=start,
		limit_page_length=page_length or 0,
		order_by="modified desc",
	)
	total_count = len(
		frappe.get_list(
			DOCTOR_DOCTYPE,
			filters=conditions,
			pluck="name",
			limit_page_length=0,
		)
	)
	return {"data": data, "total_count": total_count}


@frappe.whitelist(methods=["GET"])
def get_doctor(name: str) -> dict:
	"""Profile bác sỹ + hospital_name resolve qua Link (link ngược về BV).

	throw PermissionError nếu user không read được.
	"""
	if not frappe.has_permission(DOCTOR_DOCTYPE, "read", doc=name):
		frappe.throw(_("Bạn không có quyền xem hồ sơ bác sỹ này."), frappe.PermissionError)

	doc = frappe.get_doc(DOCTOR_DOCTYPE, name).as_dict()
	result = {
		"name": doc.get("name"),
		"doctor_code": doc.get("doctor_code"),
		"full_name": doc.get("full_name"),
		"hospital": doc.get("hospital"),
		"hospital_name": None,
		"specialty": doc.get("specialty"),
		"birthday": doc.get("birthday"),
		"phone": doc.get("phone"),
		"email": doc.get("email"),
		"zalo": doc.get("zalo"),
		"notes": doc.get("notes"),
	}
	# LL-BE-2 + LL-BE-5: enrich *_name, null-guard FK orphan.
	if doc.get("hospital"):
		result["hospital_name"] = frappe.db.get_value(
			HOSPITAL_DOCTYPE, doc.get("hospital"), "hospital_name"
		)
	return result
