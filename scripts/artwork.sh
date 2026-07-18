#!/usr/bin/env bash
set -euo pipefail

# Artwork commands use a reusable sibling toolkit while keeping this mod's
# prompts and output contract local. Override either local path for a portable
# checkout or a disposable test archive.
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
pipeline_dir="${RW_ART_PIPELINE_DIR:-$repo_root/../rw-art-pipeline}"
manifest="$repo_root/artwork/manifest.toml"

if [[ ! -f "$pipeline_dir/rw_art_pipeline/__main__.py" ]]; then
    printf 'Error: rw-art-pipeline not found at %s; set RW_ART_PIPELINE_DIR.\n' "$pipeline_dir" >&2
    exit 1
fi
if [[ $# -lt 1 ]]; then
    printf 'Usage: %s {prompt|intake|approve|stamp-ce-logo|validate} [arguments...]\n' "$0" >&2
    exit 2
fi

command="$1"
shift

# The promotional preview uses CE's canonical sombrero mark as a deterministic
# compatibility cue. Pinning the official media-pack source protects the final
# image from silently changing when the dependency checkout moves forward.
if [[ "$command" == "stamp-ce-logo" ]]; then
    combat_extended_dir="${COMBAT_EXTENDED_DIR:-}"
    if [[ -z "$combat_extended_dir" && -d "$repo_root/../CombatExtended" ]]; then
        combat_extended_dir="$repo_root/../CombatExtended"
    elif [[ -z "$combat_extended_dir" ]]; then
        combat_extended_dir="${HOME:?HOME must be set}/gitproj/public/CombatExtended"
    fi
    logo="$combat_extended_dir/Media/CE_ModIcon_JustHat.svg"
    preview="$repo_root/About/Preview.png"
    expected_logo_sha256="6f24df16420a88dd57fc7a1aa3ecae8d21f48719a58ec4e9adf42b65f36159bb"
    if [[ ! -f "$logo" || ! -f "$preview" ]]; then
        printf 'Error: approved preview and official CE media-pack logo are required.\n' >&2
        exit 1
    fi
    actual_logo_sha256="$(sha256sum "$logo" | cut -d ' ' -f 1)"
    if [[ "$actual_logo_sha256" != "$expected_logo_sha256" ]]; then
        printf 'Error: CE logo checksum changed; review the new official asset before stamping it.\n' >&2
        exit 1
    fi
    if ! command -v magick >/dev/null 2>&1; then
        printf 'Error: ImageMagick is required to stamp the CE logo.\n' >&2
        exit 1
    fi
    temporary="$(mktemp "$repo_root/About/.Preview.png.XXXXXX")"
    trap 'rm -f -- "$temporary"' EXIT
    magick "$preview" \( -background none "$logo" -resize 96x96 \) \
        -geometry +8+226 -composite -alpha off -colorspace sRGB -type TrueColor "png:$temporary"
    mv -- "$temporary" "$preview"
    trap - EXIT
    printf 'Stamped official CE logo: %s\n' "$preview"
    exit 0
fi

global_args=()
if [[ -n "${RW_ART_STATE_DIR:-}" ]]; then
    global_args+=(--state-dir "$RW_ART_STATE_DIR")
fi

PYTHONPATH="$pipeline_dir" \
    exec python3 -P -m rw_art_pipeline "${global_args[@]}" "$command" "$manifest" "$@"
