# Copyright (c) 2024, elius mgani and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase


class TestConditionstate(IntegrationTestCase):
	def test_condition_state_is_a_child_table(self):
		self.assertEqual(frappe.get_meta("Condition state").istable, 1)

	def test_condition_state_links_a_container_state(self):
		self.assertEqual(frappe.get_meta("Condition state").get_field("state").options, "Container State")
