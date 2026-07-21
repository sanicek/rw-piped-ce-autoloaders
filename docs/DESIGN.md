# Design

## Purpose

Piped CE Autoloaders integrates Combat Extended autoloaders with Vanilla
Expanded Framework pipe networks on RimWorld 1.6. Three fixed, color-coded
networks each bind to one configured CE ammo set and one exact physical round.
One pipe unit represents one CE round.

This document preserves the architecture and compatibility decisions that must
survive implementation changes. Release-specific compatibility and smoke-test
evidence belongs in [the release records](RELEASES.md).

## Runtime model

Each network has one `PipeNetDef`. Physical inputs convert `stackCount *
AmmoDef.ammoCount` into pipe units, and a `Building_AutoloaderCE` subclass draws
whole rounds from connected VEF storage into its CE-native `CompAmmoUser`
buffer. CE's unchanged autoloader path then reloads the adjacent turret.

Bindings, reload-speed multipliers, and magazine capacities are applied once
during startup and remain immutable for the session. Startup validation rejects
missing or mismatched Defs, nonphysical rounds, and duplicate exact-round
assignments. One invalid network is disabled without affecting valid networks.

## Durable invariants

- Settings bind one `AmmoSetDef` and one compatible, non-hidden `AmmoDef` per
  network before gameplay begins.
- Loader-owned fractional VEF withdrawal credit must survive save/load and may
  never duplicate or silently round away pipe resource.
- The CE `CompAmmoUser` remains the durable ammunition buffer and CE remains the
  owner of turret reload behavior.
- Pawn refill, CE ammo-management gizmos, and adjacent manual turret reload may
  not bypass pipe accounting.
- Despawning a loader cancels both sides of an active reload and stops its sound.
- Unpowered loaders preserve buffered ammunition and credit without withdrawing
  more resource.
- Visible and hidden pipes remain ordinary transmitters on the same VEF graph.
- Stable DefNames, package ID, settings keys, and save fields are compatibility
  contracts and must not change without an explicit migration decision.

## Compatibility decisions

### Authoritative rebinding

Restart-applied settings are authoritative for existing colonies. Existing VEF
storage and pending fractional values retain their numeric round counts and
adopt the newly configured round. Existing autoloaders retain their buffered
count while replacing their saved ammo set and selected round; active reloads
are cancelled when that identity changes. Existing inputs update their filter,
while old physical ammunition remains on the map for hauling.

This deliberately avoids tracking a historical resource identity. It is simple
and deterministic, but players must understand that rebinding changes the
meaning of stored counts.

### Capacity and footprint changes

VEF may discard resource above a reduced configured capacity during load or
serialization. The mod therefore does not attempt capacity migration; players
must empty affected magazines before reducing capacity.

Magazine DefNames remain Tank-suffixed for save compatibility even though the
player-facing name is ammunition magazine. Existing buildings adopt their
current 2x2 Def footprint in place, so any future footprint change requires an
explicit migration warning and representative old-save test.

### Cover and pathing

Inputs remain standable hopper-like storage with 0.5 fill and path cost 50.
Magazines and autoloaders are pass-through-only machinery with the same 0.5
fill and path cost 50. Under Combat Extended this gives all three building
types 0.88 m cover while allowing emergency traversal and strongly preferring
an unobstructed route. Magazines retain 150 hit points and autoloaders retain
100 hit points.

On 2026-07-21, the user confirmed the representative RimWorld smoke test: the
buildings reported the intended cover and durability, allowed traversal, and
caused pawns to prefer the unobstructed route.

### Narrow integration surface

Prefer XML, inheritance, composition, and supported CE or VEF APIs. A new or
materially expanded Harmony patch requires explicit approval under `AGENTS.md`.
The current design does not patch CE's core reload methods; it suppresses only
the external mutation paths that conflict with pipe-only supply.

## Completed MVP history

The MVP was developed through representative vertical slices: stock CE
autoloading, one static VEF network, a pipe-backed CE buffer, native partial and
cancelled reloads, lifecycle closure, configurable networks, existing-save
rebinding, power, configurable performance, custom machinery graphics, and
hidden pipes. Each slice passed one focused in-game smoke test before merge.

The final representative setup confirmed that mixed visible and hidden segments
formed one network, transferred ammunition into a powered piped autoloader,
reloaded an adjacent CE turret, hid completed underground segments, resisted
attacks, and remained removable through the network designator.
