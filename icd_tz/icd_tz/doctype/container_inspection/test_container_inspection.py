# Copyright (c) 2024, elius mgani and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import nowdate

from icd_tz.icd_tz.doctype.in_yard_container_booking.in_yard_container_booking import (
	create_additional_booking,
)
from icd_tz.tests.utils import (
	create_booking,
	create_container_location,
	create_icd_tz_settings,
	create_inspection,
)


class TestContainerInspection(IntegrationTestCase):
	def setUp(self):
		create_icd_tz_settings()

	def tearDown(self):
		frappe.db.rollback()

	def test_inspection_moves_the_container_to_at_inspection(self):
		inspection = create_inspection()
		self.assertEqual(frappe.db.get_value("Container", inspection.container_id, "status"), "At Inspection")

	def test_inspection_is_linked_back_onto_its_booking(self):
		inspection = create_inspection()
		self.assertEqual(
			frappe.db.get_value(
				"In Yard Container Booking", inspection.in_yard_container_booking, "container_inspection"
			),
			inspection.name,
		)

	def test_an_inspection_on_a_draft_booking_is_rejected(self):
		booking = create_booking()
		self.assertRaises(frappe.ValidationError, create_inspection, booking=booking)

	def test_a_second_inspection_for_the_same_container_is_rejected(self):
		inspection = create_inspection()
		self.assertRaises(
			frappe.ValidationError,
			create_inspection,
			booking=frappe.get_doc("In Yard Container Booking", inspection.in_yard_container_booking),
		)

	def test_an_inspection_from_an_additional_booking_is_an_additional_inspection(self):
		inspection = create_inspection(submit=True)
		booking_name = create_additional_booking(inspection.name, nowdate(), create_container_location())
		booking = frappe.get_doc("In Yard Container Booking", booking_name)
		booking.submit()

		repeat = create_inspection(booking=booking)
		self.assertEqual(repeat.is_additional_inspection, 1)

	def test_submitting_an_inspection_stamps_the_container(self):
		inspection = create_inspection(new_container_location=create_container_location("ICD Test Bay 2"))
		inspection.submit()

		container = frappe.get_doc("Container", inspection.container_id)
		self.assertEqual(container.current_location, "ICD Test Bay 2")
		self.assertEqual(
			frappe.utils.getdate(container.last_inspection_date), frappe.utils.getdate(nowdate())
		)

	def test_deleting_an_inspection_returns_the_container_to_at_booking(self):
		inspection = create_inspection()
		inspection.delete()

		self.assertEqual(frappe.db.get_value("Container", inspection.container_id, "status"), "At Booking")
