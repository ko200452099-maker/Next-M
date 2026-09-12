#!/usr/bin/env python3
"""
apply_names.py — annotate or rename ModLoader.csa using rename_map.json

Usage:
  python3 tools/apply_names.py --annotated --in ModLoader.csa --out ModLoader_Annotated.csa
  python3 tools/apply_names.py --rename   --in ModLoader.csa --out ModLoader_Renamed.csa
  (rename will replace :Label_X definitions AND all Call/Jump @Label_X references)
"""
import json, re, pathlib, argparse

def load_map(mp):
    MAP = pathlib.Path(mp)
    if not MAP.exists():
        MAP = pathlib.Path('tools') / pathlib.Path(mp).name
    with open(MAP, encoding='utf-8') as f:
        data=json.load(f)
    return data['labels'], data['statics1'], data['statics2']

labels, s1, s2 = {}, {}, {}   # populated in main via load_map()

# Generated-comment patterns from previous runs (ModLoader.csa on disk carries
# stale ones, e.g. `; -> OldName`, `; >>> OldName`, `; gOldStatic`). Stripped
# before re-annotating so outputs never show two generations of names.
CLEAN_LABEL_ANNO = re.compile(r'\s{2,};\s*(>>>|->)\s*\S+\s*$')
CLEAN_STATIC_ANNO = re.compile(r'\s{2,};\s*g[A-Za-z]\w*\s*$')
def clean_anno(line):
    line = CLEAN_LABEL_ANNO.sub('', line)
    line = CLEAN_STATIC_ANNO.sub('', line)
    return line

# Build reverse for statics already
def annotate(inp, out):
    global labels, s1, s2
    txt=pathlib.Path(inp).read_bytes().decode('utf-8', errors='replace').replace('\r\n','\n').splitlines()
    out_lines=[]
    for line in txt:
        line = clean_anno(line)
        stripped=line.strip()
        # Label def
        if stripped.startswith(':'):
            lab=stripped[1:].strip()
            if lab in labels:
                out_lines.append(f"{line}  ; >>> {labels[lab]}")
            else:
                out_lines.append(line)
            continue
        # Static accesses (handles StaticSet1, StaticGet1, StaticSet2, etc., plus pStatic)
        m=re.search(r'(?:p)?Static(?:Get|Set)?([12])\s+(\d+)', line)
        if m:
            bank=m.group(1)
            sid=int(m.group(2))
            nm = s1.get(str(sid)) if bank=='1' else s2.get(str(sid))
            # json keys are strings, but s1/s2 from json have int keys? we stored as int via json dumps sort_keys? keys are strings
            # handle both
            if sid in s1: nm=s1[sid] if str(sid) not in s1 else s1[str(sid)]
            if bank=='1' and str(sid) in s1: nm=s1[str(sid)]
            if bank=='2' and str(sid) in s2: nm=s2[str(sid)]
            if nm and f"; {nm}" not in line:
                out_lines.append(f"{line}  ; {nm}")
                continue
        # Call/Jump references
        m=re.search(r'Call @(\w+)', line)
        if m:
            lab=m.group(1)
            if lab in labels:
                out_lines.append(f"{line}  ; -> {labels[lab]}")
                continue
        m=re.search(r'Jump\w*\s+@(\w+)', line)
        if m:
            lab=m.group(1)
            if lab in labels:
                # don't duplicate if already has comment
                if '; ->' not in line and '; >>>' not in line:
                    out_lines.append(f"{line}  ; -> {labels[lab]}")
                    continue
        m=re.search(r'Switch\s+\[', line)
        if m:
            # annotate Switch targets inline
            def repl_sw(m2):
                num=m2.group(1)
                lab=m2.group(2)
                nm=labels.get(lab, lab)
                return f"{num}=@{lab}/*{nm}*/"
            newline=re.sub(r'(\d+)=@(\w+)', repl_sw, line)
            out_lines.append(newline)
            continue
        out_lines.append(line)
    # write preserving CRLF
    pathlib.Path(out).write_text('\r\n'.join(out_lines), encoding='utf-8')
    print(f"Annotated {inp} -> {out} ({len(out_lines)} lines)")

def rename(inp, out):
    global labels, s1, s2
    txt=pathlib.Path(inp).read_bytes().decode('utf-8', errors='replace')
    # Use CRLF preservation
    has_crlf='\r\n' in txt
    txt_n=txt.replace('\r\n','\n')
    # Replace labels: longest first to avoid Partial
    for old, new in sorted(labels.items(), key=lambda x: len(x[0]), reverse=True):
        # Replace :Label_X definitions
        txt_n=txt_n.replace(f":{old}", f":{new}")
        # Replace @Label_X references
        txt_n=txt_n.replace(f"@{old}", f"@{new}")
        # Refresh inline /*Label_X*/ switch annotations
        txt_n=txt_n.replace(f"/*{old}*/", f"/*{new}*/")
    # Per-line: drop stale label-annotation comments (redundant after rename),
    # refresh static ones (statics stay numeric, so comments stay useful)
    out_lines=[]
    for line in txt_n.split('\n'):
        line = CLEAN_LABEL_ANNO.sub('', line)
        m = re.search(r'(?:p)?Static(?:Get|Set)?([12])\s+(\d+)', line)
        if m and re.search(r';\s*g\w+\s*$', line):
            nm = s1.get(m.group(2)) if m.group(1)=='1' else s2.get(m.group(2))
            if nm:
                line = re.sub(r';\s*g\w+\s*$', f'; {nm}', line)
        out_lines.append(line)
    txt_n='\n'.join(out_lines)
    if has_crlf:
        txt_n=txt_n.replace('\n','\r\n')
    pathlib.Path(out).write_text(txt_n, encoding='utf-8')
    print(f"Renamed {inp} -> {out}")

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--in', dest='inp', default='ModLoader.csa')
    ap.add_argument('--out', dest='out', default='ModLoader_Annotated.csa')
    ap.add_argument('--annotated', action='store_true')
    ap.add_argument('--rename', action='store_true')
    ap.add_argument('--map', dest='mapfile', default='tools/rename_map.json')
    args=ap.parse_args()
    labels, s1, s2 = load_map(args.mapfile)
    if args.rename:
        rename(args.inp, args.out)
    else:
        annotate(args.inp, args.out)
