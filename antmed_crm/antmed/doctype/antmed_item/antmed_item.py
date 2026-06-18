# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""Controller cho DocType: AntMed Item (M03 Slice M03-S1 — catalog VTYT native-lite).

Master danh mục vật tư y tế (VTYT). native-lite (ADR-M03-01): tự chứa số ĐKLH /
mã ĐK lưu hành / requires_cocq / shelf_life / phân loại — KHÔNG dùng ERPNext Item.
autoname `field:item_code` (khoá tự nhiên → name == item_code). M02 đối chiếu SKU
trúng thầu dựa trên doctype này (Quota Item.item sẽ patch Data→Link khi M03 land).
"""

from frappe.model.document import Document


class AntMedItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		classification: DF.Literal["", "Loại A", "Loại B", "Loại C", "Loại D"]
		default_unit_price: DF.Currency
		disabled: DF.Check
		is_consignment: DF.Check
		item_code: DF.Data
		item_name: DF.Data
		ma_dkluuhanh: DF.Data | None
		manufacturer_code: DF.Data | None
		registration_no: DF.Data | None
		requires_cocq: DF.Check
		shelf_life_months: DF.Int
		uom: DF.Data | None
	# end: auto-generated types

	pass
