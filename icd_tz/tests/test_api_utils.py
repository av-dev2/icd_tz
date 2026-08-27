"""Coverage for the shared guards in icd_tz.icd_tz.api.utils."""

import frappe
from frappe.tests import IntegrationTestCase

from icd_tz.icd_tz.api.utils import (
	get_delivered_containers,
	submit_doc,
	validate_cf_agent,
	validate_delivered_container,
	validate_delivered_containers,
	validate_draft_doc,
	validate_qty_storage_item,
)
from icd_tz.tests.utils import (
	create_booking,
	create_cf_company,
	create_clearing_agent,
	create_container,
	create_icd_tz_settings,
)


class TestApiUtils(IntegrationTestCase):
	def setUp(self):
		self.settings = create_icd_tz_settings()

	def tearDown(self):
		frappe.db.rollback()

	def test_a_container_still_in_the_yard_passes_the_guard(self):
		container = create_container()
		validate_delivered_container(container.name, container.container_no)

	def test_a_delivered_container_is_blocked(self):
		container = create_container()
		container.db_set("status", "Delivered")

		self.assertRaises(
			frappe.ValidationError, validate_delivered_container, container.name, container.container_no
		)

	def test_the_guard_is_a_no_op_without_a_container(self):
		validate_delivered_container(None)

	def test_delivered_containers_are_listed_for_bulk_callers(self):
		container = create_container()
		self.assertEqual(get_delivered_containers([container.name]), [])

		container.db_set("status", "At Gate Confirmation")
		self.assertEqual(get_delivered_containers([container.name]), [container.name])

	def test_an_empty_container_list_short_circuits(self):
		self.assertEqual(get_delivered_containers([]), [])

	def test_a_batch_holding_a_delivered_container_is_blocked(self):
		container = create_container()
		container.db_set("status", "Delivered")

		self.assertRaises(frappe.ValidationError, validate_delivered_containers, [container.name])

	def test_an_agent_outside_the_company_is_rejected(self):
		company = create_cf_company()
		other_company = create_cf_company("ICD Test Other C&F Company")
		agent = create_clearing_agent("ICD Test Other Agent", other_company)

		doc = frappe.get_doc({"doctype": "Gate Pass", "c_and_f_company": company, "clearing_agent": agent})
		self.assertRaises(frappe.ValidationError, validate_cf_agent, doc)

	def test_an_agent_inside_the_company_is_accepted(self):
		company = create_cf_company()
		doc = frappe.get_doc(
			{
				"doctype": "Gate Pass",
				"c_and_f_company": company,
				"clearing_agent": create_clearing_agent(c_and_f_company=company),
			}
		)
		validate_cf_agent(doc)

	def test_a_draft_document_cannot_be_linked(self):
		booking = create_booking()
		self.assertRaises(
			frappe.ValidationError, validate_draft_doc, "In Yard Container Booking", booking.name
		)

	def test_a_submitted_document_can_be_linked(self):
		booking = create_booking()
		booking.submit()
		validate_draft_doc("In Yard Container Booking", booking.name)

	def test_submit_doc_submits_the_named_document(self):
		booking = create_booking()
		self.assertTrue(submit_doc("In Yard Container Booking", booking.name))
		self.assertEqual(frappe.db.get_value("In Yard Container Booking", booking.name, "docstatus"), 1)

	def test_a_lower_storage_qty_trims_the_container_references(self):
		doc = self.storage_order(qty=2, refs="2026-01-01,2026-01-02,2026-01-03")
		validate_qty_storage_item(doc)

		self.assertEqual(doc.items[0].container_child_refs, "2026-01-01,2026-01-02")

	def test_a_storage_qty_above_the_references_is_rejected(self):
		doc = self.storage_order(qty=5, refs="2026-01-01,2026-01-02")
		self.assertRaises(frappe.ValidationError, validate_qty_storage_item, doc)

	def test_a_house_bill_order_is_left_alone(self):
		doc = self.storage_order(qty=5, refs="2026-01-01", h_bl_no="HBL-1")
		validate_qty_storage_item(doc)

		self.assertEqual(doc.items[0].container_child_refs, "2026-01-01")

	def storage_order(self, qty, refs, h_bl_no=None):
		storage_item = next(
			row.service_name for row in self.settings.service_types if row.service_type == "Storage-Single"
		)

		order = frappe.new_doc("Sales Order")
		order.m_bl_no = "MBL-TEST-001"
		order.h_bl_no = h_bl_no
		order.append("items", {"item_code": storage_item, "qty": qty, "container_child_refs": refs})
		return order
