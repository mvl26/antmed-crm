# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M04 Slice S1 — endpoint Giao phòng mổ (Delivery, read-only).

Đường gọi: antmed_crm.api.antmed.delivery.<fn> (xem m04_or_delivery.md §5).
@frappe.whitelist(methods=["GET"]), type-annotated, RAW dict. count==rows (BR-13).
Vòng đời (assign/start_transit/handover) + SLA + BR-01/06 để slice M04-S2/S3.
"""

import json

import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime

DELIVERY_DOCTYPE = "AntMed Delivery"
HOSPITAL_DOCTYPE = "AntMed Hospital"
DOCTOR_DOCTYPE = "AntMed Doctor"

# Thứ tự cột kanban điều phối (dispatch_board) + state machine vòng đời (m04 §3).
STATUS_ORDER = ["Nháp", "Đã phân loại", "Đã gán NV", "Đang giao", "Đã bàn giao", "Đã đóng", "Từ chối"]
_NEXT = {
	"Nháp": {"Đã phân loại", "Đã gán NV", "Từ chối"},
	"Đã phân loại": {"Đã gán NV", "Từ chối"},
	"Đã gán NV": {"Đang giao", "Từ chối"},
	"Đang giao": {"Đã bàn giao"},
	"Đã bàn giao": {"Đã đóng"},
}


def _assert_transition(current: str, target: str) -> None:
	if target not in _NEXT.get(current, set()):
		frappe.throw(_("Không thể chuyển trạng thái '{0}' → '{1}'.").format(current, target))


def _check_write(name: str) -> None:
	"""Gate quyền cho endpoint mutating (LL-BE-13 — KHÔNG tin FE ẩn nút)."""
	if not frappe.has_permission(DELIVERY_DOCTYPE, "write", doc=name):
		frappe.throw(_("Bạn không có quyền cập nhật phiếu giao này."), frappe.PermissionError)

DELIVERY_LIST_FIELDS = [
	"name",
	"hospital",
	"hospital.hospital_name as hospital_name",
	"doctor",
	"doctor.full_name as doctor_name",
	"surgery_datetime",
	"status",
	"sla_status",
	"assigned_employee",
	"assigned_employee.full_name as assigned_employee_name",
]
DELIVERY_LIST_ITEM_KEYS = (
	"name",
	"hospital",
	"hospital_name",
	"doctor",
	"doctor_name",
	"surgery_datetime",
	"status",
	"sla_status",
	"assigned_employee",
	"assigned_employee_name",
)
DELIVERY_DETAIL_FIELDS = (
	"name",
	"hospital",
	"doctor",
	"surgery_room",
	"surgery_datetime",
	"sla_minutes",
	"contract",
	"assigned_employee",
	"status",
	"delivered_at",
	"sla_status",
	"notes",
	"docstatus",
)
DELIVERY_ITEM_KEYS = ("item", "item_name", "lot", "uom", "requested_qty", "delivered_qty", "consumed_qty", "returned_qty")


def _coerce_filters(filters: dict | str | None) -> list:
	if not filters:
		return []
	if isinstance(filters, str):
		filters = frappe.parse_json(filters) or []
	if isinstance(filters, dict):
		return [[k, "=", v] for k, v in filters.items()]
	return list(filters)


@frappe.whitelist(methods=["GET"])
def list_deliveries(
	filters: dict | str | None = None,
	status: str | None = None,
	hospital: str | None = None,
	start: int = 0,
	page_length: int = 20,
	search: str | None = None,
) -> dict:
	"""Danh sách phiếu giao phòng mổ. Trả RAW {data, total_count} — count==rows khi page_length=0.

	Mỗi item gồm ĐÚNG 8 field: name, hospital, hospital_name, doctor, surgery_datetime,
	status, sla_status, assigned_employee. hospital_name resolve qua Link (dotted-fetch).
	- search: lọc theo name (mã DO, LIKE %search%).
	"""
	conditions = _coerce_filters(filters)
	if status:
		conditions.append(["status", "=", status])
	if hospital:
		conditions.append(["hospital", "=", hospital])
	if search:
		conditions.append(["name", "like", f"%{search}%"])

	start = max(0, int(start))
	page_length = max(0, int(page_length))

	rows = frappe.get_list(
		DELIVERY_DOCTYPE,
		filters=conditions,
		fields=DELIVERY_LIST_FIELDS,
		limit_start=start,
		limit_page_length=page_length or 0,
		order_by=f"`tab{DELIVERY_DOCTYPE}`.surgery_datetime desc",
	)
	data = [{k: r.get(k) for k in DELIVERY_LIST_ITEM_KEYS} for r in rows]

	total_count = len(frappe.get_list(DELIVERY_DOCTYPE, filters=conditions, pluck="name", limit_page_length=0))
	return {"data": data, "total_count": total_count}


@frappe.whitelist(methods=["GET"])
def get_delivery(name: str) -> dict:
	"""Chi tiết phiếu giao + items[] + hospital_name/doctor_name. throw PermissionError nếu không read."""
	if not frappe.has_permission(DELIVERY_DOCTYPE, "read", doc=name):
		frappe.throw(_("Bạn không có quyền xem phiếu giao này."), frappe.PermissionError)

	doc = frappe.get_doc(DELIVERY_DOCTYPE, name).as_dict()
	result = {k: doc.get(k) for k in DELIVERY_DETAIL_FIELDS}
	# LL-BE-2 + LL-BE-5: enrich *_name, null-guard FK orphan.
	result["hospital_name"] = (
		frappe.db.get_value(HOSPITAL_DOCTYPE, doc.get("hospital"), "hospital_name") if doc.get("hospital") else None
	)
	result["doctor_name"] = (
		frappe.db.get_value(DOCTOR_DOCTYPE, doc.get("doctor"), "full_name") if doc.get("doctor") else None
	)
	result["assigned_employee_name"] = (
		frappe.db.get_value("User", doc.get("assigned_employee"), "full_name") if doc.get("assigned_employee") else None
	)
	result["items"] = [{k: row.get(k) for k in DELIVERY_ITEM_KEYS} for row in (doc.get("items") or [])]
	return result


@frappe.whitelist(methods=["POST"])
def create_request(
	hospital: str,
	surgery_datetime: str,
	items: str | list | None = None,
	doctor: str | None = None,
	surgery_room: str | None = None,
	contract: str | None = None,
	sla_minutes: int = 120,
) -> dict:
	"""NV tạo yêu cầu giao phòng mổ (status 'Nháp'). items = list dict (hoặc JSON-string)."""
	item_rows = json.loads(items) if isinstance(items, str) else (items or [])
	doc = frappe.get_doc(
		{
			"doctype": DELIVERY_DOCTYPE,
			"hospital": hospital,
			"doctor": doctor,
			"surgery_datetime": surgery_datetime,
			"surgery_room": surgery_room,
			"contract": contract,
			"sla_minutes": int(sla_minutes),
			"status": "Nháp",
			"items": item_rows,
		}
	)
	doc.insert()
	return {"name": doc.name, "status": doc.status}


@frappe.whitelist(methods=["POST"])
def assign(name: str, assigned_employee: str) -> dict:
	"""Gán NV phụ trách → 'Đã gán NV' (m04 §3). Gate quyền write."""
	_check_write(name)
	current = frappe.db.get_value(DELIVERY_DOCTYPE, name, "status")
	_assert_transition(current, "Đã gán NV")
	frappe.db.set_value(DELIVERY_DOCTYPE, name, {"assigned_employee": assigned_employee, "status": "Đã gán NV"})
	return {"name": name, "status": "Đã gán NV", "assigned_employee": assigned_employee}


@frappe.whitelist(methods=["POST"])
def start_transit(name: str) -> dict:
	"""NV bắt đầu giao → 'Đang giao'."""
	_check_write(name)
	current = frappe.db.get_value(DELIVERY_DOCTYPE, name, "status")
	_assert_transition(current, "Đang giao")
	frappe.db.set_value(DELIVERY_DOCTYPE, name, "status", "Đang giao")
	return {"name": name, "status": "Đang giao"}


def _line_qty(line) -> float:
	"""SL tiêu hao của dòng giao: consumed → delivered → requested."""
	return float(line.get("consumed_qty") or line.get("delivered_qty") or line.get("requested_qty") or 0)


@frappe.whitelist(methods=["POST"])
def handover(
	name: str,
	gps_lat: str | None = None,
	gps_lng: str | None = None,
	signed_by: str | None = None,
	signature_method: str | None = None,
) -> dict:
	"""Bàn giao tại phòng mổ → 'Đã bàn giao' (submit, docstatus 1) + SLA + chữ ký/GPS + trừ quota.

	- sla_status = 'OnTime' nếu giao trước/đúng giờ phẫu thuật, ngược lại 'Late'.
	- BR-06: nếu phiếu gắn HĐ → assert_quota_available trước khi submit; throw nếu chạm trần.
	- Sau submit: consume_quota (M02) cho từng dòng (idempotent theo do_ref=phiếu giao).
	"""
	_check_write(name)
	doc = frappe.get_doc(DELIVERY_DOCTYPE, name)
	_assert_transition(doc.status, "Đã bàn giao")

	# BR-06: kiểm tra trần quota TRƯỚC khi submit (nếu phiếu gắn HĐ).
	if doc.contract:
		from antmed_crm.antmed import contract_hooks

		for line in doc.items:
			contract_hooks.assert_quota_available(doc.contract, line.item, _line_qty(line))

	now = now_datetime()
	doc.delivered_at = now
	doc.status = "Đã bàn giao"
	doc.sla_status = "OnTime" if now <= get_datetime(doc.surgery_datetime) else "Late"
	if gps_lat is not None and str(gps_lat) != "":
		doc.gps_lat = float(gps_lat)
	if gps_lng is not None and str(gps_lng) != "":
		doc.gps_lng = float(gps_lng)
	if signed_by:
		doc.signed_by = signed_by
	if signature_method:
		doc.signature_method = signature_method
	doc.submit()

	# Trừ quota HĐ sau khi bàn giao (M02-3 consume_quota — idempotent theo do_ref).
	if doc.contract:
		from antmed_crm.antmed import contract_hooks

		for line in doc.items:
			qty = _line_qty(line)
			if qty:
				contract_hooks.consume_quota(doc.contract, line.item, qty, do_ref=name)

	# Wire M04→M03: ghi sổ tồn tiêu hao ca mổ (best-effort — KHÔNG vỡ bàn giao nếu lỗi/thiếu kho).
	_post_delivery_consumption(doc)

	return {"name": name, "status": doc.status, "sla_status": doc.sla_status, "delivered_at": str(doc.delivered_at)}


def _post_delivery_consumption(doc) -> None:
	"""Bàn giao → sinh AntMed Stock Entry 'Giao phòng mổ' trừ kho cá nhân NV theo lô (M04→M03 ledger).

	Để chuỗi truy vết/sổ tồn nhất quán: lô rời kho cá nhân NV khi tiêu hao tại ca mổ. Phiếu link
	`delivery` (FK đóng gap kiến trúc). GUARDED + idempotent + BEST-EFFORT:
	- Chỉ ghi khi NV phụ trách CÓ kho cá nhân (warehouse_type='Cá nhân NV', employee=assigned). Không có
	  → bỏ qua (bàn giao vẫn thành công, ledger không có dòng — tránh vỡ flow M04 cũ chưa có kho NV).
	- Idempotent: phiếu giao đã có Stock Entry 'Giao phòng mổ' (docstatus 1) → bỏ qua (không nhân đôi).
	- Best-effort: bất kỳ lỗi nào (thiếu tồn / lô recall-hết hạn bị gate / validate) → log, KHÔNG raise
	  (bàn giao là sự kiện pháp lý chính; ghi sổ là phụ). Lỗi gate recall/HSD vẫn được log để hậu kiểm.
	"""
	try:
		if not doc.get("assigned_employee"):
			return
		nv_wh = frappe.db.get_value(
			"AntMed Warehouse",
			{"warehouse_type": "Cá nhân NV", "employee": doc.assigned_employee, "disabled": 0},
			"name",
		)
		if not nv_wh:
			return
		if frappe.db.exists("AntMed Stock Entry", {"delivery": doc.name, "docstatus": 1}):
			return
		items = [
			{"item": l.item, "lot": l.lot, "qty": _line_qty(l)}
			for l in doc.items
			if l.get("lot") and _line_qty(l) > 0
		]
		if not items:
			return
		se = frappe.get_doc(
			{
				"doctype": "AntMed Stock Entry",
				"entry_type": "Giao phòng mổ",
				"from_warehouse": nv_wh,
				"nv_employee": doc.assigned_employee,
				"hospital": doc.hospital,
				"delivery": doc.name,
				"items": items,
			}
		)
		se.insert(ignore_permissions=True)
		se.submit()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "M04 handover→M03 stock consumption failed")


# Cột kanban B1 (mockup B1): gom 7 status nội bộ → ĐÚNG 4 lane. 'Từ chối' KHÔNG lên board.
DISPATCH_LANES = (
	("new", "Mới tiếp nhận", ("Nháp", "Đã phân loại")),
	("assigned", "Đã gán NV", ("Đã gán NV",)),
	("in_transit", "Đang giao", ("Đang giao",)),
	("handed", "Đã bàn giao", ("Đã bàn giao", "Đã đóng")),
)


def _dispatch_urgency(row: dict, now) -> str:
	"""urgent = chưa bàn giao & sắp/quá giờ mổ (≤60'); warn = SLA Late; ok = còn lại."""
	if row.get("status") in ("Đã bàn giao", "Đã đóng"):
		return "ok"
	if row.get("sla_status") == "Late":
		return "warn"
	sdt = row.get("surgery_datetime")
	if sdt and (get_datetime(sdt) - now).total_seconds() / 60.0 <= 60:
		return "urgent"
	return "ok"


@frappe.whitelist(methods=["GET"])
def dispatch_board(hospital: str | None = None) -> dict:
	"""Bảng điều phối ca giao phòng mổ (mockup B1) — kanban AntMed Delivery theo trạng thái.

	Trả `columns` (1 cột/status — count==rows dưới DocPerm, giữ tương thích) + `lanes`
	(gom ĐÚNG 4 cột B1; 'Từ chối' loại) + `total` + `totals{total,urgent}`. card enrich:
	+ doctor_name, sku_count, assigned_employee_name, urgency('urgent'|'warn'|'ok').
	Đọc DƯỚI permission (BR-13 fail-closed): NV chỉ thấy ca trong phạm vi.
	"""
	conditions = []
	if hospital:
		conditions.append(["hospital", "=", hospital])
	rows = frappe.get_list(
		DELIVERY_DOCTYPE,
		filters=conditions,
		fields=DELIVERY_LIST_FIELDS,
		limit_page_length=0,
		order_by=f"`tab{DELIVERY_DOCTYPE}`.surgery_datetime asc",
	)
	names = [r["name"] for r in rows]

	# sku_count = số dòng items mỗi phiếu (1 query gộp — tránh N+1).
	sku_by_parent: dict[str, int] = {}
	if names:
		for it in frappe.get_all(
			"AntMed Delivery Item", filters={"parent": ["in", names]}, fields=["parent"], limit_page_length=0
		):
			sku_by_parent[it["parent"]] = sku_by_parent.get(it["parent"], 0) + 1

	_cache: dict = {}

	def _resolve(doctype: str, key, field: str):
		if not key:
			return None
		ck = (doctype, key)
		if ck not in _cache:
			_cache[ck] = frappe.db.get_value(doctype, key, field)
		return _cache[ck]

	now = now_datetime()

	def _card(r: dict) -> dict:
		card = {k: r.get(k) for k in DELIVERY_LIST_ITEM_KEYS}
		card.update(
			{
				"delivery": r["name"],
				"doctor_name": _resolve(DOCTOR_DOCTYPE, r.get("doctor"), "full_name"),
				"sku_count": sku_by_parent.get(r["name"], 0),
				"assigned_employee_name": _resolve("User", r.get("assigned_employee"), "full_name"),
				"urgency": _dispatch_urgency(r, now),
			}
		)
		return card

	board: dict = {}
	for r in rows:
		board.setdefault(r.get("status"), []).append(_card(r))

	columns = [{"status": s, "items": board.get(s, [])} for s in STATUS_ORDER]
	lanes = []
	for key, label, statuses in DISPATCH_LANES:
		cards = [c for s in statuses for c in board.get(s, [])]
		lanes.append({"key": key, "label": label, "count": len(cards), "cards": cards})
	urgent = sum(1 for lane in lanes for c in lane["cards"] if c["urgency"] == "urgent")

	return {
		"columns": columns,
		"lanes": lanes,
		"total": len(rows),
		"totals": {"total": sum(lane["count"] for lane in lanes), "urgent": urgent},
	}


@frappe.whitelist(methods=["GET"])
def list_assignable_employees() -> dict:
	"""NV có thể gán phụ trách phiếu giao (role 'NV kinh doanh' / 'Quản lý', user active).

	Trả {data: [{value: <user>, label: <full_name>}]} cho dropdown 'Gán NV' (S2).
	value = User.name gửi BE; label = full_name hiển thị (KHÔNG leak email ra UI).
	"""
	user_ids = frappe.get_all(
		"Has Role",
		filters={"role": ["in", ["NV kinh doanh", "Quản lý"]], "parenttype": "User"},
		pluck="parent",
		distinct=True,
	)
	if not user_ids:
		return {"data": []}
	users = frappe.get_all(
		"User",
		filters=[
			["name", "in", user_ids],
			["enabled", "=", 1],
			["name", "not in", ["Administrator", "Guest"]],
		],
		fields=["name as value", "full_name as label"],
		order_by="full_name asc",
	)
	return {"data": users}
