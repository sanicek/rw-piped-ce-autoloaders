#!/usr/bin/env bash
set -euo pipefail

# Build produces a disposable, validator-approved release package from the
# maintained source tree. Runtime dependencies are compile references only:
# their assemblies must exist locally but must never be copied into the mod.

# Phase 1: establish the package contract and locate portable dependencies.
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
rimworld_input="${RIMWORLD_DIR:-${HOME:?HOME must be set}/.steam/steam/steamapps/common/RimWorld}"
project="$repo_root/Source/PipedCEAutoloaders/PipedCEAutoloaders.csproj"
metadata="$repo_root/About/About.xml"
artifact_dir="$repo_root/artifacts/PipedCEAutoloaders"
built_dll="$repo_root/Source/PipedCEAutoloaders/bin/Release/net472/PipedCEAutoloaders.dll"
versions=("1.6")

# About.xml is the single release-version source used by RimWorld, the assembly,
# release archives, tags, and GitHub releases. XML parsing avoids fragile text
# extraction when metadata formatting changes.
mod_version="$(python3 -c 'import sys, xml.etree.ElementTree as ET; print(ET.parse(sys.argv[1]).getroot().findtext("modVersion", "").strip())' "$metadata")"
if [[ ! "$mod_version" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$ ]]; then
    printf 'Error: About/About.xml modVersion is not valid SemVer: %s\n' "$mod_version" >&2
    exit 1
fi

canonical_dir() {
    if [[ ! -d "$1" ]]; then
        printf 'Error: required directory does not exist: %s\n' "$1" >&2
        exit 1
    fi
    realpath -e -- "$1"
}

dependency_dir() {
    local name="$1" configured="$2" sibling="$3" home_checkout="$4" variable="$5"
    if [[ -n "$configured" ]]; then
        canonical_dir "$configured"
    elif [[ -d "$sibling" ]]; then
        canonical_dir "$sibling"
    elif [[ -d "$home_checkout" ]]; then
        canonical_dir "$home_checkout"
    else
        printf 'Error: %s directory is required. Set %s (or place it at %s).\n' "$name" "$variable" "$sibling" >&2
        exit 1
    fi
}

# Explicit environment directories take precedence over conventional checkouts.
# The build currently requires a CE checkout as its integration reference and,
# separately, a built CombatExtended.dll from that checkout, an explicit
# override, or the installed mod.
rimworld_dir="$(canonical_dir "$rimworld_input")"
managed_dir="$(canonical_dir "$rimworld_dir/RimWorldLinux_Data/Managed")"
combat_extended_dir="$(dependency_dir "Combat Extended" "${COMBAT_EXTENDED_DIR:-}" "$repo_root/../CombatExtended" "${HOME:?HOME must be set}/gitproj/public/CombatExtended" "COMBAT_EXTENDED_DIR")"
vanilla_expanded_framework_dir="$(dependency_dir "Vanilla Expanded Framework" "${VANILLA_EXPANDED_FRAMEWORK_DIR:-}" "$repo_root/../VanillaExpandedFramework" "${HOME:?HOME must be set}/gitproj/public/VanillaExpandedFramework" "VANILLA_EXPANDED_FRAMEWORK_DIR")"

if [[ -n "${COMBAT_EXTENDED_ASSEMBLY:-}" ]]; then
    combat_extended_assembly="$(realpath -e -- "$COMBAT_EXTENDED_ASSEMBLY")"
elif [[ -f "$combat_extended_dir/Assemblies/CombatExtended.dll" ]]; then
    combat_extended_assembly="$(realpath -e -- "$combat_extended_dir/Assemblies/CombatExtended.dll")"
elif [[ -f "$rimworld_dir/Mods/CombatExtended/Assemblies/CombatExtended.dll" ]]; then
    combat_extended_assembly="$(realpath -e -- "$rimworld_dir/Mods/CombatExtended/Assemblies/CombatExtended.dll")"
else
    printf 'Error: a built CombatExtended.dll is required. Set COMBAT_EXTENDED_ASSEMBLY or build/install Combat Extended.\n' >&2
    exit 1
fi

if [[ ! -f "$project" || ! -f "$managed_dir/Assembly-CSharp.dll" || ! -f "$combat_extended_assembly" || ! -f "$vanilla_expanded_framework_dir/1.6/Assemblies/PipeSystem.dll" ]]; then
    printf 'Error: project, RimWorld Assembly-CSharp.dll, CombatExtended.dll, or PipeSystem.dll is missing.\n' >&2
    exit 1
fi

# Phase 2: restore the locked dependency graph and compile against the resolved
# game and mod APIs. The project file independently checks the reference files
# needed by direct dotnet builds before reference resolution.
printf 'Repository: %s\nVersion: %s\nRimWorld: %s\nManaged DLLs: %s\nCombat Extended: %s\nCombat Extended assembly: %s\nVanilla Expanded Framework: %s\n' "$repo_root" "$mod_version" "$rimworld_dir" "$managed_dir" "$combat_extended_dir" "$combat_extended_assembly" "$vanilla_expanded_framework_dir"
dotnet restore "$project" --locked-mode
dotnet build "$project" --configuration Release --no-restore -p:ModVersion="$mod_version" -p:RimWorldManagedDir="$managed_dir" -p:CombatExtendedDir="$combat_extended_dir" -p:CombatExtendedAssembly="$combat_extended_assembly" -p:VanillaExpandedFrameworkDir="$vanilla_expanded_framework_dir"

if [[ ! -f "$built_dll" ]]; then
    printf 'Error: build output is missing: %s\n' "$built_dll" >&2
    exit 1
fi

# Phase 3: regenerate the package from a deliberately small allowlist. Every
# entry in versions must agree with LoadFolders.xml, About.xml, and the package
# validator; only this mod's assembly belongs in each runtime folder.
rm -rf -- "$artifact_dir"
mkdir -p -- "$artifact_dir"
cp -a -- "$repo_root/About" "$artifact_dir/"
cp -a -- "$repo_root/Defs" "$artifact_dir/"
cp -a -- "$repo_root/Languages" "$artifact_dir/"
cp -a -- "$repo_root/Textures" "$artifact_dir/"
cp -- "$repo_root/LoadFolders.xml" "$artifact_dir/LoadFolders.xml"
cp -- "$repo_root/LICENSE" "$artifact_dir/LICENSE"
cp -- "$repo_root/THIRD_PARTY_NOTICES.md" "$artifact_dir/THIRD_PARTY_NOTICES.md"
for version in "${versions[@]}"; do
    mkdir -p -- "$artifact_dir/$version/Assemblies"
    cp -- "$built_dll" "$artifact_dir/$version/Assemblies/PipedCEAutoloaders.dll"
done

# Phase 4: reject malformed or accidentally expanded output before reporting a
# usable artifact.
python3 "$repo_root/scripts/validate-package.py" "$artifact_dir" --rimworld-dir "$rimworld_dir"
printf 'Success: packaged Piped CE Autoloaders at %s\n' "$artifact_dir"
