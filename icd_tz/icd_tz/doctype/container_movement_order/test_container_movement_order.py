# Copyright (c) 2024, elius mgani and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from icd_tz.tests.utils import (
	create_container_reception,
	create_icd_tz_settings,
	create_movement_order,
)


class TestContainerMovementOrder(IntegrationTestCase):
	def setUp(self):
		create_icd_tz_settings()

	def tearDown(self):
		frappe.db.rollback()

	def test_an_order_carries_its_manifest_references(self):
		order = create_movement_order()

		self.assertTrue(order.manifest)
		self.assertEqual(order.container_no, "TESU1234567")
		self.assertEqual(order.docstatus, 1)

	def test_a_container_outside_the_manifest_is_rejected(self):
		order = create_movement_order(submit=False)
		order.container_no = "TESU7654321"

		self.assertRaises(frappe.ValidationError, order.save)

	def test_receiving_the_container_marks_the_order_received(self):
		order = create_movement_order()
		reception = create_container_reception(movement_order=order)
		reception.submit()

		self.assertEqual(frappe.db.get_value("Container Movement Order", order.name, "status"), "Received")

	def test_cancelling_the_reception_returns_the_order_to_pending(self):
		order = create_movement_order()
		reception = create_container_reception(movement_order=order)
		reception.submit()
		reception.cancel()

		self.assertEqual(frappe.db.get_value("Container Movement Order", order.name, "status"), "Pending")
