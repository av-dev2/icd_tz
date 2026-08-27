# Copyright (c) 2024, elius mgani and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import nowdate

from icd_tz.icd_tz.doctype.in_yard_container_booking.in_yard_container_booking import (
	create_bulk_bookings,
)
from icd_tz.tests.utils import (
	create_booking,
	create_cf_company,
	create_clearing_agent,
	create_container,
	create_container_location,
	create_icd_tz_settings,
)


class TestInYardContainerBooking(IntegrationTestCase):
	def setUp(self):
		create_icd_tz_settings()

	def tearDown(self):
		frappe.db.rollback()

	def test_booking_moves_the_container_to_at_booking(self):
		booking = create_booking()
		self.assertEqual(frappe.db.get_value("Container", booking.container_id, "status"), "At Booking")

	def test_a_second_booking_for_the_same_container_is_rejected(self):
		booking = create_booking()
		self.assertRaises(
			frappe.ValidationError,
			create_booking,
			container=frappe.get_doc("Container", booking.container_id),
		)

	def test_an_additional_booking_is_allowed(self):
		booking = create_booking()
		container = frappe.get_doc("Container", booking.container_id)
		self.assertTrue(create_booking(container=container, is_additional_booking=1).name)

	def test_an_agent_from_another_company_is_rejected(self):
		other_company = create_cf_company("ICD Test Other C&F Company")
		self.assertRaises(
			frappe.ValidationError,
			create_booking,
			clearing_agent=create_clearing_agent("ICD Test Other Agent", other_company),
		)

	def test_a_delivered_container_cannot_be_booked(self):
		container = create_container()
		container.db_set("status", "Delivered")
		self.assertRaises(frappe.ValidationError, create_booking, container=container)

	def test_submitting_a_booking_stamps_the_container_booking_date(self):
		booking = create_booking()
		booking.submit()
		self.assertEqual(
			frappe.db.get_value("Container", booking.container_id, "booking_date"),
			frappe.utils.getdate(nowdate()),
		)

	def test_bulk_booking_skips_containers_that_are_already_booked(self):
		container = create_container()
		create_booking(container=container)
		c_and_f_company = create_cf_company()

		created = create_bulk_bookings(
			frappe.as_json(
				{
					"c_and_f_company": c_and_f_company,
					"clearing_agent": create_clearing_agent(c_and_f_company=c_and_f_company),
					"m_bl_no": container.m_bl_no,
					"inspection_date": nowdate(),
					"inspection_location": create_container_location(),
				}
			)
		)

		self.assertEqual(created, 0)
