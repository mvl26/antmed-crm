# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M10 KPI lai / Điều phối đội ngũ (Trưởng phòng KD) — endpoint roster + bảng điều phối + hồ sơ NV.

Module API-only — KHÔNG có doctype riêng; rollup/nhóm từ CRM Deal có sẵn
(deal_owner × deal_value × status × sla_status × territory × organization × probability).

Bốn endpoint (cả bốn RAW dict, KHÔNG envelope, KHÔNG bọc {data, total_count}):

1) team_roster() — antmed_crm.api.antmed.sales_team.team_roster (GET, mockup B2)
   Roster KPI doanh số tháng/SLA của từng NV kinh doanh. Shape {rows, kpis}. Xem docstring hàm.

4) revenue_by_rep_hospital() — antmed_crm.api.antmed.sales_team.revenue_by_rep_hospital (GET, mockup A3)
   Ma trận heat NV (deal_owner) × Bệnh viện (organization) — doanh thu THẬT = SUM(deal_value) CRM Deal
   status type 'Won'. Shape RAW dict { rows, hospitals, max_cell, grand_total } (Dashboard CEO,
   màn /antmed/revenue). Xem docstring hàm.

3) rep_profile(owner) — antmed_crm.api.antmed.sales_team.rep_profile (GET, mockup B2 left-card)
   Hồ sơ 1 NV kinh doanh (drill-down từ roster B2 click 1 dòng → /antmed/sales/team/:owner).
   Shape RAW dict { profile, kpi, deals }:
     profile = { deal_owner, full_name, joined_on, roles }   # joined_on = User.creation (ngày)
     kpi     = { month_sales, open_deals, total_deals, sla_ontime_pct }   # CÙNG công thức team_roster
     deals   = [{ deal, organization, territory, deal_value, status, probability, status_theme }]
   - deals = CRM Deal của owner đọc DƯỚI permission (get_list filters deal_owner=owner,
     limit_page_length=0), sort DESC deal_value ở Python. name → key 'deal'.
   - status_theme = _status_theme(status): Won → 'ok' / Lost → 'danger' / còn lại (Open/Ongoing) →
     'info' (tái dùng _statuses_of_type Won/Lost — đồng nhất phân loại với team_roster/dispatch).
     FE map status_theme → pillClass (ok/danger/info), KHÔNG tự suy diễn theme.
   - kpi: month_sales = SUM(deal_value) deal Won closed_date trong THÁNG HIỆN TẠI của owner;
     open_deals = deal NOT IN Won∪Lost; total_deals = len(deals); sla_ontime_pct =
     round(100 * (#sla_status != 'Failed') / total, 1) hoặc 100.0 khi total=0 (KHÔNG chia 0).
   - profile.full_name = _full_name(owner) (User.full_name, KHÔNG lộ email; FE chỉ dùng deal_owner
     làm :key + fetch param, KHÔNG render thô). joined_on = User.creation (ngày) — owner không là
     User → None. roles = role nghiệp vụ VI của user (Has Role, lọc bỏ role hệ thống) — [] nếu rỗng.
   - 404-safe: owner không có User record → joined_on None + full_name fallback owner + roles [].
   - BR-13 fail-closed: get_list raise PermissionError → _empty_rep_profile(owner) (kpi zero,
     deals []) — KHÔNG raise, KHÔNG lộ số toàn hệ thống (mirror team_roster/_empty_result).

2) dispatch_board() — antmed_crm.api.antmed.sales_team.dispatch_board (GET, mockup B1)
   Kanban READ-ONLY pipeline gói thầu: group CRM Deal theo CRM Deal Status thành lane,
   CHỈ lane có status type ∈ DISPATCH_LANE_TYPES ('Open','Ongoing','Won') — LOẠI 'Lost'.
   Lanes sort tăng theo position (Qualification → … → Won). Cards mỗi lane sort desc deal_value.
   Shape RAW dict:
     { lanes: [{ status, type, label, position, count, cards:[
                  { deal, organization, territory, deal_owner_name, deal_value,
                    probability, bar_theme } ] }],   # cards sort DESC deal_value; count=len(cards)
       totals: { total_deals, open_value, won_value } }
   - lanes = CRM Deal Status (get_all fields name/type/position/color/deal_status, order_by position),
     LỌC type ∈ DISPATCH_LANE_TYPES; label = deal_status (nhãn VI cấu hình) fallback name.
   - cards = CRM Deal đọc DƯỚI permission (get_list, limit_page_length=0), group ở Python theo status.
     Deal status KHÔNG thuộc lane nào (vd Lost) bị BỎ khỏi board (không lên total).
   - deal_owner_name = _full_name(deal_owner) — KHÔNG lộ email (FE chỉ dùng deal làm :key).
   - bar_theme = _prob_theme(probability): green>=70 / warn>=40 / danger (ngưỡng PROB_GREEN/PROB_WARN).
   - totals: total_deals = tổng card render; open_value = SUM deal_value lane type Open/Ongoing;
     won_value = SUM deal_value lane type Won.
   - BR-13 fail-closed: get_list raise PermissionError → _empty_dispatch() (lanes=[] + totals zero),
     KHÔNG raise, KHÔNG lộ số toàn hệ thống.

team_roster() — chi tiết:

team_roster() trả RAW dict (KHÔNG envelope):
  { rows: [{ deal_owner, full_name, territory, month_sales, open_deals,
             sla_ontime_pct, sales_pct, bar_theme, alert }] (sort desc month_sales),
    kpis: { total_reps, total_month_sales, avg_sla } }

Nguồn roster = HỢP của:
  - NV có Role 'NV kinh doanh' (kể cả 0 deal → month_sales=0, vẫn xuất hiện).
  - deal_owner phân biệt có deal trong phạm vi user ĐƯỢC PHÉP đọc (get_list permission-respecting).

month_sales = SUM(deal_value) deal status type 'Won' & closed_date trong THÁNG HIỆN TẠI.
open_deals  = số deal status type NOT IN (Won, Lost).
sla_ontime_pct = 100 * (số deal sla_status != 'Failed') / (tổng deal); 0 deal → 100.0 (không phạt).
sales_pct  = 100 * month_sales / max(month_sales toàn đội); max==0 → 0.0 (không chia 0).
bar_theme  = green (>=70) / warn (>=50) / danger (<50) theo ngưỡng 70/50.
alert      = 'DS thấp' khi sales_pct < 50, ngược lại '' (chip rỗng).

Data-scope (BR-13) fail-closed: user thiếu read-perm CRM Deal → get_list raise PermissionError →
nuốt về rows=[] + kpis zero (KHÔNG raise, KHÔNG lộ số toàn hệ thống) — mirror dashboard.overview.

KHÔNG raw SQL / KHÔNG f-string injection: chỉ get_list/get_all (filters list/dict), gộp ở Python.
Đọc field cụ thể qua fields=[...] (KHÔNG lấy toàn bộ cột).
"""

import frappe

from antmed_crm.api.antmed.rbac import ANTMED_ALLOWED_ROLES

DEAL_DOCTYPE = "CRM Deal"
DEAL_STATUS_DOCTYPE = "CRM Deal Status"
SALES_ROLE = "NV kinh doanh"

# Allow-list role NGHIỆP VỤ thuộc PHẠM VI AntMed CRM = 3 role AntMed + role sales CRM gốc.
# Whitelist → "Hồ sơ NV" CHỈ hiện role AntMed/CRM, LOẠI SẠCH role của app khác cài cùng bench
# (AssetCore / Norm / WFC / Calibration…) + role hệ thống. AntMed CRM = app RIÊNG, không lẫn module khác.
PROFILE_BUSINESS_ROLES = frozenset(
	set(ANTMED_ALLOWED_ROLES) | {"Sales Master Manager", "Sales Manager", "Sales User"}
)

# Ngưỡng % doanh số (so với đỉnh đội) → theme thanh bar (mockup B2).
SALES_PCT_GREEN = 70  # >=70 → green
SALES_PCT_WARN = 50  # >=50 → warn ; <50 → danger + cảnh báo 'DS thấp'
ALERT_LOW_SALES = "DS thấp"

# Field CRM Deal đọc cho rollup (chỉ field cần — KHÔNG lấy toàn bộ cột).
DEAL_FIELDS = ["deal_owner", "deal_value", "status", "sla_status", "territory", "closed_date"]
SLA_FAILED = "Failed"

# Hyrum contract — FE (createResource đọc r.data.{rows,kpis}) + test phụ thuộc THỨ TỰ + tên key.
# Export để test assert shape (KHÔNG hardcode lại) + làm SSoT key khi build row/kpis (chống drift).
# Đổi/đảo key = breaking FE → KHÔNG tuỳ tiện.
ROSTER_ROW_KEYS = (
	"deal_owner",
	"full_name",
	"territory",
	"month_sales",
	"open_deals",
	"sla_ontime_pct",
	"sales_pct",
	"bar_theme",
	"alert",
)
ROSTER_KPI_KEYS = ("total_reps", "total_month_sales", "avg_sla")

# ── M10-3 "Hồ sơ NV kinh doanh" (mockup B2 left-card) — rep_profile(owner) ───
# Hyrum contract — FE (createResource đọc r.data.{profile,kpi,deals}) + test phụ thuộc THỨ TỰ +
# tên key. Export làm SSoT (chống drift FE/test). Đổi/đảo key = breaking FE → KHÔNG tuỳ tiện.
REP_PROFILE_PROFILE_KEYS = ("deal_owner", "full_name", "joined_on", "roles")
REP_PROFILE_KPI_KEYS = ("month_sales", "open_deals", "total_deals", "sla_ontime_pct")
REP_PROFILE_DEAL_KEYS = (
	"deal",
	"organization",
	"territory",
	"deal_value",
	"status",
	"probability",
	"status_theme",
)

# Role hệ thống KHÔNG render trong "Hồ sơ NV" (chỉ giữ role nghiệp vụ VI). Tránh bịa 'Phòng/Cấp'.
SYSTEM_ROLES = frozenset(
	{
		"All",
		"Guest",
		"Administrator",
		"System Manager",
		"Desk User",
		"Report Manager",
		"Workspace Manager",
		"Dashboard Manager",
		"Newsletter Manager",
		"Knowledge Base Editor",
		"Knowledge Base Contributor",
		"Inbox User",
		"Blogger",
		"Website Manager",
		"Prepared Report User",
	}
)

# ── M10-2 "Bảng điều phối" (mockup B1) — pipeline kanban read-only ───────────
# Lane = CRM Deal Status có type ∈ DISPATCH_LANE_TYPES. LOẠI 'Lost' khỏi board.
DISPATCH_LANE_TYPES = ("Open", "Ongoing", "Won")

# Ngưỡng probability → theme thanh khả năng chốt deal (mockup B1 card).
PROB_GREEN = 70  # >=70 → green
PROB_WARN = 40  # >=40 → warn ; <40 → danger

# Hyrum contract — FE (createResource đọc r.data.{lanes,totals}) + test phụ thuộc THỨ TỰ + tên key.
# Export làm SSoT (chống drift FE/test). Đổi/đảo key = breaking FE → KHÔNG tuỳ tiện.
DISPATCH_LANE_KEYS = ("status", "type", "label", "position", "count", "cards")
DISPATCH_CARD_KEYS = (
	"deal",
	"organization",
	"territory",
	"deal_owner_name",
	"deal_value",
	"probability",
	"bar_theme",
)
DISPATCH_TOTAL_KEYS = ("total_deals", "open_value", "won_value")

# Field CRM Deal đọc cho bảng "Khách hàng phụ trách" (KHÔNG lấy deal_owner → không lộ email FE).
REP_PROFILE_DEAL_FIELDS = [
	"name",
	"organization",
	"territory",
	"deal_value",
	"status",
	"probability",
	"sla_status",
	"closed_date",
]

# Theme chip trạng thái deal (mockup B2) theo status type — FE map status_theme → pillClass.
# Won → 'ok' (xanh) / Lost → 'danger' (đỏ) / còn lại (Open/Ongoing) → 'info' (xanh dương).
REP_STATUS_THEME_WON = "ok"
REP_STATUS_THEME_LOST = "danger"
REP_STATUS_THEME_OPEN = "info"

# Fallback hiển thị khi field null (FE cũng có fallback; BE giữ null → FE quyết hiển thị).
# (organization/territory null → FE render '— Chưa có tổ chức —' / '—'.)

# ── M02-10 "Doanh thu theo NV Kinh doanh × Bệnh viện" (mockup A3, Dashboard CEO) ─
# Ma trận heat NV (deal_owner) × Bệnh viện (organization), doanh thu = SUM(deal_value) Won.
# HEAT_LEVELS = 4 mức màu tương đối trên max_cell (mockup .h2c..h5c — Thấp/TB/Cao/Rất cao).
# Export SSoT để FE/test map cùng 1 bộ class (chống drift). Thứ tự tăng dần độ đậm.
HEAT_LEVELS = ("h2c", "h3c", "h4c", "h5c")

# Ngưỡng TƯƠNG ĐỐI trên max_cell (mockup): >75% → h5c (rất cao) / >50% → h4c (cao) /
# >25% → h3c (TB) / >0% → h2c (thấp) / =0 hoặc None → None (cell rỗng '—', KHÔNG tô màu).
HEAT_T_VERY_HIGH = 0.75
HEAT_T_HIGH = 0.50
HEAT_T_MED = 0.25

# Hyrum contract — FE (createResource đọc r.data.{rows,hospitals,max_cell,grand_total}) + test phụ
# thuộc THỨ TỰ + tên key. Export làm SSoT (chống drift FE/test). Đổi/đảo key = breaking FE.
REP_HOSP_ROW_KEYS = ("deal_owner", "full_name", "cells", "total")
REP_HOSP_CELL_KEYS = ("hospital", "hospital_label", "value", "heat")
REP_HOSP_TOP_KEYS = ("rows", "hospitals", "max_cell", "grand_total")


def _bar_theme(sales_pct: float) -> str:
	"""Map % doanh số (so với đỉnh đội) → theme bar. Ngưỡng 70/50 (green/warn/danger)."""
	p = sales_pct or 0
	if p >= SALES_PCT_GREEN:
		return "green"
	if p >= SALES_PCT_WARN:
		return "warn"
	return "danger"


def _alert(sales_pct: float) -> str:
	"""Chip cảnh báo: 'DS thấp' khi % doanh số < 50, ngược lại '' (không render chip)."""
	return ALERT_LOW_SALES if (sales_pct or 0) < SALES_PCT_WARN else ""


def _statuses_of_type(types: list[str]) -> set[str]:
	"""Tập tên CRM Deal Status có type ∈ types (Won/Lost/Open/Ongoing/On Hold).

	get_all trên doctype cấu hình (CRM Deal Status) — KHÔNG bị data-scope NV, dùng để PHÂN LOẠI
	status (không phải đọc deal). Trả set tên status (dùng so khớp deal.status ở Python).
	"""
	rows = frappe.get_all(
		DEAL_STATUS_DOCTYPE, filters={"type": ["in", types]}, pluck="name", limit_page_length=0
	)
	return set(rows)


def _sales_rep_users() -> list[str]:
	"""Danh sách email user mang Role 'NV kinh doanh' (enabled). Rỗng nếu role chưa tồn tại."""
	if not frappe.db.exists("Role", SALES_ROLE):
		return []
	rows = frappe.get_all(
		"Has Role",
		filters={"role": SALES_ROLE, "parenttype": "User"},
		pluck="parent",
		limit_page_length=0,
	)
	# Loại user đã disable / user hệ thống (Administrator/Guest) khỏi roster đội ngũ.
	out = []
	for email in set(rows):
		if email in ("Administrator", "Guest"):
			continue
		if frappe.db.get_value("User", email, "enabled"):
			out.append(email)
	return out


def _full_name(email: str) -> str:
	"""Tên hiển thị NV (User.full_name) — KHÔNG lộ email/ID thô. Fallback email khi thiếu."""
	return frappe.db.get_value("User", email, "full_name") or email


def _empty_result() -> dict:
	return {"rows": [], "kpis": {"total_reps": 0, "total_month_sales": 0, "avg_sla": 0.0}}


@frappe.whitelist(methods=["GET"])
def team_roster() -> dict:
	"""Roster KPI đội ngũ NV kinh doanh (mockup B2) — RAW dict {rows, kpis}.

	rows = 1 dòng/NV (sort desc month_sales); kpis = tổng đội. Fail-closed BR-13:
	user thiếu read-perm CRM Deal → rows=[] + kpis zero (KHÔNG raise).
	"""
	from frappe.utils import get_first_day, get_last_day, nowdate

	# 1) Đọc deal DƯỚI permission (fail-closed). Lỗi quyền → roster rỗng (không lộ số).
	try:
		deals = frappe.get_list(DEAL_DOCTYPE, fields=DEAL_FIELDS, limit_page_length=0)
	except frappe.PermissionError:
		return _empty_result()

	won_statuses = _statuses_of_type(["Won"])
	lost_statuses = _statuses_of_type(["Lost"])

	# Cửa sổ tháng hiện tại (theo closed_date) — bao gồm [đầu tháng .. cuối tháng].
	# So khớp dạng chuỗi ISO 'YYYY-MM-DD' (đồng nhất kiểu, tránh date-vs-str compare lỗi).
	month_start = str(get_first_day(nowdate()))
	month_end = str(get_last_day(nowdate()))

	# 2) Gộp theo deal_owner ở Python (KHÔNG N+1 query / KHÔNG raw SQL).
	agg: dict[str, dict] = {}

	def _bucket(owner: str) -> dict:
		if owner not in agg:
			agg[owner] = {
				"month_sales": 0,
				"open_deals": 0,
				"total_deals": 0,
				"sla_ok": 0,
				"territory": None,
			}
		return agg[owner]

	for d in deals:
		owner = d.get("deal_owner")
		if not owner:
			continue
		b = _bucket(owner)
		b["total_deals"] += 1
		if d.get("sla_status") != SLA_FAILED:
			b["sla_ok"] += 1
		if b["territory"] is None and d.get("territory"):
			b["territory"] = d.get("territory")

		status = d.get("status")
		is_won = status in won_statuses
		is_lost = status in lost_statuses
		if not is_won and not is_lost:
			b["open_deals"] += 1

		if is_won:
			closed = d.get("closed_date")
			# closed_date trong tháng hiện tại → cộng vào doanh số tháng.
			if closed and month_start <= str(closed) <= str(month_end):
				b["month_sales"] += d.get("deal_value") or 0

	# 3) Union với NV có role (kể cả 0 deal). NV hệ thống đã được lọc trong _sales_rep_users.
	for email in _sales_rep_users():
		_bucket(email)

	# 4) Chuẩn hoá thành rows + tính sales_pct/bar_theme/alert.
	max_sales = max((b["month_sales"] for b in agg.values()), default=0)
	rows = []
	for owner, b in agg.items():
		sla_pct = round(100 * b["sla_ok"] / b["total_deals"], 1) if b["total_deals"] else 100.0
		sales_pct = round(100 * b["month_sales"] / max_sales, 1) if max_sales else 0.0
		rows.append(
			{
				"deal_owner": owner,
				"full_name": _full_name(owner),
				"territory": b["territory"],
				"month_sales": b["month_sales"],
				"open_deals": b["open_deals"],
				"sla_ontime_pct": sla_pct,
				"sales_pct": sales_pct,
				"bar_theme": _bar_theme(sales_pct),
				"alert": _alert(sales_pct),
			}
		)

	# 5) Sort desc theo doanh số tháng (mockup B2 — NV mạnh nhất lên đầu).
	rows.sort(key=lambda r: r["month_sales"], reverse=True)

	total_reps = len(rows)
	total_month_sales = sum(r["month_sales"] for r in rows)
	avg_sla = round(sum(r["sla_ontime_pct"] for r in rows) / total_reps, 1) if total_reps else 0.0

	return {
		"rows": rows,
		"kpis": {
			"total_reps": total_reps,
			"total_month_sales": total_month_sales,
			"avg_sla": avg_sla,
		},
	}


# ════════════════════════════════════════════════════════════════════════════
# M10-2 "Bảng điều phối ca giao phòng mổ" (mockup B1) — dispatch_board()
# ════════════════════════════════════════════════════════════════════════════


def _prob_theme(probability) -> str:
	"""Map probability (% khả năng chốt deal) → theme thanh card. Ngưỡng 70/40 (green/warn/danger).

	Pure: None/'' → 0 → danger (không vỡ). Không phụ thuộc state ngoài.
	"""
	p = probability or 0
	if p >= PROB_GREEN:
		return "green"
	if p >= PROB_WARN:
		return "warn"
	return "danger"


def _empty_dispatch() -> dict:
	"""Bảng rỗng fail-closed (BR-13): lanes=[] + totals zero — KHÔNG lộ số toàn hệ thống."""
	return {"lanes": [], "totals": {"total_deals": 0, "open_value": 0, "won_value": 0}}


@frappe.whitelist(methods=["GET"])
def dispatch_board() -> dict:
	"""Kanban READ-ONLY pipeline gói thầu (mockup B1) — RAW dict {lanes, totals}.

	lanes = CRM Deal Status type ∈ DISPATCH_LANE_TYPES (Open/Ongoing/Won), sort tăng theo position;
	LOẠI Lost. cards mỗi lane = CRM Deal (DƯỚI permission) group theo status, sort desc deal_value.
	Fail-closed BR-13: thiếu read-perm CRM Deal → lanes=[] + totals zero (KHÔNG raise).
	"""
	# 1) Đọc deal DƯỚI permission (fail-closed). Lỗi quyền → board rỗng (không lộ số).
	try:
		deals = frappe.get_list(
			DEAL_DOCTYPE,
			fields=["name", "organization", "territory", "deal_owner", "deal_value", "status", "probability"],
			limit_page_length=0,
		)
	except frappe.PermissionError:
		return _empty_dispatch()

	# 2) Lane = CRM Deal Status type ∈ DISPATCH_LANE_TYPES, sort tăng theo position.
	#    get_all trên doctype cấu hình (KHÔNG bị data-scope NV) — chỉ để xếp cột + nhãn VI.
	status_rows = frappe.get_all(
		DEAL_STATUS_DOCTYPE,
		filters={"type": ["in", list(DISPATCH_LANE_TYPES)]},
		fields=["name", "type", "position", "deal_status"],
		order_by="position asc",
		limit_page_length=0,
	)

	# 3) Khởi tạo lane theo thứ tự position. status→lane index để group nhanh (KHÔNG N+1).
	lanes = []
	lane_idx: dict[str, int] = {}
	for s in status_rows:
		lane_idx[s["name"]] = len(lanes)
		lanes.append(
			{
				"status": s["name"],
				"type": s["type"],
				# Nhãn VI cấu hình (deal_status) fallback name khi rỗng — header cột mockup B1.
				"label": s.get("deal_status") or s["name"],
				"position": s.get("position") or 0,
				"count": 0,
				"cards": [],
			}
		)

	# 4) Group deal ở Python theo status. Deal status KHÔNG thuộc lane nào (vd Lost) → BỎ.
	for d in deals:
		idx = lane_idx.get(d.get("status"))
		if idx is None:
			continue
		prob = d.get("probability")
		lanes[idx]["cards"].append(
			{
				"deal": d.get("name"),
				"organization": d.get("organization"),
				"territory": d.get("territory"),
				# full_name (KHÔNG lộ email deal_owner) — FE chỉ dùng deal làm :key.
				"deal_owner_name": _full_name(d.get("deal_owner")) if d.get("deal_owner") else "",
				"deal_value": d.get("deal_value") or 0,
				"probability": prob,
				"bar_theme": _prob_theme(prob),
			}
		)

	# 5) Sort cards mỗi lane desc theo deal_value; count = len(cards).
	for lane in lanes:
		lane["cards"].sort(key=lambda c: c["deal_value"] or 0, reverse=True)
		lane["count"] = len(lane["cards"])

	# 6) totals: tổng card render + tách giá trị Open/Ongoing vs Won.
	total_deals = sum(lane["count"] for lane in lanes)
	open_value = sum(
		c["deal_value"] for lane in lanes if lane["type"] in ("Open", "Ongoing") for c in lane["cards"]
	)
	won_value = sum(c["deal_value"] for lane in lanes if lane["type"] == "Won" for c in lane["cards"])

	return {
		"lanes": lanes,
		"totals": {
			"total_deals": total_deals,
			"open_value": open_value,
			"won_value": won_value,
		},
	}


# ════════════════════════════════════════════════════════════════════════════
# M10-3 "Hồ sơ NV kinh doanh" (mockup B2 left-card) — rep_profile(owner)
# ════════════════════════════════════════════════════════════════════════════


def _user_roles(email: str) -> list[str]:
	"""Danh sách role NGHIỆP VỤ AntMed/CRM của user. Rỗng nếu user không tồn tại.

	Đọc qua get_all('Has Role') — KHÔNG raw SQL. WHITELIST theo PROFILE_BUSINESS_ROLES →
	CHỈ giữ role thuộc phạm vi AntMed CRM (3 role AntMed + sales CRM), LOẠI SẠCH role của app
	khác cài cùng bench (AssetCore/Norm/WFC…) + role hệ thống. Tránh "lẫn" module khác.
	"""
	if not email or not frappe.db.exists("User", email):
		return []
	rows = frappe.get_all(
		"Has Role",
		filters={"parent": email, "parenttype": "User"},
		pluck="role",
		limit_page_length=0,
	)
	return sorted({r for r in rows if r in PROFILE_BUSINESS_ROLES})


def _status_theme(status: str, won_statuses: set, lost_statuses: set) -> str:
	"""Theme chip trạng thái deal (mockup B2): Won → 'ok' / Lost → 'danger' / còn lại → 'info'.

	Phân loại theo status type (won_statuses/lost_statuses từ _statuses_of_type — đồng nhất với
	team_roster/dispatch). FE map status_theme → pillClass (KHÔNG tự suy diễn theme).
	"""
	if status in won_statuses:
		return REP_STATUS_THEME_WON
	if status in lost_statuses:
		return REP_STATUS_THEME_LOST
	return REP_STATUS_THEME_OPEN


def _joined_on(email: str):
	"""Ngày vào làm = ngày User.creation (date). None nếu user không tồn tại / chưa có creation.

	getdate(...) trên User.creation (datetime) → date thuần (FE format dd/MM/yyyy). KHÔNG bịa.
	"""
	if not email or not frappe.db.exists("User", email):
		return None
	from frappe.utils import getdate

	created = frappe.db.get_value("User", email, "creation")
	return getdate(created) if created else None


def _empty_rep_kpi() -> dict:
	"""KPI rỗng (fail-closed / owner không deal): month_sales 0 + sla 100.0 (KHÔNG chia 0)."""
	return {"month_sales": 0, "open_deals": 0, "total_deals": 0, "sla_ontime_pct": 100.0}


def _empty_rep_profile(owner: str) -> dict:
	"""Hồ sơ fail-closed BR-13: kpi zero + deals [] — KHÔNG lộ số toàn hệ thống.

	profile vẫn giữ full_name + roles + joined_on (KHÔNG phụ thuộc deal-perm) để FE render card
	hồ sơ tối thiểu. SSoT cho shape rỗng (chống drift FE/test) — mirror team_roster._empty_result.
	"""
	return {
		"profile": {
			"deal_owner": owner,
			"full_name": _full_name(owner),
			"joined_on": _joined_on(owner),
			"roles": _user_roles(owner),
		},
		"kpi": _empty_rep_kpi(),
		"deals": [],
	}


@frappe.whitelist(methods=["GET"])
def rep_profile(owner: str) -> dict:
	"""Hồ sơ 1 NV kinh doanh (mockup B2 left-card) — RAW dict {profile, kpi, deals}.

	Drill-down từ bảng roster (/antmed/sales/team/:owner). kpi TÁI DÙNG ĐÚNG công thức team_roster:
	  month_sales = SUM(deal_value) deal status type 'Won' & closed_date trong THÁNG HIỆN TẠI của owner;
	  open_deals  = số deal status type NOT IN (Won, Lost);
	  total_deals = tổng deal của owner; sla_ontime_pct = 100*(sla_status!='Failed')/total (0 → 100.0).
	  deals = CRM Deal của owner đọc DƯỚI permission (get_list filters deal_owner=owner), sort desc deal_value.

	profile.full_name = User.full_name (KHÔNG lộ email); joined_on = User.creation (date);
	  roles = role nghiệp vụ (loại role hệ thống). Owner không-User → full_name fallback owner,
	  joined_on None, roles [] (404-safe, KHÔNG 500).

	Fail-closed BR-13: get_list raise PermissionError → kpi zero + deals [] (KHÔNG raise, KHÔNG lộ
	  số toàn hệ thống) — mirror team_roster._empty_result. profile minimal vẫn trả full_name + roles.
	"""
	from frappe.utils import get_first_day, get_last_day, nowdate

	# profile KHÔNG phụ thuộc deal-perm — luôn trả được (404-safe cho owner không-User).
	profile = {
		"deal_owner": owner,
		"full_name": _full_name(owner),
		"joined_on": _joined_on(owner),
		"roles": _user_roles(owner),
	}

	# Đọc deal của owner DƯỚI permission (fail-closed). Lỗi quyền → kpi zero + deals [] (không lộ số).
	try:
		deals_raw = frappe.get_list(
			DEAL_DOCTYPE,
			filters={"deal_owner": owner},
			fields=REP_PROFILE_DEAL_FIELDS,
			limit_page_length=0,
		)
	except frappe.PermissionError:
		return _empty_rep_profile(owner)

	won_statuses = _statuses_of_type(["Won"])
	lost_statuses = _statuses_of_type(["Lost"])
	month_start = str(get_first_day(nowdate()))
	month_end = str(get_last_day(nowdate()))

	# kpi rollup ở Python (KHÔNG N+1 / KHÔNG raw SQL) — cùng công thức team_roster.
	month_sales = 0
	open_deals = 0
	sla_ok = 0
	total_deals = len(deals_raw)

	for d in deals_raw:
		if d.get("sla_status") != SLA_FAILED:
			sla_ok += 1
		status = d.get("status")
		is_won = status in won_statuses
		is_lost = status in lost_statuses
		if not is_won and not is_lost:
			open_deals += 1
		if is_won:
			closed = d.get("closed_date")
			if closed and month_start <= str(closed) <= str(month_end):
				month_sales += d.get("deal_value") or 0

	sla_pct = round(100 * sla_ok / total_deals, 1) if total_deals else 100.0

	# deals payload: chỉ field hiển thị (KHÔNG deal_owner → không lộ email). Sort desc deal_value.
	# status_theme do BE quyết (Won/Lost/Open) — FE chỉ map → pillClass, KHÔNG tự suy diễn theme.
	deals = [
		{
			"deal": d.get("name"),
			"organization": d.get("organization"),
			"territory": d.get("territory"),
			"deal_value": d.get("deal_value") or 0,
			"status": d.get("status"),
			"probability": d.get("probability"),
			"status_theme": _status_theme(d.get("status"), won_statuses, lost_statuses),
		}
		for d in deals_raw
	]
	deals.sort(key=lambda c: c["deal_value"] or 0, reverse=True)

	return {
		"profile": profile,
		"kpi": {
			"month_sales": month_sales,
			"open_deals": open_deals,
			"total_deals": total_deals,
			"sla_ontime_pct": sla_pct,
		},
		"deals": deals,
	}


# ════════════════════════════════════════════════════════════════════════════
# M02-10 "Doanh thu theo NV Kinh doanh × Bệnh viện" (mockup A3) — revenue_by_rep_hospital()
# ════════════════════════════════════════════════════════════════════════════


def _heat_level(value, max_cell) -> str | None:
	"""Map giá trị cell → mức màu heat TƯƠNG ĐỐI trên max_cell (mockup A3). PURE.

	Ngưỡng (HEAT_T_*): >75% → 'h5c' (rất cao) / >50% → 'h4c' (cao) / >25% → 'h3c' (TB) /
	>0% → 'h2c' (thấp) / value=0 hoặc None hoặc max_cell<=0 → None (cell rỗng '—', không tô màu).
	Không phụ thuộc state ngoài → unit-test trực tiếp. Không chia khi max_cell<=0 (no ZeroDivision).
	"""
	v = value or 0
	if v <= 0 or not max_cell or max_cell <= 0:
		return None
	ratio = v / max_cell
	if ratio > HEAT_T_VERY_HIGH:
		return "h5c"
	if ratio > HEAT_T_HIGH:
		return "h4c"
	if ratio > HEAT_T_MED:
		return "h3c"
	return "h2c"


def _empty_revenue_by_rep_hospital() -> dict:
	"""Ma trận rỗng fail-closed (BR-13): rows/hospitals [] + max_cell/grand_total 0.

	SSoT cho shape rỗng (chống drift FE/test) — mirror _empty_result/_empty_dispatch/_empty_rep_profile.
	KHÔNG lộ số toàn hệ thống khi user thiếu read-perm CRM Deal.
	"""
	return {"rows": [], "hospitals": [], "max_cell": 0, "grand_total": 0}


@frappe.whitelist(methods=["GET"])
def revenue_by_rep_hospital() -> dict:
	"""Ma trận heat doanh thu NV (deal_owner) × Bệnh viện (organization) — RAW dict (mockup A3).

	Shape { rows, hospitals, max_cell, grand_total }:
	  rows = [{ deal_owner, full_name, cells:[{hospital,hospital_label,value,heat}|null], total }]
	         (sort DESC theo total — NV mạnh nhất lên đầu); cells dài = số cột hospitals (đều cạnh).
	  hospitals = [{ key, label }] — union BV xuất hiện trong các Deal Won, sort theo doanh thu cột DESC.
	  max_cell = giá trị cell lớn nhất (cơ sở ngưỡng heat tương đối); grand_total = SUM mọi total.

	Mỗi cell value = SUM(deal_value) các CRM Deal status type 'Won' của (deal_owner × organization).
	Deal Lost/Open BỊ LOẠI. cell rỗng (không có Deal Won) → None (FE render '—', heat None).
	heat = _heat_level(value, max_cell) (4 mức HEAT_LEVELS). full_name = _full_name (KHÔNG lộ email).
	hospital_label = organization (CRM Organization autoname field:organization_name → name == nhãn BV).

	Gộp deal_owner × organization ở Python từ 1 get_list CRM Deal (KHÔNG N+1, KHÔNG raw SQL).
	Fail-closed BR-13: get_list raise PermissionError → _empty (rows/hospitals []), KHÔNG raise,
	KHÔNG lộ số toàn hệ thống (mirror team_roster/dispatch_board).
	"""
	# 1) Đọc deal DƯỚI permission (fail-closed). Lỗi quyền → ma trận rỗng (không lộ số).
	try:
		deals = frappe.get_list(
			DEAL_DOCTYPE,
			fields=["deal_owner", "organization", "deal_value", "status"],
			limit_page_length=0,
		)
	except frappe.PermissionError:
		return _empty_revenue_by_rep_hospital()

	won_statuses = _statuses_of_type(["Won"])

	# 2) Gộp (owner, hospital) → SUM(deal_value) Won ở Python (KHÔNG N+1 / KHÔNG raw SQL).
	#    matrix[owner][hospital] = tổng; hosp_total[hospital] = tổng cột (để sort cột).
	matrix: dict[str, dict[str, float]] = {}
	hosp_total: dict[str, float] = {}

	for d in deals:
		if d.get("status") not in won_statuses:
			continue  # Lost/Open BỊ LOẠI.
		owner = d.get("deal_owner")
		hospital = d.get("organization")
		if not owner or not hospital:
			continue  # thiếu NV hoặc BV → không xếp được vào ma trận.
		val = d.get("deal_value") or 0
		matrix.setdefault(owner, {})
		matrix[owner][hospital] = matrix[owner].get(hospital, 0) + val
		hosp_total[hospital] = hosp_total.get(hospital, 0) + val

	# Không có Deal Won nào → ma trận rỗng (empty-state FE). Cùng shape _empty.
	if not matrix:
		return _empty_revenue_by_rep_hospital()

	# 3) Cột BV = union BV xuất hiện, sort theo doanh thu cột DESC (tie-break tên cho ổn định).
	hosp_keys = sorted(hosp_total.keys(), key=lambda h: (-hosp_total[h], h))
	hospitals = [{"key": h, "label": h} for h in hosp_keys]

	# 4) max_cell = giá trị cell lớn nhất (cơ sở ngưỡng heat tương đối).
	max_cell = max((v for cols in matrix.values() for v in cols.values()), default=0)

	# 5) Dựng rows (cells đều cạnh theo hosp_keys; ô không có Won → None). total = SUM cells.
	rows = []
	for owner, cols in matrix.items():
		cells = []
		total = 0
		for h in hosp_keys:
			val = cols.get(h)
			if val is None:
				cells.append(None)
				continue
			total += val
			cells.append(
				{
					"hospital": h,
					"hospital_label": h,
					"value": val,
					"heat": _heat_level(val, max_cell),
				}
			)
		rows.append(
			{
				"deal_owner": owner,
				"full_name": _full_name(owner),
				"cells": cells,
				"total": total,
			}
		)

	# 6) Sort rows DESC theo total (NV mạnh nhất lên đầu); tie-break full_name cho ổn định.
	rows.sort(key=lambda r: (-r["total"], r["full_name"]))

	grand_total = sum(r["total"] for r in rows)

	return {
		"rows": rows,
		"hospitals": hospitals,
		"max_cell": max_cell,
		"grand_total": grand_total,
	}
