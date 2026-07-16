#!/usr/bin/env python3
"""Validate the release contract for the RimWorld 1.6 mod package.

The validator treats package shape, version routing, gameplay Def wiring, and
metadata as one release boundary. It deliberately validates generated output
rather than compilation or in-game behavior. Exact package paths and selected
Def invariants keep common source, build, and dependency artifacts from shipping
unnoticed.
"""

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Optional

# These allowlists are release policy, not a general RimWorld package schema.
# Expanding supported versions or package content requires changing the build,
# routing, metadata, and these expectations together.
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
    # Routing is intentionally exact: the mapping must list shared root content
    # before the sole versioned directory, with no unvalidated fallbacks.
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
    # Runtime folders contain this mod's assembly only. Dependencies are supplied
    # by RimWorld's mod loader and must not be redistributed in the package.
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
    # Phase 1: constrain the Def surface before interpreting individual fields.
    defs = package / "Defs"
    require_directory(defs)
    autoloaders_path = defs / "Buildings" / "Autoloaders.xml"
    networks_path = defs / "PipeSystem" / "ConfigurableNetworks.xml"
    files = {path.relative_to(defs).as_posix() for path in defs.rglob("*") if path.is_file()}
    if files != {"Buildings/Autoloaders.xml", "PipeSystem/ConfigurableNetworks.xml"}:
        fail("Defs must contain exactly the release autoloaders and configurable-network files")
    require_file(autoloaders_path)
    require_file(networks_path)
    parse_xml_files(defs)
    autoloaders_root = ET.parse(autoloaders_path).getroot()
    networks_root = ET.parse(networks_path).getroot()
    if autoloaders_root.tag != "Defs" or networks_root.tag != "Defs":
        fail("release Def files must have Defs roots")

    # Phase 2: establish the three positional network families and their safe
    # startup defaults. Runtime settings may replace these concrete identities,
    # but startup must remain valid before binding initialization runs.
    slots = {
        "Amber": ("AmmoSet_762x51mmNATO", "Ammo_762x51mmNATO_FMJ"),
        "Blue": ("AmmoSet_556x45mmNATO", "Ammo_556x45mmNATO_FMJ"),
        "Green": ("AmmoSet_12Gauge", "Ammo_12Gauge_Buck"),
    }
    nets = {net.findtext("defName"): net for net in networks_root.findall("PipeSystem.PipeNetDef")}
    if set(nets) != {f"PipedCEAutoloaders_{slot}Net" for slot in slots}:
        fail("configurable networks must define exactly the Amber, Blue, and Green PipeNetDefs")
    expected_off_textures = {
        "PipedCEAutoloaders_AmberNet": "Things/Ammo/Rifle/Battlerifle/FMJ/FMJ_c",
        "PipedCEAutoloaders_BlueNet": "Things/Ammo/Rifle/Battlerifle/FMJ/FMJ_c",
        "PipedCEAutoloaders_GreenNet": "Things/Ammo/Shotgun/Shot/Shot_c",
    }
    for net_name, texture_path in expected_off_textures.items():
        if nets[net_name].findtext("./resource/offTexPath") != texture_path:
            fail(f"{net_name} must use its concrete startup material texture")

    # Phase 3: verify the shared VEF building patterns and the custom loader's
    # lifecycle requirements before checking each concrete family.
    network_things = {
        thing.findtext("defName"): thing
        for thing in networks_root.findall("ThingDef")
        if thing.findtext("defName")
    }
    loaders = {
        thing.findtext("defName"): thing
        for thing in autoloaders_root.findall("ThingDef")
        if thing.findtext("defName")
    }
    expected_network_things = {
        f"PipedCEAutoloaders_{slot}{suffix}"
        for slot in slots
        for suffix in ("Pipe", "Tank", "Input")
    }
    if set(network_things) != expected_network_things:
        fail("each configurable network must define exactly one pipe, tank, and input")
    if set(loaders) != {f"PipedCEAutoloaders_{slot}Autoloader" for slot in slots}:
        fail("release autoloaders must define exactly one loader per configurable network")

    pipe_base = networks_root.find("./ThingDef[@Name='PipedCEAutoloaders_PipeBase']")
    input_base = networks_root.find("./ThingDef[@Name='PipedCEAutoloaders_InputBase']")
    loader_base = autoloaders_root.find("./ThingDef[@Name='PipedCEAutoloaders_AutoloaderBase']")
    if (
        pipe_base is None
        or pipe_base.findtext("thingClass") != "PipeSystem.Building_Pipe"
        or pipe_base.findtext("uiIconPath") != "Things/Building/Linked/PowerConduit_MenuIcon"
        or pipe_base.findtext("./building/blueprintGraphicData/texPath") != "Things/Building/Linked/PowerConduit_Blueprint_Atlas"
    ):
        fail("release pipe base must retain the VEF linked-pipe rendering pattern")
    if input_base is None or any(
        input_base.findtext(path) != value
        for path, value in {
            "thingClass": "Building_Storage",
            "altitudeLayer": "BuildingOnTop",
            "passability": "Standable",
            "surfaceType": "Item",
            "canOverlapZones": "false",
            "building/preventDeteriorationOnTop": "true",
            "building/ignoreStoredThingsBeauty": "true",
        }.items()
    ):
        fail("release input base must retain the VEF hauling-safe storage pattern")
    if (
        loader_base is None
        or loader_base.findtext("thingClass") != "PipedCEAutoloaders.Building_PipeBackedAutoloaderCE"
        or loader_base.findtext("tickerType") != "Normal"
        or loader_base.findtext("drawerType") != "MapMeshAndRealTime"
        or loader_base.findtext("hasInteractionCell") != "false"
    ):
        fail("release autoloader base must use the pipe-backed class and required lifecycle settings")
    loader_power_comps = loader_base.findall("./comps/li[@Class='CompProperties_Power']")
    if (
        len(loader_power_comps) != 1
        or loader_power_comps[0].findtext("compClass") != "CompPowerTrader"
        or loader_power_comps[0].findtext("basePowerConsumption") != "100"
    ):
        fail("release autoloaders must use one 100 W CompPowerTrader")

    # Phase 4: verify each color's required edges from PipeNetDef through its
    # pipe, tank, physical input, and CE buffer. A wrong required edge would make
    # settings validation appear correct while moving the wrong resource.
    for slot, (default_set, _default_ammo) in slots.items():
        net_name = f"PipedCEAutoloaders_{slot}Net"
        pipe_name = f"PipedCEAutoloaders_{slot}Pipe"
        tank_name = f"PipedCEAutoloaders_{slot}Tank"
        input_name = f"PipedCEAutoloaders_{slot}Input"
        loader_name = f"PipedCEAutoloaders_{slot}Autoloader"
        if nets[net_name].findtext("./pipeDefs/li") != pipe_name:
            fail(f"{slot} PipeNetDef must identify its own pipe")
        expected_comps = {
            pipe_name: "PipeSystem.CompProperties_Resource",
            tank_name: "PipeSystem.CompProperties_ResourceStorage",
            input_name: "PipedCEAutoloaders.CompProperties_PipedAmmoInput",
        }
        for thing_name, comp_class in expected_comps.items():
            comp = network_things[thing_name].find(f"./comps/li[@Class='{comp_class}']")
            if comp is None or comp.findtext("pipeNet") != net_name:
                fail(f"{thing_name} must use {comp_class} on its matching PipeNetDef")
        loader = loaders[loader_name]
        loader_comps = loader.find("./comps")
        if (
            loader_comps is None
            or loader_comps.get("Inherit", "true").lower() == "false"
            or loader_comps.findall("./li[@Class='CompProperties_Power']")
        ):
            fail(f"{slot} autoloader must inherit its single power component from the loader base")
        ammo_comp = loader.find("./comps/li[@Class='CombatExtended.CompProperties_AmmoListUser']")
        resource_comp = loader.find("./comps/li[@Class='PipeSystem.CompProperties_Resource']")
        if ammo_comp is None or ammo_comp.findtext("magazineSize") != "400" or ammo_comp.findtext("ammoSet") != default_set:
            fail(f"{slot} autoloader must provide its valid default CE buffer")
        if resource_comp is None or resource_comp.findtext("pipeNet") != net_name:
            fail(f"{slot} autoloader must connect to its matching PipeNetDef")

    # Phase 5: retain selected conversion preconditions and exclude the obsolete
    # spike component that would create a path back to physical items.
    if input_base.findtext("tickerType") != "Normal":
        fail("release inputs must tick normally for atomic physical-item conversion")
    if networks_root.findall(".//li[@Class='PipeSystem.CompProperties_ConvertResourceToThing']"):
        fail("release networks must not contain Phase 1 diagnostic outputs")


def main() -> None:
    # Phase 1: parse the invocation and establish a real, self-contained package
    # root before traversing any user-supplied path.
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

    # Phase 2: validate shared metadata and Defs, then every declared runtime
    # directory. LoadFolders.xml is parsed first because it defines the version
    # contract checked by both package layout and About.xml.
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

    # Phase 3: enforce the user-facing identity and hard dependencies. The
    # installed game check remains advisory because package validity must not
    # depend on the maintainer's currently selected RimWorld version.
    metadata = ET.parse(about / "About.xml").getroot()
    name = metadata.findtext("name", default="").strip()
    description = metadata.findtext("description", default="").strip()
    package_id = metadata.findtext("packageId", default="").strip()
    versions = [element.text.strip() for element in metadata.findall("./supportedVersions/li") if element.text and element.text.strip()]
    dependency_elements = metadata.findall("./modDependencies/li")
    dependencies = {element.findtext("packageId", default="").strip() for element in dependency_elements}
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
    if any(not element.findtext("downloadUrl", default="").strip() for element in dependency_elements):
        fail("each hard dependency must provide a downloadUrl")

    if args.rimworld_dir:
        version = installed_version(args.rimworld_dir)
        if version:
            series = ".".join(version.split(".")[:2])
            if version not in versions and series not in versions:
                print(f"Warning: installed RimWorld {version} is not listed in supportedVersions ({', '.join(versions)}).", file=sys.stderr)

    print(f"Package validation succeeded: {package}")


if __name__ == "__main__":
    main()
