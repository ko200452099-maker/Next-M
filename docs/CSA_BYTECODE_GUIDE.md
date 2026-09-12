# GTA V CSA Bytecode — Complete Guide
*Reverse-engineered from `ModLoader.csa` (29,937 lines, 311 natives, 283 Functions)*

## 1. What is `.csa` ?

`.csa` = **Compiled Script Assembly (text form)** — human-readable assembly emitted by decompilers like `GTA V Script Decompiler`, `SCM Toolkit`, or `Zanzou` before assembling to binary `.csc` (PC) / `.xsc` (PS3/X360). 

It's **NOT encrypted**. It's a stack-machine assembly for RAGE `scrProgram`.

```
ModLoader.csa  -> assembler -> ModLoader.csc (PC) / ModLoader.xsc (PS3)
ModLoader_Statics.c -> Included at compile time, defines initial global/static values
```

Your file is **already decompiled text**, so we can read it directly. Binary `.csc` would be unreadable hex — you have the source assembly.

---

## 2. Execution Model (RAGE VM)

| Area | Assembly Access | Size | Scope |
|------|---------------|------|-------|
| **Stack** | `Push`, `fPush`, `Pop` (implied) |  ~8KB per script | Temp values, call args |
| **Frame (`f1`/`f2`)** | `getF1`/`setF1`, `pFrame1` | Per-Function locals | Function params + locals |
| **Statics (`Static1`, `Static2`)** | `StaticGet1`/`StaticSet1` | 512 + 512 ints | Global to script, persists (saved in Statics.c) |
| **Globals (`pGlobal`)** | `pGlobal2`, `pSet`/`pGet` | Game-wide  0..~200k | Shared memory (used for anti-freeze pSet hacks) |
| **Native Table** | `CallNative "NAME" argc retc` | — | Rockstar exposed functions |

**Calling convention:** PUSH args *right-to-left* → `Call @Label` or `CallNative` → result(s) left on stack.

Example:
```asm
fPush 0.2788
Call @Label_2   ; Label_2 returns float on stack
fAdd             ; pops 2, pushes sum
StaticSet1 0     ; pops stack → Static[0]
```
Pseudo-C:
```c
Static[0] = 0.2788f + Label_2();
```

---

## 3. Directives & Structure

### `IncludeStaticFile ModLoader_Statics.c`
Pulls `Static_XXX = value;` initializers into binary header. At runtime the game loads them as `StaticGet1[i]` initial values.

### `Function <unk> <paramCount> <localCount>`
Start of a function. In ModLoader: `Function 0 2 0` = 0 unk, 2 params, 0 locals? Actually `Function a b c` where `b` = params, `c` = locals. `Function 2 4 0` = 4 params.

### `:Label_XXX`
Jump target / function entry. In CSA **every function is also a Label** — `Call @Label_1835` *is* a function call if that label starts with `Function`.

### `Return <paramCount> <retCount>`
Pop frame. `Return 0 0` = void. `Return 2 1` = takes 2 stack items as params? Actually `Return X Y` = clean X args, return Y values on stack.

---

## 4. Full Opcode Reference (observed in ModLoader)

### Stack / Push

| Op | Args | Stack Effect | Notes |
|----|------|--------------|-------|
| `Push_0`..`Push_7`, `Push_-1` | — | `→ val` | Fast constants |
| `Push_1`, `Push1 12`, `Push2 0 178`, `Push3 ...` | int | `→ int` | `Push1` = byte, `Push2` = short |
| `Push <int>` | int32 | `→ int` | Generic int |
| `fPush <float>` | float | `→ float` | `fPush 0.2788` |
| `fPush_0.0`, `fPush_1.0` | — | `→ float` | Fast floats |
| `PushS <size>` | int | alloc temp? | Used with `PushString` to set buffer size: `PushString "foo" + PushS 128` = string alloc |
| `PushString "..."` | string | `→ string*` | Null-terminated, supports `~r~ ~b~ ~s~` color codes |
| `Dup` | — | `a → a a` | Duplicate top |
| `Drop` | — | `a →` | Discard |
| `pSet` | — | `val addr →` | Write `*addr = val` (global/pointer set) |
| `pGet` | — | `addr → val` | Read `*addr` |

### Arithmetic / Logic

| Op | Stack |
|----|-------|
| `Add`, `Sub`, `fAdd`, `fSub`, `fMult`, `fDiv` | `a b → a+b` |
| `And`, `Or`, `Not`, `CmpEq`, `CmpNe`, `JumpEQ` etc | bitwise/logic |
| `SetBit`, `ClearBit`, `IsBitSet` (via natives) | but also `SET_BIT` native wrapper |

### Memory / Frame / Static

| Op | Effect |
|----|--------|
| `StaticGet1 i` | `→ Static1[i]` |
| `StaticSet1 i` | `val → Static1[i]=val` |
| `StaticGet2 i` / `StaticSet2 i` | Secondary static bank (page 2) |
| `pStatic1 i` | `→ &Static1[i]` (address) |
| `pStatic2 i` | `→ &Static2[i]` |
| `getF1 i` | `→ Frame[i]` (param/local) |
| `setF1 i` | `val → Frame[i]` |
| `pFrame1 i` | `→ &Frame[i]` |
| `StrCopy maxLen` | `src dst →` (copies string) |
| `StrAdd maxLen` | `src dst →` (concatenates) |
| `pGlobal2 g1 g2` | push global ptr? Used with `pSet` hack: `Push 1317011488 ; Push 19705448 ; pSet` = write to global 19705448 |

### Control Flow

| Op | Args | Meaning |
|----|------|---------|
| `Jump @L` | label | unconditional `goto L` |
| `JumpTrue @L` | label | `if (pop()) goto L` |
| `JumpFalse @L` | label | `if (!pop()) goto L` |
| `JumpEQ @L`, `JumpNE @L`, `JumpGT @L`, `JumpLT @L`, `JumpLE @L`, `JumpGE` | | compare top 2? |
| `Switch [0=@A][1=@B][...]` | table | `switch(pop())` — ModLoader's main menu state uses this (see Label_3 Line 312, 60 cases) |
| `Call @L` | label | `push return addr; goto L` |
| `CallNative "NAME" argc retc` | native | Call native, argc args consumed, retc results pushed |

### Misc

| Op | Use |
|----|-----|
| `CallNative "WAIT" 1 0` | yield `WAIT(0)` |
| `Nop` / empty line | padding |
| `Return` | as above |

---

## 5. Walkthrough: Annotated Boot Sequence (first 300 lines)

```asm
IncludeStaticFile ModLoader_Statics.c   // preload colors/flags
Function 0 2 0                          // Entry guard — runs once when script loaded
  CallNative "GET_THIS_SCRIPT_NAME" 0 1 // push "ModLoader"
  CallNative "GET_HASH_KEY" 1 1         // hash it
  CallNative "UNK_029D3841" 1 1         // RAGE helper: does script match this hash? ( anti-duplicate )
  JumpTrue @Label_0                     // if true → continue, else kill
  Return 0 0                            // not our script instance → exit

:Label_0
Function 0 2 0                          // Real main init
  CallNative "NETWORK_SET_SCRIPT_IS_SAFE_FOR_NETWORK_GAME" 0 0 // mark safe for MP
  Call @Label_1                         // init locals? (Label_1 = zero memory / setup)
  fPush 0.2788                          // safezone math: 0.2788 * scale + ...
  Call @Label_2                         // Label_2: get safezone? (returns scale)
  fAdd
  StaticSet1 0                          // Static[0] = menu X ?
  fPush 0.4939 / Call @Label_2 / fAdd → Static[1] // Y
  fPush 0.3864 / ... → Static[2]       // W?
  Push_0 → Static[3] ... Push_7 → Static[7] // color preset IDs (4..7)
  Push1 12..39 → Static[8..27]         // HUD color slots
  Push_1 / fPush_1.0 → Static[28..30] // toggles, alphas
  Push1 255*8 → Static[31..37]        // RGBA 255 = white
  ... 20 more statics init
  pStatic1 71 ; Push1 10 ; SET_BIT    // set bit 10 in flags 71 → "mod enabled"
  Call @Label_3 ; Jump @Label_4       // goto main loop

:Label_4
  Call @Label_3
  Jump @Label_4                         // infinite loop: while(true) { Label_3() }

:Label_3
Function 0 2 0
  Push_0 ; CallNative "WAIT" 1 0       // WAIT(0) — yield
  Push_0 → Static[129]                 // clear temp
  Call @Label_5                        // input handling + script loading + anti-freeze
  Call @Label_6                        // draw? 
  Push1 18 ; Push_0 ; PLAYER_ID ; NETWORK_SET_THIS_SCRIPT_IS_NETWORK_SCRIPT 3 0
  // ... check IS_WARNING_MESSAGE_ACTIVE || IS_PAUSE_MENU_ACTIVE → if in pause → Return
  Switch Static[130] with 60 cases     // STATE MACHINE: 0=Main,1=Language Select,2=Mains Mods...54=Misc etc.
```

**Key function:** `:Label_1835` (the loader, 6 params):
```asm
:Label_1835
Function 6 19 0
  getF1 1 ; CallNative "DOES_SCRIPT_EXIST" 1 1 ; JumpTrue @Label_423  // script file exists?
  // else: PushString ".csc Not Found!" + pFrame1 8 ; StrCopy ...
  :Label_423
  getF1 0 ; getF1 5 ; Call @Label_396  // draw menu entry? Label_396 = AddItem?
  getF1 3 ; getF1 4 ; Call @Label_427  // handle selection highlight?
  getF1 1 ; GET_HASH_KEY ; UNK_029D3841 ; Push_0 ; CmpNe ; Call @Label_418 ; // is script running? check via entity?
  Call @Label_397 ; JumpFalse @Label_426 // if already running + input pressed?
  getF1 1 ; GET_HASH_KEY ; UNK_029D3841 ; JumpFalse @Label_428
    getF1 1 ; TERMINATE_ALL_SCRIPTS_WITH_THIS_NAME 1 0 ; // kill old instance
  :Label_428
  getF1 1 → Static[134] ; getF1 2 → Static[136] ; // queue for START_NEW_SCRIPT
:Label_426 Return 6 0
```
Called as: `PushString "Brodator" ; PushString "Brodator" ; PushS 1024 ; StaticGet1 17 ; StaticGet1 7 ; Push_1 ; Call @Label_1835`
= `LoadMenu("Brodator", "Brodator", 1024, flag1, flag2, enabled)`

---

## 6. How Menu Rendering Works

ModLoader uses **native Draw Rect/Sprite/Text per frame**:

- `:Label_327` = `DRAW_RECT` wrapper: `StaticGet2 353,354 + math → DRAW_RECT(x,y,w,h,r,g,b,a)`
- `:Label_397`/`:Label_418` = input: `IS_DISABLED_CONTROL_PRESSED(177)` etc. → `PLAY_SOUND_FRONTEND("Click_Special")`
- Text: `BEGIN_TEXT_COMMAND_DISPLAY_TEXT("STRING")` → `ADD_TEXT_COMPONENT_SUBSTRING_PLAYER_NAME` → `END_TEXT_COMMAND_DISPLAY_TEXT(x,y)` + `SET_TEXT_COLOUR/SET_TEXT_SCALE`
- Textures: `REQUEST_STREAMED_TEXTURE_DICT("commonmenu")` → `HAS_STREAMED_TEXTURE_DICT_LOADED` → `DRAW_SPRITE("commonmenu","shop_box_tick",...)`

Safe-zone handling (`Label_2`):
```c
float Label_2() { return GET_SAFE_ZONE_SIZE(); } // 0.9 default
// Static[0..2] = base_pos + safezone * scale  → ensures menu stays inside safe area
```

---

## 7. Globals Hack (`pSet` flood)

Lines 544-599 show the **anti-freeze / anti-crash pSet block**:
```asm
Push 1317011488 ; Push 19705448 ; pSet  // global 19705448 = 1317011488 ?
Push 1317011488 ; Push 19716948 ; pSet  // 16 writes in a row
...
```
This is patching RAGE globals that control freeze protection (setting them to `0x4EA...`). `:Label_5` checks `Static_139 bit 9` → if true, flood globals every frame. Disable via menu `Proteccion De Modders`.

---

## 8. Building Your Own

To add a menu entry, insert before `Return 0 0` in `:Label_64` (Mods Menus, page 1):

```asm
PushString "My Cool Menu"
PushString "MyScript"      // file must exist as MyScript.csc in scripts folder
PushS 1024                // stack, 512-6304 recommended
StaticGet1 17             // category flags (see other examples)
StaticGet1 7
Push_1                    // enabled = true
Call @Label_1835
```

To change colors, edit `ModLoader_Statics.c`:

```c
Static_210 = 0;   // R
Static_211 = 100; // G
Static_212 = 255; // B  → electric blue
Static_258 = 0;   // scrollbar R etc.
```

Then reassemble with `AssemblyToolkit` or `GLADecompiler`'s `asm.exe`.

---

## 9. Decompiling Fully to C — Tools

| Tool | Input | Output | Note |
|------|-------|--------|------|
| **GTA V Script Decompiler (Tekken57)** | `*.ysc`/`*.csc` binary | `*.c` pseudo-C + `*.asm` | Best for understanding natives |
| **Zan's CSA Toolkit** | `*.csa` text | `*.csc` binary | What compiled ModLoader |
| `tools/csa_decompile.py` (provided in this repo) | `ModLoader.csa` | `ModLoader_pseudo.c` + `callgraph.dot` | Our Python helper (see `tools/`) |

Run:
```bash
python3 tools/csa_decompile.py --in ModLoader.csa --out docs/ModLoader_pseudo.c --graph docs/callgraph.dot
python3 tools/csa_decompile.py --explain Label_1835 Label_3 Label_5
```

---

## 10. Full Opcode Frequency (this file)

```
Push:7475  Call:3599  PushString:2372  Jump:1836  CallNative:1618 ...
```
See `docs/opcode_freq.txt` for full.

---

## 11. Call Graph Highlights

```
Label_0 (init) -> Label_1, Label_2
Label_4 (loop) -> Label_3 -> Label_5, Label_6, Switch[60 states]
Switch
 ├─0 -> Label_58 (splash?)
 ├─1 -> Label_60 (language) -> Label_455 etc.
 ├─2 -> Label_62 (Mains) -> Label_1835 * 22 menus
 ├─3 -> Label_64 (Recovery) etc.
 └─...
Label_1835 (loader) <- called 87× from Label_62..Label_69
Label_396 (AddItem) <- called 400+ times
Label_327 (DrawRect) <- per-frame draw
```

---

*Want the full decompiled pseudo-C (~3000 logical blocks) or an HTML searchable viewer? Run `tools/serve.py` and open the preview — it highlights bilingual strings, natives, and cross-references every Label.*
