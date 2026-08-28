# Copyright (c) 2024, elius mgani and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase


class TestBookingdetail(IntegrationTestCase):
	def test_booking_detail_is_a_child_table(self):
		self.assertEqual(frappe.get_meta("Booking detail").istable, 1)

	def test_booking_detail_links_a_clearing_agent(self):
		self.assertEqual(
			frappe.get_meta("Booking detail").get_field("c_and_f_agent").options, "Clearing Agent"
		)
