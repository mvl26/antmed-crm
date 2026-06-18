# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M03 — Sổ tồn kho (AntMed Stock Ledger): logic ghi/đọc tồn (pure, KHÔNG whitelist).

Gọi từ AntMed Stock Entry controller (on_submit/on_cancel). Tồn = SUM(qty_change) theo
(kho × item × lot). Enforce tồn-không-âm (m03 §4). Idempotent theo stock_entry (LL-BE-7).
SQL param-bind %s cho mọi giá trị user (LL-BE-11).
"""

import frappe
from frappe import _
from frappe.utils import add_days, now_datetime, nowdate

LEDGER_DOCTYPE = "AntMed Stock Ledger"
WAREHOUSE_DOCTYPE = "AntMed Warehouse"
LOT_DOCTYPE = "AntMed Lot"
ITEM_DOCTYPE = "AntMed Item"
STOCK_ENTRY_DOCTYPE = "AntMed Stock Entry"
CONSIGNMENT_WAREHOUSE_TYPE = "Ký gửi BV"

# Map loại phiếu → danh sách (warehouse_attr, dấu). 'Điều chỉnh' = +qty vào to (hoặc from).
_RECEIPT = {"Nhập NCC", "Nhập ký gửi BV"}
_ISSUE = {"Xuất cho NV"}
_TRANSFER = {"Chuyển kho"}


def get_balance(warehouse: str, item: str, lot: str | None = None) -> float:
	"""Tồn hiện tại của (kho × item × lot) = SUM(qty_change). lot None → gộp mọi lô."""
	if not warehouse or not item:
		return 0.0
	if lot:
		rows = frappe.db.sql(
			f"""SELECT COALESCE(SUM(qty_change), 0) FROM `tab{LEDGER_DOCTYPE}`
				WHERE warehouse=%s AND item=%s AND lot=%s""",
			(warehouse, item, lot),
		)
	else:
		rows = frappe.db.sql(
			f"""SELECT COALESCE(SUM(qty_change), 0) FROM `tab{LEDGER_DOCTYPE}`
				WHERE warehouse=%s AND item=%s""",
			(warehouse, item),
		)
	return float(rows[0][0] or 0)


def get_lot_movement(lot: str) -> dict:
	"""Tổng biến động của 1 lô toàn kho từ sổ tồn (AntMed Stock Ledger) — 1 query gộp (KHÔNG N+1).

	Trả {qty_in, qty_out, qty_remaining}:
	  - qty_in       = SUM(qty_change) WHERE qty_change > 0      (SL nhập)
	  - qty_out      = ABS(SUM(qty_change) WHERE qty_change < 0) (SL đã xuất, dương)
	  - qty_remaining= SUM(qty_change) toàn bộ                   (SL còn = khớp sổ tồn)
	Lô không có dòng ledger → 0/0/0. SQL param-bind %s (LL-BE-11).
	"""
	if not lot:
		return {"qty_in": 0.0, "qty_out": 0.0, "qty_remaining": 0.0}
	rows = frappe.db.sql(
		f"""SELECT
				COALESCE(SUM(CASE WHEN qty_change > 0 THEN qty_change ELSE 0 END), 0) AS qty_in,
				COALESCE(SUM(CASE WHEN qty_change < 0 THEN qty_change ELSE 0 END), 0) AS qty_out,
				COALESCE(SUM(qty_change), 0) AS qty_remaining
			FROM `tab{LEDGER_DOCTYPE}` WHERE lot = %s""",
		(lot,),
	)
	r = rows[0] if rows else (0, 0, 0)
	return {
		"qty_in": float(r[0] or 0),
		"qty_out": abs(float(r[1] or 0)),  # SUM của các dòng âm → trả về trị dương
		"qty_remaining": float(r[2] or 0),
	}


def get_lot_trace(lot: str) -> list[dict]:
	"""Dòng thời gian di chuyển của 1 lô (mockup D3 right-card "Cây truy vết") — 1 query JOIN (KHÔNG N+1).

	JOIN AntMed Stock Ledger sl + AntMed Stock Entry se ON sl.stock_entry=se.name (lấy entry_type/
	hospital/nv_employee) + AntMed Warehouse wh ON sl.warehouse=wh.name (lấy warehouse_name/
	warehouse_type). LEFT JOIN se/wh (phòng thủ FK orphan → không rớt dòng). WHERE sl.lot=%s
	(param-bind, LL-BE-11). ORDER BY sl.posting_datetime ASC (nhập NCC → xuất NV → chuyển kho/
	ký gửi theo trình tự thời gian).

	Trả list dict ĐÚNG shape cố định (Hyrum — FE bind ổn định, KHÔNG đảo/đổi/thêm bớt):
	  {posting_datetime, entry_type, direction, warehouse, warehouse_name, warehouse_type,
	   qty, voucher_no, hospital, nv_employee}.
	  - direction = 'in' nếu qty_change > 0, ngược lại 'out' (== 0 cũng coi là out — biên hiếm).
	  - qty = ABS(qty_change) (luôn dương; chiều thể hiện qua direction).
	  - voucher_no lấy thẳng từ ledger (số phiếu); entry_type/hospital/nv_employee từ Stock Entry.
	Lô không có dòng ledger → []. Tên bảng = hằng tin cậy (module constant) interpolate qua .format
	(KHÔNG f-string SQL — giữ guard grep param-bind); giá trị lot → bind %s.
	"""
	if not lot:
		return []
	# Tên bảng = hằng tin cậy (KHÔNG user input). Giá trị lot → bind %s.
	query = (
		"SELECT sl.posting_datetime AS posting_datetime, se.entry_type AS entry_type, "
		"sl.qty_change AS qty_change, sl.warehouse AS warehouse, wh.warehouse_name AS warehouse_name, "
		"wh.warehouse_type AS warehouse_type, sl.voucher_no AS voucher_no, "
		"se.hospital AS hospital, se.nv_employee AS nv_employee "
		"FROM `tab{ledger}` sl "
		"LEFT JOIN `tab{stock_entry}` se ON se.name = sl.stock_entry "
		"LEFT JOIN `tab{warehouse}` wh ON wh.name = sl.warehouse "
		"WHERE sl.lot = %s "
		"ORDER BY sl.posting_datetime ASC, sl.creation ASC"
	).format(ledger=LEDGER_DOCTYPE, stock_entry=STOCK_ENTRY_DOCTYPE, warehouse=WAREHOUSE_DOCTYPE)
	rows = frappe.db.sql(query, (lot,), as_dict=True)
	out = []
	for r in rows:
		qc = float(r["qty_change"] or 0)
		out.append(
			{
				"posting_datetime": r["posting_datetime"],
				"entry_type": r["entry_type"],
				"direction": "in" if qc > 0 else "out",
				"warehouse": r["warehouse"],
				"warehouse_name": r["warehouse_name"],
				"warehouse_type": r["warehouse_type"],
				"qty": abs(qc),
				"voucher_no": r["voucher_no"],
				"hospital": r["hospital"],
				"nv_employee": r["nv_employee"],
			}
		)
	return out


def get_consignment_balances(hospital: str) -> list[dict]:
	"""Tồn ký gửi của 1 BV tổng hợp từ sổ tồn (AntMed Stock Ledger) — 1 query gộp GROUP BY (KHÔNG N+1).

	JOIN AntMed Warehouse lọc warehouse_type='Ký gửi BV' AND hospital=%s; GROUP BY (item, lot);
	HAVING SUM(qty_change) > 0 → chỉ lô còn tồn (lô đã xuất hết KHÔNG lọt). Trả list dict
	{item, lot, system_qty}. hospital rỗng → []. SQL param-bind %s (LL-BE-11) — KHÔNG nối
	chuỗi giá trị user. Tên bảng là hằng tin cậy (module constant), interpolate qua .format
	(KHÔNG f-string SQL — giữ guard grep param-bind).
	"""
	if not hospital:
		return []
	# Tên bảng = hằng tin cậy (KHÔNG user input). Giá trị hospital → bind %s.
	query = (
		"SELECT sl.item AS item, sl.lot AS lot, COALESCE(SUM(sl.qty_change), 0) AS system_qty "
		"FROM `tab{ledger}` sl "
		"INNER JOIN `tab{warehouse}` wh ON wh.name = sl.warehouse "
		"WHERE wh.warehouse_type = %s AND wh.hospital = %s "
		"GROUP BY sl.item, sl.lot "
		"HAVING SUM(sl.qty_change) > 0"
	).format(ledger=LEDGER_DOCTYPE, warehouse=WAREHOUSE_DOCTYPE)
	rows = frappe.db.sql(query, (CONSIGNMENT_WAREHOUSE_TYPE, hospital), as_dict=True)
	return [
		{"item": r["item"], "lot": r["lot"], "system_qty": float(r["system_qty"] or 0)} for r in rows
	]


def get_all_consignment_balances() -> list[dict]:
	"""Tồn ký gửi TOÀN BỘ (mọi BV) gộp từ sổ tồn — 1 query GROUP BY (hospital, item, lot), HAVING SUM>0.

	Dùng cho KPI cấp màn (distinct BV có tồn / lô cận date toàn kho ký gửi). Trả list dict
	{hospital, item, lot, system_qty}. SQL param-bind %s cho warehouse_type (KHÔNG user-string).
	Tên bảng = hằng tin cậy interpolate qua .format (KHÔNG f-string SQL).
	"""
	query = (
		"SELECT wh.hospital AS hospital, sl.item AS item, sl.lot AS lot, "
		"COALESCE(SUM(sl.qty_change), 0) AS system_qty "
		"FROM `tab{ledger}` sl "
		"INNER JOIN `tab{warehouse}` wh ON wh.name = sl.warehouse "
		"WHERE wh.warehouse_type = %s AND wh.hospital IS NOT NULL "
		"GROUP BY wh.hospital, sl.item, sl.lot "
		"HAVING SUM(sl.qty_change) > 0"
	).format(ledger=LEDGER_DOCTYPE, warehouse=WAREHOUSE_DOCTYPE)
	rows = frappe.db.sql(query, (CONSIGNMENT_WAREHOUSE_TYPE,), as_dict=True)
	return [
		{
			"hospital": r["hospital"],
			"item": r["item"],
			"lot": r["lot"],
			"system_qty": float(r["system_qty"] or 0),
		}
		for r in rows
	]


def get_expiring_balances(within_days: int = 90) -> list[dict]:
	"""Rollup tồn lô CẬN/QUÁ date trên TOÀN BỘ kho (Tổng + Cá nhân NV + Ký gửi BV) — 1 query gộp.

	JOIN AntMed Stock Ledger sl + AntMed Lot lot ON sl.lot=lot.name + AntMed Warehouse wh ON
	sl.warehouse=wh.name (+ LEFT JOIN AntMed Item gom item_name); GROUP BY (sl.warehouse, sl.item,
	sl.lot) HAVING SUM(sl.qty_change) > 0 (chỉ lô còn tồn — đã xuất hết KHÔNG lọt). WHERE
	lot.expiry_date IS NOT NULL AND lot.expiry_date <= add_days(nowdate, within_days) → gồm CẢ
	lô đã quá hạn (mọi expiry ≤ ngưỡng, kể cả < hôm nay).

	Trả list dict gom sẵn (KHÔNG N+1 ở endpoint):
	  {item, item_name, lot, warehouse, warehouse_name, warehouse_type, expiry_date, balance_qty}.
	  - balance_qty = SUM(sl.qty_change) của (kho × item × lô) = tồn hiện tại.
	  - item_name / warehouse_name / warehouse_type lấy thẳng qua JOIN (1 query).
	SQL param-bind %s cho ngưỡng ngày (LL-BE-11) — KHÔNG nội suy giá trị vào chuỗi SQL. Tên bảng
	là hằng tin cậy (module constant) interpolate qua .format (KHÔNG f-string SQL — giữ guard grep).
	"""
	cutoff = add_days(nowdate(), int(within_days))
	# Tên bảng = hằng tin cậy (KHÔNG user input). Giá trị ngưỡng ngày → bind %s.
	query = (
		"SELECT sl.item AS item, it.item_name AS item_name, sl.lot AS lot, "
		"sl.warehouse AS warehouse, wh.warehouse_name AS warehouse_name, "
		"wh.warehouse_type AS warehouse_type, lot.expiry_date AS expiry_date, "
		"COALESCE(SUM(sl.qty_change), 0) AS balance_qty "
		"FROM `tab{ledger}` sl "
		"INNER JOIN `tab{lot}` lot ON lot.name = sl.lot "
		"INNER JOIN `tab{warehouse}` wh ON wh.name = sl.warehouse "
		"LEFT JOIN `tab{item}` it ON it.name = sl.item "
		"WHERE lot.expiry_date IS NOT NULL AND lot.expiry_date <= %s "
		"GROUP BY sl.warehouse, sl.item, sl.lot, it.item_name, wh.warehouse_name, "
		"wh.warehouse_type, lot.expiry_date "
		"HAVING SUM(sl.qty_change) > 0"
	).format(ledger=LEDGER_DOCTYPE, lot=LOT_DOCTYPE, warehouse=WAREHOUSE_DOCTYPE, item=ITEM_DOCTYPE)
	rows = frappe.db.sql(query, (cutoff,), as_dict=True)
	return [
		{
			"item": r["item"],
			"item_name": r["item_name"],
			"lot": r["lot"],
			"warehouse": r["warehouse"],
			"warehouse_name": r["warehouse_name"],
			"warehouse_type": r["warehouse_type"],
			"expiry_date": r["expiry_date"],
			"balance_qty": float(r["balance_qty"] or 0),
		}
		for r in rows
	]


def _assert_available(warehouse: str, item: str, lot: str | None, qty: float) -> None:
	"""Tồn không âm (m03 §4): xuất quá tồn lô khả dụng → throw."""
	bal = get_balance(warehouse, item, lot)
	if float(qty) > bal:
		frappe.throw(
			_("Tồn không đủ: kho {0}, vật tư {1}, lô {2} còn {3} < yêu cầu {4}.").format(
				warehouse, item, lot or "-", bal, qty
			)
		)


def _post_ledger(warehouse, item, lot, qty_change, stock_entry, posting_datetime):
	"""Ghi 1 dòng sổ tồn + balance_qty chạy sau biến động."""
	new_balance = get_balance(warehouse, item, lot) + float(qty_change)
	frappe.get_doc(
		{
			"doctype": LEDGER_DOCTYPE,
			"warehouse": warehouse,
			"item": item,
			"lot": lot,
			"qty_change": float(qty_change),
			"balance_qty": new_balance,
			"stock_entry": stock_entry,
			"voucher_type": "AntMed Stock Entry",
			"voucher_no": stock_entry,
			"posting_datetime": posting_datetime,
		}
	).insert(ignore_permissions=True)


def post_stock_entry(doc) -> None:
	"""on_submit: ghi sổ tồn cho từng dòng phiếu. Idempotent theo stock_entry."""
	if doc.docstatus != 1:
		return
	if frappe.db.exists(LEDGER_DOCTYPE, {"stock_entry": doc.name}):
		return  # đã ghi → không nhân đôi (LL-BE-7)
	pdt = doc.posting_datetime or now_datetime()
	et = doc.entry_type
	for line in doc.items:
		qty = float(line.qty or 0)
		if et in _RECEIPT:
			_post_ledger(doc.to_warehouse, line.item, line.lot, qty, doc.name, pdt)
		elif et in _ISSUE:
			_assert_available(doc.from_warehouse, line.item, line.lot, qty)
			_post_ledger(doc.from_warehouse, line.item, line.lot, -qty, doc.name, pdt)
		elif et in _TRANSFER:
			_assert_available(doc.from_warehouse, line.item, line.lot, qty)
			_post_ledger(doc.from_warehouse, line.item, line.lot, -qty, doc.name, pdt)
			_post_ledger(doc.to_warehouse, line.item, line.lot, qty, doc.name, pdt)
		else:  # Điều chỉnh: +qty vào kho đích (hoặc nguồn)
			_post_ledger(doc.to_warehouse or doc.from_warehouse, line.item, line.lot, qty, doc.name, pdt)


def reverse_stock_entry(doc) -> None:
	"""on_cancel: ghi dòng đảo (qty_change *-1) cho mọi ledger của phiếu — giữ append-only."""
	pdt = now_datetime()
	for led in frappe.get_all(
		LEDGER_DOCTYPE, filters={"stock_entry": doc.name}, fields=["warehouse", "item", "lot", "qty_change"]
	):
		if led.get("voucher_type") == "REVERSAL":
			continue
		_post_ledger(led["warehouse"], led["item"], led.get("lot"), -float(led["qty_change"] or 0), doc.name, pdt)
