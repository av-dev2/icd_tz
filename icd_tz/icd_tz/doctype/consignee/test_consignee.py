# Copyright (c) 2024, elius mgani and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from icd_tz.icd_tz.doctype.consignee.consignee import create_customer
from icd_tz.tests.utils import create_consignee


class TestConsignee(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_a_consignee_is_given_a_customer_for_billing(self):
		consignee = create_consignee("ICD Test Billing Consignee")

		create_customer()

		customer = frappe.db.get_value("Consignee", consignee, "customer")
		self.assertTrue(customer)
		self.assertEqual(frappe.db.get_value("Customer", customer, "customer_name"), consignee)

	def test_an_existing_customer_is_reused(self):
		consignee = create_consignee("ICD Test Existing Customer")
		customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": consignee,
				"customer_group": get_customer_group(),
				"territory": "All Territories",
			}
		).insert(ignore_permissions=True)

		create_customer()

		self.assertEqual(frappe.db.get_value("Consignee", consignee, "customer"), customer.name)

	def test_a_consignee_that_already_has_a_customer_is_left_alone(self):
		consignee = create_consignee("ICD Test Linked Consignee")
		frappe.db.set_value("Consignee", consignee, "customer", "_Test Customer")

		create_customer()

		self.assertEqual(frappe.db.get_value("Consignee", consignee, "customer"), "_Test Customer")


def get_customer_group():
	return frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
