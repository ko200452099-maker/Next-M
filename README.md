# Modding — ModLoader (Tomás) Name Audit & Reference

**ModLoader by Tomás (TomasPintos22)** — a mod-menu *loader hub* for GTA V (PS3-era `*.csc`/`*.xsc` Script Assembly): it draws a bilingual (ES/EN) menu and loads 87 other mod menus/scripts on demand, plus built-in cheats (teleports, outfits, vehicle spawner, weapon toggles, protections).

This workspace contains the **fully audited naming + verification** of `ModLoader.csa` (29,938 lines, 272 functions, 2,466 labels, 352 statics):
every function label and every static has a verified English name, proven by ~120 evidence rules that re-check on every run.

## Final scoreboard

| Set | VERIFIED | LIKELY | UNNAMED | CHECK |
|---|---|---|---|---|
| Labels (341 curated) | 340 | 1 (UNK native) | 0 | 0 |
| Statics (352) | 340 | 12 (reserved slots, 0 reads) | 0 | 0 |
| Statics in code but missing from map | — | — | — | 0 |

## Start here

| # | File | What |
|---|---|---|
| 1 | `docs/NAMING_VERIFICATION.md` | **The complete report** — method, scoreboard, every fix (Rounds 2–3, Tracks 0–3, backlog), architecture discoveries, honest gaps |
| 2 | `docs/NAMING_VERIFICATION_TABLES.md` | Machine verdict tables (auto-generated, re-written by the verifier) |
| 3 | `docs/NAMING_GUIDE.md` | How to use the names (annotated vs renamed, workflow, principles) |
| 4 | `docs/BITSET_MAP.md` | Verified flag-bit tables (weapons page ↔ cheat tick, settings, boot) |
| 5 | `docs/REFERENCE_GLOSSARY.md` | A–Z glossary of all 693 curated names + evidence |
| 6 | `docs/WHOLE_MOD_OVERVIEW.md` | Architecture dossier (loader, pages, queue, cheats) |

## Layout

```
Modding/
├── README.md                    ← you are here
├── ModLoader.csa                ← PRISTINE source (never edit; all work references it)
├── ModLoader_Statics.c          ← pristine tunable globals (27 inits)
├── ModLoader_Renamed.csa        ← generated: fully renamed (curated names)
├── ModLoader_Renamed_Full.csa   ← generated: fully renamed (curated + __J_ internals)
├── docs/
│   ├── NAMING_VERIFICATION.md   ← the complete audit report (hand-written)
│   ├── NAMING_VERIFICATION_TABLES.md ← verdict tables (auto-generated)
│   ├── NAMING_MAP_LABELS.md / _STATICS.md (+ _FULL) ← name tables (auto-generated)
│   ├── REFERENCE_GLOSSARY.md    ← A–Z names + evidence (auto-generated)
│   ├── BITSET_MAP.md            ← verified bit tables (hand-written)
│   ├── NAMING_GUIDE.md          ← usage guide (hand-written)
│   ├── WHOLE_MOD_OVERVIEW.md    ← architecture dossier
│   ├── CSA_BYTECODE_GUIDE.md / DECOMPILED_WALKTHROUGH.md ← CSA primers
│   ├── ModLoader_Annotated.csa (+ _Full) ← numeric source + name comments (generated)
│   ├── ModLoader_Defines.h      ← #defines for all names (generated)
│   ├── ModLoader_Statics_Named.c← statics with // gName comments (generated)
│   ├── ModLoader_pseudo.c / callgraph.dot ← structural decompile (source-derived)
│   └── menu_list.txt / natives.txt / strings_sorted.txt ← extractions (source-derived)
└── tools/
    ├── rename_map.json          ← SOURCE OF TRUTH (curated names)
    ├── rename_map_full.json     ← full map (curated + positional internals)
    ├── verify_names.py          ← evidence-rule verifier (CHECK must stay 0)
    ├── verification_report.json ← per-name verdicts (auto-generated)
    ├── export_docs.py           ← regenerates all 7 derived docs from the JSONs
    ├── apply_names.py           ← annotated / renamed CSA generator
    └── csa_decompile.py         ← CSA → pseudo-C + call graph
```

Rule of thumb: **hand-written** = audit judgment (report, guide, bitset map); **auto-generated** = derived from the JSONs (re-run the tools, never hand-edit).

## Quick commands

```bash
python3 tools/verify_names.py     # re-prove every name (CHECK must stay 0)
python3 tools/export_docs.py      # refresh maps/glossary/defines/headers
python3 tools/apply_names.py --annotated --in ModLoader.csa --out docs/ModLoader_Annotated.csa
python3 tools/apply_names.py --rename    --in ModLoader.csa --out ModLoader_Renamed.csa --map tools/rename_map_full.json
```

## Safety & ethics note

This is a **GTA Online mod-menu loader**. Online grief/recovery/protections entries exist here **only as analyzed artifacts for education, offline/FiveM research, and single-player modding preservation**. Do not use in GTA Online (ban/corruption risk).

*Audit completed 2026-09-12 — ~200 functions and ~90 statics verified by direct line-reading; see `docs/NAMING_VERIFICATION.md` §5.*
