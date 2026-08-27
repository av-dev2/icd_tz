# Copyright (c) 2024, elius mgani and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase


class TestTransporter(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_a_transporter_is_named_after_its_company(self):
		transporter = frappe.get_doc(
			{
				"doctype": "Transporter",
				"company_name": "ICD Test Haulage",
				"phone": "255700000001",
				"email": "haulage@example.com",
				"physical_address": "Dar es Salaam",
				"person_name": "Test Person",
			}
		).insert(ignore_permissions=True)

		self.assertEqual(transporter.name, "ICD Test Haulage")

	def test_the_contact_details_are_mandatory(self):
		transporter = frappe.get_doc({"doctype": "Transporter", "company_name": "ICD Test Bare Haulage"})
		self.assertRaises(frappe.MandatoryError, transporter.insert)
