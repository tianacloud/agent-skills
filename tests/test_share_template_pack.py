import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location("pack_template", Path(__file__).resolve().parents[1] / "skills/tiana-web/scripts/pack-template.py")
pack = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pack)


class SharedTemplatePackTest(unittest.TestCase):
    def test_source_choice_preserves_installation_and_sql_mapping(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            metadata = {"name": "demo", "database_required": True, "schema": "db/schema.sql", "seeds": "db/seed.sql", "variables": [{"name": "APP_NAME", "placeholder": "__APP__", "files": ["db/seed.sql", "src/app.js"]}]}
            source = root / "source.zip"
            source.write_bytes(pack.archive({"metadata.json": json.dumps(metadata).encode(), "showcase/preview.html": b"<p>synthetic demo</p>", "showcase/cover.webp": b"cover", "showcase/prompt.md": b"build demo", "db/schema.sql": b"CREATE TABLE items(name TEXT);", "db/seed.sql": b"INSERT INTO items VALUES('__APP__');", "src/app.js": b"source"}))
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
                    self.assertTrue(manifest["database_required"])
                    self.assertEqual(manifest["variables"][0]["files"], ["seed.sql"])
                    self.assertIn("site.tweb", archive.namelist())
                self.assertEqual(result["has_source"], not without_source)

    def test_backend_shared_repository_and_compiled_reference(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            variable = {"name": "FUNCTION_ID:api", "placeholder": "__API__", "description": "Backend", "files": ["app.js"]}
            metadata = {"name": "backend", "database_required": True, "private_database": True,
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


if __name__ == "__main__":
    unittest.main()
