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
    printf 'Usage: %s {prompt|intake|approve|stamp-ce-badge|validate} [arguments...]\n' "$0" >&2
    exit 2
fi

command="$1"
shift

# CE publishes this badge specifically for third-party compatible mods. Pinning
# the official media-pack source keeps that provenance explicit and prevents a
# dependency update from silently changing the approved preview.
if [[ "$command" == "stamp-ce-badge" ]]; then
    combat_extended_dir="${COMBAT_EXTENDED_DIR:-}"
    if [[ -z "$combat_extended_dir" && -d "$repo_root/../CombatExtended" ]]; then
        combat_extended_dir="$repo_root/../CombatExtended"
    elif [[ -z "$combat_extended_dir" ]]; then
        combat_extended_dir="${HOME:?HOME must be set}/gitproj/public/CombatExtended"
    fi
    badge="$combat_extended_dir/Media/Badge_CE_compatible.png"
    preview="$repo_root/About/Preview.png"
    expected_badge_sha256="9261528d1dca7c1f56d2866691119ff5bb22e1899a4c09cf983d3945036b7b09"
    expected_preview_sha256="689fcf09c4a64e9084e29abc6439ef1c54ffbc670b3ebb720c657dbf9367a859"
    if [[ ! -f "$badge" || ! -f "$preview" ]]; then
        printf 'Error: approved preview and official CE compatibility badge are required.\n' >&2
        exit 1
    fi
    actual_badge_sha256="$(sha256sum "$badge" | cut -d ' ' -f 1)"
    if [[ "$actual_badge_sha256" != "$expected_badge_sha256" ]]; then
        printf 'Error: CE badge checksum changed; review the new official asset before stamping it.\n' >&2
        exit 1
    fi
    actual_preview_sha256="$(sha256sum "$preview" | cut -d ' ' -f 1)"
    if [[ "$actual_preview_sha256" != "$expected_preview_sha256" ]]; then
        printf 'Error: preview is not the approved unstamped source; approve preview with --replace before stamping.\n' >&2
        exit 1
    fi
    if ! command -v magick >/dev/null 2>&1; then
        printf 'Error: ImageMagick is required to stamp the CE logo.\n' >&2
        exit 1
    fi
    temporary="$(mktemp "$repo_root/About/.Preview.png.XXXXXX")"
    trap 'rm -f -- "$temporary"' EXIT
    magick "$preview" \
        \( -background none "$badge" -resize 150x50 \) \
        -gravity northwest -geometry +10+270 -composite \
        -alpha off -colorspace sRGB -type TrueColor -strip \
        -define png:exclude-chunk=date,time "png:$temporary"
    mv -- "$temporary" "$preview"
    trap - EXIT
    printf 'Stamped official CE compatibility badge: %s\n' "$preview"
    exit 0
fi

global_args=()
if [[ -n "${RW_ART_STATE_DIR:-}" ]]; then
    global_args+=(--state-dir "$RW_ART_STATE_DIR")
fi

PYTHONPATH="$pipeline_dir" \
    exec python3 -P -m rw_art_pipeline "${global_args[@]}" "$command" "$manifest" "$@"
