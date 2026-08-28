"""The app metadata must load on version-16: hooks, patches, workflows and DocType links."""

import json
from pathlib import Path

import frappe
import yaml
from frappe.tests import IntegrationTestCase

import icd_tz

APP_PATH = Path(icd_tz.__file__).parent
REPO_PATH = APP_PATH.parent


class TestAppConfiguration(IntegrationTestCase):
	def test_every_doctype_js_hook_points_at_a_real_file(self):
		for hook in ("doctype_js", "doctype_list_js"):
			for doctype, paths in (frappe.get_hooks(hook, app_name="icd_tz") or {}).items():
				for path in paths if isinstance(paths, list) else [paths]:
					with self.subTest(hook=hook, doctype=doctype, path=path):
						self.assertTrue(Path(frappe.get_app_path("icd_tz", path)).is_file())

	def test_scheduler_cron_keys_are_lowercase(self):
		scheduler_events = frappe.get_hooks("scheduler_events", app_name="icd_tz")
		self.assertIn("cron", scheduler_events)

	def test_every_scheduled_method_is_importable(self):
		for event, handlers in frappe.get_hooks("scheduler_events", app_name="icd_tz").items():
			methods = handlers if isinstance(handlers, list) else [m for v in handlers.values() for m in v]
			for method in methods:
				with self.subTest(event=event, method=method):
					self.assertTrue(callable(frappe.get_attr(method)))

	def test_every_document_event_handler_is_importable(self):
		for doctype, events in frappe.get_hooks("doc_events", app_name="icd_tz").items():
			for event, handlers in events.items():
				for handler in (
					frappe.utils.cstr(handlers).split(",") if isinstance(handlers, str) else handlers
				):
					with self.subTest(doctype=doctype, event=event):
						self.assertTrue(callable(frappe.get_attr(handler)))

	def test_every_install_and_migrate_hook_is_importable(self):
		for hook in ("before_install", "after_install", "after_migrate"):
			handlers = frappe.get_hooks(hook, app_name="icd_tz") or []
			for handler in handlers:
				with self.subTest(hook=hook, handler=handler):
					self.assertTrue(callable(frappe.get_attr(handler)))

	def test_every_patch_is_importable(self):
		patches = (APP_PATH / "patches.txt").read_text().splitlines()
		for patch in patches:
			patch = patch.split("#")[0].strip()
			if not patch or patch.startswith("["):
				continue

			with self.subTest(patch=patch):
				self.assertTrue(frappe.get_module(patch.split()[0]))

	def test_every_link_field_points_at_an_installed_doctype(self):
		for path in (APP_PATH / "icd_tz" / "doctype").glob("*/*.json"):
			definition = json.loads(path.read_text())
			if definition.get("doctype") != "DocType":
				continue

			for field in definition.get("fields", []):
				if field.get("fieldtype") not in ("Link", "Table", "Table MultiSelect"):
					continue

				with self.subTest(doctype=definition["name"], field=field["fieldname"]):
					self.assertTrue(frappe.db.exists("DocType", field["options"]))

	def test_every_workflow_yaml_parses(self):
		for path in REPO_PATH.glob(".github/workflows/*.y*ml"):
			with self.subTest(workflow=path.name):
				self.assertTrue(yaml.safe_load(path.read_text()))

	def test_the_pre_commit_configuration_parses(self):
		self.assertTrue(yaml.safe_load((REPO_PATH / ".pre-commit-config.yaml").read_text()))

	def test_the_app_requires_a_version_16_python(self):
		"""version-16 needs Python 3.14, the packaging metadata must not claim less."""

		import tomllib

		pyproject = tomllib.loads((REPO_PATH / "pyproject.toml").read_text())
		self.assertEqual(pyproject["project"]["requires-python"], ">=3.14")

	def test_the_app_declares_its_version_16_dependencies(self):
		import tomllib

		pyproject = tomllib.loads((REPO_PATH / "pyproject.toml").read_text())
		dependencies = pyproject["tool"]["bench"]["frappe-dependencies"]

		self.assertEqual(dependencies["frappe"], ">=16.0.0,<17.0.0")
		self.assertEqual(dependencies["erpnext"], ">=16.0.0,<17.0.0")
