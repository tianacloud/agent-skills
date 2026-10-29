#!/usr/bin/env python3
"""Package a reviewed source snapshot and its clean build as an installable template."""
import argparse
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
    files, total, seen = {}, 0, set()
    with zipfile.ZipFile(io.BytesIO(data)) as source:
        for item in source.infolist():
            name = item.filename.rstrip("/")
            parts = name.split("/")
            mode = item.external_attr >> 16
            if (not name or "\\" in name or "\0" in name or ":" in name
                    or any(part in ("", ".", "..") or part.lower() == ".git" for part in parts)
                    or PurePosixPath(name).is_absolute() or name in seen
                    or stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR)):
                raise ValueError(f"Unsafe source ZIP path or type: {name}")
            seen.add(name)
            if item.file_size > MAX_FILE or total + item.file_size > MAX_EXPANDED:
                raise ValueError("Source ZIP exceeds expanded size budget")
            with source.open(item) as stream:
                value = stream.read(min(MAX_FILE, MAX_EXPANDED - total) + 1)
            if len(value) > MAX_FILE or total + len(value) > MAX_EXPANDED:
                raise ValueError("Source ZIP exceeds actual expanded size budget")
            total += len(value)
            if not item.is_dir():
                files[name] = value
    return files, total, count


def validate_backend_materials(metadata, snapshot, site):
    repositories = {r["key"]: r for r in metadata.get("repositories", [])}
    for repo in repositories.values():
        prefix = "" if repo["path"] == "." else repo["path"] + "/"
        if not any(name.startswith(prefix) for name in snapshot):
            raise ValueError(f"Repository source missing: {repo['key']}")
        for variable in repo.get("variables", []):
            for name in variable["files"]:
                if variable["placeholder"].encode() not in snapshot.get(prefix + name, b""):
                    raise ValueError(f"Source placeholder missing: {repo['key']}/{name}")
    for fn in metadata.get("functions", []):
        repo = repositories.get(fn["repository"])
        if repo is None:
            raise ValueError(f"Function repository missing: {fn['key']}")
        prefix = "" if repo["path"] == "." else repo["path"] + "/"
        directory = fn.get("source_dir", "").rstrip("/")
        if fn.get("source_dir") != "/" and (not directory.startswith("/") or any(part in ("", ".", "..") for part in directory[1:].split("/")) or "\\" in directory or "\0" in directory):
            raise ValueError("Function source_dir must be a repository path starting with /")
        prefix += directory[1:] + "/" if directory else ""
        if prefix + "go.mod" not in snapshot:
            raise ValueError(f"Function source_dir requires its own go.mod: {fn['key']}")
        if not any(name.startswith(prefix) and "/" not in name[len(prefix):] and name.endswith(".go") for name in snapshot):
            raise ValueError(f"Function entry Go source missing: {fn['key']}")
    for variable in metadata.get("site_variables", []):
        for name in variable["files"]:
            if variable["placeholder"].encode() not in site.get("data/" + name, b""):
                raise ValueError(f"Built site placeholder missing: {name}")


def pack(source_zip, dist, entry, output, without_source=False):
    source = read_file(Path(source_zip))
    snapshot, source_size, source_count = source_files(source)
    metadata = json.loads(snapshot["metadata.json"])
    if type(metadata.get("database_required")) is not bool:
        raise ValueError("metadata.json requires an explicit database_required boolean")
    if without_source and metadata.get("functions"):
        raise ValueError("Function templates require source.zip to compile their backends")
    names = ["showcase/preview.html", "showcase/cover.webp"]
    if not without_source:
        names.append("showcase/prompt.md")
    files = {name: snapshot[name] for name in names}
    if len(files["showcase/preview.html"]) > 500_000:
        raise ValueError("showcase/preview.html exceeds 500,000 bytes")
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
    site_size = 0
    for file in sorted(dist.rglob("*")):
        if file.is_symlink():
            raise ValueError(f"Build contains a symlink: {file.relative_to(dist)}")
        if file.is_file():
            data = read_file(file)
            site_size += len(data)
            if site_size > MAX_FILE or len(site) >= 4097:
                raise ValueError("Build exceeds the Web archive resource budget")
            site["data/" + file.relative_to(dist).as_posix()] = data
    if not entry or "data/" + entry not in site:
        raise ValueError("Build is missing its fixed entry")
    validate_backend_materials(metadata, snapshot, site)
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
    files["install.json"] = (json.dumps(manifest, ensure_ascii=False) + "\n").encode()
    expanded = sum(map(len, files.values())) + site_size + (0 if without_source else source_size)
    entries = len(files) + len(site) + (0 if without_source else source_count)
    if expanded > MAX_EXPANDED or entries > MAX_ENTRIES or any(len(value) > MAX_FILE for value in files.values()):
        raise ValueError("Package exceeds cumulative extraction budget")
    data = archive(files)
    if len(data) > 32 * MIB:
        raise ValueError("install.zip exceeds 32 MiB")
    Path(output).write_bytes(data)
    return {"name": metadata["name"], "file": str(Path(output).resolve()), "size": len(data), "sha256": hashlib.sha256(data).hexdigest(), "has_source": not without_source, "database_required": metadata["database_required"], "expanded_bytes": expanded, "entries": entries}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="Reviewed source.zip from the build's source commit")
    parser.add_argument("--dist", required=True, help="Clean build output directory")
    parser.add_argument("--entry", required=True, help="Fixed entry relative to dist")
    parser.add_argument("--output", required=True, help="Destination install.zip")
    parser.add_argument("--without-source", action="store_true", help="Publish installation materials without source or customization prompt")
    args = parser.parse_args()
    print(json.dumps(pack(args.source, args.dist, args.entry, args.output, args.without_source), ensure_ascii=False))
