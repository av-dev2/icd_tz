"""Regressions for the framework behaviour that changed between version-15 and version-16."""

import frappe
from frappe.tests import IntegrationTestCase

from icd_tz.icd_tz.doctype.consignee.consignee import create_customer
from icd_tz.icd_tz.doctype.gate_pass.gate_pass import auto_expire_gate_passes
from icd_tz.tests.utils import create_consignee, create_icd_tz_settings


class TestV16Compatibility(IntegrationTestCase):
	def setUp(self):
		create_icd_tz_settings()

	def tearDown(self):
		frappe.db.rollback()

	def test_auto_expire_gate_passes_runs_on_version_16(self):
		"""The hourly scheduler job must build valid SQL, a list on a "!=" filter does not."""

		auto_expire_gate_passes()

	def test_consignee_without_a_customer_is_picked_up_for_billing(self):
		"""An unset Link is NULL, the create_customer sweep must still see it."""

		consignee = create_consignee("ICD Test Unbilled Consignee")
		self.assertIsNone(frappe.db.get_value("Consignee", consignee, "customer"))

		create_customer()

		self.assertTrue(frappe.db.get_value("Consignee", consignee, "customer"))

	def test_get_value_with_a_single_field_list_returns_a_scalar(self):
		"""version-16 casts a one-field result, callers must not index into it."""

		value = frappe.db.get_value("Consignee", {"name": create_consignee()}, ["name"])
		self.assertIsInstance(value, str)

	def test_ambiguous_lookups_still_return_the_newest_record(self):
		"""version-16 orders db.get_value by creation instead of modified, newest first either way."""

		older = create_consignee("ICD Test Older Consignee")
		newer = create_consignee("ICD Test Newer Consignee")
		frappe.db.set_value("Consignee", older, "consignee_tin", "TIN-1")
		frappe.db.set_value("Consignee", newer, "consignee_tin", "TIN-1")

		self.assertEqual(frappe.db.get_value("Consignee", {"consignee_tin": "TIN-1"}, "name"), newer)
