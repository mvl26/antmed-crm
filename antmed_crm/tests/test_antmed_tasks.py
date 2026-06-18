# Copyright (c) 2026, AntMed and Contributors
"""Test endpoint AntMed Tasks (antmed_crm.api.antmed.tasks.list_tasks) trên CRM Task.

R-9: fixture tạo trong setUpClass → xoá trong tearDownClass (prefix _T-TASK greppable).
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from antmed_crm.api.antmed.tasks import list_tasks

P = "_T-TASK"


class TestAntmedTasks(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.created = []
		for title, status, pr in [
			(f"{P} Gọi CSKH BS An", "Todo", "High"),
			(f"{P} Soạn hồ sơ thầu", "Done", "Low"),
		]:
			doc = frappe.get_doc(
				{
					"doctype": "CRM Task",
					"title": title,
					"status": status,
					"priority": pr,
					"assigned_to": "Administrator",
				}
			).insert(ignore_permissions=True)
			cls.created.append(doc.name)
		frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		for n in cls.created:
			try:
				frappe.delete_doc("CRM Task", n, force=True)
			except Exception:
				pass
		frappe.db.commit()
		super().tearDownClass()

	def _mine(self, rows):
		ids = {str(x) for x in self.created}
		return [t for t in rows if str(t["name"]) in ids]

	def test_list_shape_and_assignee_name(self):
		r = list_tasks()
		for k in ("data", "total_count", "open_count"):
			self.assertIn(k, r)
		mine = self._mine(r["data"])
		self.assertEqual(len(mine), 2)
		t = mine[0]
		for k in ("title", "status", "priority", "assigned_to_name", "is_open"):
			self.assertIn(k, t)
		# resolve full_name (KHÔNG lộ email)
		self.assertEqual(
			t["assigned_to_name"], frappe.db.get_value("User", "Administrator", "full_name")
		)

	def test_status_filter(self):
		r = list_tasks(status="Done")
		titles = [t["title"] for t in r["data"]]
		self.assertIn(f"{P} Soạn hồ sơ thầu", titles)
		self.assertNotIn(f"{P} Gọi CSKH BS An", titles)

	def test_is_open_flag(self):
		r = list_tasks(status="Todo")
		todo = [t for t in r["data"] if t["title"] == f"{P} Gọi CSKH BS An"]
		self.assertTrue(todo)
		self.assertTrue(todo[0]["is_open"])
