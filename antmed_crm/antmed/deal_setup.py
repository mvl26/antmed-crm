# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M08 — Custom field AntMed trên CRM Deal (gộp pipeline về CRM Deal, kế thừa Frappe CRM).

Pipeline cơ hội/deal = CRM Deal. Thông tin gói thầu VTYT (bệnh viện, số thầu, số QĐ KQLCNT)
là custom field trên chính CRM Deal — KHÔNG tách doctype riêng (AntMed Tender retire khỏi UI).

Chạy:  bench --site miyano execute antmed_crm.antmed.deal_setup.setup_deal_fields
(nên wire vào after_migrate để tái lập khi migrate).
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

DEAL_CUSTOM_FIELDS = {
	"CRM Deal": [
		{
			"fieldname": "am_section",
			"fieldtype": "Section Break",
			"label": "AntMed — Gói thầu / VTYT",
			"insert_after": "deal_value",
			"collapsible": 1,
		},
		{
			"fieldname": "am_hospital",
			"fieldtype": "Link",
			"options": "AntMed Hospital",
			"label": "Bệnh viện (AntMed)",
			"insert_after": "am_section",
		},
		{
			"fieldname": "am_tender_no",
			"fieldtype": "Data",
			"label": "Số gói thầu",
			"insert_after": "am_hospital",
		},
		{
			"fieldname": "am_decision_no",
			"fieldtype": "Data",
			"label": "Số QĐ KQLCNT (trúng thầu)",
			"insert_after": "am_tender_no",
		},
	]
}


def setup_deal_fields():
	create_custom_fields(DEAL_CUSTOM_FIELDS, ignore_validate=True)
	frappe.db.commit()
	print("CRM Deal custom fields ready:", [f["fieldname"] for f in DEAL_CUSTOM_FIELDS["CRM Deal"]])
