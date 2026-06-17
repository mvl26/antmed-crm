# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""M01 Bootstrap — harness test (TDD viết TRƯỚC implement).

Cover acceptance R1 + W0-1 (DEC-A — Role nhãn tiếng Việt, ADR-M14W0-01):
  TDD-BE-1 test_three_roles_exist     — 3 Role AntMed VI tồn tại sau migrate
  TDD-BE-1b test_exactly_three_antmed_roles — đúng tập 3 Role VI (không thừa/thiếu)
  TDD-BE-1c test_no_legacy_en_roles   — KHÔNG còn Role EN cũ (chống sót rename)
  TDD-BE-2 test_health_ping_shape     — ping() trả dict {app,status,version}, version==crm.__version__
  TDD-BE-3 test_health_ping_is_get_only — ping siết methods=['GET'], KHÔNG bare whitelist
  TDD-BE-5 test_module_registered     — 'AntMed' trong modules.txt + crm.antmed import được

Lệnh chạy:
  bench --site miyano run-tests --module crm.tests.test_antmed_bootstrap
"""

import frappe
from frappe.tests.utils import FrappeTestCase

import antmed_crm
from antmed_crm.api.antmed import health

# DEC-A (ADR-M14W0-01): name Role = nhãn tiếng Việt (đã Supersede tên EN R1).
ANTMED_ROLES = [
	"NV kinh doanh",
	"Thủ kho",
	"Quản lý",
]

# Tên Role tiếng Anh R1 — đã rename sang VI; phải KHÔNG còn trong DB (chống sót rename).
ANTMED_ROLES_LEGACY_EN = [
	"AntMed Sales Rep",
	"AntMed Warehouse Keeper",
	"AntMed Manager",
]


class TestAntMedBootstrap(FrappeTestCase):
	# --- TDD-BE-1 -----------------------------------------------------------
	def test_three_roles_exist(self):
		"""Sau migrate, cả 3 Role AntMed VI tồn tại (fixture đã sync)."""
		for role in ANTMED_ROLES:
			self.assertTrue(
				frappe.db.exists("Role", role),
				msg=f"Role fixture chưa load: {role!r} (chạy bench migrate?)",
			)

	def test_exactly_three_antmed_roles(self):
		"""ĐÚNG tập 3 Role AntMed VI — không thừa, không thiếu."""
		rows = frappe.get_all(
			"Role",
			filters={"name": ["in", ANTMED_ROLES]},
			pluck="name",
		)
		self.assertEqual(
			sorted(rows),
			sorted(ANTMED_ROLES),
			msg=f"Tập Role AntMed VI phải đúng 3 cái, thực tế: {sorted(rows)}",
		)

	def test_no_legacy_en_roles(self):
		"""Chống sót rename: KHÔNG còn Role EN cũ (DEC-A đã đổi sang VI)."""
		for role in ANTMED_ROLES_LEGACY_EN:
			self.assertIsNone(
				frappe.db.exists("Role", role),
				msg=f"Role EN cũ vẫn tồn tại sau rename: {role!r} — patch rename chưa chạy?",
			)

	# --- TDD-BE-2 -----------------------------------------------------------
	def test_health_ping_shape(self):
		"""ping() trả dict thuần đúng 3 key {app,status,version}."""
		result = health.ping()
		self.assertIsInstance(result, dict)
		self.assertEqual(set(result.keys()), {"app", "status", "version"})
		self.assertEqual(result["app"], "antmed")
		self.assertEqual(result["status"], "ok")

	def test_health_ping_version_is_dynamic(self):
		"""version đọc động từ crm.__version__ (str), KHÔNG hard-code."""
		result = health.ping()
		self.assertEqual(result["version"], crm.__version__)
		self.assertIsInstance(result["version"], str)

	# --- TDD-BE-3 -----------------------------------------------------------
	def test_health_ping_is_get_only(self):
		"""ping siết verb GET tường minh, KHÔNG là bare whitelist (mọi method)."""
		fn = getattr(health.ping, "__func__", health.ping)
		# Frappe v15: hàm đã whitelist nằm trong frappe.whitelisted:
		self.assertIn(fn, frappe.whitelisted, msg="ping() phải được @frappe.whitelist()")
		allowed = list(frappe.allowed_http_methods_for_whitelisted_func.get(fn, []))
		self.assertIn("GET", allowed, msg=f"ping() phải cho phép GET, methods={allowed}")
		# Bare whitelist mặc định ['GET','POST','PUT','DELETE'] — phải bị siết về chỉ GET:
		self.assertNotIn("POST", allowed, msg=f"ping() KHÔNG được nhận POST (bare whitelist), methods={allowed}")
		self.assertEqual(allowed, ["GET"], msg=f"ping() chỉ được phép GET, methods={allowed}")

	# --- TDD-BE-5 -----------------------------------------------------------
	def test_module_registered(self):
		"""'AntMed' có trong modules.txt và crm.antmed import được."""
		modules = frappe.get_module_list("crm")
		self.assertIn("AntMed", modules, msg="Module 'AntMed' chưa khai trong crm/modules.txt")
		# import package không lỗi:
		import antmed_crm.antmed  # noqa: F401

		self.assertTrue(True)
