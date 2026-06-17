# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M11 Dashboard — endpoint số liệu điều hành (A1 Dashboard).

Đường gọi: antmed_crm.api.antmed.dashboard.<fn>  (xem AntMed_CRM_UI_Design.md §1 mockup A1).
M11 là module API-only (KHÔNG có doctype riêng) — chỉ tổng hợp/đếm từ doctype có sẵn.

Mọi hàm @frappe.whitelist(methods=["GET"]), type-annotated
(require_type_annotated_api_methods), trả RAW dict (KHÔNG envelope _ok/_err).

Slice 2: chỉ trả 2 KPI có nguồn dữ liệu THẬT — số bệnh viện + số bác sỹ.
Các KPI khác trong mockup A1 (doanh thu / quota / SLA / bộ DC lưu hành / Top 10 BV /
pipeline / cảnh báo) CHƯA có module nguồn → FE render placeholder "Chưa có dữ liệu",
endpoint KHÔNG bịa số. Thêm key khi module nguồn (M02/M04/M05/M08/M09) land.

Invariant đếm-dưới-permission (giữ contract count==rows như customer.py):
  count = len(frappe.get_list(..., pluck="name", limit_page_length=0))
frappe.get_list TÔN TRỌNG DocPerm + (R3) permission_query_conditions — KHÔNG dùng
frappe.db.count (bỏ qua permission → leak số đếm vượt phạm vi user).
"""

import frappe

HOSPITAL_DOCTYPE = "AntMed Hospital"
DOCTOR_DOCTYPE = "AntMed Doctor"


def _count_under_permission(doctype: str) -> int:
	"""Đếm số bản ghi user ĐƯỢC PHÉP đọc của 1 doctype.

	Dùng get_list (permission-respecting) thay db.count (bỏ qua permission).
	User thiếu read-perm → Frappe raise PermissionError ở DatabaseQuery → ta nuốt
	về 0 (KHÔNG leak: không có quyền = thấy 0, không phải tổng toàn hệ thống).
	"""
	try:
		return len(
			frappe.get_list(doctype, pluck="name", limit_page_length=0)
		)
	except frappe.PermissionError:
		return 0


@frappe.whitelist(methods=["GET"])
def overview() -> dict:
	"""Số liệu tổng quan dashboard A1. Trả RAW dict {hospital_count, doctor_count}.

	Cả 2 count đếm DƯỚI permission của user (get_list) — giữ invariant count==rows
	khi M14/R3 thêm permission_query_conditions (BR-13: NV chỉ thấy BV được giao).
	"""
	return {
		"hospital_count": _count_under_permission(HOSPITAL_DOCTYPE),
		"doctor_count": _count_under_permission(DOCTOR_DOCTYPE),
	}
