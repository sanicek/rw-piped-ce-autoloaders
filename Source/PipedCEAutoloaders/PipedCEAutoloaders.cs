using System;
using System.Collections.Generic;
using System.Globalization;
using CombatExtended;
using CombatExtended.CombatExtended.Jobs.Utils;
using CombatExtended.Compatibility;
using HarmonyLib;
using PipeSystem;
using RimWorld;
using UnityEngine;
using Verse;
using Verse.AI;
using Verse.Sound;

// The runtime keeps CE authoritative over turret reloads while VEF remains
// authoritative over bulk resource storage. Startup binds each pipe network to
// one physical round and its configured performance; inputs convert items into
// pipe units, and loaders move only whole rounds into CE's durable buffer.
namespace PipedCEAutoloaders
{
    /// <summary>
    /// Owns startup ordering and the restart-required settings contract.
    /// </summary>
    public sealed class PipedCEAutoloadersMod : Mod
    {
        private readonly PipedCEAutoloadersSettingsWindow settingsWindow;
        private readonly string startupSettingsSnapshot;

        internal static PipedCEAutoloadersSettings Settings { get; private set; }

        public PipedCEAutoloadersMod(ModContentPack content)
            : base(content)
        {
            Settings = GetSettings<PipedCEAutoloadersSettings>();
            settingsWindow = new PipedCEAutoloadersSettingsWindow(Settings);
            startupSettingsSnapshot = SettingsSnapshot();
            new Harmony("Sanicek.PipedCEAutoloaders").PatchAll();
            LongEventHandler.QueueLongEvent(
                PipedAmmoBindings.Initialize,
                "PCA_LongEvent_Initialize",
                false,
                null);
        }

        public override string SettingsCategory()
        {
            return "PCA_Settings_Category".Translate();
        }

        public override void DoSettingsWindowContents(Rect inRect)
        {
            settingsWindow.Draw(inRect);
        }

        public override void WriteSettings()
        {
            base.WriteSettings();
            if (startupSettingsSnapshot != SettingsSnapshot())
            {
                Find.WindowStack.Add(new Dialog_MessageBox(
                    "PCA_Settings_Restart_Message".Translate(),
                    "PCA_Settings_RestartNow".Translate(),
                    GenCommandLine.Restart,
                    "PCA_Settings_Later".Translate(),
                    null,
                    "PCA_Settings_Restart_Title".Translate()));
            }
        }

        private static string SettingsSnapshot()
        {
            return string.Join("|", new[]
            {
                Settings.amberAmmoSet,
                Settings.amberAmmo,
                Settings.amberReloadSpeed.ToString("R", CultureInfo.InvariantCulture),
                Settings.amberTankCapacity.ToString("R", CultureInfo.InvariantCulture),
                Settings.blueAmmoSet,
                Settings.blueAmmo,
                Settings.blueReloadSpeed.ToString("R", CultureInfo.InvariantCulture),
                Settings.blueTankCapacity.ToString("R", CultureInfo.InvariantCulture),
                Settings.greenAmmoSet,
                Settings.greenAmmo,
                Settings.greenReloadSpeed.ToString("R", CultureInfo.InvariantCulture),
                Settings.greenTankCapacity.ToString("R", CultureInfo.InvariantCulture)
            });
        }
    }

    // Piped loaders must have a single supply path. These shared predicates
    // identify when CE's pawn-driven refill and turret-reload jobs would bypass
    // pipe accounting, while leaving CE's native autoloader-to-turret path
    // untouched.
    internal static class PipedAutoloaderRestrictions
    {
        internal static bool HasAdjacentPipedAutoloader(Thing thing)
        {
            if (thing?.Spawned != true)
            {
                return false;
            }

            var adjacentThings = new List<Thing>();
            GenAdjFast.AdjacentThings8Way(thing, adjacentThings);
            foreach (Thing adjacentThing in adjacentThings)
            {
                if (adjacentThing is Building_PipeBackedAutoloaderCE loader
                    && loader.HasValidBinding)
                {
                    return true;
                }
            }

            return false;
        }

        internal static IEnumerable<Toil> EndAsIncompletable(JobDriver jobDriver)
        {
            yield return new Toil
            {
                initAction = () => jobDriver.EndJobWith(JobCondition.Incompletable),
                defaultCompleteMode = ToilCompleteMode.Instant
            };
        }
    }

    /// <summary>
    /// Selects the item-consuming resource component declared by the input Defs.
    /// </summary>
    public sealed class CompProperties_PipedAmmoInput : CompProperties_Resource
    {
        public CompProperties_PipedAmmoInput()
        {
            compClass = typeof(CompPipedAmmoInput);
        }
    }

    // Consumed items become pendingResource before distribution. Persisting that
    // intermediate value prevents a full network or save/load boundary from
    // losing already-consumed rounds; the input does not consume another stack
    // until the previous value has reached storage.
    /// <summary>
    /// Atomically converts configured physical ammunition into pipe resource.
    /// </summary>
    public sealed class CompPipedAmmoInput : CompResource
    {
        private float pendingResource;

        // Building_Storage persists its player-facing filter in each save. The
        // startup binding is authoritative, so every spawned input replaces
        // that saved filter while retaining its priority and any item already
        // occupying the input cell.
        public override void PostSpawnSetup(bool respawningAfterLoad)
        {
            base.PostSpawnSetup(respawningAfterLoad);

            StorageSettings settings = (parent as Building_Storage)?.GetStoreSettings();
            if (settings?.filter == null)
            {
                return;
            }

            AmmoDef allowedAmmo = PipedAmmoBindings.For(Props.pipeNet)?.Ammo;
            settings.filter.SetDisallowAll();
            if (allowedAmmo != null)
            {
                settings.filter.SetAllow(allowedAmmo, true);
            }
        }

        public override void PostExposeData()
        {
            base.PostExposeData();
            Scribe_Values.Look(ref pendingResource, "pendingPipeResource", 0f);
        }

        public override void CompTick()
        {
            base.CompTick();
            PipedAmmoBinding binding = PipedAmmoBindings.For(Props.pipeNet);
            if (binding == null || PipeNet == null)
            {
                return;
            }

            FlushPendingResource();
            if (pendingResource > 0.0001f)
            {
                return;
            }

            Thing heldAmmo = parent.Position.GetThingList(parent.Map)
                .Find(thing => thing.def == binding.Ammo);
            if (heldAmmo == null)
            {
                return;
            }

            CompApparelReloadable reloadable = heldAmmo.TryGetComp<CompApparelReloadable>();
            int roundsPerItem = reloadable?.RemainingCharges ?? binding.Ammo.ammoCount;
            if (roundsPerItem <= 0)
            {
                heldAmmo.Destroy();
                return;
            }
            int itemsToConsume = Math.Min(
                heldAmmo.stackCount,
                (int)Math.Floor(PipeNet.AvailableCapacity / roundsPerItem));
            if (itemsToConsume <= 0)
            {
                return;
            }

            heldAmmo.SplitOff(itemsToConsume).Destroy();
            pendingResource = itemsToConsume * roundsPerItem;
            FlushPendingResource();
        }

        public override void PostDeSpawn(Map map, DestroyMode mode = DestroyMode.Vanish)
        {
            if (mode != DestroyMode.WillReplace && pendingResource > 0f)
            {
                FlushPendingResource();
                if (pendingResource > 0.0001f)
                {
                    Log.Warning($"PipedCEAutoloaders: unable to store {pendingResource} consumed rounds while despawning {parent.Label}; the unreturnable rounds were discarded.");
                    pendingResource = 0f;
                }
            }
            base.PostDeSpawn(map, mode);
        }

        private void FlushPendingResource()
        {
            if (pendingResource <= 0f || PipeNet == null)
            {
                return;
            }

            PipeNet.DistributeAmongStorage(
                pendingResource,
                out float stored,
                PipeNet.storages,
                true);
            pendingResource = Math.Max(0f, pendingResource - stored);
        }
    }

    // CE can enter the same pawn-driven operation through work scanning,
    // reservation, or toil creation. Patching all three layers keeps the
    // restriction valid for jobs created before a state change or by another
    // mod, rather than relying only on the normal work-giver path.
    [HarmonyPatch(typeof(WorkGiver_ReloadAutoLoader), nameof(WorkGiver_ReloadAutoLoader.HasJobOnThing))]
    internal static class WorkGiverReloadAutoLoaderPatch
    {
        private static bool Prefix(Thing t, ref bool __result)
        {
            if (!(t is Building_PipeBackedAutoloaderCE))
            {
                return true;
            }

            __result = false;
            return false;
        }
    }

    [HarmonyPatch(typeof(JobDriver_ReloadAutoLoader), nameof(JobDriver_ReloadAutoLoader.TryMakePreToilReservations))]
    internal static class JobDriverReloadAutoLoaderPatch
    {
        private static bool Prefix(JobDriver_ReloadAutoLoader __instance, ref bool __result)
        {
            if (!(__instance.job?.targetA.Thing is Building_PipeBackedAutoloaderCE))
            {
                return true;
            }

            __result = false;
            return false;
        }
    }

    [HarmonyPatch(typeof(JobDriver_ReloadAutoLoader), nameof(JobDriver_ReloadAutoLoader.MakeNewToils))]
    internal static class JobDriverReloadAutoLoaderToilsPatch
    {
        private static bool Prefix(JobDriver_ReloadAutoLoader __instance, ref IEnumerable<Toil> __result)
        {
            if (!(__instance.job?.targetA.Thing is Building_PipeBackedAutoloaderCE))
            {
                return true;
            }

            __result = PipedAutoloaderRestrictions.EndAsIncompletable(__instance);
            return false;
        }
    }

    // Manual turret reload has equivalent discovery and execution paths. It is
    // blocked only while a valid piped loader occupies CE's native eight-way
    // adjacency, so ordinary CE turret reloading remains available elsewhere.
    [HarmonyPatch(typeof(JobGiverUtils_Reload), nameof(JobGiverUtils_Reload.CanReload))]
    internal static class TurretCanReloadPatch
    {
        private static bool Prefix(Thing thing, ref bool __result)
        {
            if (!(thing is Building_Turret)
                || !PipedAutoloaderRestrictions.HasAdjacentPipedAutoloader(thing))
            {
                return true;
            }

            __result = false;
            return false;
        }
    }

    [HarmonyPatch(
        typeof(JobGiverUtils_Reload),
        nameof(JobGiverUtils_Reload.MakeReloadJob),
        new[] { typeof(Pawn), typeof(Building_Turret) })]
    internal static class TurretMakeReloadJobPatch
    {
        private static bool Prefix(Building_Turret turret, ref Job __result)
        {
            if (!PipedAutoloaderRestrictions.HasAdjacentPipedAutoloader(turret))
            {
                return true;
            }

            __result = null;
            return false;
        }
    }

    [HarmonyPatch(typeof(JobDriver_ReloadTurret), nameof(JobDriver_ReloadTurret.TryMakePreToilReservations))]
    internal static class JobDriverReloadTurretPatch
    {
        private static bool Prefix(JobDriver_ReloadTurret __instance, ref bool __result)
        {
            if (!PipedAutoloaderRestrictions.HasAdjacentPipedAutoloader(__instance.job?.targetA.Thing))
            {
                return true;
            }

            __result = false;
            return false;
        }
    }

    [HarmonyPatch(typeof(JobDriver_ReloadTurret), nameof(JobDriver_ReloadTurret.MakeNewToils))]
    internal static class JobDriverReloadTurretToilsPatch
    {
        private static void Postfix(JobDriver_ReloadTurret __instance, ref IEnumerable<Toil> __result)
        {
            __result = AddPipedAutoloaderEndCondition(__instance, __result);
        }

        private static IEnumerable<Toil> AddPipedAutoloaderEndCondition(
            JobDriver_ReloadTurret jobDriver,
            IEnumerable<Toil> originalToils)
        {
            jobDriver.AddEndCondition(() =>
                PipedAutoloaderRestrictions.HasAdjacentPipedAutoloader(jobDriver.job?.targetA.Thing)
                    ? JobCondition.Incompletable
                    : JobCondition.Ongoing);

            foreach (Toil toil in originalToils)
            {
                yield return toil;
            }
        }
    }

    // CompAmmoUser is the durable whole-round buffer and CE remains responsible
    // for transferring it to the turret. resourceCredit retains VEF's possible
    // fractional draw between ticks; only floor(resourceCredit) is credited as
    // ammunition, so conversion can neither duplicate nor silently round away
    // pipe resource.
    /// <summary>
    /// Bridges a VEF pipe network into CE's existing autoloader state machine.
    /// </summary>
    public sealed class Building_PipeBackedAutoloaderCE : Building_AutoloaderCE
    {
        private AmmoSetDef pipeAmmoSet;
        private AmmoDef pipeAmmo;
        private CompResource resourceComp;
        private float resourceCredit;

        internal bool HasValidBinding => pipeAmmoSet != null
            && pipeAmmo != null
            && CompAmmoUser != null
            && CompAmmoUser.UseAmmo;

        public override bool ShouldBeOn(bool failureNotify = false)
        {
            return HasValidBinding && base.ShouldBeOn(failureNotify);
        }

        public override void SpawnSetup(Map map, bool respawningAfterLoad)
        {
            base.SpawnSetup(map, respawningAfterLoad);
            resourceComp = GetComp<CompResource>();
            PipedAmmoBinding binding = PipedAmmoBindings.For(resourceComp?.Props.pipeNet);
            pipeAmmoSet = binding?.AmmoSet;
            pipeAmmo = binding?.Ammo;

            if (binding == null)
            {
                Log.Error($"{GetType().Assembly.GetName().Name}: {Label} has no valid startup ammunition binding.");
                return;
            }

            bool bindingChanged = CompAmmoUser != null
                && (CompAmmoUser.CurAmmoSet != pipeAmmoSet
                    || CompAmmoUser.CurrentAmmo != pipeAmmo);
            if (!ApplyPipeBinding())
            {
                Log.Error($"{GetType().Assembly.GetName().Name}: {Label} requires Combat Extended's ammunition system.");
                return;
            }
            if (bindingChanged)
            {
                CancelReload();
            }
        }

        // Fractional credit belongs to this loader and must survive save/load
        // until it can form a whole CE round or be returned during removal.
        public override void ExposeData()
        {
            base.ExposeData();
            Scribe_Values.Look(ref resourceCredit, "pipeResourceCredit", 0f);
        }

        public override IEnumerable<Gizmo> GetGizmos()
        {
            foreach (Gizmo gizmo in base.GetGizmos())
            {
                // This boundary depends on CE emitting building gizmos before
                // GizmoAmmoStatus and all autoloader ammo-management commands
                // after it. If CE changes that order, review this suppression.
                if (gizmo is GizmoAmmoStatus)
                {
                    yield break;
                }

                yield return gizmo;
            }
        }

        // Replacement keeps state on the same instance. Every final removal
        // instead closes CE's transient reload state, materializes whole ammo
        // items, and returns fractional values to connected pipe storage where
        // capacity permits.
        public override void DeSpawn(DestroyMode mode = DestroyMode.Vanish)
        {
            CancelReload();
            StopReloadSustainer();
            if (mode != DestroyMode.WillReplace)
            {
                DropBufferedAmmo(mode == DestroyMode.KillFinalize);
                RefundResourceCredit();
            }

            base.DeSpawn(mode);
        }

        // Power and CE's base ShouldBeOn result gate both pipe withdrawal and
        // reload continuation. Invalid targets are cancelled before base.Tick
        // can finalize against stale or forbidden turret state.
        public override void Tick()
        {
            if (!HasValidBinding)
            {
                CancelReload();
                StopReloadSustainer();
                return;
            }

            bool operational = shouldBeOn;
            if (operational)
            {
                FillBufferFromPipe();
            }

            var reloadTarget = TargetTurret;
            bool cancelReload = reloadTarget != null
                && (!reloadTarget.Spawned
                    || reloadTarget.IsForbidden(Faction)
                    || reloadTarget.GetAmmo() == null
                    || CompAmmoUser == null
                    || CompAmmoUser.EmptyMagazine
                    || !operational);
            if (cancelReload)
            {
                CancelReload();
            }
            else if (ticksToComplete == 1
                && TargetAmmoUser?.Props.reloadOneAtATime == true)
            {
                // CE's continued reload otherwise rejects the turret as already busy.
                reloadTarget.SetReloading(false);
            }

            base.Tick();
        }

        private void CancelReload()
        {
            TargetTurret?.SetReloading(false);
            TargetTurret = null;
            ticksToCompleteInitial = 0;
            ticksToComplete = 0;
            isReloading = false;
        }

        private void StopReloadSustainer()
        {
            // CE does not expose its active sound. Reflection is deliberately
            // isolated here so a CE rename degrades to a one-time diagnostic
            // rather than preventing the rest of despawn cleanup.
            var sustainerField = AccessTools.Field(
                typeof(Building_AutoloaderCE),
                "reloadingSustainer");
            if (sustainerField == null
                || !typeof(Sustainer).IsAssignableFrom(sustainerField.FieldType))
            {
                Log.ErrorOnce(
                    $"{GetType().Assembly.GetName().Name}: Combat Extended's autoloader sustainer field was not found; reload sound cleanup is unavailable.",
                    193847521);
                return;
            }

            var sustainer = sustainerField.GetValue(this) as Sustainer;
            if (sustainer == null)
            {
                return;
            }

            sustainer.End();
            sustainerField.SetValue(this, null);
        }

        private void RefundResourceCredit()
        {
            if (resourceCredit <= 0f)
            {
                return;
            }

            float creditToRefund = resourceCredit;
            float stored = 0f;
            if (resourceComp?.PipeNet != null)
            {
                resourceComp.PipeNet.DistributeAmongStorage(
                    creditToRefund,
                    out stored,
                    resourceComp.PipeNet.storages,
                    true);
            }

            resourceCredit = 0f;
            float lostCredit = Math.Max(0f, creditToRefund - stored);
            if (lostCredit > 0.0001f)
            {
                Log.Warning($"{GetType().Assembly.GetName().Name}: unable to return {lostCredit} pipe units while despawning {Label}; the unreturnable credit was discarded.");
            }
        }

        private void DropBufferedAmmo(bool forcibly)
        {
            if (CompAmmoUser == null || CompAmmoUser.EmptyMagazine || CompAmmoUser.CurrentAmmo == null)
            {
                return;
            }

            AmmoDef ammo = CompAmmoUser.CurrentAmmo;
            int ammoCount = Math.Max(1, ammo.ammoCount);
            int bufferedRounds = CompAmmoUser.CurMagCount;
            int wholeItems = bufferedRounds / ammoCount;
            int remainder = bufferedRounds % ammoCount;
            CompAmmoUser.CurMagCount = 0;

            // CE may represent several rounds with one physical item. Whole
            // items can be dropped; a non-item remainder is meaningful only as
            // resource in the loader's matching pipe network.
            if (wholeItems > 0)
            {
                Thing ammoThing = ThingMaker.MakeThing(ammo);
                ammoThing.stackCount = wholeItems;
                if (!GenThing.TryDropAndSetForbidden(
                    ammoThing,
                    Position,
                    Map,
                    ThingPlaceMode.Near,
                    out Thing droppedAmmo,
                    Faction != Faction.OfPlayer))
                {
                    Log.Warning($"{GetType().Assembly.GetName().Name}: unable to drop {ammoThing.LabelCap} while despawning {Label}; the ammunition was destroyed.");
                }
                else if (forcibly)
                {
                    droppedAmmo.TakeDamage(new DamageInfo(DamageDefOf.Bullet, Rand.Range(0, 100)));
                }
            }

            if (remainder <= 0)
            {
                Notify_ColorChanged();
                return;
            }

            float stored = 0f;
            if (ammo == pipeAmmo && resourceComp?.PipeNet != null)
            {
                resourceComp.PipeNet.DistributeAmongStorage(
                    remainder,
                    out stored,
                    resourceComp.PipeNet.storages,
                    true);
            }
            float lostRounds = Math.Max(0f, remainder - stored);
            if (lostRounds > 0.0001f)
            {
                Log.Warning($"{GetType().Assembly.GetName().Name}: unable to return {lostRounds} partial-item rounds while despawning {Label}; the unreturnable rounds were discarded.");
            }
            Notify_ColorChanged();
        }

        private void FillBufferFromPipe()
        {
            if (CompAmmoUser == null || pipeAmmo == null || resourceComp?.PipeNet == null)
            {
                return;
            }

            if (!ApplyPipeBinding() || CompAmmoUser.CurMagCount >= CompAmmoUser.MagSize)
            {
                return;
            }

            int missingRounds = CompAmmoUser.MagSize - CompAmmoUser.CurMagCount;
            float amountToDraw = missingRounds - resourceCredit;
            if (amountToDraw > 0f)
            {
                resourceComp.PipeNet.DrawAmongStorage(
                    amountToDraw,
                    out float drawn,
                    resourceComp.PipeNet.storages,
                    false);
                resourceCredit += drawn;
            }

            int creditedRounds = Math.Min(
                missingRounds,
                (int)Math.Floor(resourceCredit));
            if (creditedRounds <= 0)
            {
                return;
            }

            CompAmmoUser.CurMagCount += creditedRounds;
            resourceCredit -= creditedRounds;
            Notify_ColorChanged();
        }

        private bool ApplyPipeBinding()
        {
            if (CompAmmoUser == null || pipeAmmoSet == null || pipeAmmo == null)
            {
                return false;
            }

            if (CompAmmoUser is CompVariableAmmoUser variableAmmoUser)
            {
                variableAmmoUser.SelectedAmmoSet = pipeAmmoSet;
            }
            CompAmmoUser.CurrentAmmo = pipeAmmo;
            CompAmmoUser.SelectedAmmo = pipeAmmo;
            return CompAmmoUser.UseAmmo
                && CompAmmoUser.CurAmmoSet == pipeAmmoSet
                && CompAmmoUser.CurrentAmmo == pipeAmmo;
        }
    }
}
