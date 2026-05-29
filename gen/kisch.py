"""Minimal KiCad 10 schematic generator.

Strategy for ERC-clean connectivity WITHOUT fragile wire geometry:
- Place each symbol at a known origin, rotation 0, no mirror.
- Compute each pin's absolute endpoint from the library pin (at x y angle).
- Connect nets by placing a LABEL (local / hierarchical) or a POWER symbol
  exactly at the pin endpoint. KiCad nets a label/power-pin that shares a
  coordinate with a component pin -> no wires needed, geometry is exact.

This module only needs correct pin-endpoint math, which we validate with
`kicad-cli sch erc` on a trivial circuit before scaling up.
"""
import re, uuid, os, itertools

SYMDIR = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols"

# ---------- tiny S-expression reader ----------
def tokenize(s):
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c in ' \t\r\n':
            i += 1
        elif c == '(':
            out.append('('); i += 1
        elif c == ')':
            out.append(')'); i += 1
        elif c == '"':
            j = i + 1; buf = []
            while j < n:
                if s[j] == '\\':
                    buf.append(s[j+1]); j += 2
                elif s[j] == '"':
                    break
                else:
                    buf.append(s[j]); j += 1
            out.append(('str', ''.join(buf))); i = j + 1
        else:
            j = i
            while j < n and s[j] not in ' \t\r\n()"':
                j += 1
            out.append(('atom', s[i:j])); i = j
    return out

def parse(tokens):
    # returns nested lists; atoms as ('atom',v) or ('str',v)
    pos = 0
    def rd():
        nonlocal pos
        t = tokens[pos]; pos += 1
        if t == '(':
            lst = []
            while tokens[pos] != ')':
                lst.append(rd())
            pos += 1
            return lst
        return t
    nodes = []
    while pos < len(tokens):
        nodes.append(rd())
    return nodes

CUSTOM_LIBS = {}  # libname -> absolute path of a .kicad_sym

def load_lib(libname):
    if libname in CUSTOM_LIBS:
        path = CUSTOM_LIBS[libname]
    else:
        path = os.path.join(SYMDIR, libname + ".kicad_sym")
    with open(path) as f:
        return f.read()

# ---------- raw symbol-block text extraction (balanced parens) ----------
def extract_symbol_block(text, name):
    """Return the raw text of (symbol "name" ...) top-level block."""
    needle = '(symbol "%s"' % name
    start = text.find(needle)
    if start < 0:
        raise KeyError("symbol %r not found" % name)
    depth = 0; i = start
    while i < len(text):
        if text[i] == '(':
            depth += 1
        elif text[i] == ')':
            depth -= 1
            if depth == 0:
                return text[start:i+1]
        i += 1
    raise ValueError("unbalanced")

def pins_of(text, name):
    """Parse pins of a library symbol: list of dict(number,name,x,y,angle).
    Pins live inside child units (symbol "name_u_v" ...)."""
    block = extract_symbol_block(text, name)
    nodes = parse(tokenize(block))[0]  # the (symbol ...) list
    pins = []
    def walk(node):
        if not isinstance(node, list):
            return
        if node and node[0] == ('atom', 'pin'):
            x=y=ang=None; num=nm=None
            for c in node:
                if isinstance(c, list) and c and c[0]==('atom','at'):
                    x=float(c[1][1]); y=float(c[2][1]); ang=float(c[3][1])
                if isinstance(c, list) and c and c[0]==('atom','number'):
                    num=c[1][1]
                if isinstance(c, list) and c and c[0]==('atom','name'):
                    nm=c[1][1]
            pins.append(dict(number=num,name=nm,x=x,y=y,angle=ang))
        for c in node:
            walk(c)
    walk(nodes)
    return pins

def _uuid():
    return str(uuid.uuid4())

GRID=1.27
def snap(v):
    return round(round(v/GRID)*GRID, 2)
def snapxy(p):
    return (snap(p[0]), snap(p[1]))

FPDIR="/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"

_pwr_ctr=itertools.count(1)
def _pwr_ref():
    return "#PWR%03d"%next(_pwr_ctr)

class Comp:
    def __init__(self, lib_id, ref, value, at, pinmap, mirror=None):
        self.lib_id=lib_id; self.ref=ref; self.value=value
        self.x, self.y = snap(at[0]), snap(at[1]); self.pinmap=pinmap  # number -> (px,py)
        self.uuid=_uuid(); self.fields={}; self.mirror=mirror
        self.unit=1
    def pin(self, number):
        px, py = self.pinmap[str(number)]
        # rotation 0; lib +Y up -> sch +Y down
        return (round(self.x+px,4), round(self.y-py,4))

class Sheet:
    """A child schematic file."""
    def __init__(self, proj, name, filename, title):
        self.proj=proj; self.name=name; self.filename=filename; self.title=title
        self.file_uuid=_uuid()      # the (uuid) of this file
        self.inst_uuid=_uuid()      # uuid of the (sheet) object placed on root
        self.page="?"
        self.comps=[]; self.labels=[]; self.powers=[]; self.wires=[]
        self.glabels=[]; self.ncs=[]; self.texts=[]
        self._refs={}
    # ---- placement ----
    def place(self, lib, name, ref, value, at, footprint=None, fields=None, mirror=None):
        libtext = self.proj.lib(lib)
        pins = pins_of(libtext, name)
        pinmap = {p['number']:(p['x'],p['y']) for p in pins}
        c = Comp("%s:%s"%(lib,name), ref, value, at, pinmap, mirror)
        if footprint: c.fields['Footprint']=footprint
        if fields: c.fields.update(fields)
        self.proj.use_symbol(lib, name)
        self.comps.append(c); return c
    def power(self, sym, at):  # sym in power lib: GND,+3V3,+5V,PWR_FLAG,VBUS...
        self.proj.use_symbol('power', sym)
        pins = pins_of(self.proj.lib('power'), sym)
        pinmap={p['number']:(p['x'],p['y']) for p in pins}
        c=Comp("power:%s"%sym, _pwr_ref(), sym, at, pinmap)
        c.is_power=True
        self.powers.append(c); return c
    def label(self, text, at, angle=0):
        self.labels.append((text, snap(at[0]), snap(at[1]), angle))
    def glabel(self, text, at, angle=0, shape="bidirectional"):
        self.glabels.append((text, snap(at[0]), snap(at[1]), angle, shape))
    def wire(self, p1, p2):
        self.wires.append((snapxy(p1),snapxy(p2)))
    def nc(self, at):
        self.ncs.append(snapxy(at))
    def text(self, s, at, size=1.5):
        self.texts.append((s, at[0], at[1], size))

class Project:
    def __init__(self, name, outdir):
        self.name=name; self.outdir=outdir
        self.root_uuid=_uuid()
        self.sheets=[]
        self._libcache={}
        self._used={}  # lib -> set(names) for lib_symbols emission
        self.root_powers=[]; self.root_texts=[]
    def lib(self, libname):
        if libname not in self._libcache:
            self._libcache[libname]=load_lib(libname)
        return self._libcache[libname]
    def use_symbol(self, lib, name):
        self._used.setdefault(lib,set()).add(name)
    def add_sheet(self, name, filename, title):
        s=Sheet(self, name, filename, title); self.sheets.append(s)
        s.page=str(len(self.sheets)+1)  # root is page 1
        return s
    # ---- emit helpers ----
    def _lib_symbols_block(self):
        out=["\t(lib_symbols"]
        for lib in sorted(self._used):
            t=self.lib(lib)
            for name in sorted(self._used[lib]):
                block=extract_symbol_block(t, name)
                # rename top symbol id to lib:name
                block=block.replace('(symbol "%s"'%name, '(symbol "%s:%s"'%(lib,name),1)
                # indent
                block="\n".join("\t\t"+ln if ln.strip() else ln for ln in block.split("\n"))
                out.append(block)
        out.append("\t)")
        return "\n".join(out)
    def _prop(self, name, val, x, y, hide=False, angle=0):
        h="\n\t\t\t\t(hide yes)" if hide else ""
        v=val.replace('\\','\\\\').replace('"','\\"')
        return ('\t\t(property "%s" "%s"\n\t\t\t(at %s %s %s)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)%s\n\t\t\t)\n\t\t)'
                %(name,v,x,y,angle,h))
    def _comp_block(self, c, sheet, path):
        lines=["\t(symbol",'\t\t(lib_id "%s")'%c.lib_id, "\t\t(at %s %s 0)"%(c.x,c.y)]
        if c.mirror: lines.append("\t\t(mirror %s)"%c.mirror)
        lines+=["\t\t(unit 1)","\t\t(exclude_from_sim no)","\t\t(in_bom yes)","\t\t(on_board yes)","\t\t(dnp no)",
                '\t\t(uuid "%s")'%c.uuid]
        # properties
        refy=c.y-2.54; valy=c.y+2.54
        is_pwr=getattr(c,'is_power',False)
        lines.append(self._prop("Reference", c.ref, c.x, refy, hide=is_pwr))
        lines.append(self._prop("Value", c.value, c.x, valy, hide=False))
        lines.append(self._prop("Footprint", c.fields.get('Footprint',''), c.x, c.y, hide=True))
        lines.append(self._prop("Datasheet", c.fields.get('Datasheet','~'), c.x, c.y, hide=True))
        for k,v in c.fields.items():
            if k in ('Footprint','Datasheet'): continue
            lines.append(self._prop(k, v, c.x, c.y, hide=True))
        # pins
        for num in sorted(c.pinmap):
            lines.append('\t\t(pin "%s"\n\t\t\t(uuid "%s")\n\t\t)'%(num,_uuid()))
        # instances
        ref=c.ref
        lines.append('\t\t(instances\n\t\t\t(project "%s"\n\t\t\t\t(path "%s"\n\t\t\t\t\t(reference "%s")\n\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)'%(self.name,path,ref))
        lines.append("\t)")
        return "\n".join(lines)
    def _label_block(self, text,x,y,angle, kind="label", shape=None):
        j="left" if angle in (0,90) else "right"
        sh="\n\t\t(shape %s)"%shape if shape else ""
        return ('\t(%s "%s"\n\t\t(at %s %s %s)%s\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify %s bottom)\n\t\t)\n\t\t(uuid "%s")\n\t)'
                %(kind,text,x,y,angle,sh,j,_uuid()))
    def _wire_block(self,p1,p2):
        return ('\t(wire\n\t\t(pts\n\t\t\t(xy %s %s) (xy %s %s)\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n\t\t(uuid "%s")\n\t)'%(p1[0],p1[1],p2[0],p2[1],_uuid()))
    def _nc_block(self,at):
        return '\t(no_connect\n\t\t(at %s %s)\n\t\t(uuid "%s")\n\t)'%(at[0],at[1],_uuid())
    def _text_block(self,s,x,y,size):
        s=s.replace('"','\\"')
        return '\t(text "%s"\n\t\t(exclude_from_sim no)\n\t\t(at %s %s 0)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size %s %s)\n\t\t\t)\n\t\t\t(justify left bottom)\n\t\t)\n\t\t(uuid "%s")\n\t)'%(s,x,y,size,size,_uuid())
    def write_sheet(self, s):
        path="/%s/%s"%(self.root_uuid, s.inst_uuid)
        body=["(kicad_sch",'\t(version 20250114)','\t(generator "kisch")','\t(generator_version "10.0")',
              '\t(uuid "%s")'%s.file_uuid,'\t(paper "A3")',
              '\t(title_block\n\t\t(title "%s")\n\t\t(rev "0.1")\n\t)'%s.title,
              self._lib_symbols_block()]
        for t in s.texts: body.append(self._text_block(*t))
        for (text,x,y,a) in s.labels: body.append(self._label_block(text,x,y,a,"label"))
        for (text,x,y,a,shape) in s.glabels: body.append(self._label_block(text,x,y,a,"global_label",shape))
        for w in s.wires: body.append(self._wire_block(*w))
        for nc in s.ncs: body.append(self._nc_block(nc))
        for c in s.comps: body.append(self._comp_block(c,s,path))
        for c in s.powers: body.append(self._comp_block(c,s,path))
        body.append('\t(sheet_instances\n\t\t(path "/"\n\t\t\t(page "%s")\n\t\t)\n\t)'%s.page)
        body.append(")")
        open(os.path.join(self.outdir,s.filename),"w").write("\n".join(body)+"\n")
    def _sheet_obj(self, s):
        # a (sheet ...) placed on root referencing the child file
        x,y = s.root_pos
        return ('\t(sheet\n\t\t(at %s %s)\n\t\t(size 40 20)\n\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(dnp no)\n'
                '\t\t(uuid "%s")\n'
                '\t\t(property "Sheetname" "%s"\n\t\t\t(at %s %s 0)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(justify left bottom)\n\t\t\t)\n\t\t)\n'
                '\t\t(property "Sheetfile" "%s"\n\t\t\t(at %s %s 0)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(justify left top)\n\t\t\t)\n\t\t)\n'
                '\t\t(instances\n\t\t\t(project "%s"\n\t\t\t\t(path "/%s"\n\t\t\t\t\t(page "%s")\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)'
                %(x,y,s.inst_uuid,s.name,x,y-1,s.filename,x,y+21,self.name,self.root_uuid,s.page))
    def write_root(self, title, comment_lines):
        comments="".join('\t\t(comment %d "%s")\n'%(i+1,c) for i,c in enumerate(comment_lines))
        body=["(kicad_sch",'\t(version 20250114)','\t(generator "kisch")','\t(generator_version "10.0")',
              '\t(uuid "%s")'%self.root_uuid,'\t(paper "A3")',
              '\t(title_block\n\t\t(title "%s")\n\t\t(date "2026-05-29")\n\t\t(rev "0.1")\n%s\t)'%(title,comments),
              self._lib_symbols_block()]
        for t in self.root_texts: body.append(self._text_block(*t))
        for s in self.sheets: body.append(self._sheet_obj(s))
        for c in self.root_powers: body.append(self._comp_block(c,None,"/%s"%self.root_uuid))
        # root sheet_instances enumerates all pages
        paths='\t\t(path "/"\n\t\t\t(page "1")\n\t\t)\n'
        for s in self.sheets:
            paths+='\t\t(path "/%s"\n\t\t\t(page "%s")\n\t\t)\n'%(s.inst_uuid,s.page)
        body.append('\t(sheet_instances\n%s\t)'%paths)
        body.append(")")
        open(os.path.join(self.outdir,self.name+".kicad_sch"),"w").write("\n".join(body)+"\n")
    def write_libtables(self):
        # symbol lib table (absolute URIs for libs actually used)
        rows=[]
        for lib in sorted(self._used):
            uri = CUSTOM_LIBS[lib] if lib in CUSTOM_LIBS else "%s/%s.kicad_sym"%(SYMDIR,lib)
            rows.append('\t(lib (name "%s")(type "KiCad")(uri "%s")(options "")(descr ""))'%(lib,uri))
        open(os.path.join(self.outdir,"sym-lib-table"),"w").write("(sym_lib_table\n\t(version 7)\n"+"\n".join(rows)+"\n)\n")
        # footprint lib table (libs referenced in Footprint fields)
        fplibs=set()
        for s in self.sheets:
            for c in s.comps:
                fp=c.fields.get('Footprint','')
                if ':' in fp: fplibs.add(fp.split(':',1)[0])
        rows=[]
        for lib in sorted(fplibs):
            rows.append('\t(lib (name "%s")(type "KiCad")(uri "%s/%s.pretty")(options "")(descr ""))'%(lib,FPDIR,lib))
        open(os.path.join(self.outdir,"fp-lib-table"),"w").write("(fp_lib_table\n\t(version 7)\n"+"\n".join(rows)+"\n)\n")
    def root_power(self, sym, at):
        self.use_symbol('power', sym)
        pins=pins_of(self.lib('power'),sym); pinmap={p['number']:(p['x'],p['y']) for p in pins}
        c=Comp("power:%s"%sym,_pwr_ref(),sym,at,pinmap); c.is_power=True
        self.root_powers.append(c); return c

if __name__ == "__main__":
    import sys
    lib, sym = sys.argv[1], sys.argv[2]
    for p in pins_of(load_lib(lib), sym):
        print(p)
