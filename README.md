# Piped CE Autoloaders

RimWorld 1.6 mod project implementing Combat Extended autoloaders backed by
Vanilla Expanded Framework pipe networks. Three color-coded networks each bind
to a configured CE ammo set and exact physical round after startup validation.
Pipe-backed loaders delegate turret reloads to Combat Extended's native path
while excluding pawn refill and CE ammo-management interactions. Each loader
draws 100 W and operates only while powered. Square 2x2 ammunition magazines and
independently configured network performance let each line fit a different role.
All network buildings appear under the short `Ammo Pipes` architect category.

Bindings, reload-speed multipliers, and magazine capacities are configured under Mod
Settings. Each network supports 0.1x-5.0x reload speed and 100-10,000 rounds per
magazine. Changes require a restart and are then immutable for the session.
Duplicate, missing, hidden, or mismatched rounds disable the affected network
instead of silently selecting another resource. After a binding changes and
RimWorld restarts, that setting is authoritative for existing colonies: stored
pipe resource and buffered autoloader counts become the newly selected round,
and existing input filters update to accept it. Old physical ammunition already
on an input remains on the map and can be hauled to compatible storage.

Lowering magazine capacity is also not migrated. Empty affected magazines before saving
the new setting because VEF can discard stored resource above the reduced
capacity when the colony next loads or the magazine is later serialized.

Updating an existing colony changes placed ammunition storage from 1x2 back to
2x2 in place. Empty and deconstruct existing magazines before updating when
possible. After loading an older save, inspect walls, rooms, roofs, paths, and
pipe connections around every expanded footprint and rebuild obstructed layouts.

## Build

Prerequisites: Python 3, a .NET SDK capable of targeting .NET Framework 4.7.2,
RimWorld 1.6, Combat Extended, and Vanilla Expanded Framework.

Set portable dependency locations when they are not sibling checkouts. The
build also recognizes `$HOME/gitproj/public/CombatExtended` and
`$HOME/gitproj/public/VanillaExpandedFramework`:

```bash
RIMWORLD_DIR=/path/to/RimWorld \
COMBAT_EXTENDED_DIR=/path/to/CombatExtended \
VANILLA_EXPANDED_FRAMEWORK_DIR=/path/to/VanillaExpandedFramework \
./scripts/build.sh
```

The CE source checkout is used as an integration reference. Compilation needs a
built `CombatExtended.dll`; resolution prefers the checkout's `Assemblies/`
output, then the installed CE mod. Override both with
`COMBAT_EXTENDED_ASSEMBLY=/path/to/CombatExtended.dll` when needed. Pipe APIs
compile against VEF's `1.6/Assemblies/PipeSystem.dll`, not `VEF.dll`.

The build writes `artifacts/PipedCEAutoloaders/`, copies the constrained source
Defs, and runs package validation. Dependency DLLs are compile references only
and are never packaged. Install locally with `./scripts/install-local.sh` after
building (use the same environment variables if needed).

## Artwork

Artwork is generated through Scenario, reviewed by a human, and processed
deterministically. The tracked `artwork/manifest.toml` pins each request's prompt,
model parameters, references, canvas contract, and game outputs. The sibling
`rw-art-pipeline` first estimates the cost, submits a paid four-option batch only
after explicit confirmation, and stores originals, receipts, and review sheets
outside Git. After an option is selected, approval promotes its processed color
variants into the tracked `Textures/` tree. Manual intake remains a fallback for
externally generated or recovered source images. Credentials and raw provider
downloads never enter this repository. See `artwork/README.md` for the commands.

## Maintenance style

Maintained source follows the literate programming convention in `AGENTS.md`:
files and nontrivial phases introduce their purpose, invariants, and tradeoffs
before the implementation. Comments explain why a constraint exists rather than
repeat what the syntax already says, and must change with the behavior they
describe.

Apply that convention to the active C#, scripts, build configuration, mod
metadata, version routing, and 1.6 Defs. Simple declarative files need only the
context required to maintain their contracts. Do not rewrite generated output,
dependency lockfiles, solution files, binaries, artwork, publishing IDs, legal
text, or the checksum-frozen 1.5 payload to add commentary; document their
contracts in the maintained code that produces or validates them instead.

## Manual Smoke Test

Gameplay phases use one representative in-game verification, not an exhaustive
QA matrix. After `./scripts/install-local.sh`, build the setup introduced by the
current phase and confirm its intended path works. The pull request supplies the
short setup and expected observation for that phase.

Phase 6 passed its smoke test: after rebinding and restarting, existing stored
and buffered round counts used the new binding, the existing input accepted the
new round, and old physical ammunition remained available to haul elsewhere.

See [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) for completed
phase evidence, the current roadmap, and future work.
