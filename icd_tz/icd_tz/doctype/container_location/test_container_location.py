# Copyright (c) 2024, elius mgani and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase


class TestContainerLocation(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_a_location_is_named_after_itself(self):
		location = frappe.get_doc(
			{"doctype": "Container Location", "location_name": "ICD Test Bay 9"}
		).insert(ignore_permissions=True)

		self.assertEqual(location.name, "ICD Test Bay 9")

	def test_a_location_without_a_name_is_rejected(self):
		location = frappe.get_doc({"doctype": "Container Location"})
		self.assertRaises(frappe.ValidationError, location.insert)
