# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M03 — Sổ tồn kho (AntMed Stock Ledger): logic ghi/đọc tồn (pure, KHÔNG whitelist).

Gọi từ AntMed Stock Entry controller (on_submit/on_cancel). Tồn = SUM(qty_change) theo
(kho × item × lot). Enforce tồn-không-âm (m03 §4). Idempotent theo stock_entry (LL-BE-7).
SQL param-bind %s cho mọi giá trị user (LL-BE-11).
"""

import frappe
from frappe import _
from frappe.utils import now_datetime

LEDGER_DOCTYPE = "AntMed Stock Ledger"

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
