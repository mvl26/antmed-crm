# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M09 Slice M09-1 — endpoint Hoa hồng NV (Kế toán, read-only).

Đường gọi: antmed_crm.api.antmed.finance.<fn>  (xem m09_orders_ar.md §Frontend / mockup F2).
Module API-only — KHÔNG có doctype riêng, KHÔNG module mới, KHÔNG per-category bonus engine.
Rollup/gộp từ CRM Deal có sẵn (deal_owner × deal_value × status × closed_date).

commission_summary() — 2 card header màn /antmed/finance/commission (mockup F2):
  card trái "Tổng hoa hồng kỳ" + card phải "Quy tắc kỳ".
  Tổng hoa hồng kỳ = SUM(deal_value × FLAT_RATE) trên CRM Deal status type 'Won' & closed_date
  trong THÁNG HIỆN TẠI [get_first_day .. get_last_day].

Mọi hàm @frappe.whitelist(methods=["GET"]), trả RAW dict (KHÔNG envelope _ok/_err, KHÔNG bọc
{ data, total_count }). FE đọc r.data.<key> TRỰC TIẾP.

Fail-closed BR-13: user thiếu read-perm CRM Deal → frappe.get_list raise PermissionError →
trả _empty_commission() (mọi số = 0, rules giữ nguyên), KHÔNG raise, KHÔNG leak, KHÔNG 500.

KHÔNG raw SQL / KHÔNG f-string injection: chỉ get_list/get_all (filters list/dict), gộp ở Python.
"""

import frappe
from frappe import _

DEAL_DOCTYPE = "CRM Deal"
DEAL_STATUS_DOCTYPE = "CRM Deal Status"

# Field CRM Deal đọc cho rollup hoa hồng (chỉ field cần — KHÔNG lấy toàn bộ cột, KHÔNG lộ email).
DEAL_FIELDS = ["deal_owner", "deal_value", "status", "closed_date"]

# Tỷ lệ hoa hồng PHẲNG (flat) áp cho mọi Deal Won (M09-1 — KHÔNG per-category bonus engine).
# 2,5% doanh thu Won đóng trong kỳ. total_commission = round(SUM(deal_value Won kỳ) × FLAT_RATE, 0).
# COMMISSION_RULES chỉ MÔ TẢ quy tắc kỳ (render card "Quy tắc kỳ") — KHÔNG dùng để tính per-category
# ở slice này (engine per-category là vòng sau). FE render rules từ data THẬT (KHÔNG hardcode JSX).
FLAT_RATE = 0.025

# Quy tắc kỳ (mô tả) — list dict {label, rate_pct} render ở card "Quy tắc kỳ" (mockup F2).
# group_count = len(COMMISSION_RULES) = số "nhóm vật tư" hiển thị ở dòng phụ card trái. M09-1 chỉ
# MÔ TẢ (KHÔNG áp per-category vào công thức tính); mở rộng per-category bonus engine ở vòng sau.
COMMISSION_RULES = (
	{"label": "Chỉ PT", "rate_pct": 3.0},
	{"label": "Dao mổ", "rate_pct": 2.0},
	{"label": "Lưới", "rate_pct": 4.0},
	{"label": "Tiêu hao", "rate_pct": 1.5},
)

# Shape RAW dict (Hyrum — FROZEN; đổi = breaking FE bind AntmedCommissionPage 2 card F2).
COMMISSION_SUMMARY_KEYS = (
	"total_commission",
	"total_revenue",
	"rep_count",
	"group_count",
	"period_label",
	"flat_rate_pct",
	"currency",
	"rules",
)
COMMISSION_CURRENCY = "VND"


def _period_label(d) -> str:
	"""Nhãn kỳ 'T<m>/<yyyy>' (vd T6/2026) — khớp regex 'T\\d{1,2}/\\d{4}' (acceptance M09-1)."""
	return f"T{d.month}/{d.year:04d}"


def _rules() -> list[dict]:
	"""Bản sao mutable của COMMISSION_RULES (FE/test không mutate hằng module)."""
	return [dict(r) for r in COMMISSION_RULES]


def _empty_commission(period_label: str) -> dict:
	"""Fail-closed / kỳ rỗng: mọi số = 0, rules GIỮ NGUYÊN (mô tả quy tắc độc lập với deal).

	KHÔNG raise, KHÔNG leak (BR-13). period_label LUÔN hợp lệ (FE bind dòng phụ card).
	"""
	rules = _rules()
	return {
		"total_commission": 0,
		"total_revenue": 0,
		"rep_count": 0,
		"group_count": len(rules),
		"period_label": period_label,
		"flat_rate_pct": round(FLAT_RATE * 100, 2),
		"currency": COMMISSION_CURRENCY,
		"rules": rules,
	}


def _won_statuses() -> set[str]:
	"""Tập tên CRM Deal Status có type == 'Won' (cấu hình) — dùng PHÂN LOẠI deal.status ở Python.

	get_all trên doctype cấu hình (KHÔNG bị data-scope NV) — chỉ để biết status nào là 'Won'.
	"""
	rows = frappe.get_all(DEAL_STATUS_DOCTYPE, filters={"type": "Won"}, pluck="name", limit_page_length=0)
	return set(rows)


@frappe.whitelist(methods=["GET"])
def commission_summary(period: str | None = None) -> dict:
	"""Tổng hoa hồng kỳ + quy tắc kỳ (mockup F2 "Hoa hồng Nhân viên", Kế toán) — RAW dict.

	Trả RAW dict shape ổn định 8 key (Hyrum — COMMISSION_SUMMARY_KEYS):
	  {
	    "total_commission": number,   # round(SUM(deal_value × FLAT_RATE) Won kỳ, 0) — VND
	    "total_revenue": number,      # SUM(deal_value) Won closed_date trong kỳ
	    "rep_count": int,             # số deal_owner phân biệt có Won trong kỳ
	    "group_count": int,           # số nhóm trong quy tắc kỳ = len(rules)
	    "period_label": "T<m>/<yyyy>",
	    "flat_rate_pct": number,      # FLAT_RATE × 100 (vd 5.0)
	    "currency": "VND",
	    "rules": [{ "label": str, "rate_pct": number }],
	  }

	period: tham số tuỳ chọn (reserved — M09-1 LUÔN dùng tháng hiện tại). Nhận để FE/BE không vỡ
	signature khi mở rộng chọn kỳ; hiện bỏ qua giá trị, kỳ = THÁNG HIỆN TẠI.

	Kỳ = [get_first_day(nowdate()) .. get_last_day(nowdate())]. So khớp closed_date dạng chuỗi ISO.

	BATCH (KHÔNG N+1): 1 get_list CRM Deal (permission-respecting, fail-closed) + gộp ở Python.
	KHÔNG raw SQL.

	Fail-closed BR-13: user KHÔNG read-perm CRM Deal → frappe.get_list raise PermissionError →
	trả _empty_commission (zero, rules giữ nguyên, KHÔNG raise, KHÔNG leak, KHÔNG 500).
	"""
	from frappe.utils import get_first_day, get_last_day, getdate, nowdate

	this_month = getdate(nowdate())
	period_label = _period_label(this_month)
	# Cửa sổ kỳ = tháng hiện tại [đầu tháng .. cuối tháng], so khớp closed_date dạng chuỗi ISO.
	month_start = str(get_first_day(nowdate()))
	month_end = str(get_last_day(nowdate()))

	# Đọc deal DƯỚI permission (fail-closed). Lỗi quyền → empty (KHÔNG raise, KHÔNG leak số).
	try:
		deals = frappe.get_list(DEAL_DOCTYPE, fields=DEAL_FIELDS, limit_page_length=0)
	except frappe.PermissionError:
		return _empty_commission(period_label)

	won_statuses = _won_statuses()

	total_revenue = 0
	owners: set[str] = set()
	for d in deals:
		if d.get("status") not in won_statuses:
			continue
		closed = d.get("closed_date")
		# Chỉ tính Won closed_date trong THÁNG HIỆN TẠI (Won tháng trước/Open/Lost bị loại).
		if not closed or not (month_start <= str(closed) <= month_end):
			continue
		total_revenue += d.get("deal_value") or 0
		owner = d.get("deal_owner")
		if owner:
			owners.add(owner)

	total_commission = round(total_revenue * FLAT_RATE, 0)
	rules = _rules()
	return {
		"total_commission": total_commission,
		"total_revenue": total_revenue,
		"rep_count": len(owners),
		"group_count": len(rules),
		"period_label": period_label,
		"flat_rate_pct": round(FLAT_RATE * 100, 2),
		"currency": COMMISSION_CURRENCY,
		"rules": rules,
	}
