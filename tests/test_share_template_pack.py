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
