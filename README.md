# Piped CE Autoloaders

Piped CE Autoloaders is a RimWorld mod project scaffold. Gameplay behavior has
not yet been implemented.

## Status

The repository provides a source, build, package-validation, and local-install
workflow for RimWorld 1.6 only. The generated package contains only metadata
and the compiled scaffold assembly; no Defs or gameplay content are included.

## Build and local install

Prerequisites: Linux, Python 3, a .NET SDK compatible with .NET Framework 4.7.2
targeting, and a RimWorld installation. By default, scripts use
`$HOME/.steam/steam/steamapps/common/RimWorld`.

Build a runtime-only package:

```bash
./scripts/build.sh
```

Install the package locally:

```bash
./scripts/install-local.sh
```

To use another installation, set `RIMWORLD_DIR`:

```bash
RIMWORLD_DIR=/path/to/RimWorld ./scripts/install-local.sh
```

The generated package is written to `artifacts/PipedCEAutoloaders/`. Its
versioned layout retains `LoadFolders.xml`, which maps RimWorld 1.6 to the
`1.6/` runtime folder.

## Repository layout

- `About/` — RimWorld mod metadata
- `1.6/` — versioned runtime-folder placeholder populated when packaged
- `Source/PipedCEAutoloaders/` — C# solution, project, and minimal entry class
- `scripts/` — build, package validation, and local-install helpers
- `WORKSHOP_DESCRIPTION.md` — factual placeholder description for a future page

Source: <https://github.com/sanicek/rw-piped-ce-autoloaders>
