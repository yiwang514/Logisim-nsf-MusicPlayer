# Repository Instructions

## Project Context

This project builds a Logisim-evolution v4.1.0 music player for real NES NSF
music: a five-stage CPU plus a simplified Buzzer-based APU.

Before doing any substantial work, read:

1. `plan/SESSION_HANDOFF.md`
2. `plan/detailed_plan.html`
3. `plan/milestone1_guide.html` when continuing hardware guide work
4. `.claude/skills/logisim-zh-terms/SKILL.md` before writing Logisim-facing docs

The user is working in a Chinese Logisim UI and is effectively carrying the
whole project. Keep changes focused and move one milestone/document at a time.

## Current Status

- Script/toolchain work in `script/` is complete and verified.
- Milestone 1 Buzzer feasibility is verified:
  - BuzzerStress works when the Counter address is divided down by taking high
    bits through a Splitter.
  - PulseOneShot at timer address 253 outputs the correct 440 Hz tone.
- Next priority: draft `plan/milestone2_guide.html` for a real single Pulse
  channel in `apu.circ`.

## Critical Timing Notes

- Do not try to make Logisim's displayed clock rate be 60 Hz on Windows.
  Low-frequency auto-tick is inaccurate because Logisim uses sleeping waits
  around the millisecond range.
- Use 1000 Hz or higher auto-tick. The left display is full clock cycles per
  second, while the menu setting is half-cycle ticks.
- `frame_cycles=32` only works when the CPU really interprets `WAIT` and stalls
  the PC. It does not magically divide a direct `Counter -> ROM address` scan.
- For BuzzerStress-style tests, divide the address explicitly by dropping low
  counter bits:
  - Displayed 500 Hz: use `Counter[13:3]` for an 11-bit `freq_pulse` ROM
    address, giving about 62.5 address changes per second.
  - Displayed 1000 Hz: use `Counter[14:4]`, also about 62.5 changes per second.

## Logisim Documentation Rules

- When writing tutorials, build guides, or defense material for Logisim, use
  bilingual UI terms in the form required by
  `.claude/skills/logisim-zh-terms/SKILL.md`.
- Do not hard-code keyboard shortcuts. Logisim accelerators are configurable.
- Prefer local source/docs under `ref/logisim-evolution/` over web search for
  Logisim behavior claims.
- Do not edit section 10 of `plan/project_brief_v6.html`.

## Architecture Decisions

- ISA is fixed-width 16-bit:
  - `0x0 WAIT`, `0x1 WRITE`, `0x2 LWAIT`, `0x3 WKEY`, `0x4 LOADI`,
    `0x5 ADD`, `0x6 SUB`, `0x7 WRITEREG`, `0xF END`.
  - Playback ROMs use `WAIT`, `WRITE`, and `END`.
- PC is 16-bit. Track ROMs require more than 12 address bits.
- `$4015` maps to `reg_id = 9`; `$4009`, `$400D`, `$4017`, and DMC writes are
  dropped.
- Buzzer frequency inputs use real Hz. Do not scale pitch for Logisim clock
  speed.
- ALU is required and should participate in real playback by adjusting WAIT
  durations, not just as an isolated demo.

## Files And Generated Assets

- `script/out/track00..15.txt`: 16-bit instruction ROMs, `addrWidth=16`,
  `dataWidth=16`.
- `script/out/freq_pulse.txt`: 11-bit timer to 14-bit Hz table.
- `script/out/freq_triangle.txt`: 11-bit timer to 14-bit Hz table.
- `script/out/freq_noise.txt`: 4-bit noise code to 14-bit Hz table.
- `ref/` contains local source repositories and reference material. It is
  intentionally ignored by git.

## Git And Worktree Caution

The worktree may contain untracked generated or in-progress `.circ` and plan
files. Do not revert or delete user changes unless explicitly asked.
