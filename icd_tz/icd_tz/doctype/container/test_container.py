# Copyright (c) 2024, elius mgani and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, nowdate

from icd_tz.icd_tz.doctype.container.container import get_place_of_destination
from icd_tz.tests.utils import (
	create_container,
	create_container_reception,
	create_icd_tz_settings,
)


class TestContainer(IntegrationTestCase):
	def setUp(self):
		create_icd_tz_settings()

	def tearDown(self):
		frappe.db.rollback()

	def test_place_of_destination_must_come_from_the_settings(self):
		self.assertRaises(frappe.ValidationError, create_container, place_of_destination="Nowhere")

	def test_configured_place_of_destination_is_accepted(self):
		self.assertIn("Local", get_place_of_destination())
		self.assertTrue(create_container(place_of_destination="Local").name)

	def test_a_container_without_dates_takes_its_received_date(self):
		"""before_insert seeds container_dates from the received date when the table is empty."""

		reception = create_container_reception()
		container = frappe.get_doc(
			{
				"doctype": "Container",
				"container_reception": reception.name,
				"container_no": reception.container_no,
				"manifest": reception.manifest,
				"received_date": nowdate(),
				"place_of_destination": "Local",
				"country_of_destination": "Tanzania",
			}
		)
		container.insert(ignore_permissions=True)

		self.assertEqual(len(container.container_dates), 1)
		self.assertEqual(getdate(container.container_dates[0].date), getdate(nowdate()))

	def test_free_days_are_not_billable(self):
		container = create_container()
		for offset in range(1, 5):
			container.append("container_dates", {"date": add_days(nowdate(), offset), "is_billable": 1})
		container.save(ignore_permissions=True)

		self.assertEqual(container.no_of_free_days, len(container.container_dates))
		self.assertEqual(container.days_to_be_billed, 0)
		self.assertEqual(container.has_single_charge, 0)

	def test_days_past_the_free_window_become_a_single_charge(self):
		container = create_container()
		for offset in range(1, 10):
			container.append("container_dates", {"date": add_days(nowdate(), offset), "is_billable": 1})
		container.save(ignore_permissions=True)

		self.assertEqual(container.no_of_free_days, 7)
		self.assertEqual(container.no_of_billable_days, 3)
		self.assertEqual(container.has_single_charge, 1)
		self.assertEqual(container.has_double_charge, 0)

	def test_update_container_stay_fills_every_day_up_to_the_given_date(self):
		container = create_container(received_date=add_days(nowdate(), -3))
		container.update_container_stay()

		self.assertEqual(len(container.container_dates), 4)

	def test_a_delivered_container_cannot_be_deleted(self):
		container = create_container()
		container.db_set("status", "Delivered")
		container.reload()

		self.assertRaises(frappe.ValidationError, container.delete)
