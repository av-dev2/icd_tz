# Copyright (c) 2024, elius mgani and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from icd_tz.icd_tz.doctype.container.container import get_place_of_destination
from icd_tz.tests.utils import create_icd_tz_settings


class TestICDTZSettings(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_the_settings_single_is_loadable(self):
		self.assertEqual(frappe.get_single("ICD TZ Settings").doctype, "ICD TZ Settings")

	def test_the_storage_days_drive_the_places_of_destination(self):
		create_icd_tz_settings()
		places = get_place_of_destination()

		self.assertIn("Local", places)
		self.assertIn("Transit", places)

	def test_the_gate_pass_expiry_is_configurable(self):
		settings = create_icd_tz_settings()
		settings.gate_pass_expiry_hours = 48
		settings.save(ignore_permissions=True)

		self.assertEqual(frappe.db.get_single_value("ICD TZ Settings", "gate_pass_expiry_hours"), 48)
