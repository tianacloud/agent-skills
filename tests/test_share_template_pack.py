import importlib.util
import base64
from contextlib import contextmanager
import hashlib
import io
import json
from pathlib import Path
import tempfile
import stat
import subprocess
import sys
import unittest
from unittest.mock import patch
import zipfile

spec = importlib.util.spec_from_file_location("pack_template", Path(__file__).resolve().parents[1] / "skills/tiana-web/scripts/pack-template.py")
pack = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pack)


class SharedTemplatePackTest(unittest.TestCase):
    @contextmanager
    def fixture(self, seeds=None, declaration="template-files"):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            metadata = {"name": "demo", "display_name": "Demo", "description": "Synthetic fixture", "database_required": False}
            if declaration != "absent":
                metadata["file_seeds"] = declaration
            files = {"metadata.json": json.dumps(metadata).encode(), "showcase/preview.html": b"<p>synthetic</p>",
                     "showcase/cover.webp": b"cover", "showcase/prompt.md": b"build demo"}
            files.update({"template-files/" + name: value for name, value in (seeds or {}).items()})
            source = root / "source.zip"
            source.write_bytes(pack.archive(files))
            dist = root / "dist"
            dist.mkdir()
            (dist / "app.js").write_bytes(b"export async function mount(root, { files }) { return () => {}; }")
            yield root, source, dist

    def preflight_report(self, updates, remove=(), files=None):
        with self.fixture(declaration="absent") as (root, source, _):
            snapshot, _, _ = pack.source_files(source.read_bytes())
            metadata = json.loads(snapshot["metadata.json"])
            metadata.update(updates)
            for field in remove:
                metadata.pop(field, None)
            snapshot.update(files or {})
            snapshot["metadata.json"] = json.dumps(metadata).encode()
            source.write_bytes(pack.archive(snapshot))
            output = root / "install.zip"
            output.write_bytes(b"previous package")
            with self.assertRaises(pack.TemplatePreflightError) as caught:
                pack.pack(source, object(), "app.js", output)
            self.assertEqual(output.read_bytes(), b"previous package")
            report = str(caught.exception)
            self.assertIn("Fix:", report)
            self.assertIn("was not written or updated", report)
            self.assertNotIn("SYNTHETIC_PRIVATE_VALUE", report)
            return report

    def test_required_text_fields_fail_before_output(self):
        for field in ("name", "display_name", "description"):
            with self.subTest(field=field, missing=True):
                report = self.preflight_report({}, remove=(field,))
                self.assertIn(f"metadata.json:{field}: missing required field", report)
                self.assertEqual(report.count("[preflight/"), 1)
            for value in (None, False, 1, [], {}, "", "   ", "\ud800"):
                with self.subTest(field=field, value=value):
                    report = self.preflight_report({field: value})
                    self.assertIn(f"metadata.json:{field}:", report)
                    self.assertEqual(report.count("[preflight/"), 1)

    def test_both_boolean_fields_reject_non_booleans(self):
        for field in ("database_required", "private_database"):
            for value in ("false", "true", 0, 1, None, [], {}):
                with self.subTest(field=field, value=value):
                    report = self.preflight_report({field: value})
                    self.assertIn(f"metadata.json:{field}: requires a JSON boolean", report)
                    self.assertEqual(report.count("[preflight/"), 1)

    def test_boolean_values_and_omitted_optional_field_preserve_success(self):
        for required in (False, True):
            for private in ("absent", False, True):
                with self.subTest(required=required, private=private), self.fixture(declaration="absent") as (root, source, dist):
                    snapshot, _, _ = pack.source_files(source.read_bytes())
                    metadata = json.loads(snapshot["metadata.json"])
                    metadata["database_required"] = required
                    metadata.update(variables=[], repositories=[], functions=[], site_variables=[],
                                    custom_extension={"unowned_flag": "false"})
                    if private != "absent":
                        metadata["private_database"] = private
                    snapshot["metadata.json"] = json.dumps(metadata).encode()
                    source.write_bytes(pack.archive(snapshot))
                    target = root / "install.zip"
                    result = pack.pack(source, dist, "app.js", target)
                    self.assertEqual(result["database_required"], required)
                    with zipfile.ZipFile(target) as archive:
                        manifest = json.loads(archive.read("install.json"))
                        self.assertEqual(manifest["metadata"], metadata)
                        self.assertEqual("private_database" in manifest, private != "absent")

    def test_sql_types_missing_files_and_database_conflict(self):
        for field in ("schema", "seeds"):
            for value in (None, False, 1, [], {}, ""):
                with self.subTest(field=field, value=value):
                    report = self.preflight_report({field: value})
                    self.assertIn(f"metadata.json:{field}: requires a nonempty string", report)
                    self.assertEqual(report.count("[preflight/"), 1)
        report = self.preflight_report({"database_required": True,
                                       "schema": "SYNTHETIC_PRIVATE_VALUE/schema.sql",
                                       "seeds": "SYNTHETIC_PRIVATE_VALUE/seed.sql"})
        self.assertEqual(report.count("declared SQL file is missing"), 2)
        self.assertLess(report.index("metadata.json:schema:"), report.index("metadata.json:seeds:"))
        report = self.preflight_report({"schema": "db/schema.sql"}, files={"db/schema.sql": b"CREATE TABLE items(id);"})
        self.assertIn("SQL materials require database_required=true", report)
        self.assertIn("do not remove required SQL", report)

    def test_bad_array_parents_do_not_trigger_child_errors(self):
        for field in ("variables", "repositories", "functions", "site_variables"):
            for value in (None, False, 1, {}, "text", [None], [42]):
                with self.subTest(field=field, value=value):
                    report = self.preflight_report({field: value})
                    self.assertIn(f"metadata.json:{field}", report)
                    self.assertEqual(report.count("[preflight/"), 1)
                    self.assertNotIn(".placeholder", report)
                    self.assertNotIn(".source_dir", report)

    def test_variable_fields_and_declared_file_locations(self):
        base = {"name": "APP_NAME", "description": "App name", "placeholder": "__APP__", "files": ["src/app.js"]}
        for field in ("name", "description", "placeholder", "files"):
            variable = {key: value for key, value in base.items() if key != field}
            with self.subTest(missing=field):
                report = self.preflight_report({"variables": [variable]}, files={"src/app.js": b"__APP__"})
                self.assertIn(f"metadata.json:variables[0].{field}:", report)
                self.assertEqual(report.count("[preflight/"), 1)
        for value in (None, "src/app.js", [], [None], [{}], ["SYNTHETIC_PRIVATE_VALUE.js"]):
            with self.subTest(files=value):
                report = self.preflight_report({"variables": [{**base, "files": value}]})
                self.assertIn("metadata.json:variables[0].files", report)
                self.assertEqual(report.count("[preflight/"), 1)
        report = self.preflight_report({"variables": [base]}, files={"src/app.js": b"no placeholder"})
        self.assertIn("variables[0].files[0]: Source placeholder missing", report)

    def test_repository_shapes_references_and_source_presence(self):
        for repo, location in [({}, "repositories[0].key"),
                               ({"key": [], "path": "."}, "repositories[0].key"),
                               ({"key": "app", "path": []}, "repositories[0].path"),
                               ({"key": "app", "path": "../outside"}, "repositories[0].path"),
                               ({"key": "app", "path": "SYNTHETIC_PRIVATE_VALUE"}, "repositories[0].path"),
                               ({"key": "app", "path": ".", "variables": {}}, "repositories[0].variables")]:
            with self.subTest(location=location, repo=repo):
                report = self.preflight_report({"repositories": [repo]})
                self.assertIn(f"metadata.json:{location}:", report)
        report = self.preflight_report({"web_repository": "SYNTHETIC_PRIVATE_VALUE"})
        self.assertIn("web_repository: references an undeclared repository", report)
        report = self.preflight_report({"repositories": [{"key": "app", "path": "."}] * 2})
        self.assertIn("repositories[1].key: duplicate repository key", report)

    def test_function_fields_and_missing_repository_or_go_source(self):
        base = {"key": "api", "name": "API", "repository": "app", "source_dir": "/"}
        repositories = [{"key": "app", "path": "."}]
        for field in ("key", "name", "repository", "source_dir"):
            for value in (None, 0, [], ""):
                with self.subTest(field=field, value=value):
                    report = self.preflight_report({"repositories": repositories, "functions": [{**base, field: value}]},
                                                   files={"main.go": b"package main"})
                    self.assertIn(f"metadata.json:functions[0].{field}:", report)
                    self.assertEqual(report.count("[preflight/"), 1)
        report = self.preflight_report({"functions": [base]})
        self.assertIn("functions[0].repository: Function repository missing", report)
        report = self.preflight_report({"repositories": repositories, "functions": [base]})
        self.assertIn("functions[0].source_dir: Function entry Go source missing", report)
        report = self.preflight_report({"repositories": repositories, "functions": [base, base]}, files={"main.go": b"package main"})
        self.assertIn("functions[1].key: duplicate function key", report)

    def test_function_database_and_other_object_declarations(self):
        base = {"key": "api", "name": "API", "repository": "app", "source_dir": "/"}
        for field in ("parameters", "cors", "database"):
            report = self.preflight_report({"repositories": [{"key": "app", "path": "."}], "functions": [{**base, field: []}]},
                                           files={"main.go": b"package main"})
            self.assertIn(f"functions[0].{field}: requires an object", report)
        for database, expected in [({}, "endpoint_parameter: missing required field"),
                                   ({"endpoint_parameter": "X", "token_parameter": "X"}, "requires distinct endpoint and token"),
                                   ({"endpoint_parameter": "X", "token_parameter": "Y"}, "requires database_required=true")]:
            report = self.preflight_report({"repositories": [{"key": "app", "path": "."}], "functions": [{**base, "database": database}]},
                                           files={"main.go": b"package main"})
            self.assertIn(expected, report)

    def test_material_declaration_errors_have_actionable_feedback(self):
        for value in (None, True, 1, [], {}, "other", "template-files"):
            with self.subTest(value=value):
                report = self.preflight_report({"file_seeds": value})
                self.assertIn("metadata.json:file_seeds:", report)
                self.assertEqual(report.count("[preflight/"), 1)
        report = self.preflight_report({}, files={"template-files/a.txt": b"asset"})
        self.assertIn("file_seeds: missing declaration", report)

    def test_reports_are_bounded_and_independent_of_metadata_key_order(self):
        for count in (pack.MAX_PREFLIGHT_ISSUES, pack.MAX_PREFLIGHT_ISSUES + 1):
            report = self.preflight_report({"variables": [None] * count})
            self.assertEqual(report.count("[preflight/"), pack.MAX_PREFLIGHT_ISSUES)
            self.assertEqual("More problems found" in report, count > pack.MAX_PREFLIGHT_ISSUES)
        bad = {"name": 1, "private_database": "SYNTHETIC_PRIVATE_VALUE", "schema": []}
        self.assertEqual(self.preflight_report(bad), self.preflight_report(dict(reversed(list(bad.items())))))

    def test_cli_aggregates_extended_errors_without_leaking_or_overwriting(self):
        with self.fixture(declaration="absent") as (root, source, _):
            snapshot, _, _ = pack.source_files(source.read_bytes())
            metadata = json.loads(snapshot["metadata.json"])
            del metadata["name"]
            metadata.update(database_required=True, private_database="SYNTHETIC_PRIVATE_VALUE", schema="SYNTHETIC_PRIVATE_VALUE.sql")
            snapshot["metadata.json"] = json.dumps(metadata).encode()
            del snapshot["showcase/cover.webp"]
            source.write_bytes(pack.archive(snapshot))
            output = root / "install.zip"
            for existing in (False, True):
                if existing:
                    output.write_bytes(b"previous package")
                result = subprocess.run([sys.executable, "-B", str(spec.origin), "--source", str(source),
                                         "--dist", str(root / "does-not-exist"), "--entry", "app.js", "--output", str(output)],
                                        capture_output=True, text=True, check=False)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertEqual(result.stderr.count("[preflight/"), 4)
                self.assertNotIn("Traceback", result.stderr)
                self.assertNotIn("SYNTHETIC_PRIVATE_VALUE", result.stderr)
                locations = ["metadata.json:name:", "metadata.json:private_database:", "metadata.json:schema:", "showcase/cover.webp:"]
                offsets = [result.stderr.index(location) for location in locations]
                self.assertEqual(offsets, sorted(offsets))
                if existing:
                    self.assertEqual(output.read_bytes(), b"previous package")
                else:
                    self.assertFalse(output.exists())

    def test_preflight_collects_independent_errors_without_touching_dist_or_output(self):
        for value in ("SYNTHETIC_PRIVATE_VALUE", None, 0):
            with self.subTest(value=value), self.fixture(declaration="absent") as (root, source, _):
                snapshot, _, _ = pack.source_files(source.read_bytes())
                metadata = json.loads(snapshot["metadata.json"])
                metadata.update(database_required=value, schema="schema.sql")
                snapshot["metadata.json"] = json.dumps(metadata).encode()
                snapshot["schema.sql"] = b"CREATE TABLE items(id);"
                del snapshot["showcase/cover.webp"], snapshot["showcase/prompt.md"]
                source.write_bytes(pack.archive(snapshot))
                output = root / "install.zip"
                output.write_bytes(b"previous package")
                # Path(object()) would fail if the packer reached the build input.
                with self.assertRaises(pack.TemplatePreflightError) as caught:
                    pack.pack(source, object(), "app.js", output)
                report = str(caught.exception)
                self.assertEqual(report.count("[preflight/"), 3)
                self.assertLess(report.index("database_required"), report.index("showcase/cover.webp"))
                self.assertLess(report.index("showcase/cover.webp"), report.index("showcase/prompt.md"))
                self.assertIn("Declared schema/seeds require true", report)
                self.assertIn("do not remove required SQL", report)
                self.assertNotIn("SYNTHETIC_PRIVATE_VALUE", report)
                self.assertIn("was not written or updated", report)
                self.assertEqual(output.read_bytes(), b"previous package")

    def test_preflight_cli_reports_metadata_failures_once_without_leaking_values(self):
        for raw in (None, b" " * (pack.MIB + 1), b"\xff", b'{"SYNTHETIC_PRIVATE_VALUE":',
                    b'{"SYNTHETIC_PRIVATE_VALUE":1,"SYNTHETIC_PRIVATE_VALUE":2}', b"[]", b"null"):
            with self.subTest(raw_size=None if raw is None else len(raw)), self.fixture(declaration="absent") as (root, source, _):
                source.write_bytes(pack.archive({} if raw is None else {"metadata.json": raw}))
                output = root / "install.zip"
                output.write_bytes(b"previous package")
                result = subprocess.run([sys.executable, "-B", str(spec.origin), "--source", str(source),
                                         "--dist", str(root / "does-not-exist"), "--entry", "app.js",
                                         "--output", str(output)], capture_output=True, text=True, check=False)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertEqual(result.stderr.count("[preflight/metadata]"), 1)
                self.assertNotIn("Traceback", result.stderr)
                self.assertNotIn("SYNTHETIC_PRIVATE_VALUE", result.stderr)
                self.assertIn("Fix:", result.stderr)
                self.assertEqual(output.read_bytes(), b"previous package")

    def test_preflight_cli_lists_material_errors_and_does_not_create_output(self):
        with self.fixture(declaration="absent") as (root, source, dist):
            source.write_bytes(pack.archive({"metadata.json": b'{"name":"demo","display_name":"Demo","description":"Synthetic","database_required":"false"}',
                                            "showcase/preview.html": b"preview"}))
            output = root / "install.zip"
            result = subprocess.run([sys.executable, "-B", str(spec.origin), "--source", str(source),
                                     "--dist", str(dist), "--entry", "app.js", "--output", str(output)],
                                    capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertEqual(result.stderr.count("[preflight/"), 3)
            self.assertNotIn("Traceback", result.stderr)
            self.assertIn("not publishing approval", result.stderr)
            self.assertFalse(output.exists())

    def test_source_safety_still_precedes_preflight(self):
        for data in (b"not a ZIP", pack.archive({"../unsafe": b"file"})):
            with self.subTest(data_size=len(data)), self.fixture(declaration="absent") as (root, source, _):
                source.write_bytes(data)
                with patch.object(pack, "preflight") as preflight:
                    with self.assertRaises(ValueError):
                        pack.pack(source, object(), "app.js", root / "install.zip")
                    preflight.assert_not_called()
                self.assertFalse((root / "install.zip").exists())

    def test_preflight_preview_limit_and_combined_showcase_errors(self):
        with self.fixture(declaration="absent") as (root, source, dist):
            snapshot, _, _ = pack.source_files(source.read_bytes())
            snapshot["showcase/preview.html"] = b" " * 500_000
            source.write_bytes(pack.archive(snapshot))
            pack.pack(source, dist, "app.js", root / "allowed.zip")
            snapshot["showcase/preview.html"] += b" "
            del snapshot["showcase/cover.webp"], snapshot["showcase/prompt.md"]
            snapshot["metadata.json"] = b'{"name":"demo","display_name":"Demo","description":"Synthetic"}'
            source.write_bytes(pack.archive(snapshot))
            with self.assertRaises(pack.TemplatePreflightError) as caught:
                pack.pack(source, object(), "app.js", root / "rejected.zip")
            self.assertEqual(str(caught.exception).count("[preflight/"), 4)
            self.assertIn("exceeds 500,000 bytes", str(caught.exception))
            self.assertFalse((root / "rejected.zip").exists())

    def test_preflight_keeps_without_source_and_empty_material_semantics(self):
        with self.fixture(declaration="absent") as (root, source, dist):
            snapshot, _, _ = pack.source_files(source.read_bytes())
            del snapshot["showcase/prompt.md"]
            snapshot["showcase/preview.html"] = snapshot["showcase/cover.webp"] = b""
            source.write_bytes(pack.archive(snapshot))
            result = pack.pack(source, dist, "app.js", root / "allowed.zip", True)
            self.assertFalse(result["has_source"])
            with self.assertRaisesRegex(pack.TemplatePreflightError, "showcase/prompt.md: missing"):
                pack.pack(source, object(), "app.js", root / "rejected.zip")
            self.assertFalse((root / "rejected.zip").exists())

    def test_fixing_showcase_does_not_skip_seed_path_rejection(self):
        with self.fixture({"%2e%2e/a": b"asset"}) as (root, source, _):
            snapshot, _, _ = pack.source_files(source.read_bytes())
            cover = snapshot.pop("showcase/cover.webp")
            source.write_bytes(pack.archive(snapshot))
            output = root / "install.zip"
            with self.assertRaisesRegex(pack.TemplatePreflightError, "showcase/cover.webp: missing"):
                pack.pack(source, object(), "app.js", output)
            self.assertFalse(output.exists())
            snapshot["showcase/cover.webp"] = cover
            source.write_bytes(pack.archive(snapshot))
            with self.assertRaisesRegex(ValueError, "Invalid template file path"):
                pack.pack(source, object(), "app.js", output)
            self.assertFalse(output.exists())

    def test_source_choice_preserves_installation_and_sql_mapping(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            metadata = {"name": "demo", "display_name": "Demo", "description": "Synthetic SQL fixture", "database_required": True, "schema": "db/schema.sql", "seeds": "db/seed.sql", "variables": [{"name": "APP_NAME", "description": "App name", "placeholder": "__APP__", "files": ["db/seed.sql", "src/app.js"]}]}
            source = root / "source.zip"
            source.write_bytes(pack.archive({"metadata.json": json.dumps(metadata).encode(), "showcase/preview.html": b"<p>synthetic demo</p>", "showcase/cover.webp": b"cover", "showcase/prompt.md": b"build demo", "db/schema.sql": b"CREATE TABLE items(name TEXT);", "db/seed.sql": b"INSERT INTO items VALUES('__APP__');", "src/app.js": b"source __APP__"}))
            dist = root / "dist"
            dist.mkdir()
            (dist / "app.js").write_text("built demo")
            for without_source in (False, True):
                target = root / "install.zip"
                result = pack.pack(source, dist, "app.js", target, without_source)
                with zipfile.ZipFile(target) as archive:
                    self.assertEqual("source.zip" in archive.namelist(), not without_source)
                    self.assertEqual("showcase/prompt.md" in archive.namelist(), not without_source)
                    manifest = json.loads(archive.read("install.json"))
                    for field in ("format_version", "requires", "files"):
                        self.assertNotIn(field, manifest)
                    self.assertFalse(any(name.startswith("files/") for name in archive.namelist()))
                    self.assertTrue(manifest["database_required"])
                    self.assertEqual(manifest["variables"][0]["files"], ["seed.sql"])
                    self.assertIn("site.tweb", archive.namelist())
                self.assertEqual(result["has_source"], not without_source)

    def test_backend_shared_repository_and_compiled_reference(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            variable = {"name": "FUNCTION_ID:api", "placeholder": "__API__", "description": "Backend", "files": ["app.js"]}
            metadata = {"name": "backend", "display_name": "Backend", "description": "Synthetic backend", "database_required": True, "private_database": True,
                        "web_repository": "app", "repositories": [{"key": "app", "path": "repositories/app", "variables": [variable]}],
                        "functions": [{"key": "api", "name": "API", "repository": "app", "source_dir": "/functions/fn-old", "database": {"endpoint_parameter": "SQLITE_ENDPOINT", "token_parameter": "SQLITE_TOKEN"}}],
                        "site_variables": [variable]}
            source = root / "source.zip"
            source.write_bytes(pack.archive({"metadata.json": json.dumps(metadata).encode(), "showcase/preview.html": b"preview", "showcase/cover.webp": b"cover", "showcase/prompt.md": b"prompt", "repositories/app/app.js": b"call('__API__')", "repositories/app/go.mod": b"module service\n\ngo 1.26\n", "repositories/app/functions/fn-old/main.go": b"package main"}))
            dist = root / "dist"
            dist.mkdir()
            (dist / "app.js").write_text("call('__API__')")
            target = root / "install.zip"
            pack.pack(source, dist, "app.js", target)
            with zipfile.ZipFile(target) as archive:
                manifest = json.loads(archive.read("install.json"))
                for key in ("private_database", "web_repository", "repositories", "functions", "site_variables"):
                    self.assertEqual(manifest[key], metadata[key])
                self.assertEqual(archive.read("source.zip"), source.read_bytes())
            with self.assertRaisesRegex(ValueError, "require source"):
                pack.pack(source, dist, "app.js", target, True)
            (dist / "app.js").write_text("call('old-real-function-id')")
            with self.assertRaisesRegex(ValueError, "placeholder missing"):
                pack.pack(source, dist, "app.js", target)

    def test_backend_file_materials_keep_both_validation_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            variable = {"name": "FUNCTION_ID:api", "placeholder": "__API__", "description": "Backend", "files": ["app.js"]}
            metadata = {"name": "backend-files", "display_name": "Backend files", "description": "Synthetic backend and files", "database_required": True, "private_database": True,
                        "file_seeds": "template-files", "web_repository": "app",
                        "repositories": [{"key": "app", "path": "repositories/app", "variables": [variable]}],
                        "functions": [{"key": "api", "name": "API", "repository": "app", "source_dir": "/functions/api"}],
                        "site_variables": [variable]}
            material = b"reviewed external backend guide\n" * 100
            snapshot = {"metadata.json": json.dumps(metadata).encode(),
                        "showcase/preview.html": b"preview", "showcase/cover.webp": b"cover", "showcase/prompt.md": b"prompt",
                        "repositories/app/app.js": b"call('__API__')", "repositories/app/go.mod": b"module service\n\ngo 1.26\n",
                        "repositories/app/functions/api/main.go": b"package main",
                        "template-files/docs/guide.txt": material}
            source = root / "source.zip"
            source.write_bytes(pack.archive(snapshot))
            dist = root / "dist"
            dist.mkdir()
            (dist / "app.js").write_bytes(b"call('__API__')")
            target = root / "install.zip"
            result = pack.pack(source, dist, "app.js", target)
            with zipfile.ZipFile(target) as archive:
                manifest = json.loads(archive.read("install.json"))
                self.assertEqual(manifest["format_version"], 2)
                self.assertEqual(manifest["requires"], ["template_files_v1"])
                for field in ("private_database", "web_repository", "repositories", "functions", "site_variables"):
                    self.assertEqual(manifest[field], metadata[field])
                self.assertEqual(archive.read("source.zip"), source.read_bytes())
                self.assertEqual(archive.read("files/docs/guide.txt"), material)
                self.assertEqual(manifest["files"]["entries"][0]["sha256"], hashlib.sha256(material).hexdigest())
                self.assertEqual(result["file_bytes"], len(material))
                with zipfile.ZipFile(io.BytesIO(archive.read("site.tweb"))) as site:
                    self.assertEqual(set(site.namelist()), {"web.yaml", "data/app.js"})

            rejected = root / "rejected.zip"
            with self.assertRaisesRegex(ValueError, "Function templates require source.zip"):
                pack.pack(source, dist, "app.js", rejected, True)
            snapshot.pop("repositories/app/functions/api/main.go")
            source.write_bytes(pack.archive(snapshot))
            with self.assertRaisesRegex(ValueError, "Function entry Go source missing"):
                pack.pack(source, dist, "app.js", rejected)
            snapshot["repositories/app/functions/api/main.go"] = b"package main"
            source.write_bytes(pack.archive(snapshot))
            (dist / "app.js").write_bytes(b"call('missing-placeholder')")
            with self.assertRaisesRegex(ValueError, "Built site placeholder missing"):
                pack.pack(source, dist, "app.js", rejected)
            (dist / "app.js").write_bytes(b"call('__API__'); // " + base64.b64encode(material))
            with self.assertRaisesRegex(ValueError, "External template file embedded"):
                pack.pack(source, dist, "app.js", rejected)
            self.assertFalse(rejected.exists())

    def test_source_rejects_traversal_and_expansion_bomb(self):
        for name, data in (("../secret", b"private"), (".git/config", b"credential"), ("large", b"a" * (pack.MAX_FILE + 1))):
            with self.subTest(name=name), self.assertRaises(ValueError):
                pack.source_files(pack.archive({name: data}))

    def test_duplicate_entries_are_not_ambiguous(self):
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w") as archive:
            archive.writestr("dir/", b"")
            archive.writestr("dir", b"file")
        with self.assertRaises(ValueError):
            pack.source_files(out.getvalue())

    def test_file_materials_match_snapshot_bytes_and_require_the_verification_source(self):
        seeds = {"文档/指南.txt": "素材\n".encode(), "images/cover.WEBP": bytes(range(256)) * 100, "Z.bin": b"\x00\x01"}
        for without_source in (False, True):
            with self.subTest(without_source=without_source), self.fixture(seeds) as (root, source, dist):
                # A dirty working copy beside the reviewed archive is not an input.
                (root / "template-files").mkdir()
                (root / "template-files/Z.bin").write_bytes(b"unreviewed working bytes")
                target = root / "install.zip"
                if without_source:
                    with self.assertRaisesRegex(ValueError, "require source.zip"):
                        pack.pack(source, dist, "app.js", target, without_source)
                    self.assertFalse(target.exists())
                    continue
                result = pack.pack(source, dist, "app.js", target, without_source)
                with zipfile.ZipFile(target) as archive:
                    raw = archive.read("install.json")
                    manifest = json.loads(raw)
                    self.assertEqual(manifest["format_version"], 2)
                    self.assertEqual(manifest["requires"], ["template_files_v1"])
                    self.assertEqual(manifest["files"]["version"], 1)
                    self.assertEqual(manifest["files"]["root"], "template-assets/")
                    entries = manifest["files"]["entries"]
                    self.assertEqual([item["path"] for item in entries], sorted(seeds, key=lambda value: value.encode()))
                    self.assertEqual([item["content_type"] for item in entries], ["application/octet-stream", "image/webp", "text/plain"])
                    for item in entries:
                        self.assertEqual(archive.read("files/" + item["path"]), seeds[item["path"]])
                        self.assertEqual(item["size"], len(seeds[item["path"]]))
                        self.assertEqual(item["sha256"], hashlib.sha256(seeds[item["path"]]).hexdigest())
                    raw_files = raw[raw.rindex(b'"files":') + 8:raw.rindex(b"}")]
                    self.assertEqual(result["file_manifest_sha256"], hashlib.sha256(raw_files).hexdigest())
                    self.assertIn("文档".encode(), raw_files)
                    self.assertEqual(result["file_count"], len(seeds))
                    self.assertEqual(result["file_bytes"], sum(map(len, seeds.values())))
                    self.assertEqual("source.zip" in archive.namelist(), not without_source)
                    if not without_source:
                        with zipfile.ZipFile(io.BytesIO(archive.read("source.zip"))) as original:
                            for name, value in seeds.items():
                                self.assertEqual(original.read("template-files/" + name), value)
                    with zipfile.ZipFile(io.BytesIO(archive.read("site.tweb"))) as site:
                        self.assertEqual(set(site.namelist()), {"web.yaml", "data/app.js"})

    def test_file_declaration_presence_and_empty_directory_fail_before_output(self):
        for declaration, seeds in [("absent", {"a.txt": b"a"}), (None, {"a.txt": b"a"}),
                                   (False, {"a.txt": b"a"}), ("", {"a.txt": b"a"}),
                                   ("other", {"a.txt": b"a"}), ("template-files", {})]:
            for without_source in (False, True):
                with self.subTest(declaration=declaration, without_source=without_source), self.fixture(seeds, declaration) as (root, source, dist):
                    target = root / "install.zip"
                    with self.assertRaises(ValueError):
                        pack.pack(source, dist, "app.js", target, without_source)
                    self.assertFalse(target.exists())

    def test_invalid_seed_paths_never_become_materials(self):
        for name in ("/absolute", "../outside", "a/../b", "a/./b", "a//b", "a/", "a\\b",
                     "%2e%2e/a", "a%2fb", "%252e/a", "bad%", "a\x01b", "a\x7fb", "a\x85b", "a" * 1025):
            with self.subTest(name=name), self.fixture({name: b"asset"}) as (root, source, dist):
                with self.assertRaises(ValueError):
                    pack.pack(source, dist, "app.js", root / "install.zip")

    def test_seed_count_and_actual_aggregate_size_bounds(self):
        metadata = {"file_seeds": "template-files"}
        allowed = {f"template-files/{index}.txt": b"" for index in range(256)}
        self.assertEqual(len(pack.template_file_materials(allowed, metadata)["materials"]), 256)
        with self.assertRaises(ValueError):
            pack.template_file_materials({**allowed, "template-files/extra.txt": b""}, metadata)
        allowed = {"template-files/a.bin": b"a" * (8 << 20), "template-files/b.bin": b"b" * (8 << 20)}
        self.assertEqual(pack.template_file_materials(allowed, metadata)["bytes"], 16 << 20)
        with self.assertRaises(ValueError):
            pack.template_file_materials({**allowed, "template-files/c.bin": b"c"}, metadata)
        with self.assertRaises(ValueError):
            pack.template_file_materials({"template-files/large.bin": b"a" * ((16 << 20) + 1)}, metadata)

    def test_external_material_cannot_be_copied_or_embedded_in_build(self):
        content = b"reviewed external material\n" * 1024
        for kind in ("reserved_directory", "reserved_empty_directory", "renamed_copy", "raw_js", "base64_js"):
            with self.subTest(kind=kind), self.fixture({"documents/guide.txt": content}) as (root, source, dist):
                if kind == "reserved_directory":
                    (dist / "template-files").mkdir()
                    (dist / "template-files/guide.txt").write_bytes(b"different")
                elif kind == "reserved_empty_directory":
                    (dist / "template-assets").mkdir()
                elif kind == "renamed_copy":
                    (dist / "unexpected.txt").write_bytes(content)
                elif kind == "raw_js":
                    (dist / "app.js").write_bytes(b"export const data = `" + content + b"`;")
                else:
                    (dist / "app.js").write_bytes(b'export const data = "' + base64.b64encode(content) + b'";')
                with self.assertRaisesRegex(ValueError, "External template file"):
                    pack.pack(source, dist, "app.js", root / "install.zip")

    def test_required_platform_icon_remains_a_separate_allowed_material(self):
        content = b"synthetic platform icon bytes" * 100
        with self.fixture({"images/cover.png": content}) as (root, source, dist):
            (dist / "icon.png").write_bytes(content)
            target = root / "install.zip"
            pack.pack(source, dist, "app.js", target)
            with zipfile.ZipFile(target) as archive:
                self.assertEqual(archive.read("icon.png"), content)
                self.assertEqual(archive.read("files/images/cover.png"), content)

    def test_source_rejects_ancestor_collisions_special_files_and_type_disagreement(self):
        raw = pack.archive({"template-files/AXB": b"asset"}).replace(b"AXB", b"A\0B")
        with self.assertRaises(ValueError):
            pack.source_files(raw)
        for entries in [[("a", b"file"), ("a/b", b"child")], [("a/b", b"child"), ("a", b"file")]]:
            with self.subTest(entries=[name for name, _ in entries]), self.assertRaises(ValueError):
                pack.source_files(pack.archive(dict(entries)))
        for name, mode, content in [("template-files/a", stat.S_IFLNK | 0o777, b"../outside"),
                                    ("template-files/a", stat.S_IFIFO | 0o600, b""),
                                    ("template-files/a/", stat.S_IFREG | 0o600, b""),
                                    ("template-files/a", stat.S_IFDIR | 0o700, b""),
                                    ("template-files/a/", stat.S_IFDIR | 0o700, b"directory bytes")]:
            output = io.BytesIO()
            with zipfile.ZipFile(output, "w") as archive:
                item = zipfile.ZipInfo(name)
                item.external_attr = mode << 16
                archive.writestr(item, content)
            with self.subTest(name=name, mode=mode), self.assertRaises(ValueError):
                pack.source_files(output.getvalue())

    def test_manifest_digest_matches_the_shared_server_and_node_vector(self):
        raw = b'{"version":1,"root":"template-assets/","entries":[{"path":"a.txt","size":1,"sha256":"ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb","content_type":"text/plain"}]}'
        encoded, digest = pack.encode_install_manifest({}, {"manifest": json.loads(raw)})
        self.assertIn(b'"files":' + raw, encoded)
        self.assertEqual(digest, "57712187d2dd348f35fab47c89a5455d96c5e0e3d7fa258ca6a7221c2acdf929")


if __name__ == "__main__":
    unittest.main()
