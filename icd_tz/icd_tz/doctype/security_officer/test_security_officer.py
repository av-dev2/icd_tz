# Copyright (c) 2024, elius mgani and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase


class TestSecurityofficer(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_an_officer_is_named_after_itself(self):
		officer = frappe.get_doc({"doctype": "Security officer", "full_name": "ICD Test Officer"}).insert(
			ignore_permissions=True
		)

		self.assertEqual(officer.name, "ICD Test Officer")

	def test_an_officer_without_a_name_is_rejected(self):
		self.assertRaises(frappe.ValidationError, frappe.get_doc({"doctype": "Security officer"}).insert)
