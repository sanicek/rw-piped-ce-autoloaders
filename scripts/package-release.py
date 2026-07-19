#!/usr/bin/env python3
"""Build one installable, deterministic GitHub release archive.

The generated ZIP contains the same validator-approved directory installed by
the local workflow. It deliberately performs no Git tagging or publication:
those irreversible steps remain visible decisions in the OpenCode release
workflow after the exact candidate has passed its RimWorld smoke test.
"""

import hashlib
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
ARCHIVE_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def fail(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(1)


def mod_version(metadata: Path) -> str:
    try:
        version = ET.parse(metadata).getroot().findtext("modVersion", "").strip()
    except ET.ParseError as error:
        fail(f"invalid metadata XML in {metadata}: {error}")
    if not SEMVER.fullmatch(version):
        fail(f"About/About.xml modVersion is not valid SemVer: {version!r}")
    return version


def archive_entry(name: str, mode: int, directory: bool = False) -> zipfile.ZipInfo:
    entry = zipfile.ZipInfo(name + ("/" if directory else ""), ARCHIVE_TIMESTAMP)
    entry.create_system = 3
    entry.external_attr = ((mode & 0xFFFF) << 16) | (0x10 if directory else 0)
    entry.compress_type = zipfile.ZIP_DEFLATED
    return entry


def write_archive(package: Path, destination: Path) -> None:
    root_name = package.name
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        archive.writestr(archive_entry(root_name, 0o755, directory=True), b"")
        for path in sorted(package.rglob("*"), key=lambda item: item.relative_to(package).as_posix()):
            relative = path.relative_to(package).as_posix()
            archive_name = f"{root_name}/{relative}"
            if path.is_symlink():
                fail(f"release package may not contain symlinks: {path}")
            if path.is_dir():
                archive.writestr(archive_entry(archive_name, 0o755, directory=True), b"")
            elif path.is_file():
                archive.writestr(archive_entry(archive_name, 0o644), path.read_bytes())
            else:
                fail(f"release package contains an unsupported entry: {path}")
    with zipfile.ZipFile(destination, "r") as archive:
        corrupt = archive.testzip()
        if corrupt:
            fail(f"release archive failed its CRC check at {corrupt}")


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=normal"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if status:
        fail("release packaging requires a clean worktree")
    version = mod_version(repo_root / "About" / "About.xml")
    subprocess.run([repo_root / "scripts" / "build.sh"], check=True)

    package = repo_root / "artifacts" / "PipedCEAutoloaders"
    release_dir = repo_root / "artifacts" / "releases"
    release_dir.mkdir(parents=True, exist_ok=True)
    archive = release_dir / f"PipedCEAutoloaders-v{version}.zip"
    checksum = archive.with_suffix(".zip.sha256")
    temporary = archive.with_suffix(".zip.tmp")

    try:
        write_archive(package, temporary)
        os.replace(temporary, archive)
    finally:
        temporary.unlink(missing_ok=True)

    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="ascii")
    print(f"Release archive: {archive}")
    print(f"SHA-256: {digest}")


if __name__ == "__main__":
    main()
