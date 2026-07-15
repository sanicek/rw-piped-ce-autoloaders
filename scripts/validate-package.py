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


def load_folder_mapping(path: Path) -> Dict[str, tuple[str, ...]]:
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
        if entry.attrib or (entry.text and entry.text.strip()) or (entry.tail and entry.tail.strip()) or len(entry) != 2:
            fail(f"invalid LoadFolders.xml mapping for {entry.tag}")
        folders = []
        for item in entry:
            if item.tag != "li" or item.attrib or len(item) != 0 or item.text is None or (item.tail and item.tail.strip()):
                fail(f"invalid LoadFolders.xml mapping for {entry.tag}")
            folders.append(item.text.strip())
        mapping[entry.tag] = tuple(folders)
    if mapping != {"v1.6": ("/", "1.6")}:
        fail("LoadFolders.xml v1.6 mapping must load / followed by 1.6")
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
    phase_two = defs / "Buildings" / "Phase2_PipeBackedAutoloader.xml"
    phase_one = defs / "PipeSystem" / "Phase1_Static762x51mmNetwork.xml"
    files = {path.relative_to(defs).as_posix() for path in defs.rglob("*") if path.is_file()}
    if files != {
        "Buildings/Phase0_Autoloader.xml",
        "Buildings/Phase2_PipeBackedAutoloader.xml",
        "PipeSystem/Phase1_Static762x51mmNetwork.xml",
    }:
        fail("Defs must contain exactly the Phase 0/2 autoloaders and Phase 1 pipe-network files")
    require_file(expected)
    require_file(phase_two)
    require_file(phase_one)
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

    phase_two_root = ET.parse(phase_two).getroot()
    phase_two_loaders = phase_two_root.findall("ThingDef")
    if phase_two_root.tag != "Defs" or len(phase_two_loaders) != 1:
        fail("Phase 2 Defs file must contain exactly one ThingDef")
    phase_two_loader = phase_two_loaders[0]
    if phase_two_loader.findtext("defName") != "PipedCEAutoloader_Phase2_762x51mm":
        fail("Phase 2 autoloader has an unexpected defName")
    if phase_two_loader.findtext("thingClass") != "PipedCEAutoloaders.Building_PipeBackedAutoloaderCE":
        fail("Phase 2 autoloader must use the pipe-backed building class")
    phase_two_ammo = phase_two_loader.find("./comps/li[@Class='CombatExtended.CompProperties_AmmoListUser']")
    if (
        phase_two_ammo is None
        or phase_two_ammo.findtext("magazineSize") != "400"
        or phase_two_ammo.findtext("ammoSet") != "AmmoSet_762x51mmNATO"
        or phase_two_loader.findtext("tickerType") != "Normal"
        or phase_two_loader.findtext("drawerType") != "MapMeshAndRealTime"
        or phase_two_loader.findtext("hasInteractionCell") != "false"
        or phase_two_loader.find("interactionCellOffset") is not None
    ):
        fail("Phase 2 autoloader must define the fixed CE buffer, required update modes, and no interaction cell")
    phase_two_resource = phase_two_loader.find("./comps/li[@Class='PipeSystem.CompProperties_Resource']")
    if phase_two_resource is None or phase_two_resource.findtext("pipeNet") != "PipedCEAutoloaders_762x51mmFMJNet":
        fail("Phase 2 autoloader must connect to the fixed FMJ PipeNetDef")

    phase_one_root = ET.parse(phase_one).getroot()
    if phase_one_root.tag != "Defs":
        fail("Phase 1 pipe-network file must have a Defs root")
    nets = phase_one_root.findall("PipeSystem.PipeNetDef")
    net = nets[0] if len(nets) == 1 else None
    if net is None or net.findtext("defName") != "PipedCEAutoloaders_762x51mmFMJNet":
        fail("Phase 1 must define the fixed 7.62x51mm FMJ PipeNetDef")
    expected_things = {
        "PipedCEAutoloaders_762x51mmFMJPipe": "PipeSystem.Building_Pipe",
        "PipedCEAutoloaders_762x51mmFMJTank": None,
        "PipedCEAutoloaders_762x51mmFMJInput": "Building_Storage",
        "PipedCEAutoloaders_762x51mmFMJDiagnosticOutput": "Building_Storage",
    }
    things = {thing.findtext("defName"): thing for thing in phase_one_root.findall("ThingDef")}
    if set(things) != set(expected_things):
        fail("Phase 1 must define exactly pipe, tank, input, and diagnostic-output ThingDefs")
    for def_name, thing_class in expected_things.items():
        if thing_class is not None and things[def_name].findtext("thingClass") != thing_class:
            fail(f"Phase 1 {def_name} has an unexpected thingClass")
    pipe = things["PipedCEAutoloaders_762x51mmFMJPipe"]
    pipe_comp = pipe.find("./comps/li[@Class='PipeSystem.CompProperties_Resource']")
    tank_comp = things["PipedCEAutoloaders_762x51mmFMJTank"].find("./comps/li[@Class='PipeSystem.CompProperties_ResourceStorage']")
    if pipe_comp is None or pipe_comp.findtext("pipeNet") != "PipedCEAutoloaders_762x51mmFMJNet":
        fail("Phase 1 pipe must attach to the fixed FMJ PipeNetDef")
    if pipe.findtext("uiIconPath") != "Things/Building/Linked/PowerConduit_MenuIcon":
        fail("Phase 1 linked pipe must define the vanilla PowerConduit menu icon for ghost rendering")
    if pipe.findtext("./building/blueprintGraphicData/texPath") != "Things/Building/Linked/PowerConduit_Blueprint_Atlas":
        fail("Phase 1 pipe must define the vanilla PowerConduit blueprint graphic")
    if tank_comp is None or tank_comp.findtext("pipeNet") != "PipedCEAutoloaders_762x51mmFMJNet":
        fail("Phase 1 tank must use VEF resource storage on the fixed FMJ PipeNetDef")
    input_comp = things["PipedCEAutoloaders_762x51mmFMJInput"].find("./comps/li[@Class='PipeSystem.CompProperties_ConvertThingToResource']")
    output_comp = things["PipedCEAutoloaders_762x51mmFMJDiagnosticOutput"].find("./comps/li[@Class='PipeSystem.CompProperties_ConvertResourceToThing']")
    if input_comp is None or input_comp.findtext("thing") != "Ammo_762x51mmNATO_FMJ" or input_comp.findtext("ratio") != "1":
        fail("Phase 1 input must convert Ammo_762x51mmNATO_FMJ at a 1:1 ratio")
    if output_comp is None or output_comp.findtext("thing") != "Ammo_762x51mmNATO_FMJ" or output_comp.findtext("ratio") != "1" or output_comp.findtext("maxOutputStackSize") != "1":
        fail("Phase 1 output must materialize one FMJ item per one resource unit")
    for def_name in ("PipedCEAutoloaders_762x51mmFMJInput", "PipedCEAutoloaders_762x51mmFMJDiagnosticOutput"):
        storage = things[def_name]
        required_fields = {
            "altitudeLayer": "BuildingOnTop",
            "passability": "Standable",
            "fillPercent": "0.5",
            "pathCost": "50",
            "size": "(1,1)",
            "surfaceType": "Item",
            "canOverlapZones": "false",
            "building/preventDeteriorationOnTop": "true",
            "building/ignoreStoredThingsBeauty": "true",
        }
        if any(storage.findtext(path) != value for path, value in required_fields.items()):
            fail(f"Phase 1 {def_name} must use the VEF hauling-safe storage surface pattern")


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
    description = metadata.findtext("description", default="").strip()
    package_id = metadata.findtext("packageId", default="").strip()
    versions = [element.text.strip() for element in metadata.findall("./supportedVersions/li") if element.text and element.text.strip()]
    dependencies = {element.findtext("packageId", default="").strip() for element in metadata.findall("./modDependencies/li")}
    if name != "Piped CE Autoloaders":
        fail(f"About/About.xml has an unexpected name: {name!r}")
    if "does not yet provide piped ammunition delivery" in description:
        fail("About description must reflect the packaged Phase 2 pipe-backed loader")
    if package_id != "Sanicek.PipedCEAutoloaders" or not PACKAGE_ID.fullmatch(package_id):
        fail(f"About/About.xml has an invalid packageId: {package_id!r}")
    if versions != [mapping["v1.6"][-1]]:
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
