# Copyright (c) 2024, elius mgani and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from icd_tz.tests.utils import create_cf_company, create_clearing_agent


class TestClearingAgent(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_an_agent_is_named_after_itself(self):
		self.assertEqual(create_clearing_agent("ICD Test Named Agent"), "ICD Test Named Agent")

	def test_an_agent_belongs_to_its_company(self):
		company = create_cf_company("ICD Test Agent Company")
		agent = create_clearing_agent("ICD Test Company Agent", company)

		self.assertEqual(frappe.db.get_value("Clearing Agent", agent, "c_and_f_company"), company)

	def test_an_agent_without_a_company_is_rejected(self):
		agent = frappe.get_doc(
			{"doctype": "Clearing Agent", "agent_name": "ICD Test Orphan Agent", "tafer_id": "T-1"}
		)
		self.assertRaises(frappe.MandatoryError, agent.insert)
