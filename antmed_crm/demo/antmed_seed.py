# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""Seed dữ liệu mẫu AntMed (idempotent) — để các trang /antmed có data hiển thị.

Chạy:  bench --site miyano execute antmed_crm.demo.antmed_seed.seed_antmed_sample
Xoá :  bench --site miyano execute antmed_crm.demo.antmed_seed.clear_antmed_sample

Idempotent: bỏ qua bản ghi đã tồn tại (theo khoá tự nhiên). Tên thật (BV/VTYT VN) để demo
giống thật; mọi bản ghi gắn cờ qua khoá ổn định nên có thể xoá lại sạch.
"""

import frappe
from frappe.utils import add_days, add_months, add_to_date, now_datetime, nowdate

# (hospital_code, hospital_name, rank, contract_status)
_HOSPITALS = [
	("BV-CR", "Bệnh viện Chợ Rẫy", "Đặc biệt", "Đã ký"),
	("BV-BM", "Bệnh viện Bạch Mai", "Đặc biệt", "Đã ký"),
	("BV-TWH", "Bệnh viện TW Huế", "I", "Đã ký"),
	("BV-DHYD", "Bệnh viện ĐH Y Dược TP.HCM", "I", "Tiềm năng"),
]
# (doctor_code, full_name, hospital_code, specialty, phone)
_DOCTORS = [
	("BS-001", "PGS.TS Nguyễn Văn An", "BV-CR", "Tim mạch can thiệp", "0901000001"),
	("BS-002", "TS.BS Trần Thị Bình", "BV-CR", "Ngoại tổng quát", "0901000002"),
	("BS-003", "BS.CKII Lê Minh Châu", "BV-BM", "Tim mạch", "0901000003"),
	("BS-004", "PGS.TS Phạm Quốc Dũng", "BV-BM", "Phẫu thuật mạch máu", "0901000004"),
	("BS-005", "TS.BS Hoàng Thị Em", "BV-TWH", "Sản phụ khoa", "0901000005"),
	("BS-006", "BS.CKI Võ Thành Phát", "BV-DHYD", "Chấn thương chỉnh hình", "0901000006"),
]
# (supplier_code, supplier_name, tax_code)
_SUPPLIERS = [
	("NCC-ABBOTT", "Abbott Vietnam", "0301234567"),
	("NCC-MEDTRONIC", "Medtronic Vietnam", "0307654321"),
	("NCC-BBRAUN", "B.Braun Vietnam", "0309988776"),
]
# (item_code, item_name, classification, requires_cocq, shelf_life_months, uom, price)
_ITEMS = [
	("VTYT-STENT-DES", "Stent mạch vành phủ thuốc", "Loại D", 1, 36, "Cái", 28000000),
	("VTYT-BALLOON", "Bóng nong mạch vành", "Loại C", 1, 36, "Cái", 9500000),
	("VTYT-VALVE", "Van tim cơ học", "Loại D", 1, 60, "Cái", 65000000),
	("VTYT-GAUZE", "Gạc phẫu thuật vô khuẩn", "Loại A", 0, 60, "Gói", 35000),
	("VTYT-SUTURE", "Chỉ khâu phẫu thuật tự tiêu", "Loại B", 1, 48, "Sợi", 120000),
	("VTYT-CATHETER", "Ống thông tiểu silicone", "Loại B", 1, 36, "Cái", 85000),
]
# (warehouse_name, type, employee_user, hospital_code)
_WAREHOUSES = [
	("Kho Tổng HCM", "Tổng", None, None),
	("Kho cá nhân - NV Nguyễn Văn A", "Cá nhân NV", "Administrator", None),
	("Kho ký gửi BV Chợ Rẫy", "Ký gửi BV", None, "BV-CR"),
]


def _ensure(doctype, key_field, key_value, values):
	existing = frappe.db.get_value(doctype, {key_field: key_value}, "name")
	if existing:
		return existing
	doc = frappe.get_doc({"doctype": doctype, key_field: key_value, **values})
	doc.insert(ignore_permissions=True)
	return doc.name


def seed_antmed_sample():
	"""Tạo dữ liệu mẫu (idempotent). Trả dict đếm số bản ghi sau seed."""
	# 1) Bệnh viện
	for code, name, rank, cstatus in _HOSPITALS:
		_ensure("AntMed Hospital", "hospital_code", code, {"hospital_name": name, "rank": rank, "contract_status": cstatus})
	# 2) Bác sỹ
	for code, full_name, hosp, spec, phone in _DOCTORS:
		if not frappe.db.exists("AntMed Doctor", {"doctor_code": code}):
			frappe.get_doc(
				{"doctype": "AntMed Doctor", "doctor_code": code, "full_name": full_name, "hospital": hosp, "specialty": spec, "phone": phone}
			).insert(ignore_permissions=True)
	# 3) Nhà cung cấp
	for code, name, tax in _SUPPLIERS:
		_ensure("AntMed Supplier", "supplier_code", code, {"supplier_name": name, "tax_code": tax})
	# 4) Vật tư
	for code, name, cls, cocq, shelf, uom, price in _ITEMS:
		_ensure(
			"AntMed Item", "item_code", code,
			{"item_name": name, "classification": cls, "requires_cocq": cocq, "shelf_life_months": shelf, "uom": uom, "default_unit_price": price},
		)
	# 5) Lô (mỗi vật tư 1-2 lô, HSD trải đều, gắn NCC)
	suppliers = [s[0] for s in _SUPPLIERS]
	for idx, (code, *_rest) in enumerate(_ITEMS):
		for n in (1, 2):
			lot_no = f"LOT-{code[5:]}-{n:02d}"
			if not frappe.db.exists("AntMed Lot", lot_no):
				frappe.get_doc(
					{
						"doctype": "AntMed Lot",
						"lot_no": lot_no,
						"item": code,
						"supplier": suppliers[idx % len(suppliers)],
						"mfg_date": add_months(nowdate(), -6),
						"expiry_date": add_days(nowdate(), 60 + n * 120 + idx * 20),  # vài lô cận date
					}
				).insert(ignore_permissions=True)
	# 6) Kho 3 cấp
	wh_names = {}
	for name, wtype, emp, hosp in _WAREHOUSES:
		values = {"warehouse_type": wtype}
		if emp:
			values["employee"] = emp
		if hosp:
			values["hospital"] = hosp
		wh_names[wtype] = _ensure("AntMed Warehouse", "warehouse_name", name, values)
	# 7) Hợp đồng + quota: KHÔNG seed ở đây — module M02 (Contract/Revenue) do factory
	#    sở hữu + có test assert tổng doanh thu chính xác; seed HĐ với used_qty sẽ phá
	#    test revenue_mix. Để factory tự seed HĐ/doanh thu trong domain của nó.
	# 8) Nhập kho mẫu → sổ tồn có số (Kho Tổng nhập 3 vật tư)
	tong = wh_names.get("Tổng")
	for code in ("VTYT-STENT-DES", "VTYT-BALLOON", "VTYT-GAUZE"):
		lot = f"LOT-{code[5:]}-01"
		already = frappe.db.exists("AntMed Stock Entry", {"reason": f"SEED-{code}"})
		if tong and not already and frappe.db.exists("AntMed Lot", lot):
			se = frappe.get_doc(
				{
					"doctype": "AntMed Stock Entry",
					"entry_type": "Nhập NCC",
					"to_warehouse": tong,
					"reason": f"SEED-{code}",
					"items": [{"item": code, "lot": lot, "qty": 150, "unit_price": frappe.db.get_value("AntMed Item", code, "default_unit_price")}],
				}
			)
			se.insert(ignore_permissions=True)
			se.submit()
	frappe.db.commit()
	return _counts()


def _counts():
	dts = ["AntMed Hospital", "AntMed Doctor", "AntMed Supplier", "AntMed Item", "AntMed Lot", "AntMed Warehouse", "AntMed Contract", "AntMed Stock Entry"]
	return {dt: frappe.db.count(dt) for dt in dts}


def seed_portal_demo():
	"""Seed kịch bản Portal BV (mockup G1/G2): BV có HĐ trúng thầu + yêu cầu vật tư + phiếu giao.

	Idempotent. quota used_qty=0 → KHÔNG nhiễu revenue aggregate. Chạy:
	  bench --site miyano execute antmed_crm.demo.antmed_seed.seed_portal_demo
	"""
	from antmed_crm.api.antmed import customer

	hosp = _ensure("AntMed Hospital", "hospital_code", "BV-CR", {"hospital_name": "Bệnh viện Chợ Rẫy"})
	doctor = _ensure("AntMed Doctor", "doctor_code", "BS-PORTAL", {"full_name": "BS. Trần Mạnh Hùng", "hospital": hosp, "specialty": "Ngoại tổng quát"})
	cat = [
		("VTYT-VICRYL", "Chỉ Vicryl 2-0", "Loại B", 200000),
		("VTYT-DAOMO11", "Dao mổ #11", "Loại A", 50000),
		("VTYT-GACCM", "Gạc cầm máu", "Loại A", 80000),
	]
	for code, name, cls, _price in cat:
		_ensure("AntMed Item", "item_code", code, {"item_name": name, "classification": cls})

	# HĐ trúng thầu Hiệu lực (used_qty=0 → tender_catalog hiển thị "Còn quota", không nhiễu revenue).
	if not frappe.db.exists("AntMed Contract", {"contract_no": "HD-PORTAL-2026"}):
		c = frappe.get_doc(
			{
				"doctype": "AntMed Contract",
				"contract_no": "HD-PORTAL-2026",
				"hospital": hosp,
				"signed_date": nowdate(),
				"status": "Hiệu lực",
				"valid_to": add_months(nowdate(), 12),
				"items": [
					{"item": code, "item_name": name, "uom": "Cái", "unit_price": price, "quota_qty": 1000, "used_qty": 0, "remaining_pct": 100, "lock_at_100": 1}
					for code, name, _cls, price in cat
				],
			}
		)
		c.insert(ignore_permissions=True)
		c.submit()

	# Yêu cầu vật tư + 1 phiếu giao (cho G2 history). Idempotent theo cờ surgery_room.
	mr = frappe.db.get_value("AntMed Material Request", {"hospital": hosp, "surgery_room": "PM 4 · Demo"}, "name")
	if not mr:
		mr = customer.create_material_request(
			hospital=hosp,
			items=[{"item": "VTYT-VICRYL", "requested_qty": 5}, {"item": "VTYT-DAOMO11", "requested_qty": 3}],
			doctor=doctor,
			surgery_datetime=str(add_to_date(now_datetime(), hours=4)),
			surgery_room="PM 4 · Demo",
			urgency="Bình thường",
		)["name"]
	if frappe.db.get_value("AntMed Material Request", mr, "status") == "Mới":
		customer.receive_material_request(mr)
	if not frappe.db.get_value("AntMed Material Request", mr, "delivery_ref"):
		customer.convert_to_delivery(mr)
	# Yêu cầu thứ 2 (còn 'Mới' — cho NV-side inbox demo).
	if not frappe.db.exists("AntMed Material Request", {"hospital": hosp, "surgery_room": "PM 2 · Demo"}):
		customer.create_material_request(
			hospital=hosp,
			items=[{"item": "VTYT-GACCM", "requested_qty": 10}],
			doctor=doctor,
			surgery_room="PM 2 · Demo",
			urgency="Khẩn",
		)
	return {
		"hospital": hosp,
		"material_requests": frappe.db.count("AntMed Material Request", {"hospital": hosp}),
		"deliveries": frappe.db.count("AntMed Delivery", {"hospital": hosp}),
		"contract_items": len(frappe.get_all("AntMed Quota Item", filters={"parent": "HD-PORTAL-2026"})),
	}
