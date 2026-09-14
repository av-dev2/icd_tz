# Copyright (c) 2026, elius mgani and contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from icd_tz.icd_tz.doctype.edi_partner.edi_partner import get_partner

test_ignore = ["Company", "Cost Center"]


class TestEDIPartner(IntegrationTestCase):
	def setUp(self):
		frappe.db.set_single_value("ICD TZ Settings", "enable_edi", 1)
		frappe.db.set_single_value("ICD TZ Settings", "default_sender_id", "TZDARDSEL")
		self.partner = make_partner("TCM", enable_edi=1)

	def tearDown(self):
		frappe.db.rollback()

	def test_code_is_uppercased_and_names_the_record(self):
		partner = make_partner(" tlo ")

		self.assertEqual(partner.shipping_line_code, "TLO")
		self.assertEqual(partner.name, "TLO")

	def test_duplicate_code_is_rejected(self):
		with self.assertRaises(frappe.DuplicateEntryError):
			make_partner("TCM")

	def test_sender_falls_back_to_the_settings_default(self):
		self.assertEqual(self.partner.sender, "TZDARDSEL")

		self.partner.sender_id = "OWNCODE"
		self.assertEqual(self.partner.sender, "OWNCODE")

	def test_partner_is_found_for_its_code(self):
		self.assertEqual(get_partner("TCM").name, "TCM")

	def test_lookup_ignores_case_and_padding(self):
		self.assertEqual(get_partner("  tcm ").name, "TCM")

	def test_no_partner_when_code_is_missing(self):
		self.assertIsNone(get_partner(None))
		self.assertIsNone(get_partner(""))

	def test_no_partner_when_the_line_is_not_configured(self):
		self.assertIsNone(get_partner("NOSUCH"))

	def test_no_partner_when_the_line_is_disabled(self):
		self.partner.db_set("enable_edi", 0)

		self.assertIsNone(get_partner("TCM"))

	def test_no_partner_when_the_master_switch_is_off(self):
		frappe.db.set_single_value("ICD TZ Settings", "enable_edi", 0)

		self.assertIsNone(get_partner("TCM"))


def make_partner(shipping_line_code, **values):
	partner = frappe.get_doc(
		{
			"doctype": "EDI Partner",
			"shipping_line_code": shipping_line_code,
			"shipping_line_name": f"{shipping_line_code} LIMITED",
			"connection_type": "SMTP",
			"receiver_email": "edi@example.com",
			**values,
		}
	)
	partner.insert(ignore_permissions=True)

	return partner
