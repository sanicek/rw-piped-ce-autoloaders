# Piped CE Autoloaders

RimWorld 1.6 mod project. Phase 0 is an experimental proof that Combat
Extended's native XML-defined autoloader can reload a compatible turret. It is
not a piped-ammunition implementation.

## Build

Prerequisites: Python 3, a .NET SDK capable of targeting .NET Framework 4.7.2,
RimWorld 1.6, Combat Extended, and Vanilla Expanded Framework.

Set portable dependency locations when they are not sibling checkouts (the
build also recognizes `$HOME/gitproj/public/CombatExtended` and
`$HOME/gitproj/public/VanillaExpandedFramework`):

```bash
RIMWORLD_DIR=/path/to/RimWorld \
COMBAT_EXTENDED_DIR=/path/to/CombatExtended \
VANILLA_EXPANDED_FRAMEWORK_DIR=/path/to/VanillaExpandedFramework \
./scripts/build.sh
```

The build writes `artifacts/PipedCEAutoloaders/`, copies the constrained source
Defs, and runs package validation. Dependency DLLs are compile references only
and are never packaged. Install locally with `./scripts/install-local.sh` after
building (use the same environment variables if needed).

## Manual Phase 0 in-game acceptance

1. Enable Combat Extended, Vanilla Expanded Framework, and Piped CE Autoloaders
   in that order, then start/load a 1.6 test map.
2. Build or dev-spawn **experimental Phase 0 7.62mm autoloader** next to a CE
   medium turret (`Turret_Medium`, using `Gun_MediumTurret`).
3. Use the stock CE reload job to load the autoloader with physical
   7.62x51mm NATO ammunition, then allow the turret to consume its compatible
   physical ammunition.
4. Observe the native CE autoloader completing the reload: its stored ammo is
   reduced and the adjacent turret magazine increases/reloads.

**Pass evidence:** the Def loads without errors, the loader is buildable under
Security after Gun Turrets research, and native CE reload behavior transfers
the chosen physical ammo. **Fail evidence:** Def/class errors, no stock CE
reload job, rejected compatible ammo, or no adjacent-turret reload.

See [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) for the MVP
roadmap and deferred migration work.
