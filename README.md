# Piped CE Autoloaders

RimWorld 1.6 mod project implementing Combat Extended autoloaders backed by
Vanilla Expanded Framework pipe networks. The Phase 3 prototype fills a fixed
7.62x51mm NATO FMJ CE buffer from the pipe network and delegates turret reloads
to Combat Extended's native autoloader path.

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

Phase 3 acceptance is pending. Use an empty CE medium turret and exactly 20
rounds in the connected pipe system. Let the loader begin reloading, forbid the
turret during progress, and confirm cancellation leaves the rounds buffered and
clears the turret's reloading state. Allow the turret again and confirm CE
transfers exactly 20 rounds, then stops with the turret still 60 rounds short.

See [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) for completed
phase evidence, the current roadmap, and deferred work.
