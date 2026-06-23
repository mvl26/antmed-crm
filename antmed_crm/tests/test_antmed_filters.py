# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""CONSOLIDATE/HARDEN R2 — characterization test cho util chung coerce_filters.

Gom 8 bản copy-paste `_coerce_filters` (customer/pipeline/inventory/delivery/doctor_care/
instrument_loan = bản chuẩn; contract = map workflow_state→status ADR-M02-04; tasks =
safe parse swallow bad-JSON→[]) về 1 nguồn `antmed_crm.api.antmed._filters.coerce_filters`.

Test viết TRƯỚC refactor (TDD rule 06). Khoá hành vi OBSERVABLE để refactor KHÔNG drift:
  - standard: dict→[[k,"=",v]]; JSON-string→parse; None/empty→[]; list passthrough(list());
              bad-JSON RAISES (frappe.parse_json raise); non-dict scalar→list(...) (TypeError).
  - field_map: map key TRƯỚC khi tạo điều kiện (contract: workflow_state→status).
  - safe=True (tasks): json.loads + try/except → bad-JSON→[]; non-list fallback→[].

Lệnh: bench --site miyano run-tests --app antmed_crm --module antmed_crm.tests.test_antmed_filters
"""

import json

import frappe
from frappe.tests.utils import FrappeTestCase

from antmed_crm.api.antmed._filters import coerce_filters


class TestCoerceFiltersStandard(FrappeTestCase):
	"""Bản chuẩn (6 module giống hệt) — safe=False, không field_map."""

	def test_dict_to_conditions(self):
		self.assertEqual(coerce_filters({"a": 1}), [["a", "=", 1]])

	def test_dict_multi_key_order_preserved(self):
		# dict giữ thứ tự insert (py3.7+) → conditions theo đúng thứ tự (Hyrum: FE/BE phụ thuộc).
		self.assertEqual(
			coerce_filters({"hospital": "H1", "status": "Active"}),
			[["hospital", "=", "H1"], ["status", "=", "Active"]],
		)

	def test_json_string_dict(self):
		self.assertEqual(coerce_filters('{"a":1}'), [["a", "=", 1]])

	def test_json_string_list_passthrough(self):
		self.assertEqual(coerce_filters('[["a","=",1]]'), [["a", "=", 1]])

	def test_none_returns_empty(self):
		self.assertEqual(coerce_filters(None), [])

	def test_empty_string_returns_empty(self):
		self.assertEqual(coerce_filters(""), [])

	def test_empty_dict_returns_empty(self):
		# {} falsy → nhánh `if not filters` → [] (KHÔNG đi vào dict-branch).
		self.assertEqual(coerce_filters({}), [])

	def test_empty_list_returns_empty(self):
		self.assertEqual(coerce_filters([]), [])

	def test_list_passthrough_copies(self):
		# list → list(filters): bản sao mới (không alias), nội dung giữ nguyên.
		src = [["a", "=", 1], ["b", ">", 2]]
		out = coerce_filters(src)
		self.assertEqual(out, src)
		self.assertIsNot(out, src)

	def test_json_string_null_returns_empty(self):
		# parse_json("null") → None; `None or []` → []. (Khoá: KHÔNG raise.)
		self.assertEqual(coerce_filters("null"), [])

	def test_bad_json_raises(self):
		# CHỐT: bản chuẩn KHÔNG nuốt lỗi — frappe.parse_json raise trên JSON hỏng.
		with self.assertRaises(Exception):
			coerce_filters("{bad")


class TestCoerceFiltersFieldMap(FrappeTestCase):
	"""contract.py — ADR-M02-04: map key workflow_state→status."""

	def test_field_map_remaps_key(self):
		self.assertEqual(
			coerce_filters({"workflow_state": "Đã duyệt"}, field_map={"workflow_state": "status"}),
			[["status", "=", "Đã duyệt"]],
		)

	def test_field_map_passthrough_unmapped_key(self):
		self.assertEqual(
			coerce_filters({"hospital": "H1"}, field_map={"workflow_state": "status"}),
			[["hospital", "=", "H1"]],
		)

	def test_field_map_mixed_keys(self):
		self.assertEqual(
			coerce_filters(
				{"hospital": "H1", "workflow_state": "X"},
				field_map={"workflow_state": "status"},
			),
			[["hospital", "=", "H1"], ["status", "=", "X"]],
		)

	def test_field_map_from_json_string(self):
		self.assertEqual(
			coerce_filters('{"workflow_state":"X"}', field_map={"workflow_state": "status"}),
			[["status", "=", "X"]],
		)

	def test_field_map_does_not_affect_list(self):
		# list passthrough KHÔNG remap (bản gốc contract chỉ map trong dict-branch).
		self.assertEqual(
			coerce_filters([["workflow_state", "=", "X"]], field_map={"workflow_state": "status"}),
			[["workflow_state", "=", "X"]],
		)


class TestCoerceFiltersSafe(FrappeTestCase):
	"""tasks.py — safe=True: json.loads + swallow bad-JSON→[]; non-list fallback→[]."""

	def test_safe_dict(self):
		self.assertEqual(coerce_filters({"a": 1}, safe=True), [["a", "=", 1]])

	def test_safe_json_string_dict(self):
		self.assertEqual(coerce_filters('{"a":1}', safe=True), [["a", "=", 1]])

	def test_safe_json_string_list(self):
		self.assertEqual(coerce_filters('[["a","=",1]]', safe=True), [["a", "=", 1]])

	def test_safe_none(self):
		self.assertEqual(coerce_filters(None, safe=True), [])

	def test_safe_bad_json_swallowed(self):
		# CHỐT khác bản chuẩn: tasks NUỐT lỗi JSON → [].
		self.assertEqual(coerce_filters("{bad", safe=True), [])

	def test_safe_non_list_scalar_fallback(self):
		# tasks: non-list, non-dict → []. (json.loads("123")→123→ not dict, not list → []).
		self.assertEqual(coerce_filters("123", safe=True), [])

	def test_safe_list_passthrough(self):
		src = [["a", "=", 1]]
		self.assertEqual(coerce_filters(src, safe=True), src)
