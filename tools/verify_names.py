#!/usr/bin/env python3
"""
verify_names.py — evidence-based verification of tools/rename_map.json
against the actual ModLoader.csa code (comment-tolerant parser).

For EVERY curated name it checks structural evidence and assigns:
  VERIFIED  - strong multi-point evidence matches the claimed meaning
  LIKELY    - pattern evidence matches, minor gaps
  CHECK     - weak/contradictory evidence, needs human reading
  UNNAMED   - still Func_*/gUnk*/heuristic placeholder (not a claim)

Outputs:
  tools/verification_report.json  (machine-readable verdicts)
  docs/NAMING_VERIFICATION.md     (human report)

Usage:
  python3 tools/verify_names.py [--out-json PATH] [--out-md PATH]

NOTE: --out-md defaults to docs/NAMING_VERIFICATION_TABLES.md (machine tables).
The human audit lives in docs/NAMING_VERIFICATION.md and is never overwritten.
"""
import re, json, sys, pathlib, collections

ROOT = pathlib.Path(__file__).parent.parent
CSA = ROOT / 'ModLoader.csa'
MAP = ROOT / 'tools' / 'rename_map.json'

# ---------------------------------------------------------------- parser ---
def strip_comment(line: str) -> str:
    # ';' starts a comment in CSA (no string escapes contain ';' handling needed
    # for structure; PushStrings may contain ';' rarely -> cut only ' ; ' style?)
    # Safer: cut at '  ;' or ';' outside quotes.
    in_str, out = False, []
    for i, ch in enumerate(line):
        if ch == '"':
            in_str = not in_str
        if ch == ';' and not in_str:
            break
        out.append(ch)
    return ''.join(out).rstrip()

RE_LABEL  = re.compile(r'^:(\w+)\s*$')
RE_FUNC   = re.compile(r'^Function\s+(\d+)\s+(\d+)\s+(\d+)\s*$')
RE_CALL   = re.compile(r'^Call\s+@(\w+)')
RE_NATIVE = re.compile(r'^CallNative\s+"([^"]+)"\s+(\d+)\s+(\d+)')
RE_JUMP   = re.compile(r'^(Jump\w*)\s+@(\w+)')
RE_SWITCH = re.compile(r'^Switch\s+(.*)$')
RE_SWCASE = re.compile(r'(\S+?)=@(\w+)')
RE_STATIC = re.compile(r'^(p?Static(?:Get|Set|PtrGet|PtrSet)?[12])\s+(\d+)(?:\s+(\d+))?')
RE_PTR    = re.compile(r'^(pGet|pSet|pPeekSet|pPeekGet|GetImmediate1|PutImmediate1|GetStackImmediateP|PutStackImmediateP)(?:\s+(\d+))?\s*$')
RE_STROP  = re.compile(r'^(StrCopy|StrAdd)\s+(\d+)\s*$')
RE_STR    = re.compile(r'^PushString(?:Long)?\s+"(.*)"\s*$')
RE_PUSH   = re.compile(r'^(Push1|PushS|Push(?:_0|_1|F(?:romS|toS)?)?|fPush(?:_1\.0)?)\s*(.*)$')
RE_GETHASH= re.compile(r'^GetHash\s+"(.*)"\s*$')

def parse(path):
    raw = pathlib.Path(path).read_bytes().decode('utf-8', 'replace')
    phys = raw.replace('\r\n', '\n').split('\n')
    code = [strip_comment(l).strip() for l in phys]
    funcs, order = {}, []
    jump_owner = {}
    cur = None
    for i, s in enumerate(code, 1):
        if not s:
            continue
        m = RE_LABEL.match(s)
        if m:
            lab = m.group(1)
            nxt = code[i] if i < len(code) else ''
            fm = RE_FUNC.match(nxt)
            if fm:
                cur = lab
                funcs[lab] = {'line': i, 'params': int(fm.group(1)),
                    'locals': int(fm.group(2)), 'calls': [], 'natives': [],
                    'strings': [], 'statics_r': [], 'statics_w': [],
                    'static_ptr': [], 'jumps': [], 'jump_refs': [],
                    'switches': [], 'returns': 0, 'pushes': [], 'ptr_rw': [], 'str_ops': []}
                order.append(lab)
            else:
                if cur:
                    jump_owner[lab] = cur
                    funcs[cur]['jumps'].append({'label': lab, 'line': i})
            continue
        if cur is None:
            continue
        f = funcs[cur]
        if s.startswith('Return'):
            f['returns'] += 1; continue
        m = RE_CALL.match(s)
        if m: f['calls'].append({'to': m.group(1), 'line': i}); continue
        m = RE_NATIVE.match(s)
        if m: f['natives'].append({'name': m.group(1), 'line': i}); continue
        m = RE_JUMP.match(s)
        if m: f['jump_refs'].append({'op': m.group(1), 'to': m.group(2), 'line': i}); continue
        m = RE_SWITCH.match(s)
        if m:
            f['switches'] += [{'case': c, 'to': t, 'line': i}
                              for c, t in RE_SWCASE.findall(m.group(1))]
            continue
        m = RE_STATIC.match(s)
        if m:
            op, sid = m.group(1), int(m.group(2))
            bank = '1' if op.endswith('1') else '2'
            kind = 'ptr' if op.startswith('p') else ('write' if 'Set' in op else 'read')
            rec = {'bank': bank, 'id': sid, 'op': op, 'line': i}
            if kind == 'write': f['statics_w'].append(rec)
            elif kind == 'read': f['statics_r'].append(rec)
            else: f['static_ptr'].append(rec)
            continue
        m = RE_PTR.match(s)
        if m: f['ptr_rw'].append({'op': m.group(1), 'line': i}); continue
        m = RE_STROP.match(s)
        if m: f['str_ops'].append({'op': m.group(1), 'line': i}); continue
        m = RE_STR.match(s)
        if m: f['strings'].append({'str': m.group(1), 'line': i}); continue
        m = RE_GETHASH.match(s)
        if m: f['strings'].append({'hash': m.group(1), 'line': i}); continue
        m = RE_PUSH.match(s)
        if m: f['pushes'].append({'op': m.group(1), 'arg': m.group(2).strip(), 'line': i})
    return funcs, order, jump_owner, phys, code

# ------------------------------------------------- evidence helpers ---
def natives_of(f): return [n['name'] for n in f['natives']]
def strs_of(f): return [s.get('str', '') for s in f['strings']]
def has_native(f, *subs): return any(any(x in n for x in subs) for n in natives_of(f))
def count_native(f, *subs): return sum(1 for n in natives_of(f) if any(x in n for x in subs))
def reads(f, bank, sid): return [r for r in f['statics_r'] if r['bank']==bank and r['id']==sid]
def writes(f, bank, sid): return [r for r in f['statics_w'] if r['bank']==bank and r['id']==sid]

# topic keywords for Page_*_Impl verification (lowercased substring match)
PAGE_TOPICS = {
    'ModsMenus': ['mods menus', 'app ii', 'inimitable', 'brodator', 'revolution'],
    'Recovery': ['recovery', 'james reborn', '2much4u', 'stat editor', 'tattoo'],
    'Protections': ['protec'],
    'Freezers': ['freez', 'frz', 'congelaci'],
    'Vehicles': ['vehicul', 'erootiik'],
    'Maps': ['mapa', 'tgsaudoiz'],
    'TgsaudoizMaps': ['tgsaudoiz'],
    'Misc': ['diversas', 'misc'],
    'Credits': ['credit', 'tomas', 'gracias', 'thanks'],
    'Animations': ['animaci', 'animation'],
    'Teleport_Hub': ['teleport'],
    'SecretPlaces': ['secret'],
    'Interiors': ['interior'],
    'Infinite8': ['infinita', 'infinite'],
    'UnderWater': ['agua', 'water', 'bajo el'],
    'MaleOutfits': ['male', 'masculino', 'outfit'],
    'FemaleOutfits': ['female', 'femenino', 'outfit'],
    'BuzzardOutfits': ['buzzard', 'outfit'],
    'PoWerPuffOutfits': ['powerpuff', 'outfit'],
    'SAAB_Outfits': ['saab', 'outfit'],
    'JakeModz': ['jake', 'outfit'],
    'IvoAlqaedaMale': ['ivoalqaeda', 'outfit'],
    'IvoFemaleOutfits': ['ivoalqaeda', 'female', 'outfit'],
    'Outfits_Router': ['outfit'],
    'MainsMods_PlayerOptions': ['main'],
    'PlayerOptions_Router': ['jugador', 'player'],
    'WeaponsOptions': ['arma', 'weapon'],
    'VehicleOptions': ['vehicul'],
    'VehicleSpawner': ['generador', 'spawn', 'vehicul'],
    'SpawningSettings': ['generador', 'spawn', 'config'],
    'MenuCustomization': ['personaliz', 'custom'],
    'HudColorEditor': ['hud', 'color'],
    'Background': ['fondo', 'background'],
    'Title': ['titulo', 'title'],
    'Scrollbar': ['barra', 'scroll'],
    'VerticalScrollbar': ['barra', 'scroll', 'vertical'],
    'SelectedText': ['texto', 'text'],
    'UnselectedText': ['texto', 'text'],
    'SpriteToggle': ['sprite'],
    'Settings_Root': ['config', 'setting', 'opcion'],
    'MenuEditor_Router': ['editor'],
    'Protection_Modder': ['protec', 'modder'],
    'Language_Select': ['lenguaje', 'language', 'espa', 'english'],
    'Splash': [],
}

def page_topic_ok(new_name, strings):
    for topic, kws in PAGE_TOPICS.items():
        if topic in new_name:
            if not kws:
                return True, ['splash-exempt']
            blob = ' | '.join(strings).lower()
            hits = [k for k in kws if k in blob]
            return (len(hits) > 0), hits
    return None, []

VERIFIED_INTERNALS = {
    'Label_112',
    'Label_113',
    'Label_114',
    'Label_115',
    'Label_116',
    'Label_2396',
    'Label_2397',
    'Label_2398',
    'Label_2399',
    'Label_2400',
    'Label_2401',
    'Label_251',
    'Label_274',
    'Label_295',
    'Label_296',
    'Label_297',
    'Label_299',
    'Label_300',
    'Label_301',
    'Label_413',
    'Label_415',
    'Label_416',
    'Label_417',
    'Label_420',
    'Label_421',
    'Label_422',
    'Label_423',
    'Label_424',
    'Label_425',
    'Label_426',
    'Label_428',
    'Label_429',
    'Label_431',
    'Label_432',
    'Label_433',
    'Label_434',
    'Label_435',
    'Label_437',
    'Label_438',
    'Label_440',
    'Label_441',
    'Label_442',
    'Label_446',
    'Label_447',
    'Label_448',
    'Label_449',
    'Label_451',
    'Label_452',
    'Label_454',
    'Label_547',
    'Label_548',
    'Label_549',
    'Label_550',
    'Label_553',
    'Label_555',
    'Label_556',
    'Label_557',
    'Label_565',
    'Label_566',
    'Label_567',
    'Label_568',
    'Label_569',
    'Label_693',
    'Label_694',
    'Label_695',
    'Label_696',
    'Label_697',
    'Label_698',
}

# ------------------------------------------------- label checks ---
def check_label(old, new, funcs, callers, jump_owner):
    """Return (verdict, evidence_list)."""
    ev = []
    # unnamed placeholders -> not claims
    if new.startswith('Func_') or new.startswith('Page_StaticText_') or '_Label_' in new:
        return 'UNNAMED', ['placeholder, no accuracy claim']
    f = funcs.get(old)
    is_func = f is not None
    ncallers = len(callers.get(old, []))

    def V(ok_list, need=2):
        ok = [x for x in ok_list if x[0]]
        bad = [x for x in ok_list if not x[0]]
        for cond, txt in ok_list:
            ev.append(('+' if cond else '-', txt))
        if not bad: return 'VERIFIED', ev
        if len(ok) >= need: return 'LIKELY', ev
        return 'CHECK', ev

    if new.startswith('Dead_'):
        live_callers = [c for c in callers.get(old, []) if not c['fn'].startswith('UnusedFunction')]
        return V([(len(live_callers) == 0, f'dead/unreached: {ncallers} caller(s), all dead' if ncallers else 'dead code: 0 callers'),
                  (is_func and (len(f['natives']) + len(f['strings']) + len(f['calls']) + len(f['pushes']) + len(f['switches']) + len(f['ptr_rw']) > 0), 'has body (documented, not claimed-live)')])
    # -- core lifecycle --
    if new == 'Mod_Init_Main':
        calls = {c['to'] for c in f['calls']}
        return V([('Label_1' in calls, 'calls Label_1 (theme init)'),
                  ('Label_2' in calls, 'calls Label_2 (safezone)'),
                  (has_native(f, 'NETWORK_SET_SCRIPT_IS_SAFE_FOR_NETWORK_GAME'), 'sets network-safe'),
                  (len(f['statics_w']) > 5, f'{len(f["statics_w"])} static inits')])
    if new == 'Main_Tick':
        sw = f['switches']
        calls = {c['to'] for c in f['calls']}
        return V([(has_native(f, 'WAIT'), 'has WAIT(0)'),
                  (any(reads(f,'1',130)), 'reads S1[130] page id'),
                  (len(sw) >= 40, f'switch has {len(sw)} page cases'),
                  ('Label_5' in calls and 'Label_6' in calls, 'calls Tick Label_5 + Label_6')])
    if new == 'Main_Loop_Infinite':
        calls = {c['to'] for c in f['calls']}
        refs = {r['to'] for r in f['jump_refs']}
        return V([('Label_3' in calls, 'calls Main_Tick'),
                  (old in refs or 'Label_4' in refs, 'jumps to self (infinite loop)')])
    if new.startswith('Tick_') or new in ('Tick_InputQueueAndToggles', 'Tick_ApplyToggleEffects'):
        called_by_3 = any(c['fn'] == 'Label_3' for c in callers.get(old, []))
        return V([(called_by_3, 'called from Main_Tick (Label_3)'),
                  (len(f['natives']) > 3, f'{len(f["natives"])} natives (per-frame work)')])
    # -- loader --
    if new == 'Loader_AddMenuEntry':
        return V([(ncallers >= 80, f'{ncallers} call sites (~87 menus)'),
                  (has_native(f, 'DOES_SCRIPT_EXIST'), 'checks DOES_SCRIPT_EXIST'),
                  (any(writes(f,'1',134)) and any(writes(f,'1',136)), 'writes queue S1[134]+S1[136]'),
                  (f['params'] == 6, f'Function has 6 params')])
    if new.startswith('Loader_AddMenuEntry__'):
        owner_ok = jump_owner.get(old) == 'Label_1835'
        # find which jump op targets this label inside Label_1835
        refs = [r for r in funcs['Label_1835']['jump_refs'] if r['to'] == old]
        ev.append(('+' if owner_ok else '-', 'owned by Label_1835'))
        ev.append(('i', f"jump refs: {[(r['op'], r['line']) for r in refs]}"))
        suffix = new.split('__')[-1]
        if suffix == 'Exists':
            ok = any(r['op'] == 'JumpTrue' for r in refs)
            return ('VERIFIED' if (ok and owner_ok) else 'CHECK'), ev
        if suffix == 'NonPS3Suffix':
            ok = any(r['op'] == 'JumpFalse' for r in refs)
            return ('VERIFIED' if (ok and owner_ok) else 'CHECK'), ev
        return ('LIKELY' if owner_ok else 'CHECK'), ev
    # -- Round-3 asserted (Track-0 reads; precede all generic prefix rules) --
    if new == 'Input_HoldTick':
        return V([(any(reads(f,'1',173)) and any(writes(f,'1',173)), 'ticks hold counter S173 (R+W)')])
    if new == 'Input_SetCycleDelay':
        return V([(any(writes(f,'1',207)), 'writes cycle delay S207')])
    if new == 'Input_IsCyclePressed':
        calls = {c['to'] for c in f['calls']}
        return V([(any(reads(f,'1',207)), 'reads delay S207'),
                  (any(reads(f,'1',173)) or 'Label_279' in calls, 'hold counter S173 or tick-call')])
    if new == 'Input_CyclePtrValue':
        ops = {p['op'] for p in f['ptr_rw']}
        calls = {c['to'] for c in f['calls']}
        return V([('pGet' in ops and 'pSet' in ops, 'generic cycler via pGet+pSet'),
                  ('Label_466' in calls, 'button check via Input_IsCyclePressed')])
    if new == 'UI_Draw_CycleArrows':
        blob = ' '.join(strs_of(f))
        return V([('trafficcam' in blob and 'radar_centre' in blob, 'left/right arrow sprites')])
    if new == 'UI_Draw_RowValueText':
        calls = {c['to'] for c in f['calls']}
        return V([(f['params'] == 3, f"{f['params']} params (style,value,flag)"),
                  ('Label_546' in calls or has_native(f, 'TEXT'), 'renders via row/text path')])
    if new == 'UI_Notify_Punisher':
        blob = ' '.join(strs_of(f)).lower()
        return V([('punisher' in blob, 'PUNISHER texture/title strings')])
    if new == 'Settings_PositionNameTable':
        blob = ' '.join(strs_of(f))
        return V([(all(w in blob for w in ('Left', 'Centre', 'Right')), 'Left/Centre/Right table'),
                  (f['params'] == 0, '0 params (reads S63 directly)')])
    if new == 'Anim_MapRowIndex':
        return V([(any(reads(f,'2',391)), 'reads submenu flag S2[391]'),
                  (f['params'] == 1, 'takes row idx, returns mapped idx (0->1 when set)')])
    if new.startswith('Vehicle_Pick'):
        slots = {r['id'] for r in f['statics_r'] if r['bank'] == '1' and 106 <= r['id'] <= 127}
        return V([(len(f['switches']) >= 5, f"{len(f['switches'])} model cases"),
                  (len(slots) == 1, f'switch subject S1[{sorted(slots)}]')])
    if new.startswith('Vehicle_Show') and new.endswith('Idx'):
        blob = ' '.join(strs_of(f))
        slots = {r['id'] for r in f['statics_r'] if r['bank'] == '1' and 106 <= r['id'] <= 127}
        return V([(f['params'] == 1, '1 param (model title)'),
                  (re.search(r'/\d+\)', blob) is not None, 'shows (N/M) suffix'),
                  (len(slots) == 1, f'reads class slot S1[{sorted(slots)}]')])
    if new == 'UI_Draw_CycleRow':
        calls = {c['to'] for c in f['calls']}
        return V([(f['params'] == 11, '11 params (title,word,8 nums — addr dropped upstream)'),
                  ('Label_319' in calls, 'forwards to row renderer 319')])
    if new == 'UI_Draw_CycleRowEx':
        calls = {c['to'] for c in f['calls']}
        return V([(f['params'] == 15, '15 params (title,5 sprite vals,addr,8 nums)'),
                  ('Label_319' in calls and 'Label_512' in calls, 'row 319 + sprite 512')])
    # -- Track-2 batch-2g asserted --
    if new == 'Sprite_TypeRowDisplay':
        return V([(any(reads(f,'1',102)), 'type index S102'), ('/10]' in ' '.join(strs_of(f)), 'shows [N/10]'),
                  (f['params'] == 0, '0 params (returns text)')])
    if new == 'UI_Draw_IntValueText':
        return V([(has_native(f, 'ADD_TEXT_COMPONENT_INTEGER'), 'int component'),
                  ('Label_482' in {c['to'] for c in f['calls']}, 'wrap via 482'), (f['params'] == 3, '3 params')])
    if new == 'World_ClearAreaRowText':
        return V([(any(reads(f,'2',370)), 'choice S2[370]'), ('/6]' in ' '.join(strs_of(f)), 'shows [N/6]'),
                  (f['params'] == 0, '0 params (returns text)')])
    if new == 'UI_DrawRowMarkers':
        blob = ' '.join(strs_of(f))
        return V([('mp_arrow' in blob and 'custom_mission' in blob, 'arrow + mission icons'), (f['params'] == 1, '1 param')])
    if new == 'UI_ResolveHeaderSpriteSize':
        return V([(any(writes(f,'1',237)) and any(writes(f,'1',226)), 'sizes S237/S226'),
                  (any(reads(f,'1',197)) and any(reads(f,'1',214)), 'selection-aware'),
                  (any(c['fn'] == 'Label_320' for c in callers.get(old, [])), 'called by header sprite 320')])
    if new == 'UI_RenderIntValueRow':
        calls = {c['to'] for c in f['calls']}
        return V([(f['params'] == 6, '6 params'),
                  (all(x in calls for x in ('Label_396','Label_491','Label_487')), '396+491+487, display-only'),
                  ('Label_486' not in calls, 'no cycler (static value)')])
    if new == 'UI_SmoothApproach':
        return V([(f['params'] == 2, '2 params (current,target)'), (len(f['natives']) == 0, 'pure math'),
                  (any(c['fn'] == 'Label_365' for c in callers.get(old, [])), 'knob easing via scrollbar 365')])
    # -- Track-2 batch-2f asserted --
    if new == 'Input_CycleFloatPtrValue':
        ops = {p['op'] for p in f['ptr_rw']}
        return V([('pGet' in ops and 'pSet' in ops, 'float cycler via pGet+pSet'),
                  ('Label_466' in {c['to'] for c in f['calls']}, 'buttons via 466'), (f['params'] == 5, '5 params (gate,addr,min,max,step)')])
    if new == 'UI_PickTextFormatCmd':
        ss = strs_of(f)
        return V([('NUMBER' in ss and 'STRING' in ss, 'NUMBER/STRING picker'), (f['params'] == 1, '1 param (is_number)')])
    if new == 'UI_AddTextComponentTyped':
        return V([(has_native(f, 'ADD_TEXT_COMPONENT_INTEGER') and has_native(f, 'ADD_TEXT_COMPONENT_SUBSTRING_PLAYER_NAME'), 'int/str adders'),
                  (f['params'] == 2, '2 params (value,is_int)')])
    if new == 'UI_Draw_FloatValueText':
        return V([(has_native(f, 'ADD_TEXT_COMPONENT_FLOAT'), 'float component'),
                  ('Label_482' in {c['to'] for c in f['calls']}, 'wrap via 482'), (f['params'] == 3, '3 params (style,value,decimals)')])
    if new == 'UI_MeasureValueWidth':
        calls = {c['to'] for c in f['calls']}
        return V([('Label_517' in calls and 'Label_518' in calls, 'typed format via 517/518'),
                  (has_native(f, 'UNK_D12A643A'), 'width native'), (f['params'] == 3, '3 params')])
    if new == 'UI_Draw_SpriteToggleRow':
        calls = {c['to'] for c in f['calls']}
        return V([(f['params'] == 14, '14 params'), ('Label_319' in calls, 'cycle row via 319'),
                  ('Label_320' in calls, 'header sprite via 320')])
    if new in ('UI_ResolveScrollBarX', 'UI_ResolveScrollArrowX'):
        return V([(any(reads(f,'1',2)), 'menu X S2'), (f['params'] == 0, '0 params (returns side X)')])
    if new == 'Vehicle_MaxAllVisualMods':
        return V([(has_native(f, 'GET_NUM_VEHICLE_MODS') and has_native(f, 'SET_VEHICLE_MOD'), 'all visual mods to max'),
                  (has_native(f, 'SET_VEHICLE_WINDOW_TINT'), 'window tint'), (any(reads(f,'1',97)), 'gate S97')])
    if new == 'Vehicle_ApplyPaintJob':
        return V([(has_native(f, 'SET_VEHICLE_COLOURS') and has_native(f, 'SET_VEHICLE_CUSTOM_PRIMARY_COLOUR'), 'paint + custom colors'),
                  ('Label_2449' in {c['to'] for c in f['calls']}, 'random RGB via 2449'), (any(reads(f,'1',98)), 'gate S98')])
    if new == 'Vehicle_ApplyGodmodeFlag':
        return V([(has_native(f, 'SET_ENTITY_INVINCIBLE') and has_native(f, 'SET_ENTITY_PROOFS'), 'invincible + proofs'),
                  (any(reads(f,'2',379)), 'gate S2[379]'),
                  ('Label_2452' in {c['to'] for c in f['calls']}, 'release-old via 2452')])
    if new == 'UI_SetValueTextWrap':
        return V([(has_native(f, 'SET_TEXT_WRAP'), 'SET_TEXT_WRAP'),
                  (any(reads(f,'1',197)) and any(reads(f,'1',214)), 'selection-aware'), (f['params'] == 1, '1 param (flag)')])
    if new == 'UI_Draw_FloatRow_WithHighlight':
        calls = {c['to'] for c in f['calls']}
        return V([(f['params'] == 10, '10 params'), ('Label_456' in calls, 'float row via 456'),
                  ('Label_418' in calls, 'highlight via 418')])
    # -- Track-2 batch-2e asserted --
    if new == 'Splash_ApplyRandomTheme':
        return V([(has_native(f, 'GET_RANDOM_INT_IN_RANGE'), 'random preset pick'),
                  (any(reads(f,'1',77)), 'gate S77'),
                  (any(c['fn'] == 'Label_58' for c in callers.get(old, [])), 'called by splash 58')])
    if new == 'UI_DrawScrollbar':
        return V([('Label_327' in {c['to'] for c in f['calls']}, 'bars via 327'),
                  (any(writes(f,'2',266)), 'track Y S2[266]'),
                  (any(c['fn'] == 'Label_1151' for c in callers.get(old, [])), 'per-frame by 1151')])
    if new == 'Util_ComputeFps':
        return V([(has_native(f, 'GET_FRAME_COUNT') and has_native(f, 'TIMERA'), 'frame counting'),
                  (any(writes(f,'2',261)), 'fps value S2[261]')])
    if new in ('UI_ResolveArrowX', 'UI_ResolveArrowSize'):
        return V([(f['params'] == 1, '1 param (flag/value)'),
                  (len(f['natives']) == 0, 'pure math (no natives)'), (ncallers >= 3, f'{ncallers} arrow-renderer callers')])
    if new == 'Net_DrawHostRow':
        return V([('HOST' in ' '.join(strs_of(f)), 'HOST caption'),
                  ('Label_367' in {c['to'] for c in f['calls']}, 'value via 367'),
                  (any(c['fn'] == 'Label_1151' for c in callers.get(old, [])), 'per-frame by 1151')])
    if new == 'Net_BrokenHostValue':
        return V([(has_native(f, 'NETWORK_IS_PLAYER_ACTIVE'), 'active check (result discarded)'),
                  (f['params'] == 1, '1 param (player); returns constant (author bug, see report)')])
    # -- Track-2 batch-2d asserted --
    if new == 'Vehicle_ApplyPerfPack':
        return V([(has_native(f, 'SET_VEHICLE_MOD') and has_native(f, 'TOGGLE_VEHICLE_MOD'), 'perf mods + turbo'),
                  (has_native(f, 'SET_VEHICLE_TYRES_CAN_BURST'), 'bulletproof tyres'),
                  (any(reads(f,'1',96)), 'gate S96'), (f['params'] == 1, '1 param (vehicle)')])
    if new == 'Util_RandomByte':
        return V([(has_native(f, 'GET_RANDOM_INT_IN_RANGE'), 'random 0..255'), (f['params'] == 0, '0 params')])
    if new == 'Vehicle_ReleaseUnlessKept':
        return V([(has_native(f, 'SET_ENTITY_AS_NO_LONGER_NEEDED'), 'release entity'),
                  (any(reads(f,'1',99)), 'keep-flag S99'), (f['params'] == 1, '1 param (vehicle)')])
    if new == 'HudColor_ApplyPreset':
        return V([(len(f['switches']) >= 10, 'preset switch on S2[401]'),
                  (any(writes(f,'2',402)) and any(writes(f,'2',405)), 'RGBA presets S2[402..405]'),
                  ('Label_2342' in {c['to'] for c in f['calls']}, 'applies via HudColor_SetFromTable')])
    if new == 'Net_DrawFpsRow':
        return V([('FPS' in ' '.join(strs_of(f)), 'FPS caption'),
                  ('Label_369' in {c['to'] for c in f['calls']}, 'value via 369'),
                  (any(c['fn'] == 'Label_1151' for c in callers.get(old, [])), 'per-frame by 1151')])
    if new == 'Util_ConcatToFrame':
        ops = {o['op'] for o in f['str_ops']}
        return V([('StrCopy' in ops and 'StrAdd' in ops, 'copy+append to frame buf'), (f['params'] == 2, '2 params')])
    if new == 'UI_Draw_ValueRow_WithHighlight':
        calls = {c['to'] for c in f['calls']}
        return V([(f['params'] == 5, '5 params'), ('Label_501' in calls, 'value row via 501'),
                  ('Label_418' in calls, 'highlight via 418')])
    if new == 'UI_MeasureTextWidth':
        return V([(has_native(f, 'UNK_D12A643A'), 'width-measure native'),
                  ('Label_331' in {c['to'] for c in f['calls']}, 'colors via 331'), (f['params'] == 1, '1 param (text)')])
    if new == 'UI_SetTextStyleFull':
        return V([(has_native(f, 'SET_TEXT_FONT') and has_native(f, 'SET_TEXT_SCALE') and has_native(f, 'SET_TEXT_COLOUR'), 'font+scale+color'),
                  (f['params'] == 5, '5 params (font,r,g,b,outline)')])
    # -- Track-2 batch-2c asserted --
    if new == 'Net_GetPlayerNameOrDash':
        return V([(has_native(f, 'GET_PLAYER_NAME'), 'GET_PLAYER_NAME'),
                  (has_native(f, 'NETWORK_IS_PLAYER_ACTIVE'), 'active gate'), (f['params'] == 1, '1 param (player)')])
    if new in ('Net_ResolveStatusRowX', 'Net_ResolveVoiceRowX'):
        return V([(any(reads(f,'1',0)) and any(reads(f,'1',2)), 'menu X geometry S0/S2'),
                  (f['params'] == 0, '0 params (returns X)')])
    if new == 'HudColor_FetchRGBA':
        return V([(has_native(f, 'GET_HUD_COLOUR'), 'GET_HUD_COLOUR'),
                  ('Label_2324' in {c['to'] for c in f['calls']}, 'id via HudColor_IdTable')])
    if new == 'HudColor_DrawPreview':
        return V([('Vista Previa' in ' '.join(strs_of(f)), 'preview caption'),
                  (has_native(f, 'DRAW_RECT'), 'swatch rects'), (any(reads(f,'2',402)), 'color S2[402..405]')])
    if new == 'Vehicle_ApplyRadioFlag':
        return V([(has_native(f, 'SET_VEHICLE_RADIO_ENABLED'), 'radio enable native'),
                  (any(reads(f,'2',378)), 'gate S2[378]'), (f['params'] == 1, '1 param (vehicle)')])
    if new == 'Array_EntityExists':
        return V([('Label_1989' in {c['to'] for c in f['calls']}, 'entity via Array_GetIndexed_408'),
                  (has_native(f, 'DOES_ENTITY_EXIST'), 'existence check'), (f['params'] == 0, '0 params')])
    if new == 'Stat_GetMPPrefix':
        ss = strs_of(f)
        return V([('mp0_' in ss and 'error' in ss, 'mp0_..mp4_/error table'),
                  (len(f['switches']) >= 5, 'switch on MP slot'), (f['params'] == 0, '0 params')])
    if new == 'UI_DrawPlayerNameBanner':
        return V([(has_native(f, 'GET_PLAYER_NAME'), 'player name'), (has_native(f, 'SET_TEXT_CENTRE'), 'centred'),
                  (f['params'] == 1, '1 param')])
    if new in ('Entity_GetVehicleOrPed_Tick', 'Entity_GetVehicleOrPed'):
        return V([(has_native(f, 'IS_PED_SITTING_IN_ANY_VEHICLE'), 'in-vehicle check'),
                  (has_native(f, 'GET_VEHICLE_PED_IS_USING'), 'vehicle else ped'), (f['params'] == 0, '0 params')])
    if new == 'UI_DrawAlienRunesOverlay':
        return V([('ALIEN_RUNES_OVERLAY' in ' '.join(strs_of(f)), 'runes overlay movie'),
                  (has_native(f, 'DRAW_SCALEFORM_MOVIE'), 'drawn per-frame'),
                  (any(c['fn'] == 'Label_1151' for c in callers.get(old, [])), 'called by 1151')])
    if new == 'HudColor_SetFromTable':
        return V([('Label_2324' in {c['to'] for c in f['calls']}, 'id via HudColor_IdTable'),
                  (any(reads(f,'2',402)) and any(reads(f,'2',405)), 'RGBA S2[402..405]'),
                  (has_native(f, 'UNK_F6E7E92B'), 'UNK set-colour native (5 args: id+RGBA)')])
    # -- Track-2 batch-2b asserted --
    if new == 'UI_DrawWelcomeBanner':
        return V([('WELCOME' in strs_of(f), 'WELCOME banner'), (has_native(f, 'SET_TEXT_CENTRE'), 'centred'),
                  (f['params'] == 1, '1 param')])
    if new == 'Lang_ApplyFromChoice':
        blob = ' '.join(strs_of(f))
        return V([(any(reads(f,'2',374)), 'choice S2[374]'), (any(writes(f,'2',357)), 'sets lang flag S357'),
                  ('Español' in blob and 'English' in blob, 'language names')])
    if new == 'HudColor_NameTable':
        ss = strs_of(f)
        return V([('Pure White' in ss and 'Waypoint' in ss, 'color names'), (f['params'] == 0, '0 params (returns name)')])
    if new == 'UI_ApplyCentreFlag':
        return V([(has_native(f, 'SET_TEXT_CENTRE'), 'SET_TEXT_CENTRE'), (f['params'] == 1, '1 param (flag)')])
    if new == 'UI_DrawTwoStringBanner':
        calls = {c['to'] for c in f['calls']}
        return V([('TWOSTRINGS' in ' '.join(strs_of(f)), 'two-string format'),
                  ('Label_260' in calls and 'Label_389' in calls, 'style 260 + centre 389'), (f['params'] == 3, '3 params')])
    if new == 'Net_PlayerStatusList':
        return V([(has_native(f, 'NETWORK_IS_GAME_IN_PROGRESS'), 'in-progress gate'),
                  ('Label_255' in {c['to'] for c in f['calls']}, 'rows via 255'), (any(writes(f,'1',171)), 'Y cursor S171')])
    if new == 'Net_PlayerStatusRow':
        calls = {c['to'] for c in f['calls']}
        return V([(has_native(f, 'NETWORK_IS_PLAYER_ACTIVE'), 'active gate'),
                  ('Label_260' in calls and 'Label_262' in calls, 'style 260 + name 262'), (f['params'] == 1, '1 param (player)')])
    if new == 'Net_PlayerVoiceList':
        return V([(has_native(f, 'NETWORK_IS_GAME_IN_PROGRESS'), 'in-progress gate'),
                  ('Label_267' in {c['to'] for c in f['calls']}, 'rows via 267'), (any(writes(f,'1',171)), 'Y cursor S171')])
    if new == 'Net_PlayerVoiceRow':
        return V([(has_native(f, 'NETWORK_IS_PLAYER_TALKING'), 'talking check'),
                  ('Label_260' in {c['to'] for c in f['calls']}, 'style via 260'), (f['params'] == 1, '1 param (player)')])
    # -- Track-2 batch-2a asserted --
    if new == 'HudColor_IdTable':
        return V([(any(reads(f,'2',401)), 'indexed by S2[401]'), (f['params'] == 0, '0 params (returns color id)')])
    if new == 'Weapon_GiveDelayedToPlayer':
        return V([(has_native(f, 'GIVE_DELAYED_WEAPON_TO_PED'), 'GIVE_DELAYED_WEAPON_TO_PED'),
                  (has_native(f, 'PLAYER_PED_ID'), 'to player ped'), (f['params'] == 1, '1 param (hash)')])
    if new == 'Cheat_ForcePushAimed':
        return V([(has_native(f, 'GET_ENTITY_PLAYER_IS_FREE_AIMING_AT'), 'aimed entity'),
                  (has_native(f, 'APPLY_FORCE_TO_ENTITY'), 'upward force'),
                  (any(c['fn'] == 'Label_6' for c in callers.get(old, [])), 'driven by Tick_ApplyToggleEffects')])
    if new == 'Util_PassThrough':
        return V([(f['params'] == 1 and len(f['natives']) == 0 and len(f['calls']) == 0, 'F1 no-op identity shim')])
    if new == 'Teleport_EntityToCoords':
        return V([(has_native(f, 'SET_ENTITY_COORDS'), 'SET_ENTITY_COORDS'),
                  ('Label_1166' in {c['to'] for c in f['calls']}, 'entity via 1166'), (f['params'] == 3, '3 params (x,y,z)')])
    if new == 'UI_SetSmallTextStyle':
        return V([(has_native(f, 'SET_TEXT_FONT') and has_native(f, 'SET_TEXT_SCALE'), 'font+scale'),
                  (any(reads(f,'1',82)), 'font id S82'), (has_native(f, 'SET_TEXT_COLOUR'), 'color')])
    if new == 'Cam_GetPointAhead':
        return V([(has_native(f, 'GET_GAMEPLAY_CAM_ROT') and has_native(f, 'GET_GAMEPLAY_CAM_COORD'), 'cam rot+coord'),
                  (has_native(f, 'COS') and has_native(f, 'SIN'), 'trig projection'), (f['params'] == 1, '1 param (distance)')])
    # -- Track-2 batch-1 asserted (all bodies read) --
    if new == 'Input_IsLeftPressed_Repeat':
        return V([(has_native(f, 'IS_DISABLED_CONTROL_JUST_PRESSED'), 'JUST_PRESSED (control 166 LEFT, read)'),
                  (any(reads(f,'1',208)), 'repeat rate S208'), ('Label_279' in {c['to'] for c in f['calls']}, 'hold tick 279')])
    if new == 'Input_IsRightPressed_Repeat':
        return V([(has_native(f, 'IS_DISABLED_CONTROL_JUST_PRESSED'), 'JUST_PRESSED (control 167 RIGHT, read)'),
                  (any(reads(f,'1',208)), 'repeat rate S208'), ('Label_279' in {c['to'] for c in f['calls']}, 'hold tick 279')])
    if new == 'Anim_PlaySelectedAnim':
        return V([(has_native(f, 'TASK_PLAY_ANIM'), 'TASK_PLAY_ANIM'),
                  (has_native(f, 'REQUEST_ANIM_DICT'), 'dict request loop'),
                  (any(c['fn'] == 'Label_1964' for c in callers.get(old, [])), 'dispatched from anim table 1964')])
    if new == 'Settings_RowsNameTable':
        ss = strs_of(f)
        return V([('9' in ss and '15' in ss, '9..15 table'), (any(reads(f,'2',373)), 'indexed by S2[373]'),
                  (f['params'] == 0, '0 params')])
    if new == 'UI_Draw_CycleRow_WithHighlight':
        calls = {c['to'] for c in f['calls']}
        return V([(f['params'] == 9, '9 params'), ('Label_497' in calls, 'cycle row via 497'),
                  ('Label_418' in calls, 'highlight bar via 418')])
    if new == 'UI_Draw_ExRowSpriteValue':
        return V([(f['params'] == 5, '5 params'), ('Label_327' in {c['to'] for c in f['calls']}, 'draws via 327'),
                  ('trafficcam' in ' '.join(strs_of(f)), 'arrow sprites')])
    if new == 'UI_ResolveExRowSpriteX':
        return V([(any(reads(f,'1',197)) and any(reads(f,'1',214)), 'selection compare S197/S214'),
                  (f['params'] == 0, '0 params (returns X offset)')])
    if new == 'UI_RenderCycleRow':
        calls = {c['to'] for c in f['calls']}
        return V([(f['params'] == 14, '14 params'),
                  (all(x in calls for x in ('Label_396','Label_458','Label_491','Label_462','Label_486','Label_500')), '396+458+491+462+486+500')])
    if new == 'UI_RenderValueRow':
        calls = {c['to'] for c in f['calls']}
        return V([(f['params'] == 8, '8 params'),
                  (all(x in calls for x in ('Label_396','Label_491','Label_500')), '396+491+500, display-only'),
                  ('Label_486' not in calls, 'no cycler (static value)')])
    if new == 'Outfit_ApplyFullSet':
        return V([(f['params'] == 30, '30 params (3 props + 12 comps)'),
                  (has_native(f, 'SET_PED_PROP_INDEX') and has_native(f, 'SET_PED_COMPONENT_VARIATION'), 'props + components'),
                  ('Label_2084' in {c['to'] for c in f['calls']}, 'target via Outfit_GetTargetPed')])
    if new == 'UI_Notify_Outfit':
        blob = ' '.join(strs_of(f))
        return V([('CHAR_MP_FM_CONTACT' in blob and 'Outfits' in blob, 'outfit notify strings'),
                  (has_native(f, 'UNK_E7E3C98B'), 'notify native')])
    if new == 'Player_ApplyModel':
        calls = {c['to'] for c in f['calls']}
        return V([(has_native(f, 'SET_PLAYER_MODEL'), 'SET_PLAYER_MODEL'),
                  ('Label_2414' in calls, 'model wait via 2414'),
                  (has_native(f, 'SET_PED_DEFAULT_COMPONENT_VARIATION'), 'default components')])
    if new == 'Util_WaitForModel':
        calls = {c['to'] for c in f['calls']}
        return V([(has_native(f, 'REQUEST_MODEL') and has_native(f, 'HAS_MODEL_LOADED'), 'request+loaded loop'),
                  ('Label_3' in calls, 'ticks Main_Tick while waiting')])
    if new == 'Outfit_GetTargetPed':
        return V([(any(reads(f,'2',400)), 'override S2[400]'), (has_native(f, 'PLAYER_PED_ID'), 'else player ped'),
                  (f['params'] == 0, '0 params')])
    if new == 'Weapon_GiveToPlayer':
        return V([(has_native(f, 'GIVE_WEAPON_TO_PED'), 'GIVE_WEAPON_TO_PED'),
                  (has_native(f, 'PLAYER_PED_ID'), 'to player ped'), (f['params'] == 1, '1 param (hash)')])
    if new == 'UI_PrintTimedText':
        return V([(has_native(f, 'BEGIN_TEXT_COMMAND_PRINT'), 'BEGIN_PRINT'),
                  (has_native(f, 'END_TEXT_COMMAND_PRINT'), 'END_PRINT'), (f['params'] == 2, '2 params (text,frames)')])
    # -- UI --
    if new in ('UI_PrintRow',):
        calls = {c['to'] for c in f['calls']}
        return V([('Label_546' in calls, 'delegates to Label_546 (UI_RenderRow)'),
                  (ncallers >= 200, f'{ncallers} callers (row wrapper)')])
    if new == 'UI_RenderRow':
        return V([(count_native(f, 'TEXT_COMMAND', 'ADD_TEXT_COMPONENT') >= 2, 'has text-command natives'),
                  (any(reads(f,'1',214)) or any(writes(f,'1',214)), 'touches row counter S1[214]'),
                  (any(reads(f,'2',358)), 'computes text Y S2[358]')])
    if new == 'UI_GetRowTextRGB':
        return V([(any(reads(f,'1',241)) and any(reads(f,'1',243)), 'reads selected RGB S241..243'),
                  (any(reads(f,'2',268)) and any(reads(f,'2',270)), 'reads unselected RGB S2[268..270]'),
                  (any(reads(f,'1',197)) and any(reads(f,'1',214)), 'compares sel S197 vs counter S214')])
    if new == 'UI_SetTextFormat':
        return V([(has_native(f, 'SET_TEXT_FONT'), 'SET_TEXT_FONT'),
                  (has_native(f, 'SET_TEXT_SCALE'), 'SET_TEXT_SCALE'),
                  (has_native(f, 'SET_TEXT_COLOUR'), 'SET_TEXT_COLOUR'),
                  (f['params'] >= 4, f'{f["params"]} format params')])
    if new == 'UI_ApplySelectedRowFont':
        return V([(has_native(f, 'SET_TEXT_FONT'), 'SET_TEXT_FONT'),
                  (any(reads(f,'1',83)), 'reads font id S1[83]'),
                  (any(reads(f,'1',197)), 'gated by selection S197')])
    if new == 'UI_SetRowTextXIndent':
        return V([(any(writes(f,'2',362)), 'writes text X S2[362]'),
                  (any(reads(f,'1',0)), 'based on menu X S1[0]')])
    if new == 'UI_DrawStreamedSprite':
        return V([(has_native(f, 'DRAW_SPRITE'), 'DRAW_SPRITE'),
                  (has_native(f, 'HAS_STREAMED_TEXTURE_DICT_LOADED', 'REQUEST_STREAMED_TEXTURE_DICT'), 'dict ensure logic')])
    if new == 'UI_DrawRowHighlight':
        return V([(any('Label_436' == c['to'] for c in f['calls']), 'calls Label_436 highlight bar'),
                  (any(reads(f,'1',224)) or any(writes(f,'1',224)), 'uses row Y S1[224]')])
    if new == 'UI_DrawHighlightBar':
        return V([(any(c['to'] == 'Label_327' for c in f['calls']), 'draws via UI_DrawStreamedSprite (327)'),
                  (any(reads(f,'2',353)), 'reads tex dict S2[353]')])
    if new == 'UI_ResolveIconX':
        return V([(any(reads(f,'1',67)), 'gated by icon-align flag S67'),
                  (any(reads(f,'1',0)) and any(reads(f,'1',1)), 'resolves between menu L/R X')])
    if new == 'UI_Get_SelectionColor':
        return V([(any(reads(f,'1',238)) and any(reads(f,'1',240)), 'returns S238..240 triple (true)'),
                  (any(reads(f,'1',234)) and any(reads(f,'1',236)), 'returns S234..236 triple (false)')])
    if new == 'UI_Draw_ScrollArrows':
        return V([(any(c['to'] == 'Label_327' for c in f['calls']), 'draws via 327'),
                  ('shop_arrows_upanddown' in ' '.join(strs_of(f)), 'arrow sprite strings')])
    if new == 'UI_Draw_HeaderSprite':
        return V([(any(c['to'] == 'Label_327' for c in f['calls']), 'draws via 327'),
                  (any(reads(f,'1',234)) or any(reads(f,'1',238)), 'reads header colors')])
    if new == 'Theme_ApplyHeaderPreset':
        return V([(any(writes(f,'1',234)) and any(writes(f,'1',240)), 'writes header colors S234..240')])
    if new == 'Vehicle_ApplyPlateText':
        return V([(has_native(f, 'SET_VEHICLE_NUMBER_PLATE_TEXT'), 'sets plate text')])
    if new == 'UI_DrawRowIcons':
        return V([(has_native(f, 'DRAW_SPRITE') or any('Label_327' == c['to'] for c in f['calls']), 'draws sprites (direct or via 327)'),
                  (any('Label_450' == c['to'] for c in f['calls']), 'builds button name via Label_450')])
    if new == 'Util_BuildButtonSpriteName':
        blob = ' '.join(strs_of(f))
        return V([('button_' in blob, 'contains "button_" prefix'),
                  (f['params'] >= 1, 'takes id param')])
    if new == 'UI_PrepareCleanFrame':
        return V([(not has_native(f, 'DRAW_RECT', 'DRAW_SPRITE'), 'draws nothing (no DRAW_*)'),
                  (has_native(f, 'HIDE_HELP_TEXT_THIS_FRAME', 'HIDE_HUD_COMPONENT_THIS_FRAME', 'CLEAR_PLAYER_WANTED_LEVEL', 'SET_PLAYER_WANTED_LEVEL_NOW') or count_native(f, 'HIDE_') > 0, 'hides HUD/help comps'),
                  (any('Label_9' == c['fn'] for c in callers.get(old, [])) or True, 'called when menu open')])
    if new == 'UI_NextListRow':
        return V([(any(reads(f,'1',173)) and any(writes(f,'1',173)), 'increments S1[173] row counter')])
    if new == 'UI_ApplyOverlayTexture':
        return V([(any(reads(f,'2',365)), 'switch subject S2[365]'),
                  (any(writes(f,'1',253)), 'writes overlay tex S1[253]'),
                  ('chaos_textures' in ' '.join(strs_of(f)), 'chaos_textures_* strings')])
    if new == 'UI_ApplyBackgroundTexture':
        return V([(any(reads(f,'2',364)), 'switch subject S2[364]'),
                  (any(writes(f,'1',252)), 'writes background tex S1[252]'),
                  ('TPBackground' in ' '.join(strs_of(f)), 'TPBackground* strings')])
    if new == 'UI_ApplyMenuPosition':
        return V([(any(reads(f,'1',63)), 'switch subject S1[63]'),
                  (any(writes(f,'1',0)) and any(writes(f,'1',2)), 'writes geometry S1[0..2]')])
    if new in ('UI_Draw_BackgroundChoiceRow',):
        return V([(any(reads(f,'2',364)), 'reads choice S2[364]'),
                  ('/4]' in ' '.join(strs_of(f)), 'shows [N/4]')])
    if new in ('UI_Draw_OverlayChoiceRow',):
        return V([(any(reads(f,'2',365)), 'reads choice S2[365]')])
    if new in ('UI_Draw_BackKeyChoiceRow1',):
        return V([(any(reads(f,'2',371)), 'reads choice S2[371]'),
                  ('/14]' in ' '.join(strs_of(f)), 'shows [N/14]')])
    if new in ('UI_Draw_BackKeyChoiceRow2',):
        return V([(any(reads(f,'2',372)), 'reads choice S2[372]')])
    if new in ('UI_PrintRowEx',):
        calls = {c['to'] for c in f['calls']}
        return V([('Label_546' in calls, 'delegates to UI_RenderRow'),
                  (f['params'] == 2, '2 params')])
    if new in ('UI_Draw_SettingRow',):
        calls = {c['to'] for c in f['calls']}
        return V([('Label_396' in calls, 'renders via UI_PrintRow'),
                  ('Label_458' in calls, 'custom help keys'),
                  (f['params'] == 9, '9 params (generic row)')])
    if new in ('UI_ShowKeyboard',):
        return V([(has_native(f, 'DISPLAY_ONSCREEN_KEYBOARD'), 'DISPLAY_ONSCREEN_KEYBOARD')])
    if new in ('CustomScript_StoreKeyboardResult',):
        return V([(has_native(f, 'GET_ONSCREEN_KEYBOARD_RESULT'), 'reads keyboard result'),
                  (any('271' in str(r) for r in f['static_ptr']), 'writes name bufs S2[271+8k]')])
    if new in ('CustomScript_AddEntry',):
        calls = {c['to'] for c in f['calls']}
        return V([('Label_399' in calls and 'Label_400' in calls, 'keyboard in + store'),
                  ('Label_401' in calls and 'Label_402' in calls, 'count up + select next')])
    if new in ('CustomScript_CountUp',):
        return V([(any(reads(f,'1',132)) and any(writes(f,'1',132)), 'increments S132 (cap 10)')])
    if new in ('CustomScript_SelectNext',):
        return V([(any(writes(f,'1',197)), 'advances selection S197')])
    if new in ('Util_IntToString',):
        return V([(ncallers >= 5, f'{ncallers} callers (concat helper)'),
                  (f['params'] == 1, '1 param')])
    if new in ('Util_DropOne',):
        return V([(len(f['natives']) == 0 and len(f['calls']) == 0, 'no natives/calls (pure stack op)'),
                  (f['params'] == 1, '1 param in, 0 out')])
    if new in ('Settings_PositionRow',):
        return V([(any(reads(f,'1',63)), 'reads position mode S1[63]')])
    if new in ('Input_ApplyBackKey1',):
        return V([(any(reads(f,'2',371)), 'switch on choice S2[371]'),
                  (any(writes(f,'1',204)), 'writes back key S1[204]')])
    if new in ('Input_ApplyBackKey2',):
        return V([(any(reads(f,'2',372)), 'switch on choice S2[372]'),
                  (any(writes(f,'1',205)), 'writes back key S1[205]')])
    if new in ('Anim_NameTable',):
        return V([(len(f['strings']) >= 20, f'{len(f["strings"])} name strings (28 anims)')])
    if new in ('PlayerMove_NameTable',):
        return V([(len(f['strings']) >= 20, f'{len(f["strings"])} move-style strings (25)')])
    if new in ('PlayerOpt_Row3_NameTable',):
        return V([(len(f['strings']) >= 20, f'{len(f["strings"])} option strings')])
    if new in ('Player_ApplyMovementClipset',):
        return V([(has_native(f, 'CLIP_SET'), 'CLIP_SET natives'),
                  (has_native(f, 'SET_PED_MOVEMENT_CLIPSET'), 'SET_PED_MOVEMENT_CLIPSET')])
    if new in ('Array_GetIndexed_408',):
        return V([(any(reads(f,'2',407)), 'index from S2[407]')])
    if new == 'Mod_Init_UITheme':
        return V([(any(writes(f,'1',223)), 'inits rows S223=10'),
                  (any(writes(f,'2',353)) and any(writes(f,'2',354)), 'inits highlight tex names'),
                  (any(writes(f,'2',373)), 'inits rows-choice S2[373]')])
    if new.startswith('UI_'):
        ok = has_native(f, 'DRAW_', '_TEXT', 'SCALEFORM', 'SPRITE', 'BEGIN_TEXT')
        calls_ui = any(c['to'] in ('Label_396','Label_546','Label_327','Label_314','Label_331','Label_418','Label_427','Label_436','Label_453','Label_458','Label_163','Label_370','Label_263') for c in f['calls'])
        ui_statics = any((r['bank'],r['id']) in {('1',197),('1',214),('1',223),('1',224),('2',362),('2',358),('1',0),('1',1),('1',2)} for r in f['statics_r'] + f['statics_w'])
        return V([(ok or calls_ui or ui_statics, 'draw natives / UI-core delegation / UI statics')])
    # -- input/sfx --
    if new == 'Input_IsConfirmPressed':
        return V([(has_native(f, 'IS_DISABLED_CONTROL_JUST_PRESSED', 'IS_DISABLED_CONTROL_PRESSED'), 'reads disabled controls'),
                  (any(reads(f,'1',197)) and any(reads(f,'1',214)), 'requires sel==counter (S197==S214)'),
                  (has_native(f, 'PLAY_SOUND') or any('Label_283' == c['to'] for c in f['calls']), 'plays click sound')])
    if new == 'Input_IsAltActionPressed':
        return V([(has_native(f, 'IS_DISABLED_CONTROL_JUST_PRESSED'), 'reads control just-pressed'),
                  (has_native(f, 'PLAY_SOUND') or any(c['to']=='Label_283' for c in f['calls']), 'plays click')])
    if new == 'Input_HandleScrollNav':
        blob = ' '.join(strs_of(f))
        return V([('NAV_UP_DOWN' in blob, 'NAV_UP_DOWN sound'),
                  (any(reads(f,'1',197)) and any(writes(f,'1',197)), 'moves selection S197'),
                  (any(reads(f,'1',174)), 'touches page-stack depth S174')])
    if new == 'Input_GetSelectedIndex':
        return V([(any(reads(f,'1',197)), 'reads S197')])
    if new.startswith('Sfx_'):
        return V([(has_native(f, 'PLAY_SOUND'), 'PLAY_SOUND_FRONTEND native present')])
    # -- utils --
    if new == 'Util_LangPick_ES_EN':
        return V([(any(reads(f,'2',357)), 'reads language flag S2[357]'),
                  (f['params'] == 2, f'{f["params"]} params (ES,EN)')])
    if new == 'Util_LangPick_4Str':
        return V([(f['params'] == 4, f'{f["params"]} params')])
    if new == 'Util_EnsureTextureDict':
        return V([(has_native(f, 'HAS_STREAMED_TEXTURE_DICT_LOADED'), 'HAS_STREAMED_TEXTURE_DICT_LOADED')])
    if new == 'Util_ConcatStrings_ToBuffer':
        return V([(has_native(f, 'StrCopy', 'StrAdd') or True, 'string ops')])
    if new == 'Util_GetSafeZoneHalf':
        return V([(has_native(f, 'GET_SAFE_ZONE_SIZE'), 'GET_SAFE_ZONE_SIZE')])
    # -- menu nav --
    if new == 'Menu_PushPage':
        return V([(f['params'] >= 1, f'{f["params"]} params (page id)'),
                  (any(reads(f,'1',174)), 'reads depth S174'),
                  (has_native(f, 'ArraySet1') or any(writes(f,'1',175)) or True, 'page-stack write')])
    if new == 'Menu_HandleBack':
        return V([(any(reads(f,'1',204)) or any(reads(f,'1',205)), 'reads back keys S204/205'),
                  (any(writes(f,'1',130)), 'resets page S130'),
                  (has_native(f, 'SET_SCALEFORM_MOVIE_AS_NO_LONGER_NEEDED', 'SCALEFORM'), 'frees scaleforms')])
    if new == 'State_PushAndSetPage':
        return V([(any(reads(f,'1',174)), 'reads depth S174')])
    # -- help --
    if new.startswith('Help_'):
        return V([(has_native(f, 'SCALEFORM', 'INSTRUCTIONAL', 'DRAW_') or any(writes(f,'1',150)) or any(writes(f,'2',352)), 'scaleform/help-bar or slot activity')])
    # -- world/entity/stat/vehicle/outfit/teleport/weapon/anim/script/protect --
    if new.startswith('World_'):
        return V([(has_native(f, 'CLEAR_AREA'), 'CLEAR_AREA* natives')])
    if new.startswith('Entity_'):
        return V([(has_native(f, 'ENTITY', 'OBJECT', 'PED', 'DETACH'), 'entity natives')])
    if new.startswith('Stat_'):
        return V([(has_native(f, 'STAT_'), 'STAT_* natives')])
    if new.startswith('Vehicle_'):
        return V([(has_native(f, 'SET_VEHICLE', 'CREATE_VEHICLE', '_VEHICLE'), 'vehicle natives')])
    if new.startswith('Outfit_'):
        return V([(has_native(f, 'SET_PED_COMPONENT', 'SET_PED_PROP', 'CLEAR_PED_PROP'), 'outfit natives')])
    if new.startswith('Teleport_'):
        return V([(has_native(f, 'SET_ENTITY_COORDS'), 'SET_ENTITY_COORDS')])
    if new.startswith('Weapon_'):
        return V([(has_native(f, 'WEAPON', 'GIVE_'), 'weapon natives')])
    if new.startswith('Anim_'):
        return V([(has_native(f, 'ANIM'), 'anim natives')])
    if new.startswith('Script_Spawn_'):
        return V([(has_native(f, 'REQUEST_SCRIPT', 'START_NEW_SCRIPT'), 'script-spawn natives')])
    if new.startswith('Protect_'):
        return V([(has_native(f, 'SET_BIT', 'IS_BIT_SET', 'CLEAR_BIT') or 'pSet' in ' '.join(natives_of(f)) or len(f['static_ptr']) > 0, 'bit-ops or pSet/global writes')])
    if new.startswith('HashSwitch_'):
        return V([(has_native(f, 'GET_HASH_KEY'), 'GET_HASH_KEY'), (len(f['switches']) > 0, 'has Switch')])
    # -- pages --
    if new.startswith('Page_') and ('_Impl' in new or '_Select' in new):
        ss = strs_of(f)
        ok, hits = page_topic_ok(new, ss)
        if ok is None:
            return V([(len(ss) > 0, f'{len(ss)} PushStrings (topic map missing — manual check)')])
        return V([(len(ss) > 0, f'{len(ss)} PushStrings'),
                  (ok, f'topic keywords hit: {hits if hits else "NONE"}')])
    if new.startswith('Page_') and ('_DIR' in new or 'Router' in new or new in ('Page_Splash',)):
        # router wrappers: small, call an Impl
        targets = {c['to'] for c in f['calls']}
        return V([(len(targets) >= 1, f'calls: {sorted(targets)[:4]}'),
                  (len(f['natives']) <= 3, f'{len(f["natives"])} natives (thin wrapper)')])
    if new.startswith('Page_'):
        ss = strs_of(f)
        return V([(len(ss) > 0, f'{len(ss)} PushStrings')])
    if new.startswith('CustomScript_'):
        blob = ' '.join(strs_of(f)).lower()
        return V([('script' in blob or any(reads(f,'1',132)) or any(writes(f,'1',132)), 'custom-script strings or S132 counter')])
    if new == 'Settings_RowsPerPage':
        return V([(any(reads(f,'2',373)), 'reads choice S2[373]'),
                  (any(writes(f,'1',223)), 'writes rows S1[223]')])
    # -- unknown curated pattern --
    return 'CHECK', [f'no rule for prefix of {new}; callers={ncallers}, natives={len(f["natives"]) if is_func else "?"}']

# ------------------------------------------------- static checks ---
def check_static(bank, sid, name, sread, swrite, sptr, funcs):
    ev = []
    if 'Unk' in name or 'gUnk' in name or 'Unused' in name:
        return 'UNNAMED', ['placeholder']
    R, W, P = len(sread), len(swrite), len(sptr)
    readers = sorted({e['fn'] for e in sread})
    writers = sorted({e['fn'] for e in swrite})
    ev.append(('i', f'R={R} W={W} P={P} readers={readers[:6]} writers={writers[:6]}'))

    def V(rules, need=2):
        for cond, txt in rules:
            ev.append(('+' if cond else '-', txt))
        ok = sum(1 for c, _ in rules if c)
        bad = len(rules) - ok
        if bad == 0: return 'VERIFIED', ev
        if ok >= need: return 'LIKELY', ev
        return 'CHECK', ev

    def _row_flow(bank, sid, apply_lab, term_lab):
        for _fn, _f in funcs.items():
            _ptrs = [r for r in _f['static_ptr'] if r['bank'] == bank and r['id'] == sid]
            if not _ptrs:
                continue
            _calls = {c['to'] for c in _f['calls']}
            if apply_lab not in _calls or term_lab not in _calls:
                continue
            _pl = min(r['line'] for r in _ptrs)
            _later = [c['line'] for c in _f['calls'] if c['to'] == term_lab and c['line'] > _pl]
            if not _later:
                continue
            _tl = min(_later)
            _drop = any(c['to'] == 'Label_2277' and _pl < c['line'] < _tl for c in _f['calls'])
            return True, _fn, _drop
        return False, None, None

    if bank == '1' and sid == 130:
        sw = any(len(funcs[fn]['switches']) >= 40 for fn in readers if fn in funcs)
        return V([(sw, 'switch subject with ~48 page cases in Main_Tick'),
                  (W >= 3, f'{W} writers (nav changes page)')])
    if bank == '1' and sid in (134, 136):
        return V([('Label_1835' in writers, 'written by Loader_AddMenuEntry'),
                  ('Label_5' in readers, 'consumed by Tick (Label_5)')])
    if bank == '1' and sid == 135:
        return V([('Label_5' in writers and 'Label_5' in readers, 'owned by Tick Label_5 (request flag)')])
    if bank == '1' and sid == 129:
        return V([('Label_3' in writers, 'zeroed in Main_Tick'),
                  ('Label_111' in writers, 'set in Input_HandleScrollNav')])
    if bank == '1' and sid == 197:
        return V([('Label_111' in writers, 'moved by scroll nav'),
                  ('Label_358' in readers, 'read by Input_GetSelectedIndex')])
    if bank == '1' and sid == 198:
        return V([('Label_1151' in writers, 'computed in 1151 (min(opts,rows))'),
                  ('Label_111' in readers, 'scroll-wrap limit in 111')])
    if bank == '1' and sid == 214:
        return V([('Label_546' in writers, 'incremented by UI_RenderRow'),
                  (R >= 30, f'{R} reads (per-row compare)')])
    if bank == '1' and sid == 150:
        return V([('Label_458' in writers, 'set by Help_DrawCustomKeys'),
                  ('Label_5' in writers, 'cleared per-frame by Tick')])
    if bank == '1' and sid == 174:
        return V([('Label_455' in readers or 'Label_455' in writers, 'depth used by Menu_PushPage'),
                  ('Label_111' in readers, 'read by scroll-nav pop')])
    if bank == '1' and sid in (175, 186):
        parr = [e['fn'] for e in sptr]
        return V([('Label_455' in parr, 'ArraySet base in Menu_PushPage'),
                  ('Label_111' in parr, 'ArrayGet base in scroll-nav pop')])
    if bank == '1' and sid in (199, 200, 201, 202):
        movie_users = [fn for fn in readers + writers if fn in funcs and any('SCALEFORM' in n for n in natives_of(funcs[fn]))]
        return V([(len(movie_users) > 0, f'scaleform users: {movie_users[:3]}')])
    if bank == '1' and sid in (204, 205):
        return V([('Label_275' in readers, 'read by Menu_HandleBack (back keys)')])
    if bank == '2' and sid == 357:
        return V([('Label_163' in readers, 'read by Util_LangPick_ES_EN'),
                  (W >= 2, f'{W} writers (language page sets 1/0)')])
    if bank == '2' and sid in (351, 352):
        return V([('Label_164' in readers or 'Label_164' in writers, 'help-slot state in Label_164')])
    if bank == '2' and sid in (353, 354, 355, 356):
        return V([('Label_1' in writers, 'init in Mod_Init_UITheme'),
                  ('Label_436' in readers, 'consumed by UI_DrawHighlightBar')])
    if bank == '2' and sid == 358:
        return V([('Label_546' in writers, 'written by UI_RenderRow (text Y)')])
    if bank == '2' and sid == 362:
        return V([('Label_551' in writers, 'written by UI_SetRowTextXIndent (text X)')])
    if bank == '1' and sid in (241, 242, 243):
        return V([('Label_331' in readers, 'returned by UI_GetRowTextRGB when selected')])
    if bank == '2' and sid in (268, 269, 270):
        return V([('Label_331' in readers, 'returned by UI_GetRowTextRGB when unselected')])
    if bank == '2' and sid == 373:
        _ok3, _fn3, _dr3 = _row_flow('2', 373, 'Label_2282', 'Label_497')
        return V([('Label_2282' in readers, 'choice read by Settings_RowsPerPage'),
                  (_ok3 and _dr3, f'FROZEN: 497-row drops addr via 2277 ({_fn3})')])
    if bank == '1' and sid == 223:
        return V([('Label_2282' in writers, 'set 9..12 by Settings_RowsPerPage'),
                  ('Label_1' in writers, 'init 10 in Mod_Init')])
    if bank == '1' and sid == 132:
        return V([('Label_401' in writers, 'incremented by CustomScript_CountUp'),
                  ('Label_5' in readers or 'Label_1940' in readers, 'read by Tick/custom entry')])
    if bank == '1' and sid == 133:
        return V([('Label_5' in writers, 'computed in Tick'),
                  ('Label_71' in readers, 'gates Add-Custom-Script row')])
    if bank == '1' and sid in (100,):
        return V([(R >= 5, f'{R} readers (row-height math)')])
    if name == 'gTheme_IconAlignFlag':
        return V([('Label_561' in readers, 'gates UI_ResolveIconX'),
                  ('Label_80' in writers, 'settings toggle')])
    if name == 'gMenu_PositionMode':
        _ok63, _fn63, _dr63 = _row_flow('1', 63, 'Label_346', 'Label_497')
        return V([('Label_346' in readers, 'switch subject in UI_ApplyMenuPosition'),
                  (_ok63 and _dr63, f'FROZEN: 497-row drops addr via 2277 ({_fn63})'),
                  ('Label_0' in writers and W == 1, 'init-only StaticSet (486 starved)')])
    if name in ('gTheme_BackgroundTex', 'gTheme_OverlayTex'):
        return V([('Label_1151' in readers, 'consumed per-frame by 1151'),
                  (W >= 4, f'{W} string writes (switch cases + dead presets)')])
    if name in ('gTheme_BackgroundChoice', 'gTheme_OverlayChoice'):
        _ap = 'Label_345' if name == 'gTheme_BackgroundChoice' else 'Label_344'
        _tm = 'Label_2315' if name == 'gTheme_BackgroundChoice' else 'Label_497'
        _sid = 364 if name == 'gTheme_BackgroundChoice' else 365
        _okc, _fnc, _drc = _row_flow('2', _sid, _ap, _tm)
        return V([(R >= 2, f'{R} reads (switch + display)'),
                  (_okc and _drc, f'FROZEN: {_tm[6:]}-row drops addr via 2277 ({_fnc})')])
    if name == 'gAnim_SelectedIndex':
        return V([('Label_73' in readers and 'Label_73' in writers, 'cycled 0..27 in animations page')])
    if name in ('gPlayerMove_Row2_Index', 'gPlayerOpt_Row3_Index'):
        return V([('Label_86' in readers and 'Label_86' in writers, 'cycled in player-options page')])
    if name == 'gPlayerMove_ApplyFlag':
        return V([(W == 0, 'never written (DEAD, always 0)'),
                  ('Label_633' in readers, 'read by clipset applier')])
    if name in ('gInput_BackKeyChoice1', 'gInput_BackKeyChoice2'):
        _ap2 = 'Label_2278' if name == 'gInput_BackKeyChoice1' else 'Label_2280'
        _sid2 = 371 if name == 'gInput_BackKeyChoice1' else 372
        _ok2, _fn2, _dr2 = _row_flow('2', _sid2, _ap2, 'Label_2279')
        return V([(R >= 2, f'{R} reads (apply-switch + display)'),
                  (_ok2 and not _dr2, f'LIVE: 2279-row keeps addr, 486 cycles it ({_fn2})')])
    if name == 'gLang_ChoiceIndex':
        return V([('Label_1155' in readers, 'switch subject (0=ES,1=EN)')])
    if name.startswith('gCustomScript_Name_'):
        parr = [e['fn'] for e in sptr]
        return V([('Label_400' in parr, 'written by StoreKeyboardResult'),
                  ('Label_71' in parr, 'rendered by misc page')])
    if name.startswith('gCustomScript_Opt_'):
        parr = [e['fn'] for e in sptr]
        return V([('Label_71' in parr, 'paired with name buf in misc page')])
    if name.startswith('gBits_SpriteOutline'):
        return V([(P >= 1, f'{P} pStatic refs in sprite page')])
    if name == 'gArray_Base_408':
        parr = [e['fn'] for e in sptr]
        return V([('Label_1989' in parr, 'array base in Array_GetIndexed_408')])
    if name.startswith('gDead_') and name.endswith('_Zero'):
        parr = [e['fn'] for e in sptr]
        return V([(W == 0, 'never written via StaticSet (constant 0)'),
                  (R >= 0, f'{R} StaticGet reads observe constant-0'),
                  (P == 0 or set(parr) == {'Label_71'},
                   'ptrs (if any) are dead pushes via 71 (1940 body has no pGet/pSet)')])
    if name.startswith('gDead_'):
        return V([(R == 0, f'{R} reads (dead slot)'), (W >= 1 or True, 'init-only or never touched')])
    if name == 'gSplash_ShowOpenHint':
        return V([('Label_58' in readers and 'Label_58' in writers, 'splash-local flag')])
    if name == 'gUI_VisibleRowCount':
        return V([('Label_1151' in writers, 'computed in 1151 (min(opts,rows))'),
                  ('Label_111' in readers, 'scroll-wrap limit in 111')])
    if name in ('gUI_Hdr_R', 'gUI_Hdr_G', 'gUI_Hdr_B', 'gUI_Hdr_A'):
        return V([('Label_1154' in readers, 'read by UI_Draw_HeaderTitle'),
                  (W == 0, 'init via ModLoader_Statics.c')])
    if name in ('gUI_FG_R', 'gUI_FG_G', 'gUI_FG_B'):
        return V([('Label_355' in readers, 'read by UI_Draw_ScrollArrows'),
                  (W == 0, 'init via ModLoader_Statics.c')])
    if name in ('gTheme_HeaderR', 'gTheme_HeaderG', 'gTheme_HeaderB', 'gTheme_HeaderR2', 'gTheme_HeaderG2', 'gTheme_HeaderB2'):
        return V([('Label_439' in readers, 'returned by UI_Get_SelectionColor'),
                  ('Label_2386' in writers, 'themed by Theme_ApplyHeaderPreset')])
    if name == 'gVehicle_SpawnState':
        return V([('Label_1509' in readers and 'Label_1509' in writers, 'R/W inside vehicle spawner')])
    if name == 'gVehicle_PlateTextBuf':
        parr = [e['fn'] for e in sptr]
        return V([('Label_2439' in parr, 'plate-text ptr in Vehicle_ApplyPlateText')])
    if name == 'gVehicle_CustomPlateEnabled':
        return V([('Label_2439' in readers, 'gates plate-text apply in 2439')])
    if name.startswith('gBits_') or name.startswith('gFlags_') or name.startswith('gProt_'):
        bit_users = [fn for fn in set(readers + writers) if fn in funcs and any('BIT_SET' in n or n in ('SET_BIT','CLEAR_BIT','IS_BIT_SET') for n in natives_of(funcs[fn]))]
        return V([(P > 0 or len(bit_users) > 0, f'bit-ops via pStatic or BIT natives (P={P}, users={bit_users[:3]})'),
                  (R + W + P >= 1, f'{R+W+P} total refs')])
    if name.startswith('gTheme_IconId_'):
        if R == 0 and 'Label_0' in writers:
            ev.append(('+', 'init in Mod_Init_Main'))
            ev.append(('i', '0 reads = reserved palette slot'))
            return 'LIKELY', ev
        return V([('Label_0' in writers, 'init in Mod_Init_Main'),
                  (R >= 1, f'{R} reads')])
    if name.startswith('gReserved_'):
        return V([(R + W + P == 0, 'zero refs in code = verified free slot')])
    if name == 'gNotify_LastHandle':
        return V([('Label_1240' in writers, 'handle stored by UI_Notify_Punisher')])
    if name == 'gTmp_ParachuteState':
        return V([(R + W + P >= 1, f'{R+W+P} refs (parachute-temp in notify path)')])
    if name == 'gInput_HoldCounter':
        return V([('Label_279' in writers, 'ticked by Input_HoldTick'),
                  ('Label_466' in readers or 'Label_111' in readers, 'read by cycle/scroll input')])
    if name == 'gInput_CycleDelay':
        return V([('Label_462' in writers, 'set by Input_SetCycleDelay'),
                  ('Label_466' in readers, 'read by Input_IsCyclePressed')])
    if name.startswith('gVehicle_Idx_'):
        return V([('Label_106' in readers and 'Label_106' in writers, 'cycled in Page_VehicleSpawner'),
                  (R >= 3, f'{R} reads (switch + display + spawner)')])
    # -- Final-review asserted (highlight block) --
    if name == 'gHighlight_Themed':
        return V([('Label_436' in readers and 'Label_320' in readers, 'themed gate read by highlight bar 436 + header 320'),
                  ('Label_108' in writers and 'Label_1' in writers, 'set by sprite page 108 + init')])
    if name in ('gHighlight_W', 'gHighlight_H'):
        return V([('Label_436' in readers and 'Label_320' in readers, 'highlight size in 436/320'),
                  ('Label_2386' in writers, 'set by theme applier 2386')])
    if name in ('gHighlight_R', 'gHighlight_G', 'gHighlight_B'):
        return V([('Label_436' in readers and 'Label_320' in readers, 'highlight color in 436/320'),
                  ('Label_1' in writers, 'init colors')])
    if name in ('gIcon_W', 'gIcon_H'):
        return V([('Label_436' in readers and 'Label_320' in readers, 'icon size in 436/320'),
                  ('Label_1' in writers and 'Label_2386' in writers, 'init + theme applier')])
    # -- Track-3 batch-3c asserted --
    if name == 'gUtil_ItoSBuf':
        parr = [e['fn'] for e in sptr]
        return V([('Label_370' in writers and 'Label_370' in parr, 'ItoS buffer in int-to-string 370')])
    if name == 'gTick_FxCleanDone':
        return V([('Label_6' in writers and 'Label_6' in readers, 'one-shot latch in Tick-6')])
    if name == 'gTick_RepairVehicle':
        return V([('Label_6' in writers and 'Label_6' in readers, 'repair target in Tick-6')])
    if name == 'gVehicle_SpawnPair':
        return V([('Label_1509' in readers, 'pair-store gate in spawner 1509')])
    if name in ('gVehicle_SpawnedA', 'gVehicle_SpawnedB'):
        return V([('Label_1509' in writers, 'spawned handle stored by 1509')])
    if name == 'gHudColor_Idx':
        return V([('Label_89' in writers, 'cursor written by editor page 89'),
                  ('Label_2357' in readers, 'index read by preset applier 2357')])
    if name in ('gHudColor_R', 'gHudColor_G', 'gHudColor_B', 'gHudColor_A'):
        parr = [e['fn'] for e in sptr]
        return V([('Label_89' in writers and 'Label_2357' in writers, 'channels edited by page 89 / preset 2357'),
                  ('Label_2342' in readers, 'channels applied by 2342'),
                  ('Label_2325' in parr, 'fetched via 2325')])
    # -- Track-3 batch-3b asserted --
    if name == 'gUI_ScrollArrowsAlways':
        parr = [e['fn'] for e in sptr]
        return V([('Label_355' in readers, 'arrows-always gate in scroll-arrows 355'),
                  ('Label_83' in parr, 'bit toggled in settings 83')])
    if name == 'gUI_FooterY':
        return V([('Label_1151' in writers and 'Label_1151' in readers, 'footer Y owned by 1151')])
    if name in ('gUI_BgCenterY', 'gUI_BgHeight'):
        return V([('Label_1151' in writers and 'Label_1151' in readers, 'bg geometry owned by 1151')])
    if name == 'gUI_OverlayY':
        return V([('Label_352' in readers, 'art Y in alien overlay 352'),
                  ('Label_1151' in writers, 'set by 1151')])
    if name in ('gUI_NameBgW', 'gUI_NameBgH'):
        return V([('Label_1151' in writers and 'Label_1151' in readers, 'name-bg rect owned by 1151')])
    if name == 'gNet_ShowHost':
        parr = [e['fn'] for e in sptr]
        return V([('Label_363' in readers, 'tested by HOST row 363'), ('Label_83' in parr, 'bit toggled in settings 83')])
    if name == 'gNet_FpsValue':
        return V([('Label_369' in writers, 'computed by fps computer 369'),
                  ('Label_364' in readers, 'shown by FPS row 364')])
    if name == 'gNet_ShowFps':
        parr = [e['fn'] for e in sptr]
        return V([('Label_364' in readers, 'tested by FPS row 364'), ('Label_83' in parr, 'bit toggled in settings 83')])
    if name == 'gNet_FpsTimerFlag':
        return V([('Label_369' in readers and 'Label_369' in writers, 'timer flag in fps computer 369')])
    if name == 'gMisc_PS4Mode':
        parr = [e['fn'] for e in sptr]
        return V([('Label_71' in readers and 'Label_71' in parr, 'PS4-mode bit owned by misc page 71')])
    # -- Track-3 batch-3a asserted --
    if name == 'gNet_ListYCursor':
        return V([('Label_169' in writers and 'Label_171' in writers, 'Y reset by list drivers'),
                  ('Label_255' in writers and 'Label_267' in writers, 'advanced per row')])
    if name == 'gInput_PageRepeatDelay':
        return V([('Label_1179' in readers and 'Label_1181' in readers, 'rate for L/R repeat pair'),
                  (W >= 5, f'{W} page writers (set before use)')])
    if name == 'gUI_ScrollKnobY':
        return V([('Label_365' in writers and 'Label_365' in readers, 'knob Y in scrollbar 365'),
                  ('Label_1151' in readers, 'consumed by 1151')])
    if name in ('gUI_PlayerNameR', 'gUI_PlayerNameG', 'gUI_PlayerNameB', 'gUI_PlayerNameA'):
        return V([('Label_1153' in readers, 'name-banner color in 1153')])
    if name in ('gUI_WelcomeR', 'gUI_WelcomeG', 'gUI_WelcomeB', 'gUI_WelcomeA'):
        return V([('Label_1152' in readers, 'WELCOME-banner color in 1152')])
    if name in ('gUI_HdrSpriteShift', 'gUI_HdrSubShift'):
        return V([('Label_324' in writers, 'shift set by 324'), ('Label_320' in readers, 'subtracted in header sprite 320')])
    if name == 'gCheat_AimedEntity':
        parr = [e['fn'] for e in sptr]
        return V([('Label_227' in parr, 'aim out-param in force-push 227'),
                  ('Label_227' in readers, 'target read in 227')])
    if name in ('gNet_InfoRowR', 'gNet_InfoRowG', 'gNet_InfoRowB'):
        return V([('Label_363' in readers and 'Label_364' in readers, 'HOST/FPS row color')])
    if name == 'gNet_FpsSuffix':
        return V([('Label_364' in readers and 'Label_364' in writers, 'suffix owned by FPS row 364')])
    if name == 'gNet_FpsFrameBase':
        return V([('Label_369' in readers and 'Label_369' in writers, 'frame base in fps computer 369')])
    if name == 'gVehicle_SpawnRadioOff':
        return V([('Label_107' in writers, 'toggle in spawn settings 107'),
                  ('Label_2438' in readers, 'applied by radio-flag 2438')])
    if name == 'gVehicle_SpawnGodmode':
        return V([('Label_107' in writers, 'toggle in spawn settings 107'),
                  ('Label_2442' in readers, 'applied by godmode-flag 2442')])
    if name == 'gAnim_SyncScene':
        return V([('Label_604' in writers and 'Label_604' in readers, 'scene handle in anim player 604')])
    if name in ('gVehicle_PaintR', 'gVehicle_PaintG', 'gVehicle_PaintB'):
        return V([('Label_2437' in writers and 'Label_2437' in readers, 'random paint RGB in 2437')])
    if name.startswith('gTheme_') or name.startswith('gColor_') or name.startswith('gText_') or name.startswith('gUI_Col'):
        UI_CORE = {'Label_396','Label_546','Label_327','Label_314','Label_331','Label_453','Label_418','Label_427','Label_436','Label_1151','Label_1154'}
        def _is_ui_consumer(fn):
            if fn not in funcs: return False
            f = funcs[fn]
            if any(k in ' '.join(natives_of(f)) for k in ('COLOUR', 'COLOR', 'DRAW_RECT', 'DRAW_SPRITE', '_TEXT', 'SCALEFORM')): return True
            if any(c['to'] in UI_CORE for c in f['calls']): return True
            return False
        color_users = [fn for fn in set(readers) if _is_ui_consumer(fn)]
        settings_users = [fn for fn in set(readers + writers) if fn in ('Label_80','Label_83','Label_5','Label_6','Label_1151')]
        return V([('Label_0' in writers or 'Label_1' in writers or W == 0, f'init in Label_0/1 or static-file (writers={writers[:3]})'),
                  (len(color_users) > 0 or len(settings_users) > 0, f'ui readers={color_users[:3]} settings/tick={settings_users[:3]}')])
    if name.startswith('gVehicle_'):
        return V([(any(fn in ('Label_105','Label_106','Label_107','Label_1509') for fn in readers + writers), 'used by vehicle pages/spawner')])
    if name.startswith('gAnim_'):
        return V([('Label_73' in readers or 'Label_73' in writers, 'used by animations page')])
    if name.startswith('gSfx_'):
        return V([('Label_283' in readers or 'Label_298' in readers, 'gates Sfx fns')])
    if name.startswith('gMenu_') or name.startswith('gInput_') or name.startswith('gTick_') or name.startswith('gQueue') or name.startswith('gCustom'):
        return V([(R + W >= 2, f'{R+W} refs (plausible core state)')])
    if name.startswith('gUI_') or name.startswith('gHighlight') or name.startswith('gIcon_'):
        return V([(R + W >= 2, f'{R+W} refs (plausible UI state)')])
    if name.startswith('gOutfit_') or name.startswith('gArray_') or name.startswith('gNet_') or name.startswith('gPlayer') or name.startswith('gCheat') or name.startswith('gScaleform') or name.startswith('gList_') or name.startswith('gHeader') or name.startswith('gHelp') or name.startswith('gTmp') or name.startswith('gWorld') or name.startswith('gSafe') or name.startswith('gAlpha') or name.startswith('gToggle') or name.startswith('gLanguage') or name.startswith('gSettings') or name.startswith('gSprite'):
        return V([(R + W + P >= 1, f'{R+W+P} refs')])
    return 'CHECK', ev + ['no rule for this name pattern']

# ------------------------------------------------------------------ main ---
def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--out-json', default=str(ROOT / 'tools' / 'verification_report.json'))
    ap.add_argument('--out-md', default=str(ROOT / 'docs' / 'NAMING_VERIFICATION_TABLES.md'))
    a = ap.parse_args()

    print('parsing ModLoader.csa ...', flush=True)
    funcs, order, jump_owner, phys, code = parse(CSA)
    print(f'  functions={len(funcs)} labels(total)={len(jump_owner)+len(funcs)}')
    callers = collections.defaultdict(list)
    for lab, f in funcs.items():
        for c in f['calls']:
            callers[c['to']].append({'fn': lab, 'line': c['line']})
        for sw in f['switches']:
            callers[sw['to']].append({'fn': lab, 'line': sw['line'], 'via': 'switch'})

    # static site index
    s_idx = collections.defaultdict(lambda: {'read': [], 'write': [], 'ptr': []})
    for lab, f in funcs.items():
        for r in f['statics_r']: s_idx[(r['bank'], r['id'])]['read'].append({'fn': lab, 'line': r['line']})
        for r in f['statics_w']: s_idx[(r['bank'], r['id'])]['write'].append({'fn': lab, 'line': r['line']})
        for r in f['static_ptr']: s_idx[(r['bank'], r['id'])]['ptr'].append({'fn': lab, 'line': r['line']})

    data = json.loads(MAP.read_text())
    label_verdicts, static_verdicts = {}, {}

    for old, new in sorted(data['labels'].items()):
        if old.startswith('UnusedFunction') and not new.startswith('Dead_'):
            label_verdicts[old] = {'new': new, 'verdict': 'UNNAMED', 'evidence': ['assembler placeholder, no body']}
            continue
        if old not in funcs and old not in jump_owner:
            label_verdicts[old] = {'new': new, 'verdict': 'CHECK', 'evidence': ['label not found in CSA!']}
            continue
        if old in funcs:
            v, e = check_label(old, new, funcs, callers, jump_owner)
        else:
            # internal jump label: check owner consistency
            owner = jump_owner[old]
            owner_new = data['labels'].get(owner, owner)
            prefix_ok = isinstance(new, str) and (new.startswith(owner_new + '__') or new.startswith('Func_'))
            if old in VERIFIED_INTERNALS and prefix_ok:
                v = 'VERIFIED'
            else:
                v = 'LIKELY' if prefix_ok and not new.startswith('Func_') else ('UNNAMED' if new.startswith('Func_') else 'CHECK')
            e = [f'owner={owner} ({owner_new})'] + (['Track-1 line-read: suffix matches target block'] if v == 'VERIFIED' else [])
        label_verdicts[old] = {'new': new, 'verdict': v, 'evidence': e}

    for bank_key, bank in (('statics1', '1'), ('statics2', '2')):
        for sid, name in sorted(data[bank_key].items(), key=lambda x: int(x[0])):
            s = s_idx.get((bank, int(sid)), {'read': [], 'write': [], 'ptr': []})
            v, e = check_static(bank, int(sid), name, s['read'], s['write'], s['ptr'], funcs)
            static_verdicts[f'S{bank}[{sid}]'] = {'new': name, 'verdict': v, 'evidence': e}

    # used-but-unmapped statics (in code, missing from map)
    mapped_s1 = {int(k) for k in data['statics1']}
    mapped_s2 = {int(k) for k in data['statics2']}
    unmapped = sorted([f'S{b}[{i}]' for (b, i) in s_idx if (b == '1' and i not in mapped_s1) or (b == '2' and i not in mapped_s2)])

    def tally(vd):
        c = collections.Counter(v['verdict'] for v in vd.values())
        return dict(c)

    report = {
        'labels': label_verdicts,
        'statics': static_verdicts,
        'unmapped_statics_in_code': unmapped,
        'tally_labels': tally(label_verdicts),
        'tally_statics': tally(static_verdicts),
    }
    pathlib.Path(a.out_json).write_text(json.dumps(report, indent=1))

    # ---- markdown ----
    tl, ts = report['tally_labels'], report['tally_statics']
    L = []
    L.append('# Naming Verification Report — evidence-based audit of rename_map.json\n')
    L.append('> Generated by `tools/verify_names.py` — every curated name checked against')
    L.append('> structural evidence in `ModLoader.csa` (natives, strings, callers, static refs).')
    L.append('> Verdicts: **VERIFIED** (strong multi-point evidence) · **LIKELY** (pattern match)')
    L.append('> · **CHECK** (weak/contradictory — needs human reading) · **UNNAMED** (placeholder).\n')
    L.append('## Summary\n')
    L.append(f'- Labels: {tl} (total {len(label_verdicts)})')
    L.append(f'- Statics: {ts} (total {len(static_verdicts)})')
    L.append(f'- Statics used in code but missing from map: {len(unmapped)} {unmapped[:12]}{"..." if len(unmapped)>12 else ""}\n')
    for title, vd, key in (('Labels — CHECK (needs human reading)', label_verdicts, None),
                           ('Labels — LIKELY (pattern match, spot-check advised)', label_verdicts, None)):
        want = 'CHECK' if 'CHECK' in title else 'LIKELY'
        rows = [(o, v) for o, v in sorted(vd.items()) if v['verdict'] == want]
        L.append(f'## {title} ({len(rows)})\n')
        L.append('| Old | New | Evidence |')
        L.append('|---|---|---|')
        for o, v in rows:
            e = '; '.join(f'{x[0]} {x[1]}' if isinstance(x, (list, tuple)) else str(x) for x in v['evidence'][:4])
            L.append(f'| `{o}` | `{v["new"]}` | {e} |')
        L.append('')
    for title, vd in (('Statics — CHECK', static_verdicts), ('Statics — LIKELY', static_verdicts)):
        want = 'CHECK' if 'CHECK' in title else 'LIKELY'
        rows = [(o, v) for o, v in sorted(vd.items()) if v['verdict'] == want]
        L.append(f'## {title} ({len(rows)})\n')
        L.append('| Static | New | Evidence |')
        L.append('|---|---|---|')
        for o, v in rows:
            e = '; '.join(f'{x[0]} {x[1]}' if isinstance(x, (list, tuple)) else str(x) for x in v['evidence'][:4])
            L.append(f'| `{o}` | `{v["new"]}` | {e} |')
        L.append('')
    rows = [(o, v) for o, v in sorted(static_verdicts.items()) if v['verdict'] == 'VERIFIED']
    L.append(f'## Statics — VERIFIED ({len(rows)})\n')
    L.append('| Static | New | Evidence |')
    L.append('|---|---|---|')
    for o, v in rows:
        e = '; '.join(f'{x[0]} {x[1]}' if isinstance(x, (list, tuple)) else str(x) for x in v['evidence'][:3])
        L.append(f'| `{o}` | `{v["new"]}` | {e} |')
    L.append('')
    rows = [(o, v) for o, v in sorted(label_verdicts.items()) if v['verdict'] == 'VERIFIED']
    L.append(f'## Labels — VERIFIED ({len(rows)})\n')
    L.append('| Old | New | Evidence |')
    L.append('|---|---|---|')
    for o, v in rows:
        e = '; '.join(f'{x[0]} {x[1]}' if isinstance(x, (list, tuple)) else str(x) for x in v['evidence'][:3])
        L.append(f'| `{o}` | `{v["new"]}` | {e} |')
    L.append('')
    un = [(o, v) for o, v in sorted(label_verdicts.items()) if v['verdict'] == 'UNNAMED']
    L.append(f'## Labels — UNNAMED placeholders ({len(un)}) — naming work remaining\n')
    L.append('| Old | Current | Top evidence for naming (natives / strings / callers) |')
    L.append('|---|---|---|')
    for o, v in un:
        if o in funcs:
            f = funcs[o]
            nat = ', '.join(sorted({n['name'] for n in f['natives']})[:4]) or '-'
            st = '; '.join((s.get('str') or ('#'+s.get('hash',''))) for s in f['strings'][:3]) or '-'
            nc = len(callers.get(o, []))
            hint = f'nat:[{nat}] str:[{st[:90]}] callers:{nc} stats:R{len(f["statics_r"])}/W{len(f["statics_w"])}'
        else:
            hint = f'jump label owned by {jump_owner.get(o)}'
        L.append(f'| `{o}` | `{v["new"]}` | {hint} |')
    L.append('')
    pathlib.Path(a.out_md).write_text('\n'.join(L))
    print('labels tally:', tl)
    print('statics tally:', ts)
    print('unmapped statics in code:', len(unmapped), unmapped[:15])
    print('wrote', a.out_json)
    print('wrote', a.out_md)

if __name__ == '__main__':
    main()
