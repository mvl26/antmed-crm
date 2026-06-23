# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M08 Slice S1 — endpoint Pipeline / Gói thầu (AntMed Tender).

Đường gọi: antmed_crm.api.antmed.pipeline.<fn> (xem m08_pipeline.md §5).
@frappe.whitelist(), type-annotated, RAW dict. count==rows (BR-13).
BR-M08-01 (tender_no unique — field) · BR-M08-02 (Trúng cần decision_no).
"""

import frappe
from frappe import _

from antmed_crm.api.antmed._filters import coerce_filters

TENDER_DOCTYPE = "AntMed Tender"
HOSPITAL_DOCTYPE = "AntMed Hospital"

TENDER_LIST_FIELDS = [
	"name",
	"tender_no",
	"tender_name",
	"hospital",
	"hospital.hospital_name as hospital_name",
	"status",
	"estimated_value",
	"win_probability_pct",
]
TENDER_LIST_ITEM_KEYS = (
	"name",
	"tender_no",
	"tender_name",
	"hospital",
	"hospital_name",
	"status",
	"estimated_value",
	"win_probability_pct",
)
TENDER_DETAIL_FIELDS = (
	"name",
	"tender_no",
	"tender_name",
	"hospital",
	"status",
	"source",
	"bid_open_date",
	"bid_close_date",
	"estimated_value",
	"win_probability_pct",
	"result",
	"decision_no",
	"won_contract",
	"deal",
	"docstatus",
)

# Giai đoạn pipeline hợp lệ (state machine nhẹ qua status).
_STAGES = ("Tiếp cận", "Khảo sát", "Báo giá", "Dự thầu", "Trúng", "Trượt")

# Xác suất thắng mặc định theo giai đoạn (kéo-thả đổi giai đoạn → forecast cập nhật ngay).
STAGE_PROB = {"Tiếp cận": 10, "Khảo sát": 25, "Báo giá": 50, "Dự thầu": 75}


def _coerce_filters(filters: dict | str | None) -> list:
	return coerce_filters(filters)


@frappe.whitelist(methods=["POST"])
def create_tender(
	tender_no: str,
	tender_name: str,
	hospital: str | None = None,
	source: str | None = None,
	estimated_value: float | None = None,
	bid_open_date: str | None = None,
	bid_close_date: str | None = None,
) -> dict:
	"""Tạo gói thầu mới (status 'Tiếp cận'). BR-M08-01: tender_no unique (field)."""
	if not frappe.has_permission(TENDER_DOCTYPE, "create"):
		frappe.throw(_("Bạn không có quyền tạo gói thầu."), frappe.PermissionError)
	doc = frappe.get_doc(
		{
			"doctype": TENDER_DOCTYPE,
			"tender_no": tender_no,
			"tender_name": tender_name,
			"hospital": hospital,
			"source": source,
			"estimated_value": estimated_value,
			"bid_open_date": bid_open_date,
			"bid_close_date": bid_close_date,
			"status": "Tiếp cận",
		}
	)
	doc.insert(ignore_permissions=True)
	return {"name": doc.name, "status": doc.status}


@frappe.whitelist(methods=["POST"])
def move_stage(name: str, stage: str) -> dict:
	"""Chuyển giai đoạn pipeline (Tiếp cận→…→Dự thầu). Trúng/Trượt qua set_tender_result."""
	if not frappe.has_permission(TENDER_DOCTYPE, "write", doc=name):
		frappe.throw(_("Bạn không có quyền cập nhật gói thầu."), frappe.PermissionError)
	if stage not in _STAGES[:4]:
		frappe.throw(_("Giai đoạn '{0}' không hợp lệ (Trúng/Trượt dùng set_tender_result).").format(stage))
	# Kéo-thả 2 chiều: set status BẤT KỲ giai đoạn non-terminal + đồng bộ win% theo giai đoạn.
	prob = STAGE_PROB.get(stage, 0)
	frappe.db.set_value(TENDER_DOCTYPE, name, {"status": stage, "win_probability_pct": prob, "result": None})
	return {"name": name, "status": stage, "win_probability_pct": prob}


@frappe.whitelist(methods=["POST"])
def set_tender_result(name: str, result: str, decision_no: str | None = None) -> dict:
	"""Chốt kết quả thầu. BR-M08-02: 'Trúng' bắt buộc có decision_no (số QĐ KQLCNT)."""
	if not frappe.has_permission(TENDER_DOCTYPE, "write", doc=name):
		frappe.throw(_("Bạn không có quyền cập nhật gói thầu."), frappe.PermissionError)
	if result not in ("Trúng", "Trượt"):
		frappe.throw(_("Kết quả phải là 'Trúng' hoặc 'Trượt'."))
	if result == "Trúng" and not decision_no:
		frappe.throw(_("BR-M08-02: Gói thầu 'Trúng' phải có số quyết định (decision_no)."))
	win_pct = 100 if result == "Trúng" else 0
	frappe.db.set_value(
		TENDER_DOCTYPE,
		name,
		{"status": result, "result": result, "decision_no": decision_no, "win_probability_pct": win_pct},
	)
	won_contract = None
	if result == "Trúng":
		won_contract = _ensure_won_contract(name)
	return {"name": name, "status": result, "decision_no": decision_no, "won_contract": won_contract}


def _ensure_won_contract(tender_name: str) -> str | None:
	"""BR-M08-05: gói Trúng → tạo HĐ NHÁP (AntMed Contract) từ gói thầu. Idempotent (skip nếu đã có)."""
	existing = frappe.db.get_value(TENDER_DOCTYPE, tender_name, "won_contract")
	if existing:
		return existing
	from frappe.utils import nowdate

	tender = frappe.get_doc(TENDER_DOCTYPE, tender_name)
	contract_no = f"HD-{tender.tender_no}"
	if frappe.db.exists("AntMed Contract", {"contract_no": contract_no}):
		c_name = frappe.db.get_value("AntMed Contract", {"contract_no": contract_no}, "name")
	else:
		c = frappe.get_doc(
			{
				"doctype": "AntMed Contract",
				"contract_no": contract_no,
				"hospital": tender.hospital,
				"signed_date": nowdate(),
				"status": "Nháp",
				"total_value": tender.estimated_value,
			}
		)
		c.insert(ignore_permissions=True)
		c_name = c.name
	frappe.db.set_value(TENDER_DOCTYPE, tender_name, "won_contract", c_name)
	return c_name


@frappe.whitelist(methods=["GET"])
def forecast() -> dict:
	"""Dự báo doanh số pipeline = Σ(estimated_value × win_probability_pct/100), gộp theo giai đoạn.

	Trả {total_weighted, by_stage:[{stage, weighted}]}. Đọc dưới DocPerm.
	"""
	rows = frappe.get_list(
		TENDER_DOCTYPE, fields=["status", "estimated_value", "win_probability_pct"], limit_page_length=0
	)
	total = 0.0
	by_stage: dict = {}
	for r in rows:
		w = float(r.get("estimated_value") or 0) * float(r.get("win_probability_pct") or 0) / 100.0
		total += w
		by_stage[r.get("status")] = by_stage.get(r.get("status"), 0.0) + w
	return {
		"total_weighted": round(total, 2),
		"by_stage": [{"stage": s, "weighted": round(v, 2)} for s, v in by_stage.items()],
	}


@frappe.whitelist(methods=["GET"])
def list_tenders(
	filters: dict | str | None = None,
	status: str | None = None,
	start: int = 0,
	page_length: int = 20,
) -> dict:
	"""Danh sách gói thầu. Trả RAW {data, total_count} — count==rows dưới DocPerm."""
	conditions = _coerce_filters(filters)
	if status:
		conditions.append(["status", "=", status])
	start = max(0, int(start))
	page_length = max(0, int(page_length))
	rows = frappe.get_list(
		TENDER_DOCTYPE,
		filters=conditions,
		fields=TENDER_LIST_FIELDS,
		limit_start=start,
		limit_page_length=page_length or 0,
		order_by=f"`tab{TENDER_DOCTYPE}`.modified desc",
	)
	data = [{k: r.get(k) for k in TENDER_LIST_ITEM_KEYS} for r in rows]
	total_count = len(frappe.get_list(TENDER_DOCTYPE, filters=conditions, pluck="name", limit_page_length=0))
	return {"data": data, "total_count": total_count}


@frappe.whitelist(methods=["GET"])
def get_tender(name: str) -> dict:
	"""Chi tiết gói thầu + hospital_name. throw PermissionError nếu không read."""
	if not frappe.has_permission(TENDER_DOCTYPE, "read", doc=name):
		frappe.throw(_("Bạn không có quyền xem gói thầu này."), frappe.PermissionError)
	doc = frappe.get_doc(TENDER_DOCTYPE, name).as_dict()
	result = {k: doc.get(k) for k in TENDER_DETAIL_FIELDS}
	result["hospital_name"] = (
		frappe.db.get_value(HOSPITAL_DOCTYPE, doc.get("hospital"), "hospital_name")
		if doc.get("hospital")
		else None
	)
	return result


# ── Lead (KẾ THỪA CRM Lead của Frappe CRM, scoped qua org_hierarchy BR-13) ──────

LEAD_DOCTYPE = "CRM Lead"
LEAD_FIELDS = [
	"name",
	"lead_name",
	"organization",
	"status",
	"territory",
	"lead_owner",
	"mobile_no",
	"email_id",
	"annual_revenue",
]


@frappe.whitelist(methods=["GET"])
def lead_statuses() -> dict:
	"""Danh sách trạng thái Lead (CRM Lead Status) cho filter/kanban."""
	return {"statuses": frappe.get_all("CRM Lead Status", pluck="name")}


@frappe.whitelist(methods=["GET"])
def list_leads(
	status: str | None = None,
	search: str | None = None,
	start: int = 0,
	page_length: int = 50,
) -> dict:
	"""Danh sách Lead — get_list CRM Lead (TÔN TRỌNG permission_query_conditions org_hierarchy →
	NV chỉ thấy lead của tuyến mình, BR-13). Trả RAW {data, total_count}. Enrich tên NV phụ trách.
	"""
	conditions = []
	if status:
		conditions.append(["status", "=", status])
	if search:
		conditions.append(["lead_name", "like", f"%{search}%"])
	start = max(0, int(start))
	page_length = max(0, int(page_length))
	rows = frappe.get_list(
		LEAD_DOCTYPE,
		filters=conditions,
		fields=LEAD_FIELDS,
		limit_start=start,
		limit_page_length=page_length or 0,
		order_by="modified desc",
	)
	owners = list({r.lead_owner for r in rows if r.lead_owner})
	omap = (
		{
			u.name: u.full_name
			for u in frappe.get_all("User", filters={"name": ["in", owners]}, fields=["name", "full_name"])
		}
		if owners
		else {}
	)
	data = []
	for r in rows:
		data.append(
			{
				"name": r.name,
				"lead_name": r.lead_name or r.name,
				"organization": r.organization,
				"status": r.status,
				"territory": r.territory,
				"mobile_no": r.mobile_no,
				"email": r.email_id,
				"annual_revenue": r.annual_revenue,
				"lead_owner": r.lead_owner,
				"lead_owner_name": omap.get(r.lead_owner) or r.lead_owner,
			}
		)
	total_count = len(frappe.get_list(LEAD_DOCTYPE, filters=conditions, pluck="name", limit_page_length=0))
	return {"data": data, "total_count": total_count}


@frappe.whitelist(methods=["GET"])
def lead_form_options() -> dict:
	"""Option cho form tạo Lead: nguồn (CRM Lead Source) + khu vực (CRM Territory).

	Trả {sources: [name], territories: [name]} — FE đổ dropdown. Rỗng → dropdown chỉ có "(trống)".
	"""
	return {
		"sources": frappe.get_all("CRM Lead Source", pluck="name", order_by="name asc"),
		"territories": frappe.get_all("CRM Territory", pluck="name", order_by="name asc"),
	}


@frappe.whitelist(methods=["POST"])
def create_lead(
	lead_name: str,
	organization: str | None = None,
	mobile_no: str | None = None,
	phone: str | None = None,
	email: str | None = None,
	website: str | None = None,
	job_title: str | None = None,
	source: str | None = None,
	territory: str | None = None,
	status: str | None = None,
) -> dict:
	"""Tạo CRM Lead mới (kế thừa doctype Frappe CRM). lead_owner mặc định = user phiên.

	Field bổ sung (đều optional, khớp doctype CRM Lead): phone (cố định), website, job_title
	(chức danh người liên hệ), source (Link CRM Lead Source), territory (Link CRM Territory).
	"""
	if not frappe.has_permission(LEAD_DOCTYPE, "create"):
		frappe.throw(_("Bạn không có quyền tạo lead."), frappe.PermissionError)
	if not (lead_name or "").strip():
		frappe.throw(_("Tên lead bắt buộc."))
	doc = frappe.get_doc(
		{
			"doctype": LEAD_DOCTYPE,
			"first_name": lead_name.strip(),
			"organization": organization,
			"mobile_no": mobile_no,
			"phone": phone,
			"email_id": email,
			"website": website,
			"job_title": job_title,
			"source": source or None,
			"territory": territory or None,
			"status": status or "New",
			"lead_owner": frappe.session.user,
		}
	)
	doc.insert()
	return {"name": doc.name, "lead_name": doc.get("lead_name") or doc.name, "status": doc.status}


# ── M08-S3: Lead pipeline (chi tiết + qualify→Tender + funnel) ──────────────────
LEAD_DETAIL_KEYS = (
	"name",
	"lead_name",
	"organization",
	"status",
	"territory",
	"mobile_no",
	"email_id",
	"annual_revenue",
	"lead_owner",
	"source",
)
# Map giai đoạn funnel (mockup): Lead = CRM Lead; còn lại = giai đoạn AntMed Tender.
_FUNNEL_TENDER_STAGES = (
	("khao_sat", "Khảo sát"),
	("bao_gia", "Báo giá"),
	("du_thau", "Dự thầu"),
	("trung", "Trúng"),
)


@frappe.whitelist(methods=["GET"])
def get_lead(name: str) -> dict:
	"""Chi tiết Lead (kế thừa CRM Lead) + lead_owner_name + tender (nếu đã qualify). PermissionError nếu noperm."""
	if not frappe.has_permission(LEAD_DOCTYPE, "read", doc=name):
		frappe.throw(_("Bạn không có quyền xem lead này."), frappe.PermissionError)
	doc = frappe.get_doc(LEAD_DOCTYPE, name).as_dict()
	result = {k: doc.get(k) for k in LEAD_DETAIL_KEYS}
	result["lead_name"] = doc.get("lead_name") or name
	result["lead_owner_name"] = (
		frappe.db.get_value("User", doc.get("lead_owner"), "full_name") if doc.get("lead_owner") else None
	)
	result["tender"] = frappe.db.get_value(TENDER_DOCTYPE, {"source_lead": name}, "name")
	return result


@frappe.whitelist(methods=["POST"])
def convert_lead_to_tender(name: str, estimated_value: float | None = None) -> dict:
	"""Qualify 1 Lead → tạo AntMed Tender (gói thầu) gắn source_lead. Idempotent (1 tender/lead).

	hospital resolve theo organization của lead nếu khớp 1 AntMed Hospital (theo tên), else None.
	"""
	if not frappe.has_permission(TENDER_DOCTYPE, "create"):
		frappe.throw(_("Bạn không có quyền tạo gói thầu."), frappe.PermissionError)
	if not frappe.has_permission(LEAD_DOCTYPE, "read", doc=name):
		frappe.throw(_("Bạn không có quyền xem lead này."), frappe.PermissionError)
	existing = frappe.db.get_value(TENDER_DOCTYPE, {"source_lead": name}, "name")
	if existing:
		return {"lead": name, "tender": existing, "created": False}
	lead = frappe.get_doc(LEAD_DOCTYPE, name)
	org = lead.get("organization")
	hospital = frappe.db.get_value(HOSPITAL_DOCTYPE, {"hospital_name": org}, "name") if org else None
	tender = frappe.get_doc(
		{
			"doctype": TENDER_DOCTYPE,
			"tender_no": f"TND-{name}",
			"tender_name": org or lead.get("lead_name") or name,
			"hospital": hospital,
			"source": "Lead",
			"source_lead": name,
			"estimated_value": estimated_value,
			"status": "Tiếp cận",
		}
	)
	tender.insert(ignore_permissions=True)
	return {"lead": name, "tender": tender.name, "created": True}


@frappe.whitelist(methods=["GET"])
def lead_funnel() -> dict:
	"""Phễu pipeline (mockup): Lead (CRM Lead) → Khảo sát → Báo giá → Dự thầu → Trúng (AntMed Tender).

	Đếm DƯỚI permission (get_list — org_hierarchy/DocPerm). Trả {stages:[{key,label,count}]}.
	"""
	lead_count = len(frappe.get_list(LEAD_DOCTYPE, pluck="name", limit_page_length=0))
	stages = [{"key": "lead", "label": "Lead", "count": lead_count}]
	for key, status in _FUNNEL_TENDER_STAGES:
		count = len(
			frappe.get_list(TENDER_DOCTYPE, filters={"status": status}, pluck="name", limit_page_length=0)
		)
		stages.append({"key": key, "label": status, "count": count})
	return {"stages": stages}


# ── M08 (GỘP): Pipeline CƠ HỘI = CRM Deal (kế thừa Frappe CRM) ───────────────
# Pipeline chính = CRM Deal; gói thầu VTYT = custom field am_* trên Deal (deal_setup.py).

DEAL_DOCTYPE = "CRM Deal"
DEAL_STATUS_DOCTYPE = "CRM Deal Status"
DEAL_CARD_FIELDS = [
	"name",
	"organization",
	"deal_value",
	"status",
	"deal_owner",
	"probability",
	"territory",
	"expected_closure_date",
	"am_hospital",
	"am_tender_no",
	"am_decision_no",
]
DEAL_DETAIL_FIELDS = (
	"name",
	"organization",
	"deal_value",
	"currency",
	"status",
	"deal_owner",
	"probability",
	"territory",
	"expected_closure_date",
	"lead_name",
	"am_hospital",
	"am_tender_no",
	"am_decision_no",
)


def _deal_stage_rows():
	return frappe.get_all(DEAL_STATUS_DOCTYPE, fields=["name", "type", "position"], order_by="position asc")


@frappe.whitelist(methods=["GET"])
def deal_stages() -> dict:
	"""Giai đoạn pipeline = CRM Deal Status (order theo position)."""
	return {"stages": _deal_stage_rows()}


@frappe.whitelist(methods=["GET"])
def deal_board() -> dict:
	"""Kanban Cơ hội (CRM Deal) — group theo CRM Deal Status + forecast (weighted prob).

	get_list → tôn trọng org_hierarchy (BR-13). Enrich tên NV + BV (am_hospital).
	Trả {stages:[{name,type}], by_stage:{status:[cards]}, forecast:{total_weighted, by_stage}}.
	"""
	stages = _deal_stage_rows()
	deals = frappe.get_list(
		DEAL_DOCTYPE, fields=DEAL_CARD_FIELDS, limit_page_length=0, order_by="modified desc"
	)

	owners = list({d.deal_owner for d in deals if d.deal_owner})
	omap = (
		{
			u.name: u.full_name
			for u in frappe.get_all("User", filters={"name": ["in", owners]}, fields=["name", "full_name"])
		}
		if owners
		else {}
	)
	hosps = list({d.am_hospital for d in deals if d.get("am_hospital")})
	hmap = (
		{
			h.name: h.hospital_name
			for h in frappe.get_all(
				"AntMed Hospital", filters={"name": ["in", hosps]}, fields=["name", "hospital_name"]
			)
		}
		if hosps
		else {}
	)

	by_stage = {s.name: [] for s in stages}
	weighted = {s.name: 0.0 for s in stages}
	total = 0.0
	for d in deals:
		w = float(d.deal_value or 0) * float(d.probability or 0) / 100.0
		total += w
		if d.status in by_stage:
			by_stage[d.status].append(
				{
					"name": d.name,
					"organization": d.organization,
					"deal_value": d.deal_value,
					"status": d.status,
					"deal_owner": d.deal_owner,
					"deal_owner_name": omap.get(d.deal_owner) or d.deal_owner,
					"probability": d.probability,
					"territory": d.territory,
					"am_hospital": d.get("am_hospital"),
					"am_hospital_name": hmap.get(d.get("am_hospital")),
					"am_tender_no": d.get("am_tender_no"),
				}
			)
			weighted[d.status] += w
	return {
		"stages": [{"name": s.name, "type": s.type} for s in stages],
		"by_stage": by_stage,
		"forecast": {
			"total_weighted": round(total, 2),
			"by_stage": [{"stage": s.name, "weighted": round(weighted[s.name], 2)} for s in stages],
		},
	}


@frappe.whitelist(methods=["POST"])
def move_deal(deal: str, status: str) -> dict:
	"""Kéo-thả: đổi giai đoạn CRM Deal (2 chiều). Won→prob 100, Lost→0 (đồng bộ)."""
	if not frappe.has_permission(DEAL_DOCTYPE, "write", doc=deal):
		frappe.throw(_("Bạn không có quyền cập nhật cơ hội này."), frappe.PermissionError)
	if not frappe.db.exists(DEAL_STATUS_DOCTYPE, status):
		frappe.throw(_("Giai đoạn '{0}' không hợp lệ.").format(status))
	stype = frappe.db.get_value(DEAL_STATUS_DOCTYPE, status, "type")
	vals = {"status": status}
	if stype == "Won":
		vals["probability"] = 100
	elif stype == "Lost":
		vals["probability"] = 0
	frappe.db.set_value(DEAL_DOCTYPE, deal, vals)
	return {"name": deal, "status": status}


@frappe.whitelist(methods=["GET"])
def get_deal(deal: str) -> dict:
	"""Chi tiết 1 Cơ hội (CRM Deal) + tên NV/BV. throw PermissionError nếu không read."""
	if not frappe.has_permission(DEAL_DOCTYPE, "read", doc=deal):
		frappe.throw(_("Bạn không có quyền xem cơ hội này."), frappe.PermissionError)
	d = frappe.get_doc(DEAL_DOCTYPE, deal).as_dict()
	result = {k: d.get(k) for k in DEAL_DETAIL_FIELDS}
	result["deal_owner_name"] = (
		frappe.db.get_value("User", d.get("deal_owner"), "full_name") if d.get("deal_owner") else None
	)
	result["am_hospital_name"] = (
		frappe.db.get_value("AntMed Hospital", d.get("am_hospital"), "hospital_name")
		if d.get("am_hospital")
		else None
	)
	return result


@frappe.whitelist(methods=["POST"])
def create_deal(
	organization: str | None = None,
	deal_value: float | None = None,
	status: str | None = None,
	am_hospital: str | None = None,
	am_tender_no: str | None = None,
) -> dict:
	"""Tạo Cơ hội (CRM Deal) mới. status mặc định = giai đoạn đầu; deal_owner = user phiên."""
	if not frappe.has_permission(DEAL_DOCTYPE, "create"):
		frappe.throw(_("Bạn không có quyền tạo cơ hội."), frappe.PermissionError)
	if not status:
		rows = _deal_stage_rows()
		status = rows[0].name if rows else None
	doc = frappe.get_doc(
		{
			"doctype": DEAL_DOCTYPE,
			"organization": organization or None,
			"deal_value": deal_value,
			"status": status,
			"am_hospital": am_hospital or None,
			"am_tender_no": am_tender_no or None,
			"deal_owner": frappe.session.user,
		}
	)
	doc.insert()
	return {"name": doc.name, "status": doc.status}
