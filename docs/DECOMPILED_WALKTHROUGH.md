# Decompiled Walkthrough — 4 Hot Functions Explained

> Generated from `python3 tools/csa_decompile.py --explain` + manual annotation. 
> Line numbers match `ModLoader.csa` exactly. Pseudo-C column = simplified.

---

## A. `Label_0` — Init & Skin (lines 8–280)

**Purpose:** One-time setup when script first spawns. Network-safe flag + all visual globals.

```c
void Label_0() { // Function 0 2 0  (header: 2 params, 0 locals)
  // line 10
  NETWORK_SET_SCRIPT_IS_SAFE_FOR_NETWORK_GAME(); // allow in MP

  Label_1(); // zero out temp frame / init input exclusive?

  // ----- Safezone-scaled menu geometry -----
  // Label_2 = GET_SAFE_ZONE_SIZE() helper (returns 0.0-1.0)
  Static[0] = 0.2788f + Label_2(); // menu X anchor (left)
  Static[1] = 0.4939f + Label_2(); // menu Y anchor (top)
  Static[2] = 0.3864f + Label_2(); // menu width?

  // ----- Color presets (HUD colour IDs) -----
  Static[3]=0; Static[4]=4; Static[5]=5; Static[6]=6; Static[7]=7;
  Static[8]=12; Static[9]=13; ... Static[27]=39; // HUD colour slots for menu themes

  // ----- Opacity / scale / toggles -----
  Static[28]= -1;     // ? disabled?
  Static[29]= 1.0f;   // alpha
  Static[30]= 0.9f;   // safe-zone 90%

  // ----- RGBA 255 defaults -----
  Static[31..37]=255; // white
  // ... 20 more: blacks, selection colour 145, etc.

  // ----- Bitflags (persisted via Statics.c) -----
  // pStatic1 = &Static1[addr]
  pStatic1[71].SET_BIT(10); // bit 10 → "ModLoader enabled"
  pStatic1[72].SET_BIT(5);  // bit 5  → another toggle

  if ( IS_BIT_SET(pStatic1[73], 12) ) { Static[74]=0; } // language selected?

  // ... 50 more Statics init (scroll width, menu counts, etc)
  Static[100]=0.035f; // item height?
  Static[128]= -1;    // sentinel

  // falls through to Label_4 loop caller via caller, but here just returns
}
```

**Learnings:**
- `fPush 0.2788 + Call @Label_2 + fAdd` is the idiom for *safezone-relative* positioning. Without it menu would clip on 4:3 TVs.
- Statics 3-27 map to Rockstar `GET_HUD_COLOUR` IDs. Change them in `ModLoader_Statics.c` to re-skin.
- Bits 71/72 are the save flags. If you delete `SET_BIT(10)`, loader thinks it's disabled on next reboot.

---

## B. `Label_3` — Main Loop Tick (lines 285–470, called every frame via Label_4 infinite loop)

```c
// Label_4 is literally: while(true) { Label_3(); }
void Label_3() {
  WAIT(0); // yield to scheduler — mandatory or game freezes
  Static[129]=0; // temp clear

  Label_5(); // input + security + script-queue
  Label_6(); // rendering? (sets up scaleform / checks HUD hide)

  // Tell RAGE we are a network script (so peers can see us)
  NETWORK_SET_THIS_SCRIPT_IS_NETWORK_SCRIPT(18, 0, PLAYER_ID());
  Drop( NETWORK_GET_SCRIPT_STATUS() ); // ignore return

  // If player is in pause / warning screen → DON'T draw
  if ( IS_WARNING_MESSAGE_ACTIVE() || IS_PAUSE_MENU_ACTIVE() )
    return; // skip frame

  if ( Static[130] ) Label_9(); // if menu open → draw background/tick?

  // ---- 60-state menu state machine ----
  switch ( Static[130] ) {
    case 0:  Label_58(); break;  // splash / helper?
    case 1:  /* language picker */ if(!Static[70]) Label_60(); else Label_62(); break;
    case 2:  Label_64(); break;  // Mods Menus (22 entries → Label_1835)
    case 3:  Label_65(); break;  // Recovery menus
    case 4:  Label_66(); break;
    // ... 55 more: Cars (6), Protections (7), Freezers (8), Teleports (9), etc.
    case 30: Label_101(); break; // maps beyond
    case 54: Label_105(); break;
    case 59: Label_109(); break; // settings
  }

  // if still open, do post-draw (Label_111 = close animation / input?)
  if ( Static[130] ) Label_111();
}
```

**Learnings:**
- `Static[130]` = **current menu page ID**. Search `StaticSet1 130` to find all page switches (42 hits).
- `Label_5` is the *heart* — handles hotkeys + anti-freeze pSet flood + custom-script queue.
- `Label_6` likely hides HUD components: `HIDE_HUD_COMPONENT_THIS_FRAME`, `HIDE_HELP_TEXT_THIS_FRAME`.

---

## C. `Label_5` — Input, Anti-Freeze, Queued Scripts (lines 471–~650, heavily inlined but key slice)

```asm
:Label_5
Function 0 2 0
  StaticGet1 130 ; Push_0 ; JumpNE @Label_112  // if menu open → skip timer check?
  StaticGet1 131 ; GET_GAME_TIMER ; JumpLT @Label_112 // throttle?
  GET_GAME_TIMER ; pGlobal2 13245 ; SetImmediate2 4621 ; Push2 0 178 ; SET_INPUT_EXCLUSIVE(0,178)
:Label_112
  StaticGet1 93 ; JumpFalse @Label_113
    StaticGet1 132 ; Push1 10 ; JumpEQ @Label_114 → Static[133]= -1 else 0
  :Label_113
  // ----- queued custom script ( .csc ) -----
  StaticGet1 134 ; JumpFalse @Label_115
    if (!Static[135]) { REQUEST_SCRIPT(Static[134]); Static[135]=1; }
    if ( HAS_SCRIPT_LOADED(Static[134]) ) {
      START_NEW_SCRIPT(Static[134], Static[136]); // Static136 = stack
      SET_SCRIPT_AS_NO_LONGER_NEEDED(Static[134]);
      Static[134]=0; Static[135]=0;
    }
  :Label_115
  StaticGet1 137 bit 0 ; JumpFalse @Label_117
    PLAYER_PED_ID ; GET_ENTITY_COORDS ; REMOVE_PARTICLE_FX_IN_RANGE(9999) // clear FX spam
  :Label_117
  StaticGet1 138 bit 12 ; JumpFalse @Label_118
    Label_119(); // ? cleanup objects/cops?
  :Label_118
  StaticGet1 139 bit 9 ; JumpFalse @Label_120
    // ----- GLOBAL FLOOD (anti-freeze) -----
    Push 1317011488 ; Push 19705448 ; pSet
    Push 1317011488 ; Push 19705448 ; pSet // 16x global writes
    ... (global 19716948, 19727748, 19676708 etc.)
  :Label_120
  // ... more protections bits
```

**Pseudo-C:**
```c
void Label_5() {
  if (Static[130]==0 && GET_GAME_TIMER() > Static[131]) {
    SET_INPUT_EXCLUSIVE(0, 178); // allow menu keys without triggering game?
  }

  // throttle ticker
  if (Static[93] && Static[132]==10) Static[133]=0; else Static[133]= -1;

  // --- on-demand script launcher (used by "Add Custom Script") ---
  if (Static[134]) { // pending script hash
    if (!Static[135]) { REQUEST_SCRIPT(Static[134]); Static[135]=1; }
    if (HAS_SCRIPT_LOADED(Static[134])) {
      START_NEW_SCRIPT(Static[134], Static[136]);
      SET_SCRIPT_AS_NO_LONGER_NEEDED(Static[134]);
      Static[134]=Static[135]=0;
    }
  }

  if ( IS_BIT_SET(Static[137],0) ) {
    Vector3 pos = GET_ENTITY_COORDS(PLAYER_PED_ID());
    REMOVE_PARTICLE_FX_IN_RANGE(pos, 9999); // kill grief particle spam
  }

  if ( IS_BIT_SET(Static[139],9) ) {
    // Anti-freeze: patch globals every frame so other modders' freezes fail
    *19705448 = 1317011488; *19716948 = 1317011488; ... // 16 globals
  }
}
```

**Learnings:**
- `SET_INPUT_EXCLUSIVE(0,178)` traps input 178 (likely `INPUT_FRONTEND_RDOWN`).
- The `pSet` block is **the controversial part**. Those globals are known freeze vectors; setting them to `0x4E...` neutralizes them. Toggled via menu `Proteccion De Modders`.
- Custom script queue = how *Add Custom Script* feature works (the one at bottom of Misc). Writes hash to `Static[134]` then Label_5 spawns it.

---

## D. `Label_1835` — Universal Menu Loader (lines 5557–5630, called 87×)

**Signature:** `Label_1835(displayName, scriptName, stackSize, flagA, flagB, enabled)` → 6 args, 19 locals

```asm
:Label_1835
Function 6 19 0
  getF1 1 ; DOES_SCRIPT_EXIST(1) ; JumpTrue @Label_423  // file exists?
    getF1 1 ; pFrame1 8 ; StrCopy 64
    if ( IS_PS3_VERSION() ) PushString ".csc Not Found!" else PushString ".xsc Not Found!"
    pFrame1 8 ; StrAdd 64 ; pFrame1 8 ; getF1 5 ; Label_396() ; Jump @Label_426 // show error toast

  :Label_423
    getF1 0 ; getF1 5 ; Label_396() // draw list entry? (name + colour)
    getF1 3 ; getF1 4 ; Label_427() // draw enable toggle / star icon?
    // is script already running? via UNK_029D3841 hash check
    getF1 1 ; GET_HASH_KEY ; UNK_029D3841 ; 0 ; CmpNe ; Label_418()
    Label_397() ; JumpFalse @Label_426  // if already running AND not pressing X → return

    getF1 1 ; GET_HASH_KEY ; UNK_029D3841 ; JumpFalse @Label_428
      // already running instance → kill it (toggle off)
      getF1 1 ; TERMINATE_ALL_SCRIPTS_WITH_THIS_NAME()
      Jump @Label_426

    :Label_428
      // not running → queue start
      getF1 1 → Static[134] // pending script name hash
      getF1 2 → Static[136] // stack size

  :Label_426 Return 6 0
```

**Pseudo-C:**
```c
void Label_1835(String visible, String script, int stack, int unk1, int unk2, bool enabled) {
  if (!DOES_SCRIPT_EXIST(script)) {
    char buf[64]; StrCopy(script, buf);
    StrAdd( IS_PS3_VERSION() ? ".csc Not Found!" : ".xsc Not Found!", buf);
    Label_396(buf, unk2); // show red error line
    return;
  }

  Label_396(visible, unk2); // draw menu row
  Label_427(unk1, unk2);    // draw highlight/selection

  // anti-duplicate: UNK_029D3841 is "IS_SCRIPT_RUNNING_HASH" ?
  bool isRunning = UNK_029D3841(GET_HASH_KEY(script)) != 0;
  Label_418(enabled); // maybe check input combo? (R1+L1+X flag at 0x... ?)
  if (!Label_397()) return; // Label_397 = "was X pressed this frame?" → if not pressed, just drawing

  if ( isRunning ) {
    if ( UNK_029D3841(GET_HASH_KEY(script)) )
      TERMINATE_ALL_SCRIPTS_WITH_THIS_NAME(script); // toggle OFF
    return;
  }

  // toggle ON → queue for Label_5 to start next tick
  Static[134] = script; // will be REQUEST_SCRIPT → START_NEW_SCRIPT
  Static[136] = stack;  // 512..6304, determines script heap
}
```

**Why it matters:**
- Every one of the 87 entries in `docs/menu_list.txt` is exactly one `Call @Label_1835` with 6 pushes. Example:

  ```asm
  PushString "Brodator"         // visible
  PushString "Brodator"         // file = Brodator.csc
  PushS 1024                   // stack
  StaticGet1 17 ; StaticGet1 7 // flags (category colour maybe)
  Push_1                       // enabled
  Call @Label_1835
  ```

- To **add your own mod**: duplicate those 6 lines. To **remove a grief mod** (e.g. freezes): delete its 6-line block.
- `stackSize` matters: `Eternal Darkness` needs 3584, `Serendipity` 1024, `MoonShine` 6304. Too low = crash, too high = waste.

---

## E. How to Read Any Other Label

1. **Find label** `python3 tools/csa_decompile.py --explain Label_XXXX`
2. **Check header** `Function a b c` → `b` = params, `c` = locals. `getF1 0` = param0, etc.
3. **Follow stack**: Every `Push` pushes, every `CallNative argc retc` pops `argc` and pushes `retc`.
4. **Jumps are `if`**: `StaticGet1 X ; JumpTrue @L` = `if (Static[X]) goto L`
5. **Switch = menu**: `StaticGet1 130 ; Switch [0=@A][1=@B]` = page router. The target labels are your pages.

Full pseudo: `docs/ModLoader_pseudo.c` (8,771 lines, 283 functions). Graph: `docs/callgraph.dot` (render with `dot -Tpng callgraph.dot -o map.png` if `graphviz` installed).

---

## F. Opcode Cheat Card (print this)

```
Push_0..Push_7, Push_1xxx  = push constant
fPush x.f                 = push float
PushString "txt" + PushS n = push string (size n)
StaticGet1 i / StaticSet1 i = Static[i] load/store
getF1 i / pFrame1 i        = Frame param/local
Call @L                   = call function
Jump @L / JumpTrue @L / JumpFalse @L = goto / if
Switch [k=@L]             = switch
CallNative "NAME" a r     = native call
Return a r                = return
pSet / pGet               = *addr = val / val = *addr
StrCopy / StrAdd 64       = strcpy/strcat
```

---

*Next: try `python3 tools/csa_decompile.py --explain Label_62 Label_64 Label_72` to see Mods/Recovery/Credits pages, or `python3 tools/csa_decompile.py --stats` for full frequency.*
