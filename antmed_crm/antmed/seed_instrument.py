# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""Seed demo dữ liệu Bộ dụng cụ (M05 — màn I1 vòng đời + C3 checklist).

Tạo bộ dụng cụ theo nhóm phẫu thuật (mockup I1) + lượt mượn đi qua các trạng thái THẬT
bằng chính endpoint vòng đời (book/handover/receive_return/sterilize) → dữ liệu nhất quán.
Idempotent: bỏ qua set_code đã tồn tại.

Chạy:  bench --site miyano execute antmed_crm.antmed.seed_instrument.run
"""

import frappe
from frappe.utils import add_to_date, now_datetime

from antmed_crm.api.antmed import instrument_loan as il

SET_DOCTYPE = "AntMed Instrument Set"

# Danh mục món theo loại bộ (item_count = số dòng này).
COMPONENTS = {
	"Sọ não": [
		"Khoan điện cầm tay",
		"Lưỡi cưa #2",
		"Lưỡi cưa #3",
		"Bộ kìm gắp",
		"Banh xương #5",
		"Ống hút phẫu thuật",
		"Đầu khoan #2.5mm",
		"Kẹp cầm máu",
		"Dao tách màng",
		"Kéo vi phẫu",
	],
	"CTCH": [
		"Khoan xương",
		"Vít nén 4.5mm",
		"Nẹp khóa chữ T",
		"Banh Hohmann",
		"Búa chỉnh hình",
		"Kìm bẻ nẹp",
		"Mũi taro",
		"Thước đo độ",
	],
	"Tim mạch": [
		"Kẹp mạch máu",
		"Banh lồng ngực",
		"Kéo Metzenbaum",
		"Kẹp Satinsky",
		"Ống thông",
		"Kẹp giữ van",
		"Que dò mạch",
	],
	"Nội soi": [
		"Ống soi 30°",
		"Trocar 10mm",
		"Trocar 5mm",
		"Kẹp grasper",
		"Kéo nội soi",
		"Đầu đốt điện",
		"Ống hút-tưới",
	],
	"Tiêu hóa": [
		"Banh thành bụng",
		"Kẹp ruột",
		"Kéo phẫu tích",
		"Stapler tròn",
		"Kẹp khăn mổ",
		"Ống dẫn lưu",
	],
	"Khoan": ["Tay khoan", "Mũi khoan 2.0mm", "Mũi khoan 3.2mm", "Cờ lê chỉnh", "Đầu kẹp mũi"],
}
CRITICAL = {
	"Khoan điện cầm tay",
	"Bộ kìm gắp",
	"Banh xương #5",
	"Khoan xương",
	"Vít nén 4.5mm",
	"Kẹp mạch máu",
	"Ống soi 30°",
	"Stapler tròn",
	"Tay khoan",
}

# (set_code, surgery_type, target_state, overdue?)
PLAN = [
	("BS-007", "Sọ não", "Đang sử dụng tại BV", False),
	("BS-008", "Sọ não", "Sẵn sàng", False),
	("BS-009", "Sọ não", "Đã đặt", False),
	("BS-014", "CTCH", "Đã trả về NV KD", True),
	("BS-015", "CTCH", "Sẵn sàng", False),
	("BS-016", "CTCH", "Đang sử dụng tại BV", False),
	("BS-017", "CTCH", "Đã đặt", False),
	("BS-018", "CTCH", "Hỏng", False),
	("BS-021", "Tim mạch", "Đang xử lý/tiệt khuẩn", False),
	("BS-022", "Tim mạch", "Đã đặt", False),
	("BS-031", "Nội soi", "Sẵn sàng", False),
	("BS-032", "Nội soi", "Đang sử dụng tại BV", True),
	("BS-033", "Nội soi", "Sẵn sàng", False),
	("BS-034", "Nội soi", "Mất", False),
	("BS-019", "Tiêu hóa", "Sẵn sàng", False),
	("BS-040", "Khoan", "Đã đặt", False),
]


def _pick(values, idx, default=None):
	return values[idx % len(values)] if values else default


def _ensure_set(set_code, surgery_type):
	if frappe.db.exists(SET_DOCTYPE, set_code):
		return set_code
	comps = COMPONENTS.get(surgery_type, [])
	doc = frappe.get_doc(
		{
			"doctype": SET_DOCTYPE,
			"set_code": set_code,
			"surgery_type": surgery_type,
			"current_status": "Sẵn sàng",
			"max_loans": 200,
			"asset_value": 80_000_000,
			"components": [
				{"component_name": c, "qty": 1, "criticality": "Critical" if c in CRITICAL else "Normal"}
				for c in comps
			],
		}
	)
	doc.insert(ignore_permissions=True)
	return set_code


def _walk(set_code, hospital, doctor, employee, target, overdue):
	if target == "Sẵn sàng":
		return None
	if target in ("Mất", "Hỏng"):
		frappe.db.set_value(SET_DOCTYPE, set_code, "current_status", target, update_modified=False)
		return None

	if overdue:
		booked, due = add_to_date(now_datetime(), days=-3), add_to_date(now_datetime(), days=-1)
	else:
		booked, due = add_to_date(now_datetime(), hours=-2), add_to_date(now_datetime(), hours=6)

	loan = il.book(
		instrument_set=set_code,
		hospital=hospital,
		booked_at=str(booked),
		due_return_at=str(due),
		doctor=doctor,
		employee=employee,
		surgery_case="Ca mổ demo " + set_code,
	)["name"]
	if target == "Đã đặt":
		return loan
	il.handover(loan)
	if target == "Đang sử dụng tại BV":
		return loan
	il.receive_return(loan)
	if target == "Đã trả về NV KD":
		return loan
	il.sterilize(loan, method="Hấp", result="Pass", operator=employee)
	# target == "Đang xử lý/tiệt khuẩn" → dừng (chưa mark_ready)
	return loan


def run():
	hospitals = frappe.get_all("AntMed Hospital", pluck="name", limit=20)
	doctors = frappe.get_all("AntMed Doctor", pluck="name", limit=20)
	employee = (
		frappe.db.get_value("Has Role", {"role": "NV kinh doanh", "parenttype": "User"}, "parent")
		or "Administrator"
	)
	if not hospitals:
		print("SEED ABORT — chưa có AntMed Hospital nào để gán lượt mượn.")
		return

	created, skipped = 0, 0
	for i, (set_code, stype, target, overdue) in enumerate(PLAN):
		existed = frappe.db.exists(SET_DOCTYPE, set_code)
		_ensure_set(set_code, stype)
		if existed:
			skipped += 1
			continue
		_walk(set_code, _pick(hospitals, i), _pick(doctors, i), employee, target, overdue)
		created += 1

	frappe.db.commit()
	print(
		f"SEED DONE — created={created} skipped(existing)={skipped} total_plan={len(PLAN)} employee={employee}"
	)
