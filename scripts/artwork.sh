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
    printf 'Usage: %s {prompt|intake|approve|validate} [arguments...]\n' "$0" >&2
    exit 2
fi

command="$1"
shift
global_args=()
if [[ -n "${RW_ART_STATE_DIR:-}" ]]; then
    global_args+=(--state-dir "$RW_ART_STATE_DIR")
fi

PYTHONPATH="$pipeline_dir" \
    exec python3 -P -m rw_art_pipeline "${global_args[@]}" "$command" "$manifest" "$@"
