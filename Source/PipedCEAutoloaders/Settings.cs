using System;
using System.Collections.Generic;
using System.Linq;
using CombatExtended;
using PipeSystem;
using RimWorld;
using UnityEngine;
using Verse;

// Settings persist Def names and bounded performance values, then apply once
// after RimWorld has loaded all CE and VEF Defs. The resulting session
// configuration deliberately does not observe later writes: changing a
// network requires a restart, after which its binding authoritatively
// reinterprets existing pipe resource and loader contents as the new round.
namespace PipedCEAutoloaders
{
    /// <summary>
    /// Stores each network's resource identity and performance configuration.
    /// </summary>
    public sealed class PipedCEAutoloadersSettings : ModSettings
    {
        internal const float DefaultReloadSpeed = 0.5f;
        internal const float MinimumReloadSpeed = 0.1f;
        internal const float MaximumReloadSpeed = 5f;
        internal const float DefaultTankCapacity = 1000f;
        internal const float MinimumTankCapacity = 100f;
        internal const float MaximumTankCapacity = 10000f;

        public string amberAmmoSet = "AmmoSet_762x51mmNATO";
        public string amberAmmo = "Ammo_762x51mmNATO_FMJ";
        public float amberReloadSpeed = DefaultReloadSpeed;
        public float amberTankCapacity = DefaultTankCapacity;
        public string blueAmmoSet = "AmmoSet_556x45mmNATO";
        public string blueAmmo = "Ammo_556x45mmNATO_FMJ";
        public float blueReloadSpeed = DefaultReloadSpeed;
        public float blueTankCapacity = DefaultTankCapacity;
        public string greenAmmoSet = "AmmoSet_12Gauge";
        public string greenAmmo = "Ammo_12Gauge_Buck";
        public float greenReloadSpeed = DefaultReloadSpeed;
        public float greenTankCapacity = DefaultTankCapacity;

        public override void ExposeData()
        {
            Scribe_Values.Look(ref amberAmmoSet, "amberAmmoSet", "AmmoSet_762x51mmNATO");
            Scribe_Values.Look(ref amberAmmo, "amberAmmo", "Ammo_762x51mmNATO_FMJ");
            Scribe_Values.Look(ref amberReloadSpeed, "amberReloadSpeed", DefaultReloadSpeed);
            Scribe_Values.Look(ref amberTankCapacity, "amberTankCapacity", DefaultTankCapacity);
            Scribe_Values.Look(ref blueAmmoSet, "blueAmmoSet", "AmmoSet_556x45mmNATO");
            Scribe_Values.Look(ref blueAmmo, "blueAmmo", "Ammo_556x45mmNATO_FMJ");
            Scribe_Values.Look(ref blueReloadSpeed, "blueReloadSpeed", DefaultReloadSpeed);
            Scribe_Values.Look(ref blueTankCapacity, "blueTankCapacity", DefaultTankCapacity);
            Scribe_Values.Look(ref greenAmmoSet, "greenAmmoSet", "AmmoSet_12Gauge");
            Scribe_Values.Look(ref greenAmmo, "greenAmmo", "Ammo_12Gauge_Buck");
            Scribe_Values.Look(ref greenReloadSpeed, "greenReloadSpeed", DefaultReloadSpeed);
            Scribe_Values.Look(ref greenTankCapacity, "greenTankCapacity", DefaultTankCapacity);

            if (Scribe.mode == LoadSaveMode.PostLoadInit)
            {
                amberReloadSpeed = BoundedReloadSpeed(amberReloadSpeed);
                amberTankCapacity = BoundedTankCapacity(amberTankCapacity);
                blueReloadSpeed = BoundedReloadSpeed(blueReloadSpeed);
                blueTankCapacity = BoundedTankCapacity(blueTankCapacity);
                greenReloadSpeed = BoundedReloadSpeed(greenReloadSpeed);
                greenTankCapacity = BoundedTankCapacity(greenTankCapacity);
            }
        }

        internal string AmmoSetFor(int slot)
        {
            switch (slot)
            {
                case 0: return amberAmmoSet;
                case 1: return blueAmmoSet;
                default: return greenAmmoSet;
            }
        }

        internal string AmmoFor(int slot)
        {
            switch (slot)
            {
                case 0: return amberAmmo;
                case 1: return blueAmmo;
                default: return greenAmmo;
            }
        }

        internal float ReloadSpeedFor(int slot)
        {
            switch (slot)
            {
                case 0: return BoundedReloadSpeed(amberReloadSpeed);
                case 1: return BoundedReloadSpeed(blueReloadSpeed);
                default: return BoundedReloadSpeed(greenReloadSpeed);
            }
        }

        internal float TankCapacityFor(int slot)
        {
            switch (slot)
            {
                case 0: return BoundedTankCapacity(amberTankCapacity);
                case 1: return BoundedTankCapacity(blueTankCapacity);
                default: return BoundedTankCapacity(greenTankCapacity);
            }
        }

        internal void SetAmmoSet(int slot, string value)
        {
            switch (slot)
            {
                case 0: amberAmmoSet = value; break;
                case 1: blueAmmoSet = value; break;
                default: greenAmmoSet = value; break;
            }
        }

        internal void SetAmmo(int slot, string value)
        {
            switch (slot)
            {
                case 0: amberAmmo = value; break;
                case 1: blueAmmo = value; break;
                default: greenAmmo = value; break;
            }
        }

        internal void SetReloadSpeed(int slot, float value)
        {
            value = BoundedReloadSpeed(value);
            switch (slot)
            {
                case 0: amberReloadSpeed = value; break;
                case 1: blueReloadSpeed = value; break;
                default: greenReloadSpeed = value; break;
            }
        }

        internal void SetTankCapacity(int slot, float value)
        {
            value = BoundedTankCapacity(value);
            switch (slot)
            {
                case 0: amberTankCapacity = value; break;
                case 1: blueTankCapacity = value; break;
                default: greenTankCapacity = value; break;
            }
        }

        // Settings files are user-editable and may contain non-finite values
        // that Unity's Clamp preserves. Restore defaults before values can reach
        // CE tick math or VEF capacity accounting.
        private static float BoundedReloadSpeed(float value)
        {
            return float.IsNaN(value) || float.IsInfinity(value)
                ? DefaultReloadSpeed
                : Mathf.Clamp(value, MinimumReloadSpeed, MaximumReloadSpeed);
        }

        private static float BoundedTankCapacity(float value)
        {
            return float.IsNaN(value) || float.IsInfinity(value)
                ? DefaultTankCapacity
                : Mathf.Clamp(value, MinimumTankCapacity, MaximumTankCapacity);
        }
    }

    // A valid resource binding always pairs one exact physical AmmoDef with an
    // AmmoSetDef that contains it. Keeping both resolved Defs together prevents
    // downstream inputs and loaders from applying only half of the selection.
    internal sealed class PipedAmmoBinding
    {
        internal PipedAmmoBinding(AmmoSetDef ammoSet, AmmoDef ammo)
        {
            AmmoSet = ammoSet;
            Ammo = ammo;
        }

        internal AmmoSetDef AmmoSet { get; }
        internal AmmoDef Ammo { get; }
    }

    internal static class PipedAmmoBindings
    {
        // These arrays form one positional schema shared with the settings UI
        // and the corresponding XML Defs. Entries at each index must continue
        // to describe the same Amber, Blue, or Green network family.
        internal static readonly string[] SlotNames = { "Amber", "Blue", "Green" };

        private static readonly string[] NetworkDefNames =
        {
            "PipedCEAutoloaders_AmberNet",
            "PipedCEAutoloaders_BlueNet",
            "PipedCEAutoloaders_GreenNet"
        };

        private static readonly string[] InputDefNames =
        {
            "PipedCEAutoloaders_AmberInput",
            "PipedCEAutoloaders_BlueInput",
            "PipedCEAutoloaders_GreenInput"
        };

        private static readonly string[] LoaderDefNames =
        {
            "PipedCEAutoloaders_AmberAutoloader",
            "PipedCEAutoloaders_BlueAutoloader",
            "PipedCEAutoloaders_GreenAutoloader"
        };

        private static readonly string[] TankDefNames =
        {
            "PipedCEAutoloaders_AmberTank",
            "PipedCEAutoloaders_BlueTank",
            "PipedCEAutoloaders_GreenTank"
        };

        private static readonly Dictionary<PipeNetDef, PipedAmmoBinding> Bindings =
            new Dictionary<PipeNetDef, PipedAmmoBinding>();

        internal static PipedAmmoBinding For(PipeNetDef pipeNetDef)
        {
            if (pipeNetDef != null && Bindings.TryGetValue(pipeNetDef, out PipedAmmoBinding binding))
            {
                return binding;
            }

            return null;
        }

        internal static void Initialize()
        {
            // Initialization is a one-time session pass. Resource identity and
            // performance are applied together so instances cannot spawn with
            // a partially configured network. One invalid slot disables only
            // its own physical input while valid networks remain operational.
            Bindings.Clear();
            var usedAmmo = new HashSet<AmmoDef>();
            for (int slot = 0; slot < SlotNames.Length; slot++)
            {
                PipeNetDef network = DefDatabase<PipeNetDef>.GetNamedSilentFail(NetworkDefNames[slot]);
                ThingDef input = DefDatabase<ThingDef>.GetNamedSilentFail(InputDefNames[slot]);
                ThingDef loader = DefDatabase<ThingDef>.GetNamedSilentFail(LoaderDefNames[slot]);
                ThingDef tank = DefDatabase<ThingDef>.GetNamedSilentFail(TankDefNames[slot]);
                PipedAmmoBinding binding = Resolve(
                    PipedCEAutoloadersMod.Settings.AmmoSetFor(slot),
                    PipedCEAutoloadersMod.Settings.AmmoFor(slot),
                    usedAmmo,
                    out string error);

                CompProperties_AmmoListUser ammoProperties =
                    loader?.GetCompProperties<CompProperties_AmmoListUser>();
                CompProperties_ResourceStorage storageProperties =
                    tank?.GetCompProperties<CompProperties_ResourceStorage>();
                if (network == null || input == null || loader == null || tank == null)
                {
                    error = $"required definitions for the {SlotNames[slot]} network were not found";
                    binding = null;
                }
                else if (ammoProperties == null || storageProperties == null)
                {
                    error = $"required components for the {SlotNames[slot]} network were not found";
                    binding = null;
                }

                if (binding == null)
                {
                    DisableInput(input);
                    Log.Error($"PipedCEAutoloaders: {SlotNames[slot]} network is disabled: {error}.");
                    continue;
                }

                loader.SetStatBaseValue(
                    CE_StatDefOf.ReloadSpeed,
                    PipedCEAutoloadersMod.Settings.ReloadSpeedFor(slot));
                storageProperties.storageCapacity =
                    PipedCEAutoloadersMod.Settings.TankCapacityFor(slot);
                ConfigureInput(input, binding.Ammo);
                ammoProperties.ammoSet = binding.AmmoSet;
                ammoProperties.additionalAmmoSets.Clear();
                Bindings.Add(network, binding);
                usedAmmo.Add(binding.Ammo);
            }
        }

        internal static string ValidateSettings(PipedCEAutoloadersSettings settings)
        {
            var usedAmmo = new HashSet<AmmoDef>();
            var errors = new List<string>();
            for (int slot = 0; slot < SlotNames.Length; slot++)
            {
                PipedAmmoBinding binding = Resolve(
                    settings.AmmoSetFor(slot),
                    settings.AmmoFor(slot),
                    usedAmmo,
                    out string error);
                if (binding == null)
                {
                    errors.Add($"{SlotNames[slot]}: {error}");
                }
                else
                {
                    usedAmmo.Add(binding.Ammo);
                }
            }

            return string.Join("\n", errors.ToArray());
        }

        internal static IEnumerable<AmmoSetDef> SelectableAmmoSets()
        {
            return DefDatabase<AmmoSetDef>.AllDefsListForReading
                .Where(def => SelectableAmmo(def).Any())
                .OrderBy(def => def.label)
                .ThenBy(def => def.defName);
        }

        internal static IEnumerable<AmmoDef> SelectableAmmo(AmmoSetDef ammoSet)
        {
            if (ammoSet?.ammoTypes == null)
            {
                return Enumerable.Empty<AmmoDef>();
            }

            return ammoSet.ammoTypes
                .Where(link => link?.ammo != null && !link.ammo.menuHidden && link.ammo.ammoCount > 0)
                .Select(link => link.ammo)
                .Distinct()
                .OrderBy(ammo => ammo.label)
                .ThenBy(ammo => ammo.defName);
        }

        private static PipedAmmoBinding Resolve(
            string ammoSetDefName,
            string ammoDefName,
            HashSet<AmmoDef> usedAmmo,
            out string error)
        {
            AmmoSetDef ammoSet = DefDatabase<AmmoSetDef>.GetNamedSilentFail(ammoSetDefName);
            if (ammoSet == null)
            {
                error = $"ammo set '{ammoSetDefName}' was not found";
                return null;
            }

            AmmoDef ammo = DefDatabase<AmmoDef>.GetNamedSilentFail(ammoDefName);
            if (ammo == null)
            {
                error = $"round '{ammoDefName}' was not found";
                return null;
            }
            if (ammo.menuHidden || ammo.ammoCount <= 0)
            {
                error = $"round '{ammoDefName}' is not a usable physical ammunition type";
                return null;
            }
            if (ammoSet.ammoTypes == null || !ammoSet.ammoTypes.Any(link => link?.ammo == ammo))
            {
                error = $"round '{ammoDefName}' does not belong to ammo set '{ammoSetDefName}'";
                return null;
            }
            if (usedAmmo.Contains(ammo))
            {
                error = $"round '{ammoDefName}' is already assigned to another network";
                return null;
            }

            error = null;
            return new PipedAmmoBinding(ammoSet, ammo);
        }

        private static void ConfigureInput(ThingDef input, AmmoDef ammo)
        {
            CompProperties_PipedAmmoInput converter =
                input.GetCompProperties<CompProperties_PipedAmmoInput>();
            if (converter == null)
            {
                return;
            }

            ConfigureStorageFilter(input, ammo);
        }

        private static void DisableInput(ThingDef input)
        {
            ConfigureStorageFilter(input, null);
        }

        private static void ConfigureStorageFilter(ThingDef input, ThingDef allowedThing)
        {
            // Fixed settings constrain what may ever enter the storage building;
            // default settings constrain its initial player-facing filter. Both
            // must agree, and an invalid binding must accept no physical item.
            if (input?.building?.fixedStorageSettings?.filter != null)
            {
                input.building.fixedStorageSettings.filter.SetDisallowAll();
                if (allowedThing != null)
                {
                    input.building.fixedStorageSettings.filter.SetAllow(allowedThing, true);
                }
            }
            if (input?.building?.defaultStorageSettings?.filter != null)
            {
                input.building.defaultStorageSettings.filter.SetDisallowAll();
                if (allowedThing != null)
                {
                    input.building.defaultStorageSettings.filter.SetAllow(allowedThing, true);
                }
            }
        }
    }

    // The settings window edits persisted configuration only. Validation
    // mirrors startup resolution for immediate feedback, but runtime Def
    // mutation stays in Initialize so this UI cannot reconfigure a live colony.
    internal sealed class PipedCEAutoloadersSettingsWindow
    {
        private readonly PipedCEAutoloadersSettings settings;
        private Vector2 scrollPosition;

        internal PipedCEAutoloadersSettingsWindow(PipedCEAutoloadersSettings settings)
        {
            this.settings = settings;
        }

        internal void Draw(Rect inRect)
        {
            string errors = PipedAmmoBindings.ValidateSettings(settings);
            float viewWidth = inRect.width - 16f;
            float errorHeight = errors.NullOrEmpty() ? 0f : Text.CalcHeight(errors, viewWidth);
            var viewRect = new Rect(0f, 0f, viewWidth, Math.Max(inRect.height, 550f + errorHeight));
            Widgets.BeginScrollView(inRect, ref scrollPosition, viewRect);
            var listing = new Listing_Standard();
            listing.Begin(viewRect);
            listing.Label("Each network carries one exact CE round type and has independent performance settings. Changes take effect after restarting RimWorld.");
            listing.Label("After a restart, rebinding converts stored pipe resource and loader contents to the new round and updates existing inputs. Empty magazines before lowering capacity.");
            listing.GapLine();
            for (int slot = 0; slot < PipedAmmoBindings.SlotNames.Length; slot++)
            {
                DrawSlot(listing, slot);
                listing.Gap();
            }

            if (!errors.NullOrEmpty())
            {
                GUI.color = ColorLibrary.RedReadable;
                listing.Label(errors);
                GUI.color = Color.white;
            }
            listing.End();
            Widgets.EndScrollView();
        }

        private void DrawSlot(Listing_Standard listing, int slot)
        {
            string slotName = PipedAmmoBindings.SlotNames[slot];
            AmmoSetDef selectedSet = DefDatabase<AmmoSetDef>.GetNamedSilentFail(settings.AmmoSetFor(slot));
            AmmoDef selectedAmmo = DefDatabase<AmmoDef>.GetNamedSilentFail(settings.AmmoFor(slot));

            listing.Label($"{slotName} network");
            Rect setRow = listing.GetRect(30f);
            Widgets.Label(setRow.LeftPart(0.35f), "Ammo set");
            if (Widgets.ButtonText(setRow.RightPart(0.65f), selectedSet?.LabelCap ?? settings.AmmoSetFor(slot)))
            {
                var options = new List<FloatMenuOption>();
                foreach (AmmoSetDef ammoSet in PipedAmmoBindings.SelectableAmmoSets())
                {
                    AmmoSetDef capturedSet = ammoSet;
                    options.Add(new FloatMenuOption(ammoSet.LabelCap, () =>
                    {
                        settings.SetAmmoSet(slot, capturedSet.defName);
                        AmmoDef firstAmmo = PipedAmmoBindings.SelectableAmmo(capturedSet).FirstOrDefault();
                        settings.SetAmmo(slot, firstAmmo?.defName);
                    }));
                }
                Find.WindowStack.Add(new FloatMenu(options));
            }

            Rect ammoRow = listing.GetRect(30f);
            Widgets.Label(ammoRow.LeftPart(0.35f), "Exact round");
            if (Widgets.ButtonText(ammoRow.RightPart(0.65f), selectedAmmo?.LabelCap ?? settings.AmmoFor(slot)))
            {
                var options = new List<FloatMenuOption>();
                foreach (AmmoDef ammo in PipedAmmoBindings.SelectableAmmo(selectedSet))
                {
                    AmmoDef capturedAmmo = ammo;
                    options.Add(new FloatMenuOption(ammo.LabelCap, () => settings.SetAmmo(slot, capturedAmmo.defName)));
                }
                Find.WindowStack.Add(new FloatMenu(options));
            }
            float reloadSpeed = settings.ReloadSpeedFor(slot);
            reloadSpeed = listing.SliderLabeled(
                $"Reload speed: {reloadSpeed:0.0}x",
                reloadSpeed,
                PipedCEAutoloadersSettings.MinimumReloadSpeed,
                PipedCEAutoloadersSettings.MaximumReloadSpeed,
                tooltip: "Higher values reload adjacent turrets faster.");
            settings.SetReloadSpeed(slot, Mathf.Round(reloadSpeed * 10f) / 10f);

            float tankCapacity = settings.TankCapacityFor(slot);
            tankCapacity = listing.SliderLabeled(
                $"Magazine capacity: {tankCapacity:0}",
                tankCapacity,
                PipedCEAutoloadersSettings.MinimumTankCapacity,
                PipedCEAutoloadersSettings.MaximumTankCapacity,
                tooltip: "Maximum rounds stored by each magazine in this network.");
            settings.SetTankCapacity(slot, Mathf.Round(tankCapacity / 100f) * 100f);
        }
    }
}
