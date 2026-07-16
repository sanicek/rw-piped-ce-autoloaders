# Piped CE Autoloaders

RimWorld 1.6 mod project implementing Combat Extended autoloaders backed by
Vanilla Expanded Framework pipe networks. Three color-coded networks each bind
to a configured CE ammo set and exact physical round after startup validation.
Pipe-backed loaders delegate turret reloads to Combat Extended's native path
while excluding pawn refill and CE ammo-management interactions.

Bindings are configured under Mod Settings. Changes require a restart and are
then immutable for the session. Duplicate, missing, hidden, or mismatched rounds
disable the affected network instead of silently changing its resource.
Changing a binding for a colony that already has stored or buffered rounds is
not supported: those untyped values would take on the new binding after the
restart. Existing-save migration is not currently planned. Empty its tanks and
loaders, then reset or rebuild its existing inputs, or use the new binding in a
new game.

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
