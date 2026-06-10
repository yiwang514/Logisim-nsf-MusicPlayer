#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_cpu.py — emit cpu.circ for the Logisim NSF music player (milestones 3 & 4).

WHY A GENERATOR?
  cpu.circ is a single-cycle 5-stage CPU = 150+ Logisim components.  Hand-typing
  .circ XML coordinates is error-prone.  This generator encodes the EXACT port
  offsets of every component (verified against ref/logisim-evolution v4.x source,
  see PORT GEOMETRY below) and wires everything with TUNNELS (隧道) by name, so
  each port only needs a short stub wire to a same-named tunnel — no long-distance
  routing, no coordinate arithmetic between components.  Output is a standard .circ
  the user can open / edit in the Logisim GUI (4.1.0), same component+attribute
  vocabulary as the hand-built apu.circ.

VERIFICATION:
  build the headless jar once (see plan/logisim_test_harness.html), then
    java -Djava.awt.headless=true -jar <jar> --tty stats cpu.circ   # load check
    java -Djava.awt.headless=true -jar <jar> --tty table cpu.circ   # timing (needs a `halt` pin)

PORT GEOMETRY (offsets relative to a component's loc anchor; source-verified):
  Counter (appearance=logisim_evolution), W=150+int((w-8)/5)*10  [Java trunc toward 0]:
     CLR(0,20) LD(0,30) UD(0,50) EN(0,70) CK(0,80) D(0,110|120 if w==1)
     Q(W+40,110|120) CARRY(W+40,50)                       [std/memory/Counter.java]
  Register (appearance=logisim_evolution):
     D(0,30) Q(60,30) EN(0,50) CK(0,70) CLR(30,90)        [std/memory/Register.java]
  Decoder (select=4 -> 16 one-hot, enable=false), default facing east / select bottom-left:
     SEL = loc;  out[k] = (20, -160 + 10*k)               [std/plexers/Decoder.java]
  Splitter, default appear=left, facing=east, spacing=1 (gap=10):
     combined end = loc;  end[i] = (20, -(10+10*(fanout-1)) + 10*i)   [circuit/SplitterParameters.java]
     attr bitK = (input bit K) -> output end index 0..fanout-1
  Bit Extender:  OUT(0,0)  IN(-40,0)   attrs in_width/out_width/type   [std/wiring/BitExtender.java]
  Gate (AND/OR, 2-input, default size=50):  OUT(0,0) A(-50,-20) B(-50,20)   [std/gates/*]
  NOT gate (default):  OUT(0,0) IN(-30,0)                 [std/gates/NotGate.java]
  ROM (appearance=classic):  ADDR(0,10)  DATA(240,60)     [std/memory/RamAppearance.java]
  Pin / Constant / Clock / Tunnel / Probe:  port = loc.
"""

import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# AI-generated files use the *_pureAI names; cpu.circ / top.circ are the team's
# hand-built files and are NEVER written by this generator.
OUT  = os.path.join(REPO, "cpu_pureAI.circ")
TOP  = os.path.join(REPO, "top.circ")           # (only written if GEN_TOP is set; off by default)
TOP_PUREAI = os.path.join(REPO, "top_pureAI.circ")

# ---------------------------------------------------------------------------
# file header (libs / options / toolbar) — copied verbatim from apu.circ style
# ---------------------------------------------------------------------------
HEADER = '''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<project source="4.1.0" version="1.0">
  This file is intended to be loaded by Logisim-evolution v4.1.0(https://github.com/logisim-evolution/).

  <lib desc="#Wiring" name="0">
    <tool name="Pin">
      <a name="appearance" val="classic"/>
    </tool>
  </lib>
  <lib desc="#Gates" name="1"/>
  <lib desc="#Plexers" name="2"/>
  <lib desc="#Arithmetic" name="3"/>
  <lib desc="#FPArithmetic" name="4"/>
  <lib desc="#Memory" name="5"/>
  <lib desc="#I/O" name="6"/>
  <lib desc="#TTL" name="7"/>
  <lib desc="#TCL" name="8"/>
  <lib desc="#Base" name="9"/>
  <lib desc="#BFH-Praktika" name="10"/>
  <lib desc="#Input/Output-Extra" name="11"/>
  <lib desc="#Soc" name="12"/>
__EXTRA_LIBS__
  <main name="__MAIN__"/>
  <options>
    <a name="gateUndefined" val="ignore"/>
    <a name="simlimit" val="1000"/>
    <a name="simrand" val="0"/>
  </options>
  <mappings>
    <tool lib="9" map="Button2" name="Poke Tool"/>
    <tool lib="9" map="Button3" name="Menu Tool"/>
    <tool lib="9" map="Ctrl Button1" name="Menu Tool"/>
  </mappings>
  <toolbar>
    <tool lib="9" name="Poke Tool"/>
    <tool lib="9" name="Edit Tool"/>
    <tool lib="9" name="Wiring Tool"/>
    <tool lib="9" name="Text Tool"/>
    <sep/>
    <tool lib="0" name="Pin"/>
    <tool lib="0" name="Pin">
      <a name="facing" val="west"/>
      <a name="type" val="output"/>
    </tool>
    <sep/>
    <tool lib="1" name="NOT Gate"/>
    <tool lib="1" name="AND Gate"/>
    <tool lib="1" name="OR Gate"/>
    <tool lib="1" name="XOR Gate"/>
    <tool lib="1" name="NAND Gate"/>
    <tool lib="1" name="NOR Gate"/>
    <sep/>
    <tool lib="5" name="D Flip-Flop"/>
    <tool lib="5" name="Register"/>
  </toolbar>
'''
FOOTER = "</project>\n"

def render_header(extra_libs, main_name='main'):
    """extra_libs: list of (name, desc) for loaded file libraries."""
    libs = '\n'.join(f'  <lib desc="{d}" name="{n}"/>' for n, d in extra_libs)
    return HEADER.replace('__EXTRA_LIBS__', libs).replace('__MAIN__', main_name)


# ---------------------------------------------------------------------------
# small builder
# ---------------------------------------------------------------------------
class Circ:
    def __init__(self, name, freq="4000.0"):
        self.name = name
        self.freq = freq
        self.body = []   # xml lines (components + wires)

    def comp(self, lib, name, x, y, attrs=None):
        """attrs: list of (key, val). lib=None for a subcircuit instance.
        A multi-line value (e.g. ROM `contents`) is emitted as element TEXT
        (<a name=k>val</a>), which is how Logisim stores it — NOT as val="...".
        """
        libattr = '' if lib is None else f'lib="{lib}" '
        if attrs:
            self.body.append(f'    <comp {libattr}loc="({x},{y})" name="{name}">')
            for k, v in attrs:
                if isinstance(v, str) and '\n' in v:
                    self.body.append(f'      <a name="{k}">{v}</a>')
                else:
                    self.body.append(f'      <a name="{k}" val="{v}"/>')
            self.body.append(f'    </comp>')
        else:
            self.body.append(f'    <comp {libattr}loc="({x},{y})" name="{name}"/>')

    def wire(self, x1, y1, x2, y2):
        if (x1, y1) == (x2, y2):
            return
        assert x1 == x2 or y1 == y2, f"diagonal wire ({x1},{y1})->({x2},{y2})"
        self.body.append(f'    <wire from="({x1},{y1})" to="({x2},{y2})"/>')

    # ---- tunnels / constants -------------------------------------------------
    def tunnel(self, label, x, y, width=1, facing=None):
        a = [('label', label)]
        if width != 1:
            a.append(('width', str(width)))
        if facing:
            a.append(('facing', facing))
        self.comp(0, 'Tunnel', x, y, a)

    _DIR = {'L': (-1, 0), 'R': (1, 0), 'U': (0, -1), 'D': (0, 1)}
    _FACE = {'L': 'west', 'R': 'east', 'U': 'north', 'D': 'south'}

    def net(self, px, py, label, width=1, d='L', stub=20):
        """Attach component port (px,py) to tunnel `label` via a short stub."""
        dx, dy = self._DIR[d]
        tx, ty = px + dx * stub, py + dy * stub
        self.wire(px, py, tx, ty)
        self.tunnel(label, tx, ty, width, self._FACE[d])

    def const(self, px, py, value, width=1, d='L', stub=20):
        """Drive component port (px,py) from a Constant."""
        dx, dy = self._DIR[d]
        cx, cy = px + dx * stub, py + dy * stub
        self.wire(px, py, cx, cy)
        a = [('facing', self._FACE[d]), ('value', f'0x{value:x}')]
        if width != 1:
            a.append(('width', str(width)))
        self.comp(0, 'Constant', cx, cy, a)

    def drive_net_const(self, x, y, value, label, width=1):
        """Place a Constant at (x,y) that drives tunnel `label`."""
        a = [('facing', 'east'), ('value', f'0x{value:x}')]
        if width != 1:
            a.append(('width', str(width)))
        self.comp(0, 'Constant', x, y, a)
        self.net(x, y, label, width, 'R')

    def render(self):
        out = [f'  <circuit name="{self.name}">',
               '    <a name="appearance" val="logisim_evolution"/>',
               f'    <a name="circuit" val="{self.name}"/>',
               '    <a name="circuitnamedboxfixedsize" val="true"/>',
               f'    <a name="simulationFrequency" val="{self.freq}"/>']
        out.extend(self.body)
        out.append('  </circuit>')
        return '\n'.join(out) + '\n'


# ---------------------------------------------------------------------------
# port-offset helpers (source-verified)
# ---------------------------------------------------------------------------
def cW(w):
    return 150 + int((w - 8) / 5) * 10        # Java integer division truncates toward 0

def counter(x, y, w):
    dq = 120 if w == 1 else 110
    qx = x + cW(w) + 40
    return {'clr': (x, y + 20), 'ld': (x, y + 30), 'ud': (x, y + 50),
            'en': (x, y + 70), 'ck': (x, y + 80), 'd': (x, y + dq),
            'q': (qx, y + dq), 'carry': (qx, y + 50)}

def register(x, y):
    return {'d': (x, y + 30), 'q': (x + 60, y + 30), 'en': (x, y + 50),
            'ck': (x, y + 70), 'clr': (x + 30, y + 90)}

def dec_sel(x, y):       return (x, y)
def dec_out(x, y, k, nout=16): return (x + 20, y - 10 * nout + 10 * k)

def spl_comb(x, y):      return (x, y)
def spl_end(x, y, i, f): return (x + 20, y - (10 + 10 * (f - 1)) + 10 * i)

def bitext(x, y):        return {'out': (x, y), 'in': (x - 40, y)}
def gate2(x, y):         return {'out': (x, y), 'a': (x - 50, y - 20), 'b': (x - 50, y + 20)}
def notg(x, y):          return {'out': (x, y), 'in': (x - 30, y)}
def rom(x, y):           return {'a': (x, y + 10), 'd': (x + 240, y + 60)}


# ---------------------------------------------------------------------------
# component emitters that also place their ports onto nets
# ---------------------------------------------------------------------------
def put_counter(c, x, y, w, *, label, ck, clr, ld, en, ud, d, q=None, carry=None,
                maxval=None, ongoal=None):
    a = [('appearance', 'logisim_evolution'), ('width', str(w))]
    if maxval is not None: a.append(('max', f'0x{maxval:x}'))
    if ongoal:             a.append(('ongoal', ongoal))
    if label:              a.append(('label', label))
    c.comp(5, 'Counter', x, y, a)
    p = counter(x, y, w)
    # control pins on the LEFT edge -> route left
    _wire_port(c, p['ck'],  ck,  w=1, d='L')
    _wire_port(c, p['clr'], clr, w=1, d='L')
    _wire_port(c, p['ld'],  ld,  w=1, d='L')
    _wire_port(c, p['en'],  en,  w=1, d='L')
    _wire_port(c, p['ud'],  ud,  w=1, d='L')
    _wire_port(c, p['d'],   d,   w=w, d='L', stub=40)
    if q:     _wire_port(c, p['q'],     q,     w=w, d='R')
    if carry: _wire_port(c, p['carry'], carry, w=1, d='R')

def _wire_port(c, port, spec, *, w, d, stub=20):
    """spec: ('net',name) | ('net',name,width) | ('const',value) | ('const',value,width) | None"""
    if spec is None:
        return
    px, py = port
    kind = spec[0]
    if kind == 'net':
        name = spec[1]
        width = spec[2] if len(spec) > 2 else w
        c.net(px, py, name, width, d, stub)
    elif kind == 'const':
        value = spec[1]
        width = spec[2] if len(spec) > 2 else w
        c.const(px, py, value, width, d, stub)

def put_register(c, x, y, w, *, label, d, q, ck, en, clr):
    a = [('appearance', 'logisim_evolution'), ('width', str(w))]
    if label: a.append(('label', label))
    c.comp(5, 'Register', x, y, a)
    p = register(x, y)
    _wire_port(c, p['d'],   d,   w=w, d='L')
    _wire_port(c, p['q'],   q,   w=w, d='R')
    _wire_port(c, p['ck'],  ck,  w=1, d='L')
    _wire_port(c, p['en'],  en,  w=1, d='L', stub=40)
    _wire_port(c, p['clr'], clr, w=1, d='D')

def put_decoder(c, x, y, *, sel, outs, select_bits=4):
    """outs: dict {k: ('net',name)} for the one-hot outputs you use."""
    c.comp(2, 'Decoder', x, y, [('enable', 'false'), ('select', str(select_bits))])
    _wire_port(c, dec_sel(x, y), sel, w=select_bits, d='D', stub=30)
    nout = 1 << select_bits
    for k, spec in outs.items():
        _wire_port(c, dec_out(x, y, k, nout), spec, w=1, d='R')

def put_splitter(c, x, y, *, incoming, fanout, bits, comb, ends):
    """bits: dict {input_bit: end_index}.  ends: dict {end_index: ('net',name,width)}."""
    a = [('appearance', 'left'), ('fanout', str(fanout)), ('incoming', str(incoming))]
    # explicit per-bit mapping (avoid relying on default distribution)
    for b in range(incoming):
        a.append((f'bit{b}', str(bits[b])))
    # keep attribute order: bitN then fanout/incoming is fine; Logisim is order-independent
    c.comp(0, 'Splitter', x, y, a)
    _wire_port(c, spl_comb(x, y), comb, w=incoming, d='L')
    for i, spec in ends.items():
        _wire_port(c, spl_end(x, y, i, fanout), spec, w=spec[2], d='R')

def put_bitext(c, x, y, *, in_w, out_w, src, dst, typ='zero'):
    c.comp(0, 'Bit Extender', x, y,
           [('in_width', str(in_w)), ('out_width', str(out_w)), ('type', typ)])
    p = bitext(x, y)
    _wire_port(c, p['in'],  src, w=in_w,  d='L')
    _wire_port(c, p['out'], dst, w=out_w, d='R')

def put_gate(c, x, y, kind, *, a, b, out):
    name = {'and': 'AND Gate', 'or': 'OR Gate'}[kind]
    c.comp(1, name, x, y, None)
    p = gate2(x, y)
    _wire_port(c, p['a'],   a,   w=1, d='L')
    _wire_port(c, p['b'],   b,   w=1, d='L')
    _wire_port(c, p['out'], out, w=1, d='R')

def put_not(c, x, y, *, src, out):
    c.comp(1, 'NOT Gate', x, y, None)
    p = notg(x, y)
    _wire_port(c, p['in'],  src, w=1, d='L')
    _wire_port(c, p['out'], out, w=1, d='R')

# --- arithmetic (lib 3): Adder/Subtractor/Comparator share IN0(-40,-10) IN1(-40,10) OUT(0,0)
def put_addsub(c, x, y, kind, w, *, a, b, out):
    name = {'add': 'Adder', 'sub': 'Subtractor'}[kind]
    c.comp(3, name, x, y, [('width', str(w))])
    _wire_port(c, (x - 40, y - 10), a,   w=w, d='L', stub=30)
    _wire_port(c, (x - 40, y + 10), b,   w=w, d='L', stub=30)
    _wire_port(c, (x, y),           out, w=w, d='R')
    c.const(x - 20, y - 20, 0, 1, 'U', stub=20)   # carry/borrow in = 0

def put_cmp(c, x, y, w, *, a, b, gt=None, eq=None, lt=None):
    c.comp(3, 'Comparator', x, y, [('width', str(w))])
    _wire_port(c, (x - 40, y - 10), a, w=w, d='L', stub=30)
    _wire_port(c, (x - 40, y + 10), b, w=w, d='L', stub=30)
    if gt: _wire_port(c, (x, y - 10), gt, w=1, d='R')
    if eq: _wire_port(c, (x, y),      eq, w=1, d='R')
    if lt: _wire_port(c, (x, y + 10), lt, w=1, d='R')

# --- multiplexer (lib 2), size=wide (w=40/30, s=20), facing EAST, enable off
def put_mux(c, x, y, select_bits, width, *, sel, ins, out):
    c.comp(2, 'Multiplexer', x, y,
           [('enable', 'false'), ('select', str(select_bits)),
            ('size', '40'), ('width', str(width))])
    n = 1 << select_bits
    if n == 2:
        pins = [(x - 30, y - 10), (x - 30, y + 10)]
        spx, spy = x - 20, y + 20
    else:
        off = (n // 2) * 10           # data inputs span [-off, -off+10*(n-1)] in y
        pins = [(x - 40, y - off + 10 * i) for i in range(n)]
        spx, spy = x - 20, y - off + 10 * n   # select pin below the inputs
    for i in range(n):
        if i < len(ins) and ins[i]:
            _wire_port(c, pins[i], ins[i], w=width, d='L', stub=30)
    _wire_port(c, (spx, spy), sel, w=select_bits, d='D', stub=30)
    _wire_port(c, (x, y), out, w=width, d='R')

def put_rom(c, x, y, *, addr_w, data_w, contents, addr, data):
    c.comp(5, 'ROM', x, y,
           [('addrWidth', str(addr_w)), ('appearance', 'classic'),
            ('contents', contents), ('dataWidth', str(data_w))])
    p = rom(x, y)
    _wire_port(c, p['a'], addr, w=addr_w, d='L')
    _wire_port(c, p['d'], data, w=data_w, d='R')

def put_pin(c, x, y, *, label, width=1, output=False, radix=None, net=None, d='L', initial=None):
    # attribute order mirrors a known-good Logisim file (probe.circ): the LABEL
    # must be emitted right after `facing`/before `type`, otherwise the analyzer's
    # getPinLabels() fails to pick it up and renames the pin x/y/z.
    a = [('appearance', 'classic')]
    if initial is not None:
        a.append(('initial', f'0x{initial:x}'))   # input-pin power-on/reset value
    if output:
        a.append(('facing', 'west'))
    a.append(('label', label))
    if radix:
        a.append(('radix', radix))
    if output:
        a.append(('type', 'output'))
    if width != 1:
        a.append(('width', str(width)))
    c.comp(0, 'Pin', x, y, a)
    if net is not None:
        c.net(x, y, net, width, d)

def put_clock(c, x, y, *, net):
    c.comp(0, 'Clock', x, y, [('appearance', 'NewPins')])
    c.net(x, y, net, 1, 'R')

def put_button(c, x, y, *, net):
    c.comp(6, 'Button', x, y, None)
    c.net(x, y, net, 1, 'R')

def put_probe(c, x, y, net, width, radix='16', d='L'):
    c.comp(0, 'Probe', x, y, [('radix', radix)])
    c.net(x, y, net, width, d)


# subcircuit instance ports (auto-appearance, fixedSize): dy=20, box width=220.
#   has outputs  -> anchor top-RIGHT: out[i]=(L, L_y+20i), in[j]=(L-220, L_y+20j)
#   inputs only  -> anchor top-LEFT : in[j]=(L,  L_y+20j)
# (DefaultEvolutionAppearance: FIXED_FONT_HEIGHT=12 -> dy=20; fixedSize width=25*8/10*10+20=220)
INST_DY, INST_W = 20, 220

def put_instance(c, name, x, y, inputs, outputs, nets, lib=None):
    """Instantiate subcircuit `name`; nets: {portlabel: ('net',name[,width])}.
    lib=None for a circuit in this file; lib=<n> for a loaded-library circuit."""
    c.comp(lib, name, x, y, None)
    has_out = len(outputs) > 0
    for j, lbl in enumerate(inputs):
        px = x - INST_W if has_out else x
        spec = nets.get(lbl)
        if spec:
            _wire_port(c, (px, y + INST_DY * j), spec, w=(spec[2] if len(spec) > 2 else 1), d='L')
    for i, lbl in enumerate(outputs):
        spec = nets.get(lbl)
        if spec:
            _wire_port(c, (x, y + INST_DY * i), spec, w=(spec[2] if len(spec) > 2 else 1), d='R')

CPU_IN  = ['clk', 'reset', 'tempo_mode', 'tempo_delta']
CPU_OUT = ['reg_id', 'value', 'wr', 'frame_commit', 'pcout', 'wait_d',
           'r0_o', 'r1_o', 'r2_o', 'r3_o']
# CPU_EXT: bus-interface CPU (external instruction ROM) for top assembly.
#   inputs (WEST, by Y):  clk, reset, tempo_mode, tempo_delta, instr
#   outputs (EAST, by Y): pcbus, reg_id, value, wr, frame_commit, wait_d
CPU_EXT_IN  = ['clk', 'reset', 'tempo_mode', 'tempo_delta', 'instr']
CPU_EXT_OUT = ['pcbus', 'reg_id', 'value', 'wr', 'frame_commit', 'wait_d']
# APU subcircuit (loaded from apu.circ): inputs only, sorted top->bottom by their
# y in apu.circ -> ch_mask(110) WR(380) reg_id(510) value(530) frame_clk(730).
APU_IN  = ['ch_mask', 'WR', 'reg_id', 'value', 'frame_clk']


# ---------------------------------------------------------------------------
# ROM contents
# ---------------------------------------------------------------------------
def rom_contents_from_words(words, addr_w=16, data_w=16):
    lines = [f'addr/data: {addr_w} {data_w}']
    for i in range(0, len(words), 8):
        lines.append(' '.join(words[i:i + 8]))
    return '\n'.join(lines) + '\n'

# small WAIT-stall demo program: WRITE; WAIT 5; WRITE; END  (then zeros)
DEMO_WORDS = ['1100', '0005', '1200', 'f000']

# ALU demo: LOADI R0,5; LOADI R1,3; ADD R2,R0,R1; WRITEREG APU[2]=R2; END
#   -> R2 = 8, then APU value bus = 8 on the WRITEREG.  (change 5840->6840 for SUB=2)
ALU_WORDS = ['4005', '4403', '5840', '7280', 'f000']

def load_track_words(path):
    """Read a `v2.0 raw` ROM dump (script/out/trackNN.txt) -> list of tokens."""
    toks = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('v2.0'):
                continue
            toks.extend(line.split())
    return toks


# ---------------------------------------------------------------------------
# the M3 CPU core (built inline into a circuit, tunnel-wired)
# ---------------------------------------------------------------------------
def build_cpu_core(c, *, rom_words, m4=True, external_rom=False):
    """Lay down the single-cycle 5-stage CPU.  All signals are tunnels.
    m4=True adds the ALU tempo-control (into WAIT) and R0-R3 + LOADI/ADD/SUB/WRITEREG.
    external_rom=True omits the internal ROM: INSTR becomes an input net (driven by
    an external ROM/mux) and PCQ an output net (to the external ROM address)."""
    contents = rom_contents_from_words(rom_words)

    # --- IF: PC counter + instruction ROM -----------------------------------
    put_counter(c, 640, 160, 16, label='PC',
                ck=('net', 'clk'), clr=('net', 'reset'),
                ld=('net', 'IS_END'), en=('net', 'NSTALL'),
                ud=('const', 1), d=('const', 0, 16),
                q=('net', 'PCQ'), maxval=0xffff)
    if not external_rom:
        put_rom(c, 200, 160, addr_w=16, data_w=16, contents=contents,
                addr=('net', 'PCQ'), data=('net', 'INSTR'))

    # --- ID: split fields + decode opcode -----------------------------------
    # INSTR[11:0]=IMM/end0 , INSTR[15:12]=OPCODE/end1
    put_splitter(c, 440, 700, incoming=16, fanout=2,
                 bits={b: (0 if b < 12 else 1) for b in range(16)},
                 comb=('net', 'INSTR'),
                 ends={0: ('net', 'IMM', 12), 1: ('net', 'OPCODE', 4)})
    # IMM[7:0]=VAL/end0 , IMM[11:8]=REGID/end1
    put_splitter(c, 440, 900, incoming=12, fanout=2,
                 bits={b: (0 if b < 8 else 1) for b in range(12)},
                 comb=('net', 'IMM'),
                 ends={0: ('net', 'VAL', 8), 1: ('net', 'REGID', 4)})
    # opcode -> one-hot
    outs = {0: ('net', 'IS_WAIT'), 1: ('net', 'IS_WRITE'), 15: ('net', 'IS_END')}
    if m4:
        outs.update({4: ('net', 'IS_LOADI'), 5: ('net', 'IS_ADD'),
                     6: ('net', 'IS_SUB'), 7: ('net', 'IS_WRITEREG')})
    put_decoder(c, 1000, 1120, sel=('net', 'OPCODE'), outs=outs)
    # imm(12) zero-extended to 16 for WAIT load
    put_bitext(c, 760, 900, in_w=12, out_w=16, src=('net', 'IMM'), dst=('net', 'IMM16'))

    # --- EX: WAIT busy state machine ----------------------------------------
    # WAITCNT data = effective wait. M3: =IMM16. M4: =tempo-adjusted (see build_m4).
    waitload = ('net', 'WAITLOAD') if m4 else ('net', 'IMM16')
    put_counter(c, 1120, 160, 16, label='WAITCNT',
                ck=('net', 'clk'), clr=('net', 'reset'),
                ld=('net', 'START'), en=('net', 'ENCOUNT'),
                ud=('const', 0), d=waitload, q=('net', 'WCNTQ'),
                carry=('net', 'AT_ZERO'), maxval=0xffff, ongoal='stay')
    put_register(c, 1500, 660, 1, label='busy',
                 d=('net', 'BUSYNEXT'), q=('net', 'BUSY'),
                 ck=('net', 'clk'), en=('const', 1), clr=('net', 'reset'))

    put_not(c, 1760, 620, src=('net', 'BUSY'),     out=('net', 'NBUSY'))
    put_not(c, 1760, 700, src=('net', 'AT_ZERO'),  out=('net', 'NATZERO'))
    put_not(c, 1760, 780, src=('net', 'BUSYNEXT'), out=('net', 'NSTALL'))

    put_gate(c, 2040, 620, 'and', a=('net', 'IS_WAIT'), b=('net', 'NBUSY'),   out=('net', 'START'))
    put_gate(c, 2040, 720, 'and', a=('net', 'BUSY'),    b=('net', 'NATZERO'), out=('net', 'ENCOUNT'))
    put_gate(c, 2040, 840, 'or',  a=('net', 'START'),   b=('net', 'ENCOUNT'), out=('net', 'BUSYNEXT'))

    # --- MEM/WB: frame_commit (+ WRITE pulse; M4 folds WRITEREG into it) -----
    put_gate(c, 2040, 1060, 'and', a=('net', 'START'), b=('net', 'clk'), out=('net', 'FRAMECOMMIT'))
    if not m4:
        put_gate(c, 2040, 960, 'and', a=('net', 'IS_WRITE'), b=('net', 'clk'), out=('net', 'WRPULSE'))
    else:
        build_m4(c)


# ---------------------------------------------------------------------------
# M4: ALU tempo-control into WAIT  +  R0-R3 with LOADI/ADD/SUB/WRITEREG.
#   tempo: WAITLOAD = MUX(tempo_mode){ imm, imm+delta, clamp(imm-delta,>=1), imm }
#   regs : R[Rd] = LOADI imm8 | R[Ra]+R[Rb] | R[Ra]-R[Rb];  WRITEREG -> APU value
# Nets in: IMM16, VAL, REGID, IS_* ; in (external): tempo_mode(2), tempo_delta(16)
# Nets out: WAITLOAD(16)->WAITCNT.d, WRPULSE, VALUE_OUT(8), R0Q..R3Q
# ---------------------------------------------------------------------------
def build_m4(c):
    # ===== tempo ALU (region x~2600-3500, y~300-800) =====
    put_addsub(c, 2800, 320, 'add', 16, a=('net', 'IMM16'), b=('net', 'tempo_delta'), out=('net', 'ADD_SLOW'))
    put_addsub(c, 2800, 520, 'sub', 16, a=('net', 'IMM16'), b=('net', 'tempo_delta'), out=('net', 'SUB_FAST'))
    put_cmp(c, 2800, 720, 16, a=('net', 'IMM16'), b=('net', 'tempo_delta'),
            eq=('net', 'CMP_EQ'), lt=('net', 'CMP_LT'))
    put_gate(c, 3000, 720, 'or', a=('net', 'CMP_LT'), b=('net', 'CMP_EQ'), out=('net', 'IMM_LE'))
    # clamp fast value: if imm<=delta use 1 else (imm-delta)
    c.drive_net_const(3050, 560, 1, 'ONE16', 16)
    put_mux(c, 3220, 520, 1, 16, sel=('net', 'IMM_LE'),
            ins=[('net', 'SUB_FAST'), ('net', 'ONE16')], out=('net', 'FAST_CLAMP'))
    # tempo select: 0=normal(imm) 1=slow(imm+delta) 2=fast(clamp) 3=imm
    put_mux(c, 3460, 420, 2, 16, sel=('net', 'tempo_mode'),
            ins=[('net', 'IMM16'), ('net', 'ADD_SLOW'), ('net', 'FAST_CLAMP'), ('net', 'IMM16')],
            out=('net', 'WAITLOAD'))

    # ===== register-file field extraction =====
    # REGID[1:0]=Ra(instr[9:8]) , REGID[3:2]=Rd(instr[11:10])
    put_splitter(c, 2500, 1000, incoming=4, fanout=2,
                 bits={0: 0, 1: 0, 2: 1, 3: 1},
                 comb=('net', 'REGID'),
                 ends={0: ('net', 'RA', 2), 1: ('net', 'RD', 2)})
    # VAL[7:6]=Rb=Rs(instr[7:6])  (low 6 unused)
    put_splitter(c, 2500, 1200, incoming=8, fanout=2,
                 bits={0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 1, 7: 1},
                 comb=('net', 'VAL'),
                 ends={0: ('net', 'VLO', 6), 1: ('net', 'RB', 2)})

    # ===== R0-R3 (8-bit) =====
    for i in range(4):
        put_register(c, 2720, 1380 + 150 * i, 8, label=f'R{i}',
                     d=('net', 'REGWB'), q=('net', f'R{i}Q'),
                     ck=('net', 'clk'), en=('net', f'WE{i}'), clr=('net', 'reset'))

    # read ports: R[Ra], R[Rb]
    regq = [('net', f'R{i}Q', 8) for i in range(4)]
    put_mux(c, 3120, 1420, 2, 8, sel=('net', 'RA'), ins=regq, out=('net', 'RA_VAL'))
    put_mux(c, 3120, 1720, 2, 8, sel=('net', 'RB'), ins=regq, out=('net', 'RB_VAL'))

    # ALU: add / sub, select by IS_SUB
    put_addsub(c, 3420, 1420, 'add', 8, a=('net', 'RA_VAL'), b=('net', 'RB_VAL'), out=('net', 'ALU_ADD'))
    put_addsub(c, 3420, 1620, 'sub', 8, a=('net', 'RA_VAL'), b=('net', 'RB_VAL'), out=('net', 'ALU_SUB'))
    put_mux(c, 3700, 1500, 1, 8, sel=('net', 'IS_SUB'),
            ins=[('net', 'ALU_ADD'), ('net', 'ALU_SUB')], out=('net', 'ALU_RES'))
    # writeback: LOADI uses imm8(=VAL), else ALU result
    put_mux(c, 3940, 1640, 1, 8, sel=('net', 'IS_LOADI'),
            ins=[('net', 'ALU_RES'), ('net', 'VAL')], out=('net', 'REGWB'))

    # write enable = (is_loadi | is_add | is_sub) AND (Rd == k)
    put_gate(c, 2720, 2120, 'or', a=('net', 'IS_LOADI'), b=('net', 'IS_ADD'), out=('net', 'WRG1'))
    put_gate(c, 2920, 2120, 'or', a=('net', 'WRG1'),     b=('net', 'IS_SUB'), out=('net', 'REGWREN'))
    put_decoder(c, 3200, 2200, sel=('net', 'RD'), select_bits=2,
                outs={0: ('net', 'RDOH0'), 1: ('net', 'RDOH1'),
                      2: ('net', 'RDOH2'), 3: ('net', 'RDOH3')})
    for i in range(4):
        put_gate(c, 3460, 2080 + 70 * i, 'and',
                 a=('net', f'RDOH{i}'), b=('net', 'REGWREN'), out=('net', f'WE{i}'))

    # WRITEREG: APU value = is_writereg ? R[Rs] : imm8 ; Rs == Rb (instr[7:6])
    put_mux(c, 3940, 1900, 1, 8, sel=('net', 'IS_WRITEREG'),
            ins=[('net', 'VAL'), ('net', 'RB_VAL')], out=('net', 'VALUE_OUT'))

    # WR pulse for WRITE or WRITEREG
    put_gate(c, 2040, 960, 'or',  a=('net', 'IS_WRITE'), b=('net', 'IS_WRITEREG'), out=('net', 'WR_EN'))
    put_gate(c, 2260, 960, 'and', a=('net', 'WR_EN'),    b=('net', 'clk'),         out=('net', 'WRPULSE'))


# ---------------------------------------------------------------------------
# circuit `main` — testbench that INSTANTIATES the reusable CPU subcircuit.
#   verifies: CPU logic + subcircuit auto-appearance port geometry + track00 ROM.
# ---------------------------------------------------------------------------
def build_main(tempo_mode=0, tempo_delta=8):
    c = Circ('main')
    put_instance(c, 'CPU', 900, 320, CPU_IN, CPU_OUT, {
        'clk':   ('net', 'mclk'),
        'reset': ('net', 'mreset'),
        'tempo_mode':  ('net', 'TMODE', 2),
        'tempo_delta': ('net', 'TDELTA', 16),
        'reg_id':       ('net', 'REG_O', 4),
        'value':        ('net', 'VAL_O', 8),
        'wr':           ('net', 'WR_O'),
        'frame_commit': ('net', 'FC_O'),
        'pcout':        ('net', 'PC_O', 16),
        'wait_d':       ('net', 'WAIT_O', 16),
        'r2_o':         ('net', 'R2_O', 8),
    })
    # clock, reset, tempo controls
    put_clock(c, 300, 320, net='mclk')
    c.drive_net_const(300, 400, 0, 'mreset', 1)
    c.drive_net_const(300, 460, tempo_mode, 'TMODE', 2)
    c.drive_net_const(300, 520, tempo_delta, 'TDELTA', 16)

    # halt after `max` clock edges so --tty table terminates
    put_counter(c, 1500, 200, 8, label='tickcnt',
                ck=('net', 'mclk'), clr=('net', 'mreset'),
                ld=('const', 0), en=('const', 1), ud=('const', 1),
                d=('const', 0, 8), carry=('net', 'HALTC'), maxval=0x60, ongoal='stay')
    put_pin(c, 2100, 200, label='halt', output=True, net='HALTC', d='L')

    # observables
    put_pin(c, 2100, 300, label='pc_o',   width=16, output=True, radix='16', net='PC_O',  d='L')
    put_pin(c, 2100, 360, label='wait_o', width=16, output=True, radix='16', net='WAIT_O', d='L')
    put_pin(c, 2100, 420, label='reg_o',  width=4,  output=True, radix='16', net='REG_O', d='L')
    put_pin(c, 2100, 480, label='val_o',  width=8,  output=True, radix='16', net='VAL_O', d='L')
    put_pin(c, 2100, 540, label='wr_o',   width=1,  output=True, net='WR_O', d='L')
    put_pin(c, 2100, 600, label='r2_o',   width=8,  output=True, radix='16', net='R2_O', d='L')
    return c


# ---------------------------------------------------------------------------
# circuit `CPU` — the reusable single-cycle 5-stage CPU (for top.circ / APU)
#   inputs : clk, reset
#   outputs: reg_id(4) value(8) wr(1) frame_commit(1) pcout(16)
#   internal instruction ROM = track00 (real NES song)
# Pin label order (by Y) fixes the subcircuit's auto-appearance port order:
#   WEST inputs  top->bottom: clk, reset
#   EAST outputs top->bottom: reg_id, value, wr, frame_commit, pcout
# ---------------------------------------------------------------------------
def build_cpu_subcircuit(track_words):
    c = Circ('CPU')
    build_cpu_core(c, rom_words=track_words, m4=True)
    # boundary inputs (WEST), top->bottom = clk, reset, tempo_mode, tempo_delta
    put_pin(c, 150, 100, label='clk',         width=1,  output=False, net='clk',         d='R')
    put_pin(c, 150, 160, label='reset',       width=1,  output=False, net='reset',       d='R')
    put_pin(c, 150, 220, label='tempo_mode',  width=2,  output=False, net='tempo_mode',  d='R')
    put_pin(c, 150, 280, label='tempo_delta', width=16, output=False, net='tempo_delta', d='R')
    # boundary outputs (EAST) — labels must NOT collide with PC/WAITCNT/busy/R0-R3
    put_pin(c, 2600, 300, label='reg_id',       width=4,  output=True, radix='16', net='REGID',       d='L')
    put_pin(c, 2600, 360, label='value',        width=8,  output=True, radix='16', net='VALUE_OUT',   d='L')
    put_pin(c, 2600, 420, label='wr',           width=1,  output=True, net='WRPULSE',     d='L')
    put_pin(c, 2600, 480, label='frame_commit', width=1,  output=True, net='FRAMECOMMIT', d='L')
    put_pin(c, 2600, 540, label='pcout',        width=16, output=True, radix='16', net='PCQ',         d='L')
    put_pin(c, 2600, 600, label='wait_d',       width=16, output=True, radix='16', net='WCNTQ',       d='L')
    put_pin(c, 2600, 660, label='r0_o',         width=8,  output=True, radix='16', net='R0Q',         d='L')
    put_pin(c, 2600, 720, label='r1_o',         width=8,  output=True, radix='16', net='R1Q',         d='L')
    put_pin(c, 2600, 780, label='r2_o',         width=8,  output=True, radix='16', net='R2Q',         d='L')
    put_pin(c, 2600, 840, label='r3_o',         width=8,  output=True, radix='16', net='R3Q',         d='L')
    return c


def build_cpu_ext_subcircuit():
    """Bus-interface CPU: identical M3+M4 logic but the instruction ROM is EXTERNAL.
    PC is exposed as an address bus (pcbus), instructions arrive on a data bus (instr).
    This is the textbook CPU<->memory split; top wires the ROM bank to these buses."""
    c = Circ('CPU_EXT')
    build_cpu_core(c, rom_words=[], m4=True, external_rom=True)
    # inputs (WEST) — order by Y = clk, reset, tempo_mode, tempo_delta, instr
    put_pin(c, 150, 100, label='clk',         width=1,  output=False, net='clk',         d='R')
    put_pin(c, 150, 160, label='reset',       width=1,  output=False, net='reset',       d='R')
    put_pin(c, 150, 220, label='tempo_mode',  width=2,  output=False, net='tempo_mode',  d='R')
    put_pin(c, 150, 280, label='tempo_delta', width=16, output=False, net='tempo_delta', d='R')
    put_pin(c, 150, 340, label='instr',       width=16, output=False, net='INSTR',       d='R')  # data bus in
    # outputs (EAST) — order by Y = pcbus, reg_id, value, wr, frame_commit, wait_d
    put_pin(c, 2600, 400, label='pcbus',        width=16, output=True, radix='16', net='PCQ',         d='L')  # addr bus out
    put_pin(c, 2600, 460, label='reg_id',       width=4,  output=True, radix='16', net='REGID',       d='L')
    put_pin(c, 2600, 520, label='value',        width=8,  output=True, radix='16', net='VALUE_OUT',   d='L')
    put_pin(c, 2600, 580, label='wr',           width=1,  output=True, net='WRPULSE',     d='L')
    put_pin(c, 2600, 640, label='frame_commit', width=1,  output=True, net='FRAMECOMMIT', d='L')
    put_pin(c, 2600, 700, label='wait_d',       width=16, output=True, radix='16', net='WCNTQ', d='L')
    return c


def build_play():
    """CPU (this file) + APU (loaded from apu.circ) wired up so track00 sounds.
    Switch to this circuit in the GUI and run auto-tick (2-4 kHz) to hear it."""
    c = Circ('play')
    put_instance(c, 'CPU', 760, 300, CPU_IN, CPU_OUT, {
        'clk': ('net', 'pclk'), 'reset': ('net', 'preset'),
        'tempo_mode': ('net', 'ptmode', 2), 'tempo_delta': ('net', 'ptdelta', 16),
        'reg_id': ('net', 'AREG', 4), 'value': ('net', 'AVAL', 8),
        'wr': ('net', 'AWR'), 'frame_commit': ('net', 'AFC'),
    })
    put_instance(c, 'APU', 1320, 300, APU_IN, [], {
        'ch_mask': ('net', 'ACH', 4), 'WR': ('net', 'AWR'),
        'reg_id': ('net', 'AREG', 4), 'value': ('net', 'AVAL', 8),
        'frame_clk': ('net', 'AFC'),
    }, lib=13)
    put_clock(c, 300, 300, net='pclk')
    put_pin(c, 300, 380, label='reset', width=1, output=False, net='preset', d='R')
    put_pin(c, 300, 440, label='tempo', width=2, output=False, net='ptmode', d='R')
    c.drive_net_const(300, 500, 8, 'ptdelta', 16)
    c.drive_net_const(300, 560, 0xf, 'ACH', 4)
    return c


def build_top():
    """top.circ control panel: master Clock gated by `run` (play/pause), `reset`
    (stop), `tempo` switch; assembles CPU (lib 13=cpu.circ) + APU (lib 14=apu.circ)."""
    c = Circ('main')
    put_clock(c, 200, 200, net='mclk')
    put_pin(c, 200, 300, label='run',   width=1, output=False, net='run',   d='R')
    put_pin(c, 200, 360, label='reset', width=1, output=False, net='rst',   d='R')
    put_pin(c, 200, 440, label='tempo', width=2, output=False, net='tmode', d='R')
    c.drive_net_const(200, 500, 8,   'tdelta', 16)
    c.drive_net_const(200, 560, 0xf, 'ach', 4)
    # play/pause: CPU clock = master clock AND run  (run=0 freezes the CPU)
    put_gate(c, 520, 220, 'and', a=('net', 'mclk'), b=('net', 'run'), out=('net', 'cpuclk'))
    # CPU (from cpu.circ) -> APU (from apu.circ)
    put_instance(c, 'CPU', 820, 300, CPU_IN, CPU_OUT, {
        'clk': ('net', 'cpuclk'), 'reset': ('net', 'rst'),
        'tempo_mode': ('net', 'tmode', 2), 'tempo_delta': ('net', 'tdelta', 16),
        'reg_id': ('net', 'AREG', 4), 'value': ('net', 'AVAL', 8),
        'wr': ('net', 'AWR'), 'frame_commit': ('net', 'AFC'),
        'pcout': ('net', 'PCDISP', 16),
    }, lib=13)
    put_instance(c, 'APU', 1380, 300, APU_IN, [], {
        'ch_mask': ('net', 'ach', 4), 'WR': ('net', 'AWR'),
        'reg_id': ('net', 'AREG', 4), 'value': ('net', 'AVAL', 8),
        'frame_clk': ('net', 'AFC'),
    }, lib=14)
    # show PC on a probe
    c.comp(0, 'Probe', 1180, 700, [('radix', '16')])
    c.net(1180, 700, 'PCDISP', 16, 'L')
    return c


def build_top_pureAI(track_roms, verify=False):
    """FULL control panel (pure-AI) in top_pureAI.circ — standard CPU<->memory split.
    Loads cpu_pureAI.circ (lib 13) + apu.circ (lib 14); instantiates the CPU_EXT
    bus-interface CPU + an EXTERNAL N-ROM instruction-memory bank + APU + panel.
      - play/pause : master Clock gated by `run`              (run=0 freezes CPU)
      - stop       : `reset` -> PC=0
      - prev/next  : Buttons -> track# -> N:1 MUX = ROM bank switch (NES-mapper style)
      - tempo      : 2-bit switch -> ALU varispeed
      - ch_mask    : 4 switches (default ON) -> per-channel APU enable + probes
      (no MM:SS wall-clock timer: aligning Buzzer audio to real seconds is unreliable)
    verify=True: drive run/reset/tempo with constants + add halt/observe pins so the
    bus fetch + WAIT stall can be checked headless via --tty table."""
    c = Circ('main')

    # ----- transport controls -----
    if verify:
        put_clock(c, 200, 200, net='cpuclk')        # direct clock for headless test
        c.drive_net_const(200, 300, 0, 'rst', 1)
        c.drive_net_const(200, 360, 0, 'tmode', 2)
        put_counter(c, 200, 980, 8, label='vhalt',
                    ck=('net', 'cpuclk'), clr=('net', 'rst'),
                    ld=('const', 0), en=('const', 1), ud=('const', 1),
                    d=('const', 0, 8), carry=('net', 'VHALT'), maxval=0x80, ongoal='stay')
        put_pin(c, 600, 980,  label='halt',   width=1,  output=True, net='VHALT', d='L')
        put_pin(c, 600, 1040, label='pc_v',   width=16, output=True, radix='16', net='PCADDR', d='L')
        put_pin(c, 600, 1100, label='wait_v', width=16, output=True, radix='16', net='WAITDISP', d='L')
    else:
        put_clock(c, 200, 200, net='mclk')
        put_pin(c, 200, 300, label='run',   width=1, output=False, net='run',   d='R')
        put_pin(c, 200, 360, label='reset', width=1, output=False, net='rst_btn', d='R')
        put_pin(c, 200, 420, label='tempo', width=2, output=False, net='tmode', d='R')
        put_gate(c, 560, 220, 'and', a=('net', 'mclk'), b=('net', 'run'), out=('net', 'cpuclk'))
    c.drive_net_const(200, 480, 8, 'tdelta', 16)

    # ----- CPU_EXT (lib 13 = cpu_pureAI.circ): addr bus out (pcbus), instr bus in -----
    put_instance(c, 'CPU_EXT', 1100, 300, CPU_EXT_IN, CPU_EXT_OUT, {
        'clk': ('net', 'cpuclk'), 'reset': ('net', 'rst'),
        'tempo_mode': ('net', 'tmode', 2), 'tempo_delta': ('net', 'tdelta', 16),
        'instr': ('net', 'INSTRBUS', 16),
        'pcbus': ('net', 'PCADDR', 16),
        'reg_id': ('net', 'AREG', 4), 'value': ('net', 'AVAL', 8),
        'wr': ('net', 'AWR'),
        # frame_commit -> AFC directly in verify; else -> FCMT, then OR'd with a
        # paused-tick below so the APU keeps sampling (and thus mutes) while paused.
        'frame_commit': ('net', 'AFC' if verify else 'FCMT'),
        'wait_d': ('net', 'WAITDISP', 16),
    }, lib=13)

    # ----- prev/next -> track# selector (next=+1, prev=-1, wraps 0..N-1) -----
    # Bank/MUX/counter are sized to the ACTUAL song count N (not a fixed 16):
    # 16 big ROMs choke Logisim and "next" cycles through empty slots. With N=4
    # this is a 2-bit selector + 4:1 MUX — far lighter and no silent slots.
    have = dict(track_roms)
    n_songs = max(1, len(have))
    sel_bits = max(1, (n_songs - 1).bit_length())   # ceil(log2(N)), >=1
    n_slots = 1 << sel_bits                          # MUX width (>= n_songs)
    put_button(c, 200, 600, net='NEXTB')
    put_button(c, 200, 660, net='PREVB')
    put_gate(c, 560, 620, 'or', a=('net', 'NEXTB'), b=('net', 'PREVB'), out=('net', 'TRKCLK'))
    # reset = manual reset button  OR  song-change (next/prev): switching songs
    # pulses reset so the new track plays from PC=0 (verify mode drives rst directly).
    if not verify:
        put_gate(c, 440, 460, 'or', a=('net', 'rst_btn'), b=('net', 'TRKCLK'), out=('net', 'rst'))
    put_counter(c, 760, 600, sel_bits, label='trkcnt',
                ck=('net', 'TRKCLK'), clr=('const', 0),
                ld=('const', 0), en=('const', 1), ud=('net', 'NEXTB'),
                d=('const', 0, sel_bits), q=('net', 'TRACK'), maxval=n_songs - 1)

    # ----- EXTERNAL instruction memory: N-ROM bank (addr=PCADDR) -> N:1 MUX -> instr bus
    c.drive_net_const(1700, 150, 0xf000, 'SILENT', 16)
    mux_ins = []
    for slot in range(n_slots):
        if slot in have:
            ry = 250 + slot * 360
            put_rom(c, 1900, ry, addr_w=16, data_w=16,
                    contents=rom_contents_from_words(have[slot]),
                    addr=('net', 'PCADDR'), data=('net', f'ROM{slot}'))
            mux_ins.append(('net', f'ROM{slot}', 16))
        else:
            mux_ins.append(('net', 'SILENT', 16))   # pad non-power-of-2 gap (counter never selects it)
    put_mux(c, 2900, 700, sel_bits, 16, sel=('net', 'TRACK'), ins=mux_ins, out=('net', 'INSTRBUS'))

    # ----- APU channel mask: 4 independent on/off switches + live enable probes -----
    # ch_mask bit i -> apu.circ EN<i>: 0=Pulse1, 1=Pulse2, 2=Triangle, 3=Noise
    # (matches NES $4015 bit order; verified against apu.circ ch_mask splitter).
    # Each switch is AND'ed with `run`: pausing (run 1->0) forces ch_mask=0 (silence),
    # resuming restores the switch values. Probes read the run-gated (effective) bit.
    if verify:
        c.drive_net_const(3300, 1650, 0xf, 'ACH', 4)   # headless: force all-on
    else:
        chans = [('ch_p1', 'Pulse1'), ('ch_p2', 'Pulse2'),
                 ('ch_tri', 'Triangle'), ('ch_noise', 'Noise')]
        # active = run AND NOT rst_btn : both PAUSE (run=0) and STOP (reset held) force
        # ch_mask=0 (silence). reset alone doesn't touch the APU, so without this STOP
        # would leave the last note droning. Song-change uses TRKCLK->rst (not rst_btn),
        # so next/prev still plays with sound.
        put_not(c, 3220, 1540, src=('net', 'rst_btn'), out=('net', 'nrst'))
        put_gate(c, 3380, 1540, 'and', a=('net', 'run'), b=('net', 'nrst'), out=('net', 'active'))
        for i, (lbl, _name) in enumerate(chans):
            cy = 1620 + 40 * i
            put_pin(c, 3100, cy, label=lbl, width=1, output=False,
                    net=f'CH{i}r', d='R', initial=1)   # raw switch, default ON
            # mute-gate: CHi = switch AND active (gates spaced 60px to avoid port overlap)
            put_gate(c, 3340, 1620 + 60 * i, 'and',
                     a=('net', f'CH{i}r'), b=('net', 'active'), out=('net', f'CH{i}'))
            put_probe(c, 3540, 1620 + 60 * i, f'CH{i}', 1, '2')   # effective enable (0 when paused/stopped)
        # merge the 4 single-bit switches into the 4-bit ch_mask bus (ACH)
        put_splitter(c, 3460, 1660, incoming=4, fanout=4,
                     bits={0: 0, 1: 1, 2: 2, 3: 3},
                     comb=('net', 'ACH', 4),
                     ends={0: ('net', 'CH0', 1), 1: ('net', 'CH1', 1),
                           2: ('net', 'CH2', 1), 3: ('net', 'CH3', 1)})

    # ----- APU frame_clk: keep it ticking while paused/stopped so the muted ch_mask
    # actually latches into the APU's ENABLE_R register (which is clocked by frame_clk).
    # AFC = frame_commit OR (mclk AND NOT active). When active(playing): = frame_commit
    # (clean per-frame sampling, audio unchanged). When NOT active(paused/stopped): the
    # free-running mclk clocks the APU so ENABLE_R samples ch_mask=0 -> buzzer off.
    # Without this, pausing freezes the clock and the buzzer drones the last note.
    if not verify:
        put_not(c, 700, 1100, src=('net', 'active'), out=('net', 'nactive'))
        put_gate(c, 860, 1120, 'and', a=('net', 'mclk'), b=('net', 'nactive'), out=('net', 'ptick'))
        put_gate(c, 1020, 1120, 'or', a=('net', 'FCMT'), b=('net', 'ptick'), out=('net', 'AFC'))

    # ----- APU (lib 14 = apu.circ) -----
    put_instance(c, 'APU', 3600, 1700, APU_IN, [], {
        'ch_mask': ('net', 'ACH', 4), 'WR': ('net', 'AWR'),
        'reg_id': ('net', 'AREG', 4), 'value': ('net', 'AVAL', 8),
        'frame_clk': ('net', 'AFC'),
    }, lib=14)

    # ----- status probes (MM:SS wall-clock timer intentionally omitted:
    #        aligning a Buzzer-driven sim to real seconds is unreliable; dropped) -----
    put_probe(c, 1450, 360, 'PCADDR', 16, '16')
    put_probe(c, 760, 480, 'TRACK', sel_bits, '10unsigned')
    return c


def main():
    rom = os.environ.get('GEN_ROM', 'track00')
    tmode = int(os.environ.get('GEN_TEMPO', '0'))
    if rom == 'demo':
        words = DEMO_WORDS
    elif rom == 'alu':
        words = ALU_WORDS
    elif rom == 'alusub':
        words = ['4005', '4403', '6840', 'f000']   # R2 = R0 - R1 = 5-3 = 2
    else:
        track = os.path.join(REPO, 'script', 'out', 'track00.txt')
        words = load_track_words(track) if os.path.exists(track) else DEMO_WORDS
    circuits = [build_main(tempo_mode=tmode), build_play(),
                build_cpu_subcircuit(words), build_cpu_ext_subcircuit()]
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write(render_header([('13', 'file#apu.circ')], 'main'))
        for ci in circuits:
            f.write(ci.render())
        f.write(FOOTER)
    print(f"wrote {OUT}  (rom={rom}, {len(words)} words, tempo_mode={tmode})")

    # top_pureAI.circ — FULL control panel; loads cpu_pureAI.circ (13) + apu.circ (14).
    # Pick up every trackNN.txt that exists (make_playlist.py controls how many).
    slots = []
    for s in range(16):
        tf = os.path.join(REPO, 'script', 'out', f'track{s:02d}.txt')
        if os.path.exists(tf):
            slots.append((s, load_track_words(tf)))
    with open(TOP_PUREAI, 'w', encoding='utf-8', newline='\n') as f:
        f.write(render_header([('13', 'file#cpu_pureAI.circ'), ('14', 'file#apu.circ')], 'main'))
        f.write(build_top_pureAI(slots, verify=bool(os.environ.get('GEN_TOPTEST'))).render())
        f.write(FOOTER)
    print(f"wrote {TOP_PUREAI}  (songs in slots {[s for s, _ in slots]})")

    # top.circ control panel (assembles cpu.circ + apu.circ).
    # OFF by default: top.circ is role A's file; only write when explicitly asked.
    if os.environ.get('GEN_TOP'):
        with open(TOP, 'w', encoding='utf-8', newline='\n') as f:
            f.write(render_header([('13', 'file#cpu.circ'), ('14', 'file#apu.circ')], 'main'))
            f.write(build_top().render())
            f.write(FOOTER)
        print(f"wrote {TOP}")


if __name__ == '__main__':
    main()
