# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M11 Dashboard — endpoint số liệu điều hành (A1 Dashboard).

Đường gọi: antmed_crm.api.antmed.dashboard.<fn>  (xem AntMed_CRM_UI_Design.md §1 mockup A1).
M11 là module API-only (KHÔNG có doctype riêng) — chỉ tổng hợp/đếm từ doctype có sẵn.

Mọi hàm @frappe.whitelist(methods=["GET"]), type-annotated
(require_type_annotated_api_methods), trả RAW dict (KHÔNG envelope _ok/_err).

KPI có nguồn dữ liệu THẬT (KHÔNG bịa số):
  - overview()        — số bệnh viện + số bác sỹ (M01 land).
  - quota_summary()   — quota đã dùng (avg) + đếm HĐ >90% + cảnh báo điều hành (M02 land):
      gộp từ contract.get_contract_health (cùng SSoT ngưỡng/màu — KHÔNG lặp công thức),
      thay 2 placeholder 'Quota đã dùng' + 'Cảnh báo điều hành' trên Dashboard A1.
  - tender_pipeline() — funnel 5 tầng "Pipeline gói thầu" (A1 Hàng 3, M08 land): đếm SỐ THẬT
      từ status CRM Lead (lead/survey) + CRM Deal (quote/bid/won) — thay placeholder pipeline.
Các KPI còn lại trong mockup A1 (doanh thu / SLA / bộ DC lưu hành) CHƯA có module nguồn →
FE render placeholder "Chưa có dữ liệu", endpoint KHÔNG bịa số. Thêm key khi nguồn (M04/M05/M09) land.

Invariant đếm-dưới-permission (giữ contract count==rows như customer.py):
  count = len(frappe.get_list(..., pluck="name", limit_page_length=0))
frappe.get_list TÔN TRỌNG DocPerm + (R3) permission_query_conditions — KHÔNG dùng
frappe.db.count (bỏ qua permission → leak số đếm vượt phạm vi user).
"""

import frappe

from antmed_crm.api.antmed import contract as contract_api

HOSPITAL_DOCTYPE = "AntMed Hospital"
DOCTOR_DOCTYPE = "AntMed Doctor"

# Ngưỡng KPI quota (khớp mockup A1 + ngưỡng health_color M02 §7).
QUOTA_OVER_90 = 90  # HĐ "căng" — quota_used_pct >= 90 (inclusive).
ALERTS_CAP = 6  # tối đa số pill cảnh báo điều hành hiển thị (mockup A1).

# health_color (M02 §7) → severity pill A1: đỏ = danger, cam = warn. Xanh KHÔNG cảnh báo.
_HEALTH_SEVERITY = {"red": "danger", "orange": "warn"}

LEAD_DOCTYPE = "CRM Lead"
DEAL_DOCTYPE = "CRM Deal"

# Funnel "Pipeline gói thầu" (mockup A1 Hàng 3) — 5 tầng đếm SỐ THẬT từ status CRM Lead/Deal.
#   key/label = contract Hyrum (FE phụ thuộc THỨ TỰ + nhãn VI) — KHÔNG đổi tuỳ tiện.
#   doctype/statuses = nguồn đếm 1 count-query/tầng (get_list filter status in [...]).
#   Loại trừ Converted/Unqualified/Junk (Lead) + Lost (Deal): chỉ pipeline ĐANG CHẠY + Trúng.
#   (Nhãn status khớp install.py::add_default_lead_statuses / add_default_deal_statuses.)
TENDER_STAGES = (
	{"key": "lead", "label": "Lead", "doctype": LEAD_DOCTYPE, "statuses": ["New", "Contacted", "Nurture"]},
	{"key": "survey", "label": "Khảo sát", "doctype": LEAD_DOCTYPE, "statuses": ["Qualified"]},
	{
		"key": "quote",
		"label": "Báo giá",
		"doctype": DEAL_DOCTYPE,
		"statuses": ["Qualification", "Demo/Making", "Proposal/Quotation"],
	},
	{"key": "bid", "label": "Dự thầu", "doctype": DEAL_DOCTYPE, "statuses": ["Negotiation", "Ready to Close"]},
	{"key": "won", "label": "Trúng", "doctype": DEAL_DOCTYPE, "statuses": ["Won"]},
)

# Export key/label tuple cho test import-assert thứ tự + nhãn (KHÔNG hardcode lại trong test).
TENDER_STAGE_KEYS = tuple(s["key"] for s in TENDER_STAGES)
TENDER_STAGE_LABELS = tuple(s["label"] for s in TENDER_STAGES)


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


def _alert_for(row: dict) -> dict | None:
	"""Map 1 dòng get_contract_health → 1 item cảnh báo A1 (None nếu HĐ xanh).

	Chỉ HĐ health_color đỏ/cam (quota >90% HOẶC sắp hết hạn ≤30 ngày) thành alert.
	type ưu tiên: over_cap (>100%) → expiry (≤30 ngày) → quota (>90%).
	severity theo health_color (đỏ=danger / cam=warn). label = chuỗi VI hiển thị thẳng.
	"""
	severity = _HEALTH_SEVERITY.get(row.get("health_color"))
	if severity is None:  # xanh — không cảnh báo
		return None

	used_pct = row.get("quota_used_pct") or 0
	days = row.get("days_to_expiry")
	hospital = row.get("hospital_name") or row.get("hospital") or row.get("name")

	if used_pct > 100:
		alert_type = "over_cap"
		label = f"{hospital} — vượt trần quota {used_pct:g}%"
	elif days is not None and days <= 30:
		alert_type = "expiry"
		if days < 0:
			label = f"{hospital} — đã quá hạn {abs(days)} ngày"
		else:
			label = f"{hospital} — còn {days} ngày tới hạn"
	else:
		alert_type = "quota"
		label = f"{hospital} — quota {used_pct:g}%"

	return {
		"type": alert_type,
		"severity": severity,
		"contract": row.get("name"),
		"label": label,
	}


@frappe.whitelist(methods=["GET"])
def quota_summary() -> dict:
	"""KPI quota + cảnh báo điều hành (mockup A1) — gộp từ get_contract_health (M02).

	Trả RAW dict đúng 3 key:
	  - avg_quota_used_pct (float)      = trung bình quota_used_pct trên các HĐ user
	      ĐƯỢC PHÉP đọc, làm tròn 2 chữ số; rỗng → 0.0 (KHÔNG chia 0, KHÔNG NaN).
	  - contracts_over_90_count (int)   = số HĐ có quota_used_pct >= 90 trong phạm vi
	      permission user (đếm DƯỚI permission — KHÔNG leak số toàn hệ thống).
	  - alerts (list, ≤6)               = HĐ health_color đỏ/cam, danger trước warn;
	      mỗi item {type,severity,contract,label}; rỗng → [] (mảng trống, không null).

	Data-scope (BR-13): get_contract_health dùng get_list (tôn trọng DocPerm +
	permission_query_conditions). User KHÔNG read AntMed Contract → data rỗng/PermissionError
	→ avg=0.0, count=0, alerts=[] (fail-closed, không lộ số toàn hệ thống).
	"""
	try:
		rows = contract_api.get_contract_health(page_length=0)["data"]
	except frappe.PermissionError:
		# Mù-quyền: trả số 0/rỗng thay vì lộ tổng toàn hệ thống.
		return {"avg_quota_used_pct": 0.0, "contracts_over_90_count": 0, "alerts": []}

	pcts = [(r.get("quota_used_pct") or 0) for r in rows]
	avg_quota_used_pct = round(sum(pcts) / len(pcts), 2) if pcts else 0.0
	contracts_over_90_count = sum(1 for p in pcts if p >= QUOTA_OVER_90)

	# Cảnh báo: chỉ HĐ đỏ/cam; danger (đỏ) trước warn (cam); cắt còn ≤6.
	alerts = [a for a in (_alert_for(r) for r in rows) if a is not None]
	alerts.sort(key=lambda a: 0 if a["severity"] == "danger" else 1)
	alerts = alerts[:ALERTS_CAP]

	return {
		"avg_quota_used_pct": avg_quota_used_pct,
		"contracts_over_90_count": contracts_over_90_count,
		"alerts": alerts,
	}


def _count_status_under_permission(doctype: str, statuses: list[str]) -> int:
	"""Đếm số bản ghi 1 doctype có status ∈ statuses, ĐẾM DƯỚI permission user.

	1 count-query/tầng (get_list filter status in [...], pluck name) — KHÔNG raw SQL,
	KHÔNG loop per-row (no N+1). User thiếu read-perm → Frappe raise PermissionError ở
	DatabaseQuery → nuốt về 0 (fail-soft, mirror _count_under_permission của overview:
	không quyền = thấy 0, KHÔNG lộ tổng toàn hệ thống — BR-13).
	"""
	try:
		return len(
			frappe.get_list(
				doctype,
				filters={"status": ["in", statuses]},
				pluck="name",
				limit_page_length=0,
			)
		)
	except frappe.PermissionError:
		return 0


@frappe.whitelist(methods=["GET"])
def tender_pipeline() -> dict:
	"""Funnel "Pipeline gói thầu" (A1 Hàng 3, M08) — RAW dict {stages, total}.

	stages = list 5 phần tử ĐÚNG thứ tự + nhãn VI (Lead→Khảo sát→Báo giá→Dự thầu→Trúng);
	mỗi item {key, label, count} với count = SỐ THẬT đếm từ status CRM Lead/Deal (xem
	TENDER_STAGES — lead/survey từ CRM Lead, quote/bid/won từ CRM Deal). total = SUM(count).

	Đếm fail-soft tôn trọng permission (BR-13): mỗi tầng 1 count-query qua get_list
	(_count_status_under_permission) — user thiếu read-perm Lead/Deal → tầng đó count=0,
	KHÔNG raise (mirror overview). ≤5 query (1/tầng), KHÔNG raw SQL, KHÔNG loop per-row.
	"""
	stages = [
		{
			"key": s["key"],
			"label": s["label"],
			"count": _count_status_under_permission(s["doctype"], s["statuses"]),
		}
		for s in TENDER_STAGES
	]
	return {"stages": stages, "total": sum(s["count"] for s in stages)}
