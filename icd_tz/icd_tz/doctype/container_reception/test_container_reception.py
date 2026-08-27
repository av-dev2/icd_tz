# Copyright (c) 2024, elius mgani and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_to_date, getdate, nowdate

from icd_tz.icd_tz.doctype.container_reception.container_reception import get_received_date
from icd_tz.tests.utils import (
	create_container_reception,
	create_icd_tz_settings,
	create_movement_order,
)


class TestContainerReception(IntegrationTestCase):
	def setUp(self):
		create_icd_tz_settings()

	def tearDown(self):
		frappe.db.rollback()

	def test_received_date_falls_back_to_ship_dc_date_within_the_threshold(self):
		ship_dc_date = nowdate()
		self.assertEqual(get_received_date(ship_dc_date, ship_dc_date), getdate(ship_dc_date))

	def test_received_date_moves_to_posting_date_past_the_threshold(self):
		ship_dc_date = add_to_date(nowdate(), days=-3, as_string=True)
		self.assertEqual(get_received_date(nowdate(), ship_dc_date), getdate(nowdate()))

	def test_a_second_reception_on_the_same_movement_order_is_rejected(self):
		order = create_movement_order()
		create_container_reception(movement_order=order)

		self.assertRaises(frappe.ValidationError, create_container_reception, movement_order=order)

	def test_the_created_container_keeps_the_reception_weight(self):
		"""create_mbl_container copies the reception onto the Container, weight included."""

		reception = create_container_reception(weight="2500")
		reception.submit()

		container_no = frappe.db.get_value("Container", {"container_reception": reception.name}, "name")
		self.assertTrue(container_no)
		self.assertEqual(frappe.db.get_value("Container", container_no, "weight"), "2500")
