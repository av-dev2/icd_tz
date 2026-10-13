# Copyright (c) 2024, elius mgani and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from icd_tz.icd_tz.doctype.container.container import get_place_of_destination
from icd_tz.tests.utils import create_icd_tz_settings, get_test_company


class TestICDSetting(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_the_setting_of_the_test_company_is_loadable(self):
		settings = create_icd_tz_settings()

		self.assertEqual(frappe.get_doc("ICD Setting", settings.name).company, get_test_company())

	def test_the_storage_days_drive_the_places_of_destination(self):
		create_icd_tz_settings()
		places = get_place_of_destination(get_test_company())

		self.assertIn("Local", places)
		self.assertIn("Transit", places)

	def test_the_gate_pass_expiry_is_configurable(self):
		settings = create_icd_tz_settings()
		settings.gate_pass_expiry_hours = 48
		settings.save(ignore_permissions=True)

		self.assertEqual(frappe.db.get_value("ICD Setting", settings.name, "gate_pass_expiry_hours"), 48)
