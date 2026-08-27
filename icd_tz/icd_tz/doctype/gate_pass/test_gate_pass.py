# Copyright (c) 2024, elius mgani and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_to_date, get_datetime, now_datetime

from icd_tz.icd_tz.doctype.gate_pass.gate_pass import (
	auto_expire_gate_passes,
	create_getpass_for_empty_container,
)
from icd_tz.tests.utils import (
	create_cf_company,
	create_clearing_agent,
	create_container,
	create_gate_pass,
	create_icd_tz_settings,
)


class TestGatePass(IntegrationTestCase):
	def setUp(self):
		create_icd_tz_settings()

	def tearDown(self):
		frappe.db.rollback()

	def test_an_agent_from_another_company_is_rejected(self):
		other_company = create_cf_company("ICD Test Other C&F Company")
		self.assertRaises(
			frappe.ValidationError,
			create_gate_pass,
			clearing_agent=create_clearing_agent("ICD Test Other Agent", other_company),
		)

	def test_submitting_without_the_transport_details_is_rejected(self):
		gate_pass = create_gate_pass(container=create_empty_container())
		self.assertRaises(frappe.ValidationError, gate_pass.submit)

	def test_submitting_stamps_the_expiry_from_the_settings(self):
		gate_pass = submit_empty_gate_pass()

		self.assertTrue(gate_pass.expiry_date)
		expected = add_to_date(
			get_datetime(f"{gate_pass.submitted_date} {gate_pass.submitted_time}"), hours=24
		)
		self.assertEqual(get_datetime(gate_pass.expiry_date), expected)

	def test_submitting_moves_the_container_to_at_gate_confirmation(self):
		gate_pass = submit_empty_gate_pass()
		self.assertEqual(
			frappe.db.get_value("Container", gate_pass.container_id, "status"), "At Gate Confirmation"
		)

	def test_cancelling_flags_the_container_for_a_cancellation_charge(self):
		gate_pass = submit_empty_gate_pass()
		gate_pass.cancel()

		container = frappe.get_doc("Container", gate_pass.container_id)
		self.assertEqual(container.status, "At Gatepass")
		self.assertEqual(container.has_cancellation_charge, 1)

	def test_a_second_gate_pass_for_an_empty_container_is_rejected(self):
		container = create_empty_container()
		create_gate_pass(container=container)

		self.assertRaises(frappe.ValidationError, create_getpass_for_empty_container, container.name)

	def test_auto_expire_cancels_a_gate_pass_that_is_past_its_expiry(self):
		gate_pass = submit_empty_gate_pass()
		gate_pass.db_set("expiry_date", add_to_date(now_datetime(), hours=-1))

		auto_expire_gate_passes()

		self.assertEqual(frappe.db.get_value("Gate Pass", gate_pass.name, "docstatus"), 2)

	def test_auto_expire_leaves_a_gate_pass_that_is_still_valid(self):
		gate_pass = submit_empty_gate_pass()

		auto_expire_gate_passes()

		self.assertEqual(frappe.db.get_value("Gate Pass", gate_pass.name, "docstatus"), 1)


def create_empty_container():
	"""is_empty_container is fetched read-only from the Container, it cannot be set on the Gate Pass."""

	return create_container(is_empty_container=1)


def submit_empty_gate_pass(**kwargs):
	gate_pass = create_gate_pass(container=create_empty_container(), **kwargs)
	gate_pass.update(
		{
			"transporter": "ICD Test Transporter",
			"truck": "ICD-TRUCK-01",
			"trailer": "ICD-TRAILER-01",
			"driver": "ICD Test Driver",
			"license_no": "DL-0001",
		}
	)
	gate_pass.submit()
	return gate_pass
