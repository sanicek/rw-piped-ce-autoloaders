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
- Preserve VEF's float `resourceCredit` exactly enough to prevent loss or
  duplication when converting whole CE rounds.
- Exclude pawn refill paths that could bypass pipe accounting, while retaining
  CE's turret reload behavior.
- Confirm the configurable `AmmoSetDef` startup binding is viable, VEF float
  credit remains stable, and job/gizmo suppression closes all pawn-refill
  bypasses.

## Roadmap and acceptance gates

| Phase | Status | Observable success criterion |
| --- | --- | --- |
| 0 — stock CE autoloader compatibility spike | **Complete** | Confirmed in-game: the stock XML `Building_AutoloaderCE` loader is buildable, holds 400 rounds of 7.62x51mm NATO ammunition, and natively reloads an adjacent compatible CE turret. |
| 1 — one static VEF network | **Complete** | Confirmed in-game: the fixed-ammo pipe, tank, input, and debug outlet build, connect, transfer exact rounds, and preserve state across reconnect and save/load. |
| 2 — pipe-backed CE buffer | **Complete** | Confirmed in-game: the loader withdraws exact rounds into its CE buffer using `DrawAmongStorage`, preserves `resourceCredit`, survives disconnect and save/load tests, and supplies CE's native turret reload path; no settings. |
| 3 — end-to-end native CE reload | Planned | Native CE reload correctly handles partial supply, shortage, cancellation, and one-at-a-time turret scenarios. |
| 4 — close external mutation/lifecycle paths | Planned | Pawn jobs are excluded, CE ammo-management gizmos and the interaction spot are removed, and destruction, refund, and failure paths are fail-closed. |
| 5 — settings and three networks | Planned | Three restart-required selectors create immutable, validated bindings; end-to-end release validation passes. This completes the MVP. |
| 6 — existing-save settings migration | Deferred post-MVP; feasibility-dependent | A feasible migration strategy is demonstrated for existing settings/saves. It is explicitly not required for the MVP. |

Phase 0 manual acceptance passed. The stock CE gizmos and interaction spot were
also observed; these are intentionally retained by the spike and must not be
present on the final piped loader.

Phase 1 manual acceptance passed. Ten physical FMJ items converted to ten pipe
rounds, the diagnostic output withdrew one round at a time, connectivity
responded to pipe removal and replacement, and stored rounds survived save/load.

Phase 2 manual acceptance passed. The pipe-backed loader drew ammunition from
the connected tank into its CE buffer, respected network connectivity and
save/load accounting, and reloaded an adjacent compatible turret through CE's
native autoloader path.

### Phase 1 XML-only conversion note

`Ammo_762x51mmNATO_FMJ` inherits CE `AmmoDef.ammoCount = 1`, so this fixed
network uses VEF converter ratio `1`: one physical stack item is one pipe
unit/round. The diagnostic output is VEF's automatic storage converter capped
at one item; it proves exact network withdrawal and materialization after its
output cell is cleared, not a player-triggered extraction UI or Phase 2 loader
buffer behavior.
