# Naming Guide — How to Use Correct Names for Future Dev

> **Problem:** Stock ModLoader uses `Label_0…Label_2465` and `Static 0…512/600` — numbers are unmaintainable.
> **Solution:** Every Label/Static has a **verified English name** via `tools/rename_map.json` (**341 labels, 352 statics, 0 unnamed, 0 CHECK**) + generated artefacts below.
> Audit status and evidence: `docs/NAMING_VERIFICATION.md` (human audit) + `docs/NAMING_VERIFICATION_TABLES.md` (machine verdicts).

---

## Artefacts

| File | What | When to Use |
|---|---|---|
| `tools/rename_map.json` | **Source of truth** — `labels`, `statics1`, `statics2` dicts | Tooling, editors, CI checks |
| `tools/rename_map_full.json` | Full map — curated + ~2,100 positional `__J_*` internals | Navigation of every jump label |
| `tools/verify_names.py` | Evidence-rule verifier (~120 rules, CHECK = 0) | Run after any map edit |
| `tools/verification_report.json` | Per-name verdict + evidence | Machine-readable audit result |
| `docs/NAMING_MAP_LABELS.md` | 341-row table: `Label_1835` → `Loader_AddMenuEntry` + verdict | Reference while reading `.csa` |
| `docs/NAMING_MAP_STATICS.md` | 352-row table: `Static1[130]` → `gMenu_CurrentPage` + verdict | Reference for save/theme |
| `docs/NAMING_MAP_LABELS_FULL.md` / `NAMING_MAP_STATICS_FULL.md` | Full-map tables | Deep navigation |
| `docs/REFERENCE_GLOSSARY.md` | A–Z glossary of every curated name + evidence | “What does this name mean?” |
| `docs/BITSET_MAP.md` | Verified flag-bit tables (weapons/tick/settings) | Cheat/flag logic |
| `docs/ModLoader_Defines.h` | `#define Mod_Init_Main Label_0` etc. (curated + internals) | Cheatsheet / CSA-split reference |
| `docs/ModLoader_Statics_Named.c` | Named copy of `ModLoader_Statics.c` (`// gUI_Hdr_G` comments) | Replace `IncludeStaticFile` path |
| `docs/ModLoader_Annotated.csa` | Full 29,938-line annotated: `Call @Label_1835 ; -> Loader_AddMenuEntry`, `StaticSet1 130 ; gMenu_CurrentPage` | Read / `grep` without memorizing numbers |
| `ModLoader_Renamed.csa` (+ `_Full`) | Fully renamed (`:Mod_Init_Main`, `@Mod_Init_Main`) | Develop with names (assembles identically) |
| `tools/apply_names.py` | `--annotated` vs `--rename` switcher, `--map` selector | Generate above |
| `tools/export_docs.py` | Regenerates all 7 derived docs from the JSON maps | Run after map edits |

All derived docs carry an `AUTO-GENERATED` header — never hand-edit them, edit the JSON and re-export.

---

## Quick Start (future dev)

### Option A — Annotated (recommended, non-breaking)

Stay on original numeric `.csa` but **read annotated**:

```bash
python3 tools/apply_names.py --annotated --in ModLoader.csa --out docs/ModLoader_Annotated.csa
# then in VSCode: open Annotated, Ctrl+F "gMenu_CurrentPage" jumps to every hit
# original line numbers preserved → diffs vs upstream stay clean
```

### Option B — Renamed (clean names everywhere)

Develop with English names:

```bash
python3 tools/apply_names.py --rename --in ModLoader.csa --out ModLoader_Renamed.csa
# :Label_1835 → :Loader_AddMenuEntry
# Call @Label_1835 → Call @Loader_AddMenuEntry
# Assemble Renamed directly — toolkit accepts any label spelling
```

### Verify + re-export (after any map change)

```bash
python3 tools/verify_names.py          # CHECK must stay 0
python3 tools/export_docs.py           # refresh maps/glossary/defines/headers
python3 tools/apply_names.py --annotated --in ModLoader.csa --out docs/ModLoader_Annotated.csa
```

> **Note:** CSA syntax needs numeric `StaticSet1 130` — `gMenu_CurrentPage` is a *comment/define* for humans. The **annotated** file keeps numeric + comment; the **renamed** file renames labels only (statics stay numeric).

---

## Naming Principles (how the verified names work)

| Pattern | Example | Rule |
|---|---|---|
| `Mod_*` | `Mod_Init_Main` | Boot, lifecycle, global |
| `Main_*` | `Main_Tick` | Top-level loop / dispatch |
| `Tick_*` | `Tick_ApplyToggleEffects`, `Tick_InputQueueAndToggles` | Called every `WAIT(0)` |
| `Page_*` | `Page_Teleport_Hub_Impl`, `Page_Outfits_Router` | Menu pages; `_Impl` builds rows, router links submenus |
| `Loader_*` | `Loader_AddMenuEntry` | Script-spawning (1835 + queue) |
| `UI_*` | `UI_RenderCycleRow`, `UI_Draw_HeaderSprite` | Rendering |
| `Util_*` | `Util_LangPick_ES_EN`, `Util_IntToString` | Helpers |
| `Input_*` / `Sfx_*` | `Input_CycleFloatPtrValue` | Control/sound |
| `Vehicle_*` / `Outfit_*` / `Teleport_*` / `Weapon_*` | `Vehicle_Spawn_ByHash`, `Teleport_SharedApplier_397_399` | Feature clusters |
| `Net_*` / `Anim_*` / `Stat_*` / `World_*` / `Entity_*` / `Help_*` | `Net_ShowHost`, `Anim_PlaySelectedAnim` | Feature clusters |
| `Dead_*` | `Dead_RowVariant_U3` | Unreached code (entry dead, kept for reference) |
| `gMenu_*` / `gUI_*` / `gTheme_*` | `gMenu_CurrentPage`, `gUI_RowHeight` | Static1 UI/menu state |
| `gInput_*` / `gNet_*` / `gVehicle_*` | `gInput_SelectedRow`, `gNet_ShowHost` | Feature state |
| `gTmp_*` | `gTmp_DeleteGunTarget` | Scratch / out-params |
| `gDead_*` | `gDead_410_Zero` | Never-written slots (constant 0 — includes dead pushes) |

All `g*` names start with `g` (global/static) for grep (`grep gMenu_` lists all menu state).

---

## Keeping Names Correct (workflow)

1. **Change a name:** edit `tools/rename_map.json` (and mirror to `tools/rename_map_full.json` — same edit, or copy the file's curated section).
2. **Strengthen the proof (recommended):** add 1–4 falsifiable checks for the name in `tools/verify_names.py` (see the `Track-3 batch-*` blocks for the pattern).
3. **Verify:** `python3 tools/verify_names.py` — CHECK must stay 0, UNNAMED must stay 0.
4. **Re-export:** `python3 tools/export_docs.py` + `apply_names.py` (annotated + renamed) so every derived doc matches.
5. **Document:** add a line to `docs/NAMING_VERIFICATION.md` §3 (what was read, what changed).

---

## Example Before / After

**Before (numbers only):**

```asm
:Label_1835
Function 6 19 0
  getF1 1 ; CallNative "DOES_SCRIPT_EXIST" 1 1 ; JumpTrue @Label_423
  getF1 1 ; pFrame1 8 ; StrCopy 64
```

**After (annotated):**

```asm
:Label_1835  ; >>> Loader_AddMenuEntry
Function 6 19 0
  getF1 1 ; CallNative "DOES_SCRIPT_EXIST" 1 1 ; JumpTrue @Label_423  ; -> Loader_AddMenuEntry__ExistsBranch
  getF1 1 ; pFrame1 8 ; StrCopy 64
```

**After (fully renamed):**

```asm
:Loader_AddMenuEntry
Function 6 19 0
  getF1 1 ; CallNative "DOES_SCRIPT_EXIST" 1 1 ; JumpTrue @Loader_AddMenuEntry__ExistsBranch
```

---

## Map Stats (final audit)

- **341 labels** — 340 VERIFIED + 1 LIKELY (`World_ClearAreaAroundPlayer__ClearAll`, UNK native) · 0 UNNAMED · 0 CHECK
- **352 statics** — 340 VERIFIED + 12 LIKELY (reserved icon-palette slots, 0 reads) · 0 UNNAMED · 0 CHECK
- **~60 flag bits** verified in `BITSET_MAP.md` (weapons/tick/settings/boot)
- **Full map:** 2,466 labels (curated + positional `__J_*` internals for navigation)

Now every future change (add vehicle hash, new teleport, theme tweak) can use `gInput_SelectedRow` instead of `Static1[197]` and `Page_Teleport_Hub_Impl` instead of `Label_74` — with the verifier proving the names on every run.
