# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""Controller cho DocType: AntMed Stock Entry (M03 — phiếu nhập/xuất/chuyển kho).

Submit → ghi AntMed Stock Ledger (sổ tồn) + enforce tồn-không-âm (m03 §4). Logic sổ tồn
sống ở antmed_crm.antmed.stock (idempotent theo stock_entry). on_cancel đảo ledger.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate

# Loại phiếu cần kho nguồn / kho đích.
_NEEDS_TO = {"Nhập NCC", "Nhập ký gửi BV"}
_NEEDS_FROM = {"Xuất cho NV", "Giao phòng mổ"}
_NEEDS_BOTH = {"Chuyển kho"}

# Loại phiếu ĐƯA HÀNG đi để DÙNG (xuất cho NV / đặt ký gửi BV / giao phòng mổ) → chặn cứng lô đã
# thu hồi (recall) + lô hết hạn (HSD). 'Chuyển kho'/'Điều chỉnh' KHÔNG chặn (gom về cách ly/thanh lý).
_ISSUE_TO_USE = {"Xuất cho NV", "Nhập ký gửi BV", "Giao phòng mổ"}
_RECALL_BLOCKED = "Đã thu hồi"


class AntMedStockEntry(Document):
	def validate(self):
		"""Bắt buộc kho phù hợp theo loại phiếu (m03 §2/§4) + set cocq_ok mỗi dòng (BR-03)."""
		et = self.entry_type
		if et in _NEEDS_TO and not self.to_warehouse:
			frappe.throw(_("Phiếu '{0}' phải có kho đến (to_warehouse).").format(et))
		if et in _NEEDS_FROM and not self.from_warehouse:
			frappe.throw(_("Phiếu '{0}' phải có kho nguồn (from_warehouse).").format(et))
		if et in _NEEDS_BOTH and not (self.from_warehouse and self.to_warehouse):
			frappe.throw(_("Phiếu 'Chuyển kho' phải có cả kho nguồn và kho đến."))
		self._set_cocq_flags()
		for line in self.items:
			line.amount = (line.qty or 0) * (line.unit_price or 0)

	def _set_cocq_flags(self) -> None:
		"""BR-03 — set cờ cocq_ok mỗi dòng + chặn cứng lô đã thu hồi khi xuất (recall safety).

		Batch-fetch requires_cocq (AntMed Item) + co_cert/cq_cert/recall_status (AntMed Lot) bằng
		ĐÚNG ≤2 query (KHÔNG N+1). cocq_ok: vật tư yêu cầu CO/CQ mà lô thiếu chứng từ → 0 (FE wizard
		dùng cờ này chặn 'Xuất cho NV' — mockup 'thiếu CQ — không thể xuất'; M03 chỉ gắn cờ, M06 chặn
		cứng phát hành). Recall: phiếu ĐƯA HÀNG đi để DÙNG (_ISSUE_TO_USE) mà lô 'Đã thu hồi' → throw
		(an toàn — KHÔNG bao giờ xuất lô recall cho NV/đặt ký gửi BV; vẫn cho Chuyển kho gom cách ly).
		"""
		from antmed_crm.antmed import stock

		item_codes = {line.item for line in self.items if line.item}
		lot_codes = {line.lot for line in self.items if line.lot}
		req_map = (
			{
				r["name"]: r["requires_cocq"]
				for r in frappe.get_all(
					"AntMed Item",
					filters={"name": ["in", list(item_codes)]},
					fields=["name", "requires_cocq"],
				)
			}
			if item_codes
			else {}
		)
		lot_map = (
			{
				r["name"]: r
				for r in frappe.get_all(
					"AntMed Lot",
					filters={"name": ["in", list(lot_codes)]},
					fields=["name", "co_cert", "cq_cert", "recall_status", "expiry_date"],
				)
			}
			if lot_codes
			else {}
		)
		blocks_issue = self.entry_type in _ISSUE_TO_USE
		today = getdate(nowdate())
		for line in self.items:
			lot = lot_map.get(line.lot) or {}
			line.cocq_ok = stock.compute_cocq_ok(
				req_map.get(line.item, 0), lot.get("co_cert"), lot.get("cq_cert")
			)
			if not blocks_issue:
				continue
			# An toàn recall: KHÔNG xuất/đặt ký gửi lô đã thu hồi.
			if lot.get("recall_status") == _RECALL_BLOCKED:
				frappe.throw(_("Lô {0} đã bị thu hồi (recall) — không thể xuất/đặt ký gửi.").format(line.lot))
			# An toàn HSD: KHÔNG xuất/đặt ký gửi lô đã hết hạn (expiry < hôm nay).
			expiry = lot.get("expiry_date")
			if expiry and getdate(expiry) < today:
				frappe.throw(
					_("Lô {0} đã hết hạn (HSD {1}) — không thể xuất/đặt ký gửi.").format(
						line.lot, getdate(expiry).strftime("%d/%m/%Y")
					)
				)

	def on_submit(self):
		from antmed_crm.antmed import stock

		stock.post_stock_entry(self)

	def on_cancel(self):
		from antmed_crm.antmed import stock

		stock.reverse_stock_entry(self)
