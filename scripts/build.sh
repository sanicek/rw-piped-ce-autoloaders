#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
rimworld_input="${RIMWORLD_DIR:-${HOME:?HOME must be set}/.steam/steam/steamapps/common/RimWorld}"
project="$repo_root/Source/PipedCEAutoloaders/PipedCEAutoloaders.csproj"
artifact_dir="$repo_root/artifacts/PipedCEAutoloaders"
built_dll="$repo_root/Source/PipedCEAutoloaders/bin/Release/net472/PipedCEAutoloaders.dll"
versions=("1.6")

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

rimworld_dir="$(canonical_dir "$rimworld_input")"
managed_dir="$(canonical_dir "$rimworld_dir/RimWorldLinux_Data/Managed")"
combat_extended_dir="$(dependency_dir "Combat Extended" "${COMBAT_EXTENDED_DIR:-}" "$repo_root/../CombatExtended" "${HOME:?HOME must be set}/gitproj/public/CombatExtended" "COMBAT_EXTENDED_DIR")"
vanilla_expanded_framework_dir="$(dependency_dir "Vanilla Expanded Framework" "${VANILLA_EXPANDED_FRAMEWORK_DIR:-}" "$repo_root/../VanillaExpandedFramework" "${HOME:?HOME must be set}/gitproj/public/VanillaExpandedFramework" "VANILLA_EXPANDED_FRAMEWORK_DIR")"

if [[ ! -f "$project" || ! -f "$managed_dir/Assembly-CSharp.dll" || ! -f "$combat_extended_dir/Source/packages/CombatExtended.dll" || ! -f "$vanilla_expanded_framework_dir/1.6/Assemblies/VEF.dll" ]]; then
    printf 'Error: project, RimWorld Assembly-CSharp.dll, CombatExtended.dll, or VEF.dll is missing.\n' >&2
    exit 1
fi

printf 'Repository: %s\nRimWorld: %s\nManaged DLLs: %s\nCombat Extended: %s\nVanilla Expanded Framework: %s\n' "$repo_root" "$rimworld_dir" "$managed_dir" "$combat_extended_dir" "$vanilla_expanded_framework_dir"
dotnet restore "$project" --locked-mode
dotnet build "$project" --configuration Release --no-restore -p:RimWorldManagedDir="$managed_dir" -p:CombatExtendedDir="$combat_extended_dir" -p:VanillaExpandedFrameworkDir="$vanilla_expanded_framework_dir"

if [[ ! -f "$built_dll" ]]; then
    printf 'Error: build output is missing: %s\n' "$built_dll" >&2
    exit 1
fi

rm -rf -- "$artifact_dir"
mkdir -p -- "$artifact_dir"
cp -a -- "$repo_root/About" "$artifact_dir/"
cp -a -- "$repo_root/Defs" "$artifact_dir/"
cp -- "$repo_root/LoadFolders.xml" "$artifact_dir/LoadFolders.xml"
for version in "${versions[@]}"; do
    mkdir -p -- "$artifact_dir/$version/Assemblies"
    cp -- "$built_dll" "$artifact_dir/$version/Assemblies/PipedCEAutoloaders.dll"
done

python3 "$repo_root/scripts/validate-package.py" "$artifact_dir" --rimworld-dir "$rimworld_dir"
printf 'Success: packaged Piped CE Autoloaders at %s\n' "$artifact_dir"
