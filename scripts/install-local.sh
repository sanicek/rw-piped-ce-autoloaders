#!/usr/bin/env bash
set -euo pipefail

# Local installation is a transaction around the generated package. Validation
# completes before the current mod is moved, and failures after that point
# remove the partial replacement and restore the previous directory.

# Phase 1: record transaction state. cleanup interprets these flags so every
# reachable failure point has one owner for rollback.
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
rimworld_input="${RIMWORLD_DIR:-${HOME:?HOME must be set}/.steam/steam/steamapps/common/RimWorld}"
artifact_dir="$repo_root/artifacts/PipedCEAutoloaders"
stage_dir=""
backup_dir=""
old_target_moved=false
new_target_placed=false
commit_completed=false

canonical_dir() {
    if [[ ! -d "$1" ]]; then
        printf 'Error: required directory does not exist: %s\n' "$1" >&2
        exit 1
    fi
    realpath -e -- "$1"
}

cleanup() {
    local status=$?
    trap - EXIT
    set +e
    [[ -n "$stage_dir" && -d "$stage_dir" ]] && rm -rf -- "$stage_dir"
    if [[ "$commit_completed" != true ]]; then
        [[ "$new_target_placed" == true && ( -e "$target_dir" || -L "$target_dir" ) ]] && rm -rf -- "$target_dir"
        if [[ "$old_target_moved" == true && -n "$backup_dir" && ( -e "$backup_dir" || -L "$backup_dir" ) && ! -e "$target_dir" && ! -L "$target_dir" ]]; then
            mv -T -- "$backup_dir" "$target_dir"
        fi
    fi
    exit "$status"
}

# Phase 2: resolve the installation target before registering cleanup. Build
# failures occur before any installed mod is touched and need no rollback.
rimworld_dir="$(canonical_dir "$rimworld_input")"
mods_dir="$(canonical_dir "$rimworld_dir/Mods")"
target_dir="$mods_dir/PipedCEAutoloaders"
trap cleanup EXIT

# Phase 3: build, stage on the destination filesystem, and validate the exact
# staged tree that will become the installed mod.
"$repo_root/scripts/build.sh"
stage_dir="$(mktemp -d -- "$mods_dir/.PipedCEAutoloaders.stage.XXXXXX")"
cp -a -- "$artifact_dir/." "$stage_dir/"
python3 "$repo_root/scripts/validate-package.py" "$stage_dir" --rimworld-dir "$rimworld_dir"

# Phase 4: move the old and new directories rather than copying over a live mod.
# Keeping both moves on the Mods filesystem lets cleanup restore the old tree if
# placement or the byte-for-byte comparison fails.
if [[ -e "$target_dir" || -L "$target_dir" ]]; then
    backup_dir="$(mktemp -d -- "$mods_dir/.PipedCEAutoloaders.backup.XXXXXX")"
    rmdir -- "$backup_dir"
    old_target_moved=true
    mv -T -- "$target_dir" "$backup_dir"
fi
new_target_placed=true
mv -T -- "$stage_dir" "$target_dir"
stage_dir=""
diff -r -- "$artifact_dir" "$target_dir"

# Phase 5: commit the transaction only after the installed tree matches the
# artifact, then remove the no-longer-needed backup.
commit_completed=true
trap - EXIT
[[ -n "$backup_dir" ]] && rm -rf -- "$backup_dir"
printf 'Success: installed Piped CE Autoloaders at %s\n' "$target_dir"
