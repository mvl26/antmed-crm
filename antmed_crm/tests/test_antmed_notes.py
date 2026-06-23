# Copyright (c) 2026, AntMed and Contributors
"""Test AntMed Notes/Activity (antmed_crm.api.antmed.notes) — FCRM Note + CRM Task theo reference.

FCRM Note + CRM Task có Dynamic Link → reference_docname PHẢI là bản ghi THẬT (validate tồn tại).
R-9: fixture setUpClass (1 Bệnh viện thật làm reference) → tearDownClass (prefix _T-NOTE greppable).
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from antmed_crm.api.antmed.notes import activity, add_note, list_notes

REF_DT = "AntMed Hospital"


class TestAntmedNotes(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.notes = []
		cls.tasks = []
		# Bệnh viện THẬT làm reference (Dynamic Link validate tồn tại).
		cls.ref_dn = (
			frappe.get_doc(
				{"doctype": REF_DT, "hospital_code": "_T-NOTE-BV", "hospital_name": "BV Ghi chú Test"}
			)
			.insert(ignore_permissions=True)
			.name
		)
		# 1 ghi chú + 1 công việc cùng gắn bản ghi đó → activity gộp cả 2.
		n = add_note(REF_DT, cls.ref_dn, content="<p>Đã gọi xác nhận gói thầu</p>", title="_T-NOTE Gọi BV")
		cls.notes.append(n["name"])
		t = frappe.get_doc(
			{
				"doctype": "CRM Task",
				"title": "_T-NOTE Theo dõi ký HĐ",
				"status": "Todo",
				"priority": "High",
				"reference_doctype": REF_DT,
				"reference_docname": cls.ref_dn,
			}
		).insert(ignore_permissions=True)
		cls.tasks.append(t.name)
		frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		for dt, names in (("FCRM Note", cls.notes), ("CRM Task", cls.tasks)):
			for n in names:
				try:
					frappe.delete_doc(dt, n, force=True)
				except Exception:
					pass
		try:
			frappe.delete_doc(REF_DT, cls.ref_dn, force=True)
		except Exception:
			pass
		frappe.db.commit()
		super().tearDownClass()

	def test_add_note_persists_with_reference(self):
		row = frappe.db.get_value(
			"FCRM Note", self.notes[0], ["reference_doctype", "reference_docname"], as_dict=True
		)
		self.assertEqual(row.reference_doctype, REF_DT)
		self.assertEqual(row.reference_docname, self.ref_dn)

	def test_add_note_rejects_empty(self):
		with self.assertRaises(frappe.ValidationError):
			add_note(REF_DT, self.ref_dn, content="   ")

	def test_add_note_without_title_derives_from_content(self):
		# FCRM Note.title BẮT BUỘC → add_note KHÔNG truyền title vẫn tạo được (suy từ content),
		# KHÔNG ném MandatoryError (bug đã gặp khi thêm ghi chú từ UI).
		n = add_note(REF_DT, self.ref_dn, content="<p>Ghi chú không tiêu đề — phải tự suy</p>")
		self.notes.append(n["name"])
		self.assertTrue(n["title"])
		self.assertTrue(frappe.db.exists("FCRM Note", n["name"]))

	def test_list_notes_scoped_to_reference(self):
		r = list_notes(REF_DT, self.ref_dn)
		names = [n["name"] for n in r["data"]]
		self.assertIn(self.notes[0], names)
		self.assertEqual(r["total_count"], len(r["data"]))
		self.assertIn("owner_name", r["data"][0])

	def test_activity_merges_note_and_task(self):
		a = activity(REF_DT, self.ref_dn)
		self.assertEqual(a["note_count"], 1)
		self.assertEqual(a["task_count"], 1)
		self.assertEqual({e["type"] for e in a["events"]}, {"note", "task"})
		for e in a["events"]:
			for k in ("time", "text", "sub"):
				self.assertIn(k, e)
		task_ev = next(e for e in a["events"] if e["type"] == "task")
		self.assertTrue(task_ev.get("highlight"))
