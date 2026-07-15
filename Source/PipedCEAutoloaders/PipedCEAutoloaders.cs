using System;
using CombatExtended;
using PipeSystem;
using Verse;

namespace PipedCEAutoloaders
{
    public sealed class PipedCEAutoloadersMod : Mod
    {
        public PipedCEAutoloadersMod(ModContentPack content)
            : base(content)
        {
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

        public override void Tick()
        {
            FillBufferFromPipe();
            base.Tick();
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
            if (!CompAmmoUser.UseAmmo)
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
