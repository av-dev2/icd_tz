# Copyright (c) 2024, elius mgani and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from icd_tz.tests.utils import (
	create_booking,
	create_cf_company,
	create_clearing_agent,
	create_consignee,
	create_container,
	create_icd_tz_settings,
	create_inspection,
)


class TestServiceOrder(IntegrationTestCase):
	def setUp(self):
		create_icd_tz_settings()

	def tearDown(self):
		frappe.db.rollback()

	def test_a_service_order_moves_the_container_to_at_payments(self):
		order = create_service_order()
		self.assertEqual(frappe.db.get_value("Container", order.container_id, "status"), "At Payments")

	def test_a_service_order_copies_the_container_references(self):
		container = create_container()
		order = create_service_order(container=container)

		self.assertEqual(order.manifest, container.manifest)
		self.assertEqual(order.container_no, container.container_no)

	def test_a_delivered_container_cannot_get_a_service_order(self):
		container = create_container()
		container.db_set("status", "Delivered")

		self.assertRaises(frappe.ValidationError, create_service_order, container=container)

	def test_a_draft_booking_blocks_the_service_order(self):
		booking = create_booking()
		container = frappe.get_doc("Container", booking.container_id)

		self.assertRaises(frappe.ValidationError, create_service_order, container=container)

	def test_a_draft_inspection_blocks_the_service_order(self):
		inspection = create_inspection()
		container = frappe.get_doc("Container", inspection.container_id)

		self.assertRaises(frappe.ValidationError, create_service_order, container=container)

	def test_an_agent_from_another_company_is_rejected(self):
		other_company = create_cf_company("ICD Test Other C&F Company")

		self.assertRaises(
			frappe.ValidationError,
			create_service_order,
			clearing_agent=create_clearing_agent("ICD Test Other Agent", other_company),
		)

	def test_submitting_a_service_order_creates_its_gate_pass(self):
		container = create_container(consignee=create_consignee())
		order = create_service_order(container=container)
		order.submit()
		order.reload()

		self.assertTrue(order.get_pass)
		self.assertTrue(frappe.db.exists("Gate Pass", order.get_pass))


def create_service_order(container=None, **kwargs):
	container_doc = container or create_container()
	c_and_f_company = create_cf_company()

	values = {
		"doctype": "Service Order",
		"container_id": container_doc.name,
		"container_no": container_doc.container_no,
		"c_and_f_company": c_and_f_company,
		"clearing_agent": create_clearing_agent(c_and_f_company=c_and_f_company),
	}
	values.update(kwargs)

	order = frappe.get_doc(values)
	order.insert(ignore_permissions=True)
	return order
