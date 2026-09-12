# Round-2 Naming Audit — Are the names 100% accurate?

> **Date:** 2026-09-12 · **Auditor:** agent (tool-assisted + direct code reading)
> **Scope:** `tools/rename_map.json` (341 labels + 352 statics) vs `ModLoader.csa`
> **Tools:** `tools/verify_names.py` (comment-tolerant parser + ~120 evidence rules),
> `tools/verification_report.json` (machine verdicts), this doc (human audit).
> **Round-3 / Track-0 (same day):** the 10 §6.4 micro-questions were closed by
> line-reading; +54 labels and +10 statics moved to VERIFIED; the §4.1
> "frozen settings" claim was **corrected** (back-keys are LIVE, the other
> settings frozen by a dropped address — see §4.1); the vehicle spawner was mapped as a 22-class
> slot/switch/display machine (slots S1[106–127]).
> **Track-1 (same day):** all 69 LIKELY labels (internal jump labels) line-read:
> 68 VERIFIED (3 renamed first, §3f), 1 stays LIKELY (692, case 0 over
> an UNK native, kept honest).
> **Track-2 (same day):** all 93 unnamed labels named from line-reads (§3g) —
> 0 UNNAMED remain; CHECK still 0.
> **Track-3 (same day):** all 46 unnamed statics named from reads + Statics.c
> (§3h) — 0 UNNAMED anywhere; 3 more wrong names fixed; CHECK still 0.
> **Backlog (same day):** the §6.3 human-read backlog closed (§3i) — 104's
> 21-row bit map, L6's 49 effect sites, 1509's full pipeline, teleport
> family 74–78 + shared applier 2008, outfit router 67 + male page 81;
> S2[410] renamed `gNet_IsSessionHost` → `gDead_410_Zero` (never written).
> **Final (same day):** workspace reorganized — derived docs regenerated
> from the maps (`tools/export_docs.py`), stale + vNext files removed,
> `BITSET_MAP.md` rewritten from verified reads, `README.md` index added;
> final review corrected bg/overlay to menu-frozen-but-splash-randomized (§4.1)
> and asserted the highlight block (S225/227–233, §3f). Tallies unchanged.

## 0. Direct answer

**No — they were not 100%.** Before this audit:

- ~35 curated names were **provably wrong** (read the code: wrong behavior, wrong
  static, inverted flag, swapped pair) — all fixed in this round (see §3).
- 27 statics used by the code were **missing from the map entirely** — all named now.
- ~147 labels + 56 statics were still **honest placeholders** (`Func_*`, `gUnk_*`,
  `Page_StaticText_*`) — not claims, so not "wrong", but the map was not complete.

After Round-2, **every curated name passed its evidence check** (CHECK = 0) and
**every static touched by the code was in the map** (unmapped = 0). Round-3
(Track-0) then closed the §6.4 micro-questions by reading the code: 54 more
labels + 10 more statics became VERIFIED (93 labels + 46 statics remain
unnamed), one audit claim was **corrected** (settings are per-setting
LIVE vs frozen, §4.1). Track-1 then line-read every LIKELY internal label:
68 are now VERIFIED (3 renamed first), 1 stays LIKELY (UNK native).
Track-2 named every one of the 93 unnamed labels from full body reads —
no placeholders remain among labels. Track-3 named all 46 unnamed statics
from reads + Statics.c inits — no placeholders remain anywhere — and fixed
3 more wrong names (§3h). The §6.3 human-read backlog then closed (§3i:
weapons/tick/spawner/teleport/outfit reads), and a final review corrected
the bg/overlay-frozen claim (splash randomization, §4.1) — with one caveat: names
marked LIKELY/VERIFIED-by-tool passed structural checks but were not all read
line-by-line by a human (see §5 vs §6).

## 1. Method

1. **Parser** (`verify_names.py`): comment-tolerant CSA parser → 272 functions,
   2,466 labels, full callers/call graph, per-function natives/strings/static
   R/W/P refs, switch tables, jump refs.
2. **Evidence rules**: each curated name gets 1–4 falsifiable checks, e.g.
   `Loader_AddMenuEntry` must have ~87 callers + `DOES_SCRIPT_EXIST` + write
   S1[134/136]; `Page_*_Impl` must contain topic keywords in its `PushString`s;
   `gMenu_CurrentPage` must be the subject of the 48-case switch in `Main_Tick`.
3. **Direct reading**: ~200 functions and ~90 statics verified by reading the
   actual instructions (list in §5). This is what caught the wrong names —
   several had *plausible* heuristic evidence but wrong bodies.
4. **Corrections applied** to `tools/rename_map.json` + mirrored to
   `tools/rename_map_full.json`; verifier re-run until CHECK = 0.

Verdict meanings: **VERIFIED** = multi-point evidence matches · **LIKELY** =
pattern match, spot-check advised · **UNNAMED** = placeholder, no claim ·
**CHECK** = contradictory evidence (zero remain).

## 2. Scoreboard

| Set | Before | Round-2 | Round-3 | Track-1 | Track-2 | Track-3 | **Final** |
|---|---|---|---|---|---|---|---
| Labels VERIFIED | 89 | 125 | 179 | 247 | 340 | 340 | **340** |
| Labels LIKELY | 63 | 69 | 69 | 1 | 1 | 1 | **1** |
| Labels UNNAMED (placeholders) | 173 | 147 | 93 | 93 | 0 | 0 | **0** |
| Labels CHECK | 16 | 0 | 0 | 0 | 0 | 0 | **0** |
| Statics VERIFIED | 190 | 284 | 294 | 294 | 294 | 340 | **340** |
| Statics LIKELY | — | 12 (reserved icon-palette slots, 0 reads) | 12 | 12 | 12 | 12 | **12** |
| Statics UNNAMED | 59 | 56 | 46 | 46 | 46 | 0 | **0** |
| Statics CHECK | 76 | 0 | 0 | 0 | 0 | 0 | **0** |
| Statics in code but missing from map | 27 | 0 | 0 | 0 | 0 | 0 | **0** |

## 3. Proven-wrong names found & fixed (read the code)

### 3a. Fabricated UI names — the big catch

| Old (wrong) | Now (verified) | Evidence |
|---|---|---|
| `Label_344` = `UI_ClearTemp` | `UI_ApplyOverlayTexture` | `StaticGet2 365; Switch[0..9]` → sets S1[253]=`chaos_textures_1..10` (L8178+). Called per-frame from 1151. |
| `Label_345` = `UI_BeginDraw` | `UI_ApplyBackgroundTexture` | `StaticGet2 364; Switch[0..3]` → S1[252]=`TPBackground1..4` (L8125+). Per-frame from 1151. |
| `Label_346` = `UI_EndDraw` | `UI_ApplyMenuPosition` | `StaticGet1 63; Switch[0..2]` → sets geometry S1[0,1,2] (L4408+: right/center/left presets). Per-frame from 1151. |

### 3b. Fabricated "RowColorSet" static family

| Old (wrong) | Now (verified) | Evidence |
|---|---|---|
| S2[364] `gUI_RowColorSetA_R` | `gTheme_BackgroundChoice` | 0..3 index, switch in 345, display `[N/4]` in 2314. **Menu-frozen** (row drops the address, §4.1) but **splash-randomized** (291 → U7 cases when S77.0). |
| S2[365] `gUI_RowColorSetA_G` | `gTheme_OverlayChoice` | 0..9 index, switch in 344, display in 2317. **Menu-frozen** but **splash-randomized** (same path, §4.1). |
| S2[366] `gUI_RowColorSetA_B` | `gAnim_SelectedIndex` | Cycled 0..27 in animations page (L18543+); name table in 1964 (28 anims). LIVE. |
| S2[367] `gUI_RowColorSetB_R` | `gPlayerMove_Row2_Index` | Cycled 0..24 in player page (L11208+); 25 move names in 1168. LIVE. |
| S2[368] `gUI_RowColorSetB_G` | `gPlayerMove_ApplyFlag` | Read-only (4 reads, 0 writes) → always 0 → clipset path in 633 never triggers. **DEAD**. |
| S2[369] `gUI_RowColorSetB_B` | `gPlayerOpt_Row3_Index` | Cycled 0..55 in player page (L11220+). LIVE. |
| S2[371] `gUI_ScrollbarId1` | `gInput_BackKeyChoice1` | Switch in 2278 → sets S204; display `[N/14]` in 729. **LIVE** 0..13 via 2279-rows (init 12 — §4.1 corrected the old STUCK note). |
| S2[372] `gUI_ScrollbarId2` | `gInput_BackKeyChoice2` | Switch in 2280 → sets S205; display in 745. **LIVE** 0..13 (init 13). |

### 3c. Other wrong names

| Old (wrong) | Now (verified) | Evidence |
|---|---|---|
| S1[63] `gColor_TextSelected_R` | `gMenu_PositionMode` | Init **2** (L147), 3-way geometry switch in 346, settings row `Posicion Del Menu` (L27215). **FROZEN@2** (exhaustive: only writers are the L0 init + the frozen row's pStatic — §4.1). |
| S1[67] `gColor_Icon_G` | `gTheme_IconAlignFlag` | Gates `UI_ResolveIconX` (561: S0+0.005 vs S1−0.01125), mirrors S68 text flag. |
| S1[198] `gInput_PrevSelectedRow` | `gUI_VisibleRowCount` | Written by 1151 as min(opts,rows) (L4482); scroll-wrap limit in 111 (L3672/3678). The old heuristic name was right; the re-rename was wrong. |
| S1[203] `gTheme_PaletteId` | `gSplash_ShowOpenHint` | Splash-local: shows `Presiona LS+RS…` hint if set (L3728), cleared on open (L3762), init 1 via Statics.c. |
| S1[253] `gOutfit_CurrentIdx` | `gTheme_OverlayTex` | Holds `chaos_textures_N` strings (344 + dead presets), consumed by 1151. |
| S2[390] `gCustomScript_NameBuf` | `gCustomScript_Opt_9` | 10th opt slot paired with names (L18194-18196), not a name buf. |
| S2[411] `gProt_PlayerListCache` | `gVehicle_SpawnState` | R/W only inside vehicle spawner 1509 (+read in 2437). Zero player-list connection. |
| `Label_450` kept old `Util_MakeButton…` | `Util_BuildButtonSpriteName` | Verified rename was documented but never applied — applied now. Body re-read: `"button_"+id` → S2[359] (L5893+). |
| 401/402 unnamed (audit claimed Down/Up) | `CustomScript_CountUp` / `CustomScript_SelectNext` | 401 does S132+1 (UP, cap 10); 402 does S197+1 (selection, not a counter at all). Both called from 1942 on add. |

### 3d. New names for previously-unnamed (all read, HIGH confidence)

`UI_ShowKeyboard` (399), `CustomScript_StoreKeyboardResult` (400),
`CustomScript_AddEntry` (1942), `Util_IntToString` (370 — the `(N/M)` helper),
`Settings_PositionRow` (2276), `Util_DropOne` (2277 — stack balancer, see §4),
`Input_ApplyBackKey1/2` (2278/2280), `UI_Draw_BackKeyChoiceRow1/2` (729/745),
`UI_Draw_BackgroundChoiceRow` (2314), `UI_Draw_OverlayChoiceRow` (2317),
`Anim_NameTable` (1964), `PlayerMove_NameTable` (1168),
`PlayerOpt_Row3_NameTable` (1169), `Player_ApplyMovementClipset` (633),
`Array_GetIndexed_408` (1989), `UI_PrintRowEx` (453), `UI_Draw_SettingRow` (483),
`UI_Draw_ScrollArrows` (355), `UI_Draw_HeaderSprite` (320),
`Theme_ApplyHeaderPreset` (2386), `Vehicle_ApplyPlateText` (2439),
`UI_ResolveIconX` (561); statics `gTheme_BackgroundTex/OverlayTex` (252/253),
`gLang_ChoiceIndex` (S2[374]), `gCustomScript_Name_0..9` (S2[271+8k]),
`gCustomScript_Opt_0..9` (S2[381..390]), `gBits_Features11..15` (S1[154/156/158/161/164]),
`gBits_SpriteOutline` (S1[176]), `gArray_Base_408`, `gVehicle_PlateTextBuf` (S2[419]),
`gVehicle_CustomPlateEnabled` (S2[418]); dead slots → `gDead_*` (90, 128, 257–260, 262, 268–270).
Internal-label re-anchors fixed: 437/438/440 → `UI_DrawHighlightBar__*`,
452 → `UI_DrawStreamedSprite__*`, 429 → `Sfx_Play_FrontendDefault__Muted`,
413 → `CustomScript_CountUp__Done`. vNext-reserved slots (out of plans) → `gReserved_*`
(documented-free, zero refs).

### 3e. Round-3 (Track-0) corrections & newly-read names

| Old (wrong) | Now (verified) | Evidence |
|---|---|---|
| S1[120–127] per-aspect guesses | `gVehicle_Idx_Industrial…Trailers` | Each slot is a per-class model index, cycled in 106; class titles + case counts read (§4.5). The aspect theory was wrong. |
| S1[154/156/158/161/164] `gBits_Features*` | `gTmp_ImpactCoordA/B/C`, `gTmp_WeaponHudStats`, `gTmp_NearbyVehicles` | L6 tmp buffers/handles (impact coords, weapon HUD, nearby-vehicle scan), not bitfields. Distant BIT natives fooled the old rule (now adjacency-based). |
| S2[391] `gAnim_WasSelected` | `gDead_391_Zero` | Exhaustive grep: 7 reads, 0 writes, 0 pStatic → constant 0; its branches never fire. |
| S2[381–390] `gCustomScript_Opt_0..9` | `gDead_381_Zero…gDead_390_Zero` | Pushed as args but `Label_1940` never reads them (no pGet, hardcodes 1024); never written. |
| S1[173] `gList_RowCounter` | `gInput_HoldCounter` | All users (111/466/1179/1181 via tick 279) use it as a hold-repeat counter, never as a list index. |
| `Label_279` = `UI_NextListRow` | `Input_HoldTick` | Body only ticks S173; called only from input hold paths. |
| `Label_2276` = `Settings_PositionRow` | `Settings_PositionNameTable` | `Function 0 5`: returns Left/Centre/Right word indexed by S63 — a name table, not a row. |

New VERIFIED names from reads: `Page_MainMenu_Impl` (62, root menu),
`Input_SetCycleDelay` (462 → S207), `Input_IsCyclePressed` (466),
`Input_CyclePtrValue` (486, the generic cycler), `UI_Draw_CycleArrows` (491),
`UI_Draw_RowValueText` (500), `UI_Notify_Punisher` (1240),
`Anim_MapRowIndex` (1966, returns row 0→1 when S2[391] set — currently
identity since 391 is dead-0), 22 `Vehicle_Pick<Class>` switches (1361–1382) +
22 `Vehicle_Show<Class>Idx` displays + slots `gVehicle_Idx_<Class>` (S1[106–127]),
`gTmp_DeleteGunTarget` (155), `gTmp_TintWeapon` (157), `gTmp_AimbotTarget` (159),
`gTmp_AimWeapon` (160), `gTmp_NearbyVehInit/Count/Idx` (163/165/166),
`gNotify_LastHandle` (S2[375]), `gTmp_ParachuteState` (S2[376]),
`gInput_CycleDelay` (S1[207], only writer 462 / only reader 466),
`UI_Draw_CycleRow` (497, F11), `UI_Draw_CycleRowEx` (2279, F15 — back-key rows
+ sprite vals via 512).

### 3f. Track-1 internal-label audit (68 VERIFIED, 3 renamed)

All 69 LIKELY labels turned out to be internal jump labels (`Owner__Suffix`),
each verified against its target block + incoming jump sites:

| Old (wrong) | Now (verified) | Evidence |
|---|---|---|
| `Help_DrawCustomKeys__AfterKey21` (2398) | `…__AfterChangeValues` | Join after the Change-Values/Change-Text-Values conditional (29104–29111); no key 21 exists anywhere in 458 (keys used: 10/11/30/31). |
| `CustomScript_MenuEntry__ShowRemoveHint` (416) | `…__RemoveEntry` | Block clears the entry (`StrCopy ""`, S132−1, S197 adjust) when control 179 is JUST_PRESSED on the selected row; the "Remove" glyph hint lives outside the block (5428–5430). |
| `Help_AddButtonSlot__WaitLoad` (422) | `…__SkipUnloaded` | Body is a bare `Return` on the not-loaded path — no wait loop; bails until the movie loads. |

Kept as LIKELY (honest): `World_ClearAreaAroundPlayer__ClearAll` (692, case 0
over `UNK_20E4FFD9` — reads like the generic clear-all, but the native is
unidentified). Closed in final review: `UI_DrawHighlightBar__EnabledBranch`
(437) splits on S225 = `gHighlight_Themed` (R={108,320,436}, W={1,108});
S227–233 are the highlight/icon W/H/RGB block (R={320,436}, W={1,2386}) —
the split is themed-vs-plain highlight bar, suffix confirmed, asserted
rules added to the verifier.

### 3g. Track-2 naming (93 unnamed → 0, all from body reads)

Families named in 7 batches (every name read + asserted, CHECK stayed 0):
row renderers (`UI_RenderCycleRow` 319, `UI_RenderValueRow` 501,
`UI_RenderIntValueRow` 488, `UI_RenderFloatCycleRow` 456, value texts 500/464/
487, arrows 491+460/461/516/517/518, wrappers 2315/1847/1283/2382),
cyclers (`Input_CycleFloatPtrValue` 463, repeat pair 1179/1181 on S208),
anim (`Anim_PlaySelectedAnim` 604 — incl. dead remote-scene branch),
outfit (`Outfit_ApplyFullSet` 1915 F30, `Outfit_GetTargetPed` 2084,
`UI_Notify_Outfit` 1916), player model (`Player_ApplyModel` 690,
`Util_WaitForModel` 2414), weapons (219/198 give + delayed),
net status lists (169/255 + 171/267 + 260/262/264/272), HOST/FPS rows
(363/364 + 369 fps computer + **367 `Net_BrokenHostValue` — returns constant
1073886904, result of the active-check discarded; looks like an author bug,
compare working 262**), teleport (1239 + 1166/220 resolver twins),
HUD color editor (2324/2325/2326/2327/2342/2357), vehicle spawn appliers
(2435/2436/2437/2438/2442 + 2449/2452), stats (`Stat_GetMPPrefix` 1844),
misc UI (1152/1153 banners, 1157 two-string banner, 1155 language applier,
2281 rows table, 1845 concat, 352 alien overlay, 365 scrollbar + 377 easing,
554 row markers, 1319 timed print, 1241 identity shim, 1846 clear-area text,
2381 sprite-type display, 291 splash random-theme,
199 cam-point, 227 force-push, 324 header-size, 356 text-style, 326 measure,
389 centre-flag).
Dead code named `Dead_*` (U0 raw mem-walk from 30388384, U1 glare, U2 text
preset, U3–U5 row variants, U6 num-table, U7 theme-preset table **(entry dead
but case blocks live via 291's random jump!)**, U8/U9 notify variants,
475 unreached arrow-row). Verifier grew `str_ops` tracking, a `Dead_` rule and
60+ asserted name rules; also fixed: RE_PUSH alternation bug (multi-digit args
mis-split) and 220's `Tick_` prefix collision.

### 3h. Track-3 statics (46 unnamed → 0, reads + Statics.c inits)

Full R/W/P census first (all 46: none init in L0/L1), then 4 batches —
every name read + asserted, CHECK stayed 0 (two rule bugs caught and fixed
en route: internal-vs-function attribution, `_Zero` generalization):
input (`gInput_PageRepeatDelay` 208, set by 5 pages for the 1179/1181
repeat pair — parallel to S207), net cursor (`gNet_ListYCursor` 171),
scroll (`gUI_ScrollKnobY` 206, `gUI_ScrollArrowsAlways` 245 — “Scroll Arrows
Always” bit in settings 83, gated in 355), banner colors (215–218 player-name
RGBA in 1153, 219–222 WELCOME RGBA in 1152 — Statics.c inits (4,255,255,255)
and (7,255,255,255), near-cyan), header shifts (226/237: selection-dependent
Y offsets subtracted in 320, resolved by 324 on selected-row match),
1151 menu geometry (250/251 bg center/height, 254 overlay Y, 255/S256 name-bg
W/H, 246 footer Y — incl. the CEX/DEX/HEN + BLES/BLUS footer texts),
tick scratch (152 one-shot FX-clean latch, 169 repair-vehicle target — both
in `Tick_ApplyToggleEffects` 6), `gUtil_ItoSBuf` 172 (370's string buffer),
`gCheat_AimedEntity` 170 (227's aim out-param), net flags (257/262 Show-Host/
Show-FPS bits, 258–260 row RGB, 261 value, 263 suffix, 264 timer flag, 265
frame base), `gMisc_PS4Mode` 380 (“PS4 Mode” bit 1 in 71 — **pokes global
19425336** + timecycle swap), spawn state (378/379 radio-off/godmode toggles,
412 pair-gate, 411 state 0→1→2, 413/414 vehicle A/B, 415–417 paint RGB),
`gAnim_SyncScene` 406. Read-only zeros confirmed via Statics.c (flat
`Static_N`, S2[k]=Static_256+k — **no init lines for any of them**):
363 (U7-head only), 400 (→ `Outfit_GetTargetPed` always returns player ped),
407 (→ `Array_GetIndexed_408` always index 0), 409 (690's prefix).
Findings: 381–390 are vestigial per-script flags — 71 pushes them as 1940's
2nd pointer but 1940 (`Function 1 3 0`) never touches getF1 1 and contains no
pGet/pSet, so all 10 pushes are dead; S414 stored but never read; 258–260 are
never set so HOST/FPS rows render black. Wrong-name fixes: 226
`gUI_TextPadY` → `gUI_HdrSpriteShift` (only header fns 320/324 touch it),
237 → `gUI_HdrSubShift`, 401–405 `gArray_VehicleCache_A–E` →
`gHudColor_Idx/R/G/B/A` (editor page 89 + kit 2325/2342/2357),
152/169 `gTick6_*` → `gTick_*` (owner is `Tick_ApplyToggleEffects`).

### 3i. Backlog reads (104 + 6 + 1509 + 67 + 74–78 + 81 — all confirmed)

`Page_WeaponsOptions_Impl` (104, 613 lines): 21-case switch fully mapped —
Give-All = **56 hard-coded hashes** via `Weapon_GiveToPlayer` (incl. the
airstrike marker −1312131151), Remove-All, Reload, then 18 toggles: 72.23
InfiniteAmmo, 72.21 1-Shot (1E10 damage, one-shot natives, no tick needed),
138.27 Money, 138.26 Delete, 138.2 Teleport, 138.1 Rainbow, 72.2 Thermal,
147.12 NightVision, 72.15 Invisible, 72.18 Airstrike, 72.31 Aimbot,
**MEM[119392] Big Gun (raw pGet/pSet toggling float 1.0↔2.0 — weapon scale)**,
142.16 Boost, 147.13 SlowMo, 71.19 HiddenCutscene, 162.6+168.1 Force (double
bit), 142.23 Fire, 142.24 Explosive. Thermal/Night rows gate their OFF path
on `UNK_1FE547F2` / `UNK_62619061` (0-arg predicates, plausibly the vision-
state checks — a web hash search returned nothing, they stay UNK).
`Tick_ApplyToggleEffects` (6, 1,132 lines): all 49 `IS_BIT_SET` sites dumped;
104's 18 bits land exactly (impact-coord Money pickup 289396019, Delete via
155 = `gTmp_DeleteGunTarget` ✓, Teleport +1.0z, random tint 0–7, flare-give +
impact+75z + `UNK_CCDC33CC` Airstrike, head-bone-31086 Aimbot, aimed-vehicle
speed-100 Boost, per-frame Fire/Explosive, cutscene weapon-hide, 227 Force).
The rest of L6's bits belong to other cheat pages (godmode/invisible/wanted/
jump/vehicle/network blocks). `Vehicle_Spawn_ByHash` (1509, 222 lines) read
end-to-end: model validation + 3 error strings, delete-current-vehicle +
speed-vector restore, offset/coords, network reserve + `VEH_TO_NET` +
`UNK_D3850671`, plane/heli ground-skip, pair store, appliers 2435–2439/2442,
warp-in via S95 (`gVehicle_SpawnInside` ✓). **S2[410] is never written
anywhere (no W, no P, no Statics.c line) → `gNet_IsSessionHost` was wrong,
now `gDead_410_Zero`; 1509 therefore always takes the self-spawn path and
its “Vehicle spawned.” notify never shows.** Teleport family: hub 74 (13
destinations incl. z=2987 “Hight Sky” and z=1E9 “Outer Space”) + SecretPlaces
75 + Interiors 76 (30 rooms) + Infinite8 77 + UnderWater 78, all funnelling
coords through S2[397/398/399] into shared applier 2008 (85 calls, veh-or-ped
`SET_ENTITY_COORDS`; full-map name fixed to `Teleport_SharedApplier_397_399`
— it sits in 73's span so the positional name blamed Animations). Outfits:
router 67 (Male/Female submenus + Random/Godly/Death script entries) and male
page 81 (4 submenus + 16 outfits, each credit-line + `Outfit_ApplyFullSet`
1915 + notify 1916, zero natives). All backlog names confirmed as-is (bit tables: `docs/BITSET_MAP.md` §1–§2).

## 4. Architecture discoveries (bigger than naming)

1. **The cycler exists — but a dropped address freezes 4 of 6 settings.**
   Round-2 claimed "no PtrSet anywhere"; the parser had simply missed the bare
   `pGet`/`pSet` opcodes (161 `pSet` + 71 `pGet` in the script — now tracked).
   The real mechanism, read end-to-end:
   - Settings rows push `title + value-word + pStatic(addr) + apply-fn + 8 numbers`.
   - `UI_Draw_CycleRow` (497, F11) / `UI_Draw_CycleRowEx` (2279, F15) forward
     `(addr, min, max)` into the row renderer (319), which calls
     `Input_CyclePtrValue` (486): a generic `*addr++/--` cycler with wraparound
     on LEFT(166)/RIGHT(167) via repeat-aware `Input_IsCyclePressed` (466) +
     `Input_SetCycleDelay` (462 → S207) + hold counter (S173/279). Row chrome:
     `UI_Draw_CycleArrows` (491, ◀ ▶) + `UI_Draw_RowValueText` (500).
   - The apply-fns (344/345/346/2282) are `Function 0` with balanced case bodies
     and `Return 0 1`, so the pushed address passes THROUGH them untouched and
     emerges as their return value (verified: calls balanced, cases net-0).
   - **The bug:** on 497/2315-rows the author inserted `Util_DropOne` (2277)
     after the apply-call — apparently believing the return was a SECOND copy
     of the address (12 values for 11 params). It isn't (pass-through reuses the
     same slot), so 2277 discards the ONLY copy: 497 receives 10 values, its p2
     is the number 0 instead of the address, and 486 cycles address 0 while the
     real setting never changes. (Without 2277 the fit is a perfect 11.)
   - Per-setting verdicts: **LIVE** — back-key choice 1/2 (S2[371/372]:
     2279-rows push the address AFTER the 5-valued apply, no 2277 in range,
     0..13, inits 12/13). **FROZEN-from-menu** — position (S63@2), bg choice (S2[364], via third renderer 2315), overlay choice (S2[365]), rows-per-page
     (S2[373]@1). Anim/player indices (hardcoded cycling, no 497) were always LIVE.
   - Correction (final review): bg/overlay are frozen *from the settings rows* but NOT constant — splash 58 calls 291, which (when
     `gTheme_RandomOnOpen` S77.0 is set in settings 83) jumps into U7's case blocks (571+) and randomizes textures 252/253, choices
     364/365, and colors 39–41/45–47. S63 and S373 have no other writer (exhaustive census: L0/L1 init + the frozen row's pStatic),
     so position@2 and rows-per-page@1 are truly frozen; 364/365 are menu-frozen but splash-live.
   - Open runtime question: every LEFT/RIGHT press on a frozen row makes 486
     `pGet`/`pSet` address 0 — statically unverifiable whether that churns S1[0]
     (menu X, masked by per-frame re-apply), hits dead scratch, or crashes.
     One-line fix if ever wanted: delete the `Call @Label_2277` on those rows.
2. **Half-dead theme presets.** `UnusedFunction_7`'s *entry* is dead (S2[363] reads constant 0) but its case blocks are the splash
   random-theme writer: 291 (called once from splash 58, gated on `gTheme_RandomOnOpen` S77.0) jumps to the same cases (571+) and sets
   textures 252/253, choices 364/365, colors 39–41/45–47. The other U* (U0 raw mem-walk from 30388384, U1 glare, U2 text preset,
   U3–U5 row variants, U6 num-table, U8/U9 notify variants) have 0 callers, as does 475's arrow-row — kept as documentation.
3. **Dead feature:** movement clipset (`Label_633`) is gated by S2[368], which
   is never written (always 0) — the feature can never trigger in this build.
4. **Dead slots:** S1[90/128/257–260/262/268–270] are init-only, never read.
5. **Vehicle spawner = 22-class slot/switch/display machine.** S1[106–127] are
   per-class model indices (not aspects — the old aspect names were wrong).
   Each class owns one switch (`Vehicle_Pick<Class>`, 1361–1382, `Function 0`,
   `StaticGet slot; Switch`) routing to one display (`Vehicle_Show<Class>Idx`,
   `Function 1`, prints `MODEL (N/M)`), all called from `Page_VehicleSpawner_Impl`
   (106), which also clamps/cycles every slot. Classes/counts: Super 11, Sports 21,
   SportsClassics 16, Coupes 13, Muscle 18, Compacts 7, Sedans 23, SUVs 20,
   OffRoad 16, Motorcycles 22, Bicycles 7, Emergency 18, Service 8, Utility 18,
   Industrial 11, Military 5, Planes 18, Helicopters 15, Boats 13, Vans 29,
   Commercial 10, Trailers 17 (case counts == `/M)` suffixes, 22/22 exact).
   Titles are bilingual (ES picked first via `Util_LangPick`, 163).
6. **Corrections to old details:** rows-per-page is 9..15 over 7 cases (not
   9..12); `UNK_029D3841` result `!= 0` feeds highlight "isRunning"; 177-confirm
   is suppressed (returns 0) while 202/203 held — not an R1+L1 combo.

## 5. Personally verified by reading (strongest claims)

- **Protocols:** boot guard → `Mod_Init_Main`; `Main_Tick` (WAIT/129/5/6/
  network/pause-guard/48-case switch); queue (134/135/136 + REQUEST →
  HAS_LOADED → START → NO_LONGER_NEEDED → clear); language (357=1→ES,
  callers pass ES first); help bar (150 set in 458, read+cleared in Tick);
  page stack push (455: 175/186/174) and pop/scroll-wrap (111, incl. S198
  wrap limit + S131 = timer+750); back nav (275: 28/29 save, 204/205 keys);
  139.9 pSet flood (16+ globals); 137.0 PTFX clear; splash hint (203).
- **Functions:** 0,1,3,4?,5(queue+help+bits),6,9,58,60,111,119,145,163,164,167,
  173,275,279,283,298,314,331,344,345,346,370,396,397,399,400,401,402,418,427,
  436,439,441/442,450,453,455,458,481,483,546,551,552,561,729,745,1155,1158,
  1163,1168,1170,1835+423/424/425/428/426,1940,1942,1964,1989,2276,2277,2278,
  2280,2282+747..753,2314,2317,2315,320,355,633,1509,2439,263,1148/1149.
  (`?` = partially — head + key blocks only.)
- **Round-3 (Track-0) reads:** full bodies — 62, 279, 319, 346, 462, 466, 486,
  491, 497, 500, 604 (head), 1179, 1181, 1240, 1966, 2276, 2278/2280 (tails), 2279 (full), bg/overlay/rows-per-page row sites;
  heads — all 22 spawner switches (1361–1382) + all 22 displays;
  contexts — S1[154–166] in L6, S2[375/376], S2[391] readers, 8 spawner rows.
  Cycler chain verified end-to-end: settings row → 497 → 319 → 486 (pGet/pSet)
  with 466 repeat + 462 delay; apply-fns return the address by pass-through
  (`Function 0`, balanced cases, `Return 0 1`; Label_2 balanced).
- **Track-1 reads:** all 69 internal jump targets + incoming sites across 15
  owners (546/436/418/427/552/331/481/551/327/1163/458/164/119/5/1835/401/1940/
  163/2455/111/275/298/283/397/173), plus full bodies of 436, 458 (head), 1163
  (head) and 119 (head) to settle suffix disputes.
- **Track-2 reads:** full bodies of all 83 unnamed functions + 10 dead
  functions (batches 1/2a/2b/2c/2d/2e/2f/2g), incl. 319/456/463/475/483-family
  row renderers, 604, 690, 1157, 1915, 1984-adjacent 1988/1989, 2279/2315/2382
  wrappers, 2435–2452 spawn appliers, U0–U9 dead set.
- **Track-3 reads:** full R/W/P census of all 46 unnamed statics; line-reads —
  83 (257/261/264/245 toggle rows), 71 (380 PS4-mode row + 381–390 pushes),
  1151 (250/251/254/255/S256/246 geometry), 320/324 (226/237 shifts), 370
  (172 buffer), 1509 (412/413/414 pair store), L6 (152 latch, 169 repair
  chain), 1152/1153 (banner strings), 1940 (2nd-pointer-ignored proof);
  Statics.c flat-init dump (215–222 inits; 363/400/407/409 + 258–260 +
  378/379/412/413/414 zero-at-boot confirmed).
- **Backlog reads:** 104 (all 21 cases + 18 toggle pairs + 56-hash give-all),
  6 (all 49 bit sites + 5 calls), 1509 (full 222-line pipeline), 67 + 74
  (full bodies), 75–78 (row census), 81 (21 rows + 16 outfit blocks + dispatch),
  2008 (shared applier + 85 callers); S2[410] write-census (zero everywhere).
- **Static inits spot-checked:** S63=2, S70=0, S71.10/72.5 boot bits, S60=0,
  S61=145, S62=255, S64–66=1, S67/68=0, S69=1, S74=0, S75=1, S88–93=1,
  S120–127=1/1…, S128=−1, S223=10.0, S2[267]=11.0, S2[373]=1, S2[353/354/356]
  tex names, S234–240=255, S371=12, S372=13, S204=185, S205=186.
  Track-3: S215–218=(4,255,255,255), S219–222=(7,255,255,255); S226/237,
  S245/246/250/251/254/255, S170/171/172/208/206/152/169, S2[256–265],
  S2[363/378/379/380/400/406/407/409/412–417] all zero-at-boot (no
  Statics.c line, no L0/L1 init).

## 6. Honest gaps — what is still NOT 100%

1. **0 unnamed labels** — Track-2 named all 93 from body reads.
2. **0 unnamed statics** — Track-3 named all 46 from reads (§3h).
3. **1 LIKELY label left** — `World_ClearAreaAroundPlayer__ClearAll` (692):
   case 0 over `UNK_20E4FFD9`, plausibly the generic clear-all but the native
   is unidentified, so it stays honestly LIKELY. (The other 68 ex-LIKELY are
   now human-VERIFIED, §3f.) Remaining human-read backlog for tool-VERIFIED
   functions: CLOSED — 81 (male outfits) + 67 (router), 74–78 (teleport
   family + shared applier 2008), 104 (21-row bit map), 1509 (full pipeline),
   6 (all 49 bit sites), see §3i. Leftovers, all low-risk: outfit sub-pages
   82/84/85/97/98/99/102 (same 1915-pattern as 81, tool-VERIFIED), L6 bits of
   other cheat pages (sites dumped, most effects identified), 7 UNK natives
   with context hypotheses (thermal/night predicates, airstrike, flare-give),
   692 (still the only LIKELY, UNK native).
4. **Micro-questions (CLOSED in Round-3):** S1[106–127] = per-class model indices
   (22/22 classes mapped, §4.5); S2[375] = notify handle, S2[376] =
   parachute temp; S2[381–390] = pushed-but-unread (dead); S1[154–166] = L6
   tmp buffers/handles (impact coords, delete-gun/aimbot/tint/army handles);
   62 = main menu; 1966 = row-index map; 319 body = row renderer + cycler
   driver. **Fresh leads:** `Label_1179/1181` (LEFT/RIGHT hold-repeat pair for
   anim rows — naming-ready), `Label_604` (anim-dict loader), per-row 497
   number layouts (min/max/enable/delay/style/keys/flag), S1[208] writers,
   2315/512/2281 renderer family (consumed in Track-1/2/3). Still open:
   pGet(0)/pSet(0) runtime effect (needs a console, can't be read).
5. **Full-map internals** (`rename_map_full.json`, 2,466 labels): owners
   re-anchored for corrected functions, but the ~2,100 auto `__J_*` jump names
   are positional (`…__ShortPage`), not semantic. Fine for navigation, not for
   documentation.

## 7. Files changed & how to re-run
**Source of truth:** `tools/rename_map.json` (+ `_full` mirror) — every correction above lives there.
**Proof:** `tools/verify_names.py` (~120 asserted rules + `VERIFIED_INTERNALS` + `Dead_`/`_Zero` branches) → `tools/verification_report.json` + `docs/NAMING_VERIFICATION_TABLES.md`:

```
python3 tools/verify_names.py            # CHECK must stay 0, UNNAMED must stay 0
python3 tools/export_docs.py             # refresh the 7 derived docs (maps/glossary/defines/headers)
python3 tools/apply_names.py --annotated --in ModLoader.csa --out docs/ModLoader_Annotated.csa
python3 tools/apply_names.py --rename --in ModLoader.csa --out ModLoader_Renamed.csa --map tools/rename_map_full.json
```

**Hand-written docs:** this report, `docs/NAMING_GUIDE.md` (usage + workflow), `docs/BITSET_MAP.md` (verified bit tables), `docs/WHOLE_MOD_OVERVIEW.md` (architecture), `README.md` (index).
**Verifier history:** Round-3 added bare-`pGet`/`pSet`/`GetImmediate1` tracking, adjacency `gBits_` rule, LIVE/FROZEN row-chain rules; Track-1/2/3 added `VERIFIED_INTERNALS`, `str_ops`, `Dead_` branch, `_Zero` rule, function-granularity attribution; backlog/final review needed no structural change (410 + highlight block fell under existing/new asserted rules).
**Workflow:** edit map → add rule → `verify_names.py` (CHECK 0) → `export_docs.py` + `apply_names.py` → note it in §3.

---

# Appendix A — machine verdict tables

> Moved to **`docs/NAMING_VERIFICATION_TABLES.md`** (auto-generated by
> `tools/verify_names.py`; regenerated on every run, never hand-edited).
> Full per-name evidence is also in `tools/verification_report.json`.
