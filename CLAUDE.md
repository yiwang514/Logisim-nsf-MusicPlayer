# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

A music player built in **Logisim-evolution v4.1.0** that plays real NES (NSF) music.
It is a hardware project: a hand-built 16-bit CPU plus a simplified APU whose audio
output is Logisim `Buzzer` components. The actual deliverable is the Logisim circuit;
the code in this repo is an **offline toolchain** that pre-converts NSF songs into
Logisim ROM images the circuit can load.

Deadline **2026-06-15**. The user works in a **Chinese** Logisim UI and is effectively
building the whole project solo (also coaching teammates A/C/D for a defense / 答辩).

**Read these before substantial work** (also enforced by `AGENTS.md`):
1. `plan/SESSION_HANDOFF.md` — current status, what's done, what's next
2. `plan/detailed_plan.html` — full design + feasibility audit + bus-width tables (§4)
3. `plan/milestone1_guide.html` — when continuing the step-by-step build guide
4. `.claude/skills/logisim-zh-terms/SKILL.md` — before writing any Logisim-facing doc

## Two layers

**Layer 1 — offline toolchain (`script/`, complete & verified):** Converts NSF → Logisim ROMs.

```
NSF file ──nsfdump.exe──▶ reg log ("frame addr value") ──encode.py──▶ instruction ROM (.txt)
   │                      (GME hook on $4000-$4017)         (16-bit fixed-width ISA)
   └─ make_tables.py ─────────────────────────────────────────────▶ frequency lookup ROMs (.txt)
```

- `script/gme_dump/dump_main.cpp` + patched **game-music-emu (GME)** — Stage 1 dumper. Hooks
  `Nes_Apu::write_register` to log every APU register write with a PLAY-frame timestamp.
  GME (not NSFPlay) was chosen because that one function is the single chokepoint for all writes.
- `script/encode.py` — Stage 2. Reg log → 16-bit instruction words → Logisim `v2.0 raw` ROM text.
- `script/make_tables.py` — generates `timer → real-Hz` lookup ROMs (Pulse/Triangle/Noise).
- `script/make_playlist.py` — orchestrates dumper+encoder for the 16-slot playlist.
- `script/out/*.txt` — generated ROM images (committed). Each must be loaded into a Logisim ROM
  with the **exact widths below** — set widths *first*, then Load Image, or data gets truncated.

| File | addrWidth | dataWidth | Notes |
|---|---|---|---|
| `track00..15.txt` | **16** | **16** | song instruction ROMs (largest ~41044 words > 4096, so PC is 16-bit) |
| `freq_pulse.txt` | 11 | 14 | Pulse1/2 timer → Hz. `freq_pulse[253] ≈ 440 Hz (A4)` — sanity check |
| `freq_triangle.txt` | 11 | 14 | Triangle (one octave down) |
| `freq_noise.txt` | 4 | 14 | `$400E` low-4-bits index → Hz |

**Layer 2 — the Logisim circuit (the remaining work, built by hand in the GUI):** Multi-`.circ` layout:
- `top.circ` — top level: 16-ROM MUX song selector, play/pause/stop/prev/next, timer (role A; this is the renamed old `coolproject.circ`, whose deletion is staged in git).
- `cpu.circ` — 5-stage single-cycle CPU + ALU + R0–R3 + MMIO (role C).
- `apu.circ` — 4 channels + Buzzer; contains scaffold subcircuits `BuzzerStress` and `PulseOneShot` (role D).
- `top.circ` loads `cpu.circ`/`apu.circ` via `项目 → 加载库 → Logisim-evolution 库…（Project → Load Library → Logisim-evolution Library…）`.
- `.circ` files are XML. They are mostly authored in the Logisim GUI, not by editing XML — only hand-edit XML for surgical, well-understood changes.

## Commands

There is no build system, lint, or test suite — `script/` is stdlib Python + one C++ binary;
the rest is Logisim circuits. To **regenerate the ROM toolchain outputs** (run from repo root, `python3` on this MinGW/Windows setup may be `python`):

```bash
# 1. Build the NSF dumper (needs MinGW g++/gcc; see script/gme_dump/PATCH.md for the GME patches)
cd script/gme_dump && make            # → nsfdump.exe   (make clean to rebuild)

# 2. Generate the frequency lookup ROMs → script/out/freq_*.txt
python script/make_tables.py

# 3. Regenerate the whole 16-slot playlist → script/out/track00..15.txt
python script/make_playlist.py        # needs the .nsf files in data/raw/

# Encode a single song by hand (log → ROM); --frame-cycles is the tempo knob
python script/encode.py <reg.log> <out.txt> --frame-cycles 32 --dedup
```

Dumper CLI: `nsfdump <in.nsf> <track> <seconds> [out.log]` (track is 0-based).

## Locked architecture decisions (changing these means rework)

- **ISA = 16-bit fixed-width**, opcode = high 4 bits: `0x0 WAIT`(+imm12), `0x1 WRITE`(+reg4+val8),
  `0x2 LWAIT`, `0x3 WKEY`, `0x4 LOADI`, `0x5 ADD`, `0x6 SUB`, `0x7 WRITEREG`, `0xF END`.
  Playback ROMs only ever use `WAIT`/`WRITE`/`END`; the ALU ops are reserved for vibrato/volume effects.
- **PC = 16-bit** (not the brief's old 12-bit).
- **APU register map (4-bit reg_id):** 0-3 = Pulse1, 4-7 = Pulse2, 8/10/11 = Triangle, **9 = channel-enable
  (`$4015` remapped into the unused `$4009` slot)**, 12/14/15 = Noise. `$4009/$400D/$4017` and DMC `$4010-$4013` are dropped.
- **No pitch scaling.** Buzzer plays real wall-clock Hz independent of sim clock speed, so the freq
  tables emit real NES Hz. Only *tempo* (WAIT duration) depends on the clock. (Corrects brief §5.)
- **ALU is a hard requirement** (teacher: "可控加减运算") — LOADI/ADD/SUB/WRITEREG + R0–R3 + a real ALU, must participate in playback, not just a demo.
- **"5-stage CPU" = single-cycle 5-stage (IF/ID/EX/MEM/WB), NOT pipelined** (teacher-confirmed).
- The only real correctness trap is the **WAIT-stall busy state machine** in the CPU (see `detailed_plan.html` §5):
  `WAIT` must load a countdown and stall the PC; only then does `frame_cycles` produce an even tempo.

## Critical environment & timing facts (these have already burned time — do not relearn them)

- **Always run the sim at >1000 Hz auto-tick (use 2–4 kHz).** Below 1000 Hz, Logisim's scheduler sleeps
  via `awaitNanos`, which Windows' ~15.6 ms timer granularity rounds up — capping throughput at ~32
  cycles/s regardless of the setting. >1000 Hz busy-waits and is accurate. This is a Windows timer
  issue, *not* a Buzzer/render/Logisim bug. Do **not** try to make the displayed rate be 60 Hz.
  (The red top-left number is the *measured* clock rate = tickFreq ÷ 2, normal color, not an error.)
- **Tempo comes from clock division, not from a slow clock.** Run the clock fast; let `frame_cycles=32`
  divide it down to a ~60 Hz music-frame rate (4 kHz tick ≈ 2000 cyc/s ÷ 32 ≈ 62.5 Hz note updates).
- **`frame_cycles` only divides when the CPU actually interprets `WAIT` and stalls the PC.** A direct
  `Counter → ROM address` scan is NOT divided by it — it plays the whole song in an instant. For the
  `BuzzerStress` scaffold (no CPU), divide explicitly with a `Splitter（分线器）` taking the counter's
  **high** bits (e.g. `Counter[13:3]`) as the ROM address.
- **GME build:** never pass `-DNSF_EMU_APU_ONLY` (heap corruption on MinGW); needs
  `-DBLARGG_LITTLE_ENDIAN=1`, static linking, `-std=c++14`, and `ext/emu2413.c` compiled as C with gcc.
  All captured in `script/gme_dump/Makefile` + `PATCH.md`.

## Conventions

- **Bilingual Logisim terms are mandatory.** Any tutorial/build-guide/defense doc that tells the user
  to click a menu or place a component must render names as `中文（English）` using the verified table in
  `.claude/skills/logisim-zh-terms/SKILL.md`. Invoke that skill when writing such docs.
- **Never hard-code Logisim keyboard shortcuts** — accelerators are user-configurable; give menu paths instead.
- **Prefer local sources over web search** for Logisim behavior claims: `ref/logisim-evolution/` source
  and `ref/logisim-evolution/src/main/resources/doc/en/html`. `ref/` holds vendored repos (GME, NSFPlay,
  logisim-evolution) and is git-ignored.
- **Move one milestone / one document at a time** — the user explicitly wants this to avoid context blow-up.
- **Do not edit §10 (the four-person division of labor) of `plan/project_brief_v6.html`.**
- The user communicates in Chinese and values rigor (cite official docs/source) and human-readable HTML deliverables.
- Do not revert or delete the user's untracked in-progress `.circ`/plan files unless explicitly asked.
