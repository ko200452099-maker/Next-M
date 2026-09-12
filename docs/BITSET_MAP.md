# Bitset Map — What Each Static Bit Actually Means

> `pStatic1 71` means “address of Static1[71]”. `SET_BIT` / `CLEAR_BIT` / `IS_BIT_SET` on that address toggles a 32-bit flagword.
> **Status: VERIFIED.** Every row below was confirmed by reading the set-site (page/toggle row) AND the test-site (tick effect).
> Full evidence: `docs/NAMING_VERIFICATION.md` §3i (weapons/tick), §3f–§3h (settings/net), §5 (protocols).
> This file replaces an earlier guess-based version whose assignments were proven wrong (see “Superseded claims” at the bottom).

## 1. Weapons page (104) ↔ cheat tick (6) — the 18 toggles + Big Gun

Page `Page_WeaponsOptions_Impl` (104) toggles the bit; `Tick_ApplyToggleEffects` (6) applies the effect every frame.
Cases 1–3 are actions (Give-All = 56 hashes, Remove-All, Reload), not bits.

| Static.Bit | Row (case) | Toggle sites (104) | Effect site (6) | Effect |
|---|---|---|---|---|
| 72.23 | Infinite Ammo (4) | 12000 `CLEAR` / 12008 `SET` | one-shot in 104 | `SET_PED_INFINITE_AMMO_CLIP` 0/1 at toggle time (no tick needed) |
| 72.21 | 1 Shot 1 Kill (5) | 12020 / 12031 | one-shot in 104 | weapon + melee damage ×1.0 / ×1E10 at toggle time |
| 138.27 | Money Drop Gun (6) | 12046 / 12051 | 2382 | `CREATE_AMBIENT_PICKUP` (model 289396019) at last weapon-impact coords |
| 138.26 | Delete Gun (7) | 12060 / 12065 | 2413 | free-aimed entity → `DELETE_ENTITY` via S155 (`gTmp_DeleteGunTarget`), firing disabled |
| 138.2 | Teleport Gun (8) | 12074 / 12079 | 2441 | player teleported to last impact coords +1.0z |
| 138.1 | Rainbow Gun (9) | 12088 / 12093 | 2463 | current weapon tint randomized 0–7 every tick |
| 72.2 | Thermal Vision (10) | 12102 / 12111 | 2483 | `SET_SEETHROUGH` on; OFF path gated on `UNK_1FE547F2` (plausibly thermal-state check) |
| 147.12 | Night Vision (11) | 12120 / 12129 | 2509 | `SET_NIGHTVISION` on; OFF path gated on `UNK_62619061` (plausibly night-state check) |
| 72.15 | Invisible Weapons (12) | 12138 / 12149 | 2535 | `SET_PED_CURRENT_WEAPON_VISIBLE` all-zero (unless reloading) |
| 72.18 | Airstrike Gun (13) | 12158 / 12166 | 2557 | gives marker weapon −1312131151, impact+75z → `UNK_CCDC33CC` (18-arg strike native) |
| 72.31 | Aimbot Gun (14) | 12178 / 12189 | 2598 | free-aimed living ped → auto head-shot (bone 31086) from player pos |
| — | Big Gun (15) | 12198–12209, **not a bit** | n/a (instant) | raw `pGet`/`pSet` on MEM[119392], toggles float 1.0 ↔ 2.0 (weapon scale) |
| 142.16 | Boost Gun (16) | 12218 / 12223 | 2645 | aimed entity (or its vehicle) → `SET_VEHICLE_FORWARD_SPEED` 100 |
| 147.13 | Slow Motion Gun (17) | 12232 / 12239 | 2682 | `SET_TIME_SCALE` slowed while aimed/shooting (1.0 restored on toggle-off) |
| 71.19 | Hidden Weapons Cutscene (18) | 12248 / 12253 | 2711 | `HIDE_PED_WEAPON_FOR_SCRIPTED_CUTSCENE` |
| 162.6 + 168.1 | Force Gun (19) | 12262–12273 (both bits) | 2704 → `Call 227` | both bits required → `Force_PushAimedEntity` (227) |
| 142.23 | Fire Ammo (20) | 12282 / 12287 | 2719 | `SET_FIRE_AMMO_THIS_FRAME` |
| 142.24 | Explosive Ammo (21) | 12296 / 12301 | 2727 | `SET_EXPLOSIVE_AMMO_THIS_FRAME` |

## 2. Tick-6 bits owned by other cheat pages (all 49 sites dumped)

Same tick, different owners (player/vehicle/network cheat pages). Effects read at the test-site; the exact toggle row was not traced for each.

| Static.Bit | Test site (6) | Observed effect |
|---|---|---|
| 138.16 | 1992 | `SET_PLAYER_INVINCIBLE` (+ PTFX-guard block at 2061) |
| 138.17 | 2000 | `SET_ENTITY_VISIBLE` (invisibility) |
| 138.28 | 2009 | `SET_PLAYER_WANTED_LEVEL` + `SET_MAX_WANTED_LEVEL` |
| 138.20 | 2020 | `SET_EXPLOSIVE_MELEE_THIS_FRAME` |
| 138.21 | 2027 | `SET_SUPER_JUMP_THIS_FRAME` |
| 72.22 | 2043 | `SET_RUN_SPRINT_MULTIPLIER_FOR_PLAYER` |
| 72.24 | 2034 | `SET_PED_CONFIG_FLAG` |
| 72.13 | 2138 | entity-health block |
| 72.25 | 2166 | `SET_PED_CAPSULE` |
| 72.3 | 2054 | vehicle-presence-gated block |
| 143.3 / .5 / .13 / .16 / .17 / .18 / .20 / .21 | 2174–2374 | network-time/game-progress/radio/helmet-gated blocks |
| 140.0 | 2334 | `SET_PED_RESET_FLAG` |
| 138.24 / .25 | 2735 / 2758 | vehicle damage flags |
| 147.6 / .7 / .9 | 2767–2821 | control-action / just-pressed blocks |
| 71.9 / .11 | 2867 / 2887 | `SET_VEHICLE_BRAKE_LIGHTS` / indicator-lights blocks |
| 162.8 / 72.14 / 167.7 / 168.4 / .5 | 2898–3034 | vehicle speed/state blocks |
| 168.7 | 3050 | **auto-repair gate**: full fix + health + `SET_VEHICLE_ENGINE_ON` via S169 |
| 142.22 | 3087 | in-vehicle-gated block |

## 3. Menu / settings / boot bits

| Static.Bit | Owner | Meaning |
|---|---|---|
| 71.10, 72.5 | `Mod_Init_Main` boot | boot flag bits (set at init) |
| 139.9 | anti-freeze block | the 16× `pSet 197…` global-flood gate |
| 245.0 | settings page 83 ↔ 355 | “Scroll Arrows Always” (`gUI_ScrollArrowsAlways`) |
| S2[257].0 | settings page 83 ↔ 363 | “Show Host” row (`gNet_ShowHost`) |
| S2[262].0 | settings page 83 ↔ 364 | “Show FPS” row (`gNet_ShowFps`) |
| S2[380].1 | misc page 71 | “PS4 Mode” (`gMisc_PS4Mode`, bit **1**; also pokes global 19425336 + timecycle swap) |

Note: Static2 **does** have real bitwords (257/262/380) — set/cleared with `SET_BIT`/`CLEAR_BIT` exactly like bank 1.

## 4. How to read in code

```asm
pStatic1 138         ; address of the S138 flagword (weapon-cheat bits live here)
Push1 26             ; bit 26
CallNative "IS_BIT_SET" 2 1  ; -> is Delete Gun on?
JumpFalse @NotEnabled

; Equivalent C with new names:
if (gFlags_WeaponCheats & (1<<26)) {   // Static1[138].26 = Delete Gun
  DELETE_ENTITY(free_aimed_entity);    // Tick_ApplyToggleEffects @2413
}
```

> To re-derive: `python3 tools/verify_names.py` tracks every `pStatic` + `SET_BIT`/`CLEAR_BIT`/`IS_BIT_SET` site per function (see `ptr_rw` in the parser); the per-bit tables above are the human-read summary.

---

## Superseded claims (old guess-based version — all proven wrong, do not use)

| Bit | Old (wrong) guess | Verified meaning |
|---|---|---|
| 71.19 | QuickTeleportSpam | Hidden Weapons Cutscene |
| 72.2 | NoKnockOff | Thermal Vision |
| 72.15 | InfiniteStamina | Invisible Weapons |
| 72.18 | HelmetHack | Airstrike Gun |
| 72.21 | ArmorHack | 1 Shot 1 Kill |
| 72.23 | StealthMove | Infinite Ammo |
| 72.31 | FreezeGravity | Aimbot Gun |
| 138.1 | VisibleHack | Rainbow Gun |
| 138.2 | InvincibleToggle | Teleport Gun |
| 142.16 | LockDoors | Boost Gun |
| 147.12/13 | Vehicle mods | Night Vision / Slow Motion |
| S2 | “no SET_BIT observed” | 257/262/380 are real bitwords |
