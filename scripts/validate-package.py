#!/usr/bin/env python3
"""Validate the constrained RimWorld 1.6 Piped CE Autoloaders package."""

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Optional

EXPECTED_TOP_LEVEL = {"About", "Defs", "LoadFolders.xml", "1.6"}
EXPECTED_VERSIONS = ("1.6",)
FORBIDDEN_NAMES = {"Source", ".git", "scripts", "bin", "obj", ".vs"}
ASSEMBLY_NAME = "PipedCEAutoloaders.dll"
PACKAGE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*\.[A-Za-z0-9][A-Za-z0-9_.-]*$")


def fail(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(1)


def require_file(path: Path) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        fail(f"required non-empty file is missing: {path}")


def require_directory(path: Path) -> None:
    if not path.is_dir() or path.is_symlink():
        fail(f"required package directory is missing or not a real directory: {path}")


def parse_xml_files(directory: Path) -> None:
    for path in sorted(directory.rglob("*.xml")):
        try:
            ET.parse(path)
        except ET.ParseError as error:
            fail(f"invalid XML in {path}: {error}")


def installed_version(rimworld_dir: Path) -> Optional[str]:
    version_file = rimworld_dir / "Version.txt"
    if not version_file.is_file():
        print(f"Warning: RimWorld Version.txt not found: {version_file}", file=sys.stderr)
        return None
    match = re.search(r"\d+\.\d+(?:\.\d+)?", version_file.read_text(encoding="utf-8"))
    if not match:
        print(f"Warning: could not determine RimWorld version from {version_file}", file=sys.stderr)
        return None
    return match.group(0)


def load_folder_mapping(path: Path) -> Dict[str, str]:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as error:
        fail(f"invalid XML in {path}: {error}")
    if root.tag != "loadFolders" or root.attrib or (root.text and root.text.strip()):
        fail("LoadFolders.xml root must be loadFolders")
    entries = list(root)
    if {entry.tag for entry in entries} != {"v1.6"} or len(entries) != 1:
        fail("LoadFolders.xml must contain exactly a v1.6 mapping")
    mapping = {}
    for entry in entries:
        if entry.attrib or (entry.text and entry.text.strip()) or (entry.tail and entry.tail.strip()) or len(entry) != 1:
            fail(f"invalid LoadFolders.xml mapping for {entry.tag}")
        item = entry[0]
        if item.tag != "li" or item.attrib or len(item) != 0 or item.text is None or (item.tail and item.tail.strip()):
            fail(f"invalid LoadFolders.xml mapping for {entry.tag}")
        mapping[entry.tag] = item.text.strip()
    if mapping != {"v1.6": "1.6"}:
        fail("LoadFolders.xml mapping must select the 1.6 folder")
    return mapping


def validate_version(package: Path, version: str) -> None:
    version_dir = package / version
    require_directory(version_dir)
    if {path.name for path in version_dir.iterdir()} != {"Assemblies"}:
        fail(f"unexpected runtime content in {version_dir}")
    assemblies = version_dir / "Assemblies"
    require_directory(assemblies)
    if {path.name for path in assemblies.iterdir()} != {ASSEMBLY_NAME}:
        fail(f"unexpected runtime content in {assemblies}")
    require_file(assemblies / ASSEMBLY_NAME)


def validate_defs(package: Path) -> None:
    defs = package / "Defs"
    require_directory(defs)
    expected = defs / "Buildings" / "Phase0_Autoloader.xml"
    files = {path.relative_to(defs).as_posix() for path in defs.rglob("*") if path.is_file()}
    if files != {"Buildings/Phase0_Autoloader.xml"}:
        fail("Defs must contain exactly Buildings/Phase0_Autoloader.xml")
    require_file(expected)
    parse_xml_files(defs)
    root = ET.parse(expected).getroot()
    autoloaders = root.findall("ThingDef")
    if root.tag != "Defs" or len(autoloaders) != 1:
        fail("Phase 0 Defs file must contain exactly one ThingDef")
    autoloader = autoloaders[0]
    if autoloader.findtext("defName") != "PipedCEAutoloader_Phase0_762x51mm":
        fail("Phase 0 autoloader has an unexpected defName")
    if autoloader.findtext("thingClass") != "CombatExtended.Building_AutoloaderCE":
        fail("Phase 0 autoloader must use CombatExtended.Building_AutoloaderCE")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--rimworld-dir", type=Path)
    args = parser.parse_args()

    if args.package.is_symlink():
        fail(f"package root must not be a symlink: {args.package}")
    package = args.package.resolve()
    if not package.is_dir():
        fail(f"package directory does not exist: {package}")
    if {path.name for path in package.iterdir()} != EXPECTED_TOP_LEVEL:
        fail("package must contain exactly About, Defs, LoadFolders.xml, and 1.6")
    for path in package.rglob("*"):
        if path.is_symlink():
            fail(f"symlinks are not allowed in package: {path}")
        if path.name in FORBIDDEN_NAMES:
            fail(f"generated or repository artifact is not allowed in package: {path}")

    about = package / "About"
    require_directory(about)
    if {path.name for path in about.iterdir()} != {"About.xml"}:
        fail("About must contain exactly About.xml")
    require_file(about / "About.xml")
    load_folders = package / "LoadFolders.xml"
    require_file(load_folders)
    mapping = load_folder_mapping(load_folders)
    parse_xml_files(about)
    validate_defs(package)
    for version in EXPECTED_VERSIONS:
        validate_version(package, version)

    metadata = ET.parse(about / "About.xml").getroot()
    name = metadata.findtext("name", default="").strip()
    package_id = metadata.findtext("packageId", default="").strip()
    versions = [element.text.strip() for element in metadata.findall("./supportedVersions/li") if element.text and element.text.strip()]
    dependencies = {element.findtext("packageId", default="").strip() for element in metadata.findall("./modDependencies/li")}
    if name != "Piped CE Autoloaders":
        fail(f"About/About.xml has an unexpected name: {name!r}")
    if package_id != "Sanicek.PipedCEAutoloaders" or not PACKAGE_ID.fullmatch(package_id):
        fail(f"About/About.xml has an invalid packageId: {package_id!r}")
    if versions != [mapping["v1.6"]]:
        fail("About supportedVersions must exactly be [1.6]")
    if dependencies != {"CETeam.CombatExtended", "OskarPotocki.VanillaFactionsExpanded.Core"}:
        fail("About must declare hard Combat Extended and Vanilla Expanded Framework dependencies")

    if args.rimworld_dir:
        version = installed_version(args.rimworld_dir)
        if version:
            series = ".".join(version.split(".")[:2])
            if version not in versions and series not in versions:
                print(f"Warning: installed RimWorld {version} is not listed in supportedVersions ({', '.join(versions)}).", file=sys.stderr)

    print(f"Package validation succeeded: {package}")


if __name__ == "__main__":
    main()
