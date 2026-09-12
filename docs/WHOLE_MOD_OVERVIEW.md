# Whole Mod Understanding — ModLoader (Tomás) — Step 1 Dossier

> **Purpose:** Single source of truth for how the whole mod fits together.  
> **Date:** 2026-09-10 · Africa/Tripoli  
> **Inputs:** `ModLoader.csa` 480,326 B / 29,938 lines / CRLF, `ModLoader_Statics.c` (27 tunables), disassembly via `tools/csa_decompile.py` (272 Functions, 2,466 Labels, 311 natives, 1,803 strings) + 87 loadable scripts.  
> **Status:** Architecture dossier (living doc; updated 2026-09-12). Naming authority: `docs/NAMING_VERIFICATION.md` (341 labels + 352 statics verified). A vNext rewrite was explored and shelved — vNext docs removed.

---

## 0. Executive Summary (1 page)

**What it is:** A **RAGE ScriptAssembly hub** that runs as `ModLoader.csc/.xsc`. On boot it stays resident, draws a bilingual (ES/EN) menu, and **loads 87 other mod menus** on demand — essentially a *store* for GTA V mod menus (Brodator, Revolution, ArabicGuy Ultra, MoonShine, etc.) plus built-in cheats (teleports, outfits, vehicle spawns, protections).

**How it works core loop:**
```
Boot guard (GET_THIS_SCRIPT_NAME hash) → Label_0 init (safe-zone, colors, Static[0..128])
  → Label_4: while(true) { Label_3: WAIT(0); Label_5(input/queue/help); Label_6(toggle-effect tick)
                           NETWORK_SET_THIS_SCRIPT_IS_NETWORK_SCRIPT; if pause return;
                           Switch Static[130] (48 states); Label_111 post-draw }
```
Selection via `Label_397` (X confirm; R1/L1 suppress), rendering via `DRAW_RECT/SPRITE/TEXT`, persistence via `Static[134]/136` single-slot queue → `Label_5` does `REQUEST_SCRIPT → HAS_SCRIPT_LOADED → START_NEW_SCRIPT`.

**Scale:**
- **48 menu states** (0..59 sparse) — 9 are *loader directories* (call `Label_1835` 87×), 39 are *built-in menus* (animations, teleports, outfits, vehicles, HUD editor) that execute natives directly.
- **87 loadable scripts** grouped: Ultra/Mains (22), Recovery (8), Protections (8), Freezers (9), Vehicles (8), Maps (7+), Misc (Particle, HUD, Drone, etc.) + 2 tutorial skips.
- **Technology:** RAGE `scrProgram` stack VM, `Static1[512]/Static2[512]` globals, `pSet` global patches for anti-freeze, `GET_SAFE_ZONE_SIZE` scaling, texture dicts `commonmenu`, `timerbars`, `erootiik`.

**Health check:** Works but shows its age — 64-char StrCopy buffer, single-slot queue race, no load timeout, deprecated hash check, `TERMINATE_ALL` overkill, dead PS3 branch, no stack validation or loading feedback. The loader (1835 + queue in `Label_5`) is verified as-is by the name audit; a vNext rewrite was explored and shelved (out of scope). Built-ins duplicate outfit/teleport tables instead of data-driven.

---

## 1. File Map

| File | Lines | Role |
|---|---|---|
| `ModLoader.csa` | 29,938 | Text assembly source — *the mod* (pristine, never edit) |
| `ModLoader_Statics.c` | 27 | Initial `Static_xxx = val;` — theme / flags (included at compile) |
| `ModLoader_Renamed.csa` (+`_Full`) | 29,938 | Generated: fully renamed source (curated / +internals) |
| `docs/NAMING_VERIFICATION.md` | — | The complete name-audit report (hand-written, authoritative) |
| `docs/NAMING_MAP_*` + `REFERENCE_GLOSSARY.md` | — | Generated name tables + A–Z glossary |
| `docs/BITSET_MAP.md` | — | Verified flag-bit tables |
| `docs/CSA_BYTECODE_GUIDE.md` | 290 | VM opcode bible |
| `docs/DECOMPILED_WALKTHROUGH.md` | 291 | 4 hot functions annotated |
| `docs/ModLoader_pseudo.c` | 8,771 | Auto pseudo-C (272 funcs) |
| `docs/callgraph.dot` | 3,868 edges | `Call @Label` graph |
| `docs/ModLoader_Annotated.csa` (+`_Full`) | 29,938 | Generated: numeric source + name comments |
| `tools/verify_names.py` + `verification_report.json` | — | Evidence-rule verifier + per-name verdicts |
| `tools/rename_map.json` (+`_full`) | — | Source of truth for all names |
| `tools/export_docs.py` / `apply_names.py` | — | Doc + annotated/renamed generators |
| `tools/csa_decompile.py` | — | Disassembler / pseudo-C / stats |

No binary `.csc/.xsc` in repo — `.csa` is the source; assemble with Zan/GLA toolkit.

---

## 2. Boot & Lifecycle

### 2.1 Guard (lines 1-7)
```asm
Function 0 2 0
  GET_THIS_SCRIPT_NAME → GET_HASH_KEY → UNK_029D3841 → JumpTrue @Label_0 else Return
```
Ensures only the instance named `ModLoader` continues; duplicate launch kills instantly.

### 2.2 Init `Label_0` (8-280) + `Label_1` (29860) + `Label_2` (3864)
- `NETWORK_SET_SCRIPT_IS_SAFE_FOR_NETWORK_GAME`
- `Label_1`: resets temps, sets `Static[223]=10`, `Static[267]=11`, `Static[209]=4` etc., requests 9 texture dicts (`mpinventory`, `commonmenu`, `TPBackground1-4`, `erootiik`)
- Safe-zone: `Static[0]=0.2788+GET_SAFE_ZONE_SIZE()/2`, `Static[1]=0.4939+…`, `Static[2]=0.3864+…`
- Colors: `Static[3]=0 … Static[27]=39` (HUD colour IDs), `Static[28]=-1`, `Static[29]=1.0`, `Static[30]=0.9`, RGBA 255 blocks `31..37` etc.
- Flags: `SET_BIT(71,10)`, `SET_BIT(72,5)` → “enabled”, `Static[70]=0` language not chosen

### 2.3 Infinite Loop `Label_4` (281-284) → `Label_3` (285-470)
```c
:Label_4  Call @Label_3; Jump @Label_4   // while(1)
// Label_3:
WAIT(0); Static[129]=0;
Label_5(); Label_6();
NETWORK_SET_THIS_SCRIPT_IS_NETWORK_SCRIPT(18,0,PLAYER_ID());
if (IS_WARNING_MESSAGE_ACTIVE()||IS_PAUSE_MENU_ACTIVE()) return;
if (Static[130]) Label_9();
switch(Static[130]) { 48 cases } // see §4
if (Static[130]) Label_111();
```

---

## 3. Rendering Engine (how the menu looks)

| Layer | Helper | Native |
|---|---|---|
| **Background** | `Label_1151` / `Label_345` | `DRAW_RECT` (`Label_327` 11 params) |
| **Sprite icon** | `Label_427` → `Label_327` | `REQUEST_STREAMED_TEXTURE_DICT("erootiik")` → `DRAW_SPRITE("erootiik","button_7",x,y,w,h,rot,255)` |
| **Text row** | `Label_396` → `Label_546` | `BEGIN_TEXT_COMMAND_DISPLAY_TEXT("STRING")` → `ADD_TEXT_COMPONENT_SUBSTRING_PLAYER_NAME(rowStr)` → `END_TEXT_COMMAND_DISPLAY_TEXT(x,y)` + `SET_TEXT_COLOUR/SCALE/CENTRE/OUTLINE` |
| **Highlight rect** | `Label_418` → `Label_436` | Computes `Static[224]=Static[214]*Static[100]+0.2165` → `DRAW_RECT` selected row |
| **Safe-zone** | `Label_2` | `GET_SAFE_ZONE_SIZE()/2` → offsets all x/y |
| **Throttle** | `Label_1151` | Caps visible rows to `Static[223]=10` (scroll window) |

**Theme:** `ModLoader_Statics.c` drives RGBA: `Static_210=252,211=255…` = preview color, `Static_258=250…` = scrollbar, `Static_175/186=10` = HUD ids. Changing those 27 lines re-skins without recompiling logic.

---

## 4. Input Handling `Label_397` + `Label_5`

- **Selection cursor:** `Static[197]` selected index, `Static[214]` draw cursor, `Static[223]` visible rows
- **Confirm:** `Label_397` — row match (`Static[197]==Static[214]`) + X just-pressed:

  ```asm
  StaticGet1 197 ; StaticGet1 214 ; JumpNE → check 177
  NOT (IS_DISABLED_CONTROL_PRESSED(202) OR PRESSED(203)) AND IS_DISABLED_CONTROL_JUST_PRESSED(177) → PLAY_SOUND Click_Special → return 1
  ```
  `177` = X/A (`INPUT_FRONTEND_ACCEPT`); `202/203` = R1/L1 **SUPPRESS** confirm (verified 09-11 audit — not an R1+L1 combo)
- **Queue throttle:** `Label_5` first block uses `GET_GAME_TIMER` + `SET_INPUT_EXCLUSIVE(0,178)` to eat input for 4.6 s after opening
- **Async queue:** `Static[134]` pending script + `Static[136]` stack → `Label_5` polls `HAS_SCRIPT_LOADED`, timeout missing in v1 (fixed in v2)

---

## 5. State Machine — 48 States (the whole hub)

`Static[130]` is the page id. Dispatched at `line 312`:

```
Switch [0=@Label_10][1=@Label_11]...[59=@Label_57]  // sparse, 48 active
:Label_10  Call @Label_58 ; Return   // splash: "Press LS+RS to open"
:Label_11  -> Label_60               // language picker
... // etc
```

### 5.1 Catalog (state → inner label → strings → type)

| State | Gate | Inner | Title (ES / EN) | Type | Notes |
|---|---|---|---|---|---|
| **0** | `Label_10` | `Label_58` | Splash `STRING / Press LS+RS` | **Splash** | Shows punisher branding `CHAR_MP_FM_CONTACT` |
| **1** | `Label_11` | `Label_60` | `Lenguaje Del Menu / Menu Language` | **Setup** | Sets `Static[70]` 0/1 via `Label_455`, bilingual helper `Label_163/1156` |
| **2** | `Label_12` | `Label_64` | `Mods Menus` — `APP II Intense`…`Innocence BETA` | **Loader dir** | 22 × `Call @Label_1835`, stacks 1024-6304 |
| **3** | `Label_13` | `Label_65` | `Menu De Recovery` — `James Reborn Recovery v5.2.3`…`Tattoo Editor` | **Loader dir** | 8 ×, includes `CR_Stat` 128, `csm_menu` skip |
| **4** | `Label_14` | `Label_66` | `Menu De Protecciones` — `Unrestrained v8`…`TR4F1K4NT3` | **Loader dir** | 8 ×, recovery-leaning protections |
| **5** | `Label_15` | `Label_67` | `Outfit Menus` → Male/Female | **Loader dir (router)** | Routes to 20/22/48/49 states |
| **6** | `Label_16` | `Label_68` | `Menu De Congelaciones` — `Frezze V3ND3TT4`…`FreezeTP` | **Loader dir** | 9 × freezes (grief) |
| **7** | `Label_17` | `Label_69` | `Menu De Vehiculos` — `Erootiik Spawner`…`JR Drift` | **Loader dir** | 8 × + built-in spawn (`Label_106` etc. are *not* here, they’re elsewhere) |
| **8** | `Label_18` | `Label_70` | `Menu De Mapas` — `Tgsaudoiz Maps` + 5? | **Loader dir** | 1 loader + 8 built-in maps `Label_79` |
| **9** | `Label_19` | `Label_71` | `Opciones Diversas` + Teleports router | **Router** | Mixed loader + direct teleports |
| **10** | `Label_20` | `Label_72` | `Creditos / Credits` — Tomás + 9 helpers | **Credits** | Static text via `Label_396`, `Label_358` |
| **11** | `Label_21` | `Label_93` | `Barra De Desplazamiento 2` | **Settings** | RGB `R/G/B` 0-255 |
| **12** | `Label_22` | `Label_73` | `Animaciones / Animations` — Looped/Upper/Contorted | **Built-in** | `TASK_PLAY_ANIM`, `REQUEST_ANIM_DICT`, flags `Static2[392..395]` |
| **13** | `Label_23` | `Label_74` | `Teleportations / Lugares Secretos` → Clothing/Ammu… | **Built-in teleport** | coords → S2[397/398/399] → shared applier `Label_2008` |
| **14** | `Label_24` | `Label_75` | `Lugares Secretos` → Interiores router | **Router** | |
| **15** | `Label_25` | `Label_76` | `Lugares Interiores` — Military/Police… | **Teleport** | 15+ coords |
| **16** | `Label_26` | `Label_77` | `8 Ubicaciones Infinitas` | **Teleport** | |
| **17** | `Label_27` | `Label_78` | `Bajo El Agua` — Tanks/Whale | **Teleport** | |
| **18** | `Label_28` | `Label_79` | `Tgsaudoiz Maps` — Farm/Box/House/Jungle… | **Loader + built-in** | 7 Tgsaudoiz map loads (128 stack) |
| **19** | `Label_29` | `Label_80` | `Personalizacion Del Menu` → fonts | **Settings** | `SET_TEXT_FONT` 0-7 |
| **20** | `Label_30` | `Label_101` | `IvoAlqaeda Male Outfits` | **Outfit built-in** | `SET_PED_COMPONENT_VARIATION / PROP_INDEX` tables |
| **22** | `Label_31` | `Label_81` | `Male Outfits` — BUZZARD 13 entries | **Outfit** | |
| **23** | `Label_32` | `Label_82` | `Female Outfits` — l-PoWerPuff | **Outfit** | |
| **24** | `Label_33` | `Label_83` | `Configuraciones / Settings` → creditos etc. | **Router** | |
| **25** | `Label_34` | `Label_84` | `BUZZARD Outfits` detail | **Outfit** | |
| **26** | `Label_35` | `Label_85` | `l-PoWerPuffGirl Outfits` detail | **Outfit** | |
| **27** | `Label_36` | `Label_86` | `Opciones Del Jugador` — Anim…Modelos | **Router → player** | Routes to `Label_52/53/103` |
| **28** | `Label_37` | `Label_87` | `Opciones De Editor De Menu` | **Settings** | |
| **29** | `Label_38` | `Label_88` | `Barra 3` | **Settings RGB** | |
| **30** | `Label_39` | `Label_89` | `Editor Del Hud Color` | **Settings** | `GET_HUD_COLOUR` preview |
| **33** | `Label_40` | `Label_90` | `Fondo / Background` | **Settings** | `DRAW_RECT` alpha |
| **34** | `Label_41` | `Label_106` | `Generador De Vehiculos / Spawn Vehicles` | **Vehicle built-in** | 22-class slot/switch/display machine (slots S1[106–127], switches 1361–1382), spawn via `Label_1509` |
| **35** | `Label_42` | `Label_91` | `Titulo / Title` | **Settings** | |
| **36** | `Label_43` | `Label_92` | `Barra 1` | **Settings RGB** | |
| **37** | `Label_44` | `Label_94` | `Texto Seleccionado` | **Settings** | |
| **38** | `Label_45` | `Label_95` | `Texto No Seleccionado` | **Settings** | |
| **40** | `Label_46` | `Label_96` | `Proteccion De Modders` — *real* protections | **Protection built-in** | `pSet` global flood `1317011488→19705448...` (16 globals), `REMOVE_PARTICLE_FX`, `CLEAR_AREA_OF_COPS` |
| **44** | `Label_47` | `Label_102` | `IvoAlqaeda Female Outfits` | **Outfit** | |
| **46** | `Label_48` | `Label_97` | `SAAB Outfits (male)` — 13 variants + `~b~ Negro Sexy` | **Outfit** | Credits `SAAB Modz` per entry |
| **47** | `Label_49` | `Label_98` | `JakeModz89 Outfits` — `Invisible` etc. | **Outfit** | |
| **48** | `Label_50` | `Label_99` | `SAAB Outfits (alt)` | **Outfit** | Duplicate but different flagA/B |
| **49** | `Label_51` | `Label_100` | `JakeModz89 Invisible / Female Cop` | **Outfit** | |
| **50** | `Label_52` | `Label_103` | `Mains Mods → Player Options` | **Router → built-in** | Gives `Label_86` style |
| **51** | `Label_53` | `Label_104` | `Opciones De Armas → Dar Todas Las Armas` | **Weapon built-in** | 56-hash give-all + 18 bit-toggles + Big-Gun mem-poke (see `BITSET_MAP.md` §1) |
| **52** | `Label_54` | `Label_105` | `Opciones De Vehiculos` — spawner + fixes | **Vehicle built-in** | `SET_VEHICLE_FIXED`, `SET_VEHICLE_ON_GROUND_PROPERLY`, `SET_VEHICLE_MOD` 38 calls |
| **54** | `Label_55` | `Label_107` | `Configuracion De Generador` — Spawning Settings | **Settings** | `GENERAR_DENTRO` toggle |
| **55** | `Label_56` | `Label_108` | `Opciones De Sprite On/Off` | **Settings** | `erootiik/button_*` toggle `Static2[373/358]` |
| **59** | `Label_57` | `Label_109` | `Barra De Desplazamiento Vertical` | **Settings** | Vertical scrollbar 0-255 |

*States not listed (21,31,32,39,41-43,45,53,56-58) are unused / reserved.*

### 5.2 Loader vs Built-in Split

- **Loader directories (2-9, except 0,1,10):** 9 states → 87 × `Call @Label_1835` — they **don’t** call natives directly, they queue a separate `.csc`. See `docs/menu_list.txt` (22 Mods, 8 Recovery, 8 Protect, 9 Freezers, 8 Cars, 1 Maps loader, rest misc).
- **Built-ins (12-59):** 39 states → call natives directly (outfits do `SET_PED_COMPONENT_VARIATION`, teleports `SET_ENTITY_COORDS`, vehicles `CREATE_VEHICLE`, animations `TASK_PLAY_ANIM`, protections `pSet`). These are **not** queueing — they run instantly, so they’re lower-latency and don’t need stack allocation.

---

## 6. Data & Globals Architecture

### Statics (`Static1[~512]`, `Static2[~600]`)

| Range | Use | Example |
|---|---|---|
| `Static[0..2]` | Menu geometry (x,y,w) + safe-zone | `0.2788+safe/2` |
| `Static[3..27]` | HUD colour IDs for themes | `12,13,14…39` |
| `Static[28..30]` | Opacity / scale (`-1`, `1.0`, `0.9`) | |
| `Static[31..62]` | RGBA presets `255` | |
| `Static[63..70]` | Language / toggles | `Static[70]=0` ES, 1 EN |
| `Static[71..73]` | Bitsets for save flags (`SET_BIT 10`, `5`, `12`) | |
| `Static[100..105]` | Row metrics (`0.035` height, `1.0` scale) | |
| `Static[130..142]` | **Menu state** `130`, timers `131`, queue `134/136`, pagination `174=page`, cursor `197`, `214` draw cursor, `224` X | |
| `Static[175..270]` | Theme RGBA from `ModLoader_Statics.c` | `210=252` etc. |
| `Static2[353..373]` | Texture dict names (`PunisherOnOff`, `globe`, `erootiik`) + sprite toggles | |
| `Static2[391..395]` | Animation flags (`392 Looped`, `393 UpperOnly` etc.) | |

### Globals (`pGlobal 0..200k` via `pSet`)

16 hard-coded globals patched every frame when `IS_BIT_SET(Static[139],9)` (Protección) is on:

```asm
Push 1317011488 ; Push 19705448 ; pSet
... 19716948,19727748,19705448 etc. (16)
```

These correspond to Rockstar’s anti-freeze vectors — setting them to `0x4E...` neutralises freeze `APPLY_FORCE`/`SET_ENTITY_COORDS` spam from other modders. **Risk:** global numbers are version-sensitive (1.12 vs 1.36); after title-update they drift.

---

## 7. The 87 Loadable Scripts — By Family

Full list `docs/menu_list.txt` (stack in parens):

**Mains/Ultra (22):** `APP II Intense (2024)`, `Inimitable 6.52 (1024)`, `ArabicGuy Ultra 2.6 (6304)`, `insanity Ultra (6304)`, `Tgsaudoiz Teleport 3.8.6 (1820)`, `Brodator (1024)`, `Project CL (1024)`, `Console Trainer V (1024)`, `K&K Dark Horse (1024)`, `Eternal Darkness 4.6.5 (3584)`, `GTA FUCKER (1024)`, `AndyMoDz (1024)`, `MK3 1.5.8 (2024)`, `MoonShine 3 (6304)`, `Expulsion v1 (1024)`, `Revolution (1024)`, `Scorpion ModMenu (2024)`, `MainMenu v2 SP (1024)`, `Alien Script V2 (1024)`, `Destroy v3 (1024)`, `X Script v2 (2024)`, `Innocence 0.6 BETA (3076)`

**Recovery (8):** `James Reborn Recovery 5.2.3 (2552)`, `2much4u (512)`, `Danni X MoDz (1024)`, `Stat Editor CR_Stat (128)`, `Skip Online Tutorial csm_menu (1024)`, `insanity Recovery (1024)`, `Garage Editor (1024)`, `Tattoo Editor (512)` + `Unrestrained 8.0 (2024)`, `Serendipity (1024)` (also listed under protections but file-wise recovery)

**Protections (8):** `Black Protect Saint 5.0 (4592)`, `LimoProtex 2 (1024)`, `Helper Menu (1024)`, `RFOoDxMoDz (1024)`, `PrivateProtections (1024)`, `TR4F1K4NT3 (1024)`, etc.

**Freezers/Grief (9):** `Frezze V3ND3TT4 1 (abigail3)`, `FreezeMenuv1`, `frz2`, `Vmenu 1.3`, `PedCheckerV6 (128)`, `AutoKickPedFreezeV1`, `FREEZE-TAXI-J6`, `TestFreezeByJ6`, `FreezeTP` — *all via Label_1835, not built-in*

**Vehicles/Maps/Misc (20+):** `Erootiik Spawner (512)`, `App7e Truck Sim (1820)`, `FCLoader (1024)`, `yankton_menu (128)`, `BeachAirport (128)`, `Tgsaudoiz Farm/Box/House/Jungle… (128)`, `Perspectivemenu (128)`, `ParticleMenuV03 (1024)`, `HudEditorv1 (1024)`, `DroneModeFixed (512)`, `ProjectCL_LaserEyes (128)` etc.

Pattern: **stack 128 = FX / teleport / outfit** (light), **1024 = default**, **6304 = ultra player-list**.

---

## 8. Built-in Cheats (not loader) — Where the Real Natives Are

| Category | States | Key Natives (count) | Example Flow |
|---|---|---|---|
| **Outfits** | 20,22-26,44,46-49 (8 states) | `SET_PED_COMPONENT_VARIATION` / `SET_PED_PROP_INDEX` via `Outfit_ApplyFullSet` (1915, F30) | Choose `SAAB Black Red` → 1915 applies the 30-field set; credit line + notify per row |
| **Teleports** | 13-18 (6 states) | `SET_ENTITY_COORDS` via shared applier (85 calls) | `Lugares Secretos → Military Base Tower` → coords staged in S2[397/398/399] → `2008: ped-or-vehicle SET_ENTITY_COORDS` |
| **Vehicles** | 34,52,54 (3 states) | `CREATE_VEHICLE`, `SET_VEHICLE_MOD`, `SET_VEHICLE_COLOURS` | `Generador` → 22-class machine (switches 1361–1382 on slots S1[106–127]) → `Label_1509`: validate → `REQUEST_MODEL` → `CREATE_VEHICLE` + appliers |
| **Animations** | 12 (state12) | `REQUEST_ANIM_DICT`, `TASK_PLAY_ANIM`, `HAS_ANIM_DICT_LOADED` | `Serpentead@ / Looped` toggles `Static2[392]`, then `TASK_PLAY_ANIM(ped, dic, anim, 8.0, …)` |
| **Weapons** | 51 (state51) | `Weapon_GiveToPlayer` (56 hashes), bit-toggles, `SET_PED_INFINITE_AMMO_CLIP` | `Dar Todas Las Armas` = 56 hard-coded hashes; 18 toggles applied per-frame by the tick (see `BITSET_MAP.md` §1) |
| **Protections** | 40 (state40) | `pSet` 16, `REMOVE_PARTICLE_FX_IN_RANGE` 9999, `CLEAR_AREA` | Bit `139.9` floods globals; bit `137.0` clears FX every frame in `Label_5` |
| **Settings** | 11,19,28-30,33,35-39,55,59 | `SET_TEXT_FONT`, `GET_HUD_COLOUR`, `SET_TIMECYCLE_MODIFIER` (`AmbientPush`) | Live preview: `Label_1151` limits to 10 rows, `Label_83` theme router |

---

## 9. Dependencies

- **Textures:** `commonmenu`, `commonmenutu`, `mpinventory`, `TPBackground1-4`, `erootiik`, `timerbars` + `chaos_textures_2/5/6/10` (2-12 loads each) — all via `Label_2455` / `Label_327`
- **Scaleforms:** `REQUEST_SCALEFORM_MOVIE` → `BEGIN_SCALEFORM_MOVIE_METHOD` → `DRAW_SCALEFORM_MOVIE_FULLSCREEN`
- **Sounds:** `HUD_FRONTEND_DEFAULT_SOUNDSET`, `HUD_MINI_GAME_SOUNDSET`, `WEB_NAVIGATION_SOUNDS_PHONE` + `Click_Special`
- **Network:** `NETWORK_SET_SCRIPT_IS_SAFE_FOR_NETWORK_GAME`, `NETWORK_SET_THIS_SCRIPT_IS_NETWORK_SCRIPT`, `NETWORK_HAS_CONTROL_OF_ENTITY` (before any `SET_ENTITY_*`)
- **Strings:** 1,803 `PushString` — bilingual pairs via `Label_163(ES,EN)` / `Label_1156(4 strings)` helpers

---

## 10. Known Limitations (v1) — The Update Drivers

Loader limitations (verified as-is; a vNext rewrite was explored and shelved): 64-char buffer, single-slot queue, no timeout, deprecated hash, `TERMINATE_ALL` overkill, dead PS3 branch. Whole-mod extras:

| Area | Limitation | Impact |
|---|---|---|
| **Monolith** | Single 29,938-line file, 272 Functions interleaved — no `include` split | Merge conflicts, hard to theme |
| **Hardcoded teleports** | Coordinates inlined per state, duplicated `Amu-Nation` 6× | Bloat, inconsistent |
| **Outfit tables** | Copy-paste `SAAB 13×` × 3 menus = 39 duplicated blocks | 2,000 lines waste |
| **Vehicle class machine** | 22 switches `Label_1361..1382` + per-class slots + displays, manual | Adding a car means new switch + slot + display |
| **Static allocation** | `Static1/2` flat array, no struct, magic `210=252` | Theme fragility |
| **Globals version lock** | `19705448` etc. tied to 1.12 patch | Breaks on title update |

---

## 11. How to Navigate the Code (Practical)

- **Find a menu:** `python3 tools/csa_decompile.py --explain Label_64` (Mods), `Label_74` (Teleports), `Label_97` (SAAB outfits)
- **Find a teleport:** `grep -n "Lugares Secretos" ModLoader.csa`
- **Find a vehicle spawn:** `grep -n "adder" ModLoader.csa` → class switches at `Label_1361..1382`
- **Find protection toggles:** `grep -n "IS_BIT_SET.*139" ModLoader.csa`
- **Full graph:** `dot -Tpng docs/callgraph.dot -o map.png` (Graphviz)

---

## 12. Where To Go Next

The audit is complete: every name in this dossier resolves via `docs/NAMING_VERIFICATION.md` (the authoritative report — 340/340 VERIFIED, 0 UNNAMED, 0 CHECK) and the generated references (`NAMING_MAP_*`, `REFERENCE_GLOSSARY.md`, `BITSET_MAP.md`, `ModLoader_Annotated.csa`).

- Read a page: open `docs/ModLoader_Annotated.csa`, search the page name (e.g. `Page_Teleport_Hub_Impl`)
- Check a bit: `docs/BITSET_MAP.md` §1–§3
- Change a name: `NAMING_GUIDE.md` workflow (map → verify → export)

*This dossier stays as the living architecture doc; a vNext update was explored and shelved (out of scope).*

