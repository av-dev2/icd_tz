# Copyright (c) 2024, elius mgani and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase


class TestContainerState(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_a_state_is_named_after_itself(self):
		state = frappe.get_doc({"doctype": "Container State", "state": "ICD Test Dented"}).insert(
			ignore_permissions=True
		)

		self.assertEqual(state.name, "ICD Test Dented")

	def test_a_state_without_a_name_is_rejected(self):
		self.assertRaises(frappe.ValidationError, frappe.get_doc({"doctype": "Container State"}).insert)
