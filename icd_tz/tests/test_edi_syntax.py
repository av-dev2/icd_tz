# Copyright (c) 2026, elius mgani and Contributors
# See license.txt

from datetime import datetime

from frappe.tests import IntegrationTestCase

from icd_tz.icd_tz.api.edi.syntax import edifact_datetime, segment, text, whole_number


class TestEDISyntax(IntegrationTestCase):
	def test_lowercase_is_raised_to_the_level_a_repertoire(self):
		self.assertEqual(text("GTK Limited"), "GTK LIMITED")

	def test_characters_outside_level_a_are_dropped(self):
		self.assertEqual(text("KO@TA#NABIL_1"), "KOTANABIL1")

	def test_service_characters_are_released_so_they_cannot_break_the_segment(self):
		self.assertEqual(text("A&B+CO:LTD'X"), "A&B?+CO?:LTD?'X")

	def test_the_release_character_itself_is_released(self):
		self.assertEqual(text("WHY?"), "WHY??")

	def test_value_is_cut_to_the_element_length(self):
		self.assertEqual(text("ABCDEFGHIJ", 4), "ABCD")

	def test_empty_input_gives_an_empty_value(self):
		self.assertEqual(text(None), "")
		self.assertEqual(text(""), "")

	def test_segment_joins_elements_and_components(self):
		self.assertEqual(segment("EQD", "CN", "MSKU1", ["45G1", "102", "5"]), "EQD+CN+MSKU1+45G1:102:5'")

	def test_trailing_empty_elements_are_dropped_but_inner_ones_are_kept(self):
		self.assertEqual(segment("TDT", "20", "", "1", "", ""), "TDT+20++1'")

	def test_trailing_empty_components_are_dropped(self):
		self.assertEqual(segment("LOC", "165", ["TZDAR", "139", ""]), "LOC+165+TZDAR:139'")

	def test_datetime_formats(self):
		moment = datetime(2026, 3, 3, 22, 55, 8)

		self.assertEqual(edifact_datetime(moment, "102"), "20260303")
		self.assertEqual(edifact_datetime(moment, "203"), "202603032255")
		self.assertEqual(edifact_datetime(moment, "204"), "20260303225508")

	def test_datetime_accepts_a_string(self):
		self.assertEqual(edifact_datetime("2026-03-03 22:55:08", "203"), "202603032255")

	def test_missing_datetime_gives_an_empty_value(self):
		self.assertEqual(edifact_datetime(None), "")

	def test_weight_is_rounded_to_a_whole_number(self):
		self.assertEqual(whole_number(2200), "2200")
		self.assertEqual(whole_number("25129.4"), "25129")
		self.assertEqual(whole_number(25129.6), "25130")

	def test_missing_weight_gives_an_empty_value(self):
		self.assertEqual(whole_number(None), "")
		self.assertEqual(whole_number(""), "")
