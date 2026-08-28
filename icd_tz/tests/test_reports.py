"""Every script report must build valid version-16 SQL and return its columns."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from icd_tz.tests.utils import create_container, create_icd_tz_settings

REPORTS = (
	"Container Booking",
	"Container Status Flow",
	"Current Container Stock",
	"Daily Stripped Containers",
	"Exited Containers",
	"Gate Out Pass",
	"Loose Cargo Tracking",
	"Received Containers",
	"Revenue Summary",
)


class TestReports(IntegrationTestCase):
	def setUp(self):
		create_icd_tz_settings()
		self.filters = {
			"from_date": add_days(nowdate(), -30),
			"to_date": nowdate(),
			"company": frappe.defaults.get_user_default("Company"),
		}

	def tearDown(self):
		frappe.db.rollback()

	def test_every_report_runs_and_returns_columns(self):
		create_container()

		for report_name in REPORTS:
			with self.subTest(report=report_name):
				columns, data = frappe.get_attr(get_execute_path(report_name))(self.filters)[:2]
				self.assertTrue(columns)
				self.assertIsInstance(data, list)

	def test_container_booking_rejects_an_inverted_date_range(self):
		execute = frappe.get_attr(get_execute_path("Container Booking"))
		filters = dict(self.filters, from_date=nowdate(), to_date=add_days(nowdate(), -1))

		self.assertRaises(frappe.ValidationError, execute, filters)

	def test_container_booking_rejects_a_missing_date_range(self):
		execute = frappe.get_attr(get_execute_path("Container Booking"))
		self.assertRaises(frappe.ValidationError, execute, {})


def get_execute_path(report_name):
	module_name = frappe.scrub(report_name)
	return f"icd_tz.icd_tz.report.{module_name}.{module_name}.execute"
