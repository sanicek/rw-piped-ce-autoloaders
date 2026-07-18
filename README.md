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
instead of silently changing its resource.
Changing a binding for a colony that already has stored or buffered rounds is
not supported: those untyped values would take on the new binding after the
restart. Existing-save migration is not currently planned. Empty its magazines and
loaders, then reset or rebuild its existing inputs, or use the new binding in a
new game.

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

Artwork uses a manual-generation, deterministic-intake workflow. The tracked
`artwork/manifest.toml` supplies exact prompts and game asset contracts. The
reusable sibling `rw-art-pipeline` normally submits resumable Scenario API
batches, archives provider provenance and originals outside Git, presents four
final-size options, and promotes the selected candidate only after explicit
approval. Manual downloads use the same deterministic intake as a fallback.
See `artwork/README.md` for the short workflow.

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

Phase 5 passed its smoke test: all three configured networks remained
independent and supplied functional autoloaders. Changing a binding and
restarting applied the new ammunition Defs to newly built buildings; buildings
loaded from an existing save retained their prior ammo-set state, so migration
of mixed legacy state remains unsupported and is not currently planned.

See [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) for completed
phase evidence, the current roadmap, and future work.
