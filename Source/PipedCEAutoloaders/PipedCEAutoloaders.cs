using System;
using System.Collections.Generic;
using CombatExtended;
using CombatExtended.CombatExtended.Jobs.Utils;
using CombatExtended.Compatibility;
using HarmonyLib;
using PipeSystem;
using RimWorld;
using Verse;
using Verse.AI;

namespace PipedCEAutoloaders
{
    public sealed class PipedCEAutoloadersMod : Mod
    {
        public PipedCEAutoloadersMod(ModContentPack content)
            : base(content)
        {
            new Harmony("Sanicek.PipedCEAutoloaders").PatchAll();
        }
    }

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
                if (adjacentThing is Building_PipeBackedAutoloaderCE)
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

    public sealed class Building_PipeBackedAutoloaderCE : Building_AutoloaderCE
    {
        private const string AmmoDefName = "Ammo_762x51mmNATO_FMJ";

        private AmmoDef pipeAmmo;
        private CompResource resourceComp;
        private float resourceCredit;

        public override void SpawnSetup(Map map, bool respawningAfterLoad)
        {
            base.SpawnSetup(map, respawningAfterLoad);
            resourceComp = GetComp<CompResource>();
            pipeAmmo = DefDatabase<AmmoDef>.GetNamedSilentFail(AmmoDefName);

            if (pipeAmmo == null)
            {
                Log.Error($"{GetType().Assembly.GetName().Name}: required ammo Def {AmmoDefName} was not found.");
                return;
            }
            if (CompAmmoUser != null && !CompAmmoUser.UseAmmo)
            {
                Log.Error($"{GetType().Assembly.GetName().Name}: {Label} requires Combat Extended's ammunition system.");
                return;
            }

            SetPipeAmmoWhenSafe();
        }

        public override void ExposeData()
        {
            base.ExposeData();
            Scribe_Values.Look(ref resourceCredit, "pipeResourceCredit", 0f);
        }

        public override IEnumerable<Gizmo> GetGizmos()
        {
            foreach (Gizmo gizmo in base.GetGizmos())
            {
                // CE emits all building gizmos before this marker, followed by
                // every autoloader ammo-management command.
                if (gizmo is GizmoAmmoStatus)
                {
                    yield break;
                }

                yield return gizmo;
            }
        }

        public override void DeSpawn(DestroyMode mode = DestroyMode.Vanish)
        {
            CancelReload();
            if (mode != DestroyMode.WillReplace)
            {
                RefundResourceCredit();
            }

            base.DeSpawn(mode);
        }

        public override void Tick()
        {
            FillBufferFromPipe();

            var reloadTarget = TargetTurret;
            bool cancelReload = reloadTarget != null
                && (!reloadTarget.Spawned
                    || reloadTarget.IsForbidden(Faction)
                    || reloadTarget.GetAmmo() == null
                    || CompAmmoUser == null
                    || CompAmmoUser.EmptyMagazine
                    || !shouldBeOn);
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

        private void FillBufferFromPipe()
        {
            if (CompAmmoUser == null || pipeAmmo == null || resourceComp?.PipeNet == null)
            {
                return;
            }

            if (!SetPipeAmmoWhenSafe() || CompAmmoUser.CurMagCount >= CompAmmoUser.MagSize)
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

        private bool SetPipeAmmoWhenSafe()
        {
            if (CompAmmoUser == null || !CompAmmoUser.UseAmmo)
            {
                return false;
            }

            if (CompAmmoUser.CurrentAmmo != pipeAmmo)
            {
                if (CompAmmoUser.CurMagCount > 0)
                {
                    return false;
                }
                CompAmmoUser.CurrentAmmo = pipeAmmo;
            }

            CompAmmoUser.SelectedAmmo = pipeAmmo;
            return CompAmmoUser.CurrentAmmo == pipeAmmo;
        }
    }
}
