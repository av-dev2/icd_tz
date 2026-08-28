# Copyright (c) 2024, elius mgani and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from icd_tz.tests.utils import create_cf_company


class TestClearingandForwardingCompany(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_a_company_is_named_after_itself(self):
		self.assertEqual(create_cf_company("ICD Test Named Company"), "ICD Test Named Company")

	def test_the_contact_details_are_mandatory(self):
		company = frappe.get_doc(
			{"doctype": "Clearing and Forwarding Company", "company_name": "ICD Test Bare Company"}
		)
		self.assertRaises(frappe.MandatoryError, company.insert)
