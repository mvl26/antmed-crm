# Copyright (c) 2026, AntMed and Contributors
# See license.txt
"""AntMed health endpoint — smoke chứng minh đường BE callable (M01 R1)."""

import frappe

import antmed_crm


@frappe.whitelist(methods=["GET"])
def ping() -> dict:
	"""Smoke endpoint — chứng minh đường BE callable.

	Đường gọi: antmed_crm.api.antmed.health.ping (GET, yêu cầu session).
	Trả RAW dict thuần (KHÔNG envelope). version lấy động từ antmed_crm.__version__.
	"""
	return {
		"app": "antmed",
		"status": "ok",
		"version": antmed_crm.__version__,
	}
