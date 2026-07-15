# Implementation plan

## Scope and architecture

RimWorld 1.6 only. The preferred design has three fixed VEF `PipeNetDef`s.
Each restart-required setting maps one network to one CE `AmmoDef`. One pipe
unit equals one CE round. Physical input converts `stackCount *
AmmoDef.ammoCount` into pipe units.

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
| 5 — settings and three networks | Planned | Three restart-required selectors create immutable, validated bindings; end-to-end release validation passes. This completes the MVP. |
| 6 — existing-save settings migration | Deferred post-MVP; feasibility-dependent | A feasible migration strategy is demonstrated for existing settings/saves. It is explicitly not required for the MVP. |

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

### Phase 1 XML-only conversion note

`Ammo_762x51mmNATO_FMJ` inherits CE `AmmoDef.ammoCount = 1`, so this fixed
network uses VEF converter ratio `1`: one physical stack item is one pipe
unit/round. The diagnostic output is VEF's automatic storage converter capped
at one item; it proves exact network withdrawal and materialization after its
output cell is cleared, not a player-triggered extraction UI or Phase 2 loader
buffer behavior.
