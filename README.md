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

## Manual Phase 1 in-game acceptance

1. With Combat Extended, Vanilla Expanded Framework, and this mod enabled,
   research Gun Turrets. Confirm the experimental ammunition-pipes category
   contains the Phase 1 pipe, tank, FMJ input, and FMJ diagnostic output.
2. Build a tank, input, and diagnostic output linked by pipes. Confirm the VEF
   pipe overlay shows one connected gold network.
3. Place exactly 10 `Ammo_762x51mmNATO_FMJ` items in the input. Once converted,
   the items disappear and the tank/network reports 10 rounds (CE defines this
   ammo's `ammoCount` as 1, so the fixed ratio is 1 item = 1 round).
4. Clear the diagnostic output cell. It should materialize exactly one FMJ item
   and reduce the tank/network by exactly one round; clear it again to repeat.
5. Deconstruct a connecting pipe: input/output must no longer share the tank's
   resource. Rebuild it and confirm the network reconnects. Save and reload
   with stored rounds, then confirm the tank amount and diagnostic withdrawal
   remain consistent.

**Pass evidence:** all four buildings are visible and buildable, connected
overlay/state is visible, 10 input items become 10 stored units, each cleared
diagnostic output withdraws/materializes one FMJ item, and disconnect/reconnect
plus save/load preserve the expected state. **Fail evidence:** missing Defs or
comps, wrong resource counts, output duplication/loss, no connectivity change,
or lost stored rounds after reload. This Phase 1 network does not feed an
autoloading buffer or provide settings.
