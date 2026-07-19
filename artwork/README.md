# Artwork Workflow

The tracked manifest defines prompts and exact game outputs. Raw Web UI
downloads, processing receipts, candidates, and contact sheets are intentionally
stored outside this repository by the sibling `rw-art-pipeline` toolkit.

Run commands through the project wrapper. Scenario is the normal generation
path; manual intake remains available for recovered or externally produced art:

```bash
./scripts/artwork.sh prompt
./scripts/artwork.sh auth scenario
./scripts/artwork.sh models gpt
./scripts/artwork.sh generate magazine --estimate-only
./scripts/artwork.sh generate magazine
./scripts/artwork.sh generate magazine --confirm-cost
./scripts/artwork.sh select magazine 4
./scripts/artwork.sh approve magazine
./scripts/artwork.sh stamp-ce-badge

# Manual fallback
./scripts/artwork.sh intake autoloader /path/to/download.png
./scripts/artwork.sh approve autoloader
./scripts/artwork.sh validate
```

`generate` refreshes and stores the four-option estimate without charging;
`--confirm-cost` submits or resumes the paid jobs, downloads every source,
normalizes every output variant, and prints one numbered contact sheet. Run
`select` with the approved option number, review its final sheet, then run
`approve`. A generation receipt prevents an interrupted command from silently
submitting another paid batch; `--restart` is the explicit escape hatch.

`stamp-ce-badge` composites CE's checksum-pinned official third-party
compatibility badge onto the approved preview. Combat Extended provides this
badge for compatible mod authors in its media pack under CE's CC BY-NC-SA 4.0
license. Run the command only after approving `preview`.

`mod-icon` is the reusable blank maker badge. `mod-icon-final` uses its uploaded
Scenario asset as an exact visual reference and renders the project-specific
lower emblem in the same dimensional style. Its selected output replaces the
blank base at `About/ModIcon.png`; raw sources and reference bindings remain in
the local pipeline state like other generation receipts.

Credentials come from `SCENARIO_API_KEY` plus `SCENARIO_API_SECRET`, or from the
mode-0600 file created interactively by `auth scenario`. Neither credentials nor
raw provider downloads enter Git. Approval does not overwrite an existing
tracked image unless `--replace` is explicitly supplied.

The linked pipe atlas is excluded from image generation because its 640x640
layout encodes exact connection states. It will be constructed deterministically
after the machine palette and line weight are established by approved sprites.
