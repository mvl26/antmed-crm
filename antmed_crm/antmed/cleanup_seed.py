# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""Dọn data test + seed data thật (AntMed).

A) delete_test_users() — reassign mọi link nghiệp vụ về REAL_OWNER rồi force-delete user test
   (domain example.com / nd1.hospital.vn / prefix _t_/_test/_qa/eval_/test@).
B) topup_real_data() — xoá _T-* leftover + tạo bù record ĐẦY ĐỦ FIELD cho doctype <3.

Chạy:  bench --site miyano execute antmed_crm.antmed.cleanup_seed.delete_test_users
       bench --site miyano execute antmed_crm.antmed.cleanup_seed.topup_real_data
"""

import hashlib

import frappe
from frappe.utils import add_days, add_to_date, now_datetime, nowdate

KEEP_USERS = {"Administrator", "Guest"}
KEEP_DOMAINS = ("gmail.com", "miyano.com.vn")
TEST_DOMAINS = ("example.com", "nd1.hospital.vn")
REAL_OWNER = "chuvanhieu357@gmail.com"


def _is_test_user(email: str) -> bool:
	if email in KEEP_USERS:
		return False
	dom = email.split("@")[-1] if "@" in email else ""
	if dom in KEEP_DOMAINS:
		return False
	return (
		dom in TEST_DOMAINS
		or any(p in email for p in ("_t_", "_test", "_qa", "eval_"))
		or email.startswith("test@")
	)


def delete_test_users():
	users = frappe.get_all("User", filters={"name": ["not in", list(KEEP_USERS)]}, pluck="name")
	targets = [u for u in users if _is_test_user(u)]
	if REAL_OWNER not in frappe.get_all("User", pluck="name"):
		print("ABORT — REAL_OWNER không tồn tại:", REAL_OWNER)
		return
	tset = set(targets)

	# 1) Reassign mọi link nghiệp vụ trỏ user bị xoá → REAL_OWNER (tránh dangling).
	reassign = [
		("CRM Deal", "deal_owner"),
		("CRM Lead", "lead_owner"),
		("AntMed Delivery", "assigned_employee"),
		("AntMed Instrument Loan", "employee"),
		("AntMed Instrument Set", "current_holder"),
		("AntMed Stock Entry", "requested_by"),
	]
	for dt, field in reassign:
		if not frappe.db.exists("DocType", dt):
			continue
		if not frappe.get_meta(dt).get_field(field):
			continue
		rows = frappe.get_all(dt, filters={field: ["in", targets]}, pluck="name")
		for r in rows:
			frappe.db.set_value(dt, r, field, REAL_OWNER, update_modified=False)
		if rows:
			print(f"reassigned {len(rows)} {dt}.{field} -> {REAL_OWNER}")

	# 2) Gỡ ToDo/assignment trỏ user bị xoá (chống chặn khi delete).
	if frappe.db.exists("DocType", "ToDo"):
		todos = frappe.get_all("ToDo", filters={"allocated_to": ["in", targets]}, pluck="name")
		for t in todos:
			frappe.delete_doc("ToDo", t, force=True, ignore_permissions=True)
		if todos:
			print(f"removed {len(todos)} ToDo")

	frappe.db.commit()

	# 3) Force-delete user (bỏ qua link còn lại — owner/modified_by sẽ dangling, chấp nhận).
	deleted, skipped = [], []
	for u in targets:
		try:
			frappe.delete_doc("User", u, force=True, ignore_permissions=True, delete_permanently=True)
			deleted.append(u)
		except Exception as e:
			skipped.append((u, str(e)[:90]))
	frappe.db.commit()
	print(f"DELETED {len(deleted)} / {len(targets)} test users")
	for u, e in skipped:
		print("  SKIP", u, e)


# ── B) Top-up data thật (đầy đủ field) cho doctype < 3 ──────────────────────

def _sha(s):
	return hashlib.sha256(str(s).encode()).hexdigest()


def _del_testish(doctype):
	"""Xoá record _T-*/_test trong doctype (skip nếu FK chặn)."""
	names = [n for n in frappe.get_all(doctype, pluck="name") if any(t in n.lower() for t in ("_t-", "_test", "smoke"))]
	done = 0
	for n in names:
		try:
			frappe.delete_doc(doctype, n, ignore_permissions=True)
			done += 1
		except Exception as e:
			print(f"  skip {doctype} {n}: {str(e)[:70]}")
	return done


def topup_real_data():
	# 1) Dọn leftover _T-* (thứ tự phụ thuộc: con trước cha).
	for dt in ["AntMed Stock Ledger", "AntMed Lot", "AntMed Certificate", "AntMed Item", "AntMed Warehouse", "AntMed Supplier"]:
		d = _del_testish(dt)
		if d:
			print(f"cleaned {d} testish in {dt}")

	hospitals = frappe.get_all("AntMed Hospital", fields=["name", "hospital_name"], limit=3)
	items = frappe.get_all("AntMed Item", fields=["name", "item_name", "uom"], limit=5)
	lots = frappe.get_all("AntMed Lot", fields=["name", "item"], limit=10)
	if not (hospitals and items):
		print("ABORT topup — thiếu Hospital/Item nền.")
		return

	def lot_of(item_code):
		return next((l.name for l in lots if l.item == item_code), None)

	# 2) AntMed Certificate (0 → 3) — đủ field.
	CERTS = [
		("CO", 0), ("CQ", 1), ("Phiếu kiểm nghiệm", 2),
	]
	c = frappe.db.count("AntMed Certificate")
	for cert_type, idx in CERTS:
		if c >= 3:
			break
		it = items[idx % len(items)]
		cert_no = f"{cert_type[:2].upper()}-2026-{1000 + idx}"
		if frappe.db.exists("AntMed Certificate", {"cert_no": cert_no}):
			continue
		frappe.get_doc({
			"doctype": "AntMed Certificate",
			"cert_no": cert_no,
			"cert_type": cert_type,
			"item": it.name,
			"lot": lot_of(it.name),
			"issued_date": add_days(nowdate(), -120),
			"expires_at": add_days(nowdate(), 600),
			"file_url": f"/files/cert_{cert_no}.pdf",
			"hash_sha256": _sha(cert_no),
		}).insert(ignore_permissions=True)
		c += 1
	print("Certificate now", frappe.db.count("AntMed Certificate"))

	# 3) AntMed Contract (→ 3) — đủ field + items child.
	existing_contracts = frappe.db.count("AntMed Contract")
	need = max(0, 3 - existing_contracts)
	for i in range(need):
		hosp = hospitals[i % len(hospitals)]
		cno = f"HD-2026-{200 + i}"
		if frappe.db.exists("AntMed Contract", {"contract_no": cno}):
			continue
		child = []
		for j in range(2):
			it = items[(i + j) % len(items)]
			quota = 1000 * (j + 1)
			used = 200 * (j + 1)
			child.append({
				"item": it.name,
				"item_name": it.item_name,
				"uom": it.uom or "Cái",
				"unit_price": 1_500_000 + j * 500_000,
				"quota_qty": quota,
				"used_qty": used,
				"remaining_pct": round((quota - used) / quota * 100, 1),
				"lock_at_100": 1,
			})
		frappe.get_doc({
			"doctype": "AntMed Contract",
			"contract_no": cno,
			"hospital": hosp.name,
			"status": "Hiệu lực",
			"signed_date": add_days(nowdate(), -90),
			"valid_from": add_days(nowdate(), -90),
			"valid_to": add_days(nowdate(), 275),
			"total_value": 3_000_000_000 + i * 500_000_000,
			"items": child,
		}).insert(ignore_permissions=True)
	print("Contract now", frappe.db.count("AntMed Contract"))

	# 4) AntMed Sterilization (→ 3) — link loan thật, đủ field.
	loans = frappe.get_all("AntMed Instrument Loan", fields=["name", "instrument_set"], limit=20)
	METHODS = ["Hấp", "EO", "Plasma"]
	si = 0
	for ln in loans:
		if frappe.db.count("AntMed Sterilization") >= 3:
			break
		if frappe.db.exists("AntMed Sterilization", {"loan": ln.name}):
			continue
		frappe.get_doc({
			"doctype": "AntMed Sterilization",
			"loan": ln.name,
			"instrument_set": ln.instrument_set,
			"result": "Pass",
			"method": METHODS[si % 3],
			"operator": ["Nguyễn Thị Tiệt", "Trần Văn Khuẩn", "Lê Thanh Sạch"][si % 3],
			"started_at": add_to_date(now_datetime(), hours=-6),
			"ended_at": add_to_date(now_datetime(), hours=-5),
		}).insert(ignore_permissions=True)
		si += 1
	print("Sterilization now", frappe.db.count("AntMed Sterilization"))

	# 5) AntMed Quota Usage Log (0 → 3) — đủ field.
	contracts = frappe.get_all("AntMed Contract", fields=["name"], limit=3)
	q = frappe.db.count("AntMed Quota Usage Log")
	for i in range(max(0, 3 - q)):
		ct = contracts[i % len(contracts)]
		it = items[i % len(items)]
		qty = 50 * (i + 1)
		frappe.get_doc({
			"doctype": "AntMed Quota Usage Log",
			"contract": ct.name,
			"item": it.name,
			"do_ref": f"DO-2026-{300 + i}",
			"qty": qty,
			"snapshot_pct": round(20 + i * 15, 1),
			"ts": add_to_date(now_datetime(), days=-(i + 1)),
		}).insert(ignore_permissions=True)
	print("QuotaUsageLog now", frappe.db.count("AntMed Quota Usage Log"))

	frappe.db.commit()
	print("TOPUP DONE")


def purge_ltv():
	"""Xoá dứt điểm chuỗi test _T-LTV-* (stock entry → ledger → master) bằng force."""
	LTV = ["_T-LTV-LOT", "_T-LTV-ITEM", "_T-LTV-WH", "_T-LTV-NCC"]

	# 1) Stock Entry test (qua child item/lot) — cancel nếu submitted rồi xoá.
	se_names = set()
	for f in ("item", "lot"):
		for ch in frappe.get_all("AntMed Stock Entry Item", filters={f: ["in", LTV]}, fields=["parent"]):
			se_names.add(ch.parent)
	for se in se_names:
		try:
			doc = frappe.get_doc("AntMed Stock Entry", se)
			if doc.docstatus == 1:
				doc.cancel()
			frappe.delete_doc("AntMed Stock Entry", se, force=True, ignore_permissions=True)
			print("deleted Stock Entry", se)
		except Exception as e:
			print("FAIL SE", se, str(e)[:80])

	# 2) Stock Ledger trỏ test.
	for f in ("item", "lot", "warehouse"):
		for sl in frappe.get_all("AntMed Stock Ledger", filters={f: ["in", LTV]}, pluck="name"):
			try:
				frappe.delete_doc("AntMed Stock Ledger", sl, force=True, ignore_permissions=True)
			except Exception as e:
				print("FAIL SL", sl, str(e)[:60])

	# 3) Master theo thứ tự phụ thuộc (Lot trước Item/Supplier).
	for dt, name in [
		("AntMed Lot", "_T-LTV-LOT"),
		("AntMed Item", "_T-LTV-ITEM"),
		("AntMed Warehouse", "_T-LTV-WH"),
		("AntMed Supplier", "_T-LTV-NCC"),
	]:
		if frappe.db.exists(dt, name):
			try:
				frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
				print("deleted", dt, name)
			except Exception as e:
				print("FAIL", dt, name, str(e)[:80])
	frappe.db.commit()
	print("PURGE_LTV DONE")
