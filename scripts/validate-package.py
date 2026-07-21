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
import struct
import sys
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path
from typing import Dict, Optional

# These allowlists are release policy, not a general RimWorld package schema.
# Expanding supported versions or package content requires changing the build,
# routing, metadata, and these expectations together.
EXPECTED_TOP_LEVEL = {"About", "Defs", "Languages", "Textures", "LoadFolders.xml", "LICENSE", "THIRD_PARTY_NOTICES.md", "1.6"}
EXPECTED_VERSIONS = ("1.6",)
FORBIDDEN_NAMES = {"Source", ".git", "scripts", "bin", "obj", ".vs"}
ASSEMBLY_NAME = "PipedCEAutoloaders.dll"
PACKAGE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*\.[A-Za-z0-9][A-Za-z0-9_.-]*$")
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
PROJECT_URL = "https://github.com/sanicek/rw-piped-ce-autoloaders"
WORKSHOP_ID = "3768286113"
DEPENDENCY_WORKSHOP_URLS = {
    "CETeam.CombatExtended": "https://steamcommunity.com/sharedfiles/filedetails/?id=2890901044",
    "OskarPotocki.VanillaFactionsExpanded.Core": "https://steamcommunity.com/workshop/filedetails/?id=2023507013",
}


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
    category = networks_root.find("DesignationCategoryDef")
    if category is None or category.findtext("label") != "Ammo Pipes":
        fail("release architect category must use the compact Ammo Pipes label")

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
        for suffix in ("Pipe", "HiddenPipe", "Tank", "Input")
    }
    if set(network_things) != expected_network_things:
        fail("each configurable network must define exactly one visible pipe, hidden pipe, tank, and input")
    if set(loaders) != {f"PipedCEAutoloaders_{slot}Autoloader" for slot in slots}:
        fail("release autoloaders must define exactly one loader per configurable network")

    pipe_base = networks_root.find("./ThingDef[@Name='PipedCEAutoloaders_PipeBase']")
    hidden_pipe_base = networks_root.find("./ThingDef[@Name='PipedCEAutoloaders_HiddenPipeBase']")
    tank_base = networks_root.find("./ThingDef[@Name='PipedCEAutoloaders_TankBase']")
    input_base = networks_root.find("./ThingDef[@Name='PipedCEAutoloaders_InputBase']")
    loader_base = autoloaders_root.find("./ThingDef[@Name='PipedCEAutoloaders_AutoloaderBase']")
    if (
        pipe_base is None
        or pipe_base.findtext("thingClass") != "PipeSystem.Building_Pipe"
        or pipe_base.findtext("uiIconPath") != "Things/Building/Linked/PowerConduit_MenuIcon"
        or pipe_base.findtext("./building/blueprintGraphicData/texPath") != "Things/Building/Linked/PowerConduit_Blueprint_Atlas"
    ):
        fail("release pipe base must retain the VEF linked-pipe rendering pattern")
    if hidden_pipe_base is None or hidden_pipe_base.get("ParentName") != "PipedCEAutoloaders_PipeBase" or any(
        hidden_pipe_base.findtext(path) != value
        for path, value in {
            "graphicData/texPath": "UI/CSG/IConduit",
            "uiIconPath": "Things/Building/Linked/HiddenConduit_MenuIcon",
            "building/ai_neverTrashThis": "true",
            "building/isTargetable": "false",
            "building/expandHomeArea": "false",
            "building/canBeDamagedByAttacks": "false",
            "statBases/MaxHitPoints": "48",
            "statBases/WorkToBuild": "280",
            "statBases/Flammability": "0",
            "costList/Steel": "4",
        }.items()
    ):
        fail("release hidden pipes must retain the buried VEF pipe pattern and vanilla hidden-conduit icon")
    if (
        tank_base is None
        or tank_base.find("thingClass") is not None
        or tank_base.findtext("size") != "(2,2)"
        or tank_base.findtext("rotatable") != "false"
        or tank_base.findtext("passability") != "PassThroughOnly"
        or tank_base.findtext("fillPercent") != "0.5"
        or tank_base.findtext("pathCost") != "50"
        or tank_base.findtext("./graphicData/graphicClass") != "Graphic_Single"
        or tank_base.findtext("./graphicData/drawSize") != "(2,2)"
        or tank_base.findtext("./graphicData/drawRotated") != "false"
        or tank_base.findtext("./graphicData/allowFlip") != "false"
    ):
        fail("release magazines must retain their fixed square graphic and costly low-cover pathing")
    if input_base is None or any(
        input_base.findtext(path) != value
        for path, value in {
            "thingClass": "Building_Storage",
            "size": "(1,1)",
            "rotatable": "false",
            "graphicData/graphicClass": "Graphic_Single",
            "graphicData/drawSize": "(1,1)",
            "graphicData/drawRotated": "false",
            "graphicData/allowFlip": "false",
            "altitudeLayer": "BuildingOnTop",
            "passability": "Standable",
            "surfaceType": "Item",
            "canOverlapZones": "false",
            "building/preventDeteriorationOnTop": "true",
            "building/ignoreStoredThingsBeauty": "true",
        }.items()
    ):
        fail("release inputs must retain fixed one-way graphics and VEF hauling-safe storage")
    if (
        loader_base is None
        or loader_base.findtext("thingClass") != "PipedCEAutoloaders.Building_PipeBackedAutoloaderCE"
        or loader_base.findtext("tickerType") != "Normal"
        or loader_base.findtext("drawerType") != "MapMeshAndRealTime"
        or loader_base.findtext("size") != "(1,1)"
        or loader_base.findtext("rotatable") != "false"
        or loader_base.findtext("passability") != "PassThroughOnly"
        or loader_base.findtext("fillPercent") != "0.5"
        or loader_base.findtext("pathCost") != "50"
        or loader_base.findtext("./graphicData/graphicClass") != "Graphic_Single"
        or loader_base.findtext("./graphicData/drawSize") != "(1,1)"
        or loader_base.findtext("./graphicData/drawRotated") != "false"
        or loader_base.findtext("./graphicData/allowFlip") != "false"
        or loader_base.findtext("hasInteractionCell") != "false"
        or loader_base.findtext("./statBases/ReloadSpeed") != "0.5"
    ):
        fail("release autoloaders must retain fixed graphics, costly low-cover pathing, and pipe-backed lifecycle settings")
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
        slot_lower = slot.lower()
        net_name = f"PipedCEAutoloaders_{slot}Net"
        pipe_name = f"PipedCEAutoloaders_{slot}Pipe"
        hidden_pipe_name = f"PipedCEAutoloaders_{slot}HiddenPipe"
        tank_name = f"PipedCEAutoloaders_{slot}Tank"
        input_name = f"PipedCEAutoloaders_{slot}Input"
        loader_name = f"PipedCEAutoloaders_{slot}Autoloader"
        expected_network_copy = {
            pipe_name: (
                f"{slot_lower} ammunition pipe",
                f"Carries the configured ammunition for the {slot_lower} network.",
            ),
            hidden_pipe_name: (
                f"hidden {slot_lower} ammunition pipe",
                f"Carries the configured ammunition for the {slot_lower} network. "
                "Invisible after construction and cannot be targeted or damaged by attacks.",
            ),
            tank_name: (
                f"{slot_lower} ammunition magazine",
                f"Stores ammunition for the {slot_lower} network. Capacity is configured in Mod Settings.",
            ),
            input_name: (
                f"{slot_lower} ammunition input",
                f"Accepts only the physical ammunition configured for the {slot_lower} network. "
                "Adds every round in each item to the network.",
            ),
        }
        for thing_name, (label, description) in expected_network_copy.items():
            thing = network_things[thing_name]
            if thing.findtext("label") != label or thing.findtext("description") != description:
                fail(f"{thing_name} must retain its reviewed English label and description")
        pipe_defs = [element.text for element in nets[net_name].findall("./pipeDefs/li")]
        if pipe_defs != [pipe_name, hidden_pipe_name]:
            fail(f"{slot} PipeNetDef must identify its visible and hidden pipes in order")
        expected_comps = {
            pipe_name: "PipeSystem.CompProperties_Resource",
            hidden_pipe_name: "PipeSystem.CompProperties_Resource",
            tank_name: "PipeSystem.CompProperties_ResourceStorage",
            input_name: "PipedCEAutoloaders.CompProperties_PipedAmmoInput",
        }
        for thing_name, comp_class in expected_comps.items():
            comp = network_things[thing_name].find(f"./comps/li[@Class='{comp_class}']")
            if comp is None or comp.findtext("pipeNet") != net_name:
                fail(f"{thing_name} must use {comp_class} on its matching PipeNetDef")
            if thing_name == tank_name:
                expected_texture = f"Things/Building/PipedCEAutoloaders/{slot}Magazine"
                if network_things[thing_name].findtext("./graphicData/texPath") != expected_texture:
                    fail(f"{tank_name} must use its matching fixed magazine texture")
                if comp.findtext("storageCapacity") != "1000":
                    fail(f"{tank_name} must retain the 1000-round startup capacity")
                if comp.findtext("centerOffset") != "(0,0,0.2)":
                    fail(f"{tank_name} must center its storage gauge on the magazine lid")
        loader = loaders[loader_name]
        expected_loader_description = (
            f"Automatically reloads a compatible adjacent Combat Extended turret using ammunition "
            f"from the {slot_lower} network. Requires power."
        )
        if (
            loader.findtext("label") != f"{slot_lower} piped autoloader"
            or loader.findtext("description") != expected_loader_description
        ):
            fail(f"{loader_name} must retain its reviewed English label and description")
        expected_loader_texture = f"Things/Building/PipedCEAutoloaders/{slot}Autoloader"
        if loader.findtext("./graphicData/texPath") != expected_loader_texture:
            fail(f"{loader_name} must use its matching custom autoloader texture")
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
        expected_input_texture = f"Things/Building/PipedCEAutoloaders/{slot}Input"
        if network_things[input_name].findtext("./graphicData/texPath") != expected_input_texture:
            fail(f"{input_name} must use its matching custom input texture")

    # Phase 5: retain selected conversion preconditions and exclude the obsolete
    # spike component that would create a path back to physical items.
    if input_base.findtext("tickerType") != "Normal":
        fail("release inputs must tick normally for atomic physical-item conversion")
    if networks_root.findall(".//li[@Class='PipeSystem.CompProperties_ConvertResourceToThing']"):
        fail("release networks must not contain Phase 1 diagnostic outputs")


def language_entries(path: Path) -> Dict[str, str]:
    """Read one flat LanguageData catalog after rejecting ambiguous entries."""
    require_file(path)
    root = ET.parse(path).getroot()
    if root.tag != "LanguageData" or root.attrib:
        fail(f"language catalog must use an unadorned LanguageData root: {path}")
    entries = list(root)
    actual = {entry.tag: entry.text or "" for entry in entries}
    if len(actual) != len(entries):
        fail(f"language catalog contains duplicate keys: {path}")
    if any(entry.attrib or len(entry) for entry in entries):
        fail(f"language catalog entries must contain text only: {path}")
    if any(not value.strip() for value in actual.values()):
        fail(f"language catalog entries must not be empty: {path}")
    if any(value != value.strip() for value in actual.values()):
        fail(f"language catalog entries must not contain surrounding whitespace: {path}")
    return actual


def format_placeholders(text: str, path: Path, key: str) -> list[str]:
    """Return positional placeholders after rejecting malformed brace syntax."""
    placeholders = re.findall(r"\{\d+\}", text)
    remainder = re.sub(r"\{\d+\}", "", text)
    if "{" in remainder or "}" in remainder:
        fail(f"language catalog entry contains malformed placeholders: {path}: {key}")
    return sorted(placeholders)


def validate_languages(package: Path) -> None:
    """Require complete keyed and DefInjected catalogs for supported languages."""
    languages = package / "Languages"
    require_directory(languages)
    translations = ("ChineseSimplified", "French", "German", "Russian", "Spanish")
    english_catalogs = {
        "Keyed/LongEventHandler.xml": {
            "PCA_LongEvent_Initialize": "Initializing Piped CE Autoloaders",
        },
        "Keyed/Settings.xml": {
            "PCA_Settings_Category": "Piped CE Autoloaders",
            "PCA_Settings_Restart_Message": "Piped CE Autoloaders settings were saved. Restart RimWorld to apply the new network configuration.",
            "PCA_Settings_RestartNow": "Restart now",
            "PCA_Settings_Later": "Later",
            "PCA_Settings_Restart_Title": "Restart required",
            "PCA_Settings_Overview": "Each color network carries one exact Combat Extended ammunition type and has independent reload speed and magazine capacity settings. Changes apply after restarting RimWorld.",
            "PCA_Settings_RebindingWarning": "After restart, existing stored rounds and autoloader contents adopt the new ammunition binding, and input filters update automatically. Empty magazines before reducing capacity.",
            "PCA_Settings_AmberNetwork": "Amber network",
            "PCA_Settings_BlueNetwork": "Blue network",
            "PCA_Settings_GreenNetwork": "Green network",
            "PCA_Settings_AmmoSet": "Caliber",
            "PCA_Settings_ExactRound": "Exact round",
            "PCA_Settings_ReloadSpeed": "Reload speed: {0}x",
            "PCA_Settings_ReloadSpeedTooltip": "Higher values make adjacent turret reloads faster.",
            "PCA_Settings_MagazineCapacity": "Magazine capacity: {0}",
            "PCA_Settings_MagazineCapacityTooltip": "Maximum rounds stored by each magazine on this network.",
            "PCA_Settings_Error_Network": "{0}: {1}",
            "PCA_Settings_Error_AmmoSetMissing": "ammo set '{0}' was not found",
            "PCA_Settings_Error_RoundMissing": "round '{0}' was not found",
            "PCA_Settings_Error_RoundUnusable": "round '{0}' is not a usable physical ammunition type",
            "PCA_Settings_Error_RoundNotInSet": "round '{0}' does not belong to ammo set '{1}'",
            "PCA_Settings_Error_RoundAlreadyAssigned": "round '{0}' is already assigned to another network",
        },
    }
    injected_paths = (
        "DefInjected/DesignationCategoryDef/PipeNetworks.xml",
        "DefInjected/ThingDef/Buildings.xml",
    )
    expected_files = {f"English/{path}" for path in english_catalogs}
    expected_files.update(
        f"{language}/{path}"
        for language in translations
        for path in (*english_catalogs, *injected_paths)
    )
    files = {
        path.relative_to(languages).as_posix()
        for path in languages.rglob("*")
        if path.is_file()
    }
    if files != expected_files:
        fail("Languages must contain exactly the supported keyed and DefInjected catalogs")
    parse_xml_files(languages)

    # English remains the exact source contract. Translations may reorder prose
    # and placeholders, but must retain every key and placeholder occurrence.
    allowed_unchanged_keys = {"PCA_Settings_Category", "PCA_Settings_Error_Network"}
    for relative_path, expected_entries in english_catalogs.items():
        english_path = languages / "English" / relative_path
        if language_entries(english_path) != expected_entries:
            fail(f"English keyed catalog does not match its reviewed source text: {english_path}")
        for language in translations:
            path = languages / language / relative_path
            actual = language_entries(path)
            if set(actual) != set(expected_entries):
                fail(f"translated keyed catalog does not match the English key set: {path}")
            for key, english_text in expected_entries.items():
                if format_placeholders(actual[key], path, key) != format_placeholders(english_text, english_path, key):
                    fail(f"translated keyed entry changed placeholders: {path}: {key}")
                if actual[key] == english_text and key not in allowed_unchanged_keys:
                    fail(f"translated keyed entry unexpectedly falls back to English: {path}: {key}")

    # DefInjected coverage mirrors every concrete player-facing Def field. The
    # translated prose is deliberately not frozen in this validator so native
    # speakers can improve wording without duplicating it in maintained code.
    networks_root = ET.parse(package / "Defs" / "PipeSystem" / "ConfigurableNetworks.xml").getroot()
    autoloaders_root = ET.parse(package / "Defs" / "Buildings" / "Autoloaders.xml").getroot()
    english_things = {}
    for root in (networks_root, autoloaders_root):
        for thing in root.findall("ThingDef"):
            def_name = thing.findtext("defName")
            if def_name:
                english_things[f"{def_name}.label"] = thing.findtext("label", default="").strip()
                english_things[f"{def_name}.description"] = thing.findtext("description", default="").strip()
    category = networks_root.find("DesignationCategoryDef")
    english_category = {"PipedCEAutoloaders_PipeNetworks.label": category.findtext("label").strip()}
    for language in translations:
        category_path = languages / language / injected_paths[0]
        category_entries = language_entries(category_path)
        if set(category_entries) != set(english_category):
            fail(f"translated architect category does not match the English key set: {category_path}")
        if category_entries == english_category:
            fail(f"translated architect category unexpectedly falls back to English: {category_path}")

        things_path = languages / language / injected_paths[1]
        thing_entries = language_entries(things_path)
        if set(thing_entries) != set(english_things):
            fail(f"translated ThingDef catalog does not match the concrete English Def fields: {things_path}")
        for key, english_text in english_things.items():
            if thing_entries[key] == english_text:
                fail(f"translated ThingDef entry unexpectedly falls back to English: {things_path}: {key}")


def validate_png(path: Path, dimensions: tuple[int, int], color_type: int) -> None:
    """Decode the complete PNG stream rather than trusting header metadata."""
    require_file(path)
    idat = bytearray()
    header_data = None
    saw_iend = False
    try:
        with path.open("rb") as stream:
            if stream.read(8) != b"\x89PNG\r\n\x1a\n":
                fail(f"file is not a PNG: {path}")
            chunk_index = 0
            while not saw_iend:
                chunk_header = stream.read(8)
                if len(chunk_header) != 8:
                    fail(f"PNG has a truncated chunk header: {path}")
                length, chunk_type = struct.unpack(">I4s", chunk_header)
                if length > 100 * 1024 * 1024:
                    fail(f"PNG chunk exceeds the package safety limit: {path}")
                data, checksum = stream.read(length), stream.read(4)
                if len(data) != length or len(checksum) != 4:
                    fail(f"PNG has a truncated chunk: {path}")
                if zlib.crc32(chunk_type + data) & 0xFFFFFFFF != struct.unpack(">I", checksum)[0]:
                    fail(f"PNG has an invalid chunk checksum: {path}")
                chunk_index += 1
                if chunk_index == 1:
                    if chunk_type != b"IHDR" or length != 13:
                        fail(f"PNG does not begin with a valid IHDR: {path}")
                    header_data = data
                elif chunk_type == b"IDAT":
                    idat.extend(data)
                elif chunk_type == b"IEND":
                    if length != 0 or stream.read(1):
                        fail(f"PNG has an invalid terminal chunk or trailing data: {path}")
                    saw_iend = True
    except (OSError, struct.error) as error:
        fail(f"cannot read PNG {path}: {error}")
    if header_data is None or not idat or not saw_iend:
        fail(f"PNG is missing required image chunks: {path}")
    width, height, bit_depth, actual_color_type, compression, filtering, interlace = struct.unpack(">IIBBBBB", header_data)
    if (width, height) != dimensions or (bit_depth, actual_color_type, compression, filtering, interlace) != (8, color_type, 0, 0, 0):
        mode = "RGBA" if color_type == 6 else "RGB"
        fail(f"PNG must be an 8-bit non-interlaced {mode} image at {dimensions[0]}x{dimensions[1]}: {path}")
    channels = 4 if color_type == 6 else 3
    expected_size = height * (1 + width * channels)
    try:
        decompressor = zlib.decompressobj()
        decoded = decompressor.decompress(bytes(idat), expected_size + 1)
        if decompressor.unconsumed_tail or len(decoded) > expected_size:
            fail(f"PNG image data expands beyond its declared dimensions: {path}")
        decoded += decompressor.flush()
    except zlib.error as error:
        fail(f"PNG image data cannot be decoded in {path}: {error}")
    if not decompressor.eof or decompressor.unused_data or len(decoded) != expected_size:
        fail(f"PNG image data has an unexpected decoded size: {path}")
    row_size = 1 + width * channels
    if any(decoded[row * row_size] > 4 for row in range(height)):
        fail(f"PNG image data uses an invalid scanline filter: {path}")


def validate_textures(package: Path) -> None:
    """Phase 6: constrain custom sprites to exact paths and game-ready PNGs."""
    textures = package / "Textures"
    require_directory(textures)
    texture_root = textures / "Things" / "Building" / "PipedCEAutoloaders"
    expected = {
        f"Things/Building/PipedCEAutoloaders/{slot}{kind}.png": (256, 256) if kind == "Magazine" else (128, 128)
        for slot in ("Amber", "Blue", "Green")
        for kind in ("Autoloader", "Input", "Magazine")
    }
    files = {path.relative_to(textures).as_posix() for path in textures.rglob("*") if path.is_file()}
    if files != set(expected):
        fail("Textures must contain exactly the three color variants for each custom building graphic")
    require_directory(texture_root)
    for relative, dimensions in expected.items():
        validate_png(textures / relative, dimensions, color_type=6)


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
        fail("package must contain exactly About, Defs, Languages, Textures, LoadFolders.xml, LICENSE, THIRD_PARTY_NOTICES.md, and 1.6")
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
    about_files = {path.name for path in about.iterdir()}
    expected_about_files = {"About.xml", "ModIcon.png", "Preview.png", "PublishedFileId.txt"}
    if about_files != expected_about_files:
        fail("About must contain exactly About.xml, ModIcon.png, Preview.png, and PublishedFileId.txt")
    require_file(about / "About.xml")
    published_file_id = about / "PublishedFileId.txt"
    require_file(published_file_id)
    if published_file_id.read_text(encoding="ascii").splitlines() != [WORKSHOP_ID]:
        fail(f"About/PublishedFileId.txt must contain exactly the Workshop ID {WORKSHOP_ID}")
    if "ModIcon.png" in about_files:
        validate_png(about / "ModIcon.png", (256, 256), color_type=6)
    if "Preview.png" in about_files:
        validate_png(about / "Preview.png", (630, 330), color_type=2)
    load_folders = package / "LoadFolders.xml"
    require_file(load_folders)
    require_file(package / "LICENSE")
    require_file(package / "THIRD_PARTY_NOTICES.md")
    mapping = load_folder_mapping(load_folders)
    parse_xml_files(about)
    validate_defs(package)
    validate_languages(package)
    validate_textures(package)
    for version in EXPECTED_VERSIONS:
        validate_version(package, version)

    # Phase 3: enforce the user-facing identity and hard dependencies. The
    # installed game check remains advisory because package validity must not
    # depend on the maintainer's currently selected RimWorld version.
    metadata = ET.parse(about / "About.xml").getroot()
    name = metadata.findtext("name", default="").strip()
    description = metadata.findtext("description", default="").strip()
    package_id = metadata.findtext("packageId", default="").strip()
    mod_version = metadata.findtext("modVersion", default="").strip()
    project_url = metadata.findtext("url", default="").strip()
    versions = [element.text.strip() for element in metadata.findall("./supportedVersions/li") if element.text and element.text.strip()]
    dependency_elements = metadata.findall("./modDependencies/li")
    dependencies = {element.findtext("packageId", default="").strip() for element in dependency_elements}
    if name != "Piped CE Autoloaders":
        fail(f"About/About.xml has an unexpected name: {name!r}")
    if "does not yet provide piped ammunition delivery" in description:
        fail("About description must reflect the packaged Phase 2 pipe-backed loader")
    if package_id != "Sanicek.PipedCEAutoloaders" or not PACKAGE_ID.fullmatch(package_id):
        fail(f"About/About.xml has an invalid packageId: {package_id!r}")
    if not SEMVER.fullmatch(mod_version):
        fail(f"About/About.xml modVersion is not valid SemVer: {mod_version!r}")
    if project_url != PROJECT_URL:
        fail(f"About/About.xml must link to the canonical project URL: {PROJECT_URL}")
    if versions != [mapping["v1.6"][-1]]:
        fail("About supportedVersions must exactly be [1.6]")
    if dependencies != {"CETeam.CombatExtended", "OskarPotocki.VanillaFactionsExpanded.Core"}:
        fail("About must declare hard Combat Extended and Vanilla Expanded Framework dependencies")
    if any(not element.findtext("downloadUrl", default="").strip() for element in dependency_elements):
        fail("each hard dependency must provide a downloadUrl")
    for element in dependency_elements:
        dependency_id = element.findtext("packageId", default="").strip()
        workshop_url = element.findtext("steamWorkshopUrl", default="").strip()
        if workshop_url != DEPENDENCY_WORKSHOP_URLS[dependency_id]:
            fail(f"{dependency_id} must provide its canonical Steam Workshop URL")

    if args.rimworld_dir:
        version = installed_version(args.rimworld_dir)
        if version:
            series = ".".join(version.split(".")[:2])
            if version not in versions and series not in versions:
                print(f"Warning: installed RimWorld {version} is not listed in supportedVersions ({', '.join(versions)}).", file=sys.stderr)

    print(f"Package validation succeeded: {package}")


if __name__ == "__main__":
    main()
