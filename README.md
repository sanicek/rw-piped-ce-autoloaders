# Piped CE Autoloaders

Piped CE Autoloaders adds three configurable ammunition pipe networks to
RimWorld 1.6. Physical Combat Extended ammunition enters through an intake,
moves through Vanilla Expanded Framework pipes and magazines, and fills powered
autoloaders that use CE's native turret reload behavior.

## Features

- Three independent Amber, Blue, and Green ammunition networks.
- Caliber grouping and exact physical-round binding under Mod Settings.
- Per-network 0.1x-5.0x reload speed and 100-10,000-round magazine capacity.
- Powered autoloaders that preserve CE partial reloads, shortages, and cancellation.
- Normal pipes and slower, more expensive hidden pipes on the same network.
- Complete Simplified Chinese, French, German, Russian, and Spanish translations.

## Requirements

- RimWorld 1.6
- [Combat Extended](https://steamcommunity.com/sharedfiles/filedetails/?id=2890901044)
- [Vanilla Expanded Framework](https://steamcommunity.com/workshop/filedetails/?id=2023507013)

The RimWorld mod manager declares both dependencies and loads this mod after
them. Use its automatic sort before starting a colony.

## Installation

Subscribe on the [Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=3768286113)
or download the versioned ZIP from
[GitHub Releases](https://github.com/sanicek/rw-piped-ce-autoloaders/releases).
For a manual installation, extract the ZIP's `PipedCEAutoloaders` directory into
RimWorld's `Mods` directory and enable it in the mod manager. The attached ZIP is
the supported manual download; GitHub's automatically generated source archives
are not installable mod packages.

## Configuration

Each network selects one caliber group and one exact, non-hidden physical round.
When CE uses several internal ammo sets for a caliber, their physical rounds are
combined and the required containing set is derived automatically. Bindings,
reload speeds, and magazine capacities are validated at startup and remain fixed
until RimWorld restarts. Invalid or duplicate round assignments disable only the
affected network instead of silently selecting another round.

An input converts each physical ammunition item's CE round count into pipe units.
Existing physical ammunition that no longer matches a rebound input remains on
the map and can be hauled to compatible storage.

## Updating Existing Colonies

Network settings are authoritative after restart. Rebinding a network preserves
the numeric counts in existing pipe storage and autoloader buffers but changes
those counts to the newly selected round. Existing inputs update their filters.

Lowering magazine capacity is not migrated. Empty affected magazines before
saving the new setting because VEF may discard stored rounds above the reduced
capacity during load or later serialization.

## Troubleshooting and Reports

Reports are welcome in GitHub Issues or the Steam Workshop comments after the
page is published. To make a report actionable, include:

- RimWorld, Combat Extended, Vanilla Expanded Framework, and mod versions.
- A short reproduction sequence and whether it also occurs in a new colony.
- The active mod list and load order.
- A link to the relevant `Player.log`, especially for startup or loading errors.

On Windows, `Player.log` is normally under
`%USERPROFILE%\AppData\LocalLow\Ludeon Studios\RimWorld by Ludeon Studios`.
On Linux it is under
`~/.config/unity3d/Ludeon Studios/RimWorld by Ludeon Studios`. Upload the log to
a paste or file-sharing service and link it rather than placing the whole log in
a Workshop comment.

## Building

Prerequisites are Python 3, a .NET SDK capable of targeting .NET Framework
4.7.2, RimWorld 1.6, Combat Extended, and Vanilla Expanded Framework. The build
recognizes the environment variables below and also checks the repository's
documented sibling and home-checkout locations:

```bash
RIMWORLD_DIR=/path/to/RimWorld \
COMBAT_EXTENDED_DIR=/path/to/CombatExtended \
VANILLA_EXPANDED_FRAMEWORK_DIR=/path/to/VanillaExpandedFramework \
./scripts/build.sh
```

Compilation needs a built `CombatExtended.dll`; resolution prefers the CE
checkout, then the installed CE mod. `COMBAT_EXTENDED_ASSEMBLY` can override the
assembly directly. VEF pipe APIs compile against `1.6/Assemblies/PipeSystem.dll`.
Dependency DLLs are compile references and are never included in this package.

`scripts/build.sh` creates and validates `artifacts/PipedCEAutoloaders/`.
`scripts/install-local.sh` builds and transactionally installs that package for
testing. `python3 scripts/package-release.py` creates the versioned installable
ZIP and SHA-256 checksum used by the local release workflow.

## Maintainer Documentation

- [Design and compatibility invariants](docs/DESIGN.md)
- [Release policy and records](docs/RELEASES.md)
- [Artwork workflow](artwork/README.md)
- [Repository workflow](AGENTS.md)

## Artwork and License

Project artwork is generated, reviewed, and processed through the tracked
manifest and local approval workflow. The preview uses Combat Extended's
official compatibility badge for third-party mod authors from the
[CE media pack](https://github.com/CombatExtended-Continued/CombatExtended/tree/Development/Media).

Piped CE Autoloaders is released under the [MIT License](LICENSE). Combat
Extended's compatibility badge remains subject to Combat Extended's
[CC BY-NC-SA 4.0 license](https://creativecommons.org/licenses/by-nc-sa/4.0/).
See [the third-party notice](THIRD_PARTY_NOTICES.md) for its pinned source and
the compositing performed for the preview.
