#!/usr/bin/env python3
"""Package a reviewed source snapshot and its clean build as an installable template."""
import argparse
import base64
import hashlib
import io
import json
import stat
import struct
from pathlib import Path, PurePosixPath
import zipfile

MIB = 1 << 20
MAX_FILE = 16 * MIB
MAX_EXPANDED = 128 * MIB
MAX_ENTRIES = 5000
MAX_FILE_SEEDS = 256
MAX_PREFLIGHT_ISSUES = 20
FILE_TYPES = {
    ".webp": "image/webp", ".png": "image/png", ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg", ".gif": "image/gif", ".svg": "image/svg+xml",
    ".avif": "image/avif", ".pdf": "application/pdf", ".txt": "text/plain",
    ".json": "application/json", ".csv": "text/csv", ".md": "text/markdown",
    ".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg",
    ".mp4": "video/mp4", ".webm": "video/webm", ".woff": "font/woff",
    ".woff2": "font/woff2", ".ttf": "font/ttf", ".otf": "font/otf",
    ".glb": "model/gltf-binary", ".gltf": "model/gltf+json",
}


class TemplatePreflightError(ValueError):
    def __init__(self, issues):
        super().__init__("\n".join([
            "Template preflight failed; install.zip was not written or updated.",
            *issues,
            "Fix the source copy, re-export source.zip and rebuild from the same reviewed commit, then pack again.",
            "Remaining packaging checks have not run; this is not publishing approval.",
        ]))


def archive(files):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as result:
        for name, data in sorted(files.items()):
            result.writestr(name, data)
    return output.getvalue()


def read_file(file):
    if file.is_symlink() or not file.is_file():
        raise ValueError(f"Material must be a regular file: {file.name}")
    if file.stat().st_size > MAX_FILE:
        raise ValueError(f"Material exceeds 16 MiB: {file.name}")
    with file.open("rb") as stream:
        value = stream.read(MAX_FILE + 1)
    if len(value) > MAX_FILE:
        raise ValueError(f"Material exceeds 16 MiB: {file.name}")
    return value


def directory_count(data):
    end = next((pos for pos in range(len(data) - 22, max(-1, len(data) - 65558), -1)
                if data[pos:pos + 4] == b"PK\x05\x06" and pos + 22 + struct.unpack_from("<H", data, pos + 20)[0] == len(data)), -1)
    if end < 0:
        raise ValueError("Invalid source ZIP directory")
    disk, directory_disk, local_count, count, length, offset = struct.unpack_from("<HHHHII", data, end + 4)
    if disk or directory_disk or local_count != count or count > MAX_ENTRIES or offset + length != end:
        raise ValueError("Source ZIP exceeds entry budget or has an invalid directory")
    actual = 0
    while offset < end:
        if offset + 46 > end or data[offset:offset + 4] != b"PK\x01\x02":
            raise ValueError("Invalid source ZIP entry")
        actual += 1
        if actual > MAX_ENTRIES:
            raise ValueError("Source ZIP exceeds 5,000 entries")
        offset += 46 + sum(struct.unpack_from("<HHH", data, offset + 28))
    if actual != count or offset != end:
        raise ValueError("Invalid source ZIP entry count")
    return actual


def source_files(data):
    count = directory_count(data)
    files, directories, total, seen = {}, set(), 0, set()
    with zipfile.ZipFile(io.BytesIO(data)) as source:
        for item in source.infolist():
            decoded = item.orig_filename
            if not item.flag_bits & 0x800:
                decoded = decoded.encode("cp437").decode("utf-8")
            name = decoded.removesuffix("/")
            parts = name.split("/")
            mode = item.external_attr >> 16
            if (not name or "\\" in name or "\0" in name or ":" in name
                    or any(part in ("", ".", "..") or part.lower() == ".git" for part in parts)
                    or PurePosixPath(name).is_absolute() or name in seen
                    or stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR)
                    or item.is_dir() and stat.S_IFMT(mode) == stat.S_IFREG
                    or not item.is_dir() and stat.S_IFMT(mode) == stat.S_IFDIR
                    or name in directories and not item.is_dir()):
                raise ValueError(f"Unsafe source ZIP path or type: {name}")
            for parent in PurePosixPath(name).parents:
                if str(parent) == ".":
                    continue
                if str(parent) in files:
                    raise ValueError(f"Source ZIP file/directory collision: {name}")
                directories.add(str(parent))
            if item.is_dir():
                directories.add(name)
            seen.add(name)
            if item.file_size > MAX_FILE or total + item.file_size > MAX_EXPANDED:
                raise ValueError("Source ZIP exceeds expanded size budget")
            with source.open(item) as stream:
                value = stream.read(min(MAX_FILE, MAX_EXPANDED - total) + 1)
            if len(value) > MAX_FILE or total + len(value) > MAX_EXPANDED:
                raise ValueError("Source ZIP exceeds actual expanded size budget")
            total += len(value)
            if item.is_dir() and value:
                raise ValueError(f"Source ZIP directory contains file bytes: {name}")
            if not item.is_dir():
                files[name] = value
    return files, total, count


def template_file_materials(snapshot, metadata):
    names = [name for name in snapshot if name == "template-files" or name.startswith("template-files/")]
    if "file_seeds" not in metadata:
        if names:
            raise ValueError("template-files requires a file_seeds declaration")
        return None
    if metadata["file_seeds"] != "template-files":
        raise ValueError("file_seeds must be template-files")
    if not 1 <= len(names) <= MAX_FILE_SEEDS:
        raise ValueError("template-files requires 1..256 files")
    entries, materials, total = [], {}, 0
    for name in sorted(names, key=lambda value: value.encode("utf-8")):
        relative = name[len("template-files/"):]
        if (not relative or len(relative.encode("utf-8")) > 1024
                or any(part in ("", ".", "..") for part in relative.split("/"))
                or any(character in "\\%" or ord(character) < 32 or 127 <= ord(character) <= 159 for character in relative)):
            raise ValueError(f"Invalid template file path: {relative}")
        value = snapshot[name]
        total += len(value)
        if len(value) > MAX_FILE or total > MAX_FILE:
            raise ValueError("template-files exceeds 16 MiB")
        entries.append({"path": relative, "size": len(value),
                        "sha256": hashlib.sha256(value).hexdigest(),
                        "content_type": FILE_TYPES.get(PurePosixPath(relative).suffix.lower(), "application/octet-stream")})
        materials["files/" + relative] = value
    return {"manifest": {"version": 1, "root": "template-assets/", "entries": entries},
            "materials": materials, "bytes": total}


def check_seed_build_output(name, data, seeds):
    if seeds is None:
        return
    if any(part in ("template-files", "template-assets") for part in PurePosixPath(name).parts):
        raise ValueError(f"External template files must not enter the Web build: {name}")
    # The platform requires this exact root icon independently of file seeds.
    if name == "icon.png":
        return
    for seed, content in seeds["materials"].items():
        if content and (data == content or len(content) >= 16 and (content in data or base64.b64encode(content) in data)):
            raise ValueError(f"External template file embedded in Web build: {seed} in {name}")


def encode_install_manifest(manifest, seeds):
    if seeds is None:
        return (json.dumps(manifest, ensure_ascii=False, allow_nan=False) + "\n").encode(), None
    raw_files = json.dumps(seeds["manifest"], ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
    base = json.dumps({**manifest, "format_version": 2, "requires": ["template_files_v1"]}, ensure_ascii=False, allow_nan=False).encode()
    return base[:-1] + b',"files":' + raw_files + b"}\n", hashlib.sha256(raw_files).hexdigest()


def unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise TemplatePreflightError([
                "[preflight/metadata] metadata.json: duplicate object key.\n"
                "  Fix: keep one intended value per key; remove the duplicate declaration.",
            ])
        result[key] = value
    return result


def preflight(snapshot, without_source):
    # Only fixed fields and material names enter diagnostics, never input values.
    if "metadata.json" not in snapshot:
        raise TemplatePreflightError([
            "[preflight/metadata] metadata.json: missing.\n"
            "  Fix: include metadata.json at the root of the source snapshot.",
        ])
    raw_metadata = snapshot["metadata.json"]
    if len(raw_metadata) > MIB:
        raise TemplatePreflightError([
            "[preflight/metadata] metadata.json: exceeds 1 MiB.\n"
            "  Fix: reduce metadata to at most 1 MiB; keep application data outside metadata.",
        ])
    try:
        metadata = json.loads(raw_metadata.decode("utf-8"), object_pairs_hook=unique_json_object)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise TemplatePreflightError([
            "[preflight/metadata] metadata.json: invalid UTF-8 or JSON.\n"
            "  Fix: save a valid UTF-8 JSON object before checking its fields.",
        ]) from None
    if type(metadata) is not dict:
        raise TemplatePreflightError([
            "[preflight/metadata] metadata.json: must be an object.\n"
            "  Fix: put the template fields in a JSON object, not a list or scalar.",
        ])

    issues = []
    missing = object()

    def issue(location, problem, fix, stage="metadata"):
        if len(issues) < MAX_PREFLIGHT_ISSUES:
            if stage == "metadata":
                location = "metadata.json:" + location
            issues.append(f"[preflight/{stage}] {location}: {problem}.\n  Fix: {fix}")
        elif len(issues) == MAX_PREFLIGHT_ISSUES:
            issues.append(f"More problems found; showing the first {MAX_PREFLIGHT_ISSUES}. Fix these and run again.")

    def string(value, location):
        if value is missing:
            issue(location, "missing required field", "add a nonempty string for this field.")
        elif type(value) is not str or not value.strip():
            issue(location, "requires a nonempty string", "supply text, not null, a number, a list or an object.")
        else:
            try:
                value.encode("utf-8")
                return value
            except UnicodeEncodeError:
                issue(location, "contains invalid Unicode", "replace unpaired Unicode surrogates with valid text.")
        return None

    def objects(value, location):
        if type(value) is not list:
            issue(location, "requires an array", "use an array of objects; omit this optional field if unused.")
            return
        for index, item in enumerate(value):
            where = f"{location}[{index}]"
            if type(item) is not dict:
                issue(where, "requires an object", "supply the fields of this declaration in a JSON object.")
            else:
                yield where, item

    def variables(value, location, prefix):
        for where, variable in objects(value, location):
            for field in ("name", "description"):
                string(variable.get(field, missing), f"{where}.{field}")
            placeholder = string(variable.get("placeholder", missing), f"{where}.placeholder")
            files = variable.get("files")
            if type(files) is not list or not files:
                issue(f"{where}.files", "requires a nonempty array of file paths",
                      "list the files that contain this variable's placeholder.")
                continue
            for index, value in enumerate(files):
                at = f"{where}.files[{index}]"
                name = string(value, at)
                # site_variables refer to dist, which is checked only after preflight.
                if name is None or prefix is None:
                    continue
                content = snapshot.get(prefix + name)
                if content is None:
                    issue(at, "declared source file is missing",
                          "include this file in source.zip or correct its path relative to the declared source root.")
                elif placeholder is not None and placeholder.encode("utf-8") not in content:
                    issue(at, "Source placeholder missing",
                          "restore the declared placeholder in this file or correct the variable declaration.")

    for field in ("name", "display_name", "description"):
        string(metadata.get(field, missing), field)
    if type(metadata.get("database_required")) is not bool:
        issue("database_required", "requires a JSON boolean",
              "use true or false, not a quoted value, after confirming the app's database needs.\n"
              "  Declared schema/seeds require true; do not remove required SQL just to pass.")
    if "private_database" in metadata and type(metadata["private_database"]) is not bool:
        issue("private_database", "requires a JSON boolean",
              "use true or false without quotes; true keeps the database off the browser's Web binding.")

    sql = []
    for field in ("schema", "seeds"):
        if field not in metadata:
            continue
        name = string(metadata[field], field)
        if name is not None:
            sql.append(name)
            if name not in snapshot:
                issue(field, "declared SQL file is missing",
                      "include the declared SQL file in source.zip or correct its path relative to the snapshot root.")
    if sql and metadata.get("database_required") is False:
        issue("database_required", "SQL materials require database_required=true",
              "confirm the database dependency and use true for SQL-backed apps; do not remove required SQL just to pass.")
    has_file_seeds = any(name == "template-files" or name.startswith("template-files/") for name in snapshot)
    if "file_seeds" in metadata:
        if metadata["file_seeds"] != "template-files":
            issue("file_seeds", "must be the string template-files",
                  "use the declared template-files directory; omit this optional field only when no file seeds are needed.")
        elif not has_file_seeds:
            issue("file_seeds", "declared material files are missing",
                  "include the reviewed files under template-files/ in source.zip.")
    elif has_file_seeds:
        issue("file_seeds", "missing declaration for template-files",
              "declare file_seeds as template-files after reviewing the files for public distribution.")

    variables(metadata.get("variables", []), "variables", "")
    repositories = {}
    for where, repo in objects(metadata.get("repositories", []), "repositories"):
        key = string(repo.get("key", missing), f"{where}.key")
        path = string(repo.get("path", missing), f"{where}.path")
        prefix = None
        if path is not None:
            if path != "." and ("\\" in path or any(part in ("", ".", "..") for part in path.split("/"))):
                issue(f"{where}.path", "requires a relative source directory",
                      "use '.' or a relative directory without empty, dot or parent segments.")
            else:
                prefix = "" if path == "." else path + "/"
                if not any(name.startswith(prefix) for name in snapshot):
                    issue(f"{where}.path", "Repository source missing",
                          "include the reviewed repository snapshot under this directory.")
                    prefix = None
        if key is not None:
            if key in repositories:
                issue(f"{where}.key", "duplicate repository key", "give each logical repository a unique key.")
            else:
                repositories[key] = prefix
        variables(repo.get("variables", []), f"{where}.variables", prefix)
    repositories_typed = type(metadata.get("repositories", [])) is list
    if "web_repository" in metadata:
        key = string(metadata["web_repository"], "web_repository")
        if key is not None and repositories_typed and key not in repositories:
            issue("web_repository", "references an undeclared repository",
                  "use the key of the declared repository containing the Web source.")

    function_keys = set()
    for where, fn in objects(metadata.get("functions", []), "functions"):
        key = string(fn.get("key", missing), f"{where}.key")
        string(fn.get("name", missing), f"{where}.name")
        repo = string(fn.get("repository", missing), f"{where}.repository")
        directory = string(fn.get("source_dir", missing), f"{where}.source_dir")
        if key is not None:
            if key in function_keys:
                issue(f"{where}.key", "duplicate function key", "give each function a unique key.")
            function_keys.add(key)
        if repo is not None and repositories_typed and repo not in repositories:
            issue(f"{where}.repository", "Function repository missing", "reference a declared repository key.")
        if directory is not None:
            directory = directory.rstrip("/")
            if fn["source_dir"] != "/" and (not directory.startswith("/") or any(part in ("", ".", "..") for part in directory[1:].split("/")) or "\\" in directory or "\0" in directory):
                issue(f"{where}.source_dir", "requires a repository path starting with /",
                      "use the function's actual source directory, without dot or parent segments.")
            elif repo in repositories and repositories[repo] is not None:
                prefix = repositories[repo] + (directory[1:] + "/" if directory else "")
                if not any(name.startswith(prefix) and "/" not in name[len(prefix):] and name.endswith(".go") for name in snapshot):
                    issue(f"{where}.source_dir", "Function entry Go source missing",
                          "include the function's Go entry source directly in this repository directory.")
        for field in ("parameters", "cors", "database"):
            if field in fn and type(fn[field]) is not dict:
                issue(f"{where}.{field}", "requires an object", "use the documented object fields or omit this optional declaration.")
        database = fn.get("database")
        if type(database) is dict:
            endpoint = string(database.get("endpoint_parameter", missing), f"{where}.database.endpoint_parameter")
            token = string(database.get("token_parameter", missing), f"{where}.database.token_parameter")
            if endpoint is not None and endpoint == token:
                issue(f"{where}.database", "requires distinct endpoint and token parameter names",
                      "declare separate backend parameters; credentials are supplied during installation.")
            if metadata.get("database_required") is False:
                issue(f"{where}.database", "requires database_required=true",
                      "confirm the backend database dependency; do not remove required configuration just to pass.")
    variables(metadata.get("site_variables", []), "site_variables", None)

    names = ["showcase/preview.html", "showcase/cover.webp"]
    if not without_source:
        names.append("showcase/prompt.md")
    fixes = [
        "add the self-contained preview HTML to the source snapshot.",
        "add the WebP cover made from the reviewed preview to the source snapshot.",
        "add the customization prompt for source-sharing mode to the source snapshot.",
    ]
    for name, fix in zip(names, fixes):
        if name not in snapshot:
            issue(name, "missing", fix, "showcase")
        elif name == "showcase/preview.html" and len(snapshot[name]) > 500_000:
            issue(name, "exceeds 500,000 bytes",
                  "simplify the self-contained preview to at most 500,000 bytes before compression.", "showcase")
    if issues:
        raise TemplatePreflightError(issues)
    return metadata, names


def validate_site_variables(metadata, site):
    for variable in metadata.get("site_variables", []):
        for name in variable["files"]:
            if variable["placeholder"].encode() not in site.get("data/" + name, b""):
                raise ValueError(f"Built site placeholder missing: {name}")


def pack(source_zip, dist, entry, output, without_source=False):
    source = read_file(Path(source_zip))
    snapshot, source_size, source_count = source_files(source)
    metadata, names = preflight(snapshot, without_source)
    if without_source and metadata.get("functions"):
        raise ValueError("Function templates require source.zip to compile their backends")
    seeds = template_file_materials(snapshot, metadata)
    if seeds is not None and without_source:
        raise ValueError("File templates require source.zip for server byte verification; --without-source is only available for templates without file_seeds")
    files = {name: snapshot[name] for name in names}
    sql_names = {}
    for field, target in (("schema", "schema.sql"), ("seeds", "seed.sql")):
        name = metadata.get(field)
        if name:
            if not metadata["database_required"]:
                raise ValueError("SQL materials require database_required=true")
            files[target] = snapshot[name]
            sql_names[name] = target
    site = {"web.yaml": b""}
    dist = Path(dist)
    if dist.is_symlink() or not dist.is_dir():
        raise ValueError("Build directory must be a real directory")
    site_size = 0
    for file in sorted(dist.rglob("*")):
        if file.is_symlink():
            raise ValueError(f"Build contains a symlink: {file.relative_to(dist)}")
        relative = file.relative_to(dist).as_posix()
        if seeds is not None and any(part in ("template-files", "template-assets") for part in file.relative_to(dist).parts):
            raise ValueError(f"External template files must not enter the Web build: {relative}")
        if file.is_file():
            data = read_file(file)
            check_seed_build_output(relative, data, seeds)
            site_size += len(data)
            if site_size > MAX_FILE or len(site) >= 4097:
                raise ValueError("Build exceeds the Web archive resource budget")
            site["data/" + file.relative_to(dist).as_posix()] = data
        elif not file.is_dir():
            raise ValueError(f"Build contains a nonregular entry: {relative}")
    if not entry or "data/" + entry not in site:
        raise ValueError("Build is missing its fixed entry")
    validate_site_variables(metadata, site)
    compiled = archive(site)
    if len(compiled) > MAX_FILE:
        raise ValueError("site.tweb exceeds 16 MiB")
    variables = []
    for variable in metadata.get("variables", []):
        targets = [sql_names[name] for name in variable["files"] if name in sql_names]
        if targets:
            if variable["name"] not in ("WEB_ID", "SQLITE_INSTANCE_ID", "APP_NAME"):
                raise ValueError(f"Unsupported installation SQL variable: {variable['name']}")
            variables.append({**variable, "files": targets})
    if not without_source:
        files["source.zip"] = source
    if "data/icon.png" in site:
        files["icon.png"] = site["data/icon.png"]
    files["site.tweb"] = compiled
    manifest = {"metadata": metadata, "entry": entry, "database_required": metadata["database_required"], "variables": variables}
    for field in ("private_database", "web_repository", "repositories", "functions", "site_variables"):
        if field in metadata:
            manifest[field] = metadata[field]
    files["install.json"], file_manifest_digest = encode_install_manifest(manifest, seeds)
    if len(files["install.json"]) > MIB:
        raise ValueError("install.json exceeds 1 MiB")
    if seeds is not None:
        files.update(seeds["materials"])
    expanded = sum(map(len, files.values())) + site_size + (0 if without_source else source_size)
    entries = len(files) + len(site) + (0 if without_source else source_count)
    if expanded > MAX_EXPANDED or entries > MAX_ENTRIES or any(len(value) > MAX_FILE for value in files.values()):
        raise ValueError("Package exceeds cumulative extraction budget")
    data = archive(files)
    if len(data) > 32 * MIB:
        raise ValueError("install.zip exceeds 32 MiB")
    Path(output).write_bytes(data)
    result = {"name": metadata["name"], "file": str(Path(output).resolve()), "size": len(data), "sha256": hashlib.sha256(data).hexdigest(), "has_source": not without_source, "database_required": metadata["database_required"], "expanded_bytes": expanded, "entries": entries}
    if seeds is not None:
        result.update({"format_version": 2, "file_count": len(seeds["manifest"]["entries"]), "file_bytes": seeds["bytes"], "file_manifest_sha256": file_manifest_digest})
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="Reviewed source.zip from the build's source commit")
    parser.add_argument("--dist", required=True, help="Clean build output directory")
    parser.add_argument("--entry", required=True, help="Fixed entry relative to dist")
    parser.add_argument("--output", required=True, help="Destination install.zip")
    parser.add_argument("--without-source", action="store_true", help="No-file templates only: omit source and customization prompt")
    args = parser.parse_args()
    try:
        result = pack(args.source, args.dist, args.entry, args.output, args.without_source)
    except TemplatePreflightError as error:
        parser.exit(1, f"{error}\n")
    print(json.dumps(result, ensure_ascii=False))
