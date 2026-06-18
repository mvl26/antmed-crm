# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M10-1 "Quản lý Đội ngũ" (Trưởng phòng KD) — endpoint sales_team.team_roster (TDD viết TRƯỚC).

Màn /antmed/sales/team (mockup B2): bảng roster NV kinh doanh với KPI doanh số tháng,
rollup từ CRM Deal (deal_owner × deal_value × status × sla_status × territory).
KHÔNG new DocType, KHÔNG new module nghiệp vụ — chỉ tổng hợp/đếm doctype có sẵn.

team_roster() trả RAW dict:
  { rows: [{ deal_owner, full_name, territory, month_sales, open_deals,
             sla_ontime_pct, sales_pct, bar_theme, alert }],
    kpis: { total_reps, total_month_sales, avg_sla } }

Cover (acceptance Test-case TDD):
  (a) shape   — team_roster trả dict có keys ROSTER_KPI_KEYS + mỗi row đủ ROSTER_ROW_KEYS.
  (b) zero    — NV có role 'NV kinh doanh' nhưng 0 deal vẫn xuất hiện month_sales=0.
  (c) won-this-month — month_sales chỉ cộng deal status type Won closed trong tháng hiện tại
                       (deal Won tháng trước KHÔNG cộng, deal Open KHÔNG cộng).
  (d) open_deals — đếm đúng deal NOT IN (Won/Lost) theo deal_owner.
  (e) sla     — sla_ontime_pct = % deal sla_status != 'Failed'.
  (f) bar/alert — sales_pct & bar_theme green/warn/danger theo ngưỡng 70/50; alert='DS thấp' khi <50.
  (g) kpis    — total_reps/total_month_sales/avg_sla khớp tổng rows.
  (h) fail-closed — user thiếu read-perm CRM Deal → rows=[] kpis zero KHÔNG raise (BR-13).
  (i) no_raw_sql / no f-string injection trong source.
  (j) sort rows desc theo month_sales.

Lệnh chạy:
  bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_sales_team
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_months, get_first_day, nowdate

from antmed_crm.api.antmed import sales_team

ROSTER_ROW_KEYS = {
	"deal_owner",
	"full_name",
	"territory",
	"month_sales",
	"open_deals",
	"sla_ontime_pct",
	"sales_pct",
	"bar_theme",
	"alert",
}
ROSTER_KPI_KEYS = {"total_reps", "total_month_sales", "avg_sla"}

SALES_ROLE = "NV kinh doanh"


def _ensure_lost_reason():
	reason = "_T-ST-Lost-Reason"
	if not frappe.db.exists("CRM Lost Reason", reason):
		frappe.get_doc({"doctype": "CRM Lost Reason", "lost_reason": reason}).insert(ignore_permissions=True)
	return reason


def _won_status() -> str:
	"""Tên CRM Deal Status có type == 'Won' (mặc định CRM = 'Won')."""
	rows = frappe.get_all("CRM Deal Status", filters={"type": "Won"}, pluck="name", limit_page_length=1)
	return rows[0] if rows else "Won"


def _lost_status() -> str:
	rows = frappe.get_all("CRM Deal Status", filters={"type": "Lost"}, pluck="name", limit_page_length=1)
	return rows[0] if rows else "Lost"


def _open_status() -> str:
	rows = frappe.get_all(
		"CRM Deal Status", filters={"type": ["in", ["Open", "Ongoing"]]}, pluck="name", limit_page_length=1
	)
	return rows[0] if rows else "Qualification"


def _mk_sales_user(email: str, first_name: str, with_role: bool = True):
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": first_name, "send_welcome_email": 0}
		).insert(ignore_permissions=True)
	user = frappe.get_doc("User", email)
	if with_role and not frappe.db.exists("Role", SALES_ROLE):
		frappe.get_doc({"doctype": "Role", "role_name": SALES_ROLE}).insert(ignore_permissions=True)
	if with_role and SALES_ROLE not in [r.role for r in user.roles]:
		user.add_roles(SALES_ROLE)
	return email


def _mk_deal(owner: str, status: str, value: float, force_closed_date: str = "", **kw):
	"""Seed 1 CRM Deal. force_closed_date: set closed_date SAU insert qua db.set_value.

	Lý do: CRM Deal.validate ép closed_date=nowdate() khi status đổi sang type Won (insert =
	value-changed). Để seed deal Won ĐÃ closed THÁNG TRƯỚC, phải set_value sau insert (bypass
	controller override) — đây là dàn dựng dữ liệu test, KHÔNG đổi luồng prod.
	"""
	doc = frappe.get_doc(
		{
			"doctype": "CRM Deal",
			"status": status,
			"deal_owner": owner,
			"deal_value": value,
			**kw,
		}
	)
	doc.insert(ignore_permissions=True)
	if force_closed_date:
		frappe.db.set_value("CRM Deal", doc.name, "closed_date", force_closed_date)
		doc.reload()
	return doc


class TestAntMedTeamRoster(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.won = _won_status()
		cls.lost = _lost_status()
		cls.open_st = _open_status()
		cls.this_month_closed = nowdate()
		# Ngày closed tháng TRƯỚC (đầu tháng trước cho chắc < tháng hiện tại).
		cls.last_month_closed = get_first_day(add_months(nowdate(), -1))

		cls.u1 = _mk_sales_user("_t_st_rep1@example.com", "RepOne")
		cls.u2 = _mk_sales_user("_t_st_rep2@example.com", "RepTwo")
		# NV có role nhưng 0 deal (case b).
		cls.u_empty = _mk_sales_user("_t_st_empty@example.com", "RepEmpty")

		# Dọn deal cũ của 3 owner test (setUpClass commit → tránh tích luỹ qua các lần chạy lại).
		for owner in (cls.u1, cls.u2, cls.u_empty):
			for nm in frappe.get_all("CRM Deal", filters={"deal_owner": owner}, pluck="name"):
				frappe.delete_doc("CRM Deal", nm, force=True, ignore_permissions=True)

		# u1: 2 deal Won tháng này (100tr + 50tr) + 1 Open + 1 Won tháng trước (KHÔNG cộng).
		# Won tháng này: controller tự set closed_date=nowdate() (== this_month_closed) — không cần force.
		_mk_deal(cls.u1, cls.won, 100_000_000, sla_status="Fulfilled")
		_mk_deal(cls.u1, cls.won, 50_000_000, sla_status="Failed")
		_mk_deal(cls.u1, cls.open_st, 30_000_000, sla_status="Fulfilled")
		# Won tháng TRƯỚC: ép closed_date sau insert (controller override sang nowdate phải bị ghi đè lại).
		_mk_deal(cls.u1, cls.won, 999_000_000, force_closed_date=cls.last_month_closed, sla_status="Fulfilled")

		# u2: 1 deal Won tháng này (40tr) + 1 Lost (không phải open).
		_mk_deal(cls.u2, cls.won, 40_000_000, sla_status="Fulfilled")
		_mk_deal(cls.u2, cls.lost, 10_000_000, sla_status="Fulfilled",
				lost_reason=_ensure_lost_reason())

	def _rows_by_owner(self):
		return {r["deal_owner"]: r for r in sales_team.team_roster()["rows"]}

	# (a) shape ----------------------------------------------------------------
	def test_team_roster_shape(self):
		res = sales_team.team_roster()
		self.assertIsInstance(res, dict)
		self.assertEqual(set(res.keys()), {"rows", "kpis"})
		self.assertEqual(set(res["kpis"].keys()), ROSTER_KPI_KEYS)
		self.assertIsInstance(res["rows"], list)
		self.assertTrue(res["rows"], "phải có ít nhất 1 NV trong roster")
		for r in res["rows"]:
			self.assertEqual(set(r.keys()), ROSTER_ROW_KEYS, msg=f"row thừa/thiếu key: {r}")
		# RAW dict — KHÔNG envelope bọc.
		self.assertNotIn("data", res)
		self.assertNotIn("_ok", res)

	# (b) NV có role nhưng 0 deal vẫn xuất hiện, month_sales=0 -----------------
	def test_rep_with_role_no_deal_appears_zero(self):
		by = self._rows_by_owner()
		self.assertIn(self.u_empty, by, msg="NV có role 'NV kinh doanh' nhưng 0 deal phải vẫn xuất hiện")
		self.assertEqual(by[self.u_empty]["month_sales"], 0)
		self.assertEqual(by[self.u_empty]["open_deals"], 0)

	# (c) month_sales chỉ cộng Won tháng hiện tại -----------------------------
	def test_month_sales_only_won_this_month(self):
		by = self._rows_by_owner()
		# u1: 100tr + 50tr (Won tháng này) = 150tr; KHÔNG cộng Won tháng trước (999tr) / Open (30tr).
		self.assertEqual(by[self.u1]["month_sales"], 150_000_000)
		self.assertEqual(by[self.u2]["month_sales"], 40_000_000)

	# (d) open_deals = NOT IN Won/Lost ----------------------------------------
	def test_open_deals_count(self):
		by = self._rows_by_owner()
		self.assertEqual(by[self.u1]["open_deals"], 1, msg="u1 chỉ 1 deal Open (30tr)")
		self.assertEqual(by[self.u2]["open_deals"], 0, msg="u2: Won + Lost đều không phải open")

	# (e) sla_ontime_pct = % sla_status != 'Failed' ---------------------------
	def test_sla_ontime_pct(self):
		by = self._rows_by_owner()
		# u1 có 4 deal: 3 Fulfilled + 1 Failed → 3/4 = 75.0
		self.assertEqual(by[self.u1]["sla_ontime_pct"], 75.0)
		# u2 có 2 deal: 2 Fulfilled (không Failed) → 100.0
		self.assertEqual(by[self.u2]["sla_ontime_pct"], 100.0)
		# NV không deal → 100.0 (không chia 0, coi như đúng giờ — không phạt)
		self.assertEqual(by[self.u_empty]["sla_ontime_pct"], 100.0)

	# (f) sales_pct & bar_theme & alert ---------------------------------------
	def test_sales_pct_bar_theme_alert(self):
		rows = sales_team.team_roster()["rows"]
		by = {r["deal_owner"]: r for r in rows}
		max_sales = max((r["month_sales"] for r in rows), default=0)
		self.assertEqual(max_sales, 150_000_000)  # u1 đỉnh đội

		# u1 = đỉnh → 100% → green, alert rỗng.
		self.assertEqual(by[self.u1]["sales_pct"], 100.0)
		self.assertEqual(by[self.u1]["bar_theme"], "green")
		self.assertEqual(by[self.u1]["alert"], "")

		# u2 = 40/150 ≈ 26.7% < 50 → danger + alert 'DS thấp'.
		self.assertEqual(by[self.u2]["bar_theme"], "danger")
		self.assertEqual(by[self.u2]["alert"], "DS thấp")
		self.assertLess(by[self.u2]["sales_pct"], 50)

		# u_empty = 0% < 50 → danger + 'DS thấp'.
		self.assertEqual(by[self.u_empty]["bar_theme"], "danger")
		self.assertEqual(by[self.u_empty]["alert"], "DS thấp")

	def test_bar_theme_thresholds_warn(self):
		"""Ngưỡng warn (50 ≤ pct < 70): kiểm trực tiếp helper map (đơn giản, không phụ thuộc seed)."""
		self.assertEqual(sales_team._bar_theme(70.0), "green")
		self.assertEqual(sales_team._bar_theme(100.0), "green")
		self.assertEqual(sales_team._bar_theme(69.9), "warn")
		self.assertEqual(sales_team._bar_theme(50.0), "warn")
		self.assertEqual(sales_team._bar_theme(49.9), "danger")
		self.assertEqual(sales_team._bar_theme(0.0), "danger")
		self.assertEqual(sales_team._alert(49.9), "DS thấp")
		self.assertEqual(sales_team._alert(50.0), "")

	# (g) kpis khớp tổng rows --------------------------------------------------
	def test_kpis_match_rows(self):
		res = sales_team.team_roster()
		rows = res["rows"]
		kpis = res["kpis"]
		self.assertEqual(kpis["total_reps"], len(rows))
		self.assertEqual(kpis["total_month_sales"], sum(r["month_sales"] for r in rows))
		expected_avg = round(sum(r["sla_ontime_pct"] for r in rows) / len(rows), 1) if rows else 0.0
		self.assertEqual(kpis["avg_sla"], expected_avg)

	# (h) fail-closed BR-13 ----------------------------------------------------
	def test_fail_closed_no_perm(self):
		email = "_t_st_noperm@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": "STNoPerm", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.set_user(email)
		try:
			res = sales_team.team_roster()  # KHÔNG được raise
			self.assertEqual(res["rows"], [], msg=f"LEAK rows: {res}")
			self.assertEqual(res["kpis"]["total_reps"], 0)
			self.assertEqual(res["kpis"]["total_month_sales"], 0)
			self.assertEqual(res["kpis"]["avg_sla"], 0.0)
		finally:
			frappe.set_user("Administrator")

	# (i) no raw sql / no f-string injection ----------------------------------
	def test_no_raw_sql_no_injection(self):
		import inspect

		src = inspect.getsource(sales_team)
		self.assertNotIn("frappe.db.sql", src, msg="KHÔNG raw SQL — dùng get_list/get_all")
		self.assertNotIn("SELECT", src.upper(), msg="KHÔNG raw SELECT string")

	# (j) sort rows desc theo month_sales -------------------------------------
	def test_rows_sorted_desc_by_month_sales(self):
		rows = sales_team.team_roster()["rows"]
		sales = [r["month_sales"] for r in rows]
		self.assertEqual(sales, sorted(sales, reverse=True), msg=f"rows phải sort desc month_sales: {sales}")

	def test_team_roster_is_get_only(self):
		self.assertIn(sales_team.team_roster, frappe.whitelisted, msg="team_roster() chưa @frappe.whitelist()")
		allowed = frappe.allowed_http_methods_for_whitelisted_func.get(sales_team.team_roster)
		self.assertEqual(allowed, ["GET"], msg="team_roster() phải @frappe.whitelist(methods=['GET'])")


# ════════════════════════════════════════════════════════════════════════════
# M10-2 "Bảng điều phối ca giao phòng mổ" (Trưởng phòng KD) — dispatch_board()
# ════════════════════════════════════════════════════════════════════════════
# Màn /antmed/sales/dispatch (mockup B1): kanban read-only pipeline gói thầu —
# group CRM Deal theo CRM Deal Status (lane), CHỈ status type IN (Open/Ongoing/Won),
# LOẠI Lost. Mỗi lane sort theo position; card sort desc deal_value. KHÔNG new DocType.
#
# dispatch_board() trả RAW dict { lanes: [...], totals: {...} }:
#   lane = { status, type, label, position, count, cards }
#   card = { deal, organization, territory, deal_owner_name, deal_value, probability, bar_theme }
#   totals = { total_deals, open_value, won_value }
#
# Cover (acceptance Test-case TDD):
#   (a) shape   — dict {lanes, totals}; totals đủ DISPATCH_TOTAL_KEYS; lane/card đủ key tuple.
#   (b) no-lost — lanes CHỈ type IN (Open,Ongoing,Won); KHÔNG có lane status type Lost.
#   (c) sort    — lanes sort tăng theo position (Qualification trước Won).
#   (d) card-lane — deal Won/Qualification của owner test xuất hiện đúng lane theo status.
#   (e) name    — card.deal_owner_name = full_name (KHÔNG = email).
#   (f) card-sort — cards trong lane sort desc deal_value.
#   (g) theme   — _prob_theme pure: 80→green / 50→warn / 20→danger (ngưỡng 70/40); card.bar_theme khớp.
#   (h) totals  — total_deals = tổng card render (KHÔNG đếm Lost); open_value = SUM lane Open/Ongoing;
#                 won_value = SUM lane Won.
#   (i) fail-closed — get_list raise PermissionError → lanes=[] + totals zero, KHÔNG raise (BR-13).
#   (j) get-only — @frappe.whitelist(methods=['GET']).

DISPATCH_LANE_KEYS = {"status", "type", "label", "position", "count", "cards"}
DISPATCH_CARD_KEYS = {
	"deal",
	"organization",
	"territory",
	"deal_owner_name",
	"deal_value",
	"probability",
	"bar_theme",
}
DISPATCH_TOTAL_KEYS = {"total_deals", "open_value", "won_value"}


class TestAntMedDispatchBoard(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.won = _won_status()
		cls.lost = _lost_status()
		cls.open_st = _open_status()

		cls.owner = _mk_sales_user("_t_db_rep@example.com", "DispatchRep")
		# Deal Lost giá trị riêng (không trùng giá trị Won của test class khác) → assert KHÔNG-lên-board chắc.
		cls.lost_value = 77_777_777
		# Won closed THÁNG TRƯỚC: dispatch group theo STATUS (không quan tâm date) nên vẫn lên lane Won,
		# nhưng KHÔNG làm phình month_sales/max_sales của roster (test class kia assert max tuyệt đối).
		cls.last_month_closed = get_first_day(add_months(nowdate(), -1))

		# Dọn deal cũ của owner test (setUpClass commit → tránh tích luỹ qua các lần chạy lại).
		for nm in frappe.get_all("CRM Deal", filters={"deal_owner": cls.owner}, pluck="name"):
			frappe.delete_doc("CRM Deal", nm, force=True, ignore_permissions=True)

		# owner: 2 deal Open (80tr, 120tr) + 1 deal Won (200tr) + 1 deal Lost (KHÔNG lên board).
		_mk_deal(cls.owner, cls.open_st, 80_000_000, organization="", territory="", probability=30)
		_mk_deal(cls.owner, cls.open_st, 120_000_000, organization="", territory="", probability=80)
		_mk_deal(
			cls.owner, cls.won, 200_000_000, force_closed_date=cls.last_month_closed,
			organization="", territory="", probability=100,
		)
		_mk_deal(
			cls.owner, cls.lost, cls.lost_value, organization="", territory="", probability=0,
			lost_reason=_ensure_lost_reason(),
		)

	def _board(self):
		return sales_team.dispatch_board()

	def _lane_by_status(self, status):
		for lane in self._board()["lanes"]:
			if lane["status"] == status:
				return lane
		return None

	# (a) shape ----------------------------------------------------------------
	def test_dispatch_board_shape(self):
		res = self._board()
		self.assertIsInstance(res, dict)
		self.assertEqual(set(res.keys()), {"lanes", "totals"})
		self.assertIsInstance(res["lanes"], list)
		self.assertEqual(set(res["totals"].keys()), DISPATCH_TOTAL_KEYS)
		for lane in res["lanes"]:
			self.assertEqual(set(lane.keys()), DISPATCH_LANE_KEYS, msg=f"lane thừa/thiếu key: {lane}")
			self.assertIsInstance(lane["cards"], list)
			for card in lane["cards"]:
				self.assertEqual(set(card.keys()), DISPATCH_CARD_KEYS, msg=f"card thừa/thiếu key: {card}")
		# RAW dict — KHÔNG envelope bọc.
		self.assertNotIn("data", res)
		self.assertNotIn("_ok", res)

	# (b) lanes CHỈ type IN (Open,Ongoing,Won) — KHÔNG Lost ---------------------
	def test_lanes_only_open_ongoing_won_no_lost(self):
		res = self._board()
		types = {lane["type"] for lane in res["lanes"]}
		self.assertTrue(types.issubset({"Open", "Ongoing", "Won"}), msg=f"lane type lạ: {types}")
		self.assertNotIn("Lost", types)
		# KHÔNG có lane nào mang status type Lost.
		lost_statuses = sales_team._statuses_of_type(["Lost"])
		lane_statuses = {lane["status"] for lane in res["lanes"]}
		self.assertEqual(lane_statuses & lost_statuses, set(), msg="KHÔNG được có lane status type Lost")

	# (c) lanes sort tăng theo position ----------------------------------------
	def test_lanes_sorted_by_position(self):
		positions = [lane["position"] for lane in self._board()["lanes"]]
		self.assertEqual(positions, sorted(positions), msg=f"lanes phải sort tăng theo position: {positions}")

	# (d) card xuất hiện đúng lane theo status ----------------------------------
	def test_cards_land_in_correct_lane(self):
		won_lane = self._lane_by_status(self.won)
		open_lane = self._lane_by_status(self.open_st)
		self.assertIsNotNone(won_lane, msg="lane Won phải tồn tại")
		self.assertIsNotNone(open_lane, msg="lane Open phải tồn tại")
		won_deals = {c["deal"] for c in won_lane["cards"]}
		open_deals = {c["deal"] for c in open_lane["cards"]}
		# deal Won 200tr ở lane Won; 2 deal Open ở lane Open.
		self.assertTrue(any(c["deal_value"] == 200_000_000 for c in won_lane["cards"]))
		self.assertTrue(any(c["deal_value"] == 120_000_000 for c in open_lane["cards"]))
		self.assertTrue(any(c["deal_value"] == 80_000_000 for c in open_lane["cards"]))
		self.assertEqual(won_deals & open_deals, set(), msg="deal KHÔNG được lặp giữa 2 lane")

	# (e) deal_owner_name = full_name (KHÔNG email) ----------------------------
	def test_card_owner_name_is_full_name_not_email(self):
		open_lane = self._lane_by_status(self.open_st)
		card = open_lane["cards"][0]
		expected = sales_team._full_name(self.owner)
		self.assertEqual(card["deal_owner_name"], expected)
		self.assertNotEqual(card["deal_owner_name"], self.owner, msg="KHÔNG lộ email deal_owner")
		self.assertNotIn("@", card["deal_owner_name"], msg="deal_owner_name không được là email")

	# (f) cards trong lane sort desc deal_value --------------------------------
	def test_cards_sorted_desc_deal_value(self):
		open_lane = self._lane_by_status(self.open_st)
		values = [c["deal_value"] for c in open_lane["cards"]]
		self.assertEqual(values, sorted(values, reverse=True), msg=f"cards sort desc deal_value: {values}")
		# count == len(cards)
		self.assertEqual(open_lane["count"], len(open_lane["cards"]))

	# (g) _prob_theme pure ngưỡng 70/40 ---------------------------------------
	def test_prob_theme_thresholds(self):
		self.assertEqual(sales_team._prob_theme(80), "green")
		self.assertEqual(sales_team._prob_theme(70), "green")
		self.assertEqual(sales_team._prob_theme(69.9), "warn")
		self.assertEqual(sales_team._prob_theme(50), "warn")
		self.assertEqual(sales_team._prob_theme(40), "warn")
		self.assertEqual(sales_team._prob_theme(39.9), "danger")
		self.assertEqual(sales_team._prob_theme(20), "danger")
		self.assertEqual(sales_team._prob_theme(0), "danger")
		self.assertEqual(sales_team._prob_theme(None), "danger")

	def test_card_bar_theme_matches_prob_theme(self):
		for lane in self._board()["lanes"]:
			for card in lane["cards"]:
				self.assertEqual(
					card["bar_theme"],
					sales_team._prob_theme(card["probability"]),
					msg=f"bar_theme phải khớp _prob_theme(probability): {card}",
				)

	# (h) totals ---------------------------------------------------------------
	def test_totals(self):
		res = self._board()
		lanes = res["lanes"]
		totals = res["totals"]
		# total_deals = tổng card render (KHÔNG đếm Lost).
		rendered = sum(len(lane["cards"]) for lane in lanes)
		self.assertEqual(totals["total_deals"], rendered)
		# open_value = SUM deal_value lane type Open/Ongoing.
		expected_open = sum(
			c["deal_value"] for lane in lanes if lane["type"] in ("Open", "Ongoing") for c in lane["cards"]
		)
		self.assertEqual(totals["open_value"], expected_open)
		# won_value = SUM deal_value lane type Won.
		expected_won = sum(c["deal_value"] for lane in lanes if lane["type"] == "Won" for c in lane["cards"])
		self.assertEqual(totals["won_value"], expected_won)
		# deal Lost (giá trị riêng) KHÔNG nằm trong bất kỳ lane/total nào (Lost bị loại khỏi board).
		self.assertNotIn(self.lost_value, [c["deal_value"] for lane in lanes for c in lane["cards"]])

	# (i) fail-closed BR-13 — get_list raise PermissionError -------------------
	def test_fail_closed_no_perm(self):
		orig = frappe.get_list

		def _raise(*a, **k):
			if a and a[0] == sales_team.DEAL_DOCTYPE:
				raise frappe.PermissionError("no perm")
			return orig(*a, **k)

		frappe.get_list = _raise
		try:
			res = sales_team.dispatch_board()  # KHÔNG được raise
			self.assertEqual(res["lanes"], [], msg=f"LEAK lanes: {res}")
			self.assertEqual(res["totals"]["total_deals"], 0)
			self.assertEqual(res["totals"]["open_value"], 0)
			self.assertEqual(res["totals"]["won_value"], 0)
		finally:
			frappe.get_list = orig

	# (j) get-only -------------------------------------------------------------
	def test_dispatch_board_is_get_only(self):
		self.assertIn(sales_team.dispatch_board, frappe.whitelisted, msg="dispatch_board() chưa @frappe.whitelist()")
		allowed = frappe.allowed_http_methods_for_whitelisted_func.get(sales_team.dispatch_board)
		self.assertEqual(allowed, ["GET"], msg="dispatch_board() phải @frappe.whitelist(methods=['GET'])")

	# (k) SSoT export — DISPATCH_LANE_TYPES + key tuples -----------------------
	def test_dispatch_ssot_exports(self):
		self.assertEqual(set(sales_team.DISPATCH_LANE_TYPES), {"Open", "Ongoing", "Won"})
		self.assertEqual(set(sales_team.DISPATCH_LANE_KEYS), DISPATCH_LANE_KEYS)
		self.assertEqual(set(sales_team.DISPATCH_CARD_KEYS), DISPATCH_CARD_KEYS)
		self.assertEqual(set(sales_team.DISPATCH_TOTAL_KEYS), DISPATCH_TOTAL_KEYS)


# ════════════════════════════════════════════════════════════════════════════
# M10-3 "Hồ sơ NV kinh doanh" (Trưởng phòng KD) — rep_profile(owner)
# ════════════════════════════════════════════════════════════════════════════
# Màn /antmed/sales/team/:owner (mockup B2 left-card) — drill-down 1 NV từ roster.
# rep_profile(owner) trả RAW dict (KHÔNG envelope):
#   { profile: { deal_owner, full_name, joined_on, roles },
#     kpi:     { month_sales, open_deals, total_deals, sla_ontime_pct },
#     deals:   [{ deal, organization, territory, deal_value, status, probability }] }
#
# kpi tái dùng ĐÚNG công thức team_roster (cùng module → cùng SSoT helper).
#
# Cover (acceptance Test-case TDD):
#   (1) shape   — đủ key profile/kpi/deals; REP_PROFILE_*_KEYS khớp (assert qua hằng export).
#   (2) won-this-month — kpi.month_sales = SUM Won closed_date trong THÁNG của owner
#                        (Won tháng trước KHÔNG cộng).
#   (3) open_deals — đếm đúng status NOT IN Won/Lost.
#   (4) sla     — sla_ontime_pct công thức + total=0 → 100.0 (KHÔNG chia 0).
#   (5) deals   — chỉ của owner (deal owner khác KHÔNG lọt) + sort desc deal_value.
#   (6) profile — full_name = User.full_name KHÔNG email; joined_on từ User.creation;
#                 owner không-User → joined_on None + full_name fallback owner KHÔNG 500.
#   (7) fail-closed — get_list raise PermissionError → kpi zero + deals [] KHÔNG raise (BR-13).
#   (8) get-only — @frappe.whitelist(methods=['GET']); POST bị chặn.
#   (9) no_raw_sql + KHÔNG lộ email trong deals payload.

REP_PROFILE_PROFILE_KEYS = {"deal_owner", "full_name", "joined_on", "roles"}
REP_PROFILE_KPI_KEYS = {"month_sales", "open_deals", "total_deals", "sla_ontime_pct"}
REP_PROFILE_DEAL_KEYS = {
	"deal",
	"organization",
	"territory",
	"deal_value",
	"status",
	"probability",
	"status_theme",
}


class TestAntMedRepProfile(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.won = _won_status()
		cls.lost = _lost_status()
		cls.open_st = _open_status()
		cls.last_month_closed = get_first_day(add_months(nowdate(), -1))

		cls.owner = _mk_sales_user("_t_rp_rep@example.com", "ProfileRep")
		cls.other = _mk_sales_user("_t_rp_other@example.com", "OtherRep")

		# Dọn deal cũ của 2 owner test (setUpClass commit → tránh tích luỹ qua các lần chạy lại).
		for owner in (cls.owner, cls.other):
			for nm in frappe.get_all("CRM Deal", filters={"deal_owner": owner}, pluck="name"):
				frappe.delete_doc("CRM Deal", nm, force=True, ignore_permissions=True)

		# owner: 2 Won tháng này (100tr + 30tr = 130tr — GIỮ < 150tr đỉnh roster của TestAntMedTeamRoster
		#        để KHÔNG phá assert max_sales tuyệt đối của test class kia) + 1 Open (90tr) +
		#        1 Won tháng trước (KHÔNG cộng) + 1 deal sla Failed (cho công thức SLA).
		_mk_deal(cls.owner, cls.won, 100_000_000, sla_status="Fulfilled", probability=100)
		_mk_deal(cls.owner, cls.won, 30_000_000, sla_status="Failed", probability=100)
		_mk_deal(cls.owner, cls.open_st, 90_000_000, sla_status="Fulfilled", probability=50)
		_mk_deal(
			cls.owner, cls.won, 999_000_000, force_closed_date=cls.last_month_closed,
			sla_status="Fulfilled", probability=100,
		)
		# other: 1 Won (KHÔNG được lọt vào deals của owner).
		_mk_deal(cls.other, cls.won, 11_111_111, sla_status="Fulfilled", probability=100)

	# (1) shape ----------------------------------------------------------------
	def test_rep_profile_shape(self):
		res = sales_team.rep_profile(self.owner)
		self.assertIsInstance(res, dict)
		self.assertEqual(set(res.keys()), {"profile", "kpi", "deals"})
		self.assertEqual(set(res["profile"].keys()), REP_PROFILE_PROFILE_KEYS)
		self.assertEqual(set(res["kpi"].keys()), REP_PROFILE_KPI_KEYS)
		self.assertIsInstance(res["deals"], list)
		for d in res["deals"]:
			self.assertEqual(set(d.keys()), REP_PROFILE_DEAL_KEYS, msg=f"deal thừa/thiếu key: {d}")
		# RAW dict — KHÔNG envelope bọc.
		self.assertNotIn("data", res)
		self.assertNotIn("_ok", res)

	def test_rep_profile_ssot_exports(self):
		"""REP_PROFILE_*_KEYS export làm SSoT (assert qua hằng, KHÔNG hardcode lại shape)."""
		self.assertEqual(set(sales_team.REP_PROFILE_PROFILE_KEYS), REP_PROFILE_PROFILE_KEYS)
		self.assertEqual(set(sales_team.REP_PROFILE_KPI_KEYS), REP_PROFILE_KPI_KEYS)
		self.assertEqual(set(sales_team.REP_PROFILE_DEAL_KEYS), REP_PROFILE_DEAL_KEYS)

	# (2) month_sales chỉ cộng Won tháng hiện tại -----------------------------
	def test_month_sales_only_won_this_month(self):
		kpi = sales_team.rep_profile(self.owner)["kpi"]
		# 100tr + 30tr (Won tháng này) = 130tr; KHÔNG cộng Won tháng trước (999tr) / Open (90tr).
		self.assertEqual(kpi["month_sales"], 130_000_000)

	# (3) open_deals = NOT IN Won/Lost ----------------------------------------
	def test_open_deals_count(self):
		kpi = sales_team.rep_profile(self.owner)["kpi"]
		self.assertEqual(kpi["open_deals"], 1, msg="owner chỉ 1 deal Open (90tr)")
		# total_deals = tất cả deal của owner (3 Won + 1 Open = 4).
		self.assertEqual(kpi["total_deals"], 4)

	# (4) sla_ontime_pct công thức + total=0 → 100.0 --------------------------
	def test_sla_ontime_pct(self):
		kpi = sales_team.rep_profile(self.owner)["kpi"]
		# owner: 4 deal, 1 Failed → 3/4 = 75.0
		self.assertEqual(kpi["sla_ontime_pct"], 75.0)

	def test_sla_ontime_pct_no_deal_is_100(self):
		"""total=0 → 100.0 (KHÔNG chia 0)."""
		empty = _mk_sales_user("_t_rp_zero@example.com", "ZeroRep")
		for nm in frappe.get_all("CRM Deal", filters={"deal_owner": empty}, pluck="name"):
			frappe.delete_doc("CRM Deal", nm, force=True, ignore_permissions=True)
		kpi = sales_team.rep_profile(empty)["kpi"]
		self.assertEqual(kpi["total_deals"], 0)
		self.assertEqual(kpi["sla_ontime_pct"], 100.0)
		self.assertEqual(kpi["month_sales"], 0)
		self.assertEqual(kpi["open_deals"], 0)

	# (5) deals chỉ của owner + sort desc deal_value --------------------------
	def test_deals_only_owner_sorted_desc(self):
		deals = sales_team.rep_profile(self.owner)["deals"]
		values = [d["deal_value"] for d in deals]
		self.assertEqual(values, sorted(values, reverse=True), msg=f"deals phải sort desc deal_value: {values}")
		# deal của other (11_111_111) KHÔNG được lọt.
		self.assertNotIn(11_111_111, values, msg="deal owner khác KHÔNG được lọt")
		# 4 deal của owner.
		self.assertEqual(len(deals), 4)

	# (5b) status_theme do BE quyết: Won → ok / còn lại Open → info -----------
	def test_deal_status_theme(self):
		deals = sales_team.rep_profile(self.owner)["deals"]
		won_statuses = sales_team._statuses_of_type(["Won"])
		for d in deals:
			expected = sales_team._status_theme(d["status"], won_statuses, sales_team._statuses_of_type(["Lost"]))
			self.assertEqual(d["status_theme"], expected, msg=f"status_theme phải khớp _status_theme: {d}")
		# Won deal → 'ok'; Open deal → 'info'.
		themes = {d["status"]: d["status_theme"] for d in deals}
		self.assertEqual(themes.get(self.won), "ok")
		self.assertEqual(themes.get(self.open_st), "info")

	# (6) profile.full_name = full_name (KHÔNG email); joined_on từ User.creation ---
	def test_profile_full_name_not_email(self):
		profile = sales_team.rep_profile(self.owner)["profile"]
		expected = frappe.db.get_value("User", self.owner, "full_name")
		self.assertEqual(profile["full_name"], expected)
		self.assertNotEqual(profile["full_name"], self.owner, msg="full_name KHÔNG được = email")
		self.assertNotIn("@", profile["full_name"], msg="full_name không được là email")
		# joined_on = User.creation (ngày) — không None với user thật.
		self.assertIsNotNone(profile["joined_on"])
		# roles = danh sách (chứa role nghiệp vụ 'NV kinh doanh').
		self.assertIsInstance(profile["roles"], list)
		self.assertIn(SALES_ROLE, profile["roles"])

	def test_profile_unknown_owner_404_safe(self):
		"""Owner không có User record → joined_on None + full_name fallback owner, KHÔNG 500."""
		ghost = "_t_rp_ghost_not_a_user@example.com"
		self.assertFalse(frappe.db.exists("User", ghost))
		res = sales_team.rep_profile(ghost)
		self.assertEqual(res["profile"]["deal_owner"], ghost)
		self.assertEqual(res["profile"]["full_name"], ghost)  # fallback owner (không có full_name)
		self.assertIsNone(res["profile"]["joined_on"])
		self.assertEqual(res["profile"]["roles"], [])
		self.assertEqual(res["deals"], [])
		self.assertEqual(res["kpi"]["month_sales"], 0)
		self.assertEqual(res["kpi"]["total_deals"], 0)
		self.assertEqual(res["kpi"]["sla_ontime_pct"], 100.0)

	# (7) fail-closed BR-13 — get_list raise PermissionError -------------------
	def test_fail_closed_no_perm(self):
		orig = frappe.get_list

		def _raise(*a, **k):
			if a and a[0] == sales_team.DEAL_DOCTYPE:
				raise frappe.PermissionError("no perm")
			return orig(*a, **k)

		frappe.get_list = _raise
		try:
			res = sales_team.rep_profile(self.owner)  # KHÔNG được raise
			self.assertEqual(res["deals"], [], msg=f"LEAK deals: {res}")
			self.assertEqual(res["kpi"]["month_sales"], 0)
			self.assertEqual(res["kpi"]["open_deals"], 0)
			self.assertEqual(res["kpi"]["total_deals"], 0)
			self.assertEqual(res["kpi"]["sla_ontime_pct"], 100.0)
			# profile minimal vẫn trả full_name + roles (KHÔNG lộ số toàn hệ thống).
			self.assertEqual(res["profile"]["deal_owner"], self.owner)
			self.assertNotIn("@", res["profile"]["full_name"])
		finally:
			frappe.get_list = orig

	# (8) get-only -------------------------------------------------------------
	def test_rep_profile_is_get_only(self):
		self.assertIn(sales_team.rep_profile, frappe.whitelisted, msg="rep_profile() chưa @frappe.whitelist()")
		allowed = frappe.allowed_http_methods_for_whitelisted_func.get(sales_team.rep_profile)
		self.assertEqual(allowed, ["GET"], msg="rep_profile() phải @frappe.whitelist(methods=['GET'])")

	# (9) no raw sql + KHÔNG lộ email trong deals ------------------------------
	def test_no_raw_sql_and_no_email_leak(self):
		import inspect

		src = inspect.getsource(sales_team)
		self.assertNotIn("frappe.db.sql", src, msg="KHÔNG raw SQL — dùng get_list/get_all")
		self.assertNotIn("SELECT", src.upper(), msg="KHÔNG raw SELECT string")
		# deals payload KHÔNG chứa email (deal_owner) — chỉ deal/organization/territory/value/status/prob.
		deals = sales_team.rep_profile(self.owner)["deals"]
		for d in deals:
			self.assertNotIn("deal_owner", d, msg=f"deals KHÔNG được lộ deal_owner email: {d}")
			for v in d.values():
				self.assertNotIn("@example.com", str(v), msg=f"deals KHÔNG được chứa email: {d}")


# ════════════════════════════════════════════════════════════════════════════
# M02-10 "Doanh thu theo NV Kinh doanh × Bệnh viện" (Dashboard CEO, mockup A3)
# ════════════════════════════════════════════════════════════════════════════
# Màn /antmed/revenue (card heat) — ma trận NV (deal_owner) × Bệnh viện (organization)
# với doanh thu THẬT = SUM(deal_value) CRM Deal status type 'Won'. KHÔNG new DocType/module.
#
# revenue_by_rep_hospital() trả RAW dict (KHÔNG envelope):
#   { rows:[{ deal_owner, full_name, cells:[{hospital,hospital_label,value,heat}|null], total }],
#     hospitals:[{ key, label }], max_cell, grand_total }
#
# Cover (acceptance Test-case TDD M02-10):
#   (1) shape   — dict đủ key rows/hospitals/max_cell/grand_total; row đủ REP_HOSP_ROW_KEYS.
#   (2) cell    — cell value = SUM(deal_value) Won theo (owner×hospital); Deal Lost/Open BỊ LOẠI.
#   (3) name    — full_name KHÔNG phải email.
#   (4) total   — total NV = SUM cells; grand_total = SUM total.
#   (5) sort    — rows sort DESC theo total.
#   (6) heat    — _heat_level 4 ngưỡng trên max_cell; cell=0/None → heat None.
#   (7) empty   — không Deal Won → _empty shape rỗng KHÔNG vỡ.
#   (8) fail-closed — get_list raise PermissionError → _empty (KHÔNG raise, KHÔNG leak).
#   (9) get-only — @frappe.whitelist(methods=['GET']).
#   (10) no raw sql + batch (KHÔNG frappe.db.sql).
#   (11) SSoT export REP_HOSP_ROW_KEYS / HEAT_LEVELS khớp shape.

REP_HOSP_ROW_KEYS = {"deal_owner", "full_name", "cells", "total"}
REP_HOSP_CELL_KEYS = {"hospital", "hospital_label", "value", "heat"}
REP_HOSP_TOP_KEYS = {"rows", "hospitals", "max_cell", "grand_total"}


def _mk_org(name: str):
	"""Seed 1 CRM Organization (autoname field:organization_name → name == organization_name)."""
	if not frappe.db.exists("CRM Organization", name):
		frappe.get_doc({"doctype": "CRM Organization", "organization_name": name}).insert(
			ignore_permissions=True
		)
	return name


class TestAntMedRevenueByRepHospital(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.won = _won_status()
		cls.lost = _lost_status()
		cls.open_st = _open_status()

		# 2 NV × 2 BV (+ Deal Lost/Open bị loại).
		cls.u1 = _mk_sales_user("_t_rh_rep1@example.com", "RhRepOne")
		cls.u2 = _mk_sales_user("_t_rh_rep2@example.com", "RhRepTwo")
		cls.bm = _mk_org("_T-RH-BachMai")
		cls.vd = _mk_org("_T-RH-VietDuc")
		# Won closed THÁNG TRƯỚC: revenue_by_rep_hospital group theo STATUS (date-agnostic) nên vẫn
		# tính đủ, NHƯNG KHÔNG làm phình month_sales/max_sales của roster (TestAntMedTeamRoster assert
		# max_sales tuyệt đối tháng hiện tại). Mirror cách TestAntMedDispatchBoard cô lập.
		cls.last_month_closed = get_first_day(add_months(nowdate(), -1))

		# Dọn deal cũ của 2 owner test (setUpClass commit → tránh tích luỹ qua các lần chạy lại).
		for owner in (cls.u1, cls.u2):
			for nm in frappe.get_all("CRM Deal", filters={"deal_owner": owner}, pluck="name"):
				frappe.delete_doc("CRM Deal", nm, force=True, ignore_permissions=True)

		# u1: Won BM 2.000tr + Won VD 800tr + 1 Open BM (KHÔNG cộng vào cell Won) → total 2.800tr.
		# Open giữ giá trị NHỎ (1tr) — chứng minh Open bị loại khỏi cell Won, ĐỒNG THỜI không sort lên
		# đầu lane Open chung của TestAntMedDispatchBoard (tránh cross-contaminate card[0] test cũ).
		_mk_deal(cls.u1, cls.won, 2_000_000_000, force_closed_date=cls.last_month_closed, organization=cls.bm, probability=100)
		_mk_deal(cls.u1, cls.won, 800_000_000, force_closed_date=cls.last_month_closed, organization=cls.vd, probability=100)
		_mk_deal(cls.u1, cls.open_st, 1_000_000, organization=cls.bm, probability=50)
		# u2: Won VD 1.200tr + Lost BM (KHÔNG cộng) → total 1.200tr.
		_mk_deal(cls.u2, cls.won, 1_200_000_000, force_closed_date=cls.last_month_closed, organization=cls.vd, probability=100)
		_mk_deal(
			cls.u2, cls.lost, 555_000_000, organization=cls.bm, probability=0,
			lost_reason=_ensure_lost_reason(),
		)

	def _res(self):
		return sales_team.revenue_by_rep_hospital()

	def _row(self, owner):
		for r in self._res()["rows"]:
			if r["deal_owner"] == owner:
				return r
		return None

	def _cell(self, owner, hospital):
		row = self._row(owner)
		if not row:
			return None
		res = self._res()
		hkeys = [h["key"] for h in res["hospitals"]]
		try:
			idx = hkeys.index(hospital)
		except ValueError:
			return None
		return row["cells"][idx]

	# (1) shape ----------------------------------------------------------------
	def test_shape(self):
		res = self._res()
		self.assertIsInstance(res, dict)
		self.assertEqual(set(res.keys()), REP_HOSP_TOP_KEYS)
		self.assertIsInstance(res["rows"], list)
		self.assertIsInstance(res["hospitals"], list)
		for h in res["hospitals"]:
			self.assertEqual(set(h.keys()), {"key", "label"})
		for row in res["rows"]:
			self.assertEqual(set(row.keys()), REP_HOSP_ROW_KEYS, msg=f"row thừa/thiếu key: {row}")
			self.assertIsInstance(row["cells"], list)
			# cells dài đúng = số cột BV (matrix đều cạnh).
			self.assertEqual(len(row["cells"]), len(res["hospitals"]))
			for c in row["cells"]:
				if c is not None:
					self.assertEqual(set(c.keys()), REP_HOSP_CELL_KEYS, msg=f"cell thừa/thiếu key: {c}")
		# RAW dict — KHÔNG envelope bọc, KHÔNG {data,total_count}.
		self.assertNotIn("data", res)
		self.assertNotIn("total_count", res)
		self.assertNotIn("_ok", res)

	# (2) cell value = SUM(deal_value) Won; Lost/Open BỊ LOẠI ------------------
	def test_cell_value_won_only(self):
		c_u1_bm = self._cell(self.u1, self.bm)
		c_u1_vd = self._cell(self.u1, self.vd)
		c_u2_vd = self._cell(self.u2, self.vd)
		c_u2_bm = self._cell(self.u2, self.bm)
		self.assertIsNotNone(c_u1_bm)
		# u1×BM = chỉ Won 2.000tr (Open 999tr KHÔNG cộng).
		self.assertEqual(c_u1_bm["value"], 2_000_000_000)
		self.assertEqual(c_u1_vd["value"], 800_000_000)
		self.assertEqual(c_u2_vd["value"], 1_200_000_000)
		# u2×BM = chỉ có Deal Lost → KHÔNG có cell (None, render '—').
		self.assertIsNone(c_u2_bm, msg="Deal Lost KHÔNG được tạo cell")

	# (3) full_name KHÔNG phải email ------------------------------------------
	def test_full_name_not_email(self):
		for row in self._res()["rows"]:
			self.assertEqual(row["full_name"], sales_team._full_name(row["deal_owner"]))
			self.assertNotIn("@", row["full_name"], msg=f"full_name KHÔNG được là email: {row}")

	# (4) total NV = SUM cells; grand_total = SUM total ------------------------
	def test_totals(self):
		res = self._res()
		for row in res["rows"]:
			cells_sum = sum((c["value"] for c in row["cells"] if c), 0)
			self.assertEqual(row["total"], cells_sum, msg=f"total != SUM cells: {row}")
		grand = sum(r["total"] for r in res["rows"])
		self.assertEqual(res["grand_total"], grand)
		# u1 total = 2.000 + 800 = 2.800tr; u2 = 1.200tr.
		self.assertEqual(self._row(self.u1)["total"], 2_800_000_000)
		self.assertEqual(self._row(self.u2)["total"], 1_200_000_000)

	# (5) rows sort DESC theo total -------------------------------------------
	def test_rows_sorted_desc_total(self):
		totals = [r["total"] for r in self._res()["rows"]]
		self.assertEqual(totals, sorted(totals, reverse=True), msg=f"rows phải sort desc total: {totals}")
		# u1 (2.800tr) đứng trước u2 (1.200tr).
		owners = [r["deal_owner"] for r in self._res()["rows"]]
		self.assertLess(owners.index(self.u1), owners.index(self.u2))

	# (6) _heat_level 4 ngưỡng trên max_cell; 0/None → None -------------------
	def test_heat_level_thresholds(self):
		# max_cell = 100 → ngưỡng >75 h5c / >50 h4c / >25 h3c / >0 h2c / =0 None.
		self.assertEqual(sales_team._heat_level(100, 100), "h5c")
		self.assertEqual(sales_team._heat_level(76, 100), "h5c")
		self.assertEqual(sales_team._heat_level(75, 100), "h4c")
		self.assertEqual(sales_team._heat_level(51, 100), "h4c")
		self.assertEqual(sales_team._heat_level(50, 100), "h3c")
		self.assertEqual(sales_team._heat_level(26, 100), "h3c")
		self.assertEqual(sales_team._heat_level(25, 100), "h2c")
		self.assertEqual(sales_team._heat_level(1, 100), "h2c")
		self.assertIsNone(sales_team._heat_level(0, 100))
		self.assertIsNone(sales_team._heat_level(None, 100))
		# max_cell 0 (no data) → heat None (no ZeroDivision).
		self.assertIsNone(sales_team._heat_level(0, 0))
		self.assertIsNone(sales_team._heat_level(10, 0))

	def test_cell_heat_matches_helper(self):
		res = self._res()
		mx = res["max_cell"]
		for row in res["rows"]:
			for c in row["cells"]:
				if c is not None:
					self.assertEqual(c["heat"], sales_team._heat_level(c["value"], mx), msg=f"heat lệch: {c}")
		# max_cell = cell lớn nhất (u1×BM 2.000tr).
		self.assertEqual(mx, 2_000_000_000)

	# (7) empty-scope → _empty shape rỗng KHÔNG vỡ ----------------------------
	def test_empty_scope(self):
		empty = sales_team._empty_revenue_by_rep_hospital()
		self.assertEqual(empty, {"rows": [], "hospitals": [], "max_cell": 0, "grand_total": 0})
		# shape khớp top-keys (chống drift _empty vs endpoint).
		self.assertEqual(set(empty.keys()), REP_HOSP_TOP_KEYS)

	# (8) fail-closed BR-13 — get_list raise PermissionError ------------------
	def test_fail_closed_no_perm(self):
		orig = frappe.get_list

		def _raise(*a, **k):
			if a and a[0] == sales_team.DEAL_DOCTYPE:
				raise frappe.PermissionError("no perm")
			return orig(*a, **k)

		frappe.get_list = _raise
		try:
			res = sales_team.revenue_by_rep_hospital()  # KHÔNG được raise
			self.assertEqual(res, sales_team._empty_revenue_by_rep_hospital(), msg=f"LEAK: {res}")
			self.assertEqual(res["rows"], [])
			self.assertEqual(res["hospitals"], [])
			self.assertEqual(res["grand_total"], 0)
		finally:
			frappe.get_list = orig

	# (9) get-only -------------------------------------------------------------
	def test_is_get_only(self):
		self.assertIn(
			sales_team.revenue_by_rep_hospital,
			frappe.whitelisted,
			msg="revenue_by_rep_hospital() chưa @frappe.whitelist()",
		)
		allowed = frappe.allowed_http_methods_for_whitelisted_func.get(sales_team.revenue_by_rep_hospital)
		self.assertEqual(allowed, ["GET"], msg="revenue_by_rep_hospital() phải @frappe.whitelist(methods=['GET'])")

	# (10) no raw sql + batch --------------------------------------------------
	def test_no_raw_sql(self):
		import inspect

		src = inspect.getsource(sales_team)
		self.assertNotIn("frappe.db.sql", src, msg="KHÔNG raw SQL — dùng get_list/get_all")
		self.assertNotIn("SELECT", src.upper(), msg="KHÔNG raw SELECT string")
		# KHÔNG lộ email trong rows (full_name only).
		for row in self._res()["rows"]:
			for c in row["cells"]:
				if c is not None:
					for v in c.values():
						self.assertNotIn("@example.com", str(v))

	# (11) SSoT export ---------------------------------------------------------
	def test_ssot_exports(self):
		self.assertEqual(set(sales_team.REP_HOSP_ROW_KEYS), REP_HOSP_ROW_KEYS)
		# HEAT_LEVELS = 4 mức màu (h2c..h5c) thứ tự tăng dần.
		self.assertEqual(tuple(sales_team.HEAT_LEVELS), ("h2c", "h3c", "h4c", "h5c"))
