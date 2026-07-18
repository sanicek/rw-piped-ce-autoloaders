# Implementation plan

## Scope and architecture

RimWorld 1.6 only. The preferred design has three fixed VEF `PipeNetDef`s.
Each restart-required setting maps one network to one CE `AmmoDef`. One pipe
unit equals one CE round. Physical input converts `stackCount *
AmmoDef.ammoCount` into pipe units.

The same startup pass applies each network's independent reload-speed multiplier
and magazine capacity to its concrete Def. Magazines occupy 2x2 cells. Performance
settings remain immutable during a session for the same reason as bindings.

A `Building_AutoloaderCE` subclass keeps `CompAmmoUser` as the durable,
CE-native ammunition buffer. It fills that buffer through
`PipeNet.DrawAmongStorage`, then lets CE's unchanged native reload path serve
the adjacent turret. Suppress only the narrow conflicting jobs/gizmos; do not
patch CE core reload methods.

### Invariants and spike risks

- Bind each configured `AmmoSetDef` at startup; settings bindings are immutable
  during a session and must be validated before use.
- Preserve the loader-owned fractional withdrawal credit returned by VEF's
  float accounting so whole-round conversion cannot lose or duplicate resource.
- Exclude pawn refill paths that could bypass pipe accounting, while retaining
  CE's turret reload behavior.
- Confirm the configurable `AmmoSetDef` startup binding is viable, loader-owned
  fractional credit remains stable, and job/gizmo suppression closes pawn-refill
  bypasses.

## Roadmap and acceptance gates

Each gameplay phase has one representative manual smoke test: verify that the
setup introduced by that phase works in-game. The implementation and code review
still cover listed invariants and edge cases, but manual acceptance is not an
exhaustive QA matrix.

| Phase | Status | Observable success criterion |
| --- | --- | --- |
| 0 — stock CE autoloader compatibility spike | **Complete** | Confirmed in-game: the stock XML `Building_AutoloaderCE` loader is buildable, holds 400 rounds of 7.62x51mm NATO ammunition, and natively reloads an adjacent compatible CE turret. |
| 1 — one static VEF network | **Complete** | Confirmed in-game: the fixed-ammo pipe, tank, input, and debug outlet build, connect, transfer exact rounds, and preserve state across reconnect and save/load. |
| 2 — pipe-backed CE buffer | **Complete** | Confirmed in-game: a connected tank supplies the loader's CE buffer and the native autoloader path reloads an adjacent compatible turret; no settings. |
| 3 — end-to-end native CE reload | **Complete** | Confirmed in-game: pipe supply produced the expected partial turret reload, and forbidding the turret cancelled an active reload cleanly. |
| 4 — close external mutation/lifecycle paths | **Complete** | Confirmed in-game: pawn refill and CE gizmos are absent, adjacent loaders control manual turret reload eligibility without breaking native reload, and deconstruction stops an active reload and its sound. |
| 5 — settings and three networks | **Complete** | Confirmed in-game: three independent configured networks supply functional autoloaders, and restart rebinding applies to newly built network buildings. This completes the MVP. |
| 6 — authoritative existing-save rebinding | **Complete** | Confirmed in-game: existing pipe resource and autoloader counts adopted the newly configured round, while existing inputs accepted that round after restart. |
| 7 — powered autoloaders | **Complete** | Confirmed in-game: an autoloader requires power and functions only while powered. |
| 8 — compact tanks and network performance | **Complete** | Confirmed in-game: 1x2 tanks use the intended battery-scale fit and centered gauge, the `Ammo Pipes` label fits, and each network applies its configured tank capacity and reload speed. |
| 9 — custom machinery graphics and square magazines | **Complete** | Confirmed in-game: custom autoloader, input, and magazine graphics render clearly with matching network accents; all machinery retains one fixed visual orientation, and square 2x2 magazines keep their storage gauge centered on the lid. |

Phase 0 manual acceptance passed. The stock CE gizmos and interaction spot were
also observed; these are intentionally retained by the spike and must not be
present on the final piped loader.

Phase 1 manual acceptance passed. Ten physical FMJ items converted to ten pipe
rounds, the diagnostic output withdrew one round at a time, connectivity
responded to pipe removal and replacement, and stored rounds survived save/load.

Phase 2 manual acceptance passed. The pipe-backed loader drew ammunition from
the connected tank into its CE buffer and reloaded an adjacent compatible
turret through CE's native autoloader path.

Phase 3 retains CE's native partial-transfer path and permits CE's intended
one-at-a-time continuation by clearing its stale busy flag on the completion
tick. The pipe-backed subclass now also cancels invalid or inactive reloads
before CE can finalize against a cleared target, resets both sides' reload
state, and preserves the loader's buffered rounds and fractional pipe credit.
Manual acceptance passed: the pipe system supplied the loader as expected,
limited supply produced a partial turret reload, and forbidding the turret
cancelled an active reload.

Phase 4 blocks CE's normal autoloader work scan and defensively rejects refill
jobs that reach startup for the piped subclass. It also blocks manual turret
reload jobs whenever CE's native eight-way adjacency check finds a piped
autoloader, preventing physical ammo from bypassing pipe-only supply. The loader
exposes no CE ammo management gizmos or pawn interaction cell. Despawning
cancels both sides of an active reload; ordinary removal retains CE's physical
drop for whole buffered rounds and first returns fractional withdrawal credit
when connected storage has capacity. Credit that cannot be returned is warned
and discarded rather than duplicated; replacement removal leaves buffered and
credit state on the same instance. Manual acceptance passed: CE gizmos and pawn
loader refill were absent; manual turret reload worked without an adjacent
loader, was blocked when one was constructed, and resumed after its removal;
native autoloader reload continued to work; and deconstruction during an active
reload stopped its ambient sound.

Phase 5 replaces the fixed prototypes with Amber, Blue, and Green network
families. Each setting selects an `AmmoSetDef` and one exact, non-hidden
`AmmoDef` from that set. Startup validation rejects missing or mismatched Defs,
nonphysical rounds, and duplicate exact-round assignments. A rejected slot is
left unbound and cannot convert or supply rounds; valid slots remain available.
Successful bindings credit each physical item from `AmmoDef.ammoCount` (or its
remaining partial charges), configure the loader's CE ammo set, and are never
reread during gameplay. The diagnostic output was a Phase 1 test aid and is not
part of the release networks. Manual acceptance passed: all three configured
networks remained independent and supplied functional autoloaders; changing a
binding and restarting applied the new ammunition Defs to newly built buildings.
Buildings loaded from a save retained their pre-change ammo-set state. This
mixed legacy state motivated the intentionally simple authoritative rebinding
policy implemented in Phase 6.

Phase 6 treats restart-applied settings as authoritative instead of tracking or
materializing a network's former resource identity. Existing VEF storage and
pending fractional values keep their numeric round counts and therefore become
the newly configured round. Existing CE autoloaders preserve their buffered
count while replacing their saved ammo set, current round, and selected round;
any saved active reload is cancelled when that identity changes. Existing input
buildings replace their saved item filter with the configured round while
preserving storage priority and physical items already on the cell. Those old
items are no longer consumed and can be hauled to other compatible storage.
Manual acceptance passed: after rebinding and restarting, existing stored and
buffered round counts used the new binding, the existing input accepted the new
round, and old physical ammunition remained available to haul elsewhere.

Phase 7 adds a standard 100 W `CompPowerTrader` to all three autoloaders and
uses CE's native power check to gate operation. Unpowered loaders preserve their
buffered rounds and fractional pipe credit, do not withdraw additional pipe
rounds, and cancel active reloads through the existing lifecycle cleanup. Normal
pipe filling and CE reload behavior resume when power returns. Manual acceptance
passed: the autoloader required power and functioned only while powered.

Phase 8 changes the shared tank footprint from 2x2 to 1x2, renders its placeholder
at the vanilla battery's 2x3 draw scale, shortens the architect category label to
`Ammo Pipes`, centers the storage gauge on the visible tank, and adds independent
restart-required reload-speed and tank-capacity sliders for Amber, Blue, and
Green. Reload speed configures CE's `ReloadSpeed` stat from 0.1x to 5.0x in 0.1
steps; capacity configures VEF storage from 100 to 10,000 rounds in 100-round
steps. Existing defaults remain 0.5x and 1,000 rounds. Capacity reductions are
not migrated: VEF can cap existing contents during load or later serialization,
so tanks must be emptied before lowering their configured capacity. Existing
2x2 tanks also adopt the 1x2 Def in place; pre-change-save troubleshooting must
account for adjacent rooms, roofs, paths, pipe connections, and tank rotation.
Manual acceptance passed: capacity and reload-speed settings worked independently,
the tank footprint and `Ammo Pipes` label were correct, the battery placeholder
fit the occupied cells, and the storage gauge was centered on the graphic.

Phase 9 replaces the placeholder autoloader, input, and storage art with custom
network-colored sprites. Storage returns to a square 2x2 footprint and keeps its
existing Tank-suffixed DefNames for save compatibility, while user-facing labels
call it an ammunition magazine. `Graphic_Single`, disabled rotation/flip, and a
square draw size keep one visual orientation through ordinary and gravship
rotation. Existing 1x2 storage is not migrated and can obstruct adjacent cells
after the update. Manual acceptance passed: the simplified sprites were readable
and acceptable at normal game scale, the fixed orientations and magazine gauge
placement were correct, and the representative piped-autoloader setup remained
functional.

## Unprioritized future features

The following features are candidates for future implementation in no particular
order:

- Add a custom linked-pipe atlas and menu/blueprint icons.
- Add a hidden pipe variant.
- Add a mod icon.

### Phase 1 XML-only conversion note

`Ammo_762x51mmNATO_FMJ` inherits CE `AmmoDef.ammoCount = 1`, so this fixed
network uses VEF converter ratio `1`: one physical stack item is one pipe
unit/round. The diagnostic output is VEF's automatic storage converter capped
at one item; it proves exact network withdrawal and materialization after its
output cell is cleared, not a player-triggered extraction UI or Phase 2 loader
buffer behavior.
